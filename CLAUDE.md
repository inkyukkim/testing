# PartSA adaptation agents: prototype (Gate 0)

Prototype agent system that adapts a global oncology partitioned-survival (PartSA)
cost-effectiveness model to a local country and regenerates its technical report.
**Synthetic data only.** Nothing in this repository is real clinical, price or HTA data.

Status: **Gate 0** = architecture, synthetic fixtures, deterministic recalculation and
independent parity test. No agent is implemented yet.

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

- Linux, Python 3.11+ (`openpyxl`, `python-docx`, `numpy`, `pytest`), LibreOffice headless
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
| 2 | **Input Mapper** | `model_profile.json`, local input `.xlsx` (e.g. `adaptation_input_KR.xlsx`) | `mapping_spec.json`: one entry per model input with `target_name`, `source` (`item_id` / model name / `retain_global`), whitelisted `operation`, rationale, and `status` (`mapped` / `retained` / `gap` / `rejected`); gaps and judgement calls flagged for human sign-off | `read_local_inputs` (item_id → value, unit), `apply_mapping --dry-run` (validates every reference, every unit chain and every operation; computes nothing the agent sees as prose) |
| 3 | **Builder/Runner** | global model, approved `mapping_spec.json`, scenario list | `adapted_model.xlsx` (constants written into named input cells only), recalculated copy, `run_log.json` (tool versions, file hashes, overrides) | `apply_mapping` → `workbook_io.write_named` **(G0)**, `recalc.recalc` **(G0)** |
| 4 | **Model Verifier** | global and adapted workbooks (recalculated), `mapping_spec.json` | `model_verification.json`: pass/fail per check | `partsa_engine.run_model` **(G0)** parity (tol 1e-6), `diff_workbooks` (only mapped input cells changed; formulas byte-identical), model checks (`check_*` cells) **(G0)**, mapping round-trip (each written value recomputed from its source) |

### Stage 2: report regeneration

