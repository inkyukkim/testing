"""Build work/claims_register.json (Claims Analyst). No numeric literals; truths are filled by tools/claims.py."""
import json
from pathlib import Path

SC = [f"res_icer@SC{i}" for i in range(1, 9)]   # scenario ids are reference strings, not numbers
sc = dict(zip([f"SC{i}" for i in range(1, 9)], SC))
CAT = ["res_inc_cost_drug", "res_inc_cost_admin", "res_inc_cost_pf_state", "res_inc_cost_pd_state",
       "res_inc_cost_terminal", "res_inc_cost_st", "res_inc_cost_ae"]

TEST = ("Local truth is evaluated on a build that uses a test-only resolution of c_terminal (GAP-001, "
        "open block); any rendering from it is a draft.")
EFF = ("Relies on retained tagged efficacy and exposure inputs (GAP-006: int_pfs_shape, int_pfs_scale, "
       "int_os_shape, int_os_scale, int_tot_shape, int_tot_scale, comp_pfs_shape, comp_pfs_scale, comp_os_shape, "
       "comp_os_scale, comp_tot_shape, comp_tot_scale, the arm correlation names, int_p_death_first_pfs, "
       "comp_p_death_first_pfs, int_rdi, comp_rdi).")
POP = ("Relies on retained flagged population inputs prop_male and baseline_age (GAP-005) and on the "
       "flagged life-table conversion lt_qx_male, lt_qx_female with open-band ages (GAP-004).")
UTIL = ("Relies on retained flagged utility inputs int_ae_qaly_loss, comp_ae_qaly_loss (GAP-002, UK value set) "
        "and gpu_intercept, gpu_male, gpu_age, gpu_age2 (GAP-003, UK population norms).")
COST_DEPS = " ".join([EFF, POP, TEST])
ALL_DEPS = " ".join([EFF, POP, UTIL, TEST])
NOSCEN = "No Korean scenario set has been specified, so local truth stays pending until one exists; a person must decide which scenarios the local report presents."

pos = lambda r: {"op": "sign", "ref": r, "sign": "positive"}
neg = lambda r: {"op": "sign", "ref": r, "sign": "negative"}
zero = lambda r: {"op": "sign", "ref": r, "sign": "zero"}

claims = []
def add(block, excerpt, kind, expression, action, rationale, terms=None):
    c = {"claim_id": f"C{len(claims) + 1:02d}", "block": block, "excerpt": excerpt, "kind": kind,
         "expression": expression}
    if terms:
        c["jurisdiction_terms"] = terms
    c["action"] = action
    c["rationale"] = rationale
    claims.append(c)

add(1, "Cost-effectiveness analysis: technical report (United Kingdom)", "jurisdiction_specific", None, "reword",
    "Title names the source jurisdiction; replace with the local country from the model cell country.",
    ["United Kingdom"])
add(5, "from the perspective of the NHS and Personal Social Services (PSS) in England", "jurisdiction_specific", None,
    "reword", "Perspective is localised: use the mapped model cell perspective (healthcare system perspective per the local guideline).",
    ["NHS", "Personal Social Services", "PSS", "England"])
add(6, "The incremental cost was £24,746 for an incremental gain of 0.875 QALYs", "ranking",
    {"op": "all", "of": [pos("res_inc_total_cost"), pos("res_inc_qaly_disc")]}, "rerender",
    "The words incremental cost and gain presuppose that Drug A costs more and yields more QALYs; the sentence stays and only numbers change if the signs hold locally. Currency symbol is set by the local format. " + ALL_DEPS)
add(7, "At the upper end of the range normally considered by NICE (£30,000 per QALY), Drug A is cost-effective, with an incremental net monetary benefit of £1,514.",
    "threshold_comparison",
    {"op": "all", "of": [{"op": "le", "lhs": "res_icer", "rhs": "wtp_threshold"}, pos("res_inc_qaly_disc"), pos("res_inc_nmb")]},
    "reword",
    "Truth is re-evaluated against the local reference value in wtp_threshold. The NICE range wording must go: the local context has a single reference value, not an official threshold and no range. " + ALL_DEPS,
    ["NICE"])
