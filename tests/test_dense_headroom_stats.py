"""Statistics and decision rules of the dense headroom pre-check on hand-made tables."""

from __future__ import annotations

import copy
import math

import numpy as np
import pytest

from harness import dense_headroom_data as dhd
from harness import dense_headroom_stats as dhs
from scripts import run_dense_headroom_precheck_doctor as doctor

SEEDS = [42, 43, 44]


def _interval(point: float, lower: float, evaluable: bool = True) -> dict:
    return {"point": point, "lower": lower, "upper": point + (point - lower),
            "evaluable": evaluable}


def _answering(h2a=(60.0, 40.0), h2b=(20.0, 5.0)) -> dict:
    return {"h2a": _interval(*h2a), "h2b": _interval(*h2b)}


def test_selector_columns() -> None:
    names = dhs.selector_names(SEEDS)
    assert names[:10] == ["T:hs", "T:mp", "T:hm", "U", "Uk", "rand", "LEX", "T:hs@fixed",
                          "T:mp@fixed", "rand@fixed"]
    assert len(names) == 10 + 2 * len(dhs.SIGMAS) * 3
    assert names[10] == "N:hs:0.25:42" and names[-1] == "N:mp:2:44"


def test_doctor_statistics_case_passes() -> None:
    result = doctor.case_statistics()
    assert result["status"] == "PASS", result["failures"]


@pytest.mark.parametrize(("h1", "lower", "answering", "expected"), [
    (20.0, 10.0, _answering(), "NEGATIVE_CAPABLE"),
    (19.99, 15.0, _answering(), "GO_ONLY_CAPABLE"),
    (25.0, 9.99, _answering(), "GO_ONLY_CAPABLE"),
    (10.0, 2.0, _answering(), "GO_ONLY_CAPABLE"),
    (9.99, 2.0, _answering(), "NOT_VIABLE"),
    (30.0, 20.0, _answering(h2a=(29.0, 20.0)), "NOT_VIABLE"),
    (30.0, 20.0, _answering(h2a=(35.0, 25.0), h2b=(6.0, -2.0)), "NEGATIVE_CAPABLE"),
    (30.0, 20.0, _answering(h2b=(4.0, 1.0)), "NOT_VIABLE"),
])
def test_lane_classification_boundaries(h1, lower, answering, expected) -> None:
    headroom = {"h1_cx_points": h1, "h1_cx_lower": lower, "h1_cx_target": "hs"}
    assert dhs.classify_lane(headroom, answering, None)["lane_class"] == expected


def test_a_failed_smoke_reproduction_invalidates_the_lane() -> None:
    headroom = {"h1_cx_points": 30.0, "h1_cx_lower": 20.0, "h1_cx_target": "hs"}
    read = dhs.classify_lane(headroom, _answering(), {"status": "NOT_REPRODUCED"})
    assert read["lane_class"] == "INVALID"


def test_h2_status() -> None:
    assert dhs.h2_status(_answering()) == "PASS"
    assert dhs.h2_status(_answering(h2a=(35.0, 25.0))) == "POINT_ONLY"
    assert dhs.h2_status(_answering(h2b=(6.0, 0.0))) == "POINT_ONLY"
    assert dhs.h2_status(_answering(h2a=(30.0, 25.0))) == "FAIL"
    assert dhs.h2_status({"h2a": {"evaluable": False}, "h2b": _interval(9, 2)}) == "FAIL"


def test_k1_v1_prestep_is_k1s_rule() -> None:
    ok = dhs.k1_v1_prestep({"h1_cx_points": 12.0}, _answering())
    assert ok == {"decision": "PROCEED_TO_K1", "h1_negative_ready": False}
    stop = dhs.k1_v1_prestep({"h1_cx_points": 25.0}, _answering(h2b=(6.0, 0.0)))
    assert stop == {"decision": "ESCALATE_OR_STOP", "h1_negative_ready": True}


