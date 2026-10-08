"""Q1 runner: one subprocess per work item, per-device worker slots, phase watchdog.

- **Isolation.** Every item (kernel x gate or audit channel x seed) runs in a
  fresh ``python -m harness.q1.worker`` process in its own session, so a
  hung or crashed candidate is killed with its whole process group and no
  state leaks between gates.
- **Slots.** One thread per slot (``cuda:N`` or ``cpu``) pulls items from a
  shared queue; a ``cuda:N`` slot runs its child with
  ``CUDA_VISIBLE_DEVICES=N`` and device ``cuda:0`` inside. Timing items run
  only on the dedicated timing slots, and correctness items never do.
  Several slots may name the same device; an item marked ``exclusive`` (a
  problem whose inputs alone fill much of the GPU) then waits until the
  device is empty and runs alone (``DeviceShare``), so concurrency can never
  turn a neighbour's memory use into a candidate's out-of-memory rejection.
  Items may also hold a number of capacity ``units`` (the memory-aware
  execution policy ``q1-stage0-exec/2``, ``harness.q1.memory``): a device's
  capacity is the number of slots naming it, and an item starts only when its
  units fit. With a ``MemoryGuard`` (``RunnerConfig.memory_guard``) an item
  also starts only when the larger of the device's reported used memory and
  the estimated peaks (``memory_bytes``) of this runner's running items, plus
  its own estimate, fits the guard's budget, unless nothing of this runner is
  running on the device (so the rule can never deadlock).
- **Contention retries.** An item that ran in a shared class (fewer units than
  the device's capacity) and either timed out or shows a GPU resource failure
  (CUDA out-of-memory, cuBLAS or cuDNN allocation failure; one list,
  ``harness.q1.faults``) is an infrastructure failure
  (``infra_failure-timeout-shared`` or ``infra_failure-oom-shared``): its rows
  are journaled as not final with ``retry_alone`` and it runs once more alone
  on its device (also after a resume). Alone, the outcome stands.
- **Watchdog.** Phases ``compile`` (from spawn), ``correctness`` and
  ``timing`` have their own limits (default 120 s, 180 s, 300 s). The child
  reports phase changes on a pipe; phases only move forward. On expiry the
  process group gets SIGKILL and the item gets a ``timeout`` row naming the
  phase: the first timeout ends that item.
- **Crashes.** A child that dies without writing rows gets one row: ``reject``
  if it died after the candidate loaded (``correctness``/``timing`` phase),
  otherwise ``error``. The worker runs candidate code only before it builds
  rows; a failure while building, validating or serialising rows is written
  by the worker itself as one ``error`` row (``infra_failure-harness-row``),
  so a harness fault after the candidate ran is never charged to it. After
  any crash or timeout on a GPU slot a health check (one small CUDA allocation)
  runs in a fresh process, after the item's units are released. A failed
  check never retires a slot by itself: the slot first drains its device
  (waits until no other item of this runner runs there) and repeats the check
  alone with backoff. Passing alone, the slot stays and the item's own row
  stands (a crash under contention that shows a resource failure is retried
  alone as above). Failing alone, the item is ``error``
  (``infra_failure-gpu-health-check``) and the device stops taking items: as
  ``gpu-health-fault`` when the failure is not an allocation failure (a fresh
  process cannot run on the device), or as ``gpu-memory-held`` when even an
  empty device cannot allocate (memory held outside this runner). Unstarted
  items stay queued for the next job either way.
- **Memory records.** A worker writes its process's peak CUDA memory; the
  runner appends it with the item's estimate and units to ``memory.jsonl``
  beside the journal (never to a row), for measured peaks in later jobs
  (``memory.measured_peaks``).
- **Infrastructure retries.** An item whose rows carry an ``infra_failure``
  reason is queued once more as the next attempt (the journal keeps both
  attempts; analyses read the final one). A second infrastructure failure is
  final and is excluded and listed by the analysis.
- **Journal.** Rows are appended to the append-only journal
  (``journal.py``); resume skips finished items and reruns the rest with the
  next attempt number. An item may name its own journal (``journal``: a path,
  or a name beside the main journal); reference items (decision D31,
  ``refstore``) use one so the scoring journal holds verdict rows only.
- **Requirements.** An item with ``requires`` (item keys) starts only when none
  of them is still queued or running in this run (a requirement queued again
  for a retry still counts as pending); until then a slot takes the next item
  that is ready, so queue order is kept except around a running requirement.
  A requirement that failed, was deferred or was cut counts as done: the item
  runs anyway (a consumer without a usable reference entry computes inline).
  ``RunnerConfig.on_done`` is called once per item that leaves the queue for
  good, with its journaled rows (``None`` when it never ran), e.g. to delete a
  reference entry's tensors after its last consumer.
- **Time boxes.** ``soft_deadline`` stops slots from taking new items;
  ``hard_deadline`` kills running children (not journaled, like a signal,
  but no checkpoint marker is written). With ``fit_deadline``, an item starts
  only if its watchdog limits (compile plus correctness, or timing) end before
  the hard deadline, so a large item is deferred to the next job instead of
  being started and killed. Every killed item is recorded in ``cut.jsonl``
  next to the journal with its spawn and kill times (censored cost). Every
  row records ``item_wall_seconds`` (spawn to verdict) for the cost card.
- **Signals.** Under the lane's checkpoint contract (docs/operations.md), SIGUSR1
  or SIGTERM stops scheduling and kills running children (their items are not
  journaled and rerun on resume). Once the journal is complete, the runner
  writes ``checkpoint.ready`` atomically (temp file in the same directory, then
  rename) with the line ``trigger=SIGUSR1`` or ``trigger=SIGTERM``. The marker
  is reserved for that signal-triggered save: progress after each journaled
  item goes to a separate ``progress.json`` and never to the marker. The CLI
  exits 75 when interrupted.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from harness.q1 import faults
from harness.q1.journal import Journal, item_key
from harness.q1.schema import make_verdict_row, validate_verdict_row
from harness.q1.versions import row_code_sha256

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIMEOUTS = {"compile": 120.0, "correctness": 180.0, "timing": 300.0}
PHASE_ORDER = ("compile", "correctness", "timing")
#: An infrastructure-failed item runs at most this many attempts (prereg section 10).
MAX_INFRA_ATTEMPTS = 2


def is_infra_failure(rows: Sequence[Mapping[str, Any]]) -> bool:
    """True when the item's rows record an infrastructure failure, not a verdict."""
    return any(
        row["verdict"] == "error"
        and str(row["details"].get("reason", "")).startswith("infra_failure")
        for row in rows
    )


