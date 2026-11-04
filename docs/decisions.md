# Decisions log

Each entry: what was decided, by whom, status. Entries D01-D11 were provisional defaults
and were accepted by the HEOR lead on 2026-11-04 ("accept the provisional defaults"). Changing one means changing the fixture, the answer keys and the tests together.

| ID | Gate | Decision | Basis | Status |
|----|------|----------|-------|--------|
| D01 | 0.5 | GPM cap = per-cycle conditional survival min(curve, life table) on PFS and OS; sex-specific survival weighted by proportion male | DSU-style hazard constraint; avoids averaging qx | Accepted (HEOR lead, 2026-11-04) |
| D02 | 0.5 | ToT capped by OS (not PFS); treatment beyond progression allowed | Trial ToT includes post-progression treatment | Accepted (HEOR lead, 2026-11-04) |
| D03 | 0.5 | Dosing costs discounted at cycle start (time of dose) in Fixture A | Consistent with "ToT at cycle start, no HCC" | Accepted (HEOR lead, 2026-11-04) |
| D04 | 0.5 | RDI applied to drug cost after vial rounding; administration cost not adjusted | Treats RDI as dose reduction, not missed doses | Accepted (HEOR lead, 2026-11-04) |
| D05 | 0.5 | Progressions = PF decrement x (1 - constant share of PFS events that are deaths) | Simple, declared; biased at older ages | Accepted (HEOR lead, 2026-11-04) |
| D06 | 1 | Model year in annual-step discounting computed as INT(cycle x days / days_per_year), multiply before divide | Keeps exact year boundaries exact (cycle 1461 = year 28) | Decided (numerical correctness) |
| D07 | 1 | KR life table: qx = 1 - exp(-mx) ("exponential"); 100+ rate carried to ages 101-110 | Constant hazard within year; negligible cohort share above 100 | Accepted (HEOR lead, 2026-11-04); GAP-004 retain_flagged |
| D08 | 1 | KR "2 years" reimbursement limit -> 35 doses (rule doses_starting_within: every dose that starts within the limit) | Q3W doses at weeks 0..102 start before 104.36 weeks; alternative rule gives 34 | Accepted (HEOR lead, 2026-11-04) |
| D09 | 1 | KR single reference threshold mapped to both wtp_threshold and wtp_threshold_lower | Korea has no range; avoids carrying the UK lower bound | Accepted (HEOR lead, 2026-11-04); Report Writer must not describe a range |
| D10 | 1 | Trial efficacy and PSA correlations retained via GAP-006 (retain_tagged) in the gap register | Report Writer needs the tag; alternative is mapping-spec only | Accepted (HEOR lead, 2026-11-04) |
| D11 | 1 | Structural settings (cycle length, days per year, switches, PSA controls, age grid) retained with basis structural_setting, listed for human review | Not data gaps | Accepted (HEOR lead, 2026-11-04) |
| D12 | 1 | Retaining any currency-valued global input after the currency is remapped is a validation error | Prevents silent GBP values in a KRW model | Decided |
| D13 | 2.1 | KR answer key adopts the blind agent's classifications: `prop_male`, `baseline_age` retain_flagged (they weight the Korean life table and norms); AE QALY losses partial / retain_flagged (UK 3L value set vs Korean 5L state utilities). Scorer counts retain_tagged vs retain_flagged as a minor difference | Caution costs only a review flag; mixed value sets are a standard HTA objection | Accepted (HEOR lead, 2026-11-04) |
| D14 | 2.1 | GAP-001 (terminal care) to be resolved with option E2 (cited Korean end-of-life cost estimate entered as KR-C11) for the base case, with E3 (exclusion from both arms) as a scenario; if no credible source is found, E3 becomes the base case. Gap stays **open** until a source is entered and a named human records the resolution | Terminal care is a small, negative share of incremental cost (`res_inc_cost_terminal`), so exclusion is conservative against Drug A | Approach accepted (HEOR lead, 2026-11-04); resolution pending |
| D15 | 2.1 | Fix the five tool issues raised by the blind agent before Gate 3 (label-only confirmations, list-valued retained_source, YAML anchors, life-table gap convention, single-threshold guidance) | Gate 3 consumes retained-input tags | Accepted (HEOR lead, 2026-11-04) |
| D16 | 3 | Start Gate 3 before GAP-001 is resolved; KR truth values of claims are recorded as pending the adapted model, and developed against a test-only build | Report profiling depends only on the global report | Accepted (HEOR lead, 2026-11-04) |
