"""Input Mapper tools: local-input reader, mapping validation, apply, and a Stage 1 smoke run."""
import copy
import json
import math
import subprocess
import sys
from fractions import Fraction

import openpyxl
import pytest

from conftest import FIXTURES, MODEL, ROOT, engine_inputs
from test_recalc_parity import compare_all
from tools import gap_register
from tools.apply_mapping import apply_mapping, load_all, validate_spec
from tools.read_local_inputs import read_local_inputs
from tools.recalc import recalc
from tools.workbook_io import read_named, write_named

SPEC = FIXTURES / "mapping_spec_KR.json"


@pytest.fixture(scope="module")
def loaded():
    return load_all(SPEC)


@pytest.fixture()
def parts(loaded):
    spec, model, local, register = loaded
    return copy.deepcopy(spec), model, copy.deepcopy(local), copy.deepcopy(register)


def entry(spec, target):
    return next(m for m in spec["mappings"] if m["target"] == target)


def resolve_terminal_care(spec, local, register, value=4500000):
    """Test-only: simulate the human resolution of GAP-001 with local data (option E1)."""
    local["KR-C11"]["value"] = value
    g = next(g for g in register["gaps"] if g["gap_id"] == "GAP-001")
    g["status"] = "resolved"
    g["resolution"] = {"option_id": "E1", "decided_by": {"kind": "human", "role": "HEOR lead (KR)"},
                       "date": "2026-11-04", "evidence": "KR-C11 from local claims analysis (test fixture)"}
    e = entry(spec, "c_terminal")
    e.update(status="mapped", operation="copy", args={"source": "KR-C11"})


def test_local_reader_rows_and_vectors():
    items = read_local_inputs(FIXTURES / "adaptation_input_KR.xlsx")
    assert items["KR-C09"]["cell"] == "C12" and items["KR-C09"]["unit"].startswith("KRW per month")
    lt = items["KR-L01"]
    assert lt["unit"] == "mx male" and lt["ages"][-1] == "100+" and len(lt["value"]) == 101


def test_answer_key_is_valid_and_blocked(parts):
    spec, model, local, register = parts
    assert validate_spec(spec, model, local, register) == []
    res = apply_mapping(spec, model, local, register, dry_run=True)
    assert res["gate_blocked"] and res["blocking_gaps"] == ["GAP-001"] and "overrides" not in res
    with pytest.raises(PermissionError):
        apply_mapping(spec, model, local, register)


