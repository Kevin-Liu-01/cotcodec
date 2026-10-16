from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

import pytest

from scripts.fetch_open_model import DEFAULT_REGISTRY, artifact_root, load_registry
from scripts.run_lm1_smoke import (
    GpuPoller,
    SmokeError,
    check_receipt,
    load_plan,
    parse_gpu_rows,
    run_model,
    server_argv,
    sha256_bytes,
    short_hash,
    summarize_server_log,
    text_stats,
    validate_plan,
)

PLAN_PATH = Path(__file__).resolve().parents[1] / "experiments" / "lm1" / "lm1-host-smoke-v1.json"
REGISTRY = load_registry(DEFAULT_REGISTRY)

FAKE_SERVER = r"""
import json, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer

args = sys.argv[1:]
port = int(args[args.index("--port") + 1])
mode = __MODE__
if mode == "crash":
    print("load_tensors: failed to load model", flush=True)
    sys.exit(3)
print("load_tensors: offloaded 62/62 layers to GPU", flush=True)
print("load_tensors:        CUDA0 model buffer size = 61234.50 MiB", flush=True)
print("load_tensors:        CUDA1 model buffer size = 60123.25 MiB", flush=True)
time.sleep(0.3)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        self._send(200, {"status": "ok"})
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert req["temperature"] == 0.0 and req["top_k"] == 1 and req["cache_prompt"] is False
        t = {"prompt_n": 900, "prompt_ms": 450.0, "prompt_per_second": 2000.0,
             "predicted_n": req.get("n_predict", req.get("max_tokens")), "predicted_ms": 100.0,
             "predicted_per_second": 40.0}
        if self.path == "/completion":
            self._send(200, {"content": "Rayleigh scattering makes the sky blue.", "timings": t,
                             "stop_type": "limit"})
        else:
            self._send(200, {"choices": [{"finish_reason": "stop", "message": {
                "content": "Canberra.", "reasoning_content": "The user asks."}}], "timings": t})

HTTPServer(("127.0.0.1", port), H).serve_forever()
"""


def _plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def test_committed_plan_is_valid_against_the_registry() -> None:
    plan = validate_plan(_plan(), REGISTRY)
    ids = [model["model_id"] for model in plan["models"]]
    assert ids[0] == "gpt-oss-120b-mxfp4-gguf"
    assert "kimi-k2.5-ud-tq1-0-gguf" in ids
    assert len(ids) == len(set(ids)) == 6
    load_plan(PLAN_PATH, sha256_bytes(PLAN_PATH.read_bytes()), REGISTRY)


def test_plan_digest_must_match() -> None:
    with pytest.raises(SmokeError, match="SHA-256"):
        load_plan(PLAN_PATH, "0" * 64, REGISTRY)


@pytest.mark.parametrize("flag", ["-ngl", "--split-mode", "-fit", "--port", "-m", "-dev"])
def test_plan_cannot_set_driver_owned_flags(flag: str) -> None:
    plan = _plan()
    plan["server_args"] = [*plan["server_args"], flag, "1"]
    with pytest.raises(SmokeError, match="driver"):
        validate_plan(plan, REGISTRY)
    plan = _plan()
    plan["models"][0]["extra_args"] = [flag, "1"]
    with pytest.raises(SmokeError, match="driver-owned"):
        validate_plan(plan, REGISTRY)


def test_plan_models_must_be_registered_llamacpp_entries() -> None:
    plan = _plan()
    plan["models"][0]["model_id"] = "kimi-k2.6"
    with pytest.raises(SmokeError, match="llama.cpp entry"):
        validate_plan(plan, REGISTRY)
    plan = _plan()
    plan["models"][0]["gguf"] = "other.gguf"
    with pytest.raises(SmokeError, match="required file"):
        validate_plan(plan, REGISTRY)
    plan = _plan()
    plan["models"][0]["gguf"] = "../escape.gguf"
    with pytest.raises(SmokeError, match="safe relative"):
        validate_plan(plan, REGISTRY)


def test_server_argv_puts_every_layer_on_the_gpus() -> None:
    plan = _plan()
    argv = server_argv(plan, plan["models"][0], Path("/m/x.gguf"), 18931, 32)
    assert argv[:3] == [plan["llama_server"], "-m", "/m/x.gguf"]
    assert argv[3:9] == ["-ngl", "all", "--split-mode", "layer", "-fit", "off"]
    assert argv[-6:] == ["--host", "127.0.0.1", "--port", "18931", "-t", "32"]


