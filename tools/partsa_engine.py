"""Deterministic tool: independent Python implementation of the 3-state PartSA.

Used by the Model Verifier to check the spreadsheet. It reads only input VALUES (never
formulas) and re-derives every result, so a parity pass means the workbook's formulas
implement the conventions below. It does not validate the conventions themselves.

Conventions (must match CLAUDE.md "Model conventions"):
- Weibull (AFT, time in months): S(t) = exp(-(t/scale)^shape)
- PF = min(S_PFS, S_OS); PD = S_OS - PF; Dead = 1 - S_OS
- Half-cycle correction: trapezoid on state membership at cycle boundaries
- Discount factor per cycle evaluated at cycle mid-point: (1+r)^-((i+0.5)*cycle_years)
- Treatment while in PF and cycle start < max treatment duration
- Per-administration costs spread evenly: cost/admin x cycle_days / (7 x interval_weeks)
- Terminal care cost applied to deaths occurring in the cycle (S_OS drop)
- AE cost and QALY loss: one-off at t=0, undiscounted
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

ARMS = ("int", "comp")
ARM_PARAMS = ("pfs_shape", "pfs_scale", "os_shape", "os_scale", "drug_cost_per_admin",
              "admin_cost_per_admin", "admin_interval_weeks", "max_tx_weeks",
              "ae_cost", "ae_qaly_loss")
SHARED_PARAMS = ("cycle_length_days", "days_per_year", "time_horizon_years", "dr_costs",
                 "dr_outcomes", "c_pf_week", "c_pd_week", "c_terminal", "u_pf", "u_pd",
                 "wtp_threshold")
REQUIRED_INPUTS = SHARED_PARAMS + tuple(f"{a}_{p}" for a in ARMS for p in ARM_PARAMS)


@dataclass
class ArmResult:
    costs: dict[str, float]
    total_cost: float
    ly_undisc: float
    ly_disc: float
    qaly_undisc: float
    qaly_disc: float
    pf: np.ndarray
    pd: np.ndarray
    s_os_horizon: float


def weibull_s(t_months, shape, scale):
    return np.exp(-((np.asarray(t_months, dtype=float) / scale) ** shape))


def weibull_median(shape, scale):
    return scale * math.log(2.0) ** (1.0 / shape)


def run_arm(p: dict, arm: str) -> ArmResult:
    g = lambda k: float(p[f"{arm}_{k}"])
    cyc_days = float(p["cycle_length_days"])
    cyc_years = cyc_days / float(p["days_per_year"])
    n = int(round(float(p["time_horizon_years"]) * float(p["days_per_year"]) / cyc_days))
    i = np.arange(n + 1)
    t_m = i * cyc_years * 12.0
    s_pfs = weibull_s(t_m, g("pfs_shape"), g("pfs_scale"))
    s_os = weibull_s(t_m, g("os_shape"), g("os_scale"))
    pf = np.minimum(s_pfs, s_os)
    pd = s_os - pf
    pf_h = (pf[:-1] + pf[1:]) / 2.0
    pd_h = (pd[:-1] + pd[1:]) / 2.0
    deaths = s_os[:-1] - s_os[1:]
    c = i[:-1]
    df_c = (1.0 + float(p["dr_costs"])) ** -((c + 0.5) * cyc_years)
    df_o = (1.0 + float(p["dr_outcomes"])) ** -((c + 0.5) * cyc_years)
    on_tx = np.where(c * cyc_days < g("max_tx_weeks") * 7.0, pf_h, 0.0)
    admins = cyc_days / (7.0 * g("admin_interval_weeks"))
    streams = {
        "drug": on_tx * g("drug_cost_per_admin") * admins,
        "admin": on_tx * g("admin_cost_per_admin") * admins,
        "pf_state": pf_h * float(p["c_pf_week"]) * cyc_days / 7.0,
        "pd_state": pd_h * float(p["c_pd_week"]) * cyc_days / 7.0,
        "terminal": deaths * float(p["c_terminal"]),
    }
    costs = {k: float(np.sum(v * df_c)) for k, v in streams.items()}
    costs["ae"] = g("ae_cost")
    ly = (pf_h + pd_h) * cyc_years
    qaly = (pf_h * float(p["u_pf"]) + pd_h * float(p["u_pd"])) * cyc_years
    return ArmResult(
        costs=costs,
        total_cost=sum(costs.values()),
        ly_undisc=float(ly.sum()),
        ly_disc=float((ly * df_o).sum()),
        qaly_undisc=float(qaly.sum()) - g("ae_qaly_loss"),
        qaly_disc=float((qaly * df_o).sum()) - g("ae_qaly_loss"),
        pf=pf, pd=pd, s_os_horizon=float(s_os[-1]),
    )


def run_model(p: dict) -> dict:
    missing = [k for k in REQUIRED_INPUTS if k not in p or p[k] is None]
    if missing:
        raise KeyError(f"Missing inputs: {missing}")
    a, b = run_arm(p, "int"), run_arm(p, "comp")
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
