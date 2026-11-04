import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.partsa_engine import REQUIRED_INPUTS, load_conventions  # noqa: E402
from tools.recalc import recalc  # noqa: E402
from tools.workbook_io import read_named, write_named  # noqa: E402

FIXTURES = ROOT / "fixtures"
MODEL = FIXTURES / "global_model.xlsx"
CONVENTIONS = FIXTURES / "global_model.conventions.yaml"
FIRST = 20   # first data row on trace sheets

# Perturbation that makes every new feature matter: older cohort and flatter Drug A OS tail
# (GPM cap binds early), weight-based Drug B, KR-like costs and utilities, Drug B PFS that
# crosses OS (exercises the MIN cap), different stopping rules and RDI.
PERTURBED = {
    "dr_costs": 0.045, "dr_outcomes": 0.045, "time_horizon_years": 30, "u_pf": 0.80, "u_pd": 0.66,
    "baseline_age": 72, "prop_male": 0.45, "weight_mean_kg": 64.5, "weight_sd_kg": 11.8,
    "c_pf_week": 138000, "c_pd_week": 241500, "c_terminal": 4000000,
    "int_vial_price": 1050000, "int_admin_cost_per_admin": 95000, "comp_admin_cost_per_admin": 95000,
    "int_ae_cost": 1600000, "comp_ae_cost": 3100000,
    "int_os_shape": 0.55, "int_os_scale": 60.0, "int_max_doses": 20, "int_rdi": 0.88,
    "comp_pfs_shape": 0.8, "comp_pfs_scale": 40.0,
    "comp_dose_weight_based": 1, "comp_dose_mg": 7.5, "comp_vial_mg": 100, "comp_vial_price": 84000,
    "st_cost_1": 3900000, "st_cost_2": 38000000, "st_cost_3": 21000000,
    "int_st_share_1": 0.55, "int_st_share_2": 0.0, "int_st_share_3": 0.08,
}


@pytest.fixture(scope="session")
def conventions() -> dict:
    return load_conventions(CONVENTIONS)


@pytest.fixture(scope="session")
def recalculated_model(tmp_path_factory) -> Path:
    """Global model recalculated by LibreOffice headless (cached values populated)."""
    return recalc(MODEL, tmp_path_factory.mktemp("recalc_base"))


@pytest.fixture(scope="session")
def model_values(recalculated_model) -> dict:
    return read_named(recalculated_model)


@pytest.fixture(scope="session")
def perturbed_model(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("recalc_perturbed")
    return recalc(write_named(MODEL, d / "perturbed.xlsx", PERTURBED), d / "rc")


@pytest.fixture(scope="session")
def perturbed_values(perturbed_model) -> dict:
    return read_named(perturbed_model)


def engine_inputs(values: dict) -> dict:
    return {k: values[k] for k in REQUIRED_INPUTS}


SLOW_FIXTURES = {"recalculated_model", "model_values", "perturbed_model", "perturbed_values", "built",
                 "kr_contexts", "global_contexts", "scenario_values", "values_b", "kr_render"}
SLOW_CALLS = ("recalc(", "build_run(", "run_scenarios(")


def pytest_collection_modifyitems(config, items):
    """Mark LibreOffice-dependent tests 'slow' so `pytest -m "not slow"` is a fast lane."""
    import inspect
    for item in items:
        fn = getattr(item, "function", None)
        src = inspect.getsource(fn) if fn else ""
        if SLOW_FIXTURES & set(getattr(item, "fixturenames", ())) or any(c in src for c in SLOW_CALLS):
            item.add_marker(pytest.mark.slow)
