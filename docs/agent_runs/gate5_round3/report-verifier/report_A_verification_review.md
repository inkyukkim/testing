# Verification review: reports/report_A.docx

Command: `python -m tools.verify_report reports/report_A.docx runs/kr_test approved/claims_register.json approved_test_resolved/gap_register_resolved.yaml`
Exit code: 0 (`PASS (draft)`); results in `reports/report_A_verification.json`.

- R01 trace: PASS
- R02 rounding: PASS
- R03 claims: PASS
- R04 jurisdiction: PASS
- R05 retained: PASS
- R06 status: PASS
- R07 currency: PASS

## Open items (draft: provenance `draft: true`, DRAFT banner)
- Open human reviews (provenance `blockers`): C04, C05, C17, C18, C19, C20.
- Gap resolution disclosed: GAP-001 (terminal care cost) resolved by HEOR lead (test), option E1, evidence KR-C11 (test-only value). Per LOCAL_HTA_CONTEXT.md this resolution is TEST-ONLY; GAP-001 remains unresolved in the real pipeline.
- Note (not a check failure): reference [2] cites a NICE DSU TSD for survival methods; R04 did not flag it (citation, not a jurisdictional claim). HEOR lead may confirm that is acceptable.

## Recommendation
Do not accept for submission. All checks pass, but this is a draft built on a test-only GAP-001 resolution with six open human reviews. Acceptable as an internal draft only; re-render and re-verify once GAP-001 is resolved with real local evidence and the open reviews are closed.
