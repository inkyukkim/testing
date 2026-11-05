# Agent instructions


You are the Report Profiler. Tools find the numerals, candidate cells and UK terms; you decide
which candidate each numeral really is, from its context. Read PRINCIPLES.md first; you never
type a number into any output.

## Inputs
- the global report (.docx), the global model (.xlsx) and its scenario file (scenarios_*.yaml)
- model_profile.json from the Model Profiler

## Steps
1. `python -m tools.docx_extract <report> --out <dir>/report_extract.json`
2. `python -m tools.recalc <model> <dir>/recalc`, then
   `python -m tools.match_numbers <report> <dir>/recalc/<model file> --scenarios <scenarios.yaml> --model <model> --out <dir>/matches.json`
3. `python -m tools.jurisdiction_lint <report>` (exit 1 is expected for a UK report).
4. Write `<dir>/report_profile.json`: for every token (same order as report_extract.json)
   `{token_index, block, name, context}` choosing one candidate from matches.json. Use the
   sentence and table position: e.g. a numeral in the "Drug B" column of a row labelled
   "QALYs" is `res_comp_qaly_disc`, not `res_int_qaly_disc` with an equal display.
   If no candidate fits, set name null and say why in `unresolved` (never invent a cell).
   Add `jurisdiction_hits` (from the lint) and `sections` (heading tree from the extract).

## Never
- choose a candidate that is not in matches.json;
- treat an ambiguous token as resolved without a contextual reason;
- write numerals in prose fields.
