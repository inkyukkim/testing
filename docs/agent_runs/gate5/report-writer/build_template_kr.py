"""Write the KR report template (directives, no numerals) and its sidecar.

Run from the workspace root: python work/build_template_kr.py
"""
from pathlib import Path

import yaml
from docx import Document

OUT = Path("work/report_template_KR.docx")
SIDE = Path("work/report_template_KR.sidecar.yaml")

doc = Document()


def P(text, style=None):
    return doc.add_paragraph(text, style=style)


def H(text, level=1):
    return doc.add_heading(text, level=level)


def T(caption, header, rows):
    P(caption)
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.style = "Table Grid"
    for j, h in enumerate(header):
        t.rows[0].cells[j].text = h
    for i, r in enumerate(rows, start=1):
        for j, v in enumerate(r):
            t.rows[i].cells[j].text = v
    return t


M = lambda n: "{{" + n + "|money}}"

# ---------------------------------------------------------------- title page
P("Drug A for previously untreated advanced synthetic carcinoma", style="Title")
P("Cost-effectiveness analysis: technical report (Republic of Korea)")
P("SYNTHETIC DOCUMENT FOR SOFTWARE TESTING. All data are fictitious. Not for clinical, "
  "reimbursement or investment decisions.")
P("Local adaptation of the global model | Model file: adapted_model.xlsx")
P("{{draft_banner}}")

# ---------------------------------------------------------------- 1
H("1. Executive summary")
P("This report describes the methods and results of a cost-utility analysis comparing Drug A with "
  "Drug B, a platinum doublet regimen, for adults with previously untreated advanced synthetic "
  "carcinoma in the {{text country}}. The analysis takes the perspective required by the local "
  "pharmacoeconomic guideline: {{text perspective}}. It uses a three-state partitioned survival "
  "model with weekly cycles over a lifetime horizon of {{time_horizon_years|int}} years, with costs "
  "and outcomes discounted at {{dr_costs|pct}} per annum.")
P("In the base case, Drug A was associated with total discounted costs of {{res_int_total_cost|money}} "
  "and {{res_int_qaly_disc|qaly}} QALYs, compared with {{res_comp_total_cost|money}} and "
  "{{res_comp_qaly_disc|qaly}} QALYs for Drug B. The incremental cost was {{res_inc_total_cost|money}} "
  "for an incremental gain of {{res_inc_qaly_disc|qaly}} QALYs, giving an incremental "
  "cost-effectiveness ratio (ICER) of {{res_icer|money}} per QALY gained.")
P("The decision rule is a single reference value of {{wtp_threshold|money}} per QALY gained; it is "
  "not an official threshold. "
  "{{if C02}}At this reference value Drug A is cost-effective, with an incremental net monetary "
  "benefit of {{res_inc_nmb|money}}.{{endif}}"
  "{{ifnot C02}}At this reference value Drug A is not cost-effective; the incremental net monetary "
  "benefit is {{res_inc_nmb|money}}.{{endif}}")
P("No Korean scenario set has been specified yet, so the sensitivity of the ICER to alternative "
  "assumptions is not yet reported (Section 4.3). {{review C04}}")

# ---------------------------------------------------------------- 2
H("2. Decision problem")
P("Advanced synthetic carcinoma is a fictitious malignancy used here to exercise model-adaptation "
  "software. Patients with advanced disease have a poor prognosis. First-line systemic therapy with "
  "a platinum doublet (Drug B) is assumed to be the standard of care in Korea; this has not yet been "
  "confirmed by local clinicians. {{review C05}} Drug A is a hypothetical targeted agent administered "
  "intravenously every {{int_admin_interval_weeks|int}} weeks.")
