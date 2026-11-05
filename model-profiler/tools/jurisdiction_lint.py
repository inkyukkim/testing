"""Deterministic tool: find jurisdiction-specific terms in an extracted report.

    lint(blocks, jurisdiction="UK") -> [{block, kind, section, term, category}]
CLI: python -m tools.jurisdiction_lint <report.docx> [--jurisdiction UK]   exit 1 if any hit
Terms come from tools/jurisdiction_terms.yaml (case-sensitive for acronyms, whole words).
Blocks of kind "reference" are reported separately (citations may legitimately remain).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

TERMS = yaml.safe_load(Path(__file__).with_name("jurisdiction_terms.yaml").read_text())


def _pattern(term: str) -> re.Pattern:
    if term == "£":
        return re.compile("£")
    flags = 0 if term.isupper() or len(term) <= 4 else re.IGNORECASE
    return re.compile(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", flags)


def lint(blocks, jurisdiction="UK") -> list[dict]:
    hits = []
    cats = TERMS["jurisdictions"][jurisdiction]
    for b in blocks:
        found = set()
        for cat, terms in cats.items():
            for term in sorted(terms, key=len, reverse=True):
                if any(term in f for f in found):
                    continue          # already covered by a longer term (e.g. "NICE reference case")
                if _pattern(term).search(b["text"]):
                    found.add(term)
                    hits.append({"block": b["index"], "kind": b["kind"], "section": b["section"],
                                 "term": term, "category": cat})
    return hits


def main() -> int:
    from tools.docx_extract import extract
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("docx")
    ap.add_argument("--jurisdiction", default="UK")
    a = ap.parse_args()
    hits = lint(extract(a.docx)["blocks"], a.jurisdiction)
    print(json.dumps(hits, indent=2))
    return 1 if any(h["kind"] != "reference" for h in hits) else 0


if __name__ == "__main__":
    sys.exit(main())
