"""Contamination rule v2, including v1's false contamination reproduced from its evidence."""

from __future__ import annotations

import json
import subprocess
import time
import types
from pathlib import Path

import pytest

from harness.serving_probe.metrics import GpuSample
from harness.serving_probe_v2 import contamination as cont
from harness.serving_probe_v2.contamination import (
    DEVICE_MODE,
    ENGINE,
    OTHER,
    PID_MODE,
    UNRESOLVED,
    AppRow,
    AppsSnapshot,
)
from scripts import run_vllm_throughput_probe as v1

PROJECT_ROOT = Path(__file__).resolve().parents[1]
V1_JOB_A = (
    PROJECT_ROOT
    / "program"
    / "evidence"
    / "2026-10-07"
    / "serving-throughput-probe-v1"
    / "jobs"
    / "a-442"
    / "probe"
)
UUID = "GPU-00000000-1111-2222-3333-444444444444"
ENGINE_PID = 1824294
GAP = 300.0


def _v1() -> tuple[dict, dict]:
    summary = json.loads((V1_JOB_A / "summary.json").read_text(encoding="utf-8"))
    r3 = json.loads((V1_JOB_A / "points" / "r3.json").read_text(encoding="utf-8"))
    return summary, r3


def _samples(memory: float, n: int = 10) -> list[GpuSample]:
    return [GpuSample(float(i), memory, 90.0, 500.0, 1800.0) for i in range(n)]


def _snapshots(device: float, *extra: AppRow, n: int = 5, own: float | None = None) -> list:
    used = device - GAP if own is None else own
    engine = AppRow(UUID, ENGINE_PID, "[Not Found]", used, UNRESOLVED)
    return [AppsSnapshot(float(i), True, (engine, *extra), device) for i in range(n)]


def _assess(reservation, device_peak, snapshots, needed=1):
    return cont.assess_contamination(
        reservation=reservation,
        device_peak_mib=device_peak,
        snapshots=snapshots,
        needed_snapshots=needed,
        device_margin_mib=2048,
        own_margin_mib=2048,
        unattributed_margin_mib=1024,
    )


def test_v1_evidence_shows_the_false_contamination() -> None:
    """r3 failed only no_contamination: 76,611 MiB against 74,301 + 2,048 = 76,349 MiB."""
    summary, r3 = _v1()
    reservation = summary["phases"]["real"]["reservation_mib"]
    peak = r3["gpu"]["peak_memory_used_mib"]
    assert (reservation, peak) == (74301.0, 76611.0)
    assert r3["status"] == "invalid"
    assert {name for name, ok in r3["checks"].items() if not ok} == {"no_contamination"}
    for attempt in r3["superseded_attempts"]:
        assert {name for name, ok in attempt["checks"].items() if not ok} == {"no_contamination"}
    assert cont.v1_no_contamination(peak, reservation, 2048) is False
    # The frozen v1 assessment reproduces the verdict from the recorded point.
    status, _flags, checks = v1.assess_point(
        r3["result"],
        counters=r3["counter_check"],
        gpu=r3["gpu"],
        reservation_mib=reservation,
        reservation_required=True,
        margin_mib=2048,
        api_cpu_pct=r3["api_server_cpu_pct"],
        client_cpu_pct=r3["client_cpu_pct"],
        flag_pct=90,
        stop_reason=r3["stop_reason"],
        ran_to_end=r3["ran_to_end"],
        caches_ok=True,
        min_samples=1,
    )
    assert status == "invalid" and checks["no_contamination"] is False


@pytest.mark.parametrize(
    ("warmup_peak", "flagged"),
    [
        (76611.0, False),  # the warm-up reached r3's footprint (the largest shape)
        (75807.0, False),  # it reached only r1's (own growth of 804 MiB)
        (74301.0, True),  # it reached only the smoke's (growth 2,310 MiB: flagged, valid)
    ],
)
def test_v2_pid_mode_keeps_v1s_r3_valid(warmup_peak: float, flagged: bool) -> None:
    _summary, r3 = _v1()
    peak = r3["gpu"]["peak_memory_used_mib"]
    reservation, verdict = cont.measure_reservation(_samples(warmup_peak), _snapshots(warmup_peak))
    assert verdict["pass"] and reservation.mode == PID_MODE
    assert reservation.own_pids == frozenset({ENGINE_PID})
    checks, flags, details = _assess(reservation, peak, _snapshots(peak))
    assert checks == {
        "attribution_sampled": True,
        "no_foreign_process": True,
        "no_unattributed_memory": True,
    }
    assert ("own-footprint-above-reservation" in flags) is flagged
    assert details["foreign_pids"] == []


