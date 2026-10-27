"""Validate the independent Python engine against closed-form results (no LibreOffice).

Parity with the workbook only shows both implement the same conventions; these tests
anchor the engine itself to analytic survival results.
"""
import math

import pytest

from tools.partsa_engine import run_arm, run_model, weibull_median

BASE = dict(cycle_length_days=7, days_per_year=365.25, time_horizon_years=60, dr_costs=0.0,
            dr_outcomes=0.0, c_pf_week=0, c_pd_week=0, c_terminal=0, u_pf=1.0, u_pd=1.0,
            wtp_threshold=30000)


def arm(prefix, pfs=(1.0, 6.0), os_=(1.0, 12.0)):
    return {f"{prefix}_pfs_shape": pfs[0], f"{prefix}_pfs_scale": pfs[1],
            f"{prefix}_os_shape": os_[0], f"{prefix}_os_scale": os_[1],
            f"{prefix}_drug_cost_per_admin": 0, f"{prefix}_admin_cost_per_admin": 0,
            f"{prefix}_admin_interval_weeks": 3, f"{prefix}_max_tx_weeks": 0,
            f"{prefix}_ae_cost": 0, f"{prefix}_ae_qaly_loss": 0}


@pytest.mark.parametrize("shape,scale", [(1.0, 12.0), (0.9, 20.0), (1.3, 15.0)])
def test_undiscounted_life_years_equal_weibull_mean(shape, scale):
    p = {**BASE, **arm("int", os_=(shape, scale))}
    expected_years = scale * math.gamma(1 + 1 / shape) / 12
    assert run_arm(p, "int").ly_undisc == pytest.approx(expected_years, abs=1e-4)


def test_trapezoid_error_is_second_order():
    """Exponential S(t)=exp(-kt): trapezoid sum has closed form; check exact agreement."""
    p = {**BASE, **arm("int", os_=(1.0, 12.0))}
    h = 7 / 365.25
    k = 1.0  # per year: scale 12 months
    n = round(60 * 365.25 / 7)
    q = math.exp(-k * h)
    exact_trapezoid = h * (1 + q) / 2 * (1 - q**n) / (1 - q)
    assert run_arm(p, "int").ly_undisc == pytest.approx(exact_trapezoid, rel=1e-12)


def test_discounting_matches_closed_form_for_exponential():
    r = 0.035
    p = {**BASE, **arm("int", os_=(1.0, 12.0)), "dr_outcomes": r}
    h, k = 7 / 365.25, 1.0
    n = round(60 * 365.25 / 7)
    q, d = math.exp(-k * h), (1 + r) ** -h
    expected = h * (1 + q) / 2 * (1 + r) ** (-0.5 * h) * (1 - (q * d) ** n) / (1 - q * d)
    assert run_arm(p, "int").ly_disc == pytest.approx(expected, rel=1e-12)


def test_states_partition_and_pf_capped_by_os():
    p = {**BASE, **arm("int", pfs=(0.7, 30.0), os_=(1.4, 10.0))}  # PFS crosses above OS
    a = run_arm(p, "int")
    assert (a.pf >= 0).all() and (a.pd >= -1e-15).all()
    assert (a.pf + a.pd <= 1 + 1e-15).all()


def test_weibull_median():
    assert weibull_median(1.0, 12.0) == pytest.approx(12 * math.log(2))


def test_icer_sign_and_nmb_identity():
    p = {**BASE, **arm("int", os_=(1.0, 24.0)), **arm("comp"), "int_ae_cost": 10000}
    r = run_model(p)
    assert r["inc_qaly"] > 0 and r["inc_cost"] == pytest.approx(10000)
    assert r["inc_nmb"] == pytest.approx(r["inc_qaly"] * 30000 - r["inc_cost"])
