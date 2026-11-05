# Status

## Build status by gate

Status: **Gate 1** = Gate 0.5 (realistic Fixture A, conventions, gap register, rounding
verifier, parity tests) plus Fixture B (annual-step discounting), the Model Profiler and
Input Mapper deterministic tools (`profile_workbook`, `read_local_inputs`, `apply_mapping`,
`eval_mapping`), their agent definitions in `.claude/agents/`, and KR answer keys
(`mapping_spec_KR.json`, `gap_register_KR.yaml`). **Gate 2** adds the Builder/Runner
(`build_run`) and Model Verifier (`verify_model`, checks V01-V10) tools and agent
definitions, the mapping-spec schema, exact float writing, and a first blind Input Mapper
agent run scored against the answer key (`docs/gate2_agent_eval.md`). **Gate 2.1** fixes the
tool issues that run raised (label-only confirmations, list-valued `retained_source`, YAML
anchors R8, free-text numerals R7) and updates the answer key (D13). Decisions D01-D16 are
in `docs/decisions.md`; GAP-001 remains open (D14). **Gate 3** adds the Report Profiler and
Claims Analyst: tools `docx_extract`, `match_numbers`, `jurisdiction_lint`, `scenario_runner`,
`evaluate_claim` (cell-referencing claim language, no numeric literals), `claims` (register
rules K1-K6 and a readiness gate for the Report Writer), the claims-register schema, agent
definitions, `fixtures/scenarios_UK.yaml` and the KR claims answer key. **Gate 4** adds the
Report Writer (`render_report`: directive templates, no numerals, truth-driven wording,
provenance; final render refused until the claims register is ready, otherwise a disclosed
DRAFT) and the Report Verifier (`verify_report`, checks R01-R07), `tools/formats.yaml`
(currency-aware formats), agent definitions, the KR template answer key, a `slow` test
marker with a fast lane, and CI (`.github/workflows/tests.yml`). The KR report exists only
as a draft against a test-only build: GAP-001 and six human reviews remain open.

**Gate 5** runs blind evaluations of all eight agents (`evals/`, `docs/gate5_agent_evals.md`). Rounds 1
and 2 were exposed to fixture notes through the session's cached CLAUDE.md. Round 3 ran in a separate
session on an orphan branch holding only the workspaces. It matched the earlier rounds within one to
two items per agent, with no critical differences. Its five findings were fixed afterwards (D17–D19, accepted by the HEOR lead on 2026-11-05).
