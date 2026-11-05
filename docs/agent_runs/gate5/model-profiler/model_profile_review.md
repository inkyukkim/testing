# Model profile review: fixtures/model.xlsx

Evidence base: `work/model_profile.json` (written by `python -m tools.profile_workbook`, exit 0), the
convention check `tools.partsa_engine.load_conventions('fixtures/model.conventions.yaml')` (exit 0, no
convention refused) and read-only formula probes in `work/scratch/probe_layout.py`,
`work/scratch/probe_deps.py` and `work/scratch/probe_misc.py` (openpyxl, formulas only, no recalculation).
No values from the workbook are restated here; cells and names are cited instead.

Recommendation: **do not accept the model for adaptation yet.** One declaration mismatch, two
hardcoding findings, one cross-arm link and the resulting break of the parallel layout each need a
human decision. All of them move the base-case results (`res_icer`, `res_inc_nmb`, `res_below_wtp`
and the arm totals depend on the affected regions).

## 1. Convention mismatches (`convention_mismatches`)

**M1. `discounting.method`: declaration says `annual_step`, formulas show `mid_cycle_continuous`.**

- Formulas (`conventions_detected.discount_factor_regions`): `Trace_Int!Y20` and `Trace_Comp!Y20`
  discount at cycle start (`dr_costs`); `Trace_Int!Z20`, `Trace_Comp!Z20` (`dr_costs`) and
  `Trace_Int!AA20`, `Trace_Comp!AA20` (`dr_outcomes`) at the cycle mid-point, all with the
  continuous exponent `(cycle [+ half]) * cycle_length_years` and no `INT(` year step.
- Usage (Results formulas): drug and administration costs (`res_*_cost_drug`, `res_*_cost_admin`)
  use column Y; state, terminal care and subsequent-therapy costs use column Z; LYs and QALYs use
  column AA; AE cost and AE QALY loss are undiscounted.
- Declaration: `discounting.method: annual_step` and every `discounting.timing` stream `model_year`.
- Likely wrong side: **the declaration.** The formulas are internally coherent (dosing at cycle start,
  other streams at mid-cycle, identical in both arms), and the workbook's own `ReadMe` sheet describes
  exactly this scheme ("dosing costs at cycle start; other costs and outcomes at cycle mid-point") and
  refers to a declaration file named differently from the one supplied. The supplied YAML looks like an
  annual-step declaration attached to a mid-cycle workbook.
- Consequence: `load_conventions` accepted the YAML because `annual_step` is an implemented value, so
  engine parity (V07) would compare the workbook against the wrong convention. A human must decide
  which side to correct; I have not changed either.

## 2. Hardcoding findings (`hardcoding_findings`)

**H1. `literal_in_formula` in `Trace_Int!AF20` (region spans rows 20 to 2107, PF state cost, intervention arm).**
The formula multiplies the PF state cost by a non-structural literal (listed in the finding's `literals`
field). The comparator region `Trace_Comp!AF20` has the same formula without that factor. Judgement:
**hidden input**, not a structural constant: it is an unexplained arm-specific uplift on a cost that is
supposed to be shared (`c_pf_week`), it has no defined name, label, unit or PSA metadata, and it is
invisible in `input_dependencies` (`res_int_cost_pf_state` shows only `c_pf_week` and the trace inputs).
A human must decide whether it is an error to remove or an intended adjustment to expose as a named,
documented input.

**H2. `constant_on_calc_sheet` at `Trace_Comp!AG300` (PD state cost, comparator arm).**
A typed number replaces the formula in one row of the PD state cost column; rows above and below
(`Trace_Comp!AG299`, `Trace_Comp!AG301`) carry the regular formula, which is why the profiler split the
column into two regions. Judgement: **hidden input / pasted override**, not a structural constant: it
sits inside a per-cycle formula column and carries no name. `work/scratch/probe_deps.py` shows that
`res_comp_cost_pd_state`, `res_comp_total_cost`, `res_inc_cost_pd_state`, `res_inc_total_cost`,
`res_icer`, `res_icer_ly`, `res_inc_nmb`, `res_inc_nmb_lower`, `res_dominance`, `res_below_wtp`,
`res_below_wtp_lower` and `res_comp_drug_share` all reach it. Localising `c_pd_week` would not
update that cycle. Human decision needed (most likely: restore the formula).

## 3. Inputs whose role or dependencies look wrong

**D1. The comparator drug cost uses the intervention's RDI.** `Trace_Comp!C10` is `=int_rdi`
(the same text as `Trace_Int!C10`), so `input_dependencies` for `res_comp_cost_drug`,
`res_comp_total_cost` and `res_comp_drug_share` contain `int_rdi`. `comp_rdi` (labelled as the
comparator RDI on `Inputs_Clinical`) reaches no derived or output name. Because both cells have the
same formula text, this cross-arm link does not show up as a layout difference; it shows only in the
dependency sets. Likely an error (the parameter block should link `comp_rdi`); a human decides.

