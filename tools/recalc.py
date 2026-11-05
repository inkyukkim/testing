"""Deterministic tool: recalculate every formula in an .xlsx with LibreOffice headless.

Portable contract (used by Builder/Runner and Model Verifier):
    recalc(src_xlsx, out_dir) -> path to recalculated .xlsx (cached values populated)

Equivalent in an Excel/VBA-only environment: open the workbook, run
Application.CalculateFull, save a copy. No Claude runtime is involved.

openpyxl-written workbooks carry no cached values, and LibreOffice by default does not
recalculate OOXML files on load. We therefore launch soffice with a throw-away user
profile whose registry forces "always recalculate on load" (OOXMLRecalcMode=0).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

_REGISTRY = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry"
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <item oor:path="/org.openoffice.Office.Calc/Formula/Load">
    <prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop>
  </item>
  <item oor:path="/org.openoffice.Office.Calc/Formula/Load">
    <prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop>
  </item>
</oor:items>
"""


class RecalcError(RuntimeError):
    pass


def soffice_binary() -> str:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    raise RecalcError(
        "LibreOffice (soffice) not found. Install it; do not substitute another engine."
    )


def recalc(src: str | Path, out_dir: str | Path, timeout: int = 300) -> Path:
    src = Path(src).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if src.parent == out_dir:
        raise RecalcError("out_dir must differ from the source directory (would overwrite source)")
    with tempfile.TemporaryDirectory(prefix="lo_profile_") as profile:
        user_dir = Path(profile) / "user"
        user_dir.mkdir(parents=True)
        (user_dir / "registrymodifications.xcu").write_text(_REGISTRY)
        cmd = [
            soffice_binary(),
            f"-env:UserInstallation=file://{profile}",
            "--headless", "--norestore", "--nolockcheck",
            "--convert-to", "xlsx:Calc MS Excel 2007 XML",
            "--outdir", str(out_dir), str(src),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = out_dir / (src.stem + ".xlsx")
    if proc.returncode != 0 or not out.exists():
        raise RecalcError(f"LibreOffice failed ({proc.returncode}): {proc.stdout}\n{proc.stderr}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src")
    ap.add_argument("out_dir")
    args = ap.parse_args()
    print(recalc(args.src, args.out_dir))


if __name__ == "__main__":
    main()