def _sigma(v1: bool, xi: float, rel: float, evaluable: bool = True) -> dict:
    return {"english_ml": {"v1_pass": v1}, "xi": {"point": xi},
            "xi_rel": {"evaluable": evaluable, "point": rel}}


def test_null_verdict() -> None:
    assert dhs.null_verdict({"0.5": _sigma(True, 1.9, -0.09),
                             "2": _sigma(False, 15.0, 0.6)})["verdict"] == "CENTRED"
    assert dhs.null_verdict({"0.5": _sigma(True, 2.1, 0.0)})["verdict"] == "NOT_CENTRED"
    assert dhs.null_verdict({"0.5": _sigma(True, 0.0, 0.11)})["verdict"] == "NOT_CENTRED"
    assert dhs.null_verdict({"0.5": _sigma(False, 0.0, 0.0)})["verdict"] == "NOT_EVALUABLE"
    assert dhs.null_verdict({"0.5": _sigma(True, 0.0, math.nan, False)})["verdict"] == (
        "NOT_EVALUABLE")


def _entity(all_rel, ctrl_rel, controlled_share=0.5) -> dict:
    def block(rel):
        if rel is None:
            return {"evaluable": False}
        return {"xi_rel": {"evaluable": True, "point": rel}}

    return {"controlled_share": controlled_share,
            "literal_selector": {"all": {t: block(r) for t, r in zip(dhs.TARGETS, all_rel,
                                                                       strict=True)},
                                 "controlled": {t: block(r) for t, r in zip(
                                     dhs.TARGETS, ctrl_rel, strict=True)}}}


def test_entity_flags() -> None:
    flags = dhs.entity_flags(_entity([0.12, 0.02], [0.05, 0.09]))
    assert (flags["anchor_confound"], flags["entity_control"]) == ("PRESENT", "SUFFICIENT")
    flags = dhs.entity_flags(_entity([0.09, 0.02], [0.05, 0.10]))
    assert (flags["anchor_confound"], flags["entity_control"]) == ("ABSENT", "INSUFFICIENT")
    flags = dhs.entity_flags(_entity([0.2, 0.2], [0.0, 0.0], controlled_share=0.25))
    assert flags["entity_control"] == "INSUFFICIENT"
    flags = dhs.entity_flags(_entity([None, 0.2], [None, 0.0]))
    assert (flags["anchor_confound"], flags["entity_control"]) == ("NOT_EVALUABLE",
                                                                   "NOT_EVALUABLE")


def test_retention_interval() -> None:
    group = dhs.Group.of([{"pair": p, "cluster": f"c{i}"} for i in range(6)
                          for p in ("a", "b")])
    n = len(group.prompts)
    tgt, rnd = [40.0] * n, [10.0] * n
    assert dhs.retention_interval(tgt, tgt, rnd, group, 200)["point"] == pytest.approx(1.0)
    assert dhs.retention_interval(rnd, tgt, rnd, group, 200)["point"] == pytest.approx(0.0)
    half = [25.0] * n
    read = dhs.retention_interval(half, tgt, rnd, group, 200)
    assert read["point"] == pytest.approx(0.5) and read["lower"] == pytest.approx(0.5)
    flat = dhs.retention_interval(half, [10.5] * n, rnd, group, 200)
    assert not flat["evaluable"]
    few = dhs.Group.of([{"pair": "a", "cluster": "c0"}, {"pair": "a", "cluster": "c1"}])
    assert not dhs.retention_interval([1.0, 1.0], [5.0, 5.0], [0.0, 0.0], few, 50)["evaluable"]


def test_wilson() -> None:
    low, high = dhs.wilson(10, 20)
    assert low == pytest.approx(0.2993, abs=1e-4) and high == pytest.approx(0.7007, abs=1e-4)
    assert all(math.isnan(v) for v in dhs.wilson(0, 0))


def _decisions(lane_class: str, **overrides) -> dict:
    base = {"lane_class": lane_class, "anchor_confound": "ABSENT",
            "entity_control": "SUFFICIENT",
            "null_calibration": {"hs": "CENTRED", "mp": "CENTRED"},
            "floor_candidate": "VIABLE"}
    return {**base, **overrides}


