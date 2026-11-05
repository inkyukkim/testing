"""Deterministic tool: verify an adapted model against the global model it came from.

Portable contract (Model Verifier):
    verify(run_dir, spec_path) -> model_verification.json  {"overall": pass|fail, "checks": [...]}
CLI: python -m tools.verify_model <run_dir> <spec.json>   exit 0 pass, 1 fail

run_dir is a Builder/Runner output directory (run_log.json, overrides.json,
adapted_model.xlsx, recalc/adapted_model.xlsx). Checks:
  V01 structure      same sheets and defined names (identical references)
  V02 formulas       every formula cell byte-identical; none added or removed
  V03 inputs_only    every changed cell is a named input in the overrides; every override written exactly
  V04 round_trip     re-applying the mapping spec reproduces every override exactly
  V05 recalc_clean   no error values after recalculation
  V06 model_checks   every OK/FAIL check cell reads OK
  V07 parity         independent engine within 1e-6 (abs and rel) under the declared conventions
  V08 conventions    conventions detected from formulas match the declaration; no hardcoding
  V09 invariants     trace invariants (partition, monotonicity, cap, ToT <= OS, dosing schedule)
  V10 currency       every currency-valued input was mapped from a local source (none retained)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import openpyxl

from tools.apply_mapping import CURRENCY_DIMS, ROOT, apply_mapping, dimension, load_all
from tools.invariants import check_invariants
from tools.parity import parity
from tools.partsa_engine import ConventionError, load_conventions
from tools.profile_workbook import profile
from tools.workbook_io import list_names, read_named

ERRORS = ("#NUM!", "#VALUE!", "#NAME?", "#REF!", "#DIV/0!", "#N/A", "#NULL!", "Err:")


def _cells(wb):
    out = {}
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.value is not None:
                    out[(ws.title, c.coordinate)] = c.value
    return out


def verify(run_dir, spec_path, register_override=None, local_override=None) -> dict:
    run_dir = Path(run_dir)
    log = json.loads((run_dir / "run_log.json").read_text())
    if log["status"] != "built":
        return {"overall": "fail", "checks": [{"id": "V00", "name": "built", "status": "fail",
                                               "details": [f"run status {log['status']}: nothing to verify"]}]}
    spec, model, local, register = load_all(spec_path)
    local = local_override or local
    register = register_override or register
    glob_path = ROOT / spec["model"]
    adapted = run_dir / "adapted_model.xlsx"
    recalculated = run_dir / "recalc" / "adapted_model.xlsx"
    ov = json.loads((run_dir / "overrides.json").read_text())
    overrides, provenance = ov["overrides"], ov["provenance"]
    checks = []

    def add(cid, name, details):
        checks.append({"id": cid, "name": name, "status": "pass" if not details else "fail", "details": details})

    gwb, awb = openpyxl.load_workbook(glob_path), openpyxl.load_workbook(adapted)
    d = []
    if gwb.sheetnames != awb.sheetnames:
        d.append(f"sheets differ: {gwb.sheetnames} vs {awb.sheetnames}")
    gn, an = list_names(glob_path), list_names(adapted)
    if gn != an:
        d.append(f"defined names differ: {sorted(set(gn) ^ set(an)) or 'references changed'}")
    add("V01", "structure", d)

    gc, ac = _cells(gwb), _cells(awb)
    is_f = lambda v: isinstance(v, str) and v.startswith("=")
    d = [f"{k[0]}!{k[1]}: formula changed" for k, v in gc.items() if is_f(v) and ac.get(k) != v]
    d += [f"{k[0]}!{k[1]}: formula added" for k, v in ac.items() if is_f(v) and not is_f(gc.get(k))]
    add("V02", "formulas", d[:50])

    named_cells = {}
    for n, (s, ref) in gn.items():
        cells = [c for row in gwb[s][ref] for c in row] if ":" in ref else [gwb[s][ref]]
        for c in cells:
            named_cells[(s, c.coordinate)] = n
    d = []
    for k in set(gc) | set(ac):
        if gc.get(k) != ac.get(k) and not is_f(gc.get(k)):
            n = named_cells.get(k)
            if n is None or n not in overrides:
                d.append(f"{k[0]}!{k[1]}: changed but not a mapped input ({n})")
    written = read_named(adapted, list(overrides), data_only=False)
    d += [f"{n}: written value differs from override" for n, v in overrides.items() if written[n] != v]
    add("V03", "inputs_only", d[:50])

    try:
        again = apply_mapping(spec, model, local, register)
        d = again["errors"][:]
        d += [f"{n}: re-applied value differs" for n, v in again.get("overrides", {}).items() if overrides.get(n) != v]
        d += [f"{n}: in run but not in re-application" for n in set(overrides) - set(again.get("overrides", {}))]
    except PermissionError as e:
        d = [f"mapping cannot be re-applied: {e}"]
    add("V04", "round_trip", d)

    rwb = openpyxl.load_workbook(recalculated, data_only=True)
    d = [f"{ws.title}!{c.coordinate} = {c.value}" for ws in rwb.worksheets for row in ws.iter_rows() for c in row
         if isinstance(c.value, str) and c.value.startswith(ERRORS)]
    add("V05", "recalc_clean", d[:50])

    values = read_named(recalculated)
    d = [f"{k} = {v}" for k, v in values.items() if k.startswith("check_") and isinstance(v, str) and v != "OK"]
    add("V06", "model_checks", d)

    conv_path = glob_path.with_name(glob_path.stem + ".conventions.yaml")
    try:
        conv = load_conventions(conv_path)
        add("V07", "parity", parity(values, conv))
    except ConventionError as e:
        conv = None
        add("V07", "parity", [f"engine refuses declared conventions: {e}"])

    prof = profile(adapted, conv_path)
    d = list(prof.get("convention_mismatches", []))
    d += [f"hardcoding: {f}" for f in prof["hardcoding_findings"]]
    add("V08", "conventions", d)

    add("V09", "invariants", check_invariants(recalculated, values))

    d = []
    for n, e in model.items():
        if dimension(e["unit"]) in CURRENCY_DIMS:
            p = provenance.get(n)
            if p is None:
                d.append(f"{n}: currency input without provenance")
            elif p["status"] != "mapped" or "source" not in p:
                d.append(f"{n}: currency input not mapped from a local source ({p['status']})")
    add("V10", "currency", d)

    result = {"overall": "pass" if all(c["status"] == "pass" for c in checks) else "fail",
              "run_dir": str(run_dir), "spec": str(spec_path), "checks": checks}
    (run_dir / "model_verification.json").write_text(json.dumps(result, indent=2, default=str))
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir")
    ap.add_argument("spec")
    a = ap.parse_args(argv)
    res = verify(a.run_dir, a.spec)
    for c in res["checks"]:
        print(f"{c['id']} {c['name']:<13} {c['status'].upper()}" + (f"  {c['details'][0]}" if c["details"] else ""))
    print(res["overall"].upper())
    return 0 if res["overall"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