@dataclass
class WorkItem:
    kernel_id: str
    kernel_path: str
    problem_id: str
    gate: str
    seed: int = 42
    problem_source_path: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    #: Run alone on its device (no other item of this runner on the same slot
    #: device at the same time), e.g. a problem whose inputs fill the GPU.
    exclusive: bool = False
    #: Per-item phase limits overriding the runner's (a preregistered size rule,
    #: e.g. ``harness.q1.pilot.watchdog_limits``); ``None`` keeps the defaults.
    timeouts: dict[str, float] | None = None
    #: Capacity units held on the device (``None``: one unit; ``exclusive``: all).
    units: int | None = None
    #: Item keys that must leave the queue (finish, fail, be deferred) before this starts.
    requires: list[str] = field(default_factory=list)
    #: Journal for this item's rows (``None``: the main journal; a relative path is
    #: resolved beside the main journal).
    journal: str | None = None
    #: Estimated peak GPU bytes (``harness.q1.memory``), read by the memory guard.
    memory_bytes: int | None = None

    @property
    def key(self) -> str:
        return item_key(self.kernel_id, self.gate, self.seed)

    @property
    def is_timing(self) -> bool:
        return self.gate == "timing"


@dataclass
class RunnerConfig:
    journal_path: Path
    slots: Sequence[str] = ("cpu",)
    timing_slots: Sequence[str] = ()
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timeouts: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_TIMEOUTS))
    python: str = sys.executable
    extra_env: Mapping[str, str] = field(default_factory=dict)
    health_check: bool = True
    workdir: Path | None = None
    checkpoint_marker: Path | None = None
    progress_path: Path | None = None
    #: ``time.monotonic()`` after which slots take no new item (a time box;
    #: unstarted items stay queued and are counted in ``left_in_queue``).
    soft_deadline: float | None = None
    #: ``time.monotonic()`` after which running children are killed; their
    #: items are not journaled (as on a signal) and are counted as cut.
    hard_deadline: float | None = None
    #: Start an item only if its watchdog limits end before ``hard_deadline``.
    fit_deadline: bool = False
    #: Free-memory check before an item starts on a CUDA slot (``MemoryGuard``).
    memory_guard: MemoryGuard | None = None
    #: Seconds to wait before each repeat of a failed health check, run alone.
    health_retry_delays: Sequence[float] = (2.0, 5.0, 10.0)
    #: Health-check argv (``None``: one small CUDA allocation in ``python``).
    health_command: Sequence[str] | None = None
    #: Called once per item that leaves the queue for good: (item, journaled rows or None).
    on_done: Callable[[WorkItem, list[dict[str, Any]] | None], None] | None = None