add(7, "At £20,000 per QALY, Drug A is not cost-effective.", "threshold_comparison",
    {"op": "all", "of": [{"op": "gt", "lhs": "res_icer", "rhs": "wtp_threshold_lower"}, neg("res_inc_nmb_lower")]},
    "remove",
    "Lower bound of the source threshold range. Locally wtp_threshold_lower was set equal to the single reference value and the local context forbids describing a range, so the statement does not apply (and its local truth is evaluated for the record). " + TEST)
add(8, "In scenario analyses, the ICER was most sensitive to removing the stopping rule for Drug A and setting Drug A time on treatment equal to PFS",
    "sensitivity_ranking",
    {"op": "rank_abs_change", "refs": SC, "base": "res_icer", "expect_order": [sc["SC4"], sc["SC8"]]},
    "human_review", "Ranking of scenarios by absolute ICER change; generated from data. " + NOSCEN)
add(10, "first-line systemic therapy with a platinum doublet is assumed to be the established standard of care in the NHS",
    "jurisdiction_specific", None, "human_review",
    "Local clinical fact: whether Drug B (platinum doublet) reflects the Korean standard of care has not been confirmed by local clinicians.",
    ["NHS"])
add(23, "NHS and PSS", "jurisdiction_specific", None, "reword",
    "Perspective row of the decision problem table; use the mapped model cell perspective.", ["NHS", "PSS"])
add(26, "The analysis follows the NICE reference case [1].", "jurisdiction_specific", None, "reword",
    "Replace with the local pharmacoeconomic guideline (synthetic placeholder).", ["NICE reference case"])
add(26, "Health effects are expressed in quality-adjusted life years (QALYs) using EQ-5D-3L values from the pivotal trial",
    "jurisdiction_specific", None, "reword",
    "State utilities u_pf and u_pd are mapped from local EQ-5D-5L values with the Korean value set, not trial EQ-5D-3L values. "
    "AE disutilities int_ae_qaly_loss, comp_ae_qaly_loss (GAP-002) are retained from the global model on the UK value set and must be tagged as a flagged limitation.")
add(26, "costs reflect NHS list prices and national reference costs", "jurisdiction_specific", None, "reword",
    "Local unit costs come from the local drug list, fee schedule and claims analysis; name the local sources.",
    ["NHS", "national reference costs"])
add(26, "A confidential patient access scheme (PAS) discount is applied to the price of Drug A in all analyses.",
    "jurisdiction_specific", None, "remove",
    "The local input states that no risk-sharing agreement applies and list prices are used (int_vial_price mapped from the local list price), so the discount statement does not apply.",
    ["patient access scheme", "PAS"])
add(30, "The horizon captures virtually all survival in both arms; the modelled proportion alive at the end of the horizon is below 0.1% in each arm.",
    "model_check",
    {"op": "all", "of": [{"op": "lt", "lhs": "res_int_s_os_horizon", "rhs": "lifetime_check_tol"},
                         {"op": "lt", "lhs": "res_comp_s_os_horizon", "rhs": "lifetime_check_tol"}]},
    "rerender",
    "Horizon sufficiency check re-evaluated on the adapted model (time_horizon_years retained as structural setting). " + " ".join([EFF, POP, TEST]))
add(32, "Costs and outcomes are discounted at annual rates of 3.5% and 3.5% respectively, in line with the reference case",
    "jurisdiction_specific", None, "reword",
    "Reference case means the source agency reference case; local rates dr_costs and dr_outcomes are mapped from the local guideline, so cite that guideline instead.")
add(34, "The Weibull distribution was selected on the basis of statistical fit, visual inspection against the Kaplan-Meier curves, and the clinical plausibility of long-term extrapolations.",
    "external_assertion_untraceable", {"op": "external"}, "human_review",
    "Model selection evidence is not in the model; the curves are retained global inputs. " + EFF + " Clinical plausibility for Korean patients needs local confirmation.")
add(34, "following the NICE Decision Support Unit guidance on survival analysis [3]", "jurisdiction_specific", None, "reword",
    "Methodological citation of the source agency; reword to cite the technical support document as method guidance or the local guideline.",
    ["NICE", "Decision Support Unit"])
add(64, "The fitted PFS and OS curves did not cross in either arm.", "model_check",
    {"op": "all", "of": [zero("check_cross_int"), zero("check_cross_comp")]}, "rerender",
    "Curve-crossing counts from the model checks. " + EFF)
