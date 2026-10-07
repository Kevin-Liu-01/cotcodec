"""Contamination rule v2: foreign processes by PID, own growth by a largest-shape reservation.

serving-throughput-probe-v1 measured the engine's reservation after a one-image
smoke and declared a point contaminated when device ``memory.used`` exceeded it
by more than 2 GiB. Its own footprint under 20-screenshot prompts (76,611 MiB)
crossed that line (74,301 + 2,048 = 76,349 MiB) with no other process on the
GPU, so r3 and r4 were invalid only by this rule. v2 separates the two causes:

* **Foreign processes** are identified by PID. A background poller lists the
  compute processes on the (only visible) GPU with their memory, next to the
  device's ``memory.used``. A PID is the engine's own when it is in the engine's
  process tree in this container, or when it is one of the PIDs that appeared on
  the GPU, empty at G0.8, while the engine started (NVML reports host-namespace
  PIDs inside a container, which ``/proc`` here cannot resolve). Any other PID is
  foreign. Memory that no listed process accounts for, beyond what was
  unaccounted at the reservation plus a margin, is treated as a foreign process
  NVML does not list.
* **The engine's own growth** is bounded by a reservation measured after a
  warm-up at the largest registered prompt shape (G0.9). With PID attribution
  ("pid" mode), growth of the engine's own processes is not contamination and is
  checked against a separate own-footprint ceiling (reservation plus a margin),
  flagged when exceeded. Without attribution ("device" mode, when NVML lists no
  process here) the device peak must stay within the largest-shape reservation
  plus the margin, as v1's rule did with its smaller reservation.
"""

from __future__ import annotations

import csv
import math
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness.serving_probe.metrics import GpuSample

APPS_QUERY = [
    "nvidia-smi",
    "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
    "--format=csv,noheader,nounits",
]
DEVICE_QUERY = ["nvidia-smi", "--query-gpu=uuid,memory.used", "--format=csv,noheader,nounits"]
#: nvidia-smi's own line when no compute process holds the GPU.
NO_PROCESSES = "No running processes found"

ENGINE, UNRESOLVED, OTHER = "engine", "unresolved", "other"
PID_MODE, DEVICE_MODE = "pid", "device"


@dataclass(frozen=True)
class AppRow:
    gpu_uuid: str
    pid: int
    name: str
    used_mib: float | None
    #: ``engine``: in the engine's process tree in this container; ``unresolved``: no
    #: such PID in this container (a host-namespace PID); ``other``: a process in this
    #: container outside the engine's tree.
    origin: str


@dataclass(frozen=True)
class AppsSnapshot:
    t: float
    ok: bool
    rows: tuple[AppRow, ...] = ()
    device_mib: float | None = None
    error: str | None = None

    @property
    def pids(self) -> frozenset[int]:
        return frozenset(row.pid for row in self.rows)


