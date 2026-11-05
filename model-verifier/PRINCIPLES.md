# Principles (excerpt)

Workspace: this directory only. Paths in specs are relative to it.

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


### Gap register

Every model input that the local data do not supply, or supply only in part, gets an
entry in `gap_register.yaml` (schema: `schemas/gap_register.schema.yaml`).

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
<file>`) exits 0 (proceed), 1 (invalid register) or 2 (an open `block` gap).


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
| `docx_extract` **(G3)** | `extract(docx) -> {blocks, tokens}`; defines the structural-numeral exemption | `tools/docx_extract.py` | `officer::docx_summary` + regex | `Document.Range` walk |
| `match_numbers` **(G3)** | tokens + base and scenario values → candidates per numeral (unique / ambiguous / unmatched) | `tools/match_numbers.py` | same comparison | same comparison |
| `jurisdiction_lint` **(G3)** | blocks → hits from `tools/jurisdiction_terms.yaml` | `tools/jurisdiction_lint.py` | `stringr` | `InStr` loop |
| `scenario_runner` **(G3)** | model + scenarios YAML → values per scenario | `tools/scenario_runner.py` | as `build_run` | as `build_run` |
| `evaluate_claim` / `claims` **(G3)** | expression + contexts → true / false / pending / not_evaluable; register validation K1-K6 and readiness | `tools/evaluate_claim.py`, `tools/claims.py` | same language | same language |
| `render_report` **(G4)** | template + sidecar + run + claims + gap register → docx + provenance; CLI exit 0 / 1 invalid / 2 not ready | `tools/render_report.py` (+ `tools/formats.yaml`) | `officer` | Word field replace |
| `verify_report` **(G4)** | report + provenance + run + registers → R01-R07; CLI exit 0/1 | `tools/verify_report.py` | same checks | same checks |
