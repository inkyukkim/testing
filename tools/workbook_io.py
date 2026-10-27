"""Deterministic tool: read and write workbook values by defined name.

Portable contract (Input Mapper, Builder/Runner, Model Verifier, Claims Analyst):
    list_names(xlsx)                       -> {name: (sheet, cell)}
    read_named(xlsx, names=None)           -> {name: value}   (cached values; recalc first)
    write_named(src, dst, overrides)       -> writes constants into named input cells only

Equivalent in VBA: ThisWorkbook.Names(name).RefersToRange.Value.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

_REF = re.compile(r"^'?(?P<sheet>[^'!]+)'?!\$?(?P<col>[A-Z]+)\$?(?P<row>\d+)$")


def list_names(xlsx: str | Path) -> dict[str, tuple[str, str]]:
    wb = openpyxl.load_workbook(xlsx, read_only=False)
    out = {}
    for name, dn in wb.defined_names.items():
        m = _REF.match(dn.attr_text)
        if not m:
            raise ValueError(f"Defined name {name!r} is not a single-cell reference: {dn.attr_text}")
        out[name] = (m["sheet"], f"{m['col']}{m['row']}")
    return out


def read_named(xlsx: str | Path, names=None, data_only: bool = True) -> dict[str, object]:
    refs = list_names(xlsx)
    wb = openpyxl.load_workbook(xlsx, data_only=data_only)
    keys = refs if names is None else names
    return {n: wb[refs[n][0]][refs[n][1]].value for n in keys}


def write_named(src: str | Path, dst: str | Path, overrides: dict[str, object]) -> Path:
    """Write constants into named cells. Refuses to overwrite a formula cell."""
    refs = list_names(src)
    wb = openpyxl.load_workbook(src)
    for name, value in overrides.items():
        if name not in refs:
            raise KeyError(f"Unknown named range: {name}")
        cell = wb[refs[name][0]][refs[name][1]]
        if isinstance(cell.value, str) and cell.value.startswith("="):
            raise ValueError(f"{name} is a calculated cell; inputs only")
        cell.value = value
    wb.save(dst)
    return Path(dst)


if __name__ == "__main__":
    import sys
    print(json.dumps(read_named(sys.argv[1]), indent=2, default=str))
