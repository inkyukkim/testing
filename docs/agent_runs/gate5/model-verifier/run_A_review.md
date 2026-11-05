# Model verification review: run_A

Command: `python -m tools.verify_model runs/run_A approved_test_resolved/mapping_spec_resolved.json`
Exit code: 0. `model_verification.json` `overall`: pass. `run_log.json` `status`: built.

| Check | Status |
|-------|--------|
| V01 structure | pass |
| V02 formulas | pass |
| V03 inputs_only | pass |
| V04 round_trip | pass |
| V05 recalc_clean | pass |
| V06 model_checks | pass |
| V07 parity | pass |
| V08 conventions | pass |
| V09 invariants | pass |
| V10 currency | pass |

No failures.

## Recommendation

Accept, subject to the human sign-off below. Every check passes.

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
