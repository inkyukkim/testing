"""Deterministic tool: score a candidate mapping spec against an answer key.

    evaluate(candidate, key) -> {"agreement": float, "critical": [...], "differences": [...]}
CLI: python -m tools.eval_mapping <candidate.json> <key.json> [<candidate_register> <key_register>]
     exit 0 if no critical finding

Gap ids are labels chosen by whoever wrote the register, so they are never compared as
strings. With both registers, the gap an input points to is compared by its class and
handling; without them, only the presence of a gap reference is compared.

Critical findings are the errors that would let a wrong number into an adapted model:
a key gap that the candidate fills, a key-retained input that the candidate maps from a
different local item, and any input missing from the candidate. Other differences
(rationale wording aside) lower the agreement score and are listed for review.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

COMPARED = ("status", "operation", "gap_id", "basis")
ARG_KEYS = ("source", "period", "rule", "interval_weeks_from", "method", "open_band")


def _index(spec):
    return {m["target"]: m for m in spec["mappings"]}


def _gap_view(m, register):
    gid = m.get("gap_id")
    if gid is None:
        return None
    if register is None:
        return "gap"
    g = next((g for g in register.get("gaps", []) if g["gap_id"] == gid), None)
    return (g["class"], g["handling"]) if g else ("missing", gid)


def evaluate(candidate: dict, key: dict, cand_register: dict | None = None, key_register: dict | None = None) -> dict:
    cand, ref = _index(candidate), _index(key)
    critical, diffs, agree = [], [], 0
    for t, k in ref.items():
        c = cand.get(t)
        if c is None:
            critical.append(f"{t}: missing from candidate")
            continue
        if k["status"] == "gap" and c["status"] != "gap":
            critical.append(f"{t}: key has gap {k.get('gap_id')}, candidate fills it ({c['status']}/{c.get('operation')})")
            continue
        fields = [(f, k.get(f), c.get(f)) for f in COMPARED if f != "gap_id"]
        fields.append(("gap", _gap_view(k, key_register), _gap_view(c, cand_register)))
        fields += [(f"args.{a}", k.get("args", {}).get(a), c.get("args", {}).get(a)) for a in ARG_KEYS]
        bad = [(f, kv, cv) for f, kv, cv in fields if kv != cv]
        if k["status"] == "retained" and c["status"] == "mapped":
            critical.append(f"{t}: key retains the global value, candidate maps it from {c.get('args', {}).get('source')}")
        if bad:
            diffs.append({"target": t, "fields": [{"field": f, "key": kv, "candidate": cv} for f, kv, cv in bad]})
        else:
            agree += 1
    extra = sorted(set(cand) - set(ref))
    critical += [f"{t}: not an input in the key" for t in extra]
    ku = {u["item"] for u in key.get("unused_local_items", [])}
    cu = {u["item"] for u in candidate.get("unused_local_items", [])}
    if ku != cu:
        diffs.append({"target": "unused_local_items", "fields": [{"field": "items", "key": sorted(ku), "candidate": sorted(cu)}]})
    return {"agreement": agree / len(ref), "n_targets": len(ref), "critical": critical, "differences": diffs}


def main() -> int:
    regs = [yaml.safe_load(Path(p).read_text()) for p in sys.argv[3:5]] if len(sys.argv) >= 5 else [None, None]
    res = evaluate(json.loads(Path(sys.argv[1]).read_text()), json.loads(Path(sys.argv[2]).read_text()), *regs)
    print(json.dumps(res, indent=2))
    return 1 if res["critical"] else 0


if __name__ == "__main__":
    sys.exit(main())
