"""Generate fixtures/global_model.xlsx: formula-driven 3-state PartSA (synthetic data).

Run:  python scripts/build_global_model.py [A|B]
      A (default) -> fixtures/global_model.xlsx    mid-cycle continuous discounting
      B           -> fixtures/global_model_B.xlsx  annual-step discounting (otherwise identical)
All values are SYNTHETIC. Calculation sheets contain formulas only; every input is a
named single-cell or one-dimensional range on an Inputs_* sheet. Conventions are declared
in fixtures/global_model.conventions.yaml ("Fixture A").
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.workbook.defined_name import DefinedName

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synthetic_data import LT_AGES, UK_QX_FEMALE, UK_QX_MALE  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "global_model.xlsx"

MAX_TRACE_CYCLES = 2088          # interval rows; 2088 weekly cycles = 40.03 years
FIRST = 20                       # first data row on trace sheets
LAST_INTERVAL = FIRST + MAX_TRACE_CYCLES - 1   # 2107
LAST_BOUNDARY = LAST_INTERVAL + 1              # 2108
VIAL_ROWS = 60                   # vial-count bands in Calc_Dosing

INPUT_FILL = PatternFill("solid", fgColor="DDEBF7")
CALC_FILL = PatternFill("solid", fgColor="F2F2F2")
HEAD = Font(bold=True)
TITLE = Font(bold=True, size=14)

ARMS = {"int": "Drug A (intervention)", "comp": "Drug B, platinum doublet (comparator)"}
ST_LABELS = {1: "Docetaxel-based chemotherapy", 2: "Immunotherapy", 3: "Other targeted therapy"}

# (label, name, value, unit, PSA distribution, PSA SE, source / note)
SETTINGS = [
    ("Country / setting", "country", "United Kingdom", "text", "Fixed", None, "Global base case"),
    ("Currency", "currency_code", "GBP", "ISO 4217", "Fixed", None, ""),
    ("Price year", "price_year", 2025, "year", "Fixed", None, "Synthetic"),
    ("Perspective", "perspective", "NHS and PSS", "text", "Fixed", None, "NICE reference case"),
    ("Cycle length", "cycle_length_days", 7, "days", "Fixed", None, "Weekly cycles"),
    ("Days per year", "days_per_year", 365.25, "days", "Fixed", None, ""),
    ("Time horizon", "time_horizon_years", 40, "years", "Fixed", None, "Lifetime"),
    ("Discount rate, costs", "dr_costs", 0.035, "per annum", "Fixed", None, "NICE reference case"),
    ("Discount rate, outcomes", "dr_outcomes", 0.035, "per annum", "Fixed", None, "NICE reference case"),
    ("WTP threshold (upper)", "wtp_threshold", 30000, "currency/QALY", "Fixed", None, "NICE range upper bound"),
    ("WTP threshold (lower)", "wtp_threshold_lower", 20000, "currency/QALY", "Fixed", None, "NICE range lower bound"),
    ("Lifetime check: max proportion alive at horizon", "lifetime_check_tol", 0.001, "proportion", "Fixed", None, "QA setting"),
    ("Apply general-population mortality cap (1 = yes)", "use_gpm_cap", 1, "switch", "Fixed", None, "Base case on"),
    ("Apply age adjustment to utilities (1 = yes)", "use_age_util_adj", 1, "switch", "Fixed", None, "Base case on"),
]
SETTINGS_CALC = [
    ("Cycle length (years)", "cycle_length_years", "=cycle_length_days/days_per_year", "years"),
    ("Number of model cycles", "n_cycles", "=ROUND(time_horizon_years*days_per_year/cycle_length_days,0)", "cycles"),
    ("Trace rows available", "max_trace_cycles", f"=ROWS(Trace_Int!$A${FIRST}:$A${LAST_INTERVAL})", "cycles"),
]

POPULATION = [
    ("Mean age at baseline", "baseline_age", 62, "years", "Fixed", None, "Synthetic trial baseline"),
    ("Proportion male", "prop_male", 0.6, "proportion", "Fixed", None, "Synthetic trial baseline"),
    ("Mean body weight", "weight_mean_kg", 76, "kg", "Fixed", None, "Synthetic trial baseline"),
    ("SD of body weight", "weight_sd_kg", 16, "kg", "Fixed", None, "Synthetic trial baseline; lognormal by moments"),
]

CLINICAL = []
_surv = {
    "int": {"pfs": (0.95, 12.0, 0.06, 0.05, -0.35), "os": (0.85, 32.0, 0.07, 0.08, -0.40),
            "tot": (0.90, 10.0, 0.05, 0.05, -0.30)},
    "comp": {"pfs": (1.25, 7.0, 0.05, 0.04, -0.30), "os": (1.15, 16.0, 0.06, 0.05, -0.38),
             "tot": (1.40, 4.5, 0.05, 0.04, -0.25)},
}
_other = {"int": (0.15, 0.95), "comp": (0.12, 0.90)}
for arm, label in ARMS.items():
    for ep in ("pfs", "os", "tot"):
        shape, scale, se_ls, se_lsc, rho = _surv[arm][ep]
        src = f"Synthetic Weibull fit to {ep.upper()} KM, {label}"
        CLINICAL += [
            (f"{label}: {ep.upper()} Weibull shape", f"{arm}_{ep}_shape", shape, "-", "MVN on log", se_ls, src),
            (f"{label}: {ep.upper()} Weibull scale", f"{arm}_{ep}_scale", scale, "months", "MVN on log", se_lsc, src),
            (f"{label}: {ep.upper()} corr(log shape, log scale)", f"{arm}_{ep}_corr", rho, "-", "PSA only", None, "Not used in deterministic run"),
        ]
    pdf, rdi = _other[arm]
    CLINICAL += [
        (f"{label}: proportion of PFS events that are deaths", f"{arm}_p_death_first_pfs", pdf, "proportion", "Beta", 0.03, "Synthetic trial event composition"),
        (f"{label}: relative dose intensity", f"{arm}_rdi", rdi, "proportion", "Beta", 0.02, "Synthetic trial exposure data"),
    ]

COSTS = [
    ("Drug A dosing basis (1 = mg/kg, 0 = flat mg)", "int_dose_weight_based", 1, "switch", "Fixed", None, "SmPC"),
    ("Drug A dose", "int_dose_mg", 2, "mg/kg", "Fixed", None, "SmPC: 2 mg/kg Q3W"),
    ("Drug A vial size", "int_vial_mg", 100, "mg", "Fixed", None, "SmPC"),
    ("Drug A net price per vial (incl. PAS)", "int_vial_price", 700, "GBP", "Fixed", None, "Synthetic list price with confidential discount"),
    ("Drug A administration cost per administration", "int_admin_cost_per_admin", 310, "GBP", "Gamma", 62, "Synthetic NHS reference cost, SB12Z"),
    ("Drug A administration interval", "int_admin_interval_weeks", 3, "weeks", "Fixed", None, "Q3W per SmPC"),
    ("Drug A maximum number of doses (stopping rule)", "int_max_doses", 35, "doses", "Fixed", None, "35 doses Q3W per protocol"),
    ("Drug A adverse event cost (one-off)", "int_ae_cost", 1150, "GBP", "Gamma", 230, "Grade 3+ AE incidence x unit costs"),
    ("Drug B dosing basis (1 = mg/kg, 0 = flat mg)", "comp_dose_weight_based", 0, "switch", "Fixed", None, "Synthetic regimen"),
    ("Drug B dose", "comp_dose_mg", 500, "mg (flat)", "Fixed", None, "Synthetic regimen"),
    ("Drug B vial size", "comp_vial_mg", 100, "mg", "Fixed", None, "Synthetic"),
    ("Drug B price per vial", "comp_vial_price", 96, "GBP", "Fixed", None, "Synthetic eMIT price"),
    ("Drug B administration cost per administration", "comp_admin_cost_per_admin", 310, "GBP", "Gamma", 62, "Synthetic NHS reference cost, SB12Z"),
    ("Drug B administration interval", "comp_admin_interval_weeks", 3, "weeks", "Fixed", None, "Q3W"),
    ("Drug B maximum number of doses", "comp_max_doses", 6, "doses", "Fixed", None, "6 cycles"),
    ("Drug B adverse event cost (one-off)", "comp_ae_cost", 2400, "GBP", "Gamma", 480, "Grade 3+ AE incidence x unit costs"),
    ("Progression-free health state cost per week", "c_pf_week", 150, "GBP/week", "Gamma", 30, "Synthetic resource use x PSSRU"),
    ("Progressed disease health state cost per week", "c_pd_week", 230, "GBP/week", "Gamma", 46, "Synthetic resource use x PSSRU"),
    ("Terminal care cost (one-off at death)", "c_terminal", 6500, "GBP", "Gamma", 1300, "Synthetic end-of-life costing"),
]
_st_cost = {1: 2800, 2: 30000, 3: 15000}
_st_share = {"int": {1: 0.45, 2: 0.05, 3: 0.10}, "comp": {1: 0.30, 2: 0.35, 3: 0.08}}
ST_ROWS = [(f"Subsequent therapy course cost: {ST_LABELS[j]}", f"st_cost_{j}", _st_cost[j], "GBP per course",
            "Gamma", _st_cost[j] * 0.2, "Synthetic: drug + administration for mean course") for j in ST_LABELS]
for arm, label in ARMS.items():
    ST_ROWS += [(f"Share receiving {ST_LABELS[j]} after progression on {label}", f"{arm}_st_share_{j}",
                 _st_share[arm][j], "proportion", "Dirichlet", None, "Synthetic trial post-progression therapy")
                for j in ST_LABELS]

UTILITIES = [
    ("Utility, progression-free", "u_pf", 0.75, "-", "Beta", 0.03, "Synthetic trial EQ-5D-3L, UK value set"),
    ("Utility, progressed disease", "u_pd", 0.60, "-", "Beta", 0.04, "Synthetic trial EQ-5D-3L, UK value set"),
    ("Drug A AE QALY loss (one-off)", "int_ae_qaly_loss", 0.008, "QALY", "Beta", 0.002, "Synthetic"),
    ("Drug B AE QALY loss (one-off)", "comp_ae_qaly_loss", 0.015, "QALY", "Beta", 0.004, "Synthetic"),
    ("General-population utility: intercept", "gpu_intercept", 0.95, "-", "Fixed", None, "Synthetic UK norms regression"),
    ("General-population utility: male coefficient", "gpu_male", 0.021, "-", "Fixed", None, "Synthetic UK norms regression"),
    ("General-population utility: age coefficient", "gpu_age", -0.00026, "per year", "Fixed", None, "Synthetic UK norms regression"),
    ("General-population utility: age-squared coefficient", "gpu_age2", -0.000033, "per year^2", "Fixed", None, "Synthetic UK norms regression"),
]

ARM_BLOCK = [  # (row, label, formula) on trace sheets, value in column C
    (3, "PFS Weibull shape", "={a}_pfs_shape"), (4, "PFS Weibull scale (months)", "={a}_pfs_scale"),
    (5, "OS Weibull shape", "={a}_os_shape"), (6, "OS Weibull scale (months)", "={a}_os_scale"),
    (7, "ToT Weibull shape", "={a}_tot_shape"), (8, "ToT Weibull scale (months)", "={a}_tot_scale"),
    (9, "Proportion of PFS events that are deaths", "={a}_p_death_first_pfs"),
    (10, "Relative dose intensity", "={a}_rdi"),
    (11, "Drug cost per administration (after vial rounding)", "=calc_{a}_drug_cost_per_admin"),
    (12, "Administration cost per administration", "={a}_admin_cost_per_admin"),
    (13, "Dosing interval (cycles)", "=calc_{a}_interval_cycles"),
    (14, "Maximum number of doses", "={a}_max_doses"),
    (15, "Subsequent therapy cost per progression", "=calc_{a}_st_cost_per_progression"),
    (16, "AE cost (one-off)", "={a}_ae_cost"), (17, "AE QALY loss (one-off)", "={a}_ae_qaly_loss"),
]


def ratio(col, r, p):
    return f"IF({col}{p}>0,{col}{r}/{col}{p},0)"


# (col, header, first-row formula or None for same as general, general formula); {r} row, {n} next, {p} previous
TRACE_COLS = [
    ("A", "Cycle", None, f"=ROW()-ROW($A${FIRST})"),
    ("B", "Time (years)", None, "=A{r}*cycle_length_years"),
    ("C", "Time (months)", None, "=B{r}*12"),
    ("D", "Age at time t", None, "=baseline_age+B{r}"),
    ("E", "S_PFS raw", None, "=EXP(-((C{r}/$C$4)^$C$3))"),
    ("F", "S_OS raw", None, "=EXP(-((C{r}/$C$6)^$C$5))"),
    ("G", "S_ToT raw", None, "=EXP(-((C{r}/$C$8)^$C$7))"),
    ("H", "GPM survival, male", "=1",
     "=IF(A{p}<n_cycles,H{p}*(1-INDEX(lt_qx_male,MATCH(INT(D{p}),lt_age,0)))^cycle_length_years,H{p})"),
    ("I", "GPM survival, female", "=1",
     "=IF(A{p}<n_cycles,I{p}*(1-INDEX(lt_qx_female,MATCH(INT(D{p}),lt_age,0)))^cycle_length_years,I{p})"),
    ("J", "GPM survival, cohort", None, "=prop_male*H{r}+(1-prop_male)*I{r}"),
    ("K", "S_OS (capped)", "=F{r}",
     "=K{p}*IF(use_gpm_cap=1,MIN(" + ratio("F", "{r}", "{p}") + "," + ratio("J", "{r}", "{p}") + ")," + ratio("F", "{r}", "{p}") + ")"),
    ("L", "S_PFS (capped)", "=E{r}",
     "=L{p}*IF(use_gpm_cap=1,MIN(" + ratio("E", "{r}", "{p}") + "," + ratio("J", "{r}", "{p}") + ")," + ratio("E", "{r}", "{p}") + ")"),
    ("M", "S_ToT (capped by OS)", None, "=MIN(G{r},K{r})"),
    ("N", "PF", None, "=MIN(L{r},K{r})"),
    ("O", "PD", None, "=K{r}-N{r}"),
    ("P", "Dead", None, "=1-K{r}"),
    ("Q", "In horizon", None, "=IF(A{r}<n_cycles,1,0)"),
    ("R", "PF (HCC)", None, "=IF(Q{r}=1,(N{r}+N{n})/2,0)"),
    ("S", "PD (HCC)", None, "=IF(Q{r}=1,(O{r}+O{n})/2,0)"),
    ("T", "Alive (HCC)", None, "=R{r}+S{r}"),
    ("U", "Deaths in cycle", None, "=IF(Q{r}=1,K{r}-K{n},0)"),
    ("V", "Progressions in cycle", None, "=IF(Q{r}=1,MAX(0,N{r}-N{n})*(1-$C$9),0)"),
    ("W", "Dose due", None, "=IF(AND(Q{r}=1,MOD(A{r},$C$13)=0,A{r}/$C$13<$C$14),1,0)"),
    ("X", "Doses (ToT at cycle start)", None, "=W{r}*M{r}"),
    ("Y", "DF costs, cycle start", None, "=1/(1+dr_costs)^(A{r}*cycle_length_years)"),
    ("Z", "DF costs, mid-cycle", None, "=1/(1+dr_costs)^((A{r}+0.5)*cycle_length_years)"),
    ("AA", "DF outcomes, mid-cycle", None, "=1/(1+dr_outcomes)^((A{r}+0.5)*cycle_length_years)"),
    ("AB", "Age at mid-cycle", None, "=baseline_age+(A{r}+0.5)*cycle_length_years"),
    ("AC", "Utility age multiplier", None,
     "=IF(use_age_util_adj=1,(gpu_intercept+gpu_male*prop_male+gpu_age*AB{r}+gpu_age2*AB{r}^2)/calc_gpu_baseline,1)"),
    ("AD", "Drug cost", None, "=X{r}*$C$11*$C$10"),
    ("AE", "Admin cost", None, "=X{r}*$C$12"),
    ("AF", "PF state cost", None, "=R{r}*c_pf_week*cycle_length_days/7"),
    ("AG", "PD state cost", None, "=S{r}*c_pd_week*cycle_length_days/7"),
    ("AH", "Terminal care cost", None, "=U{r}*c_terminal"),
    ("AI", "Subsequent therapy cost", None, "=V{r}*$C$15"),
    ("AJ", "Total cost (undisc.)", None, "=SUM(AD{r}:AI{r})"),
    ("AK", "LY (undisc.)", None, "=T{r}*cycle_length_years"),
    ("AL", "QALY (undisc.)", None, "=(R{r}*u_pf+S{r}*u_pd)*AC{r}*cycle_length_years"),
    ("AM", "Raw PFS > OS flag", None, "=IF(E{r}>F{r},1,0)"),
    ("AN", "GPM cap binds (OS)", None,
     "=IF(AND(use_gpm_cap=1,Q{r}=1)," + "IF(" + ratio("J", "{n}", "{r}") + "<" + ratio("F", "{n}", "{r}") + ",1,0),0)"),
]
BOUNDARY_COLS = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"}


def add_name(wb, name, sheet, ref):
    parts = []
    for cell in ref.split(":"):
        col = "".join(ch for ch in cell if ch.isalpha())
        parts.append(f"${col}${cell[len(col):]}")
    wb.defined_names[name] = DefinedName(name, attr_text=f"{sheet}!{':'.join(parts)}")


def input_sheet(wb, title, heading, rows):
    ws = wb.create_sheet(title)
    ws["A1"] = heading
    ws["A1"].font = TITLE
    hdr = ["Parameter", "Name (defined range)", "Value", "Unit", "PSA distribution", "PSA SE", "Source / note"]
    for j, h in enumerate(hdr, 1):
        ws.cell(row=3, column=j, value=h).font = HEAD
    for i, (label, name, value, unit, dist, se, src) in enumerate(rows, start=4):
        ws.cell(row=i, column=1, value=label)
        ws.cell(row=i, column=2, value=name)
        ws.cell(row=i, column=3, value=value).fill = INPUT_FILL
        ws.cell(row=i, column=4, value=unit)
        ws.cell(row=i, column=5, value=dist)
        ws.cell(row=i, column=6, value=se)
        ws.cell(row=i, column=7, value=src)
        add_name(wb, name, title, f"C{i}")
    for col, w in zip("ABCDEFG", (60, 30, 16, 14, 16, 10, 60)):
        ws.column_dimensions[col].width = w
    return ws, 4 + len(rows)


def life_table_sheet(wb):
    ws = wb.create_sheet("Inputs_LifeTable")
    ws["A1"] = "General-population life table (synthetic, UK-like): qx = annual probability of death"
    ws["A1"].font = TITLE
    for j, h in enumerate(["Age (lt_age)", "qx male (lt_qx_male)", "qx female (lt_qx_female)"], 1):
        ws.cell(row=3, column=j, value=h).font = HEAD
    for i, (age, qm, qf) in enumerate(zip(LT_AGES, UK_QX_MALE, UK_QX_FEMALE), start=4):
        ws.cell(row=i, column=1, value=age).fill = INPUT_FILL
        ws.cell(row=i, column=2, value=qm).fill = INPUT_FILL
        ws.cell(row=i, column=3, value=qf).fill = INPUT_FILL
    last = 3 + len(LT_AGES)
    add_name(wb, "lt_age", "Inputs_LifeTable", f"A4:A{last}")
    add_name(wb, "lt_qx_male", "Inputs_LifeTable", f"B4:B{last}")
    add_name(wb, "lt_qx_female", "Inputs_LifeTable", f"C4:C{last}")
    ws["E3"] = "Source: synthetic Gompertz-Makeham table (scripts/synthetic_data.py). Not ONS data."
    for col, w in zip("ABC", (14, 22, 24)):
        ws.column_dimensions[col].width = w


def dosing_sheet(wb):
    """Expected vials per administration and derived per-arm costs (formulas only)."""
    ws = wb.create_sheet("Calc_Dosing")
    ws["A1"] = "Dosing, vial wastage and per-arm derived inputs (formulas only)"
    ws["A1"].font = TITLE
    ws["A3"], ws["B3"] = "Lognormal log-mean of weight", "=LN(weight_mean_kg)-calc_weight_sigma2/2"
    ws["A4"], ws["B4"] = "Lognormal log-variance of weight", "=LN(1+(weight_sd_kg/weight_mean_kg)^2)"
    add_name(wb, "calc_weight_mu", "Calc_Dosing", "B3")
    add_name(wb, "calc_weight_sigma2", "Calc_Dosing", "B4")
    ws["A5"], ws["B5"] = "General-population utility at baseline age", \
        "=gpu_intercept+gpu_male*prop_male+gpu_age*baseline_age+gpu_age2*baseline_age^2"
    add_name(wb, "calc_gpu_baseline", "Calc_Dosing", "B5")
    first, last = 10, 10 + VIAL_ROWS - 1
    cols = {"int": ("C", "D", "E"), "comp": ("G", "H", "I")}
    ws["A9"] = "Vials (k)"
    ws["A9"].font = HEAD
    for arm, (cw, cp, ck) in cols.items():
        ws[f"{cw}9"], ws[f"{cp}9"], ws[f"{ck}9"] = f"{arm}: weight upper bound (kg)", f"{arm}: P(k vials)", f"{arm}: k x P"
    for r in range(first, last + 1):
        ws[f"A{r}"] = f"=ROW()-ROW($A${first})+1"
        for arm, (cw, cp, ck) in cols.items():
            ws[f"{cw}{r}"] = f"=A{r}*{arm}_vial_mg/{arm}_dose_mg"
            lower = f"IF(A{r}=1,0,NORMDIST(LN({cw}{r - 1}),calc_weight_mu,SQRT(calc_weight_sigma2),TRUE))" if r > first else "0"
            ws[f"{cp}{r}"] = f"=NORMDIST(LN({cw}{r}),calc_weight_mu,SQRT(calc_weight_sigma2),TRUE)-{lower}"
            ws[f"{ck}{r}"] = f"=A{r}*{cp}{r}"
    derived = [
        ("Expected vials per administration", "expected_vials",
         lambda a, cp, ck: f"=IF({a}_dose_weight_based=1,IF(calc_weight_sigma2=0,ROUNDUP({a}_dose_mg*weight_mean_kg/{a}_vial_mg,0),"
                           f"SUM({ck}{first}:{ck}{last})/SUM({cp}{first}:{cp}{last})),ROUNDUP({a}_dose_mg/{a}_vial_mg,0))"),
        ("Probability mass beyond last vial band (weight-based only)", "vial_tail_mass",
         lambda a, cp, ck: f"=IF(AND({a}_dose_weight_based=1,calc_weight_sigma2>0),1-SUM({cp}{first}:{cp}{last}),0)"),
        ("Drug cost per administration", "drug_cost_per_admin", lambda a, cp, ck: f"=calc_{a}_expected_vials*{a}_vial_price"),
        ("Dosing interval in cycles", "interval_cycles", lambda a, cp, ck: f"={a}_admin_interval_weeks*7/cycle_length_days"),
        ("Subsequent therapy cost per progression", "st_cost_per_progression",
         lambda a, cp, ck: "=" + "+".join(f"{a}_st_share_{j}*st_cost_{j}" for j in ST_LABELS)),
        ("Sum of subsequent therapy shares", "st_share_sum", lambda a, cp, ck: "=" + "+".join(f"{a}_st_share_{j}" for j in ST_LABELS)),
    ]
    ws["E2"], ws["F2"], ws["G2"] = "Derived per arm", "Drug A", "Drug B"
    for i, (label, key, f) in enumerate(derived, start=3):
        ws[f"E{i}"] = label
        for col, arm in (("F", "int"), ("G", "comp")):
            ws[f"{col}{i}"] = f(arm, cols[arm][1], cols[arm][2])
            ws[f"{col}{i}"].fill = CALC_FILL
            add_name(wb, f"calc_{arm}_{key}", "Calc_Dosing", f"{col}{i}")
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["E"].width = 56


def trace_sheet(wb, arm):
    title = "Trace_Int" if arm == "int" else "Trace_Comp"
    ws = wb.create_sheet(title)
    ws["A1"] = f"Partitioned survival trace: {ARMS[arm]}"
    ws["A1"].font = TITLE
    ws["B2"] = "Arm parameter block (links to named inputs; do not edit here)"
    ws["B2"].font = HEAD
    for row, label, formula in ARM_BLOCK:
        ws[f"B{row}"] = label
        ws[f"C{row}"] = formula.format(a=arm)
        ws[f"C{row}"].fill = CALC_FILL
    for col, header, _, _ in TRACE_COLS:
        ws[f"{col}{FIRST - 1}"] = header
        ws[f"{col}{FIRST - 1}"].font = HEAD
        ws[f"{col}{FIRST - 1}"].alignment = Alignment(wrap_text=True)
    for r in range(FIRST, LAST_BOUNDARY + 1):
        for col, _, first_f, f in TRACE_COLS:
            if r == LAST_BOUNDARY and col not in BOUNDARY_COLS:
                continue
            tmpl = first_f if (r == FIRST and first_f is not None) else f
            ws[f"{col}{r}"] = tmpl.format(r=r, n=r + 1, p=r - 1)
    ws.freeze_panes = f"B{FIRST}"
    ws.column_dimensions["B"].width = 44
    return title


def rng(sheet, col, last=LAST_INTERVAL):
    return f"{sheet}!${col}${FIRST}:${col}${last}"


def results_sheet(wb):
    ws = wb.create_sheet("Results")
    ws["A1"] = "Deterministic base-case results (discounted unless stated)"
    ws["A1"].font = TITLE
    ws["A2"] = '="Currency: "&currency_code&"; WTP "&TEXT(wtp_threshold,"#,##0")&" per QALY"'
    for j, h in enumerate(["Outcome", "Drug A", "Drug B", "Incremental", "Name (B / C / D)"], 1):
        ws.cell(row=4, column=j, value=h).font = HEAD
    sheets = {"int": "Trace_Int", "comp": "Trace_Comp"}
    sp = lambda col, df: (lambda s, a: f"=SUMPRODUCT({rng(s, col)},{rng(s, df)})")
    rows = [
        ("Drug acquisition cost", "cost_drug", sp("AD", "Y")),
        ("Administration cost", "cost_admin", sp("AE", "Y")),
        ("Progression-free state cost", "cost_pf_state", sp("AF", "Z")),
        ("Progressed disease state cost", "cost_pd_state", sp("AG", "Z")),
        ("Terminal care cost", "cost_terminal", sp("AH", "Z")),
        ("Subsequent therapy cost", "cost_st", sp("AI", "Z")),
        ("Adverse event cost", "cost_ae", lambda s, a: f"={a}_ae_cost"),
        ("Total costs", "total_cost", None),
        ("Life years (undiscounted)", "ly_undisc", lambda s, a: f"=SUM({rng(s, 'AK')})"),
        ("Life years (discounted)", "ly_disc", sp("AK", "AA")),
        ("QALYs (undiscounted)", "qaly_undisc", lambda s, a: f"=SUM({rng(s, 'AL')})-{a}_ae_qaly_loss"),
        ("QALYs (discounted)", "qaly_disc", lambda s, a: f"=SUMPRODUCT({rng(s, 'AL')},{rng(s, 'AA')})-{a}_ae_qaly_loss"),
    ]
    r, pos = 5, {}
    for label, key, f in rows:
        ws.cell(row=r, column=1, value=label)
        for col, arm in (("B", "int"), ("C", "comp")):
            ws[f"{col}{r}"] = f"=SUM({col}5:{col}11)" if key == "total_cost" else f(sheets[arm], arm)
            add_name(wb, f"res_{arm}_{key}", "Results", f"{col}{r}")
        ws[f"D{r}"] = f"=B{r}-C{r}"
        add_name(wb, f"res_inc_{key}", "Results", f"D{r}")
        ws[f"E{r}"] = f"res_int_{key} / res_comp_{key} / res_inc_{key}"
        if key in ("total_cost", "qaly_disc"):
            for col in "ABCD":
                ws[f"{col}{r}"].font = HEAD
        pos[key] = r
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="Cost-effectiveness").font = HEAD
    r += 1
    tc, qd, ld = pos["total_cost"], pos["qaly_disc"], pos["ly_disc"]
    summary = [
        ("ICER (cost per QALY gained)", "res_icer", f"=IF(D{qd}=0,NA(),D{tc}/D{qd})"),
        ("ICER (cost per LY gained)", "res_icer_ly", f"=IF(D{ld}=0,NA(),D{tc}/D{ld})"),
        ("Incremental NMB at upper WTP", "res_inc_nmb", f"=D{qd}*wtp_threshold-D{tc}"),
        ("Incremental NMB at lower WTP", "res_inc_nmb_lower", f"=D{qd}*wtp_threshold_lower-D{tc}"),
        ("Dominance status", "res_dominance",
         f'=IF(AND(D{tc}<=0,D{qd}>=0),"Dominant",IF(AND(D{tc}>=0,D{qd}<=0),"Dominated",'
         f'IF(D{qd}>0,"More costly, more effective","Less costly, less effective")))'),
        ("ICER at or below upper WTP", "res_below_wtp", f'=IF(AND(D{qd}>0,res_icer<=wtp_threshold),"Yes","No")'),
        ("ICER at or below lower WTP", "res_below_wtp_lower", f'=IF(AND(D{qd}>0,res_icer<=wtp_threshold_lower),"Yes","No")'),
    ]
    for label, name, formula in summary:
        ws.cell(row=r, column=1, value=label)
        ws[f"D{r}"] = formula
        ws[f"E{r}"] = name
        add_name(wb, name, "Results", f"D{r}")
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="Survival, dosing and cost summaries").font = HEAD
    r += 1
    extra = [
        ("Median PFS, Weibull uncapped (months)", "median_pfs", lambda a: f"={a}_pfs_scale*LN(2)^(1/{a}_pfs_shape)"),
        ("Median OS, Weibull uncapped (months)", "median_os", lambda a: f"={a}_os_scale*LN(2)^(1/{a}_os_shape)"),
        ("Median ToT, Weibull uncapped (months)", "median_tot", lambda a: f"={a}_tot_scale*LN(2)^(1/{a}_tot_shape)"),
        ("Proportion alive at end of horizon", "s_os_horizon",
         lambda a: f"=INDEX({rng(sheets[a], 'K', LAST_BOUNDARY)},n_cycles+1)"),
        ("Expected number of doses per patient", "n_doses", lambda a: f"=SUM({rng(sheets[a], 'X')})"),
        ("Expected vials per administration", "expected_vials", lambda a: f"=calc_{a}_expected_vials"),
        ("Drug cost per administration", "drug_cost_per_admin", lambda a: f"=calc_{a}_drug_cost_per_admin"),
        ("Subsequent therapy cost per progression", "st_cost_per_progression", lambda a: f"=calc_{a}_st_cost_per_progression"),
        ("Drug acquisition share of total costs", "drug_share", lambda a: f"=res_{a}_cost_drug/res_{a}_total_cost"),
        ("Cycles in which the GPM cap binds (OS)", "gpm_bind_cycles", lambda a: f"=SUM({rng(sheets[a], 'AN')})"),
        ("Age when the GPM cap first binds (OS)", "gpm_first_bind_age",
         lambda a: f'=IF(res_{a}_gpm_bind_cycles=0,"None",baseline_age+(MATCH(1,{rng(sheets[a], "AN")},0)-1)*cycle_length_years)'),
        ("Proportion alive when the GPM cap first binds", "gpm_first_bind_alive",
         lambda a: f'=IF(res_{a}_gpm_bind_cycles=0,"None",INDEX({rng(sheets[a], "K")},MATCH(1,{rng(sheets[a], "AN")},0)))'),
    ]
    for label, key, f in extra:
        ws.cell(row=r, column=1, value=label)
        for col, arm in (("B", "int"), ("C", "comp")):
            ws[f"{col}{r}"] = f(arm)
            add_name(wb, f"res_{arm}_{key}", "Results", f"{col}{r}")
        ws[f"E{r}"] = f"res_int_{key} / res_comp_{key}"
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="Model checks").font = HEAD
    r += 1
    checks = [
        ("Trace rows sufficient for horizon", "check_trace_rows_ok", '=IF(n_cycles<=max_trace_cycles,"OK","FAIL")'),
        ("Residual alive at horizon below lifetime_check_tol (both arms)", "check_lifetime_ok",
         '=IF(MAX(res_int_s_os_horizon,res_comp_s_os_horizon)<lifetime_check_tol,"OK","FAIL")'),
        ("Life table covers ages to end of horizon", "check_life_table_ok",
         '=IF(AND(MIN(lt_age)<=baseline_age,MAX(lt_age)>=INT(baseline_age+time_horizon_years)),"OK","FAIL")'),
        ("Dosing intervals are whole cycles", "check_interval_ok",
         '=IF(AND(MOD(calc_int_interval_cycles,1)=0,MOD(calc_comp_interval_cycles,1)=0),"OK","FAIL")'),
        ("Subsequent therapy shares sum to at most 1", "check_st_shares_ok",
         '=IF(AND(calc_int_st_share_sum<=1,calc_comp_st_share_sum<=1),"OK","FAIL")'),
        ("Vial bands cover the weight distribution", "check_vial_bands_ok",
         '=IF(MAX(calc_int_vial_tail_mass,calc_comp_vial_tail_mass)<lifetime_check_tol,"OK","FAIL")'),
        ("Cycles with raw S_PFS > S_OS, Drug A (capped by MIN)", "check_cross_int", f"=SUM({rng('Trace_Int', 'AM', LAST_BOUNDARY)})"),
        ("Cycles with raw S_PFS > S_OS, Drug B (capped by MIN)", "check_cross_comp", f"=SUM({rng('Trace_Comp', 'AM', LAST_BOUNDARY)})"),
    ]
    for label, name, formula in checks:
        ws.cell(row=r, column=1, value=label)
        ws[f"D{r}"] = formula
        ws[f"E{r}"] = name
        add_name(wb, name, "Results", f"D{r}")
        r += 1

    for col, w in zip("ABCDE", (56, 18, 18, 18, 52)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=5, max_row=r, min_col=2, max_col=4):
        for c in row:
            c.number_format = "#,##0.0000"


def psa_sheet(wb):
    ws = wb.create_sheet("PSA_Placeholder")
    ws["A1"] = "PSA: placeholder (no VBA in this fixture)"
    ws["A1"].font = TITLE
    notes = [
        "STATUS: Not implemented. This sheet documents the output a VBA macro (mod_PSA) would write.",
        "The workbook is .xlsx and contains no macros. A runnable version would need .xlsm plus Excel.",
        "",
        "Specification of the intended macro:",
        "1. Seed: Rnd -1 then Randomize psa_seed (cell B12). Iterations: psa_iterations (cell B13).",
        "2. Per iteration: sample every input whose 'PSA distribution' is not Fixed/PSA only, using",
        "   mean = Value column and SE = 'PSA SE' column on the Inputs_* sheets: Gamma (method of moments) for",
        "   costs; Beta for utilities, QALY losses, RDI and event proportions; Dirichlet for subsequent-therapy shares;",
        "   bivariate normal on (log shape, log scale) per Weibull curve (PFS, OS, ToT), correlation from *_corr (Cholesky).",
        "3. Write sampled values to the named input cells, Application.Calculate, read the res_* cells",
        "   listed in row 16 into one row of the table below, then restore base-case inputs.",
        "4. Summaries (rows 6-9 of column J) and CEAC (columns L:M) derived from the table.",
    ]
    for i, t in enumerate(notes, start=2):
        ws.cell(row=i, column=1, value=t)
    ws["A12"], ws["B12"] = "psa_seed", 20251027
    ws["A13"], ws["B13"] = "psa_iterations", 1000
    add_name(wb, "psa_seed", "PSA_Placeholder", "B12")
    add_name(wb, "psa_iterations", "PSA_Placeholder", "B13")
    hdr = ["Iteration", "res_int_total_cost", "res_comp_total_cost", "res_int_qaly_disc",
           "res_comp_qaly_disc", "res_inc_total_cost", "res_inc_qaly_disc", "res_inc_nmb"]
    for j, h in enumerate(hdr, 1):
        ws.cell(row=16, column=j, value=h).font = HEAD
    ws["A17"] = "(empty: populated by macro)"
    ws["J5"] = "Summary (macro output)"
    ws["J5"].font = HEAD
    for i, t in enumerate(["Mean incremental cost", "Mean incremental QALYs",
                           "Probabilistic ICER (ratio of means)", "P(cost-effective) at wtp_threshold"], start=6):
        ws[f"J{i}"] = t
        ws[f"K{i}"] = "(empty)"
    ws["L5"], ws["M5"] = "CEAC: WTP", "P(cost-effective)"
    ws["L5"].font = ws["M5"].font = HEAD
    ws["L6"] = "(empty: grid 0 to 3 x wtp_threshold, populated by macro)"
    ws.column_dimensions["A"].width = 110


def readme_sheet(wb):
    ws = wb.active
    ws.title = "ReadMe"
    lines = [
        ("Global PartSA cost-effectiveness model: SYNTHETIC FIXTURE (Fixture A)", TITLE),
        ("All data are synthetic and for software testing only. Not for decision making.", HEAD),
        ("Conventions are declared in global_model.conventions.yaml; this sheet is a summary.", None),
        ("", None),
        ("Structure: 3-state partitioned survival (progression-free, progressed disease, death), 2 arms.", None),
        ("Survival: independent Weibull (AFT) per arm for PFS, OS and ToT; S(t) = EXP(-((t/scale)^shape)), t in months.", None),
        ("General-population mortality: per-cycle conditional survival = MIN(parametric, life table) for PFS and OS.", None),
        ("PF = MIN(S_PFS, S_OS); PD = S_OS - PF; Dead = 1 - S_OS (capped curves). ToT = MIN(S_ToT, S_OS).", None),
        ("Cycles: weekly; lifetime horizon. Half-cycle correction (trapezoid) on state membership for state costs, LYs, QALYs.", None),
        ("Dosing: costs only in dosing weeks, ToT at cycle start, no HCC; stopping rule by number of doses; RDI on drug cost.", None),
        ("Vials: weight-based dosing uses exact expected vials under a lognormal weight distribution (no vial sharing).", None),
        ("Discounting: dosing costs at cycle start; other costs and outcomes at cycle mid-point; (1+r)^-t, t in years.", None),
        ("Utilities: state utility x age multiplier gpu(age)/gpu(baseline_age); AE QALY loss one-off at t=0.", None),
        ("One-off events: terminal care on deaths (OS decrement); subsequent therapy on progressions", None),
        ("  (PF decrement x (1 - proportion of PFS events that are deaths)), costed as share-weighted course costs.", None),
        ("", None),
        ("Sheet map", HEAD),
        ("Inputs_Settings / _Population / _Clinical / _Costs / _Utilities / _LifeTable: all inputs (blue cells), named.", None),
        ("Calc_Dosing: expected vials, per-arm derived costs (formulas only).", None),
        ("Trace_Int / Trace_Comp: identical formula layout; arm parameter block in C3:C17 links to named inputs.", None),
        ("Results: costs, LYs, QALYs, ICER, NMB, summaries, model checks (named res_* / check_* cells).", None),
        ("PSA_Placeholder: specification of the VBA PSA macro output (not implemented).", None),
    ]
    for i, (t, f) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=t)
        if f:
            ws.cell(row=i, column=1).font = f
    ws.column_dimensions["A"].width = 130


VARIANTS = {
    "A": {"out": OUT, "label": "Fixture A", "df": {
        "Y": ("DF costs, cycle start", "=1/(1+dr_costs)^(A{r}*cycle_length_years)"),
        "Z": ("DF costs, mid-cycle", "=1/(1+dr_costs)^((A{r}+0.5)*cycle_length_years)"),
        "AA": ("DF outcomes, mid-cycle", "=1/(1+dr_outcomes)^((A{r}+0.5)*cycle_length_years)")},
        "readme": "Discounting: dosing costs at cycle start; other costs and outcomes at cycle mid-point; (1+r)^-t, t in years."},
    "B": {"out": OUT.with_name("global_model_B.xlsx"), "label": "Fixture B", "df": {
        "Y": ("DF costs, model year (dosing)", "=1/(1+dr_costs)^INT(A{r}*cycle_length_days/days_per_year)"),
        "Z": ("DF costs, model year", "=1/(1+dr_costs)^INT(A{r}*cycle_length_days/days_per_year)"),
        "AA": ("DF outcomes, model year", "=1/(1+dr_outcomes)^INT(A{r}*cycle_length_days/days_per_year)")},
        "readme": "Discounting: annual step; every cycle starting in model year k is discounted by (1+r)^-k (year 1 undiscounted)."},
}


def apply_variant(variant: str) -> Path:
    v = VARIANTS[variant]
    for i, (col, header, first_f, f) in enumerate(TRACE_COLS):
        if col in v["df"]:
            TRACE_COLS[i] = (col, v["df"][col][0], first_f, v["df"][col][1])
    return v["out"]


def main(variant: str = "A"):
    out = apply_variant(variant)
    wb = Workbook()
    readme_sheet(wb)
    ws, nxt = input_sheet(wb, "Inputs_Settings", "Model settings", SETTINGS)
    ws.cell(row=nxt + 1, column=1, value="Calculated settings (formulas; do not edit)").font = HEAD
    for i, (label, name, formula, unit) in enumerate(SETTINGS_CALC, start=nxt + 2):
        ws.cell(row=i, column=1, value=label)
        ws.cell(row=i, column=2, value=name)
        ws.cell(row=i, column=3, value=formula).fill = CALC_FILL
        ws.cell(row=i, column=4, value=unit)
        add_name(wb, name, "Inputs_Settings", f"C{i}")
    input_sheet(wb, "Inputs_Population", "Population characteristics", POPULATION)
    input_sheet(wb, "Inputs_Clinical", "Clinical inputs (survival, treatment exposure)", CLINICAL)
    input_sheet(wb, "Inputs_Costs", "Cost and resource-use inputs", COSTS + ST_ROWS)
    input_sheet(wb, "Inputs_Utilities", "Utility inputs", UTILITIES)
    life_table_sheet(wb)
    dosing_sheet(wb)
    trace_sheet(wb, "int")
    trace_sheet(wb, "comp")
    results_sheet(wb)
    psa_sheet(wb)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    readme = wb["ReadMe"]
    readme["A1"] = readme["A1"].value.replace("(Fixture A)", f"({VARIANTS[variant]['label']})")
    for row in readme.iter_rows():
        if row[0].value and str(row[0].value).startswith("Discounting:"):
            row[0].value = VARIANTS[variant]["readme"]
        if row[0].value and "global_model.conventions.yaml" in str(row[0].value):
            row[0].value = row[0].value.replace("global_model.conventions.yaml", out.stem + ".conventions.yaml")
    wb.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "A")