add(66, "Drug A is given every 3 weeks for a maximum of 35 doses, consistent with the stopping rule in the trial protocol.",
    "jurisdiction_specific", None, "reword",
    "int_max_doses is mapped from the local reimbursed maximum treatment duration (converted to a dose count by apply_mapping), so the source of the stopping rule is the local reimbursement criteria, not the trial protocol. int_admin_interval_weeks retained, confirmed by local label text.")
add(69, "Drug acquisition costs for Drug A reflect the list price net of the confidential PAS discount.",
    "jurisdiction_specific", None, "reword",
    "Local price is the list price from the local drug list with no risk-sharing agreement; state that.", ["PAS"])
add(69, "The cost of Drug B was taken from the electronic market information tool (eMIT).", "jurisdiction_specific",
    None, "reword", "comp_vial_price is mapped from the local drug list; name that source.",
    ["electronic market information tool", "eMIT"])
add(69, "Administration costs per intravenous infusion are based on NHS reference costs.", "jurisdiction_specific",
    None, "reword", "Administration costs are mapped from the local fee schedule (infusion fee per visit, both arms).",
    ["NHS reference costs", "NHS"])
add(69, "Health state costs comprise outpatient visits, imaging, blood tests and community care, valued using PSSRU unit costs.",
    "jurisdiction_specific", None, "reword",
    "c_pf_week and c_pd_week are converted from local monthly claims-analysis costs; the components and the source must be described from the local data, not the UK unit-cost source.",
    ["PSSRU"])
add(69, "A one-off terminal care cost is applied to each death.", "scope_statement", None, "human_review",
    "c_terminal is an open blocking gap (GAP-001): no local value exists and the resolution (local data, literature, or an approved method change excluding terminal care) decides whether this sentence stays. The run used here holds a test-only value.")
add(70, "All costs are in GBP at 2025 prices.", "jurisdiction_specific", None, "reword",
    "Currency is set by currency_code and the price year by price_year (mapped locally); render both from cells.",
    ["GBP"])
add(108, "weighted by the proportion of patients receiving each therapy in the trial", "jurisdiction_specific", None,
    "reword",
    "Subsequent-therapy shares and course costs are mapped from a local expert panel and local claims analysis, with renamed local categories (immune checkpoint inhibitor, other targeted agents); the source is no longer the trial. int_p_death_first_pfs and comp_p_death_first_pfs in the same sentence are retained tagged trial inputs (GAP-006).")
add(131, "Health state utility values were derived from EQ-5D-3L questionnaires collected in the pivotal trial and valued using the UK time trade-off value set, consistent with the NICE reference case.",
    "jurisdiction_specific", None, "reword",
    "u_pf and u_pd are mapped from local EQ-5D-5L values with the Korean value set. The AE QALY losses later in the block (int_ae_qaly_loss, comp_ae_qaly_loss, GAP-002) stay on the UK value set and must be tagged as a flagged retained input.",
    ["UK time trade-off value set", "NICE reference case"])
add(131, "using a regression on age and sex from UK population norms", "jurisdiction_specific", None, "human_review",
    "Korean population norms were not supplied; gpu_intercept, gpu_male, gpu_age, gpu_age2 are retained flagged (GAP-003). A person decides whether the UK norms stay, with a limitation and the no-age-adjustment scenario, or local norms are sought.",
    ["UK population norms"])
add(152, "PSA results are not included in this version of the report and will be provided in an addendum.",
    "scope_statement", None, "human_review",
    "No PSA has been run on the adapted model; whether the local submission commits to a PSA addendum is a decision for the HEOR lead.")
add(155, "Drug A increased discounted life years by 1.37 and QALYs by 0.875 compared with Drug B, at an additional cost of £24,746.",
    "ranking", {"op": "all", "of": [pos("res_inc_ly_disc"), pos("res_inc_qaly_disc"), pos("res_inc_total_cost")]},
    "rerender",
    "Direction words (increased, additional cost) depend on the signs of the incremental results. " + ALL_DEPS)
add(184, "The largest single contributor to incremental costs was drug acquisition (£16,309).", "ranking",
    {"op": "argmax", "refs": CAT, "expect": "res_inc_cost_drug"}, "regenerate",
    "Selection of the largest incremental cost category; rebuild from the local argmax. " + COST_DEPS)
