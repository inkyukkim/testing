import json
from pathlib import Path

RET_ALL = ("Relies on retained inputs named in the gap register: GAP-002 int_ae_qaly_loss and comp_ae_qaly_loss "
           "(retain_flagged, UK value set), GAP-003 gpu_intercept, gpu_male, gpu_age and gpu_age2 (retain_flagged, UK norms), "
           "GAP-004 lt_qx_male and lt_qx_female from KR-L01 and KR-L02 (retain_flagged, open band carried), "
           "GAP-005 prop_male and baseline_age (retain_flagged, trial cohort) and GAP-006 trial efficacy and exposure "
           "inputs (retain_tagged). Local truth comes from runs/kr_test, built from a TEST-ONLY resolution of the open "
           "blocking gap GAP-001 (c_terminal), so any report from it is a draft and the claim must be re-evaluated once "
           "GAP-001 is resolved by a human.")
RET_COST = ("Relies on GAP-001 (c_terminal, open block; local value is TEST-ONLY) and on the retained inputs of "
            "GAP-005 prop_male and baseline_age (retain_flagged), GAP-004 lt_qx_male and lt_qx_female (retain_flagged) "
            "and GAP-006 trial efficacy and exposure inputs including int_rdi and comp_rdi (retain_tagged).")
RET_SURV = ("Relies on GAP-006 trial efficacy inputs (int_/comp_ pfs, os and tot Weibull parameters, retain_tagged).")
RET_GPM = ("Relies on GAP-004 lt_qx_male and lt_qx_female (Korean mx converted to qx, open top-age band carried; "
           "retain_flagged), GAP-005 prop_male and baseline_age (retain_flagged) and GAP-006 survival inputs (retain_tagged).")
NO_LOCAL_SC = ("No Korean scenario set has been specified, so the local truth is pending for every scenario reference; "
               "the UK scenario SC1 (lower discount rate) is defined relative to the UK reference case and needs a local "
               "definition. A human must specify the local scenarios before this sentence can be regenerated.")
THRESH = ("KR-S07 is a single reference value, not an official threshold and not a range; wtp_threshold_lower was set "
          "equal to it (mapping spec), so no threshold range may be described.")

SC = [f"SC{i}" for i in range(1, 9)]
icer_sc = [f"res_icer@{s}" for s in SC]
INC = ["res_inc_cost_drug", "res_inc_cost_admin", "res_inc_cost_pf_state", "res_inc_cost_pd_state",
       "res_inc_cost_terminal", "res_inc_cost_st", "res_inc_cost_ae"]

C = []
def add(block, excerpt, kind, expr, action, rationale, terms=None):
    c = {"claim_id": f"C{len(C)+1:02d}", "block": block, "excerpt": excerpt, "kind": kind,
         "expression": expr, "action": action, "rationale": rationale}
    if terms:
        c["jurisdiction_terms"] = terms
    C.append(c)

add(1, "Cost-effectiveness analysis: technical report (United Kingdom)", "jurisdiction_specific", None, "reword",
    "Title names the source jurisdiction; replace with the local setting from the country cell (KR-S01).", ["United Kingdom"])
add(5, "from the perspective of the NHS and Personal Social Services (PSS) in England", "jurisdiction_specific", None, "reword",
    "Perspective is localised: the perspective cell is mapped from KR-S04 (healthcare system, total cost regardless of payer).",
    ["NHS", "Personal Social Services", "PSS", "England"])
add(6, "The incremental cost was £24,746 for an incremental gain of 0.875 QALYs", "magnitude_judgement",
    {"op": "all", "of": [{"op": "sign", "ref": "res_inc_total_cost", "sign": "positive"},
                         {"op": "sign", "ref": "res_inc_qaly_disc", "sign": "positive"}]},
    "rerender",
    "Direction words (incremental cost, gain) depend on signs of res_inc_total_cost and res_inc_qaly_disc. The currency "
    "symbol is rendered from currency_code (KR-S02), never converted. " + RET_ALL, ["£"])
add(7, "At the upper end of the range normally considered by NICE (£30,000 per QALY)", "jurisdiction_specific", None, "reword",
    "Agency and threshold-range wording. " + THRESH + " Reword to the local reference value from wtp_threshold.", ["NICE", "£"])
add(7, "Drug A is cost-effective, with an incremental net monetary benefit of £1,514", "threshold_comparison",
    {"op": "all", "of": [{"op": "le", "lhs": "res_icer", "rhs": "wtp_threshold"},
                         {"op": "sign", "ref": "res_inc_nmb", "sign": "positive"}]},
    "rerender",
    "Comparison of res_icer with wtp_threshold and sign of res_inc_nmb. " + THRESH +
    " Wording should say below the reference value rather than imply an official threshold. " + RET_ALL, ["£"])