| # | Agent | Inputs | Outputs | Deterministic tools called |
|---|-------|--------|---------|----------------------------|
| 5 | **Report Profiler** | global report `.docx`, `model_profile.json` | `report_profile.json`: section tree, tables, every numeric token with location, and a candidate link to a model name | `docx_extract` (paragraphs, tables, runs, numeric tokens via the verifier's regex), `match_numbers` (numeric token ↔ recalculated global cell at displayed precision) |
| 6 | **Claims Analyst** | `report_profile.json`, recalculated global and adapted models, `mapping_spec.json` | `claims_register.json`: each claim typed (`numeric`, `threshold_comparison`, `ranking`, `jurisdiction_specific`, `external_assertion_untraceable`, `scope_statement`), its numeric dependencies, the tool-evaluated truth value under the adapted model, and an action (`rerender` / `reword` / `remove` / `human_review`) | `evaluate_claim` (comparisons, rankings and sign tests run on cell values), `scenario_runner` (`write_named` + `recalc` per scenario) |
| 7 | **Report Writer** | `claims_register.json`, `report_profile.json`, local HTA context (agency, threshold wording) | `report_template.docx` with `{{name|fmt}}` placeholders and no literal numerals; final `report_KR.docx` + `report_KR.provenance.json` | `render_report` (fills placeholders from recalculated cells, writes provenance) |
| 8 | **Report Verifier** | `report_KR.docx`, provenance, recalculated adapted model, `claims_register.json` | `report_verification.json` | `trace_numbers` (every numeral has provenance and matches its cell at displayed precision; logic in `tests/test_fixtures_report_and_kr.py` **(G0)**), `evaluate_claim` re-run on the final text, `jurisdiction_lint` (residual UK terms: NICE, NHS, PSS, PAS, eMIT, PSSRU, £) |

Human sign-off points: approve `mapping_spec.json` (after agent 2), accept
`model_verification.json` (after agent 4), and resolve every `human_review` claim (after
agent 6) before the Report Writer runs.

### Deterministic tool contracts (portable, no Claude runtime)

Every tool is a pure function over files with a CLI entry point, JSON in and JSON out.
Python is the reference implementation; the R and VBA columns state the equivalent so the
pipeline can run where only one of them is available.

| Tool | Contract | Python (reference) | R equivalent | VBA equivalent |
|------|----------|--------------------|--------------|----------------|
| `recalc` **(G0)** | `recalc(src.xlsx, out_dir) -> out.xlsx` | `tools/recalc.py` (LibreOffice headless) | `system2("soffice", ...)` with same profile | `Application.CalculateFull` + `SaveCopyAs` |
| `workbook_io` **(G0)** | `list_names`, `read_named`, `write_named` (refuses formula cells) | `tools/workbook_io.py` (openpyxl) | `openxlsx2::wb_get_named_regions`, `wb_add_data` | `ThisWorkbook.Names(n).RefersToRange.Value` |
| `partsa_engine` **(G0)** | `run_model(inputs: dict) -> results` | `tools/partsa_engine.py` (numpy) | ~60 lines of base R, same conventions | not needed (the workbook is the VBA-side model) |
| `apply_mapping` | `mapping_spec.json` + local inputs → overrides JSON; operations limited to `copy`, `scale_by_cell`, `per_vial_to_per_admin` (ceil(dose/vial) x price), `per_period_to_per_week` (factor from model cells), `retain_global` | planned | planned | planned |
| `trace_numbers` | docx + provenance → list of untraced or mismatched numerals | logic in tests (G0); to be extracted | `officer::docx_summary` + regex | `Document.Range.Find` with wildcards |
| `evaluate_claim` | claim JSON + values → bool / ranking | planned | planned | planned |
| `render_report` | template.docx + values + format map → docx + provenance | planned (pattern in `scripts/build_global_report_uk.py`) | `officer` | Word mail-merge style field replace |

## Model conventions (global fixture)

These are the conventions the Model Verifier's engine implements. Changing one means
changing both the workbook generator and `tools/partsa_engine.py`.

- Three states: PF = MIN(S_PFS, S_OS); PD = S_OS − PF; Dead = 1 − S_OS.
- Weibull (AFT), time in months: `S(t) = EXP(-((t/scale)^shape))`.
- Weekly cycles (`cycle_length_days` = 7, `days_per_year` = 365.25); lifetime horizon
  (`time_horizon_years`); `n_cycles = ROUND(horizon*days_per_year/cycle_days)`.
- Half-cycle correction: trapezoid on state membership at cycle boundaries.
- Discounting: per-cycle factor at the mid-point, `(1+r)^-((i+0.5)*cycle_years)`;
  separate rates for costs and outcomes.
- Treatment while PF and `cycle_start < max_tx_weeks`; per-administration costs spread
  evenly over each dosing interval (`cost * cycle_days / (7 * interval_weeks)`).
- Terminal care: one-off cost on deaths in each cycle (drop in S_OS), discounted.
- AEs: one-off cost and QALY loss at t = 0, undiscounted.
- Not modelled (deliberately, for Gate 0): background mortality cap, age-adjusted
  utilities, time-on-treatment curve, subsequent therapies.

## Known traps (encode in tools, not in prompts)

- **Unary minus precedence.** In Excel and LibreOffice, `-x^k` evaluates as `(-x)^k`, the
  opposite of Python. `EXP(-(t/s)^k)` returns `#NUM!`; write `EXP(-((t/s)^k))`.
- LibreOffice does not recalculate OOXML on load by default; `tools/recalc.py` forces it.
  A test asserts that the source fixture has no cached results, so a stale cache cannot
  pass for a recalculation.
- Run concurrent LibreOffice instances with separate `-env:UserInstallation` profiles
  (handled by `recalc`).
- Treat-to-progression is represented as `max_tx_weeks` ≥ horizon (e.g. 2088), not blank.

## Repository layout

```
CLAUDE.md                       this file
tools/                          deterministic tools (portable; no Claude runtime)
  recalc.py                     LibreOffice headless recalculation
  workbook_io.py                read/write defined names
  partsa_engine.py              independent Python PartSA (verification oracle)
scripts/                        fixture generators (deterministic, re-runnable)
  build_global_model.py         -> fixtures/global_model.xlsx
  build_adaptation_input_kr.py  -> fixtures/adaptation_input_KR.xlsx
  build_global_report_uk.py     -> fixtures/global_report_UK.docx + .provenance.json
fixtures/                       synthetic inputs for later gates
tests/                          pytest suite (LibreOffice required for most tests)
```

## Commands

```bash
pip install -r requirements.txt          # plus LibreOffice: apt-get install libreoffice-calc libreoffice-writer
python scripts/build_global_model.py     # 1. model (must run first)
python scripts/build_adaptation_input_kr.py
python scripts/build_global_report_uk.py # 2. report (recalcs the model and 5 scenarios, ~1 min)
python -m pytest -q                      # ~1 min; recalcs via LibreOffice
```

Regenerate the report whenever the model generator changes; the provenance tests fail if
they drift apart.

## Fixture notes for later gates

- `adaptation_input_KR.xlsx` is intentionally **not** shaped like the model's inputs:
  per-vial drug price plus dose and vial size; monthly (30.4375-day) health-state costs;
  maximum treatment duration in years; a missing terminal care cost (`KR-C11`); no local
  AE disutility (`KR-U03`); an exchange rate and co-payment rate marked informational only.
  These test whether the Input Mapper flags gaps rather than filling them.
- `global_report_UK.provenance.json` is the answer key for the Report Profiler and Claims
  Analyst: 130 traced numbers (base case plus 5 scenarios) and 10 typed claims, including
  one deliberately untraceable external assertion (medians within KM CIs) and one scope
  statement (PSA not reported).
- `PSA_Placeholder` documents the intended VBA macro (seed, distributions, Cholesky on
  log-Weibull parameters, output table). It is empty, and the workbook contains no macros.

## Conventions for contributors (human or agent)

- Never hand-edit fixtures; change the generator and regenerate.
- Calculation sheets are formula-only (enforced by tests). Inputs live only on `Inputs_*`
  sheets as single-cell defined names.
- Do not commit recalculated copies; they are produced in temporary directories.
