"""Scratch analysis of work/model_profile.json (read-only)."""
import json
d = json.load(open('work/model_profile.json'))
names, deps = d['names'], d['input_dependencies']
inputs = {n for n, e in names.items() if e['role'] == 'input'}
print("== cross-arm dependencies")
for n, ds in sorted(deps.items()):
    if n.startswith(('res_int_', 'calc_int_')):
        x = [i for i in ds if i.startswith('comp_')]
        if x: print(n, '<- comp inputs', x)
    if n.startswith(('res_comp_', 'calc_comp_')):
        x = [i for i in ds if i.startswith('int_')]
        if x: print(n, '<- int inputs', x)
print("== non-input names with no input deps")
for n, ds in sorted(deps.items()):
    if not ds: print(n, names[n]['role'])
print("== inputs used by no derived/output name")
used = set().union(*map(set, deps.values()))
for n in sorted(inputs - used): print(n)
print("== asymmetric arm deps (int vs comp, after renaming prefix)")
for n in sorted(deps):
    if n.startswith('res_int_'):
        m = 'res_comp_' + n[8:]
        if m in deps:
            a = {i.replace('int_', 'X_', 1) if i.startswith('int_') else i for i in deps[n]}
            b = {i.replace('comp_', 'X_', 1) if i.startswith('comp_') else i for i in deps[m]}
            if a != b: print(n, 'only-int:', sorted(a-b), 'only-comp:', sorted(b-a))