add(7, "At £20,000 per QALY, Drug A is not cost-effective.", "threshold_comparison",
    {"op": "gt", "lhs": "res_icer", "rhs": "wtp_threshold_lower"}, "remove",
    "Refers to the lower bound of the UK threshold range. " + THRESH + " The sentence does not apply locally.", ["£"])
add(8, "the ICER was most sensitive to removing the stopping rule for Drug A and setting Drug A time on treatment equal to PFS",
    "sensitivity_ranking",
    {"op": "rank_abs_change", "refs": icer_sc, "base": "res_icer", "expect_order": ["res_icer@SC4", "res_icer@SC8"]},
    "human_review", "Ranking of scenario ICER changes. " + NO_LOCAL_SC + " " + RET_ALL)
add(10, "first-line systemic therapy with a platinum doublet is assumed to be the established standard of care in the NHS",
    "jurisdiction_specific", None, "human_review",
    "Local clinical fact: whether Drug B reflects the Korean standard of care has not been confirmed by local clinicians.",
    ["NHS"])
add(23, "NHS and PSS", "jurisdiction_specific", None, "reword",
    "Perspective row of the decision-problem table; reword from the perspective cell mapped from KR-S04.", ["NHS", "PSS"])
add(26, "The analysis follows the NICE reference case [1].", "jurisdiction_specific", None, "reword",
    "Replace with the local pharmacoeconomic guideline (synthetic placeholder) named by the HEOR lead.", ["NICE reference case"])
add(26, "Health effects are expressed in quality-adjusted life years (QALYs) using EQ-5D-3L values from the pivotal trial",
    "jurisdiction_specific", None, "reword",
    "State utilities u_pf and u_pd are mapped from KR-U01 and KR-U02 (Korean EQ-5D-5L value set); AE disutilities "
    "int_ae_qaly_loss and comp_ae_qaly_loss are retained under GAP-002 (retain_flagged, UK EQ-5D-3L value set) and "
    "population norms under GAP-003 (retain_flagged). The wording must state the mixed value sets.")
add(26, "costs reflect NHS list prices and national reference costs", "jurisdiction_specific", None, "reword",
    "Local costs come from the Korean sources of KR-C01 to KR-C13 and KR-T01 to KR-T03 (drug list, fee schedule, claims "
    "analysis). Terminal care (c_terminal) is GAP-001, open block; the run uses a TEST-ONLY value.",
    ["NHS", "national reference costs"])
add(26, "A confidential patient access scheme (PAS) discount is applied to the price of Drug A in all analyses.",
    "jurisdiction_specific", None, "remove",
    "No risk-sharing agreement applies in the local submission (KR-C15); int_vial_price is the Korean list price (KR-C01).",
    ["patient access scheme", "PAS"])
add(30, "the modelled proportion alive at the end of the horizon is below 0.1% in each arm", "model_check",
    {"op": "all", "of": [{"op": "lt", "lhs": "res_int_s_os_horizon", "rhs": "lifetime_check_tol"},
                         {"op": "lt", "lhs": "res_comp_s_os_horizon", "rhs": "lifetime_check_tol"}]},
    "rerender", "Horizon adequacy check against lifetime_check_tol (retained structural setting). " + RET_GPM)
add(31, "the value implied by national life tables", "scope_statement", None, "reword",
    "The life table is now Korean: lt_qx_male and lt_qx_female are converted from KR-L01 and KR-L02 central death rates "
    "(exponential method) with the open top-age band rate carried to the oldest model ages; GAP-004 is retain_flagged and "
    "must be named as a limitation.")
add(32, "in line with the reference case", "jurisdiction_specific", None, "reword",
    "Discount rates dr_costs and dr_outcomes are mapped from KR-S05 and KR-S06 (local guideline); refer to the local "
    "guideline, not the UK reference case.")
add(34, "following the NICE Decision Support Unit guidance on survival analysis [3]", "jurisdiction_specific", None, "reword",
    "Agency wording outside the References; keep the citation as published methods guidance. " + RET_SURV,
    ["NICE", "Decision Support Unit"])
add(64, "The fitted PFS and OS curves did not cross in either arm.", "model_check",
    {"op": "all", "of": [{"op": "sign", "ref": "check_cross_int", "sign": "zero"},
                         {"op": "sign", "ref": "check_cross_comp", "sign": "zero"}]},
    "rerender", "Curve-crossing checks of the model. " + RET_SURV)
