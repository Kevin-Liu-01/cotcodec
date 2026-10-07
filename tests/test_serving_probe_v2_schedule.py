"""The launch-window ledger: reserved time for required points, reruns from slack only."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from harness.serving_probe_v2.config import is_required, load_config, phase_points
from harness.serving_probe_v2.schedule import FIRST, OPTIONAL, RERUN, LaunchLedger, PhaseBudget
from scripts import run_vllm_throughput_probe_v2 as probe

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v2.yaml")
JOB = CONFIG.job("a")


def _ledger() -> LaunchLedger:
    return probe.ledger_for(CONFIG, JOB, start=0.0)


def _simulate(
    durations: dict[str, float],
    invalid_first: set[str],
    *,
    start_minutes: tuple[float, float] = (2.4, 1.3),
    preamble: float = 0.3,
) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """Walk job a with the driver's stage order; times in minutes from the allocation start.

    Every attempt takes ``durations[point]`` (capped at its wall cap); a point in
    ``invalid_first`` is invalid on its first attempt and valid on its rerun.
    """
    ledger = _ledger()
    now = preamble * 60.0
    launched: list[tuple[str, str]] = []
    status: dict[str, str] = {}
    for index, phase in enumerate(JOB.phases):
        now += start_minutes[index] * 60.0
        roles = phase_points(phase)
        required = [*roles["smoke"], *roles["warmup"], *roles["required"]]
        reruns: list = []
        optional_reruns: list = []
        stages = [(FIRST, required), (RERUN, reruns), (OPTIONAL, list(roles["optional"]))]
        stages.append((RERUN, optional_reruns))
        done: set[str] = set()
        for kind, points in stages:
            for point in list(points):
                pending = [p.point_id for p in required if p.point_id not in done]
                pending = [p for p in pending if p != point.point_id]
                if not ledger.may_launch(
                    index,
                    now=now,
                    point_id=point.point_id,
                    kind=kind,
                    cap_minutes=point.max_minutes,
                    required_pending=pending,
                ):
                    status.setdefault(point.point_id, "not-run")
                    if kind == FIRST:
                        break
                    continue
                deadline = ledger.deadline(index, now=now, cap_minutes=point.max_minutes)
                took = min(60.0 * durations[point.point_id], deadline - now)
                now += took
                done.add(point.point_id)
                launched.append((point.point_id, kind))
                truncated = took < 60.0 * durations[point.point_id]
                if truncated:
                    status[point.point_id] = "truncated"
                elif kind != RERUN and point.point_id in invalid_first:
                    status[point.point_id] = "invalid"
                    (reruns if is_required(point) else optional_reruns).append(point)
                else:
                    status[point.point_id] = "valid"
    return launched, status


#: Wall time per attempt in v1 (job A, Slurm 442), minutes including preparation;
#: the warm-up (r3's steps 1-3, about 0.4 min in v1, then a cold step 20 estimated from
#: v1's r4 step 18) and the dummy phase's points are estimates; r1b is r1's time.
V1_DURATIONS = {
    "a-smoke": 0.06,
    "a-warmup": 1.25,
    "a1a": 0.70,
    "r1": 1.45,
    "r3": 7.58,
    "r4": 2.40,
    "a1b": 0.70,
    "a1c": 0.70,
    "r2": 2.0,
    "a2": 1.2,
    "f1": 0.75,
    "r1b": 1.45,
    "x1-smoke": 0.06,
    "x1-warmup": 1.25,
    "x1-a1": 0.68,
    "x1-r1": 1.38,
}


def test_static_reservation_fits_the_soft_stop() -> None:
    ledger = _ledger()
    assert ledger.soft == pytest.approx(51 * 60)
    assert ledger.hard == pytest.approx(56 * 60)
    real, dummy = ledger.phases
    assert real.reserved_minutes == pytest.approx(4 + 28.0)
    assert dummy.reserved_minutes == pytest.approx(3 + 8)
    assert ledger.bound(0) == pytest.approx((51 - 11) * 60)
    assert ledger.bound(1) == pytest.approx(51 * 60)
    assert ledger.hard_deadline(0) == ledger.bound(0)
    assert ledger.hard_deadline(1) == ledger.hard


def test_v1s_reruns_no_longer_cut_the_required_points() -> None:
    """v1's r3 and r4 were invalid twice and their reruns cut a1c, r2, f1, a2, d8, a6.

    With v1's timings and r3 and r4 invalid on their first attempt, every required
    first attempt (a1b, a1c and f1 included) launches before any rerun, the reruns
    run from slack, and the optional points (r1b last) and the X1 phase still run.
    """
    launched, status = _simulate(V1_DURATIONS, {"r3", "r4"})
    order = [point for point, _kind in launched]
    assert order.index("f1") < order.index("r3", order.index("a1c"))
    assert order.index("r2") < order.index("a2") < order.index("r1b") < order.index("x1-smoke")
    assert ("r3", RERUN) in launched and ("r4", RERUN) in launched
    assert all(status[name] == "valid" for name in V1_DURATIONS), status


def test_reruns_are_skipped_rather_than_taking_reserved_time() -> None:
    """If the engine start took 20 minutes, long reruns do not fit; required points still run."""
    launched, status = _simulate(V1_DURATIONS, {"r3", "r4", "a1a"}, start_minutes=(20.0, 1.3))
    first = [point for point, kind in launched if kind == FIRST]
    assert first == [
        "a-smoke",
        "a-warmup",
        "a1a",
        "r1",
        "r3",
        "r4",
        "a1b",
        "a1c",
        "f1",
        "x1-smoke",
        "x1-warmup",
        "x1-a1",
        "x1-r1",
    ]
    # About 4.1 minutes of slack remain: the a1a rerun (cap 1.5) fits, the r4 (3.5) and
    # r3 (12) reruns do not; of the optional points only a2 (cap 2) still fits.
    assert ("a1a", RERUN) in launched
    assert ("r4", RERUN) not in launched and ("r3", RERUN) not in launched
    assert status["r3"] == "invalid" and status["r4"] == "invalid"
    assert (status["r2"], status["a2"], status["r1b"]) == ("not-run", "valid", "not-run")
    assert all(status[name] == "valid" for name in ("x1-a1", "x1-r1"))


def test_required_first_attempts_always_launch_within_their_reservation() -> None:
    """Random attempt times within each cap and random invalid points (2,000 draws)."""
    rng = np.random.default_rng(20261007)
    names = list(V1_DURATIONS)
    caps = {p.point_id: p.max_minutes for p in CONFIG.points.values()}
    for _draw in range(2000):
        durations = {name: float(rng.uniform(0.05, 1.0) * caps[name]) for name in names}
        invalid = {name for name in names if rng.uniform() < 0.3}
        starts = (float(rng.uniform(0.5, 4.0)), float(rng.uniform(0.5, 3.0)))
        launched, status = _simulate(durations, invalid, start_minutes=starts, preamble=2.0)
        required = [p.point_id for p in CONFIG.points.values() if is_required(p)]
        assert all((name, FIRST) in launched for name in required), (durations, starts)
        assert all(status[name] != "truncated" for name in required)


def test_slack_rule_and_decision_record() -> None:
    ledger = LaunchLedger(
        start=100.0,
        allocation_minutes=10,
        soft_fraction=1.0,
        hard_margin_minutes=1,
        phases=[PhaseBudget("p", 1.0, {"x": 2.0, "y": 3.0})],
    )
    # Bound at 600 s after start; pending y (180 s) plus a 2-minute rerun need 300 s.
    assert ledger.may_launch(
        0, now=400.0, point_id="z", kind=RERUN, cap_minutes=2, required_pending=["y"]
    )
    assert not ledger.may_launch(
        0, now=401.0, point_id="z", kind=RERUN, cap_minutes=2, required_pending=["y"]
    )
    assert ledger.may_launch(0, now=699.0, point_id="y", kind=FIRST, cap_minutes=3)
    assert not ledger.may_launch(0, now=700.0, point_id="y", kind=FIRST, cap_minutes=3)
    assert [d["launched"] for d in ledger.decisions] == [True, False, True, False]
    assert ledger.decisions[1] == {
        "phase": "p",
        "point": "z",
        "kind": RERUN,
        "at_s": 301.0,
        "bound_s": 600.0,
        "needed_s": 300.0,
        "launched": False,
    }
    assert ledger.deadline(0, now=650.0, cap_minutes=3) == ledger.hard
