You are acting as the Report Profiler agent of a health-economic model adaptation pipeline. Work ONLY
inside this directory; do not read, list, search or write anything outside it, and do not use git
(put any scripts or scratch files under work/):

{WS}

cd into it in every Bash call (tools resolve paths relative to it).

Read PRINCIPLES.md, then INSTRUCTIONS.md, and follow INSTRUCTIONS.md exactly.

Inputs: report fixtures/global_report_UK.docx, model fixtures/global_model.xlsx, scenarios
fixtures/scenarios_UK.yaml, model profile work/model_profile.json. Put intermediate tool outputs in work/.

Required output: work/report_profile.json with exactly this shape:
{"numerals": [{"token_index": <int, order in the extract's tokens>, "block": <int>, "token": "<as extracted>",
  "name": "<defined name or null>", "context": "base" | "<scenario id>", "reason": "<short, no numerals>"}, ...],
 "unresolved": [{"token_index": <int>, "why": "<text>"}], "sections": [...], "jurisdiction_hits": [...]}
There must be one entry in "numerals" per extracted token, in the same order. Choose each name/context only
from that token's candidates in the match output, using the sentence and table position to disambiguate.

Hard rules: do not modify anything under fixtures/, tools/ or schemas/; never invent a cell that is not a candidate.

Reply in under 300 words: the commands and exit codes, how many tokens you resolved and left unresolved
(counted by a script over your file), and which kinds of ambiguity were hardest.

In your final reply, never restate numbers from files in prose: quote tool output or counts
produced by a script, and cite names, ids and file fields instead.