def _number(text: str) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_compute_apps(text: str) -> list[tuple[str, int, str, float | None]]:
    """Rows of ``--query-compute-apps=gpu_uuid,pid,process_name,used_memory`` (nounits).

    The process name may contain commas, so the UUID and PID are split from the
    left and the memory from the right. A malformed row raises ``ValueError``.
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line == NO_PROCESSES:
            continue
        head = line.split(",", 2)
        if len(head) != 3:
            raise ValueError(f"unparseable compute-apps row {line!r}")
        name, separator, memory = head[2].rpartition(",")
        if not separator:
            raise ValueError(f"unparseable compute-apps row {line!r}")
        rows.append((head[0].strip(), int(head[1].strip()), name.strip(), _number(memory.strip())))
    return rows


def parse_device_memory(text: str) -> tuple[str, float]:
    """``(uuid, memory.used MiB)`` of the only visible GPU; anything else raises."""
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError(f"expected exactly one visible GPU, nvidia-smi listed {len(lines)}")
    uuid, _, memory = lines[0].partition(",")
    value = _number(memory.strip())
    if value is None:
        raise ValueError(f"unparseable memory.used {memory!r}")
    return uuid.strip(), value


def classify(pid: int, engine_pids: frozenset[int], proc_root: Path = Path("/proc")) -> str:
    if pid in engine_pids:
        return ENGINE
    return OTHER if (proc_root / str(pid)).is_dir() else UNRESOLVED


def take_snapshot(
    *,
    engine_pids: frozenset[int],
    runner: Callable[..., Any] = subprocess.run,
    proc_root: Path = Path("/proc"),
    clock: Callable[[], float] = time.perf_counter,
) -> AppsSnapshot:
    """One compute-apps listing and the device memory right after it."""
    t = clock()
    try:
        apps = runner(APPS_QUERY, check=True, capture_output=True, text=True, timeout=20)
        device = runner(DEVICE_QUERY, check=True, capture_output=True, text=True, timeout=20)
        uuid, device_mib = parse_device_memory(device.stdout)
        rows = []
        for gpu_uuid, pid, name, used in parse_compute_apps(apps.stdout):
            if gpu_uuid != uuid:
                raise ValueError(f"compute app on {gpu_uuid}, not the visible GPU {uuid}")
            rows.append(AppRow(gpu_uuid, pid, name, used, classify(pid, engine_pids, proc_root)))
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return AppsSnapshot(t, False, error=f"{type(exc).__name__}: {exc}"[:300])
    return AppsSnapshot(t, True, tuple(rows), device_mib)


class AppsSampler:
    """Background poller of the GPU's compute processes (``interval_s`` apart) with a CSV trace.

    ``engine_pids`` returns the running engine's process tree (empty when no engine
    runs); it is read at each snapshot, so a PID's origin is fixed when it is seen.
    """

    def __init__(
        self,
        csv_path: Path,
        interval_s: float,
        engine_pids: Callable[[], Iterable[int]],
        snapshot: Callable[..., AppsSnapshot] = take_snapshot,
    ) -> None:
        self.csv_path = csv_path
        self.interval_s = interval_s
        self.engine_pids = engine_pids
        self._snapshot = snapshot
        self._snapshots: list[AppsSnapshot] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._run, name="apps-sampler", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        with self.csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            while not self._stop.is_set():
                snapshot = self._snapshot(engine_pids=frozenset(self.engine_pids()))
                with self._lock:
                    self._snapshots.append(snapshot)
                for row in snapshot.rows or [None]:
                    writer.writerow(
                        [
                            f"{snapshot.t:.3f}",
                            int(snapshot.ok),
                            snapshot.device_mib,
                            *(
                                ["", "", "", "", ""]
                                if row is None
                                else [row.gpu_uuid, row.pid, row.name, row.used_mib, row.origin]
                            ),
                            snapshot.error or "",
                        ]
                    )
                handle.flush()
                self._stop.wait(self.interval_s)

    def window(self, start: float, end: float) -> list[AppsSnapshot]:
        with self._lock:
            return [s for s in self._snapshots if start <= s.t <= end]

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=30)


def min_snapshots(duration_s: float, interval_s: float, fraction: float) -> int:
    """Snapshots a point needs: ``fraction`` of those its wall time implies, at least one."""
    return max(1, math.floor(fraction * max(0.0, duration_s) / interval_s))


def baseline_apps_verdict(snapshots: Sequence[AppsSnapshot]) -> dict[str, Any]:
    """G0.8's PID condition: before an engine starts, the GPU lists no compute process.

    Judged on the last readable snapshot of the baseline window. No readable
    snapshot leaves the condition ``unavailable`` (the device checks still apply).
    """
    readable = [s for s in snapshots if s.ok]
    if not readable:
        errors = sorted({str(s.error) for s in snapshots})[:3]
        return {"pass": True, "status": "unavailable", "errors": errors}
    last = readable[-1]
    return {
        "pass": not last.rows,
        "status": "empty" if not last.rows else "processes-listed",
        "pids": sorted(last.pids),
        "names": sorted({row.name for row in last.rows}),
    }


@dataclass(frozen=True)
class Reservation:
    """The engine's footprint after the largest-shape warm-up (G0.9)."""

    mode: str
    basis: str
    device_mib: float
    own_pids: frozenset[int] = frozenset()
    own_mib: float | None = None
    unattributed_mib: float | None = None
    snapshots: int = 0
    details: Mapping[str, Any] = field(default_factory=dict)

    def describe(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "basis": self.basis,
            "device_mib": self.device_mib,
            "own_pids": sorted(self.own_pids),
            "own_mib": self.own_mib,
            "unattributed_mib": self.unattributed_mib,
            "snapshots": self.snapshots,
            **dict(self.details),
        }


