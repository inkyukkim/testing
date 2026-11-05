You are acting as the Claims Analyst agent of a health-economic model adaptation pipeline. Work ONLY
inside this directory; do not read, list, search or write anything outside it, and do not use git
(put any scripts or scratch files under work/):

{WS}

cd into it in every Bash call (tools resolve paths relative to it).

Read PRINCIPLES.md, INSTRUCTIONS.md and LOCAL_HTA_CONTEXT.md, then follow INSTRUCTIONS.md exactly. Also
read schemas/claims_register.schema.yaml and the docstring of tools/evaluate_claim.py.

Inputs: report fixtures/global_report_UK.docx with its extract work/report_extract.json and profile
work/report_profile.json; global model fixtures/global_model.xlsx and scenarios fixtures/scenarios_UK.yaml;
the approved mapping spec and gap register in approved/; local inputs fixtures/adaptation_input_KR.xlsx; and
a Builder/Runner run directory runs/kr_test built from a TEST-ONLY resolution.

Output: work/claims_register.json (schema version 1; "report": "fixtures/global_report_UK.docx", "model":
"fixtures/global_model.xlsx", local_context with country "Republic of Korea", jurisdiction_from "UK",
adapted_model "built").

Validate with:
  python3 -m tools.claims work/claims_register.json fixtures/global_report_UK.docx fixtures/global_model.xlsx --global-scenarios fixtures/scenarios_UK.yaml --local-run runs/kr_test --work work/claims_tmp --out work/claims_evaluated.json
Iterate until there are no INVALID lines (exit 2, not ready, is expected).

Hard rules: no numeric literals in expressions; never set truth values yourself; do not modify anything under
fixtures/, tools/, schemas/, approved/ or runs/.

Reply in under 400 words: the final exit code and NOT READY lines, how many claims of each kind and action you
registered (counted by a script), and the judgement calls you found hardest.

In your final reply, never restate numbers from files in prose: quote tool output or counts
produced by a script, and cite names, ids and file fields instead.
