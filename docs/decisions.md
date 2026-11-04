# Decisions log

Each entry: what was decided, by whom, status. **Provisional** entries are defaults chosen
so work could continue; they are open questions for the HEOR lead and are listed in the
PR. Changing one means changing the fixture, the answer keys and the tests together.

| ID | Gate | Decision | Basis | Status |
|----|------|----------|-------|--------|
| D01 | 0.5 | GPM cap = per-cycle conditional survival min(curve, life table) on PFS and OS; sex-specific survival weighted by proportion male | DSU-style hazard constraint; avoids averaging qx | Provisional |
| D02 | 0.5 | ToT capped by OS (not PFS); treatment beyond progression allowed | Trial ToT includes post-progression treatment | Provisional |
| D03 | 0.5 | Dosing costs discounted at cycle start (time of dose) in Fixture A | Consistent with "ToT at cycle start, no HCC" | Provisional |
| D04 | 0.5 | RDI applied to drug cost after vial rounding; administration cost not adjusted | Treats RDI as dose reduction, not missed doses | Provisional (open Q1) |
| D05 | 0.5 | Progressions = PF decrement x (1 - constant share of PFS events that are deaths) | Simple, declared; biased at older ages | Provisional (open Q3) |
| D06 | 1 | Model year in annual-step discounting computed as INT(cycle x days / days_per_year), multiply before divide | Keeps exact year boundaries exact (cycle 1461 = year 28) | Decided (numerical correctness) |
| D07 | 1 | KR life table: qx = 1 - exp(-mx) ("exponential"); 100+ rate carried to ages 101-110 | Constant hazard within year; negligible cohort share above 100 | Provisional (open Q5); GAP-004 retain_flagged |
| D08 | 1 | KR "2 years" reimbursement limit -> 35 doses (rule doses_starting_within: every dose that starts within the limit) | Q3W doses at weeks 0..102 start before 104.36 weeks; alternative rule gives 34 | Provisional (open Q6) |
| D09 | 1 | KR single reference threshold mapped to both wtp_threshold and wtp_threshold_lower | Korea has no range; avoids carrying the UK lower bound | Provisional; Report Writer must not describe a range |
| D10 | 1 | Trial efficacy and PSA correlations retained via GAP-006 (retain_tagged) in the gap register | Report Writer needs the tag; alternative is mapping-spec only | Provisional (open Q7) |
| D11 | 1 | Structural settings (cycle length, days per year, switches, PSA controls, age grid) retained with basis structural_setting, listed for human review | Not data gaps | Provisional |
| D12 | 1 | Retaining any currency-valued global input after the currency is remapped is a validation error | Prevents silent GBP values in a KRW model | Decided |
