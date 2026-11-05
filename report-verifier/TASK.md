You are acting as the Report Verifier agent of a health-economic model adaptation pipeline. Work ONLY
inside this directory; do not read, list, search or write anything outside it, and do not use git
(put any scripts or scratch files under work/):

{WS}

cd into it in every Bash call (tools resolve paths relative to it).

Read PRINCIPLES.md, INSTRUCTIONS.md and LOCAL_HTA_CONTEXT.md, then follow INSTRUCTIONS.md exactly.

Two rendered reports are waiting for verification: reports/report_A.docx and reports/report_B.docx (each with
its .provenance.json). Both were rendered from the run directory runs/kr_test, the claims register
approved/claims_register.json and the gap register approved_test_resolved/gap_register_resolved.yaml. Verify
each and write its review next to it, as the instructions say.

Hard rules: do not modify the reports, their provenance files, the registers, runs/, fixtures/, tools/ or
schemas/; never restate numbers in prose (cite check ids and provenance ids).

Reply in under 400 words: for each report, the command and exit code, every check's status, what each failure
means and which agent must act, and your recommendation.

In your final reply, never restate numbers from files in prose: quote tool output or counts
produced by a script, and cite names, ids and file fields instead.
