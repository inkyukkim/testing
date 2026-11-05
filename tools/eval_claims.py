"""Deterministic tool: score a Claims Analyst register against an answer key.

    evaluate(candidate, key, blocks, global_contexts, local_contexts) -> scores
Claims are matched when they sit in the same block and their excerpts overlap (character
spans in the block text); a block with one claim on each side also matches. For matched
pairs: kind, action, and truth-equivalence of the expressions on the global and the local
model (same truth value; both non-evaluable counts as agreement).
Critical findings: a key claim with an evaluable expression whose candidate has none (a
numeric claim left unchecked), a removed claim kept with rerender/regenerate, an untraceable
assertion not sent to human review, and any validator error (tools.claims.validate).
"""
from __future__ import annotations

from tools.claims import validate
from tools.evaluate_claim import evaluate as eval_expr


def _span(block_text, excerpt):
    i = block_text.find(excerpt)
    return (i, i + len(excerpt)) if i >= 0 else None


def _truth(expr, ctx):
    try:
        return eval_expr(expr, ctx)["truth"]
    except Exception as e:  # noqa: BLE001 - an unevaluable candidate expression is a finding, not a crash
        return f"error: {e}"


def evaluate(candidate, key, blocks, global_contexts, local_contexts) -> dict:
    cand, ref = candidate["claims"], key["claims"]
    pairs, used = [], set()
    for k in ref:
        kt = blocks[k["block"]]["text"]
        ks = _span(kt, k["excerpt"])
        same_block = [c for c in cand if c.get("block") == k["block"] and id(c) not in used]
        match = None
        for c in same_block:
            cs = _span(kt, c.get("excerpt", ""))
            if ks and cs and cs[0] < ks[1] and ks[0] < cs[1]:
                match = c
                break
        if match is None and len(same_block) == 1 and sum(r["block"] == k["block"] for r in ref) == 1:
            match = same_block[0]
        if match is not None:
            used.add(id(match))
        pairs.append((k, match))
    matched = [(k, c) for k, c in pairs if c is not None]
    critical, rows = [], []
    kind_ok = action_ok = truth_ok = 0
    for k, c in matched:
        kinds = k["kind"] == c.get("kind")
        acts = k["action"] == c.get("action")
        tg = (_truth(k["expression"], global_contexts), _truth(c.get("expression"), global_contexts))
        tl = (_truth(k["expression"], local_contexts), _truth(c.get("expression"), local_contexts))
        truths = tg[0] == tg[1] and tl[0] == tl[1]
        kind_ok += kinds
        action_ok += acts
        truth_ok += truths
        if k["expression"] and k["expression"].get("op") != "external" and not c.get("expression"):
            critical.append(f"{k['claim_id']}: key claim is evaluable; candidate {c.get('claim_id')} has no expression")
        if k["action"] == "remove" and c.get("action") in ("rerender", "regenerate"):
            critical.append(f"{k['claim_id']}: removed in key, candidate keeps it ({c.get('action')})")
        if k["kind"] == "external_assertion_untraceable" and c.get("action") != "human_review":
            critical.append(f"{k['claim_id']}: untraceable assertion not sent to human review")
        if not (kinds and acts and truths):
            rows.append({"key": k["claim_id"], "candidate": c.get("claim_id"), "block": k["block"],
                         "kind": [k["kind"], c.get("kind")], "action": [k["action"], c.get("action")],
                         "truth_global": list(tg), "truth_local": list(tl)})
    missed = [k["claim_id"] for k, c in pairs if c is None]
    extra = [c.get("claim_id") for c in cand if id(c) not in used]
    errors = validate(candidate, blocks)
    critical += [f"validator: {e}" for e in errors]
    n = len(matched) or 1
    return {"key_claims": len(ref), "candidate_claims": len(cand), "matched": len(matched),
            "recall": len(matched) / len(ref), "precision": len(matched) / len(cand) if cand else 0.0,
            "kind_agreement": kind_ok / n, "action_agreement": action_ok / n, "truth_agreement": truth_ok / n,
            "missed_key_claims": missed, "extra_candidate_claims": extra, "critical": critical, "differences": rows}
