"""S1a engine client, fake engine and bridge (registration section 3.1 items 3-4)."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from harness.q2_stage1 import bridge, engine
from harness.q2_stage1.fake_engine import FakeEngine, fake_prompt_ids

ROOT = Path(__file__).resolve().parents[1]
SAMPLING = {"temperature": 0.0, "top_p": 0.9, "top_k": -1, "max_tokens": 2048}
MESSAGES = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]


def short_dir(tmp_path: Path) -> Path:
    """AF_UNIX paths are limited to about 100 bytes; pytest's tmp paths can be longer."""
    import tempfile

    return Path(tempfile.mkdtemp(prefix="s1a", dir="/tmp"))


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_streamed_completion_carries_usage_digest_and_timings(tmp_path):
    sock = str(short_dir(tmp_path) / "e.sock")
    reply = {"text": "Action: x\n<tool_call>\n</tool_call>", "completion_tokens": 7}
    with FakeEngine(sock, {"replies": [reply]}) as fake:
        client = engine.EngineClient(sock, "s1a-model")
        out = client.chat(MESSAGES, SAMPLING)
    assert out.content == reply["text"]
    assert out.finish_reason == "stop"
    assert out.completion_tokens == 7 and out.prompt_tokens > 0
    assert out.prompt_ids_sha256 == engine.token_ids_sha256(fake_prompt_ids(MESSAGES))
    assert out.prompt_id_count == 16
    assert out.ttft_s is not None and out.latency_s >= out.ttft_s
    assert out.cached_tokens is None  # the card's flags report none
    sent = fake.requests[0]
    assert sent["sampling"] == SAMPLING
    assert sent["stream"] is True and sent["return_token_ids"] is True


def test_token_digest_matches_the_serving_probe_v2():
    import numpy as np

    ids = [1, 2, 300000, 7]
    expected = __import__("hashlib").sha256(np.asarray(ids, dtype="<i8").tobytes()).hexdigest()
    assert engine.token_ids_sha256(ids) == expected


def test_sampling_outside_the_registration_is_refused(tmp_path):
    client = engine.EngineClient("/nonexistent", "m")
    with pytest.raises(ValueError, match="outside the registration"):
        client.body(MESSAGES, {**SAMPLING, "repetition_penalty": 1.0})


def test_context_length_rejection_is_its_own_error(tmp_path):
    sock = str(short_dir(tmp_path) / "e.sock")
    script = {
        "replies": [
            {"status": 400, "message": "This model's maximum context length is 131072 tokens."}
        ]
    }
    with FakeEngine(sock, script):
        client = engine.EngineClient(sock, "m", sleep=lambda s: None)
        with pytest.raises(engine.ContextLengthError) as info:
            client.chat(MESSAGES, SAMPLING)
    assert info.value.kind == "context_length"
    assert len(info.value.attempts) == 1  # a 4xx is never retried


def test_other_4xx_is_a_bad_request_without_retry(tmp_path):
    sock = str(short_dir(tmp_path) / "e.sock")
    with FakeEngine(sock, {"replies": [{"status": 422, "message": "bad image"}]}):
        client = engine.EngineClient(sock, "m", sleep=lambda s: None)
        with pytest.raises(engine.EngineError) as info:
            client.chat(MESSAGES, SAMPLING)
    assert info.value.kind == "bad_request" and len(info.value.attempts) == 1


def test_server_errors_are_retried_with_osworld_backoff_then_fail(tmp_path):
    sock = str(short_dir(tmp_path) / "e.sock")
    slept: list[float] = []
    with FakeEngine(sock, {"replies": [{"status": 500}]}) as fake:
        client = engine.EngineClient(sock, "m", sleep=slept.append)
        with pytest.raises(engine.EngineError) as info:
            client.chat(MESSAGES, SAMPLING)
    assert info.value.kind == "transport"
    assert len(fake.requests) == engine.ATTEMPTS
    assert slept == [engine.backoff_s(a) for a in range(1, engine.ATTEMPTS)]
    assert slept == [5.0, 10.0, 15.0, 20.0]


def test_missing_socket_is_a_transport_failure(tmp_path):
    client = engine.EngineClient(str(short_dir(tmp_path) / "none.sock"), "m", sleep=lambda s: None)
    with pytest.raises(engine.EngineError) as info:
        client.chat(MESSAGES, SAMPLING)
    assert info.value.kind == "transport" and len(info.value.attempts) == engine.ATTEMPTS


def test_a_request_past_its_deadline_times_out_without_retry(tmp_path):
    sock = str(short_dir(tmp_path) / "e.sock")
    with FakeEngine(sock, {"replies": [{"text": "late", "sleep_s": 2.0}]}) as fake:
        client = engine.EngineClient(sock, "m", timeout_s=0.5, sleep=lambda s: None)
        with pytest.raises(engine.EngineError) as info:
            client.chat(MESSAGES, SAMPLING)
    assert info.value.kind == "timeout"
    assert len(fake.requests) == 1


def test_length_finish_and_stream_errors(tmp_path):
    sock = str(short_dir(tmp_path) / "e.sock")
    script = {
        "replies": [
            {"text": "<think>long", "finish_reason": "length", "completion_tokens": 2048},
            {"stream_error": "prompt is too long for the context window"},
        ]
    }
    with FakeEngine(sock, script):
        client = engine.EngineClient(sock, "m")
        first = client.chat(MESSAGES, SAMPLING)
        assert first.finish_reason == "length" and first.completion_tokens == 2048
        second = [*MESSAGES, {"role": "assistant", "content": [{"type": "text", "text": "a"}]}]
        with pytest.raises(engine.ContextLengthError):
            client.chat(second, SAMPLING)