class ReadyQueue:
    """FIFO of (item, attempt) whose ``get`` returns the first entry whose
    requirements are no longer pending, waiting while every entry is blocked."""

    def __init__(self, pending: set[str], stopped: threading.Event) -> None:
        self._entries: list[tuple[WorkItem, int]] = []
        self._cond = threading.Condition()
        self._pending = pending
        self._stopped = stopped

    def put(self, entry: tuple[WorkItem, int]) -> None:
        with self._cond:
            self._entries.append(entry)
            self._cond.notify_all()

    def qsize(self) -> int:
        with self._cond:
            return len(self._entries)

    def keys(self) -> list[str]:
        with self._cond:
            return [item.key for item, _ in self._entries]

    def notify(self) -> None:
        with self._cond:
            self._cond.notify_all()

    def get(self, deadline: float | None = None) -> tuple[WorkItem, int] | None:
        with self._cond:
            while True:
                if self._stopped.is_set() or not self._entries:
                    return None
                if deadline is not None and time.monotonic() >= deadline:
                    return None
                for index, (item, attempt) in enumerate(self._entries):
                    if not any(key in self._pending for key in item.requires):
                        del self._entries[index]
                        return item, attempt
                self._cond.wait(0.5)


class MemoryGuard:
    """Free-memory check before an item starts on a CUDA device.

    ``probe(slot)`` returns the device's ``(used_bytes, total_bytes)`` or ``None``
    (unreadable: the guard then admits on the units rule alone). An item of
    ``need`` estimated bytes is admitted when ``max(used, reserved) + need <=
    budget``, where ``reserved`` sums the estimates of this runner's running items
    on the device: their memory may not have materialised yet, and memory above
    the estimates (or held by someone else) shows in ``used``. Readings are cached
    for ``ttl`` seconds."""

    def __init__(
        self,
        budget_bytes: int,
        probe: Callable[[str], tuple[int, int] | None] | None = None,
        ttl: float = 1.0,
    ) -> None:
        self.budget_bytes = int(budget_bytes)
        self.probe = probe if probe is not None else nvidia_smi_memory
        self.ttl = ttl
        self._cache: dict[str, tuple[float, tuple[int, int] | None]] = {}
        self.unreadable = 0

    def reading(self, slot: str) -> tuple[int, int] | None:
        now = time.monotonic()
        cached = self._cache.get(slot)
        if cached is not None and now - cached[0] < self.ttl:
            return cached[1]
        try:
            value = self.probe(slot)
        except Exception:
            value = None
        if value is None:
            self.unreadable += 1
        self._cache[slot] = (now, value)
        return value

    def admits(self, slot: str, need: int, reserved: int) -> bool:
        if not slot.startswith("cuda:"):
            return True
        value = self.reading(slot)
        if value is None:
            return True
        used, _total = value
        return max(int(used), int(reserved)) + int(need) <= self.budget_bytes

    def invalidate(self, slot: str) -> None:
        self._cache.pop(slot, None)


def nvidia_smi_memory(slot: str) -> tuple[int, int] | None:
    """``(used, total)`` bytes of the slot's device from ``nvidia-smi`` (the index is
    the slot's; with one GPU per job, as Stage 0 runs, it is index 0 either way)."""
    if not slot.startswith("cuda:"):
        return None
    index = slot.split(":", 1)[1]
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                f"--id={index}",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        used, total = (int(float(v)) * 1024 * 1024 for v in out.splitlines()[0].split(","))
        return used, total
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


class DeviceShare:
    """Capacity admission per device: an item holds ``units`` of the device's
    ``capacity`` (the number of slots naming it); an exclusive item holds all of it.
    A waiting request larger than one unit blocks smaller new ones until it is
    admitted (writer preference), so a large or exclusive item cannot starve.
    With a ``MemoryGuard`` an item also needs the device's memory to fit (unless
    nothing else of this runner runs on the device). A retired device admits
    nothing (``retire``)."""

    def __init__(self, capacity: int = 1, slot: str = "", guard: MemoryGuard | None = None) -> None:
        self._cond = threading.Condition()
        self.capacity = max(1, int(capacity))
        self.slot = slot
        self.guard = guard
        self._used = 0
        self._reserved = 0
        self._waiting_large = 0
        self.retired: str | None = None
        self.guard_waits = 0

    def units_for(self, exclusive: bool, units: int | None) -> int:
        if exclusive:
            return self.capacity
        return max(1, min(self.capacity, int(units or 1)))

    def _memory_ok(self, memory_bytes: int | None) -> bool:
        if self.guard is None or self._used == 0:
            return True
        return self.guard.admits(self.slot, int(memory_bytes or 0), self._reserved)

    def acquire(
        self,
        exclusive: bool,
        stopped: threading.Event,
        units: int | None = None,
        memory_bytes: int | None = None,
    ) -> bool:
        need = self.units_for(exclusive, units)
        with self._cond:
            large = need > 1
            if large:
                self._waiting_large += 1
            try:
                while True:
                    if stopped.is_set() or self.retired is not None:
                        return False
                    fits = self._used + need <= self.capacity and not (
                        not large and self._waiting_large
                    )
                    if fits and self._memory_ok(memory_bytes):
                        break
                    if fits:
                        self.guard_waits += 1
                    self._cond.wait(0.5)
            finally:
                if large:
                    self._waiting_large -= 1
            self._used += need
            self._reserved += int(memory_bytes or 0)
            return True

    def release(
        self, exclusive: bool, units: int | None = None, memory_bytes: int | None = None
    ) -> None:
        with self._cond:
            self._used -= self.units_for(exclusive, units)
            self._reserved -= int(memory_bytes or 0)
            if self.guard is not None:
                self.guard.invalidate(self.slot)
            self._cond.notify_all()

    def retire(self, reason: str) -> None:
        with self._cond:
            if self.retired is None:
                self.retired = reason
            self._cond.notify_all()


