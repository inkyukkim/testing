You are acting as the Input Mapper agent of a health-economic model adaptation pipeline. Work ONLY
inside this directory; do not read, list, search or write anything outside it, and do not use git
(put any scripts or scratch files under work/):

{WS}

cd into it in every Bash call (tools resolve paths relative to it).

Read, in this order: PRINCIPLES.md, INSTRUCTIONS.md, schemas/mapping_spec.schema.yaml,
schemas/gap_register.schema.yaml, tools/constants_registry.yaml, and the docstrings of
tools/apply_mapping.py and tools/gap_register.py. The model profile is at work/model_profile.json
(from fixtures/global_model.xlsx with fixtures/global_model.conventions.yaml). The local inputs are
fixtures/adaptation_input_KR.xlsx; read them with `python3 -m tools.read_local_inputs
fixtures/adaptation_input_KR.xlsx` (you may also open workbooks with openpyxl to read labels, units and notes).

Task: write work/mapping_spec.json and work/gap_register.yaml for adapting the global model to the
Korean inputs, following INSTRUCTIONS.md exactly. In mapping_spec.json set "model":
"fixtures/global_model.xlsx", "local_inputs": "fixtures/adaptation_input_KR.xlsx", "gap_register":
"work/gap_register.yaml".

Validate with:
  python3 -m tools.gap_register work/gap_register.yaml
  python3 -m tools.apply_mapping work/mapping_spec.json
Iterate until the dry run prints no INVALID lines (exit 0, or exit 2 with only the blocking gaps you intend).

Hard rules: never write a numeric value into either file; never modify anything under tools/,
schemas/ or fixtures/; do not run apply_mapping with --apply; do not work around a blocking gap.

Reply in under 500 words: the final exit codes and output of both validation commands, every blocking
gap, every retain_flagged gap, every decision where you chose between two defensible options with one
line of reasoning, and anything in the tools or instructions you think is ambiguous or wrong.

In your final reply, never restate numbers from files in prose: quote tool output or counts
produced by a script, and cite names, ids and file fields instead.
