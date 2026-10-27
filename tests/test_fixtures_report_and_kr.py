"""Checks on the UK report fixture (numbers trace to recalculated model cells) and on
the KR adaptation input fixture."""
import json
import re

import openpyxl
import pytest
from docx import Document

from conftest import FIXTURES, MODEL
from tools.recalc import recalc
from tools.workbook_io import list_names, read_named, write_named

PROV = json.loads((FIXTURES / "global_report_UK.provenance.json").read_text())
DOC = Document(FIXTURES / "global_report_UK.docx")
NUM = re.compile(r"(?<![A-Za-z0-9.\-])-?£?\d(?:[\d,]*\d)?(?:\.\d+)?%?(?![A-Za-z0-9])")


def body_chunks():
    """Text the traceability rule applies to: paragraphs after the title page and before
    References (headings, table captions and citation markers excluded) plus all table cells."""
    chunks, started = [], False
    for p in DOC.paragraphs:
        if p.style.name.startswith("Heading"):
            started = True
            if p.text == "References":
                break
            continue
        if started and not p.text.startswith("Table "):
            chunks.append(p.text)
    for t in DOC.tables:
        chunks += [c.text for row in t.rows[1:] for c in row.cells]
    return [re.sub(r"\[\d+\]|Section \d+(\.\d+)*", "", c) for c in chunks]


def test_every_number_in_report_body_is_traced():
    displays = {x["display"] for x in PROV["numbers"]}
    untraced = sorted({m for c in body_chunks() for m in NUM.findall(c)} - displays)
    assert not untraced, f"numbers without provenance: {untraced}"


def test_every_provenance_display_appears_in_report():
    text = "\n".join(body_chunks())
    missing = [x["id"] for x in PROV["numbers"] if x["display"] not in text]
    assert not missing


def formatted(value, fmt):
    x = value * fmt["scale"]
    return round(abs(x), fmt["decimals"])


def parse(display, fmt):
    s = display.removeprefix("-").removeprefix(fmt["prefix"]).removesuffix(fmt["suffix"]).replace(",", "")
    return float(s)


def test_base_case_numbers_match_recalculated_cells(model_values):
    names = list_names(MODEL)
    for x in PROV["numbers"]:
        src = x["source"]
        if src["scenario"] is not None:
            continue
        assert names[src["name"]] == (src["sheet"], src["cell"]), f"{x['id']} cell reference stale"
        assert parse(x["display"], x["format"]) == formatted(model_values[src["name"]], x["format"]), x


def test_scenario_numbers_match_recalculated_cells(tmp_path):
    for sid, sc in PROV["scenarios"].items():
        src = write_named(MODEL, tmp_path / f"{sid}.xlsx", sc["overrides"])
        values = read_named(recalc(src, tmp_path / f"rc_{sid}"))
        for x in PROV["numbers"]:
            if x["source"]["scenario"] == sid:
                assert parse(x["display"], x["format"]) == formatted(values[x["source"]["name"]], x["format"]), x


def test_conclusion_cites_icer_against_uk_threshold(model_values):
    concl = next(i for i, p in enumerate(DOC.paragraphs) if p.text == "7. Conclusion")
    text = DOC.paragraphs[concl + 1].text
    assert f"£{model_values['res_icer']:,.0f}" in text and f"£{model_values['wtp_threshold']:,.0f}" in text


KR_REQUIRED = {"KR-S02", "KR-S05", "KR-S06", "KR-S07", "KR-C01", "KR-C02", "KR-C03", "KR-C06",
               "KR-C08", "KR-C09", "KR-C10", "KR-C12", "KR-C13", "KR-U01", "KR-U02"}


def test_kr_adaptation_input_items():
    wb = openpyxl.load_workbook(FIXTURES / "adaptation_input_KR.xlsx")
    items = {}
    for ws in wb.worksheets[1:]:
        assert [c.value for c in ws[3]] == ["item_id", "Item", "Value", "Unit", "Source (synthetic)", "Note"]
        for row in ws.iter_rows(min_row=4, values_only=True):
            assert row[0] not in items, f"duplicate item_id {row[0]}"
            items[row[0]] = row
    assert KR_REQUIRED <= items.keys()
    assert items["KR-S02"][2] == "KRW"
    for k in KR_REQUIRED - {"KR-S02"}:
        assert isinstance(items[k][2], (int, float)), k
    assert items["KR-C11"][2] is None, "terminal care gap is intentional"
