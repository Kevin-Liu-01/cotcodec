"""The S1a episode runner end to end against a fake guest, engine and OSWorld session."""

from __future__ import annotations

import base64
import http.server
import io
import json
import socketserver
import sys
import tempfile
import textwrap
import threading
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

from harness.q2.vm import desktop
from harness.q2.vm.guest_http import GuestClient
from harness.q2_stage1 import agents, driver
from harness.q2_stage1.fake_engine import FakeEngine
from harness.q2_stage1.records import validate


def png(shade: int) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (1920, 1080), (shade % 256, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeGuest:
    """The OSWorld guest server's endpoints the runner uses, over TCP on 127.0.0.1.

    ``drop`` names paths whose requests are answered by closing the connection (the client
    sees a reset, a ``requests`` ``ConnectionError``); ``drop_execute`` does the same for
    the ``/execute`` commands it matches; ``files`` is what ``/file`` serves.
    """

    def __init__(self) -> None:
        self.shots = 0
        self.commands: list[list[str]] = []
        self.fail_screenshots = False
        self.executor_rc = 0
        self.executor_error = "device"
        self.warmup_pid = 4242
        self.pids = [4242]
        self.pid_calls = 0
        self.warmup_ok = True
        self.drop: set[str] = set()
        self.drop_execute: Any = None
        self.files: dict[str, bytes] = {}
        self.setup_calls: list[str] = []
        self._server: socketserver.TCPServer | None = None

    def start(self) -> FakeGuest:
        guest = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                return None

            def reply(self, status: int, body: bytes, ctype: str = "application/json") -> None:
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def hang_up(self) -> None:
                self.close_connection = True  # no reply: the client sees the reset

            def do_GET(self) -> None:  # noqa: N802
                if self.path in guest.drop:
                    self.hang_up()
                elif self.path == "/screenshot":
                    if guest.fail_screenshots:
                        self.reply(500, b"no")
                        return
                    guest.shots += 1
                    self.reply(200, png(guest.shots), "image/png")
                elif self.path == "/terminal":
                    self.reply(200, b'{"output": ""}')
                else:
                    self.reply(404, b"{}")

            def do_POST(self) -> None:  # noqa: N802
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                if self.path in guest.drop:
                    self.hang_up()
                    return
                if self.path == "/file":
                    form = urllib.parse.parse_qs(raw.decode())
                    data = guest.files.get(form["file_path"][0])
                    if data is None:
                        self.reply(404, b"file not found")
                    else:
                        self.reply(200, data, "application/octet-stream")
                    return
                if self.path.startswith("/setup/"):
                    guest.setup_calls.append(self.path)
                    out = {"status": "success", "output": "ok\n", "error": "", "returncode": 0}
                    self.reply(200, json.dumps(out).encode())
                    return
                argv = json.loads(raw)["command"]
                guest.commands.append(argv)
                if guest.drop_execute is not None and guest.drop_execute(argv):
                    self.hang_up()
                    return
                self.reply(200, json.dumps(guest.execute(argv)).encode())

        class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
            daemon_threads = True
            allow_reuse_address = True

        self._server = Server(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def execute(self, argv: list[str]) -> dict[str, Any]:
        ok = {"status": "success", "error": "", "returncode": 0}
        if argv[0] == "python3" and len(argv) >= 4:
            source = base64.b64decode(argv[3]).decode()
            if "warm_up" in source:
                if not self.warmup_ok:
                    return {**ok, "output": json.dumps({"error": "no xtest"})}
                out = {"keycode": 250, "shell": {"idle": True}, "server_pid": self.warmup_pid}
                return {**ok, "output": json.dumps(out)}
            if "server_pid" in source:
                pid = self.pids[min(self.pid_calls, len(self.pids) - 1)]
                self.pid_calls += 1
                return {**ok, "output": json.dumps({"server_pid": pid})}
        if argv[0] == "cat":
            return {**ok, "output": "0::/system.slice/osworld.service\n"}
        if argv[0] == "systemctl":
            return {**ok, "output": "0\n"}
        if argv[0] == "python" and argv[1] == "-c":
            return {**ok, "output": "{}", "returncode": self.executor_rc,
                    "error": "" if self.executor_rc == 0 else self.executor_error}  # fmt: skip
        return {**ok, "output": ""}

    def executor_commands(self) -> list[list[str]]:
        return [c for c in self.commands if c[0] == "python" and "q2ap_l0" in c[2]]


class FakeSession:
    def __init__(self, score: Any = 1.0, setup_error: Exception | None = None,
                 evaluate_error: Exception | None = None):  # fmt: skip
        self.score = score
        self.setup_error = setup_error
        self.evaluate_error = evaluate_error
        self.last_action: Any = "unset"
        self.closed = False

    def setup(self) -> dict[str, Any]:
        if self.setup_error:
            raise self.setup_error
        return {"seconds": 0.1, "steps": 2}

    def evaluate(self, last_action: str | None) -> Any:
        self.last_action = last_action
        if self.evaluate_error:
            raise self.evaluate_error
        return self.score

    def capture_sweep(self) -> list[dict[str, Any]]:
        return [{"type": "vm_file", "ok": True}]

    def write_capture(self, capture_dir: Path) -> dict[str, Any]:
        capture_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"vm_files": {"/home/user/a.pptx": "ab" * 32}, "state_sha256": "cd" * 32}
        (capture_dir / "capture.json").write_text(json.dumps(manifest))
        return manifest

    def close(self) -> None:
        self.closed = True


def call(action: str, **params: Any) -> str:
    body = "".join(f"<parameter={k}>\n{v}\n</parameter>\n" for k, v in params.items())
    return (
        "<think>\nok\n</think>\n\nAction: go.\n<tool_call>\n<function=computer_use>\n"
        f"<parameter=action>\n{action}\n</parameter>\n{body}</function>\n</tool_call>"
    )


CLICK = call("left_click", coordinate="[500, 500]")
DONE = call("terminate", status="success")
GIVE_UP = call("terminate", status="failure")


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    monkeypatch.setattr(desktop, "RETRY_INTERVAL_S", 0.0)


@pytest.fixture
def guest():
    fake = FakeGuest().start()
    yield fake
    fake.stop()


def run(guest: FakeGuest, replies: list[Any], session: FakeSession | None = None,
        _factory: Any = None,
        **overrides: Any) -> tuple[dict[str, Any], Path, FakeSession]:  # fmt: skip
    base = Path(tempfile.mkdtemp(prefix="s1a", dir="/tmp"))
    sock = str(base / "e.sock")
    session = session or FakeSession()
    factory = _factory or (lambda c, t: session)
    cfg = driver.EpisodeConfig(
        job="A1-9B-S1", size="9B", session="S1", task_id="t-1", harness="H-OSW-fixed",
        rerun=1, attempt=1, extension_block=None, block="b1", slot="S1:9B:b1:0",
        out_dir=str(base / "out"), guest_ip="127.0.0.1", server_port=guest.port,
        engine_socket=sock, settle_after_reset_s=0, settle_before_eval_s=0, boot_timeout_s=0.5,
        date="2026-10-08", certified_keysyms=["Return"],
    )  # fmt: skip
    for key, value in overrides.items():
        setattr(cfg, key, value)
    with FakeEngine(sock, {"replies": replies}) as fake_engine:
        runner = driver.Runner(
            cfg,
            guest=GuestClient("127.0.0.1", guest.port),
            session_factory=factory,
            client_factory=agents.make_client,
            task={"id": "t-1", "instruction": "Do it."},
            sleep=lambda s: None,
        )
        record = runner.run()
        record["_engine_requests"] = len(fake_engine.requests)
    return record, base / "out", session


def test_hosw_episode_scored_with_done_and_logged(guest):
    record, out, session = run(guest, [CLICK, DONE])
    assert record["status"] == "scored" and record["score"] == 1.0
    assert record["steps"] == 2 and record["ended"] == "terminate_success"
    assert session.last_action == "DONE" and session.closed
    assert len(guest.executor_commands()) == 1
    steps = [json.loads(line) for line in (out / "steps.jsonl").read_text().splitlines()]
    assert [s["step"] for s in steps] == [1, 2]
    assert steps[0]["ir"][0]["op"] == "click" and steps[0]["prompt_sha256"]
    assert steps[1]["terminated"] == "success"
    assert (out / "capture" / "capture.json").exists()
    assert record["warmup"]["keycode"] == 250
    assert record["server_start"]["unit"] == "osworld.service"
    assert record["date_line"] == "Thursday, October 08, 2026"
    saved = json.loads((out / "episode.json").read_text())
    validate(saved)


def test_failure_terminate_puts_fail_in_the_checker_history(guest):
    record, _, session = run(guest, [GIVE_UP], harness="H-GA")
    assert session.last_action == "FAIL" and record["ended"] == "terminate_failure"
    assert record["status"] == "scored"


def test_step_cap_and_last_command_in_history(guest):
    record, _, session = run(guest, [CLICK], step_cap=3)
    assert record["steps"] == 3 and record["ended"] == "step_cap"
    assert session.last_action.startswith("import base64 as _q2b")


def test_no_action_turns_follow_each_harness(guest):
    for harness, same in (("H-OSW-fixed", True), ("H-GA", False)):
        _, out, _ = run(guest, ["nothing parseable here", DONE], harness=harness)
        steps = [json.loads(line) for line in (out / "steps.jsonl").read_text().splitlines()]
        if harness == "H-GA":
            assert steps[0]["ir"] == [{"op": "wait", "ms": 1000}]  # the parser's own wait
            assert steps[0]["executed"]
            continue
        assert steps[0]["ir"] == [] and not steps[0]["executed"]
        assert (steps[0]["screenshot_sha256"] == steps[1]["screenshot_sha256"]) is same


def test_hga_empty_turn_gets_a_fresh_capture(guest):
    hscroll = call("hscroll", pixels="3")  # H-GA has no hscroll: no action, an Action: line
    _, out, _ = run(guest, [hscroll, DONE], harness="H-GA")
    steps = [json.loads(line) for line in (out / "steps.jsonl").read_text().splitlines()]
    assert steps[0]["ir"] == [] and not steps[0]["executed"]
    assert steps[0]["screenshot_sha256"] != steps[1]["screenshot_sha256"]


def test_ir_errors_truncation_and_exposure_are_counted(guest):
    bad_key = call("key", keys='["nosuchkey"]')
    enter = call("key", keys='["ctrl", "s"]')
    truncated = {"text": "<think>loop", "finish_reason": "length", "completion_tokens": 2048}
    record, _, _ = run(guest, [bad_key, truncated, enter, DONE])
    assert record["ir_errors"] == 1 and record["truncated_steps"] == 1
    assert record["uncertified_key_actions"] == 1  # Control_L and s are outside {"Return"}
    assert record["status"] == "scored"


def test_engine_failure_is_an_infrastructure_loss(guest, monkeypatch):
    import harness.q2_stage1.engine as engine_module

    monkeypatch.setattr(engine_module.time, "sleep", lambda s: None)
    record, _, session = run(guest, [{"status": 500}])
    assert record["status"] == "infrastructure"
    assert record["infrastructure_type"] == "engine_request"
    assert session.last_action == "unset"  # no checker ran
    validate(record)


def test_setup_failure_and_boot_failure(guest):
    record, _, _ = run(guest, [DONE], session=FakeSession(setup_error=RuntimeError("upload")))
    assert record["infrastructure_type"] == "task_setup"
    guest.fail_screenshots = True
    record, _, _ = run(guest, [DONE])
    assert record["infrastructure_type"] == "vm_boot"


def test_executor_device_failure_and_failed_warmup(guest):
    guest.executor_rc = 1
    record, _, _ = run(guest, [CLICK, DONE])
    assert record["infrastructure_type"] == "executor_device"
    guest.executor_rc = 0
    guest.warmup_ok = False
    record, _, _ = run(guest, [CLICK, DONE])
    assert record["infrastructure_type"] == "executor_device"
    assert record["_engine_requests"] == 0


def test_guest_server_restart_voids_the_episode(guest):
    guest.pids = [4243]  # the server that answers after the episode is another process
    record, _, session = run(guest, [DONE])
    assert record["infrastructure_type"] == "guest_server_restart"
    assert session.last_action == "unset"


def test_transport_loss_behind_a_server_restart_counts_as_a_restart(guest):
    import requests

    session = FakeSession(evaluate_error=requests.exceptions.ConnectionError("reset"))
    # The check before evaluation sees the same server; after the failure, another one answers.
    guest.pids = [4242, 4243]
    record, _, _ = run(guest, [DONE], session=session)
    assert record["infrastructure_type"] == "guest_server_restart"
    assert record["server_end"]["server_pid"] == 4242
    assert record["server_after_loss"]["server_pid"] == 4243


def test_metric_exception_scores_zero_but_transport_is_a_loss(guest):
    record, _, _ = run(guest, [DONE], session=FakeSession(evaluate_error=KeyError("sheet")))
    assert record["status"] == "scored" and record["score"] == 0.0
    assert record["metric_exception"] and "KeyError" in record["metric_error"]
    import requests

    session = FakeSession(evaluate_error=requests.exceptions.ConnectionError("reset"))
    record, _, _ = run(guest, [DONE], session=session)
    assert record["infrastructure_type"] == "transport"
    record, _, _ = run(guest, [DONE], session=FakeSession(score=None))
    assert record["metric_exception"] and record["score"] == 0.0


def test_setup_only_mode_runs_no_model(guest):
    record, _, _ = run(guest, [DONE], mode="setup-only")
    assert record["status"] == "setup_ok" and record["_engine_requests"] == 0
    assert record["server_start"]["server_pid"] == 4242
    assert not guest.executor_commands()
    record, _, _ = run(guest, [DONE], mode="setup-only",
                       session=FakeSession(setup_error=ValueError("x")))  # fmt: skip
    assert record["status"] == "setup_failed" and record["infrastructure_type"] == "task_setup"


def test_slow_but_answered_execute_is_not_a_loss():
    rec = {"execute": {"ok": True, "attempts": [{"status": 200, "elapsed_s": 45.0}]},
           "screenshot_ok": True}  # fmt: skip
    assert driver.step_losses(rec) == [] and driver.slow_execute(rec)
    retried = {"execute": {"ok": True, "attempts": [{"error": "reset"}, {"status": 200}]},
               "screenshot_ok": True}  # fmt: skip
    assert driver.step_losses(retried) == ["execute"]


def test_config_rejects_unknown_keys():
    with pytest.raises(ValueError, match="unknown episode config keys"):
        driver.EpisodeConfig.from_json({"job": "x", "bogus": 1})


# --------------------------------------------------------------------------- live OSWorld path
# A stand-in ``desktop_env`` package whose error handling follows the pinned OSWorld
# ``b138d348`` code the runner calls: ``SetupController.setup`` probes ``/terminal`` with a
# bare ``except`` and re-raises a failed step as ``Exception(...) from e``;
# ``_execute_setup`` logs a ``RequestException`` and goes on; ``_open_setup`` wraps one in
# ``Exception``; ``get_vm_file`` catches any exception from ``controller.get_file`` and
# returns None; ``get_cache_file`` asserts the cached file exists; ``DesktopEnv.evaluate``
# runs the postconfig, ignores what ``setup`` returns, applies the FAIL rule and calls the
# getter and the metric.

FAKE_OSWORLD = {
    "desktop_env/__init__.py": "",
    "desktop_env/controllers/__init__.py": "",
    "desktop_env/controllers/python.py": """
        class PythonController:
            def __init__(self, vm_ip, server_port=5000):
                self.vm_ip = vm_ip
                self.http_server = f"http://{vm_ip}:{server_port}"
    """,
    "desktop_env/controllers/setup.py": """
        import json
        import os

        import requests

        MAX_RETRIES = 2


        class SetupController:
            def __init__(self, vm_ip, server_port=5000, chromium_port=9222, vlc_port=8080,
                         cache_dir="cache", client_password="", screen_width=1920,
                         screen_height=1080):
                self.http_server = f"http://{vm_ip}:{server_port}"
                self.cache_dir = cache_dir

            def reset_cache_dir(self, cache_dir):
                self.cache_dir = cache_dir

            def setup(self, config, use_proxy=False):
                retry = 0
                while retry < MAX_RETRIES:
                    try:
                        requests.get(self.http_server + "/terminal")
                        break
                    except:  # noqa: E722 - as the pinned code
                        retry += 1
                    if retry == MAX_RETRIES:
                        return False
                for i, cfg in enumerate(config):
                    name = "_{}_setup".format(cfg["type"])
                    try:
                        getattr(self, name)(**cfg["parameters"])
                    except Exception as e:
                        raise Exception(f"Setup step {i + 1} failed: {name} - {e}") from e
                return True

            def _execute_setup(self, command, stdout="", stderr="", shell=False, until=None):
                payload = json.dumps({"command": command, "shell": shell})
                headers = {"Content-Type": "application/json"}
                try:
                    response = requests.post(self.http_server + "/setup/execute",
                                             headers=headers, data=payload)
                    if response.status_code == 200 and stdout:
                        with open(os.path.join(self.cache_dir, stdout), "w") as f:
                            f.write(response.json()["output"])
                except requests.exceptions.RequestException:
                    pass  # logged and ignored upstream

            def _open_setup(self, path):
                payload = json.dumps({"path": path})
                try:
                    response = requests.post(self.http_server + "/setup/open_file",
                                             data=payload, timeout=1810)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    raise Exception(f"Failed to open file '{path}': {e}") from e
    """,
    "desktop_env/evaluators/__init__.py": "",
    "desktop_env/evaluators/getters/__init__.py": """
        import os


        def get_vm_file(env, config):
            path = os.path.join(env.cache_dir, config["dest"])
            try:
                data = env.controller.get_file(config["path"])
                if data is None:
                    return None
                with open(path, "wb") as f:
                    f.write(data)
            except Exception:
                return None
            return path


        def get_cache_file(env, config):
            path = os.path.join(env.cache_dir, config["path"])
            assert os.path.exists(path)
            return path
    """,
    "desktop_env/evaluators/metrics/__init__.py": """
        def check_text(path, **options):
            if path is None:
                return 0.0
            with open(path, "rb") as f:
                return 1.0 if f.read().strip() in (b"good", b"ok") else 0.0
    """,
    "desktop_env/desktop_env.py": """
        import os

        from desktop_env.evaluators import getters, metrics


        class DesktopEnv:
            def _set_task_info(self, task_config):
                self.task_id = task_config["id"]
                self.cache_dir = os.path.join(self.cache_dir_base, self.task_id)
                os.makedirs(self.cache_dir, exist_ok=True)
                self.instruction = task_config["instruction"]
                self.config = task_config.get("config", [])
                self.evaluator = task_config["evaluator"]
                self.metric = getattr(metrics, self.evaluator["func"])
                self.metric_conj = self.evaluator.get("conj", "and")
                self.result_getter = getattr(
                    getters, "get_{}".format(self.evaluator["result"]["type"]))
                self.expected_getter = None
                self.metric_options = self.evaluator.get("options", {})

            def evaluate(self):
                postconfig = self.evaluator.get("postconfig", [])
                self.setup_controller.setup(postconfig, self.enable_proxy)
                if self.action_history and self.action_history[-1] == "FAIL":
                    return 0
                try:
                    result_state = self.result_getter(self, self.evaluator["result"])
                except FileNotFoundError:
                    return 0
                return self.metric(result_state, **self.metric_options)
    """,
}

VM_FILE_TASK = {
    "id": "t-1",
    "instruction": "Do it.",
    "config": [{"type": "execute", "parameters": {"command": ["true"]}}],
    "evaluator": {
        "func": "check_text",
        "result": {"type": "vm_file", "path": "/home/user/out.txt", "dest": "out.txt"},
    },
}
POSTCONFIG_TASK = {
    "id": "t-1",
    "instruction": "Do it.",
    "config": [],
    "evaluator": {
        "postconfig": [
            {"type": "execute", "parameters": {"command": ["cat", "x"], "stdout": "out.txt"}}
        ],
        "func": "check_text",
        "result": {"type": "cache_file", "path": "out.txt"},
    },
}


@pytest.fixture
def osworld(tmp_path, monkeypatch):
    """The stand-in package on sys.path; ``requests`` and the module table restored after."""
    import requests

    from harness.q2_stage1 import osworld_live

    root = tmp_path / "OSWorld"
    for rel, text in FAKE_OSWORLD.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text))
    monkeypatch.setattr(osworld_live, "GET_FILE_INTERVAL_S", 0.0)
    real = (requests.get, requests.post)
    stale = [m for m in sys.modules if m == "desktop_env" or m.startswith("desktop_env.")]
    for name in stale:
        monkeypatch.delitem(sys.modules, name)
    yield root
    requests.get, requests.post = real
    for name in [m for m in sys.modules if m == "desktop_env" or m.startswith("desktop_env.")]:
        del sys.modules[name]
    while str(root) in sys.path:
        sys.path.remove(str(root))


