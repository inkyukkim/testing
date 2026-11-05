import json
from tools.claims import evaluate_register, ready, validate
from tools.workbook_io import read_named
ctx={"base":read_named("runs/kr_test/recalc/adapted_model.xlsx")}
r=evaluate_register(json.load(open("approved/claims_register.json")),None,ctx)
for c in r["claims"]:
    print(c["claim_id"],c["action"],c["truth_local"],json.dumps(c["evidence_local"])[:200])
print("validate",validate(r)); print("ready",ready(r))
