# Model verification review: run_B

Command: `python -m tools.verify_model runs/run_B approved_test_resolved/mapping_spec_resolved.json`
Exit code: 1. `model_verification.json` `overall`: fail. `run_log.json` `status`: built.

| Check | Status |
|-------|--------|
| V01 structure | pass |
| V02 formulas | **fail** (`Trace_Int!AD200`: formula changed) |
| V03 inputs_only | **fail** (`int_os_scale`: written value differs from override) |
| V04 round_trip | pass |
| V05 recalc_clean | pass |
| V06 model_checks | pass |
| V07 parity | pass |
| V08 conventions | **fail** (hardcoding: `literal_in_formula` in `Trace_Int!AD200`) |
| V09 invariants | pass |
| V10 currency | pass |

## Failures

- **V02**: one trace formula in the intervention arm differs from the global model, so the
  adapted model no longer computes what the global model computes and its results are not
  comparable to the global submission.
- **V08**: the changed formula contains a hardcoded literal (see `checks[V08].details`). This is
  the same cell as V02; a constant typed into a calculation sheet breaks the rule that only
  named input cells change.
- **V03**: the value written to `int_os_scale` is not the value `apply_mapping` produced in
  `overrides.json`. The workbook carries a number with no traceable source. `int_os_scale` is
  a retained global input (GAP-006); `overrides.json` is identical to run_A's, so the
  difference was introduced in the workbook, not by the mapping.
- V07 parity and V06 still pass, which shows the edit is local enough that these checks
  alone would not catch it; V02, V03 and V08 are the controls that do.

Responsible agent: **Builder/Runner**. The approved spec is the same one run_A was built from,
and run_A passes every check, so the defect is in the build of run_B (the workbook was altered
after or outside `write_named`), not in the Input Mapper output or the global model. Rebuild
with `build_run` from the approved spec and re-verify; do not patch the workbook.

## Recommendation

**Reject.** Three checks fail; there is no partial acceptance.

## Not covered by the checks (reviewer attention)

- GAP-001 (`c_terminal`) is resolved with a test-only value (resolution `evidence` in the gap
  register). The build is a smoke test, not a submission-grade model.
- Retained global inputs flagged for human review (`retain_flagged`): GAP-002 (AE QALY loss),
  GAP-003 (population utility norms), GAP-004 (life table conversion, `lt_qx_male`,
  `lt_qx_female`), GAP-005 (`prop_male`, `baseline_age`). GAP-006 (efficacy, correlation, RDI)
  is `retain_tagged`.
- Structural settings retained with basis `structural_setting`: `cycle_length_days`,
  `days_per_year`, `lifetime_check_tol`, `use_gpm_cap`, `use_age_util_adj`, `psa_seed`,
  `psa_iterations`, `time_horizon_years`, `lt_age`. Confirm these suit the local HTA reference case.
- `run_log.json` `tools.git_commit` and `tools.git_dirty` are null, so the build cannot be tied
  to a code revision.