add(184, "Lower subsequent therapy, adverse event and terminal care costs with Drug A partially offset its higher costs in other categories.",
    "ranking",
    {"op": "select", "refs": CAT, "where": {"op": "sign", "sign": "negative"},
     "expect": ["res_inc_cost_terminal", "res_inc_cost_st", "res_inc_cost_ae"]},
    "regenerate",
    "Selection of categories with negative incremental cost; rebuild the list from the local selection. The terminal care category depends on the test-only c_terminal (GAP-001). " + COST_DEPS)
add(223, "Removing the stopping rule for Drug A had the largest effect on the ICER, followed by setting Drug A time on treatment equal to PFS and the alternative utility values.",
    "sensitivity_ranking",
    {"op": "rank_abs_change", "refs": SC, "base": "res_icer", "expect_order": [sc["SC4"], sc["SC8"], sc["SC3"]]},
    "human_review", "Scenario ranking by absolute ICER change. " + NOSCEN)
add(223, "The ICER was lower than in the base case only with the lower discount rate, removing the general-population mortality constraint and removing the age adjustment of utilities.",
    "sensitivity_ranking",
    {"op": "select", "refs": SC, "where": {"op": "lt", "rhs": "res_icer"}, "expect": [sc["SC1"], sc["SC6"], sc["SC7"]]},
    "human_review",
    "Selection of scenarios with an ICER below the base case. The lower discount rate scenario is defined relative to the source discount rate and has no meaning against the local rate without a local scenario set. " + NOSCEN)
add(275, "The ICER exceeded £30,000 per QALY with the alternative utility values (£30,270), removing the stopping rule for Drug A (£31,811), the conservative OS extrapolation (£30,205) and setting Drug A time on treatment equal to PFS (£31,528), and remained below it in all other scenarios.",
    "threshold_comparison",
    {"op": "select", "refs": SC, "where": {"op": "gt", "rhs": "wtp_threshold"},
     "expect": [sc["SC3"], sc["SC4"], sc["SC5"], sc["SC8"]]},
    "human_review", "Selection of scenarios above the threshold; locally the comparator is the single reference value in wtp_threshold. " + NOSCEN)
add(277, "The model was quality-assured using a checklist covering input transcription, formula consistency between arms, and extreme-value testing.",
    "external_assertion_untraceable", {"op": "external"}, "human_review",
    "QA process of the global model is not traceable to cells; for the adapted model the evidence is the Model Verifier report, which a person must accept.")
add(277, "The time horizon is sufficient for the modelled cohort, with fewer than 0.1% of patients in either arm alive at the end of the horizon.",
    "model_check",
    {"op": "all", "of": [{"op": "lt", "lhs": "res_int_s_os_horizon", "rhs": "lifetime_check_tol"},
                         {"op": "lt", "lhs": "res_comp_s_os_horizon", "rhs": "lifetime_check_tol"}]},
    "rerender", "Same horizon check as in the methods section. " + " ".join([EFF, POP, TEST]))
add(277, "The deterministic results were reproduced to within numerical precision by an independent implementation of the model in Python.",
    "external_assertion_untraceable", {"op": "external"}, "human_review",
    "Not a model cell; for the adapted model this corresponds to the engine-parity check of the Model Verifier, which must be run and accepted by a person before the sentence is kept.")
add(278, "The general-population mortality constraint was active in 312 weekly cycles in the Drug A arm, from age 96, when 0.02% of patients remained alive, and was not active in the Drug B arm",
    "model_check", {"op": "all", "of": [pos("res_int_gpm_bind_cycles"), zero("res_comp_gpm_bind_cycles")]},
    "rerender",
    "Activity of the mortality cap by arm, re-evaluated on the localised life table. " + " ".join([EFF, POP, TEST]))
add(278, "its effect on the ICER was negligible (Table 8)", "magnitude_judgement",
    {"op": "rel_change_below", "a": sc["SC6"], "b": "res_icer", "tol": {"registry": "negligible_rel_change"}},
    "human_review", "Magnitude wording rule from the constants registry against the no-cap scenario. " + POP + " " + NOSCEN)
add(279, "Modelled medians were within the confidence intervals of the observed medians for all six curves.",
    "external_assertion_untraceable", {"op": "external"}, "human_review",
    "Kaplan-Meier confidence intervals are not in the model. Curves are retained global inputs. " + EFF)
