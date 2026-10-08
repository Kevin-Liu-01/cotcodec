"""S1a episode records, loss classification and the registered decision rules."""

from __future__ import annotations

import math

import numpy as np
import pytest

from harness.q2_stage1 import records as R
from harness.q2_stage1 import rules


def rec(**kw):
    base = {
        "schema": R.SCHEMA,
        "job": "A1-9B-S1",
        "size": "9B",
        "session": "S1",
        "task_id": "t1",
        "harness": "H-GA",
        "rerun": 1,
        "extension_block": None,
        "attempt": 1,
        "status": "scored",
        "score": 1.0,
    }
    base.update(kw)
    return base


def test_schema_validation():
    R.validate(rec())
    for bad in (
        rec(schema="other"),
        rec(size="27B"),
        rec(attempt=3),
        rec(status="error"),
        rec(status="infrastructure", score=None),
        rec(status="infrastructure", score=None, infrastructure_type="ir_error"),
        rec(score=0.5, metric_exception=True),
        rec(status="cap_truncated", score=1.0),
        rec(ir_errors=-1),
        rec(extension_block=0),
    ):
        with pytest.raises(R.RecordError):
            R.validate(bad)
    # Agent-caused events are not infrastructure types.
    assert "ir_error" not in R.INFRASTRUCTURE_TYPES
    assert "metric_exception" not in R.INFRASTRUCTURE_TYPES


def test_final_records_and_outcomes():
    lost = rec(status="infrastructure", score=None, infrastructure_type="vm_boot")
    retry = rec(attempt=2, score=0.0)
    exc = rec(task_id="t2", score=0.0, metric_exception=True)
    frac = rec(task_id="t3", score=0.5)
    finals = R.final_records([retry, lost, exc, frac])
    assert finals[R.slot_key(lost)]["attempt"] == 2
    assert R.outcome(finals[R.slot_key(retry)]) == 0.0
    assert R.outcome(finals[R.slot_key(exc)]) == 0.0
    assert math.isnan(R.outcome(finals[R.slot_key(exc)], metric_exception_missing=True))
    assert R.outcome(finals[R.slot_key(frac)]) == 0.0
    y = R.outcome_array(finals, ["t1", "t2", "t3"])
    assert y.shape == (2, 3, 2, 2, 2)
    assert y[1, 0, 1, 0, 0] == 0.0 and math.isnan(y[0, 0, 1, 0, 0])
    s = R.outcome_array(finals, ["t3"], value="score")
    assert s[1, 0, 1, 0, 0] == 0.5


def test_losses_count_infrastructure_only():
    rs = [
        rec(task_id=f"t{i}", harness="H-OSW-fixed", ir_errors=3) for i in range(18)
    ] + [
        rec(task_id="t18", harness="H-OSW-fixed", status="infrastructure", score=None,
            infrastructure_type="engine_context_fallback"),
        rec(task_id="t18", harness="H-OSW-fixed", attempt=2, score=1.0),
        rec(task_id="t19", harness="H-OSW-fixed", score=0.0, metric_exception=True),
        rec(task_id="t20", harness="H-OSW-fixed", status="cap_truncated", score=None),
    ]  # fmt: skip
    loss = R.first_attempt_losses(rs, "A1-9B-S1")[("9B", "H-OSW-fixed")]
    assert (loss.first_attempts, loss.infrastructure) == (20, 1)
    assert loss.share == 0.05
    assert rules.dr0({("9B", "H-OSW-fixed"): loss}, True)["fires"] is False
    rs.append(rec(task_id="t21", harness="H-OSW-fixed", status="infrastructure", score=None,
                  infrastructure_type="vm_boot"))  # fmt: skip
    loss = R.first_attempt_losses(rs, "A1-9B-S1")[("9B", "H-OSW-fixed")]
    out = rules.dr0({("9B", "H-OSW-fixed"): loss}, True)
    assert out["fires"] and "cell loss" in out["reasons"][0]
    assert R.event_counts(rs, "ir_errors")[("9B", "H-OSW-fixed")] == 54
    assert R.metric_exception_counts(rs)[("9B", "H-OSW-fixed")] == 1


def test_base_and_extension_completion():
    base = ["t1"]
    rs = [rec(task_id="t1", harness=h, rerun=r) for h in R.HARNESSES for r in R.RERUNS]
    assert R.base_complete(rs, "A1-9B-S1", "9B", "S1", base)
    rs[0] = rec(task_id="t1", harness="H-OSW-fixed", rerun=1, status="infrastructure",
                score=None, infrastructure_type="transport")  # fmt: skip
    assert not R.base_complete(rs, "A1-9B-S1", "9B", "S1", base)
    rs.append(
        rec(task_id="t1", harness="H-OSW-fixed", rerun=1, attempt=2, status="infrastructure",
            score=None, infrastructure_type="transport")
    )  # fmt: skip
    assert R.base_complete(rs, "A1-9B-S1", "9B", "S1", base)
    full = [
        rec(job=f"A1-{z}-{s}", size=z, session=s, task_id=t, harness=h, rerun=r,
            extension_block=1)
        for z in R.SIZES for s in R.SESSIONS for t in ("e1", "e2")
        for h in R.HARNESSES for r in R.RERUNS
    ]  # fmt: skip
    assert R.completed_extension_blocks(full, {1: ["e1", "e2"]}) == [1]
    full[-1] = dict(full[-1], status="cap_truncated", score=None)
    assert R.completed_extension_blocks(full, {1: ["e1", "e2"]}) == []


