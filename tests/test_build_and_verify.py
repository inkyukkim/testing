"""Builder/Runner and Model Verifier (Gate 2).

The real KR adaptation is blocked by GAP-001 (terminal care), so the full build path is
exercised on a test-only resolution written to a temporary directory: a copy of the KR
inputs with a terminal care value, a register whose GAP-001 is resolved by a human role,
and a spec that maps c_terminal from that item. None of it is a fixture.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest
import yaml

from conftest import FIXTURES, ROOT
from tools.build_run import build_run
from tools.verify_model import verify

SPEC = FIXTURES / "mapping_spec_KR.json"


def make_resolved(tmp, terminal_value=4500000):
    wb = openpyxl.load_workbook(FIXTURES / "adaptation_input_KR.xlsx")
    ws = wb["Costs_KR"]
    row = next(r for r in range(4, ws.max_row + 1) if ws.cell(row=r, column=1).value == "KR-C11")
    ws.cell(row=row, column=3, value=terminal_value)
    ws.cell(row=row, column=6, value="TEST ONLY: simulated local claims analysis")
    local = tmp / "adaptation_input_KR_resolved.xlsx"
    wb.save(local)
    reg = yaml.safe_load((FIXTURES / "gap_register_KR.yaml").read_text())
    g = next(g for g in reg["gaps"] if g["gap_id"] == "GAP-001")
    g.update(status="resolved", resolution={"option_id": "E1", "decided_by": {"kind": "human", "role": "HEOR lead (test)"},
                                            "date": "2026-11-04", "evidence": "KR-C11 (test-only value)"})
    reg["adaptation"]["local_inputs"] = str(local)
    register = tmp / "gap_register_resolved.yaml"
    register.write_text(yaml.safe_dump(reg, sort_keys=False))
    spec = json.loads(SPEC.read_text())
    spec.update(local_inputs=str(local), gap_register=str(register))
    e = next(m for m in spec["mappings"] if m["target"] == "c_terminal")
    e.update(status="mapped", operation="copy", args={"source": "KR-C11"},
             rationale="Resolved by human with local data (test only).")
    spec_path = tmp / "mapping_spec_resolved.json"
    spec_path.write_text(json.dumps(spec, indent=2))
    return spec_path


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("build")
    spec = make_resolved(tmp)
    log = build_run(spec, tmp / "run", scenarios_path=None)
    return tmp, spec, log


def test_real_kr_spec_is_blocked_and_builds_nothing(tmp_path):
    log = build_run(SPEC, tmp_path / "run")
    assert log["status"] == "blocked" and log["blocking_gaps"] == ["GAP-001"]
    assert not (tmp_path / "run" / "adapted_model.xlsx").exists()
    assert json.loads((tmp_path / "run" / "run_log.json").read_text())["status"] == "blocked"
    r = subprocess.run([sys.executable, "-m", "tools.build_run", str(SPEC), str(tmp_path / "cli")],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2 and "BLOCKED: GAP-001" in r.stdout
    assert verify(tmp_path / "run", SPEC)["overall"] == "fail"


def test_run_log_records_provenance_and_versions(built):
    tmp, _, log = built
    assert log["status"] == "built"
    for k in ("model", "local_inputs", "gap_register", "spec", "conventions"):
        assert len(log["inputs"][k]["sha256"]) == 64, k
    assert log["tools"]["libreoffice"].startswith("LibreOffice") and log["tools"]["registry_version"] == 1
    ov = json.loads((tmp / "run" / "overrides.json").read_text())
    assert ov["provenance"]["c_pf_week"]["source"]["item_id"] == "KR-C09"
    assert isinstance(log["base_case"]["res_icer"], float)


def test_verifier_passes_on_clean_build(built):
    tmp, spec, _ = built
    res = verify(tmp / "run", spec)
    failed = [c for c in res["checks"] if c["status"] != "pass"]
    assert res["overall"] == "pass", failed
    assert [c["id"] for c in res["checks"]] == [f"V{i:02d}" for i in range(1, 11)]
    assert (tmp / "run" / "model_verification.json").exists()


def tampered(built, tmp_path, edit):
    tmp, spec, _ = built
    run = tmp_path / "run"
    shutil.copytree(tmp / "run", run)
    wb = openpyxl.load_workbook(run / "adapted_model.xlsx")
    edit(wb)
    wb.save(run / "adapted_model.xlsx")
    return {c["id"]: c for c in verify(run, spec)["checks"]}


def test_changed_formula_is_caught(built, tmp_path):
    def edit(wb):
        wb["Trace_Int"]["AF100"] = "=R100*c_pf_week*cycle_length_days/7*1.1"
    checks = tampered(built, tmp_path, edit)
    assert checks["V02"]["status"] == "fail" and "Trace_Int!AF100" in checks["V02"]["details"][0]


def test_changed_retained_input_is_caught(built, tmp_path):
    def edit(wb):
        ws = wb["Inputs_Clinical"]
        cell = next(r[2] for r in ws.iter_rows(min_row=4) if r[1].value == "int_os_scale")
        cell.value = cell.value * 1.2
    checks = tampered(built, tmp_path, edit)
    assert checks["V03"]["status"] == "fail" and any("int_os_scale" in x for x in checks["V03"]["details"])


def test_pasted_constant_is_caught(built, tmp_path):
    def edit(wb):
        wb["Trace_Comp"]["AG300"] = 1234.5
    checks = tampered(built, tmp_path, edit)
    assert checks["V02"]["status"] == "fail" or checks["V03"]["status"] == "fail"
    assert checks["V08"]["status"] == "fail"


def test_parity_is_not_reported_under_a_contradicted_declaration(built, tmp_path):
    """Round 2: with a wrong but supported declaration, V07 would have tested the wrong convention."""
    tmp, spec, _ = built
    shutil.copy(FIXTURES / "global_model.xlsx", tmp_path / "global_model.xlsx")
    conv = (FIXTURES / "global_model.conventions.yaml").read_text()
    (tmp_path / "global_model.conventions.yaml").write_text(
        conv.replace("  method: mid_cycle_continuous", "  method: annual_step", 1))
    s = json.loads(Path(spec).read_text())
    s["model"] = str(tmp_path / "global_model.xlsx")
    spec2 = tmp_path / "spec.json"
    spec2.write_text(json.dumps(s))
    c = {x["id"]: x for x in verify(tmp / "run", spec2)["checks"]}
    assert c["V07"]["status"] == "fail" and "not evaluated" in c["V07"]["details"][0]
    assert c["V08"]["status"] == "fail"


def test_scenarios_use_references_only(tmp_path):
    spec = make_resolved(tmp_path)
    sc = tmp_path / "scenarios.yaml"
    sc.write_text(yaml.safe_dump({"scenarios": [
        {"id": "KS1", "label": "No age adjustment of utilities", "set": {"use_age_util_adj": {"registry": "switch_off"}}},
        {"id": "KS2", "label": "PD utility equal to PF", "set": {"u_pd": {"model": "u_pf"}}},
    ]}))
    log = build_run(spec, tmp_path / "run", sc)
    s = {x["id"]: x["results"] for x in log["scenarios"]}
    assert s["KS1"]["res_inc_qaly_disc"] > log["base_case"]["res_inc_qaly_disc"]
    assert s["KS2"]["res_inc_qaly_disc"] > log["base_case"]["res_inc_qaly_disc"]
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump({"scenarios": [{"id": "X", "label": "typed number", "set": {"u_pd": {"value": 0.7}}}]}))
    with pytest.raises(ValueError):
        build_run(spec, tmp_path / "run2", bad)


def test_git_state_unknown_outside_a_repository(tmp_path):
    """Found by the blind Builder/Runner run: outside a repo, dirty read False (looked clean)."""
    from tools.build_run import git_state
    assert git_state(tmp_path) == (None, None)
    commit, dirty = git_state(ROOT)
    assert isinstance(commit, str) and len(commit) == 40 and isinstance(dirty, bool)


def test_git_dirty_ignores_files_outside_its_scope(tmp_path):
    """Found by the blind round-3 Builder/Runner: other agents' outputs made every run dirty."""
    import subprocess
    from tools.build_run import dirty_scope, git_state

    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
    (tmp_path / "tools").mkdir()
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs" / "model.xlsx").write_text("x")
    git("add", "-A")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "inputs")
    scope = dirty_scope(tmp_path, [tmp_path / "inputs" / "model.xlsx", Path("/elsewhere/spec.json")])
    assert scope == ["tools", "schemas", "inputs/model.xlsx"]
    (tmp_path / "other_agent_output.json").write_text("{}")
    assert git_state(tmp_path, scope)[1] is False
    assert git_state(tmp_path)[1] is True                       # unscoped: whole tree
    (tmp_path / "inputs" / "model.xlsx").write_text("changed")
    assert git_state(tmp_path, scope)[1] is True


def test_convention_mismatch_blocks_the_build(tmp_path):
    """Round 2 (Model Profiler): a wrong but supported declaration (annual_step) passed the engine,
    so V07 would have tested parity against the wrong convention. The build now refuses."""
    spec_path = make_resolved(tmp_path)
    model = tmp_path / "global_model.xlsx"
    shutil.copy(FIXTURES / "global_model.xlsx", model)
    conv = (FIXTURES / "global_model.conventions.yaml").read_text()
    wrong = conv.replace("  method: mid_cycle_continuous", "  method: annual_step", 1)
    assert wrong != conv
    (tmp_path / "global_model.conventions.yaml").write_text(wrong)
    spec = json.loads(spec_path.read_text())
    spec["model"] = str(model)
    spec_path.write_text(json.dumps(spec))
    log = build_run(spec_path, tmp_path / "run")
    assert log["status"] == "invalid" and not (tmp_path / "run" / "adapted_model.xlsx").exists()
    assert any("convention mismatch" in e and "annual_step" in e for e in log["errors"])