def test_v2_device_mode_needs_the_largest_shape_reservation() -> None:
    """Without attribution, the largest-shape reservation is what admits v1's r3."""
    _summary, r3 = _v1()
    peak = r3["gpu"]["peak_memory_used_mib"]
    after_warmup, verdict = cont.measure_reservation(_samples(76611.0), [])
    assert verdict["mode"] == DEVICE_MODE
    assert _assess(after_warmup, peak, [])[0] == {"no_contamination": True}
    after_smoke, _ = cont.measure_reservation(_samples(74301.0), [])
    assert _assess(after_smoke, peak, [])[0] == {"no_contamination": False}


def test_a_small_foreign_process_is_caught_by_pid_inside_the_device_margin() -> None:
    reservation, _ = cont.measure_reservation(_samples(76611.0), _snapshots(76611.0))
    foreign = AppRow(UUID, 99, "[Not Found]", 600.0, UNRESOLVED)
    device = 76611.0 + 600.0
    checks, _flags, details = _assess(reservation, device, _snapshots(device, foreign, own=76311))
    assert checks["no_foreign_process"] is False and details["foreign_pids"] == [99]
    # The device-level rule alone would not see it (600 MiB < 2,048 MiB margin).
    assert cont.v1_no_contamination(device, 76611.0, 2048) is True


def test_an_unlisted_foreign_process_is_unattributed_memory() -> None:
    reservation, _ = cont.measure_reservation(_samples(76611.0), _snapshots(76611.0))
    assert reservation.unattributed_mib == pytest.approx(GAP)
    device = 76611.0 + 1500.0
    checks, _flags, details = _assess(reservation, device, _snapshots(device, own=76311.0))
    assert checks["no_unattributed_memory"] is False
    assert details["unattributed_peak_mib"] == pytest.approx(1800.0)
    assert details["unattributed_ceiling_mib"] == pytest.approx(GAP + 1024)


def test_an_engine_tree_pid_is_always_own() -> None:
    reservation, _ = cont.measure_reservation(_samples(76611.0), _snapshots(76611.0))
    child = AppRow(UUID, 7, "VLLM::EngineCore", 200.0, ENGINE)
    checks, _flags, _details = _assess(
        reservation, 76811.0, _snapshots(76811.0, child, own=76311.0)
    )
    assert checks["no_foreign_process"] is True and checks["no_unattributed_memory"] is True


def test_pid_mode_needs_enough_readable_snapshots() -> None:
    reservation, _ = cont.measure_reservation(_samples(76611.0), _snapshots(76611.0))
    unreadable = [AppsSnapshot(0.0, False, error="nvidia-smi failed")]
    checks, _flags, _details = _assess(reservation, 76611.0, unreadable, needed=1)
    assert checks["attribution_sampled"] is False
    assert checks["no_unattributed_memory"] is False
    assert cont.min_snapshots(450.0, 2.0, 0.2) == 45
    assert cont.min_snapshots(0.5, 2.0, 0.2) == 1


def test_reservation_modes_and_failures() -> None:
    assert cont.measure_reservation([], _snapshots(1.0))[0] is None
    # No readable listing, or an empty one, falls back to the device rule.
    broken = [AppsSnapshot(0.0, False, error="x")]
    assert cont.measure_reservation(_samples(5.0), broken)[1]["mode"] == DEVICE_MODE
    empty = [AppsSnapshot(0.0, True, (), 5.0)]
    assert cont.measure_reservation(_samples(5.0), empty)[0].mode == DEVICE_MODE
    no_memory = [
        AppsSnapshot(0.0, True, (AppRow(UUID, ENGINE_PID, "[Not Found]", None, UNRESOLVED),), 5.0)
    ]
    assert cont.measure_reservation(_samples(5.0), no_memory)[0].mode == DEVICE_MODE
    # A process of this container outside the engine fails G0.9.
    other = AppRow(UUID, 12, "python", 500.0, OTHER)
    reservation, verdict = cont.measure_reservation(_samples(5.0), _snapshots(5.0, other))
    assert reservation is None and "outside the engine" in verdict["reason"]
    # A process list that changes inside the window fails G0.9.
    changing = _snapshots(5.0) + _snapshots(5.0, AppRow(UUID, 99, "[N]", 1.0, UNRESOLVED))
    reservation, verdict = cont.measure_reservation(_samples(5.0), changing)
    assert reservation is None and "changed" in verdict["reason"]
    # Container-namespace PIDs in the engine's tree name their own basis.
    translated = [AppsSnapshot(0.0, True, (AppRow(UUID, 40, "vllm", 4.0, ENGINE),), 5.0)]
    reservation, _ = cont.measure_reservation(_samples(5.0), translated)
    assert reservation.basis == "container-namespace PIDs in the engine's process tree"


