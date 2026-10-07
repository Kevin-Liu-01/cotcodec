from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import signal
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from serving_probe_fakes import FakeVllm, WordTokenizer

from harness.serving_probe.client import RequestResult
from harness.serving_probe.config import load_config
from harness.serving_probe.metrics import GpuSample, parse_prometheus
from harness.serving_probe.prompts import allowed_token_ids, count_images
from scripts import preregister
from scripts import run_vllm_throughput_probe as probe
from scripts.fetch_open_model import artifact_root, snapshot_files

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v1.yaml"
PREREG = PROJECT_ROOT / "program" / "preregistrations" / "serving-throughput-probe-v1.md"


@pytest.fixture(autouse=True)
def _restore_signal_handlers():
    saved = {
        sig: signal.getsignal(sig)
        for sig in (signal.SIGUSR1, signal.SIGTERM, signal.SIGINT, signal.SIGALRM)
    }
    yield
    signal.setitimer(signal.ITIMER_REAL, 0)
    for sig, handler in saved.items():
        signal.signal(sig, handler)


def _small_config(tmp_path: Path) -> Path:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw = copy.deepcopy(raw)
    raw["gates"].update(
        baseline_settle_s=0.0,
        baseline_duration_s=0.05,
        engine_ready_timeout_s=5,
        gpu_release_timeout_s=1,
        doctor_timeout_s=5,
    )
    raw["validity"]["reservation_window_s"] = 0.01
    raw["stop"]["in_flight_grace_s"] = 0.5
    raw["sampling"]["kv_poll_interval_s"] = 0.05
    raw["screenshot"] = {"width": 64, "height": 36}
    for point_id, point in raw["points"].items():
        for key, value in {
            "requests": 4,
            "concurrency": 2,
            "prefix_tokens": 8,
            "body_tokens": 8,
            "episodes": 2,
            "t_env_s": 0.01,
            "stagger_s": 0.0,
            "system_tokens": 8,
            "task_tokens": 4,
            "action_tokens": 2,
            "prebuilt_response_tokens": 4,
            "output_tokens": 3,
            "prompts": 2,
            "input_tokens": 8,
        }.items():
            if key in point:
                point[key] = value
        if point.get("kind") == "replay":
            point["steps"] = 4 if point_id == "r3" else 2
            if point.get("a11y_tokens"):
                point["a11y_tokens"] = 6
            if point.get("start_depth"):
                point["start_depth"] = 2
        if point.get("kind") == "aa":
            point["requests"] = 3
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


class FakeSampler:
    def __init__(self) -> None:
        self.memory = 0.0
        self.util = 0.0
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def window(self, start: float, end: float) -> list[GpuSample]:
        times = np.arange(start, max(end, start + 0.01), 0.01)
        return [GpuSample(float(t), self.memory, self.util, 100.0, 1980.0) for t in times]


class FakeServerEngine:
    mode = "server"
    served_name = "probe-model"

    def __init__(self, server: FakeVllm, model_dir: str, sampler: FakeSampler, ready: bool = True):
        self.server = server
        self.model_dir = model_dir
        self.sampler = sampler
        self.ready = ready
        self.pid = os.getpid()
        self.eager: bool | None = None

    def argv(self, eager: bool) -> list[str]:
        return ["vllm", "serve", self.model_dir] + (["--enforce-eager"] if eager else [])

    def start(self, eager: bool) -> None:
        self.eager = eager
        self.sampler.memory = 70000.0

    def wait_ready(self, timeout_s: float, should_stop=None) -> bool:
        return self.ready

    def alive(self) -> bool:
        return self.server.alive

    def metrics(self) -> dict[str, float]:
        with self.server.sync_client() as client:
            return parse_prometheus(client.get("/metrics").text)

    def reset_caches(self) -> dict[str, Any]:
        with self.server.sync_client() as client:
            ok = client.post("/reset_prefix_cache").json()["success"]
        return {"prefix": ok, "mm": True, "encoder": True}

    def async_client(self):
        return self.server.async_client()

    def log_text(self) -> str:
        return "INFO GPU KV cache size: 1,000 tokens\n"

    def tmp_maps(self) -> dict[str, list[str]]:
        return {}

    def stop(self, timeout_s: float = 30.0) -> dict[str, Any]:
        self.sampler.memory = 0.0
        return {"returncode": 0}


