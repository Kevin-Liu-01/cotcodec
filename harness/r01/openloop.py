"""Stage A1 captures and Stage C open-loop replay (draft registration v2, sections 5.3 and 6).

Both run in the S1a lane's episode container, on S1a's runner (``driver.Runner``, unmodified,
subclassed here), so boot wait, offline setup, the guard's warm-up, the 60 s settle, the
certified L0-fixed executor through ``DesktopEnv.step`` (``pause = 0``), the restart checks, the
live checker and the capture are S1a's own code paths. What changes is where actions come from:

* ``stage-c``: the actions are S1a's recorded IR for the episode (its ``steps.jsonl``), never a
  model. Per recorded step k: frame f0 (the observation S1a's agent saw at step k: the first
  screenshot after the settle, then the screenshot ``DesktopEnv.step`` returns after the
  previous action), frame f1 ``f1_delay_s`` later, a sleep for the rest of the step's recorded
  ``latency_s`` (so actions are spaced as in S1a), then the step's IR. A step whose IR is empty
  (the harness's no-action rule) captures nothing new, as H-OSW-fixed observes the same frame
  again. ``terminate`` ends the replay; the 20 s settle, the restart check, ``evaluate()`` and the
  capture follow as in S1a.
* ``a1``: no checker. After the settle, frames at ``frame_offsets_s`` from t0 and, on the
  positive-control boots, at ``late_frame_s``; then, on boots that build step-2 requests,
  ``open_loop_steps`` recorded steps from the t0 frame (sleeping the recorded latency from the t0
  capture), with the step-2 frame f0 and its f1.
* ``blink_off``: before the settle, ``gsettings set org.gnome.desktop.interface cursor-blink
  false`` through the guest server, read back with ``gsettings get``; a boot where the read-back
  is not ``false`` is a setup loss. The setting is a measurement condition outside the agent
  runtime D53 certifies (an owner decision, section 18).

Every frame is written as a PNG under ``frames/`` (host run root only); the record keeps each
frame's raw and processed SHA-256 (``agents.process_image``), its label and its capture time.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import time
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness.q2_stage1 import agents, driver

SCHEMA = "r01-openloop-v1"
BLINK_SET = ["gsettings", "set", "org.gnome.desktop.interface", "cursor-blink", "false"]
BLINK_GET = ["gsettings", "get", "org.gnome.desktop.interface", "cursor-blink"]


@dataclass
class OpenLoopConfig(driver.EpisodeConfig):
    r01_mode: str = "stage-c"  # or "a1"
    recorded_steps: str = ""  # S1a's steps.jsonl of the episode whose IR is replayed
    replay_of: str = ""  # S1a slot of that episode (provenance)
    frame_offsets_s: list[float] = field(default_factory=lambda: [0.0, 0.6, 1.2])
    late_frame_s: float | None = None
    open_loop_steps: int = 0
    f1_delay_s: float = 0.6
    blink_off: bool = False

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> OpenLoopConfig:
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        unknown = sorted(set(data) - set(known))
        if unknown:
            raise ValueError(f"unknown open-loop config keys: {unknown}")
        return cls(**known)


def load_recorded(path: str | Path) -> list[dict[str, Any]]:
    """S1a's step log lines reduced to what the replay needs."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out.append(
            {
                "step": int(row["step"]),
                "ir": list(row.get("ir") or []),
                "ir_sha256": row.get("ir_sha256"),
                "latency_s": float((row.get("completion") or {}).get("latency_s") or 0.0),
                "terminated": row.get("terminated"),
            }
        )
    return sorted(out, key=lambda r: r["step"])


