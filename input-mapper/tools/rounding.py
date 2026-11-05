"""Deterministic tool: is a displayed derived value consistent with its displayed operands?

A report shows rounded numbers. A reader recomputing ICER = cost / QALY from the displayed
operands can get a different figure (e.g. 24,622 / 0.869 = 28,334, displayed 28,321) even
though all three come from the same unrounded cells. This tool decides whether such a
discrepancy can be explained by rounding alone:

    check_derived(op, operands, result) -> RoundingCheck
        op        "ratio" | "difference" | "sum" | "product"
        operands  [(displayed_value, decimals), ...]   (two for ratio/difference)
        result    (displayed_value, decimals)

Each displayed value x with d decimals stands for the closed interval [x - h, x + h],
h = 0.5 * 10^-d. Interval arithmetic gives the feasible set of the derived value.
    pass                recomputing from the displayed operands reproduces the display
    pass_with_footnote  it does not, but the display lies within rounding error; the
                        report needs a "may not compute exactly due to rounding" footnote
    fail                no unrounded operands consistent with their displays can yield the
                        displayed result: a transcription or calculation error
    indeterminate       the interval is unbounded (divisor interval contains zero); human review
Exact rational arithmetic (fractions.Fraction) is used throughout; inputs may be numbers or
strings such as "24,622" or "£28,321".
Equivalent in R or VBA: the same four-corner interval arithmetic on Decimal/Currency types.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from itertools import product as _cartesian

OPS = {
    "ratio": lambda a, b: a / b,
    "difference": lambda a, b: a - b,
    "sum": lambda *xs: sum(xs, Fraction(0)),
    "product": lambda *xs: _prod(xs),
}


def _prod(xs):
    out = Fraction(1)
    for x in xs:
        out *= x
    return out


def to_fraction(x) -> Fraction:
    if isinstance(x, Fraction):
        return x
    if isinstance(x, str):
        x = x.replace(",", "").replace("£", "").replace("₩", "").strip()
    return Fraction(Decimal(str(x)))


def display_interval(value, decimals: int) -> tuple[Fraction, Fraction]:
    v = to_fraction(value)
    h = Fraction(1, 2 * 10 ** decimals) if decimals >= 0 else Fraction(10 ** -decimals, 2)
    return v - h, v + h


def round_half_up(x: Fraction, decimals: int) -> Fraction:
    d = Decimal(x.numerator) / Decimal(x.denominator)
    return Fraction(d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class RoundingCheck:
    status: str
    feasible: tuple[Fraction, Fraction] | None
    displayed: tuple[Fraction, Fraction]
    naive: Fraction | None

    @property
    def ok(self) -> bool:
        return self.status in ("pass", "pass_with_footnote")

    @property
    def needs_footnote(self) -> bool:
        return self.status == "pass_with_footnote"


def feasible_interval(op: str, intervals):
    if op not in OPS:
        raise ValueError(f"unknown op {op!r}")
    if op in ("ratio", "difference") and len(intervals) != 2:
        raise ValueError(f"{op} needs two operands")
    if op == "ratio" and intervals[1][0] <= 0 <= intervals[1][1]:
        return None
    corners = [OPS[op](*c) for c in _cartesian(*intervals)]
    return min(corners), max(corners)


def check_derived(op: str, operands, result) -> RoundingCheck:
    shown = [to_fraction(v) for v, _ in operands]
    intervals = [display_interval(v, d) for v, d in operands]
    res_value, res_dec = to_fraction(result[0]), result[1]
    displayed = display_interval(res_value, res_dec)
    feasible = feasible_interval(op, intervals)
    if feasible is None:
        return RoundingCheck("indeterminate", None, displayed, None)
    naive = OPS[op](*shown) if not (op == "ratio" and shown[1] == 0) else None
    if displayed[1] < feasible[0] or displayed[0] > feasible[1]:
        return RoundingCheck("fail", feasible, displayed, naive)
    if naive is not None and round_half_up(naive, res_dec) == res_value:
        return RoundingCheck("pass", feasible, displayed, naive)
    return RoundingCheck("pass_with_footnote", feasible, displayed, naive)
