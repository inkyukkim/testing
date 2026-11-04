"""Deterministic tool: read and write workbook values by defined name.

Portable contract (Input Mapper, Builder/Runner, Model Verifier, Claims Analyst):
    list_names(xlsx)                       -> {name: (sheet, ref)}  ref = "C4" or "B4:B114"
    read_named(xlsx, names=None)           -> {name: value | [values]}  (cached values; recalc first)
    write_named(src, dst, overrides)       -> writes constants into named input cells only

Names are single cells or one-dimensional ranges (vectors, e.g. life tables).
Equivalent in VBA: ThisWorkbook.Names(name).RefersToRange.Value.
"""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path

import openpyxl
import openpyxl.cell._writer as _cell_writer

_REF = re.compile(r"^'?(?P<sheet>[^'!]+)'?!\$?(?P<c1>[A-Z]+)\$?(?P<r1>\d+)(?::\$?(?P<c2>[A-Z]+)\$?(?P<r2>\d+))?$")


def list_names(xlsx: str | Path) -> dict[str, tuple[str, str]]:
    wb = openpyxl.load_workbook(xlsx, read_only=False)
    out = {}
    for name, dn in wb.defined_names.items():
        m = _REF.match(dn.attr_text)
        if not m:
            raise ValueError(f"Defined name {name!r} is not a cell or range reference: {dn.attr_text}")
        ref = f"{m['c1']}{m['r1']}"
        if m["c2"]:
            if m["c1"] != m["c2"] and m["r1"] != m["r2"]:
                raise ValueError(f"Defined name {name!r} is not one-dimensional: {dn.attr_text}")
            ref += f":{m['c2']}{m['r2']}"
        out[name] = (m["sheet"], ref)
    return out


def _cells(ws, ref):
    if ":" not in ref:
        return ws[ref]
    return [c for row in ws[ref] for c in row]


def read_named(xlsx: str | Path, names=None, data_only: bool = True) -> dict[str, object]:
    refs = list_names(xlsx)
    wb = openpyxl.load_workbook(xlsx, data_only=data_only)
    keys = refs if names is None else names
    out = {}
    for n in keys:
        cells = _cells(wb[refs[n][0]], refs[n][1])
        out[n] = [c.value for c in cells] if isinstance(cells, list) else cells.value
    return out


@contextmanager
def exact_floats():
    """openpyxl serialises floats with '%.16g', dropping the 17th significant digit (one ULP),
    so a written value can differ from the computed one. Write floats with repr (shortest
    exact round-trip) while saving, then restore the library default."""
    original = _cell_writer.safe_string

    def safe_string(value):
        return repr(value) if isinstance(value, float) else original(value)

    _cell_writer.safe_string = safe_string
    try:
        yield
    finally:
        _cell_writer.safe_string = original


def write_named(src: str | Path, dst: str | Path, overrides: dict[str, object]) -> Path:
    """Write constants into named cells or vectors. Refuses to overwrite a formula cell."""
    refs = list_names(src)
    wb = openpyxl.load_workbook(src)
    for name, value in overrides.items():
        if name not in refs:
            raise KeyError(f"Unknown named range: {name}")
        cells = _cells(wb[refs[name][0]], refs[name][1])
        targets, values = (cells, list(value)) if isinstance(cells, list) else ([cells], [value])
        if len(targets) != len(values):
            raise ValueError(f"{name}: expected {len(targets)} values, got {len(values)}")
        for cell, v in zip(targets, values):
            if isinstance(cell.value, str) and cell.value.startswith("="):
                raise ValueError(f"{name} is a calculated cell; inputs only")
            cell.value = v
    with exact_floats():
        wb.save(dst)
    return Path(dst)


if __name__ == "__main__":
    import sys
    print(json.dumps(read_named(sys.argv[1]), indent=2, default=str))
