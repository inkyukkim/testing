"""Build blind workspaces for agent evaluations (Gate 5). Synthetic data only.

    python evals/prepare_blind.py <base_dir>

Creates <base_dir>/<agent>/ for seven agents. Each workspace holds only that agent's
legitimate inputs: the tools, schemas, a principles excerpt, the agent's instructions and
its input files. Never copied: answer keys, docs/decisions.md, CLAUDE.md fixture notes,
fixture generators, tests. Inputs that would come from an upstream agent are produced by the
reference pipeline so each agent is evaluated in isolation. Planted defects (profiler,
verifiers) and the expected findings are written to <base_dir>/_keys/, outside every workspace.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import openpyxl
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
PY = sys.executable

AGENTS = ["input-mapper", "model-profiler", "builder-runner", "model-verifier", "report-profiler",
          "claims-analyst", "report-writer", "report-verifier"]

LOCAL_HTA_CONTEXT = """# Local HTA context (provided by the HEOR lead, synthetic)

- Country: Republic of Korea. Evaluation follows a local pharmacoeconomic guideline (synthetic
  placeholder); perspective as stated in local item KR-S04 (healthcare system).
- Decision rule: a single reference value (KR-S07). It is not an official threshold and there is
  no range; the lower bound in the model was set equal to it. Do not describe a threshold range.
- Currency KRW, displayed with the won sign; price year from KR-S03.
- Terminal care cost (GAP-001) is unresolved in the real pipeline. The run directory you are
  given uses a TEST-ONLY resolution; any report produced from it is a draft.
- No Korean scenario set has been specified yet.
- Whether Drug B reflects the Korean standard of care has not been confirmed by local clinicians.
- State utilities use the Korean EQ-5D-5L value set; AE disutilities and population norms are
  retained from the global model (different value set).
