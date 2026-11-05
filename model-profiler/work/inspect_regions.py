"""Scratch: inspect formula regions via tools.profile_workbook.Workbook (reads formulas, no recalculation)."""
import sys
from tools.profile_workbook import Workbook
from openpyxl.utils import get_column_letter as L
W = Workbook('fixtures/model.xlsx')
def regs(sheet):
    return {(L(r['col']), tuple(r['rows'])): r for r in W.regions.values() if r['sheet'] == sheet}
a, b = regs('Trace_Int'), regs('Trace_Comp')
print("== regions only in one trace sheet, or differing signature")
for k in sorted(set(a) | set(b)):
    ra, rb = a.get(k), b.get(k)
    if ra is None or rb is None:
        r = ra or rb
        print('only', r['sheet'], r['id'], 'rows', r['rows'], r['formula'][:160])
    elif ra['sig'].replace('int_', 'X_') != rb['sig'].replace('comp_', 'X_'):
        print('diff', k, '\n  INT ', ra['formula'][:200], '\n  COMP', rb['formula'][:200])
print("== specific cells")
for ref in sys.argv[1:]:
    s, c = ref.split('!')
    print(ref, repr(W.wb[s][c].value))
