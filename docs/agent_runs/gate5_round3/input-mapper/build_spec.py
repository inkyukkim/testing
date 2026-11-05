import json
M = []
def mp(t, src, rat, op="copy", **args):
    a = {"source": src}; a.update(args)
    M.append({"target": t, "status": "mapped", "operation": op, "args": a, "rationale": rat})
def ret(t, rat, gap_id=None, basis=None, confirm=None):
    e = {"target": t, "status": "retained", "operation": "retain_global"}
    if gap_id: e["gap_id"] = gap_id
    if basis: e["basis"] = basis
    if confirm: e["confirm_in_source"] = confirm
    e["rationale"] = rat; M.append(e)
def gap(t, gid, rat):
    M.append({"target": t, "status": "gap", "gap_id": gid, "rationale": rat})

# Settings
mp("country", "KR-S01", "Local setting name.")
mp("currency_code", "KR-S02", "Report in KRW as instructed by KR-S02; no FX conversion of any global value.")
mp("price_year", "KR-S03", "Local price year of the KRW unit costs.")
mp("perspective", "KR-S04", "Local reference-case perspective (total healthcare cost regardless of payer).")
mp("dr_costs", "KR-S05", "Local guideline discount rate for costs.")
mp("dr_outcomes", "KR-S06", "Local guideline discount rate for outcomes.")
mp("wtp_threshold", "KR-S07", "Single local reference ICER threshold used as the upper bound.")
mp("wtp_threshold_lower", "KR-S07", "Decision D09: the local setting has a single reference threshold, so the lower bound is mapped from the same item; no global bound is kept.")
ret("time_horizon_years", "KR-S08 states a lifetime horizon and asks to retain the global lifetime horizon; a label does not confirm a number, so retained as a structural setting.", basis="structural_setting")
ret("cycle_length_days", "Model cycle length is a structural choice of the global model; not a local input.", basis="structural_setting")
ret("days_per_year", "Calendar constant of the model; consistent with the period length stated in the units of KR-C09 and KR-C10 (checked by the tool).", basis="structural_setting")
ret("lifetime_check_tol", "QA tolerance of the model, not a local input.", basis="structural_setting")
ret("use_gpm_cap", "Base-case switch kept on; a local life table is supplied (KR-L01, KR-L02).", basis="structural_setting")
ret("use_age_util_adj", "Base-case switch kept on; see GAP-005 for the retained general-population utility norms.", basis="structural_setting")
ret("psa_seed", "PSA control setting, not a local input.", basis="structural_setting")
ret("psa_iterations", "PSA control setting, not a local input.", basis="structural_setting")

# Population
ret("baseline_age", "No local baseline age supplied; trial baseline retained (GAP-003).", gap_id="GAP-003")
gap_prop = None
ret("prop_male", "KR-P03 not supplied; note says the trial population is assumed, so the trial value is retained (GAP-003).", gap_id="GAP-003")
mp("weight_mean_kg", "KR-P01", "Local mean body weight from the Korean registry; drives weight-based vial use for Drug A.")
mp("weight_sd_kg", "KR-P02", "Local SD of body weight from the Korean registry.")
ret("lt_age", "Model age grid (single years) is structural; local rates are mapped onto it by mx_to_qx.", basis="structural_setting")
mp("lt_qx_male", "KR-L01", "Korean male central death rates converted to annual qx by the tool (exponential method), open band carried for model ages beyond it; see GAP-004.", op="mx_to_qx", method="exponential", open_band="carry_last_rate")
M[-1]["gap_id"] = "GAP-004"
mp("lt_qx_female", "KR-L02", "Korean female central death rates converted to annual qx by the tool (exponential method), open band carried for model ages beyond it; see GAP-004.", op="mx_to_qx", method="exponential", open_band="carry_last_rate")
M[-1]["gap_id"] = "GAP-004"

# Clinical efficacy (transferable)
for arm in ("int", "comp"):
    for ep in ("pfs", "os", "tot"):
        for p in ("shape", "scale", "corr"):
            ret(f"{arm}_{ep}_{p}", "Trial efficacy (survival extrapolation) is transferable and retained as a tagged global input; the local inputs state that clinical efficacy is not supplied (GAP-001).", gap_id="GAP-001")
    ret(f"{arm}_p_death_first_pfs", "Trial event composition is transferable efficacy and retained as a tagged global input (GAP-001).", gap_id="GAP-001")
    ret(f"{arm}_rdi", "Relative dose intensity is trial exposure data, retained as a tagged global input as the local inputs instruct (GAP-001).", gap_id="GAP-001")

# Drug A
ret("int_dose_weight_based", "KR-C02 gives the Drug A dose in mg/kg, confirming weight-based dosing.", basis="confirmed_by_local_text",
    confirm={"item": "KR-C02", "field": "unit", "pattern": "mg/kg"})
mp("int_dose_mg", "KR-C02", "Korean label dose for Drug A, per kg.")
mp("int_vial_mg", "KR-C03", "Korean label vial size for Drug A.")
mp("int_vial_price", "KR-C01", "Local list price per vial; KR-C15 states no risk-sharing agreement, so the list price replaces the global net price.")
mp("int_admin_cost_per_admin", "KR-C08", "Local infusion fee per visit, which KR-C08 says applies to both arms.")
ret("int_admin_interval_weeks", "KR-C04 states the Drug A schedule; the tool checks that it matches the retained interval.", basis="confirmed_by_local_text",
    confirm={"item": "KR-C04", "field": "value", "pattern": "Q{value}W"})