class FakeOfflineEngine:
    mode = "offline"
    served_name = "offline"

    def __init__(self, model_dir: str, sampler: FakeSampler) -> None:
        self.model_dir = model_dir
        self.sampler = sampler
        self.pid = os.getpid()
        self.prompt_tokens = 0
        self.generation_tokens = 0
        self.resets = 0

    def start(self, eager: bool) -> None:
        self.sampler.memory = 60000.0

    def wait_ready(self, timeout_s: float, should_stop=None) -> bool:
        return True

    def alive(self) -> bool:
        return True

    def tokenizer(self) -> WordTokenizer:
        return WordTokenizer()

    def metrics(self) -> dict[str, float]:
        return {
            "vllm:prompt_tokens": float(self.prompt_tokens),
            "vllm:generation_tokens": float(self.generation_tokens),
        }

    def reset_caches(self) -> dict[str, Any]:
        self.resets += 1
        return {"prefix": True}

    def generate(self, prompts, *, n, temperature, top_p, max_tokens) -> list[list[int]]:
        self.prompt_tokens += sum(len(p) for p in prompts)
        self.generation_tokens += len(prompts) * n * max_tokens
        return [[max_tokens] * n for _ in prompts]

    def log_text(self) -> str:
        return ""

    def tmp_maps(self) -> dict[str, list[str]]:
        return {}

    def stop(self, timeout_s: float = 30.0) -> dict[str, Any]:
        self.sampler.memory = 0.0
        return {"returncode": 0}


