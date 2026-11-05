"""Build work/report_template_KR.docx and its sidecar (Report Writer, KR adaptation).

Run from the workspace root:  python -m work.build_template_KR
The template holds prose and directives only; every number is a placeholder resolved by
tools/render_report.py. Styles are taken from the global report (opened read-only).
"""
from pathlib import Path

import yaml
from docx import Document
from docx.shared import Pt

SRC = "fixtures/global_report_UK.docx"
OUT = Path("work/report_template_KR.docx")
SIDECAR = Path("work/report_template_KR.sidecar.yaml")

doc = Document(SRC)
body = doc.element.body
for el in list(body.iterchildren()):
    if not el.tag.endswith("}sectPr"):
        body.remove(el)
TABLE_STYLE = "Light Grid Accent 1"


def P(text, style=None, bold=False):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    r.bold = bold
    return p


def H1(text):
    doc.add_heading(text, level=1)


def H2(text):
    doc.add_heading(text, level=2)


def T(caption, header, rows):
    P(caption, style="Caption")
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.style = TABLE_STYLE
    for j, h in enumerate(header):
        t.rows[0].cells[j].text = h
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            t.rows[i].cells[j].text = v
    return t


# ---------------------------------------------------------------- title page
P("Drug A for previously untreated advanced synthetic carcinoma", bold=True)
P("Cost-effectiveness analysis: technical report ({{text country}})")
P("SYNTHETIC DOCUMENT FOR SOFTWARE TESTING. All data are fictitious. Not for clinical, "
  "reimbursement or investment decisions.")
P("Local adaptation of the global model | Model run: runs/kr_test (adapted_model.xlsx)")
P("{{draft_banner}}")

# ---------------------------------------------------------------- 1. Executive summary
H1("1. Executive summary")
P("This report describes the methods and results of a cost-utility analysis comparing Drug A with "
  "Drug B, a platinum doublet regimen, for adults with previously untreated advanced synthetic "
  "carcinoma in the {{text country}}. The analysis takes the perspective specified for the local "
  "setting (KR-S04): {{text perspective}}. It uses a three-state partitioned survival model with "
  "weekly cycles over a lifetime horizon of {{time_horizon_years|int}} years, with costs discounted "
  "at {{dr_costs|pct}} and outcomes at {{dr_outcomes|pct}} per annum.")
P("In the base case, Drug A was associated with total discounted costs of {{res_int_total_cost|money}} "
  "and {{res_int_qaly_disc|qaly}} QALYs, compared with {{res_comp_total_cost|money}} and "
  "{{res_comp_qaly_disc|qaly}} QALYs for Drug B. The incremental cost was {{res_inc_total_cost|money}} "
  "for an incremental gain of {{res_inc_qaly_disc|qaly}} QALYs, giving an incremental "
  "cost-effectiveness ratio (ICER) of {{res_icer|money}} per QALY gained.")
P("The local decision rule is a single reference value of {{wtp_threshold|money}} per QALY gained "
  "(KR-S07); it is not an official threshold. "
  "{{if C02}}At this reference value, Drug A is cost-effective, with an incremental net monetary "
  "benefit of {{res_inc_nmb|money}}.{{endif}}"
  "{{ifnot C02}}At this reference value, Drug A is not cost-effective; the incremental net monetary "
  "benefit is {{res_inc_nmb|money}}.{{endif}}")
P("No scenario set has yet been specified for the Korean setting, so the sensitivity of the ICER to "
  "key assumptions is not reported in this draft {{review C04}}.")

# ---------------------------------------------------------------- 2. Decision problem
H1("2. Decision problem")
P("Advanced synthetic carcinoma is a fictitious malignancy used here to exercise model-adaptation "
  "software. Patients with advanced disease have a poor prognosis. The comparator is first-line "
  "systemic therapy with a platinum doublet (Drug B); whether this reflects the standard of care in "
  "Korean practice has not been confirmed by local clinicians {{review C05}}. Drug A is a "
  "hypothetical targeted agent administered intravenously every {{int_admin_interval_weeks|int}} weeks.")
