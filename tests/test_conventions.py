"""Convention declarations: valid, enforced by the engine, and consistent with the formulas."""
import copy
import re

import openpyxl
import pytest
import yaml

from conftest import CONVENTIONS, MODEL
from tools.partsa_engine import ConventionError, check_conventions
from tools.workbook_io import list_names

RAW = yaml.safe_load(CONVENTIONS.read_text())


def test_fixture_a_declares_mid_cycle_continuous():
    check_conventions(RAW)
    assert RAW["discounting"]["method"] == "mid_cycle_continuous"


@pytest.mark.parametrize("path,value", [
    (("half_cycle_correction", "method"), "simpson"),
    (("discounting", "method"), "continuous_rate"),
    (("dosing", "population_treated"), "tot_hcc"),
    (("one_off_incidence", "progression"), "pfs_decrement"),
    (("general_population_mortality", "method"), "min_of_curves"),
])
def test_engine_refuses_undeclared_or_unimplemented_conventions(path, value):
    c = copy.deepcopy(RAW)
    c[path[0]][path[1]] = value
    with pytest.raises(ConventionError):
        check_conventions(c)


def test_annual_step_requires_matching_timing_block():
    c = copy.deepcopy(RAW)
    c["discounting"]["method"] = "annual_step"
    with pytest.raises(ConventionError):
        check_conventions(c)          # timing block still says cycle_midpoint/cycle_start
    c["discounting"]["timing"] = {k: ("undiscounted" if k == "ae_at_baseline" else "model_year")
                                  for k in c["discounting"]["timing"]}
    check_conventions(c)


@pytest.fixture(scope="module")
def results_formulas():
    wb = openpyxl.load_workbook(MODEL)
    names = list_names(MODEL)
    return {n: wb[s][c].value for n, (s, c) in names.items() if n.startswith("res_int_")}, wb["Trace_Int"]


def test_declared_discount_timing_matches_formulas(results_formulas):
    """Y = DF at cycle start, Z = DF costs at mid-cycle, AA = DF outcomes at mid-cycle."""
    f, trace = results_formulas
    assert "/(1+dr_costs)^(A21*cycle_length_years)" in trace["Y21"].value
    assert "/(1+dr_costs)^((A21+0.5)*cycle_length_years)" in trace["Z21"].value
    timing = RAW["discounting"]["timing"]
    df_col = {"cycle_start": "$Y$", "cycle_midpoint": "$Z$"}
    streams = {"dosing_costs": ["res_int_cost_drug", "res_int_cost_admin"],
               "state_costs": ["res_int_cost_pf_state", "res_int_cost_pd_state"],
               "one_off_event_costs": ["res_int_cost_terminal", "res_int_cost_st"]}
    for stream, names in streams.items():
        for n in names:
            assert df_col[timing[stream]] in f[n], f"{n} not discounted at {timing[stream]}"
    assert "$AA$" in f["res_int_qaly_disc"] and "$AA$" in f["res_int_ly_disc"]
    assert "SUMPRODUCT" not in f["res_int_cost_ae"], "AE costs undiscounted"


def test_declared_hcc_scope_matches_formulas(results_formulas):
    """HCC columns are R (PF) and S (PD). Declared HCC streams use them; the others must not."""
    _, t = results_formulas
    hcc = {"pf_state_cost": "AF", "pd_state_cost": "AG", "life_years": "AK", "qalys": "AL"}
    no_hcc = {"drug_cost": "AD", "admin_cost": "AE", "terminal_care_cost": "AH", "subsequent_therapy_cost": "AI"}
    uses_hcc = lambda col: bool(re.search(r"(?<![A-Z])[RST]21\b", t[f"{col}21"].value))
    for key in RAW["half_cycle_correction"]["applied_to"]:
        assert uses_hcc(hcc[key]), key
    for key in RAW["half_cycle_correction"]["not_applied_to"]:
        if key in no_hcc:
            assert not uses_hcc(no_hcc[key]), key
    assert "X21" in t["AD21"].value and "X21" in t["AE21"].value, "dosing costs use doses (ToT at cycle start)"
    assert "M21" in t["X21"].value, "doses use ToT capped by OS at cycle start"
