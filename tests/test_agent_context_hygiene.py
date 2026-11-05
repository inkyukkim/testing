"""CLAUDE.md is injected into every agent started in this repository, including agents under
blind evaluation (found in Gate 5: all round-1 evaluation transcripts contained its fixture
notes). It must therefore hold no answer-key or fixture-outcome content."""
from conftest import ROOT

FORBIDDEN = ["GAP-001", "KR-C11", "KR-S07", "terminal care", "86 unique", "lower-bound", "34 mapped",
             "46 retained", "Fixture A (", "mid_cycle_continuous", "annual_step", "D09", "D13", "test-only",
             "standard of care", "prop_male", "100+", "28,271", "28,321", "22 claims"]


def test_claude_md_has_no_answer_key_content():
    text = (ROOT / "CLAUDE.md").read_text()
    hits = [t for t in FORBIDDEN if t in text]
    assert not hits, f"move to docs/fixture_notes.md: {hits}"


def test_fixture_notes_exist_outside_claude_md():
    notes = (ROOT / "docs" / "fixture_notes.md").read_text()
    assert "GAP-001" in notes and "never be loaded into an agent under evaluation" in notes
