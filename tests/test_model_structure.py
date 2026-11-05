"""Static checks on fixtures/global_model.xlsx (no recalculation needed)."""
import zipfile

import openpyxl
import pytest

from conftest import MODEL
from tools.partsa_engine import REQUIRED_INPUTS, VECTOR_PARAMS
from tools.workbook_io import list_names

INPUT_SHEETS = ("Inputs_Settings", "Inputs_Population", "Inputs_Clinical", "Inputs_Costs",
                "Inputs_Utilities", "Inputs_LifeTable")
FIRST, LAST_INTERVAL, LAST_BOUNDARY = 20, 2107, 2108
ARM_BLOCK_ROWS = range(3, 18)
TRACE_COLS = [openpyxl.utils.get_column_letter(i) for i in range(1, 41)]   # A..AN
STRUCTURAL_FIRST_ROW = {"H": "=1", "I": "=1"}   # GPM survival is 1 at t = 0 by definition


@pytest.fixture(scope="module")
def wb():
    return openpyxl.load_workbook(MODEL)


@pytest.fixture(scope="module")
def names():
    return list_names(MODEL)


def is_formula(v):
    return isinstance(v, str) and v.startswith("=")


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def test_required_inputs_are_named_numeric_constants(wb, names):
    for name in REQUIRED_INPUTS:
        assert name in names, f"missing named range {name}"
        sheet, ref = names[name]
        assert sheet in INPUT_SHEETS, f"{name} not on an input sheet"
        cells = [c for row in wb[sheet][ref] for c in row] if ":" in ref else [wb[sheet][ref]]
        assert (len(cells) > 1) == (name in VECTOR_PARAMS), f"{name}: vector/scalar mismatch"
        for c in cells:
            assert is_number(c.value), f"{name} {c.coordinate}={c.value!r} is not a numeric constant"


def test_life_table_vectors_align(wb, names):
    lengths = {n: len(wb[names[n][0]][names[n][1]]) for n in VECTOR_PARAMS}
    assert len(set(lengths.values())) == 1, lengths
    ages = [r[0].value for r in wb[names["lt_age"][0]][names["lt_age"][1]]]
    assert ages == list(range(ages[0], ages[0] + len(ages))), "life table ages must be contiguous single years"


@pytest.mark.parametrize("sheet", ["Trace_Int", "Trace_Comp", "Calc_Dosing"])
def test_calculation_sheets_are_formula_only(wb, sheet):
    ws = wb[sheet]
    if sheet.startswith("Trace"):
        for r in ARM_BLOCK_ROWS:
            assert is_formula(ws[f"C{r}"].value), f"{sheet}!C{r} must link to a named input"
        rows = ws.iter_rows(min_row=FIRST, max_row=LAST_BOUNDARY)
    else:
        rows = ws.iter_rows(min_row=3, max_row=ws.max_row, min_col=2)
    for row in rows:
        for c in row:
            if c.value is None or (sheet == "Calc_Dosing" and isinstance(c.value, str) and not c.value[0] == "="
                                   and not c.value[:1].isdigit()):
                continue   # labels on Calc_Dosing
            assert is_formula(c.value), f"hardcoded value at {sheet}!{c.coordinate}: {c.value!r}"
            if sheet.startswith("Trace") and c.row == FIRST and c.column_letter in STRUCTURAL_FIRST_ROW:
                assert c.value == STRUCTURAL_FIRST_ROW[c.column_letter]


def test_no_numeric_literals_in_trace_formulas_beyond_structural(wb):
    """Formulas may contain only structural constants (0, 0.5, 1, 2, 7, 12); inputs come from names."""
    import re
    allowed = {"0", "0.5", "1", "2", "7", "12"}   # 2: trapezoid; 7: days per week; 12: months per year
    ws = wb["Trace_Int"]
    for col in TRACE_COLS:
        f = ws[f"{col}{FIRST + 1}"].value
        literals = set(re.findall(r"(?<![A-Za-z_$\d.])(\d+(?:\.\d+)?)(?![\d.]*[A-Za-z_(])", f.replace("$", "")))
        assert literals <= allowed, f"{col}: {literals - allowed}"


def test_arms_share_identical_formula_layout(wb):
    a, b = wb["Trace_Int"], wb["Trace_Comp"]
    for r in range(FIRST, LAST_BOUNDARY + 1):
        for col in TRACE_COLS:
            assert a[f"{col}{r}"].value == b[f"{col}{r}"].value, f"layout differs at {col}{r}"
    for r in ARM_BLOCK_ROWS:
        assert a[f"C{r}"].value.replace("int_", "ARM_") == b[f"C{r}"].value.replace("comp_", "ARM_")


def test_results_cells_are_formulas(wb, names):
    for name, (sheet, cell) in names.items():
        if name.startswith(("res_", "check_", "calc_")):
            assert sheet in ("Results", "Calc_Dosing")
            assert is_formula(wb[sheet][cell].value), f"{name} is not a formula"


def test_psa_placeholder_documents_macro_and_is_empty(wb):
    ws = wb["PSA_Placeholder"]
    assert "Not implemented" in ws["A2"].value
    assert ws["B17"].value is None, "PSA output table must be empty"


def test_workbook_contains_no_macros():
    assert not any("vbaProject" in n for n in zipfile.ZipFile(MODEL).namelist())
