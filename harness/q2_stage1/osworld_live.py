"""OSWorld ``b138d348`` task setup and checker, run live against an S1a episode's VM.

Registration section 7.1 steps 2, 7 and 8. The episode runner runs inside the checker-
mutation study's metric image (OSWorld's own locked environment, ``/opt/venv-lock``) in the
VM container's ``--network none`` namespace, with the OSWorld tree and the pinned file cache
mounted read-only. It builds ``DesktopEnv`` without a provider (``DesktopEnv.__new__``: the
VM is already a cold boot from the read-only qcow2, so ``reset``'s snapshot revert has
nothing to do) and calls the unmodified pinned code:

* setup: ``_set_task_info``, ``setup_controller.reset_cache_dir`` and
  ``setup_controller.setup(config)``, which is ``DesktopEnv.reset`` for a clean VM;
* evaluation: ``DesktopEnv.evaluate()`` (postconfig, the ``FAIL`` rule, getters, metric).

Two things are wrapped, neither changes what the checker computes:

* ``requests.get``/``requests.post``: a request to the guest server passes through; a
  file-cache URL is answered from the pinned, hash-checked local cache
  (``offline_eval.file_cache_local``); any other URL raises ``OfflineNetworkRefused``. The VM
  namespace has no egress anyway; the shim makes the offline run explicit. Every guest-bound
  call that raises a ``requests`` exception is recorded (``LiveTask.guest_errors``) before
  it propagates.
* ``controller.get_file``: OSWorld's own loop (``PythonController.get_file``: three
  attempts 5 s apart, ``None`` after the last), recording each attempt's HTTP status and the
  bytes it returned, so the final state can be captured and hashed (section 7.3) and a file
  that never arrived because of transport is told apart from one the agent never wrote
  (``TransportFailure``, an infrastructure loss; a 404 is agent state).

The pinned OSWorld code swallows transport errors in many places: ``get_vm_file`` catches
any exception from ``get_file`` (so ``TransportFailure`` never leaves it) and returns
``None``; ``SetupController._execute_setup`` and ``_activate_window_setup`` log a
``RequestException`` and go on; ``setup`` re-wraps any other step error as a bare
``Exception``; ``DesktopEnv.evaluate`` ignores a failed postconfig. So the outcome of a call
cannot tell transport from agent state. Registration section 7.2 counts "a checker getter
that cannot retrieve a file because of transport" as an infrastructure loss, so after task
setup, after ``evaluate()`` and after the capture sweep ``LiveTask`` raises
``TransportFailure`` when any guest request of that phase raised, or any file read of that
phase got no answer on every attempt, whatever the pinned code did with the error.
``is_transport_error`` reads the whole ``__cause__``/``__context__`` chain.

The pinned code also cannot see a setup step that fails *inside* the guest: the guest
server's ``/setup/execute`` answers HTTP 200 with the command's ``returncode`` for any command
that finishes, and ``_execute_setup``, ``_launch_setup`` and ``_activate_window_setup`` only log
a reply that is not 200. So the shim records every guest ``/setup/*`` reply (HTTP status,
``returncode``, the tail of stderr or of the error message, the tail of stdout) with the setup
step it answers (``LiveTask.setup_replies``; the step index and type come from wrapping the
``SetupController``'s ``_<type>_setup`` methods, which the pinned ``setup`` calls by name).
``setup_reply_failed`` is the registered reading of a reply (section 7.2): not HTTP 200, or a
non-zero ``returncode``. A failed task-setup step is a ``task_setup`` loss (driver); a failed
postconfig step during ``evaluate()`` is recorded, not a loss (it acts on the agent's state).

After evaluation a capture sweep calls every result getter once more, so the captured state
holds every file every metric reads even when ``and`` stopped early or the agent's ``FAIL``
returned 0 before any getter ran; ``rescore.py`` scores it offline with the raw and the
corrected checker.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# DesktopEnv.__init__'s client password for every provider but AWS (b138d348); it is the
# public default of the OSWorld Ubuntu image, used by setup commands' {CLIENT_PASSWORD}.
UPSTREAM_CLIENT_PASSWORD = "password"
SCREEN = (1920, 1080)
GET_FILE_ATTEMPTS = 3
GET_FILE_INTERVAL_S = 5.0
SETUP_PATH_PREFIX = "/setup/"
REPLY_TAIL = 300
# Setup step types whose argv the records keep (rule (a) of section 5.4 reads them).
ARGV_STEP_TYPES = ("execute", "command", "launch", "execute_with_verification")


class OfflineNetworkRefused(RuntimeError):
    """A setup step or checker asked for a URL that is neither the guest nor the file cache."""


class TransportFailure(RuntimeError):
    """A checker getter could not retrieve a file because the transport failed."""


@dataclass
class FileRead:
    path: str
    attempts: list[dict[str, Any]] = field(default_factory=list)
    sha256: str | None = None
    bytes: int | None = None


def import_osworld(osworld_dir: str) -> None:
    if osworld_dir not in sys.path:
        sys.path.insert(0, osworld_dir)


def setup_reply_summary(response: Any, streamed: bool = False) -> dict[str, Any]:
    """What the records keep of one guest ``/setup/*`` reply: the HTTP status and, from the
    guest server's JSON (``/setup/execute``: ``output``, ``error``, ``returncode``; a failure:
    ``status: error`` and ``message``), the ``returncode`` and the tails of stderr or the error
    message and of stdout; a text reply (``/setup/launch``, ``/setup/activate_window``, ...)
    keeps its tail."""
    out: dict[str, Any] = {"status": getattr(response, "status_code", None)}
    if streamed:
        return out
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 - a text reply
        body = None
    if isinstance(body, dict):
        if "returncode" in body:
            out["returncode"] = body["returncode"]
        for key in ("error", "message"):
            if body.get(key):
                out["error_tail"] = str(body[key])[-REPLY_TAIL:]
                break
        if body.get("output"):
            out["output_tail"] = str(body["output"])[-REPLY_TAIL:]
    else:
        with contextlib.suppress(Exception):  # nothing readable
            out["text_tail"] = str(response.text)[-REPLY_TAIL:]
    return out


def setup_reply_failed(reply: Mapping[str, Any]) -> bool:
    """The registered reading of one ``/setup/*`` reply (section 7.2): the step failed in the
    guest when the reply is not HTTP 200 or carries a non-zero ``returncode``."""
    return reply.get("status") != 200 or reply.get("returncode") not in (None, 0)


def describe_reply(reply: Mapping[str, Any]) -> str:
    where = f"{reply.get('phase')} step {reply.get('step')} ({reply.get('type')})"
    detail = reply.get("error_tail") or reply.get("text_tail") or ""
    return (
        f"{where}: {reply.get('path')} HTTP {reply.get('status')} "
        f"rc={reply.get('returncode')} {str(detail)[-160:]}"
    ).strip()


def install_network_shim(
    guest_base: str,
    file_cache: Path,
    fetched: list[str],
    guest_errors: list[dict[str, Any]] | None = None,
    guest_replies: list[dict[str, Any]] | None = None,
    context: Callable[[], dict[str, Any]] | None = None,
) -> Callable[[], None]:
    """Route ``requests.get``/``post`` (guest passes, file cache served locally, rest refused).

    A guest-bound call that raises a ``requests`` exception (connection refused or reset, a
    timeout, a broken chunked body) is appended to ``guest_errors`` and re-raised, so a
    caller that swallows it (the pinned OSWorld code does, in many places) cannot hide it.
    Every guest ``/setup/*`` reply is appended to ``guest_replies`` (``setup_reply_summary``)
    with ``context()``, the setup phase and step it answers.
    """
    import requests

    from harness.q2_mutation.offline_eval import OfflineNetworkRefused as Refused
    from harness.q2_mutation.offline_eval import make_offline_get

    real_get, real_post = requests.get, requests.post
    offline_get = make_offline_get(file_cache, fetched)
    errors = guest_errors if guest_errors is not None else []
    where = context or dict

    def guest_call(method: str, call: Callable[..., Any], url: str, *args: Any, **kwargs: Any):
        path = str(url)[len(guest_base) :]
        try:
            response = call(url, *args, **kwargs)
        except requests.exceptions.RequestException as exc:
            errors.append(
                {
                    "method": method,
                    "path": path[:200],
                    "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                    "t": time.time(),
                    **where(),
                }
            )
            raise
        if guest_replies is not None and path.startswith(SETUP_PATH_PREFIX):
            summary = setup_reply_summary(response, streamed=bool(kwargs.get("stream")))
            guest_replies.append(
                {
                    "method": method,
                    "path": path.split("?")[0][:200],
                    **summary,
                    "t": time.time(),
                    **where(),
                }  # fmt: skip
            )
        return response

    def get(url: str, *args: Any, **kwargs: Any) -> Any:
        if str(url).startswith(guest_base):
            return guest_call("GET", real_get, url, *args, **kwargs)
        try:
            return offline_get(url, *args, **kwargs)
        except Refused as exc:
            raise OfflineNetworkRefused(str(url)) from exc

    def post(url: str, *args: Any, **kwargs: Any) -> Any:
        if str(url).startswith(guest_base):
            return guest_call("POST", real_post, url, *args, **kwargs)
        raise OfflineNetworkRefused(str(url))

    requests.get, requests.post = get, post

    def restore() -> None:
        requests.get, requests.post = real_get, real_post

    return restore


def make_capture_controller(base: type, guest_ip: str, port: int, sleep=time.sleep) -> Any:
    """A ``PythonController`` whose ``get_file`` records what it read (OSWorld's loop)."""
    import requests

    class CaptureController(base):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__(vm_ip=guest_ip, server_port=port)
            self.reads: list[FileRead] = []
            self.blobs: dict[str, bytes] = {}

        def get_file(self, file_path: str) -> bytes | None:
            read = FileRead(path=file_path)
            self.reads.append(read)
            transport = 0
            for _ in range(GET_FILE_ATTEMPTS):
                try:
                    response = requests.post(
                        self.http_server + "/file", data={"file_path": file_path}
                    )
                    read.attempts.append({"status": response.status_code})
                    if response.status_code == 200:
                        data = response.content
                        read.sha256 = hashlib.sha256(data).hexdigest()
                        read.bytes = len(data)
                        self.blobs[file_path] = data
                        return data
                except requests.exceptions.RequestException as exc:
                    transport += 1
                    read.attempts.append({"error": f"{type(exc).__name__}: {str(exc)[:200]}"})
                sleep(GET_FILE_INTERVAL_S)
            if transport == GET_FILE_ATTEMPTS:
                raise TransportFailure(f"get_file({file_path}): no answer from the guest")
            return None

    return CaptureController()


class LiveTask:
    """One task's OSWorld environment against a live guest (setup, evaluate, capture)."""

    def __init__(
        self,
        task: Mapping[str, Any],
        *,
        osworld_dir: str,
        file_cache: Path,
        guest_ip: str,
        server_port: int,
        cache_root: Path,
    ):
        import_osworld(osworld_dir)
        from desktop_env.controllers.python import PythonController
        from desktop_env.controllers.setup import SetupController
        from desktop_env.desktop_env import DesktopEnv

        self.task = dict(task)
        self.fetched: list[str] = []
        self.guest_errors: list[dict[str, Any]] = []
        self.setup_replies: list[dict[str, Any]] = []
        self.transport: dict[str, list[str]] = {}
        self.step_state: dict[str, Any] = {"phase": None, "step": 0, "type": None, "depth": 0}
        self.guest_base = f"http://{guest_ip}:{server_port}"
        self.restore = install_network_shim(
            self.guest_base, file_cache, self.fetched, self.guest_errors,
            self.setup_replies, self.step_context,
        )  # fmt: skip
        env = DesktopEnv.__new__(DesktopEnv)
        env.provider_name = "docker"
        env.enable_proxy = False
        env.current_use_proxy = False
        env.is_environment_used = False
        env.action_space = "pyautogui"
        env.require_a11y_tree = False
        env.require_terminal = False
        env.vm_ip = guest_ip
        env.server_port = server_port
        env.chromium_port = 9222
        env.vlc_port = 8080
        env.client_password = UPSTREAM_CLIENT_PASSWORD
        env.screen_width, env.screen_height = SCREEN
        env.cache_dir_base = str(cache_root)
        env._traj_no = 0
        env._step_no = 0
        env.action_history = []
        env.controller = make_capture_controller(PythonController, guest_ip, server_port)
        env.setup_controller = SetupController(
            vm_ip=guest_ip,
            server_port=server_port,
            chromium_port=9222,
            vlc_port=8080,
            cache_dir=str(cache_root),
            client_password=UPSTREAM_CLIENT_PASSWORD,
            screen_width=SCREEN[0],
            screen_height=SCREEN[1],
        )
        self.track_steps(env.setup_controller)
        self.env = env

    # ---------------------------------------------------------------- setup steps (7.2)
    def step_context(self) -> dict[str, Any]:
        state = self.step_state
        return {"phase": state["phase"], "step": state["step"] or None, "type": state["type"]}

    def track_steps(self, controller: Any) -> None:
        """Wrap the controller's ``_<type>_setup`` methods (instance attributes, which the
        pinned ``setup`` reaches through ``getattr(self, name)``) so each guest reply is
        labelled with the step it answers; nested calls (``_command_setup`` calls
        ``_execute_setup``) stay in their outer step. Nothing else changes."""
        state = self.step_state

        def wrap(name: str, method: Callable[..., Any]) -> Callable[..., Any]:
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                if state["depth"] == 0:
                    state["step"] += 1
                    state["type"] = name[1 : -len("_setup")]
                state["depth"] += 1
                try:
                    return method(*args, **kwargs)
                finally:
                    state["depth"] -= 1

            return wrapped

        for name in dir(type(controller)):
            if not (name.startswith("_") and not name.startswith("__") and name.endswith("_setup")):
                continue
            method = getattr(controller, name)
            if callable(method):
                setattr(controller, name, wrap(name, method))

    def begin_phase(self, phase: str) -> int:
        self.step_state.update(phase=phase, step=0, type=None, depth=0)
        return len(self.setup_replies)

    def replies_since(self, start: int) -> list[dict[str, Any]]:
        return [dict(r) for r in self.setup_replies[start:]]

    # ---------------------------------------------------------------- transport (7.2)
    def mark(self) -> tuple[int, int]:
        return len(self.guest_errors), len(self.env.controller.reads)

    def transport_since(self, mark: tuple[int, int]) -> list[str]:
        """Transport failures since ``mark``: a guest request that raised, or a file read
        with no answer on any attempt (what the pinned code may have swallowed)."""
        errors, reads = mark
        out = [f"{e['method']} {e['path']}: {e['error']}" for e in self.guest_errors[errors:]]
        for read in self.env.controller.reads[reads:]:
            if read.attempts and all("error" in a for a in read.attempts):
                out.append(f"get_file({read.path}): no answer on {len(read.attempts)} attempts")
        return out

    def check_transport(
        self, phase: str, mark: tuple[int, int], cause: BaseException | None = None
    ) -> None:
        failures = self.transport_since(mark)
        if failures:
            self.transport[phase] = failures
            raise TransportFailure(
                f"{phase}: {len(failures)} guest transport failure(s), first {failures[0]}"
            ) from cause

    # ---------------------------------------------------------------- phases
    def setup(self) -> dict[str, Any]:
        """``DesktopEnv.reset``'s task part on a clean VM; raises on a step that raises.

        Returns the step count, every guest ``/setup/*`` reply (``replies``), the replies
        that failed in the guest (``failures``, ``setup_reply_failed``) and the task's setup
        steps (``config_steps``: type, and argv for command steps). Whether a failure loses
        the episode is the driver's call (section 7.2).
        """
        env = self.env
        started = time.monotonic()
        env._set_task_info(self.task)
        env.setup_controller.reset_cache_dir(env.cache_dir)
        mark = self.mark()
        first = self.begin_phase("setup")
        try:
            ok = env.setup_controller.setup(env.config, False)
        except Exception as exc:
            self.check_transport("setup", mark, exc)
            raise
        finally:
            self.step_state["phase"] = None
        self.check_transport("setup", mark)
        if not ok:
            raise RuntimeError("setup controller could not reach the guest server")
        if env.config:
            env.is_environment_used = True
        replies = self.replies_since(first)
        return {
            "seconds": round(time.monotonic() - started, 3),
            "steps": len(env.config),
            "config_steps": config_steps(env.config),
            "replies": replies,
            "failures": [describe_reply(r) for r in replies if setup_reply_failed(r)],
        }

    def probe_postconfig(self) -> dict[str, Any]:
        """G0 item 5's second pass only: the task's postconfig steps on the untouched initial
        state, with every reply recorded. No getter and no metric runs, so no verdict exists.
        A step that raises is recorded, not raised; a transport failure raises."""
        env = self.env
        postconfig = list((env.evaluator or {}).get("postconfig", []))
        started = time.monotonic()
        mark = self.mark()
        first = self.begin_phase("postconfig_probe")
        out: dict[str, Any] = {"steps": len(postconfig), "config_steps": config_steps(postconfig)}
        try:
            env.setup_controller.setup(postconfig, False)
        except Exception as exc:  # noqa: BLE001 - recorded; a transport failure raises below
            self.check_transport("postconfig_probe", mark, exc)
            out["error"] = f"{type(exc).__name__}: {exc}"[:500]
        finally:
            self.step_state["phase"] = None
        self.check_transport("postconfig_probe", mark)
        replies = self.replies_since(first)
        out.update(
            seconds=round(time.monotonic() - started, 3),
            replies=replies,
            failures=[describe_reply(r) for r in replies if setup_reply_failed(r)],
        )
        return out

    def evaluate(self, last_action: str | None) -> Any:
        """The pinned ``DesktopEnv.evaluate()`` with the episode's last action in history.

        Raises ``TransportFailure`` when any guest request of the evaluation (postconfig,
        getters) failed in transport, whatever ``evaluate()`` returned or raised. The
        postconfig's ``/setup/*`` replies are kept in ``evaluate_replies``.
        """
        self.env.action_history = [last_action] if last_action is not None else []
        mark = self.mark()
        first = self.begin_phase("evaluate")
        try:
            score = self.env.evaluate()
        except Exception as exc:
            self.check_transport("evaluate", mark, exc)
            raise
        finally:
            self.step_state["phase"] = None
            self.evaluate_replies = self.replies_since(first)
        self.check_transport("evaluate", mark)
        return score

    def capture_sweep(self) -> list[dict[str, Any]]:
        """Call every result getter once more (the captured state then holds every input);
        a transport failure during the sweep raises ``TransportFailure``."""
        env = self.env
        evaluator = env.evaluator
        results = evaluator.get("result")
        getters = env.result_getter
        configs = results if isinstance(results, list) else [results]
        functions = getters if isinstance(getters, list) else [getters]
        out = []
        mark = self.mark()
        for config, getter in zip(configs, functions, strict=False):
            if getter is None or not config:
                continue
            try:
                getter(env, config)
                out.append({"type": config.get("type"), "ok": True})
            except TransportFailure:
                raise
            except Exception as exc:  # noqa: BLE001 - a getter that fails on agent state
                self.check_transport("capture_sweep", mark, exc)
                out.append({"type": config.get("type"), "ok": False, "error": str(exc)[:200]})
        self.check_transport("capture_sweep", mark)
        return out

    def write_capture(self, capture_dir: Path) -> dict[str, Any]:
        """Copy the files the checker read and the task cache off the VM; hash both."""
        controller = self.env.controller
        vm_root = capture_dir / "vm"
        files = {}
        for path, data in sorted(controller.blobs.items()):
            target = vm_root / path.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            files[path] = hashlib.sha256(data).hexdigest()
        cache = {}
        cache_dir = Path(self.env.cache_dir)
        if cache_dir.is_dir():
            for item in sorted(cache_dir.rglob("*")):
                if item.is_file():
                    rel = item.relative_to(cache_dir).as_posix()
                    target = capture_dir / "cache" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(item, target)
                    cache[rel] = hashlib.sha256(item.read_bytes()).hexdigest()
        manifest = {
            "schema": "q2-stage1a-capture-v1",
            "task_id": self.task["id"],
            "vm_files": files,
            "cache_files": cache,
            "reads": [read.__dict__ for read in controller.reads],
            "file_cache_urls": sorted(set(self.fetched)),
            "action_history": list(self.env.action_history),
            "guest_request_errors": list(self.guest_errors),
            "setup_replies": list(self.setup_replies),
        }
        manifest["state_sha256"] = hashlib.sha256(
            json.dumps({"vm": files, "cache": cache}, sort_keys=True).encode()
        ).hexdigest()
        (capture_dir / "capture.json").write_text(
            json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8"
        )
        return manifest

    def close(self) -> None:
        self.restore()


def config_steps(steps: Any) -> list[dict[str, Any]]:
    """Each setup or postconfig step's type and, for command steps, its argv (truncated):
    what rule (a) of section 5.4 (a software install from the network) reads."""
    out = []
    for index, step in enumerate(steps or [], start=1):
        kind = str((step or {}).get("type"))
        row: dict[str, Any] = {"step": index, "type": kind}
        params = (step or {}).get("parameters") or {}
        if kind in ARGV_STEP_TYPES and "command" in params:
            command = params["command"]
            row["argv"] = (
                [str(a)[:300] for a in command][:40]
                if isinstance(command, list)
                else str(command)[:600]
            )
            row["shell"] = bool(params.get("shell"))
        out.append(row)
    return out


def is_transport_error(exc: BaseException) -> bool:
    """Whether an exception out of setup or evaluate is the transport to the guest failing.

    The pinned ``SetupController.setup`` re-raises a failed step as a bare
    ``Exception(...) from e`` (and ``_open_setup`` wraps its own), so the whole
    ``__cause__``/``__context__`` chain is read, not only the top-level type.
    """
    try:
        import requests

        transport: tuple[type[BaseException], ...] = (
            TransportFailure,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        )
    except ImportError:  # pragma: no cover - the metric image has requests
        transport = (TransportFailure,)
    seen: set[int] = set()
    stack: list[BaseException] = [exc]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, transport):
            return True
        stack += [e for e in (current.__cause__, current.__context__) if e is not None]
    return False


def is_offline_refusal(exc: BaseException) -> bool:
    """Whether a checker asked for a URL the offline run cannot serve (neither the guest nor
    the pinned file cache): an ``OfflineNetworkRefused`` anywhere in the exception chain."""
    seen: set[int] = set()
    stack: list[BaseException] = [exc]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if type(current).__name__ == "OfflineNetworkRefused":
            return True
        stack += [e for e in (current.__cause__, current.__context__) if e is not None]
    return False


def load_task(osworld_dir: str, task_id: str) -> dict[str, Any]:
    examples = Path(osworld_dir) / "evaluation_examples" / "examples"
    matches = list(examples.glob(f"*/{task_id}.json"))
    if len(matches) != 1:
        raise FileNotFoundError(f"task {task_id}: {len(matches)} config files")
    return json.loads(matches[0].read_text(encoding="utf-8"))


def env_flags() -> dict[str, str]:
    """What the runner records about its environment (no secrets)."""
    return {"python": sys.version.split()[0], "executable": sys.executable, "pid": str(os.getpid())}