add(281, "The analysis indicates that Drug A provides substantial health gains relative to Drug B, driven mainly by longer overall survival.",
    "magnitude_judgement", None, "human_review",
    "Substantial is a judgement with no wording rule in the registry, and the attribution to overall survival is not a model cell; a person decides the local wording. " + ALL_DEPS)
add(281, "The additional costs arise from drug acquisition and administration during the treatment period and from health state costs accumulated over the longer survival period",
    "ranking",
    {"op": "select", "refs": CAT, "where": {"op": "sign", "sign": "positive"},
     "expect": ["res_inc_cost_drug", "res_inc_cost_admin", "res_inc_cost_pf_state", "res_inc_cost_pd_state"]},
    "regenerate", "Selection of categories with positive incremental cost; rebuild from the local selection. " + COST_DEPS)
add(283, "long-term extrapolation of OS is the main source of structural uncertainty", "magnitude_judgement", None,
    "human_review",
    "Judgement not traceable to cells; with retained trial curves it may still hold, but no local scenario set exists to support it. " + EFF)
add(287, "as discussed in NICE DSU guidance [2]", "jurisdiction_specific", None, "reword",
    "Methodological citation of the source agency; reword as a neutral citation of the technical support document.",
    ["NICE", "DSU"])
add(288, "The base-case ICER lies close to the upper end of the threshold range, so plausible changes in key assumptions move it above that threshold.",
    "threshold_comparison",
    {"op": "all", "of": [{"op": "le", "lhs": "res_icer", "rhs": "wtp_threshold"},
                         {"op": "any", "of": [{"op": "gt", "lhs": r, "rhs": "wtp_threshold"} for r in SC]}]},
    "human_review",
    "Refers to a threshold range that does not exist locally (single reference value), and the second half depends on scenarios. Closeness is a judgement. " + NOSCEN + " " + ALL_DEPS)
add(288, "The stopping rule is a key assumption and should be reflected in the commissioning arrangements for Drug A.",
    "jurisdiction_specific", None, "reword",
    "Commissioning is a source-payer term; locally the stopping rule (int_max_doses) comes from the reimbursement criteria.",
    ["commissioning"])
add(290, "This is below the threshold of £30,000 per QALY gained", "threshold_comparison",
    {"op": "all", "of": [{"op": "le", "lhs": "res_icer", "rhs": "wtp_threshold"}, pos("res_inc_qaly_disc")]},
    "reword",
    "Re-evaluated against wtp_threshold, which locally is a reference value and not an official threshold; reword accordingly. " + ALL_DEPS)
add(290, "within the range of £20,000 to £30,000 per QALY that NICE normally considers to represent a cost-effective use of NHS resources",
    "threshold_comparison",
    {"op": "all", "of": [{"op": "ge", "lhs": "res_icer", "rhs": "wtp_threshold_lower"},
                         {"op": "le", "lhs": "res_icer", "rhs": "wtp_threshold"}]},
    "remove",
    "Source threshold range; the local context has a single reference value and forbids describing a range. " + TEST,
    ["NICE", "NHS"])
add(290, "Drug A can therefore be considered a cost-effective option for adults with previously untreated advanced synthetic carcinoma in the NHS, with the PAS discount and the stopping rule in place.",
    "overall_conclusion",
    {"op": "all", "of": [{"op": "le", "lhs": "res_icer", "rhs": "wtp_threshold"}, pos("res_inc_qaly_disc"), pos("res_inc_nmb")]},
    "reword",
    "Conclusion re-evaluated against the local reference value; remove the payer and PAS wording (no risk-sharing agreement locally), keep the stopping-rule condition. Final wording depends on the GAP-001 resolution. " + ALL_DEPS,
    ["NHS", "PAS"])

reg = {"schema_version": 1,
       "note": "Claims Analyst register for the KR adaptation. Truth values are filled by tools/claims.py.",
       "report": "fixtures/global_report_UK.docx", "model": "fixtures/global_model.xlsx",
       "local_context": {"country": "Republic of Korea", "jurisdiction_from": "UK", "adapted_model": "built"},
       "claims": claims}
Path("work/claims_register.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
print(len(claims))
