"""The S1a episode runner (registration section 3.1 item 3, sections 7.1-7.3).

One process per episode, inside the GPU-less episode container that the lane
(``lane.py``) starts in a freshly booted VM container's network namespace. It runs the
episode of section 7.1 and writes its record:

1. wait for the cold boot (the guest server's ``/screenshot`` answers with an image);
2. task setup offline from the pinned file cache (``osworld_live.LiveTask.setup``);
3. the guard's keyboard warm-up, once per boot (``harness/q2/vm/guest/guard.py warmup``,
   action-path v2 design decision 31), which also names the guest server's process;
4. OSWorld's 60 s settle;
5. up to 15 model turns. Each turn's IR runs on the certified L0-fixed executor through
   ``DesktopEnv.step`` (``harness/q2/vm/desktop.py``, ``pause = 0.0``), one action per step,
   each step observing the screen as upstream does; the last screenshot is the next turn's
   observation. A turn with no action leaves H-OSW-fixed's observation unchanged (upstream
   OSWorld calls ``predict`` again on the same ``obs``) and gives H-GA a fresh capture
   (gym-anything's ``env.step([])``). ``terminate`` ends the episode;
6. the 20 s settle and the guest-server restart check (``NRestarts`` and the server's pid);
7. ``DesktopEnv.evaluate()`` with the last action in its history (``FAIL`` after
   ``terminate(failure)``, OSWorld's own convention, for both harnesses);
8. the capture sweep, the final-state capture and the restart check once more.

Classification follows section 7.2 (``records.INFRASTRUCTURE_TYPES``): a failed boot or setup
(a setup step that raises, or whose guest reply is not HTTP 200 or carries a non-zero
``returncode``, ``osworld_live.setup_reply_failed``: the pinned code goes on after either),
an engine request that fails after the client's retries, H-GA's context fallback for any
reason but a context-length rejection, a step whose ``/execute`` or screenshot fails
(``desktop.infra_failures``) or whose executor exits non-zero, a failed warm-up, a guest-
server restart (at the check after the 20 s settle or at the one after the capture) and a
checker getter or postconfig step that loses its transport (``osworld_live``: any guest
request of the evaluation or the sweep that failed in transport, even one the pinned code
swallowed) are infrastructure losses, and so is a checker that asks for a URL the offline
run cannot serve (``offline_network``). An observation the guest server did not deliver is a
``guest_observation`` loss (D53 (iii)): a screenshot of the agent's whose attempts all got an
HTTP reply that was no image (a 5xx), or a checker read (``osworld_live``: a guest read of
``evaluate()`` or the capture sweep that got HTTP 5xx on every attempt, which the pinned code
would hand the metric as ``None`` and score 0); one whose attempts failed in transport stays
a ``transport`` loss. Every observation is counted per episode (``observations``: calls,
delivered on retry, slow, undelivered), reported. A failed postconfig reply during
``evaluate()`` is recorded (``postconfig_failures``), not a loss: postconfig steps act on the
agent's final state. The episode container must see no GPU device (D12): a visible
``/dev/nvidia*`` ends the episode before the boot wait, and the lane stops dispatching. A
restart check that cannot reach the guest server, or that the server answers with an HTTP
error, is a transport loss: the episode cannot be shown restart-free. A reply that yields no
valid IR (``IRError`` or a parser exception) is handled under the harness's rule and counted
(``ir_errors``); a checker metric that raises scores 0 (``metric_exception``). The record
follows ``records.SCHEMA``; the step log, raw replies and capture stay under the episode's
output directory on the host.
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import hashlib
import json
import re
import time
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from harness.q2_stage1 import agents
from harness.q2_stage1.records import SCHEMA, validate

STEP_CAP = 15
SETTLE_AFTER_RESET_S = 60.0
SETTLE_BEFORE_EVAL_S = 20.0
BOOT_TIMEOUT_S = 300.0
GPU_DEVICE_GLOB = "/dev/nvidia*"  # D12: none may be visible in the episode container
DIAGNOSTIC_TIMEOUT_S = 130.0
# Run through /execute, so the guest server is the script's parent process.
SERVER_PID_SCRIPT = "import json, os\nprint(json.dumps({'server_pid': os.getppid()}))\n"


class Session(Protocol):
    """What the runner needs from the OSWorld side (``osworld_live.LiveTask`` or a fake)."""

    def setup(self) -> dict[str, Any]: ...
    def evaluate(self, last_action: str | None) -> Any: ...
    def capture_sweep(self) -> list[dict[str, Any]]: ...
    def write_capture(self, capture_dir: Path) -> dict[str, Any]: ...
    def close(self) -> None: ...


@dataclass
class EpisodeConfig:
    job: str
    size: str
    session: str
    task_id: str
    harness: str
    rerun: int
    attempt: int
    extension_block: int | None
    block: str
    slot: str
    out_dir: str
    guest_ip: str = "20.20.20.21"
    server_port: int = 5000
    osworld_dir: str = "/inputs/OSWorld"
    file_cache_dir: str = "/inputs/file_cache/files"
    engine_socket: str = "/engine/engine.sock"
    served_model: str = "s1a-model"
    sampling: dict[str, Any] = field(
        default_factory=lambda: {"temperature": 0.0, "top_p": 0.9, "top_k": -1, "max_tokens": 2048}
    )
    step_cap: int = STEP_CAP
    settle_after_reset_s: float = SETTLE_AFTER_RESET_S
    settle_before_eval_s: float = SETTLE_BEFORE_EVAL_S
    boot_timeout_s: float = BOOT_TIMEOUT_S
    certified_keysyms: list[str] = field(default_factory=list)
    mode: str = "episode"  # or "setup-only" (G0 item 5)
    # G0 item 5's second pass (setup-only mode only): run the postconfig on the untouched
    # initial state, and the registered diagnostics (plan.SETUP_DIAGNOSTICS) after setup.
    postconfig_probe: bool = False
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    t_vm_start: float | None = None
    date: str | None = None  # YYYY-MM-DD for tests and replays; None keeps today's date

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> EpisodeConfig:
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        unknown = sorted(set(data) - set(known))
        if unknown:
            raise ValueError(f"unknown episode config keys: {unknown}")
        return cls(**known)


def strip_stdout(replies: Any) -> list[dict[str, Any]]:
    """Guest setup replies as the episode record keeps them: status, returncode and stderr
    tail, without the stdout tail, which can print task fixtures' stored credentials (a
    postconfig decrypts a Thunderbird test profile); the capture on the host keeps it
    (section 16)."""
    return [{k: v for k, v in dict(r).items() if k != "output_tail"} for r in replies or []]


def for_record(block: Any) -> Any:
    if isinstance(block, dict) and "replies" in block:
        return {**block, "replies": strip_stdout(block["replies"])}
    return block


def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


SLOW_EXECUTE_S = 30.0
SLOW_OBSERVATION_S = 30.0  # an observation that took longer is counted as slow (reported)


def observation_loss_kind(attempts: Any) -> str:
    """The loss of an undelivered screenshot: ``transport`` when an attempt failed in
    transport (no HTTP reply), else ``guest_observation`` (the guest server answered every
    attempt with no image, a 5xx; D53 (iii))."""
    rows = list(attempts or [])
    if not rows or any("error" in (row or {}) for row in rows):
        return "transport"
    return "guest_observation"


def step_losses(record: Mapping[str, Any]) -> list[str]:
    """Transport losses of one ``DesktopEnv.step``: ``/execute`` never answered 200, or its
    first attempt failed (a retry may have run the action twice), or no screenshot came.

    Unlike the action-path suite's rule (``desktop.infra_failures``), a first attempt that
    answered 200 after more than 30 s is not a loss here: a long ``type`` is agent behaviour.
    It is recorded as ``slow_execute``.
    """
    out = []
    execute = record.get("execute")
    if execute is not None:
        first = (execute.get("attempts") or [{}])[0]
        if not execute.get("ok") or first.get("status") != 200:
            out.append("execute")
    if not record.get("screenshot_ok"):
        out.append("screenshot")
    return out


def slow_execute(record: Mapping[str, Any]) -> bool:
    first = ((record.get("execute") or {}).get("attempts") or [{}])[0]
    return float(first.get("elapsed_s") or 0.0) > SLOW_EXECUTE_S


def uncertified(ir: list[dict[str, Any]], certified: set[str]) -> int:
    from harness.q2_stage1.records import uncertified_key_actions

    return uncertified_key_actions(ir, certified) if certified else 0


class Runner:
    """One episode against a guest server, an engine and an OSWorld session."""

    def __init__(
        self,
        cfg: EpisodeConfig,
        *,
        guest: Any,
        session_factory: Callable[[EpisodeConfig, dict[str, Any]], Session],
        client_factory: Callable[..., agents.HarnessClient],
        task: Mapping[str, Any],
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ):
        self.cfg = cfg
        self.guest = guest
        self.session_factory = session_factory
        self.client_factory = client_factory
        self.task = dict(task)
        self.sleep = sleep
        self.clock = clock
        self.out = Path(cfg.out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.timings: dict[str, float] = {}
        self.agent_observations: dict[str, Any] = {
            "calls": 0, "retried": 0, "slow": 0, "undelivered": 0, "max_s": None,
        }  # fmt: skip
        self.session: Session | None = None
        self.record: dict[str, Any] = {
            "schema": SCHEMA,
            "job": cfg.job,
            "size": cfg.size,
            "session": cfg.session,
            "task_id": cfg.task_id,
            "harness": cfg.harness,
            "rerun": cfg.rerun,
            "extension_block": cfg.extension_block,
            "attempt": cfg.attempt,
            "block": cfg.block,
            "slot": cfg.slot,
            "status": "infrastructure",
            "infrastructure_type": "runner_crash",
            "score": None,
            "metric_exception": False,
            "steps": 0,
            "truncated_steps": 0,
            "truncated_no_tool_call_steps": 0,
            "ir_errors": 0,
            "uncertified_key_actions": 0,
            "context_fallbacks": 0,
            "ended": None,
        }

    # ---------------------------------------------------------------- guest helpers
    def server_identity(self, pid: int | None = None) -> dict[str, Any]:
        from harness.q2.vm.suite import unit_of_cgroup

        out: dict[str, Any] = {"server_pid": pid}
        try:
            if pid is None:
                out["server_pid"] = self.guest.run_script(SERVER_PID_SCRIPT).get("server_pid")
            if isinstance(out["server_pid"], int):
                cgroup = self.guest.execute(["cat", f"/proc/{out['server_pid']}/cgroup"], 30.0)
                if cgroup.get("http_status") != 200:
                    raise RuntimeError(f"/execute answered HTTP {cgroup.get('http_status')}")
                unit = unit_of_cgroup(str(cgroup.get("output", "")))
                out["unit"] = unit
                if unit:
                    result = self.guest.execute(
                        ["systemctl", "show", "--property=NRestarts", "--value", unit], 30.0
                    )
                    if result.get("http_status") != 200:
                        raise RuntimeError(f"/execute answered HTTP {result.get('http_status')}")
                    value = str(result.get("output", "")).strip()
                    out["n_restarts"] = int(value) if value.isdigit() else None
        except Exception as exc:  # noqa: BLE001 - recorded; the restart rule reads what exists
            out["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        return out

    def wait_for_boot(self) -> bytes:
        from harness.q2.vm import desktop

        started = self.clock()
        while True:
            shot, _ = desktop.get_screenshot(self.guest)
            if shot is not None:
                self.timings["boot_wait_s"] = round(self.clock() - started, 3)
                if self.cfg.t_vm_start is not None:
                    self.timings["boot_s"] = round(self.clock() - self.cfg.t_vm_start, 3)
                return shot
            if self.clock() - started > self.cfg.boot_timeout_s:
                limit = self.cfg.boot_timeout_s
                raise agents.InfraLoss("vm_boot", f"no screenshot within {limit} s")
            self.sleep(2.0)

    # ---------------------------------------------------------------- the episode
    def run(self) -> dict[str, Any]:
        t0 = self.clock()
        self.record["t_start"] = t0
        session: Session | None = None
        steps_log = (self.out / "steps.jsonl").open("w", encoding="utf-8")
        replies_log = (self.out / "replies.jsonl").open("w", encoding="utf-8")
        try:
            self.check_no_gpu()
            self.wait_for_boot()
            t = self.clock()
            try:
                session = self.session_factory(self.cfg, self.task)
                self.session = session
                self.record["setup"] = for_record(session.setup())
            except agents.InfraLoss:
                raise
            except Exception as exc:  # noqa: BLE001 - any setup failure is a setup loss
                raise agents.InfraLoss("task_setup", f"{type(exc).__name__}: {exc}") from exc
            self.timings["setup_s"] = round(self.clock() - t, 3)
            setup = self.record["setup"] if isinstance(self.record["setup"], dict) else {}
            failures = list(setup.get("failures") or [])
            if self.cfg.mode == "setup-only":
                self.record["server_start"] = self.server_identity()
                self.setup_check_extras(session)
                if failures:
                    raise agents.InfraLoss("task_setup", f"failed in the guest: {failures[0]}")
                self.record.update(status="setup_ok", infrastructure_type=None, ended="setup-only")
                return self.finish(t0)
            if failures:
                # The pinned code goes on after a step that failed in the guest (a reply that
                # is not 200, or a non-zero returncode); the task is then not set up (7.2).
                raise agents.InfraLoss("task_setup", f"failed in the guest: {failures[0]}")
            self.warm_up()
            t = self.clock()
            self.sleep(self.cfg.settle_after_reset_s)
            self.timings["settle_after_reset_s"] = round(self.clock() - t, 3)
            last_action = self.loop(steps_log, replies_log)
            t = self.clock()
            self.sleep(self.cfg.settle_before_eval_s)
            self.timings["settle_before_eval_s"] = round(self.clock() - t, 3)
            self.check_restarts()
            self.evaluate(session, last_action)
        except agents.InfraLoss as loss:
            kind = self.restart_behind(loss)
            self.record.update(
                status="infrastructure", infrastructure_type=kind, score=None,
                infrastructure_detail=loss.detail[:500], ended=self.record["ended"] or "infra",
            )  # fmt: skip
            if self.cfg.mode == "setup-only":
                self.record["status"] = "setup_failed"
        except Exception as exc:  # noqa: BLE001 - a runner crash is an infrastructure loss
            self.record.update(
                status="infrastructure", infrastructure_type="runner_crash", score=None,
                infrastructure_detail=f"{type(exc).__name__}: {exc}"[:500],
                traceback_tail=traceback.format_exc()[-1500:], ended="infra",
            )  # fmt: skip
            if self.cfg.mode == "setup-only":
                self.record["status"] = "setup_failed"
        finally:
            steps_log.close()
            replies_log.close()
            if session is not None:
                # The shim's restore cannot change the record.
                with contextlib.suppress(Exception):
                    session.close()
        return self.finish(t0)

    def finish(self, t0: float) -> dict[str, Any]:
        if self.cfg.mode == "episode":
            self.record["observations"] = self.observation_counts()
        self.record["t_end"] = self.clock()
        self.timings["runner_s"] = round(self.record["t_end"] - t0, 3)
        self.record["timings"] = self.timings
        if self.cfg.mode == "episode":
            validate(self.record)
        (self.out / "episode.json").write_text(
            json.dumps(self.record, indent=1, sort_keys=True), encoding="utf-8"
        )
        return self.record

    def observe(self, attempts: Any, seconds: float, delivered: bool) -> None:
        """Count one of the agent's screenshots (section 7.3, D53 (iii)): delivered on a
        retry (its first attempt was not an image), slow (over ``SLOW_OBSERVATION_S``) or
        undelivered."""
        stats, rows = self.agent_observations, list(attempts or [])
        stats["calls"] += 1
        first = rows[0] if rows else {}
        stats["retried"] += int(delivered and (first.get("status") != 200 or len(rows) > 1))
        stats["slow"] += int(seconds > SLOW_OBSERVATION_S)
        stats["undelivered"] += int(not delivered)
        stats["max_s"] = round(max(seconds, stats["max_s"] or 0.0), 3)

    def observation_counts(self) -> dict[str, Any]:
        """The episode's observations: the agent's screenshots and, when the session
        records them, the checker's reads (``osworld_live.LiveTask.observation_summary``)."""
        out: dict[str, Any] = {"agent": dict(self.agent_observations), "slow_s": SLOW_OBSERVATION_S}
        summary = getattr(self.session, "observation_summary", None)
        if callable(summary):
            with contextlib.suppress(Exception):  # counts only; never changes the record
                out["checker"] = summary()
        return out

    def check_no_gpu(self) -> None:
        """D12: the episode container is GPU-less; a visible device ends the episode."""
        devices = sorted(glob.glob(GPU_DEVICE_GLOB))
        self.record["gpu_devices"] = devices
        if devices:
            raise agents.InfraLoss("runner_crash", f"D12: GPU device files visible: {devices}")

    def setup_check_extras(self, session: Session) -> None:
        """G0 item 5's second pass: the registered diagnostics after setup (each argv's
        output and whether it shows the step's product, ``expect``), then the postconfig on
        the untouched initial state (``probe_postconfig``: no getter, no metric)."""
        rows = []
        for item in self.cfg.diagnostics:
            argv, expect = list(item["argv"]), item.get("expect")
            row: dict[str, Any] = {"argv": argv, "expect": expect}
            try:
                result = self.guest.execute(argv, DIAGNOSTIC_TIMEOUT_S)
                output = str(result.get("output", ""))
                row.update(
                    http_status=result.get("http_status"), returncode=result.get("returncode"),
                    output_tail=output[-2000:], error_tail=str(result.get("error", ""))[-300:],
                    found=bool(expect) and re.search(expect, output) is not None,
                )  # fmt: skip
            except Exception as exc:  # noqa: BLE001 - recorded; the rule reads found=False
                row.update(error=f"{type(exc).__name__}: {str(exc)[:200]}", found=False)
            rows.append(row)
        if rows:
            self.record["diagnostics"] = rows
        if self.cfg.postconfig_probe:
            from harness.q2_stage1.osworld_live import is_transport_error

            probe = getattr(session, "probe_postconfig", None)
            if probe is None:
                raise RuntimeError("this session cannot probe the postconfig")
            try:
                self.record["postconfig_probe"] = for_record(probe())
            except Exception as exc:  # noqa: BLE001 - a lost transport is a transport loss
                if is_transport_error(exc):
                    raise agents.InfraLoss("transport", f"postconfig probe: {exc}") from exc
                raise

    def warm_up(self) -> None:
        from harness.q2.vm.suite import guest_source

        t = self.clock()
        try:
            result = self.guest.run_script(
                guest_source("guard.py"), ["warmup", json.dumps({"sock": None, "reserved": None})]
            )
        except Exception as exc:  # noqa: BLE001 - the guard failing is an executor-level loss
            raise agents.InfraLoss("executor_device", f"guard warm-up failed: {exc}") from exc
        if not isinstance(result.get("keycode"), int):
            raise agents.InfraLoss("executor_device", f"guard warm-up: {str(result)[:300]}")
        self.timings["warmup_s"] = round(self.clock() - t, 3)
        self.record["warmup"] = {
            "keycode": result["keycode"],
            "shell_idle": (result.get("shell") or {}).get("idle"),
        }
        start = self.server_identity(result.get("server_pid"))
        self.record["server_start"] = start
        if "error" in start:
            # Without the starting identity no later restart could be seen (section 7.2).
            raise agents.InfraLoss("transport", f"identity at warm-up: {start['error']}")

    @staticmethod
    def restarted(start: Mapping[str, Any], end: Mapping[str, Any]) -> tuple[bool, int]:
        """Whether a different server process answers, or its unit's NRestarts moved; and
        how many restarts that shows (D30, D33)."""
        changed_pid = (
            isinstance(start.get("server_pid"), int)
            and isinstance(end.get("server_pid"), int)
            and start["server_pid"] != end["server_pid"]
        )
        n0, n1 = start.get("n_restarts"), end.get("n_restarts")
        counted = isinstance(n0, int) and isinstance(n1, int) and n1 != n0
        count = max(int(changed_pid), (n1 - n0) if counted else 0)
        return changed_pid or counted, count

    def restart_behind(self, loss: agents.InfraLoss) -> str:
        """A transport or guest-observation loss behind which the guest server restarted is
        a restart (D30)."""
        if loss.kind not in ("transport", "guest_observation") or not self.record.get(
            "server_start"
        ):
            return loss.kind
        start, end = self.record["server_start"], self.server_identity()
        self.record["server_after_loss"] = end
        changed, _ = self.restarted(start, end)
        return "guest_server_restart" if changed else loss.kind

    def check_restarts(self, key: str = "server_end") -> None:
        """Compare the guest server with the warm-up's (after the 20 s settle, ``server_end``,
        and after the capture, ``server_final``). A check that cannot reach the server is a
        transport loss; a different process or a moved NRestarts is a restart."""
        start = self.record.get("server_start") or {}
        end = self.server_identity()
        self.record[key] = end
        if "error" in end:
            raise agents.InfraLoss("transport", f"identity at {key}: {end['error']}")
        changed, count = self.restarted(start, end)
        self.record["guest_server_restarts"] = max(
            count, int(self.record.get("guest_server_restarts") or 0)
        )
        if changed:
            raise agents.InfraLoss("guest_server_restart", f"{key}: server {start} -> {end}")

    def loop(self, steps_log: Any, replies_log: Any) -> str | None:
        from harness.q2.action_path.executor import step_command
        from harness.q2.vm import desktop
        from harness.q2_stage1.engine import EngineClient

        engine = EngineClient(self.cfg.engine_socket, self.cfg.served_model)
        today = datetime.strptime(self.cfg.date, "%Y-%m-%d") if self.cfg.date else datetime.today()
        client = self.client_factory(
            self.cfg.harness, self.task["instruction"], engine, self.cfg.sampling, today
        )
        self.record["date_line"] = client.date_line
        certified = set(self.cfg.certified_keysyms)
        t = self.clock()
        shot, attempts = desktop.get_screenshot(self.guest)
        self.observe(attempts, self.clock() - t, shot is not None)
        if shot is None:
            kind = observation_loss_kind(attempts)
            raise agents.InfraLoss(kind, f"first observation failed: {attempts}")
        last_action: str | None = None
        self.record["ended"] = "step_cap"
        t_loop = self.clock()
        tokens = {"prompt": 0, "completion": 0}
        for step in range(1, self.cfg.step_cap + 1):
            observed = client.observe(shot)
            turn = client.act()  # InfraLoss propagates
            self.record["steps"] = step
            completion = turn.completion or {}
            tokens["prompt"] += completion.get("prompt_tokens") or 0
            tokens["completion"] += completion.get("completion_tokens") or 0
            self.record["truncated_steps"] += int(turn.truncated)
            # Section 6.2's and 15's truncation: the cap hit without a complete tool call.
            self.record["truncated_no_tool_call_steps"] += int(
                turn.truncated and not turn.complete_tool_call
            )
            self.record["ir_errors"] += int(turn.parse_error is not None)
            self.record["context_fallbacks"] += turn.context_fallbacks
            exposure = uncertified(turn.ir, certified)
            self.record["uncertified_key_actions"] += exposure
            replies_log.write(json.dumps({"step": step, "response": turn.response}) + "\n")
            executed: list[dict[str, Any]] = []
            terminated = None
            for action in turn.ir:
                if action["op"] == "terminate":
                    terminated = action["status"]
                    break
                command = step_command(action)
                rec, new_shot = desktop.step(self.guest, command, pause=0.0)
                self.observe(
                    rec.get("screenshot_attempts"),
                    float((rec.get("timing_s") or {}).get("screenshot") or 0.0),
                    new_shot is not None,
                )
                result = ((rec.get("execute") or {}).get("result")) or {}
                executed.append(
                    {
                        "op": action["op"],
                        "timing_s": rec.get("timing_s"),
                        "returncode": result.get("returncode"),
                        "retried": rec.get("retried"),
                        "slow_execute": slow_execute(rec),
                    }
                )
                infra = step_losses(rec)
                if infra:
                    kind = (
                        "transport"
                        if "execute" in infra
                        else observation_loss_kind(rec.get("screenshot_attempts"))
                    )
                    raise agents.InfraLoss(kind, f"step {step} {action['op']}: {infra}")
                if result.get("returncode") not in (0, None):
                    raise agents.InfraLoss(
                        "executor_device",
                        f"step {step} {action['op']} rc={result.get('returncode')}: "
                        f"{str(result.get('error'))[-300:]}",
                    )
                last_action = command
                shot = new_shot
            if terminated is not None:
                last_action = "FAIL" if terminated == "failure" else "DONE"
                self.record["ended"] = f"terminate_{terminated}"
            elif not executed and self.cfg.harness == "H-GA":
                t = self.clock()
                fresh, attempts = desktop.get_screenshot(self.guest)
                self.observe(attempts, self.clock() - t, fresh is not None)
                if fresh is None:
                    kind = observation_loss_kind(attempts)
                    raise agents.InfraLoss(kind, f"step {step} capture failed: {attempts}")
                shot = fresh
            steps_log.write(
                json.dumps(
                    {
                        "step": step,
                        "completion": completion,
                        "truncated": turn.truncated,
                        "complete_tool_call": turn.complete_tool_call,
                        "ir": turn.ir,
                        "ir_sha256": sha256_json(turn.ir),
                        "prompt_sha256": completion.get("prompt_ids_sha256"),
                        "messages_sha256": turn.messages_sha256,
                        "parse_error": turn.parse_error,
                        "low_level": turn.low_level[:300],
                        "context_variant": list(turn.context_variant),
                        "context_fallbacks": turn.context_fallbacks,
                        "uncertified_key_actions": exposure,
                        "executed": executed,
                        "terminated": terminated,
                        "screenshot_sha256": observed.raw_sha256,
                        "processed_sha256": observed.processed_sha256,
                        "queue_wait_s": None,  # vLLM v0.31.0 reports none per request
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            steps_log.flush()
            if terminated is not None:
                break
        self.timings["steps_s"] = round(self.clock() - t_loop, 3)
        self.record["tokens"] = tokens
        self.record["last_action_kind"] = (
            last_action if last_action in ("FAIL", "DONE", None) else "command"
        )
        return last_action

    def evaluate(self, session: Session, last_action: str | None) -> None:
        from harness.q2_stage1.osworld_live import (
            is_observation_failure,
            is_offline_refusal,
            is_transport_error,
            setup_reply_failed,
        )

        t = self.clock()
        try:
            score = session.evaluate(last_action)
        except Exception as exc:  # noqa: BLE001 - classified below
            self.record_postconfig(session, setup_reply_failed)
            if is_transport_error(exc):
                raise agents.InfraLoss("transport", f"evaluate: {exc}") from exc
            if is_observation_failure(exc):
                raise agents.InfraLoss("guest_observation", f"evaluate: {exc}") from exc
            if is_offline_refusal(exc):
                raise agents.InfraLoss("offline_network", f"evaluate: {exc}") from exc
            error = f"{type(exc).__name__}: {exc}"[:500]
            self.record.update(metric_exception=True, metric_error=error)
            score = 0.0
        else:
            self.record_postconfig(session, setup_reply_failed)
        if score is None:
            self.record.update(metric_exception=True, metric_error="evaluate() returned None")
            score = 0.0
        score = float(score)
        if not 0.0 <= score <= 1.0:
            self.record.update(metric_exception=True, metric_error=f"score {score} outside [0, 1]")
            score = 0.0
        self.timings["evaluate_s"] = round(self.clock() - t, 3)
        t = self.clock()
        try:
            self.record["capture_sweep"] = session.capture_sweep()
        except Exception as exc:  # noqa: BLE001 - a lost transport voids the episode
            if is_transport_error(exc):
                raise agents.InfraLoss("transport", f"capture: {exc}") from exc
            if is_observation_failure(exc):
                raise agents.InfraLoss("guest_observation", f"capture: {exc}") from exc
            self.record["capture_sweep_error"] = f"{type(exc).__name__}: {exc}"[:300]
        manifest = session.write_capture(self.out / "capture")
        self.timings["capture_s"] = round(self.clock() - t, 3)
        # The pinned checker swallows many guest errors, and a restart during evaluation or
        # the capture would go unseen by the check before it (section 7.2, D30).
        self.check_restarts("server_final")
        self.record.update(
            status="scored",
            infrastructure_type=None,
            score=0.0 if self.record["metric_exception"] else score,
            checker_input_sha256=manifest.get("vm_files", {}),
            state_sha256=manifest.get("state_sha256"),
        )

    def record_postconfig(self, session: Session, failed: Callable[[Any], bool]) -> None:
        """The postconfig's guest replies during ``evaluate()``: recorded and counted, not a
        loss (section 7.2)."""
        replies = getattr(session, "evaluate_replies", None)
        if replies is None:
            return
        self.record["postconfig_replies"] = strip_stdout(replies)
        self.record["postconfig_failures"] = sum(1 for r in replies if failed(r))


def run_from_config(config_path: Path) -> dict[str, Any]:
    """The episode container's entry point: a live guest, the bridge socket, live OSWorld."""
    from harness.q2.vm.guest_http import GuestClient
    from harness.q2_stage1.osworld_live import LiveTask, load_task

    data = json.loads(config_path.read_text(encoding="utf-8"))
    cfg = EpisodeConfig.from_json(data)
    task = load_task(cfg.osworld_dir, cfg.task_id)

    def session_factory(c: EpisodeConfig, t: dict[str, Any]) -> LiveTask:
        return LiveTask(
            t,
            osworld_dir=c.osworld_dir,
            file_cache=Path(c.file_cache_dir),
            guest_ip=c.guest_ip,
            server_port=c.server_port,
            cache_root=Path("/tmp/osworld-cache"),
        )

    runner = Runner(
        cfg,
        guest=GuestClient(cfg.guest_ip, cfg.server_port),
        session_factory=session_factory,
        client_factory=agents.make_client,
        task=task,
    )
    return runner.run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    record = run_from_config(args.config)
    keys = ("slot", "status", "infrastructure_type", "score")
    print(json.dumps({k: record.get(k) for k in keys}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
