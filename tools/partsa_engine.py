"""Deterministic tool: independent Python implementation of the 3-state PartSA.

Used by the Model Verifier to check the spreadsheet. It reads only input VALUES (never
formulas) and re-derives every result, so a parity pass means the workbook's formulas
implement the declared conventions. It does not validate the conventions themselves.

Conventions are declared per model in <model>.conventions.yaml. `check_conventions`
refuses any declaration this engine does not implement; the only switchable convention
is `discounting.method` (mid_cycle_continuous | annual_step).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ARMS = ("int", "comp")
ST_CATEGORIES = (1, 2, 3)
ARM_PARAMS = (
    "pfs_shape", "pfs_scale", "os_shape", "os_scale", "tot_shape", "tot_scale",
    "p_death_first_pfs", "rdi", "dose_weight_based", "dose_mg", "vial_mg", "vial_price",
    "admin_cost_per_admin", "admin_interval_weeks", "max_doses", "ae_cost", "ae_qaly_loss",
) + tuple(f"st_share_{j}" for j in ST_CATEGORIES)
SHARED_PARAMS = (
    "cycle_length_days", "days_per_year", "time_horizon_years", "dr_costs", "dr_outcomes",
    "c_pf_week", "c_pd_week", "c_terminal", "u_pf", "u_pd", "wtp_threshold",
    "baseline_age", "prop_male", "weight_mean_kg", "weight_sd_kg", "use_gpm_cap",
    "use_age_util_adj", "gpu_intercept", "gpu_male", "gpu_age", "gpu_age2",
) + tuple(f"st_cost_{j}" for j in ST_CATEGORIES)
VECTOR_PARAMS = ("lt_age", "lt_qx_male", "lt_qx_female")
REQUIRED_INPUTS = SHARED_PARAMS + VECTOR_PARAMS + tuple(f"{a}_{p}" for a in ARMS for p in ARM_PARAMS)

# Every declared convention must equal one of these values (see CLAUDE.md).
SUPPORTED = {
    ("time", "cycle_length"): {"weekly"},
    ("time", "time_unit_survival"): {"months"},
    ("time", "horizon"): {"lifetime"},
    ("survival", "form"): {"weibull_aft"},
    ("survival", "endpoints"): {("pfs", "os", "tot")},
    ("survival", "pf_definition"): {"min_pfs_os"},
    ("survival", "tot_constraint"): {"capped_by_os"},
    ("general_population_mortality", "applied"): {True},
    ("general_population_mortality", "method"): {"per_cycle_hazard_max"},
    ("general_population_mortality", "applied_to"): {("pfs", "os")},
    ("general_population_mortality", "life_table_quantity"): {"qx"},
    ("general_population_mortality", "age_lookup"): {"int_age_at_cycle_start"},
    ("general_population_mortality", "sex_mixing"): {"weight_sex_specific_survival"},
    ("utilities", "age_adjustment"): {"multiplicative_general_population"},
    ("utilities", "age_adjustment_formula"): {"quadratic_age_sex"},
    ("utilities", "age_evaluated_at"): {"cycle_midpoint"},
    ("utilities", "reference_age"): {"baseline_age"},
    ("utilities", "ae_qaly_loss_age_adjusted"): {False},
    ("discounting", "method"): {"mid_cycle_continuous", "annual_step"},
    ("discounting", "rate_basis"): {"annual_effective"},
    ("half_cycle_correction", "method"): {"trapezoidal"},
    ("half_cycle_correction", "applied_to"): {("pf_state_cost", "pd_state_cost", "life_years", "qalys")},
    ("dosing", "cost_timing"): {"dosing_weeks_only"},
    ("dosing", "population_treated"): {"tot_at_cycle_start"},
    ("dosing", "schedule"): {"fixed_interval"},
    ("dosing", "stopping_rule"): {"max_doses"},
    ("dosing", "rdi_applied_to"): {("drug_cost",)},
    ("dosing", "rdi_basis"): {"cost_after_vial_rounding"},
    ("dosing", "weight_based_vials"): {"lognormal_moments_exact"},
    ("dosing", "flat_dose_vials"): {"roundup"},
    ("one_off_incidence", "death"): {"os_decrement"},
    ("one_off_incidence", "progression"): {"pf_decrement_times_one_minus_p_death_first"},
    ("one_off_incidence", "subsequent_therapy_trigger"): {"progression"},
    ("one_off_incidence", "subsequent_therapy_costing"): {"one_off_course_cost_by_share"},
    ("one_off_incidence", "terminal_care_trigger"): {"death"},
}
# Discount timing per stream for each supported method
TIMING = {
    "mid_cycle_continuous": {"state_costs": "cycle_midpoint", "one_off_event_costs": "cycle_midpoint",
                             "dosing_costs": "cycle_start", "outcomes": "cycle_midpoint",
                             "ae_at_baseline": "undiscounted"},
    "annual_step": {"state_costs": "model_year", "one_off_event_costs": "model_year",
                    "dosing_costs": "model_year", "outcomes": "model_year",
                    "ae_at_baseline": "undiscounted"},
}


class ConventionError(ValueError):
    pass


def load_conventions(path: str | Path) -> dict:
    import yaml
    conv = yaml.safe_load(Path(path).read_text())
    check_conventions(conv)
    return conv


def check_conventions(conv: dict) -> None:
    for (section, key), allowed in SUPPORTED.items():
        try:
            v = conv[section][key]
        except KeyError:
            raise ConventionError(f"missing convention {section}.{key}") from None
        if isinstance(v, list):
            v = tuple(v)
        if v not in allowed:
            raise ConventionError(f"{section}.{key}={v!r} not implemented (allowed: {sorted(map(str, allowed))})")
    method = conv["discounting"]["method"]
    if conv["discounting"].get("timing") != TIMING[method]:
        raise ConventionError(f"discounting.timing does not match the implementation of {method}")


@dataclass
class ArmResult:
    costs: dict[str, float]
    total_cost: float
    ly_undisc: float
    ly_disc: float
    qaly_undisc: float
    qaly_disc: float
    n_doses: float
    expected_vials: float
    drug_cost_per_admin: float
    st_cost_per_progression: float
    trace: dict[str, np.ndarray]
    s_os_horizon: float


def weibull_s(t_months, shape, scale):
    return np.exp(-((np.asarray(t_months, dtype=float) / scale) ** shape))


def weibull_median(shape, scale):
    return scale * math.log(2.0) ** (1.0 / shape)


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def expected_vials_lognormal(dose_mg_per_kg, vial_mg, mean_kg, sd_kg, k_max=1000):
    """E[ceil(dose*W/vial)] for W lognormal with the given mean and SD (method of moments)."""
    s2 = math.log(1.0 + (sd_kg / mean_kg) ** 2)   # same arithmetic as the workbook (no log1p)
    if s2 == 0.0:
        return float(math.ceil(dose_mg_per_kg * mean_kg / vial_mg))
    mu, s = math.log(mean_kg) - s2 / 2.0, math.sqrt(s2)
    w_per_vial = vial_mg / dose_mg_per_kg
    cdf = [0.0] + [_phi((math.log(k * w_per_vial) - mu) / s) for k in range(1, k_max + 1)]
    probs = [cdf[k] - cdf[k - 1] for k in range(1, k_max + 1)]
    return sum(k * p for k, p in zip(range(1, k_max + 1), probs)) / sum(probs)


def vials_per_admin(p: dict, arm: str) -> float:
    g = lambda k: float(p[f"{arm}_{k}"])
    if int(g("dose_weight_based")) == 1:
        return expected_vials_lognormal(g("dose_mg"), g("vial_mg"), float(p["weight_mean_kg"]), float(p["weight_sd_kg"]))
    return float(math.ceil(g("dose_mg") / g("vial_mg")))


def gpm_survival(p: dict, n: int, cyc_years: float) -> np.ndarray:
    ages = list(p["lt_age"])
    qm, qf = np.asarray(p["lt_qx_male"], float), np.asarray(p["lt_qx_female"], float)
    pm = float(p["prop_male"])
    sm, sf = np.ones(n + 1), np.ones(n + 1)
    for i in range(1, n + 1):
        idx = ages.index(int(math.floor(float(p["baseline_age"]) + (i - 1) * cyc_years)))
        sm[i] = sm[i - 1] * (1.0 - qm[idx]) ** cyc_years
        sf[i] = sf[i - 1] * (1.0 - qf[idx]) ** cyc_years
    return pm * sm + (1.0 - pm) * sf


def _ratios(s: np.ndarray) -> np.ndarray:
    prev = s[:-1]
    return np.divide(s[1:], prev, out=np.zeros_like(prev), where=prev > 0)


def _capped(s_raw, s_gpm, cap_on):
    r = _ratios(s_raw)
    if cap_on:
        r = np.minimum(r, _ratios(s_gpm))
    return np.concatenate(([s_raw[0]], s_raw[0] * np.cumprod(r)))


def discount_factors(rate, c, cyc_years, method):
    if method == "mid_cycle_continuous":
        return (1.0 + rate) ** -((c + 0.5) * cyc_years), (1.0 + rate) ** -(c * cyc_years)
    if method == "annual_step":
        year = np.floor(c * cyc_years)
        return (1.0 + rate) ** -year, (1.0 + rate) ** -year
    raise ConventionError(method)


def gpu(p, age):
    return (float(p["gpu_intercept"]) + float(p["gpu_male"]) * float(p["prop_male"])
            + float(p["gpu_age"]) * age + float(p["gpu_age2"]) * age ** 2)


def run_arm(p: dict, arm: str, method: str = "mid_cycle_continuous") -> ArmResult:
    g = lambda k: float(p[f"{arm}_{k}"])
    cyc_days = float(p["cycle_length_days"])
    cy = cyc_days / float(p["days_per_year"])
    n = int(round(float(p["time_horizon_years"]) * float(p["days_per_year"]) / cyc_days))
    i = np.arange(n + 1)
    t_m = i * cy * 12.0
    cap_on = int(p["use_gpm_cap"]) == 1
    s_gpm = gpm_survival(p, n, cy)
    s_os = _capped(weibull_s(t_m, g("os_shape"), g("os_scale")), s_gpm, cap_on)
    s_pfs = _capped(weibull_s(t_m, g("pfs_shape"), g("pfs_scale")), s_gpm, cap_on)
    s_tot = np.minimum(weibull_s(t_m, g("tot_shape"), g("tot_scale")), s_os)
    pf = np.minimum(s_pfs, s_os)
    pd = s_os - pf
    pf_h, pd_h = (pf[:-1] + pf[1:]) / 2.0, (pd[:-1] + pd[1:]) / 2.0
    deaths = s_os[:-1] - s_os[1:]
    progressions = np.maximum(0.0, pf[:-1] - pf[1:]) * (1.0 - g("p_death_first_pfs"))
    c = i[:-1]
    df_c_mid, df_c_start = discount_factors(float(p["dr_costs"]), c, cy, method)
    df_o_mid, _ = discount_factors(float(p["dr_outcomes"]), c, cy, method)
    ic = g("admin_interval_weeks") * 7.0 / cyc_days
    dose_due = (np.mod(c, ic) == 0) & (c / ic < g("max_doses"))
    doses = np.where(dose_due, s_tot[:-1], 0.0)
    vials = vials_per_admin(p, arm)
    cost_admin = vials * g("vial_price")
    st_cost = sum(g(f"st_share_{j}") * float(p[f"st_cost_{j}"]) for j in ST_CATEGORIES)
    streams = {
        "drug": (doses * cost_admin * g("rdi"), df_c_start),
        "admin": (doses * g("admin_cost_per_admin"), df_c_start),
        "pf_state": (pf_h * float(p["c_pf_week"]) * cyc_days / 7.0, df_c_mid),
        "pd_state": (pd_h * float(p["c_pd_week"]) * cyc_days / 7.0, df_c_mid),
        "terminal": (deaths * float(p["c_terminal"]), df_c_mid),
        "st": (progressions * st_cost, df_c_mid),
    }
    costs = {k: float(np.sum(v * df)) for k, (v, df) in streams.items()}
    costs["ae"] = g("ae_cost")
    if int(p["use_age_util_adj"]) == 1:
        mult = gpu(p, float(p["baseline_age"]) + (c + 0.5) * cy) / gpu(p, float(p["baseline_age"]))
    else:
        mult = np.ones(n)
    ly = (pf_h + pd_h) * cy
    qaly = (pf_h * float(p["u_pf"]) + pd_h * float(p["u_pd"])) * mult * cy
    return ArmResult(
        costs=costs, total_cost=sum(costs.values()),
        ly_undisc=float(ly.sum()), ly_disc=float((ly * df_o_mid).sum()),
        qaly_undisc=float(qaly.sum()) - g("ae_qaly_loss"),
        qaly_disc=float((qaly * df_o_mid).sum()) - g("ae_qaly_loss"),
        n_doses=float(doses.sum()), expected_vials=vials, drug_cost_per_admin=cost_admin,
        st_cost_per_progression=st_cost,
        trace={"s_gpm": s_gpm, "s_os": s_os, "s_pfs": s_pfs, "s_tot": s_tot, "pf": pf, "pd": pd,
               "deaths": deaths, "progressions": progressions, "doses": doses, "util_mult": mult},
        s_os_horizon=float(s_os[-1]),
    )


def run_model(p: dict, conventions: dict | None = None) -> dict:
    missing = [k for k in REQUIRED_INPUTS if k not in p or p[k] is None]
    if missing:
        raise KeyError(f"Missing inputs: {missing}")
    method = "mid_cycle_continuous"
    if conventions is not None:
        check_conventions(conventions)
        method = conventions["discounting"]["method"]
    a, b = run_arm(p, "int", method), run_arm(p, "comp", method)
    d_c = a.total_cost - b.total_cost
    d_q = a.qaly_disc - b.qaly_disc
    d_l = a.ly_disc - b.ly_disc
    wtp = float(p["wtp_threshold"])
    return {
        "int": a, "comp": b,
        "inc_cost": d_c, "inc_qaly": d_q, "inc_ly": d_l,
        "icer": d_c / d_q if d_q != 0 else float("nan"),
        "icer_ly": d_c / d_l if d_l != 0 else float("nan"),
        "inc_nmb": d_q * wtp - d_c,
    }
