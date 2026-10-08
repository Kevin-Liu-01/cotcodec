"""The S1a episode runner end to end against a fake guest, engine and OSWorld session."""

from __future__ import annotations

import base64
import http.server
import io
import json
import socketserver
import tempfile
import threading
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
    """The OSWorld guest server's endpoints the runner uses, over TCP on 127.0.0.1."""

    def __init__(self) -> None:
        self.shots = 0
        self.commands: list[list[str]] = []
        self.fail_screenshots = False
        self.executor_rc = 0
        self.warmup_pid = 4242
        self.pids = [4242]
        self.pid_calls = 0
        self.warmup_ok = True
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

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/screenshot":
                    if guest.fail_screenshots:
                        self.reply(500, b"no")
                        return
                    guest.shots += 1
                    self.reply(200, png(guest.shots), "image/png")
                else:
                    self.reply(404, b"{}")

            def do_POST(self) -> None:  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                argv = body["command"]
                guest.commands.append(argv)
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
                    "error": "" if self.executor_rc == 0 else "device"}  # fmt: skip
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
        **overrides: Any) -> tuple[dict[str, Any], Path, FakeSession]:  # fmt: skip
    base = Path(tempfile.mkdtemp(prefix="s1a", dir="/tmp"))
    sock = str(base / "e.sock")
    session = session or FakeSession()
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
            session_factory=lambda c, t: session,
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
