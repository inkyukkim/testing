# Gate 5: blind agent evaluations (all eight agents)

**Date:** 2026-11-05. **Harness:** `evals/prepare_blind.py`. **Scorers:** `tools/eval_mapping.py`, `tools/eval_report_profile.py`, `tools/eval_claims.py`, plus checklists for planted defects.

**Outputs:** round 2 in `docs/agent_runs/gate5/`, round 3 in `docs/agent_runs/gate5_round3/`. **Keys and plants:** `docs/agent_runs/gate5_keys.json`, `docs/agent_runs/gate5_round3_keys.json`.

## Headline: rounds 1 and 2 were not fully blind; round 3 was

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

**Round 3** ran in a separate session on an orphan branch that held only the eight workspaces. Its scores match or come close to round 2, so the leaked hints did not inflate the earlier results in any way we can measure. See "Round 3" below.

## Results

| Agent | Task | Round 1 | Round 2 | Round 3 (blind) |
|-------|------|---------|---------|-----------------|
| Input Mapper | KR mapping spec + gap register vs answer key | (Gate 2 run) 77/81 → 80/81 after D13 | **81/81, no critical or minor differences** | 79/81, 0 critical; 2 differences: AE QALY losses classed `transferable` (key `partial`), both `retain_flagged` |
| Model Profiler | find 4 planted defects (hidden literal, cross-arm RDI link, pasted constant, wrong discount declaration) | **4/4**; one item of supporting evidence came from leaked context | **4/4**, all evidence from the workspace (ReadMe sheet, profile fields) | **4/4**, all evidence cited from profile fields and formulas |
| Builder/Runner | real spec (blocked) + test-resolved spec | correct; **found a tool bug** (git state) | correct; confirms the fix (commit and dirty both null) | correct; read `git_dirty: true` correctly as not reproducible from the commit |
| Model Verifier | clean run vs tampered run | correct accept/reject; reported 3 extra one-ULP differences, **which were real** (harness bug) | correct; only planted V02/V03/V08 | correct; only planted V02/V03/V08 |
| Report Profiler | resolve 184 numerals (98 ambiguous) | **184/184**, but wrote a script outside its workspace | **184/184**, within workspace | **184/184**, 98/98 ambiguous, within workspace |
| Claims Analyst | claims register vs 22-claim key | recall 100%, precision 50%, kind 100%, action 91%, truth 100%, 0 critical | recall 95.5% (missed C14 rounding note), precision 43%, kind 100%, action 95%, truth 100%, 0 critical | recall 95.5% (missed C13 PSA scope note), precision 40% (53 claims), kind 100%, action 90%, truth 100%, 0 critical |
| Report Writer | own template → draft passing R01–R07 | pass, 134 numbers; **found a renderer bug** | pass on first render, 141 numbers, 0 numerals in template | pass, 142 numbers, 0 numerals in template |
| Report Verifier | clean draft vs tampered draft | correct: A pass but not acceptable as final; B reject on R01/R04/R05 | correct, same | correct: A pass; B reject on R01/R04/R05 |

**Precision.** Low claims precision is not an error rate. Every Claims Analyst run registered more claims than the key (44, 49 and 53 against 22). Many additions are legitimate, for example "in line with the reference case", trial-protocol stopping rules and trial-based subsequent-therapy shares. The key is a minimum, not the full set.

**Recurring discipline failure.** Agents **restate numbers in hand-back prose** even when their files are correct: the Gate 2 Input Mapper's miscounted summary, and the round-2 Report Writer and Claims Analyst quoting figures. Prompts and agent definitions must forbid this explicitly, and the orchestrator must only quote tool output.

## Tool and harness defects found by the agents

