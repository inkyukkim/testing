"""Regression baseline: catches changes that move the workbook and the engine together.

Parity tests cannot see a change applied identically to both implementations; this test
pins the recalculated base case. Re-baseline deliberately with scripts/rebaseline.py.
"""
import json

from conftest import FIXTURES

BASELINE = json.loads((FIXTURES / "baseline.json").read_text())
TOL = 1e-6


def test_base_case_matches_recorded_baseline(model_values):
    for key, expected in BASELINE["values"].items():
        got = model_values[key]
        assert abs(got - expected) <= TOL and abs(got - expected) <= TOL * abs(expected), \
            f"{key}: {got!r} vs baseline {expected!r} ({BASELINE['label']}); re-baseline only if intended"
