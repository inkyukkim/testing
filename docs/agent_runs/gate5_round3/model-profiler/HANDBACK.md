I would not accept the model for adaptation yet. A human needs to decide four issues (D1 to D4 below), and then the profiler should be re-run until `parallel_layouts` pairs Trace_Int with Trace_Comp. I wrote the profile and the review, changed nothing under fixtures/, tools/ or schemas/, and did not recalculate the workbook.

**Commands (all run from /home/user/testing/model-profiler)**
- `python -m tools.profile_workbook fixtures/model.xlsx --conventions fixtures/model.conventions.yaml --out work/model_profile.json`: exit 0.
- `python -c "from tools.partsa_engine import load_conventions; load_conventions('fixtures/model.conventions.yaml')"`: exit 0, so the engine accepted every declared convention.
- Three helper scripts in work/ that only read the profile or the formulas (`check_deps.py`, `inspect_regions.py` run with `PYTHONPATH=.`, `dump_trace.py`): exit 0 each. The first `inspect_regions.py` run failed with exit 1 because the `tools` module was not on the path; the rerun worked.

**Issues a human must decide**
- **D1, discounting convention mismatch.** The profile's `convention_mismatches[0]` says: "discounting.method declared 'annual_step', formulas show 'mid_cycle_continuous'".
  - The formulas discount from cycle start in Trace_*!Y20 (used by Results!B5 and B6) and from mid-cycle in Z20 and AA20.
  - The declaration says `model_year` for every `discounting.timing` sub-key, so the timings disagree as well as the method.
  - I think the declaration is the wrong side: the formulas match in both arms and the column headers state the timing. Because the engine accepted `annual_step`, a parity check against the workbook would fail.
- **D2, hidden multiplier at Trace_Int!AF20 ("PF state cost").** This is `hardcoding_findings[0]`: an unnamed literal that appears only in the intervention arm. Trace_Comp!AF20 has the same formula without it. It looks like a hidden input, and it reaches `res_inc_total_cost` and `res_icer`.
- **D3, pasted constant at Trace_Comp!AG300 ("PD state cost").** This is `hardcoding_findings[1]`, a `constant_on_calc_sheet`. It overwrites the copied formula, splitting the column into regions AG20 and AG301, and it does not respond to `c_pd_week`.
- **D4, comparator uses the intervention's RDI.** `input_dependencies` for `res_comp_cost_drug`, `res_comp_drug_share` and `res_comp_total_cost` include `int_rdi`. Trace_Comp!C10 reads `=int_rdi`, and `comp_rdi` is used by no formula. It looks like a copy-paste wiring error.
- **D5, arm layouts differ.** `parallel_layouts` is empty. The only differing regions are AF20, AG (the split) and C10, which are D2 to D4 above.
- **D6 (minor, QA only).** Results!D47 reuses `lifetime_check_tol` as the tolerance for the vial-band check.

**Other findings**
- No other output name lacks input dependencies except `max_trace_cycles`, which is a row count and fine.
- The unused `*_corr` and `psa_*` inputs are expected; their metadata says PSA only.
- The review also lists, as advice for the Input Mapper, which inputs likely need localising and which are likely transferable.

Files are in /home/user/testing/model-profiler/work:
- model_profile.json
- model_profile_review.md
- check_deps.py
- inspect_regions.py
- dump_trace.py
