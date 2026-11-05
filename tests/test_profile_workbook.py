"""Model Profiler tool: roles, dependencies, hardcoding scan and convention detection."""
import openpyxl
import pytest

from conftest import CONVENTIONS, FIXTURES, MODEL
from tools.profile_workbook import profile

MODEL_B = FIXTURES / "global_model_B.xlsx"
CONV_B = FIXTURES / "global_model_B.conventions.yaml"


@pytest.fixture(scope="module")
def prof_a():
    return profile(MODEL, CONVENTIONS)


@pytest.fixture(scope="module")
def prof_b():
    return profile(MODEL_B, CONV_B)


def test_roles_are_structural_not_prefix_based(prof_a):
    names = prof_a["names"]
    for n, e in names.items():
        if n.startswith(("res_", "check_", "calc_")) or n in ("n_cycles", "cycle_length_years", "max_trace_cycles"):
            assert e["role"] in ("derived", "output"), n
        elif n.startswith(("int_", "comp_", "lt_", "u_", "c_", "dr_", "st_", "gpu_")):
            assert e["role"] == "input", n
    assert names["lt_qx_male"]["vector"] and names["lt_qx_male"]["role"] == "input"
    assert names["res_icer"]["role"] == "derived", "referenced by res_below_wtp"
    assert names["res_inc_nmb"]["role"] == "output"


def test_input_metadata_read_from_input_rows(prof_a):
    m = prof_a["names"]["c_pd_week"]["metadata"]
    assert m["Unit"] == "GBP/week" and m["PSA distribution"] == "Gamma"


def test_vector_inputs_are_labelled_from_their_header(prof_a):
    """Round 2: life-table ranges had no label in the report's retained-inputs list."""
    assert prof_a["names"]["lt_qx_male"]["metadata"] == {"Parameter": "qx male"}
    assert prof_a["names"]["lt_age"]["metadata"] == {"Parameter": "Age"}


def test_dependencies_follow_the_arm(prof_a):
    deps = prof_a["input_dependencies"]
    drug_a = set(deps["res_int_cost_drug"])
    assert {"int_vial_price", "int_rdi", "int_tot_shape", "weight_mean_kg", "dr_costs", "int_max_doses"} <= drug_a
    assert not any(d.startswith("comp_") for d in drug_a), "Drug A cost must not depend on Drug B inputs"
    assert not {"u_pf", "c_pf_week", "c_terminal", "dr_outcomes"} & drug_a
    qaly = set(deps["res_int_qaly_disc"])
    assert {"u_pf", "u_pd", "dr_outcomes", "gpu_age", "int_ae_qaly_loss"} <= qaly and "int_vial_price" not in qaly
    icer = set(deps["res_icer"])
    assert {"int_vial_price", "comp_vial_price", "u_pf", "c_terminal"} <= icer
    assert "wtp_threshold" not in icer and "psa_seed" not in icer


def test_parallel_arm_layouts_and_no_hardcoding(prof_a):
    assert ["Trace_Int", "Trace_Comp"] in prof_a["parallel_layouts"]
    assert prof_a["hardcoding_findings"] == []


def test_hardcoded_literal_and_constant_are_found(tmp_path):
    wb = openpyxl.load_workbook(MODEL)
    wb["Trace_Int"]["AD500"] = "=X500*$C$11*$C$10*0.95"     # hidden discount
    wb["Trace_Comp"]["AF600"] = 123.4                      # pasted value
    p = tmp_path / "hard.xlsx"
    wb.save(p)
    f = profile(p)["hardcoding_findings"]
    assert any(x["kind"] == "literal_in_formula" and "0.95" in x["literals"] and x["region"] == "Trace_Int!AD500" for x in f)
    assert any(x["kind"] == "constant_on_calc_sheet" and x["cell"] == "Trace_Comp!AF600" for x in f)


def test_detects_fixture_a_conventions(prof_a):
    d = prof_a["conventions_detected"]
    assert d["discounting_method"] == "mid_cycle_continuous"
    assert d["hcc_method"] == "trapezoidal" and {h["averages_column"] for h in d["hcc_columns"]} == {"N", "O"}
    assert d["survival_forms"] == ["weibull_aft"] and d["gpm_cap"]
    assert prof_a["convention_mismatches"] == []


def test_detects_fixture_b_annual_step(prof_b):
    assert prof_b["conventions_detected"]["discounting_method"] == "annual_step"
    assert prof_b["convention_mismatches"] == []


def test_wrong_declaration_is_reported():
    """Fixture A profiled against Fixture B's declaration: the Profiler must flag it."""
    issues = profile(MODEL, CONV_B)["convention_mismatches"]
    assert any("annual_step" in i and "mid_cycle_continuous" in i for i in issues)