def test_combined_recommendation_and_requirements() -> None:
    read = dhs.combined_recommendation({
        "qwen3-0.6b-base": _decisions("GO_ONLY_CAPABLE"),
        "qwen3.5-4b-base": _decisions("NEGATIVE_CAPABLE", anchor_confound="PRESENT",
                                      entity_control="INSUFFICIENT",
                                      null_calibration={"hs": "NOT_CENTRED",
                                                        "mp": "CENTRED"},
                                      floor_candidate="NOT_VIABLE")})
    assert (read["design"], read["base"]) == ("NEGATIVE_CAPABLE_V3", "qwen3.5-4b-base")
    text = " ".join(read["requirements"])
    for phrase in ("seen-script", "gauntlet", "entity-controlled MN leg", "anchor masking",
                   "null-calibrated", "redesigned non-literal floor"):
        assert phrase in text
    clean = dhs.combined_recommendation({"qwen3-0.6b-base": _decisions("NEGATIVE_CAPABLE"),
                                         "qwen3.5-4b-base": _decisions("NOT_VIABLE")})
    assert clean["base"] == "qwen3-0.6b-base"
    assert len(clean["requirements"]) == 3 and "0.5" in clean["requirements"][2]
    none = dhs.combined_recommendation({"qwen3-0.6b-base": _decisions("NOT_VIABLE"),
                                        "qwen3.5-4b-base": _decisions("INVALID")})
    assert (none["design"], none["base"]) == ("NO_K1_V3", None)
    assert dhs.combined_recommendation({})["design"] == "INCOMPLETE"


def test_smoke_reproduction_tolerance() -> None:
    names = dhs.selector_names(SEEDS)
    prompts, units = [], {}
    wanted = [f"c{i}-q{i}" for i in range(20)]
    for i in range(20):
        prompts.append({"context_index": 100 + i, "query_index": 100 + i,
                        "source_unit": wanted[i]})
        recall = np.zeros((28, len(names)))
        for name, value in dhs.SMOKE_452.items():
            recall[:, names.index(name)] = value + (0.3 if name == "T:hs" else 0.0)
        units[f"c{100 + i}-q{100 + i}"] = {"recall": recall}
    artifact = {"prompts": prompts, "source": {"k1_smoke_units": wanted}}
    results = dhs.Results(names, units)
    assert dhs.smoke_452_reproduction(artifact, results)["status"] == "REPRODUCED"
    bad = copy.deepcopy(results)
    for row in bad.units.values():
        row["recall"][:, names.index("rand")] += 0.6
    assert dhs.smoke_452_reproduction(artifact, bad)["status"] == "NOT_REPRODUCED"
    missing = {**artifact, "prompts": prompts[:19]}
    assert dhs.smoke_452_reproduction(missing, results)["status"] == "NOT_REPRODUCED"


def test_coverage_refuses_missing_and_over_budget_units() -> None:
    names = dhs.selector_names(SEEDS)
    units = [dhd.Unit("c0-q0", "A-main", 0, 0, True, True)]
    row = {"recall": np.zeros((2, len(names))), "ties": np.zeros(len(names)),
           "max_selected": 10, "k_blocks": 2, "mc_scores": np.zeros(4), "mc_correct": 1}
    ok = dhs.check_coverage(units, dhs.Results(names, {"c0-q0": row}), {"c0-q0": 11})
    assert ok["within_budget"]
    with pytest.raises(dhs.DenseStatsError):
        dhs.check_coverage(units, dhs.Results(names, {"c0-q0": row}), {"c0-q0": 9})
    with pytest.raises(dhs.DenseStatsError):
        dhs.check_coverage(units, dhs.Results(names, {}), {"c0-q0": 11})
    bad = {**row, "mc_correct": -1}
    with pytest.raises(dhs.DenseStatsError):
        dhs.check_coverage(units, dhs.Results(names, {"c0-q0": bad}), {"c0-q0": 11})
