# Verification review: reports/report_B.docx

Command: `python -m tools.verify_report reports/report_B.docx runs/kr_test approved/claims_register.json approved_test_resolved/gap_register_resolved.yaml`
Exit code: 1 (`FAIL (draft)`); results in `reports/report_B_verification.json`.

- R01 trace: FAIL - numeral at token position 8 (provenance N009, name `res_icer`, section 1. Executive summary) does not match its provenance `display`. The base-case ICER shown in the executive summary is not the rendered value: a hand-edited/rounded number with no traceable source cell. Acts: Report Writer (restore the placeholder and re-render; never type numerals).
- R02 rounding: PASS
- R03 claims: PASS
- R04 jurisdiction: FAIL - block 29 (3. Methods) says the discount rates follow the "NICE reference case". This is a UK term in a Korean submission and misattributes the discounting basis (the local guideline). Acts: Report Writer (restore the local-guideline wording in the template/sidecar and re-render).
- R05 retained: FAIL - `prop_male` (GAP-005) is a retained global input but is missing from the report's list of retained inputs in 6. Discussion; the disclosure of retained/flagged inputs is incomplete. Acts: Report Writer (re-render so the retained-input list is generated in full from the gap register).
- R06 status: PASS
- R07 currency: PASS

No failure points to the model run or claims register (R02, R03 pass); Builder/Runner and Claims Analyst need not act. The pattern (one numeral, one phrase, one list item changed relative to a clean render) suggests post-render manual editing of the docx.

## Open items (draft: provenance `draft: true`, DRAFT banner)
- Open human reviews (provenance `blockers`): C04, C05, C17, C18, C19, C20.
- Gap resolution disclosed: GAP-001 resolved by HEOR lead (test), option E1, evidence KR-C11 (test-only value); TEST-ONLY per LOCAL_HTA_CONTEXT.md.

## Recommendation
Reject. Three checks fail (R01, R04, R05), and it is in any case a draft on a test-only gap resolution. Report Writer must re-render from the template without manual edits, then re-verify.
