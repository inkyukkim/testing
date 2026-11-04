"""Scoring of agent-produced mapping specs against the KR answer key."""
import copy
import json

from conftest import FIXTURES
from tools.eval_mapping import evaluate

KEY = json.loads((FIXTURES / "mapping_spec_KR.json").read_text())


def entry(spec, t):
    return next(m for m in spec["mappings"] if m["target"] == t)


def test_key_against_itself():
    r = evaluate(KEY, KEY)
    assert r["agreement"] == 1.0 and r["critical"] == [] and r["differences"] == []


def test_filling_the_terminal_care_gap_is_critical():
    cand = copy.deepcopy(KEY)
    entry(cand, "c_terminal").update(status="retained", operation="retain_global", basis="structural_setting")
    r = evaluate(cand, KEY)
    assert any(c.startswith("c_terminal: key has gap GAP-001") for c in r["critical"])


def test_mapping_a_retained_input_is_critical_and_method_choice_is_a_difference():
    cand = copy.deepcopy(KEY)
    e = entry(cand, "prop_male")
    e.update(status="mapped", operation="copy", args={"source": "KR-P01"})
    entry(cand, "lt_qx_male")["args"]["method"] = "actuarial"
    r = evaluate(cand, KEY)
    assert any(c.startswith("prop_male: key retains") for c in r["critical"])
    assert any(d["target"] == "lt_qx_male" for d in r["differences"])
    assert r["agreement"] < 1.0


def test_missing_target_is_critical():
    cand = copy.deepcopy(KEY)
    cand["mappings"] = [m for m in cand["mappings"] if m["target"] != "u_pd"]
    assert "u_pd: missing from candidate" in evaluate(cand, KEY)["critical"]
