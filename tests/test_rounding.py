"""Rounding-interval verifier (tools/rounding.py)."""
import json
import random
from fractions import Fraction

import pytest
from docx import Document

from conftest import FIXTURES
from tools.rounding import check_derived, display_interval


def test_icer_example_from_gate0_passes_with_footnote():
    r = check_derived("ratio", [("24,622", 0), ("0.869", 3)], ("28,321", 0))
    assert r.status == "pass_with_footnote" and r.needs_footnote
    assert round(float(r.naive)) == 28334
    lo, hi = r.feasible
    assert lo < 28321 < hi


@pytest.mark.parametrize("shown", ["28,400", "28,300", "28,316", "28,352"])   # interval is [28,316.8, 28,350.6]
def test_icer_outside_interval_fails(shown):
    assert check_derived("ratio", [("24,622", 0), ("0.869", 3)], (shown, 0)).status == "fail"


def test_boundary_overlap_passes_with_footnote():
    assert check_derived("ratio", [("24,622", 0), ("0.869", 3)], ("28,351", 0)).status == "pass_with_footnote"


def test_exact_recomputation_passes_without_footnote():
    assert check_derived("ratio", [("24,622", 0), ("0.869", 3)], ("28,334", 0)).status == "pass"
    assert check_derived("difference", [("49,467", 0), ("24,845", 0)], ("24,622", 0)).status == "pass"


def test_difference_off_by_rounding_needs_footnote_and_off_by_two_fails():
    assert check_derived("difference", [("1.802", 3), ("0.794", 3)], ("1.007", 3)).status == "pass_with_footnote"
    assert check_derived("difference", [("1.802", 3), ("0.794", 3)], ("1.005", 3)).status == "fail"


def test_divisor_interval_containing_zero_is_indeterminate():
    assert check_derived("ratio", [("100", 0), ("0.0", 1)], ("5,000", 0)).status == "indeterminate"


def test_currency_symbols_and_exact_arithmetic():
    lo, hi = display_interval("£0.1", 1)
    assert (lo, hi) == (Fraction(1, 20), Fraction(3, 20))
    assert check_derived("sum", [("0.1", 1), ("0.2", 1)], ("0.3", 1)).status == "pass"   # no float artefact


def test_no_false_failures_on_correctly_rounded_values():
    """Property: values rounded correctly from the same unrounded numbers never fail."""
    rng = random.Random(20251027)
    for _ in range(2000):
        cost, qaly = rng.uniform(-50_000, 200_000), rng.uniform(0.01, 3.0)
        for op, a, b, da, db, dr in [("ratio", cost, qaly, 0, 3, 0), ("difference", cost, qaly * 1e4, 0, 0, 0)]:
            res = a / b if op == "ratio" else a - b
            r = check_derived(op, [(f"{a:.{da}f}", da), (f"{b:.{db}f}", db)], (f"{res:.{dr}f}", dr))
            assert r.ok, (op, a, b, r)


def test_report_icer_display_is_interval_consistent_and_footnoted():
    prov = json.loads((FIXTURES / "global_report_UK.provenance.json").read_text())
    base = {x["source"]["name"]: x["display"] for x in prov["numbers"] if x["source"]["scenario"] is None}
    r = check_derived("ratio", [(base["res_inc_total_cost"], 0), (base["res_inc_qaly_disc"], 3)], (base["res_icer"], 0))
    assert r.ok
    text = "\n".join(p.text for p in Document(FIXTURES / "global_report_UK.docx").paragraphs)
    footnoted = "calculated from unrounded results" in text
    assert footnoted == any(c["kind"] == "rounding_disclosure" for c in prov["claims"])
    if r.needs_footnote:
        assert footnoted, "ICER needs a rounding footnote but the report has none"
