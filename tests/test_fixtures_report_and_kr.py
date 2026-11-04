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
from tools.docx_extract import CAPTION, NUM, STRUCTURAL, extract  # single definition




def body_chunks():
    """Text the traceability rule applies to, in document order: paragraphs and table cells after
    the title page and before References. Exempt: headings, table captions, citation markers and
    references to sections/tables (the structural numerals defined by this verifier)."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    chunks, started = [], False
    for el in DOC.element.body.iterchildren():
        if el.tag.endswith("}p"):
            p = Paragraph(el, DOC)
            if p.style.name.startswith("Heading"):
                started = True
                if p.text == "References":
                    break
                continue
            if started and not CAPTION.match(p.text):
                chunks.append(p.text)
        elif el.tag.endswith("}tbl") and started:
            t = Table(el, DOC)
            for row in t.rows[1:]:
                seen = []
                for c in row.cells:          # merged cells repeat; keep each cell once
                    if c._tc not in seen:
                        seen.append(c._tc)
                        chunks.append(c.text)
    return [STRUCTURAL.sub("", c) for c in chunks]


def test_every_number_in_report_body_is_traced():
    displays = {x["display"] for x in PROV["numbers"]}
    untraced = sorted({m for c in body_chunks() for m in NUM.findall(c)} - displays)
    assert not untraced, f"numbers without provenance: {untraced}"


def test_numerals_match_provenance_in_document_order():
    """Stronger than set membership: the k-th numeral in the text is the k-th provenance entry,
    so a stray number cannot hide behind an identical traced one."""
    found = [m for c in body_chunks() for m in NUM.findall(c)]
    expected = [x["display"] for x in PROV["numbers"]]
    for i, (a, b) in enumerate(zip(found, expected)):
        assert a == b, f"position {i}: text has {a!r}, provenance has {b!r} ({PROV['numbers'][i]['id']})"
    assert len(found) == len(expected)


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


KR_REQUIRED = {"KR-S02", "KR-S05", "KR-S06", "KR-S07", "KR-P01", "KR-P02",
               "KR-C01", "KR-C02", "KR-C03", "KR-C06", "KR-C08", "KR-C09", "KR-C10", "KR-C12", "KR-C13",
               "KR-U01", "KR-U02"} | {f"KR-T0{i}" for i in range(1, 10)}
KR_DELIBERATE_GAPS = {"KR-C11", "KR-U03", "KR-U04", "KR-P03"}


@pytest.fixture(scope="module")
def kr():
    return openpyxl.load_workbook(FIXTURES / "adaptation_input_KR.xlsx")


def kr_items(kr):
    items = {}
    for ws in kr.worksheets[1:]:
        if ws.title == "LifeTable_KR":
            continue
        assert [c.value for c in ws[3]] == ["item_id", "Item", "Value", "Unit", "Source (synthetic)", "Note"], ws.title
        for row in ws.iter_rows(min_row=4, values_only=True):
            assert row[0] not in items, f"duplicate item_id {row[0]}"
            items[row[0]] = row
    return items


def test_kr_adaptation_input_items(kr):
    items = kr_items(kr)
    assert KR_REQUIRED <= items.keys()
    assert items["KR-S02"][2] == "KRW"
    for k in KR_REQUIRED - {"KR-S02"}:
        assert isinstance(items[k][2], (int, float)), k
    for k in KR_DELIBERATE_GAPS:
        assert items[k][2] is None, f"{k} must stay missing (deliberate gap)"
    assert items["KR-C02"][3] == "mg/kg" and items["KR-C05"][3] == "years", "unit traps preserved"


def test_kr_subsequent_therapy_mix(kr):
    items = kr_items(kr)
    for arm_rows in (("KR-T04", "KR-T05", "KR-T06"), ("KR-T07", "KR-T08", "KR-T09")):
        shares = [items[k][2] for k in arm_rows]
        assert all(0 <= x <= 1 for x in shares) and sum(shares) <= 1


def test_kr_life_table_is_mx_with_open_last_band(kr):
    ws = kr["LifeTable_KR"]
    assert [ws.cell(row=4, column=c).value for c in (2, 3)] == ["KR-L01", "KR-L02"]
    assert [ws.cell(row=5, column=c).value for c in (2, 3)] == ["mx male", "mx female"]
    rows = list(ws.iter_rows(min_row=6, values_only=True))
    ages = [r[0] for r in rows]
    assert ages[:-1] == list(range(0, 100)) and ages[-1] == "100+"
    for col in (1, 2):
        mx = [r[col] for r in rows]
        assert all(isinstance(x, float) and x > 0 for x in mx)
        assert all(b >= a for a, b in zip(mx[1:], mx[2:])), "adult mx increases with age"


def test_docx_extract_tokens_equal_provenance_sequence():
    x = extract(FIXTURES / "global_report_UK.docx")
    assert [t["token"] for t in x["tokens"]] == [n["display"] for n in PROV["numbers"]]
    by_kind = {b["kind"] for b in x["blocks"]}
    assert {"heading", "paragraph", "table_cell", "caption", "title", "reference"} <= by_kind
    t = next(t for t in x["tokens"] if t["token"] == "£28,271")
    assert (t["value"], t["decimals"], t["kind"]) == (28271.0, 0, "currency") and t["section"] == "1. Executive summary"
