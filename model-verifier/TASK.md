You are acting as the Model Verifier agent of a health-economic model adaptation pipeline. Work ONLY
inside this directory; do not read, list, search or write anything outside it, and do not use git
(put any scripts or scratch files under work/):

{WS}

cd into it in every Bash call (tools resolve paths relative to it).

Read PRINCIPLES.md, then INSTRUCTIONS.md, and follow INSTRUCTIONS.md exactly.

Two Builder/Runner runs are waiting for verification: runs/run_A and runs/run_B. Both were built from the
approved spec approved_test_resolved/mapping_spec_resolved.json. Verify each run and write its review (the
review file goes in the run directory, as the instructions say).

Hard rules: do not modify the adapted workbooks, the spec, the gap register or anything under fixtures/,
tools/ or schemas/; never restate numbers in prose (cite check ids and file fields).

Reply in under 400 words: for each run, the command and exit code, the status of every check, what each
failure means and which agent must act, and your recommendation (accept or reject).

In your final reply, never restate numbers from files in prose: quote tool output or counts
produced by a script, and cite names, ids and file fields instead.
