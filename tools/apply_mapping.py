"""Deterministic tool: validate a mapping spec and turn it into named-input overrides.

Portable contract (Input Mapper dry-run, Builder/Runner apply):
    validate_spec(spec, model, local, register)      -> list of errors   (no values exposed)
    apply_mapping(spec, model, local, register)      -> {"overrides": {name: value},
                                                         "provenance": {name: {...}}}
CLI: python -m tools.apply_mapping <spec.json> [--apply --out overrides.json]
     exit 0 ok, 1 invalid spec, 2 blocked by the gap register gate

The Input Mapper (an agent) decides meaning: which local item feeds which model input,
by which whitelisted operation, or why an input is retained or a gap. This tool does
every number: it reads local and model cells, applies the operation with constants from
tools/constants_registry.yaml or model cells, and records provenance per value.

Operations (whitelist):
    copy                     value as is; unit dimensions must match
    per_period_to_per_week   currency per month -> per week; period length from model
                             days_per_year / registry months_per_year, cross-checked against
                             any "(N days)" stated in the source unit
    duration_to_doses        years -> dose count with a declared rule:
                             doses_starting_within (ceil) | complete_intervals_within (floor)
    mx_to_qx                 central death rates -> qx by single age, method exponential
                             (1 - exp(-mx)) or actuarial (mx / (1 + mx/2)); ages past an
                             open "N+" band only with open_band: carry_last_rate
    retain_global            keep the global value; needs a gap_id (retain_* gap) or
                             basis structural_setting | confirmed_by_local_text
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

import yaml

from tools import gap_register
from tools.read_local_inputs import read_local_inputs
from tools.workbook_io import read_named

REGISTRY = yaml.safe_load((Path(__file__).with_name("constants_registry.yaml")).read_text())
OPS = {"copy", "per_period_to_per_week", "duration_to_doses", "mx_to_qx", "retain_global"}
STATUSES = {"mapped", "retained", "gap"}
RETAIN_BASES = {"structural_setting", "confirmed_by_local_text"}
DOSE_RULES = {"doses_starting_within", "complete_intervals_within"}
MX_METHODS = {"exponential", "actuarial"}
CURRENCY_DIMS = {"currency", "currency_per_week", "currency_per_month", "currency_per_qaly"}
_PERIOD_DAYS = re.compile(r"\((\d+(?:\.\d+)?) days\)")


def dimension(unit) -> str | None:
    return REGISTRY["units"].get(unit)


def model_inputs(model) -> dict[str, dict]:
    """Input names (constant cells) of the model with value and unit, via its own input rows."""
    from tools.profile_workbook import profile
    prof = profile(model)
    values = read_named(model, data_only=False)
    out = {}
    for n, e in prof["names"].items():
        if e["role"] == "input":
            unit = (e.get("metadata") or {}).get("Unit")
            out[n] = {"value": values[n], "unit": unit, "vector": e["vector"], "sheet": e["sheet"], "ref": e["ref"]}
    return out


def _fmt_value(v) -> str:
    return str(int(v)) if isinstance(v, (int, float)) and float(v).is_integer() else str(v)


def validate_spec(spec: dict, model: dict, local: dict, register: dict) -> list[str]:
    errors = []
    gaps = {g["gap_id"]: g for g in register.get("gaps", [])}
    targets = [m.get("target") for m in spec.get("mappings", [])]
    for t in set(targets):
        if targets.count(t) > 1:
            errors.append(f"{t}: mapped more than once")
    for t in targets:
        if t not in model:
            errors.append(f"{t}: not an input of the model")
    for n in model:
        if n not in targets:
            errors.append(f"{n}: model input not covered by the mapping")
    used = set()
    remapped_currency = False
    retained_currency = []
    for m in spec.get("mappings", []):
        t, st, op, args = m.get("target"), m.get("status"), m.get("operation"), m.get("args", {})
        if t not in model:
            continue
        tgt = model[t]
        if st not in STATUSES:
            errors.append(f"{t}: unknown status {st!r}")
            continue
        gid = m.get("gap_id")
        if gid is not None:
            if gid not in gaps:
                errors.append(f"{t}: gap {gid} not in register")
            elif t not in gaps[gid]["target_names"]:
                errors.append(f"{t}: gap {gid} does not list this target")
        if st == "gap":
            if gid is None:
                errors.append(f"{t}: status gap needs gap_id")
            if op is not None:
                errors.append(f"{t}: a gap has no operation")
            continue
        if op not in OPS:
            errors.append(f"{t}: operation {op!r} not whitelisted")
            continue
        if (op == "retain_global") != (st == "retained"):
            errors.append(f"{t}: status {st} inconsistent with operation {op}")
        if op == "retain_global":
            basis = m.get("basis")
            if gid is None and basis not in RETAIN_BASES:
                errors.append(f"{t}: retain_global needs a gap_id or basis in {sorted(RETAIN_BASES)}")
            if gid is not None and gid in gaps and gaps[gid]["handling"] not in ("retain_tagged", "retain_flagged"):
                errors.append(f"{t}: gap {gid} handling {gaps[gid]['handling']} does not allow retention")
            if basis == "confirmed_by_local_text":
                c = m.get("confirm_in_source") or {}
                item = local.get(c.get("item"))
                if item is None:
                    errors.append(f"{t}: confirm_in_source item {c.get('item')!r} not found")
                else:
                    used.add(c["item"])
                    text = str(item.get(c.get("field", "value")))
                    needle = c.get("pattern", "{value}").replace("{value}", _fmt_value(tgt["value"]))
                    if needle not in text:
                        errors.append(f"{t}: local item {c['item']} does not confirm the retained value")
            if dimension(tgt["unit"]) in CURRENCY_DIMS:
                retained_currency.append(t)
            continue
        src_id = args.get("source")
        src = local.get(src_id)
        if src is None:
            errors.append(f"{t}: source {src_id!r} not in local inputs")
            continue
        used.add(src_id)
        if src["value"] is None or (isinstance(src["value"], list) and None in src["value"]):
            errors.append(f"{t}: source {src_id} has no value")
        sdim, tdim = dimension(src["unit"]), dimension(tgt["unit"])
        if op == "copy":
            if sdim is None or tdim is None:
                errors.append(f"{t}: unknown unit ({src['unit']!r} -> {tgt['unit']!r}); add to the registry")
            elif sdim != tdim:
                errors.append(f"{t}: copy changes dimension {sdim} -> {tdim}")
            if t == "currency_code" and src["value"] != tgt["value"]:
                remapped_currency = True
        elif op == "per_period_to_per_week":
            if (sdim, tdim) != ("currency_per_month", "currency_per_week") or args.get("period") != "month":
                errors.append(f"{t}: per_period_to_per_week supports month -> week currency only")
            stated = _PERIOD_DAYS.search(src["unit"] or "")
            if stated:
                derived = Fraction(str(model["days_per_year"]["value"])) / REGISTRY["constants"]["months_per_year"]
                if Fraction(stated.group(1)) != derived:
                    errors.append(f"{t}: source states {stated.group(1)} days per month, model implies {float(derived)}")
        elif op == "duration_to_doses":
            if sdim != "duration_years" or tdim != "count":
                errors.append(f"{t}: duration_to_doses needs years -> doses")
            if args.get("rule") not in DOSE_RULES:
                errors.append(f"{t}: dose rule must be one of {sorted(DOSE_RULES)}")
            if args.get("interval_weeks_from") not in model:
                errors.append(f"{t}: interval_weeks_from must name a model input")
        elif op == "mx_to_qx":
            if not tgt["vector"] or not isinstance(src["value"], list):
                errors.append(f"{t}: mx_to_qx maps a vector to a vector")
            elif not str(src["unit"]).startswith("mx"):
                errors.append(f"{t}: source unit {src['unit']!r} is not mx")
            if args.get("method") not in MX_METHODS:
                errors.append(f"{t}: mx method must be one of {sorted(MX_METHODS)}")
            if gid is None:
                errors.append(f"{t}: life-table conversion must reference its gap entry")
            if isinstance(src.get("ages"), list) and "lt_age" in model:
                single = {int(a) for a in src["ages"] if not (isinstance(a, str) and a.endswith("+"))}
                beyond = [a for a in model["lt_age"]["value"] if a not in single]
                has_open = any(isinstance(a, str) and a.endswith("+") for a in src["ages"])
                if beyond and not (has_open and args.get("open_band") == "carry_last_rate"):
                    errors.append(f"{t}: model ages {beyond[0]}-{beyond[-1]} have no local rate; "
                                  "declare open_band: carry_last_rate (and its gap entry) or supply rates")
    if remapped_currency:
        errors += [f"{t}: retains a global {model[t]['unit']} value although the currency is remapped"
                   for t in retained_currency]
    accounted = used | {u["item"] for u in spec.get("unused_local_items", [])}
    for g in register.get("gaps", []):
        accounted |= set(g["source_items"])
    for item_id in local:
        if item_id not in accounted:
            errors.append(f"{item_id}: local item neither used, listed in the gap register, nor declared unused")
    for u in spec.get("unused_local_items", []):
        if u["item"] in used:
            errors.append(f"{u['item']}: declared unused but used by a mapping")
        if not u.get("reason"):
            errors.append(f"{u['item']}: unused item needs a reason")
    return errors


def _compute(m, model, local, overrides):
    t, op, args = m["target"], m["operation"], m.get("args", {})
    if op == "retain_global":
        return model[t]["value"], {"retained_from": f"{model[t]['sheet']}!{model[t]['ref']}"}
    src = local[args["source"]]
    prov = {"source": {"item_id": args["source"], "sheet": src["sheet"], "cell": src["cell"]}}
    v = src["value"]
    if op == "copy":
        return v, prov
    if op == "per_period_to_per_week":
        dpy = Fraction(str(model["days_per_year"]["value"]))
        period_days = dpy / REGISTRY["constants"]["months_per_year"]
        prov["constants"] = {"days_per_week": REGISTRY["constants"]["days_per_week"],
                             "months_per_year": REGISTRY["constants"]["months_per_year"],
                             "days_per_year": f"model:{model['days_per_year']['sheet']}!{model['days_per_year']['ref']}"}
        return float(Fraction(str(v)) * REGISTRY["constants"]["days_per_week"] / period_days), prov
    if op == "duration_to_doses":
        iname = args["interval_weeks_from"]
        interval = overrides.get(iname, model[iname]["value"])
        days = Fraction(str(v)) * Fraction(str(model["days_per_year"]["value"]))
        n = days / (REGISTRY["constants"]["days_per_week"] * Fraction(str(interval)))
        prov["constants"] = {"interval_weeks": iname, "rule": args["rule"]}
        return (math.ceil(n) if args["rule"] == "doses_starting_within" else math.floor(n)), prov
    if op == "mx_to_qx":
        ages_model = model["lt_age"]["value"]
        labels = src["ages"]
        rates = {}
        open_age = None
        for lab, mx in zip(labels, v):
            if isinstance(lab, str) and lab.endswith("+"):
                open_age = int(lab[:-1])
                rates[open_age] = mx
            else:
                rates[int(lab)] = mx
        out = []
        for a in ages_model:
            if a in rates and a != open_age:
                mx = rates[a]
            elif open_age is not None and a >= open_age and args.get("open_band") == "carry_last_rate":
                mx = rates[open_age]
            else:
                raise ValueError(f"{t}: no local rate for age {a}")
            out.append(1 - math.exp(-mx) if args["method"] == "exponential" else mx / (1 + mx / 2))
        prov["constants"] = {"method": args["method"], "open_band": args.get("open_band")}
        return out, prov
    raise ValueError(op)


def apply_mapping(spec, model, local, register, dry_run=False) -> dict:
    errors = validate_spec(spec, model, local, register)
    gate = gap_register.gate(register)
    result = {"errors": errors, "gate_blocked": gate.blocked, "blocking_gaps": gate.blocking}
    if errors or dry_run:
        return result
    if gate.blocked:
        raise PermissionError(f"gap register blocks the pipeline: {gate.blocking}")
    overrides, provenance = {}, {}
    order = sorted(spec["mappings"], key=lambda m: m.get("operation") == "duration_to_doses")
    for m in order:
        if m["status"] == "gap":
            continue
        value, prov = _compute(m, model, local, overrides)
        overrides[m["target"]] = value
        provenance[m["target"]] = {"operation": m["operation"], "status": m["status"],
                                   "gap_id": m.get("gap_id"), **prov}
    result.update(overrides=overrides, provenance=provenance)
    return result


def load_all(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    root = Path(spec_path).resolve().parents[1]
    resolve = lambda p: (root / p) if not Path(p).is_absolute() else Path(p)
    model = model_inputs(resolve(spec["model"]))
    local = read_local_inputs(resolve(spec["local_inputs"]))
    register = gap_register.load(resolve(spec["gap_register"]))
    return spec, model, local, register


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    spec, model, local, register = load_all(a.spec)
    res = apply_mapping(spec, model, local, register, dry_run=not a.apply)
    for e in res["errors"]:
        print(f"INVALID: {e}")
    for g in res["blocking_gaps"]:
        print(f"BLOCKED: {g}")
    if res["errors"]:
        return 1
    if res["gate_blocked"]:
        return 2
    if a.apply and a.out:
        Path(a.out).write_text(json.dumps({k: res[k] for k in ("overrides", "provenance")}, indent=2, default=str))
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
