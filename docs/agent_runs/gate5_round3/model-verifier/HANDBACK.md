I verified both runs and wrote a review for each in its run directory. Recommendation: **accept run_A, reject run_B.**

**run_A**
- Command: `python -m tools.verify_model runs/run_A approved_test_resolved/mapping_spec_resolved.json`
- Exit code: 0. `runs/run_A/model_verification.json` has `overall: pass`.
- Checks: V01 structure, V02 formulas, V03 inputs_only, V04 round_trip, V05 recalc_clean, V06 model_checks, V07 parity, V08 conventions, V09 invariants and V10 currency all PASS.
- Recommendation: **ACCEPT**, because every check passes.
- Review: `/home/user/testing/model-verifier/runs/run_A/model_verification_review.md`

**run_B**
- Command: `python -m tools.verify_model runs/run_B approved_test_resolved/mapping_spec_resolved.json`
- Exit code: 1. `runs/run_B/model_verification.json` has `overall: fail`.
- Checks: V01, V04, V05, V06, V07, V09 and V10 PASS; V02, V03 and V08 FAIL.
- What each failure means (the Builder/Runner must act on all three):
  - **V02 FAIL** (`Trace_Int!AD200: formula changed`): a formula in the intervention trace no longer matches the global model. The results are not comparable to the global submission, and the approved spec does not authorise the change.
  - **V03 FAIL** (`int_os_scale: written value differs from override`): the workbook holds a different value from the one in `overrides.json` for this GAP-006 `retain_tagged` survival parameter. The overall survival (OS) curve in use was approved by neither the spec nor the gap register.
  - **V08 FAIL** (`literal_in_formula`, region `Trace_Int!AD200`): the changed formula has a typed-in number with no source cell. It has the same cause as V02.
- V07 parity passing does not make up for these failures.
- Recommendation: **REJECT**, since there is no partial acceptance. The Builder/Runner must rebuild with `tools.build_run` from the approved spec and resubmit. No change to the spec, gap register or global model is needed.
- Review: `/home/user/testing/model-verifier/runs/run_B/model_verification_review.md`

**Not covered by the checks (listed in both reviews)**
- The gap register gate (`python -m tools.gap_register`) exited 0, and GAP-001 (`handling: block`) has `status: resolved`.
- Global inputs kept and flagged for human review (`retain_flagged`): GAP-002 (AE QALY losses), GAP-003 (the `gpu_*` coefficients), GAP-004 (life-table items `KR-L01` and `KR-L02`) and GAP-005 (`prop_male`, `baseline_age`).
- GAP-006 (`retain_tagged`): the retained survival and RDI parameters must be tagged in the report.
- Spec items kept with `basis: structural_setting`: `cycle_length_days`, `days_per_year`, `lifetime_check_tol`, `use_gpm_cap`, `use_age_util_adj`, `psa_seed`, `psa_iterations`, `time_horizon_years` and `lt_age`.
- Dosing items kept with `basis: confirmed_by_local_text`: the checks do not test whether the local text supports them.

I did not modify any workbook, the spec, the register, or anything under fixtures/, tools/ or schemas/. I created no scratch files.
