# Report Verifier review: report_A.docx

Command: `python -m tools.verify_report reports/report_A.docx runs/kr_test approved/claims_register.json approved_test_resolved/gap_register_resolved.yaml`
Exit code: 0 (overall pass, draft). Output: `reports/report_A_verification.json`.

- R01 trace: pass. Every numeral matches its provenance entry in document order and the current run cells.
- R02 rounding: pass. Rounding intervals hold and the rounding footnote is present.
- R03 claims: pass. Claim choices re-evaluated; rerender/regenerate coverage complete; no removed claim rendered.
- R04 jurisdiction: pass. No source-jurisdiction terms outside References.
- R05 retained: pass. Every retained/flagged gap target is listed.
- R06 status: pass. Correctly marked DRAFT (provenance `draft: true`).
- R07 currency: pass. Local currency symbol used.

## Draft status (not a final report)

Open items from the DRAFT banner (provenance `blockers`): C04, C05, C17, C18, C19, C20, each an open human review. Owner: human reviewers via the Claims Analyst (claims register must become ready before a final render).

Gap resolution disclosed: GAP-001 resolved by HEOR lead (test), option E1, evidence KR-C11 marked test-only. This is a TEST-ONLY resolution (LOCAL_HTA_CONTEXT); GAP-001 remains open in the real pipeline. A human must resolve it with real local evidence, after which the Builder/Runner rebuilds and the Report Writer re-renders.

Observation (not a check failure): provenance `template` points to a path outside this workspace; the template itself was not inspected here.

## Recommendation

Technically consistent draft. Do NOT accept for submission: it is a draft built on a test-only gap resolution with six open human reviews. Acceptable only as an internal review draft.
