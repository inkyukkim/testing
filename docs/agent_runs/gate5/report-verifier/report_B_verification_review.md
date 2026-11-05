# Report Verifier review: report_B.docx

Command: `python -m tools.verify_report reports/report_B.docx runs/kr_test approved/claims_register.json approved_test_resolved/gap_register_resolved.yaml`
Exit code: 1 (overall fail, draft). Output: `reports/report_B_verification.json`.

- R01 trace: FAIL. At trace position for provenance N009 (`res_icer`, Results sheet) the displayed ICER does not equal the provenance display. A numeral in the document has no traceable source cell; this breaks the core design principle.
- R02 rounding: pass.
- R03 claims: pass.
- R04 jurisdiction: FAIL. Block in section "3. Methods" (discounting sentence) cites the NICE reference case outside References; the Korean report must cite the local guideline.
- R05 retained: FAIL. `prop_male` (GAP-005, retain_flagged) is missing from the list of retained global inputs, so a flagged limitation is undisclosed.
- R06 status: pass (marked DRAFT).
- R07 currency: pass.

## Diagnosis

The provenance manifest of report_B is identical in its numbers to report_A's, but the docx differs from report_A in exactly the three places above. render_report cannot produce such output from the same template and inputs, so report_B appears to have been edited by hand after rendering (an altered ICER figure, a reworded discounting citation, a deleted retained-input line). Post-render edits are not allowed.

## Who must act

- Report Writer: discard report_B, do not patch it; re-render from the approved template and sidecar with `render_report` (fixes R01, R04, R05). If the NICE wording or the missing line originates in the template, correct the template directives, not the rendered docx.
- Process owner / HEOR lead: establish how a rendered report was modified outside the tool.

Draft open items (same banner as report_A): C04, C05, C17, C18, C19, C20 open human reviews (Claims Analyst / human reviewers); GAP-001 test-only resolution (option E1, evidence KR-C11 test-only) still needs a real human resolution, then Builder/Runner rebuild.

## Recommendation

REJECT.
