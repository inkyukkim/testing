"""Deterministic tool: extract a report's structure and numeric tokens (Report Profiler, Verifier).

    extract(docx) -> {"blocks": [...], "tokens": [...]}
CLI: python -m tools.docx_extract <report.docx> [--out profile.json]

Blocks follow document order (paragraphs and table cells interleaved). Tokens are the
numerals the traceability rule applies to: body paragraphs and table body cells after the
title page and before "References". Exempt (structural numerals, defined here and nowhere
else): headings, table/figure captions, citation markers [n], and references such as
"Section 4.3", "Table 8" or "Tables 6 and 7". Exempt spans are blanked, not removed, so
token offsets index the original text.
Equivalent in R: officer::docx_summary + the same regular expressions.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

NUM = re.compile(r"(?<![A-Za-z0-9.\-])-?£?\d(?:[\d,]*\d)?(?:\.\d+)?%?(?![A-Za-z0-9])")
CAPTION = re.compile(r"^(Table|Figure) \d+\. ")
STRUCTURAL = re.compile(r"\[\d+\]|\b(?:Sections?|Tables?|Figures?) \d+(?:\.\d+)*(?: and \d+(?:\.\d+)*)?")
END_HEADING = "References"


def _blank_structural(text: str) -> str:
    return STRUCTURAL.sub(lambda m: " " * len(m.group(0)), text)


def parse_token(tok: str) -> dict:
    kind = "currency" if "£" in tok else "percent" if tok.endswith("%") else "plain"
    body = tok.replace("£", "").replace("%", "").replace(",", "")
    decimals = len(body.split(".")[1]) if "." in body else 0
    return {"value": float(body), "decimals": decimals, "kind": kind}


def extract(path) -> dict:
    doc = Document(path)
    blocks, tokens = [], []
    started, ended = False, False
    section = subsection = None
    tcount = 0

    def add_block(**b):
        b["index"] = len(blocks)
        blocks.append(b)
        return b

    def scan(block):
        text = _blank_structural(block["text"])
        for m in NUM.finditer(text):
            tokens.append({"token": m.group(0), "block": block["index"], "start": m.start(), "end": m.end(),
                           "section": block["section"], "subsection": block["subsection"], **parse_token(m.group(0))})

    for el in doc.element.body.iterchildren():
        if el.tag.endswith("}p"):
            p = Paragraph(el, doc)
            style = p.style.name
            if style.startswith("Heading"):
                started = True
                level = int(style.split()[-1]) if style.split()[-1].isdigit() else 1
                if level == 1:
                    section, subsection = p.text, None
                    ended = ended or p.text == END_HEADING
                else:
                    subsection = p.text
                add_block(kind="heading", level=level, text=p.text, section=section, subsection=subsection)
                continue
            if not p.text.strip():
                continue
            kind = "title" if not started else "reference" if ended else "caption" if CAPTION.match(p.text) else \
                "list_item" if "List" in style else "paragraph"
            b = add_block(kind=kind, text=p.text, section=section, subsection=subsection)
            if kind in ("paragraph", "list_item"):
                scan(b)
        elif el.tag.endswith("}tbl") and started and not ended:
            tcount += 1
            t = Table(el, doc)
            for r, row in enumerate(t.rows):
                seen = []
                for c, cell in enumerate(row.cells):
                    if cell._tc in seen:
                        continue
                    seen.append(cell._tc)
                    b = add_block(kind="table_header" if r == 0 else "table_cell", table=tcount, row=r, col=c,
                                  text=cell.text, section=section, subsection=subsection)
                    if r > 0:
                        scan(b)
    return {"document": str(path), "blocks": blocks, "tokens": tokens}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("docx")
    ap.add_argument("--out")
    a = ap.parse_args()
    text = json.dumps(extract(a.docx), indent=2)
    Path(a.out).write_text(text) if a.out else print(text)


if __name__ == "__main__":
    main()
