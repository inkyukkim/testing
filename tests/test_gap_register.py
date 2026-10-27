"""Gap register: schema, cross-field rules, referential integrity, and the pipeline gate."""
import copy
import subprocess
import sys

import openpyxl
import pytest

from conftest import FIXTURES, MODEL, ROOT
from tools import gap_register as G
from tools.workbook_io import list_names

REGISTER = FIXTURES / "gap_register_KR.yaml"
KR = FIXTURES / "adaptation_input_KR.xlsx"


@pytest.fixture()
def reg():
    return G.load(REGISTER)


def gap(reg, gid):
    return next(g for g in reg["gaps"] if g["gap_id"] == gid)


def test_kr_register_is_valid(reg):
    assert G.validate(reg) == []


def test_terminal_care_gap_blocks_pipeline(reg):
    g = gap(reg, "GAP-001")
    assert g["target_names"] == ["c_terminal"] and g["source_items"] == ["KR-C11"]
    assert (g["class"], g["handling"], g["status"]) == ("non_transferable", "block", "open")
    result = G.gate(reg)
    assert result.blocked and result.blocking == ["GAP-001"] and result.errors == []


def test_gate_cli_exit_codes(tmp_path, reg):
    run = lambda path: subprocess.run([sys.executable, "-m", "tools.gap_register", str(path)],
                                      cwd=ROOT, capture_output=True, text=True)
    blocked = run(REGISTER)
    assert blocked.returncode == 2 and "BLOCKED: GAP-001" in blocked.stdout
    bad = copy.deepcopy(reg)
    gap(bad, "GAP-001")["handling"] = "retain_tagged"
    p = tmp_path / "bad.yaml"
    p.write_text(G.yaml.safe_dump(bad))
    assert run(p).returncode == 1


def test_human_resolution_unblocks(reg):
    g = gap(reg, "GAP-001")
    g["status"] = "resolved"
    g["resolution"] = {"option_id": "E1", "decided_by": {"kind": "human", "role": "HEOR lead (KR)"},
                       "date": "2026-11-02", "evidence": "KR-C11 updated from local claims analysis"}
    result = G.gate(reg)
    assert not result.blocked and result.errors == []


@pytest.mark.parametrize("mutate,rule", [
    (lambda g: g.update(handling="retain_tagged", retained_source="c_terminal"), "R1"),
    (lambda g: g.update(escalation_options=[]), "R2"),
    (lambda g: g.update(status="resolved", resolution={"option_id": "E1", "decided_by": {"kind": "agent", "role": "Input Mapper"},
                                                       "date": "2026-11-02", "evidence": "x"}), "R3"),
    (lambda g: g.update(status="resolved", resolution={"option_id": "E9", "decided_by": {"kind": "human", "role": "lead"},
                                                       "date": "2026-11-02", "evidence": "x"}), "R3"),
    (lambda g: g.update(resolution={"option_id": "E1", "decided_by": {"kind": "human", "role": "lead"},
                                    "date": "2026-11-02", "evidence": "x"}), "R4"),
])
def test_rule_violations_detected(reg, mutate, rule):
    mutate(gap(reg, "GAP-001"))
    errors = G.validate(reg)
    assert any(rule in e for e in errors), errors
    assert G.gate(reg).blocked


def test_retain_requires_source(reg):
    gap(reg, "GAP-002")["retained_source"] = None
    assert any("R5" in e for e in G.validate(reg))


def test_schema_rejects_unknown_class_and_extra_keys(reg):
    gap(reg, "GAP-002")["class"] = "mostly_transferable"
    gap(reg, "GAP-003")["value"] = 0.9                  # a number smuggled into the register
    errors = G.validate(reg)
    assert any("mostly_transferable" in e for e in errors) and any("unexpected key 'value'" in e for e in errors)


def test_register_references_exist(reg):
    names = set(list_names(MODEL))
    wb = openpyxl.load_workbook(KR)
    items = {ws.cell(row=r, column=1).value for ws in wb.worksheets for r in range(1, ws.max_row + 1)}
    items |= {ws.cell(row=4, column=c).value for ws in wb.worksheets for c in range(1, 5)}   # life-table column ids
    for g in reg["gaps"]:
        assert set(g["target_names"]) <= names, g["gap_id"]
        assert set(g["source_items"]) <= items, g["gap_id"]


def test_register_contains_no_numbers_in_decisions(reg):
    """Rationale may describe, but sources and resolutions are references, never values."""
    for g in reg["gaps"]:
        for key in ("target_names", "source_items"):
            assert all(isinstance(x, str) for x in g[key])