T("Table 1. Decision problem", ["Element", "Base case"], [
    ["Population", "Adults with previously untreated advanced synthetic carcinoma"],
    ["Intervention", "Drug A, intravenous, every {{int_admin_interval_weeks|int}} weeks, with a maximum "
                     "treatment duration set by the local reimbursement criteria (KR-C05)"],
    ["Comparator", "Drug B (platinum doublet), every {{comp_admin_interval_weeks|int}} weeks, for a fixed "
                   "number of cycles"],
    ["Outcomes", "Progression-free survival, overall survival, health-related quality of life, costs"],
    ["Perspective", "{{text perspective}}"],
    ["Economic evaluation", "Cost-utility analysis; cost per QALY gained"],
])
P("The analysis follows the local pharmacoeconomic guideline [1], represented in this adaptation by a "
  "synthetic placeholder, and the perspective stated in local item KR-S04. Health effects are expressed "
  "in quality-adjusted life years (QALYs), with health state utilities valued using the Korean EQ-5D-5L "
  "value set, and costs reflect Korean list prices and local unit costs (Section 3.4).")

# ---------------------------------------------------------------- 3. Methods
H1("3. Methods")
H2("3.1 Model structure")
P("A partitioned survival model with three mutually exclusive health states was developed in Microsoft "
  "Excel: progression-free (PF), progressed disease (PD) and death [2]. The proportion of patients in "
  "each state at each time point is derived directly from the parametric survival curves for "
  "progression-free survival (PFS) and overall survival (OS). The PF proportion is the lower of the PFS "
  "and OS curves, the PD proportion is the difference between OS and PF, and the proportion dead is the "
  "complement of OS.")
P("The model uses a cycle length of {{cycle_length_days|int}} days and a time horizon of "
  "{{time_horizon_years|int}} years, retained from the global model as structural settings. The "
  "modelled cohort has a mean starting age of {{baseline_age|int}} years and is {{prop_male|pct}} male; "
  "both characteristics are those of the trial population, because local values were not supplied "
  "(GAP-005). The model's lifetime check, which requires the proportion alive at the end of the "
  "horizon to be below {{lifetime_check_tol|pct}} in each arm, reports: {{text check_lifetime_ok}}.")
P("Modelled survival is constrained so that the risk of death is never lower than in the general "
  "population of the same age and sex. In each cycle, the conditional probability of surviving the "
  "cycle is taken as the lower of the value implied by the fitted curve and the value implied by the "
  "Korean national life table (KR-L01, KR-L02), applied separately to the PFS and OS curves. The life "
  "table is published as central death rates; these were converted to probabilities by the declared "
  "exponential method, and the rate of the open top-age band was carried to the oldest model ages "
  "(GAP-004). General-population survival is calculated separately for men and women and weighted by "
  "the proportion of men at baseline.")
P("A half-cycle correction is applied to state membership by taking the average of the start and end "
  "of each cycle (trapezoidal method); it is used for health state costs, life years and QALYs. Drug "
  "acquisition and administration costs are incurred at the time of each dose and are not half-cycle "
  "corrected. Costs and outcomes are discounted at annual rates of {{dr_costs|pct}} and "
  "{{dr_outcomes|pct}} respectively, as set out in the local guideline (KR-S05, KR-S06), using a "
  "discount factor evaluated at the mid-point of each cycle, or at the time of administration for "
  "dosing costs.")

H2("3.2 Survival extrapolation")
P("Independent Weibull models were fitted to patient-level PFS, OS and time on treatment (ToT) data "
  "from the pivotal trial for each treatment arm, following published technical guidance on survival "
  "analysis for economic evaluation [3] and the survival-analysis expectations of the local guideline "
  "[1]. The Weibull distribution was selected on the basis of statistical fit, visual inspection "
  "against the Kaplan-Meier curves, and the clinical plausibility of long-term extrapolations. The "
  "survival function is parameterised as S(t) = exp(-(t/scale)^shape), with time in months. The "
  "survival and time-on-treatment parameters are retained from the global trial analysis (GAP-006). "
  "Medians in Table 2 are those of the fitted curves before the general-population constraint.")
