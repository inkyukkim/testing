# PartSA adaptation agents: prototype (Gate 0)

Prototype agent system that adapts a global oncology partitioned-survival (PartSA)
cost-effectiveness model to a local country and regenerates its technical report.
**Synthetic data only.** Nothing in this repository is real clinical, price or HTA data.

Status: **Gate 1** = Gate 0.5 (realistic Fixture A, conventions, gap register, rounding
verifier, parity tests) plus Fixture B (annual-step discounting), the Model Profiler and
Input Mapper deterministic tools (`profile_workbook`, `read_local_inputs`, `apply_mapping`,
`eval_mapping`), their agent definitions in `.claude/agents/`, and KR answer keys
(`mapping_spec_KR.json`, `gap_register_KR.yaml`). **Gate 2** adds the Builder/Runner
(`build_run`) and Model Verifier (`verify_model`, checks V01-V10) tools and agent
definitions, the mapping-spec schema, exact float writing, and a first blind Input Mapper
agent run scored against the answer key (`docs/gate2_agent_eval.md`). **Gate 2.1** fixes the
tool issues that run raised (label-only confirmations, list-valued `retained_source`, YAML
anchors R8, free-text numerals R7) and updates the answer key (D13). Decisions D01-D16 are
in `docs/decisions.md`; GAP-001 remains open (D14).

## Design principle (non-negotiable)

> **Agents decide meaning; deterministic tools move numbers.**
> **No numeric value may pass through LLM-generated text without a traceable source cell.**

Operational rules that follow from it:

1. An agent never types a number into a workbook, a mapping, or a report. It emits
   *references* (defined names, `item_id`s, sheet!cell) and *declarative instructions*
   (which operation, which source); a deterministic tool performs the arithmetic and writes
   the value.
2. Agent-authored prose contains **placeholders**, not numerals: `{{res_icer|gbp}}`. The
   renderer resolves them from a recalculated workbook and records provenance
   (workbook, scenario overrides, name, sheet, cell, format).
3. Unit and conversion constants (days per month, weeks per year) are not literals in
   agent output. They come from model cells (e.g. `days_per_year`) or from a versioned
   constants registry that a tool reads.
4. Every numeral in a delivered report must match an entry in its provenance manifest.
   Structural numerals (section, table and reference numbers, document version) are the
   only exemption, and the exemption is defined by the verifier tool, not by an agent.
5. A claim whose truth depends on numbers (e.g. "cost-effective at the threshold") must be
   re-evaluated by a tool against the recalculated values. An agent may choose the wording,
   but not the truth value.
6. If a required tool is unavailable (e.g. LibreOffice), **stop and report**. Never
   substitute an LLM estimate or a different engine silently.

## Environment

- Linux, Python 3.11+ (`openpyxl`, `python-docx`, `numpy`, `pyyaml`, `pytest`), LibreOffice headless
  (tested with 24.2). No Excel, no VBA execution.
- Recalculation uses LibreOffice with a throw-away profile that forces "always recalculate
  on load" for OOXML (`tools/recalc.py`). openpyxl-written files carry **no cached values**,
  so any value read after `recalc()` was computed by LibreOffice.

## Architecture: 8 agents in 2 stages

Each agent consumes and produces files only. Hand-offs are JSON or xlsx/docx artifacts, so
any step can be rerun, inspected, or replaced by a human. Tools marked **(G0)** exist now;
the rest are specified contracts for later gates.

### Stage 1: model adaptation

