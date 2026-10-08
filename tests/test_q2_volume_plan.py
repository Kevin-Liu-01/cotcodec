"""Q2 A4 volume plan: per-class and per-boot zero-failure bounds (review finding on A4 power)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from harness.q2.action_path import catalog as cat
from harness.q2.action_path import volume
from harness.q2.action_path.ir import parse_action

HERE = Path(cat.__file__).resolve().parent


@pytest.fixture(scope="module")
def plan():
    return json.loads((HERE / "volume_plan.json").read_text(encoding="utf-8"))


def test_the_old_uniform_design_bounds_entries_only_at_about_four_percent():
    # 6,020 uniform trials over 86 entries: 70 per entry (90 with A1's 20).
    assert pytest.approx(4.976e-4, rel=1e-3) == volume.upper_bound(6020)
    assert volume.upper_bound(70) == pytest.approx(0.0419, rel=1e-2)
    assert volume.upper_bound(90) == pytest.approx(0.0327, rel=1e-2)
    # An entry failing 1% of the time passes A1 + A4 with probability 0.99^90.
    assert pytest.approx(0.405, abs=1e-3) == 0.99**90


def test_zero_failure_sample_sizes():
    assert pytest.approx(0.05 / 8) == volume.ALPHA_EACH
    assert volume.ACTIONS_PER_CLASS == 10148
    assert volume.MIN_SESSIONS == 1013
    n = volume.zero_failure_n(5e-4, volume.ALPHA_EACH)
    assert (1 - 5e-4) ** n <= volume.ALPHA_EACH < (1 - 5e-4) ** (n - 1)


def test_action_classes():
    def cls(raw):
        return volume.action_class(parse_action(raw))

    assert cls({"op": "click", "x": 1, "y": 1}) == "click_left"
    assert cls({"op": "click", "x": 1, "y": 1, "count": 2}) == "click_other"
    assert cls({"op": "click", "x": 1, "y": 1, "modifiers": ["Shift_L"]}) == "click_other"
    assert cls({"op": "click", "x": 1, "y": 1, "button": 3}) == "click_other"
    assert cls({"op": "wait", "ms": 5}) is None
    with pytest.raises(ValueError):
        cls({"op": "key_down", "keys": ["Shift_L"]})


def test_plan_meets_every_class_and_boot_target(plan):
    assert plan == volume.build_plan(cat.load())
    rule = plan["rule"]
    assert rule["episode_loss_bound_pp"] == 1.5
    for name in volume.CLASSES:
        assert plan["class_actions"][name] >= volume.ACTIONS_PER_CLASS, name
        assert plan["class_upper_bound_family_95"][name] <= 5e-4, name
    assert plan["sessions"] >= volume.MIN_SESSIONS
    assert plan["boot_upper_bound_family_95"] <= 5e-3
    gating = cat.validate(cat.load())["gating"]
    assert sorted(plan["entries"]) == sorted(gating)
    for entry_id, row in plan["entries"].items():
        assert row["reps"] >= volume.MIN_REPS and row["reps"] % 2 == 0, entry_id
    assert plan["trials"] == sum(row["reps"] for row in plan["entries"].values())
    # Within a class, every pure entry gets the same repetitions.
    for name in volume.CLASSES:
        reps = {r["reps"] for r in plan["entries"].values() if r["pure_class"] == name}
        assert len(reps) == 1, name


def test_sessions_are_bounded_and_reproduce_the_pinned_order(plan):
    realized = volume.sessions(plan)
    for setting, cut in realized.items():
        assert len(cut) == plan["sessions_per_setting"][setting]
        sizes = [len(s) for s in cut]
        assert max(sizes) <= volume.SESSION_TRIALS and max(sizes) - min(sizes) <= 1
        assert sum(sizes) == plan["trials_per_setting"][setting]
    assert volume.order_sha256(plan) == plan["order_sha256"]
    counts: dict[str, int] = {}
    for cut in realized.values():
        for session in cut:
            for entry_id in session:
                counts[entry_id] = counts.get(entry_id, 0) + 1
    assert counts == {e: r["reps"] for e, r in plan["entries"].items()}
    assert math.isclose(plan["trials"] / plan["sessions"], 59.95, abs_tol=0.1)
