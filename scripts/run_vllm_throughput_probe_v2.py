#!/usr/bin/env python3
"""Run the vLLM serving-throughput probe v2 (experiment serving-throughput-probe-v2).

Subcommands:

* ``plan``: resolve the contract for job a and print it with its launch-window
  ledger (CPU only, no vLLM).
* ``run``: execute job a inside the vLLM overlay image under the docker research
  lane: gates G0.0-G0.9, both engines, the launch-window ledger, and atomic
  per-point JSON.
* ``project``: apply the preregistered Q2 budget rules and control X1 to the
  finished job.
* ``vllm-args-doctor``: CPU-only check of every engine flag and the v2 request
  payload with vLLM's own parsers (run by the overlay builder).
* ``digest``: print the contract SHA-256 and the probe code digest.

The v1 driver (``scripts/run_vllm_throughput_probe.py``, frozen with
serving-throughput-probe-v1) supplies the engines, the CUDA doctor (G0.2-G0.4,
its ``cuda-doctor`` subcommand), the lane checks and the signal-checkpoint
machinery; this driver subclasses its runner and replaces the point loop
(launch-window ledger), the reservation (largest-shape warm-up, gate G0.9), the
contamination rule (foreign processes by PID), the request path (prebuilt
history, prompt-token-id digests) and control X1. Exit codes are v1's: 0
finished, 1 crash, 2 pre-result (a gate failed), 3 interrupted.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx  # noqa: E402
import numpy as np  # noqa: E402

from harness.serving_probe import budget as budget_rules  # noqa: E402
from harness.serving_probe.client import (  # noqa: E402
    ChatRequest,
    StopToken,
    summarize_replay,
    summarize_requests,
)
from harness.serving_probe.config import (  # noqa: E402
    JobSpec,
    PhaseSpec,
    PointSpec,
    ProbeConfig,
    ProbeConfigError,
    bind_seeds,
    check_pins,
    parse_weight_pins,
)
from harness.serving_probe.metrics import (  # noqa: E402
    baseline_verdict,
    check_counters,
    cpu_percent,
    parse_engine_log,
    parse_prometheus,
    point_counter_deltas,
    process_tree,
    read_cpu_ticks,
    summarize_gpu,
)
from harness.serving_probe.prompts import allowed_token_ids  # noqa: E402
from harness.serving_probe_v2 import contamination as cont  # noqa: E402
from harness.serving_probe_v2.client import (  # noqa: E402
    build_payload_v2,
    request_identity,
    run_fixed_replay,
    run_open_loop,
)
from harness.serving_probe_v2.config import (  # noqa: E402
    check_warmup_dominates,
    is_required,
    launch_window_check,
    load_config,
    phase_points,
    phase_start_minutes,
)
from harness.serving_probe_v2.requests import build_fixed_replay_plans  # noqa: E402
from harness.serving_probe_v2.schedule import (  # noqa: E402
    FIRST,
    OPTIONAL,
    RERUN,
    LaunchLedger,
    PhaseBudget,
)
from harness.serving_probe_v2.x1 import evaluate_x1  # noqa: E402
from scripts import run_vllm_throughput_probe as v1  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v2.yaml"
EXIT_OK, EXIT_CRASH, EXIT_PRE_RESULT, EXIT_INTERRUPTED = 0, 1, 2, 3
TERMINAL_STATUSES = v1.TERMINAL_STATUSES
VALID_STATUSES = {"valid", "valid-flagged"}
ACCEPTED_JOB_STATUSES = v1.ACCEPTED_JOB_STATUSES
#: Gates recorded once per phase (G0.9 is the largest-shape reservation and attribution).
PHASE_GATES = ("G0.5", "G0.6", "G0.7", "G0.8", "G0.9")
JOB_GATES = v1.JOB_GATES
#: The code whose digest the preregistration names: the v2 package and driver and the
#: frozen v1 package and driver they import. Any change after freezing is a new id.
PROBE_CODE_GLOBS = (
    "harness/serving_probe/*.py",
    "harness/serving_probe_v2/*.py",
    "scripts/run_vllm_throughput_probe.py",
    "scripts/run_vllm_throughput_probe_v2.py",
)
GateFailure = v1.GateFailure
ProbeInterrupted = v1.ProbeInterrupted
ProjectionError = v1.ProjectionError
utc_now = v1.utc_now
sha256_file = v1.sha256_file
atomic_write_json = v1.atomic_write_json


def probe_code_digest(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """SHA-256 over the sorted (path, SHA-256) list of the probe's code files (v1's method)."""
    files = sorted(
        {path for pattern in PROBE_CODE_GLOBS for path in root.glob(pattern) if path.is_file()}
    )
    if not files:
        raise ProbeConfigError(f"no probe code files under {root}")
    listing = [[path.relative_to(root).as_posix(), sha256_file(path)] for path in files]
    digest = hashlib.sha256(json.dumps(listing, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"digest": digest, "files": dict(listing)}


def git_revision(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """HEAD and whether the probe code or contracts differ from it (None outside git)."""

    def git(*args: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return completed.stdout.strip()

    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--", *PROBE_CODE_GLOBS, "experiments/serving")
    return {"head": head, "probe_files_modified": None if status is None else bool(status)}


def verify_preregistration(
    config: ProbeConfig, ledger: Path | None = None, root: Path = PROJECT_ROOT
) -> dict[str, Any]:
    """G0.0: the v2 preregistration is frozen and names this contract and this probe code."""
    from scripts.preregister import DEFAULT_LEDGER, PreregistrationError, verify

    try:
        row = verify(config.experiment_id, ledger=ledger or DEFAULT_LEDGER, root=root)
    except PreregistrationError as exc:
        raise GateFailure(f"G0.0 preregistration is not frozen: {exc}") from exc
    if row.get("path") != config.preregistration:
        raise GateFailure("G0.0 the frozen preregistration path differs from the contract")
    text = (root / str(row["path"])).read_text(encoding="utf-8")
    if config.sha256 not in text:
        raise GateFailure(
            f"G0.0 the frozen preregistration does not name contract SHA-256 {config.sha256}"
        )
    code = probe_code_digest(root)
    if code["digest"] not in text:
        raise GateFailure(
            f"G0.0 the frozen preregistration does not name probe code digest {code['digest']}"
        )
    return {
        **dict(row),
        "contract_sha256": config.sha256,
        "probe_code_digest": code["digest"],
        "probe_code_files": code["files"],
    }


def job_acceptance(summary: Mapping[str, Any]) -> dict[str, Any]:
    """v1's acceptance rule (section 5) with G0.9 among the per-phase gates."""
    gates = summary.get("gates", {})
    job_gate_failures = sorted(
        {gate for gate in JOB_GATES if not (gates.get(gate) or {}).get("pass")}
        | {
            gate
            for gate, verdict in gates.items()
            if gate not in PHASE_GATES and not verdict.get("pass")
        }
    )
    phase_failures: dict[str, list[str]] = {}
    eager_phases = []
    for gate in PHASE_GATES:
        for phase, verdict in gates.get(gate, {}).items():
            if verdict.get("pass"):
                continue
            if gate == "G0.5" and verdict.get("eager_fallback"):
                eager_phases.append(phase)
                continue
            phase_failures.setdefault(phase.split("/", 1)[0], []).append(gate)
    status = summary.get("status")
    accepted = status in ACCEPTED_JOB_STATUSES and not job_gate_failures
    return {
        "accepted": bool(accepted),
        "status": status,
        "eager": bool(eager_phases),
        "eager_phases": sorted(eager_phases),
        "job_gate_failures": job_gate_failures,
        "phase_gate_failures": {phase: sorted(set(g)) for phase, g in phase_failures.items()},
    }


