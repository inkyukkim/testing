I wrote `work/report_profile.json`. A check script over the file printed `tokens 184 numerals 184`, `order_ok True`, `resolved 184 unresolved 0`, `reasons_with_digits 0`, `non_base 32`, `sections 8`, `jurisdiction_hits 108`. Every chosen (name, context) pair is asserted to be in that token's candidates in `work/matches.json`, so nothing was invented.

**Commands and exit codes:**
- `python -m tools.docx_extract fixtures/global_report_UK.docx --out work/report_extract.json` exited 0.
- `python -m tools.recalc fixtures/global_model.xlsx work/recalc` exited 0.
- `python -m tools.match_numbers ... --scenarios fixtures/scenarios_UK.yaml --model fixtures/global_model.xlsx --out work/matches.json` exited 0. Its tally was `Counter({'ambiguous': 98, 'unique': 86})`.
  - My first run left out `--work`, so the scenario runs went to the tool's default `runs/match_numbers`, outside `work/`.
  - I re-ran with `--work work/scenario_runs`. That also exited 0 and gave an identical `matches.json` (`cmp` printed SAME), so I deleted `runs/`.
- `python -m tools.jurisdiction_lint fixtures/global_report_UK.docx > work/jurisdiction_lint.json` exited 1, which INSTRUCTIONS.md says to expect for a UK report.

The script that builds the profile, with the reason for each choice, is `work/scratch/build_profile.py`.

**Hardest ambiguities:**
1. **Same value in different roles.** The every-N-weeks interval token matched a long candidate list, including dosing intervals, cycle counts and life-year results. Other clashes were `st_cost_2` vs `wtp_threshold`, `comp_vial_price` vs `res_int_gpm_first_bind_age`, `comp_ae_qaly_loss` vs `dr_costs@SC1`, and `prop_male` vs `u_pd`. Sentence wording or the table row decided each one.
2. **Input vs result, and calc_ vs res_.** AE costs are inputs (`int_ae_cost`) in Table 3 but results (`res_int_cost_ae`) in Table 7. Where a `calc_*` and a `res_*` cell display the same value, I took the `res_*` one; it has role "output" on the Results sheet in `model_profile.json`.
3. **Scenario rows where the output doesn't change.** Examples are incremental QALYs in the SC4 and SC8 rows and incremental cost in the SC3 and SC7 rows. The matcher only lists scenario candidates whose values differ from base, so these resolve to `context: base` with that reason stated.
4. **One numeral standing for both discount rates.** In block 5 and the SC1 setting cell, one numeral covers both rates. I chose `dr_costs`, following the `setting_display` convention in `fixtures/scenarios_UK.yaml`.
