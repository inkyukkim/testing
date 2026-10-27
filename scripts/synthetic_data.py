"""Synthetic demographic inputs shared by the fixture generators (not real data)."""
from __future__ import annotations

import math

LT_AGES = list(range(0, 111))


def gompertz_makeham_qx(a: float, b: float, c: float, ages=LT_AGES, infant: float = 0.004) -> list[float]:
    """Annual death probability qx = 1 - exp(-(a + b*exp(c*x))), rounded to 6 dp like published tables."""
    out = []
    for x in ages:
        h = a + b * math.exp(c * x)
        q = infant if x == 0 else 1.0 - math.exp(-h)
        out.append(round(min(q, 0.999), 6))
    return out


def gompertz_makeham_mx(a: float, b: float, c: float, ages) -> list[float]:
    """Central death rate mx (hazard at mid-year), rounded to 6 dp."""
    return [round(a + b * math.exp(c * (x + 0.5)), 6) for x in ages]


UK_QX_MALE = gompertz_makeham_qx(0.0005, 0.000030, 0.0950)
UK_QX_FEMALE = gompertz_makeham_qx(0.0003, 0.000016, 0.0985)

KR_LT_AGES = list(range(0, 101))          # published table ends at an open "100+" band
KR_MX_MALE = gompertz_makeham_mx(0.0004, 0.000020, 0.0985, KR_LT_AGES)
KR_MX_FEMALE = gompertz_makeham_mx(0.0002, 0.000008, 0.1040, KR_LT_AGES)
