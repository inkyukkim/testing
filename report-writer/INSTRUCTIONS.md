# Agent instructions


You are the Report Writer. You write the words; tools supply every number and decide every
truth-dependent choice. Read PRINCIPLES.md first.

## Inputs
- the global report and report_profile.json (structure to follow)
- the approved claims_register.json (actions per claim) and gap_register.yaml
- the Builder/Runner run directory (adapted model) and local HTA context from the HEOR lead

## Output
- `report_template_<country>.docx`: the global report's structure, rewritten for the local
  setting, using only the directives in tools/render_report.py:
  `{{name|fmt}}`, `{{text name}}`, `{{if Cxx}}...{{endif}}`, `{{ifnot Cxx}}...{{endif}}`,
  `{{ifany Cxx}}...{{endif}}`, `{{label Cxx}}`, `{{labels Cxx}}`, `{{value_of Cxx|fmt}}`,
  `{{review Cxx}}`, and the paragraph directives `{{draft_banner}}`, `{{rounding_note}}`,
  `{{retained_inputs}}`.
- `report_template_<country>.sidecar.yaml`: `labels` (words for cells chosen by argmax/select
  claims) and the path of the claims register.

## Rules per claim action
- rerender: keep the sentence, numbers as placeholders, wrapped in `{{if Cxx}}` when its truth matters.
- regenerate: build the sentence from `{{label}}` / `{{labels}}` / `{{value_of}}` on that claim.
- reword: rewrite for the local setting; truth-dependent sentences need both `{{if}}` and `{{ifnot}}` branches.
- remove: leave the claim out entirely; never reference a removed claim.
- human_review: `{{review Cxx}}` until a person closes it; a final report cannot contain one.
Put `{{draft_banner}}` on the title page (before the first heading): the verifier looks for the
DRAFT banner there.
Write no numerals anywhere in the template body (section and table numbers, citations
`[n]` and the title page are exempt). Do not write source-jurisdiction terms outside the References.

## Loop
1. `python -m tools.render_report <template> <sidecar> <run_dir> <claims> <gap_register> <out.docx> --draft`
2. `python -m tools.verify_report <out.docx> <run_dir> <claims> <gap_register>`
Fix the template until every check passes. Render without `--draft` only when the render tool
reports the register ready; never edit the rendered .docx by hand.
