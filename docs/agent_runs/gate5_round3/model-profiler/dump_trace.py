"""Scratch: print header labels and row-20 formulas of a trace sheet, plus top parameter block."""
import sys, openpyxl
wb = openpyxl.load_workbook('fixtures/model.xlsx')
ws = wb[sys.argv[1]]
for r in range(1, 19):
    vals = [(c.coordinate, c.value) for c in ws[r] if c.value is not None]
    if vals: print(vals)
for c in ws[20]:
    if c.value is not None: print(c.column_letter, ws.cell(19, c.column).value, '|', c.value)
