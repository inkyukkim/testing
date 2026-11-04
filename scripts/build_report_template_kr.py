"""Generate fixtures/report_template_KR.docx + .sidecar.yaml: the expected Report Writer output.

Run:  python scripts/build_report_template_kr.py
The template adapts the UK report to the KR claims register (fixtures/claims_register_KR.json):
jurisdiction-specific wording replaced (reword), the PAS and lower-bound statements dropped
(remove), truth-dependent sentences wrapped in {{if}}/{{ifnot}} on their claim, data-driven
sentences regenerated from claim evaluations, and open reviews marked with {{review}}.
It contains no numerals; tools/render_report.py supplies every number. SYNTHETIC.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "report_template_KR.docx"
SIDECAR = ROOT / "fixtures" / "report_template_KR.sidecar.yaml"

LABELS = {
    "res_inc_cost_drug": "drug acquisition", "res_inc_cost_admin": "administration",
    "res_inc_cost_pf_state": "progression-free state", "res_inc_cost_pd_state": "progressed disease state",
    "res_inc_cost_terminal": "terminal care", "res_inc_cost_st": "subsequent therapy",
    "res_inc_cost_ae": "adverse event",
}


def build():
    d = Document()
    st = d.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(11)
    h = lambda t, lvl=1: d.add_heading(t, level=lvl)
    p = lambda t: d.add_paragraph(t)

    def table(caption, header, rows):
        c = d.add_paragraph(caption)
        c.runs[0].bold = True
        t = d.add_table(rows=1, cols=len(header))
        t.style = "Light Grid Accent 1"
        for j, x in enumerate(header):
            t.rows[0].cells[j].text = x
        for row in rows:
            cells = t.add_row().cells
            for j, x in enumerate(row):
                cells[j].text = x
        d.add_paragraph()

    t = d.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Drug A for previously untreated advanced synthetic carcinoma")
    r.bold, r.font.size = True, Pt(20)
    d.add_paragraph("Cost-effectiveness analysis: technical report (Republic of Korea)").alignment = WD_ALIGN_PARAGRAPH.CENTER
    n = d.add_paragraph("SYNTHETIC DOCUMENT FOR SOFTWARE TESTING. All data are fictitious.")
    n.alignment = WD_ALIGN_PARAGRAPH.CENTER
    d.add_paragraph("{{draft_banner}}")
    d.add_page_break()

    h("1. Executive summary")
    p("This report describes a cost-utility analysis comparing Drug A with Drug B for adults with previously "
      "untreated advanced synthetic carcinoma, adapted to Korea from the global model. The analysis takes the "
      "perspective of the {{text perspective}}. It uses a three-state partitioned survival model with weekly cycles "
      "over a lifetime horizon of {{time_horizon_years|int}} years, with costs and outcomes discounted at "
      "{{dr_costs|pct}} per annum.")
    p("In the base case, Drug A was associated with total discounted costs of {{res_int_total_cost|money}} and "
      "{{res_int_qaly_disc|qaly}} QALYs, compared with {{res_comp_total_cost|money}} and {{res_comp_qaly_disc|qaly}} "
      "QALYs for Drug B. The incremental cost was {{res_inc_total_cost|money}} for an incremental gain of "
      "{{res_inc_qaly_disc|qaly}} QALYs, giving an incremental cost-effectiveness ratio (ICER) of "
      "{{res_icer|money}} per QALY gained.")
    p("{{if C02}}At the reference value of {{wtp_threshold|money}} per QALY used in this analysis, Drug A is "
      "cost-effective, with an incremental net monetary benefit of {{res_inc_nmb|money}}.{{endif}}"
      "{{ifnot C02}}At the reference value of {{wtp_threshold|money}} per QALY used in this analysis, Drug A is "
      "not cost-effective.{{endif}} The reference value is not an official threshold.")
    p("Scenario analyses for the Korean setting have not yet been specified {{review C04}}.")

    h("2. Decision problem")
    p("Advanced synthetic carcinoma is a fictitious malignancy used to exercise model-adaptation software. "
      "Drug B, a platinum doublet, is the comparator in the pivotal trial {{review C05}}. Drug A is administered "
      "intravenously every {{int_admin_interval_weeks|int}} weeks.")
    table("Table 1. Decision problem", ["Element", "Base case"], [
        ["Population", "Adults with previously untreated advanced synthetic carcinoma"],
        ["Intervention", "Drug A, intravenous, every {{int_admin_interval_weeks|int}} weeks, within the reimbursed maximum duration"],
        ["Comparator", "Drug B (platinum doublet), every {{comp_admin_interval_weeks|int}} weeks, for a fixed number of cycles"],
        ["Perspective", "{{text perspective}}"],
        ["Economic evaluation", "Cost-utility analysis; cost per QALY gained"],
    ])
    p("The analysis follows the local pharmacoeconomic guideline. Costs are Korean list prices and fee-schedule "
      "and claims-based unit costs; no risk-sharing agreement is applied. Health state utilities use the Korean "
      "EQ-5D-5L value set.")

    h("3. Methods")
    h("3.1 Model structure", 2)
    p("A partitioned survival model with three health states (progression-free, progressed disease and death) "
      "was used. The model uses a cycle length of {{cycle_length_days|int}} days and a time horizon of "
      "{{time_horizon_years|int}} years; fewer than {{lifetime_check_tol|pct}} of patients in either arm are "
      "alive at the end of the horizon. The modelled cohort has the trial's mean starting age of "
      "{{baseline_age|int}} years and is {{prop_male|pct}} male.")
    p("Modelled survival is constrained so that the risk of death is never lower than in the Korean general "
      "population of the same age and sex. The Korean life table is published as central death rates; these "
      "were converted to annual probabilities of death assuming a constant hazard within each year of age, and "
      "the rate of the open top-age band was applied to older ages.")
    p("A half-cycle correction is applied to state membership for health state costs, life years and QALYs. "
      "Costs and outcomes are discounted at annual rates of {{dr_costs|pct}} and {{dr_outcomes|pct}}, "
      "following the local guideline.")
    h("3.2 Survival extrapolation", 2)
    p("Independent Weibull models fitted to the pivotal trial were retained from the global model, following "
      "published guidance on survival analysis for economic evaluation [2]. Efficacy is assumed to transfer "
      "to Korean patients.")
    table("Table 2. Weibull parameters (retained global inputs)", ["Arm and endpoint", "Shape", "Scale (months)"], [
        [f"{al}, {el}", f"{{{{{a}_{e}_shape|p2}}}}", f"{{{{{a}_{e}_scale|p2}}}}"]
        for a, al in (("int", "Drug A"), ("comp", "Drug B")) for e, el in (("pfs", "PFS"), ("os", "OS"), ("tot", "ToT"))
    ])
    p("{{if C09}}The fitted PFS and OS curves did not cross in either arm.{{endif}}"
      "{{ifnot C09}}The fitted PFS and OS curves crossed and PF was capped by OS.{{endif}}")
    h("3.3 Treatment duration and dosing", 2)
    p("Drug A is given every {{int_admin_interval_weeks|int}} weeks for a maximum of {{int_max_doses|int}} doses, "
      "the doses that start within the reimbursed maximum treatment duration. Drug B is given for a maximum of "
      "{{comp_max_doses|int}} doses. Drug A is dosed at {{int_dose_mg|p2}} mg/kg; the expected number of vials per "
      "administration ({{res_int_expected_vials|p2}}) assumes no vial sharing and a lognormal body weight "
      "distribution with mean {{weight_mean_kg|kg}} kg and standard deviation {{weight_sd_kg|kg}} kg from a "
      "Korean registry. Relative dose intensity is retained from the trial.")
    h("3.4 Costs", 2)
    p("All costs are in {{text currency_code}} at {{price_year|year}} prices. Drug prices are Korean list prices "
      "per vial. Administration costs are the chemotherapy infusion fee. Health state costs were derived from "
      "monthly claims-based costs converted to weekly costs.")
    table("Table 3. Cost inputs", ["Input", "Value", "Unit"], [
        ["Drug A price per vial", "{{int_vial_price|money}}", "per vial"],
        ["Drug A drug cost per administration (expected vials)", "{{res_int_drug_cost_per_admin|money}}", "per administration"],
        ["Drug B price per vial", "{{comp_vial_price|money}}", "per vial"],
        ["Infusion fee", "{{int_admin_cost_per_admin|money}}", "per administration"],
        ["Progression-free health state", "{{c_pf_week|money}}", "per week"],
        ["Progressed disease health state", "{{c_pd_week|money}}", "per week"],
        ["Terminal care", "{{c_terminal|money}}", "one-off"],
        ["Adverse events, Drug A", "{{int_ae_cost|money}}", "one-off"],
        ["Adverse events, Drug B", "{{comp_ae_cost|money}}", "one-off"],
    ])
    h("3.5 Health-related quality of life", 2)
    p("State utilities use the Korean EQ-5D-5L value set ({{u_pf|p2}} progression-free, {{u_pd|p2}} progressed "
      "disease). Adverse-event QALY losses and the population norms used for the age adjustment are retained "
      "from the global model and were valued with a different value set; both are flagged for review.")
    h("3.6 Uncertainty", 2)
    p("Probabilistic sensitivity analysis results are not included in this version and will be provided in an "
      "addendum. The Korean scenario set is to be specified {{review C17}}.")

    h("4. Results")
    h("4.1 Base-case results", 2)
    table("Table 4. Base-case results (discounted)", ["Outcome", "Drug A", "Drug B", "Incremental"], [
        ["Total costs", "{{res_int_total_cost|money}}", "{{res_comp_total_cost|money}}", "{{res_inc_total_cost|money}}"],
        ["Life years", "{{res_int_ly_disc|ly}}", "{{res_comp_ly_disc|ly}}", "{{res_inc_ly_disc|ly}}"],
        ["QALYs", "{{res_int_qaly_disc|qaly}}", "{{res_comp_qaly_disc|qaly}}", "{{res_inc_qaly_disc|qaly}}"],
        ["ICER (cost per QALY gained)", "", "", "{{res_icer|money}}"],
    ])
    d.add_paragraph("{{rounding_note}}")
    h("4.2 Disaggregated costs", 2)
    p("The largest single contributor to incremental costs was {{label C15}} ({{value_of C15|money}})."
      "{{ifany C16}} Lower {{labels C16}} costs with Drug A partially offset its higher costs in other "
      "categories.{{endif}}")
    table("Table 5. Disaggregated discounted costs", ["Category", "Drug A", "Drug B", "Incremental"], [
        [lab.capitalize() if k != "drug" else "Drug acquisition", f"{{{{res_int_cost_{k}|money}}}}",
         f"{{{{res_comp_cost_{k}|money}}}}", f"{{{{res_inc_cost_{k}|money}}}}"]
        for k, lab in (("drug", ""), ("admin", "administration"), ("pf_state", "progression-free state"),
                       ("pd_state", "progressed disease state"), ("terminal", "terminal care"),
                       ("st", "subsequent therapy"), ("ae", "adverse events"))
    ] + [["Total", "{{res_int_total_cost|money}}", "{{res_comp_total_cost|money}}", "{{res_inc_total_cost|money}}"]])

    h("5. Model validation")
    p("The adapted model was verified against the global model (identical formulas, only mapped inputs changed) "
      "and reproduced by an independent implementation. The effect of the general-population mortality "
      "constraint under the Korean life table is to be assessed {{review C19}}. Agreement of modelled medians "
      "with the trial Kaplan-Meier estimates {{review C20}}.")

    h("6. Discussion")
    p("Several limitations should be noted.")
    for t in ["Efficacy, time on treatment and dose intensity are retained from the global trial.",
              "Adverse-event QALY losses and population utility norms come from a different value set than the "
              "Korean state utilities.",
              "The cohort's age and sex are those of the trial, while mortality and norms are Korean.",
              "Ages above the open top band of the Korean life table use that band's rate."]:
        d.add_paragraph(t, style="List Bullet")
    p("Inputs retained from the global model:")
    d.add_paragraph("{{retained_inputs}}")
    p("The reimbursed maximum treatment duration for Drug A is a key assumption and should be reflected in the "
      "reimbursement criteria.")

    h("7. Conclusion")
    p("Drug A is associated with an ICER of {{res_icer|money}} per QALY gained compared with Drug B. "
      "{{if C22}}This is below the reference value of {{wtp_threshold|money}} per QALY used in this analysis.{{endif}}"
      "{{ifnot C22}}This is above the reference value of {{wtp_threshold|money}} per QALY used in this analysis.{{endif}}")

    h("References")
    for ref in ["[1] Local pharmacoeconomic evaluation guideline (synthetic placeholder).",
                "[2] Latimer N. NICE DSU Technical Support Document 14: Survival analysis for economic evaluations "
                "alongside clinical trials. 2011 (updated 2013)."]:
        p(ref)
    d.save(OUT)
    SIDECAR.write_text(yaml.safe_dump({
        "note": "Sidecar of report_template_KR.docx: labels for regenerated phrases (words only, no numbers).",
        "claims_register": "fixtures/claims_register_KR.json",
        "labels": LABELS,
    }, sort_keys=False))
    print(f"wrote {OUT} and {SIDECAR}")


if __name__ == "__main__":
    build()
