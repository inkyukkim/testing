"""Deterministic tool: invariants of a recalculated PartSA trace (independent of the engine).

    check_invariants(recalculated_xlsx, values) -> list of failure strings (empty = pass)
Trace layout as in the global model generator (data from row 20, columns A..AN).
"""
from __future__ import annotations

import math

import numpy as np
import openpyxl

FIRST = 20
COLS = {name: i for i, name in enumerate(
    "cycle t_years t_months age s_pfs_raw s_os_raw s_tot_raw gpm_m gpm_f gpm s_os s_pfs s_tot pf pd dead "
    "in_h pf_h pd_h alive_h deaths progs dose_due doses df_start df_c df_o age_mid util_mult "
    "c_drug c_admin c_pf c_pd c_term c_st c_total ly qaly cross bind".split())}
TOL = 1e-12


def load_trace(path, sheet, n):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows = list(wb[sheet].iter_rows(min_row=FIRST, max_row=FIRST + n, max_col=40, values_only=True))
    return {k: np.array([r[i] if r[i] is not None else np.nan for r in rows], dtype=float) for k, i in COLS.items()}


def check_invariants(path, values) -> list[str]:
    n = int(values["n_cycles"])
    fails = []
    for sheet, arm in (("Trace_Int", "int"), ("Trace_Comp", "comp")):
        tr = load_trace(path, sheet, n)
        f = lambda msg: fails.append(f"{sheet}: {msg}")
        if np.max(np.abs(tr["pf"] + tr["pd"] + tr["dead"] - 1)) > TOL:
            f("states do not sum to one")
        for k in ("pf", "pd", "dead", "s_os", "s_pfs", "s_tot", "gpm"):
            if np.any(tr[k] < -TOL) or np.any(tr[k] > 1 + TOL):
                f(f"{k} outside [0, 1]")
        for k in ("s_os", "s_pfs", "s_tot", "pf", "gpm"):
            if np.any(np.diff(tr[k]) > TOL):
                f(f"{k} increases")
        if np.any(tr["s_os"] > tr["s_os_raw"] + TOL) or np.any(tr["s_pfs"] > tr["s_pfs_raw"] + TOL):
            f("mortality cap raises survival")
        if values["use_gpm_cap"] == 1:
            for k in ("s_os", "s_pfs"):
                s, g = tr[k], tr["gpm"]
                alive = s[:-1] > 1e-300
                if np.any(s[1:][alive] / s[:-1][alive] > g[1:][alive] / g[:-1][alive] + 1e-12):
                    f(f"{k} conditional survival above general population")
        if np.any(tr["s_tot"] > tr["s_os"] + TOL) or np.any(tr["pf"] > tr["s_os"] + TOL):
            f("ToT or PF above OS")
        interval = values[f"calc_{arm}_interval_cycles"]
        due, cyc = tr["dose_due"][:n], tr["cycle"][:n]
        if np.any(due[np.mod(cyc, interval) != 0] != 0):
            f("dose outside a dosing week")
        if due.sum() != min(values[f"{arm}_max_doses"], math.ceil(n / interval)):
            f("stopping rule not respected")
        off = due == 0
        if np.any(tr["c_drug"][:n][off] != 0) or np.any(tr["c_admin"][:n][off] != 0):
            f("dosing cost outside dosing weeks")
        if np.any(tr["deaths"][:n] < -TOL) or np.any(tr["progs"][:n] < -TOL):
            f("negative event incidence")
        m = tr["util_mult"][:n]
        if values["use_age_util_adj"] == 1 and (np.any(np.diff(m) > TOL) or np.any(m > 1 + TOL)):
            f("utility multiplier increases or exceeds one")
    return fails
