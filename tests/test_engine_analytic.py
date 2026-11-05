"""Validate the independent Python engine against closed-form results (no LibreOffice).

Parity with the workbook only shows both implement the same conventions; these tests
anchor the engine itself to analytic results.
"""
import math

import pytest

from tools.partsa_engine import (expected_vials_lognormal, gpm_survival, run_arm, run_model,
                                 weibull_median)

H = 7 / 365.25
N60 = round(60 * 365.25 / 7)
BASE = dict(cycle_length_days=7, days_per_year=365.25, time_horizon_years=60, dr_costs=0.0,
            dr_outcomes=0.0, c_pf_week=0, c_pd_week=0, c_terminal=0, u_pf=1.0, u_pd=1.0,
            wtp_threshold=30000, baseline_age=40, prop_male=0.5, weight_mean_kg=70, weight_sd_kg=10,
            use_gpm_cap=0, use_age_util_adj=0, gpu_intercept=0.95, gpu_male=0.02, gpu_age=-0.0003,
            gpu_age2=-0.00003, st_cost_1=0, st_cost_2=0, st_cost_3=0,
            lt_age=list(range(0, 111)), lt_qx_male=[0.01] * 111, lt_qx_female=[0.01] * 111)


def arm(prefix, pfs=(1.0, 6.0), os_=(1.0, 12.0), tot=(1.0, 3.0), **kw):
    d = {"pfs_shape": pfs[0], "pfs_scale": pfs[1], "os_shape": os_[0], "os_scale": os_[1],
         "tot_shape": tot[0], "tot_scale": tot[1], "p_death_first_pfs": 0.0, "rdi": 1.0,
         "dose_weight_based": 0, "dose": 100, "vial_mg": 100, "vial_price": 0, "admin_cost_per_admin": 0,
         "admin_interval_weeks": 3, "max_doses": 0, "ae_cost": 0, "ae_qaly_loss": 0,
         "st_share_1": 0, "st_share_2": 0, "st_share_3": 0, **kw}
    return {f"{prefix}_{k}": v for k, v in d.items()}


@pytest.mark.parametrize("shape,scale", [(1.0, 12.0), (0.9, 20.0), (1.3, 15.0)])
def test_undiscounted_life_years_equal_weibull_mean(shape, scale):
    p = {**BASE, **arm("int", os_=(shape, scale))}
    assert run_arm(p, "int").ly_undisc == pytest.approx(scale * math.gamma(1 + 1 / shape) / 12, abs=1e-4)


def test_trapezoid_sum_exact_for_exponential():
    p = {**BASE, **arm("int", os_=(1.0, 12.0))}
    q = math.exp(-H)
    assert run_arm(p, "int").ly_undisc == pytest.approx(H * (1 + q) / 2 * (1 - q**N60) / (1 - q), rel=1e-12)


def test_mid_cycle_discounting_closed_form():
    r = 0.035
    p = {**BASE, **arm("int", os_=(1.0, 12.0)), "dr_outcomes": r}
    q, d = math.exp(-H), (1 + r) ** -H
    expected = H * (1 + q) / 2 * (1 + r) ** (-0.5 * H) * (1 - (q * d) ** N60) / (1 - q * d)
    assert run_arm(p, "int").ly_disc == pytest.approx(expected, rel=1e-12)