T("Table 1. Decision problem", ["Element", "Base case"], [
    ["Population", "Adults with previously untreated advanced synthetic carcinoma"],
    ["Intervention", "Drug A, intravenous, every {{int_admin_interval_weeks|int}} weeks, with a "
                     "maximum treatment duration"],
    ["Comparator", "Drug B (platinum doublet), every {{comp_admin_interval_weeks|int}} weeks, for a "
                   "fixed number of cycles"],
    ["Outcomes", "Progression-free survival, overall survival, health-related quality of life, costs"],
    ["Perspective", "{{text perspective}}"],
    ["Economic evaluation", "Cost-utility analysis; cost per QALY gained"],
])
P("The analysis follows the local pharmacoeconomic evaluation guideline [1], with the healthcare "
  "system perspective stated above, counting total costs regardless of payer. Health effects are "
  "expressed in quality-adjusted life years (QALYs). Health state utilities use EQ-5D-5L values "
  "with the Korean value set, and costs reflect Korean list prices, the national fee schedule and "
  "local claims analyses (Section 3.4).")

# ---------------------------------------------------------------- 3
H("3. Methods")
H("3.1 Model structure", 2)
P("A partitioned survival model with three mutually exclusive health states was developed in "
  "Microsoft Excel: progression-free (PF), progressed disease (PD) and death [2]. The proportion of "
  "patients in each state at each time point is derived directly from the parametric survival "
  "curves for progression-free survival (PFS) and overall survival (OS). The PF proportion is the "
  "lower of the PFS and OS curves, the PD proportion is the difference between OS and PF, and the "
  "proportion dead is the complement of OS. The global model structure is unchanged in this "
  "adaptation; only input values were replaced.")
P("The model uses a cycle length of {{cycle_length_days|int}} days and a time horizon of "
  "{{time_horizon_years|int}} years. The modelled cohort has a mean starting age of "
  "{{baseline_age|int}} years and is {{prop_male|pct}} male; both characteristics are retained from "
  "the trial population because Korean values were not supplied (Section 3.7). The model's horizon "
  "check compares the proportion alive at the end of the horizon in each arm with a tolerance of "
  "{{lifetime_check_tol|pct}} and returns {{text check_lifetime_ok}}.")
P("Modelled survival is constrained so that the risk of death is never lower than in the general "
  "population of the same age and sex. In each cycle, the conditional probability of surviving the "
  "cycle is taken as the lower of the value implied by the fitted curve and the value implied by "
  "the Korean complete life table, applied separately to the PFS and OS curves. The life table is "
  "published as central death rates up to an open top-age band; these were converted to annual "
  "probabilities of death by a declared method, and the open-band rate was applied to older ages "
  "in the model's age grid (Section 3.7). General-population survival is calculated separately for "
  "men and women and weighted by the proportion of men at baseline.")
P("A half-cycle correction is applied to state membership by taking the average of the start and "
  "end of each cycle (trapezoidal method); it is used for health state costs, life years and QALYs. "
  "Drug acquisition and administration costs are incurred at the time of each dose and are not "
  "half-cycle corrected. Costs and outcomes are discounted at annual rates of {{dr_costs|pct}} and "
  "{{dr_outcomes|pct}} respectively, as specified by the local guideline, using a discount factor "
  "evaluated at the mid-point of each cycle, or at the time of administration for dosing costs.")

H("3.2 Survival extrapolation", 2)
P("Independent Weibull models were fitted to patient-level PFS, OS and time on treatment (ToT) "
  "data from the pivotal trial for each treatment arm, following published methodological guidance "
  "on survival analysis for economic evaluation [3] and the survival-analysis expectations of the "
  "local guideline [1]. The Weibull distribution was selected on the basis of statistical fit, "
  "visual inspection against the Kaplan-Meier curves, and the clinical plausibility of long-term "
  "extrapolations. The survival function is parameterised as S(t) = exp(-(t/scale)^shape), with "
  "time in months. Clinical efficacy is taken from the global trial and is assumed to transfer to "
  "Korean patients (Section 3.7). Medians in Table 2 are those of the fitted curves before the "
  "general-population constraint.")
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
  "{{ifnot C09}}The fitted PFS and OS curves cross in at least one arm; the PF proportion is "
  "capped by OS from that point.{{endif}}")