@dataclass
class HealthResult:
    """A health check's outcome: ``kind`` is ``ok``, ``allocation`` (a resource
    failure: the device could not give a fresh process memory) or ``fault``."""

    kind: str
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.kind == "ok"


def classify_health(returncode: int | None, output: str, timed_out: bool = False) -> HealthResult:
    if returncode == 0 and not timed_out:
        return HealthResult("ok")
    tail = output[-2000:]
    if not timed_out and faults.is_resource_text(output):
        return HealthResult("allocation", tail)
    marker = faults.first_marker(output, faults.DEVICE_FAULT_MARKERS)
    prefix = "timeout" if timed_out else f"exit {returncode}"
    return HealthResult("fault", f"{prefix}; marker={marker}; {tail}")


#: Text that marks a GPU resource failure in rows or a worker log: one list with the
#: reference store's (``harness.q1.faults``).
OOM_MARKERS = faults.RESOURCE_MARKERS


def contention_failure(rows: Sequence[Mapping[str, Any]]) -> str | None:
    """``timeout-shared`` or ``oom-shared`` when an item's rows show a watchdog
    timeout or a GPU resource failure (CUDA out-of-memory, cuBLAS/cuDNN allocation;
    ``faults.RESOURCE_MARKERS``); only meaningful for a shared item."""
    if any(row["verdict"] == "timeout" for row in rows):
        return "timeout-shared"
    for row in rows:
        if faults.is_resource_text(json.dumps(row.get("details", {}), default=str)):
            return "oom-shared"
    return None


def item_budget_seconds(item: WorkItem, timeouts: Mapping[str, float]) -> float:
    """The longest an item can run before its watchdog ends it."""
    limits = {**DEFAULT_TIMEOUTS, **dict(timeouts), **(item.timeouts or {})}
    if item.is_timing:
        return limits["compile"] + limits["timing"]
    return limits["compile"] + limits["correctness"]


def _set_pdeathsig() -> None:
    """Linux: the child dies if the runner dies (best effort, no-op elsewhere)."""
    try:
        import ctypes

        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl(1, signal.SIGKILL)  # PR_SET_PDEATHSIG
    except Exception:
        pass


