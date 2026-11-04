"""Report Writer (render_report) and Report Verifier (verify_report), Gate 4.

Rendered against the test-only KR build (terminal care resolved with a test value), so the
report is a DRAFT: open human reviews remain (C04, C05, C17-C20) and the banner discloses the
test-only gap resolution.
"""
import copy
import json
import shutil

import pytest
from docx import Document

from conftest import FIXTURES
from test_build_and_verify import make_resolved
from tools.build_run import build_run
from tools.render_report import TemplateError, render
from tools.verify_report import verify_report

TEMPLATE = FIXTURES / "report_template_KR.docx"
SIDECAR = FIXTURES / "report_template_KR.sidecar.yaml"
CLAIMS = FIXTURES / "claims_register_KR.json"


@pytest.fixture(scope="module")
def kr_render(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("render")
    spec = make_resolved(tmp)
    assert build_run(spec, tmp / "run")["status"] == "built"
    register = json.loads(spec.read_text())["gap_register"]
    res = render(TEMPLATE, SIDECAR, tmp / "run", CLAIMS, register, tmp / "report_KR.docx", draft=True)
    return tmp, register, res


def paragraphs(path):
    return [p.text for p in Document(path).paragraphs]


def checks(tmp, register, report=None):
    r = verify_report(report or tmp / "report_KR.docx", tmp / "run", CLAIMS, register)
    return r, {c["id"]: c for c in r["checks"]}


def copy_report(tmp, dst):
    for suffix in (".docx", ".provenance.json"):
        shutil.copy(tmp / f"report_KR{suffix}", dst / f"report_KR{suffix}")
    return dst / "report_KR.docx"


def test_final_render_refuses_while_not_ready(kr_render, tmp_path):
    tmp, register, _ = kr_render
    res = render(TEMPLATE, SIDECAR, tmp / "run", CLAIMS, register, tmp_path / "final.docx")
    assert res["status"] == "not_ready" and "C05: open human review" in res["blockers"]
    assert not (tmp_path / "final.docx").exists()


def test_draft_renders_and_passes_every_check(kr_render):
    tmp, register, res = kr_render
    assert res["status"] == "draft" and res["currency"] == "KRW" and len(res["numbers"]) > 50
    r, c = checks(tmp, register)
    assert r["overall"] == "pass", [x for x in r["checks"] if x["status"] != "pass"]
    banner = next(p for p in paragraphs(tmp / "report_KR.docx") if p.startswith("DRAFT"))
    assert "GAP-001 resolved by HEOR lead (test)" in banner and "test-only value" in banner, "test resolution disclosed"


def test_truth_driven_wording(kr_render):
    tmp, _, res = kr_render
    text = "\n".join(paragraphs(tmp / "report_KR.docx"))
    assert "Drug A is cost-effective" in text and "Drug A is not cost-effective" not in text
    assert "This is below the reference value" in text
    assert "lower" not in text.split("1. Executive summary")[1].split("2. Decision problem")[0], "no threshold range (D09)"
    assert "lt_qx_male: local value derived by a declared method" in text
    used = {(u.get("claim"), u.get("directive")) for u in res["claims_used"]}
    assert ("C15", "label") in used and ("C16", "labels") in used and ("C03", "if") not in used


def test_template_with_a_literal_numeral_is_refused(kr_render, tmp_path):
    tmp, register, _ = kr_render
    doc = Document(TEMPLATE)
    doc.paragraphs[8].add_run(" About 5 patients in every 100 discontinue.")
    bad = tmp_path / "bad_template.docx"
    doc.save(bad)
    with pytest.raises(TemplateError, match="literal numerals"):
        render(bad, SIDECAR, tmp / "run", CLAIMS, register, tmp_path / "x.docx", draft=True)


def test_review_marker_cannot_reach_a_final_report(kr_render, tmp_path):
    """Even with every review closed in the register, a template still carrying {{review}} fails."""
    tmp, register, _ = kr_render
    reg = json.loads(CLAIMS.read_text())
    for c in reg["claims"]:
        if c["action"] == "human_review":
            c["action"] = "remove" if c["kind"] != "external_assertion_untraceable" else "human_review"
    reg["claims"] = [c for c in reg["claims"] if c["action"] != "human_review"]
    closed = tmp_path / "claims_closed.json"
    closed.write_text(json.dumps(reg))
    with pytest.raises(TemplateError, match="open review|not in the claims register"):
        render(TEMPLATE, SIDECAR, tmp / "run", closed, register, tmp_path / "final.docx")


def edit_docx(path, old, new):
    doc = Document(path)
    for p in doc.paragraphs:
        if old in p.text:
            for r in p.runs:
                r.text = r.text.replace(old, new)
    doc.save(path)


def test_changed_number_fails_trace(kr_render, tmp_path):
    tmp, register, res = kr_render
    rep = copy_report(tmp, tmp_path)
    icer = next(n["display"] for n in res["numbers"] if n["source"]["name"] == "res_icer")
    edit_docx(rep, icer, icer[:-1] + ("1" if icer[-1] != "1" else "2"))
    r, c = checks(tmp, register, rep)
    assert c["R01"]["status"] == "fail"


def test_inserted_uk_term_and_currency_fail(kr_render, tmp_path):
    tmp, register, _ = kr_render
    rep = copy_report(tmp, tmp_path)
    edit_docx(rep, "following the local guideline", "following the NICE reference case")
    edit_docx(rep, "₩50,000,000", "£50,000,000")
    r, c = checks(tmp, register, rep)
    assert c["R04"]["status"] == "fail" and c["R07"]["status"] == "fail"


def test_missing_rounding_note_and_retained_tag_fail(kr_render, tmp_path):
    tmp, register, _ = kr_render
    rep = copy_report(tmp, tmp_path)
    doc = Document(rep)
    for p in list(doc.paragraphs):
        if p.text.startswith("Note: figures") or p.text.startswith("Proportion male (prop_male)"):
            p._element.getparent().remove(p._element)
    doc.save(rep)
    r, c = checks(tmp, register, rep)
    assert c["R02"]["status"] == "fail" and any("prop_male" in x for x in c["R05"]["details"])


@pytest.mark.parametrize("tamper,expect", [
    (lambda m: next(u for u in m["claims_used"] if u.get("claim") == "C02").update(kept=False), "local truth"),
    (lambda m: m["claims_used"].append({"claim": "C03", "directive": "if", "truth_local": False, "kept": False}), "removed claim"),
    (lambda m: m.update(claims_used=[u for u in m["claims_used"] if u.get("claim") != "C15"]), "C15: regenerate claim not used"),
])
def test_claim_manifest_tampering_fails(kr_render, tmp_path, tamper, expect):
    tmp, register, _ = kr_render
    rep = copy_report(tmp, tmp_path)
    mpath = rep.with_suffix(".provenance.json")
    m = json.loads(mpath.read_text())
    tamper(m)
    mpath.write_text(json.dumps(m))
    r, c = checks(tmp, register, rep)
    assert c["R03"]["status"] == "fail" and any(expect in x for x in c["R03"]["details"]), c["R03"]


def test_draft_without_banner_fails_status(kr_render, tmp_path):
    tmp, register, _ = kr_render
    rep = copy_report(tmp, tmp_path)
    doc = Document(rep)
    for p in list(doc.paragraphs):
        if p.text.startswith("DRAFT"):
            p._element.getparent().remove(p._element)
    doc.save(rep)
    r, c = checks(tmp, register, rep)
    assert c["R06"]["status"] == "fail"