H("3.3 Treatment duration and dosing", 2)
P("Treatment duration is modelled with the ToT curves, constrained not to exceed OS, so patients "
  "may continue treatment after progression as observed in the trial. Doses are given at fixed "
  "intervals and costed only in the weeks in which a dose is due, for the proportion of patients on "
  "treatment at the start of that week. Drug A is given every {{int_admin_interval_weeks|int}} weeks "
  "for a maximum of {{int_max_doses|int}} doses; the dose count is derived from the reimbursed "
  "maximum treatment duration in the local reimbursement criteria. Drug B is given every "
  "{{comp_admin_interval_weeks|int}} weeks for a maximum of {{comp_max_doses|int}} doses, as in the "
  "local dosing schedule.")
P("Drug A is dosed at {{int_dose_mg|p2}} mg/kg, as in the Korean label. The expected number of "
  "vials per administration ({{res_int_expected_vials|p2}}) accounts for wastage, assuming no vial "
  "sharing and a lognormal distribution of body weight with mean {{weight_mean_kg|kg}} kg and "
  "standard deviation {{weight_sd_kg|kg}} kg, taken from the Korean cancer registry (synthetic). "
  "Drug B is given at a flat dose of {{comp_dose_mg|int}} mg ({{res_comp_expected_vials|int}} vials). "
  "Drug acquisition costs are multiplied by the relative dose intensity observed in the trial "
  "({{int_rdi|pct}} for Drug A and {{comp_rdi|pct}} for Drug B); administration costs are not "
  "adjusted. Patients received an expected {{res_int_n_doses|p2}} doses of Drug A and "
  "{{res_comp_n_doses|p2}} doses of Drug B.")

H("3.4 Costs and resource use", 2)
P("Drug acquisition costs for Drug A and Drug B are list prices per vial from the Korean drug "
  "reimbursement list (synthetic); no risk-sharing agreement is applied in this submission. "
  "Administration costs per intravenous infusion are the chemotherapy infusion fee from the national "
  "fee schedule (synthetic) and apply to both arms. Health state costs come from a local claims "
  "analysis (synthetic), supplied per month and converted to weekly costs by the mapping tool using "
  "model constants. Adverse event costs per patient are local one-off estimates (synthetic). A "
  "one-off terminal care cost is applied to each death; no local estimate is yet available, and the "
  "value used in this draft is a test-only resolution of the corresponding gap (see the draft "
  "notice on the title page).")
P("All costs are in {{text currency_code}} at {{price_year|year}} prices.")
T("Table 3. Cost inputs", ["Input", "Value", "Unit"], [
    ["Drug A list price per vial", M("int_vial_price"), "per vial"],
    ["Drug A drug cost per administration (expected vials)", M("res_int_drug_cost_per_admin"),
     "per administration"],
    ["Drug B list price per vial", M("comp_vial_price"), "per vial"],
    ["Drug B drug cost per administration", M("res_comp_drug_cost_per_admin"), "per administration"],
    ["Administration cost, Drug A", M("int_admin_cost_per_admin"), "per administration"],
    ["Administration cost, Drug B", M("comp_admin_cost_per_admin"), "per administration"],
    ["Progression-free health state", M("c_pf_week"), "per week"],
    ["Progressed disease health state", M("c_pd_week"), "per week"],
    ["Terminal care (test-only value, draft)", M("c_terminal"), "one-off"],
    ["Adverse events, Drug A", M("int_ae_cost"), "one-off"],
    ["Adverse events, Drug B", M("comp_ae_cost"), "one-off"],
])
P("Subsequent therapies are costed once, at progression, as the cost of a mean treatment course "
  "weighted by the proportion of patients receiving each therapy in Korean practice, as estimated "
  "by a local expert panel (synthetic); course costs come from the local claims analysis. "
  "Progression events are estimated from the decline in the PF proportion, excluding the share of "
  "PFS events that were deaths in the trial ({{int_p_death_first_pfs|pct}} for Drug A and "
  "{{comp_p_death_first_pfs|pct}} for Drug B).")
