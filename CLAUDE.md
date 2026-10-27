# PartSA adaptation agents: prototype (Gate 0)

Prototype agent system that adapts a global oncology partitioned-survival (PartSA)
cost-effectiveness model to a local country and regenerates its technical report.
**Synthetic data only.** Nothing in this repository is real clinical, price or HTA data.

Status: **Gate 0.5** = architecture, synthetic fixtures with realistic structure (mortality
cap, age-adjusted utilities, ToT with dose-count stopping rule, vial wastage, RDI,
subsequent therapies), per-model convention declarations, gap register with a blocking
gate, rounding-interval verifier, deterministic recalculation and independent parity tests.
No agent is implemented yet.

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
| 1 | **Model Profiler** | global model `.xlsx` | `model_profile.json`: sheets, defined names with role (input / calc / result / check), units, PSA metadata, arm-block layout, conventions detected (HCC, discounting, survival form) | `workbook_io.list_names` **(G0)**, `workbook_io.read_named` **(G0)**, `profile_workbook` (formula dependency graph, hardcoded-constant scan) |
| 2 | **Input Mapper** | `model_profile.json`, `<model>.conventions.yaml`, local input `.xlsx` (e.g. `adaptation_input_KR.xlsx`) | `mapping_spec.json`: one entry per model input with `target_name`, `source` (`item_id` / model name / `retain_global`), whitelisted `operation`, rationale, and `status` (`mapped` / `retained` / `gap` / `rejected`); `gap_register.yaml` (every `gap` and `retained` entry classified, see below) | `read_local_inputs` (item_id → value, unit), `apply_mapping --dry-run` (validates every reference, every unit chain and every operation; computes nothing the agent sees as prose), `gap_register.validate` **(G0.5)** |
| 3 | **Builder/Runner** | global model, approved `mapping_spec.json`, approved `gap_register.yaml`, scenario list | `adapted_model.xlsx` (constants written into named input cells only), recalculated copy, `run_log.json` (tool versions, file hashes, overrides) | `gap_register.gate` **(G0.5)** first (exit 2 = stop), then `apply_mapping` → `workbook_io.write_named` **(G0)**, `recalc.recalc` **(G0)** |
| 4 | **Model Verifier** | global and adapted workbooks (recalculated), `mapping_spec.json`, conventions | `model_verification.json`: pass/fail per check | `partsa_engine.run_model` **(G0.5)** parity (tol 1e-6) with `check_conventions`, convention ↔ formula checks (pattern in `tests/test_conventions.py`), invariants (pattern in `tests/test_invariants.py`), `diff_workbooks` (only mapped input cells changed; formulas byte-identical), model checks (`check_*` cells), mapping round-trip |

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
retain_flagged; partial → retain_flagged or block. The gate (`python -m tools.gap_register
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
| `apply_mapping` | `mapping_spec.json` + local inputs → overrides JSON; operations limited to `copy`, `scale_by_cell`, `per_period_to_per_week` (factor from model cells), `duration_to_doses` (years → doses via interval; rounding rule declared), `mx_to_qx` (method declared, e.g. 1 − exp(−mx)), `extend_open_age_band`, `retain_global` | planned | planned | planned |
| `trace_numbers` | docx + provenance → list of untraced or mismatched numerals | logic in tests (G0); to be extracted | `officer::docx_summary` + regex | `Document.Range.Find` with wildcards |
| `evaluate_claim` | claim JSON + values → bool / ranking | planned | planned | planned |
| `render_report` | template.docx + values + format map → docx + provenance | planned (pattern in `scripts/build_global_report_uk.py`) | `officer` | Word mail-merge style field replace |

## Convention declarations

Each model ships a `<model>.conventions.yaml` that states, in a fixed vocabulary, the
choices a reviewer would otherwise have to reverse-engineer from formulas. The engine
(`check_conventions`) refuses any value it does not implement, and the Model Verifier
checks the declaration against the formulas (`tests/test_conventions.py`). Changing a
convention means changing the workbook generator, the engine and the YAML together.

| Key | Fixture A (`global_model.xlsx`, built) | Fixture B (Gate 1, to be built) |
|-----|------------------------------------------|---------------------------------|
| `discounting.method` | `mid_cycle_continuous`: DF = (1+r)^-t, t in years, continuous in time | `annual_step`: every cycle starting in model year k gets DF = (1+r)^-k, k = INT(cycle start in years); year 1 undiscounted |
| `discounting.timing` | state costs, one-off event costs and outcomes at the cycle mid-point; dosing costs at cycle start (time of dose); AE at baseline undiscounted | all streams `model_year`; AE at baseline undiscounted |
| `half_cycle_correction` | trapezoidal on state membership; applied to PF/PD state costs, LYs, QALYs; **not** to drug, administration, terminal care, subsequent therapy or AE | to be declared with Fixture B |
| `dosing` | costs only in dosing weeks, ToT (capped by OS) at cycle start, no HCC; stopping rule by dose count; RDI on drug cost after vial rounding; exact expected vials for mg/kg under a lognormal weight distribution, no vial sharing | |
| `one_off_incidence` | deaths = S_OS(t) − S_OS(t+1); progressions = (PF(t) − PF(t+1)) × (1 − share of PFS events that are deaths); subsequent therapy = share-weighted course cost per progression; terminal care per death | |
| `general_population_mortality` | per-cycle hazard max on PFS and OS: S(t+1) = S(t) × min(S_param ratio, S_gpm ratio); qx by single age at cycle start; sex-specific survival weighted by proportion male | |
| `utilities` | multiplicative age adjustment gpu(age at mid-cycle)/gpu(baseline age), quadratic in age plus sex term; AE QALY loss not age-adjusted | |

Fixture B exists so the Model Profiler and Model Verifier are tested on a model whose
conventions differ; the engine already implements `annual_step` (tested against a closed
form), so Fixture B parity is possible from the start.

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
fixtures/
  global_model.xlsx, global_model.conventions.yaml   Fixture A
  adaptation_input_KR.xlsx, gap_register_KR.yaml     KR inputs and expected gap register
  global_report_UK.docx, global_report_UK.provenance.json
  baseline.json                 recorded base case and history
tests/                          pytest suite (LibreOffice required for most tests)
```

## Commands

```bash
pip install -r requirements.txt          # plus LibreOffice: apt-get install libreoffice-calc libreoffice-writer
python scripts/build_global_model.py     # 1. model (must run first)
python scripts/build_adaptation_input_kr.py
python scripts/build_global_report_uk.py # 2. report (recalcs the model and 8 scenarios, ~1.5 min)
python scripts/rebaseline.py <label>     # 3. only after an intended model change
python -m tools.gap_register fixtures/gap_register_KR.yaml   # exit 2: GAP-001 blocks
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
- `gap_register_KR.yaml` is the expected Input Mapper output for those gaps; `GAP-001`
  (terminal care) is `non_transferable` / `block` and stops the pipeline.
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
