# Model profile review: fixtures/model.xlsx

Profiler agent review of `work/model_profile.json`, checked against
`fixtures/model.conventions.yaml`. This review contains no workbook values. Values are cited by
defined name, region (Sheet!Cell) or profile field.

## Evidence and commands

| Step | Command | Exit |
|------|---------|------|
| 1 | `python -m tools.profile_workbook fixtures/model.xlsx --conventions fixtures/model.conventions.yaml --out work/model_profile.json` | 0 |
| 2 | `python -c "from tools.partsa_engine import load_conventions; load_conventions('fixtures/model.conventions.yaml')"` | 0 (engine accepts every declared convention) |
| aux | `python work/check_deps.py` (reads `input_dependencies` and `names` in the profile) | 0 |
| aux | `PYTHONPATH=. python work/inspect_regions.py <cells>` (uses `tools.profile_workbook.Workbook` to diff the regions in Trace_Int and Trace_Comp; it reads formulas and does not recalculate) | 0 |
| aux | `python work/dump_trace.py Trace_Comp` (labels and formulas of the parameter block and first trace row) | 0 |

The workbook was not recalculated. No step in this review needs recalculated values.

## Summary of decisions a human must make

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| D1 | Discounting convention mismatch | Trace_Int/Trace_Comp Y20, Z20, AA20; `discounting` in YAML | blocks engine parity |
| D2 | Hard-coded multiplier on the intervention PF state cost | Trace_Int!AF20 region | likely hidden input |
| D3 | Hard-coded constant that overwrites one row of the comparator PD state cost | Trace_Comp!AG300 | likely error or hidden override |
| D4 | Comparator drug cost uses the intervention RDI | Trace_Comp!C10 (`=int_rdi`); `comp_rdi` unused | wiring error |
| D5 | Arm layouts are not parallel | `parallel_layouts` is empty | follows from D2 to D4 |
| D6 | QA tolerance reused for an unrelated check | Results!D47 uses `lifetime_check_tol` | minor |

## convention_mismatches

The profile reports one mismatch (`convention_mismatches[0]`):
`discounting.method declared 'annual_step', formulas show 'mid_cycle_continuous'`.

Evidence from `conventions_detected.discount_factor_regions`:
- Trace_Int!Y20 and Trace_Comp!Y20 (header "DF costs, cycle start"): `dr_costs`, timing `cycle_start`.
- Trace_Int!Z20 and Trace_Comp!Z20 ("DF costs, mid-cycle"): `dr_costs`, timing `cycle_midpoint`.
- Trace_Int!AA20 and Trace_Comp!AA20 ("DF outcomes, mid-cycle"): `dr_outcomes`, timing `cycle_midpoint`.
- No discount region uses `INT(` in its exponent, so the formulas contain no annual step.

The profiler compares only `discounting.method`. The timing sub-keys also disagree:
- The declaration gives `discounting.timing` as `model_year` for state costs, one-off event costs,
  dosing costs and outcomes.
- In the formulas, Results!B5 and B6 (drug and administration costs) weight by column Y, which
  discounts from cycle start.
- Results!B7 to B10 (PF state, PD state, terminal care and subsequent therapy costs) weight by
  column Z, which discounts from mid-cycle.
- Results!B14 and B16 (discounted LYs and QALYs) weight by column AA, which also discounts from
  mid-cycle.
- `ae_at_baseline: undiscounted` agrees with the formulas: Results!B11 is `=int_ae_cost` and
  Results!B16 subtracts `int_ae_qaly_loss` without discounting.

Which side is likely wrong:
- I think the declaration is the side that is wrong. The formulas are internally consistent: the
  same three discount columns appear in both arms, the column headers name the timing, and the
  timing is chosen deliberately by cost type (dosing at cycle start, state costs at mid-cycle).
  That looks like an intended design, not an accident.
- `partsa_engine` accepted `annual_step` (step 2 exited 0). An engine built from this declaration
  would therefore discount differently from the workbook, and the parity check would fail or give
  misleading results.
