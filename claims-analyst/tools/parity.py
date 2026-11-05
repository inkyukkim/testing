"""Deterministic tool: compare a recalculated workbook with the independent Python engine.

    parity(values, conventions, tol=1e-6) -> list of mismatch strings (empty = pass)
Both absolute and relative differences must be within tol for every compared result.
"""
from __future__ import annotations

from tools.partsa_engine import REQUIRED_INPUTS, run_model

ARM_FIELDS = ("ly_undisc", "ly_disc", "qaly_undisc", "qaly_disc", "n_doses", "expected_vials",
              "drug_cost_per_admin", "st_cost_per_progression", "s_os_horizon")


def parity(values: dict, conventions: dict | None, tol: float = 1e-6) -> list[str]:
    r = run_model({k: values[k] for k in REQUIRED_INPUTS}, conventions)
    pairs = [("res_icer", r["icer"]), ("res_icer_ly", r["icer_ly"]), ("res_inc_nmb", r["inc_nmb"]),
             ("res_inc_total_cost", r["inc_cost"]), ("res_inc_qaly_disc", r["inc_qaly"])]
    for arm in ("int", "comp"):
        a = r[arm]
        pairs.append((f"res_{arm}_total_cost", a.total_cost))
        pairs += [(f"res_{arm}_cost_{k}", v) for k, v in a.costs.items()]
        pairs += [(f"res_{arm}_{k}", getattr(a, k)) for k in ARM_FIELDS]
    out = []
    for name, eng in pairs:
        got = values.get(name)
        if not isinstance(got, (int, float)) or isinstance(got, bool):
            out.append(f"{name}: no numeric value in workbook ({got!r})")
            continue
        diff = abs(got - eng)
        if eng != 0 and (diff > tol or diff / abs(eng) > tol):
            out.append(f"{name}: workbook {got!r} vs engine {eng!r} (abs {diff:.3e})")
    return out
