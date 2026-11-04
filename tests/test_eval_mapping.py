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


def test_gap_ids_are_labels_compared_by_class_and_handling():
    """Relabelled gap ids must not lower agreement; a different class or handling must."""
    import yaml
    reg = yaml.safe_load((FIXTURES / "gap_register_KR.yaml").read_text())
    cand, creg = copy.deepcopy(KEY), copy.deepcopy(reg)
    relabel = {g["gap_id"]: f"GAP-{900 + i:03d}" for i, g in enumerate(creg["gaps"])}
    for g in creg["gaps"]:
        g["gap_id"] = relabel[g["gap_id"]]
    for m in cand["mappings"]:
        if "gap_id" in m:
            m["gap_id"] = relabel[m["gap_id"]]
    assert evaluate(cand, KEY, creg, reg)["agreement"] == 1.0
    next(g for g in creg["gaps"] if "prop_male" in g["target_names"])["handling"] = "retain_flagged"
    r = evaluate(cand, KEY, creg, reg)
    assert {d["target"] for d in r["differences"]} == {"prop_male", "baseline_age"} and r["critical"] == []


def test_first_blind_agent_run_is_recorded_and_scores():
    """Gate 2 evidence: the blind Input Mapper run (docs/agent_runs/gate2) has no critical finding."""
    import yaml
    run = FIXTURES.parent / "docs" / "agent_runs" / "gate2"
    cand = json.loads((run / "mapping_spec.json").read_text())
    r = evaluate(cand, KEY, yaml.safe_load((run / "gap_register.yaml").read_text()),
                 yaml.safe_load((FIXTURES / "gap_register_KR.yaml").read_text()))
    assert r["critical"] == [] and r["agreement"] >= 0.95