def test_cli_dry_run_exit_code():
    r = subprocess.run([sys.executable, "-m", "tools.apply_mapping", str(SPEC)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2 and "BLOCKED: GAP-001" in r.stdout


def test_operations_compute_exactly(parts):
    spec, model, local, register = parts
    resolve_terminal_care(spec, local, register)
    res = apply_mapping(spec, model, local, register)
    o, prov = res["overrides"], res["provenance"]
    assert o["c_pf_week"] == float(Fraction(600000) * 7 / (Fraction("365.25") / 12))
    assert prov["c_pf_week"]["source"] == {"item_id": "KR-C09", "sheet": "Costs_KR", "cell": "C12"}
    assert o["int_max_doses"] == 35, "doses at weeks 0..102 start within 2 years (104.36 weeks)"
    mx = local["KR-L01"]["value"]
    assert o["lt_qx_male"][62] == pytest.approx(1 - math.exp(-mx[62]), rel=1e-15)
    assert o["lt_qx_male"][101:] == [pytest.approx(1 - math.exp(-mx[100]))] * 10, "100+ rate carried to 110"
    assert o["comp_max_doses"] == 6 and prov["comp_max_doses"]["retained_from"].startswith("Inputs_Costs!")
    assert o["currency_code"] == "KRW" and o["c_terminal"] == 4500000
    assert o["wtp_threshold"] == o["wtp_threshold_lower"] == 50000000


def test_dose_rule_matters(parts):
    spec, model, local, register = parts
    resolve_terminal_care(spec, local, register)
    entry(spec, "int_max_doses")["args"]["rule"] = "complete_intervals_within"
    assert apply_mapping(spec, model, local, register)["overrides"]["int_max_doses"] == 34


@pytest.mark.parametrize("mutate,expect", [
    (lambda s, l: entry(s, "c_terminal").update(status="retained", operation="retain_global", basis="structural_setting"),
     "retains a global GBP value"),
    (lambda s, l: entry(s, "int_vial_price").update(args={"source": "KR-S09"}), "copy changes dimension"),
    (lambda s, l: l["KR-C09"].update(unit="KRW per month (30 days)"), "states 30 days per month"),
    (lambda s, l: s["mappings"].remove(entry(s, "u_pd")), "u_pd: model input not covered"),
    (lambda s, l: s["unused_local_items"].append({"item": "KR-C01", "reason": "x"}), "declared unused but used"),
    (lambda s, l: l.update({"KR-X99": {"value": 1, "unit": "-", "sheet": "x", "cell": "A1"}}), "KR-X99: local item neither used"),
    (lambda s, l: entry(s, "comp_max_doses")["confirm_in_source"].update(pattern="maximum {value} doses"),
     "does not confirm the retained value"),
    (lambda s, l: entry(s, "int_vial_price").update(operation="fx_convert"), "not whitelisted"),
    (lambda s, l: entry(s, "lt_qx_male")["args"].pop("open_band"), "have no local rate"),
    (lambda s, l: entry(s, "int_pfs_shape").pop("gap_id"), "needs a gap_id or basis"),
    (lambda s, l: entry(s, "prop_male").update(gap_id="GAP-002"), "does not list this target"),
    # round 2: shares were checked only in the built model (check_st_shares_ok)
    (lambda s, l: l["KR-T04"].update(value=0.99), "int: subsequent-therapy shares sum to more than one"),
    (lambda s, l: entry(s, "comp_st_share_2").update(status="retained", operation="retain_global", args={},
                                                     basis="structural_setting") or l["KR-T07"].update(value=0.9),
     "comp: subsequent-therapy shares sum to more than one"),
    # round 2: a label alone was weak evidence for a switch
    (lambda s, l: entry(s, "int_dose_weight_based")["confirm_in_source"].pop("means"), "must declare means"),
    (lambda s, l: entry(s, "comp_dose_weight_based")["confirm_in_source"].update(means="switch_on"),
     "which is not the retained value"),
])
def test_validation_catches(parts, mutate, expect):
    spec, model, local, register = parts
    mutate(spec, local)
    errors = validate_spec(spec, model, local, register)
    assert any(expect in e for e in errors), errors


def test_stage1_smoke_adapted_model_recalculates_and_matches_engine(parts, tmp_path, conventions):
    """Not the Builder/Runner (Gate 2): checks that the answer-key mapping yields a valid KR model."""
    spec, model, local, register = parts
    resolve_terminal_care(spec, local, register)
    res = apply_mapping(spec, model, local, register)
    src = write_named(MODEL, tmp_path / "adapted_KR.xlsx", res["overrides"])
    v = read_named(recalc(src, tmp_path / "rc"))
    for k, val in v.items():
        if k.startswith("check_") and isinstance(val, str):
            assert val == "OK", k
    compare_all(v, conventions)
    assert v["currency_code"] == "KRW" and v["res_int_total_cost"] > 1e7, "costs now in KRW"
    (tmp_path / "kr_result.json").write_text(json.dumps({k: v[k] for k in ("res_icer", "res_inc_total_cost", "res_inc_qaly_disc")}))
    print(f"\nKR smoke ICER (terminal care from test value): {v['res_icer']:,.0f} KRW/QALY")


def test_label_only_confirmation_rejected_for_numbers_and_listed_for_switches(parts):
    spec, model, local, register = parts
    e = entry(spec, "time_horizon_years")
    e.update(basis="confirmed_by_local_text", confirm_in_source={"item": "KR-S08", "field": "value", "pattern": "Lifetime"})
    spec["unused_local_items"] = [u for u in spec["unused_local_items"] if u["item"] != "KR-S08"]
    assert any("label-only confirmation" in x for x in validate_spec(spec, model, local, register))
    spec2, *_ = load_all(SPEC)
    res = apply_mapping(spec2, model, local, register, dry_run=True)
    assert ("int_dose_weight_based: confirmed by a label in KR-C02, not by its value "
            "(declared to mean switch_on)") in res["review"]
    assert any(r.startswith("cycle_length_days: retained as a structural setting") for r in res["review"])


def test_retained_source_references_must_exist(parts):
    spec, model, local, register = parts
    next(g for g in register["gaps"] if g["gap_id"] == "GAP-003")["retained_source"] = ["gpu_intercept", "uk_norms_2014"]
    assert any("retained_source 'uk_norms_2014'" in x for x in validate_spec(spec, model, local, register))
