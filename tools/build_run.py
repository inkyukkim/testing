"""Deterministic tool: build and run an adapted model from an approved mapping spec.

Portable contract (Builder/Runner):
    build_run(spec_path, out_dir, scenarios_path=None) -> run_log (also written as run_log.json)
CLI: python -m tools.build_run <spec.json> <out_dir> [--scenarios <yaml>]
     exit 0 built, 1 invalid spec, 2 blocked by the gap register (nothing is built)

Steps: gap gate -> apply_mapping -> write constants into named input cells of a copy of the
global model -> LibreOffice recalculation -> optional scenarios -> run_log with file hashes,
tool versions and the provenance of every override.

Scenario files contain references only (no numbers):
    scenarios:
      - id: KS1
        label: No age adjustment of utilities
        set:
          use_age_util_adj: {registry: switch_off}      # constants_registry.yaml key
          dr_costs: {item: KR-S10}                        # local item
          u_pd: {model: u_pf}                             # value of another model name
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tools import gap_register
from tools.apply_mapping import REGISTRY, ROOT, apply_mapping, load_all
from tools.recalc import recalc, soffice_binary
from tools.workbook_io import read_named, write_named

RESULT_KEYS = ["res_icer", "res_inc_total_cost", "res_inc_qaly_disc", "res_inc_ly_disc", "res_inc_nmb",
               "res_int_total_cost", "res_comp_total_cost", "res_int_qaly_disc", "res_comp_qaly_disc",
               "res_below_wtp", "res_dominance"]


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _versions() -> dict:
    import numpy
    import openpyxl
    try:
        lo = subprocess.run([soffice_binary(), "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:  # noqa: BLE001 - recorded, recalc itself will fail loudly
        lo = f"unavailable: {e}"
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    except Exception:  # noqa: BLE001
        commit, dirty = None, None
    return {"python": platform.python_version(), "openpyxl": openpyxl.__version__, "numpy": numpy.__version__,
            "libreoffice": lo, "registry_version": REGISTRY["version"], "git_commit": commit, "git_dirty": dirty}


def resolve_scenario(sset: dict, local: dict, base_values: dict) -> dict:
    out = {}
    for name, ref in sset.items():
        if set(ref) == {"registry"}:
            out[name] = REGISTRY["constants"][ref["registry"]]
        elif set(ref) == {"item"}:
            v = local[ref["item"]]["value"]
            if v is None:
                raise ValueError(f"scenario {name}: local item {ref['item']} has no value")
            out[name] = v
        elif set(ref) == {"model"}:
            out[name] = base_values[ref["model"]]
        else:
            raise ValueError(f"scenario {name}: reference must be exactly one of registry, item, model")
    return out


def build_run(spec_path, out_dir, scenarios_path=None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    spec, model, local, register = load_all(spec_path)
    paths = {k: (ROOT / spec[k]) for k in ("model", "local_inputs", "gap_register")}
    log = {"started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "spec": str(spec_path),
           "inputs": {k: {"path": str(p), "sha256": sha256(p)} for k, p in paths.items()},
           "tools": _versions()}
    log["inputs"]["spec"] = {"path": str(spec_path), "sha256": sha256(spec_path)}
    conv = paths["model"].with_name(paths["model"].stem + ".conventions.yaml")
    if conv.exists():
        log["inputs"]["conventions"] = {"path": str(conv), "sha256": sha256(conv)}

    def finish(status, **extra):
        log.update(status=status, finished=datetime.now(timezone.utc).isoformat(timespec="seconds"), **extra)
        (out_dir / "run_log.json").write_text(json.dumps(log, indent=2, default=str))
        return log

    gate = gap_register.gate(register)
    if gate.errors:
        return finish("invalid", errors=gate.errors)
    if gate.blocked:
        return finish("blocked", blocking_gaps=gate.blocking)
    res = apply_mapping(spec, model, local, register)
    if res["errors"]:
        return finish("invalid", errors=res["errors"])
    (out_dir / "overrides.json").write_text(json.dumps({"overrides": res["overrides"], "provenance": res["provenance"]},
                                                        indent=2, default=str))
    adapted = write_named(paths["model"], out_dir / "adapted_model.xlsx", res["overrides"])
    recalculated = recalc(adapted, out_dir / "recalc")
    values = read_named(recalculated)
    log["outputs"] = {"adapted_model": {"path": str(adapted), "sha256": sha256(adapted)},
                      "recalculated": {"path": str(recalculated), "sha256": sha256(recalculated),
                                       "note": "LibreOffice output embeds timestamps; hash identifies this run only"},
                      "overrides": {"path": str(out_dir / "overrides.json"), "sha256": sha256(out_dir / "overrides.json")}}
    log["base_case"] = {k: values[k] for k in RESULT_KEYS}
    if scenarios_path:
        scen_spec = yaml.safe_load(Path(scenarios_path).read_text())
        log["inputs"]["scenarios"] = {"path": str(scenarios_path), "sha256": sha256(scenarios_path)}
        results = []
        for sc in scen_spec["scenarios"]:
            overrides = resolve_scenario(sc["set"], local, values)
            src = write_named(adapted, out_dir / f"scenario_{sc['id']}.xlsx", overrides)
            v = read_named(recalc(src, out_dir / f"recalc_{sc['id']}"))
            results.append({"id": sc["id"], "label": sc["label"], "set": sc["set"], "results": {k: v[k] for k in RESULT_KEYS}})
        log["scenarios"] = results
    return finish("built")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("out_dir")
    ap.add_argument("--scenarios")
    a = ap.parse_args(argv)
    log = build_run(a.spec, a.out_dir, a.scenarios)
    print(f"{log['status'].upper()}: run_log at {Path(a.out_dir) / 'run_log.json'}")
    for g in log.get("blocking_gaps", []):
        print(f"BLOCKED: {g}")
    for e in log.get("errors", []):
        print(f"INVALID: {e}")
    return {"built": 0, "invalid": 1, "blocked": 2}[log["status"]]


if __name__ == "__main__":
    sys.exit(main())