class Runner:
    def __init__(self, config: RunnerConfig) -> None:
        self.config = config
        self.journal = Journal(config.journal_path)
        self._journals: dict[str, Journal] = {}
        #: Keys of this run's items that are queued or running (requirements).
        self._pending: set[str] = set()
        self._queues: list[ReadyQueue] = []
        self._lock = threading.Lock()
        self.summary: dict[str, int] = {"run": 0, "skipped": 0, "timeouts": 0, "crashes": 0}
        self.retired_slots: list[str] = []
        #: Device slot -> why it stopped taking items (``gpu-health-fault`` or
        #: ``gpu-memory-held``); see the module docstring.
        self.retired_devices: dict[str, str] = {}
        self.health_events: list[dict[str, Any]] = []
        self.stopped = threading.Event()
        self.trigger: str | None = None
        self.expired = False
        self._children: set[subprocess.Popen] = set()
        self._shares: dict[str, DeviceShare] = {}
        self.deferred: list[str] = []
        self.cut_path = config.journal_path.with_name("cut.jsonl")
        self.memory_path = config.journal_path.with_name("memory.jsonl")

    def expire(self) -> None:
        """Hard time box: stop scheduling and kill children, without a signal trigger
        (no checkpoint marker is written for a time box)."""
        self.expired = True
        self.stopped.set()
        with self._lock:
            children = list(self._children)
        for child in children:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(child.pid, signal.SIGKILL)

    def stop(self, trigger: str = "SIGUSR1") -> None:
        """Stop scheduling and kill running children; their items rerun on resume."""
        if self.trigger is None:
            self.trigger = trigger
        self.stopped.set()
        with self._lock:
            children = list(self._children)
        for child in children:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(child.pid, signal.SIGKILL)

    def _journal_facts(self) -> dict[str, Any]:
        rows, invalid = self.journal.read()
        return {
            "run_id": self.config.run_id,
            "journal_rows": len(rows),
            "invalid_lines": invalid,
            "items_final": sum(1 for s in self.journal.status().values() if s["final"]),
            "written_at": time.time(),
        }

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temp.write_text(text, encoding="utf-8")
        os.replace(temp, path)

    def write_progress(self) -> None:
        """Periodic progress record; never the checkpoint marker."""
        if self.config.progress_path is not None:
            self._atomic_write(
                self.config.progress_path, json.dumps(self._journal_facts(), sort_keys=True)
            )

    def write_checkpoint_marker(self) -> bool:
        """Signal-triggered checkpoint marker. Returns False when no signal was received."""
        marker = self.config.checkpoint_marker
        if marker is None or self.trigger is None:
            return False
        facts = self._journal_facts()
        lines = [f"trigger={self.trigger}"] + [f"{key}={facts[key]}" for key in sorted(facts)]
        self._atomic_write(marker, "\n".join(lines) + "\n")
        return True

    def journal_for(self, item: WorkItem) -> Journal:
        if not item.journal:
            return self.journal
        path = Path(item.journal)
        if not path.is_absolute():
            path = self.config.journal_path.parent / path
        key = str(path)
        if key not in self._journals:
            self._journals[key] = Journal(path)
        return self._journals[key]

    def _done(self, item: WorkItem, rows: list[dict[str, Any]] | None = None) -> None:
        """``item`` left the queue for good in this run: wake items that require it."""
        with self._lock:
            self._pending.discard(item.key)
        for work in self._queues:
            work.notify()
        if self.config.on_done is not None:
            try:
                self.config.on_done(item, rows)
            except Exception as exc:  # a hook fault never stops scoring
                with self._lock:
                    self.summary["on_done_errors"] = self.summary.get("on_done_errors", 0) + 1
                    self.health_events.append({"on_done_error": f"{type(exc).__name__}: {exc}"})

    # --- scheduling ---------------------------------------------------------

    def run(self, items: Iterable[WorkItem]) -> dict[str, Any]:
        items = list(items)
        status = dict(self.journal.status())
        for item in items:
            if item.journal:
                journal = self.journal_for(item)
                if journal is not self.journal and journal.path.exists():
                    status.update({k: v for k, v in journal.status().items() if k not in status})
        pending: list[tuple[WorkItem, int]] = []
        for item in items:
            entry = status.get(item.key)
            if entry and entry["final"]:
                self.summary["skipped"] += 1
                continue
            if entry and entry.get("retry_alone") and not item.exclusive:
                item = replace(item, exclusive=True)
            pending.append((item, (entry["attempt"] + 1) if entry else 1))
        for slot in {*self.config.slots, *self.config.timing_slots}:
            capacity = list(self.config.slots).count(slot) + list(self.config.timing_slots).count(
                slot
            )
            self._shares.setdefault(
                slot, DeviceShare(capacity, slot=slot, guard=self.config.memory_guard)
            )
        self._pending = {item.key for item, _ in pending}
        correctness = ReadyQueue(self._pending, self.stopped)
        timing = ReadyQueue(self._pending, self.stopped)
        self._queues = [correctness, timing]
        for item, attempt in pending:
            (timing if item.is_timing else correctness).put((item, attempt))
        threads = [
            threading.Thread(target=self._slot_loop, args=(slot, correctness), daemon=True)
            for slot in self.config.slots
        ] + [
            threading.Thread(target=self._slot_loop, args=(slot, timing), daemon=True)
            for slot in self.config.timing_slots
        ]
        if timing.qsize() and not self.config.timing_slots:
            raise ValueError("timing items need at least one timing slot")
        for thread in threads:
            thread.start()
        if self.config.hard_deadline is not None:
            while any(thread.is_alive() for thread in threads):
                if time.monotonic() >= self.config.hard_deadline:
                    self.expire()
                    break
                time.sleep(0.5)
        for thread in threads:
            thread.join()
        guard = self.config.memory_guard
        return {
            **self.summary,
            "retired_slots": self.retired_slots,
            "retired_devices": dict(self.retired_devices),
            "health_events": list(self.health_events),
            "memory_guard_waits": sum(share.guard_waits for share in self._shares.values()),
            "memory_guard_unreadable": guard.unreadable if guard is not None else None,
            "run_id": self.config.run_id,
            "left_in_queue": correctness.qsize() + timing.qsize() + len(self.deferred),
            "deferred_by_deadline": len(self.deferred),
            "time_boxed": self.expired
            or (
                self.config.soft_deadline is not None
                and time.monotonic() >= self.config.soft_deadline
                and correctness.qsize() + timing.qsize() > 0
            ),
        }

    def _fits(self, item: WorkItem) -> bool:
        if not self.config.fit_deadline or self.config.hard_deadline is None:
            return True
        budget = item_budget_seconds(item, self.config.timeouts)
        return time.monotonic() + budget <= self.config.hard_deadline

    def _record_cut(self, item: WorkItem, attempt: int, rows: list[dict], slot: str) -> None:
        """A killed item is not journaled; its spawn and kill times are kept for the
        cost card (a censored lower bound on its cost)."""
        started = rows[0]["details"].get("item_started_at") if rows else None
        record = {
            "item_key": item.key,
            "attempt": attempt,
            "slot": slot,
            "units": item.units,
            "exclusive": item.exclusive,
            "started_at": started,
            "killed_at": round(time.time(), 3),
            "reason": "hard-deadline" if self.expired else f"signal-{self.trigger}",
            "run_id": self.config.run_id,
        }
        with self._lock, self.cut_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _slot_loop(self, slot: str, work: ReadyQueue) -> None:
        share = self._shares.setdefault(slot, DeviceShare(slot=slot))
        while not self.stopped.is_set():
            if share.retired is not None:
                self._retire_slot(slot, share.retired)
                return
            if (
                self.config.soft_deadline is not None
                and time.monotonic() >= self.config.soft_deadline
            ):
                return
            entry = work.get(self.config.soft_deadline)
            if entry is None:
                return
            item, attempt = entry
            if not self._fits(item):
                with self._lock:
                    self.deferred.append(item.key)
                self._done(item)
                continue  # left for the next job (resume); never started and killed
            if not share.acquire(item.exclusive, self.stopped, item.units, item.memory_bytes):
                if share.retired is not None and not self.stopped.is_set():
                    work.put((item, attempt))  # unstarted: it stays queued for the next job
                    self._retire_slot(slot, share.retired)
                return  # stopped while waiting; the item reruns on resume
            alone = item.exclusive or share.units_for(False, item.units) >= share.capacity
            try:
                rows, needs_check = self.execute(item, attempt, slot)
            finally:
                share.release(item.exclusive, item.units, item.memory_bytes)
            if self.stopped.is_set():
                self._record_cut(item, attempt, rows, slot)
                return  # an interrupted item is not journaled; it reruns on resume
            healthy = True
            if needs_check:
                health = self._recover(slot, share)
                if self.stopped.is_set():
                    self._record_cut(item, attempt, rows, slot)
                    return
                healthy = health.ok
                if not healthy:
                    for row in rows:
                        row["verdict"] = "error"
                        row["details"]["reason"] = "infra_failure-gpu-health-check"
                        row["details"]["health"] = {"kind": health.kind, "detail": health.detail}
            infra = is_infra_failure(rows)
            contention = None if alone or item.is_timing else contention_failure(rows)
            retry = (infra or contention is not None) and attempt < MAX_INFRA_ATTEMPTS
            if retry:
                for row in rows:  # journaled for the record, but not final
                    row["details"]["item_final"] = False
                    if contention is not None:
                        row["details"]["retry_alone"] = True
                        row["details"]["infra_failure_kind"] = f"infra_failure-{contention}"
            with self._lock:
                self.journal_for(item).append(rows)
                self.summary["run"] += 1
                if infra:
                    self.summary["infra_failures"] = self.summary.get("infra_failures", 0) + 1
                if contention is not None:
                    key = f"contention_{contention.replace('-', '_')}"
                    self.summary[key] = self.summary.get(key, 0) + 1
                self.write_progress()
            if retry:
                work.put((replace(item, exclusive=True) if contention else item, attempt + 1))
            else:
                self._done(item, rows)
            if not healthy:
                self._retire_slot(slot, share.retired or "gpu-health-fault")
                return

    def _retire_slot(self, slot: str, reason: str) -> None:
        with self._lock:
            self.retired_slots.append(slot)
            self.retired_devices.setdefault(slot, reason)

    def _recover(self, slot: str, share: DeviceShare) -> HealthResult:
        """Health check after a crash or timeout on a GPU slot (module docstring).

        A failed first check drains the device (an exclusive hold: every other item
        of this runner on it finishes first, no new one starts) and repeats the check
        alone after each of ``health_retry_delays``. Only a check that fails alone
        stops the device: ``gpu-memory-held`` for an allocation failure (memory held
        outside this runner), ``gpu-health-fault`` otherwise."""
        if not slot.startswith("cuda:") or not self.config.health_check:
            return HealthResult("ok")
        first = self._health_check(slot)
        event: dict[str, Any] = {"slot": slot, "at": round(time.time(), 3), "first": first.kind}
        if first.ok:
            return first
        if not share.acquire(True, self.stopped):
            # stopped, or another slot already retired the device while we waited
            return first if share.retired is not None else HealthResult("ok")
        result = first
        try:
            for delay in self.config.health_retry_delays:
                time.sleep(delay)
                result = self._health_check(slot)
                if result.ok:
                    break
            if not result.ok:
                share.retire(
                    "gpu-memory-held" if result.kind == "allocation" else "gpu-health-fault"
                )
        finally:
            share.release(True)
        event.update({"alone": result.kind, "retired": share.retired})
        with self._lock:
            self.health_events.append(event)
            key = "health_recovered_alone" if result.ok else "health_failed_alone"
            self.summary[key] = self.summary.get(key, 0) + 1
        return result

    # --- one item -------------------------------------------------------------

    def _env(self, slot: str) -> dict[str, str]:
        env = dict(os.environ)
        # torch derives cache paths from the user name; containers that run as
        # a uid without a passwd entry need it from the environment.
        env.setdefault("USER", "q1")
        env.setdefault("LOGNAME", env["USER"])
        env.update(self.config.extra_env)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(PROJECT_ROOT), *filter(None, [env.get("PYTHONPATH")])]
        )
        if slot.startswith("cuda:"):
            env["CUDA_VISIBLE_DEVICES"] = slot.split(":", 1)[1]
        else:
            env["CUDA_VISIBLE_DEVICES"] = ""
        return env

    def execute(self, item: WorkItem, attempt: int, slot: str) -> tuple[list[dict], bool]:
        """Run one item in a fresh worker; returns its rows and whether a GPU health
        check is due (the worker crashed or timed out on a CUDA slot)."""
        workdir = Path(tempfile.mkdtemp(prefix="q1item-", dir=self.config.workdir))
        payload = {
            **asdict(item),
            "item_key": item.key,
            "run_id": self.config.run_id,
            "attempt": attempt,
            "device": "cuda:0" if slot.startswith("cuda:") else "cpu",
            "workdir": str(workdir),
            "spawned_at": round(time.time(), 3),
        }
        if slot.startswith("cuda:") and item.is_timing:
            payload["options"] = {**item.options, "gpu_index": int(slot.split(":", 1)[1])}
        item_path, out_path = workdir / "item.json", workdir / "rows.jsonl"
        item_path.write_text(json.dumps(payload), encoding="utf-8")
        read_fd, write_fd = os.pipe()
        env = self._env(slot)
        env["Q1_PHASE_FD"] = str(write_fd)
        start = time.monotonic()
        started_at = time.time()
        log_path = workdir / "worker.log"
        with log_path.open("wb") as log:
            process = subprocess.Popen(
                [self.config.python, "-m", "harness.q1.worker", str(item_path), str(out_path)],
                cwd=PROJECT_ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                pass_fds=(write_fd,),
                start_new_session=True,
                preexec_fn=_set_pdeathsig if sys.platform.startswith("linux") else None,
            )
            os.close(write_fd)
            with self._lock:
                self._children.add(process)
            try:
                phase, timed_out = self._watch(process, read_fd, item.timeouts)
            finally:
                with self._lock:
                    self._children.discard(process)
        os.close(read_fd)
        wall = time.monotonic() - start
        rows = self._collect(out_path) if process.returncode == 0 and not timed_out else []
        self._record_memory(item, attempt, slot, workdir)
        needs_check = False
        if not rows:
            tail = log_path.read_bytes()[-4000:].decode("utf-8", "replace")
            with self._lock:
                self.summary["timeouts" if timed_out else "crashes"] += 1
            if timed_out:
                verdict, reason = "timeout", f"watchdog-{phase}"
            else:
                verdict = "reject" if phase in {"correctness", "timing"} else "error"
                reason = "worker-crashed"
            needs_check = slot.startswith("cuda:") and self.config.health_check
            rows = [
                make_verdict_row(
                    kernel_id=item.kernel_id,
                    gate=item.gate,
                    config_id=f"item/seed-{item.seed}",
                    verdict=verdict,
                    tf32_policy="not-applicable",
                    gpu_seconds=wall if slot.startswith("cuda:") else 0.0,
                    wall_seconds=wall,
                    details={
                        "reason": reason,
                        "phase": phase,
                        "returncode": process.returncode,
                        "log_tail": tail,
                        "slot": slot,
                    },
                    seed=item.seed,
                    run_id=self.config.run_id,
                    attempt=attempt,
                    code_sha256=row_code_sha256(item.gate),
                )
            ]
        for row in rows:
            row["details"]["item_key"] = item.key
            row["details"].setdefault("slot", slot)
            # Cost accounting (preregistration section 7.1): the slot is held from
            # worker spawn to verdict, compile and process start-up included.
            row["details"]["item_wall_seconds"] = round(wall, 3)
            row["details"]["item_started_at"] = round(started_at, 3)
            row["details"]["item_ended_at"] = round(started_at + wall, 3)
            row["details"]["item_exclusive"] = item.exclusive
            if item.units is not None:
                row["details"]["item_units"] = item.units
            if item.timeouts:
                row["details"]["item_timeouts"] = dict(item.timeouts)
        rows[-1]["details"]["item_final"] = True
        return [validate_verdict_row(row) for row in rows], needs_check

    def _record_memory(self, item: WorkItem, attempt: int, slot: str, workdir: Path) -> None:
        """Append the worker's peak CUDA memory (``memory.json``) to ``memory.jsonl``."""
        path = workdir / "memory.json"
        if not path.exists():
            return
        try:
            facts = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        record = {
            **facts,
            "item_key": item.key,
            "problem_id": item.problem_id,
            "gate": item.gate,
            "attempt": attempt,
            "slot": slot,
            "units": item.units,
            "exclusive": item.exclusive,
            "memory_bytes_estimate": item.memory_bytes,
            "run_id": self.config.run_id,
        }
        with self._lock, self.memory_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _watch(
        self,
        process: subprocess.Popen,
        read_fd: int,
        overrides: Mapping[str, float] | None = None,
    ) -> tuple[str, bool]:
        phase = "compile"
        phase_start = time.monotonic()
        buffer = b""
        while True:
            limit = (overrides or {}).get(
                phase, self.config.timeouts.get(phase, DEFAULT_TIMEOUTS[phase])
            )
            remaining = limit - (time.monotonic() - phase_start)
            if remaining <= 0:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                return phase, True
            ready, _, _ = select.select([read_fd], [], [], min(0.2, remaining))
            if ready:
                chunk = os.read(read_fd, 4096)
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    name = line.decode("utf-8", "replace").strip()
                    if name in PHASE_ORDER and PHASE_ORDER.index(name) > PHASE_ORDER.index(phase):
                        phase, phase_start = name, time.monotonic()
                if not chunk:
                    if process.poll() is not None:
                        return phase, False
                    time.sleep(0.05)
            if process.poll() is not None:
                return phase, False

    def _collect(self, out_path: Path) -> list[dict[str, Any]]:
        if not out_path.exists():
            return []
        rows = []
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(validate_verdict_row(json.loads(line)))
        return rows

    def _health_check(self, slot: str) -> HealthResult:
        """One small CUDA allocation in a fresh process, classified (``classify_health``)."""
        command = list(self.config.health_command or [self.config.python, "-c", HEALTH_CODE])
        try:
            done = subprocess.run(
                command, env=self._env(slot), capture_output=True, text=True, timeout=60
            )
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            if isinstance(output, bytes):
                output = output.decode("utf-8", "replace")
            return classify_health(None, output, timed_out=True)
        except OSError as exc:
            return classify_health(None, f"{type(exc).__name__}: {exc}")
        return classify_health(done.returncode, (done.stdout or "") + (done.stderr or ""))