def _own_rows(snapshot: AppsSnapshot, own_pids: frozenset[int]) -> list[AppRow]:
    return [row for row in snapshot.rows if row.pid in own_pids or row.origin == ENGINE]


def measure_reservation(
    gpu_samples: Sequence[GpuSample], snapshots: Sequence[AppsSnapshot]
) -> tuple[Reservation | None, dict[str, Any]]:
    """G0.9: the reservation and the attribution mode, from the warm-up and the window after it.

    Fails (``None``) when the device sampler gave nothing, when a process in this
    container but outside the engine's tree holds the GPU, or when the listed
    PIDs change inside the window. Falls back to ``device`` mode when no snapshot
    is readable, when NVML lists no process here, or when a listed process has
    no memory figure. Otherwise ``pid`` mode, with the listed PIDs as the
    engine's own.
    """
    if not gpu_samples:
        return None, {"pass": False, "reason": "no device sample in the reservation window"}
    device_mib = max(sample.memory_used_mib for sample in gpu_samples)
    readable = [s for s in snapshots if s.ok]
    verdict: dict[str, Any] = {
        "pass": True,
        "device_mib": device_mib,
        "device_samples": len(gpu_samples),
        "snapshots": len(snapshots),
        "readable_snapshots": len(readable),
    }

    def device(basis: str) -> tuple[Reservation, dict[str, Any]]:
        reservation = Reservation(DEVICE_MODE, basis, device_mib, snapshots=len(readable))
        return reservation, {**verdict, "mode": DEVICE_MODE, "basis": basis}

    if not readable:
        return device("no readable compute-apps snapshot")
    others = sorted({row.pid for s in readable for row in s.rows if row.origin == OTHER})
    if others:
        return None, {
            **verdict,
            "pass": False,
            "reason": f"processes {others} in this container but outside the engine hold the GPU",
        }
    pid_sets = {s.pids for s in readable}
    if pid_sets == {frozenset()}:
        return device("NVML lists no compute process in this container")
    if len(pid_sets) != 1:
        return None, {
            **verdict,
            "pass": False,
            "reason": "the GPU's process list changed inside the reservation window",
            "pid_sets": [sorted(pids) for pids in pid_sets],
        }
    if any(row.used_mib is None for s in readable for row in s.rows) or any(
        s.device_mib is None for s in readable
    ):
        return device("NVML reports no per-process or device memory")
    (own_pids,) = pid_sets
    origins = sorted({row.origin for s in readable for row in s.rows})
    basis = {
        (ENGINE,): "container-namespace PIDs in the engine's process tree",
        (UNRESOLVED,): "host-namespace PIDs that appeared on the GPU, empty at G0.8, "
        "while the engine started",
    }.get(tuple(origins), "engine-tree and host-namespace PIDs")
    own_mib = max(sum(float(row.used_mib or 0.0) for row in s.rows) for s in readable)
    unattributed = max(
        float(s.device_mib or 0.0) - sum(float(row.used_mib or 0.0) for row in s.rows)
        for s in readable
    )
    reservation = Reservation(
        PID_MODE,
        basis,
        device_mib,
        own_pids=own_pids,
        own_mib=own_mib,
        unattributed_mib=unattributed,
        snapshots=len(readable),
        details={"origins": origins},
    )
    return reservation, {**verdict, "mode": PID_MODE, **reservation.describe()}