T("Table 4. Subsequent therapies",
  ["Therapy", "Course cost", "Share after Drug A", "Share after Drug B"], [
      ["Docetaxel", M("st_cost_1"), "{{int_st_share_1|pct}}", "{{comp_st_share_1|pct}}"],
      ["Immune checkpoint inhibitor", M("st_cost_2"), "{{int_st_share_2|pct}}", "{{comp_st_share_2|pct}}"],
      ["Other targeted agents", M("st_cost_3"), "{{int_st_share_3|pct}}", "{{comp_st_share_3|pct}}"],
      ["Cost per progression", "", M("res_int_st_cost_per_progression"),
       M("res_comp_st_cost_per_progression")],
  ])

H("3.5 Health-related quality of life", 2)
P("Health state utility values are local EQ-5D-5L values valued with the Korean value set "
  "(synthetic). Utilities were assumed to depend on health state only and not on treatment. To "
  "reflect declining quality of life with age, state utilities are multiplied by the ratio of "
  "general-population utility at the current age to that at the baseline age, using a regression "
  "on age and sex. Korean population norms were not supplied, so the regression coefficients are "
  "retained from the global model, which used a different instrument and value set from the local "
  "state utilities. Quality-of-life losses associated with severe adverse events (grade three or "
  "higher) were applied as one-off QALY decrements at the start of the model; no local estimate was "
  "available and the global values, also on a different value set, are retained. Both retained "
  "inputs are flagged for review (Section 3.7).")
T("Table 5. Utility inputs", ["Input", "Value"], [
    ["Progression-free", "{{u_pf|p2}}"],
    ["Progressed disease", "{{u_pd|p2}}"],
    ["AE QALY loss, Drug A (retained global input)", "{{int_ae_qaly_loss|qaly}}"],
    ["AE QALY loss, Drug B (retained global input)", "{{comp_ae_qaly_loss|qaly}}"],
    ["Population norms: intercept (retained global input)", "{{gpu_intercept|p2}}"],
    ["Population norms: male (retained global input)", "{{gpu_male|coef}}"],
    ["Population norms: age (retained global input)", "{{gpu_age|coef}}"],
    ["Population norms: age squared (retained global input)", "{{gpu_age2|coef}}"],
])

H("3.6 Uncertainty", 2)
P("Structural and parameter uncertainty will be explored through scenario analyses once a Korean "
  "scenario set has been specified (Section 4.3). Probabilistic sensitivity analysis (PSA) is "
  "specified in the model, with gamma distributions for costs, beta distributions for utilities "
  "and proportions, Dirichlet distributions for subsequent-therapy shares and correlated "
  "multivariate normal distributions for the log-transformed Weibull parameters. PSA results are "
  "not included in this version of the report and will be provided in an addendum.")

H("3.7 Local inputs and retained global inputs", 2)
P("Inputs not supplied by the local data, or supplied only in part, are recorded in the gap "
  "register. The following model inputs are retained from the global model or derived from local "
  "data by a declared method; those flagged for review are also limitations of this analysis "
  "(Section 6).")
P("{{retained_inputs}}")

# ---------------------------------------------------------------- 4
H("4. Results")
H("4.1 Base-case results", 2)
P("Drug A increased discounted life years by {{res_inc_ly_disc|ly}} and QALYs by "
  "{{res_inc_qaly_disc|qaly}} compared with Drug B, at an additional cost of "
  "{{res_inc_total_cost|money}}. The base-case ICER is {{res_icer|money}} per QALY gained and "
  "{{res_icer_ly|money}} per life year gained.")