def test_annual_step_discounting_closed_form():
    """Fixture B convention: every cycle starting in model year k is discounted by (1+r)^-k."""
    r = 0.035
    p = {**BASE, **arm("int", os_=(1.0, 12.0)), "dr_outcomes": r}
    q = math.exp(-H)
    expected = sum(H * (q**i + q**(i + 1)) / 2 * (1 + r) ** -((i * 7) // 365.25) for i in range(N60))
    assert run_arm(p, "int", method="annual_step").ly_disc == pytest.approx(expected, rel=1e-12)


def test_model_year_exact_at_year_boundaries():
    """Cycle 1461 starts exactly at year 28; naive i*(7/365.25) gives 27.999... and floors to 27."""
    from tools.partsa_engine import model_year
    assert math.floor(1461 * (7 / 365.25)) == 27
    assert model_year(1461, 7.0, 365.25) == 28
    for k in range(1, 41):
        i = round(k * 365.25 / 7)
        assert model_year(i, 7.0, 365.25) == ((i * 7) // 365.25)


def test_gpm_survival_constant_qx():
    p = {**BASE, "lt_qx_male": [0.02] * 111, "lt_qx_female": [0.01] * 111, "prop_male": 0.3}
    s = gpm_survival(p, 520, H)
    t = 520 * H
    assert s[-1] == pytest.approx(0.3 * 0.98**t + 0.7 * 0.99**t, rel=1e-12)


def test_cap_binds_to_life_table_when_curve_is_flatter():
    """OS with near-zero hazard is replaced by general-population survival."""
    p = {**BASE, **arm("int", pfs=(1.0, 1e9), os_=(1.0, 1e9)), "use_gpm_cap": 1}
    a = run_arm(p, "int")
    assert a.trace["s_os"] == pytest.approx(a.trace["s_gpm"], rel=1e-12)
    assert a.trace["s_pfs"] == pytest.approx(a.trace["s_gpm"], rel=1e-12)


def test_doses_follow_tot_at_cycle_start_with_stopping_rule():
    p = {**BASE, **arm("int", tot=(1.0, 6.0), max_doses=4, vial_price=10, admin_cost_per_admin=1)}
    a = run_arm(p, "int")
    expected = sum(math.exp(-(3 * k * H * 12) / 6.0) for k in range(4))
    assert a.n_doses == pytest.approx(expected, rel=1e-12)
    assert a.costs["drug"] == pytest.approx(10 * expected, rel=1e-12)
    assert a.costs["admin"] == pytest.approx(expected, rel=1e-12)


def test_rdi_scales_drug_but_not_admin():
    p = {**BASE, **arm("int", max_doses=5, vial_price=10, admin_cost_per_admin=1, rdi=0.8)}
    full = {**p, "int_rdi": 1.0}
    a, b = run_arm(p, "int"), run_arm(full, "int")
    assert a.costs["drug"] == pytest.approx(0.8 * b.costs["drug"]) and a.costs["admin"] == b.costs["admin"]


def test_subsequent_therapy_on_progressions():
    """Exponential PFS with a flat OS: every PF exit is a progression (p_death_first = 0)."""
    p = {**BASE, **arm("int", pfs=(1.0, 6.0), os_=(1.0, 1e12), st_share_1=0.5, st_share_3=0.25),
         "st_cost_1": 1000, "st_cost_3": 4000}
    a = run_arm(p, "int")
    assert a.st_cost_per_progression == pytest.approx(1500)
    assert a.costs["st"] == pytest.approx(1500 * (1 - math.exp(-N60 * H * 12 / 6.0)), rel=1e-9)


def test_age_multiplier_is_ratio_of_population_norms():
    p = {**BASE, **arm("int"), "use_age_util_adj": 1}
    m = run_arm(p, "int").trace["util_mult"]
    g = lambda age: 0.95 + 0.02 * 0.5 - 0.0003 * age - 0.00003 * age**2
    assert m[100] == pytest.approx(g(40 + 100.5 * H) / g(40), rel=1e-12)


def test_expected_vials_degenerate_and_monotone():
    assert expected_vials_lognormal(1, 100, 50, 1e-6) == pytest.approx(1.0)        # 50 mg always 1 vial
    assert expected_vials_lognormal(1, 100, 150, 1e-6) == pytest.approx(2.0)       # 150 mg always 2 vials
    assert expected_vials_lognormal(2, 100, 76, 16) < expected_vials_lognormal(2, 100, 80, 16)


def test_weibull_median():
    assert weibull_median(1.0, 12.0) == pytest.approx(12 * math.log(2))


def test_icer_sign_and_nmb_identity():
    p = {**BASE, **arm("int", os_=(1.0, 24.0)), **arm("comp"), "int_ae_cost": 10000}
    r = run_model(p)
    assert r["inc_qaly"] > 0 and r["inc_cost"] == pytest.approx(10000)
    assert r["inc_nmb"] == pytest.approx(r["inc_qaly"] * 30000 - r["inc_cost"])
