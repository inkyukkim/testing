"""Deterministic tool: render a report template into a local report with provenance (Report Writer).

    render(template_docx, sidecar_yaml, run_dir, claims_register, gap_register, out_docx, draft=False)
        -> manifest (also written next to out_docx as <stem>.provenance.json)
CLI: python -m tools.render_report <template.docx> <sidecar.yaml> <run_dir> <claims.json> <gap_register.yaml> <out.docx> [--draft]
     exit 0 rendered, 1 template or claims invalid, 2 not ready (use --draft to render a marked draft)

The Report Writer (an agent) writes the template and its sidecar: prose with directives and
no numerals. This tool supplies every number and every truth-dependent choice.

Directives (inside one paragraph or table cell):
    {{name|fmt}}  {{name@SC1|fmt}}   value of a named cell, formatted per tools/formats.yaml
    {{text name}}                    text-valued cell (e.g. perspective, currency_code)
    {{if Cxx}} ... {{endif}}         kept only if claim Cxx is true on the adapted model
    {{ifnot Cxx}} ... {{endif}}      kept only if claim Cxx is false
    {{ifany Cxx}} ... {{endif}}      kept only if a select-claim selected at least one cell
    {{label Cxx}}                    sidecar label of the cell chosen by an argmax/argmin claim
    {{value_of Cxx|fmt}}             value of that chosen cell
    {{labels Cxx}}                   sidecar labels of the cells selected by a select claim
    {{review Cxx}}                   open human review: a marker in a draft, an error in a final
Paragraph directives (the whole paragraph):
    {{draft_banner}}  {{rounding_note}}  {{retained_inputs}}
A paragraph left empty after conditional removal is deleted.

Wording whose truth depends on results (tools/truth_cues.yaml: verdicts, attributions such as
"driven mainly by", rankings, signed changes such as "increased ... by {{x}}") must sit inside a
claim conditional; the renderer refuses a template where it does not (T1).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from tools.claims import evaluate_register, ready, validate, TRUTH_CUE
from tools.docx_extract import extract
from tools.workbook_io import list_names, read_named

FORMATS = yaml.safe_load(Path(__file__).with_name("formats.yaml").read_text())
DIRECTIVE = re.compile(r"\{\{(.*?)\}\}")
BLOCK = re.compile(r"\{\{(if|ifnot|ifany) (C\d{2})\}\}(.*?)\{\{endif\}\}", re.S)


class TemplateError(ValueError):
    pass


def fmt_spec(fmt: str, currency: str) -> dict:
    if fmt not in FORMATS["formats"]:
        raise TemplateError(f"unknown format {fmt!r}")
    f = dict(FORMATS["formats"][fmt])
    cur = FORMATS["currencies"][currency]
    if f["decimals"] == "currency":
        f["decimals"] = cur["decimals"]
    if f["prefix"] == "currency":
        f["prefix"] = cur["symbol"]
    return f


def format_value(v, f) -> str:
    x = v * f["scale"]
    dec = f["decimals"]
    body = f"{abs(x):.{dec}f}" if f.get("grouping") is False else f"{abs(x):,.{dec}f}"
    sign = "-" if x < 0 and round(abs(x), dec) != 0 else ""
    return f"{sign}{f['prefix']}{body}{f['suffix']}"


def join_phrases(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


class Renderer:
    def __init__(self, contexts, refs, workbook, claims, labels, draft, currency):
        self.contexts, self.refs, self.workbook = contexts, refs, workbook
        self.claims = {c["claim_id"]: c for c in claims["claims"]}
        self.labels, self.draft, self.currency = labels, draft, currency
        self.prov, self.used, self.errors = [], [], []

    def _claim(self, cid):
        if cid not in self.claims:
            raise TemplateError(f"{cid}: not in the claims register")
        return self.claims[cid]

    def _number(self, ref, fmt, section):
        name, _, ctx = ref.partition("@")
        ctx = ctx or "base"
        if ctx not in self.contexts or name not in self.contexts[ctx]:
            raise TemplateError(f"{ref}: no value in context {ctx}")
        v = self.contexts[ctx][name]
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise TemplateError(f"{ref}: not numeric ({v!r}); use {{{{text {name}}}}}")
        f = fmt_spec(fmt, self.currency)
        disp = format_value(v, f)
        sheet, cell = self.refs[name]
        self.prov.append({"id": f"N{len(self.prov) + 1:03d}", "section": section, "display": disp, "value": v,
                          "format": {"scale": f["scale"], "decimals": f["decimals"], "prefix": f["prefix"],
                                     "suffix": f["suffix"], "grouping": f.get("grouping", True)},
                          "source": {"workbook": self.workbook, "name": name, "sheet": sheet, "cell": cell,
                                     "scenario": None if ctx == "base" else ctx}})
        return disp

    def _chosen(self, cid):
        ev = self._claim(cid).get("evidence_local", {})
        for k in ("argmax", "argmin"):
            if k in ev:
                return ev[k]
        raise TemplateError(f"{cid}: not an argmax/argmin claim with a local evaluation")

    def text(self, s: str, section: str) -> str:
        def block(m):
            kind, cid, body = m.groups()
            c = self._claim(cid)
            t = c.get("truth_local")
            if kind == "ifany":
                sel = c.get("evidence_local", {}).get("selected")
                if sel is None:
                    raise TemplateError(f"{cid}: ifany needs a select claim with a local evaluation")
                keep = bool(sel)
            else:
                if not isinstance(t, bool):
                    if self.draft:
                        self.used.append({"claim": cid, "directive": kind, "rendered": "pending"})
                        return f"[pending {cid}]"
                    raise TemplateError(f"{cid}: local truth is {t!r}; cannot choose wording")
                keep = t if kind == "if" else not t
            self.used.append({"claim": cid, "directive": kind, "truth_local": t, "kept": keep})
            return body if keep else ""

        s = BLOCK.sub(block, s)

        def one(m):
            d = m.group(1).strip()
            if d.startswith("text "):
                name = d[5:]
                return str(self.contexts["base"][name])
            if d.startswith("label "):
                cid = d[6:]
                self.used.append({"claim": cid, "directive": "label"})
                return self.labels[self._chosen(cid)]
            if d.startswith("labels "):
                cid = d[7:]
                self.used.append({"claim": cid, "directive": "labels"})
                sel = self._claim(cid).get("evidence_local", {}).get("selected", [])
                return join_phrases([self.labels[r] for r in sel]) if sel else ""
            if d.startswith("value_of "):
                cid, _, fmt = d[9:].partition("|")
                return self._number(self._chosen(cid), fmt, section)
            if d.startswith("review "):
                cid = d[7:]
                if not self.draft:
                    raise TemplateError(f"{cid}: open review cannot appear in a final report")
                self.used.append({"claim": cid, "directive": "review"})
                return f"[open review {cid}]"
            if "|" in d:
                ref, fmt = d.split("|", 1)
                return self._number(ref.strip(), fmt.strip(), section)
            raise TemplateError(f"unknown directive {{{{{d}}}}}")

        return DIRECTIVE.sub(one, s)


def _set_text(par: Paragraph, text: str):
    runs = par.runs
    if not runs:
        par.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._element.getparent().remove(r._element)


def _delete(par: Paragraph):
    par._element.getparent().remove(par._element)


def _insert_after(par: Paragraph, text: str, style=None) -> Paragraph:
    new = copy.deepcopy(par._element)
    par._element.addnext(new)
    p = Paragraph(new, par._parent)
    _set_text(p, text)
    if style:
        p.style = style
    return p


def retained_lines(gap_register, input_labels, provenance) -> list[str]:
    """One line per target of a retain_* gap. Whether the value is global or local comes from
    the run's provenance: a mapped target (e.g. a converted life table) is a local value derived
    by a declared method, not a retained global input."""
    lines = []
    for g in gap_register["gaps"]:
        if g["handling"] in ("retain_tagged", "retain_flagged"):
            flag = ", flagged for review" if g["handling"] == "retain_flagged" else ""
            for t in g["target_names"]:
                status = (provenance.get(t) or {}).get("status")
                what = "local value derived by a declared method" if status == "mapped" else "retained global input"
                label = input_labels.get(t, t)
                lead = f"{label} ({t})" if label != t else t
                lines.append(f"{lead}: {what}{flag} [{g['gap_id']}]")
    return lines


def resolution_lines(gap_register) -> list[str]:
    out = []
    for g in gap_register["gaps"]:
        r = g.get("resolution")
        if g["status"] == "resolved" and r:
            out.append(f"{g['gap_id']} resolved by {r['decided_by']['role']} (option {r['option_id']}; "
                       f"evidence: {r['evidence']})")
    return out


def rounding_needed(contexts, prov) -> bool:
    from tools.rounding import check_derived
    shown = {p["source"]["name"]: p for p in prov if p["source"]["scenario"] is None}
    checks = []
    for name in shown:
        if name.startswith("res_inc_"):
            key = name[len("res_inc_"):]
            a, b = shown.get(f"res_int_{key}"), shown.get(f"res_comp_{key}")
            if a and b:
                checks.append(("difference", [a, b], shown[name]))
    if all(k in shown for k in ("res_icer", "res_inc_total_cost", "res_inc_qaly_disc")):
        checks.append(("ratio", [shown["res_inc_total_cost"], shown["res_inc_qaly_disc"]], shown["res_icer"]))
    num = lambda p: (p["display"].replace("%", ""), p["format"]["decimals"])
    results = [check_derived(op, [num(o) for o in ops], num(r)) for op, ops, r in checks]
    bad = [r for r in results if not r.ok]
    if bad:
        raise TemplateError(f"rounding-interval check failed on {len(bad)} derived figures")
    return any(r.needs_footnote for r in results)


_CONDITIONAL = re.compile(r"\{\{(?:if|ifnot|ifany) C\w+\}\}.*?\{\{endif\}\}", re.DOTALL)


def truth_cues(text: str, conditionals: bool = True) -> list[str]:
    """Truth-dependent wording in text; with conditionals, text inside claim conditionals is
    exempt. Placeholders count as '#'."""
    outside = _CONDITIONAL.sub(" ", text) if conditionals else text
    outside = re.sub(r"\{\{[^}]*\}\}", "#", outside)
    return [outside[max(0, m.start() - 40):m.end() + 20].strip() for m in TRUTH_CUE.finditer(outside)]


def unconditioned_cues(doc) -> list[str]:
    texts = [p.text for p in doc.paragraphs] + [c.text for tb in doc.tables for r in tb.rows for c in r.cells]
    return [hit for tx in dict.fromkeys(texts) for hit in truth_cues(tx)]


def render(template, sidecar, run_dir, claims_path, register_path, out, draft=False) -> dict:
    from tools.gap_register import load as load_register
    from tools.profile_workbook import profile
    run_dir = Path(run_dir)
    log = json.loads((run_dir / "run_log.json").read_text())
    if log["status"] != "built":
        raise TemplateError(f"model run status {log['status']}: nothing to render")
    recalculated = run_dir / "recalc" / "adapted_model.xlsx"
    contexts = {"base": read_named(recalculated)}
    for sc in log.get("scenarios", []):
        contexts[sc["id"]] = read_named(run_dir / f"recalc_{sc['id']}" / f"scenario_{sc['id']}.xlsx")
    side = yaml.safe_load(Path(sidecar).read_text())
    template_tokens = extract(template)["tokens"]
    if template_tokens:
        raise TemplateError(f"template contains literal numerals: {[t['token'] for t in template_tokens][:10]}")
    claims_raw = json.loads(Path(claims_path).read_text())
    claims = evaluate_register(claims_raw, None, contexts)   # local truth only; K1 is the Claims Analyst's gate
    errors = validate(claims)
    if errors:
        raise TemplateError(f"claims register invalid: {errors[:5]}")
    blockers = ready(claims)
    if blockers and not draft:
        return {"status": "not_ready", "blockers": blockers}
    register = load_register(register_path)
    labels_in = {n: (e.get("metadata") or {}).get("Parameter", n)
                 for n, e in profile(recalculated)["names"].items() if e["role"] == "input"}
    currency = contexts["base"]["currency_code"]
    R = Renderer(contexts, list_names(recalculated), str(recalculated), claims, side.get("labels", {}), draft, currency)
    doc = Document(template)
    cues = unconditioned_cues(doc)
    if cues:
        raise TemplateError(f"T1 truth-dependent wording outside a claim conditional: {cues[:5]}")
    section = None
    for el in list(doc.element.body.iterchildren()):
        if el.tag.endswith("}p"):
            p = Paragraph(el, doc)
            if p.style.name.startswith("Heading"):
                if p.style.name in ("Heading 1", "Heading"):
                    section = p.text
                continue
            t = p.text.strip()
            if t == "{{draft_banner}}":
                res_lines = resolution_lines(register)
                if draft:
                    _set_text(p, "DRAFT, not for submission. Open items: " + "; ".join(blockers or ["none"])
                              + ". Gap resolutions: " + ("; ".join(res_lines) or "none") + ".")
                elif res_lines:
                    _set_text(p, "Gap resolutions: " + "; ".join(res_lines) + ".")
                else:
                    _delete(p)
                continue
            if t == "{{rounding_note}}":
                p._rounding = True
                R.used.append({"directive": "rounding_note"})
                R._rounding_par = p
                continue
            if t == "{{retained_inputs}}":
                run_prov = json.loads((run_dir / "overrides.json").read_text())["provenance"]
                lines = retained_lines(register, labels_in, run_prov)
                anchor = p
                for line in lines:
                    anchor = _insert_after(anchor, line, style="List Bullet")
                _delete(p)
                continue
            if "{{" in p.text:
                new = R.text(p.text, section)
                if not new.strip():
                    _delete(p)
                else:
                    _set_text(p, new)
        elif el.tag.endswith("}tbl"):
            t = Table(el, doc)
            for row in t.rows:
                seen = []
                for cell in row.cells:
                    if cell._tc in seen:
                        continue
                    seen.append(cell._tc)
                    for p in cell.paragraphs:
                        if "{{" in p.text:
                            _set_text(p, R.text(p.text, section))
    rp = getattr(R, "_rounding_par", None)
    footnote = False
    if rp is not None:
        footnote = rounding_needed(contexts, R.prov)
        if footnote:
            _set_text(rp, " ".join(FORMATS["rounding_note"].split()))
        else:
            _delete(rp)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    # template and sidecar are identified by content, not by path: a path can point outside the
    # workspace (e.g. at an evaluation answer key) and says nothing about what was rendered
    ident = lambda f: {"file": Path(f).name, "sha256": hashlib.sha256(Path(f).read_bytes()).hexdigest()}
    manifest = {"document": str(out), "template": ident(template), "sidecar": ident(sidecar),
                "model_run": str(run_dir), "draft": draft,
                "blockers": blockers, "currency": currency, "rounding_footnote": footnote,
                "claims_used": R.used, "numbers": R.prov}
    Path(out).with_suffix(".provenance.json").write_text(json.dumps(manifest, indent=2, default=str))
    return {"status": "draft" if draft else "rendered", **manifest}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for a in ("template", "sidecar", "run_dir", "claims", "gap_register", "out"):
        ap.add_argument(a)
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    try:
        res = render(a.template, a.sidecar, a.run_dir, a.claims, a.gap_register, a.out, a.draft)
    except TemplateError as e:
        print(f"INVALID: {e}")
        return 1
    if res["status"] == "not_ready":
        for b in res["blockers"]:
            print(f"NOT READY: {b}")
        return 2
    print(f"{res['status'].upper()}: {a.out} ({len(res['numbers'])} numbers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
