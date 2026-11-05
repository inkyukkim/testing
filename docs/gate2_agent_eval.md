# Gate 2: first blind Input Mapper run

**Date:** 2026-11-04.

**Agent:** fresh general-purpose Claude agent, with no context from the building session, following the Input Mapper instructions (`.claude/agents/input-mapper.md`).

**Outputs:** `docs/agent_runs/gate2/mapping_spec.json` and `docs/agent_runs/gate2/gap_register.yaml`.

**Scored by:** `python -m tools.eval_mapping docs/agent_runs/gate2/mapping_spec.json fixtures/mapping_spec_KR.json docs/agent_runs/gate2/gap_register.yaml fixtures/gap_register_KR.yaml`.

## Set-up (blind workspace)

The agent worked in a copy of the repository that contained only:
- `tools/`
- `schemas/`
- the global model and its conventions file
- the KR input workbook
- an excerpt of the design principle and the gap-register rules
- the agent instructions

These were left out, because each would reveal the expected answer:
- the answer keys
- `docs/decisions.md`
- the CLAUDE.md fixture notes
- the fixture generators (their docstrings list the KR traps)
- the tests

`model_profile.json` was produced by the deterministic profiler tool, not by the Model Profiler agent. That way the run tests the Input Mapper alone.

Before this run, two leaks were found and removed from the main repository. The agent definition pointed at the answer key "for the shape"; it now points at `schemas/mapping_spec.schema.yaml`. The gap-register section of CLAUDE.md named the KR blocking gap; it was excluded from the blind excerpt.

**Remaining threat to validity:** the agent had file-system access outside the workspace and was told not to use it. Its tool calls were not audited. Its outputs differ from the answer key in ways that suggest it did not copy the key (different gap numbering, structure and wording).

## Results

| Measure | Value |
|---------|-------|
| Model inputs covered | 81 of 81 |
| Dry run (`apply_mapping`) | exit 2, blocked by its terminal-care gap only; no INVALID lines |
| Gap register gate | exit 2, same gap |
| Critical findings (filled a blocking gap; mapped an input the key retains; missing input) | **none** |
| Agreement, with gaps compared by class and handling | **95.1% (77 of 81)** |
| Agreement, with gap ids compared as strings (scorer flaw, since fixed) | 61.7% |

The 4 disagreements are judgement calls. In each one the agent is more cautious than the key.

| Input | Answer key | Agent | Agent's reason |
|-------|-----------|-------|----------------|
| `prop_male`, `baseline_age` | transferable / retain_tagged | transferable / retain_flagged | Both now weight a Korean life table and population norms, so the mix of trial cohort and Korean data should be reviewed |
| `int_ae_qaly_loss`, `comp_ae_qaly_loss` | transferable / retain_tagged | partial / retain_flagged | The disutilities were valued with the UK value set, while the state utilities now use the Korean one |

Both arguments are defensible. Whether the answer key should adopt them is a decision for the HEOR lead; the key has not been changed.

## Findings about the agent

- It got every high-stakes decision right:
  - It blocked the terminal-care gap and listed FX conversion, zero and "retain UK" as prohibited.
  - It left the exchange rate and co-payment unused.
  - It used Korean list prices and recorded that no risk-sharing discount applies.
  - It matched the subsequent-therapy classes by meaning.
  - It chose the same dose-counting rule and the same life-table conversion as the accepted decisions D07 and D08. It did not see those decisions.
- **It mis-stated a number in prose.** Its report said "37 mapped, 43 retained"; the file has 34 mapped and 46 retained. The files were right and the summary was wrong. This is the failure the design principle exists to prevent. Agent hand-back summaries must cite tool output, not restate counts.

## Findings about the tools (raised by the agent, verified)

| Issue | Action |
|-------|--------|
| The scorer compared gap ids as strings, but ids are arbitrary labels | Fixed: gaps are compared by class and handling; test added |
| The numeral check covered mapping rationales but not gap-register text | Fixed: rule R7 in `tools/gap_register.py`. It found numerals in **the answer key's own register** (GAP-001, GAP-003, GAP-004), which have been reworded |
| `retained_source` is a single string, but one gap can retain many targets | Open: the schema should allow a list |
| `mx_to_qx` requires a gap_id, but the rules do not say which class or handling | Open: document partial / retain_flagged as the convention |
| `confirm_in_source` without `{value}` (e.g. "Lifetime", "mg/kg") confirms a label, not the retained number | Open: report label-only confirmations separately in the dry run |
| No guidance for jurisdiction-specific bounds such as `wtp_threshold_lower` | Open: covered by accepted D09; add to the agent instructions |
| YAML anchors (`&id001`) pass validation | Open: reject anchors and aliases in registers |

## Update after Gate 2.1 (2026-11-04)

The HEOR lead accepted the agent's four classifications into the answer key (D13). The
recorded run now scores **80 of 81**, with no critical or minor differences. The one
remaining difference is `time_horizon_years`. The agent confirmed it with the label
"Lifetime"; Gate 2.1 rejects a label-only confirmation of a numeric input, so the key now
retains the horizon as a structural setting. The agent had raised this weakness itself.

The open tool issues listed above were fixed in Gate 2.1 (D15):
- `retained_source` is a list and every entry is checked.
- Label-only confirmations are rejected for numeric inputs and listed as REVIEW for switches.
- YAML anchors are rejected (R8).
- The life-table gap convention and the single-threshold rule (D09) are in the agent instructions.