def ledger_for(config: ProbeConfig, job: JobSpec, start: float) -> LaunchLedger:
    stop = config.section("stop")
    raw_job = config.raw["jobs"][job.job_id]
    return LaunchLedger(
        start=start,
        allocation_minutes=job.allocation_minutes,
        soft_fraction=float(stop["soft_fraction"]),
        hard_margin_minutes=float(stop["hard_margin_minutes"]),
        phases=[
            PhaseBudget(
                phase.phase_id,
                phase_start_minutes(raw_job, phase.phase_id),
                {p.point_id: p.max_minutes for p in phase.points if is_required(p)},
            )
            for phase in job.phases
        ],
    )


def plan_payload(config: ProbeConfig, job: JobSpec, model_root: str) -> dict[str, Any]:
    image_tokens = int(config.section("budget")["q2"]["image_tokens"])
    plan = v1.plan_payload(config, job, model_root)
    plan["launch_window"] = launch_window_check(config, job.job_id)
    plan["warmup_dominance"] = {
        phase.phase_id: check_warmup_dominates(phase, image_tokens) for phase in job.phases
    }
    plan["required_points"] = {
        phase.phase_id: [p.point_id for p in phase.points if is_required(p)] for phase in job.phases
    }
    return plan


#: Added by ``project`` to every Q2 cell when F1 is not valid (v1's rule then applies no
#: front-end correction, which is not conservative: F1 can only raise the open-loop bound).
FRONTEND_UNCORRECTED = (
    "front-end-uncorrected (f1 not valid: the open-loop bound has no PNG correction, "
    "which can only understate it)"
)


def attribution_record(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    """G0.9's attribution per phase: mode, basis, PID check and what it can detect.

    Reported next to X1 and the Q2 outcome, because what "no foreign process"
    means depends on the basis (``harness.serving_probe_v2.contamination``).
    """
    verdicts = ((summary or {}).get("gates") or {}).get("G0.9") or {}
    keys = ("pass", "mode", "basis", "pid_check", "foreign_process_detection", "reason")
    return {phase: {key: verdict.get(key) for key in keys} for phase, verdict in verdicts.items()}


def _attempt_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: record.get(key) for key in ("attempt", "status", "checks", "error")}