- A human must decide which side to change: correct the YAML to describe the cycle-level
  discounting, or approve a change to the workbook's method. If the YAML is corrected, the engine
  must also implement the new convention.

The other declared conventions that the profiler checks agree with the formulas:
- `survival_forms` is `weibull_aft`.
- `gpm_cap` is true.
- `hcc_method` is `trapezoidal`. The HCC columns are R and S, which average columns N and O.

Spot checks of formulas that the profiler does not test, all in agreement with the declaration:
- Trace_*!K21 and L21 take the per-cycle minimum of the parametric and GPM survival ratios.
- Trace_*!J20 weights the sex-specific survival by `prop_male`.
- Trace_*!H21 and I21 look up the age with `INT(D20)` at cycle start.
- Trace_*!M20 is `MIN(G20,K20)`, the ToT capped by OS.

## hardcoding_findings

1. `literal_in_formula` at region **Trace_Int!AF20** ("PF state cost"). The region runs over the
   whole trace, and its literal is in `hardcoding_findings[0].literals`.
   - The Trace_Int formula is `R*c_pf_week*cycle_length_days/7*<literal>`.
   - The matching comparator region Trace_Comp!AF20 has the same formula without the multiplier.
   - Assessment: this looks like a **hidden input**. Possible meanings are an uplift, an inflation
     index or a sensitivity factor. It is not a structural constant, because it is unnamed, it
     applies to one arm only, and the input sheets do not document it.
   - Effect: it inflates `res_int_cost_pf_state` and therefore `res_inc_cost_pf_state`,
     `res_inc_total_cost` and `res_icer`.
   - Human decision: remove it, or promote it to a named input with a source.

2. `constant_on_calc_sheet` at **Trace_Comp!AG300**. This is a numeric constant inside the
   comparator "PD state cost" column.
   - The cells above and below it hold the copied formula `=S*c_pd_week*cycle_length_days/7`
     (Trace_Comp!AG299 and AG301). The constant splits the column into regions Trace_Comp!AG20
     and Trace_Comp!AG301.
   - Assessment: a **hidden input or a pasted-over formula**, not a structural constant. It
     replaces one cycle's PD cost for the comparator and does not respond to `c_pd_week`,
     `cycle_length_days` or the trace.
   - Effect: it distorts `res_comp_cost_pd_state` and hence the incremental results. Under PSA
     or after localisation of `c_pd_week`, that cell would stay at the global value.
   - Human decision: restore the formula, or document the override.

## Inputs whose role or dependencies look wrong

- **Comparator drug cost depends on the intervention's RDI.**
  - `check_deps.py` reports that `input_dependencies` of `res_comp_cost_drug`,
    `res_comp_drug_share` and `res_comp_total_cost` contain `int_rdi`.
  - Trace_Comp!C10 (label "Relative dose intensity") is `=int_rdi`, and Trace_Comp!AD20 multiplies
    the drug cost by `$C$10`.
  - `comp_rdi` (Inputs_Clinical) is an input that no derived or output name uses.
  - Likely a copy-paste wiring error. Human decision: re-link Trace_Comp!C10 to `comp_rdi`.
- **`lifetime_check_tol` has two roles.** The input is labelled "Lifetime check: max proportion
  alive at horizon", but Results!D47 also uses it as the tolerance for the vial-band tail mass.
  This is QA only and does not affect the results. Human decision: keep it shared, or add a
  separate tolerance.
- **Unused inputs.** Names that no derived or output name depends on:
  - `int_/comp_{pfs,os,tot}_corr`. Their metadata says "PSA only / Not used in deterministic run",
    so this is expected.
  - `psa_seed` and `psa_iterations`, on the PSA_Placeholder sheet. Expected.
  - `country`, `currency_code`, `perspective` and `price_year`. These are descriptive labels, but
    `price_year` has to be set correctly during localisation even though no formula reads it.
  - `comp_rdi`. Not expected; see above.
