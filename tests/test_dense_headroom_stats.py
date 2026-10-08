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
    assert names[10] == "N:hs:0.25:42" and names[-1] == "N:mp:4:44"
    ratios = [b / a for a, b in zip(dhs.SIGMAS, dhs.SIGMAS[1:], strict=False)]
    assert all(1.35 < r < 1.45 for r in ratios)  # about sqrt(2): the reach rule's grid


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


def _sigma(v1: bool, xi: float, rel: float, evaluable: bool = True, loss: float = 3.0
           ) -> dict:
    return {"english_ml": {"v1_pass": v1, "loss_seed_mean": loss}, "xi": {"point": xi},
            "xi_rel": {"evaluable": evaluable, "point": rel}}


def test_null_verdict() -> None:
    assert dhs.null_verdict({"0.5": _sigma(True, 1.9, -0.09),
                             "2": _sigma(False, 15.0, 0.6, loss=9.0)})["verdict"] == "CENTRED"
    assert dhs.null_verdict({"0.5": _sigma(True, 2.1, 0.0)})["verdict"] == "NOT_CENTRED"
    assert dhs.null_verdict({"0.5": _sigma(True, 0.0, 0.11)})["verdict"] == "NOT_CENTRED"
    assert dhs.null_verdict({"0.5": _sigma(False, 0.0, 0.0)})["verdict"] == "NOT_EVALUABLE"
    assert dhs.null_verdict({"0.5": _sigma(True, 0.0, math.nan, False)})["verdict"] == (
        "NOT_EVALUABLE")


