"""Write work/mapping_spec.json and work/gap_register.yaml (references only, no values)."""
import json
import yaml

AGENT = {"kind": "agent", "role": "Input Mapper"}
CLIN = ["pfs_shape", "pfs_scale", "pfs_corr", "os_shape", "os_scale", "os_corr",
        "tot_shape", "tot_scale", "tot_corr", "p_death_first_pfs", "rdi"]
EFFICACY = [f"{arm}_{p}" for arm in ("int", "comp") for p in CLIN]
GPU = ["gpu_intercept", "gpu_male", "gpu_age", "gpu_age2"]


def esc(*opts):
    return [{"option_id": f"E{i + 1}", "action": a, "description": d} for i, (a, d) in enumerate(opts)]


gaps = [
    {
        "gap_id": "GAP-001", "target_names": ["c_terminal"], "source_items": ["KR-C11"],
        "description": "Terminal care cost (one-off at death) is not supplied in the Korean inputs; KR-C11 is empty and a local study is pending.",
        "class": "non_transferable", "handling": "block", "retained_source": None,
        "rationale": "Terminal care cost is a local health-system unit cost; the global UK value must not be used, converted or set to zero, so the pipeline stops until a human supplies local evidence.",
        "escalation_options": esc(
            ("obtain_local_data", "Obtain the pending Korean end-of-life costing study and populate KR-C11 in KRW."),
            ("cite_local_literature", "Cite a published Korean end-of-life cost estimate for the target population, reviewed by a local health economist."),
            ("expert_elicitation", "Structured elicitation of Korean end-of-life resource use valued with the local fee schedule."),
            ("approved_method_change", "Human-approved change to the costing method, documented and disclosed as a limitation.")),
        "prohibited_options": [
            "Convert the global UK terminal care cost to KRW with the reference exchange rate KR-S09.",
            "Retain the global UK terminal care cost.",
            "Set terminal care cost to zero or omit the cost component silently.",
            "Scale the UK value by a ratio of other Korean to UK costs."],
        "decided_by": AGENT, "status": "open", "resolution": None,
    },
    {
        "gap_id": "GAP-002", "target_names": EFFICACY, "source_items": [],
        "description": "Trial efficacy and exposure parameters (Weibull PFS, OS and time-on-treatment fits and their PSA correlations, share of PFS events that are deaths, relative dose intensity) for both arms are not supplied locally; the input Overview sheet states they are to be retained.",
        "class": "transferable", "handling": "retain_tagged", "retained_source": EFFICACY,
        "rationale": "Relative and absolute trial efficacy and dose intensity are expected to transfer across settings; the global values are retained and tagged as retained global inputs in the report.",
        "escalation_options": esc(
            ("cite_local_literature", "Cite Korean or East Asian subgroup data supporting transferability of the trial efficacy."),
            ("retain_with_scenario", "Run a scenario with alternative survival extrapolations if a reviewer questions transferability.")),
        "prohibited_options": ["Recalibrate the survival curves by hand to match Korean registry survival without an approved method."],
        "decided_by": AGENT, "status": "open", "resolution": None,
    },
    {
        "gap_id": "GAP-003", "target_names": ["baseline_age"], "source_items": [],
        "description": "Mean age at baseline is not supplied for the Korean population; the global trial baseline age is retained.",
        "class": "transferable", "handling": "retain_flagged", "retained_source": ["baseline_age"],
        "rationale": "Baseline age is consistent with the trial population behind the retained efficacy, but it drives general-population mortality from the Korean life table and the utility age adjustment, so a reviewer should confirm it represents Korean patients.",
        "escalation_options": esc(
            ("obtain_local_data", "Obtain mean age of the target population from the Korean cancer registry."),
            ("retain_with_scenario", "Report a scenario using a local registry baseline age.")),
        "prohibited_options": ["Guess a Korean baseline age without a cited source."],
        "decided_by": AGENT, "status": "open", "resolution": None,
    },
    {
        "gap_id": "GAP-004", "target_names": ["prop_male"], "source_items": ["KR-P03"],
        "description": "Proportion male is not supplied (KR-P03 empty; note says the trial population is assumed); the global trial value is retained.",
        "class": "transferable", "handling": "retain_flagged", "retained_source": ["prop_male"],
        "rationale": "The local affiliate assumes the trial population; the value weights sex-specific Korean mortality and the utility norms, so it is flagged for review.",
        "escalation_options": esc(
            ("obtain_local_data", "Obtain the sex distribution of the target population from the Korean cancer registry."),
            ("retain_with_scenario", "Report a scenario using a local registry sex distribution.")),
        "prohibited_options": ["Assume an even sex split without a source."],
        "decided_by": AGENT, "status": "open", "resolution": None,
    },
    {
        "gap_id": "GAP-005", "target_names": ["int_ae_qaly_loss", "comp_ae_qaly_loss"], "source_items": ["KR-U03"],
        "description": "AE QALY loss (one-off) for both arms is not supplied (KR-U03 empty, no local estimate); the global values are retained.",
        "class": "partial", "handling": "retain_flagged", "retained_source": ["int_ae_qaly_loss", "comp_ae_qaly_loss"],
        "rationale": "AE incidence and duration come from the trial and transfer, but the disutility valuation is UK-based while health-state utilities now use the Korean value set; the inconsistency is flagged as a limitation.",
        "escalation_options": esc(
            ("cite_local_literature", "Cite Korean AE disutility estimates valued with the Korean value set."),
            ("obtain_local_data", "Revalue trial AE disutility with the Korean EQ-5D-5L value set."),
            ("retain_with_scenario", "Report a scenario excluding or varying AE QALY loss.")),
        "prohibited_options": ["Set AE QALY loss to zero silently."],
        "decided_by": AGENT, "status": "open", "resolution": None,
    },
    {
        "gap_id": "GAP-006", "target_names": GPU, "source_items": ["KR-U04"],
        "description": "Korean general-population utility norms by age and sex are not supplied (KR-U04 empty); the global UK norms regression coefficients are retained for the age adjustment of utilities.",
        "class": "partial", "handling": "retain_flagged", "retained_source": GPU,
        "rationale": "The structure of the multiplicative age adjustment transfers, but the norms are country-specific calibration; the UK coefficients are retained and flagged as a limitation.",
        "escalation_options": esc(
            ("cite_local_literature", "Cite published Korean EQ-5D population norms by age and sex and refit the regression."),
            ("obtain_local_data", "Obtain Korean population norms from a national health survey."),
            ("retain_with_scenario", "Report a scenario with the utility age adjustment switched off.")),
        "prohibited_options": ["Rescale UK norms to Korean levels by an ad hoc factor."],
        "decided_by": AGENT, "status": "open", "resolution": None,
    },
    {
        "gap_id": "GAP-007", "target_names": ["lt_qx_male", "lt_qx_female"], "source_items": ["KR-L01", "KR-L02"],
        "description": "The Korean life table gives central death rates mx by single age with an open band at the top age, while the model needs annual probabilities qx by single age up to the model's last life-table age; qx are derived by mx_to_qx with the exponential method and the open-band rate carried to the older ages.",
        "class": "partial", "handling": "retain_flagged", "retained_source": ["KR-L01", "KR-L02"],
        "rationale": "The life-table structure transfers and the rates are local, but the mx to qx conversion method and the carried open-band rate are assumptions that a reviewer should approve.",
        "escalation_options": esc(
            ("obtain_local_data", "Obtain the official Korean complete life table with qx and single ages beyond the open band."),
            ("approved_method_change", "Approve the actuarial conversion or a fitted old-age mortality model instead of carrying the open-band rate."),
            ("retain_with_scenario", "Report a scenario with the alternative conversion method.")),
        "prohibited_options": ["Fill older ages from the UK life table.", "Use mx directly as qx."],
        "decided_by": AGENT, "status": "open", "resolution": None,
    },
]