#: The health check: a fresh process creates a CUDA context and allocates 4 KiB.
HEALTH_CODE = "import torch; x = torch.ones(1024, device='cuda'); assert float(x.sum()) == 1024.0"


def install_signal_handlers(runner: Runner) -> None:
    """SIGUSR1 and SIGTERM stop the runner and name the trigger for the marker."""
    for signum in (signal.SIGUSR1, signal.SIGTERM):
        name = signal.Signals(signum).name
        signal.signal(signum, lambda *_, _name=name: runner.stop(_name))


def load_items(path: Path) -> list[WorkItem]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(WorkItem(**json.loads(line)))
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Q1 work items with a watchdog.")
    parser.add_argument("--items", type=Path, required=True, help="JSONL of WorkItem fields")
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--slots", default="cpu", help="comma list: cpu or cuda:N")
    parser.add_argument("--timing-slots", default="", help="comma list of timing-only slots")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--timeouts", default=None, help="JSON overriding phase limits")
    parser.add_argument("--workdir", type=Path, default=None)
    parser.add_argument(
        "--checkpoint-marker",
        type=Path,
        default=Path(os.environ["COTCODEC_CHECKPOINT_MARKER"])
        if os.environ.get("COTCODEC_CHECKPOINT_MARKER")
        else None,
    )
    args = parser.parse_args(argv)
    config = RunnerConfig(
        journal_path=args.journal,
        slots=[s for s in args.slots.split(",") if s],
        timing_slots=[s for s in args.timing_slots.split(",") if s],
        workdir=args.workdir,
        checkpoint_marker=args.checkpoint_marker,
        progress_path=args.journal.with_name("progress.json"),
    )
    if args.run_id:
        config.run_id = args.run_id
    if args.timeouts:
        config.timeouts = {**DEFAULT_TIMEOUTS, **json.loads(args.timeouts)}
    overlap = set(config.slots) & set(config.timing_slots)
    if overlap:
        parser.error(f"slots used for both correctness and timing: {sorted(overlap)}")
    runner = Runner(config)
    install_signal_handlers(runner)
    summary = runner.run(load_items(args.items))
    interrupted = runner.stopped.is_set()
    runner.write_checkpoint_marker()
    print(json.dumps({**summary, "interrupted": interrupted}, sort_keys=True))
    return 75 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