T("Table 2. Weibull parameters and medians of the fitted curves",
  ["Arm and endpoint", "Shape", "Scale (months)", "Median (months)"], [
    ["Drug A, PFS", "{{int_pfs_shape|p2}}", "{{int_pfs_scale|p2}}", "{{res_int_median_pfs|m1}}"],
    ["Drug A, OS", "{{int_os_shape|p2}}", "{{int_os_scale|p2}}", "{{res_int_median_os|m1}}"],
    ["Drug A, ToT", "{{int_tot_shape|p2}}", "{{int_tot_scale|p2}}", "{{res_int_median_tot|m1}}"],
    ["Drug B, PFS", "{{comp_pfs_shape|p2}}", "{{comp_pfs_scale|p2}}", "{{res_comp_median_pfs|m1}}"],
    ["Drug B, OS", "{{comp_os_shape|p2}}", "{{comp_os_scale|p2}}", "{{res_comp_median_os|m1}}"],
    ["Drug B, ToT", "{{comp_tot_shape|p2}}", "{{comp_tot_scale|p2}}", "{{res_comp_median_tot|m1}}"],
])
P("Median OS of the fitted curves was {{res_int_median_os|m1}} months with Drug A and "
  "{{res_comp_median_os|m1}} months with Drug B. Median PFS was {{res_int_median_pfs|m1}} and "
  "{{res_comp_median_pfs|m1}} months, respectively. "
  "{{if C09}}The fitted PFS and OS curves did not cross in either arm.{{endif}}"
  "{{ifnot C09}}The fitted PFS and OS curves crossed in at least one arm.{{endif}}")

H2("3.3 Treatment duration and dosing")
P("Treatment duration is modelled with the ToT curves, constrained not to exceed OS, so patients may "
  "continue treatment after progression as observed in the trial. Doses are given at fixed intervals "
  "and costed only in the weeks in which a dose is due, for the proportion of patients on treatment at "
  "the start of that week. Drug A is given every {{int_admin_interval_weeks|int}} weeks for a maximum "
  "of {{int_max_doses|int}} doses, derived from the maximum reimbursed treatment duration in the local "
  "reimbursement criteria (KR-C05) by counting the doses that start within that duration. Drug B is "
  "given every {{comp_admin_interval_weeks|int}} weeks for a maximum of {{comp_max_doses|int}} doses "
  "(KR-C07).")
P("Drug A is dosed at {{int_dose_mg|p2}} mg/kg, as in the Korean label (KR-C02). The expected number "
  "of vials per administration ({{res_int_expected_vials|p2}}) accounts for wastage, assuming no vial "
  "sharing and a lognormal distribution of body weight with mean {{weight_mean_kg|kg}} kg and standard "
  "deviation {{weight_sd_kg|kg}} kg, taken from the Korean cancer registry source supplied by the local "
  "affiliate (KR-P01, KR-P02). Drug B is given at a flat dose of {{comp_dose_mg|int}} mg "
  "({{res_comp_expected_vials|int}} vials). Drug acquisition costs are multiplied by the relative dose "
  "intensity observed in the trial ({{int_rdi|pct}} for Drug A and {{comp_rdi|pct}} for Drug B); "
  "administration costs are not adjusted. Patients received an expected {{res_int_n_doses|p2}} doses "
  "of Drug A and {{res_comp_n_doses|p2}} doses of Drug B.")

H2("3.4 Costs and resource use")
P("Drug acquisition costs for Drug A and Drug B are list prices per vial from the national drug list "
  "supplied by the local affiliate (KR-C01, KR-C06); no risk-sharing agreement applies in this "
  "submission (KR-C15). Administration costs per intravenous infusion are based on the chemotherapy "
  "infusion fee in the local fee schedule, applied to both arms (KR-C08). Health state costs come "
  "from a local claims analysis reported per month (KR-C09, KR-C10) and were converted to weekly costs "
  "by the declared mapping. Adverse event costs are local one-off costs per patient (KR-C12, KR-C13). "
  "A one-off terminal care cost is applied to each death; no local estimate is available yet, and the "
  "value used in this draft comes from a test-only resolution of the gap (KR-C11, GAP-001). All source "
  "descriptions are those recorded in the local input workbook, which is synthetic.")
P("All costs are in {{text currency_code}} at {{price_year|year}} prices (KR-S02, KR-S03); no global "
  "cost was converted from another currency.")
