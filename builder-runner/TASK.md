You are acting as the Builder/Runner agent of a health-economic model adaptation pipeline. Work ONLY
inside this directory; do not read, list, search or write anything outside it, and do not use git
(put any scripts or scratch files under work/):

{WS}

cd into it in every Bash call (tools resolve paths relative to it).

Read PRINCIPLES.md, then INSTRUCTIONS.md, and follow INSTRUCTIONS.md exactly.

You have been handed two approved mapping specs to build:
1. approved/mapping_spec.json, with output directory work/run_approved
2. approved_test_resolved/mapping_spec_resolved.json (a test-only resolution prepared by the HEOR lead),
   with output directory work/run_test_resolved

Hard rules: do not modify anything under fixtures/, tools/, schemas/, approved/ or approved_test_resolved/;
do not edit any produced workbook; never type a number into a file or your reply except identifiers and
exit codes (cite run_log fields by name instead).

Reply in under 400 words: for each spec, the command, its exit code, the run status, what you reported
(blocking gaps, or the run_log location and the input-hash and tool-version fields you checked), and
whether the run is reproducible from a commit.

In your final reply, never restate numbers from files in prose: quote tool output or counts
produced by a script, and cite names, ids and file fields instead.
