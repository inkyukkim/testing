"""Generate fixtures/adaptation_input_KR.xlsx: synthetic Korean adaptation inputs.

Run:  python scripts/build_adaptation_input_kr.py
All values are SYNTHETIC. The layout deliberately differs from the global model so the
Input Mapper has real mapping decisions to make (units, per-vial pricing, monthly state
costs, a missing item, an informational-only exchange rate and co-payment rate).
Each row carries a stable item_id so every mapped number has a traceable source cell.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

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

COSTS = [
    ("KR-C01", "Drug A price per vial (100 mg)", 1050000, "KRW per vial", "Synthetic HIRA drug list", ""),
    ("KR-C02", "Drug A dose per administration", 200, "mg (flat dose)", "Synthetic label", "No vial sharing"),
    ("KR-C03", "Drug A vial size", 100, "mg", "Synthetic label", ""),
    ("KR-C04", "Drug A dosing schedule", "Q3W", "text", "Synthetic label", ""),
    ("KR-C05", "Drug A reimbursed treatment duration (maximum)", 2, "years", "Synthetic reimbursement criteria", ""),
    ("KR-C06", "Drug B acquisition cost per administration", 420000, "KRW per administration", "Synthetic HIRA drug list", ""),
    ("KR-C07", "Drug B dosing schedule", "Q3W, maximum 6 cycles", "text", "Synthetic", ""),
    ("KR-C08", "Chemotherapy infusion fee per visit", 95000, "KRW per administration", "Synthetic fee schedule", "Applies to both arms"),
    ("KR-C09", "Progression-free state cost", 600000, "KRW per month (30.4375 days)", "Synthetic claims analysis", ""),
    ("KR-C10", "Progressed disease state cost", 1050000, "KRW per month (30.4375 days)", "Synthetic claims analysis", ""),
    ("KR-C11", "Terminal care cost", None, "KRW (one-off)", "-", "Not available; local study pending"),
    ("KR-C12", "Drug A adverse event cost (one-off)", 1600000, "KRW", "Synthetic", ""),
    ("KR-C13", "Drug B adverse event cost (one-off)", 3100000, "KRW", "Synthetic", ""),
    ("KR-C14", "Patient co-payment rate (cancer)", 0.05, "proportion", "Synthetic",
     "Informational; perspective counts total cost"),
]

UTILITIES = [
    ("KR-U01", "Utility, progression-free", 0.80, "-", "Synthetic EQ-5D-5L, Korean value set", ""),
    ("KR-U02", "Utility, progressed disease", 0.66, "-", "Synthetic EQ-5D-5L, Korean value set", ""),
    ("KR-U03", "AE disutility", None, "QALY", "-", "No local estimate"),
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
    for col, w in zip("ABCDEF", (10, 50, 18, 30, 36, 50)):
        ws.column_dimensions[col].width = w


def main():
    wb = Workbook()
    ws = wb.active
    ws.title = "Overview"
    for i, t in enumerate([
        "Korean adaptation inputs: SYNTHETIC FIXTURE",
        "All data are synthetic and for software testing only.",
        "Submitted by local affiliate for adaptation of the global PartSA model (Drug A vs Drug B).",
        "Clinical efficacy (survival) inputs: retain global values; not supplied here.",
        "Values are in local units as supplied; mapping to model inputs is done by the Input Mapper.",
    ], start=1):
        ws.cell(row=i, column=1, value=t)
    ws["A1"].font = TITLE
    ws.column_dimensions["A"].width = 100
    sheet(wb, "Settings_KR", "Settings", SETTINGS)
    sheet(wb, "Costs_KR", "Costs", COSTS)
    sheet(wb, "Utilities_KR", "Utilities", UTILITIES)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