| Found by | Defect | Status |
|----------|--------|--------|
| Builder/Runner (r1) | `run_log` recorded `git_dirty: false` outside a repository, which looks like a clean tree | Fixed (`git_state`), test added |
| Model Verifier (r1) | harness re-saved the tampered workbook with openpyxl defaults, so extra one-ULP changes appeared | Fixed (exact-float save) |
| Report Writer (r1) | `{{st_cost_1\|money}}` refused as a "literal numeral" (digit after `_`) | Fixed in `docx_extract` |
| Report Writer (r1) | R06 needs the DRAFT banner on the title page; undocumented | Documented in the agent definition |
| Report Profiler (r1) | wrote outside its workspace | Prompts now require scratch files under `work/` |
| Model Profiler (r2) | `annual_step` is a supported value, so the engine accepts a wrong declaration, and V07 would test parity against the wrong convention | Fixed: `build_run` refuses to build on a declared-vs-detected mismatch (exit 1, "convention mismatch"), and V07 reports "not evaluated" when V08 finds one |
| Input Mapper (r2) | `apply_mapping` does not check that subsequent-therapy shares sum to at most 1 (only the built model's `check_st_shares_ok` does) | Fixed: registry `share_groups`, checked in the dry run in exact arithmetic without showing values |
| Input Mapper (r2) | `mx_to_qx` with `carry_last_rate` also replaces the open-band age's own rate; `duration_to_doses` rule semantics undocumented | Fixed: both documented in the `apply_mapping` docstring (open band replaces age N and above; ceil counts doses starting before the limit, floor counts whole intervals) |
| Input Mapper (r2) | label-only confirmations for switches are weak evidence | Fixed: a label confirming a switch must declare `means: switch_on/switch_off`, and the tool checks it against the retained value |
| Report Writer (r2) | no bare "UK" in the jurisdiction term list | Fixed: added to `geography` (no hit in any existing report) |
| Report Writer (r2) | truth-dependent prose with no claim behind it (e.g. "driven mainly by longer OS"); reworded claims only get a banned-term check | Fixed: `tools/truth_cues.yaml`. The renderer refuses truth-dependent wording outside a claim conditional (T1), and `claims` lists report wording no claim excerpt covers (REVIEW). This showed the key itself lacked the claim, so C23–C25 were added (D20) |
| Report Writer (r2) | life-table ranges have no label in the retained-inputs list | Fixed: `profile_workbook` labels a column-vector input from the header above it |
| Report Verifier (r2) | provenance records a template path outside the workspace, which points at the answer-key template | Fixed: provenance records template and sidecar as file name plus SHA-256 |

## Round 3: blind run

**Setup.**
- `evals/prepare_blind.py` built the eight workspaces and `evals/tasks.py` wrote their prompts.
- They were pushed to the orphan branch `eval/blind-round3` (commit `fbe3f4e`). That branch has no CLAUDE.md, fixtures, docs, tests or answer keys from `main`.
- A fresh cloud session cloned only that branch and launched the eight agents from `ORCHESTRATOR.md`. Agent outputs were pushed to `eval/blind-round3-results` (`6904ce2`) and scored here with the same scorers as round 2.

**Audit.**
- The session's full event log was read: 211 assistant events and 121 tool calls.
- No tool call ran git fetch or checkout, and none touched a path outside the agent's own workspace. The one flagged call was an agent reading its own harness tool-result file, which is harmless.
- The hash snapshot of 313 protected workspace files is unchanged. All 86 changed files are agent outputs.
- No hand-back, review or script mentions an answer key, `fixture_notes` or CLAUDE.md.
- **Residual risk:** the answer keys still exist on other branches of the same repository. An agent could have fetched them, but the audit shows none did.

**What changed relative to round 2.**
- **Input Mapper: 79/81, down from 81/81, no critical difference.**
  - Both AE QALY-loss inputs were classed `transferable / retain_flagged`; the key has `partial / retain_flagged`. Handling is the same, so the report outcome is unchanged.
  - The agent's own rationale argues for `partial`: AE incidence transfers, but the losses are valued with a UK value set while local state utilities use a Korean one. That is a structure-transfers, calibration-is-local case, so the classification contradicts the rationale.
  - The rest matches the key: the only block is terminal care, and the life table, population norms, baseline characteristics and trial efficacy are all handled as in the key. The register numbers gaps in a different order, which the scorer ignores.
- **Claims Analyst: same profile as round 2.**
  - It missed a different scope note (C13, "PSA results are not included", instead of C14).
  - **C02 is the wrong action.** "Drug A is cost-effective" got `rerender` instead of `reword`. The agent's own rationale says the threshold-range wording must change, and its hand-back says so too, so this is an inconsistency rather than a misreading. The sentence also carries a GBP value, which `rerender` would keep.
  - **C21 is more conservative than the key.** The commissioning sentence got `human_review` instead of `reword`.
  - It correctly found both threshold claims that are false locally, at the lower threshold and for the range, and marked them `remove`.
- **Builder/Runner.** Here the tools ran inside a git checkout, so `git_commit` is set. `git_dirty` is true because other agents were writing into the same checkout at the same time. The agent read this correctly: not reproducible from a commit.
- **Hand-back discipline is much better.**
  - No hand-back restates a model value in its own words.
  - The Report Verifier quotes the verifier's own failure message, which contains the tampered and the traced ICER. That is allowed, as tool output.
  - The Claims Analyst quotes two report excerpts verbatim, with GBP thresholds. This is borderline: it is a quote from a file, not tool output.

**Rescored against the 25-claim key (D20, accepted).** The Claims Analyst gets recall 96% in both rounds. Round 2: precision 49%, action agreement 96%, truth agreement 100%. Round 3: precision 45%, action agreement 88%, truth agreement 96%. Neither round has a critical difference. Both rounds registered the "driven mainly by" claim the key lacked. In round 3, C24 is another `rerender` where the key says `reword`, and C23 is a truth disagreement: the agent checked only direction, while the key holds the attribution not traceable to a cell.

**Findings from round 3 (fixed after the round; decisions D17–D19, accepted).**

| Found by | Finding | Fix |
|----------|---------|-----|
| Claims Analyst, Report Writer | Was `rerender` allowed to keep source-currency or source-jurisdiction wording? And did R03 count expression-less scope notes (C13, C14) as rerender claims? | `rerender` is now defined: the excerpt stays word for word, and only its numerals and their attached currency symbol change. A new rule K7 in `tools/claims.py` refuses a rerender excerpt that keeps any other source-jurisdiction term. An advisory REVIEW line flags a rerender whose rationale asks for new wording; on the round-3 register it flags C05 and C51. On the Report Writer's second point: R03 already exempts rerender claims with no expression. The writer misread it, and the docstring now says so explicitly. |
| Builder/Runner | `git_dirty` covered the whole checkout, so unrelated untracked files made every run non-reproducible. | `git_state` now checks only `git_dirty_scope`: the `tools/` and `schemas/` folders plus the run's declared inputs inside the repository. The scope is recorded in `run_log`. |
| Input Mapper | `int_dose_mg` was labelled in mg but its unit is mg/kg. | Renamed to `int_dose` and `comp_dose` in the generator, engine, report, template, answer key and tests. The fixtures were regenerated; values are unchanged and only the names in the provenance changed. |
| Input Mapper | No guidance on whether population characteristics are `transferable` or `partial`. | Classification rule added to `.claude/agents/input-mapper.md` (D19). |
| Input Mapper | Class contradicted the rationale for AE QALY losses. | `gap_register.review_notes` prints a REVIEW line when a `transferable` gap's text cites a value set, tariff, calibration or local valuation. It flags the round-3 register's GAP-006 and nothing in the key or the round-2 register. |

**Caveat on D19.** The new guidance turns the D13 answer-key classifications into a general rule. Future blind Input Mapper scores on those items therefore test whether the agent follows instructions, not its own judgement.

**Conclusion.**
- Blind scores are within one to two items of the exposed rounds for every agent.
- The planted-defect agents (Model Profiler, Model Verifier, Report Verifier) and the Report Profiler were perfect in all three rounds.
- The remaining weaknesses are judgement calls in the Input Mapper and the Claims Analyst. Each was caught by a deterministic scorer and none was critical. Those are the two hand-offs where the human sign-off matters most.