def live(guest: FakeGuest, task: dict[str, Any], osworld: Path, tmp_path: Path, before=None):
    """A session factory for the real ``LiveTask`` against the fake guest; ``before`` runs
    just before ``evaluate`` (to break the guest after the agent's steps)."""
    from harness.q2_stage1.osworld_live import LiveTask

    holder: dict[str, Any] = {}

    def factory(cfg, t):
        session = LiveTask(task, osworld_dir=str(osworld), file_cache=tmp_path / "files",
                           guest_ip="127.0.0.1", server_port=guest.port,
                           cache_root=tmp_path / "cache")  # fmt: skip
        if before is not None:
            evaluate = session.evaluate

            def wrapped(last_action):
                before()
                return evaluate(last_action)

            session.evaluate = wrapped
        holder["session"] = session
        return session

    return factory, holder


def run_live(guest, task, osworld, tmp_path, before=None, replies=None):
    factory, holder = live(guest, task, osworld, tmp_path, before)
    record, out, _ = run(guest, replies or [DONE], session=None, _factory=factory)
    return record, out, holder["session"]


def test_live_path_scores_a_healthy_episode(guest, osworld, tmp_path):
    guest.files["/home/user/out.txt"] = b"good"
    record, out, session = run_live(guest, VM_FILE_TASK, osworld, tmp_path)
    assert record["status"] == "scored" and record["score"] == 1.0
    assert not session.guest_errors and record["server_final"]["server_pid"] == 4242
    capture = json.loads((out / "capture" / "capture.json").read_text())
    assert capture["vm_files"] and capture["guest_request_errors"] == []