class ProbeRunnerV2(v1.ProbeRunner):
    """v1's runner with v2's ledger, warm-up reservation, contamination rule and X1."""

    def __init__(
        self,
        *,
        apps_sampler_factory: Callable[[Path, Callable[[], set[int]]], Any] | None = None,
        prereg_check: Callable[[ProbeConfig], dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(prereg_check=prereg_check or verify_preregistration, **kwargs)
        factory = self.engine_factory

        def tracked(phase: PhaseSpec, model_dir: str, log_path: Path) -> Any:
            # The compute-process poller attributes PIDs to the engine from its creation.
            self._engine = factory(phase, model_dir, log_path)
            return self._engine

        self.engine_factory = tracked
        interval = float(self.config.section("sampling")["apps_interval_s"])
        self.apps_sampler_factory = apps_sampler_factory or (
            lambda path, pids: cont.AppsSampler(path, interval, pids)
        )
        self.apps: Any = None
        self.ledger: LaunchLedger | None = None
        self._engine: Any = None
        self._last_window: tuple[float, float] | None = None
        #: The last G0.8 window (perf times) and when the engine answered /health: a
        #: host-namespace PID is the engine's only if first listed between the two.
        self._baseline_window: tuple[float, float] | None = None
        self._engine_ready_at: float | None = None

    # -- infrastructure -------------------------------------------------

    def _engine_pids(self) -> set[int]:
        engine = self._engine
        pid = getattr(engine, "pid", None) if engine is not None else None
        if not pid:
            return set()
        try:
            return set(process_tree(int(pid)))
        except OSError:
            return {int(pid)}

    def _baseline(self) -> dict[str, Any]:
        """G0.8: v1's idle-device check plus an empty compute-process list."""
        gates = self.config.section("gates")
        self.sleep(float(gates["baseline_settle_s"]))
        start = time.perf_counter()
        self.sleep(float(gates["baseline_duration_s"]))
        end = time.perf_counter()
        self._baseline_window = (start, end)
        verdict = baseline_verdict(
            self.sampler.window(start, end),
            max_memory_mib=float(gates["baseline_max_memory_used_mib"]),
            max_utilization_pct=float(gates["baseline_max_utilization_pct"]),
        )
        apps = cont.baseline_apps_verdict(self.apps.window(start, end) if self.apps else [])
        return {**verdict, "pass": bool(verdict["pass"] and apps["pass"]), "compute_apps": apps}

    # -- main -----------------------------------------------------------

    def run(self) -> int:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("points", "engines", "doctor", "samples"):
            (self.output_dir / sub).mkdir(exist_ok=True)
        for path in self.env.values():
            if path.startswith(str(self.output_dir)):
                Path(path).mkdir(parents=True, exist_ok=True)
        self._console_fd = os.dup(2)
        self._install_signals()
        if os.getpid() == 1:
            threading.Thread(target=self._reaper, name="reaper", daemon=True).start()
        self.summary = {
            "experiment_id": self.config.experiment_id,
            "job": self.job.job_id,
            "config_path": v1._display_path(self.config.path),
            "config_sha256": self.config.sha256,
            "argv": self.argv,
            "seeds": self.seeds,
            "image_variant": self.variant,
            "started_at": utc_now(),
            "gates": {},
            "phases": {},
            "eager": False,
        }
        atomic_write_json(
            self.output_dir / "plan.json",
            {
                **plan_payload(self.config, self.job, str(self.model_root)),
                "env": self.env,
                "argv": self.argv,
                "pins": self.pins,
            },
        )
        exit_code, status = EXIT_CRASH, "crashed"
        try:
            exit_code, status = self._run_job()
        except GateFailure as exc:
            self.log(f"pre-result: {exc}")
            self.summary["pre_result_reason"] = str(exc)
            exit_code, status = EXIT_PRE_RESULT, "pre-result"
        except ProbeInterrupted:
            exit_code, status = EXIT_INTERRUPTED, "interrupted"
        except Exception as exc:  # noqa: BLE001 - recorded in the summary, exit code 1
            self.log(f"crash: {type(exc).__name__}: {exc}")
            self.summary["crash"] = f"{type(exc).__name__}: {exc}"[:2000]
            exit_code, status = EXIT_CRASH, "crashed"
        finally:
            if self.stop_event.is_set() and status != "pre-result":
                exit_code, status = EXIT_INTERRUPTED, "interrupted"
            self._finalize(status, exit_code)
        return exit_code

    def _run_job(self) -> tuple[int, str]:
        self.summary["gates"]["G0.0"] = {"pass": True, "ledger_row": self.prereg_check(self.config)}
        existing = self._load_existing()
        for point_id, record in existing.items():
            self.point_status[point_id] = record["status"]
        self.summary["resumed_terminal_points"] = sorted(
            point for point, record in existing.items() if record["status"] in TERMINAL_STATUSES
        )
        lane = v1.check_lane_outputs(self.outputs_root, self.config, self.job)
        check_pins(self.job, self.pins)
        self.summary["gates"]["G0.1"] = {"pass": True, **lane}

        now_perf = time.perf_counter()
        start, anchor = v1.allocation_start_perf(
            self.outputs_root / "job.env", now_wall=time.time(), now_perf=now_perf
        )
        self.ledger = ledger_for(self.config, self.job, start)
        self.summary["launch_window"] = {
            "anchor": anchor,
            "elapsed_at_driver_start_s": now_perf - start,
            **self.ledger.describe(),
        }
        self._write_progress("gates")

        doctor_report = self.doctor(self.output_dir / "doctor" / "cuda-doctor.json", self.env)
        for gate in ("G0.2", "G0.3", "G0.4"):
            self.summary["gates"][gate] = doctor_report.get(gate, {"pass": False})
        if not doctor_report.get("pass"):
            raise GateFailure("G0.2-G0.4 CUDA doctor failed; see doctor/cuda-doctor.json")

        self.sampler = self.sampler_factory(self.output_dir / "samples" / "nvidia-smi.csv")
        self.sampler.start()
        process = getattr(self.sampler, "_process", None)
        if process is not None and getattr(process, "pid", None):
            self._tracked.add(int(process.pid))
        self.apps = self.apps_sampler_factory(
            self.output_dir / "samples" / "compute-apps.csv", self._engine_pids
        )
        self.apps.start()
        cut = False
        for index, phase in enumerate(self.job.phases):
            if self.stop_event.is_set():
                break
            outcome = self._run_phase(index, phase, existing)
            self.summary["phases"][phase.phase_id] = outcome
            cut = cut or bool(outcome.get("cut"))
            if self.stop_event.is_set():
                break
            gate = outcome.get("gate_failed")
            if gate and phase.role == "primary":
                raise GateFailure(f"{gate} failed in phase {phase.phase_id}")
        return EXIT_OK, ("complete-with-cuts" if cut else "complete")

    def _pending(self, phase: PhaseSpec, existing: Mapping[str, dict[str, Any]]) -> list[str]:
        reruns = int(self.config.section("validity")["reruns_per_invalid_point"])
        pending = []
        for point in phase.points[2:]:
            record = existing.get(point.point_id, {})
            status = record.get("status")
            if status not in TERMINAL_STATUSES or (
                status == "invalid"
                and record.get("rerun_pending")
                and len(record.get("attempts", [])) < 1 + reruns
            ):
                pending.append(point.point_id)
        return pending

    def _run_phase(
        self, index: int, phase: PhaseSpec, existing: Mapping[str, dict[str, Any]]
    ) -> dict[str, Any]:
        assert self.ledger is not None
        outcome: dict[str, Any] = {"engine": phase.engine.engine_id, "role": phase.role}
        if not self._pending(phase, existing):
            outcome["skipped"] = "every point is already terminal (resume)"
            return outcome
        bound = self.ledger.bound(index)
        if time.perf_counter() >= bound:
            self._mark_not_run(phase.points, "launch window: the phase bound passed before start")
            outcome.update({"cut": True, "skipped": "phase bound passed before start"})
            return outcome
        if self.stop_event.is_set():
            return outcome
        baseline = self._baseline()
        outcome["G0.8"] = baseline
        self.summary["gates"].setdefault("G0.8", {})[phase.phase_id] = baseline
        if not baseline["pass"]:
            self._mark_not_run(phase.points, "G0.8 device baseline failed")
            outcome["gate_failed"] = "G0.8"
            return outcome
        if self.stop_event.is_set():
            return outcome
        engine_dir = self.output_dir / "engines" / phase.phase_id
        engine_dir.mkdir(parents=True, exist_ok=True)
        self._engine_ready_at = None
        engine, attempts, stopped_by = self._start_engine(phase, engine_dir, bound)
        if engine is not None:
            self._engine_ready_at = time.perf_counter()
        default_mode = engine is not None and not any(
            a.get("eager") for a in attempts if a["ready"]
        )
        verdict = {
            "pass": bool(default_mode),
            "eager_fallback": engine is not None and not default_mode,
            "attempts": attempts,
        }
        outcome["G0.5"] = verdict
        self.summary["gates"].setdefault("G0.5", {})[phase.phase_id] = verdict
        if engine is None:
            self._engine = None
            gate = stopped_by or "G0.5"
            self._mark_not_run(phase.points, f"{gate} failed while starting the engine")
            outcome["gate_failed"] = gate
            if not self.stop_event.is_set():
                outcome["memory_release"] = self._wait_memory_released()
            return outcome
        if not default_mode:
            self.eager = True
            self.summary["eager"] = True
        self._engine = engine
        facts = parse_engine_log(engine.log_text())
        facts["tmp_mapped_files"] = engine.tmp_maps()
        outcome["engine_facts"] = facts
        try:
            outcome.update(self._run_points(index, phase, engine, existing))
            if not self.stop_event.is_set():
                # A rerun still pending when the phase ends will not run (a resumed
                # job after a signal keeps it pending).
                for point in phase.points[2:]:
                    held = self._read_point(point)
                    if held and held.get("rerun_pending"):
                        held.update({"rerun_pending": False, "rerun": "not launched"})
                        self._record(point, held)
                        outcome.setdefault("reruns_not_launched", []).append(point.point_id)
        finally:
            self._checkpoint_after_signal()
            outcome["engine_facts_final"] = parse_engine_log(engine.log_text())
            outcome["engine_stop"] = engine.stop()
            self._engine = None
            self._reaper_paused.clear()
            if not self.stop_event.is_set():
                outcome["memory_release"] = self._wait_memory_released()
        return outcome

    # -- the point loop -------------------------------------------------------

    def _launch(
        self,
        index: int,
        point: PointSpec,
        attempt: int,
        context: tuple[Any, ...],
        reservation: cont.Reservation | None,
        previous: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """Run one attempt, merge it with the earlier ones and persist the point file."""
        assert self.ledger is not None
        engine, tokenizer, allowed, size, pool = context
        now = time.perf_counter()
        deadline = self.ledger.deadline(index, now=now, cap_minutes=point.max_minutes)
        record = self._execute(
            point, attempt, engine, tokenizer, allowed, size, pool, deadline, reservation
        )
        earlier = list((previous or {}).get("attempts", []))
        superseded = list((previous or {}).get("superseded_attempts", []))
        if previous:
            superseded.append(
                {
                    key: value
                    for key, value in previous.items()
                    if key not in {"attempts", "superseded_attempts", "rerun_pending", "rerun"}
                }
            )
        record["attempts"] = [*earlier, _attempt_summary(record)]
        # Earlier attempts are kept in full (metrics included); the last one stands.
        record["superseded_attempts"] = superseded
        reruns = int(self.config.section("validity")["reruns_per_invalid_point"])
        record["rerun_pending"] = (
            record["status"] == "invalid" and len(record["attempts"]) < 1 + reruns
        )
        self._record(point, record)
        self.log(f"{point.point_id} attempt {attempt}: {record['status']}")
        return record

    def _stop_reason(self, record: Mapping[str, Any], engine: Any) -> str | None:
        if record["status"] == "interrupted" or self.stop_event.is_set():
            return "signal"
        if record["status"] == "failed-infra" or not engine.alive():
            return "engine"
        return None

    def _gate_attempts(
        self,
        index: int,
        point: PointSpec,
        context: tuple[Any, ...],
        pending: Sequence[str],
    ) -> tuple[dict[str, Any], str | None]:
        """The smoke or the warm-up: one attempt, then at most one immediate rerun from slack.

        ``pending`` lists the phase's required points still to run after this one,
        whose reserved time a rerun may not take.
        """
        assert self.ledger is not None
        reruns = int(self.config.section("validity")["reruns_per_invalid_point"])
        engine = context[0]
        record: dict[str, Any] = {}
        for attempt in range(1, 2 + reruns):
            kind = FIRST if attempt == 1 else RERUN
            if not self.ledger.may_launch(
                index,
                now=time.perf_counter(),
                point_id=point.point_id,
                kind=kind,
                cap_minutes=point.max_minutes,
                required_pending=pending,
            ):
                if attempt == 1:
                    return record, "bound"
                break
            record = self._launch(index, point, attempt, context, None, record or None)
            stop = self._stop_reason(record, engine)
            if stop or record["status"] != "invalid":
                return record, stop
        return record, None

    def _run_points(
        self,
        index: int,
        phase: PhaseSpec,
        engine: Any,
        existing: Mapping[str, dict[str, Any]],
    ) -> dict[str, Any]:
        assert self.ledger is not None
        outcome: dict[str, Any] = {"cut": False, "reruns_not_launched": []}
        validity = self.config.section("validity")
        reruns = int(validity["reruns_per_invalid_point"])
        screenshot = self.config.section("screenshot")
        size = (int(screenshot["width"]), int(screenshot["height"]))
        tokenizer = self.tokenizer_loader(engine.model_dir)
        allowed = allowed_token_ids(tokenizer)
        roles = phase_points(phase)
        (smoke,) = roles["smoke"]
        (warmup,) = roles["warmup"]

        def left(*, besides: str | None = None) -> list[PointSpec]:
            return [
                p
                for p in phase.points
                if self.point_status.get(p.point_id) not in TERMINAL_STATUSES
                and p.point_id != besides
            ]

        def engine_failed(point: PointSpec) -> None:
            self._mark_not_run(left(besides=point.point_id), "engine failed")
            outcome["engine_failed"] = True

        with ThreadPoolExecutor(max_workers=8) as pool:
            context = (engine, tokenizer, allowed, size, pool)
            # 1. The smoke (gates G0.6, G0.7), as in v1.
            later = [p.point_id for p in (warmup, *roles["required"])]
            record, stop = self._gate_attempts(index, smoke, context, later)
            if stop == "bound":
                self._mark_not_run(left(), "launch window: the phase bound passed")
                outcome["cut"] = True
                return outcome
            if stop == "signal":
                self._checkpoint_after_signal()
                return outcome
            if stop == "engine":
                engine_failed(smoke)
                reason = f"smoke {record['status']}: {record.get('error')}"
                self._fail_gate(phase, "G0.6", {"pass": False, "reason": reason}, outcome)
                return outcome
            gates = record.get("gates", {})
            outcome.update(gates)
            for gate, verdict in gates.items():
                self.summary["gates"].setdefault(gate, {})[phase.phase_id] = verdict
            if record["status"] not in VALID_STATUSES:
                failed = [g for g, v in gates.items() if not v.get("pass")]
                if not failed:
                    bad = sorted(k for k, ok in record.get("checks", {}).items() if not ok)
                    verdict = {
                        **gates.get("G0.6", {}),
                        "pass": False,
                        "reason": f"smoke {record['status']}; failed checks {bad}",
                    }
                    self._fail_gate(phase, "G0.6", verdict, outcome)
                    failed = ["G0.6"]
                outcome["gate_failed"] = failed[0]
                self._mark_not_run(left(besides=smoke.point_id), f"{failed[0]} failed in the smoke")
                return outcome

            # 2. The warm-up at the largest registered shape, then the reservation (G0.9).
            later = [p.point_id for p in roles["required"]]
            record, stop = self._gate_attempts(index, warmup, context, later)
            if stop == "bound":
                self._mark_not_run(left(), "launch window: the phase bound passed")
                outcome["cut"] = True
                return outcome
            if stop == "signal":
                self._checkpoint_after_signal()
                return outcome
            reservation, verdict = self._reserve(record)
            self.summary["gates"].setdefault("G0.9", {})[phase.phase_id] = verdict
            outcome["G0.9"] = verdict
            if stop == "engine" or reservation is None:
                if stop == "engine":
                    engine_failed(warmup)
                outcome["gate_failed"] = "G0.9"
                self._mark_not_run(left(besides=warmup.point_id), "G0.9 reservation failed")
                return outcome
            outcome["reservation"] = reservation.describe()

            # 3-6. Required first attempts, then reruns and optional points from slack.
            required = [p for p in roles["required"]]
            optional = [p for p in roles["optional"]]
            reruns_required: list[PointSpec] = []
            reruns_optional: list[PointSpec] = []
            first_done: set[str] = set()

            def queue_rerun(point: PointSpec, record: Mapping[str, Any]) -> None:
                if record.get("status") == "invalid" and len(record.get("attempts", [])) < (
                    1 + reruns
                ):
                    (reruns_required if is_required(point) else reruns_optional).append(point)

            stages: list[tuple[str, list[PointSpec]]] = [
                (FIRST, required),
                (RERUN, reruns_required),
                (OPTIONAL, optional),
                (RERUN, reruns_optional),
            ]
            for kind, points in stages:
                for point in list(points):
                    previous = existing.get(point.point_id)
                    if kind != RERUN and previous and previous.get("status") in TERMINAL_STATUSES:
                        first_done.add(point.point_id)
                        if previous.get("rerun_pending"):
                            queue_rerun(point, previous)
                        continue
                    if self.stop_event.is_set():
                        return outcome
                    if not engine.alive():
                        engine_failed(point)
                        return outcome
                    pending = [
                        p.point_id
                        for p in required
                        if p.point_id not in first_done and p.point_id != point.point_id
                    ]
                    allowed_now = self.ledger.may_launch(
                        index,
                        now=time.perf_counter(),
                        point_id=point.point_id,
                        kind=kind,
                        cap_minutes=point.max_minutes,
                        required_pending=pending,
                    )
                    if not allowed_now:
                        outcome["cut"] = True
                        if kind == FIRST:
                            self._mark_not_run(left(), "launch window: the phase bound passed")
                            return outcome
                        if kind == OPTIONAL:
                            self._mark_not_run(
                                [point], "launch window: no slack for an optional point"
                            )
                            continue
                        held = dict(self._read_point(point) or {})
                        held.update({"rerun_pending": False, "rerun": "not launched: no slack"})
                        self._record(point, held)
                        outcome["reruns_not_launched"].append(point.point_id)
                        continue
                    prior = self._read_point(point) if kind == RERUN else None
                    attempt = 1 if prior is None else len(prior.get("attempts", [])) + 1
                    record = self._launch(index, point, attempt, context, reservation, prior)
                    first_done.add(point.point_id)
                    stop = self._stop_reason(record, engine)
                    if stop == "signal":
                        self._checkpoint_after_signal()
                        return outcome
                    if stop == "engine":
                        engine_failed(point)
                        return outcome
                    if kind != RERUN:
                        queue_rerun(point, record)
        return outcome

    def _read_point(self, point: PointSpec) -> dict[str, Any] | None:
        path = self.points_dir / f"{point.point_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _reserve(self, warmup: Mapping[str, Any]) -> tuple[cont.Reservation | None, dict[str, Any]]:
        """G0.9: the warm-up completed; then the reservation over it and the window after it."""
        if warmup.get("status") not in VALID_STATUSES or self._last_window is None:
            return None, {
                "pass": False,
                "reason": f"the largest-shape warm-up ended {warmup.get('status')!r}",
            }
        if self._baseline_window is None or self._engine_ready_at is None:
            return None, {"pass": False, "reason": "no G0.8 window or engine readiness time"}
        window_s = float(self.config.section("validity")["reservation_window_s"])
        self.sleep(window_s)
        start, end = self._last_window[0], time.perf_counter()
        samples = self.sampler.window(start, end)
        snapshots = self.apps.window(start, end) if self.apps else []
        history = self.apps.window(self._baseline_window[0], end) if self.apps else []
        reservation, verdict = cont.measure_reservation(
            samples,
            snapshots,
            history=history,
            engine_start_at=self._baseline_window[1],
            engine_ready_at=self._engine_ready_at,
        )
        verdict["warmup_prompt_tokens_max"] = max(
            (entry[1] for entry in warmup.get("request_identity", {}).get("requests", {}).values()),
            default=None,
        )
        return reservation, verdict

    # -- one attempt ------------------------------------------------------

    def _execute(
        self,
        point: PointSpec,
        attempt: int,
        engine: Any,
        tokenizer: Any,
        allowed: np.ndarray,
        size: tuple[int, int],
        pool: ThreadPoolExecutor,
        deadline: float,
        reservation: cont.Reservation | None,
    ) -> dict[str, Any]:
        record = self._base_record(point, attempt)
        record["started_at"] = utc_now()
        try:
            body = self._server_point(
                point, engine, tokenizer, allowed, size, pool, deadline, reservation
            )
        except ProbeInterrupted:
            record.update({"status": "interrupted", "reason": self.signal_name})
            return record
        except (httpx.HTTPError, OSError, RuntimeError, ValueError, KeyError) as exc:
            record.update({"status": "failed-infra", "error": f"{type(exc).__name__}: {exc}"[:500]})
            return record
        record.update(body)
        validity = self.config.section("validity")
        resets = [body["cache_reset"]]
        status, flags, checks = v1.assess_point(
            body["result"],
            counters=body["counter_check"],
            gpu=body["gpu"],
            reservation_mib=None,
            reservation_required=False,
            margin_mib=float(validity["contamination_margin_mib"]),
            api_cpu_pct=body.get("api_server_cpu_pct"),
            client_cpu_pct=body.get("client_cpu_pct"),
            flag_pct=float(validity["frontend_cpu_flag_pct"]),
            stop_reason=body.get("stop_reason"),
            ran_to_end=body["ran_to_end"],
            caches_ok=v1.caches_reset(resets, server=True),
            min_samples=v1.min_gpu_samples(
                float(body["result"].get("duration_s") or 0.0),
                float(self.config.section("sampling")["gpu_interval_ms"]),
                float(validity["min_gpu_sample_fraction"]),
            ),
        )
        contamination = body.get("contamination")
        if contamination is not None:
            checks.update(contamination["checks"])
            flags = [*flags, *contamination["flags"]]
            if status in VALID_STATUSES:
                if not all(checks.values()):
                    status = "invalid"
                else:
                    status = "valid-flagged" if flags else "valid"
        gates = body.get("gates")
        gates_failed = gates and not all(verdict.get("pass") for verdict in gates.values())
        if gates_failed and status in VALID_STATUSES:
            status = "invalid"
        record.update(
            {"status": status, "flags": flags, "checks": checks, "finished_at": utc_now()}
        )
        return record

    def _server_point(
        self,
        point: PointSpec,
        engine: Any,
        tokenizer: Any,
        allowed: np.ndarray,
        size: tuple[int, int],
        pool: ThreadPoolExecutor,
        deadline: float,
        reservation: cont.Reservation | None = None,
    ) -> dict[str, Any]:
        timeout_s = float(self.config.section("server")["request_timeout_s"])
        gates_cfg = self.config.section("gates")
        validity = self.config.section("validity")
        prep_start = time.perf_counter()
        payload: Any
        if point.kind == "replay":
            payload = build_fixed_replay_plans(point, tokenizer, allowed, size, pool)
        elif point.kind == "smoke-server":
            payload = v1.build_smoke_requests(point, tokenizer, allowed, size, pool)
        else:
            payload = v1.build_open_loop_requests(point, tokenizer, allowed, size, pool)
        prep_s = time.perf_counter() - prep_start
        reset = engine.reset_caches()
        before = engine.metrics()
        api_start = read_cpu_ticks(engine.pid) if engine.pid else None
        me_start = read_cpu_ticks(os.getpid())
        stop = StopToken(
            deadline=max(deadline, time.perf_counter() + 1.0),
            external=self.stop_event,
            grace_s=float(self.config.section("stop")["in_flight_grace_s"]),
        )
        kv: list[tuple[float, float | None, float | None, float | None]] = []
        started = time.perf_counter()
        body = asyncio.run(self._server_coroutine(point, engine, payload, stop, kv, timeout_s))
        finished = time.perf_counter()
        self._last_window = (started, finished)
        after = engine.metrics()
        wall = finished - started
        api_end = read_cpu_ticks(engine.pid) if engine.pid else None
        result = body["result"]
        deltas = point_counter_deltas(before, after)
        counters = check_counters(
            deltas,
            client_prompt_tokens=int(result["prompt_tokens"]),
            client_output_tokens=int(result["output_tokens"]),
            prompt_tolerance=float(gates_cfg["prompt_counter_relative_tolerance"]),
        )
        self._write_kv_trace(point.point_id, kv)
        gpu = summarize_gpu(self.sampler.window(started, finished))
        snapshots = self.apps.window(started, finished) if self.apps else []
        out: dict[str, Any] = {
            "prep_s": prep_s,
            "cache_reset": reset,
            "result": result,
            "counters": deltas,
            "counter_check": counters,
            "gpu": gpu,
            "compute_apps": cont.describe_snapshots(snapshots),
            "request_identity": request_identity(body["results"]),
            "api_server_cpu_pct": cpu_percent(api_start, api_end, wall),
            "client_cpu_pct": cpu_percent(me_start, read_cpu_ticks(os.getpid()), wall),
            "kv_cache_usage_peak": max((r[1] for r in kv if r[1] is not None), default=None),
            "num_requests_waiting_peak": max((r[3] for r in kv if r[3] is not None), default=None),
            "ran_to_end": body["ran_to_end"],
            "stop_reason": body["stop_reason"],
        }
        if reservation is not None:
            interval = float(self.config.section("sampling")["apps_interval_s"])
            checks, flags, details = cont.assess_contamination(
                reservation=reservation,
                device_peak_mib=gpu.get("peak_memory_used_mib"),
                snapshots=snapshots,
                needed_snapshots=cont.min_snapshots(
                    float(result.get("duration_s") or 0.0),
                    interval,
                    float(validity["min_apps_snapshot_fraction"]),
                ),
                device_margin_mib=float(validity["contamination_margin_mib"]),
                own_margin_mib=float(validity["own_footprint_margin_mib"]),
                unattributed_margin_mib=float(validity["unattributed_margin_mib"]),
            )
            out["contamination"] = {"checks": checks, "flags": flags, **details}
        if point.kind == "smoke-server":
            differential = v1.image_differential(
                body["results"],
                int(gates_cfg["image_tokens_expected"]),
                float(gates_cfg["image_tokens_relative_tolerance"]),
            )
            smoke_ok = (
                result["failed"] == 0
                and result["completed"] == result["planned"]
                and result["short_outputs"] == 0
            )
            out["gates"] = {
                "G0.6": {
                    "pass": bool(smoke_ok and differential["pass"]),
                    "smoke_ok": smoke_ok,
                    "image_differential": differential,
                },
                "G0.7": counters,
            }
        return out

    async def _server_coroutine(
        self,
        point: PointSpec,
        engine: Any,
        payload: Any,
        stop: StopToken,
        kv: list[Any],
        timeout_s: float,
    ) -> dict[str, Any]:
        done = asyncio.Event()
        interval = float(self.config.section("sampling")["kv_poll_interval_s"])

        async def poll(client: httpx.AsyncClient) -> None:
            while not done.is_set():
                with contextlib.suppress(httpx.HTTPError):
                    snapshot = parse_prometheus((await client.get("/metrics")).text)
                    kv.append(
                        (
                            time.perf_counter(),
                            snapshot.get("vllm:kv_cache_usage_perc"),
                            snapshot.get("vllm:num_requests_running"),
                            snapshot.get("vllm:num_requests_waiting"),
                        )
                    )
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(done.wait(), timeout=interval)

        output_tokens = int(point["output_tokens"])
        async with engine.async_client() as client:
            poller = asyncio.create_task(poll(client))
            try:
                if point.kind == "replay":
                    records, start, end, spans = await run_fixed_replay(
                        client, payload, model=engine.served_name, timeout_s=timeout_s, stop=stop
                    )
                    planned_steps = payload[0].steps if payload else []
                    result = summarize_replay(
                        records,
                        episodes=len(payload),
                        planned_steps=planned_steps,
                        start=start,
                        end=end,
                        spans=spans,
                        expected_output=output_tokens,
                    )
                    ran_to_end = len(records) == len(payload) * len(planned_steps)
                    return {
                        "result": result,
                        "results": [record.result for record in records],
                        "ran_to_end": ran_to_end,
                        "stop_reason": None if ran_to_end else stop.reason(),
                    }
                results, start, end, unlaunched = await run_open_loop(
                    client,
                    payload,
                    concurrency=int(point["concurrency"]),
                    model=engine.served_name,
                    timeout_s=timeout_s,
                    stop=stop,
                )
                result = summarize_requests(
                    results,
                    planned=len(payload),
                    start=start,
                    end=end,
                    expected_output=output_tokens,
                )
                ran_to_end = unlaunched == 0 and len(results) == len(payload)
                return {
                    "result": result,
                    "results": results,
                    "ran_to_end": ran_to_end,
                    "stop_reason": None if ran_to_end else stop.reason(),
                }
            finally:
                done.set()
                await poller

    # -- finalize -----------------------------------------------------------

    def _finalize(self, status: str, exit_code: int) -> None:
        for sampler in (self.sampler, self.apps):
            with contextlib.suppress(Exception):
                if sampler is not None:
                    sampler.stop()
        points: dict[str, dict[str, Any]] = {}
        point_sha256: dict[str, str] = {}
        if self.points_dir.is_dir():
            for path in sorted(self.points_dir.glob("*.json")):
                record = json.loads(path.read_text(encoding="utf-8"))
                points[record["point_id"]] = record
                point_sha256[path.stem] = sha256_file(path)
        self.summary["points"] = {name: record.get("status") for name, record in points.items()}
        self.summary["point_sha256"] = point_sha256
        limit = float(self.config.section("validity")["unstable_relative_range"])
        self.summary["x1"] = evaluate_x1(points, self.config.section("dummy_admissibility"))
        self.summary["x1"]["attribution"] = attribution_record(self.summary)
        self.summary["a1_stability"] = budget_rules.stability(points, ("a1a", "a1b", "a1c"), limit)
        if self.ledger is not None:
            self.summary["launch_decisions"] = list(self.ledger.decisions)
        self.summary.update(
            {
                "status": status,
                "exit_code": exit_code,
                "finished_at": utc_now(),
                "signal": self.signal_name,
                "signals_received": list(self.signals_received),
            }
        )
        self.summary["acceptance"] = job_acceptance(self.summary)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.output_dir / "summary.json", self.summary)
        self._write_progress(status)
        # The marker answers signals only; a run that received none never writes it.
        self._checkpoint_after_signal(state=status)
        self._reaper_stop.set()
        if os.getpid() == 1:
            self._reap_once()


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def job_admission(directory: Path, config: ProbeConfig, job_id: str) -> dict[str, Any]:
    """v1's admission rule (preregistration section 5) with v2's acceptance."""
    path = directory / "summary.json"
    termination = v1.lane_termination(directory)
    if not path.is_file():
        return {
            "summary": None,
            "lane_termination": termination,
            "accepted": False,
            "reasons": ["no summary.json (the driver did not finish)"]
            + ([termination["problem"]] if termination["problem"] else []),
        }
    summary = json.loads(path.read_text(encoding="utf-8"))
    if (
        summary.get("experiment_id") != config.experiment_id
        or summary.get("config_sha256") != config.sha256
        or summary.get("job") != job_id
    ):
        raise ProjectionError(f"{path} belongs to another experiment, contract or job")
    reasons: list[str] = []
    recorded = summary.get("acceptance") or {}
    if recorded.get("accepted") is not True:
        reasons.append(
            f"summary records acceptance.accepted {recorded.get('accepted')!r} "
            f"(status {summary.get('status')!r})"
        )
    recomputed = job_acceptance(summary)
    if not recomputed["accepted"]:
        reasons.append(
            f"acceptance recomputed from the summary is false (status "
            f"{summary.get('status')!r}, job gate failures {recomputed['job_gate_failures']})"
        )
    if summary.get("exit_code") != EXIT_OK:
        reasons.append(f"driver exit code {summary.get('exit_code')!r}")
    on_disk = {p.stem: sha256_file(p) for p in sorted((directory / "points").glob("*.json"))}
    listed = summary.get("point_sha256")
    if not isinstance(listed, Mapping):
        reasons.append("summary lists no point SHA-256s")
    elif dict(listed) != on_disk:
        changed = sorted(
            name for name in set(listed) | set(on_disk) if listed.get(name) != on_disk.get(name)
        )
        reasons.append(f"point files differ from those the summary lists: {changed}")
    if termination["problem"]:
        reasons.append(termination["problem"])
    return {
        "summary_sha256": sha256_file(path),
        "status": summary.get("status"),
        "exit_code": summary.get("exit_code"),
        "acceptance": recorded,
        "eager": summary.get("eager"),
        "image_variant": summary.get("image_variant"),
        "lane_termination": termination,
        "accepted": not reasons,
        "reasons": reasons,
    }


def project(
    config: ProbeConfig,
    *,
    job_a: Path,
    prereg_check: Callable[[ProbeConfig], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply the preregistered Q2 rules and control X1 to job a's outputs.

    Refuses unless the frozen v2 preregistration names this contract and this
    probe code, and refuses point files from another contract, job or
    experiment. Only an admitted job's points enter the budget. Q1 is not
    projected by v2.
    """
    try:
        prereg = (prereg_check or verify_preregistration)(config)
    except GateFailure as exc:
        raise ProjectionError(f"projection refused: {exc}") from exc
    budget = config.section("budget")
    limit = float(config.section("validity")["unstable_relative_range"])
    loaded = v1.load_job_points(job_a, config, "a")
    admission = job_admission(job_a, config, "a")
    points = loaded if admission["accepted"] else None
    x1 = evaluate_x1(points or {}, config.section("dummy_admissibility"))
    if points is None:
        x1["reason"] = "job a is not accepted; its points enter no budget"
    summary_path = job_a / "summary.json"
    attribution = attribution_record(
        json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
    )
    x1["attribution"] = attribution
    out: dict[str, Any] = {
        "experiment_id": config.experiment_id,
        "config_sha256": config.sha256,
        "preregistration": prereg,
        "code": {**probe_code_digest(), "git": git_revision()},
        "jobs": {"a": admission},
        "x1": x1,
        "a1_stability": v1.seed_stability_report(
            "a",
            job_a,
            points,
            seeds=("a1a", "a1b", "a1c"),
            summary_key="a1_stability",
            limit=limit,
        ),
        "q1": {
            "decision": "not-projected",
            "reason": "v2 registers Q2 cells only; Q1 stays with serving-throughput-probe-v1",
        },
    }
    max_model_len = max(
        int(config.engines[phase.engine.engine_id].flags["max_model_len"])
        for phase in config.job("a").phases
    )
    if points is None:
        reasons = "; ".join(admission["reasons"])
        out["q2"] = {
            "decision": "incomplete-re-probe",
            "reason": f"job a is not accepted: {reasons}",
            "attribution": attribution.get("real"),
        }
        return out
    try:
        q2 = budget_rules.project_q2(
            budget,
            job_a=points,
            job_c=None,
            x1_outcome=x1["outcome"],
            unstable_limit=limit,
            max_model_len=max_model_len,
        )
    except budget_rules.BudgetError as exc:
        q2 = {"decision": "incomplete-re-probe", "reason": str(exc)}
    if q2.get("frontend_correction", {}).get("ratio") is None and "cells" in q2:
        for cell in q2["cells"]:
            cell["flags"].append(FRONTEND_UNCORRECTED)
        q2["frontend_uncorrected"] = {
            "cells": len(q2["cells"]),
            "open_loop_binding": sum(1 for cell in q2["cells"] if cell["binding"] == "open-loop"),
        }
    q2["attribution"] = attribution.get("real")
    out["q2"] = q2
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def vllm_args_doctor(config: ProbeConfig) -> dict[str, Any]:
    """v1's CPU-only parser check of every engine, plus v2's request payload."""
    from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest

    report = v1.vllm_args_doctor(config)
    image = {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
    message = [{"role": "user", "content": [{"type": "text", "text": "x"}, image]}]
    for thinking in (False, True):
        request = ChatCompletionRequest(
            **build_payload_v2(ChatRequest(message, 300, thinking), model="m")
        )
        ok = (
            request.return_token_ids is True
            and request.ignore_eos is True
            and request.min_tokens == 300
            and request.chat_template_kwargs == {"enable_thinking": thinking}
            and request.stream is True
        )
        report[f"v2_payload_thinking_{thinking}"] = ok
        report["pass"] = report["pass"] and ok
    return report


def build_parser() -> argparse.ArgumentParser:
    # allow_abbrev=False everywhere: the lane's seed binding assumes no option can be
    # reached by an abbreviation (docs/operations.md, seed_binding).
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    plan.add_argument("--job", required=True)
    plan.add_argument("--model-root", default="/model-cache/cotcodec-models")

    run = commands.add_parser("run", allow_abbrev=False)
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--job", required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--model-root", type=Path, default=Path("/model-cache/cotcodec-models"))
    run.add_argument("--receipt-root", type=Path, default=Path("/model-cache/cotcodec-receipts"))
    run.add_argument("--allocation-minutes", type=int, required=True)
    run.add_argument("--image-variant", default="cu129")
    run.add_argument("--weights-pin", action="append", default=[])
    run.add_argument("--seeds", type=int, nargs="+", required=True)

    args_doctor = commands.add_parser("vllm-args-doctor", allow_abbrev=False)
    args_doctor.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    proj = commands.add_parser("project", allow_abbrev=False)
    proj.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    proj.add_argument("--job-a", type=Path, required=True)
    proj.add_argument("--output", type=Path, required=True)

    commands.add_parser("digest", allow_abbrev=False).add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(v1.resolve_config_path(args.config))
    if args.command == "vllm-args-doctor":
        report = vllm_args_doctor(config)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else EXIT_PRE_RESULT
    if args.command == "plan":
        payload = plan_payload(config, config.job(args.job), args.model_root)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "digest":
        print(
            json.dumps(
                {"contract_sha256": config.sha256, **probe_code_digest()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "project":
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite {args.output}")
        try:
            payload = project(config, job_a=args.job_a)
        except ProjectionError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return EXIT_PRE_RESULT
        atomic_write_json(args.output, payload)
        modes = {phase: entry.get("mode") for phase, entry in payload["x1"]["attribution"].items()}
        print(
            json.dumps(
                {
                    "q2": payload["q2"].get("decision"),
                    "x1": payload["x1"]["outcome"],
                    "attribution": modes,
                },
                sort_keys=True,
            )
        )
        return 0
    try:
        job = config.job(args.job)
        seeds = bind_seeds(config, args.seeds)
        if args.allocation_minutes != job.allocation_minutes:
            raise ProbeConfigError(
                f"--allocation-minutes {args.allocation_minutes} differs from the contract's "
                f"{job.allocation_minutes}"
            )
        pins = parse_weight_pins(args.weights_pin)
        check_pins(job, pins)
    except ProbeConfigError as exc:
        print(f"pre-result: {exc}", file=sys.stderr)
        return EXIT_PRE_RESULT
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    outputs_root = Path(os.environ.get("COTCODEC_OUTPUT_DIR", str(args.output_dir.parent)))
    runner = ProbeRunnerV2(
        config=config,
        job=job,
        output_dir=args.output_dir,
        outputs_root=outputs_root,
        model_root=args.model_root,
        receipt_root=args.receipt_root,
        pins=pins,
        image_variant=args.image_variant,
        seeds=seeds,
        argv=list(argv) if argv is not None else list(sys.argv),
        marker_path=Path(marker) if marker else None,
    )
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
