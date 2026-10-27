"""Generate fixtures/global_report_UK.docx plus its provenance sidecar (synthetic).

Run:  python scripts/build_global_report_uk.py   (after build_global_model.py)

Every model-derived number in the report is formatted from a LibreOffice-recalculated
cell of fixtures/global_model.xlsx (base case or a scenario with named-input overrides)
and recorded in fixtures/global_report_UK.provenance.json. The sidecar is the answer key
for later gates (Report Profiler / Claims Analyst); it is not part of the report itself.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.recalc import recalc  # noqa: E402
from tools.workbook_io import list_names, read_named, write_named  # noqa: E402

MODEL = ROOT / "fixtures" / "global_model.xlsx"
OUT = ROOT / "fixtures" / "global_report_UK.docx"
PROV = ROOT / "fixtures" / "global_report_UK.provenance.json"

# id: (table label, short phrase for narrative, overrides, [(name, fmt, unit text)] shown as setting)
SCENARIOS = {
    "SC1": ("Lower discount rate (costs and outcomes)", "the lower discount rate",
            {"dr_costs": 0.015, "dr_outcomes": 0.015}, [("dr_costs", "pct", "")]),
    "SC2": ("Shorter time horizon", "the shorter time horizon",
            {"time_horizon_years": 20}, [("time_horizon_years", "int", " years")]),
    "SC3": ("Alternative utility values (PF / PD)", "the alternative utility values",
            {"u_pf": 0.72, "u_pd": 0.55}, [("u_pf", "p2", ""), ("u_pd", "p2", "")]),
    "SC4": ("No stopping rule for Drug A (maximum treatment duration)", "removing the stopping rule for Drug A",
            {"int_max_tx_weeks": 2088}, [("int_max_tx_weeks", "int", " weeks")]),
    "SC5": ("Conservative Drug A OS extrapolation (Weibull scale)", "the conservative OS extrapolation",
            {"int_os_scale": 30}, [("int_os_scale", "p2", " months")]),
}

# formatter: (scale, decimals, prefix, suffix)
FMT = {
    "gbp": (1, 0, "£", ""), "qaly": (1, 3, "", ""), "ly": (1, 2, "", ""),
    "pct": (100, 1, "", "%"), "year": (1, 0, "", ""), "m1": (1, 1, "", ""), "p2": (1, 2, "", ""),
    "int": (1, 0, "", ""),
}


class Report:
    def __init__(self, base: dict, scen: dict, refs: dict):
        self.base, self.scen, self.refs = base, scen, refs
        self.doc = Document()
        self.prov: list[dict] = []
        self.claims: list[dict] = []
        self.section = "Title"
        st = self.doc.styles["Normal"]
        st.font.name = "Calibri"
        st.font.size = Pt(11)

    # -- numbers -----------------------------------------------------------
    def n(self, name: str, fmt: str, scenario: str | None = None) -> str:
        vals = self.base if scenario is None else self.scen[scenario]
        v = vals[name]
        if fmt == "text":
            return str(v)
        scale, dec, pre, suf = FMT[fmt]
        x = v * scale
        body = f"{abs(x):.0f}" if fmt == "year" else f"{abs(x):,.{dec}f}"
        disp = f"{'-' if x < 0 and round(abs(x), dec) != 0 else ''}{pre}{body}{suf}"
        sheet, cell = self.refs[name]
        self.prov.append({
            "id": f"N{len(self.prov) + 1:03d}", "section": self.section, "display": disp,
            "value": v, "format": {"scale": scale, "decimals": dec, "prefix": pre, "suffix": suf},
            "source": {"workbook": "fixtures/global_model.xlsx", "name": name, "sheet": sheet,
                       "cell": cell, "scenario": scenario,
                       "overrides": None if scenario is None else SCENARIOS[scenario][2]},
        })
        return disp

    def claim(self, text: str, depends_on: list[str], kind: str):
        self.claims.append({"id": f"C{len(self.claims) + 1:02d}", "section": self.section,
                            "kind": kind, "text": text, "depends_on": depends_on})

    # -- layout ------------------------------------------------------------
    def h(self, text, level=1):
        if level == 1:
            self.section = text
        self.doc.add_heading(text, level=level)

    def p(self, text):
        self.doc.add_paragraph(text)

    def bullets(self, items):
        for t in items:
            self.doc.add_paragraph(t, style="List Bullet")

    def table(self, caption, header, rows):
        cap = self.doc.add_paragraph(caption)
        cap.runs[0].bold = True
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = "Light Grid Accent 1"
        for j, hd in enumerate(header):
            t.rows[0].cells[j].text = hd
        for row in rows:
            cells = t.add_row().cells
            for j, v in enumerate(row):
                cells[j].text = v
        self.doc.add_paragraph()


def scenario_values(tmp: Path) -> dict:
    out = {}
    for sid, (_, _, overrides, _) in SCENARIOS.items():
        src = tmp / f"model_{sid}.xlsx"
        write_named(MODEL, src, overrides)
        out[sid] = read_named(recalc(src, tmp / f"rc_{sid}"))
    return out


def scenario_ranking(base: dict, scen: dict) -> list[str]:
    """Scenario ids ordered by absolute change in ICER from base case (largest first)."""
    return sorted(scen, key=lambda sid: abs(scen[sid]["res_icer"] - base["res_icer"]), reverse=True)


def join_phrases(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def assert_static_narrative(b: dict) -> None:
    """Fixed wording in the report is only valid while these hold; fail loudly otherwise."""
    assert b["res_below_wtp"] == "Yes" and b["res_below_wtp_lower"] == "No", "threshold wording"
    assert b["check_cross_int"] == 0 and b["check_cross_comp"] == 0, "'curves did not cross'"
    assert b["check_lifetime_ok"] == "OK" and b["check_trace_rows_ok"] == "OK", "validation wording"
    inc = {k: b[f"res_inc_cost_{k}"] for k in ("drug", "admin", "pf_state", "pd_state", "terminal", "ae")}
    assert max(inc, key=inc.get) == "pd_state", "'largest contributor ... progressed disease'"
    assert inc["ae"] < 0, "'lower adverse event costs partially offset'"
    assert b["res_dominance"] == "More costly, more effective"


def build(base: dict, scen: dict, refs: dict) -> Report:
    assert_static_narrative(base)
    R = Report(base, scen, refs)
    n = R.n
    d = R.doc

    # Title page --------------------------------------------------------------
    t = d.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Drug A for previously untreated advanced synthetic carcinoma")
    r.bold, r.font.size = True, Pt(20)
    t2 = d.add_paragraph("Cost-effectiveness analysis: technical report (United Kingdom)")
    t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t3 = d.add_paragraph("SYNTHETIC DOCUMENT FOR SOFTWARE TESTING. All data are fictitious. "
                         "Not for clinical, reimbursement or investment decisions.")
    t3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t3.runs[0].italic = True
    d.add_paragraph("Version 1.0 | Global HEOR | Model file: global_model.xlsx").alignment = WD_ALIGN_PARAGRAPH.CENTER
    d.add_page_break()

    # 1 Executive summary -------------------------------------------------------
    R.h("1. Executive summary")
    R.p("This report describes the methods and results of a cost-utility analysis comparing Drug A with "
        "Drug B, a platinum doublet regimen, for adults with previously untreated advanced synthetic "
        "carcinoma, from the perspective of the NHS and Personal Social Services (PSS) in England. The "
        "analysis uses a three-state partitioned survival model with weekly cycles over a lifetime horizon "
        f"of {n('time_horizon_years','int')} years, with costs and outcomes discounted at "
        f"{n('dr_costs','pct')} per annum.")
    R.p(f"In the base case, Drug A was associated with total discounted costs of {n('res_int_total_cost','gbp')} "
        f"and {n('res_int_qaly_disc','qaly')} QALYs, compared with {n('res_comp_total_cost','gbp')} and "
        f"{n('res_comp_qaly_disc','qaly')} QALYs for Drug B. The incremental cost was "
        f"{n('res_inc_total_cost','gbp')} for an incremental gain of {n('res_inc_qaly_disc','qaly')} QALYs, "
        f"giving an incremental cost-effectiveness ratio (ICER) of {n('res_icer','gbp')} per QALY gained.")
    txt = (f"At the upper end of the range normally considered by NICE ({n('wtp_threshold','gbp')} per QALY), "
           f"Drug A is cost-effective, with an incremental net monetary benefit of {n('res_inc_nmb','gbp')}. "
           f"At {n('wtp_threshold_lower','gbp')} per QALY, Drug A is not cost-effective.")
    R.p(txt)
    R.claim("Drug A is cost-effective at the upper NICE threshold", ["res_icer", "wtp_threshold", "res_below_wtp"], "threshold_comparison")
    R.claim("Drug A is not cost-effective at the lower NICE threshold", ["res_icer", "wtp_threshold_lower", "res_below_wtp_lower"], "threshold_comparison")
    rank = scenario_ranking(base, scen)
    R.p(f"In scenario analyses, the ICER was most sensitive to {SCENARIOS[rank[0]][1]} and "
        f"{SCENARIOS[rank[1]][1]} (Section 4.3).")
    R.claim(f"ICER most sensitive to {rank[0]} then {rank[1]}", [f"res_icer@{sid}" for sid in SCENARIOS] + ["res_icer"],
            "sensitivity_ranking")

    # 2 Decision problem --------------------------------------------------------
    R.h("2. Decision problem")
    R.p("Advanced synthetic carcinoma is a fictitious malignancy used here to exercise model-adaptation "
        "software. Patients with advanced disease have a poor prognosis, and first-line systemic therapy with a "
        "platinum doublet is assumed to be the established standard of care in the NHS. Drug A is a "
        f"hypothetical targeted agent administered intravenously every {n('int_admin_interval_weeks','int')} weeks.")
    R.table("Table 1. Decision problem", ["Element", "Base case"], [
        ["Population", "Adults with previously untreated advanced synthetic carcinoma"],
        ["Intervention", f"Drug A, intravenous, every {n('int_admin_interval_weeks','int')} weeks, with a maximum treatment duration"],
        ["Comparator", f"Drug B (platinum doublet), every {n('comp_admin_interval_weeks','int')} weeks, for a fixed number of cycles"],
        ["Outcomes", "Progression-free survival, overall survival, health-related quality of life, costs"],
        ["Perspective", "NHS and PSS"],
        ["Economic evaluation", "Cost-utility analysis; cost per QALY gained"],
    ])
    R.p("The analysis follows the NICE reference case [1]. Health effects are expressed in quality-adjusted "
        "life years (QALYs) using EQ-5D-3L values from the pivotal trial, and costs reflect NHS list prices "
        "and national reference costs. A confidential patient access scheme (PAS) discount is applied to "
        "the price of Drug A in all analyses.")

    # 3 Methods -----------------------------------------------------------------
    R.h("3. Methods")
    R.h("3.1 Model structure", 2)
    R.p("A partitioned survival model with three mutually exclusive health states was developed in "
        "Microsoft Excel: progression-free (PF), progressed disease (PD) and death [2]. The proportion of "
        "patients in each state at each time point is derived directly from the parametric survival "
        "curves for progression-free survival (PFS) and overall survival (OS). The PF proportion is the "
        "lower of the PFS and OS curves, the PD proportion is the difference between OS and PF, and the "
        "proportion dead is the complement of OS. Constraining PF by OS prevents the curves from crossing.")
    R.p(f"The model uses a cycle length of {n('cycle_length_days','int')} days and a time horizon of "
        f"{n('time_horizon_years','int')} years. The mean starting age of {n('baseline_age','int')} years "
        "means that the horizon captures virtually all survival in both arms; the modelled proportion alive "
        f"at the end of the horizon is below {n('lifetime_check_tol','pct')} in each arm.")
    R.p("A half-cycle correction is applied by taking the average of state membership at the start and end "
        "of each cycle (trapezoidal method). Costs and QALYs are discounted using a discount factor evaluated "
        f"at the mid-point of each cycle, with annual rates of {n('dr_costs','pct')} for costs and "
        f"{n('dr_outcomes','pct')} for health outcomes, in line with the reference case.")

    R.h("3.2 Survival extrapolation", 2)
    R.p("Independent Weibull models were fitted to patient-level PFS and OS data from the pivotal trial "
        "for each treatment arm, following the NICE Decision Support Unit guidance on survival analysis [3]. "
        "The Weibull distribution was selected on the basis of statistical fit, visual inspection against "
        "the Kaplan-Meier curves, and the clinical plausibility of long-term extrapolations. The survival "
        "function is parameterised as S(t) = exp(-(t/scale)^shape), with time in months.")
    R.table("Table 2. Weibull parameters and modelled medians", [
        "Arm and endpoint", "Shape", "Scale (months)", "Median (months)"], [
        ["Drug A, PFS", n("int_pfs_shape", "p2"), n("int_pfs_scale", "p2"), n("res_int_median_pfs", "m1")],
        ["Drug A, OS", n("int_os_shape", "p2"), n("int_os_scale", "p2"), n("res_int_median_os", "m1")],
        ["Drug B, PFS", n("comp_pfs_shape", "p2"), n("comp_pfs_scale", "p2"), n("res_comp_median_pfs", "m1")],
        ["Drug B, OS", n("comp_os_shape", "p2"), n("comp_os_scale", "p2"), n("res_comp_median_os", "m1")],
    ])
    R.p(f"Modelled median OS was {n('res_int_median_os','m1')} months with Drug A and "
        f"{n('res_comp_median_os','m1')} months with Drug B. Modelled median PFS was "
        f"{n('res_int_median_pfs','m1')} and {n('res_comp_median_pfs','m1')} months, respectively. "
        "The modelled curves did not cross in either arm.")
    R.claim("Modelled PFS and OS curves do not cross", ["check_cross_int", "check_cross_comp"], "model_check")

    R.h("3.3 Treatment duration", 2)
    R.p("Treatment duration was assumed to follow PFS, so patients receive treatment while progression-free. "
        f"Drug A is given every {n('int_admin_interval_weeks','int')} weeks until progression or for a maximum of "
        f"{n('int_max_tx_weeks','int')} weeks, consistent with the stopping rule in the trial protocol. Drug B "
        f"is given every {n('comp_admin_interval_weeks','int')} weeks for a maximum of "
        f"{n('comp_max_tx_weeks','int')} weeks. Acquisition and administration costs per administration are "
        "spread evenly over the weeks of each dosing interval.")

    R.h("3.4 Costs and resource use", 2)
    R.p("Drug acquisition costs for Drug A reflect the list price net of the confidential PAS discount. "
        "The cost of Drug B was taken from the electronic market information tool (eMIT). Administration "
        "costs per intravenous infusion are based on NHS reference costs. Health state costs comprise "
        "outpatient visits, imaging, blood tests and community care, valued using PSSRU unit costs. A one-off "
        "terminal care cost is applied at death.")
    R.p(f"All costs are in {n('currency_code','text')} at {n('price_year','year')} prices.")
    R.table("Table 3. Cost inputs", ["Input", "Value", "Unit"], [
        ["Drug A net price per administration", n("int_drug_cost_per_admin", "gbp"), "per administration"],
        ["Drug B price per administration", n("comp_drug_cost_per_admin", "gbp"), "per administration"],
        ["Administration cost, Drug A", n("int_admin_cost_per_admin", "gbp"), "per administration"],
        ["Administration cost, Drug B", n("comp_admin_cost_per_admin", "gbp"), "per administration"],
        ["Progression-free health state", n("c_pf_week", "gbp"), "per week"],
        ["Progressed disease health state", n("c_pd_week", "gbp"), "per week"],
        ["Terminal care", n("c_terminal", "gbp"), "one-off"],
        ["Adverse events, Drug A", n("int_ae_cost", "gbp"), "one-off"],
        ["Adverse events, Drug B", n("comp_ae_cost", "gbp"), "one-off"],
    ])

    R.h("3.5 Health-related quality of life", 2)
    R.p("Health state utility values were derived from EQ-5D-3L questionnaires collected in the pivotal "
        "trial and valued using the UK time trade-off value set, consistent with the NICE reference case. "
        "Utilities were assumed to depend on health state only and not on treatment. Quality-of-life losses "
        "associated with severe (grade three or higher) adverse events were applied as one-off QALY decrements at the "
        "start of the model.")
    R.table("Table 4. Utility inputs", ["Input", "Value"], [
        ["Progression-free", n("u_pf", "p2")],
        ["Progressed disease", n("u_pd", "p2")],
        ["AE QALY loss, Drug A", n("int_ae_qaly_loss", "qaly")],
        ["AE QALY loss, Drug B", n("comp_ae_qaly_loss", "qaly")],
    ])

    R.h("3.6 Uncertainty", 2)
    R.p("Structural and parameter uncertainty were explored through pre-specified scenario analyses "
        "(Table 7). Probabilistic sensitivity analysis (PSA) is specified in the model, with gamma "
        "distributions for costs, beta distributions for utilities and correlated multivariate normal "
        "distributions for the log-transformed Weibull parameters. PSA results are not included in this "
        "version of the report and will be provided in an addendum.")
    R.claim("PSA results not reported in this version", [], "scope_statement")

    # 4 Results -----------------------------------------------------------------
    R.h("4. Results")
    R.h("4.1 Base-case results", 2)
    R.p(f"Drug A increased discounted life years by {n('res_inc_ly_disc','ly')} and QALYs by "
        f"{n('res_inc_qaly_disc','qaly')} compared with Drug B, at an additional cost of "
        f"{n('res_inc_total_cost','gbp')}. The base-case ICER is {n('res_icer','gbp')} per QALY gained "
        f"and {n('res_icer_ly','gbp')} per life year gained.")
    R.table("Table 5. Base-case results (discounted)", ["Outcome", "Drug A", "Drug B", "Incremental"], [
        ["Total costs", n("res_int_total_cost", "gbp"), n("res_comp_total_cost", "gbp"), n("res_inc_total_cost", "gbp")],
        ["Life years", n("res_int_ly_disc", "ly"), n("res_comp_ly_disc", "ly"), n("res_inc_ly_disc", "ly")],
        ["QALYs", n("res_int_qaly_disc", "qaly"), n("res_comp_qaly_disc", "qaly"), n("res_inc_qaly_disc", "qaly")],
        ["ICER (cost per QALY gained)", "", "", n("res_icer", "gbp")],
        ["Incremental NMB at upper threshold", "", "", n("res_inc_nmb", "gbp")],
    ])
    R.p(f"Undiscounted, Drug A provided {n('res_int_ly_undisc','ly')} life years versus "
        f"{n('res_comp_ly_undisc','ly')} with Drug B.")

    R.h("4.2 Disaggregated costs", 2)
    R.p(f"Drug acquisition accounted for {n('res_int_drug_share','pct')} of total costs in the Drug A arm, "
        f"compared with {n('res_comp_drug_share','pct')} in the Drug B arm. The largest single contributor to "
        f"incremental costs was the progressed disease state ({n('res_inc_cost_pd_state','gbp')}), reflecting "
        "longer post-progression survival with Drug A. Lower adverse event costs partially offset the higher "
        "acquisition and administration costs of Drug A.")
    R.claim("PD state cost is the largest contributor to incremental costs",
            ["res_inc_cost_drug", "res_inc_cost_admin", "res_inc_cost_pf_state", "res_inc_cost_pd_state",
             "res_inc_cost_terminal", "res_inc_cost_ae"], "ranking")
    rows = []
    for key, label in [("cost_drug", "Drug acquisition"), ("cost_admin", "Administration"),
                       ("cost_pf_state", "Progression-free state"), ("cost_pd_state", "Progressed disease state"),
                       ("cost_terminal", "Terminal care"), ("cost_ae", "Adverse events"),
                       ("total_cost", "Total")]:
        rows.append([label, n(f"res_int_{key}", "gbp"), n(f"res_comp_{key}", "gbp"), n(f"res_inc_{key}", "gbp")])
    R.table("Table 6. Disaggregated discounted costs (GBP)", ["Category", "Drug A", "Drug B", "Incremental"], rows)

    R.h("4.3 Scenario analyses", 2)
    lower = [sid for sid in SCENARIOS if scen[sid]["res_icer"] < base["res_icer"]]
    R.p(f"Table 7 presents the results of the scenario analyses. {SCENARIOS[rank[0]][1][0].upper() + SCENARIOS[rank[0]][1][1:]} had "
        f"the largest effect on the ICER, followed by {SCENARIOS[rank[1]][1]} and {SCENARIOS[rank[2]][1]}. "
        + (f"The ICER was lower than in the base case only with {join_phrases([SCENARIOS[s_][1] for s_ in lower])}."
           if lower else "No scenario reduced the ICER below the base case."))
    R.claim(f"Scenario ranking by ICER change: {rank}; ICER lower than base only in {lower}",
            [f"res_icer@{sid}" for sid in SCENARIOS] + ["res_icer"], "sensitivity_ranking")
    srows = [["Base case", "-", n("res_inc_total_cost", "gbp"), n("res_inc_qaly_disc", "qaly"), n("res_icer", "gbp")]]
    for sid, (label, _, _, setting) in SCENARIOS.items():
        shown = " / ".join(n(name, fmt, sid) + unit for name, fmt, unit in setting)
        srows.append([label, shown, n("res_inc_total_cost", "gbp", sid), n("res_inc_qaly_disc", "qaly", sid),
                      n("res_icer", "gbp", sid)])
    R.table("Table 7. Scenario analyses",
            ["Scenario", "Setting", "Incremental costs", "Incremental QALYs", "ICER"], srows)
    above = [sid for sid in SCENARIOS if scen[sid]["res_below_wtp"] != "Yes"]
    if above:
        R.p(f"The ICER exceeded {n('wtp_threshold','gbp')} per QALY with "
            + join_phrases([f"{SCENARIOS[sid][1]} ({n('res_icer','gbp',sid)})" for sid in above])
            + ", and remained below it in all other scenarios.")
    else:
        R.p(f"The ICER remained below {n('wtp_threshold','gbp')} per QALY in all scenarios.")
    R.claim(f"ICER above upper threshold only in {above}",
            [f"res_below_wtp@{sid}" for sid in SCENARIOS] + ["wtp_threshold"], "threshold_comparison")

    # 5 Validation ---------------------------------------------------------------
    R.h("5. Model validation")
    R.p("The model was quality-assured using a checklist covering input transcription, formula "
        "consistency between arms, and extreme-value testing. Both treatment arms use identical formula "
        "layouts that differ only in the arm-specific parameter block. State membership sums to one in every "
        "cycle by construction. The time horizon is sufficient for the modelled cohort, with fewer than "
        f"{n('lifetime_check_tol','pct')} of patients in either arm alive at the end of the horizon. The deterministic results were reproduced to "
        "within numerical precision by an independent implementation of the model in Python.")
    R.p("Face validity was assessed by comparing modelled medians with the trial Kaplan-Meier estimates. "
        "Modelled medians were within the confidence intervals of the observed medians for all four curves.")
    R.claim("Modelled medians within trial KM CIs", [], "external_assertion_untraceable")

    # 6 Discussion ---------------------------------------------------------------
    R.h("6. Discussion")
    R.p("The analysis indicates that Drug A provides substantial health gains relative to Drug B, driven "
        "mainly by longer overall survival. The additional costs arise from drug acquisition and "
        "administration during the treatment period and from health state costs accumulated over the "
        "longer survival period.")
    R.p("Several limitations should be noted.")
    R.bullets([
        "Independent Weibull models were fitted to each arm. Alternative distributions were not explored "
        "in this version of the report, and long-term extrapolation of OS is the main source of structural "
        "uncertainty.",
        "Treatment duration was assumed to equal PFS, capped by the stopping rule. Time-on-treatment data "
        "would provide a more accurate estimate of drug costs.",
        "General population mortality was not applied as a constraint on modelled survival; given the low "
        "proportion of patients alive in the long term, the impact is expected to be small.",
        "Utilities were not adjusted for age.",
        "The partitioned survival structure does not explicitly model the relationship between progression and "
        "death, as discussed in NICE DSU guidance [2].",
    ])
    R.p("The base-case ICER lies close to the upper end of the threshold range, so several plausible "
        "scenarios move it above that threshold. The stopping rule is a key assumption and should be "
        "reflected in the commissioning arrangements for Drug A.")

    # 7 Conclusion ---------------------------------------------------------------
    R.h("7. Conclusion")
    R.p(f"Drug A is associated with an ICER of {n('res_icer','gbp')} per QALY gained compared with Drug B. "
        f"This is below the threshold of {n('wtp_threshold','gbp')} per QALY gained and within the range "
        f"of {n('wtp_threshold_lower','gbp')} to {n('wtp_threshold','gbp')} per QALY that NICE normally "
        "considers to represent a cost-effective use of NHS resources. Drug A can therefore be considered a "
        "cost-effective option for adults with previously untreated advanced synthetic carcinoma in the NHS, "
        "with the PAS discount and the stopping rule in place.")
    R.claim("Drug A is a cost-effective use of NHS resources", ["res_icer", "wtp_threshold", "wtp_threshold_lower"],
            "overall_conclusion")

    # References -----------------------------------------------------------------
    R.h("References")
    for ref in [
        "[1] National Institute for Health and Care Excellence. NICE health technology evaluations: the manual (PMG36). 2022.",
        "[2] Woods B, Sideris E, Palmer S, Latimer N, Soares M. NICE DSU Technical Support Document 19: "
        "Partitioned survival analysis for decision modelling in health care: a critical review. 2017.",
        "[3] Latimer N. NICE DSU Technical Support Document 14: Survival analysis for economic evaluations "
        "alongside clinical trials. 2011 (updated 2013).",
    ]:
        R.p(ref)
    return R


def main():
    refs = list_names(MODEL)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base = read_named(recalc(MODEL, tmp / "rc_base"))
        scen = scenario_values(tmp)
    R = build(base, scen, refs)
    R.doc.save(OUT)
    PROV.write_text(json.dumps({
        "document": "fixtures/global_report_UK.docx",
        "model": "fixtures/global_model.xlsx",
        "note": "Answer key for synthetic fixture. Each display string is formatted from the named cell "
                "after LibreOffice recalculation (scenario overrides applied where stated).",
        "scenarios": {k: {"label": v[0], "overrides": v[2]} for k, v in SCENARIOS.items()},
        "numbers": R.prov,
        "claims": R.claims,
    }, indent=2))
    print(f"wrote {OUT} ({len(R.prov)} numbers, {len(R.claims)} claims)")


if __name__ == "__main__":
    main()
