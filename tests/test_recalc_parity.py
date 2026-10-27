"""Recalculate the workbook with LibreOffice headless and compare with the independent
Python engine. Tolerance 1e-6 (absolute AND relative) on the ICER and component results.
"""
import openpyxl
import pytest

from conftest import MODEL, PERTURBED, engine_inputs
from tools.partsa_engine import run_model
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


def compare_all(values: dict, conventions: dict) -> dict:
    r = run_model(engine_inputs(values), conventions)
    for key, eng in (("res_icer", r["icer"]), ("res_icer_ly", r["icer_ly"]), ("res_inc_nmb", r["inc_nmb"]),
                     ("res_inc_total_cost", r["inc_cost"]), ("res_inc_qaly_disc", r["inc_qaly"])):
        assert_close(key, values[key], eng)
    for arm in ("int", "comp"):
        a = r[arm]
        assert_close(f"res_{arm}_total_cost", values[f"res_{arm}_total_cost"], a.total_cost)
        assert set(a.costs) == {"drug", "admin", "pf_state", "pd_state", "terminal", "st", "ae"}
        for k, v in a.costs.items():
            assert_close(f"res_{arm}_cost_{k}", values[f"res_{arm}_cost_{k}"], v)
        for k in ("ly_undisc", "ly_disc", "qaly_undisc", "qaly_disc", "n_doses", "expected_vials",
                  "drug_cost_per_admin", "st_cost_per_progression"):
            assert_close(f"res_{arm}_{k}", values[f"res_{arm}_{k}"], getattr(a, k))
        assert_close(f"res_{arm}_s_os_horizon", values[f"res_{arm}_s_os_horizon"], a.s_os_horizon)
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


def test_base_case_icer_parity(model_values, conventions):
    r = compare_all(model_values, conventions)
    print(f"\nICER workbook={model_values['res_icer']!r} engine={r['icer']!r} "
          f"abs diff={abs(model_values['res_icer'] - r['icer']):.3e}")


@pytest.mark.parametrize("which", ["base", "perturbed"])
def test_trace_parity(which, recalculated_model, model_values, perturbed_model, perturbed_values, conventions):
    path, values = (recalculated_model, model_values) if which == "base" else (perturbed_model, perturbed_values)
    r = run_model(engine_inputs(values), conventions)
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    cols = {"s_gpm": 9, "s_os": 10, "s_pfs": 11, "s_tot": 12, "pf": 13, "pd": 14}   # J..O (0-based)
    for sheet, arm in (("Trace_Int", "int"), ("Trace_Comp", "comp")):
        tr = r[arm].trace
        n = len(tr["s_os"])
        rows = list(wb[sheet].iter_rows(min_row=20, max_row=20 + n - 1, max_col=40, values_only=True))
        for i, row in enumerate(rows):
            for key, j in cols.items():
                assert abs(row[j] - tr[key][i]) < 1e-12, f"{sheet} cycle {i} {key}"
            if i < n - 1:
                assert abs(row[23] - tr["doses"][i]) < 1e-12, f"{sheet} cycle {i} doses"
                assert abs(row[21] - tr["progressions"][i]) < 1e-12, f"{sheet} cycle {i} progressions"
                assert abs(row[28] - tr["util_mult"][i]) < 1e-12, f"{sheet} cycle {i} utility multiplier"


def test_model_checks_pass(model_values):
    for k, v in model_values.items():
        if k.startswith("check_") and isinstance(v, str):
            assert v == "OK", k
    assert model_values["check_cross_int"] == 0 and model_values["check_cross_comp"] == 0


def test_perturbed_inputs_parity(model_values, perturbed_values, conventions):
    assert perturbed_values["res_icer"] != pytest.approx(model_values["res_icer"], rel=1e-3)
    assert perturbed_values["check_cross_comp"] > 0, "perturbation should exercise the PFS <= OS cap"
    compare_all(perturbed_values, conventions)


def test_switches_off_parity_and_cap_materiality(tmp_path, perturbed_values, conventions):
    """With the cap and age adjustment switched off the workbook still matches the engine, and in the
    perturbed (older, long-tail) case the cap changes the result materially."""
    src = write_named(MODEL, tmp_path / "off.xlsx", {**PERTURBED, "use_gpm_cap": 0, "use_age_util_adj": 0})
    off = read_named(recalc(src, tmp_path / "rc"))
    compare_all(off, conventions)
    assert off["res_int_gpm_bind_cycles"] == 0
    assert perturbed_values["res_int_gpm_bind_cycles"] > 0
    assert off["res_int_ly_undisc"] > perturbed_values["res_int_ly_undisc"] * 1.01, "cap should matter here"


def test_write_named_refuses_formula_cells(tmp_path):
    with pytest.raises(ValueError):
        write_named(MODEL, tmp_path / "x.xlsx", {"n_cycles": 10})


def test_write_named_vector_length_checked(tmp_path):
    with pytest.raises(ValueError):
        write_named(MODEL, tmp_path / "x.xlsx", {"lt_qx_male": [0.01] * 3})


def test_zero_weight_variance_edge_case(tmp_path, conventions):
    """SD = 0 makes the lognormal degenerate; both sides fall back to vials at the mean weight."""
    v = read_named(recalc(write_named(MODEL, tmp_path / "sd0.xlsx", {"weight_sd_kg": 0}), tmp_path / "rc"))
    assert v["check_vial_bands_ok"] == "OK"
    compare_all(v, conventions)