T("Table 3. Cost inputs", ["Input", "Value", "Unit"], [
    ["Drug A list price per vial", "{{int_vial_price|money}}", "per vial"],
    ["Drug A drug cost per administration (expected vials)", "{{res_int_drug_cost_per_admin|money}}",
     "per administration"],
    ["Drug B list price per vial", "{{comp_vial_price|money}}", "per vial"],
    ["Drug B drug cost per administration", "{{res_comp_drug_cost_per_admin|money}}", "per administration"],
    ["Administration cost, Drug A", "{{int_admin_cost_per_admin|money}}", "per administration"],
    ["Administration cost, Drug B", "{{comp_admin_cost_per_admin|money}}", "per administration"],
    ["Progression-free health state", "{{c_pf_week|money}}", "per week"],
    ["Progressed disease health state", "{{c_pd_week|money}}", "per week"],
    ["Terminal care (test-only value, GAP-001)", "{{c_terminal|money}}", "one-off"],
    ["Adverse events, Drug A", "{{int_ae_cost|money}}", "one-off"],
    ["Adverse events, Drug B", "{{comp_ae_cost|money}}", "one-off"],
])
P("Subsequent therapies are costed once, at progression, as the cost of a mean treatment course "
  "weighted by the proportion of patients receiving each therapy. Course costs come from a local claims "
  "analysis (KR-T01 to KR-T03) and the shares receiving each therapy from a local expert panel (KR-T04 "
  "to KR-T09). Progression events are estimated from the decline in the PF proportion, excluding the "
  "share of PFS events that were deaths in the trial ({{int_p_death_first_pfs|pct}} for Drug A and "
  "{{comp_p_death_first_pfs|pct}} for Drug B).")
T("Table 4. Subsequent therapies", ["Therapy", "Course cost", "Share after Drug A", "Share after Drug B"], [
    ["Docetaxel-based chemotherapy", "{{st_cost_1|money}}", "{{int_st_share_1|pct}}", "{{comp_st_share_1|pct}}"],
    ["Immunotherapy", "{{st_cost_2|money}}", "{{int_st_share_2|pct}}", "{{comp_st_share_2|pct}}"],
    ["Other targeted therapy", "{{st_cost_3|money}}", "{{int_st_share_3|pct}}", "{{comp_st_share_3|pct}}"],
    ["Cost per progression", "", "{{res_int_st_cost_per_progression|money}}",
     "{{res_comp_st_cost_per_progression|money}}"],
])

H2("3.5 Health-related quality of life")
P("Health state utility values are local values from EQ-5D-5L data valued with the Korean value set "
  "(KR-U01, KR-U02). Utilities were assumed to depend on health state only and not on treatment. To "
  "reflect declining quality of life with age, state utilities are multiplied by the ratio of "
  "general-population utility at the current age to that at the baseline age, using a regression on "
  "age and sex retained from the global model; Korean population norms were not supplied, and the "
  "retained regression is based on a different value set from the local state utilities (GAP-003). "
  "Quality-of-life losses associated with severe (grade three or higher) adverse events were applied "
  "as one-off QALY decrements at the start of the model; these are also retained from the global model "
  "and were valued with a different value set (GAP-002). Both retained inputs are flagged for review.")
T("Table 5. Utility inputs", ["Input", "Value"], [
    ["Progression-free", "{{u_pf|p2}}"],
    ["Progressed disease", "{{u_pd|p2}}"],
    ["AE QALY loss, Drug A (retained, GAP-002)", "{{int_ae_qaly_loss|qaly}}"],
    ["AE QALY loss, Drug B (retained, GAP-002)", "{{comp_ae_qaly_loss|qaly}}"],
    ["Population norms: intercept (retained, GAP-003)", "{{gpu_intercept|p2}}"],
    ["Population norms: male (retained, GAP-003)", "{{gpu_male|coef}}"],
    ["Population norms: age (retained, GAP-003)", "{{gpu_age|coef}}"],
    ["Population norms: age squared (retained, GAP-003)", "{{gpu_age2|coef}}"],
])

H2("3.6 Uncertainty")
P("Structural and parameter uncertainty are to be explored through scenario analyses; a scenario set "
  "for the Korean setting has not yet been specified (Section 4.3). Probabilistic sensitivity analysis "
  "(PSA) is specified in the model, with gamma distributions for costs, beta distributions for "
  "utilities and proportions, Dirichlet distributions for subsequent-therapy shares and correlated "
  "multivariate normal distributions for the log-transformed Weibull parameters. PSA results are not "
  "included in this version of the report and will be provided in an addendum.")

H2("3.7 Retained global inputs")
P("The following model inputs are covered by a gap register entry whose handling retains or flags "
  "them. Each line states whether the global value was retained or a local value was derived by a "
  "declared method, and names the gap register entry.")
P("{{retained_inputs}}")

# ---------------------------------------------------------------- 4. Results
H1("4. Results")
H2("4.1 Base-case results")
P("Drug A increased discounted life years by {{res_inc_ly_disc|ly}} and QALYs by "
  "{{res_inc_qaly_disc|qaly}} compared with Drug B, at an additional cost of "
  "{{res_inc_total_cost|money}}. The base-case ICER is {{res_icer|money}} per QALY gained and "
  "{{res_icer_ly|money}} per life year gained.")