add(66, "consistent with the stopping rule in the trial protocol", "scope_statement", None, "reword",
    "Locally int_max_doses is mapped from the Korean reimbursed maximum treatment duration KR-C05 (duration_to_doses), "
    "not from the trial protocol; reword the source of the stopping rule.")
add(69, "Drug acquisition costs for Drug A reflect the list price net of the confidential PAS discount.",
    "jurisdiction_specific", None, "reword",
    "int_vial_price is the Korean list price (KR-C01) with no risk-sharing agreement (KR-C15); reword to a list price.",
    ["PAS"])
add(69, "The cost of Drug B was taken from the electronic market information tool (eMIT).", "jurisdiction_specific",
    None, "reword", "comp_vial_price is mapped from KR-C06 (Korean drug list).",
    ["electronic market information tool", "eMIT"])
add(69, "Administration costs per intravenous infusion are based on NHS reference costs.", "jurisdiction_specific",
    None, "reword", "Administration costs are mapped from KR-C08 (Korean fee schedule).", ["NHS reference costs"])
add(69, "valued using PSSRU unit costs", "jurisdiction_specific", None, "reword",
    "c_pf_week and c_pd_week are converted from KR-C09 and KR-C10 (Korean claims analysis, monthly to weekly).", ["PSSRU"])
add(69, "A one-off terminal care cost is applied to each death.", "scope_statement", None, "human_review",
    "c_terminal is GAP-001 (non_transferable, block, open). The run directory uses a TEST-ONLY resolution; a human must "
    "resolve the gap (local data, local literature or an approved method change) before this method statement can stand.")
add(70, "All costs are in GBP at 2025 prices.", "jurisdiction_specific", None, "reword",
    "Currency from currency_code (KR-S02) and price year from price_year (KR-S03); no conversion of UK values.", ["GBP"])
add(131, "valued using the UK time trade-off value set, consistent with the NICE reference case", "jurisdiction_specific",
    None, "reword",
    "u_pf and u_pd are mapped from KR-U01 and KR-U02 (Korean EQ-5D-5L value set) under the local guideline.",
    ["UK time trade-off value set", "NICE reference case"])
add(131, "using a regression on age and sex from UK population norms", "jurisdiction_specific", None, "human_review",
    "gpu_intercept, gpu_male, gpu_age and gpu_age2 are retained UK norms under GAP-003 (partial, retain_flagged, open): "
    "the wording is accurate but must be flagged as a retained global input on a different value set and listed as a "
    "limitation; a human decides whether to cite Korean norms or rely on the scenario without age adjustment.",
    ["UK population norms"])
add(131, "Quality-of-life losses associated with severe (grade three or higher) adverse events were applied as one-off QALY decrements at the start of the model.",
    "scope_statement", None, "reword",
    "int_ae_qaly_loss and comp_ae_qaly_loss are retained under GAP-002 (partial, retain_flagged): tag them as retained "
    "global values valued with a different value set from the local state utilities.")
add(155, "Drug A increased discounted life years by 1.37 and QALYs by 0.875 compared with Drug B, at an additional cost of £24,746.",
    "magnitude_judgement",
    {"op": "all", "of": [{"op": "sign", "ref": "res_inc_ly_disc", "sign": "positive"},
                         {"op": "sign", "ref": "res_inc_qaly_disc", "sign": "positive"},
                         {"op": "sign", "ref": "res_inc_total_cost", "sign": "positive"}]},
    "rerender", "Direction words (increased, additional) depend on the signs of incremental results; currency symbol "
    "rendered from currency_code. " + RET_ALL, ["£"])
add(181, "incremental values and the ICER are calculated from unrounded results and may differ slightly from values recalculated from the rounded figures shown",
    "rounding_disclosure", None, "rerender",
    "Rounding disclosure; holds for any recalculated workbook and is checked by the report verifier, not by a cell.")
add(184, "The largest single contributor to incremental costs was drug acquisition (£16,309).", "ranking",
    {"op": "argmax", "refs": INC, "expect": "res_inc_cost_drug"}, "regenerate",
    "Selection of the largest incremental cost category; rebuild from the local evaluation. " + RET_COST, ["£"])
add(184, "Lower subsequent therapy, adverse event and terminal care costs with Drug A partially offset its higher costs in other categories.",
    "ranking",
    {"op": "select", "refs": INC, "where": {"op": "sign", "sign": "negative"},
     "expect": ["res_inc_cost_terminal", "res_inc_cost_st", "res_inc_cost_ae"]},
    "regenerate", "Selection of categories with negative incremental cost; terminal care depends on the TEST-ONLY "
    "value of c_terminal. " + RET_COST)
