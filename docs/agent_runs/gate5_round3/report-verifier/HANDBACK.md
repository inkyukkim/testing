I ran the verifier on both reports and wrote a review next to each one. Report A passes every check but is only a draft. Report B fails three checks and should be rejected.

**Report A**
- Command: `python -m tools.verify_report reports/report_A.docx runs/kr_test approved/claims_register.json approved_test_resolved/gap_register_resolved.yaml`
- Exit code 0, output `PASS (draft)`.
- R01 trace, R02 rounding, R03 claims, R04 jurisdiction, R05 retained, R06 status and R07 currency all PASS.
- Its provenance file has `draft: true`. The DRAFT banner and the provenance `blockers` list six open human reviews: C04, C05, C17, C18, C19, C20.
- It discloses one gap resolution: GAP-001, resolved by "HEOR lead (test)" with option E1 and evidence KR-C11 (test-only value). LOCAL_HTA_CONTEXT.md says this resolution is for testing only.
- Reference [2] cites a NICE DSU technical support document. R04 did not flag it; the HEOR lead may want to confirm that is acceptable.
- **Recommendation: do not accept for submission.** Use it as an internal draft only, and re-render and re-verify once GAP-001 has real local evidence and the reviews are closed.

**Report B**
- Same command with `report_B.docx`. Exit code 1, output `FAIL (draft)`.
- **R01 trace FAIL:** the numeral at position 8 is provenance N009 (`res_icer`, 1. Executive summary). The verifier says: "report shows '₩32,462,800', provenance '₩32,462,855'". So the ICER in the executive summary has no traceable source cell. **Report Writer** must restore the placeholder and re-render.
- R02 rounding PASS.
- R03 claims PASS.
- **R04 jurisdiction FAIL:** "block 29 (3. Methods): NICE reference case". The discount rates are attributed to the UK reference case instead of the local guideline. **Report Writer** must fix the wording and re-render.
- **R05 retained FAIL:** "prop_male (GAP-005): not listed in the report". The list of retained global inputs in section 6 is incomplete. **Report Writer** must re-render the list in full from the gap register.
- R06 status PASS.
- R07 currency PASS.
- The Builder/Runner and Claims Analyst don't need to act.
- Report B has the same draft status, open reviews and test-only GAP-001 disclosure as Report A.
- Compared with Report A's text, only the three flagged passages differ, which points to the .docx being edited by hand after rendering.
- **Recommendation: reject.** Re-render without manual edits, then re-verify.

I did not change any report, provenance file, register, or anything in `runs/` or `tools/`.

Files are in /home/user/testing/report-verifier/reports:
- report_A_verification.json
- report_A_verification_review.md
- report_B_verification.json
- report_B_verification_review.md
