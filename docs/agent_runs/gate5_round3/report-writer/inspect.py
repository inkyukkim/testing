import json
from tools.workbook_io import read_named, list_names
from tools.profile_workbook import profile
from tools.claims import evaluate_register
p="runs/kr_test/recalc/adapted_model.xlsx"
v=read_named(p)
for k,x in v.items():
    if isinstance(x,list): x=f"list[{len(x)}]"
    print(k, repr(x)[:60])
pr=profile(p)["names"]
print("---labels")
for n,e in pr.items():
    if e["role"]=="input": print(n,"|",(e.get("metadata") or {}).get("Parameter"))
ctx={"base":v}
r=evaluate_register(json.load(open("approved/claims_register.json")),None,ctx)
for c in r["claims"]:
    if c["claim_id"] in("C15","C16"): print(c["evidence_local"])
