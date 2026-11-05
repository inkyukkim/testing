"""Task prompts for blind agent evaluations (Gate 5, round 3 onward).

    python evals/tasks.py <base_dir>    writes <base_dir>/<agent>/TASK.md and <base_dir>/ORCHESTRATOR.md

Each TASK.md is the complete prompt for one agent. {WS} is replaced by the orchestrator with
the absolute path of that workspace on the machine where the agent runs.
"""
from __future__ import annotations

import sys
from pathlib import Path

COMMON_HEAD = """You are acting as the {role} agent of a health-economic model adaptation pipeline. Work ONLY
inside this directory; do not read, list, search or write anything outside it, and do not use git
(put any scripts or scratch files under work/):

{{WS}}

cd into it in every Bash call (tools resolve paths relative to it).
"""
COMMON_TAIL = """
In your final reply, never restate numbers from files in prose: quote tool output or counts
produced by a script, and cite names, ids and file fields instead."""

TASKS = {
    "input-mapper": ("Input Mapper", """Read, in this order: PRINCIPLES.md, INSTRUCTIONS.md, schemas/mapping_spec.schema.yaml,
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
line of reasoning, and anything in the tools or instructions you think is ambiguous or wrong."""),
    "model-profiler": ("Model Profiler", """Read PRINCIPLES.md, then INSTRUCTIONS.md, and follow INSTRUCTIONS.md exactly.

Your inputs: the workbook fixtures/model.xlsx and its declaration fixtures/model.conventions.yaml.
Write work/model_profile.json (with the profiling tool) and work/model_profile_review.md.

Hard rules: do not modify anything under fixtures/, tools/ or schemas/; do not recalculate with anything
other than tools/recalc.py; never restate workbook values as numbers in prose (cite names, regions or tool
output fields). Support every judgement in the review with evidence you can point to in this workspace.

Reply in under 400 words: the commands you ran with their exit codes, every issue in the review that a
human must decide on (with the region or name it concerns and the evidence), and your recommendation
(accept the model for adaptation, or not)."""),
    "builder-runner": ("Builder/Runner", """Read PRINCIPLES.md, then INSTRUCTIONS.md, and follow INSTRUCTIONS.md exactly.

You have been handed two approved mapping specs to build:
1. approved/mapping_spec.json, with output directory work/run_approved
2. approved_test_resolved/mapping_spec_resolved.json (a test-only resolution prepared by the HEOR lead),
   with output directory work/run_test_resolved

Hard rules: do not modify anything under fixtures/, tools/, schemas/, approved/ or approved_test_resolved/;
do not edit any produced workbook; never type a number into a file or your reply except identifiers and
exit codes (cite run_log fields by name instead).

Reply in under 400 words: for each spec, the command, its exit code, the run status, what you reported
(blocking gaps, or the run_log location and the input-hash and tool-version fields you checked), and
whether the run is reproducible from a commit."""),
    "model-verifier": ("Model Verifier", """Read PRINCIPLES.md, then INSTRUCTIONS.md, and follow INSTRUCTIONS.md exactly.

Two Builder/Runner runs are waiting for verification: runs/run_A and runs/run_B. Both were built from the
approved spec approved_test_resolved/mapping_spec_resolved.json. Verify each run and write its review (the
review file goes in the run directory, as the instructions say).

Hard rules: do not modify the adapted workbooks, the spec, the gap register or anything under fixtures/,
tools/ or schemas/; never restate numbers in prose (cite check ids and file fields).

Reply in under 400 words: for each run, the command and exit code, the status of every check, what each
failure means and which agent must act, and your recommendation (accept or reject)."""),
    "report-profiler": ("Report Profiler", """Read PRINCIPLES.md, then INSTRUCTIONS.md, and follow INSTRUCTIONS.md exactly.

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
(counted by a script over your file), and which kinds of ambiguity were hardest."""),
    "claims-analyst": ("Claims Analyst", """Read PRINCIPLES.md, INSTRUCTIONS.md and LOCAL_HTA_CONTEXT.md, then follow INSTRUCTIONS.md exactly. Also
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
registered (counted by a script), and the judgement calls you found hardest."""),
    "report-writer": ("Report Writer", """Read PRINCIPLES.md, INSTRUCTIONS.md and LOCAL_HTA_CONTEXT.md, then follow INSTRUCTIONS.md exactly. Read
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
anything in the tools or instructions that got in your way."""),
    "report-verifier": ("Report Verifier", """Read PRINCIPLES.md, INSTRUCTIONS.md and LOCAL_HTA_CONTEXT.md, then follow INSTRUCTIONS.md exactly.

Two rendered reports are waiting for verification: reports/report_A.docx and reports/report_B.docx (each with
its .provenance.json). Both were rendered from the run directory runs/kr_test, the claims register
approved/claims_register.json and the gap register approved_test_resolved/gap_register_resolved.yaml. Verify
each and write its review next to it, as the instructions say.

Hard rules: do not modify the reports, their provenance files, the registers, runs/, fixtures/, tools/ or
schemas/; never restate numbers in prose (cite check ids and provenance ids).

Reply in under 400 words: for each report, the command and exit code, every check's status, what each failure
means and which agent must act, and your recommendation."""),
}

ORCHESTRATOR = """# Blind evaluation round: orchestrator instructions

This branch holds only eight agent workspaces (synthetic data). You are the orchestrator.
Do not do any agent's task yourself and do not read the workspaces' contents beyond each TASK.md.

1. For each directory listed below, read <dir>/TASK.md, replace the line `{WS}` with the absolute
   path of that directory, and launch one subagent (Agent tool, subagent_type general-purpose,
   in the background) with exactly that text as its prompt. Launch all eight, then wait.
   Directories: input-mapper, model-profiler, builder-runner, model-verifier, report-profiler,
   claims-analyst, report-writer, report-verifier.
2. When each subagent finishes, save its final reply verbatim to <dir>/HANDBACK.md.
3. When all eight have finished: `git add -A`, commit with the message
   "Blind evaluation round 3: agent outputs", and push to the branch you were told to push to.
   Do not modify, revert or tidy any file the agents produced, and do not run any tool yourself.
4. Reply with one line per directory: its name and whether a HANDBACK.md was saved.
"""


def write(base: Path):
    for agent, (role, body) in TASKS.items():
        ws = base / agent
        assert ws.is_dir(), agent
        (ws / "TASK.md").write_text(COMMON_HEAD.format(role=role) + "\n" + body + "\n" + COMMON_TAIL + "\n")
    (base / "ORCHESTRATOR.md").write_text(ORCHESTRATOR)


if __name__ == "__main__":
    write(Path(sys.argv[1]))