def test_a_null_tested_only_on_near_copies_is_not_evaluable() -> None:
    # Only sigma 0.25 passes V1 and it loses 0.3 points: a near-exact copy of the
    # target, whose xi is 0 by construction. Centring would be vacuous.
    near = {"0.25": _sigma(True, 0.1, 0.01, loss=0.3), "0.35": _sigma(False, 8.0, 0.4, loss=6.0)}
    read = dhs.null_verdict(near)
    assert read["verdict"] == "NOT_EVALUABLE" and read["reaching_sigmas"] == []
    assert read["english_ml_loss"] == {"0.25": 0.3, "0.35": 6.0}
    # One adequate scale at the boundary region makes it evaluable; every adequate
    # scale must then be centred, the near copy included.
    reach = {**near, "0.35": _sigma(True, 1.5, 0.08, loss=dhs.NULL_REACH_POINTS)}
    assert dhs.null_verdict(reach)["verdict"] == "CENTRED"
    off = {**reach, "0.25": _sigma(True, 2.5, 0.01, loss=0.3)}
    assert dhs.null_verdict(off)["verdict"] == "NOT_CENTRED"
    # A near copy that already breaks the limits is evidence, not a vacuous test.
    broken = {**near, "0.25": _sigma(True, 0.1, 0.2, loss=0.3)}
    assert dhs.null_verdict(broken)["verdict"] == "NOT_CENTRED"
    assert dhs.NULL_REACH_POINTS == 2.5


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
    assert (flags["lexical_confound"], flags["entity_control"]) == ("PRESENT", "SUFFICIENT")
    assert "anchor_confound" not in flags  # LEX reads lexical overlap, not entities
    flags = dhs.entity_flags(_entity([0.09, 0.02], [0.05, 0.10]))
    assert (flags["lexical_confound"], flags["entity_control"]) == ("ABSENT", "INSUFFICIENT")
    flags = dhs.entity_flags(_entity([0.2, 0.2], [0.0, 0.0], controlled_share=0.25))
    assert flags["entity_control"] == "INSUFFICIENT"
    flags = dhs.entity_flags(_entity([None, 0.2], [None, 0.0]))
    assert (flags["lexical_confound"], flags["entity_control"]) == ("NOT_EVALUABLE",
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
    base = {"lane_class": lane_class, "lexical_confound": "ABSENT",
            "entity_control": "SUFFICIENT", "h2_status": "PASS",
            "null_calibration": {"hs": "CENTRED", "mp": "CENTRED"},
            "floor_candidate": "VIABLE"}
    return {**base, **overrides}


D26 = ("a seen-script cross-script condition (D26; not measurable here)",
       "an entity-controlled question set (D26)",
       "a new experiment id and the research gauntlet (D26)")


def test_combined_recommendation_and_requirements() -> None:
    read = dhs.combined_recommendation({
        "qwen3-0.6b-base": _decisions("GO_ONLY_CAPABLE"),
        "qwen3.5-4b-base": _decisions("NEGATIVE_CAPABLE", lexical_confound="PRESENT",
                                      entity_control="INSUFFICIENT", h2_status="POINT_ONLY",
                                      null_calibration={"hs": "NOT_CENTRED",
                                                        "mp": "CENTRED"},
                                      floor_candidate="NOT_VIABLE")})
    assert (read["design"], read["base"]) == ("NEGATIVE_CAPABLE_V3", "qwen3.5-4b-base")
    assert set(D26) <= set(read["requirements"])
    text = " ".join(read["requirements"])
    for phrase in ("computed on the entity-controlled set", "anchor masking",
                   "null-calibrated", "redesigned", "H2 re-tested"):
        assert phrase in text
    clean = dhs.combined_recommendation({"qwen3-0.6b-base": _decisions("NEGATIVE_CAPABLE"),
                                         "qwen3.5-4b-base": _decisions("NOT_VIABLE")})
    assert clean["base"] == "qwen3-0.6b-base"
    assert clean["requirements"][:3] == list(D26)
    assert len(clean["requirements"]) == 4 and "0.5" in clean["requirements"][3]
    none = dhs.combined_recommendation({"qwen3-0.6b-base": _decisions("NOT_VIABLE"),
                                        "qwen3.5-4b-base": _decisions("NOT_VIABLE")})
    assert (none["design"], none["base"], none["requirements"]) == ("NO_K1_V3", None, [])
    assert dhs.combined_recommendation({})["design"] == "INCOMPLETE"


def test_flags_never_remove_d26_requirements() -> None:
    # Whatever the flags read, D26's entity-controlled set, floor, seen-script
    # condition and gauntlet stay; the flags can only add.
    for confound in ("ABSENT", "PRESENT", "NOT_EVALUABLE"):
        for control in ("SUFFICIENT", "INSUFFICIENT", "NOT_EVALUABLE"):
            for floor in ("VIABLE", "NOT_VIABLE", "NOT_EVALUABLE"):
                read = dhs.combined_recommendation({
                    "qwen3-0.6b-base": _decisions("GO_ONLY_CAPABLE", lexical_confound=confound,
                                                  entity_control=control,
                                                  floor_candidate=floor),
                    "qwen3.5-4b-base": _decisions("NOT_VIABLE")})
                assert set(D26) <= set(read["requirements"])
                assert any("non-literal" in r for r in read["requirements"])


@pytest.mark.parametrize("classes", [("INVALID", "NOT_VIABLE"), ("INVALID", "NEGATIVE_CAPABLE"),
                                     ("INVALID", "GO_ONLY_CAPABLE"), ("NOT_VIABLE", "INVALID"),
                                     ("NEGATIVE_CAPABLE", "INVALID"), ("INVALID",)])
def test_an_invalid_lane_invalidates_the_combined_read(classes) -> None:
    decisions = {lane: _decisions(c) for lane, c in zip(dhd.REGISTERED_ORDER, classes,
                                                        strict=False)}
    read = dhs.combined_recommendation(decisions)
    assert (read["design"], read["base"], read["requirements"]) == ("INVALID", None, [])


def _floor_case() -> tuple[dict, dhs.Results, dict]:
    """A lane whose floor conditions (a) and (b) hold, with its null block."""

    levels = {"T:MN": 45, "T:CX": 40, "T:ML": 80, "rand": 12, "LEX:MN": 15,
              "acc:CX": 0.95, "acc:absent": 0.1, "acc:MN": 0.95}
    artifact, results = doctor._results_fixture(levels, SEEDS)
    controlled = dhs.question_sets(artifact["features"])["controlled"]
    null = dhs.null_block(artifact["prompts"], results, SEEDS, 200, controlled)
    return artifact, results, null


def _set_nulls(null: dict, **sigmas: tuple[bool, float, float]) -> None:
    """Every null of target hs: (v1_pass, seed-mean English ML loss, lower bound of
    the controlled G(MN)); scales not named fail V1."""

    for name, block in null["hs"]["sigmas"].items():
        v1, loss, lower = sigmas.get("s" + name.replace(".", "_"), (False, 9.0, 0.9))
        block["english_ml"]["v1_pass"] = v1
        block["english_ml"]["loss_seed_mean"] = loss
        block["g_mn_controlled"] = {"evaluable": True, "point": lower + 0.1, "lower": lower,
                                    "upper": lower + 0.2}


def _floor(artifact: dict, results: dhs.Results, null: dict) -> dict:
    return dhs.floor_block(artifact["prompts"], results, artifact["features"], null, "hs", 200)


def test_the_floor_is_judged_on_the_nulls_lower_bound() -> None:
    artifact, results, null = _floor_case()
    _set_nulls(null, s0_5=(True, 3.0, 0.05), s0_7=(True, 4.0, 0.05))
    wide = _floor(artifact, results, null)
    assert wide["verdict"] == "NOT_VIABLE" and wide["adequate_nulls_passing"] == []
    assert any("lower bound" in reason for reason in wide["reasons"])
    assert wide["null_g_mn_controlled"]["0.5"]["lower"] == 0.05
    assert wide["null_g_mn_controlled"]["0.5"]["english_ml_loss"] == 3.0
    _set_nulls(null, s0_5=(True, 3.0, 0.5), s0_7=(True, 4.0, 0.05))
    tight = _floor(artifact, results, null)
    assert tight["verdict"] == "VIABLE", tight["reasons"]
    assert tight["adequate_nulls_passing"] == ["0.5"]
    lex = tight["references"]["LEX"]["controlled"]
    assert lex["point"] < 0.5 and "upper" in lex and "lower" in lex


def test_a_floor_passed_only_by_the_near_copy_is_not_viable() -> None:
    # D32: condition (c) counts only nulls that meet decision 8's reach rule. The
    # near-exact copy at sigma 0.25 (loss 0.3) passes the floor; the reaching,
    # V1-adequate scales do not, so the floor is not shown to admit an imperfect
    # selector.
    artifact, results, null = _floor_case()
    _set_nulls(null, s0_25=(True, 0.3, 0.8), s0_35=(True, 1.2, 0.6),
               s0_5=(True, 2.6, 0.3), s0_7=(True, 4.5, 0.1))
    read = _floor(artifact, results, null)
    assert read["verdict"] == "NOT_VIABLE"
    assert read["reaching_sigmas"] == ["0.5", "0.7"] and read["adequate_nulls_passing"] == []
    assert read["reasons"] == [
        "no V1-adequate null that loses at least 2.5 points of English ML recall has a 99 "
        "percent lower bound of G(MN) of at least 0.5"]
    # The reach rule is the null verdict's own.
    assert read["reaching_sigmas"] == dhs.reaching_sigmas(null["hs"]["sigmas"])
    assert dhs.null_verdict(null["hs"]["sigmas"])["reaching_sigmas"] == read["reaching_sigmas"]
    # A reach-qualified scale that passes keeps the floor VIABLE.
    _set_nulls(null, s0_25=(True, 0.3, 0.8), s0_5=(True, 2.6, 0.3), s0_7=(True, 4.5, 0.55))
    assert _floor(artifact, results, null)["adequate_nulls_passing"] == ["0.7"]
    assert _floor(artifact, results, null)["verdict"] == "VIABLE"
    # A large loss does not count without V1.
    _set_nulls(null, s0_25=(True, 0.3, 0.8), s1=(False, 6.0, 0.7))
    assert _floor(artifact, results, null)["verdict"] == "NOT_VIABLE"


@pytest.mark.parametrize(("loss", "expected"), [(2.5, "VIABLE"), (2.4999, "NOT_VIABLE"),
                                                (math.nan, "NOT_VIABLE")])
def test_the_floors_reach_boundary(loss, expected) -> None:
    artifact, results, null = _floor_case()
    _set_nulls(null, s0_25=(True, 0.2, 0.9), s0_5=(True, loss, 0.5))
    assert _floor(artifact, results, null)["verdict"] == expected


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