def _fixture_model(tmp_path: Path) -> tuple[dict, dict, Path, Path]:
    entry = copy.deepcopy(REGISTRY["models"]["gpt-oss-120b-mxfp4-gguf"])
    model_root = tmp_path / "models"
    receipt_root = tmp_path / "receipts"
    snapshot = model_root / "gpt-oss-120b-mxfp4-gguf"
    snapshot.mkdir(parents=True)
    receipt_root.mkdir()
    files = []
    for name in sorted(entry["required_files"]):
        data = f"fixture:{name}\n".encode()
        (snapshot / name).write_bytes(data)
        files.append({"path": name, "bytes": len(data), "sha256": sha256_bytes(data)})
    receipt = {
        "schema_version": 1,
        "model_id": "gpt-oss-120b-mxfp4-gguf",
        "backend": "huggingface",
        "repo_id": entry["repo_id"],
        "revision": entry["revision"],
        "mode": "full",
        "trust_remote_code": False,
        "publication_eligible": True,
        "files": files,
        "total_bytes": sum(f["bytes"] for f in files),
        "artifact_root_sha256": artifact_root(files),
        "allow_patterns": entry["allow_patterns"],
    }
    raw = json.dumps(receipt).encode()
    (receipt_root / "gpt-oss-120b-mxfp4-gguf.json").write_bytes(raw)
    model = {
        "model_id": "gpt-oss-120b-mxfp4-gguf",
        "gguf": "gpt-oss-120b-MXFP4.gguf",
        "receipt_sha256": sha256_bytes(raw),
        "artifact_root_sha256": receipt["artifact_root_sha256"],
        "load_timeout_s": 20,
    }
    return model, entry, model_root, receipt_root


def test_receipt_check_passes_and_detects_drift(tmp_path: Path) -> None:
    model, entry, model_root, receipt_root = _fixture_model(tmp_path)
    result = check_receipt(model, entry, model_root, receipt_root)
    assert result["sizes_match"] and result["files"] == 2
    bad = dict(model, receipt_sha256="f" * 64)
    with pytest.raises(SmokeError, match="receipt SHA-256"):
        check_receipt(bad, entry, model_root, receipt_root)
    (model_root / model["model_id"] / "gpt-oss-120b-MXFP4.gguf").write_bytes(b"short")
    with pytest.raises(SmokeError, match="bytes"):
        check_receipt(model, entry, model_root, receipt_root)
    other = dict(entry, revision="0" * 40)
    with pytest.raises(SmokeError, match="revision"):
        check_receipt(model, other, model_root, receipt_root)


def test_text_and_log_summaries() -> None:
    stats = text_stats("the cat sat on the mat. the cat sat on the mat. the cat sat on the mat.")
    assert stats["max_4gram_repeats"] == 3 and stats["words"] == 18
    assert text_stats("")["chars"] == 0
    log = (
        "load_tensors: offloaded 62/62 layers to GPU\n"
        "load_tensors:        CUDA0 model buffer size = 100.50 MiB\n"
        "llama_kv_cache:      CUDA1 KV buffer size =    20.00 MiB\n"
        "tensor blk.0.x (q4_0) cannot be used with preferred buffer type CUDA0, using CPU instead\n"
    )
    summary = summarize_server_log(log)
    assert summary["all_layers_offloaded"] and summary["cpu_fallback_lines"] == 1
    assert {b["kind"] for b in summary["buffers"]} == {"model", "KV"}
    assert not summarize_server_log("offloaded 60/62 layers to GPU")["all_layers_offloaded"]
    assert short_hash("abc") == sha256_bytes(b"abc")[:16]


def test_gpu_poller_keeps_per_gpu_peaks() -> None:
    values = iter([100, 100, 5000, 40000, 300])

    def query() -> str:
        used = next(values)
        return f"0, GPU-a, {used}, 81559\n1, GPU-b, {used // 2}, 81559\n"

    poller = GpuPoller(query)
    baseline = poller.reset()
    assert baseline["GPU-a"]["used_mib"] == 100
    for _ in range(3):
        poller.sample()
    peaks, samples = poller.snapshot()
    assert peaks == {"GPU-a": 40000, "GPU-b": 20000} and samples == 3
    with pytest.raises(SmokeError):
        parse_gpu_rows("garbage")


