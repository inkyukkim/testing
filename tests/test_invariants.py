"""Invariants of the recalculated workbook trace (independent of the Python engine).

Each test states a property that must hold for any valid inputs; it runs on the base case
and on the perturbed case in which the mortality cap binds early and Drug B PFS crosses OS.
"""
import math

import numpy as np
import openpyxl
import pytest

from conftest import FIRST
from tools.partsa_engine import expected_vials_lognormal

COLS = {name: i for i, name in enumerate(
    "cycle t_years t_months age s_pfs_raw s_os_raw s_tot_raw gpm_m gpm_f gpm s_os s_pfs s_tot pf pd dead "
    "in_h pf_h pd_h alive_h deaths progs dose_due doses df_start df_c df_o age_mid util_mult "
    "c_drug c_admin c_pf c_pd c_term c_st c_total ly qaly cross bind".split())}
TOL = 1e-12


def load_trace(path, sheet, values):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    n = int(values["n_cycles"])
    rows = list(wb[sheet].iter_rows(min_row=FIRST, max_row=FIRST + n, max_col=40, values_only=True))
    arr = {k: np.array([r[i] if r[i] is not None else np.nan for r in rows], dtype=float) for k, i in COLS.items()}
    return arr, n


@pytest.fixture(params=["base", "perturbed"], scope="module")
def case(request, recalculated_model, model_values, perturbed_model, perturbed_values):
    return (recalculated_model, model_values) if request.param == "base" else (perturbed_model, perturbed_values)


@pytest.fixture(params=[("Trace_Int", "int"), ("Trace_Comp", "comp")], scope="module")
def trace(request, case):
    path, values = case
    tr, n = load_trace(path, request.param[0], values)
    return tr, n, values, request.param[1]


def test_states_partition_and_bounds(trace):
    tr, n, _, _ = trace
    total = tr["pf"] + tr["pd"] + tr["dead"]
    assert np.max(np.abs(total - 1)) < TOL
    for k in ("pf", "pd", "dead", "s_os", "s_pfs", "s_tot", "gpm"):
        assert np.all(tr[k] >= -TOL) and np.all(tr[k] <= 1 + TOL), k


def test_curves_non_increasing(trace):
    tr, *_ = trace
    for k in ("s_os", "s_pfs", "s_tot", "pf", "gpm"):
        assert np.all(np.diff(tr[k]) <= TOL), k


def test_cap_never_raises_survival(trace):
    tr, *_ = trace
    assert np.all(tr["s_os"] <= tr["s_os_raw"] + TOL)
    assert np.all(tr["s_pfs"] <= tr["s_pfs_raw"] + TOL)


def test_conditional_survival_not_above_general_population(trace):
    tr, _, values, _ = trace
    if values["use_gpm_cap"] != 1:
        pytest.skip("cap switched off")
    for k in ("s_os", "s_pfs"):
        s = tr[k]
        alive = s[:-1] > 1e-300
        assert np.all(s[1:][alive] / s[:-1][alive] <= tr["gpm"][1:][alive] / tr["gpm"][:-1][alive] + 1e-12), k


def test_tot_and_pf_bounded_by_os(trace):
    tr, *_ = trace
    assert np.all(tr["s_tot"] <= tr["s_os"] + TOL)
    assert np.all(tr["pf"] <= tr["s_os"] + TOL)


def test_dosing_schedule_and_stopping_rule(trace):
    tr, n, values, arm = trace
    interval = values[f"calc_{arm}_interval_cycles"]
    due = tr["dose_due"][:n]
    cycles = tr["cycle"][:n]
    assert np.all(due[np.mod(cycles, interval) != 0] == 0), "dose outside a dosing week"
    assert due.sum() == min(values[f"{arm}_max_doses"], math.ceil(n / interval)), "stopping rule"
    assert due[0] == 1 and tr["doses"][0] == pytest.approx(1.0), "everyone receives the first dose"
    off = due == 0
    assert np.all(tr["c_drug"][:n][off] == 0) and np.all(tr["c_admin"][:n][off] == 0)
    assert np.allclose(tr["doses"][:n][~off], tr["s_tot"][:n][~off], atol=TOL), "ToT at cycle start, no HCC"


def test_one_off_incidence_non_negative_and_bounded(trace):
    tr, n, values, arm = trace
    assert np.all(tr["deaths"][:n] >= -TOL) and np.all(tr["progs"][:n] >= -TOL)
    assert tr["deaths"][:n].sum() == pytest.approx(1 - tr["s_os"][n], abs=1e-10)
    assert tr["progs"][:n].sum() <= (1 - values[f"{arm}_p_death_first_pfs"]) + TOL


def test_utility_multiplier(trace):
    tr, n, values, _ = trace
    m = tr["util_mult"][:n]
    if values["use_age_util_adj"] != 1:
        assert np.all(m == 1)
        return
    assert np.all(np.diff(m) <= TOL) and np.all(m <= 1 + TOL) and np.all(m > 0)


def test_expected_vials_bounds(case):
    _, values = case
    for arm in ("int", "comp"):
        v = values[f"calc_{arm}_expected_vials"]
        if values[f"{arm}_dose_weight_based"] == 1:
            mean_vials = values[f"{arm}_dose"] * values["weight_mean_kg"] / values[f"{arm}_vial_mg"]
            assert mean_vials <= v <= mean_vials + 1, "E[ceil(X)] lies in [E[X], E[X]+1]"
        else:
            assert v == math.ceil(values[f"{arm}_dose"] / values[f"{arm}_vial_mg"])


def test_expected_vials_formula_against_monte_carlo():
    """The closed form used by engine and workbook, checked by simulation (independent method)."""
    rng = np.random.default_rng(20251027)
    for dose, vial, mean, sd in [(2, 100, 76, 16), (7.5, 100, 64.5, 11.8), (10, 50, 70, 20)]:
        s2 = math.log(1 + (sd / mean) ** 2)
        w = rng.lognormal(math.log(mean) - s2 / 2, math.sqrt(s2), 2_000_000)
        assert np.ceil(dose * w / vial).mean() == pytest.approx(expected_vials_lognormal(dose, vial, mean, sd), abs=3e-3)


def test_gpm_first_bind_consistent_with_trace(trace):
    tr, n, values, arm = trace
    bind = tr["bind"][:n]
    if bind.sum() == 0:
        assert values[f"res_{arm}_gpm_first_bind_age"] == "None"
        return
    i = int(np.argmax(bind))
    assert values[f"res_{arm}_gpm_first_bind_age"] == pytest.approx(values["baseline_age"] + tr["t_years"][i], abs=1e-12)
    assert values[f"res_{arm}_gpm_first_bind_alive"] == pytest.approx(tr["s_os"][i], abs=1e-15)