def assess_contamination(
    *,
    reservation: Reservation,
    device_peak_mib: float | None,
    snapshots: Sequence[AppsSnapshot],
    needed_snapshots: int,
    device_margin_mib: float,
    own_margin_mib: float,
    unattributed_margin_mib: float,
) -> tuple[dict[str, bool], list[str], dict[str, Any]]:
    """Contamination checks of one measured point; returns (checks, flags, details).

    ``pid`` mode: ``attribution_sampled`` (enough readable snapshots),
    ``no_foreign_process`` (every listed PID is the engine's) and
    ``no_unattributed_memory`` (device memory minus the engine's processes stays
    within the reservation's unattributed memory plus the margin). Own growth
    above the own-footprint ceiling, or a device peak above the largest-shape
    reservation plus the device margin, is flagged, not invalid. ``device``
    mode: ``no_contamination`` (device peak within the largest-shape
    reservation plus the device margin).
    """
    device_ceiling = reservation.device_mib + device_margin_mib
    details: dict[str, Any] = {
        "mode": reservation.mode,
        "device_peak_mib": device_peak_mib,
        "device_ceiling_mib": device_ceiling,
    }
    flags: list[str] = []
    if reservation.mode == DEVICE_MODE:
        within = device_peak_mib is not None and device_peak_mib <= device_ceiling
        return {"no_contamination": within}, flags, details
    readable = [s for s in snapshots if s.ok]
    foreign: set[int] = set()
    own_peak = 0.0
    unattributed_peak: float | None = None
    for snapshot in readable:
        own = _own_rows(snapshot, reservation.own_pids)
        foreign |= {row.pid for row in snapshot.rows if row not in own}
        own_mib = sum(float(row.used_mib or 0.0) for row in own)
        own_peak = max(own_peak, own_mib)
        if snapshot.device_mib is not None:
            gap = float(snapshot.device_mib) - own_mib
            unattributed_peak = gap if unattributed_peak is None else max(unattributed_peak, gap)
    unattributed_ceiling = float(reservation.unattributed_mib or 0.0) + unattributed_margin_mib
    own_ceiling = float(reservation.own_mib or 0.0) + own_margin_mib
    checks = {
        "attribution_sampled": len(readable) >= needed_snapshots,
        "no_foreign_process": not foreign,
        "no_unattributed_memory": unattributed_peak is not None
        and unattributed_peak <= unattributed_ceiling,
    }
    if readable and own_peak > own_ceiling:
        flags.append("own-footprint-above-reservation")
    if device_peak_mib is not None and device_peak_mib > device_ceiling:
        flags.append("device-above-largest-shape-reservation")
    details.update(
        {
            "snapshots": len(readable),
            "needed_snapshots": needed_snapshots,
            "foreign_pids": sorted(foreign),
            "own_peak_mib": own_peak if readable else None,
            "own_ceiling_mib": own_ceiling,
            "unattributed_peak_mib": unattributed_peak,
            "unattributed_ceiling_mib": unattributed_ceiling,
        }
    )
    return checks, flags, details


def v1_no_contamination(
    peak_mib: float | None, reservation_mib: float | None, margin_mib: float
) -> bool:
    """serving-throughput-probe-v1's rule (section 7), kept to show what v2 replaces."""
    return (
        reservation_mib is not None
        and peak_mib is not None
        and peak_mib <= (reservation_mib + margin_mib)
    )


def describe_snapshots(snapshots: Sequence[AppsSnapshot]) -> dict[str, Any]:
    """A compact record of a window's listings (for the smoke and the warm-up)."""
    readable = [s for s in snapshots if s.ok]
    return {
        "snapshots": len(snapshots),
        "readable": len(readable),
        "pids": sorted({pid for s in readable for pid in s.pids}),
        "origins": sorted({row.origin for s in readable for row in s.rows}),
        "max_listed_mib": max(
            (sum(float(row.used_mib or 0.0) for row in s.rows) for s in readable), default=None
        ),
        "errors": sorted({str(s.error) for s in snapshots if not s.ok})[:3],
    }