T("Table 6. Base-case results (discounted)", ["Outcome", "Drug A", "Drug B", "Incremental"], [
    ["Total costs", M("res_int_total_cost"), M("res_comp_total_cost"), M("res_inc_total_cost")],
    ["Life years", "{{res_int_ly_disc|ly}}", "{{res_comp_ly_disc|ly}}", "{{res_inc_ly_disc|ly}}"],
    ["QALYs", "{{res_int_qaly_disc|qaly}}", "{{res_comp_qaly_disc|qaly}}", "{{res_inc_qaly_disc|qaly}}"],
    ["ICER (cost per QALY gained)", "", "", M("res_icer")],
    ["Incremental NMB at the reference value", "", "", M("res_inc_nmb")],
])
P("{{rounding_note}}")
P("Undiscounted, Drug A provided {{res_int_ly_undisc|ly}} life years versus "
  "{{res_comp_ly_undisc|ly}} with Drug B.")

H("4.2 Disaggregated costs", 2)
P("Drug acquisition accounted for {{res_int_drug_share|pct}} of total costs in the Drug A arm, "
  "compared with {{res_comp_drug_share|pct}} in the Drug B arm. The largest single contributor to "
  "incremental costs was {{label C15}} ({{value_of C15|money}}). "
  "{{ifany C16}}Lower {{labels C16}} costs with Drug A partially offset its higher costs in other "
  "categories.{{endif}}")
T("Table 7. Disaggregated discounted costs (KRW)", ["Category", "Drug A", "Drug B", "Incremental"], [
    ["Drug acquisition", M("res_int_cost_drug"), M("res_comp_cost_drug"), M("res_inc_cost_drug")],
    ["Administration", M("res_int_cost_admin"), M("res_comp_cost_admin"), M("res_inc_cost_admin")],
    ["Progression-free state", M("res_int_cost_pf_state"), M("res_comp_cost_pf_state"),
     M("res_inc_cost_pf_state")],
    ["Progressed disease state", M("res_int_cost_pd_state"), M("res_comp_cost_pd_state"),
     M("res_inc_cost_pd_state")],
    ["Terminal care (test-only input)", M("res_int_cost_terminal"), M("res_comp_cost_terminal"),
     M("res_inc_cost_terminal")],
    ["Subsequent therapy", M("res_int_cost_st"), M("res_comp_cost_st"), M("res_inc_cost_st")],
    ["Adverse events", M("res_int_cost_ae"), M("res_comp_cost_ae"), M("res_inc_cost_ae")],
    ["Total", M("res_int_total_cost"), M("res_comp_total_cost"), M("res_inc_total_cost")],
])

H("4.3 Scenario analyses", 2)
P("The scenario set of the global analysis contains values specific to the source setting and has "
  "not been carried over. No Korean scenario set has been specified yet, so scenario results, the "
  "ranking of scenarios by their effect on the ICER and the comparison of scenario ICERs with the "
  "reference value are not reported in this draft. {{review C17}} {{review C18}}")

# ---------------------------------------------------------------- 5
H("5. Model validation")
P("The global model was quality-assured using a checklist covering input transcription, formula "
  "consistency between arms, and extreme-value testing. Both treatment arms use identical formula "
  "layouts that differ only in the arm-specific parameter block. State membership sums to one in "
  "every cycle by construction. In the adapted model only named input cells were changed; formulas "
  "are identical to the global model, and the adapted model is checked against an independent "
  "implementation in Python as part of model verification, which is accepted separately.")
P("The general-population mortality constraint, now based on the Korean life table, was active in "
  "{{res_int_gpm_bind_cycles|int}} weekly cycles in the Drug A arm, from about age "
  "{{res_int_gpm_first_bind_age|int}}, when {{res_int_gpm_first_bind_alive|pct2}} of patients "
  "remained alive, and in {{res_comp_gpm_bind_cycles|int}} weekly cycles in the Drug B arm. Its "
  "effect on the ICER has not yet been assessed on the adapted model. {{review C19}}")
P("Face validity of the fitted curves, which are retained from the global analysis, was assessed "
  "against the trial Kaplan-Meier estimates. {{review C20}}")