mp("int_max_doses", "KR-C05", "Local reimbursed maximum treatment duration converted to a dose count by the tool using the Drug A interval; rule doses_starting_within because dose one is given at cycle zero and every dose that starts within the reimbursed period is reimbursed.",
   op="duration_to_doses", interval_weeks_from="int_admin_interval_weeks", rule="doses_starting_within")
mp("int_ae_cost", "KR-C12", "Local Drug A adverse event cost.")
ret("int_ae_qaly_loss", "KR-U03 gives no local AE disutility; global value retained and flagged (GAP-006).", gap_id="GAP-006")

# Drug B
ret("comp_dose_weight_based", "KR-C07 states flat dosing for Drug B; switch confirmed by label.", basis="confirmed_by_local_text",
    confirm={"item": "KR-C07", "field": "value", "pattern": "flat"})
ret("comp_dose_mg", "KR-C07 states the Drug B flat dose; the tool checks it against the retained value.", basis="confirmed_by_local_text",
    confirm={"item": "KR-C07", "field": "value", "pattern": "{value} mg flat"})
ret("comp_vial_mg", "The KR-C06 item label states the Drug B vial size priced locally; the tool checks it against the retained value.", basis="confirmed_by_local_text",
    confirm={"item": "KR-C06", "field": "item", "pattern": "({value} mg)"})
mp("comp_vial_price", "KR-C06", "Local list price per vial for Drug B.")
mp("comp_admin_cost_per_admin", "KR-C08", "Local infusion fee per visit, which KR-C08 says applies to both arms.")
ret("comp_admin_interval_weeks", "KR-C07 states the Drug B schedule; the tool checks it against the retained interval.", basis="confirmed_by_local_text",
    confirm={"item": "KR-C07", "field": "value", "pattern": "Q{value}W"})
ret("comp_max_doses", "KR-C07 states the maximum number of Drug B cycles (one dose per cycle); the tool checks it against the retained dose count.", basis="confirmed_by_local_text",
    confirm={"item": "KR-C07", "field": "value", "pattern": "maximum {value} cycles"})
mp("comp_ae_cost", "KR-C13", "Local Drug B adverse event cost.")
ret("comp_ae_qaly_loss", "KR-U03 gives no local AE disutility; global value retained and flagged (GAP-006).", gap_id="GAP-006")

# State costs
mp("c_pf_week", "KR-C09", "Local monthly progression-free state cost converted to per week by the tool; period length from model days_per_year and registry months_per_year, cross-checked against the unit text.", op="per_period_to_per_week", period="month")
mp("c_pd_week", "KR-C10", "Local monthly progressed-disease state cost converted to per week by the tool; period length from model days_per_year and registry months_per_year, cross-checked against the unit text.", op="per_period_to_per_week", period="month")
gap("c_terminal", "GAP-002", "KR-C11 has no value (local study pending); terminal care is a local health-system cost, so it blocks. No GBP value, FX conversion or zero.")

# Subsequent therapy
for i, (c, a, b) in enumerate([("KR-T01", "KR-T04", "KR-T07"), ("KR-T02", "KR-T05", "KR-T08"), ("KR-T03", "KR-T06", "KR-T09")], start=1):
    mp(f"st_cost_{i}", c, "Local subsequent-therapy course cost (claims analysis).")
    mp(f"int_st_share_{i}", a, "Local subsequent-therapy share after Drug A (expert panel).")
    mp(f"comp_st_share_{i}", b, "Local subsequent-therapy share after Drug B (expert panel).")

# Utilities
mp("u_pf", "KR-U01", "Local progression-free utility, Korean value set.")
mp("u_pd", "KR-U02", "Local progressed-disease utility, Korean value set.")
for g in ("gpu_intercept", "gpu_male", "gpu_age", "gpu_age2"):
    ret(g, "KR-U04: Korean general-population utility norms not supplied; global regression retained and flagged (GAP-005).", gap_id="GAP-005")

spec = {
    "schema_version": 1,
    "note": "Korean adaptation of the global PartSA model. References only; all values are read and computed by tools/apply_mapping.py.",
    "model": "fixtures/global_model.xlsx",
    "local_inputs": "fixtures/adaptation_input_KR.xlsx",
    "gap_register": "work/gap_register.yaml",
    "mappings": M,
    "unused_local_items": [
        {"item": "KR-S08", "reason": "Label-only statement of a lifetime horizon; it cannot confirm a number, so time_horizon_years is retained as a structural setting and this item is cited in its rationale only."},
        {"item": "KR-S09", "reason": "Reference exchange rate for information only; converting global GBP inputs is prohibited."},
        {"item": "KR-C14", "reason": "Patient co-payment rate is informational; the perspective counts total cost regardless of payer, so no model input uses it."},
        {"item": "KR-C15", "reason": "Confirms list prices with no risk-sharing agreement; supports copying KR-C01 and KR-C06 as is, no model input of its own."},
    ],
}
json.dump(spec, open("work/mapping_spec.json", "w"), indent=2)
print(len(M), "mappings")