def test_a_stream_cut_before_done_is_retried_then_a_transport_failure(tmp_path):
    sock = str(short_dir(tmp_path) / "e.sock")
    with FakeEngine(sock, {"replies": [{"cut_stream": True}]}) as fake:
        client = engine.EngineClient(sock, "m", sleep=lambda s: None)
        with pytest.raises(engine.EngineError) as info:
            client.chat(MESSAGES, SAMPLING)
    assert info.value.kind == "transport" and len(fake.requests) == engine.ATTEMPTS


def test_fake_engine_walks_its_script_by_assistant_turns(tmp_path):
    sock = str(short_dir(tmp_path) / "e.sock")
    with FakeEngine(sock, {"replies": ["one", "two"]}):
        client = engine.EngineClient(sock, "m")
        assert client.chat(MESSAGES, SAMPLING).content == "one"
        later = [*MESSAGES, {"role": "assistant", "content": "x"}, {"role": "user", "content": "y"}]
        assert client.chat(later, SAMPLING).content == "two"
        much_later = later + [{"role": "assistant", "content": "z"}]
        assert client.chat(much_later, SAMPLING).content == "two"


def test_forwarder_reaches_a_loopback_engine_only(tmp_path):
    port = free_port()
    sock = str(short_dir(tmp_path) / "fwd.sock")
    with FakeEngine(None, {"replies": ["through the bridge"]}, tcp_port=port):
        forwarder = bridge.Forwarder(sock, port).start()
        try:
            assert oct(os.stat(sock).st_mode & 0o777) == "0o600"
            out = engine.EngineClient(sock, "m").chat(MESSAGES, SAMPLING)
            assert out.content == "through the bridge"
            assert engine.health(sock)
        finally:
            forwarder.stop()
    assert not os.path.exists(sock)
    with pytest.raises(ValueError, match="loopback"):
        bridge.Forwarder(sock, port, host="10.0.0.1")


def _serve(bridge_dir: Path, port: int, script: Path, env: dict[str, str]) -> subprocess.Popen:
    argv = [sys.executable, "-m", "harness.q2_stage1.fake_engine", "--tcp-port", str(port),
            "--script", str(script)]  # fmt: skip
    return subprocess.Popen(
        [sys.executable, "-m", "harness.q2_stage1.bridge", "serve", "--bridge-dir",
         str(bridge_dir), "--engine-argv-json", json.dumps(argv), "--port", str(port),
         "--gpu-sample-s", "0", "--health-timeout-s", "30"],
        cwd=ROOT, env=env,
    )  # fmt: skip


def _wait_for(path: Path, seconds: float = 30.0) -> None:
    end = time.time() + seconds
    while not path.exists():
        if time.time() > end:
            raise AssertionError(f"{path} never appeared")
        time.sleep(0.1)


def test_serve_runs_engine_and_stops_on_vm_done(tmp_path):
    base = short_dir(tmp_path)
    script = base / "script.json"
    script.write_text(json.dumps({"replies": ["served"]}))
    port = free_port()
    proc = _serve(base / "bridge", port, script, dict(os.environ))
    try:
        _wait_for(base / "bridge" / bridge.READY_NAME)
        ready = json.loads((base / "bridge" / bridge.READY_NAME).read_text())
        assert ready["engine_bind"] == f"127.0.0.1:{port}" and ready["socket_mode"] == "0600"
        sock = str(base / "bridge" / bridge.SOCKET_NAME)
        assert engine.EngineClient(sock, "m").chat(MESSAGES, SAMPLING).content == "served"
        (base / "bridge" / bridge.DONE_NAME).write_text("done")
        assert proc.wait(30) == 0
    finally:
        proc.kill()
    stopped = json.loads((base / "bridge" / "stopped.json").read_text())
    assert stopped["stop_reason"] == "vm_done" and stopped["connections"] >= 1
    assert not (base / "bridge" / bridge.SOCKET_NAME).exists()


def test_serve_writes_usr1_and_the_lane_marker(tmp_path):
    base = short_dir(tmp_path)
    script = base / "script.json"
    script.write_text(json.dumps({"replies": ["x"]}))
    marker = base / "checkpoint.ready"
    env = dict(os.environ, COTCODEC_CHECKPOINT_MARKER=str(marker))
    proc = _serve(base / "bridge", free_port(), script, env)
    try:
        _wait_for(base / "bridge" / bridge.READY_NAME)
        proc.send_signal(signal.SIGUSR1)
        assert proc.wait(30) == 0
    finally:
        proc.kill()
    assert json.loads((base / "bridge" / bridge.USR1_NAME).read_text())["signal"] == "USR1"
    assert "trigger=SIGUSR1" in marker.read_text().splitlines()
    assert json.loads((base / "bridge" / "stopped.json").read_text())["stop_reason"] == "usr1"


def test_serve_fails_cleanly_when_the_engine_never_answers(tmp_path):
    base = short_dir(tmp_path)
    rc = bridge.serve(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        base / "bridge",
        port=free_port(),
        health_timeout_s=1.0,
        gpu_sample_s=0,
        poll_s=0.1,
    )
    assert rc == 3
    failed = json.loads((base / "bridge" / bridge.FAILED_NAME).read_text())
    assert failed["engine_returncode"] is not None or failed["t_failed"]


def test_registered_engine_argv_binds_loopback_8000():
    from harness.q2_stage1 import plan

    argv = plan.engine_argv(plan.MODEL_DIRS["9B"], plan.SERVED_NAME)
    assert argv[argv.index("--host") + 1] == "127.0.0.1"
    assert argv[argv.index("--port") + 1] == str(bridge.ENGINE_PORT)
