"""The K2 injection executor: one in-VM run of one sampled scoring job.

Registration ``q2-evaluator-mutation-v1-k2`` sections 3-5. One process per run, inside the
GPU-less episode container (the checker-mutation study's metric image, OSWorld's locked
environment) that the K2 lane (``lane.py``) starts in a freshly booted VM container's
``--network none`` namespace (D12, D13), exactly as the S1a lane starts an episode. It
executes the frozen injection plan of ``harness/q2_mutation/vm_injection.py`` against the
certified VM runtime (action-path v2) and writes one run record:

1. wait for the cold boot (``driver.Runner.wait_for_boot``);
2. ``reset_task``: the task's own setup, offline from the pinned file cache
   (``osworld_live.LiveTask.setup``, S1a's unmodified call of the pinned code);
3. the guard's keyboard warm-up, once per boot (action-path v2 design decision 31; the
   postconfig's Ctrl+S must not be the boot's first XTest key event), and OSWorld's 60 s
   settle (S1a section 7.1 step 4);
4. the plan's ops, in the plan's order: ``kill_process`` (SIGTERM, then SIGKILL after 20 s;
   then LibreOffice's stale lock files for the targets are removed), ``assert_no_window``,
   ``hash pre_inject``, ``upload`` (the pinned ``SetupController._upload_file_setup``: the
   ``/setup/upload`` endpoint the task's download step uses), ``hash post_inject`` (each
   placed file must equal the candidate's SHA-256, else cause (3)), ``config_step`` (the
   task's own ``open``/``launch`` step through the pinned ``SetupController``, then a wait
   for a window that names the file), ``agent_save`` (open if no window names the file,
   ``activate_window`` strict, the postconfig's own Ctrl+S command, then a wait for the
   write) and ``open_file`` (the ``open`` step, then the window wait);
5. S1a's 20 s settle before evaluation and its guest-server restart check;
6. ``hash pre_postconfig``; then the plan's ``postconfig``, ``hash post_postconfig`` and
   ``evaluate`` are one call of the pinned ``DesktopEnv.evaluate()`` (it runs the postconfig
   itself, then the getters), with ``DONE`` as the last action (the offline harness's
   ``NON_FAIL_ACTION``). ``post_postconfig`` is read without a guest call between the
   postconfig and the getters: it is the SHA-256 of the bytes each getter read
   (``CaptureController``), so the checker reads the file exactly when the pipeline does
   (section 12 item 2);
7. ``hash post_evaluate``; a postconfig-saved target the checker read unsaved is watched up
   to 30 s for a late write (cause (1)'s evidence); then S1a's capture sweep, the capture
   (kept on the host, never committed) and the final restart check.

Context files that a postconfig ``--convert-to`` derives are not uploaded: the postconfig
makes them in the VM, as the offline save stage removes them before its conversion
(section 3.3).

Classification (section 5.1, ``rules.py``): a failure of an executor step (boot, task setup,
warm-up, kill, window, upload, reopen, agent save), a guest transport failure, an undelivered
checker observation, an offline refusal, a guest-server restart or a runner crash ends the
run as ``vm_infrastructure_failure`` (cause 4); a placed file whose in-VM hash differs from
the candidate's ends it as ``injection_hash_mismatch`` (cause 3). A metric that raises, or an
``evaluate()`` that returns ``None``, is the in-VM verdict ``error`` (the offline harness's
reading), never an exclusion. The record keeps no stdout tail of any guest command
(``driver.strip_stdout``).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import posixpath
import time
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from harness.q2_mutation_k2 import rules

CTRL_S_COMMAND = ["python", "-c", 'import pyautogui; pyautogui.hotkey("ctrl", "s");']
LAST_ACTION = "DONE"  # harness.q2_mutation.offline_eval.NON_FAIL_ACTION
GUEST_SCRIPT = Path(__file__).resolve().parent / "guest" / "k2_guest.py"
DIALOG_MARKERS = ("Document Recovery", "Document in Use", "Locked Document")
SETTLE_AFTER_RESET_S = 60.0
SETTLE_BEFORE_EVAL_S = 20.0
BOOT_TIMEOUT_S = 300.0
WINDOW_TIMEOUT_S = 90.0
WRITE_TIMEOUT_S = 30.0
LATE_WRITE_WATCH_S = 30.0
CLOSE_TERM_WAIT_S = 20.0
CLOSE_KILL_WAIT_S = 5.0


class InjectionFailure(RuntimeError):
    """An executor step failed: the run is a VM infrastructure failure (cause 4)."""

    def __init__(self, step: str, detail: str):
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail


class HashMismatch(RuntimeError):
    """A placed file's in-VM hash differs from the candidate's (cause 3)."""


@dataclass
class K2Config:
    lane: str
    purpose: str
    slot: str
    set: str
    pair: int
    run: int
    attempt: int
    block: str
    job_id: str
    mutant_id: str
    task_id: str
    kind: str
    candidate_sha256: str
    files: dict[str, dict[str, str]]
    out_dir: str = "/out"
    guest_ip: str = "20.20.20.21"
    server_port: int = 5000
    osworld_dir: str = "/inputs/OSWorld"
    file_cache_dir: str = "/inputs/file_cache/files"
    settle_after_reset_s: float = SETTLE_AFTER_RESET_S
    settle_before_eval_s: float = SETTLE_BEFORE_EVAL_S
    boot_timeout_s: float = BOOT_TIMEOUT_S
    window_timeout_s: float = WINDOW_TIMEOUT_S
    write_timeout_s: float = WRITE_TIMEOUT_S
    late_write_watch_s: float = LATE_WRITE_WATCH_S
    t_vm_start: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> K2Config:
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        unknown = sorted(set(data) - set(known))
        if unknown:
            raise ValueError(f"unknown K2 run config keys: {unknown}")
        return cls(**known)


class VMOps(Protocol):
    """The guest operations the plan needs (``LiveOps`` in the VM, a fake in tests)."""

    def hash(self, paths: Sequence[str]) -> dict[str, Any]: ...
    def close_app(self, name: str) -> dict[str, Any]: ...
    def remove_locks(self, paths: Sequence[str]) -> dict[str, Any]: ...
    def windows(self) -> list[str]: ...
    def wait_written(self, path: str, before: Mapping[str, Any], timeout: float) -> dict: ...
    def upload(self, path: str, local: str) -> dict[str, Any]: ...
    def run_steps(self, steps: Sequence[Mapping[str, Any]]) -> dict[str, Any]: ...


class Session(Protocol):
    """What the executor needs from the OSWorld side (``InjectionTask`` or a fake)."""

    def setup(self) -> dict[str, Any]: ...
    def evaluate(self, last_action: str | None) -> Any: ...
    def checker_reads_since(self, index: int) -> dict[str, str | None]: ...
    def read_count(self) -> int: ...
    def capture_sweep(self) -> list[dict[str, Any]]: ...
    def write_capture(self, capture_dir: Path) -> dict[str, Any]: ...
    def close(self) -> None: ...


def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def derived_paths(raw: Mapping[str, Any], paths: Sequence[str]) -> list[str]:
    """Candidate paths a postconfig ``--convert-to`` produces (not uploaded; section 3.3).

    Matches the offline save stage's rule (``LoSession.convert``): in the conversion's output
    directory, ``stem.ext`` or ``stem-*.ext`` of a converted input.
    """
    from harness.q2_mutation.reachability import derived_outputs, plan_postconfig

    outputs: list[tuple[str, str, str]] = []
    for step in plan_postconfig(raw.get("evaluator", {}).get("postconfig", [])):
        if step.kind == "convert":
            outputs += derived_outputs(step.argv)
    out = []
    for path in paths:
        directory, name = posixpath.split(path)
        for out_dir, stem, ext in outputs:
            if directory != out_dir or not name.endswith(f".{ext}"):
                continue
            if name == f"{stem}.{ext}" or name.startswith(f"{stem}-"):
                out.append(path)
                break
    return sorted(out)


def window_names(titles: Sequence[str], path: str) -> list[str]:
    name = posixpath.basename(path)
    return [t for t in titles if name in t]


def dialogs(titles: Sequence[str]) -> list[str]:
    return [t for t in titles if any(marker in t for marker in DIALOG_MARKERS)]


class Injector:
    """One K2 run: boot wait, reset, warm-up, the plan's ops, evaluation and the record.

    The boot wait, warm-up and restart checks are S1a's (``driver.Runner``'s methods, used
    unchanged through ``_runner``)."""

    def __init__(
        self,
        cfg: K2Config,
        *,
        guest: Any,
        task: Mapping[str, Any],
        session_factory: Callable[[K2Config, Mapping[str, Any]], Session],
        ops_factory: Callable[[Any, Session], VMOps],
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        gpu_glob: Callable[[], list[str]] | None = None,
    ):
        self.cfg = cfg
        self.guest = guest
        self.task = dict(task)
        self.session_factory = session_factory
        self.ops_factory = ops_factory
        self.sleep = sleep
        self.clock = clock
        self.gpu_glob = gpu_glob
        self.out = Path(cfg.out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.timings: dict[str, float] = {}
        self.session: Session | None = None
        self.ops: VMOps | None = None
        self.steps: list[dict[str, Any]] = []
        self.record: dict[str, Any] = {
            "schema": rules.RUN_SCHEMA,
            "experiment_id": rules.EXPERIMENT_ID,
            "lane": cfg.lane,
            "purpose": cfg.purpose,
            "slot": cfg.slot,
            "set": cfg.set,
            "pair": cfg.pair,
            "run": cfg.run,
            "attempt": cfg.attempt,
            "block": cfg.block,
            "job_id": cfg.job_id,
            "mutant_id": cfg.mutant_id,
            "task_id": cfg.task_id,
            "kind": cfg.kind,
            "candidate_sha256": cfg.candidate_sha256,
            "status": "infrastructure",
            "exclusion": rules.VM_INFRA,
            "infrastructure_type": "runner_crash",
            "score": None,
            "verdict": None,
        }
        self._runner = self._make_runner()

    def _make_runner(self) -> Any:
        """S1a's ``driver.Runner`` holding this run's guest, clock, record and timings, so its
        boot wait, warm-up and restart checks run unchanged."""
        from harness.q2_stage1 import driver

        runner = driver.Runner.__new__(driver.Runner)
        runner.cfg = self.cfg
        runner.guest = self.guest
        runner.sleep = self.sleep
        runner.clock = self.clock
        runner.timings = self.timings
        runner.record = self.record
        runner.session = None
        runner.out = self.out
        return runner

    # ---------------------------------------------------------------- helpers
    def step(self, op: str, **data: Any) -> dict[str, Any]:
        row = {"op": op, "t": round(self.clock(), 3), **data}
        self.steps.append(row)
        return row

    def guest_hash(self, tag: str, paths: Sequence[str]) -> dict[str, dict[str, Any]]:
        assert self.ops is not None
        try:
            result = self.ops.hash(list(paths))
        except Exception as exc:  # noqa: BLE001 - a hash the guest cannot answer is cause (4)
            raise InjectionFailure(f"hash {tag}", f"{type(exc).__name__}: {exc}") from exc
        files = {row["path"]: row for row in result.get("files", [])}
        missing = sorted(set(paths) - set(files))
        if missing:
            raise InjectionFailure(f"hash {tag}", f"no reading for {missing}")
        self.step(
            "hash",
            tag=tag,
            files={p: files[p].get("sha256") for p in paths},
            guest_time=result.get("guest_time"),
            t_local=self.clock(),
        )
        return files

    def windows(self) -> list[str]:
        assert self.ops is not None
        try:
            return list(self.ops.windows())
        except Exception as exc:  # noqa: BLE001 - the window list is an executor step
            raise InjectionFailure("windows", f"{type(exc).__name__}: {exc}") from exc

    def wait_window(self, path: str, reason: str) -> str:
        """Wait for a window that names ``path`` and no recovery or lock dialog."""
        started = self.clock()
        titles: list[str] = []
        while True:
            titles = self.windows()
            found = window_names(titles, path)
            if dialogs(titles):
                raise InjectionFailure(reason, f"dialog after opening {path}: {dialogs(titles)}")
            if found:
                self.step(
                    "window",
                    path=path,
                    reason=reason,
                    title=found[0],
                    waited_s=round(self.clock() - started, 3),
                )
                return found[0]
            if self.clock() - started > self.cfg.window_timeout_s:
                raise InjectionFailure(
                    reason,
                    f"no window names {posixpath.basename(path)} "
                    f"within {self.cfg.window_timeout_s} s",
                )
            self.sleep(1.0)

    def steps_ok(self, op: str, result: Mapping[str, Any]) -> None:
        from harness.q2_stage1.driver import strip_stdout

        self.step(
            op,
            replies=strip_stdout(result.get("replies")),
            failures=list(result.get("failures") or []),
        )
        if result.get("failures"):
            raise InjectionFailure(op, f"failed in the guest: {result['failures'][0]}")
        if result.get("ok") is False:
            raise InjectionFailure(op, "the setup controller could not reach the guest")

    def run_steps(self, op: str, steps: Sequence[Mapping[str, Any]]) -> None:
        assert self.ops is not None
        try:
            result = self.ops.run_steps(list(steps))
        except Exception as exc:  # noqa: BLE001 - any failure of an executor step is cause (4)
            raise InjectionFailure(op, f"{type(exc).__name__}: {str(exc)[:300]}") from exc
        self.steps_ok(op, result)

    # ---------------------------------------------------------------- the run
    def candidate(self) -> tuple[dict[str, dict[str, str]], list[str]]:
        """The files to place (VM path -> local, SHA-256), each checked against its declared
        digest, and the derived paths left to the postconfig (section 3.3)."""
        from harness.q2_mutation.tasks import resolve_vm_path

        files = {resolve_vm_path(p): dict(v) for p, v in self.cfg.files.items()}
        target_ok = False
        for path, info in files.items():
            local = Path(info["local"])
            if not local.is_file():
                raise InjectionFailure("candidate", f"{path}: candidate file missing")
            actual = sha256_file(local)
            if actual != info["sha256"]:
                raise InjectionFailure("candidate", f"{path}: candidate file digest differs")
            target_ok |= actual == self.cfg.candidate_sha256
        if not target_ok:
            raise InjectionFailure("candidate", "no file carries the candidate's SHA-256")
        derived = derived_paths(self.task, sorted(files))
        placed = {p: v for p, v in files.items() if p not in derived}
        if not placed:
            raise InjectionFailure("candidate", "every candidate file is a postconfig output")
        return placed, derived

    def run(self) -> dict[str, Any]:
        t0 = self.clock()
        self.record["t_start"] = t0
        session: Session | None = None
        try:
            self.check_no_gpu()
            self._runner.wait_for_boot()
            placed, derived = self.candidate()
            self.record["derived_not_uploaded"] = derived
            t = self.clock()
            try:
                session = self.session_factory(self.cfg, self.task)
                self.session = session
                self._runner.session = session
                setup = session.setup()
            except Exception as exc:  # noqa: BLE001 - any setup failure is a reset failure
                raise InjectionFailure("reset_task", f"{type(exc).__name__}: {exc}") from exc
            from harness.q2_stage1.driver import for_record

            self.record["setup"] = for_record(setup)
            self.timings["setup_s"] = round(self.clock() - t, 3)
            if (setup or {}).get("failures"):
                raise InjectionFailure("reset_task", f"failed in the guest: {setup['failures'][0]}")
            self.ops = self.ops_factory(self.guest, session)
            self._runner.warm_up()
            t = self.clock()
            self.sleep(self.cfg.settle_after_reset_s)
            self.timings["settle_after_reset_s"] = round(self.clock() - t, 3)
            self.execute(placed)
        except HashMismatch as exc:
            self.record.update(
                status="infrastructure",
                exclusion=rules.HASH_MISMATCH,
                infrastructure_type="injection_hash_mismatch",
                infrastructure_detail=str(exc)[:500],
                score=None,
                verdict=None,
            )
        except InjectionFailure as exc:
            self.record.update(
                status="infrastructure",
                exclusion=rules.VM_INFRA,
                infrastructure_type=f"executor:{exc.step}",
                infrastructure_detail=exc.detail[:500],
                score=None,
                verdict=None,
            )
        except Exception as exc:  # noqa: BLE001 - S1a's InfraLoss and any crash are cause (4)
            kind = getattr(exc, "kind", None)
            if kind is not None:
                kind = self._runner.restart_behind(exc)
            self.record.update(
                status="infrastructure",
                exclusion=rules.VM_INFRA,
                infrastructure_type=kind or "runner_crash",
                infrastructure_detail=str(getattr(exc, "detail", exc))[:500],
                score=None,
                verdict=None,
            )
            if kind is None:
                self.record["traceback_tail"] = traceback.format_exc()[-1500:]
        finally:
            if session is not None:
                with contextlib.suppress(Exception):
                    session.close()
        return self.finish(t0)

    def check_no_gpu(self) -> None:
        import glob

        devices = sorted(self.gpu_glob() if self.gpu_glob else glob.glob("/dev/nvidia*"))
        self.record["gpu_devices"] = devices
        if devices:
            raise InjectionFailure("gpu", f"D12: GPU device files visible: {devices}")

    def execute(self, placed: Mapping[str, Mapping[str, str]]) -> None:
        from harness.q2_mutation.vm_injection import build_injection_plan

        assert self.ops is not None and self.session is not None
        plan = build_injection_plan(self.task, placed, self.cfg.candidate_sha256)
        self.record["plan_sha256"] = sha256_json(plan)
        self.record["plan_ops"] = [p["op"] for p in plan]
        save_paths = dict(plan[-1]["save_paths"])
        self.record["save_paths"] = save_paths
        targets = sorted(save_paths)
        hashes: dict[str, dict[str, Any]] = {}
        t = self.clock()
        for op in plan:
            kind = op["op"]
            if kind == "reset_task":
                continue  # done above (setup), before the warm-up and the settle
            if kind == "kill_process":
                self.kill(op["name"])
                self.remove_locks(targets)
            elif kind == "assert_no_window":
                titles = self.windows()
                held = [t for t in titles if any(n in t for n in op["titles_containing"])]
                self.step("assert_no_window", held=held)
                if held:
                    raise InjectionFailure(
                        "assert_no_window", f"a window still names a target: {held}"
                    )
            elif kind == "hash" and op["tag"] in ("pre_inject", "post_inject"):
                hashes[op["tag"]] = self.guest_hash(op["tag"], op["paths"])
                if op.get("expect") == "candidate":
                    bad = sorted(
                        p
                        for p in op["paths"]
                        if hashes[op["tag"]][p].get("sha256") != placed[p]["sha256"]
                    )
                    if bad:
                        raise HashMismatch(f"post_inject: in-VM hash differs for {bad}")
            elif kind == "upload":
                self.upload(op["path"], op["local"])
            elif kind == "config_step":
                self.run_steps("config_step", [op["step"]])
                for path in op["opens"]:
                    self.wait_window(path, "config_step")
            elif kind == "agent_save":
                self.agent_save(op["path"], op["window"])
            elif kind == "open_file":
                self.run_steps("open_file", [{"type": "open", "parameters": {"path": op["path"]}}])
                self.wait_window(op["path"], "open_file")
            elif kind == "hash" and op["tag"] == "pre_postconfig":
                self.timings["inject_s"] = round(self.clock() - t, 3)
                ts = self.clock()
                self.sleep(self.cfg.settle_before_eval_s)
                self.timings["settle_before_eval_s"] = round(self.clock() - ts, 3)
                self._runner.check_restarts("server_end")
                titles = self.windows()
                self.record["windows_before_postconfig"] = titles
                if dialogs(titles):
                    raise InjectionFailure("pre_postconfig", f"dialog open: {dialogs(titles)}")
                hashes["pre_postconfig"] = self.guest_hash("pre_postconfig", op["paths"])
            elif kind == "postconfig":
                continue  # run by evaluate() itself (section 3.4)
            elif kind == "hash" and op["tag"] == "post_postconfig":
                continue  # read from the checker's own reads (section 3.4)
            elif kind == "evaluate":
                self.evaluate(save_paths, hashes)
            else:
                raise InjectionFailure("plan", f"unknown op {kind}")
        self.record["hashes"] = {
            tag: {p: row.get("sha256") for p, row in rows.items()} for tag, rows in hashes.items()
        }

    def kill(self, name: str) -> None:
        assert self.ops is not None
        try:
            result = self.ops.close_app(name)
        except Exception as exc:  # noqa: BLE001
            raise InjectionFailure("kill_process", f"{type(exc).__name__}: {exc}") from exc
        self.step(
            "kill_process",
            name=name,
            found=len(result.get("found") or []),
            term=len(result.get("term") or []),
            kill=len(result.get("kill") or []),
            remaining=result.get("remaining") or [],
            term_wait_s=result.get("term_wait_s"),
        )
        if result.get("remaining"):
            raise InjectionFailure("kill_process", f"still running: {result['remaining']}")

    def remove_locks(self, paths: Sequence[str]) -> None:
        assert self.ops is not None
        try:
            result = self.ops.remove_locks(list(paths))
        except Exception as exc:  # noqa: BLE001
            raise InjectionFailure("remove_locks", f"{type(exc).__name__}: {exc}") from exc
        self.step("remove_locks", removed=result.get("removed") or [])
        if result.get("error"):
            raise InjectionFailure("remove_locks", str(result["error"]))

    def upload(self, path: str, local: str) -> None:
        assert self.ops is not None
        try:
            result = self.ops.upload(path, local)
        except Exception as exc:  # noqa: BLE001
            raise InjectionFailure("upload", f"{type(exc).__name__}: {str(exc)[:300]}") from exc
        self.steps_ok("upload", result)

    def agent_save(self, path: str, window: str | None) -> None:
        """Open if no window names the file, activate it (strict), the postconfig's own Ctrl+S,
        then wait for the write (the offline save stage's agent-equivalent save)."""
        assert self.ops is not None
        if not window_names(self.windows(), path):
            self.run_steps("agent_save:open", [{"type": "open", "parameters": {"path": path}}])
            self.wait_window(path, "agent_save")
        if window:
            self.run_steps(
                "agent_save:activate",
                [
                    {
                        "type": "activate_window",
                        "parameters": {"window_name": window, "strict": True},
                    }
                ],
            )
        before = self.guest_hash("agent_save:before", [path])[path]
        self.run_steps(
            "agent_save:ctrl_s",
            [{"type": "execute", "parameters": {"command": list(CTRL_S_COMMAND)}}],
        )
        try:
            waited = self.ops.wait_written(path, before, self.cfg.write_timeout_s)
        except Exception as exc:  # noqa: BLE001
            raise InjectionFailure("agent_save", f"{type(exc).__name__}: {exc}") from exc
        seconds = waited.get("seconds")
        self.step(
            "agent_save",
            path=path,
            seconds_to_write=seconds,
            after=(waited.get("state") or {}).get("sha256"),
        )
        if seconds is None:
            raise InjectionFailure(
                "agent_save", f"{path} not written within {self.cfg.write_timeout_s} s"
            )

    def evaluate(self, save_paths: Mapping[str, str], hashes: dict[str, Any]) -> None:
        from harness.q2_mutation.schema import verdict_for_score
        from harness.q2_stage1.driver import strip_stdout
        from harness.q2_stage1.osworld_live import (
            is_observation_failure,
            is_offline_refusal,
            is_transport_error,
            setup_reply_failed,
        )

        assert self.session is not None and self.ops is not None
        session = self.session
        reads_before = session.read_count()
        t = self.clock()
        score: Any = None
        try:
            score = session.evaluate(LAST_ACTION)
        except Exception as exc:  # noqa: BLE001 - classified below
            if is_transport_error(exc):
                raise InjectionFailure("evaluate", f"transport: {exc}") from exc
            if is_observation_failure(exc):
                raise InjectionFailure("evaluate", f"guest observation: {exc}") from exc
            if is_offline_refusal(exc):
                raise InjectionFailure("evaluate", f"offline refusal: {exc}") from exc
            self.record["metric_error"] = f"{type(exc).__name__}: {exc}"[:500]
            score = None
        finally:
            replies = getattr(session, "evaluate_replies", None)
            if replies is not None:
                self.record["postconfig_replies"] = strip_stdout(replies)
                self.record["postconfig_failures"] = sum(
                    1 for r in replies if setup_reply_failed(r)
                )
        self.timings["evaluate_s"] = round(self.clock() - t, 3)
        if score is not None and not isinstance(score, bool):
            try:
                score = float(score)
            except (TypeError, ValueError):
                self.record["metric_error"] = f"score {score!r} is not a number"
                score = None
        checker_read = session.checker_reads_since(reads_before)
        targets = sorted(save_paths)
        post = self.guest_hash("post_evaluate", targets)
        pre = {p: row.get("sha256") for p, row in hashes["pre_postconfig"].items()}
        unsaved = rules.unsaved_at_read(save_paths, pre, checker_read)
        late: dict[str, Any] = {}
        for path in unsaved:
            changed = post[path].get("sha256") != pre.get(path)
            seconds = None
            if not changed:
                waited = self.ops.wait_written(
                    path, hashes["pre_postconfig"][path], self.cfg.late_write_watch_s
                )
                seconds = waited.get("seconds")
                changed = seconds is not None
            late[path] = {"changed": changed, "watched_s": seconds}
        self.record.update(
            checker_read=checker_read,
            post_postconfig={p: checker_read.get(p) for p in targets},
            unsaved_at_read=unsaved,
            late_write=late,
            save_latency=self.save_latency(hashes["pre_postconfig"], post, save_paths),
        )
        hashes["post_evaluate"] = post
        t = self.clock()
        try:
            self.record["capture_sweep"] = session.capture_sweep()
        except Exception as exc:  # noqa: BLE001
            if is_transport_error(exc) or is_observation_failure(exc):
                raise InjectionFailure("capture", f"{exc}") from exc
            self.record["capture_sweep_error"] = f"{type(exc).__name__}: {exc}"[:300]
        manifest = session.write_capture(self.out / "capture")
        self.timings["capture_s"] = round(self.clock() - t, 3)
        self._runner.check_restarts("server_final")
        observations = getattr(session, "observation_summary", None)
        if callable(observations):
            with contextlib.suppress(Exception):
                self.record["observations"] = observations()
        verdict = verdict_for_score(score)
        self.record.update(
            status="scored",
            exclusion=None,
            infrastructure_type=None,
            score=score,
            verdict=verdict,
            state_sha256=manifest.get("state_sha256"),
        )

    def save_latency(
        self, pre: Mapping[str, Any], post: Mapping[str, Any], save_paths: Mapping[str, str]
    ) -> dict[str, Any]:
        """Reported only (section 8): each postconfig-saved target's write time after the
        postconfig's Ctrl+S reply, on the guest clock (mtime) mapped through the offset read
        at the pre-postconfig hash. Approximate: it bounds the save, it decides nothing."""
        out: dict[str, Any] = {}
        offset_row = next((s for s in self.steps if s.get("tag") == "pre_postconfig"), None)
        replies = self.record.get("postconfig_replies") or []
        ctrl = [r for r in replies if r.get("type") == "execute" and r.get("t") is not None]
        if not offset_row or offset_row.get("guest_time") is None or not ctrl:
            return out
        offset = float(offset_row["guest_time"]) - float(offset_row["t_local"])
        for path, how in save_paths.items():
            mtime = (post.get(path) or {}).get("mtime_ns")
            if how != "postconfig_save" or mtime is None:
                continue
            if (post.get(path) or {}).get("sha256") == (pre.get(path) or {}).get("sha256"):
                continue
            out[path] = round(mtime / 1e9 - offset - float(ctrl[0]["t"]), 3)
        return out

    def finish(self, t0: float) -> dict[str, Any]:
        self.record["steps"] = self.steps
        self.record["t_end"] = self.clock()
        self.timings["run_s"] = round(self.record["t_end"] - t0, 3)
        self.record["timings"] = self.timings
        (self.out / "k2-run.json").write_text(
            json.dumps(self.record, indent=1, sort_keys=True), encoding="utf-8"
        )
        return self.record


# ------------------------------------------------------------------- live side (metric image)


def make_injection_task(base: type) -> type:
    """``osworld_live.LiveTask`` plus the inject phase: setup steps sent through the pinned
    ``SetupController`` with S1a's reply and transport tracking, and the checker's reads."""

    class InjectionTask(base):  # type: ignore[misc, valid-type]
        def run_steps(self, steps: Sequence[Mapping[str, Any]], phase: str = "inject") -> dict:
            from harness.q2_stage1.osworld_live import describe_reply, setup_reply_failed

            mark = self.mark()
            first = self.begin_phase(phase)
            try:
                ok = self.env.setup_controller.setup(list(steps), False)
            except Exception as exc:
                self.check_transport(phase, mark, exc)
                raise
            finally:
                self.step_state["phase"] = None
            self.check_transport(phase, mark)
            replies = self.replies_since(first)
            return {
                "ok": ok,
                "replies": replies,
                "failures": [describe_reply(r) for r in replies if setup_reply_failed(r)],
            }

        def read_count(self) -> int:
            return len(self.env.controller.reads)

        def checker_reads_since(self, index: int) -> dict[str, str | None]:
            """The SHA-256 of the bytes the checker's ``get_file`` calls returned, per path
            (the last read of a path wins; ``None`` when it never arrived)."""
            from harness.q2_mutation.tasks import resolve_vm_path

            out: dict[str, str | None] = {}
            for read in self.env.controller.reads[index:]:
                out[resolve_vm_path(str(read.path))] = read.sha256
            return out

    return InjectionTask


class LiveOps:
    """``VMOps`` against the guest server: the guest helper script and the pinned
    ``SetupController`` steps (through the session, so S1a's shim records every reply)."""

    def __init__(self, guest: Any, session: Any):
        self.guest = guest
        self.session = session
        self.source = GUEST_SCRIPT.read_text(encoding="utf-8")

    def script(self, mode: str, config: Mapping[str, Any]) -> dict[str, Any]:
        return self.guest.run_script(self.source, [mode, json.dumps(config)])

    def hash(self, paths: Sequence[str]) -> dict[str, Any]:
        return self.script("hash", {"paths": list(paths)})

    def close_app(self, name: str) -> dict[str, Any]:
        return self.script(
            "close_app",
            {"name": name, "term_wait_s": CLOSE_TERM_WAIT_S, "kill_wait_s": CLOSE_KILL_WAIT_S},
        )

    def remove_locks(self, paths: Sequence[str]) -> dict[str, Any]:
        return self.script("remove_locks", {"paths": list(paths)})

    def windows(self) -> list[str]:
        result = self.script("windows", {})
        if result.get("returncode") != 0:
            raise RuntimeError(f"wmctrl -l: rc={result.get('returncode')} {result.get('stderr')}")
        return list(result.get("titles") or [])

    def wait_written(self, path: str, before: Mapping[str, Any], timeout: float) -> dict:
        return self.script(
            "wait_written",
            {
                "path": path,
                "mtime_ns": before.get("mtime_ns"),
                "size": before.get("size"),
                "timeout_s": timeout,
            },
        )

    def upload(self, path: str, local: str) -> dict[str, Any]:
        step = {
            "type": "upload_file",
            "parameters": {"files": [{"local_path": local, "path": path}]},
        }
        return self.session.run_steps([step])

    def run_steps(self, steps: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return self.session.run_steps(list(steps))


def run_from_config(config_path: Path) -> dict[str, Any]:
    """The episode container's entry point: a live guest and live OSWorld."""
    from harness.q2.vm.guest_http import GuestClient
    from harness.q2_stage1.osworld_live import LiveTask, load_task

    data = json.loads(config_path.read_text(encoding="utf-8"))
    cfg = K2Config.from_json(data)
    task = load_task(cfg.osworld_dir, cfg.task_id)
    injection_task = make_injection_task(LiveTask)

    def session_factory(c: K2Config, t: Mapping[str, Any]) -> Any:
        return injection_task(
            t,
            osworld_dir=c.osworld_dir,
            file_cache=Path(c.file_cache_dir),
            guest_ip=c.guest_ip,
            server_port=c.server_port,
            cache_root=Path("/tmp/osworld-cache"),
        )

    injector = Injector(
        cfg,
        guest=GuestClient(cfg.guest_ip, cfg.server_port),
        task=task,
        session_factory=session_factory,
        ops_factory=LiveOps,
    )
    return injector.run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    record = run_from_config(args.config)
    keys = ("slot", "status", "exclusion", "infrastructure_type", "verdict")
    print(json.dumps({k: record.get(k) for k in keys}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
