"""Static checks on fixtures/global_model.xlsx (no recalculation needed)."""
import openpyxl
import pytest

from conftest import MODEL
from tools.partsa_engine import REQUIRED_INPUTS
from tools.workbook_io import list_names

INPUT_SHEETS = ("Inputs_Settings", "Inputs_Clinical", "Inputs_Costs", "Inputs_Utilities")
FIRST, LAST_INTERVAL, LAST_BOUNDARY = 17, 2104, 2105


@pytest.fixture(scope="module")
def wb():
    return openpyxl.load_workbook(MODEL)


@pytest.fixture(scope="module")
def names():
    return list_names(MODEL)


def test_required_inputs_are_named_numeric_constants(wb, names):
    for name in REQUIRED_INPUTS:
        assert name in names, f"missing named range {name}"
        sheet, cell = names[name]
        assert sheet in INPUT_SHEETS, f"{name} not on an input sheet"
        v = wb[sheet][cell].value
        assert isinstance(v, (int, float)) and not isinstance(v, bool), f"{name}={v!r} is not a numeric constant"


def is_formula(v):
    return isinstance(v, str) and v.startswith("=")


@pytest.mark.parametrize("sheet", ["Trace_Int", "Trace_Comp"])
def test_trace_sheets_are_formula_only(wb, sheet):
    ws = wb[sheet]
    for r in range(3, 13):
        assert is_formula(ws[f"C{r}"].value), f"{sheet}!C{r} must link to a named input"
    for row in ws.iter_rows(min_row=FIRST, max_row=LAST_BOUNDARY):
        for c in row:
            if c.value is not None:
                assert is_formula(c.value), f"hardcoded value at {sheet}!{c.coordinate}: {c.value!r}"


def test_arms_share_identical_formula_layout(wb):
    a, b = wb["Trace_Int"], wb["Trace_Comp"]
    for r in range(FIRST, LAST_BOUNDARY + 1):
        for col in "ABCDEFGHIJKLMNOPQRSTUVWXY":
            assert a[f"{col}{r}"].value == b[f"{col}{r}"].value, f"layout differs at {col}{r}"


def test_results_cells_are_formulas(wb, names):
    for name, (sheet, cell) in names.items():
        if name.startswith(("res_", "check_")):
            assert sheet == "Results"
            assert is_formula(wb[sheet][cell].value), f"{name} is not a formula"


def test_psa_placeholder_documents_macro_and_is_empty(wb):
    ws = wb["PSA_Placeholder"]
    assert "Not implemented" in ws["A2"].value
    assert ws["B17"].value is None, "PSA output table must be empty in Gate 0"


def test_workbook_contains_no_macros():
    import zipfile
    assert not any("vbaProject" in n for n in zipfile.ZipFile(MODEL).namelist())
