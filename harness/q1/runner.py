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
  any crash or timeout on a GPU slot a health check runs in a fresh process;
  a failed check marks the item ``error`` (``infra_failure``) and retires the
  slot.
- **Infrastructure retries.** An item whose rows carry an ``infra_failure``
  reason is queued once more as the next attempt (the journal keeps both
  attempts; analyses read the final one). A second infrastructure failure is
  final and is excluded and listed by the analysis.
- **Journal.** Rows are appended to the append-only journal
  (``journal.py``); resume skips finished items and reruns the rest with the
  next attempt number.
- **Time boxes.** ``soft_deadline`` stops slots from taking new items;
  ``hard_deadline`` kills running children (not journaled, like a signal,
  but no checkpoint marker is written). Every row records
  ``item_wall_seconds`` (spawn to verdict) for the cost card.
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
import queue
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

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


class DeviceShare:
    """Readers-writer admission per device: shared items run together up to the
    slot count; an exclusive item waits until the device is empty and blocks new
    items until it finishes (writer preference, so it cannot starve)."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._running = 0
        self._exclusive = False
        self._waiting_exclusive = 0

    def acquire(self, exclusive: bool, stopped: threading.Event) -> bool:
        with self._cond:
            if exclusive:
                self._waiting_exclusive += 1
                try:
                    while self._running or self._exclusive:
                        if stopped.is_set():
                            return False
                        self._cond.wait(0.5)
                finally:
                    self._waiting_exclusive -= 1
                self._exclusive = True
            else:
                while self._exclusive or self._waiting_exclusive:
                    if stopped.is_set():
                        return False
                    self._cond.wait(0.5)
                self._running += 1
            return True

    def release(self, exclusive: bool) -> None:
        with self._cond:
            if exclusive:
                self._exclusive = False
            else:
                self._running -= 1
            self._cond.notify_all()


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
        self._lock = threading.Lock()
        self.summary: dict[str, int] = {"run": 0, "skipped": 0, "timeouts": 0, "crashes": 0}
        self.retired_slots: list[str] = []
        self.stopped = threading.Event()
        self.trigger: str | None = None
        self.expired = False
        self._children: set[subprocess.Popen] = set()
        self._shares: dict[str, DeviceShare] = {}

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

    # --- scheduling ---------------------------------------------------------

    def run(self, items: Iterable[WorkItem]) -> dict[str, Any]:
        status = self.journal.status()
        pending: list[tuple[WorkItem, int]] = []
        for item in items:
            entry = status.get(item.key)
            if entry and entry["final"]:
                self.summary["skipped"] += 1
                continue
            pending.append((item, (entry["attempt"] + 1) if entry else 1))
        correctness: queue.Queue = queue.Queue()
        timing: queue.Queue = queue.Queue()
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
        return {
            **self.summary,
            "retired_slots": self.retired_slots,
            "run_id": self.config.run_id,
            "left_in_queue": correctness.qsize() + timing.qsize(),
            "time_boxed": self.expired
            or (
                self.config.soft_deadline is not None
                and time.monotonic() >= self.config.soft_deadline
                and correctness.qsize() + timing.qsize() > 0
            ),
        }

    def _slot_loop(self, slot: str, work: queue.Queue) -> None:
        while not self.stopped.is_set():
            if (
                self.config.soft_deadline is not None
                and time.monotonic() >= self.config.soft_deadline
            ):
                return
            try:
                item, attempt = work.get_nowait()
            except queue.Empty:
                return
            with self._lock:
                share = self._shares.setdefault(slot, DeviceShare())
            if not share.acquire(item.exclusive, self.stopped):
                return  # stopped while waiting; the item reruns on resume
            try:
                rows, healthy = self.execute(item, attempt, slot)
            finally:
                share.release(item.exclusive)
            if self.stopped.is_set():
                return  # an interrupted item is not journaled; it reruns on resume
            infra = is_infra_failure(rows)
            if infra and attempt < MAX_INFRA_ATTEMPTS:
                for row in rows:  # journaled for the record, but not final
                    row["details"]["item_final"] = False
            with self._lock:
                self.journal.append(rows)
                self.summary["run"] += 1
                if infra:
                    self.summary["infra_failures"] = self.summary.get("infra_failures", 0) + 1
                self.write_progress()
            if infra and attempt < MAX_INFRA_ATTEMPTS:
                work.put((item, attempt + 1))
            if not healthy:
                with self._lock:
                    self.retired_slots.append(slot)
                return

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
        workdir = Path(tempfile.mkdtemp(prefix="q1item-", dir=self.config.workdir))
        payload = {
            **asdict(item),
            "item_key": item.key,
            "run_id": self.config.run_id,
            "attempt": attempt,
            "device": "cuda:0" if slot.startswith("cuda:") else "cpu",
            "workdir": str(workdir),
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
        healthy = True
        if not rows:
            tail = log_path.read_bytes()[-4000:].decode("utf-8", "replace")
            with self._lock:
                self.summary["timeouts" if timed_out else "crashes"] += 1
            if timed_out:
                verdict, reason = "timeout", f"watchdog-{phase}"
            else:
                verdict = "reject" if phase in {"correctness", "timing"} else "error"
                reason = "worker-crashed"
            if slot.startswith("cuda:") and self.config.health_check:
                healthy = self._health_check(slot)
                if not healthy:
                    verdict, reason = "error", "infra_failure-gpu-health-check"
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
            if item.timeouts:
                row["details"]["item_timeouts"] = dict(item.timeouts)
        rows[-1]["details"]["item_final"] = True
        return [validate_verdict_row(row) for row in rows], healthy

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

    def _health_check(self, slot: str) -> bool:
        code = "import torch; x = torch.ones(1024, device='cuda'); assert float(x.sum()) == 1024.0"
        try:
            subprocess.run(
                [self.config.python, "-c", code],
                env=self._env(slot),
                check=True,
                capture_output=True,
                timeout=60,
            )
            return True
        except (subprocess.SubprocessError, OSError):
            return False


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
