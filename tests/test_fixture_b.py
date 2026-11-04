"""Fixture B: identical to Fixture A except annual-step discounting (declared and implemented)."""
import openpyxl
import pytest
import yaml

from conftest import FIXTURES, MODEL, engine_inputs
from test_recalc_parity import compare_all
from tools.partsa_engine import load_conventions
from tools.recalc import recalc
from tools.workbook_io import read_named

MODEL_B = FIXTURES / "global_model_B.xlsx"
CONV_B = FIXTURES / "global_model_B.conventions.yaml"
DF_COLS = {"Y", "Z", "AA"}


@pytest.fixture(scope="module")
def values_b(tmp_path_factory):
    return read_named(recalc(MODEL_B, tmp_path_factory.mktemp("rc_b")))


def test_fixture_b_parity(values_b):
    conv = load_conventions(CONV_B)
    assert conv["discounting"]["method"] == "annual_step"
    compare_all(values_b, conv)


def test_fixture_b_differs_from_a_only_in_discounting(values_b, model_values):
    a, b = openpyxl.load_workbook(MODEL), openpyxl.load_workbook(MODEL_B)
    assert a.sheetnames == b.sheetnames
    for ws in a.sheetnames:
        for row in a[ws].iter_rows():
            for c in row:
                other = b[ws][c.coordinate].value
                if c.value != other:
                    assert ws.startswith("Trace") and c.column_letter in DF_COLS or ws == "ReadMe", \
                        f"{ws}!{c.coordinate} differs outside discount columns"
    ca, cb = yaml.safe_load((FIXTURES / "global_model.conventions.yaml").read_text()), yaml.safe_load(CONV_B.read_text())
    diff = {k for k in ca if ca[k] != cb[k]}
    assert diff == {"model_id", "workbook", "discounting"}
    # Same undiscounted outcomes, different discounted ones
    assert values_b["res_int_ly_undisc"] == pytest.approx(model_values["res_int_ly_undisc"], rel=1e-12)
    assert values_b["res_icer"] != pytest.approx(model_values["res_icer"], rel=1e-6)


def test_fixture_b_formulas_match_declared_annual_step():
    t = openpyxl.load_workbook(MODEL_B)["Trace_Int"]
    for col, rate in (("Y", "dr_costs"), ("Z", "dr_costs"), ("AA", "dr_outcomes")):
        assert t[f"{col}21"].value == f"=1/(1+{rate})^INT(A21*cycle_length_days/days_per_year)"


def test_year_one_undiscounted_and_boundary_exact(values_b, tmp_path):
    wb = openpyxl.load_workbook(recalc(MODEL_B, tmp_path), data_only=True, read_only=True)
    rows = list(wb["Trace_Int"].iter_rows(min_row=20, max_row=20 + 1462, min_col=25, max_col=25, values_only=True))
    assert all(r[0] == 1 for r in rows[:52]), "first model year undiscounted"
    assert rows[1461][0] == pytest.approx(1.035 ** -28, rel=1e-12), "cycle 1461 starts exactly in year 28"
    assert rows[1460][0] == pytest.approx(1.035 ** -27, rel=1e-12)
