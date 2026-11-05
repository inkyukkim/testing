"""Deterministic tool: evaluate and validate a claims register (Claims Analyst, Report Writer gate).

    evaluate_register(register, global_contexts, local_contexts=None) -> register with truths filled
        (global_contexts None: local truth only)
    validate(register, blocks) -> errors (schema + rules K1-K7)
    review_notes(register) -> advisory REVIEW lines (not errors) for a human approving the register
    ready(register) -> blockers before the Report Writer may start

rerender means: the excerpt stays word for word; only its numerals become placeholders, rendered
from the adapted model in the local format (a currency symbol attached to a numeral is part of the
numeral). Any other change to the excerpt is reword. Text of the block outside the excerpt is
governed by its own claims and by the Report Verifier's jurisdiction check (R04).
CLI: python -m tools.claims <register.json> <report.docx> <global_model.xlsx>
         [--global-scenarios <yaml>] [--local-run <build_run dir>] [--work <dir>] [--out <json>]
     exit 0 valid and ready, 1 invalid, 2 valid but not ready
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

import yaml

from tools.evaluate_claim import check_no_literals, evaluate
from tools.gap_register import _check
from tools.jurisdiction_lint import TERMS, lint

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "claims_register.schema.yaml"
REGEN_KINDS = {"ranking", "sensitivity_ranking", "threshold_comparison", "magnitude_judgement"}
# advisory: a rationale that asks for new wording contradicts action rerender
_REWORDING = re.compile(r"\breword|\bwording\b|\brephras|\bshould (?:say|read)\b", re.IGNORECASE)


def _currency_numerals(jurisdiction: str) -> re.Pattern:
    symbols = TERMS["jurisdictions"][jurisdiction].get("currency", [])
    alt = "|".join(re.escape(s) for s in sorted(symbols, key=len, reverse=True)) or "(?!)"
    return re.compile(rf"(?:{alt})\s?\d[\d,]*(?:\.\d+)?")


def rerender_terms(excerpt: str, jurisdiction: str = "UK") -> list[str]:
    """Source-jurisdiction terms a rerender would keep: lint hits in the excerpt after removing
    currency-prefixed numerals (those are re-rendered in the local currency)."""
    text = _currency_numerals(jurisdiction).sub("", excerpt or "")
    return sorted({h["term"] for h in lint([{"index": 0, "kind": "paragraph", "section": "", "text": text}], jurisdiction)})


def evaluate_register(register, global_contexts, local_contexts=None) -> dict:
    reg = copy.deepcopy(register)
    for c in reg["claims"]:
        if global_contexts is None:
            c.pop("truth_global", None)          # local-only evaluation (renderer, report verifier)
        else:
            c["truth_global"] = evaluate(c["expression"], global_contexts)["truth"]
        if local_contexts is None:
            c["truth_local"] = "pending" if c["expression"] else "not_evaluable"
            c["evidence_local"] = {}
        else:
            loc = evaluate(c["expression"], local_contexts)
            c["truth_local"], c["evidence_local"] = loc["truth"], loc["evidence"]
    return reg


def _jurisdiction(register) -> str:
    j = (register.get("local_context") or {}).get("jurisdiction_from") or "UK"
    return j if j in TERMS["jurisdictions"] else "UK"


def validate(register, blocks=None) -> list[str]:
    errors: list[str] = []
    _check(register, yaml.safe_load(SCHEMA.read_text()), "$", errors)
    jur = _jurisdiction(register)
    for c in register.get("claims", []):
        cid, kind, action = c.get("claim_id"), c.get("kind"), c.get("action")
        try:
            if c.get("expression"):
                check_no_literals(c["expression"])
        except ValueError as e:
            errors.append(f"{cid}: K5 {e}")
        if c.get("truth_global") is False:
            errors.append(f"{cid}: K1 claim is false on the global model")
        if kind == "external_assertion_untraceable" and action != "human_review":
            errors.append(f"{cid}: K2 untraceable assertion needs human_review")
        if kind == "jurisdiction_specific" and action not in ("reword", "remove", "human_review"):
            errors.append(f"{cid}: K2 jurisdiction_specific must be reworded, removed or reviewed")
        if kind == "overall_conclusion" and action not in ("reword", "remove"):
            errors.append(f"{cid}: K2 overall_conclusion must be reworded or removed")
        if action == "regenerate" and (kind not in REGEN_KINDS or not c.get("expression")):
            errors.append(f"{cid}: K3 regenerate needs a data-driven kind and an expression")
        if action == "rerender" and c.get("truth_local") is False:
            errors.append(f"{cid}: K4 claim is false locally and cannot be rerendered")
        if action == "rerender" and (terms := rerender_terms(c.get("excerpt", ""), jur)):
            errors.append(f"{cid}: K7 rerender would keep source-jurisdiction terms {terms}; reword instead")
        if blocks is not None:
            b = c.get("block")
            if not isinstance(b, int) or b >= len(blocks) or c.get("excerpt", "") not in blocks[b]["text"]:
                errors.append(f"{cid}: K6 excerpt not found in block {b}")
    return errors


def review_notes(register) -> list[str]:
    """Advisory lines for the human approving the register; they never make it invalid."""
    out = []
    for c in register.get("claims", []):
        if c.get("action") == "rerender" and _REWORDING.search(c.get("rationale") or ""):
            out.append(f"{c.get('claim_id')}: action rerender keeps the excerpt verbatim, but the rationale "
                       "asks for new wording; reword if any word of the excerpt must change")
    return out


def ready(register) -> list[str]:
    out = []
    for c in register["claims"]:
        if c["action"] in ("rerender", "regenerate") and c.get("truth_local") == "pending":
            out.append(f"{c['claim_id']}: local truth pending (adapted model not built)")
        if c["action"] == "human_review":
            out.append(f"{c['claim_id']}: open human review")
    return out


def main() -> int:
    from tools.docx_extract import extract
    from tools.recalc import recalc
    from tools.scenario_runner import run_scenarios
    from tools.workbook_io import read_named
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("register")
    ap.add_argument("report")
    ap.add_argument("model")
    ap.add_argument("--global-scenarios")
    ap.add_argument("--local-run")
    ap.add_argument("--work", default="runs/claims")
    ap.add_argument("--out")
    a = ap.parse_args()
    reg = json.loads(Path(a.register).read_text())
    work = Path(a.work)
    g = {"base": read_named(recalc(a.model, work / "global"))}
    if a.global_scenarios:
        g.update(run_scenarios(a.model, a.global_scenarios, work / "global_scen"))
    loc = None
    if a.local_run:
        loc = {"base": read_named(Path(a.local_run) / "recalc" / "adapted_model.xlsx")}
    reg = evaluate_register(reg, g, loc)
    errors = validate(reg, extract(a.report)["blocks"])
    blockers = ready(reg)
    if a.out:
        Path(a.out).write_text(json.dumps(reg, indent=2, default=str))
    for e in errors:
        print(f"INVALID: {e}")
    for r in review_notes(reg):
        print(f"REVIEW: {r}")
    for b in blockers:
        print(f"NOT READY: {b}")
    return 1 if errors else 2 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