def _lane_outputs(root: Path, config, job_id: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    job = config.job(job_id)
    model = config.models[job.lane_model]
    (root / "provenance-verification.txt").write_text(
        json.dumps({"status": "PASS", "git_sha": "a" * 40})
    )
    (root / "container-doctor.txt").write_text("PASS command python\nSTATUS PASS mode=container\n")
    (root / "model-verification.txt").write_text(
        json.dumps(
            {
                "model_id": job.lane_model,
                "revision": model["revision"],
                "mode": "full",
                "artifact_root_sha256": model["artifact_root_sha256"],
                "publication_eligible": True,
            }
        )
    )
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    (root / "job.env").write_text(f"job_id=1\nstarted_at={started}\n")


def _doctor_pass(output: Path, env) -> dict[str, Any]:
    report = {"pass": True, "G0.2": {"pass": True}, "G0.3": {"pass": True}, "G0.4": {"pass": True}}
    output.write_text(json.dumps(report))
    return report


def _runner(
    tmp_path: Path,
    job_id: str = "a",
    *,
    server: FakeVllm | None = None,
    doctor=_doctor_pass,
    pins=None,
    ready: bool = True,
    model_root: Path | None = None,
    receipt_root: Path | None = None,
):
    config = load_config(_small_config(tmp_path))
    outputs = tmp_path / "outputs"
    if not (outputs / "job.env").exists():
        _lane_outputs(outputs, config, job_id)
    sampler = FakeSampler()
    server = server or FakeVllm()
    engines: list[Any] = []

    def factory(phase, model_dir, log_path):
        if phase.engine.mode == "offline":
            engine = FakeOfflineEngine(model_dir, sampler)
        else:
            engine = FakeServerEngine(server, model_dir, sampler, ready=ready)
        engines.append(engine)
        return engine

    runner = probe.ProbeRunner(
        config=config,
        job=config.job(job_id),
        output_dir=outputs / "probe",
        outputs_root=outputs,
        model_root=model_root or tmp_path / "models",
        receipt_root=receipt_root or tmp_path / "receipts",
        pins=pins or {},
        image_variant="cu129",
        seeds=[42, 43, 44],
        argv=["test"],
        engine_factory=factory,
        sampler_factory=lambda path: sampler,
        doctor=doctor,
        tokenizer_loader=lambda model_dir: WordTokenizer(),
        prereg_check=lambda config: {"experiment_id": config.experiment_id},
        marker_path=outputs / "checkpoint.ready",
    )
    return runner, server, engines


def _points(output: Path) -> dict[str, dict[str, Any]]:
    return {p.stem: json.loads(p.read_text()) for p in (output / "points").glob("*.json")}


def test_job_a_runs_every_point_and_writes_summary_and_marker(tmp_path: Path) -> None:
    runner, server, engines = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    output = tmp_path / "outputs" / "probe"
    summary = json.loads((output / "summary.json").read_text())
    assert summary["status"] == "complete"
    points = _points(output)
    expected = [p.point_id for phase in runner.job.phases for p in phase.points]
    assert sorted(points) == sorted(expected)
    assert {record["status"] for record in points.values()} <= {"valid", "valid-flagged"}
    assert [engine.eager for engine in engines] == [False, False]
    assert summary["gates"]["G0.6"]["real"]["image_differential"]["image_tokens"] == 2042
    assert summary["gates"]["G0.7"]["real"]["pass"] is True
    assert summary["x1"]["outcome"] in {"pass", "fail", "underpowered"}
    assert summary["a1_stability"]["valid"] == 3
    assert points["d8"]["agreement"]["agreement_rate"] == 1.0
    replay = points["r1"]["result"]
    assert replay["complete_steps"] == [1, 2] and replay["planned"] == 4
    assert points["r4"]["result"]["planned_steps"] == [3, 4]
    for record in points.values():
        assert record["config_sha256"] == runner.config.sha256
        assert "text" not in json.dumps(record.get("result", {}))
    marker = json.loads((tmp_path / "outputs" / "checkpoint.ready").read_text())
    assert marker["reason"] == "final"
    plan = json.loads((output / "plan.json").read_text())
    assert plan["env"]["TRITON_CACHE_DIR"].startswith(str(output / "cache"))
    assert server.resets >= len(expected)


def test_resume_skips_terminal_points_and_refuses_another_contract(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    again, server, engines = _runner(tmp_path)
    assert again.run() == probe.EXIT_OK
    assert server.requests == 0 and engines == []
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["phases"]["real"]["skipped"].startswith("every point")
    record_path = tmp_path / "outputs" / "probe" / "points" / "a1a.json"
    record = json.loads(record_path.read_text())
    record["config_sha256"] = "0" * 64
    record_path.write_text(json.dumps(record))
    third, _server, _engines = _runner(tmp_path)
    assert third.run() == probe.EXIT_PRE_RESULT
    assert (
        "another contract"
        in json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())[
            "pre_result_reason"
        ]
    )


def test_resume_reruns_interrupted_points(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    path = tmp_path / "outputs" / "probe" / "points" / "a6.json"
    record = json.loads(path.read_text())
    record["status"] = "interrupted"
    path.write_text(json.dumps(record))
    again, server, engines = _runner(tmp_path)
    assert again.run() == probe.EXIT_OK
    assert len(engines) == 1
    assert json.loads(path.read_text())["status"] in {"valid", "valid-flagged"}
    smoke_and_a6 = 4 + 4
    assert server.requests == smoke_and_a6


def test_signal_saves_progress_before_the_marker(tmp_path: Path, monkeypatch) -> None:
    writes: list[tuple[str, str | None]] = []
    original = probe.atomic_write_json

    def tracking(path: Path, payload: Any) -> None:
        state = payload.get("state") if isinstance(payload, dict) else None
        writes.append((path.name, state if path.name == "progress.json" else payload.get("reason")))
        original(path, payload)

    monkeypatch.setattr(probe, "atomic_write_json", tracking)
    holder: dict[str, Any] = {}

    def usr1_after(server: FakeVllm) -> None:
        if server.requests == 10:
            holder["runner"].signal_name = "SIGUSR1"
            holder["runner"].stop_event.set()

    runner, _server, _engines = _runner(
        tmp_path, server=FakeVllm(latency_s=0.01, on_request=usr1_after)
    )
    holder["runner"] = runner
    assert runner.run() == probe.EXIT_INTERRUPTED
    first_marker = next(i for i, (name, _) in enumerate(writes) if name == "checkpoint.ready")
    assert writes[first_marker][1] == "signal-checkpoint"
    assert ("progress.json", "signal-checkpoint") in writes[:first_marker]
    statuses = {p["status"] for p in _points(tmp_path / "outputs" / "probe").values()}
    assert "interrupted" in statuses
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["status"] == "interrupted" and summary["signal"] == "SIGUSR1"


def test_doctor_failure_is_a_pre_result_with_no_points(tmp_path: Path) -> None:
    def failing(output: Path, env) -> dict[str, Any]:
        return {"pass": False, "G0.2": {"pass": False}}

    runner, server, _engines = _runner(tmp_path, doctor=failing)
    assert runner.run() == probe.EXIT_PRE_RESULT
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["status"] == "pre-result" and summary["gates"]["G0.2"]["pass"] is False
    assert server.requests == 0
    assert json.loads((tmp_path / "outputs" / "checkpoint.ready").read_text())["reason"] == "final"


def test_lane_model_mismatch_fails_g01(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path)
    verification = tmp_path / "outputs" / "model-verification.txt"
    payload = json.loads(verification.read_text())
    payload["artifact_root_sha256"] = "f" * 64
    verification.write_text(json.dumps(payload))
    assert runner.run() == probe.EXIT_PRE_RESULT
    reason = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())[
        "pre_result_reason"
    ]
    assert "G0.1" in reason


def test_engine_that_never_starts_fails_g05_after_the_eager_retry(tmp_path: Path) -> None:
    runner, server, engines = _runner(tmp_path, ready=False)
    assert runner.run() == probe.EXIT_PRE_RESULT
    assert [engine.eager for engine in engines] == [False, True]
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["gates"]["G0.5"]["real"]["pass"] is False
    assert server.requests == 0


def test_smoke_failure_stops_the_primary_phase(tmp_path: Path) -> None:
    runner, server, _engines = _runner(tmp_path, server=FakeVllm(fail_every=3))
    assert runner.run() == probe.EXIT_PRE_RESULT
    points = _points(tmp_path / "outputs" / "probe")
    assert points["a-smoke"]["status"] == "invalid"
    assert len(points["a-smoke"]["attempts"]) == 2
    assert points["a1a"]["status"] == "not-run"


def _metadata_snapshot(
    tmp_path: Path, model_id: str, revision: str, repo: str
) -> tuple[Path, Path, str]:
    model_root = tmp_path / "models"
    receipt_root = tmp_path / "receipts"
    snapshot = model_root / model_id
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text('{"architectures": ["Qwen3ForCausalLM"]}')
    (snapshot / "tokenizer.json").write_text("{}")
    files = snapshot_files(snapshot)
    receipt = {
        "schema_version": 1,
        "model_id": model_id,
        "backend": "huggingface",
        "repo_id": repo,
        "revision": revision,
        "mode": "metadata",
        "publication_eligible": False,
        "trust_remote_code": False,
        "files": files,
        "total_bytes": sum(f["bytes"] for f in files),
        "artifact_root_sha256": artifact_root(files),
    }
    receipt_root.mkdir(parents=True)
    path = receipt_root / f"{model_id}.json"
    path.write_text(json.dumps(receipt))
    return model_root, receipt_root, f"{probe.sha256_file(path)}:{receipt['artifact_root_sha256']}"


def test_offline_job_b_verifies_its_pin_and_runs(tmp_path: Path) -> None:
    model_root, receipt_root, pin = _metadata_snapshot(
        tmp_path, "qwen3-8b", "b968826d9c46dd6066d109eabc6255188de91218", "Qwen/Qwen3-8B"
    )
    receipt, root = pin.split(":")
    runner, _server, engines = _runner(
        tmp_path,
        "b",
        pins={"qwen3-8b": (receipt, root)},
        model_root=model_root,
        receipt_root=receipt_root,
    )
    assert runner.run() == probe.EXIT_OK
    points = _points(tmp_path / "outputs" / "probe")
    assert {p["status"] for p in points.values()} <= {"valid", "valid-flagged"}
    assert points["b2"]["result"]["completions"] == 2 * 8
    assert points["b2"]["counter_check"]["prompt_matched"] == 2 * 8
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["gates"]["G0.1"]["metadata_pins"][0]["model_id"] == "qwen3-8b"
    assert summary["b1_stability"]["valid"] == 3
    assert engines[0].resets == len(points)


def test_tampered_metadata_snapshot_fails_g01(tmp_path: Path) -> None:
    model_root, receipt_root, pin = _metadata_snapshot(
        tmp_path, "qwen3-8b", "b968826d9c46dd6066d109eabc6255188de91218", "Qwen/Qwen3-8B"
    )
    (model_root / "qwen3-8b" / "config.json").write_text("{}")
    receipt, root = pin.split(":")
    runner, _server, _engines = _runner(
        tmp_path,
        "b",
        pins={"qwen3-8b": (receipt, root)},
        model_root=model_root,
        receipt_root=receipt_root,
    )
    assert runner.run() == probe.EXIT_PRE_RESULT
    reason = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())[
        "pre_result_reason"
    ]
    assert "no longer match" in reason or "does not match" in reason


