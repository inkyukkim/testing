"""Record the recalculated base-case results of the global model as the regression baseline.

Run deliberately (never from tests) after an intended model change:
    python scripts/rebaseline.py
The values are copied from LibreOffice-recalculated cells; nothing is typed by hand.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.recalc import recalc  # noqa: E402
from tools.workbook_io import read_named  # noqa: E402

MODEL = ROOT / "fixtures" / "global_model.xlsx"
OUT = ROOT / "fixtures" / "baseline.json"
KEYS = ["res_icer", "res_icer_ly", "res_inc_total_cost", "res_inc_qaly_disc", "res_inc_ly_disc", "res_inc_nmb",
        "res_int_total_cost", "res_comp_total_cost", "res_int_qaly_disc", "res_comp_qaly_disc"]


def main():
    previous = json.loads(OUT.read_text()) if OUT.exists() else None
    with tempfile.TemporaryDirectory() as tmp:
        values = read_named(recalc(MODEL, tmp))
    history = (previous or {}).get("history", [])
    if previous:
        history.append({"label": previous["label"], "res_icer": previous["values"]["res_icer"]})
    label = sys.argv[1] if len(sys.argv) > 1 else "unlabelled"
    OUT.write_text(json.dumps({"label": label, "model": "fixtures/global_model.xlsx",
                               "conventions": "fixtures/global_model.conventions.yaml",
                               "values": {k: values[k] for k in KEYS}, "history": history}, indent=2) + "\n")
    print(f"wrote {OUT}: res_icer = {values['res_icer']!r}")


if __name__ == "__main__":
    main()
