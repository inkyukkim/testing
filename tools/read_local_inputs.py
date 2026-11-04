"""Deterministic tool: read a local adaptation input workbook by item_id.

Portable contract (Input Mapper, apply_mapping):
    read_local_inputs(xlsx) -> {item_id: {value, unit, item, sheet, cell, source, note}}
Row items: sheets whose row 3 header is item_id | Item | Value | Unit | Source | Note.
Vector items (life tables): an 'item_id' row whose cells name column ids, followed by a
header row and one row per age; value is the list, 'ages' the first-column labels.
Equivalent in VBA: loop UsedRange rows; in R: readxl + tidy.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import openpyxl

ROW_HEADER = ["item_id", "Item", "Value", "Unit"]


def read_local_inputs(xlsx: str | Path) -> dict[str, dict]:
    wb = openpyxl.load_workbook(xlsx)
    items: dict[str, dict] = {}

    def add(item_id, entry):
        if item_id in items:
            raise ValueError(f"duplicate item_id {item_id}")
        items[item_id] = entry

    for ws in wb.worksheets:
        header = [c.value for c in ws[3]][:4] if ws.max_row >= 3 else []
        if header == ROW_HEADER:
            cols = [c.value for c in ws[3]]
            for row in ws.iter_rows(min_row=4):
                if row[0].value is None:
                    continue
                rec = {cols[j]: row[j].value for j in range(len(cols))}
                add(rec["item_id"], {"value": rec["Value"], "unit": rec["Unit"], "item": rec["Item"],
                                     "sheet": ws.title, "cell": row[2].coordinate,
                                     "source": rec.get("Source (synthetic)"), "note": rec.get("Note")})
            continue
        for r in range(1, min(ws.max_row, 10) + 1):
            if ws.cell(row=r, column=1).value == "item_id":
                label_row, first = r + 1, r + 2
                last = ws.max_row
                ages = [ws.cell(row=i, column=1).value for i in range(first, last + 1)]
                for c in range(2, ws.max_column + 1):
                    iid = ws.cell(row=r, column=c).value
                    if not iid:
                        continue
                    col = openpyxl.utils.get_column_letter(c)
                    add(iid, {"value": [ws.cell(row=i, column=c).value for i in range(first, last + 1)],
                              "ages": ages, "unit": ws.cell(row=label_row, column=c).value,
                              "item": f"{ws.title}: {ws.cell(row=label_row, column=c).value}",
                              "sheet": ws.title, "cell": f"{col}{first}:{col}{last}", "source": None, "note": None})
                break
    return items


if __name__ == "__main__":
    print(json.dumps(read_local_inputs(sys.argv[1]), indent=2, default=str))