| # | Agent | Inputs | Outputs | Deterministic tools called |
|---|-------|--------|---------|----------------------------|
| 1 | **Model Profiler** (`.claude/agents/model-profiler.md`) | global model `.xlsx`, `<model>.conventions.yaml` | `model_profile.json`: formula regions, defined names with structural role (input / derived / output), input metadata (label, unit, PSA), input dependencies of every formula name, parallel arm layouts, hardcoding findings, detected conventions and mismatches with the declaration; `model_profile_review.md` (agent's reading of it) | `profile_workbook` **(G1)**, `partsa_engine.load_conventions` **(G0.5)** |
| 2 | **Input Mapper** (`.claude/agents/input-mapper.md`) | `model_profile.json`, `<model>.conventions.yaml`, local input `.xlsx` (e.g. `adaptation_input_KR.xlsx`) | `mapping_spec.json`: one entry per model input with `target_name`, `source` (`item_id` / model name / `retain_global`), whitelisted `operation`, rationale, and `status` (`mapped` / `retained` / `gap` / `rejected`); `gap_register.yaml` (every `gap` and `retained` entry classified, see below) | `read_local_inputs` **(G1)**, `apply_mapping` dry run **(G1)** (coverage of every input, every local item accounted for, gap references, unit dimensions via `tools/constants_registry.yaml`, text confirmations, currency mixing; exposes no values), `gap_register.validate` **(G0.5)**; scored offline by `eval_mapping` **(G1)** |
| 3 | **Builder/Runner** (`.claude/agents/builder-runner.md`) | global model, approved `mapping_spec.json`, approved `gap_register.yaml`, scenario list (references only) | `adapted_model.xlsx` (constants written into named input cells only), recalculated copy, `overrides.json` (values + provenance), scenario results, `run_log.json` (status built/blocked/invalid, input/output hashes, tool versions, git commit and dirty flag) | `build_run` **(G2)**: `gap_register.gate` first (exit 2 = stop, nothing built), `apply_mapping`, `workbook_io.write_named` (exact floats), `recalc` |
| 4 | **Model Verifier** (`.claude/agents/model-verifier.md`) | Builder/Runner run directory, approved `mapping_spec.json` | `model_verification.json` (V01-V10 pass/fail with details), `model_verification_review.md` | `verify_model` **(G2)**: V01 structure, V02 formulas byte-identical, V03 only mapped inputs changed and written exactly, V04 mapping round-trip, V05 no error values, V06 model checks, V07 engine parity (`tools/parity.py`), V08 detected conventions and no hardcoding (`profile_workbook`), V09 trace invariants (`tools/invariants.py`), V10 every currency input mapped from a local source |

### Stage 2: report regeneration

| # | Agent | Inputs | Outputs | Deterministic tools called |
|---|-------|--------|---------|----------------------------|
| 5 | **Report Profiler** | global report `.docx`, `model_profile.json` | `report_profile.json`: section tree, tables, every numeric token with location, and a candidate link to a model name | `docx_extract` (paragraphs, tables, runs, numeric tokens via the verifier's regex), `match_numbers` (numeric token ↔ recalculated global cell at displayed precision) |
| 6 | **Claims Analyst** | `report_profile.json`, recalculated global and adapted models, `mapping_spec.json` | `claims_register.json`: each claim typed (`numeric`, `threshold_comparison`, `ranking`, `jurisdiction_specific`, `external_assertion_untraceable`, `scope_statement`), its numeric dependencies, the tool-evaluated truth value under the adapted model, and an action (`rerender` / `reword` / `remove` / `human_review`) | `evaluate_claim` (comparisons, rankings and sign tests run on cell values), `scenario_runner` (`write_named` + `recalc` per scenario) |
| 7 | **Report Writer** | `claims_register.json`, `report_profile.json`, local HTA context (agency, threshold wording) | `report_template.docx` with `{{name|fmt}}` placeholders and no literal numerals; final `report_KR.docx` + `report_KR.provenance.json` | `render_report` (fills placeholders from recalculated cells, writes provenance) |
| 8 | **Report Verifier** | `report_KR.docx`, provenance, recalculated adapted model, `claims_register.json` | `report_verification.json` | `trace_numbers` (numerals match provenance **in document order** and each matches its cell at displayed precision; logic in `tests/test_fixtures_report_and_kr.py`), `rounding.check_derived` **(G0.5)** on every displayed difference and ratio (footnote required on `pass_with_footnote`), `evaluate_claim` re-run on the final text, `jurisdiction_lint` (residual UK terms: NICE, NHS, PSS, PAS, eMIT, PSSRU, £), retained-input tags present for every `retain_tagged` gap |

Human sign-off points: approve `mapping_spec.json` and `gap_register.yaml` (after agent 2),
resolve every open `block` gap (only a human can), accept `model_verification.json` (after
agent 4), and resolve every `human_review` claim (after agent 6) before the Report Writer
runs.

### Gap register

Every model input that the local data do not supply, or supply only in part, gets an
entry in `gap_register.yaml` (schema: `schemas/gap_register.schema.yaml`; KR answer key:
`fixtures/gap_register_KR.yaml`).

| Field | Values | Meaning |
|-------|--------|---------|
| `class` | `non_transferable` | depends on the local health system (unit costs, resource use, prices); global value must not be used |
| | `transferable` | expected to hold across settings (e.g. trial efficacy); global value may be retained |
| | `partial` | structure transfers, calibration is local (e.g. life table format, population norms) |
| `handling` | `block` | pipeline stops until a human resolves the gap with local evidence or an approved method change |
| | `retain_tagged` | keep global value; Report Writer tags it as a retained global input |
| | `retain_flagged` | keep global value; flagged for human review and listed as a limitation |
| `escalation_options` | `obtain_local_data`, `cite_local_literature`, `approved_method_change`, `retain_with_scenario`, `expert_elicitation` | the legitimate ways out; `prohibited_options` lists tempting illegitimate ones (e.g. FX conversion of a UK cost) |
| `decided_by` | `{kind: agent \| human, role}` | who classified the gap; a `resolution` must be `kind: human` |

Allowed class → handling: non_transferable → block; transferable → retain_tagged or
retain_flagged; partial → retain_flagged or block. `retained_source` is a list of model names
or item_ids. Life-table conversions are mapped inputs with a partial / retain_flagged gap
entry. Free text holds no numerals (R7) and registers use no YAML anchors (R8). The gate (`python -m tools.gap_register
<file>`) exits 0 (proceed), 1 (invalid register) or 2 (an open `block` gap). In the KR
fixture, the missing terminal care cost (`GAP-001`, `KR-C11`) blocks the pipeline.

### Deterministic tool contracts (portable, no Claude runtime)

Every tool is a pure function over files with a CLI entry point, JSON in and JSON out.
Python is the reference implementation; the R and VBA columns state the equivalent so the
pipeline can run where only one of them is available.

| Tool | Contract | Python (reference) | R equivalent | VBA equivalent |
|------|----------|--------------------|--------------|----------------|
| `recalc` **(G0)** | `recalc(src.xlsx, out_dir) -> out.xlsx` | `tools/recalc.py` (LibreOffice headless) | `system2("soffice", ...)` with same profile | `Application.CalculateFull` + `SaveCopyAs` |
| `workbook_io` **(G0)** | `list_names`, `read_named`, `write_named` (refuses formula cells) | `tools/workbook_io.py` (openpyxl) | `openxlsx2::wb_get_named_regions`, `wb_add_data` | `ThisWorkbook.Names(n).RefersToRange.Value` |
| `partsa_engine` **(G0.5)** | `run_model(inputs: dict, conventions) -> results`; `check_conventions` refuses anything not implemented | `tools/partsa_engine.py` (numpy, PyYAML) | ~150 lines of base R, same conventions | not needed (the workbook is the VBA-side model) |
| `gap_register` **(G0.5)** | `validate(register) -> errors`; `gate(register) -> blocked, blocking ids`; CLI exit 0/1/2 | `tools/gap_register.py` (PyYAML; minimal JSON Schema subset, no third-party validator) | `yaml` + `jsonvalidate` | parse the JSON form of the register |
| `rounding` **(G0.5)** | `check_derived(op, operands, result) -> pass / pass_with_footnote / fail / indeterminate` | `tools/rounding.py` (exact `Fraction` interval arithmetic) | same four-corner arithmetic | `Decimal`/`Currency` arithmetic |
| `profile_workbook` **(G1)** | `profile(xlsx, conventions) -> model_profile.json` | `tools/profile_workbook.py` (R1C1 region compression; no recalculation) | `tidyxl` cells + formulas | walk `UsedRange.FormulaR1C1` |
| `read_local_inputs` **(G1)** | `read_local_inputs(xlsx) -> {item_id: value, unit, sheet, cell}` incl. vector items | `tools/read_local_inputs.py` | `readxl` | loop `UsedRange` |
| `apply_mapping` **(G1)** | `mapping_spec.json` + local inputs + gap register → errors (dry run) or overrides + provenance; whitelist `copy`, `per_period_to_per_week`, `duration_to_doses` (rule declared), `mx_to_qx` (method and open band declared), `retain_global` (gap_id or basis); CLI exit 0/1/2 | `tools/apply_mapping.py` (exact `Fraction` arithmetic; constants from `tools/constants_registry.yaml` or model cells) | same operations | same operations |
| `build_run` **(G2)** | `build_run(spec, out_dir, scenarios) -> run_log`; CLI exit 0 built / 1 invalid / 2 blocked | `tools/build_run.py` | same steps via `openxlsx2` + `system2(soffice)` | write names, `CalculateFull`, `SaveCopyAs` |
| `verify_model` **(G2)** | `verify(run_dir, spec) -> model_verification.json`; CLI exit 0/1 | `tools/verify_model.py` (+ `parity.py`, `invariants.py`) | same checks | formula-by-formula compare of two workbooks; parity needs the engine |
| `eval_mapping` **(G1)** | candidate spec vs answer key → agreement, critical findings (filled gap, wrongly mapped retained input, missing input) | `tools/eval_mapping.py` | n/a | n/a |
| `trace_numbers` | docx + provenance → list of untraced or mismatched numerals | logic in tests (G0); to be extracted | `officer::docx_summary` + regex | `Document.Range.Find` with wildcards |
| `evaluate_claim` | claim JSON + values → bool / ranking | planned | planned | planned |
| `render_report` | template.docx + values + format map → docx + provenance | planned (pattern in `scripts/build_global_report_uk.py`) | `officer` | Word mail-merge style field replace |

## Convention declarations

Each model ships a `<model>.conventions.yaml` that states, in a fixed vocabulary, the
choices a reviewer would otherwise have to reverse-engineer from formulas. The engine
(`check_conventions`) refuses any value it does not implement, and the Model Verifier
checks the declaration against the formulas (`tests/test_conventions.py`). Changing a
convention means changing the workbook generator, the engine and the YAML together.

| Key | Fixture A (`global_model.xlsx`) | Fixture B (`global_model_B.xlsx`) |
|-----|------------------------------------------|---------------------------------|
| `discounting.method` | `mid_cycle_continuous`: DF = (1+r)^-t, t in years, continuous in time | `annual_step`: every cycle starting in model year k gets DF = (1+r)^-k, k = INT(cycle start in years); year 1 undiscounted |
| `discounting.timing` | state costs, one-off event costs and outcomes at the cycle mid-point; dosing costs at cycle start (time of dose); AE at baseline undiscounted | all streams `model_year`; AE at baseline undiscounted |
| `half_cycle_correction` | trapezoidal on state membership; applied to PF/PD state costs, LYs, QALYs; **not** to drug, administration, terminal care, subsequent therapy or AE | same as A |
| `dosing` | costs only in dosing weeks, ToT (capped by OS) at cycle start, no HCC; stopping rule by dose count; RDI on drug cost after vial rounding; exact expected vials for mg/kg under a lognormal weight distribution, no vial sharing | |
| `one_off_incidence` | deaths = S_OS(t) − S_OS(t+1); progressions = (PF(t) − PF(t+1)) × (1 − share of PFS events that are deaths); subsequent therapy = share-weighted course cost per progression; terminal care per death | |
| `general_population_mortality` | per-cycle hazard max on PFS and OS: S(t+1) = S(t) × min(S_param ratio, S_gpm ratio); qx by single age at cycle start; sex-specific survival weighted by proportion male | |
| `utilities` | multiplicative age adjustment gpu(age at mid-cycle)/gpu(baseline age), quadratic in age plus sex term; AE QALY loss not age-adjusted | |

Fixture B is generated by the same script (`build_global_model.py B`) and differs from A
only in the three discount-factor columns (enforced by `tests/test_fixture_b.py`), so the
Model Profiler and Verifier are tested on a model whose conventions differ in exactly one
declared way. Base-case ICER: A £28,270.86, B £28,278.66 per QALY.

## Model conventions (Fixture A summary)

- Three states: PF = MIN(S_PFS, S_OS); PD = S_OS − PF; Dead = 1 − S_OS, after the
  general-population cap. ToT = MIN(S_ToT, S_OS), so treatment beyond progression is allowed.
- Weibull (AFT), time in months: `S(t) = EXP(-((t/scale)^shape))`, for PFS, OS and ToT.
- Weekly cycles (`cycle_length_days` = 7, `days_per_year` = 365.25); lifetime horizon;
  `n_cycles = ROUND(horizon*days_per_year/cycle_days)`.
- Stopping rules are dose counts (`*_max_doses`): Drug A 35 doses Q3W, Drug B 6 doses Q3W.
- Not modelled: vial sharing, treatment effect of subsequent therapies, time-varying share
  of deaths among PFS events, age-adjusted AE disutility.

## Known traps (encode in tools, not in prompts)

- **Unary minus precedence.** In Excel and LibreOffice, `-x^k` evaluates as `(-x)^k`, the
  opposite of Python. `EXP(-(t/s)^k)` returns `#NUM!`; write `EXP(-((t/s)^k))`.
- LibreOffice does not recalculate OOXML on load by default; `tools/recalc.py` forces it.
  A test asserts that the source fixture has no cached results, so a stale cache cannot
  pass for a recalculation.
- Run concurrent LibreOffice instances with separate `-env:UserInstallation` profiles
  (handled by `recalc`).
- Treat-to-progression is represented as `*_max_doses` ≥ cycles / interval (e.g. 696), not blank.
- **Lookups past the horizon.** The trace has a fixed 2,088 rows; rows beyond `n_cycles` are
  masked but still calculated. A life-table `MATCH` there returns `#N/A` for older cohorts and
  poisons every `SUMPRODUCT`. Lookups are guarded by the horizon; coverage within the horizon is
  a model check (`check_life_table_ok`), never silently extended.
- **Cancellation in `LN(1+x)`.** For SD/mean below about 1e-8 the lognormal variance is
  exactly 0 in double precision. Workbook and engine both fall back to vials at the mean
  weight; the engine deliberately mirrors the workbook arithmetic (no `log1p`).
- **The mortality cap is usually immaterial** for Weibull extrapolations in a cohort aged
  about 60: in Fixture A it binds only from age 96 (0.02% alive). Tests exercise it with a
  perturbed older, long-tail case where it changes life years by more than 1%. Do not tune
  curves to make it matter in the base case.
- **Rounded displays do not recompute exactly.** 24,622 / 0.869 = 28,334 but the ICER from
  unrounded cells is 28,321. `tools/rounding.py` decides whether the display is explainable
  by rounding (pass with footnote) or is an error (fail).
- **Year boundaries in floating point.** `1461*(7/365.25)` is 27.999999999999996, so a naive
  floor puts the cycle that starts exactly at year 28 in year 27 (LibreOffice's `INT` snaps
  it to 28, Python's `floor` does not). Compute model years as `INT(cycle*days/days_per_year)`
  (multiply before divide); both sides then agree exactly.
- **openpyxl drops the 17th significant digit** (`'%.16g'`), so 241478.43942505133 was written
  as 241478.4394250513 and the written model differed from the computed override by one ULP.
  `write_named` saves with exact `repr` floats (`workbook_io.exact_floats`); V03 compares exactly.
- **Answer keys leak through context.** An agent definition that points at an answer key, or a
  CLAUDE.md that lists fixture traps, invalidates an evaluation. Agent runs for scoring use a
  blind workspace without answer keys, decision logs, fixture generators or tests.
- The traceability check matches numerals to provenance in document order; matching as a set
  let a stray numeral hide behind an identical traced one (found in Gate 0.5).

## Repository layout

```
CLAUDE.md                       this file
tools/                          deterministic tools (portable; no Claude runtime)
  recalc.py                     LibreOffice headless recalculation
  workbook_io.py                read/write defined names (cells and 1-D ranges)
  partsa_engine.py              independent Python PartSA (verification oracle) + convention check
  gap_register.py               gap register validation and pipeline gate
  rounding.py                   rounding-interval verifier for displayed derived values
schemas/gap_register.schema.yaml
scripts/                        fixture generators (deterministic, re-runnable)
  synthetic_data.py             synthetic life tables (UK-like qx, KR-like mx)
  build_global_model.py         -> fixtures/global_model.xlsx
  build_adaptation_input_kr.py  -> fixtures/adaptation_input_KR.xlsx
  build_global_report_uk.py     -> fixtures/global_report_UK.docx + .provenance.json
  rebaseline.py                 -> fixtures/baseline.json (run deliberately)
tools/ (Gate 1-2)
  profile_workbook.py, read_local_inputs.py, apply_mapping.py, eval_mapping.py
  build_run.py, verify_model.py, parity.py, invariants.py
schemas/mapping_spec.schema.yaml
  constants_registry.yaml       versioned unit constants and unit dimensions
.claude/agents/                 model-profiler.md, input-mapper.md, builder-runner.md, model-verifier.md
docs/decisions.md               decision log (provisional defaults flagged)
fixtures/
  global_model.xlsx, global_model.conventions.yaml   Fixture A
  global_model_B.xlsx, global_model_B.conventions.yaml   Fixture B (annual-step)
  mapping_spec_KR.json          expected Input Mapper output (answer key)
  adaptation_input_KR.xlsx, gap_register_KR.yaml     KR inputs and expected gap register
  global_report_UK.docx, global_report_UK.provenance.json
  baseline.json                 recorded base case and history
tests/                          pytest suite (LibreOffice required for most tests)
```

## Commands

```bash
pip install -r requirements.txt          # plus LibreOffice: apt-get install libreoffice-calc libreoffice-writer
python scripts/build_global_model.py     # 1. model A (must run first)
python scripts/build_global_model.py B   #    model B
python scripts/build_adaptation_input_kr.py
python scripts/build_global_report_uk.py # 2. report (recalcs the model and 8 scenarios, ~1.5 min)
python scripts/rebaseline.py <label>     # 3. only after an intended model change
python -m tools.gap_register fixtures/gap_register_KR.yaml   # exit 2: GAP-001 blocks
python -m tools.profile_workbook fixtures/global_model.xlsx --conventions fixtures/global_model.conventions.yaml
python -m tools.apply_mapping fixtures/mapping_spec_KR.json  # dry run; exit 2: blocked by GAP-001
python -m tools.eval_mapping <candidate.json> fixtures/mapping_spec_KR.json
python -m tools.build_run fixtures/mapping_spec_KR.json runs/kr   # exit 2: blocked by GAP-001, nothing built
python -m tools.verify_model <run_dir> <spec.json>
python -m pytest -q                      # ~3-4 min; recalcs via LibreOffice
```

Regenerate the report whenever the model generator changes; the provenance tests fail if
they drift apart. The baseline test fails on any change to the base case; re-baseline only
when the change is intended, and say so in the PR.

## Fixture notes for later gates

- `adaptation_input_KR.xlsx` is intentionally **not** shaped like the model's inputs:
  list price per vial (UK input is a net PAS price); mg/kg dose with KR weight mean/SD;
  reimbursed maximum duration in **years** (model uses a dose count); monthly (30.4375-day)
  state costs; life table as **mx** (not qx) ending at an open **100+** band (model needs
  ages to 110); subsequent-therapy categories renamed; missing terminal care cost
  (`KR-C11`), AE disutility (`KR-U03`), population utility norms (`KR-U04`) and proportion
  male (`KR-P03`); exchange rate and co-payment rate marked informational only.
- `gap_register_KR.yaml` and `mapping_spec_KR.json` are the expected Input Mapper outputs
  (81 model inputs: 34 mapped, 46 retained, 1 gap; D13 classifications). `GAP-001` (terminal care) is
  `non_transferable` / `block` and stops the pipeline; `apply_mapping` refuses to produce
  overrides until a human resolves it. Tests simulate that resolution with a test-only
  value to smoke-test the adapted model; that number is not a fixture.
- `global_report_UK.provenance.json` is the answer key for the Report Profiler and Claims
  Analyst: 184 traced numbers (base case plus 8 scenarios) and 12 typed claims, including
  one deliberately untraceable external assertion (medians within KM CIs), one scope
  statement (PSA not reported), one magnitude judgement (cap effect negligible) and one
  rounding disclosure.
- `PSA_Placeholder` documents the intended VBA macro (seed, distributions, Cholesky on
  log-Weibull parameters, output table). It is empty, and the workbook contains no macros.

## Conventions for contributors (human or agent)

- Never hand-edit fixtures; change the generator and regenerate.
- Calculation sheets are formula-only (enforced by tests). Inputs live only on `Inputs_*`
  sheets as single-cell defined names.
- Do not commit recalculated copies; they are produced in temporary directories.
