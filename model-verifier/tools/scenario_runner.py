"""Deterministic tool: run a model's scenario definitions and collect named results.

    run_scenarios(model_xlsx, scenarios_yaml, out_dir) -> {scenario_id: {name: value}}
CLI: python -m tools.scenario_runner <model.xlsx> <scenarios.yaml> <out_dir> [--out values.json]

Scenario files for a *global* model are human-authored inputs (like input cells), so their
overrides may hold values. Scenarios on an *adapted* model are run by tools/build_run.py,
whose scenario files hold references only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from tools.recalc import recalc
from tools.workbook_io import read_named, write_named


def load_scenarios(path) -> list[dict]:
    return yaml.safe_load(Path(path).read_text())["scenarios"]


def run_scenarios(model, scenarios_yaml, out_dir) -> dict[str, dict]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    values = {}
    for sc in load_scenarios(scenarios_yaml):
        src = write_named(model, out_dir / f"model_{sc['id']}.xlsx", sc["overrides"])
        values[sc["id"]] = read_named(recalc(src, out_dir / f"rc_{sc['id']}"))
    return values


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model")
    ap.add_argument("scenarios")
    ap.add_argument("out_dir")
    ap.add_argument("--out")
    a = ap.parse_args()
    vals = run_scenarios(a.model, a.scenarios, a.out_dir)
    text = json.dumps(vals, indent=2, default=str)
    Path(a.out).write_text(text) if a.out else print(text)


if __name__ == "__main__":
    main()