register = {
    "schema_version": 1,
    "adaptation": {"model": "fixtures/global_model.xlsx", "local_inputs": "fixtures/adaptation_input_KR.xlsx",
                   "country": "Republic of Korea"},
    "gaps": gaps,
}


def mapped(target, op, rationale, **args):
    return {"target": target, "status": "mapped", "operation": op, "args": args, "rationale": rationale}


def structural(target, rationale):
    return {"target": target, "status": "retained", "operation": "retain_global",
            "basis": "structural_setting", "rationale": rationale}


def confirmed(target, item, pattern, rationale, field="value"):
    return {"target": target, "status": "retained", "operation": "retain_global",
            "basis": "confirmed_by_local_text",
            "confirm_in_source": {"item": item, "field": field, "pattern": pattern}, "rationale": rationale}


def gap_retain(target, gid, rationale):
    return {"target": target, "status": "retained", "operation": "retain_global", "gap_id": gid,
            "rationale": rationale}


M = []
# Settings
M += [
    mapped("country", "copy", "Country of the adaptation from KR-S01.", source="KR-S01"),
    mapped("currency_code", "copy", "Currency KRW from KR-S02; all currency inputs are remapped from local sources, none converted.", source="KR-S02"),
    mapped("price_year", "copy", "Local price year from KR-S03.", source="KR-S03"),
    mapped("perspective", "copy", "Korean healthcare system perspective (insurer plus out-of-pocket, total cost) from KR-S04.", source="KR-S04"),
    mapped("dr_costs", "copy", "Korean guideline discount rate for costs from KR-S05 (note asks to verify against the current guideline).", source="KR-S05"),
    mapped("dr_outcomes", "copy", "Korean guideline discount rate for outcomes from KR-S06 (note asks to verify against the current guideline).", source="KR-S06"),
    mapped("wtp_threshold", "copy", "Korean reference ICER threshold from KR-S07; a reference value, not an official threshold.", source="KR-S07"),
    mapped("wtp_threshold_lower", "copy", "Korea has a single reference threshold instead of a range, so the lower bound is mapped from the same item KR-S07 (decision D09); the global bound is not kept.", source="KR-S07"),
    structural("cycle_length_days", "Model cycle length is a structural setting of the global model; not a local input."),
    structural("days_per_year", "Calendar convention of the model; the per-month conversion of KR-C09 and KR-C10 is cross-checked against it by the tool."),
    structural("time_horizon_years", "KR-S08 states a lifetime horizon and asks to retain the global one; the label does not confirm the number of years, so it is retained as a structural setting."),
    structural("lifetime_check_tol", "QA tolerance of the model check, not a country input."),
    structural("use_gpm_cap", "Switch of the general-population mortality cap; base-case method choice retained (the cap now uses the Korean life table)."),
    structural("use_age_util_adj", "Switch of the utility age adjustment; base-case method choice retained (norms retained under GAP-006)."),
    structural("psa_seed", "PSA control setting on the placeholder sheet; not a country input."),
    structural("psa_iterations", "PSA control setting on the placeholder sheet; not a country input."),
]
# Population
M += [
    gap_retain("baseline_age", "GAP-003", "No Korean baseline age supplied; trial baseline retained and flagged (GAP-003)."),
    gap_retain("prop_male", "GAP-004", "KR-P03 is empty with a note that the trial population is assumed; retained and flagged (GAP-004)."),
    mapped("weight_mean_kg", "copy", "Korean mean body weight of adults with advanced disease from KR-P01; drives mg/kg vial use.", source="KR-P01"),
    mapped("weight_sd_kg", "copy", "Korean SD of body weight from KR-P02; used in the lognormal vial calculation.", source="KR-P02"),
]
# Clinical efficacy
for t in EFFICACY:
    M.append(gap_retain(t, "GAP-002", "Trial efficacy or exposure parameter; transferable, retained global value tagged as a retained global input (GAP-002), as the Overview sheet instructs."))
