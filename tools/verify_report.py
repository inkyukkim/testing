"""Deterministic tool: verify a rendered local report (Report Verifier).

    verify_report(report_docx, run_dir, claims_register, gap_register, jurisdiction_from="UK")
        -> report_verification.json  {"overall": pass|fail, "checks": [...]}
CLI: python -m tools.verify_report <report.docx> <run_dir> <claims.json> <gap_register.yaml> [--from UK]
     exit 0 pass, 1 fail. Reads <report>.provenance.json written by tools/render_report.py.

  R01 trace         numerals equal the provenance in document order; each still matches its cell
  R02 rounding      every displayed difference and the ICER pass the rounding-interval check; the
                    rounding note is present exactly when a figure needs it
  R03 claims        every truth-dependent choice re-evaluated on the adapted model; every rerender /
                    regenerate claim WITH an expression is used (expression-less ones, such as scope
                    notes, may appear as plain prose); no removed claim is used
  R04 jurisdiction  no term of the source jurisdiction outside the References
  R05 retained      every target of a retain_tagged / retain_flagged gap is listed in the report
  R06 status        a final report needs a ready claims register; a draft carries the DRAFT banner
  R07 currency      every currency figure uses the symbol of the model's currency_code
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from tools.claims import evaluate_register, ready
from tools.docx_extract import extract
from tools.gap_register import load as load_register
from tools.jurisdiction_lint import lint
from tools.render_report import FORMATS, TemplateError, format_value, rounding_needed
from tools.workbook_io import read_named


def verify_report(report, run_dir, claims_path, register_path, jurisdiction_from="UK") -> dict:
    report, run_dir = Path(report), Path(run_dir)
    manifest = json.loads(report.with_suffix(".provenance.json").read_text())
    x = extract(report)
    text = "\n".join(b["text"] for b in x["blocks"])
    log = json.loads((run_dir / "run_log.json").read_text())
    contexts = {"base": read_named(run_dir / "recalc" / "adapted_model.xlsx")}
    for sc in log.get("scenarios", []):
        contexts[sc["id"]] = read_named(run_dir / f"recalc_{sc['id']}" / f"scenario_{sc['id']}.xlsx")
    checks = []

    def add(cid, name, details):
        checks.append({"id": cid, "name": name, "status": "pass" if not details else "fail", "details": details[:50]})

    nums = manifest["numbers"]
    d = []
    toks = [t["token"] for t in x["tokens"]]
    for i, (a, n) in enumerate(zip(toks, nums)):
        if a != n["display"]:
            d.append(f"position {i}: report shows {a!r}, provenance {n['display']!r}")
    if len(toks) != len(nums):
        d.append(f"report has {len(toks)} numerals, provenance {len(nums)}")
    for n in nums:
        src = n["source"]
        ctx = src["scenario"] or "base"
        current = contexts.get(ctx, {}).get(src["name"])
        if current is None or format_value(current, n["format"]) != n["display"]:
            d.append(f"{n['id']} {src['name']}@{ctx}: cell now displays differently from {n['display']!r}")
    add("R01", "trace", d)

    d = []
    try:
        needed = rounding_needed(contexts, nums)
        note = " ".join(FORMATS["rounding_note"].split())
        if needed and note not in text:
            d.append("rounding note required but absent")
        if not needed and note in text:
            d.append("rounding note present but no figure needs it")
    except TemplateError as e:
        d.append(str(e))
    add("R02", "rounding", d)

    claims = evaluate_register(json.loads(Path(claims_path).read_text()), None, contexts)
    by_id = {c["claim_id"]: c for c in claims["claims"]}
    used = [u for u in manifest["claims_used"] if "claim" in u]
    used_ids = {u["claim"] for u in used}
    d = []
    for u in used:
        c = by_id.get(u["claim"])
        if c is None:
            d.append(f"{u['claim']}: not in the claims register")
            continue
        if "kept" in u:
            t = c["truth_local"]
            want = t if u["directive"] == "if" else (not t) if u["directive"] == "ifnot" else u["kept"]
            if u["directive"] in ("if", "ifnot") and (not isinstance(t, bool) or u["kept"] != want):
                d.append(f"{u['claim']}: {u['directive']} kept={u['kept']} but local truth is {t!r}")
        if c["action"] == "remove":
            d.append(f"{u['claim']}: removed claim used in the report")
    for c in claims["claims"]:
        if c["action"] in ("rerender", "regenerate") and c["expression"] and c["claim_id"] not in used_ids:
            d.append(f"{c['claim_id']}: {c['action']} claim not used by the report")
    add("R03", "claims", d)

    hits = [h for h in lint(x["blocks"], jurisdiction_from) if h["kind"] != "reference"]
    add("R04", "jurisdiction", [f"block {h['block']} ({h['section']}): {h['term']}" for h in hits])

    register = load_register(register_path)
    d = [f"{t} ({g['gap_id']}): not listed in the report" for g in register["gaps"]
         if g["handling"] in ("retain_tagged", "retain_flagged") for t in g["target_names"]
         if f"({t})" not in text and f"{t}:" not in text]
    add("R05", "retained", d)

    d = []
    title_text = " ".join(b["text"] for b in x["blocks"] if b["kind"] == "title")
    blockers = ready(claims)
    if manifest["draft"]:
        if "DRAFT" not in title_text:
            d.append("draft report without the DRAFT banner")
    else:
        if blockers:
            d.append(f"final report with open items: {blockers}")
        if "DRAFT" in title_text:
            d.append("final report carries a DRAFT banner")
    add("R06", "status", d)

    symbol = FORMATS["currencies"][contexts["base"]["currency_code"]]["symbol"]
    others = [s for c, v in FORMATS["currencies"].items() for s in [v["symbol"]] if s != symbol]
    d = [f"{t['token']} in {t['section']}" for t in x["tokens"] if t["kind"] == "currency" and any(o in t["token"] for o in others)]
    add("R07", "currency", d)

    result = {"overall": "pass" if all(c["status"] == "pass" for c in checks) else "fail",
              "report": str(report), "draft": manifest["draft"], "checks": checks}
    report.with_name(report.stem + "_verification.json").write_text(json.dumps(result, indent=2, default=str))
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for a in ("report", "run_dir", "claims", "gap_register"):
        ap.add_argument(a)
    ap.add_argument("--from", dest="jurisdiction_from", default="UK")
    a = ap.parse_args()
    res = verify_report(a.report, a.run_dir, a.claims, a.gap_register, a.jurisdiction_from)
    for c in res["checks"]:
        print(f"{c['id']} {c['name']:<13} {c['status'].upper()}" + (f"  {c['details'][0]}" if c["details"] else ""))
    print(res["overall"].upper() + (" (draft)" if res["draft"] else ""))
    return 0 if res["overall"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
