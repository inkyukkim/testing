"""Claims Analyst tools: claim language, register rules, readiness, and KR re-evaluation."""
import copy
import json

import pytest

from conftest import FIXTURES, MODEL
from test_build_and_verify import make_resolved
from tools.build_run import build_run
from tools.claims import evaluate_register, ready, validate
from tools.docx_extract import extract
from tools.evaluate_claim import evaluate
from tools.jurisdiction_lint import lint
from tools.scenario_runner import run_scenarios
from tools.workbook_io import read_named

KEY = json.loads((FIXTURES / "claims_register_KR.json").read_text())
BLOCKS = extract(FIXTURES / "global_report_UK.docx")["blocks"]


@pytest.fixture(scope="module")
def global_contexts(model_values, tmp_path_factory):
    return {"base": model_values, **run_scenarios(MODEL, FIXTURES / "scenarios_UK.yaml", tmp_path_factory.mktemp("sc"))}


@pytest.fixture(scope="module")
def kr_contexts(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("kr")
    log = build_run(make_resolved(tmp), tmp / "run")
    assert log["status"] == "built"
    return {"base": read_named(tmp / "run" / "recalc" / "adapted_model.xlsx")}


def test_every_evaluable_claim_is_true_on_the_global_model(global_contexts):
    reg = evaluate_register(KEY, global_contexts)
    truths = {c["claim_id"]: c["truth_global"] for c in reg["claims"]}
    assert all(t is True for t in truths.values() if t != "not_evaluable"), truths
    assert sum(t is True for t in truths.values()) == 10
    assert validate(reg, BLOCKS) == []


def test_kr_truths_pending_until_adapted_model_exists(global_contexts):
    reg = evaluate_register(KEY, global_contexts)
    assert {c["truth_local"] for c in reg["claims"]} <= {"pending", "not_evaluable"}
    blockers = ready(reg)
    assert any("C09: local truth pending" in b for b in blockers)
    assert any("C20: open human review" in b for b in blockers)


def test_kr_reevaluation_on_test_only_build(global_contexts, kr_contexts):
    """Development check (D16): which claims flip under KR inputs. Scenario claims stay pending."""
    reg = evaluate_register(KEY, global_contexts, kr_contexts)
    t = {c["claim_id"]: c["truth_local"] for c in reg["claims"]}
    assert t["C03"] is False, "single KR reference value: no 'not cost-effective at the lower bound'"
    assert t["C09"] is True, "efficacy retained: curves still do not cross"
    for cid in ("C04", "C17", "C18", "C19"):
        assert t[cid] == "pending", "needs a local scenario set"
    assert validate(reg, BLOCKS) == [], "C03 is removed, so its local falsity is consistent"
    print("\nKR truths (test-only build):", {k: v for k, v in t.items() if v not in ("pending", "not_evaluable")})


def claim(reg, cid):
    return next(c for c in reg["claims"] if c["claim_id"] == cid)


@pytest.mark.parametrize("mutate,rule", [
    (lambda r: claim(r, "C20").update(action="rerender"), "K2"),        # untraceable assertion
    (lambda r: claim(r, "C01").update(action="rerender"), "K2"),        # jurisdiction-specific
    (lambda r: claim(r, "C22").update(action="human_review"), "K2"),    # conclusion must be reworded
    (lambda r: claim(r, "C09").update(action="regenerate"), "K3"),      # model_check cannot regenerate
    (lambda r: claim(r, "C02")["expression"]["of"][1].update(rhs=30000), "K5"),
    (lambda r: claim(r, "C02").update(excerpt="Drug A is dominant"), "K6"),
])
def test_rules(mutate, rule):
    reg = copy.deepcopy(KEY)
    mutate(reg)
    assert any(rule in e for e in validate(reg, BLOCKS))


def test_rerendering_a_locally_false_claim_is_rejected(global_contexts, kr_contexts):
    reg = copy.deepcopy(KEY)
    claim(reg, "C03")["action"] = "rerender"
    errors = validate(evaluate_register(reg, global_contexts, kr_contexts), BLOCKS)
    assert any(e.startswith("C03: K4") for e in errors)


def test_claim_language_ops():
    ctx = {"base": {"a": 3, "b": 5, "x": -1, "y": 2, "s": "Yes"}, "S1": {"a": 4, "s": "No"}, "S2": {"a": 9, "s": "Yes"}}
    assert evaluate({"op": "lt", "lhs": "a", "rhs": "b"}, ctx)["truth"] is True
    assert evaluate({"op": "argmax", "refs": ["x", "y"], "expect": "y"}, ctx)["truth"] is True
    assert evaluate({"op": "rank_abs_change", "refs": ["a@S1", "a@S2"], "base": "a", "expect_order": ["a@S2"]}, ctx)["truth"] is True
    assert evaluate({"op": "select", "refs": ["s@S1", "s@S2"], "where": {"op": "ne", "rhs": {"text": "Yes"}},
                     "expect": ["s@S1"]}, ctx)["truth"] is True
    assert evaluate({"op": "rel_change_below", "a": "a@S1", "b": "a", "tol": {"registry": "negligible_rel_change"}}, ctx)["truth"] is False
    assert evaluate({"op": "le", "lhs": "a@S9", "rhs": "b"}, ctx)["truth"] == "pending"
    assert evaluate({"op": "external"}, ctx)["truth"] == "not_evaluable"
    with pytest.raises(ValueError):
        evaluate({"op": "le", "lhs": "a", "rhs": 4}, ctx)


def test_jurisdiction_lint_finds_uk_terms_and_key_covers_them():
    hits = lint(BLOCKS)
    body = [h for h in hits if h["kind"] != "reference"]
    assert {"NICE", "NHS", "PAS", "eMIT", "PSSRU", "£"} <= {h["term"] for h in body}
    claimed = {c["block"] for c in KEY["claims"]}
    term_paragraphs = {h["block"] for h in body if BLOCKS[h["block"]]["kind"] == "paragraph" and h["term"] != "£"}
    assert term_paragraphs - claimed == set(), "every paragraph with a UK term (other than currency) is in the register"