# Drug A costs and dosing
M += [
    confirmed("int_dose_weight_based", "KR-C02", "mg/kg", "Switch for weight-based dosing; the Korean label dose KR-C02 is stated in mg/kg, confirming weight-based dosing.", field="unit"),
    mapped("int_dose_mg", "copy", "Drug A dose per kg from the Korean label, KR-C02 (no vial sharing, as in the model).", source="KR-C02"),
    mapped("int_vial_mg", "copy", "Drug A vial size from the Korean label, KR-C03.", source="KR-C03"),
    mapped("int_vial_price", "copy", "Drug A price per vial from the Korean drug list, KR-C01. The global input is a net confidential-discount price; KR-C15 states no risk-sharing agreement applies, so the local list price is the correct local price.", source="KR-C01"),
    mapped("int_admin_cost_per_admin", "copy", "Korean chemotherapy infusion fee per visit, KR-C08, which applies to both arms.", source="KR-C08"),
    confirmed("int_admin_interval_weeks", "KR-C04", "Q{value}W", "Korean label schedule KR-C04 states the same three-weekly interval as the model; retained and checked against the text."),
    mapped("int_max_doses", "duration_to_doses", "Korean reimbursement caps Drug A treatment at a maximum duration in years (KR-C05); converted to a dose count with the model administration interval. Rule doses_starting_within: the first dose is at time zero, so every dose starting within the reimbursed period is counted.", source="KR-C05", interval_weeks_from="int_admin_interval_weeks", rule="doses_starting_within"),
    mapped("int_ae_cost", "copy", "Korean Drug A adverse event cost (one-off), KR-C12.", source="KR-C12"),
]
# Drug B costs and dosing
M += [
    confirmed("comp_dose_weight_based", "KR-C07", "mg flat", "Switch for weight-based dosing; KR-C07 states a flat dose, confirming flat dosing for Drug B."),
    confirmed("comp_dose_mg", "KR-C07", "{value} mg flat", "Drug B flat dose stated in the Korean schedule KR-C07 equals the model value; retained and checked against the text."),
    confirmed("comp_vial_mg", "KR-C06", "({value} mg)", "Drug B vial size is stated in the label of the Korean price item KR-C06 and equals the model value; retained and checked against the item label.", field="item"),
    mapped("comp_vial_price", "copy", "Drug B price per vial from the Korean drug list, KR-C06.", source="KR-C06"),
    mapped("comp_admin_cost_per_admin", "copy", "Korean chemotherapy infusion fee per visit, KR-C08, which applies to both arms.", source="KR-C08"),
    confirmed("comp_admin_interval_weeks", "KR-C07", "Q{value}W", "Korean schedule KR-C07 states the same three-weekly interval as the model; retained and checked against the text."),
    confirmed("comp_max_doses", "KR-C07", "maximum {value} cycles", "Korean schedule KR-C07 states the same maximum number of treatment cycles (one dose per cycle) as the model dose cap; retained and checked against the text."),
    mapped("comp_ae_cost", "copy", "Korean Drug B adverse event cost (one-off), KR-C13.", source="KR-C13"),
]
# State costs, terminal care, subsequent therapy
M += [
    mapped("c_pf_week", "per_period_to_per_week", "Korean progression-free state cost is per month (KR-C09); converted to per week by the tool from model days_per_year and the registry, cross-checked against the month length stated in the unit.", source="KR-C09", period="month"),
    mapped("c_pd_week", "per_period_to_per_week", "Korean progressed disease state cost is per month (KR-C10); converted to per week by the tool from model days_per_year and the registry, cross-checked against the month length stated in the unit.", source="KR-C10", period="month"),
    {"target": "c_terminal", "status": "gap", "gap_id": "GAP-001",
     "rationale": "Korean terminal care cost KR-C11 is missing; a non-transferable local unit cost, so the pipeline is blocked (GAP-001). No UK value, conversion or zero."},
    mapped("st_cost_1", "copy", "Model category docetaxel-based chemotherapy corresponds to the Korean category docetaxel, KR-T01 (drug plus administration per course).", source="KR-T01"),
    mapped("st_cost_2", "copy", "Model category immunotherapy corresponds to the Korean category immune checkpoint inhibitor, KR-T02.", source="KR-T02"),
    mapped("st_cost_3", "copy", "Model category other targeted therapy corresponds to the Korean category other targeted agents, KR-T03.", source="KR-T03"),
    mapped("int_st_share_1", "copy", "Share of Drug A progressors receiving docetaxel, Korean expert panel KR-T04.", source="KR-T04"),
    mapped("int_st_share_2", "copy", "Share of Drug A progressors receiving an immune checkpoint inhibitor, KR-T05 (IO re-treatment not reimbursed in Korea).", source="KR-T05"),
    mapped("int_st_share_3", "copy", "Share of Drug A progressors receiving other targeted agents, KR-T06.", source="KR-T06"),
    mapped("comp_st_share_1", "copy", "Share of Drug B progressors receiving docetaxel, KR-T07.", source="KR-T07"),
    mapped("comp_st_share_2", "copy", "Share of Drug B progressors receiving an immune checkpoint inhibitor, KR-T08.", source="KR-T08"),
    mapped("comp_st_share_3", "copy", "Share of Drug B progressors receiving other targeted agents, KR-T09.", source="KR-T09"),
]
# Utilities
M += [
    mapped("u_pf", "copy", "Korean progression-free utility, EQ-5D-5L Korean value set, KR-U01.", source="KR-U01"),
    mapped("u_pd", "copy", "Korean progressed disease utility, EQ-5D-5L Korean value set, KR-U02.", source="KR-U02"),
    gap_retain("int_ae_qaly_loss", "GAP-005", "KR-U03 empty; global AE QALY loss retained and flagged (GAP-005)."),
    gap_retain("comp_ae_qaly_loss", "GAP-005", "KR-U03 empty; global AE QALY loss retained and flagged (GAP-005)."),
]
for t in GPU:
    M.append(gap_retain(t, "GAP-006", "Korean population utility norms KR-U04 not supplied; UK norms coefficient retained and flagged (GAP-006)."))
