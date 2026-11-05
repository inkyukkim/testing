# PartSA adaptation agents (prototype)

A prototype pipeline of eight agents that adapts a global oncology **partitioned-survival (PartSA) cost-effectiveness model** to a local setting and regenerates its **technical report**. The worked example adapts a UK model and report to Korea.

> **All data in this repository are synthetic.** Nothing here is real clinical, price or HTA data, and no output is suitable for a reimbursement decision.

## Design principle

**Agents decide meaning; deterministic tools move numbers.** No numeric value passes through LLM-generated text without a traceable source cell.

In practice:
- **Agents write references and instructions, never numbers.** Their output is defined names, item ids and whitelisted operations.
- **Prose contains placeholders** such as `{{res_icer|money}}`. A renderer fills them from a recalculated workbook and records the provenance of every numeral.
- **Claims are checked by tools.** A claim's truth (for example "cost-effective at the reference value") is evaluated against model cells; an agent may choose the wording only.
- **Missing tools stop the pipeline.** If a required tool such as LibreOffice is missing, the pipeline stops rather than substituting an estimate.

The full rules are in [`CLAUDE.md`](CLAUDE.md).

## Pipeline

```
Stage 1: model adaptation
  1 Model Profiler  ──►  2 Input Mapper  ──►  3 Builder/Runner  ──►  4 Model Verifier
      profile + review      mapping spec +        adapted model +        checks V01–V10
                            gap register          run log
Stage 2: report regeneration
  5 Report Profiler ──►  6 Claims Analyst ──►  7 Report Writer   ──►  8 Report Verifier
      numeral → cell        claims register       template → report      checks R01–R07
```

People sign off at four points:
- approve the mapping spec and the gap register;
- resolve every blocking gap (only a person can);
- accept the model verification;
- close every claim marked for human review.

Agent definitions are in [`.claude/agents/`](.claude/agents). Every deterministic tool is a plain command-line program with JSON in and out, and needs no Claude runtime. [`CLAUDE.md`](CLAUDE.md) gives R and VBA equivalents for each.

## Quick start

Requirements: Python 3.11+ and LibreOffice (headless, with Calc and Writer). Excel and VBA are not used.

```bash
sudo apt-get install -y libreoffice-calc libreoffice-writer
pip install -r requirements.txt -r requirements-dev.txt

python -m pytest -q -m "not slow"     # fast lane, no LibreOffice (about 1 minute)
python -m pytest -q -n auto           # full suite in parallel, with LibreOffice recalculation
```

Rebuild the synthetic fixtures (only after changing a generator):

```bash
python scripts/build_global_model.py        # global model (Fixture A)
python scripts/build_global_model.py B      # same model, annual-step discounting (Fixture B)
python scripts/build_adaptation_input_kr.py
python scripts/build_global_report_uk.py    # UK report + provenance (recalculates the model and scenarios)
python scripts/build_report_template_kr.py
```

## Running the tools

The example pipeline, step by step:

```bash
# Stage 1
python -m tools.profile_workbook fixtures/global_model.xlsx --conventions fixtures/global_model.conventions.yaml --out runs/model_profile.json
python -m tools.apply_mapping fixtures/mapping_spec_KR.json            # dry run: validates, shows no values
python -m tools.gap_register fixtures/gap_register_KR.yaml             # exit 0 proceed / 1 invalid / 2 blocked
python -m tools.build_run fixtures/mapping_spec_KR.json runs/kr        # stops if a gap blocks
python -m tools.verify_model runs/kr fixtures/mapping_spec_KR.json

# Stage 2
python -m tools.docx_extract fixtures/global_report_UK.docx
python -m tools.jurisdiction_lint fixtures/global_report_UK.docx
python -m tools.claims fixtures/claims_register_KR.json fixtures/global_report_UK.docx fixtures/global_model.xlsx --global-scenarios fixtures/scenarios_UK.yaml
python -m tools.render_report <template.docx> <sidecar.yaml> <run_dir> <claims.json> <gap_register.yaml> out/report.docx --draft
python -m tools.verify_report out/report.docx <run_dir> <claims.json> <gap_register.yaml>
```

The KR example is deliberately incomplete, so the pipeline stops at a blocking gap (a local cost item is missing) until a person resolves it. The tests show the full path using a clearly labelled test-only resolution. A report rendered from that path is always a watermarked **draft**.

## Repository layout

| Path | Contents |
|------|----------|
| `tools/` | deterministic tools: recalculation, workbook I/O, independent Python engine, profiler, mapping, build, verifiers, report extraction and rendering, claim language |
| `schemas/` | JSON Schemas (YAML) for the gap register, mapping spec and claims register |
| `.claude/agents/` | the eight agent definitions |
| `scripts/` | generators for the synthetic fixtures |
| `fixtures/` | synthetic global model (two convention variants), UK report, KR inputs, answer keys |
| `evals/` | blind-evaluation harness (workspace builder, task prompts) |
| `tests/` | pytest suite; LibreOffice-dependent tests are marked `slow` |
| `docs/` | decision log, status by gate, fixture notes, agent-evaluation reports |

## How correctness is checked

- **Independent engine.** The workbook is formula-only and is recalculated by LibreOffice. A separate numpy implementation reproduces every result within 1e-6, absolute and relative.
- **Declared conventions.** Each model ships a conventions file (discounting, half-cycle correction, dosing, mortality cap and so on). The engine refuses conventions it doesn't implement, and the profiler checks the declaration against the formulas.
- **Model Verifier (V01–V10):**
  - the adapted workbook differs from the global model only in mapped input cells;
  - formulas are byte-identical;
  - the mapping round-trips;
  - parity and trace invariants hold.
- **Report Verifier (R01–R07):**
  - every numeral matches its provenance in document order;
  - rounding is consistent;
  - claim choices are re-checked against the model;
  - no source-jurisdiction terms remain;
  - retained inputs are disclosed;
  - the local currency is used.

## Agent evaluations

The agents have been evaluated in blind workspaces against answer keys and planted defects; see [`docs/gate2_agent_eval.md`](docs/gate2_agent_eval.md) and [`docs/gate5_agent_evals.md`](docs/gate5_agent_evals.md). Earlier rounds turned out not to be fully blind, because an agent started in this repository receives its `CLAUDE.md`. Fixture-specific notes and answer keys are therefore kept out of `CLAUDE.md`, in [`docs/fixture_notes.md`](docs/fixture_notes.md). **Do not give that file to an agent being evaluated.**

## Status and limitations

- **Gate history and modelling decisions:** [`docs/status.md`](docs/status.md) and [`docs/decisions.md`](docs/decisions.md).
- **PSA:** only a documented placeholder, because VBA cannot run here.
- **Independent engine:** written by the same author as the workbook. Parity shows that the workbook implements its declared conventions, not that the conventions are right.
- **Synthetic data:** the KR adaptation is a synthetic example with deliberate traps. It is not a template for real HIRA submissions.