T("Table 6. Base-case results (discounted)", ["Outcome", "Drug A", "Drug B", "Incremental"], [
    ["Total costs", "{{res_int_total_cost|money}}", "{{res_comp_total_cost|money}}", "{{res_inc_total_cost|money}}"],
    ["Life years", "{{res_int_ly_disc|ly}}", "{{res_comp_ly_disc|ly}}", "{{res_inc_ly_disc|ly}}"],
    ["QALYs", "{{res_int_qaly_disc|qaly}}", "{{res_comp_qaly_disc|qaly}}", "{{res_inc_qaly_disc|qaly}}"],
    ["ICER (cost per QALY gained)", "", "", "{{res_icer|money}}"],
    ["Incremental NMB at the local reference value", "", "", "{{res_inc_nmb|money}}"],
])
P("{{rounding_note}}")
P("Undiscounted, Drug A provided {{res_int_ly_undisc|ly}} life years versus {{res_comp_ly_undisc|ly}} "
  "with Drug B.")

H2("4.2 Disaggregated costs")
P("Drug acquisition accounted for {{res_int_drug_share|pct}} of total costs in the Drug A arm, compared "
  "with {{res_comp_drug_share|pct}} in the Drug B arm. The largest single contributor to incremental "
  "costs was {{label C15}} ({{value_of C15|money}}). "
  "{{ifany C16}}Lower {{labels C16}} costs with Drug A partially offset its higher costs in other "
  "categories.{{endif}}")
T("Table 7. Disaggregated discounted costs ({{text currency_code}})",
  ["Category", "Drug A", "Drug B", "Incremental"], [
    ["Drug acquisition", "{{res_int_cost_drug|money}}", "{{res_comp_cost_drug|money}}", "{{res_inc_cost_drug|money}}"],
    ["Administration", "{{res_int_cost_admin|money}}", "{{res_comp_cost_admin|money}}", "{{res_inc_cost_admin|money}}"],
    ["Progression-free state", "{{res_int_cost_pf_state|money}}", "{{res_comp_cost_pf_state|money}}",
     "{{res_inc_cost_pf_state|money}}"],
    ["Progressed disease state", "{{res_int_cost_pd_state|money}}", "{{res_comp_cost_pd_state|money}}",
     "{{res_inc_cost_pd_state|money}}"],
    ["Terminal care (test-only value)", "{{res_int_cost_terminal|money}}", "{{res_comp_cost_terminal|money}}",
     "{{res_inc_cost_terminal|money}}"],
    ["Subsequent therapy", "{{res_int_cost_st|money}}", "{{res_comp_cost_st|money}}", "{{res_inc_cost_st|money}}"],
    ["Adverse events", "{{res_int_cost_ae|money}}", "{{res_comp_cost_ae|money}}", "{{res_inc_cost_ae|money}}"],
    ["Total", "{{res_int_total_cost|money}}", "{{res_comp_total_cost|money}}", "{{res_inc_total_cost|money}}"],
])

H2("4.3 Scenario analyses")
P("No scenario set has been specified for the Korean setting. The global scenario set contains values "
  "specific to the source setting and has not been run on the adapted model, so this draft reports no "
  "scenario results, no ranking of the assumptions with the largest effect on the ICER and no "
  "comparison of scenario results with the local reference value {{review C17}} {{review C18}}.")

# ---------------------------------------------------------------- 5. Model validation
H1("5. Model validation")
P("The global model was quality-assured using a checklist covering input transcription, formula "
  "consistency between arms, and extreme-value testing. Both treatment arms use identical formula "
  "layouts that differ only in the arm-specific parameter block. State membership sums to one in every "
  "cycle by construction. In the adapted model, the lifetime check reports {{text check_lifetime_ok}}, "
  "the life-table check reports {{text check_life_table_ok}} and the subsequent-therapy share check "
  "reports {{text check_st_shares_ok}}. Reproduction of the adapted results by an independent "
  "implementation is not reported in this draft.")
P("The general-population mortality constraint was active in {{res_int_gpm_bind_cycles|int}} weekly "
  "cycles in the Drug A arm, from age {{res_int_gpm_first_bind_age|int}}, when "
  "{{res_int_gpm_first_bind_alive|pct2}} of patients remained alive, and in "
  "{{res_comp_gpm_bind_cycles|int}} cycles in the Drug B arm. Its effect on the ICER under the Korean "
  "life table has not yet been assessed, because the scenario without the constraint has not been run "
  "on the adapted model {{review C19}}.")
