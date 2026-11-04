"""Deterministic tool: validate a gap register and decide whether the pipeline may proceed.

Portable contract (Input Mapper writes, human approves, Builder/Runner checks):
    validate(register) -> list of error strings (schema + cross-field rules R1-R6)
    gate(register)     -> GateResult(blocked, blocking_gap_ids, errors)
CLI: python -m tools.gap_register <register.yaml>   exit 0 = proceed, 2 = blocked, 1 = invalid

The schema lives in schemas/gap_register.schema.yaml. Only the JSON Schema keywords that
schema uses are implemented here (type, enum, required, properties, additionalProperties,
items, minItems, pattern), so the tool needs no third-party validator.
Equivalent in R: yaml + jsonvalidate; in VBA: parse the JSON form of the register.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "gap_register.schema.yaml"
ALLOWED_HANDLING = {
    "non_transferable": {"block"},
    "transferable": {"retain_tagged", "retain_flagged"},
    "partial": {"retain_flagged", "block"},
}
_TYPES = {"object": dict, "array": list, "string": str, "integer": int, "null": type(None)}


def load(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def _check(node, schema, path, errors):
    types = schema.get("type")
    if types is not None:
        types = types if isinstance(types, list) else [types]
        if not any(isinstance(node, _TYPES[t]) and not (t == "integer" and isinstance(node, bool)) for t in types):
            errors.append(f"{path}: expected {types}, got {type(node).__name__}")
            return
    if node is None:
        return
    if "enum" in schema and node not in schema["enum"]:
        errors.append(f"{path}: {node!r} not in {schema['enum']}")
    if "pattern" in schema and isinstance(node, str) and not re.search(schema["pattern"], node):
        errors.append(f"{path}: {node!r} does not match {schema['pattern']}")
    if isinstance(node, dict):
        for key in schema.get("required", []):
            if key not in node:
                errors.append(f"{path}: missing required '{key}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    errors.append(f"{path}: unexpected key '{key}'")
        for key, sub in props.items():
            if key in node:
                _check(node[key], sub, f"{path}.{key}", errors)
    if isinstance(node, list):
        if len(node) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(node):
                _check(item, schema["items"], f"{path}[{i}]", errors)


_NUMERAL = re.compile(r"(?<![A-Za-z_\-])\d+(?:[.,]\d+)?(?![A-Za-z_\d])")
_IDS = re.compile(r"\b(?:KR|GAP)-[A-Z]?\d+\b|\bE\d+\b|\bEQ-5D-[35]L\b|\b[A-Z]{1,4}\d+\b")


def _numerals(text: str) -> bool:
    return bool(_NUMERAL.search(_IDS.sub("", text or "")))


def validate_rules(register: dict) -> list[str]:
    errors, seen = [], set()
    for g in register.get("gaps", []):
        gid = g.get("gap_id", "?")
        if gid in seen:
            errors.append(f"{gid}: R6 duplicate gap_id")
        seen.add(gid)
        cls, handling = g.get("class"), g.get("handling")
        if cls in ALLOWED_HANDLING and handling not in ALLOWED_HANDLING[cls]:
            errors.append(f"{gid}: R1 class {cls} does not allow handling {handling}")
        if handling == "block" and not g.get("escalation_options"):
            errors.append(f"{gid}: R2 block requires escalation options")
        res = g.get("resolution")
        if g.get("status") == "resolved":
            options = {o.get("option_id") for o in g.get("escalation_options", [])}
            if not res:
                errors.append(f"{gid}: R3 resolved gap needs a resolution")
            else:
                if res.get("option_id") not in options:
                    errors.append(f"{gid}: R3 resolution option {res.get('option_id')} is not an escalation option")
                if (res.get("decided_by") or {}).get("kind") != "human":
                    errors.append(f"{gid}: R3 resolution must be decided by a human")
        if g.get("status") == "open" and res is not None:
            errors.append(f"{gid}: R4 open gap must have resolution null")
        if handling in ("retain_tagged", "retain_flagged") and not g.get("retained_source"):
            errors.append(f"{gid}: R5 {handling} requires retained_source")
        texts = [g.get("description"), g.get("rationale")] + [o.get("description") for o in g.get("escalation_options", [])]
        texts += list(g.get("prohibited_options", []))
        if any(_numerals(t) for t in texts if isinstance(t, str)):
            errors.append(f"{gid}: R7 numeral in free text; cite the item or name instead")
    return errors


def validate(register: dict, schema: dict | None = None) -> list[str]:
    errors: list[str] = []
    _check(register, schema or load(SCHEMA_PATH), "$", errors)
    return errors + validate_rules(register)


@dataclass
class GateResult:
    blocked: bool
    blocking: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def gate(register: dict) -> GateResult:
    errors = validate(register)
    blocking = [g["gap_id"] for g in register.get("gaps", [])
                if g.get("handling") == "block" and g.get("status") == "open"]
    return GateResult(blocked=bool(blocking or errors), blocking=blocking, errors=errors)


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    result = gate(load(argv[0]))
    for e in result.errors:
        print(f"INVALID: {e}")
    for gid in result.blocking:
        print(f"BLOCKED: {gid}")
    if result.errors:
        return 1
    return 2 if result.blocked else 0


if __name__ == "__main__":
    sys.exit(main())