add(185, "Table 7. Disaggregated discounted costs (GBP)", "jurisdiction_specific", None, "reword",
    "Caption currency from currency_code (KR-S02).", ["GBP"])
add(223, "Removing the stopping rule for Drug A had the largest effect on the ICER, followed by setting Drug A time on treatment equal to PFS and the alternative utility values.",
    "sensitivity_ranking",
    {"op": "rank_abs_change", "refs": icer_sc, "base": "res_icer",
     "expect_order": ["res_icer@SC4", "res_icer@SC8", "res_icer@SC3"]},
    "human_review", "Ranking of scenario effects. " + NO_LOCAL_SC + " " + RET_ALL)
add(223, "The ICER was lower than in the base case only with the lower discount rate, removing the general-population mortality constraint and removing the age adjustment of utilities.",
    "sensitivity_ranking",
    {"op": "select", "refs": icer_sc, "where": {"op": "lt", "rhs": "res_icer"},
     "expect": ["res_icer@SC1", "res_icer@SC6", "res_icer@SC7"]},
    "human_review", "Selection of scenarios with a lower ICER. " + NO_LOCAL_SC + " " + RET_ALL)
add(275, "The ICER exceeded £30,000 per QALY with the alternative utility values (£30,270), removing the stopping rule for Drug A (£31,811), the conservative OS extrapolation (£30,205) and setting Drug A time on treatment equal to PFS (£31,528), and remained below it in all other scenarios.",
    "threshold_comparison",
    {"op": "select", "refs": icer_sc, "where": {"op": "gt", "rhs": "wtp_threshold"},
     "expect": ["res_icer@SC3", "res_icer@SC4", "res_icer@SC5", "res_icer@SC8"]},
    "human_review", "Selection of scenarios above wtp_threshold. " + NO_LOCAL_SC + " " + THRESH + " " + RET_ALL, ["£"])
add(277, "The model was quality-assured using a checklist covering input transcription, formula consistency between arms, and extreme-value testing.",
    "external_assertion_untraceable", {"op": "external"}, "human_review",
    "QA process statement about the global model; not traceable to a cell and not repeated for the adapted model.")
add(277, "Both treatment arms use identical formula layouts that differ only in the arm-specific parameter block.",
    "external_assertion_untraceable", {"op": "external"}, "human_review",
    "Structural assertion not traceable to a named cell; no model verification output exists in runs/kr_test.")
add(277, "State membership sums to one in every cycle by construction.", "external_assertion_untraceable",
    {"op": "external"}, "human_review",
    "No named check cell; confirm with the trace invariants of tools/verify_model on runs/kr_test, which has no "
    "verification output yet.")
add(277, "with fewer than 0.1% of patients in either arm alive at the end of the horizon", "model_check",
    {"op": "all", "of": [{"op": "lt", "lhs": "res_int_s_os_horizon", "rhs": "lifetime_check_tol"},
                         {"op": "lt", "lhs": "res_comp_s_os_horizon", "rhs": "lifetime_check_tol"},
                         {"op": "eq", "lhs": "check_lifetime_ok", "rhs": {"text": "OK"}}]},
    "rerender", "Horizon adequacy check. " + RET_GPM)
add(277, "The deterministic results were reproduced to within numerical precision by an independent implementation of the model in Python.",
    "external_assertion_untraceable", {"op": "external"}, "human_review",
    "Parity statement for the global model; engine parity has not been reported for the adapted model in runs/kr_test.")
add(278, "The general-population mortality constraint was active in 312 weekly cycles in the Drug A arm, from age 96, when 0.02% of patients remained alive, and was not active in the Drug B arm",
    "model_check",
    {"op": "all", "of": [{"op": "sign", "ref": "res_int_gpm_bind_cycles", "sign": "positive"},
                         {"op": "sign", "ref": "res_comp_gpm_bind_cycles", "sign": "zero"}]},
    "rerender", "Active and not active depend on the binding-cycle counts. " + RET_GPM)
add(278, "its effect on the ICER was negligible (Table 8)", "magnitude_judgement",
    {"op": "rel_change_below", "a": "res_icer@SC6", "b": "res_icer", "tol": {"registry": "negligible_rel_change"}},
    "human_review", "Negligible per the registry rule negligible_rel_change, using scenario SC6. " + NO_LOCAL_SC +
    " " + RET_GPM)
