# Gate 5: blind agent evaluations (all eight agents)

**Date:** 2026-11-05. **Harness:** `evals/prepare_blind.py`. **Scorers:** `tools/eval_mapping.py`, `tools/eval_report_profile.py`, `tools/eval_claims.py`, plus checklists for planted defects.

**Round-2 outputs:** `docs/agent_runs/gate5/`. **Keys and plants:** `docs/agent_runs/gate5_keys.json`.

## Headline: neither round is fully blind

**What leaked.** Every agent started in this repository received the CLAUDE.md that was **loaded when the orchestrating session started**. That copy had its "Fixture notes" section, which describes the KR traps, the answer keys' outcomes and Fixture A's conventions.

**Round 1 vs round 2.**
- Round 1 exposed all eight agents in this gate, and the Gate 2 Input Mapper run too.
- Before round 2 the notes were moved to `docs/fixture_notes.md`, and a test now keeps CLAUDE.md clean.
- Round 2 was still exposed: subagents get the session's cached CLAUDE.md, not the file on disk.

**What the audits show.** Transcript audits find, for every agent in both rounds:
- **no tool call reading the repository or any answer-key file**;
- **no change to any protected input**, per hash snapshots;
- the injected text present in context.

**What this means for the results.**
- *Not plausibly affected:* the planted-defect agents (Model Profiler, Model Verifier, Report Verifier) and the Builder/Runner. Their plants appear nowhere in CLAUDE.md.
- *Upper bounds:* the Input Mapper, Claims Analyst and Report Writer. Their scores may benefit from the hints.
- *Partly affected:* the Report Profiler. CLAUDE.md gave counts, not mappings.

**A truly blind round** needs a session that never loaded the old CLAUDE.md. See "Round 3" below.

## Results

| Agent | Task | Round 1 | Round 2 |
|-------|------|---------|---------|
| Input Mapper | KR mapping spec + gap register vs answer key | (Gate 2 run) 77/81 → 80/81 after D13 | **81/81, no critical or minor differences** |
| Model Profiler | find 4 planted defects (hidden literal, cross-arm RDI link, pasted constant, wrong discount declaration) | **4/4**; one item of supporting evidence came from leaked context | **4/4**, all evidence from the workspace (ReadMe sheet, profile fields) |
| Builder/Runner | real spec (blocked) + test-resolved spec | correct; **found a tool bug** (git state) | correct; confirms the fix (commit and dirty both null) |
| Model Verifier | clean run vs tampered run | correct accept/reject; reported 3 extra one-ULP differences, **which were real** (harness bug) | correct; only planted V02/V03/V08 |
| Report Profiler | resolve 184 numerals (98 ambiguous) | **184/184**, but wrote a script outside its workspace | **184/184**, within workspace |
| Claims Analyst | claims register vs 22-claim key | recall 100%, precision 50%, kind 100%, action 91%, truth 100%, 0 critical | recall 95.5% (missed C14 rounding note), precision 43%, kind 100%, action 95%, truth 100%, 0 critical |
| Report Writer | own template → draft passing R01–R07 | pass, 134 numbers; **found a renderer bug** | pass on first render, 141 numbers, 0 numerals in template |
| Report Verifier | clean draft vs tampered draft | correct: A pass but not acceptable as final; B reject on R01/R04/R05 | correct, same |

**Precision.** Low claims precision is not an error rate. Both Claims Analyst runs registered more claims than the key (44 and 49 against 22). Many additions are legitimate, for example "in line with the reference case", trial-protocol stopping rules and trial-based subsequent-therapy shares. The key is a minimum, not the full set.

**Recurring discipline failure.** Agents **restate numbers in hand-back prose** even when their files are correct: the Gate 2 Input Mapper's miscounted summary, and the round-2 Report Writer and Claims Analyst quoting figures. Prompts and agent definitions must forbid this explicitly, and the orchestrator must only quote tool output.

## Tool and harness defects found by the agents

| Found by | Defect | Status |
|----------|--------|--------|
| Builder/Runner (r1) | `run_log` recorded `git_dirty: false` outside a repository, which looks like a clean tree | Fixed (`git_state`), test added |
| Model Verifier (r1) | harness re-saved the tampered workbook with openpyxl defaults, so extra one-ULP changes appeared | Fixed (exact-float save) |
| Report Writer (r1) | `{{st_cost_1\|money}}` refused as a "literal numeral" (digit after `_`) | Fixed in `docx_extract` |
| Report Writer (r1) | R06 needs the DRAFT banner on the title page; undocumented | Documented in the agent definition |
| Report Profiler (r1) | wrote outside its workspace | Prompts now require scratch files under `work/` |
| Model Profiler (r2) | `annual_step` is a supported value, so the engine accepts a wrong declaration, and V07 would test parity against the wrong convention | **Open**: make a Model Profiler mismatch a blocking sign-off before the Model Verifier |
| Input Mapper (r2) | `apply_mapping` does not check that subsequent-therapy shares sum to at most 1 (only the built model's `check_st_shares_ok` does) | Open |
| Input Mapper (r2) | `mx_to_qx` with `carry_last_rate` also replaces the open-band age's own rate; `duration_to_doses` rule semantics undocumented | Open (documentation) |
| Input Mapper (r2) | label-only confirmations for switches are weak evidence | Open |
| Report Writer (r2) | no bare "UK" in the jurisdiction term list | Open |
| Report Writer (r2) | truth-dependent prose with no claim behind it (e.g. "driven mainly by longer OS"); reworded claims only get a banned-term check | Open: Claims Analyst coverage rule |
| Report Writer (r2) | life-table ranges have no label in the retained-inputs list | Open |
| Report Verifier (r2) | provenance records a template path outside the workspace, which points at the answer-key template | Open: record template hash only |

## Round 3 (proposed, not run)

A truly blind run needs agents in a session that never loaded the old CLAUDE.md:
1. Push the eight workspaces (only) to an orphan branch, with no CLAUDE.md, fixtures or docs.
2. Start a fresh cloud session on that branch, and run the eight agents there.
3. Copy the outputs back and score them here with the same scorers.

This needs the HEOR lead's approval, because it creates a branch on the repository and a new session.