def _fake_plan(tmp_path: Path, mode: str) -> dict:
    server = tmp_path / f"fake-server-{mode}.py"
    server.write_text(FAKE_SERVER.replace("__MODE__", repr(mode)), encoding="utf-8")
    launcher = tmp_path / f"llama-server-{mode}"
    launcher.write_text(f'#!/bin/sh\nexec {sys.executable} {server} "$@"\n', encoding="utf-8")
    launcher.chmod(0o755)
    plan = _plan()
    plan["llama_server"] = str(launcher)
    plan["requests"]["request_timeout_s"] = 20
    return plan


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.parametrize("mode", ["ok", "crash"])
def test_run_model_against_a_fake_server(tmp_path: Path, mode: str) -> None:
    model, entry, model_root, receipt_root = _fixture_model(tmp_path)
    plan = _fake_plan(tmp_path, mode)
    poller = GpuPoller(lambda: "0, GPU-a, 10, 81559\n")
    out = tmp_path / "out"
    row = run_model(
        plan,
        model,
        entry,
        model_root=model_root,
        receipt_root=receipt_root,
        out_dir=out,
        port=_free_port(),
        threads=4,
        poller=poller,
        deadline=time.monotonic() + 600,
        state={"process": None},
    )
    if mode == "crash":
        assert row["status"] == "load_failed"
        assert row["server_log"]["offloaded_layers"] == []
        return
    assert row["status"] == "ok", row
    assert row["server_log"]["all_layers_offloaded"]
    assert row["prefill"]["prompt_per_second"] == 2000.0
    assert row["decode"]["predicted_n"] == plan["requests"]["completion_tokens"]
    assert row["decode"]["output_sha256_16"] == short_hash(
        "Rayleigh scattering makes the sky blue."
    )
    assert row["chat"]["finish_reason"] == "stop" and row["chat"]["reasoning_chars"] > 0
    assert "<snapshot>/gpt-oss-120b-MXFP4.gguf" in row["server_argv"]
    text_free = json.dumps(row)
    assert "Rayleigh" not in text_free and "Canberra" not in text_free
    assert (out / model["model_id"] / "completion.txt").read_text().startswith("Rayleigh")


def test_run_model_skips_when_time_is_short(tmp_path: Path) -> None:
    model, entry, model_root, receipt_root = _fixture_model(tmp_path)
    row = run_model(
        _plan(),
        model,
        entry,
        model_root=model_root,
        receipt_root=receipt_root,
        out_dir=tmp_path / "out",
        port=_free_port(),
        threads=4,
        poller=GpuPoller(lambda: "0, GPU-a, 10, 81559\n"),
        deadline=time.monotonic() + 5,
        state={"process": None},
    )
    assert row["status"] == "skipped_time"


def test_plan_refuses_the_other_projects_gpu() -> None:
    plan = _plan()
    assert plan["refuse_gpu_uuids"] == ["GPU-b23c3b4d-5413-4d75-cad3-74be85f8d058"]
    plan["refuse_gpu_uuids"] = ["0"]
    with pytest.raises(SmokeError, match="GPU UUIDs"):
        validate_plan(plan, REGISTRY)


def test_run_stops_before_loading_when_a_refused_gpu_is_visible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.run_lm1_smoke as smoke

    monkeypatch.setattr(
        smoke,
        "nvidia_smi_query",
        lambda: "0, GPU-b23c3b4d-5413-4d75-cad3-74be85f8d058, 0, 81559\n1, GPU-a, 0, 81559\n",
    )
    called: list[str] = []
    monkeypatch.setattr(smoke, "run_model", lambda *a, **k: called.append("x"))
    code = smoke.main(
        [
            "run",
            "--plan",
            str(PLAN_PATH),
            "--output-dir",
            str(tmp_path / "o"),
            "--allocation-minutes",
            "5",
        ]
    )
    assert code == 3 and not called
    summary = json.loads((tmp_path / "o" / "summary.json").read_text())
    assert summary["refused"] and summary["refused_gpus"] == [
        "GPU-b23c3b4d-5413-4d75-cad3-74be85f8d058"
    ]