def test_vm_file_getter_that_swallows_a_dead_guest_is_a_transport_loss(guest, osworld, tmp_path):
    """OSWorld's ``get_vm_file`` catches the ``TransportFailure`` and returns None, so the
    metric scores 0; the episode is still a transport loss (section 7.2)."""
    guest.files["/home/user/out.txt"] = b"good"
    record, _, session = run_live(
        guest, VM_FILE_TASK, osworld, tmp_path, before=lambda: guest.drop.add("/file")
    )
    assert record["status"] == "infrastructure"
    assert record["infrastructure_type"] == "transport" and record["score"] is None
    assert "POST /file: ConnectionError" in record["infrastructure_detail"]
    assert len(session.guest_errors) == 3  # OSWorld's three attempts, each a reset
    assert any("get_file(/home/user/out.txt): no answer" in f
               for f in session.transport["evaluate"])  # fmt: skip
    validate(record)


def test_a_guest_that_stops_answering_during_evaluation_is_a_transport_loss(
    guest, osworld, tmp_path
):
    guest.files["/home/user/out.txt"] = b"good"

    def die():
        guest.drop.update({"/file", "/terminal", "/setup/execute"})
        guest.drop_execute = lambda argv: True

    record, _, _ = run_live(guest, VM_FILE_TASK, osworld, tmp_path, before=die)
    assert record["status"] == "infrastructure" and record["infrastructure_type"] == "transport"
    assert "error" in record["server_after_loss"]  # the restart check could not reach it


