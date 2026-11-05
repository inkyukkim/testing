"""Deterministic tool: link each report numeral to candidate model cells (Report Profiler).

    match(tokens, base_values, scenario_values=None) -> [{token, block, candidates, status}]
CLI: python -m tools.match_numbers <report.docx> <recalculated_model.xlsx>
         [--scenarios <scenarios.yaml> --model <model.xlsx> --work <dir>] [--out matches.json]

A candidate is (name, context) where the named cell, formatted at the token's precision
(percent tokens scaled by 100), equals the token. Context "base" or a scenario id; scenario
candidates are limited to names whose value differs from the base case in that scenario.
status: unique | ambiguous (agent resolves from context) | unmatched (no cell displays as
this numeral: either a scenario not supplied or an untraceable number).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _numeric(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def displays_as(value, token) -> bool:
    scale = 100 if token["kind"] == "percent" else 1
    return float(f"{value * scale:.{token['decimals']}f}") == token["value"]


def match(tokens, base_values, scenario_values=None) -> list[dict]:
    contexts = [("base", {k: v for k, v in base_values.items() if _numeric(v)})]
    for sid, vals in (scenario_values or {}).items():
        contexts.append((sid, {k: v for k, v in vals.items() if _numeric(v) and v != base_values.get(k)}))
    out = []
    for t in tokens:
        cands = [{"name": n, "context": ctx} for ctx, vals in contexts for n, v in vals.items() if displays_as(v, t)]
        status = "unmatched" if not cands else "unique" if len(cands) == 1 else "ambiguous"
        out.append({"token": t["token"], "block": t["block"], "section": t["section"],
                    "candidates": cands, "status": status})
    return out


def main():
    from tools.docx_extract import extract
    from tools.workbook_io import read_named
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("docx")
    ap.add_argument("recalculated")
    ap.add_argument("--scenarios")
    ap.add_argument("--model")
    ap.add_argument("--work", default="runs/match_numbers")
    ap.add_argument("--out")
    a = ap.parse_args()
    scen = None
    if a.scenarios:
        from tools.scenario_runner import run_scenarios
        scen = run_scenarios(a.model, a.scenarios, a.work)
    res = match(extract(a.docx)["tokens"], read_named(a.recalculated), scen)
    text = json.dumps(res, indent=2)
    Path(a.out).write_text(text) if a.out else print(text)


if __name__ == "__main__":
    main()