def test_preregistration_draft_freezes_cleanly_and_the_gate_checks_the_ledger(
    tmp_path: Path,
) -> None:
    config = load_config(CONFIG_PATH)
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(probe.GateFailure, match="not frozen"):
        probe.verify_preregistration(config, ledger=ledger)
    row = preregister.freeze(PREREG, config.experiment_id, ledger=ledger, root=PROJECT_ROOT)
    assert probe.verify_preregistration(config, ledger=ledger)["sha256"] == row["sha256"]


def test_preregistration_names_the_live_contract_hash() -> None:
    text = PREREG.read_text(encoding="utf-8")
    assert probe.sha256_file(CONFIG_PATH) in text


def test_helpers(tmp_path: Path) -> None:
    env = probe.cache_environment(tmp_path, {"VLLM_ENABLE_CUDA_COMPATIBILITY": "0"})
    for key in probe.CACHE_DIRS:
        assert env[key].startswith(str(tmp_path / "cache"))
    assert env["VLLM_SERVER_DEV_MODE"] == "1" and env["VLLM_NO_USAGE_STATS"] == "1"
    job_env = tmp_path / "job.env"
    job_env.write_text("started_at=2026-10-07T00:00:00Z\n")
    wall = datetime(2026, 10, 7, 0, 10, tzinfo=UTC).timestamp()
    start, anchor = probe.allocation_start_perf(job_env, now_wall=wall, now_perf=1000.0)
    assert start == pytest.approx(400.0) and anchor == "job.env started_at"
    assert probe.allocation_start_perf(tmp_path / "missing", now_wall=wall, now_perf=5.0) == (
        5.0,
        "driver start (job.env unavailable)",
    )
    deadlines = probe.Deadlines(
        start=0.0,
        allocation_minutes=40,
        soft_fraction=0.85,
        hard_margin_minutes=4,
        reserves_after=[9, 0],
    )
    assert deadlines.soft == pytest.approx(2040.0)
    assert deadlines.phase_launch_deadline(0) == pytest.approx(2040.0 - 540.0)
    assert deadlines.phase_hard_deadline(0) == deadlines.phase_launch_deadline(0)
    assert deadlines.phase_hard_deadline(1) == pytest.approx(36 * 60.0)