def test_first_divergence_and_uncertified_exposure():
    a = [{"prompt_sha256": "p1", "ir_sha256": "i1"}, {"prompt_sha256": "p2", "ir_sha256": "i2"}]
    b = [{"prompt_sha256": "p1", "ir_sha256": "i1"}, {"prompt_sha256": "pX", "ir_sha256": "i2"}]
    c = [{"prompt_sha256": "p1", "ir_sha256": "iX"}]
    assert R.first_divergence(a, b) == {"kind": "environment", "step": 2}
    assert R.first_divergence(a, c) == {"kind": "serving", "step": 1}
    assert R.first_divergence(a, a[:1]) == {"kind": "length", "step": 2}
    assert R.first_divergence(a, a)["kind"] == "identical"
    certified = R.certified_keysym_set()
    assert len(certified) == 33 and "Control_L" in certified and "F2" not in certified
    actions = [
        {"op": "key", "keys": ["Control_L", "c"]},
        {"op": "key", "keys": ["F2"]},
        {"op": "click", "x": 1, "y": 1, "modifiers": ["Hyper_L"]},
        {"op": "type", "text": "x"},
    ]
    assert R.uncertified_key_actions(actions, certified) == 2


def test_anchor_reading_set_and_dr_anchor():
    order = ["a", "b", "c", "d"]
    finals = {
        "a": {"status": "scored"},
        "b": {"status": "infrastructure"},
        "c": {"status": "scored"},
        "d": {"status": "cap_truncated"},
    }
    assert rules.anchor_reading_set(order, finals) == (["a", "c"], ["b"])
    assert rules.dr_anchor([], [], first_attempts=0, infrastructure_losses=0,
                           available=False)["outcome"] == "ANCHOR-UNAVAILABLE"  # fmt: skip
    rng = np.random.default_rng(0)
    pub = (rng.random((3, 64)) < 0.25).astype(float)
    ours = pub[0]
    ok = rules.dr_anchor(ours, pub, first_attempts=64, infrastructure_losses=1)
    assert ok["outcome"] == "ANCHOR-PASS"
    bad = rules.dr_anchor(np.zeros(64), pub, first_attempts=64, infrastructure_losses=0)
    assert bad["outcome"] == "ANCHOR-FAIL"
    few = rules.dr_anchor(ours[:50], pub[:, :50], first_attempts=50, infrastructure_losses=0)
    assert few["outcome"] == "ANCHOR-INCOMPLETE"
    lossy = rules.dr_anchor(ours, pub, first_attempts=64, infrastructure_losses=7)
    assert lossy["outcome"] == "ANCHOR-INCOMPLETE"


def test_dr1_dr2_dr4_dr5_and_predictions():
    assert rules.dr1([0.05, 0.09]) and not rules.dr1([0.05, 0.11])
    assert rules.dr2(0.02, 0.9, (-0.05, 0.05), 0.05)["class"] == "Present"
    assert rules.dr2(0.03, 0.04, (-0.05, 0.05), 0.05)["class"] == "Near-equivalent"
    assert rules.dr2(0.3, 0.3, (-0.05, 0.08), 0.05)["class"] == "Inconclusive"
    assert rules.dr2(0.3, 0.3, (-0.05, 0.05), 0.13)["class"] == "Inconclusive"
    assert rules.dr4({"A1-9B-S1": (0.0112, 20)})["exceeds_high"] is False
    assert rules.dr4({"A1-9B-S1": (0.0112, 20), "A1-4B-S1": (0.0130, 16)})["jobs"] == ["A1-4B-S1"]
    m = rules.M_SMALL
    assert rules.dr5(m + 0.01, 0.5, False)["outcome"] == "GO"
    assert rules.dr5(0.0, m - 0.01, False)["outcome"] == "NO-GO"
    assert rules.dr5(0.0, m + 0.01, False)["outcome"] == "INCONCLUSIVE"
    assert rules.dr5(0.0, rules.M_9B - 0.01, True) == {
        "outcome": "NO-GO",
        "M": rules.M_9B,
        "share": "pi_9B",
    }
    p = rules.predictions(
        excess_ub95=0.005, db_ci95=(0.21, 0.3), dr2_class="Present", dr1_fires=False,
        dr4_exceeds=True,
    )  # fmt: skip
    assert [p[k]["falsified"] for k in ("P1", "P2", "P3", "P4", "P5")] == [
        True, True, True, False, True
    ]  # fmt: skip
