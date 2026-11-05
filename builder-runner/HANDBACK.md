I ran both specs as INSTRUCTIONS.md says. The approved spec is blocked on GAP-001 and the test-resolved spec built. Neither run can be reproduced from a commit, because both run logs record `tools.git_dirty: true`.

**1. Approved spec (`approved/mapping_spec.json`)**
- Command: `python -m tools.build_run approved/mapping_spec.json work/run_approved`
- Exit code: 2. `status: "blocked"`.
- Output: `BLOCKED: run_log at work/run_approved/run_log.json` and `BLOCKED: GAP-001`.
- The only entry in `blocking_gaps` is **GAP-001**. It covers target `c_terminal` (source item `KR-C11`, terminal care cost) and is `non_transferable` with handling `block`. Only a human can resolve it, using one of its escalation options (`obtain_local_data`, `cite_local_literature`, `approved_method_change`). I stopped there and did not edit the register, spec or local inputs.
- The log still records hashes and tool versions. `tools.git_commit` is set, and `tools.git_dirty: true` means it is not reproducible from that commit.

**2. Test-resolved spec (`approved_test_resolved/mapping_spec_resolved.json`)**
- Command: `python -m tools.build_run approved_test_resolved/mapping_spec_resolved.json work/run_test_resolved`
- Exit code: 0. Output: `BUILT: run_log at work/run_test_resolved/run_log.json`. `status: "built"`.
- Run log: `/home/user/testing/builder-runner/work/run_test_resolved/run_log.json`
- Input hashes I checked, all `inputs.*.sha256`:
  - `model`: `fixtures/global_model.xlsx`
  - `local_inputs`: `approved_test_resolved/adaptation_input_KR_resolved.xlsx`
  - `gap_register`: `approved_test_resolved/gap_register_resolved.yaml`
  - `spec`
  - `conventions`: `fixtures/global_model.conventions.yaml`
  - The `model` and `conventions` hashes are the same as in the approved run.
- Tool versions I checked: `tools.python`, `tools.openpyxl`, `tools.numpy`, `tools.libreoffice`, `tools.registry_version`.
- Outputs (`outputs.*.sha256`):
  - `adapted_model`: `work/run_test_resolved/adapted_model.xlsx`
  - `recalculated`: `work/run_test_resolved/recalc/adapted_model.xlsx`. Its note says LibreOffice puts timestamps in the file, so this hash identifies this run only.
  - `overrides`: `work/run_test_resolved/overrides.json`
- Results are in the run log's `base_case` field. I am not restating them.
- In this register, GAP-001 has `status: resolved` with `resolution.option_id: E1`. It was decided by a human with the role `HEOR lead (test)`. This output is test-only and should not be handed on as a delivery run.
- Not reproducible from a commit, because `tools.git_dirty: true`.

I did not open or edit any workbook, did not run the Model Verifier checks, and did not change anything under fixtures/, tools/, schemas/, approved/ or approved_test_resolved/.