def test_assessment_statuses() -> None:
    result = {"failed": 0, "completed": 4, "planned": 4, "short_outputs": 0}
    common = dict(
        counters={"pass": True},
        gpu={"peak_memory_used_mib": 71000.0},
        reservation_mib=70000.0,
        margin_mib=2048.0,
        client_cpu_pct=10.0,
        flag_pct=90.0,
        stop_reason=None,
        ran_to_end=True,
    )
    assert probe.assess_point(result, api_cpu_pct=50.0, **common)[0] == "valid"
    status, flags, _ = probe.assess_point(result, api_cpu_pct=95.0, **common)
    assert status == "valid-flagged" and flags == ["front-end-bound"]
    hot = {**common, "gpu": {"peak_memory_used_mib": 73000.0}}
    status, _, checks = probe.assess_point(result, api_cpu_pct=1.0, **hot)
    assert status == "invalid" and checks["no_contamination"] is False
    assert (
        probe.assess_point(
            result, api_cpu_pct=1.0, **{**common, "ran_to_end": False, "stop_reason": "deadline"}
        )[0]
        == "truncated"
    )
    assert (
        probe.assess_point(
            result, api_cpu_pct=1.0, **{**common, "ran_to_end": False, "stop_reason": "signal"}
        )[0]
        == "interrupted"
    )
    short = {**result, "short_outputs": 1}
    assert probe.assess_point(short, api_cpu_pct=1.0, **common)[0] == "invalid"


def test_image_differential_window() -> None:
    def res(tag: int, tokens: int) -> RequestResult:
        return RequestResult((tag,), True, None, 0.0, 1.0, prompt_tokens=tokens)

    assert probe.image_differential([res(0, 100), res(1, 2142)], 2040, 0.02)["pass"]
    assert not probe.image_differential([res(0, 100), res(1, 2200)], 2040, 0.02)["pass"]
    assert not probe.image_differential([res(1, 2142)], 2040, 0.02)["pass"]