# ---------------------------------------------------------------- 6
H("6. Discussion")
P("The analysis indicates that Drug A provides health gains relative to Drug B, driven mainly by "
  "longer overall survival. The additional costs arise from drug acquisition and administration "
  "during the treatment period and from health state costs accumulated over the longer survival "
  "period, partly offset by lower costs in some other categories (Section 4.2).")
P("Several limitations should be noted.")
P("Independent Weibull models were fitted to each arm. Alternative distributions were not explored "
  "in this version of the report, and long-term extrapolation of OS is the main source of structural "
  "uncertainty. Efficacy is taken from the global trial and its applicability to Korean patients "
  "has not been assessed.", style="List Bullet")
P("Progression events are approximated from the decline in the PF proportion using a constant "
  "share of deaths among PFS events; this share is likely to increase at older ages.",
  style="List Bullet")
P("Subsequent therapies are costed as one-off courses at progression, without their effect on "
  "survival beyond that observed in the trial.", style="List Bullet")
P("Vial sharing was not considered, which may overestimate drug costs for Drug A in centres that "
  "share vials.", style="List Bullet")
P("The partitioned survival structure does not explicitly model the relationship between "
  "progression and death [2].", style="List Bullet")
P("Adverse-event QALY losses and general-population utility norms are retained from the global "
  "model on a different value set from the Korean state utilities, and the cohort's age and sex "
  "distribution is that of the trial (Section 3.7).", style="List Bullet")
P("No local terminal care cost is yet available; the value in this draft is for testing only.",
  style="List Bullet")
P("{{if C02}}The base-case ICER is below the local reference value. Without a Korean scenario set "
  "the robustness of this result to key assumptions cannot yet be judged.{{endif}}"
  "{{ifnot C02}}The base-case ICER exceeds the local reference value. Without a Korean scenario set "
  "the effect of key assumptions on this result cannot yet be judged.{{endif}} "
  "The stopping rule is a key assumption and should be reflected in the reimbursement criteria for "
  "Drug A.")

# ---------------------------------------------------------------- 7
H("7. Conclusion")
P("Drug A is associated with an ICER of {{res_icer|money}} per QALY gained compared with Drug B. "
  "{{if C22}}This is below the local reference value of {{wtp_threshold|money}} per QALY gained. "
  "Drug A can therefore be considered a cost-effective option for adults with previously untreated "
  "advanced synthetic carcinoma in Korea at the listed price and with the reimbursed maximum "
  "treatment duration in place.{{endif}}"
  "{{ifnot C22}}This is not below the local reference value of {{wtp_threshold|money}} per QALY "
  "gained, so Drug A cannot be considered a cost-effective option for adults with previously "
  "untreated advanced synthetic carcinoma in Korea at the listed price.{{endif}}")

# ---------------------------------------------------------------- refs
H("References")
P("[1] Local pharmacoeconomic evaluation guideline, Republic of Korea (synthetic placeholder).")
P("[2] Woods B, Sideris E, Palmer S, Latimer N, Soares M. NICE DSU Technical Support Document 19: "
  "Partitioned survival analysis for decision modelling in health care: a critical review. 2017.")
P("[3] Latimer N. NICE DSU Technical Support Document 14: Survival analysis for economic "
  "evaluations alongside clinical trials. 2011 (updated 2013).")

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)

SIDE.write_text(yaml.safe_dump({
    "claims_register": "approved/claims_register.json",
    "labels": {
        "res_inc_cost_drug": "drug acquisition",
        "res_inc_cost_admin": "administration",
        "res_inc_cost_pf_state": "progression-free state",
        "res_inc_cost_pd_state": "progressed disease state",
        "res_inc_cost_terminal": "terminal care",
        "res_inc_cost_st": "subsequent therapy",
        "res_inc_cost_ae": "adverse event",
    },
}, sort_keys=False))
print("wrote", OUT, SIDE)