"""


def principles() -> str:
    src = (ROOT / "CLAUDE.md").read_text()
    out = [src[src.index("## Design principle"):src.index("## Environment")]]
    gap = src[src.index("### Gap register"):src.index("### Deterministic tool contracts")]
    gap = re.sub(r" In the KR\s+fixture, the missing terminal care cost \(`GAP-001`, `KR-C11`\) blocks the pipeline\.", "", gap)
    gap = re.sub(r";\s*KR answer key:\s*`fixtures/gap_register_KR\.yaml`", "", gap)
    out.append(gap)
    tools = src[src.index("### Deterministic tool contracts"):src.index("## Convention declarations")]
    tools = "\n".join(line for line in tools.splitlines() if not line.startswith("| `eval_mapping`"))
    out.append(tools)
    text = "# Principles (excerpt)\n\nWorkspace: this directory only. Paths in specs are relative to it.\n\n" + "\n".join(out)
    for leak in ("mapping_spec_KR", "claims_register_KR", "report_template_KR", "provenance.json", "answer key"):
        assert leak not in text, f"principles excerpt leaks {leak}"
    return text


def instructions(agent: str) -> str:
    body = (ROOT / ".claude" / "agents" / f"{agent}.md").read_text().split("---", 2)[2]
    return "# Agent instructions\n" + body.replace("Read CLAUDE.md first", "Read PRINCIPLES.md first")


def base(ws: Path, agent: str, stage2=False):
    if ws.exists():
        shutil.rmtree(ws)
    (ws / "fixtures").mkdir(parents=True)
    (ws / "work").mkdir()
    shutil.copytree(ROOT / "tools", ws / "tools", ignore=shutil.ignore_patterns("__pycache__", "eval_*.py"))
    shutil.copytree(ROOT / "schemas", ws / "schemas")
    (ws / "PRINCIPLES.md").write_text(principles())
    (ws / "INSTRUCTIONS.md").write_text(instructions(agent))
    if stage2:
        (ws / "LOCAL_HTA_CONTEXT.md").write_text(LOCAL_HTA_CONTEXT)


def copy(ws: Path, *names):
    for n in names:
        shutil.copy(FIX / n, ws / "fixtures" / n)


def run(ws: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run([PY, "-m", *args], cwd=ws, capture_output=True, text=True)


def resolved_build(ws: Path, run_dir="runs/kr_test"):
    """Test-only resolution of GAP-001 inside the workspace, then build with the workspace tools."""
    sys.path.insert(0, str(ROOT / "tests"))
    from test_build_and_verify import make_resolved
    appr = ws / "approved_test_resolved"
    appr.mkdir(exist_ok=True)
    spec = make_resolved(appr)
    r = run(ws, "tools.build_run", str(spec), run_dir)
    assert r.returncode == 0, r.stdout + r.stderr
    return spec, ws / run_dir


def prep_input_mapper(ws, keys):
    base(ws, "input-mapper")
    copy(ws, "global_model.xlsx", "global_model.conventions.yaml", "adaptation_input_KR.xlsx")
    r = run(ws, "tools.profile_workbook", "fixtures/global_model.xlsx", "--conventions",
            "fixtures/global_model.conventions.yaml", "--out", "work/model_profile.json")
    assert r.returncode == 0, r.stderr
    keys["input-mapper"] = {"key_spec": str(FIX / "mapping_spec_KR.json"), "key_register": str(FIX / "gap_register_KR.yaml")}


def prep_model_profiler(ws, keys):
    base(ws, "model-profiler")
    wb = openpyxl.load_workbook(FIX / "global_model.xlsx")
    t = wb["Trace_Int"]
    for r in range(20, 2108):
        t[f"AF{r}"] = f"=R{r}*c_pf_week*cycle_length_days/7*1.08"          # P1 hidden uplift
    wb["Trace_Comp"]["C10"] = "=int_rdi"                                      # P2 cross-arm link
    wb["Trace_Comp"]["AG300"] = 1234.5                                        # P4 pasted constant
    wb.save(ws / "fixtures" / "model.xlsx")
    conv = (FIX / "global_model.conventions.yaml").read_text()
    conv = conv.replace("  method: mid_cycle_continuous    # alternatives: annual_step (Fixture B, Gate 1)",
                        "  method: annual_step")                              # P3 wrong declaration
    for k in ("state_costs", "one_off_event_costs", "dosing_costs", "outcomes"):
        conv = re.sub(rf"    {k}: \w+.*", f"    {k}: model_year", conv)
    conv = conv.replace("Fixture A", "the model").replace("fixtures/global_model.xlsx", "fixtures/model.xlsx")
    conv = conv.replace("model_id: fixture_A_global_UK", "model_id: global_model")    # neutral id (no fixture hint)
    (ws / "fixtures" / "model.conventions.yaml").write_text(conv)
    keys["model-profiler"] = {"plants": {
        "P1": "Trace_Int AF (PF state cost) has a hidden literal uplift",
        "P2": "Trace_Comp C10 (Drug B RDI) links to int_rdi: Drug B cost depends on a Drug A input",
        "P3": "conventions declare annual_step discounting; formulas are mid-cycle continuous",
        "P4": "pasted constant at Trace_Comp!AG300"}}


def prep_builder_runner(ws, keys):
    base(ws, "builder-runner")
    copy(ws, "global_model.xlsx", "global_model.conventions.yaml", "adaptation_input_KR.xlsx")
    (ws / "approved").mkdir()
    spec = json.loads((FIX / "mapping_spec_KR.json").read_text())
    spec["gap_register"] = "approved/gap_register.yaml"
    (ws / "approved" / "mapping_spec.json").write_text(json.dumps(spec, indent=2))
    shutil.copy(FIX / "gap_register_KR.yaml", ws / "approved" / "gap_register.yaml")
    sys.path.insert(0, str(ROOT / "tests"))
    from test_build_and_verify import make_resolved
    (ws / "approved_test_resolved").mkdir()
    make_resolved(ws / "approved_test_resolved")
    keys["builder-runner"] = {"expect": {"approved": "blocked by GAP-001, nothing built",
                                         "approved_test_resolved": "built"}}


def prep_model_verifier(ws, keys):
    base(ws, "model-verifier")
    copy(ws, "global_model.xlsx", "global_model.conventions.yaml")
    spec, run_a = resolved_build(ws, "runs/run_A")
    spec2, run_b = resolved_build(ws, "runs/run_B")
    wb = openpyxl.load_workbook(run_b / "adapted_model.xlsx")
    wb["Trace_Int"]["AD200"] = "=X200*$C$11*$C$10*0.9"                         # changed formula
    ws_c = wb["Inputs_Clinical"]
    cell = next(r[2] for r in ws_c.iter_rows(min_row=4) if r[1].value == "int_os_scale")
    cell.value = cell.value * 1.25                                             # changed retained input
    from tools.workbook_io import exact_floats
    with exact_floats():                                                       # no unintended ULP changes
        wb.save(run_b / "adapted_model.xlsx")
    from tools.recalc import recalc
    shutil.rmtree(run_b / "recalc")
    recalc(run_b / "adapted_model.xlsx", run_b / "recalc")
    keys["model-verifier"] = {"spec_A": str(spec), "spec_B": str(spec2),
                              "expect": {"run_A": "accept (all pass)", "run_B": "reject: V02 formula Trace_Int!AD200; V03 int_os_scale"}}


def prep_report_profiler(ws, keys):
    base(ws, "report-profiler", stage2=False)
    copy(ws, "global_report_UK.docx", "global_model.xlsx", "global_model.conventions.yaml", "scenarios_UK.yaml")
    r = run(ws, "tools.profile_workbook", "fixtures/global_model.xlsx", "--conventions",
            "fixtures/global_model.conventions.yaml", "--out", "work/model_profile.json")
    assert r.returncode == 0, r.stderr
    keys["report-profiler"] = {"key": str(FIX / "global_report_UK.provenance.json")}


def oracle_report_profile(path):
    prov = json.loads((FIX / "global_report_UK.provenance.json").read_text())
    from tools.docx_extract import extract
    toks = extract(FIX / "global_report_UK.docx")["tokens"]
    path.write_text(json.dumps({"note": "Report profile from the reference pipeline.", "numerals": [
        {"token_index": i, "block": t["block"], "token": t["token"], "name": n["source"]["name"],
         "context": n["source"]["scenario"] or "base"} for i, (t, n) in enumerate(zip(toks, prov["numbers"]))]}, indent=2))


def prep_claims_analyst(ws, keys):
    base(ws, "claims-analyst", stage2=True)
    copy(ws, "global_report_UK.docx", "global_model.xlsx", "global_model.conventions.yaml", "scenarios_UK.yaml",
         "adaptation_input_KR.xlsx")
    (ws / "approved").mkdir()
    shutil.copy(FIX / "mapping_spec_KR.json", ws / "approved" / "mapping_spec.json")
    shutil.copy(FIX / "gap_register_KR.yaml", ws / "approved" / "gap_register.yaml")
    run(ws, "tools.docx_extract", "fixtures/global_report_UK.docx", "--out", "work/report_extract.json")
    oracle_report_profile(ws / "work" / "report_profile.json")
    resolved_build(ws)
    keys["claims-analyst"] = {"key": str(FIX / "claims_register_KR.json")}


def prep_report_writer(ws, keys):
    base(ws, "report-writer", stage2=True)
    copy(ws, "global_report_UK.docx", "global_model.xlsx", "global_model.conventions.yaml", "adaptation_input_KR.xlsx")
    (ws / "approved").mkdir()
    shutil.copy(FIX / "claims_register_KR.json", ws / "approved" / "claims_register.json")
    run(ws, "tools.docx_extract", "fixtures/global_report_UK.docx", "--out", "work/report_extract.json")
    oracle_report_profile(ws / "work" / "report_profile.json")
    spec, run_dir = resolved_build(ws)
    keys["report-writer"] = {"gap_register": json.loads(spec.read_text())["gap_register"], "run_dir": str(run_dir)}


def prep_report_verifier(ws, keys):
    base(ws, "report-verifier", stage2=True)
    copy(ws, "global_model.xlsx", "global_model.conventions.yaml")
    (ws / "approved").mkdir()
    shutil.copy(FIX / "claims_register_KR.json", ws / "approved" / "claims_register.json")
    spec, run_dir = resolved_build(ws)
    register = json.loads(spec.read_text())["gap_register"]
    from tools.render_report import render
    from docx import Document
    for name in ("report_A", "report_B"):
        render(FIX / "report_template_KR.docx", FIX / "report_template_KR.sidecar.yaml", run_dir,
               ws / "approved" / "claims_register.json", register, ws / "reports" / f"{name}.docx", draft=True)
    rep_b = ws / "reports" / "report_B.docx"
    doc = Document(rep_b)
    man = json.loads(rep_b.with_suffix(".provenance.json").read_text())
    icer = next(n["display"] for n in man["numbers"] if n["source"]["name"] == "res_icer")
    changed = False
    for p in list(doc.paragraphs):
        if p.text.startswith("Proportion male (prop_male)"):
            p._element.getparent().remove(p._element)                          # deleted retained tag
            continue
        for r in p.runs:
            r.text = r.text.replace("following the local guideline", "following the NICE reference case")
            if not changed and icer in r.text:
                r.text = r.text.replace(icer, icer[:-2] + "00", 1)              # changed number (first occurrence)
                changed = True
    doc.save(rep_b)
    keys["report-verifier"] = {"gap_register": register, "run_dir": str(run_dir),
                               "expect": {"report_A": "pass (draft: not acceptable as final)",
                                          "report_B": "reject: R01 changed ICER, R04 NICE, R05 prop_male"}}


def main(base_dir):
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT))
    keys = {}
    for agent, fn in zip(AGENTS, [prep_input_mapper, prep_model_profiler, prep_builder_runner, prep_model_verifier, prep_report_profiler,
                                  prep_claims_analyst, prep_report_writer, prep_report_verifier]):
        fn(base_dir / agent, keys)
        print(f"prepared {agent}")
    (base_dir / "_keys").mkdir(exist_ok=True)
    (base_dir / "_keys" / "keys.json").write_text(json.dumps(keys, indent=2))
    check_leaks(base_dir)


def check_leaks(base_dir):
    base_dir = Path(base_dir)
    forbidden = {"mapping_spec_KR.json", "gap_register_KR.yaml", "claims_register_KR.json", "report_template_KR.docx",
                 "report_template_KR.sidecar.yaml", "global_report_UK.provenance.json", "decisions.md",
                 "gate2_agent_eval.md", "CLAUDE.md", "keys.json", "fixture_notes.md", "status.md",
                 "gate5_agent_evals.md"}
    for agent in AGENTS:
        names = {p.name for p in (base_dir / agent).rglob("*")}
        assert not names & forbidden, f"{agent}: leaked {names & forbidden}"
        generators = ("build_global_", "build_adaptation_", "build_report_template_", "synthetic_data", "rebaseline", "test_", "conftest")
        assert not any(n.startswith(generators) and n.endswith(".py") for n in names), f"{agent}: generator or test copied"

if __name__ == "__main__":
    check_leaks(sys.argv[2]) if sys.argv[1] == "--check" else main(sys.argv[1])
