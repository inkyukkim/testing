import sys
from tools.workbook_io import read_named
g=read_named(sys.argv[1]); l=read_named(sys.argv[2])
for k in sorted(set(g)|set(l)):
    gv=g.get(k); lv=l.get(k)
    if isinstance(gv,list) or isinstance(lv,list):
        print(k,'[vector]'); continue
    print(k, gv, '|', lv)
