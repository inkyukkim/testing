"""Report Profiler tools: extraction, numeral-to-cell matching, jurisdiction lint, scenarios."""
import json
from collections import Counter

import pytest

from conftest import FIXTURES, MODEL
from tools.docx_extract import extract
from tools.match_numbers import match
from tools.scenario_runner import run_scenarios

REPORT = FIXTURES / "global_report_UK.docx"
PROV = json.loads((FIXTURES / "global_report_UK.provenance.json").read_text())


@pytest.fixture(scope="module")
def scenario_values(tmp_path_factory):
    return run_scenarios(MODEL, FIXTURES / "scenarios_UK.yaml", tmp_path_factory.mktemp("scen"))


def test_scenario_runner_reproduces_report_scenarios(scenario_values):
    for x in PROV["numbers"]:
        sid = x["source"]["scenario"]
        if sid:
            assert x["value"] == scenario_values[sid][x["source"]["name"]], x["id"]


def test_match_recall_against_provenance(model_values, scenario_values):
    tokens = extract(REPORT)["tokens"]
    res = match(tokens, model_values, scenario_values)
    missed = []
    for r, truth in zip(res, PROV["numbers"]):
        name, sid = truth["source"]["name"], truth["source"]["scenario"] or "base"
        ok = any(c["name"] == name and (c["context"] == sid or
                 (c["context"] == "base" and model_values[name] == truth["value"])) for c in r["candidates"])
        if not ok:
            missed.append((truth["id"], r["token"], name, sid))
    assert missed == [], missed
    stats = Counter(r["status"] for r in res)
    assert stats["unmatched"] == 0
    print(f"\nmatch status: {dict(stats)} of {len(res)} tokens")


def test_without_scenarios_scenario_numbers_go_unmatched_or_ambiguous(model_values):
    res = match(extract(REPORT)["tokens"], model_values)
    sc4 = next(i for i, x in enumerate(PROV["numbers"]) if x["source"]["scenario"] == "SC4" and x["source"]["name"] == "res_icer")
    assert res[sc4]["status"] == "unmatched", "SC4 ICER cannot be traced without the scenario definitions"
