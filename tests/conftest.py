import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.recalc import recalc  # noqa: E402
from tools.workbook_io import read_named  # noqa: E402

FIXTURES = ROOT / "fixtures"
MODEL = FIXTURES / "global_model.xlsx"


@pytest.fixture(scope="session")
def recalculated_model(tmp_path_factory) -> Path:
    """Global model recalculated by LibreOffice headless (cached values populated)."""
    return recalc(MODEL, tmp_path_factory.mktemp("recalc_base"))


@pytest.fixture(scope="session")
def model_values(recalculated_model) -> dict:
    return read_named(recalculated_model)
