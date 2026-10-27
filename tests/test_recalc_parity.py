"""Recalculate the workbook with LibreOffice headless and compare with the independent
Python engine. Tolerance 1e-6 (absolute AND relative) on the ICER and component results.
"""
import math

import openpyxl
import pytest

from conftest import MODEL
from tools.partsa_engine import REQUIRED_INPUTS, run_model
from tools.recalc import recalc
from tools.workbook_io import read_named, write_named

TOL = 1e-6
ERRORS = ("#NUM!", "#VALUE!", "#NAME?", "#REF!", "#DIV/0!", "#N/A", "#NULL!", "Err:")


def assert_close(name, sheet_value, engine_value):
    assert isinstance(sheet_value, (int, float)), f"{name}: no numeric cached value ({sheet_value!r})"
    diff = abs(sheet_value - engine_value)
    rel = diff / max(abs(engine_value), 1e-300)
    assert diff <= TOL or engine_value == 0, f"{name}: abs diff {diff:.3e} > {TOL}"
    assert rel <= TOL or engine_value == 0, f"{name}: rel diff {rel:.3e} > {TOL}"


def compare_all(values: dict):
    r = run_model({k: values[k] for k in REQUIRED_INPUTS})
    assert_close("res_icer", values["res_icer"], r["icer"])
    assert_close("res_icer_ly", values["res_icer_ly"], r["icer_ly"])
    assert_close("res_inc_nmb", values["res_inc_nmb"], r["inc_nmb"])
    assert_close("res_inc_total_cost", values["res_inc_total_cost"], r["inc_cost"])
    assert_close("res_inc_qaly_disc", values["res_inc_qaly_disc"], r["inc_qaly"])
    for arm in ("int", "comp"):
        a = r[arm]
        assert_close(f"res_{arm}_total_cost", values[f"res_{arm}_total_cost"], a.total_cost)
        for k, v in a.costs.items():
            assert_close(f"res_{arm}_cost_{k}", values[f"res_{arm}_cost_{k}"], v)
        for k in ("ly_undisc", "ly_disc", "qaly_undisc", "qaly_disc"):
            assert_close(f"res_{arm}_{k}", values[f"res_{arm}_{k}"], getattr(a, k))
    return r


def test_recalc_populates_values_without_errors(recalculated_model):
    wb = openpyxl.load_workbook(recalculated_model, data_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str):
                    assert not c.value.startswith(ERRORS), f"{ws.title}!{c.coordinate} = {c.value}"


def test_source_fixture_has_no_cached_values():
    """Guards against a stale cache masquerading as a recalculation."""
    v = read_named(MODEL, ["res_icer", "res_int_total_cost"])
    assert all(x is None for x in v.values())


def test_base_case_icer_parity(model_values):
    r = compare_all(model_values)
    print(f"\nICER workbook={model_values['res_icer']!r} engine={r['icer']!r} "
          f"abs diff={abs(model_values['res_icer'] - r['icer']):.3e}")


def test_trace_parity(recalculated_model, model_values):
    r = run_model({k: model_values[k] for k in REQUIRED_INPUTS})
    wb = openpyxl.load_workbook(recalculated_model, data_only=True, read_only=True)
    for sheet, arm in (("Trace_Int", "int"), ("Trace_Comp", "comp")):
        rows = list(wb[sheet].iter_rows(min_row=17, max_row=17 + len(r[arm].pf) - 1,
                                        min_col=6, max_col=7, values_only=True))
        for i, (pf, pd) in enumerate(rows):
            assert abs(pf - r[arm].pf[i]) < 1e-12 and abs(pd - r[arm].pd[i]) < 1e-12, f"{sheet} cycle {i}"


def test_model_checks_pass(model_values):
    assert model_values["check_trace_rows_ok"] == "OK"
    assert model_values["check_lifetime_ok"] == "OK"
    assert model_values["check_cross_int"] == 0 and model_values["check_cross_comp"] == 0


PERTURBED = {
    # KR-like setting plus survival changes: proves results are driven by the named inputs
    "dr_costs": 0.045, "dr_outcomes": 0.045, "time_horizon_years": 30, "u_pf": 0.80, "u_pd": 0.66,
    "c_pf_week": 138000, "c_pd_week": 241500, "c_terminal": 4000000, "int_drug_cost_per_admin": 2100000,
    "comp_drug_cost_per_admin": 420000, "int_admin_cost_per_admin": 95000, "comp_admin_cost_per_admin": 95000,
    "int_ae_cost": 1600000, "comp_ae_cost": 3100000, "int_os_scale": 28.0, "comp_pfs_shape": 0.8,
    "comp_pfs_scale": 40.0,  # forces S_PFS > S_OS for Drug B, exercising the MIN() cap
}


def test_perturbed_inputs_parity(tmp_path, model_values):
    src = write_named(MODEL, tmp_path / "perturbed.xlsx", PERTURBED)
    values = read_named(recalc(src, tmp_path / "rc"))
    assert values["res_icer"] != pytest.approx(model_values["res_icer"], rel=1e-3)
    assert values["check_cross_comp"] > 0
    compare_all(values)


def test_write_named_refuses_formula_cells(tmp_path):
    with pytest.raises(ValueError):
        write_named(MODEL, tmp_path / "x.xlsx", {"n_cycles": 10})