def test_baseline_needs_an_empty_listing() -> None:
    assert cont.baseline_apps_verdict([AppsSnapshot(0.0, True, (), 0.0)])["pass"] is True
    listed = [AppsSnapshot(0.0, True, (AppRow(UUID, 5, "[N]", 600.0, UNRESOLVED),), 600.0)]
    verdict = cont.baseline_apps_verdict(listed)
    assert verdict["pass"] is False and verdict["pids"] == [5]
    unavailable = cont.baseline_apps_verdict([AppsSnapshot(0.0, False, error="e")])
    assert unavailable == {"pass": True, "status": "unavailable", "errors": ["e"]}
    # Judged on the last readable snapshot: a process that has left no longer counts.
    leaving = listed + [AppsSnapshot(1.0, True, (), 0.0)]
    assert cont.baseline_apps_verdict(leaving)["pass"] is True


def test_parsers() -> None:
    text = (
        f"{UUID}, 1824294, [Not Found], 74001\n"
        f"{UUID}, 12, /usr/bin/python3, with, commas, 500\n"
        f"{UUID}, 13, x, [N/A]\n"
    )
    assert cont.parse_compute_apps(text) == [
        (UUID, 1824294, "[Not Found]", 74001.0),
        (UUID, 12, "/usr/bin/python3, with, commas", 500.0),
        (UUID, 13, "x", None),
    ]
    assert cont.parse_compute_apps("No running processes found\n") == []
    assert cont.parse_compute_apps("") == []
    with pytest.raises(ValueError):
        cont.parse_compute_apps("garbage")
    assert cont.parse_device_memory(f"{UUID}, 74301\n") == (UUID, 74301.0)
    with pytest.raises(ValueError, match="exactly one"):
        cont.parse_device_memory(f"{UUID}, 1\n{UUID}, 2\n")


def test_take_snapshot_classifies_pids(tmp_path: Path) -> None:
    proc = tmp_path / "proc"
    for pid in (40, 12):
        (proc / str(pid)).mkdir(parents=True)

    def runner(argv, **kwargs):
        if "--query-compute-apps" in argv[1]:
            out = f"{UUID}, 40, vllm, 70000\n{UUID}, 12, python, 500\n{UUID}, 9999, [N], 10\n"
        else:
            out = f"{UUID}, 70810\n"
        return types.SimpleNamespace(stdout=out)

    snapshot = cont.take_snapshot(engine_pids=frozenset({40}), runner=runner, proc_root=proc)
    assert snapshot.ok and snapshot.device_mib == 70810.0
    assert [(row.pid, row.origin) for row in snapshot.rows] == [
        (40, ENGINE),
        (12, OTHER),
        (9999, UNRESOLVED),
    ]

    def failing(argv, **kwargs):
        raise subprocess.CalledProcessError(9, argv)

    failed = cont.take_snapshot(engine_pids=frozenset(), runner=failing, proc_root=proc)
    assert failed.ok is False and "CalledProcessError" in failed.error

    def other_gpu(argv, **kwargs):
        if "--query-compute-apps" in argv[1]:
            return types.SimpleNamespace(stdout="GPU-other, 40, vllm, 1\n")
        return types.SimpleNamespace(stdout=f"{UUID}, 1\n")

    assert cont.take_snapshot(engine_pids=frozenset(), runner=other_gpu).ok is False


def test_apps_sampler_polls_into_a_window_and_a_trace(tmp_path: Path) -> None:
    calls = []

    def snapshot(*, engine_pids):
        calls.append(engine_pids)
        row = AppRow(UUID, 40, "vllm", 1.0, ENGINE)
        return AppsSnapshot(time.perf_counter(), True, (row,), 2.0)

    sampler = cont.AppsSampler(tmp_path / "apps.csv", 0.01, lambda: {40}, snapshot=snapshot)
    start = time.perf_counter()
    sampler.start()
    time.sleep(0.1)
    sampler.stop()
    window = sampler.window(start, time.perf_counter())
    assert len(window) >= 2 and calls[0] == frozenset({40})
    lines = (tmp_path / "apps.csv").read_text().splitlines()
    assert len(lines) >= 2 and ",40,vllm,1.0,engine," in lines[0]