def test_request_builders(tmp_path: Path) -> None:
    config = load_config(_small_config(tmp_path))
    tokenizer = WordTokenizer()
    allowed = allowed_token_ids(tokenizer)
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(2) as pool:
        jpeg = probe.build_open_loop_requests(
            config.points["a1a"], tokenizer, allowed, (64, 36), pool
        )
        png = probe.build_open_loop_requests(
            config.points["f1"], tokenizer, allowed, (64, 36), pool
        )
        smoke = probe.build_smoke_requests(
            config.points["a-smoke"], tokenizer, allowed, (64, 36), pool
        )
        plans = probe.build_replay_plans(config.points["r4"], tokenizer, allowed, (64, 36), pool)

    def texts(requests):
        return [
            [p["text"] for m in r.messages for p in m["content"] if p["type"] == "text"]
            for r in requests
        ]

    assert texts(jpeg) == texts(png)
    assert jpeg[0].messages[1]["content"][1]["image_url"]["url"].startswith("data:image/jpeg")
    assert png[0].messages[1]["content"][1]["image_url"]["url"].startswith("data:image/png")
    assert count_images(smoke[0].messages) == 0 and count_images(smoke[1].messages) == 1
    assert texts(smoke[:1]) == texts(smoke[1:2])
    assert [plan.steps for plan in plans] == [[3, 4], [3, 4]]
    assert len(plans[0].prebuilt_responses) == 2
    first = plans[0].build(3, list(plans[0].prebuilt_responses))
    assert count_images(first) == 3
    offline = probe.build_offline_prompts(config.points["b2"], allowed)
    assert len(offline) == 2 and all(len(ids) == 8 for ids in offline)


def test_plan_and_project_cli(tmp_path: Path, capsys) -> None:
    assert probe.main(["plan", "--job", "a"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["phases"][0]["argv"][:2] == ["vllm", "serve"]
    assert plan["pinned_models"] == []
    runner, _server, _engines = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    capsys.readouterr()
    output = tmp_path / "projection.json"
    args = [
        "project",
        "--config",
        str(_small_config(tmp_path)),
        "--job-a",
        str(tmp_path / "outputs" / "probe"),
        "--output",
        str(output),
    ]
    assert probe.main(args) == 0
    projection = json.loads(output.read_text())
    assert projection["q2"]["decision"] in {
        "rescope-before-gauntlet",
        "dossier-overestimated",
        "within-dossier-range",
    }
    assert len(projection["q2"]["cells"]) == 16
    with pytest.raises(SystemExit, match="overwrite"):
        probe.main(args)


def test_run_cli_refuses_wrong_seeds_and_allocation(capsys) -> None:
    base = ["run", "--config", str(CONFIG_PATH), "--job", "a", "--output-dir", "/nonexistent/probe"]
    assert (
        probe.main([*base, "--allocation-minutes", "40", "--seeds", "1", "2", "3"])
        == probe.EXIT_PRE_RESULT
    )
    assert (
        probe.main([*base, "--allocation-minutes", "30", "--seeds", "42", "43", "44"])
        == probe.EXIT_PRE_RESULT
    )
    assert (
        probe.main(
            [
                "run",
                "--config",
                str(CONFIG_PATH),
                "--job",
                "b",
                "--output-dir",
                "/x",
                "--allocation-minutes",
                "20",
                "--seeds",
                "42",
                "43",
                "44",
            ]
        )
        == probe.EXIT_PRE_RESULT
    )
    assert "pre-result" in capsys.readouterr().err


def test_marker_absent_without_env_and_console_logging(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path)
    runner.marker_path = None
    with contextlib.redirect_stderr(io.StringIO()):
        assert runner.run() == probe.EXIT_OK
    assert not (tmp_path / "outputs" / "checkpoint.ready").exists()
    assert "a1a" in (tmp_path / "outputs" / "probe" / "driver.log").read_text()
    assert time.perf_counter() > 0


def test_compare_parsed_flags_catches_drift() -> None:
    config = load_config(CONFIG_PATH)
    engine = config.engines["a-real"]
    parsed = {
        **dict(engine.flags),
        "load_format": "auto",
        "speculative_config": None,
        "enforce_eager": False,
    }
    assert probe.compare_parsed_flags(engine, parsed) == []
    drifted = {
        **parsed,
        "max_model_len": 32768,
        "speculative_config": {"method": "mtp"},
        "enforce_eager": True,
    }
    problems = probe.compare_parsed_flags(engine, drifted)
    assert any(p.startswith("max_model_len") for p in problems)
    assert "speculative decoding is configured" in problems
    assert "eager mode is forced" in problems


def test_interrupt_during_engine_start_is_not_a_gate_failure(tmp_path: Path) -> None:
    runner, server, engines = _runner(tmp_path, ready=False)
    original = runner.engine_factory

    def factory(phase, model_dir, log_path):
        engine = original(phase, model_dir, log_path)
        runner.signal_name = "SIGTERM"
        runner.stop_event.set()
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_INTERRUPTED
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["status"] == "interrupted" and "pre_result_reason" not in summary
    assert len(engines) == 1
    marker = json.loads((tmp_path / "outputs" / "checkpoint.ready").read_text())
    assert marker["reason"] == "signal-checkpoint"
