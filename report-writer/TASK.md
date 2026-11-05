You are acting as the Report Writer agent of a health-economic model adaptation pipeline. Work ONLY
inside this directory; do not read, list, search or write anything outside it, and do not use git
(put any scripts or scratch files under work/):

{WS}

cd into it in every Bash call (tools resolve paths relative to it).

Read PRINCIPLES.md, INSTRUCTIONS.md and LOCAL_HTA_CONTEXT.md, then follow INSTRUCTIONS.md exactly. Read
the docstrings of tools/render_report.py and tools/verify_report.py and tools/formats.yaml.

Inputs: the global report fixtures/global_report_UK.docx (with work/report_extract.json and
work/report_profile.json); the approved claims register approved/claims_register.json; the gap register
approved_test_resolved/gap_register_resolved.yaml; the Builder/Runner run directory runs/kr_test (TEST-ONLY
resolution, so the report can only be a draft); local inputs fixtures/adaptation_input_KR.xlsx (for source
descriptions only).

Outputs: work/report_template_KR.docx and work/report_template_KR.sidecar.yaml, written with python-docx from a
script you write in work/. Render a draft to work/report_KR.docx with tools/render_report.py --draft and verify
it with tools/verify_report.py. Iterate on the template until every verifier check passes. Cover the global
report's sections adapted for Korea.

Hard rules: no numerals in the template body; never edit the rendered .docx by hand; do not modify anything
under fixtures/, tools/, schemas/, approved/, approved_test_resolved/ or runs/.

Reply in under 400 words: the final render and verify exit codes with the status of each check, how many
numbers the draft contains (counted by a script from the provenance file), which claims you used and how, and
anything in the tools or instructions that got in your way.

In your final reply, never restate numbers from files in prose: quote tool output or counts
produced by a script, and cite names, ids and file fields instead.
