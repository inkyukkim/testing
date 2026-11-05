# Model verification review: run_B

Command: `python -m tools.verify_model runs/run_B approved_test_resolved/mapping_spec_resolved.json`
Exit code: 1. Output: `runs/run_B/model_verification.json` (`overall: fail`).

## Checks
- V01 structure: PASS
- V02 formulas: FAIL (`Trace_Int!AD200: formula changed`)
- V03 inputs_only: FAIL (`int_os_scale: written value differs from override`)
- V04 round_trip: PASS
- V05 recalc_clean: PASS
- V06 model_checks: PASS
- V07 parity: PASS
- V08 conventions: FAIL (hardcoding, `kind: literal_in_formula`, region `Trace_Int!AD200`; see `checks[V08].details`)
- V09 invariants: PASS
- V10 currency: PASS

## Failures
- V02: a formula in the intervention trace (`Trace_Int!AD200`) is no longer the global model's formula. The adapted model's logic has been altered, so its results are not comparable to the global submission and the change is not traceable to the approved spec. Must act: Builder/Runner (the spec only authorises writing named inputs, not editing formulas).
- V03: the value written for `int_os_scale` does not equal the value in `runs/run_B/overrides.json`. This item is a GAP-006 `retain_tagged` global survival parameter, so the run is using an OS curve that neither the spec nor the gap register approved. Must act: Builder/Runner (rebuild from `overrides.json` via `tools.build_run`; do not hand-type values).
- V08: the changed formula at `Trace_Int!AD200` contains a hard-coded numeric literal, violating the model conventions and the principle that no number enters the model without a traceable source cell. Same root cause as V02. Must act: Builder/Runner.

V07 parity passing does not offset these failures: a single-cell edit and an altered parameter are exactly what V02/V03/V08 exist to catch.

## Recommendation
REJECT. Three checks fail (V02, V03, V08); there is no partial acceptance. Builder/Runner must rebuild run_B from the approved spec with `tools.build_run` and resubmit for verification. No change to the spec, gap register or global model is required.

## Not covered by the checks (for the human reviewer, after a clean rebuild)
- Retained global inputs with `handling: retain_flagged`: GAP-002 (`int_ae_qaly_loss`, `comp_ae_qaly_loss`), GAP-003 (`gpu_*` utility coefficients), GAP-004 (life-table items `KR-L01`, `KR-L02`), GAP-005 (`prop_male`, `baseline_age`).
- GAP-006 `retain_tagged` survival/RDI parameters (includes `int_os_scale`).
- `basis: structural_setting` items: `cycle_length_days`, `days_per_year`, `lifetime_check_tol`, `use_gpm_cap`, `use_age_util_adj`, `psa_seed`, `psa_iterations`, `time_horizon_years`, `lt_age`.
- `basis: confirmed_by_local_text` dosing items.