def test_swallowed_postconfig_connection_error_is_a_transport_loss(guest, osworld, tmp_path):
    """``_execute_setup`` swallows the reset, ``get_cache_file``'s assert then raises: that
    would be a metric exception scored 0, but the transport failed first."""
    record, _, _ = run_live(
        guest, POSTCONFIG_TASK, osworld, tmp_path,
        before=lambda: guest.drop.add("/setup/execute"),
    )  # fmt: skip
    assert record["status"] == "infrastructure" and record["infrastructure_type"] == "transport"
    assert not record["metric_exception"]
    guest.drop.clear()
    healthy, _, _ = run_live(guest, POSTCONFIG_TASK, osworld, tmp_path / "again")
    assert healthy["status"] == "scored" and healthy["score"] == 1.0


def test_wrapped_postconfig_connection_error_is_a_transport_loss(guest, osworld, tmp_path):
    task = json.loads(json.dumps(POSTCONFIG_TASK))
    task["evaluator"]["postconfig"] = [{"type": "open", "parameters": {"path": "/home/x"}}]
    record, _, _ = run_live(
        guest, task, osworld, tmp_path, before=lambda: guest.drop.add("/setup/open_file")
    )
    assert record["status"] == "infrastructure" and record["infrastructure_type"] == "transport"


