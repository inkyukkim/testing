"""Generate fixtures/adaptation_input_KR.xlsx: synthetic Korean adaptation inputs.

Run:  python scripts/build_adaptation_input_kr.py
All values are SYNTHETIC. The layout deliberately differs from the global model so the
Input Mapper has real mapping decisions to make: per-vial prices, a reimbursement limit
in years rather than doses, monthly state costs, a life table published as central death
rates (mx, not qx) ending at an open 100+ band, renamed subsequent-therapy categories,
missing items (terminal care cost, AE disutility, general-population utility norms), and
an exchange rate and co-payment rate that are informational only.
Each row (or life-table column) carries a stable item_id so every mapped number has a
traceable source cell.
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synthetic_data import KR_LT_AGES, KR_MX_FEMALE, KR_MX_MALE  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "adaptation_input_KR.xlsx"
HEAD = Font(bold=True)
TITLE = Font(bold=True, size=14)
FILL = PatternFill("solid", fgColor="FFF2CC")

COLS = ["item_id", "Item", "Value", "Unit", "Source (synthetic)", "Note"]

SETTINGS = [
    ("KR-S01", "Country", "Republic of Korea", "text", "-", ""),
    ("KR-S02", "Currency", "KRW", "ISO 4217", "-", "Report in KRW; no conversion from GBP"),
    ("KR-S03", "Price year", 2025, "year", "-", ""),
    ("KR-S04", "Perspective", "Healthcare system (NHIS insurer plus patient out-of-pocket)", "text",
     "Synthetic HIRA-style guideline", "Total cost regardless of payer"),
    ("KR-S05", "Discount rate, costs", 0.045, "per annum", "Synthetic HIRA-style guideline", "Verify against current guideline"),
    ("KR-S06", "Discount rate, outcomes", 0.045, "per annum", "Synthetic HIRA-style guideline", "Verify against current guideline"),
    ("KR-S07", "Reference ICER threshold", 50000000, "KRW per QALY", "Synthetic",
     "No official threshold; reference value only"),
    ("KR-S08", "Time horizon", "Lifetime", "text", "-", "Retain global lifetime horizon"),
    ("KR-S09", "Reference exchange rate", 1750, "KRW per GBP", "Synthetic",
     "For information only. Do NOT use to convert global inputs."),
]

POPULATION = [
    ("KR-P01", "Mean body weight, adults with advanced disease", 64.5, "kg", "Synthetic KR cancer registry", ""),
    ("KR-P02", "SD of body weight", 11.8, "kg", "Synthetic KR cancer registry", ""),
    ("KR-P03", "Proportion male", None, "proportion", "-", "Not supplied; trial population assumed"),
]

COSTS = [
    ("KR-C01", "Drug A price per vial (100 mg)", 1050000, "KRW per vial", "Synthetic HIRA drug list", "List price"),
    ("KR-C02", "Drug A dose", 2, "mg/kg", "Synthetic Korean label", "No vial sharing"),
    ("KR-C03", "Drug A vial size", 100, "mg", "Synthetic Korean label", ""),
    ("KR-C04", "Drug A dosing schedule", "Q3W", "text", "Synthetic Korean label", ""),
    ("KR-C05", "Drug A reimbursed treatment duration (maximum)", 2, "years", "Synthetic reimbursement criteria", ""),
    ("KR-C06", "Drug B price per vial (100 mg)", 84000, "KRW per vial", "Synthetic HIRA drug list", ""),
    ("KR-C07", "Drug B dosing schedule", "500 mg flat, Q3W, maximum 6 cycles", "text", "Synthetic", ""),
    ("KR-C08", "Chemotherapy infusion fee per visit", 95000, "KRW per administration", "Synthetic fee schedule", "Applies to both arms"),
    ("KR-C09", "Progression-free state cost", 600000, "KRW per month (30.4375 days)", "Synthetic claims analysis", ""),
    ("KR-C10", "Progressed disease state cost", 1050000, "KRW per month (30.4375 days)", "Synthetic claims analysis", ""),
    ("KR-C11", "Terminal care cost", None, "KRW (one-off)", "-", "Not available; local study pending"),
    ("KR-C12", "Drug A adverse event cost (one-off)", 1600000, "KRW", "Synthetic", ""),
    ("KR-C13", "Drug B adverse event cost (one-off)", 3100000, "KRW", "Synthetic", ""),
    ("KR-C14", "Patient co-payment rate (cancer)", 0.05, "proportion", "Synthetic",
     "Informational; perspective counts total cost"),
    ("KR-C15", "Risk-sharing agreement applied in this submission", "None (list prices)", "text", "Synthetic", ""),
]

SUBSEQUENT = [
    ("KR-T01", "Course cost: docetaxel", 3900000, "KRW per course", "Synthetic claims analysis", "Drug + administration"),
    ("KR-T02", "Course cost: immune checkpoint inhibitor", 38000000, "KRW per course", "Synthetic claims analysis", ""),
    ("KR-T03", "Course cost: other targeted agents", 21000000, "KRW per course", "Synthetic claims analysis", ""),
    ("KR-T04", "After Drug A: share receiving docetaxel", 0.55, "proportion of progressors", "Synthetic KR expert panel", ""),
    ("KR-T05", "After Drug A: share receiving immune checkpoint inhibitor", 0.0, "proportion of progressors",
     "Synthetic KR expert panel", "IO re-treatment not reimbursed"),
    ("KR-T06", "After Drug A: share receiving other targeted agents", 0.08, "proportion of progressors", "Synthetic KR expert panel", ""),
    ("KR-T07", "After Drug B: share receiving docetaxel", 0.35, "proportion of progressors", "Synthetic KR expert panel", ""),
    ("KR-T08", "After Drug B: share receiving immune checkpoint inhibitor", 0.25, "proportion of progressors", "Synthetic KR expert panel", ""),
    ("KR-T09", "After Drug B: share receiving other targeted agents", 0.06, "proportion of progressors", "Synthetic KR expert panel", ""),
]

UTILITIES = [
    ("KR-U01", "Utility, progression-free", 0.80, "-", "Synthetic EQ-5D-5L, Korean value set", ""),
    ("KR-U02", "Utility, progressed disease", 0.66, "-", "Synthetic EQ-5D-5L, Korean value set", ""),
    ("KR-U03", "AE disutility", None, "QALY", "-", "No local estimate"),
    ("KR-U04", "General-population utility norms by age and sex", None, "-", "-", "Korean norms not supplied"),
]


def sheet(wb, title, heading, rows):
    ws = wb.create_sheet(title)
    ws["A1"] = heading
    ws["A1"].font = TITLE
    for j, h in enumerate(COLS, 1):
        ws.cell(row=3, column=j, value=h).font = HEAD
    for i, row in enumerate(rows, start=4):
        for j, v in enumerate(row, 1):
            ws.cell(row=i, column=j, value=v)
        ws.cell(row=i, column=3).fill = FILL
    for col, w in zip("ABCDEF", (10, 56, 18, 30, 36, 50)):
        ws.column_dimensions[col].width = w


def life_table(wb):
    ws = wb.create_sheet("LifeTable_KR")
    ws["A1"] = "Complete life table 2024 (synthetic, KOSIS-style): central death rate mx by single year of age"
    ws["A1"].font = TITLE
    ws["A2"] = "Source: synthetic. Ages 100 and over are reported as one open band."
    ws["A4"], ws["B4"], ws["C4"] = "item_id", "KR-L01", "KR-L02"
    ws["A5"], ws["B5"], ws["C5"] = "Age", "mx male", "mx female"
    for c in ("A4", "B4", "C4", "A5", "B5", "C5"):
        ws[c].font = HEAD
    for i, (age, mm, mf) in enumerate(zip(KR_LT_AGES, KR_MX_MALE, KR_MX_FEMALE), start=6):
        ws.cell(row=i, column=1, value="100+" if age == KR_LT_AGES[-1] else age)
        ws.cell(row=i, column=2, value=mm).fill = FILL
        ws.cell(row=i, column=3, value=mf).fill = FILL
    for col, w in zip("ABC", (10, 14, 14)):
        ws.column_dimensions[col].width = w


def main():
    wb = Workbook()
    ws = wb.active
    ws.title = "Overview"
    for i, t in enumerate([
        "Korean adaptation inputs: SYNTHETIC FIXTURE",
        "All data are synthetic and for software testing only.",
        "Submitted by local affiliate for adaptation of the global PartSA model (Drug A vs Drug B).",
        "Clinical efficacy (survival, time on treatment, dose intensity): retain global values; not supplied here.",
        "Values are in local units as supplied; mapping to model inputs is done by the Input Mapper.",
    ], start=1):
        ws.cell(row=i, column=1, value=t)
    ws["A1"].font = TITLE
    ws.column_dimensions["A"].width = 100
    sheet(wb, "Settings_KR", "Settings", SETTINGS)
    sheet(wb, "Population_KR", "Population", POPULATION)
    sheet(wb, "Costs_KR", "Costs", COSTS)
    sheet(wb, "SubsequentTx_KR", "Subsequent therapy mix and costs", SUBSEQUENT)
    sheet(wb, "Utilities_KR", "Utilities", UTILITIES)
    life_table(wb)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
