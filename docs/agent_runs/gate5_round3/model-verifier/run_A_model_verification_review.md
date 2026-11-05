# Model verification review: run_A

Command: `python -m tools.verify_model runs/run_A approved_test_resolved/mapping_spec_resolved.json`
Exit code: 0. Output: `runs/run_A/model_verification.json` (`overall: pass`).

## Checks
- V01 structure: PASS
- V02 formulas: PASS
- V03 inputs_only: PASS
- V04 round_trip: PASS
- V05 recalc_clean: PASS
- V06 model_checks: PASS
- V07 parity: PASS
- V08 conventions: PASS
- V09 invariants: PASS
- V10 currency: PASS

## Failures
None.

## Recommendation
ACCEPT. Every check V01-V10 passes (`model_verification.json` field `overall`).

## Not covered by the checks (for the human reviewer)
- Gap register `approved_test_resolved/gap_register_resolved.yaml` (gate exit 0; GAP-001 `handling: block` has `status: resolved`). Retained global inputs flagged for review (`handling: retain_flagged`, listed as limitations):
  - GAP-002 (partial): `int_ae_qaly_loss`, `comp_ae_qaly_loss`
  - GAP-003 (partial): `gpu_intercept`, `gpu_male`, `gpu_age`, `gpu_age2`
  - GAP-004 (partial): life-table items `KR-L01`, `KR-L02`
  - GAP-005 (transferable): `prop_male`, `baseline_age`
- GAP-006 (`retain_tagged`): global survival, correlation, first-PFS death and RDI parameters are retained and must be tagged by the Report Writer.
- Spec items retained with `basis: structural_setting`: `cycle_length_days`, `days_per_year`, `lifetime_check_tol`, `use_gpm_cap`, `use_age_util_adj`, `psa_seed`, `psa_iterations`, `time_horizon_years`, `lt_age`. A reviewer should confirm these suit the local setting (time horizon especially).
- Items retained with `basis: confirmed_by_local_text` (dosing and administration settings): checks confirm values were written, not that the local text supports them.