def test_transport_failure_during_task_setup_is_a_setup_loss(guest, osworld, tmp_path):
    guest.drop.add("/setup/execute")
    record, _, _ = run_live(guest, VM_FILE_TASK, osworld, tmp_path)
    assert record["infrastructure_type"] == "task_setup"
    assert "TransportFailure" in record["infrastructure_detail"]


def test_is_transport_error_reads_the_cause_chain():
    import requests

    from harness.q2_stage1.osworld_live import TransportFailure, is_transport_error

    def wrapped(inner: BaseException) -> Exception:
        try:
            try:
                raise inner
            except Exception as e:
                raise Exception("Failed to open file") from e
        except Exception as e:
            try:
                raise Exception("Setup step 1 failed: _open_setup") from e
            except Exception as outer:
                return outer

    assert is_transport_error(wrapped(requests.exceptions.ConnectionError("reset")))
    assert is_transport_error(wrapped(requests.exceptions.ReadTimeout("slow")))
    assert is_transport_error(wrapped(TransportFailure("x")))
    assert not is_transport_error(wrapped(KeyError("sheet")))
    assert not is_transport_error(wrapped(requests.exceptions.HTTPError("404")))


def test_restart_during_evaluation_or_capture_is_caught_after_the_capture(guest):
    guest.pids = [4242, 4243]  # the check before evaluation sees 4242, the one after 4243
    record, out, session = run(guest, [DONE])
    assert record["infrastructure_type"] == "guest_server_restart"
    assert session.last_action == "DONE"  # evaluated and captured, then voided
    assert record["server_final"]["server_pid"] == 4243
    assert (out / "capture" / "capture.json").exists()


def test_a_restart_check_that_cannot_reach_the_server_is_a_transport_loss(guest):
    def identity(argv):
        source = base64.b64decode(argv[3]).decode() if argv[0] == "python3" else ""
        return source == driver.SERVER_PID_SCRIPT

    guest.drop_execute = identity
    record, _, session = run(guest, [DONE])
    assert record["infrastructure_type"] == "transport"
    assert "identity at server_end" in record["infrastructure_detail"]
    assert session.last_action == "unset"  # no checker ran on an unverified server
    guest.drop_execute = lambda argv: argv[0] == "cat"  # the warm-up's own identity
    record, _, _ = run(guest, [DONE])
    assert record["infrastructure_type"] == "transport"
    assert "identity at warm-up" in record["infrastructure_detail"]