P("Face validity was assessed by comparing modelled medians with the trial Kaplan-Meier estimates. "
  "Whether the modelled medians lie within the confidence intervals of the observed medians must be "
  "confirmed against the trial source, which is not part of the model {{review C20}}.")

# ---------------------------------------------------------------- 6. Discussion
H1("6. Discussion")
P("The analysis indicates that Drug A provides health gains relative to Drug B, driven mainly by "
  "longer overall survival in the retained trial efficacy. The largest contributor to the additional "
  "costs is {{label C15}}. "
  "{{ifany C16}}Lower {{labels C16}} costs with Drug A partly offset the additional costs.{{endif}}")
P("Several limitations should be noted.")
for item in [
    "Independent Weibull models were fitted to each arm. Alternative distributions were not explored in "
    "this version of the report, and long-term extrapolation of OS is the main source of structural "
    "uncertainty.",
    "Clinical efficacy and treatment exposure are retained from the global trial (GAP-006); their "
    "applicability to Korean patients has not been assessed.",
    "The terminal care cost is a test-only value (GAP-001); results that depend on it are provisional.",
    "Adverse-event disutilities and general-population utility norms are retained from the global model "
    "and use a different value set from the Korean state utilities (GAP-002, GAP-003).",
    "Baseline age and the proportion of men are those of the trial population (GAP-005).",
    "Progression events are approximated from the decline in the PF proportion using a constant share "
    "of deaths among PFS events; this share is likely to increase at older ages.",
    "Subsequent therapies are costed as one-off courses at progression, without their effect on survival "
    "beyond that observed in the trial.",
    "Vial sharing was not considered, which may overestimate drug costs for Drug A in centres that share "
    "vials.",
    "The partitioned survival structure does not explicitly model the relationship between progression "
    "and death, as discussed in published technical guidance [2].",
    "Whether Drug B reflects the Korean standard of care has not been confirmed by local clinicians, and "
    "no Korean scenario set has been specified.",
]:
    P(item, style="List Bullet")
P("No scenario analyses have been run for the Korean setting, so it is not yet known whether plausible "
  "changes in key assumptions would move the ICER across the local reference value. The stopping rule "
  "is a key assumption and should be reflected in the reimbursement criteria for Drug A (KR-C05).")

# ---------------------------------------------------------------- 7. Conclusion
H1("7. Conclusion")
P("Drug A is associated with an ICER of {{res_icer|money}} per QALY gained compared with Drug B. "
  "{{if C22}}This does not exceed the local reference value of {{wtp_threshold|money}} per QALY gained "
  "(KR-S07), and Drug A can therefore be considered a cost-effective option for adults with previously "
  "untreated advanced synthetic carcinoma in the {{text country}}, with the stopping rule reflected in "
  "the reimbursement criteria.{{endif}}"
  "{{ifnot C22}}At the local reference value of {{wtp_threshold|money}} per QALY gained (KR-S07), Drug A "
  "cannot be considered a cost-effective option for adults with previously untreated advanced synthetic "
  "carcinoma in the {{text country}}.{{endif}} "
  "This conclusion is provisional: the terminal care cost is a test-only value and several items await "
  "human review.")

# ---------------------------------------------------------------- References
H1("References")
P("[1] Local pharmacoeconomic guideline for the Republic of Korea (synthetic placeholder; full citation "
  "to be supplied by the HEOR lead).")
P("[2] Woods B, Sideris E, Palmer S, Latimer N, Soares M. NICE DSU Technical Support Document 19: "
  "Partitioned survival analysis for decision modelling in health care: a critical review. 2017.")
P("[3] Latimer N. NICE DSU Technical Support Document 14: Survival analysis for economic evaluations "
  "alongside clinical trials. 2011 (updated 2013).")

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)

labels = {
    "res_inc_cost_drug": "drug acquisition",
    "res_inc_cost_admin": "administration",
    "res_inc_cost_pf_state": "progression-free state",
    "res_inc_cost_pd_state": "progressed disease state",
    "res_inc_cost_terminal": "terminal care",
    "res_inc_cost_st": "subsequent therapy",
    "res_inc_cost_ae": "adverse event",
}
SIDECAR.write_text(yaml.safe_dump({"claims_register": "approved/claims_register.json", "labels": labels},
                                  sort_keys=False))
print(f"wrote {OUT} and {SIDECAR}")