- **Output with no input dependency.** The only non-input name with an empty dependency list is
  `max_trace_cycles` (`=ROWS(Trace_Int!$A$20:...)`). It is a structural row count used by
  Results!D42, which is acceptable.
- No intervention result depends on a comparator input. Every other int/comp pair of `res_*` names
  has symmetric dependencies after the prefix is renamed (`check_deps.py`, asymmetric section).

## parallel_layouts

`parallel_layouts` is empty, so the profiler did **not** find a shared layout for Trace_Int and
Trace_Comp. `inspect_regions.py` diffed the region signatures with the arm prefix normalised. The
differences are:
- **AF20**: the Trace_Int formula carries the extra literal multiplier (hardcoding finding 1).
- **AG**: Trace_Int has a single region AG20. Trace_Comp is split into AG20 and AG301 around the
  constant at Trace_Comp!AG300 (hardcoding finding 2).
- **C10**: both sheets read `=int_rdi`. For Trace_Int this is correct. For Trace_Comp the
  arm-normalised signature should be `comp_rdi` (see the RDI finding).

Every other region matches between the two sheets. If the three issues above are fixed, the arms
should share one layout. Re-run the profiler after the fixes to confirm.

## Localisation advice for the Input Mapper (not a mapping)

These are advisory classes; they are not gap-register decisions.

**Likely non-transferable (local evidence needed):**
- Health-state and event costs: `c_pf_week`, `c_pd_week`, `c_terminal`.
- Administration costs: `int_admin_cost_per_admin`, `comp_admin_cost_per_admin`. Their source
  notes cite an NHS reference cost.
- Drug prices: `int_vial_price` (net of a confidential discount), `comp_vial_price` (eMIT), and
  `int_vial_mg` and `comp_vial_mg` if local pack sizes differ.
- Adverse-event costs: `int_ae_cost`, `comp_ae_cost`.
- Subsequent therapy course costs `st_cost_1` to `st_cost_3`, and the shares
  `int_st_share_*` and `comp_st_share_*`, which reflect local treatment practice.
- Discount rates `dr_costs` and `dr_outcomes`, both sourced to the NICE reference case.
- `wtp_threshold` and `wtp_threshold_lower`, which are the NICE range.
- Setting: `perspective`, `currency_code`, `price_year` and `country`.

**Likely partial (the structure transfers, but calibration is local):**
- Life tables: `lt_qx_male`, `lt_qx_female` and `lt_age`.
- General-population utility norms `gpu_intercept`, `gpu_male`, `gpu_age` and `gpu_age2`
  (labelled UK norms).
- Health-state utilities `u_pf` and `u_pd`, which use a UK EQ-5D value set and may need a local
  value set.
- Population characteristics `baseline_age`, `prop_male`, `weight_mean_kg` and `weight_sd_kg`.

**Likely transferable (trial efficacy and regimen):**
- Weibull parameters `int_/comp_{pfs,os,tot}_{shape,scale}` and their `*_corr` terms.
- `int_p_death_first_pfs` and `comp_p_death_first_pfs`.
- `int_rdi` and `comp_rdi`.
- `int_ae_qaly_loss` and `comp_ae_qaly_loss`.
- Regimen inputs `*_dose_mg`, `*_dose_weight_based`, `*_admin_interval_weeks` and
  `*_max_doses`. Check these against the local label or SmPC.

**Model settings that stay unless the method changes:** `cycle_length_days`, `days_per_year`,
`time_horizon_years`, `use_gpm_cap`, `use_age_util_adj` and `lifetime_check_tol`.

## Recommendation

**Do not accept the model for adaptation yet.** Before it can be accepted, a human must resolve
four issues, and then the profiler must be re-run and `parallel_layouts` must list
[Trace_Int, Trace_Comp]:
- D1: the discounting declaration does not match the formulas.
- D2: Trace_Int!AF20 contains an unnamed one-arm multiplier.
- D3: a pasted constant sits at Trace_Comp!AG300.
- D4: Trace_Comp!C10 points to `int_rdi`.
