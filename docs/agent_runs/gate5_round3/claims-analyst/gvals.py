import json
from pathlib import Path
from tools.recalc import recalc
from tools.scenario_runner import run_scenarios
from tools.workbook_io import read_named
g={"base": read_named(recalc("fixtures/global_model.xlsx", Path("work/claims_tmp")/"global"))}
g.update(run_scenarios("fixtures/global_model.xlsx","fixtures/scenarios_UK.yaml",Path("work/claims_tmp")/"global_scen"))
out={c:{k:v for k,v in d.items() if not isinstance(v,list)} for c,d in g.items()}
Path("work/global_values.json").write_text(json.dumps(out,indent=1,default=str))
for c,d in out.items():
    print(c, {k:d.get(k) for k in ["res_icer","res_inc_total_cost","res_inc_qaly_disc","res_inc_nmb","res_below_wtp"]})
