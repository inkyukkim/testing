"""Deterministic tool: evaluate a claim expression against model values (Claims Analyst).

    evaluate(expr, contexts) -> {"truth": True | False | "not_evaluable" | "pending", "evidence": {...}}
contexts: {"base": {name: value}, "<scenario id>": {...}}. A missing context gives "pending".

Expressions reference cells only: "name" (base) or "name@SC4" (scenario); {"registry": key}
for constants in tools/constants_registry.yaml; {"text": "Yes"} for text values. A numeric
literal anywhere in an expression is rejected: truth must come from cells, not from prose.

    {"op": "le" | "lt" | "ge" | "gt" | "eq" | "ne", "lhs": ref, "rhs": ref}
    {"op": "sign", "ref": ref, "sign": "positive" | "negative" | "zero"}
    {"op": "argmax" | "argmin", "refs": [ref, ...], "expect": ref}
    {"op": "rank_abs_change", "refs": [...], "base": ref, "expect_order": [ref, ...]}   # top of ranking
    {"op": "select", "refs": [...], "where": <predicate with "lhs" omitted>, "expect": [ref, ...]}
    {"op": "rel_change_below", "a": ref, "b": ref, "tol": {"registry": key}}
    {"op": "all" | "any", "of": [expr, ...]}
    {"op": "external"}                                                                  # not evaluable
"""
from __future__ import annotations

from pathlib import Path

import yaml

REGISTRY = yaml.safe_load((Path(__file__).with_name("constants_registry.yaml")).read_text())
CMP = {"le": lambda a, b: a <= b, "lt": lambda a, b: a < b, "ge": lambda a, b: a >= b,
       "gt": lambda a, b: a > b, "eq": lambda a, b: a == b, "ne": lambda a, b: a != b}


class Pending(Exception):
    pass


def check_no_literals(expr, path="$"):
    if isinstance(expr, bool):
        return
    if isinstance(expr, (int, float)):
        raise ValueError(f"{path}: numeric literal {expr!r}; reference a cell or registry key")
    if isinstance(expr, dict):
        for k, v in expr.items():
            check_no_literals(v, f"{path}.{k}")
    elif isinstance(expr, list):
        for i, v in enumerate(expr):
            check_no_literals(v, f"{path}[{i}]")


def _value(ref, contexts, evidence):
    if isinstance(ref, dict):
        if set(ref) == {"registry"}:
            return REGISTRY["constants"][ref["registry"]]
        if set(ref) == {"text"}:
            return ref["text"]
        raise ValueError(f"bad reference {ref!r}")
    name, _, ctx = ref.partition("@")
    ctx = ctx or "base"
    if ctx not in contexts:
        raise Pending(ctx)
    if name not in contexts[ctx]:
        raise KeyError(f"{ref}: no such name")
    v = contexts[ctx][name]
    evidence[ref] = v
    return v


def _pred(pred, lhs_ref, contexts, evidence):
    if pred["op"] == "sign":
        v = _value(lhs_ref, contexts, evidence)
        return {"positive": v > 0, "negative": v < 0, "zero": v == 0}[pred["sign"]]
    return CMP[pred["op"]](_value(lhs_ref, contexts, evidence), _value(pred["rhs"], contexts, evidence))


def _eval(e, contexts, evidence):
    op = e["op"]
    if op in CMP:
        return CMP[op](_value(e["lhs"], contexts, evidence), _value(e["rhs"], contexts, evidence))
    if op == "sign":
        return _pred(e, e["ref"], contexts, evidence)
    if op in ("argmax", "argmin"):
        vals = {r: _value(r, contexts, evidence) for r in e["refs"]}
        pick = (max if op == "argmax" else min)(vals, key=vals.get)
        evidence[f"{op}"] = pick
        return pick == e["expect"]
    if op == "rank_abs_change":
        b = _value(e["base"], contexts, evidence)
        vals = {r: abs(_value(r, contexts, evidence) - b) for r in e["refs"]}
        order = sorted(vals, key=vals.get, reverse=True)
        evidence["ranking"] = order
        return order[:len(e["expect_order"])] == e["expect_order"]
    if op == "select":
        chosen = [r for r in e["refs"] if _pred(e["where"], r, contexts, evidence)]
        evidence["selected"] = chosen
        return chosen == e["expect"]
    if op == "rel_change_below":
        a, b = _value(e["a"], contexts, evidence), _value(e["b"], contexts, evidence)
        return abs(a - b) / abs(b) < _value(e["tol"], contexts, evidence)
    if op in ("all", "any"):
        results = [_eval(x, contexts, evidence) for x in e["of"]]
        return all(results) if op == "all" else any(results)
    raise ValueError(f"unknown op {op!r}")


def evaluate(expr, contexts) -> dict:
    if expr is None or expr.get("op") == "external":
        return {"truth": "not_evaluable", "evidence": {}}
    check_no_literals(expr)
    evidence = {}
    try:
        return {"truth": bool(_eval(expr, contexts, evidence)), "evidence": evidence}
    except Pending as p:
        return {"truth": "pending", "evidence": {"missing_context": str(p)}}