add(279, "Modelled medians were within the confidence intervals of the observed medians for all six curves.",
    "external_assertion_untraceable", {"op": "external"}, "human_review",
    "Kaplan-Meier medians and confidence intervals are not in the model; the curves are retained under GAP-006 "
    "(retain_tagged), so the statement may carry over but cannot be traced.")
add(281, "The analysis indicates that Drug A provides substantial health gains relative to Drug B, driven mainly by longer overall survival.",
    "magnitude_judgement",
    {"op": "all", "of": [{"op": "sign", "ref": "res_inc_qaly_disc", "sign": "positive"},
                         {"op": "gt", "lhs": "res_int_median_os", "rhs": "res_comp_median_os"}]},
    "human_review",
    "The tool checks direction only; substantial and driven mainly have no registry rule, so a person must judge them. "
    "State utilities are local while AE disutilities (GAP-002) and norms (GAP-003) are retained. " + RET_ALL)
add(281, "The additional costs arise from drug acquisition and administration during the treatment period and from health state costs accumulated over the longer survival period, partly offset by lower subsequent therapy costs.",
    "ranking",
    {"op": "all", "of": [
        {"op": "select", "refs": INC, "where": {"op": "sign", "sign": "positive"},
         "expect": ["res_inc_cost_drug", "res_inc_cost_admin", "res_inc_cost_pf_state", "res_inc_cost_pd_state"]},
        {"op": "sign", "ref": "res_inc_cost_st", "sign": "negative"}]},
    "regenerate", "Selection of cost drivers and offsets; rebuild from the local evaluation. " + RET_COST)
add(283, "long-term extrapolation of OS is the main source of structural uncertainty", "external_assertion_untraceable",
    {"op": "external"}, "human_review",
    "Judgement not traceable to a cell; in the global scenarios the stopping rule had the largest effect. Survival inputs "
    "are retained under GAP-006 (retain_tagged).")
add(287, "as discussed in NICE DSU guidance [2]", "jurisdiction_specific", None, "reword",
    "Agency wording outside the References; keep the citation.", ["NICE", "DSU"])
add(288, "The base-case ICER lies close to the upper end of the threshold range, so plausible changes in key assumptions move it above that threshold.",
    "magnitude_judgement",
    {"op": "any", "of": [{"op": "gt", "lhs": r, "rhs": "wtp_threshold"} for r in icer_sc]},
    "human_review", THRESH + " Closeness has no registry rule, and the scenario part needs local scenarios. " +
    NO_LOCAL_SC + " " + RET_ALL)
add(288, "The stopping rule is a key assumption and should be reflected in the commissioning arrangements for Drug A.",
    "jurisdiction_specific", None, "human_review",
    "Commissioning is a UK payer term; locally the maximum duration already comes from the reimbursement criteria "
    "(KR-C05). Whether the stopping rule is a key assumption locally needs the local scenario set.", ["commissioning"])
add(290, "This is below the threshold of £30,000 per QALY gained", "threshold_comparison",
    {"op": "lt", "lhs": "res_icer", "rhs": "wtp_threshold"}, "rerender",
    "Comparison of res_icer with wtp_threshold (KR-S07). " + THRESH + " Reword threshold to reference value. " + RET_ALL,
    ["£"])
add(290, "within the range of £20,000 to £30,000 per QALY that NICE normally considers to represent a cost-effective use of NHS resources",
    "threshold_comparison",
    {"op": "all", "of": [{"op": "ge", "lhs": "res_icer", "rhs": "wtp_threshold_lower"},
                         {"op": "le", "lhs": "res_icer", "rhs": "wtp_threshold"}]},
    "remove", "UK threshold range and agency. " + THRESH, ["£", "NICE", "NHS"])
add(290, "Drug A can therefore be considered a cost-effective option for adults with previously untreated advanced synthetic carcinoma in the NHS, with the PAS discount and the stopping rule in place.",
    "overall_conclusion", {"op": "eq", "lhs": "res_below_wtp", "rhs": {"text": "Yes"}}, "reword",
    "Conclusion follows res_below_wtp. Reword: Korean healthcare system instead of NHS, no PAS (KR-C15), stopping rule "
    "from the reimbursement criteria (KR-C05); " + THRESH + " The conclusion is a draft: " + RET_ALL,
    ["NHS", "PAS"])

reg = {"schema_version": 1,
       "note": "Claims register for the KR adaptation of the UK global report. Truth values are filled by tools/claims.py.",
       "report": "fixtures/global_report_UK.docx", "model": "fixtures/global_model.xlsx",
       "local_context": {"country": "Republic of Korea", "jurisdiction_from": "UK", "adapted_model": "built"},
       "claims": C}
Path("work/claims_register.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False))
print(len(C))
