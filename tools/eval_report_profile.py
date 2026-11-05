"""Deterministic tool: score a Report Profiler output against the report's provenance key.

    evaluate(profile, provenance, base_values, scenario_values=None) -> scores
A resolution is correct when (name, context) equals the key, or when the key's cell has the
same value in the base case and the agent chose (name, "base") (indistinguishable on display).
"""
from __future__ import annotations


def evaluate(profile: dict, provenance: dict, base_values: dict, tokens: list, candidates: list) -> dict:
    key = provenance["numbers"]
    got = {n["token_index"]: n for n in profile.get("numerals", [])}
    rows, correct, invalid, unresolved, amb_total, amb_correct = [], 0, 0, 0, 0, 0
    for i, (k, t, c) in enumerate(zip(key, tokens, candidates)):
        g = got.get(i)
        kn, kc = k["source"]["name"], k["source"]["scenario"] or "base"
        if g is None or g.get("name") is None:
            unresolved += 1
            ok = False
        else:
            in_cands = any(x["name"] == g["name"] and x["context"] == g.get("context", "base") for x in c["candidates"])
            invalid += 0 if in_cands else 1
            ok = (g["name"], g.get("context", "base")) == (kn, kc) or (
                g["name"] == kn and g.get("context", "base") == "base" and base_values.get(kn) == k["value"])
        correct += ok
        if c["status"] == "ambiguous":
            amb_total += 1
            amb_correct += ok
        if not ok:
            rows.append({"token_index": i, "token": t["token"], "key": f"{kn}@{kc}",
                         "agent": None if g is None else f"{g.get('name')}@{g.get('context', 'base')}"})
    n = len(key)
    return {"n": n, "accuracy": correct / n, "ambiguous_accuracy": amb_correct / amb_total if amb_total else None,
            "n_ambiguous": amb_total, "unresolved": unresolved, "not_a_candidate": invalid,
            "entries": len(profile.get("numerals", [])), "errors": rows}