# Life table
M += [
    structural("lt_age", "Single-year age index of the model life table; structure retained, local rates are mapped onto it."),
    {**mapped("lt_qx_male", "mx_to_qx", "Korean male central death rates KR-L01 converted to qx by the exponential method (constant hazard within each year of age), open top band rate carried to older model ages; partial gap GAP-007.", source="KR-L01", method="exponential", open_band="carry_last_rate"), "gap_id": "GAP-007"},
    {**mapped("lt_qx_female", "mx_to_qx", "Korean female central death rates KR-L02 converted to qx by the exponential method (constant hazard within each year of age), open top band rate carried to older model ages; partial gap GAP-007.", source="KR-L02", method="exponential", open_band="carry_last_rate"), "gap_id": "GAP-007"},
]

spec = {
    "schema_version": 1,
    "note": "Input Mapper output for the Korean adaptation; references and declared operations only.",
    "model": "fixtures/global_model.xlsx",
    "local_inputs": "fixtures/adaptation_input_KR.xlsx",
    "gap_register": "work/gap_register.yaml",
    "mappings": M,
    "unused_local_items": [
        {"item": "KR-S08", "reason": "Text label confirming a lifetime horizon; it does not state the number of years, so time_horizon_years is retained as a structural setting."},
        {"item": "KR-S09", "reason": "Reference exchange rate, marked for information only; using it to convert global inputs is prohibited."},
        {"item": "KR-C14", "reason": "Patient co-payment rate is informational; the perspective counts total cost regardless of payer, and the model has no co-payment input."},
        {"item": "KR-C15", "reason": "States that no risk-sharing agreement applies (list prices); supports using list prices KR-C01 and KR-C06, no model input of its own."},
    ],
}

class NoAlias(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

with open("work/gap_register.yaml", "w") as f:
    yaml.dump(register, f, Dumper=NoAlias, sort_keys=False, allow_unicode=True, width=100)
with open("work/mapping_spec.json", "w") as f:
    json.dump(spec, f, indent=2)
print(len(M))