**D2. Inputs that reach no derived or output name** (from `work/scratch/probe_deps.py`):
- `comp_rdi`: see D1; this is the anomaly.
- `int_pfs_corr`, `int_os_corr`, `int_tot_corr`, `comp_pfs_corr`, `comp_os_corr`, `comp_tot_corr`,
  `psa_iterations`, `psa_seed`: expected, they are labelled "Not used in deterministic run" or sit on
  `PSA_Placeholder` (PSA not implemented).
- `country`, `currency_code`, `perspective`, `price_year`: text/metadata inputs; expected.

**D3. Other observations (no action expected).** No output has an empty dependency set.
`max_trace_cycles` is derived with no input dependencies, but its formula is `ROWS()` over the trace
range, a structural count. `lt_age`, `lt_qx_male`, `lt_qx_female` are vector inputs without
label/unit metadata in the profile (the row-metadata reader does not cover vectors); their units should
be confirmed by the Input Mapper from the sheet itself.

## 4. Parallel layouts (`parallel_layouts`)

`parallel_layouts` is **empty**: the profiler did not find `Trace_Int` and `Trace_Comp` to share one
layout, although the `ReadMe` sheet states they have an identical formula layout. Comparison of their
regions (`work/scratch/probe_layout.py`):
- column AF (`Trace_Int!AF20` vs `Trace_Comp!AF20`): different formulas, caused by H1;
- column AG: one region in `Trace_Int` (`Trace_Int!AG20`), two regions in `Trace_Comp`
  (`Trace_Comp!AG20` and `Trace_Comp!AG301`), caused by H2;
- the parameter block `C3:C17` differs only by the expected arm prefix (`int_*` vs `comp_*`,
  `calc_int_*` vs `calc_comp_*`), except `C10`, which links `int_rdi` in both sheets (D1).
All other trace regions match. Once H1, H2 and D1 are fixed, the arms should share one layout; a rerun
of the profiler should confirm it.

## 5. Localisation advice for the Input Mapper (advice, not a mapping)

Likely need local values (`non_transferable` or `partial`):
- Unit costs and prices: `int_vial_price` (labelled net price incl. a confidential discount),
  `comp_vial_price`, `int_admin_cost_per_admin`, `comp_admin_cost_per_admin`, `c_pf_week`, `c_pd_week`,
  `c_terminal`, `st_cost_1`, `st_cost_2`, `st_cost_3`, `int_ae_cost`, `comp_ae_cost`.
- Local treatment practice: `int_st_share_1..3`, `comp_st_share_1..3` (post-progression therapy mix),
  `int_max_doses`, `comp_max_doses` (reimbursed stopping rules may differ).
- Population: `baseline_age`, `prop_male`, `weight_mean_kg`, `weight_sd_kg` (local patient profile).
- Life table: `lt_age`, `lt_qx_male`, `lt_qx_female` (local qx; note the model needs `qx` by single age).
- Utilities: `u_pf`, `u_pd` (labelled UK value set), `gpu_intercept`, `gpu_male`, `gpu_age`, `gpu_age2`
  (labelled UK norms), possibly `int_ae_qaly_loss`, `comp_ae_qaly_loss`.
- HTA settings: `dr_costs`, `dr_outcomes`, `wtp_threshold`, `wtp_threshold_lower` (labelled NICE
  reference case), `perspective`, `country`, `currency_code`, `price_year`, possibly
  `time_horizon_years`.

Likely transferable (trial efficacy and regimen): `int_/comp_pfs_shape`, `_pfs_scale`, `_os_shape`,
`_os_scale`, `_tot_shape`, `_tot_scale`, `_p_death_first_pfs`, `int_rdi`, `comp_rdi`, the `*_corr`
inputs, `int_dose_mg`, `comp_dose_mg`, `*_dose_weight_based`, `*_vial_mg`, `*_admin_interval_weeks`
(subject to local labelling).

Structural/QA settings, normally not localised: `cycle_length_days`, `days_per_year`,
`use_gpm_cap`, `use_age_util_adj`, `lifetime_check_tol`, `psa_iterations`, `psa_seed`.

The hidden factor in H1 and the override in H2 are not inputs at all today, so the Input Mapper cannot
map them; they must be resolved before mapping.

## Decisions required from a human

| ID | Concerns | Decision |
|----|----------|----------|
| M1 | `discounting.method` / `Trace_*!Y20:AA20` | correct the declaration or the formulas |
| H1 | `Trace_Int!AF20` (rows 20 to 2107) | remove the literal or expose it as a named input |
| H2 | `Trace_Comp!AG300` | restore the formula or justify and name the override |
| D1 | `Trace_Comp!C10`, `comp_rdi`, `int_rdi` | relink the comparator RDI or document the choice |
| P1 | `parallel_layouts` empty | confirm after H1, H2, D1 by rerunning the profiler |