class OpenLoopRunner(driver.Runner):
    def __init__(
        self,
        cfg: OpenLoopConfig,
        *,
        guest: Any,
        session_factory: Any,
        task: Mapping[str, Any],
        recorded: Sequence[Mapping[str, Any]] | None = None,
        sleep: Any = time.sleep,
        clock: Any = time.time,
    ):
        super().__init__(
            cfg,
            guest=guest,
            session_factory=session_factory,
            client_factory=agents.make_client,
            task=task,
            sleep=sleep,
            clock=clock,
        )
        self.cfg: OpenLoopConfig = cfg
        if recorded is None and cfg.recorded_steps:
            recorded = load_recorded(cfg.recorded_steps)
        self.recorded = [dict(r) for r in (recorded or [])]
        self.frames: list[dict[str, Any]] = []
        self.frames_dir = self.out / "frames"
        self.record.update(
            schema=SCHEMA, r01_mode=cfg.r01_mode, replay_of=cfg.replay_of, blink_off=cfg.blink_off
        )

    # ---------------------------------------------------------------- frames
    def keep(self, label: str, png: bytes) -> None:
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        (self.frames_dir / f"{label}.png").write_bytes(png)
        shot = agents.process_image(png)
        self.frames.append(
            {
                "label": label,
                "raw_sha256": shot.raw_sha256,
                "processed_sha256": shot.processed_sha256,
                "t": self.clock(),
            }
        )

    def capture(self, label: str) -> bytes:
        from harness.q2.vm import desktop

        t = self.clock()
        shot, attempts = desktop.get_screenshot(self.guest)
        self.observe(attempts, self.clock() - t, shot is not None)
        if shot is None:
            raise agents.InfraLoss(
                driver.observation_loss_kind(attempts), f"frame {label}: {attempts}"
            )
        self.keep(label, shot)
        return shot

    def wait_until(self, t_target: float) -> None:
        remaining = t_target - self.clock()
        if remaining > 0:
            self.sleep(remaining)

    # ---------------------------------------------------------------- guest condition
    def warm_up(self) -> None:
        if self.cfg.blink_off:
            self.set_blink_off()
        super().warm_up()

    def set_blink_off(self) -> None:
        try:
            first = self.guest.execute(BLINK_SET, 30.0)
            check = self.guest.execute(BLINK_GET, 30.0)
        except Exception as exc:  # noqa: BLE001 - the condition could not be set
            raise agents.InfraLoss("task_setup", f"blink-off: {exc}") from exc
        value = str(check.get("output", "")).strip()
        self.record["blink_off_check"] = {"set_status": first.get("http_status"), "get": value}
        if value != "false":
            raise agents.InfraLoss("task_setup", f"blink-off read back {value!r}")

    # ---------------------------------------------------------------- recorded actions
    def execute_step(
        self, rec: Mapping[str, Any], step: int
    ) -> tuple[bytes | None, str | None, list[dict[str, Any]]]:
        """Run one recorded step's IR as S1a's runner did; returns the screenshot after the last
        action (None if nothing ran), the terminate status, and per-action rows."""
        from harness.q2.action_path.executor import step_command
        from harness.q2.vm import desktop

        new_shot = None
        executed: list[dict[str, Any]] = []
        for action in rec["ir"]:
            if action["op"] == "terminate":
                return new_shot, action["status"], executed
            command = step_command(action)
            row, new_shot = desktop.step(self.guest, command, pause=0.0)
            self.observe(
                row.get("screenshot_attempts"),
                float((row.get("timing_s") or {}).get("screenshot") or 0.0),
                new_shot is not None,
            )
            result = ((row.get("execute") or {}).get("result")) or {}
            executed.append(
                {
                    "op": action["op"],
                    "timing_s": row.get("timing_s"),
                    "returncode": result.get("returncode"),
                }
            )
            infra = driver.step_losses(row)
            if infra:
                kind = (
                    "transport"
                    if "execute" in infra
                    else driver.observation_loss_kind(row.get("screenshot_attempts"))
                )
                raise agents.InfraLoss(kind, f"step {step} {action['op']}: {infra}")
            if result.get("returncode") not in (0, None):
                raise agents.InfraLoss(
                    "executor_device", f"step {step} {action['op']} rc={result.get('returncode')}"
                )
            self.last_command = command
        return new_shot, None, executed

    def replay_steps(
        self,
        steps_log: Any,
        first_shot: bytes,
        t_first: float,
        limit: int | None = None,
        f1_first: bool = True,
    ) -> str | None:
        """Replay recorded steps from ``first_shot`` (captured at ``t_first``). Each step's clock
        starts when its observation is available; S1a sent the next request at once after a step,
        so an empty-IR step still advances the clock by its recorded latency."""
        t_obs = t_first
        pending: bytes | None = None
        last_action: str | None = None
        terminated: str | None = None
        self.last_command = None
        recorded = self.recorded if limit is None else self.recorded[:limit]
        for rec in recorded:
            k = rec["step"]
            if pending is not None:
                self.keep(f"s{k:02d}-f0", pending)
                pending = None
            if k > 1 or f1_first:
                self.wait_until(t_obs + self.cfg.f1_delay_s)
                self.capture(f"s{k:02d}-f1")
            self.wait_until(t_obs + rec["latency_s"])
            new_shot, terminated, executed = self.execute_step(rec, k)
            ir_sha = driver.sha256_json(rec["ir"])
            steps_log.write(
                json.dumps(
                    {
                        "step": k,
                        "ir_sha256": ir_sha,
                        "recorded_ir_sha256": rec.get("ir_sha256"),
                        "ir_matches_record": rec.get("ir_sha256") in (None, ir_sha),
                        "executed": executed,
                        "terminated": terminated,
                        "new_observation": new_shot is not None,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            steps_log.flush()
            self.record["steps"] = k
            if terminated is not None:
                last_action = "FAIL" if terminated == "failure" else "DONE"
                self.record["ended"] = f"terminate_{terminated}"
                break
            if new_shot is not None:
                pending = new_shot
                last_action = self.last_command
            t_obs = self.clock()
        if limit is not None and pending is not None and terminated is None:
            nxt = len(recorded) + 1
            self.keep(f"s{nxt:02d}-f0", pending)
            self.wait_until(t_obs + self.cfg.f1_delay_s)
            self.capture(f"s{nxt:02d}-f1")
        return last_action

    # ---------------------------------------------------------------- Stage C
    def loop(self, steps_log: Any, replies_log: Any) -> str | None:
        if not self.recorded:
            raise agents.InfraLoss("runner_crash", "stage-c needs the recorded steps")
        self.record["ended"] = "step_cap"
        first = self.capture("s01-f0")
        t_first = self.clock()
        t_loop = self.clock()
        last = self.replay_steps(steps_log, first, t_first)
        self.timings["steps_s"] = round(self.clock() - t_loop, 3)
        self.record["last_action_kind"] = last if last in ("FAIL", "DONE", None) else "command"
        return last

    # ---------------------------------------------------------------- A1
    def run_a1(self) -> dict[str, Any]:
        t0 = self.clock()
        self.record["t_start"] = t0
        session = None
        steps_log = (self.out / "steps.jsonl").open("w", encoding="utf-8")
        try:
            self.check_no_gpu()
            self.wait_for_boot()
            t = self.clock()
            try:
                session = self.session_factory(self.cfg, self.task)
                self.session = session
                self.record["setup"] = driver.for_record(session.setup())
            except agents.InfraLoss:
                raise
            except Exception as exc:  # noqa: BLE001 - any setup failure is a setup loss
                raise agents.InfraLoss("task_setup", f"{type(exc).__name__}: {exc}") from exc
            self.timings["setup_s"] = round(self.clock() - t, 3)
            failures = list((self.record["setup"] or {}).get("failures") or [])
            if failures:
                raise agents.InfraLoss("task_setup", f"failed in the guest: {failures[0]}")
            self.warm_up()
            t = self.clock()
            self.sleep(self.cfg.settle_after_reset_s)
            self.timings["settle_after_reset_s"] = round(self.clock() - t, 3)
            base = self.clock()
            first = None
            for off in self.cfg.frame_offsets_s:
                self.wait_until(base + off)
                shot = self.capture(f"t{off:+.1f}")
                first = first or shot
            if self.cfg.late_frame_s is not None:
                self.wait_until(base + self.cfg.late_frame_s)
                self.capture(f"t{self.cfg.late_frame_s:+.1f}")
            if self.cfg.open_loop_steps:
                self.record["ended"] = None
                self.replay_steps(
                    steps_log, first, base, limit=self.cfg.open_loop_steps, f1_first=False
                )
            self.record.update(
                status="captured", infrastructure_type=None, ended=self.record.get("ended") or "a1"
            )
        except agents.InfraLoss as loss:
            self.record.update(
                status="infrastructure",
                infrastructure_type=loss.kind,
                infrastructure_detail=loss.detail[:500],
                ended="infra",
            )
        except Exception as exc:  # noqa: BLE001
            self.record.update(
                status="infrastructure",
                infrastructure_type="runner_crash",
                infrastructure_detail=f"{type(exc).__name__}: {exc}"[:500],
                traceback_tail=traceback.format_exc()[-1500:],
                ended="infra",
            )
        finally:
            steps_log.close()
            if session is not None:
                with contextlib.suppress(Exception):
                    session.close()
        return self.finish(t0)

    def finish(self, t0: float) -> dict[str, Any]:
        self.record["observations"] = {"agent": dict(self.agent_observations)}
        self.record["frames"] = self.frames
        self.record["t_end"] = self.clock()
        self.timings["runner_s"] = round(self.record["t_end"] - t0, 3)
        self.record["timings"] = self.timings
        (self.out / "episode.json").write_text(
            json.dumps(self.record, indent=1, sort_keys=True), encoding="utf-8"
        )
        lines = [f"{f['raw_sha256']}  frames/{f['label']}.png" for f in self.frames]
        (self.out / "frames.sha256").write_text(
            "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
        )
        return self.record

    def run(self) -> dict[str, Any]:
        if self.cfg.r01_mode == "a1":
            return self.run_a1()
        if self.cfg.r01_mode != "stage-c":
            raise ValueError(f"unknown r01_mode {self.cfg.r01_mode}")
        return super().run()


def frame_digest(png: bytes) -> str:
    return hashlib.sha256(png).hexdigest()


def run_from_config(config_path: Path) -> dict[str, Any]:
    """The episode container's entry point (live guest and OSWorld; no engine)."""
    from harness.q2.vm.guest_http import GuestClient
    from harness.q2_stage1.osworld_live import LiveTask, load_task

    cfg = OpenLoopConfig.from_json(json.loads(config_path.read_text(encoding="utf-8")))
    task = load_task(cfg.osworld_dir, cfg.task_id)

    def session_factory(c: OpenLoopConfig, t: dict[str, Any]) -> LiveTask:
        return LiveTask(
            t,
            osworld_dir=c.osworld_dir,
            file_cache=Path(c.file_cache_dir),
            guest_ip=c.guest_ip,
            server_port=c.server_port,
            cache_root=Path("/tmp/osworld-cache"),
        )

    runner = OpenLoopRunner(
        cfg,
        guest=GuestClient(cfg.guest_ip, cfg.server_port),
        session_factory=session_factory,
        task=task,
    )
    return runner.run()


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, required=True)
    args = ap.parse_args(list(argv) if argv is not None else None)
    record = run_from_config(args.config)
    print(
        json.dumps(
            {
                k: record.get(k)
                for k in ("slot", "r01_mode", "status", "infrastructure_type", "score")
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
