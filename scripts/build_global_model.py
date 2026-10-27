"""Generate fixtures/global_model.xlsx: formula-driven 3-state PartSA (synthetic data).

Run:  python scripts/build_global_model.py
All values are SYNTHETIC. Calculation sheets contain formulas only; every input is a
named single-cell range on an Inputs_* sheet.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "global_model.xlsx"

MAX_TRACE_CYCLES = 2088          # interval rows; 2088 weekly cycles = 40.03 years
FIRST = 17                       # first data row on trace sheets
LAST_INTERVAL = FIRST + MAX_TRACE_CYCLES - 1   # 2104
LAST_BOUNDARY = LAST_INTERVAL + 1              # 2105

INPUT_FILL = PatternFill("solid", fgColor="DDEBF7")
CALC_FILL = PatternFill("solid", fgColor="F2F2F2")
HEAD = Font(bold=True)
TITLE = Font(bold=True, size=14)

ARMS = {"int": "Drug A (intervention)", "comp": "Drug B, platinum doublet (comparator)"}

# (label, name, value, unit, PSA distribution, PSA SE, source / note)
SETTINGS = [
    ("Country / setting", "country", "United Kingdom", "text", "Fixed", None, "Global base case"),
    ("Currency", "currency_code", "GBP", "ISO 4217", "Fixed", None, ""),
    ("Price year", "price_year", 2025, "year", "Fixed", None, "Synthetic"),
    ("Perspective", "perspective", "NHS and PSS", "text", "Fixed", None, "NICE reference case"),
    ("Cycle length", "cycle_length_days", 7, "days", "Fixed", None, "Weekly cycles"),
    ("Days per year", "days_per_year", 365.25, "days", "Fixed", None, ""),
    ("Time horizon", "time_horizon_years", 40, "years", "Fixed", None, "Lifetime (age 62 to 102)"),
    ("Baseline age", "baseline_age", 62, "years", "Fixed", None, "Informational; no age-adjusted utility or background mortality"),
    ("Discount rate, costs", "dr_costs", 0.035, "per annum", "Fixed", None, "NICE reference case"),
    ("Discount rate, outcomes", "dr_outcomes", 0.035, "per annum", "Fixed", None, "NICE reference case"),
    ("WTP threshold (upper)", "wtp_threshold", 30000, "currency/QALY", "Fixed", None, "NICE range upper bound"),
    ("WTP threshold (lower)", "wtp_threshold_lower", 20000, "currency/QALY", "Fixed", None, "NICE range lower bound"),
    ("Lifetime check: max proportion alive at horizon", "lifetime_check_tol", 0.001, "proportion", "Fixed", None, "QA setting"),
]
SETTINGS_CALC = [
    ("Cycle length (years)", "cycle_length_years", "=cycle_length_days/days_per_year", "years"),
    ("Number of model cycles", "n_cycles", "=ROUND(time_horizon_years*days_per_year/cycle_length_days,0)", "cycles"),
    ("Trace rows available", "max_trace_cycles", f"=ROWS(Trace_Int!$A${FIRST}:$A${LAST_INTERVAL})", "cycles"),
]

CLINICAL = []
_surv = {
    "int": {"pfs": (0.95, 12.0, 0.06, 0.05, -0.35), "os": (1.05, 34.0, 0.07, 0.08, -0.40)},
    "comp": {"pfs": (1.25, 7.0, 0.05, 0.04, -0.30), "os": (1.15, 16.0, 0.06, 0.05, -0.38)},
}
for arm, label in ARMS.items():
    for ep in ("pfs", "os"):
        shape, scale, se_ls, se_lsc, rho = _surv[arm][ep]
        src = f"Synthetic Weibull fit to {ep.upper()} KM, {label}"
        CLINICAL += [
            (f"{label}: {ep.upper()} Weibull shape", f"{arm}_{ep}_shape", shape, "-", "MVN on log", se_ls, src),
            (f"{label}: {ep.upper()} Weibull scale", f"{arm}_{ep}_scale", scale, "months", "MVN on log", se_lsc, src),
            (f"{label}: {ep.upper()} corr(log shape, log scale)", f"{arm}_{ep}_corr", rho, "-", "PSA only", None, "Not used in deterministic run"),
        ]

COSTS = [
    ("Drug A net price per administration (incl. PAS)", "int_drug_cost_per_admin", 780, "GBP", "Fixed", None, "Synthetic list price with confidential discount"),
    ("Drug A administration cost per administration", "int_admin_cost_per_admin", 310, "GBP", "Gamma", 62, "Synthetic NHS reference cost, SB12Z"),
    ("Drug A administration interval", "int_admin_interval_weeks", 3, "weeks", "Fixed", None, "Q3W per SmPC"),
    ("Drug A maximum treatment duration", "int_max_tx_weeks", 104, "weeks", "Fixed", None, "2-year stopping rule"),
    ("Drug A adverse event cost (one-off)", "int_ae_cost", 1150, "GBP", "Gamma", 230, "Grade 3+ AE incidence x unit costs"),
    ("Drug B acquisition cost per administration", "comp_drug_cost_per_admin", 480, "GBP", "Fixed", None, "Synthetic eMIT price"),
    ("Drug B administration cost per administration", "comp_admin_cost_per_admin", 310, "GBP", "Gamma", 62, "Synthetic NHS reference cost, SB12Z"),
    ("Drug B administration interval", "comp_admin_interval_weeks", 3, "weeks", "Fixed", None, "Q3W"),
    ("Drug B maximum treatment duration", "comp_max_tx_weeks", 18, "weeks", "Fixed", None, "6 cycles"),
    ("Drug B adverse event cost (one-off)", "comp_ae_cost", 2400, "GBP", "Gamma", 480, "Grade 3+ AE incidence x unit costs"),
    ("Progression-free health state cost per week", "c_pf_week", 150, "GBP/week", "Gamma", 30, "Synthetic resource use x PSSRU"),
    ("Progressed disease health state cost per week", "c_pd_week", 230, "GBP/week", "Gamma", 46, "Synthetic resource use x PSSRU"),
    ("Terminal care cost (one-off at death)", "c_terminal", 6500, "GBP", "Gamma", 1300, "Synthetic end-of-life costing"),
]

UTILITIES = [
    ("Utility, progression-free", "u_pf", 0.75, "-", "Beta", 0.03, "Synthetic trial EQ-5D-3L, UK value set"),
    ("Utility, progressed disease", "u_pd", 0.60, "-", "Beta", 0.04, "Synthetic trial EQ-5D-3L, UK value set"),
    ("Drug A AE QALY loss (one-off)", "int_ae_qaly_loss", 0.008, "QALY", "Beta", 0.002, "Synthetic"),
    ("Drug B AE QALY loss (one-off)", "comp_ae_qaly_loss", 0.015, "QALY", "Beta", 0.004, "Synthetic"),
]

ARM_BLOCK = [  # (row, label, suffix) on trace sheets, value in column C
    (3, "PFS Weibull shape", "pfs_shape"), (4, "PFS Weibull scale (months)", "pfs_scale"),
    (5, "OS Weibull shape", "os_shape"), (6, "OS Weibull scale (months)", "os_scale"),
    (7, "Drug cost per administration", "drug_cost_per_admin"),
    (8, "Administration cost per administration", "admin_cost_per_admin"),
    (9, "Administration interval (weeks)", "admin_interval_weeks"),
    (10, "Maximum treatment duration (weeks)", "max_tx_weeks"),
    (11, "AE cost (one-off)", "ae_cost"), (12, "AE QALY loss (one-off)", "ae_qaly_loss"),
]

TRACE_COLS = [  # (col, header, formula template with {r} and {n} = r+1)
    ("A", "Cycle", f"=ROW()-ROW($A${FIRST})"),
    ("B", "Time (years)", "=A{r}*cycle_length_years"),
    ("C", "Time (months)", "=B{r}*12"),
    ("D", "S_PFS(t)", "=EXP(-((C{r}/$C$4)^$C$3))"),
    ("E", "S_OS(t)", "=EXP(-((C{r}/$C$6)^$C$5))"),
    ("F", "PF", "=MIN(D{r},E{r})"),
    ("G", "PD", "=E{r}-F{r}"),
    ("H", "Dead", "=1-E{r}"),
    ("I", "In horizon", "=IF(A{r}<n_cycles,1,0)"),
    ("J", "PF (HCC)", "=IF(I{r}=1,(F{r}+F{n})/2,0)"),
    ("K", "PD (HCC)", "=IF(I{r}=1,(G{r}+G{n})/2,0)"),
    ("L", "Alive (HCC)", "=J{r}+K{r}"),
    ("M", "On treatment", "=IF(A{r}*cycle_length_days<$C$10*7,J{r},0)"),
    ("N", "Deaths in cycle", "=IF(I{r}=1,E{r}-E{n},0)"),
    ("O", "DF costs", "=1/(1+dr_costs)^((A{r}+0.5)*cycle_length_years)"),
    ("P", "DF outcomes", "=1/(1+dr_outcomes)^((A{r}+0.5)*cycle_length_years)"),
    ("Q", "Drug cost", "=M{r}*$C$7*cycle_length_days/(7*$C$9)"),
    ("R", "Admin cost", "=M{r}*$C$8*cycle_length_days/(7*$C$9)"),
    ("S", "PF state cost", "=J{r}*c_pf_week*cycle_length_days/7"),
    ("T", "PD state cost", "=K{r}*c_pd_week*cycle_length_days/7"),
    ("U", "Terminal care cost", "=N{r}*c_terminal"),
    ("V", "Total cost (undisc.)", "=SUM(Q{r}:U{r})"),
    ("W", "LY (undisc.)", "=L{r}*cycle_length_years"),
    ("X", "QALY (undisc.)", "=(J{r}*u_pf+K{r}*u_pd)*cycle_length_years"),
    ("Y", "PFS > OS flag", "=IF(D{r}>E{r},1,0)"),
]
BOUNDARY_COLS = "ABCDEFGH"


def add_name(wb, name, sheet, cell):
    col = "".join(ch for ch in cell if ch.isalpha())
    row = cell[len(col):]
    wb.defined_names[name] = DefinedName(name, attr_text=f"{sheet}!${col}${row}")


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
        c = ws.cell(row=i, column=3, value=value)
        c.fill = INPUT_FILL
        ws.cell(row=i, column=4, value=unit)
        ws.cell(row=i, column=5, value=dist)
        ws.cell(row=i, column=6, value=se)
        ws.cell(row=i, column=7, value=src)
        add_name(wb, name, title, f"C{i}")
    for col, w in zip("ABCDEFG", (52, 30, 16, 14, 16, 10, 60)):
        ws.column_dimensions[col].width = w
    return ws, 4 + len(rows)


def trace_sheet(wb, arm):
    title = "Trace_Int" if arm == "int" else "Trace_Comp"
    ws = wb.create_sheet(title)
    ws["A1"] = f"Partitioned survival trace: {ARMS[arm]}"
    ws["A1"].font = TITLE
    ws["B2"] = "Arm parameter block (links to named inputs; do not edit here)"
    ws["B2"].font = HEAD
    for row, label, suffix in ARM_BLOCK:
        ws[f"B{row}"] = label
        ws[f"C{row}"] = f"={arm}_{suffix}"
        ws[f"C{row}"].fill = CALC_FILL
    for col, header, _ in TRACE_COLS:
        ws[f"{col}{FIRST - 1}"] = header
        ws[f"{col}{FIRST - 1}"].font = HEAD
        ws[f"{col}{FIRST - 1}"].alignment = Alignment(wrap_text=True)
    for r in range(FIRST, LAST_BOUNDARY + 1):
        for col, _, tmpl in TRACE_COLS:
            if r == LAST_BOUNDARY and col not in BOUNDARY_COLS:
                continue
            ws[f"{col}{r}"] = tmpl.format(r=r, n=r + 1)
    ws.freeze_panes = f"B{FIRST}"
    ws.column_dimensions["B"].width = 36
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
    rows = [
        ("Drug acquisition cost", "cost_drug", lambda s, a: f"=SUMPRODUCT({rng(s,'Q')},{rng(s,'O')})"),
        ("Administration cost", "cost_admin", lambda s, a: f"=SUMPRODUCT({rng(s,'R')},{rng(s,'O')})"),
        ("Progression-free state cost", "cost_pf_state", lambda s, a: f"=SUMPRODUCT({rng(s,'S')},{rng(s,'O')})"),
        ("Progressed disease state cost", "cost_pd_state", lambda s, a: f"=SUMPRODUCT({rng(s,'T')},{rng(s,'O')})"),
        ("Terminal care cost", "cost_terminal", lambda s, a: f"=SUMPRODUCT({rng(s,'U')},{rng(s,'O')})"),
        ("Adverse event cost", "cost_ae", lambda s, a: f"={a}_ae_cost"),
        ("Total costs", "total_cost", None),
        ("Life years (undiscounted)", "ly_undisc", lambda s, a: f"=SUM({rng(s,'W')})"),
        ("Life years (discounted)", "ly_disc", lambda s, a: f"=SUMPRODUCT({rng(s,'W')},{rng(s,'P')})"),
        ("QALYs (undiscounted)", "qaly_undisc", lambda s, a: f"=SUM({rng(s,'X')})-{a}_ae_qaly_loss"),
        ("QALYs (discounted)", "qaly_disc", lambda s, a: f"=SUMPRODUCT({rng(s,'X')},{rng(s,'P')})-{a}_ae_qaly_loss"),
    ]
    r = 5
    pos = {}
    for label, key, f in rows:
        ws.cell(row=r, column=1, value=label)
        for col, arm in (("B", "int"), ("C", "comp")):
            if key == "total_cost":
                ws[f"{col}{r}"] = f"=SUM({col}5:{col}10)"
            else:
                ws[f"{col}{r}"] = f(sheets[arm], arm)
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
    summary = [
        ("ICER (cost per QALY gained)", "res_icer", f"=IF(D{pos['qaly_disc']}=0,NA(),D{pos['total_cost']}/D{pos['qaly_disc']})"),
        ("ICER (cost per LY gained)", "res_icer_ly", f"=IF(D{pos['ly_disc']}=0,NA(),D{pos['total_cost']}/D{pos['ly_disc']})"),
        ("Incremental NMB at upper WTP", "res_inc_nmb", f"=D{pos['qaly_disc']}*wtp_threshold-D{pos['total_cost']}"),
        ("Incremental NMB at lower WTP", "res_inc_nmb_lower", f"=D{pos['qaly_disc']}*wtp_threshold_lower-D{pos['total_cost']}"),
        ("Dominance status", "res_dominance",
         f'=IF(AND(D{pos["total_cost"]}<=0,D{pos["qaly_disc"]}>=0),"Dominant",'
         f'IF(AND(D{pos["total_cost"]}>=0,D{pos["qaly_disc"]}<=0),"Dominated",'
         f'IF(D{pos["qaly_disc"]}>0,"More costly, more effective","Less costly, less effective")))'),
        ("ICER at or below upper WTP", "res_below_wtp", f'=IF(AND(D{pos["qaly_disc"]}>0,res_icer<=wtp_threshold),"Yes","No")'),
        ("ICER at or below lower WTP", "res_below_wtp_lower", f'=IF(AND(D{pos["qaly_disc"]}>0,res_icer<=wtp_threshold_lower),"Yes","No")'),
    ]
    for label, name, formula in summary:
        ws.cell(row=r, column=1, value=label)
        ws[f"D{r}"] = formula
        ws[f"E{r}"] = name
        add_name(wb, name, "Results", f"D{r}")
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="Survival and cost summaries").font = HEAD
    r += 1
    extra = [
        ("Median PFS (months)", "median_pfs", lambda a: f"={a}_pfs_scale*LN(2)^(1/{a}_pfs_shape)"),
        ("Median OS (months)", "median_os", lambda a: f"={a}_os_scale*LN(2)^(1/{a}_os_shape)"),
        ("Proportion alive at end of horizon", "s_os_horizon",
         lambda a: f"=INDEX({rng(sheets[a],'E',LAST_BOUNDARY)},n_cycles+1)"),
        ("Drug acquisition share of total costs", "drug_share", lambda a: f"=res_{a}_cost_drug/res_{a}_total_cost"),
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
        ("Cycles with S_PFS > S_OS, Drug A (capped by MIN)", "check_cross_int", f"=SUM({rng('Trace_Int','Y',LAST_BOUNDARY)})"),
        ("Cycles with S_PFS > S_OS, Drug B (capped by MIN)", "check_cross_comp", f"=SUM({rng('Trace_Comp','Y',LAST_BOUNDARY)})"),
    ]
    for label, name, formula in checks:
        ws.cell(row=r, column=1, value=label)
        ws[f"D{r}"] = formula
        ws[f"E{r}"] = name
        add_name(wb, name, "Results", f"D{r}")
        r += 1

    for col, w in zip("ABCDE", (48, 18, 18, 18, 52)):
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
        "   mean = Value column and SE = 'PSA SE' column on the Inputs_* sheets:",
        "   Gamma (method of moments) for costs; Beta (method of moments) for utilities and QALY losses;",
        "   bivariate normal on (log shape, log scale) per Weibull curve, correlation from *_corr inputs (Cholesky).",
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
                           "Probabilistic ICER (ratio of means)",
                           "P(cost-effective) at wtp_threshold"], start=6):
        ws[f"J{i}"] = t
        ws[f"K{i}"] = "(empty)"
    ws["L5"], ws["M5"] = "CEAC: WTP", "P(cost-effective)"
    ws["L5"].font = ws["M5"].font = HEAD
    ws["L6"] = "(empty: grid 0 to 3 x wtp_threshold, populated by macro)"
    ws.column_dimensions["A"].width = 100


def readme_sheet(wb):
    ws = wb.active
    ws.title = "ReadMe"
    lines = [
        ("Global PartSA cost-effectiveness model: SYNTHETIC FIXTURE", TITLE),
        ("All data are synthetic and for software testing only. Not for decision making.", HEAD),
        ("", None),
        ("Structure: 3-state partitioned survival (progression-free, progressed disease, death), 2 arms.", None),
        ("Survival: independent Weibull (AFT) per arm and endpoint; S(t) = EXP(-((t/scale)^shape)), t in months.", None),
        ("PF = MIN(S_PFS, S_OS); PD = S_OS - PF; Dead = 1 - S_OS.", None),
        ("Cycles: weekly; lifetime horizon (time_horizon_years). Half-cycle correction: trapezoidal on state membership.", None),
        ("Discounting: per-cycle factor at cycle mid-point, (1+r)^-((cycle+0.5) x cycle_length_years); separate r for costs and outcomes.", None),
        ("Treatment: while progression-free, up to max_tx_weeks (cycle start). Per-administration costs spread evenly across weeks.", None),
        ("Terminal care: one-off cost applied to deaths in each cycle. AE cost and QALY loss: one-off at t=0, undiscounted.", None),
        ("", None),
        ("Sheet map", HEAD),
        ("Inputs_Settings / Inputs_Clinical / Inputs_Costs / Inputs_Utilities: all inputs, one named range each (blue cells).", None),
        ("Trace_Int / Trace_Comp: identical formula layout; arm parameter block in C3:C12 links to named inputs.", None),
        ("Results: costs, LYs, QALYs, ICER, NMB, medians, model checks (named res_* / check_* cells).", None),
        ("PSA_Placeholder: specification of the VBA PSA macro output (not implemented).", None),
        ("", None),
        ("Calculation sheets contain formulas only. Inputs are edited only on Inputs_* sheets.", None),
    ]
    for i, (t, f) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=t)
        if f:
            ws.cell(row=i, column=1).font = f
    ws.column_dimensions["A"].width = 130


def main():
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
    input_sheet(wb, "Inputs_Clinical", "Clinical inputs (survival)", CLINICAL)
    input_sheet(wb, "Inputs_Costs", "Cost inputs", COSTS)
    input_sheet(wb, "Inputs_Utilities", "Utility inputs", UTILITIES)
    trace_sheet(wb, "int")
    trace_sheet(wb, "comp")
    results_sheet(wb)
    psa_sheet(wb)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
