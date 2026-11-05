"""Deterministic tool: profile a formula-driven workbook (Model Profiler's evidence base).

Portable contract:
    profile(xlsx, conventions_yaml=None) -> dict   (written as model_profile.json)
CLI: python -m tools.profile_workbook <model.xlsx> [--conventions <yaml>] [--out <json>]

What it reports, without relying on naming conventions such as res_* or Inputs_*:
- formula regions: runs of cells in a column with the same relative (R1C1) formula,
  so a 2,088-row trace column is one region (standard spreadsheet-audit compression);
- defined names with a structural role: input (constant cells), derived (formula), and
  output (derived and referenced by no other formula), plus labels/units/PSA metadata
  read from the row of each input;
- for every derived or output name, the set of input names it depends on (region dependency graph);
- numeric literals inside formulas beyond an allowed structural set, and numeric
  constants sitting on calculation sheets (hardcoding scan);
- sheets with identical region layouts (parallel arm traces);
- conventions detected from formula patterns, and mismatches with the declaration.
It reads formulas only; it never recalculates. Equivalent in VBA: walk UsedRange.FormulaR1C1.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter

STRUCTURAL_LITERALS = {"0", "0.5", "1", "2", "7", "12"}
_REF = re.compile(
    r"(?:(?P<sheet>'[^']+'|[A-Za-z_][A-Za-z0-9_]*)!)?"
    r"(?<![A-Za-z_\d.])(?P<c1>\$?[A-Z]{1,3})(?P<r1>\$?\d+)(?::(?P<c2>\$?[A-Z]{1,3})(?P<r2>\$?\d+))?(?![A-Za-z_\d(])")
_STR = re.compile(r'"[^"]*"')
_IDENT = re.compile(r"(?<![A-Za-z_\d.$!])([A-Za-z_][A-Za-z0-9_.]*)(?![A-Za-z0-9_.(!])")
_LITERAL = re.compile(r"(?<![A-Za-z_$\d.])(\d+(?:\.\d+)?)(?![\d.]*[A-Za-z_(])")


def _strip_strings(f: str) -> str:
    return _STR.sub('""', f)


def _col(c: str) -> int:
    return column_index_from_string(c.lstrip("$"))


def _row(r: str) -> int:
    return int(r.lstrip("$"))


def r1c1(formula: str, row: int, col: int) -> str:
    """Relative signature of a formula: identical for cells copied down a column."""
    def sub(m):
        out = (m["sheet"] + "!") if m["sheet"] else ""
        parts = [(m["c1"], m["r1"])] + ([(m["c2"], m["r2"])] if m["c2"] else [])
        refs = []
        for c, r in parts:
            cs = f"C{_col(c)}" if c.startswith("$") else f"C[{_col(c) - col}]"
            rs = f"R{_row(r)}" if r.startswith("$") else f"R[{_row(r) - row}]"
            refs.append(rs + cs)
        return out + ":".join(refs)
    return _REF.sub(sub, _strip_strings(formula))


class Workbook:
    def __init__(self, path):
        self.path = Path(path)
        self.wb = openpyxl.load_workbook(path)
        self.names = {}
        for name, dn in self.wb.defined_names.items():
            m = _REF.fullmatch(dn.attr_text)
            sheet = m["sheet"].strip("'")
            c1, r1 = _col(m["c1"]), _row(m["r1"])
            c2, r2 = (_col(m["c2"]), _row(m["r2"])) if m["c2"] else (c1, r1)
            self.names[name] = (sheet, c1, r1, c2, r2)
        self.cell_name = {}
        for n, (s, c1, r1, c2, r2) in self.names.items():
            for c in range(c1, c2 + 1):
                for r in range(r1, r2 + 1):
                    self.cell_name[(s, c, r)] = n
        self._regions()

    def _regions(self):
        """Group formula cells into regions of identical R1C1 signature within a column."""
        self.region_of, self.regions = {}, {}
        for ws in self.wb.worksheets:
            by_col = defaultdict(list)
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("="):
                        by_col[c.column].append((c.row, c.value))
            for col, cells in by_col.items():
                cells.sort()
                start = prev_row = prev_sig = None
                for r, f in cells:
                    sig = r1c1(f, r, col)
                    named = (ws.title, col, r) in self.cell_name
                    if sig != prev_sig or r != prev_row + 1 or named or start is None:
                        start = r
                        rid = f"{ws.title}!{get_column_letter(col)}{r}"
                        self.regions[rid] = {"sheet": ws.title, "col": col, "rows": [r, r], "sig": sig,
                                             "formula": f, "deps": set()}
                    else:
                        self.regions[rid]["rows"][1] = r
                    self.region_of[(ws.title, col, r)] = rid
                    prev_row, prev_sig = r, (None if named else sig)
        for rid, reg in self.regions.items():
            reg["deps"] = self._deps(reg)
            reg["id"] = rid

    def _target(self, sheet, col, row):
        if (sheet, col, row) in self.region_of:
            return self.region_of[(sheet, col, row)]
        name = self.cell_name.get((sheet, col, row))
        if name:
            return f"name:{name}"
        v = self.wb[sheet].cell(row=row, column=col).value
        return f"const:{sheet}!{get_column_letter(col)}{row}" if isinstance(v, (int, float)) else None

    def _deps(self, reg):
        deps = set()
        f = _strip_strings(reg["formula"])
        rows = range(reg["rows"][0], reg["rows"][1] + 1)
        for m in _REF.finditer(f):
            sheet = m["sheet"].strip("'") if m["sheet"] else reg["sheet"]
            for row in (rows if not (m["r1"].startswith("$")) else [reg["rows"][0]]):
                off = row - reg["rows"][0]
                c1 = _col(m["c1"])
                r1 = _row(m["r1"]) + (0 if m["r1"].startswith("$") else off)
                c2 = _col(m["c2"]) if m["c2"] else c1
                r2 = (_row(m["r2"]) + (0 if m["r2"].startswith("$") else off)) if m["c2"] else r1
                for c in range(c1, c2 + 1):
                    for r in range(r1, r2 + 1):
                        t = self._target(sheet, c, r)
                        if t:
                            deps.add(t)
        for ident in _IDENT.findall(_REF.sub(" ", f)):
            if ident in self.names:
                s, c1, r1, c2, r2 = self.names[ident]
                if (s, c1, r1) in self.region_of and (c1, r1) == (c2, r2):
                    deps.add(self.region_of[(s, c1, r1)])
                else:
                    deps.add(f"name:{ident}")
        deps.discard(reg.get("id"))
        return deps


def _input_metadata(wb, sheet, col, row):
    ws = wb[sheet]
    header_row = None
    for r in range(1, min(row, 10)):
        if ws.cell(row=r, column=col).value == "Value":
            header_row = r
    if header_row is None:
        return {}
    meta = {}
    for c in range(1, ws.max_column + 1):
        h = ws.cell(row=header_row, column=c).value
        if h and c != col:
            meta[str(h)] = ws.cell(row=row, column=c).value
    return meta


def detect_conventions(W: Workbook) -> dict:
    det = {"discount_factor_regions": [], "hcc_columns": [], "survival_forms": set(), "gpm_cap": False}
    for rid, reg in W.regions.items():
        f = reg["formula"].replace("$", "")
        m = re.search(r"1/\(1\+(\w+)\)\^(.+)$", f)
        if m:
            expo = m.group(2)
            kind = "annual_step" if "INT(" in expo else ("cycle_midpoint" if "+0.5" in expo else "cycle_start")
            det["discount_factor_regions"].append({"region": rid, "rate": m.group(1), "timing": kind,
                                                   "rows": reg["rows"]})
        for col in re.findall(r"\(([A-Z]+)(\d+)\+\1(\d+)\)/2", f):
            letter, r_a, r_b = col
            if int(r_b) == int(r_a) + 1:
                det["hcc_columns"].append({"region": rid, "averages_column": letter})
        if re.search(r"EXP\(-\(\(\w+\d*/[^)]+\)\^", f):
            det["survival_forms"].add("weibull_aft")
        if not det["gpm_cap"] and "MIN(" in f:
            det["gpm_cap"] = any(d.startswith("name:lt_") for d in _closure(W, rid, depth=3))
    timings = {d["timing"] for d in det["discount_factor_regions"]}
    det["discounting_method"] = ("annual_step" if timings == {"annual_step"} else
                                 "mid_cycle_continuous" if "cycle_midpoint" in timings and "annual_step" not in timings
                                 else "mixed_or_unknown")
    det["survival_forms"] = sorted(det["survival_forms"])
    det["hcc_method"] = "trapezoidal" if det["hcc_columns"] else "none_detected"
    return det


def _closure(W, rid, depth=50):
    seen, frontier = set(), {rid}
    for _ in range(depth):
        nxt = set()
        for r in frontier:
            for d in W.regions.get(r, {}).get("deps", ()):
                if d not in seen:
                    seen.add(d)
                    nxt.add(d)
        if not nxt:
            break
        frontier = nxt
    return seen


def compare_conventions(detected: dict, declared: dict) -> list[str]:
    issues = []
    if detected["discounting_method"] != declared["discounting"]["method"]:
        issues.append(f"discounting.method declared {declared['discounting']['method']!r}, "
                      f"formulas show {detected['discounting_method']!r}")
    if declared["half_cycle_correction"]["method"] == "trapezoidal" and detected["hcc_method"] != "trapezoidal":
        issues.append("half_cycle_correction declared trapezoidal, no trapezoid found in formulas")
    if declared["survival"]["form"] == "weibull_aft" and "weibull_aft" not in detected["survival_forms"]:
        issues.append("survival.form declared weibull_aft, not found in formulas")
    if declared["general_population_mortality"]["applied"] and not detected["gpm_cap"]:
        issues.append("general_population_mortality declared, no life-table-driven cap found")
    return issues


def profile(xlsx, conventions_yaml=None, structural_literals=STRUCTURAL_LITERALS) -> dict:
    W = Workbook(xlsx)
    referenced = set()
    for reg in W.regions.values():
        referenced |= reg["deps"]
    names_out, input_names = {}, set()
    for n, (s, c1, r1, c2, r2) in sorted(W.names.items()):
        cells = [(s, c, r) for c in range(c1, c2 + 1) for r in range(r1, r2 + 1)]
        is_formula = any(k in W.region_of for k in cells)
        node = W.region_of.get(cells[0]) if is_formula else f"name:{n}"
        if not is_formula:
            role = "input"
            input_names.add(n)
        elif node in referenced:
            role = "derived"
        else:
            role = "output"
        entry = {"role": role, "sheet": s,
                 "ref": f"{get_column_letter(c1)}{r1}" + (f":{get_column_letter(c2)}{r2}" if (c1, r1) != (c2, r2) else ""),
                 "vector": len(cells) > 1}
        if role == "input" and not entry["vector"]:
            entry["metadata"] = _input_metadata(W.wb, s, c1, r1)
            v = W.wb[s].cell(row=r1, column=c1).value
            entry["type"] = "number" if isinstance(v, (int, float)) and not isinstance(v, bool) else "text"
        names_out[n] = entry
    deps_of = {}
    for n, e in names_out.items():
        if e["role"] != "input":
            s, c1, r1, *_ = W.names[n]
            reach = _closure(W, W.region_of[(s, c1, r1)])
            deps_of[n] = sorted(d[5:] for d in reach if d.startswith("name:") and d[5:] in input_names)
    findings = []
    input_sheets = {names_out[n]["sheet"] for n in input_names}
    for rid, reg in W.regions.items():
        lits = set(_LITERAL.findall(_REF.sub(" ", _strip_strings(reg["formula"])).replace("$", ""))) - structural_literals
        if lits:
            findings.append({"kind": "literal_in_formula", "region": rid, "literals": sorted(lits)})
    for ws in W.wb.worksheets:
        if ws.title in input_sheets:
            continue
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, (int, float)) and not isinstance(c.value, bool) \
                        and (ws.title, c.column, c.row) not in W.cell_name:
                    findings.append({"kind": "constant_on_calc_sheet", "cell": f"{ws.title}!{c.coordinate}",
                                     "value_present": True})
    layouts = defaultdict(list)
    for ws in W.wb.worksheets:
        sig = tuple(sorted((get_column_letter(r["col"]), tuple(r["rows"]), r["sig"])
                           for r in W.regions.values() if r["sheet"] == ws.title and r["rows"][1] - r["rows"][0] > 100))
        if sig:
            layouts[sig].append(ws.title)
    detected = detect_conventions(W)
    out = {
        "workbook": str(xlsx),
        "sheets": W.wb.sheetnames,
        "n_formula_cells": len(W.region_of),
        "n_regions": len(W.regions),
        "names": names_out,
        "input_dependencies": deps_of,
        "parallel_layouts": [v for v in layouts.values() if len(v) > 1],
        "hardcoding_findings": findings,
        "conventions_detected": detected,
    }
    if conventions_yaml:
        import yaml
        declared = yaml.safe_load(Path(conventions_yaml).read_text())
        out["conventions_declared"] = str(conventions_yaml)
        out["convention_mismatches"] = compare_conventions(detected, declared)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("xlsx")
    ap.add_argument("--conventions")
    ap.add_argument("--out")
    a = ap.parse_args()
    text = json.dumps(profile(a.xlsx, a.conventions), indent=2, default=str)
    if a.out:
        Path(a.out).write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
