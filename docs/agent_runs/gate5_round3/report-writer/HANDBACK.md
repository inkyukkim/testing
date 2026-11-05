The draft Korean report renders and passes every verifier check. Both commands exited 0 on the final run. It is a draft only: six claims are still waiting for human review.

**Final run**
- Render (`--draft`): exit 0, `DRAFT: work/report_KR.docx (142 numbers)`
- Verify: exit 0
  - R01 trace PASS, R02 rounding PASS, R03 claims PASS, R04 jurisdiction PASS
  - R05 retained PASS, R06 status PASS, R07 currency PASS
  - `PASS (draft)`
- The draft banner lists open items C04, C05, C17, C18, C19 and C20 as open human reviews. It also lists the test-only resolution of GAP-001.

**Numbers in the draft** (counted by `work/count_numbers.py` from `work/report_KR.provenance.json`)
- `numbers in provenance: 142`
- `distinct source names: 114`
- `scenario-sourced: 0`
- `rounding_footnote: True`
- The template itself has zero literal numerals; `docx_extract` finds no tokens in it.

**Claims used, and how**
- **Reworded:**
  - C01, C06: perspective from `{{text perspective}}`, KR-S04 and the local guideline placeholder [1].
  - C08: kept as a methods citation alongside the local guideline.
  - C10, C11: Korean sources by item id; currency and price year as placeholders.
  - C12: Korean EQ-5D-5L value set, with GAP-002 and GAP-003 inputs flagged as retained.
  - C21: "reimbursement criteria (KR-C05)".
  - C02, C22: written with both `{{if}}` and `{{ifnot}}` branches against the single reference value `wtp_threshold`. No range is described.
- **Rerendered:**
  - C09: `{{if}}`/`{{ifnot}}` on the curve-crossing check.
  - C13: PSA scope sentence kept.
  - C14: via `{{rounding_note}}`; the tool kept the note.
- **Regenerated:**
  - C15: `{{label C15}}` and `{{value_of C15|money}}`.
  - C16: `{{ifany C16}}` and `{{labels C16}}`, with labels in the sidecar.
- **Removed:** C03 (lower bound) and C07 (PAS) are left out and never referenced. The scenario table (global Table 8) is dropped because there is no Korean scenario set.
- **Human review:** each of C04, C05, C17, C18, C19 and C20 has a `{{review}}` marker.
- **Retained inputs:** listed through `{{retained_inputs}}` in a new section 3.7.

**What got in the way**
- R03 counts C13 and C14 as rerender claims, but they have no expression and the template cannot state their truth. Using them in `{{if}}` would render "[pending]" in a draft, so they appear only as plain prose and the rounding note.
- `value_of` is not logged in `claims_used`; only `label` is, so C15's value directive is missing from that record.
- `run_log.json` has no scenarios, so C04 and C17–C19 can only stay as review markers.
- No model-verification output exists in `runs/kr_test`, so the draft makes no parity claim for the adapted model.
- The lifetime-check sentence has no claim in the register. I used the model's text check cells (`check_lifetime_ok` and the other checks) instead of asserting the result.
- The jurisdiction lint covers the title page, so the global "(United Kingdom)" title and version line had to be rewritten.

Files are in /home/user/testing/report-writer/work:
- report_template_KR.docx
- report_template_KR.sidecar.yaml
- build_template_KR.py
- report_KR.docx
- report_KR.provenance.json
- report_KR_verification.json
- count_numbers.py
