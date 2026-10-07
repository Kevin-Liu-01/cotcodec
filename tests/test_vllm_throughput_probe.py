from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from serving_probe_fakes import FakeVllm, WordTokenizer, write_job_dir, x1_passing_job_a_points

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
BATCH_SCRIPT = PROJECT_ROOT / "infra" / "slurm" / "host-single-node" / "docker-research.sbatch"
MARKER_HEAD_BYTES = 4096


def lane_confirms(marker: Path, signal_name: str) -> bool:
    """The content rule of docker-research.sbatch checkpoint_marker_is_fresh()."""
    content = marker.read_bytes()[:MARKER_HEAD_BYTES].decode("utf-8", "replace")
    return f"\ntrigger=SIG{signal_name}\n" in f"\n{content}\n"


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
        #: Set to simulate an nvidia-smi reader that stopped producing samples.
        self.dead = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def window(self, start: float, end: float) -> list[GpuSample]:
        if self.dead:
            return []
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
        #: reset_caches() call numbers whose multimodal-cache reset fails.
        self.mm_reset_failures: set[int] = set()
        self.reset_calls = 0

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
        self.reset_calls += 1
        with self.server.sync_client() as client:
            ok = client.post("/reset_prefix_cache").json()["success"]
        return {"prefix": ok, "mm": self.reset_calls not in self.mm_reset_failures, "encoder": True}

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
        self.calls = 0
        #: generate() call number that is still decoding when its wall cap fires.
        self.stall_call: int | None = None
        #: Requests left in the engine by an interrupted call (vLLM keeps them).
        self.leftover: list[list[int]] = []
        self.abort_works = True
        self.aborts = 0
        self.poisoned = False

    def start(self, eager: bool) -> None:
        self.sampler.memory = 60000.0

    def wait_ready(self, timeout_s: float, should_stop=None) -> bool:
        return True

    def alive(self) -> bool:
        return not self.poisoned

    def abort_unfinished(self) -> dict[str, Any]:
        self.aborts += 1
        if self.abort_works:
            self.leftover = []
        self.poisoned = bool(self.leftover)
        return {"aborted_request_ids": 1, "unfinished_after_abort": self.poisoned}

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
        self.calls += 1
        if self.calls == self.stall_call:
            self.leftover = [[max_tokens] * n for _ in prompts]
            time.sleep(30)  # the point's SIGALRM interrupts this
        # Like vLLM's _run_engine, finish whatever is left from an interrupted call
        # and return it ahead of this call's outputs.
        extra, self.leftover = self.leftover, []
        self.prompt_tokens += sum(len(p) for p in prompts)
        self.generation_tokens += len(prompts) * n * max_tokens
        self.generation_tokens += sum(sum(choice) for choice in extra)
        return extra + [[max_tokens] * n for _ in prompts]

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
    config_path: Path | None = None,
):
    config = load_config(config_path or _small_config(tmp_path))
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
        assert record["superseded_attempts"] == []
    # checkpoint.ready is reserved for a signal-triggered save; no signal, no marker.
    assert not (tmp_path / "outputs" / "checkpoint.ready").exists()
    assert summary["acceptance"] == {
        "accepted": True,
        "status": "complete",
        "eager": False,
        "eager_phases": [],
        "job_gate_failures": [],
        "phase_gate_failures": {},
    }
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
    writes: list[tuple[str, str]] = []
    original = probe.atomic_write_text

    def tracking(path: Path, text: str) -> None:
        if path.name == "progress.json":
            writes.append((path.name, json.loads(text)["state"]))
        else:
            writes.append((path.name, text.splitlines()[0] if text else ""))
        original(path, text)

    monkeypatch.setattr(probe, "atomic_write_text", tracking)

    def usr1_after(server: FakeVllm) -> None:
        if server.requests == 10:
            os.kill(os.getpid(), signal.SIGUSR1)  # the driver's own handler

    runner, _server, _engines = _runner(
        tmp_path, server=FakeVllm(latency_s=0.01, on_request=usr1_after)
    )
    assert runner.run() == probe.EXIT_INTERRUPTED
    markers = [i for i, (name, _) in enumerate(writes) if name == "checkpoint.ready"]
    assert len(markers) == 1, "one signal, one marker"
    assert writes[markers[0]][1] == "trigger=SIGUSR1"
    assert ("progress.json", "signal-checkpoint") in writes[: markers[0]]
    marker = tmp_path / "outputs" / "checkpoint.ready"
    assert lane_confirms(marker, "USR1") and not lane_confirms(marker, "TERM")
    progress = tmp_path / "outputs" / "probe" / "progress.json"
    lines = marker.read_text().splitlines()
    assert any(line.startswith("progress_sha256=") for line in lines)
    statuses = {p["status"] for p in _points(tmp_path / "outputs" / "probe").values()}
    assert "interrupted" in statuses
    summary = json.loads(progress.parent.joinpath("summary.json").read_text())
    assert summary["status"] == "interrupted" and summary["signal"] == "SIGUSR1"
    assert summary["signals_received"] == ["SIGUSR1"]
    assert summary["acceptance"]["accepted"] is False


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or shutil.which("bash") is None,
    reason="the lane's predicate uses GNU stat",
)
def test_lane_batch_predicate_confirms_the_driver_marker(tmp_path: Path) -> None:
    """Run the batch script's own checkpoint_marker_is_fresh() on the driver's marker."""
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    functions = "\n".join(
        "{}() {{{}\n}}".format(name, content.split(f"{name}() {{", 1)[1].split("\n}\n", 1)[0])
        for name in ("checkpoint_marker_identity", "checkpoint_marker_is_fresh")
    )
    marker = tmp_path / "outputs" / "checkpoint.ready"

    def fresh(before: str, requested_ns: int, signal_name: str) -> bool:
        script = (
            f'checkpoint_marker="{marker}"\n{functions}\n'
            f'checkpoint_marker_is_fresh "{before}" "{requested_ns}" "{signal_name}"'
        )
        return subprocess.run(["bash", "-c", script], check=False).returncode == 0

    requested = time.time_ns()

    def usr1_after(server: FakeVllm) -> None:
        if server.requests == 6:
            os.kill(os.getpid(), signal.SIGUSR1)

    runner, _server, _engines = _runner(
        tmp_path, server=FakeVllm(latency_s=0.01, on_request=usr1_after)
    )
    assert runner.run() == probe.EXIT_INTERRUPTED
    assert fresh("absent", requested, "USR1")
    assert not fresh("absent", requested, "TERM")


def test_term_after_a_usr1_checkpoint_writes_a_second_marker(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path)
    runner.note_signal("SIGUSR1")
    runner.output_dir.mkdir(parents=True)
    runner._checkpoint_after_signal()
    marker = tmp_path / "outputs" / "checkpoint.ready"
    assert lane_confirms(marker, "USR1")
    first = marker.read_text()
    runner._checkpoint_after_signal()  # nothing new to acknowledge
    assert marker.read_text() == first
    runner.note_signal("SIGTERM")
    runner._checkpoint_after_signal()
    assert lane_confirms(marker, "TERM") and not lane_confirms(marker, "USR1")


def test_doctor_failure_is_a_pre_result_with_no_points(tmp_path: Path) -> None:
    def failing(output: Path, env) -> dict[str, Any]:
        return {"pass": False, "G0.2": {"pass": False}}

    runner, server, _engines = _runner(tmp_path, doctor=failing)
    assert runner.run() == probe.EXIT_PRE_RESULT
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["status"] == "pre-result" and summary["gates"]["G0.2"]["pass"] is False
    assert summary["acceptance"]["accepted"] is False
    # The doctor stopped at G0.2; the gates it never reached are recorded as not passed.
    assert summary["acceptance"]["job_gate_failures"] == ["G0.2", "G0.3", "G0.4"]
    assert server.requests == 0
    assert not (tmp_path / "outputs" / "checkpoint.ready").exists()


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


def test_preregistration_names_the_live_probe_code_digest() -> None:
    code = probe.probe_code_digest()
    assert code["digest"] in PREREG.read_text(encoding="utf-8")
    assert "scripts/run_vllm_throughput_probe.py" in code["files"]
    assert "harness/serving_probe/budget.py" in code["files"]


def test_preregistration_reads_as_frozen_and_states_the_rules_as_coded() -> None:
    raw = PREREG.read_text(encoding="utf-8")
    text = " ".join(raw.split())
    status = raw.split("\n## 1.", 1)[0]
    assert "Status: frozen in program/preregistrations/ledger.jsonl" in status
    for stale in ("DRAFT", "Not frozen", "not frozen", "Freeze with"):
        assert stale not in status
    for stale in ("can overrule any of them before freezing", "The owner may require"):
        assert stale not in text
    # budget.build_profiles: the larger of the last two step means, not their mean.
    assert (
        "the larger of r2's last two step means minus the larger of r1's last two step means"
        in text
    )
    assert "steady latency (the larger of its last two step means)" in text
    # test_serving_probe_budget.test_x1_operating_characteristics_match_the_preregistration
    assert "P(pass) is at most 0.02, 0.12, 0.11 and 0.07" in text
    assert "with a true 8% difference, P(pass) is at most 0.03 at any of these CVs" not in text
    # client.percentile_summary records the SE; project() admits accepted jobs only.
    assert "standard error of each step mean" in text
    assert "**Accepted jobs only**" in text
    # job_admission() also reads the lane's termination.env (lane_termination).
    assert "`termination.env`" in text and "`reason=completed` and `exit_code=0`" in text
    # The cu130 retry answers only a gate failure that ends the job (section 5).
    assert "A gate failure on the cu129 image ends a job as a pre-result" in text
    assert "does not end the job and triggers no cu130 retry" in text
    assert "rerun's output replaces the failed job's output in the projection" in text
    # Budget figures as D8 and D17 state them.
    assert "D8 expects 0.75 GPU-h" in text and "0.333 GPU-h" in text
    for stale in ("expected about 0.8", "cap 0.33 GPU-h", "A gate from G0.2 to G0.8 fails"):
        assert stale not in text
    numbers = [int(n) for n in re.findall(r"^(\d+)\. \*\*", raw, flags=re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1)), "design decisions stay numbered in order"


def _copy_tree(root: Path) -> None:
    for pattern in (
        *probe.PROBE_CODE_GLOBS,
        "program/preregistrations/serving-throughput-probe-v1.md",
    ):
        for path in PROJECT_ROOT.glob(pattern):
            target = root / path.relative_to(PROJECT_ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def test_g00_binds_the_frozen_text_to_the_contract_and_the_code(tmp_path: Path) -> None:
    config = load_config(CONFIG_PATH)
    root = tmp_path / "repo"
    _copy_tree(root)
    prereg = root / config.preregistration
    text = prereg.read_text(encoding="utf-8")
    code = probe.probe_code_digest(root)
    assert code["digest"] == probe.probe_code_digest()["digest"]

    # 1. A frozen text that does not name this contract is refused.
    prereg.write_text(text.replace(config.sha256, "0" * 64), encoding="utf-8")
    ledger = tmp_path / "ledger-1.jsonl"
    preregister.freeze(prereg, config.experiment_id, ledger=ledger, root=root)
    with pytest.raises(probe.GateFailure, match="contract SHA-256"):
        probe.verify_preregistration(config, ledger=ledger, root=root)

    # 2. Code edited after the freeze (here a budget rule) is refused.
    prereg.write_text(text, encoding="utf-8")
    ledger = tmp_path / "ledger-2.jsonl"
    row = preregister.freeze(prereg, config.experiment_id, ledger=ledger, root=root)
    verified = probe.verify_preregistration(config, ledger=ledger, root=root)
    assert verified["sha256"] == row["sha256"]
    assert verified["probe_code_digest"] == code["digest"]
    budget = root / "harness" / "serving_probe" / "budget.py"
    budget.write_text(budget.read_text() + "\n# edited after the freeze\n")
    with pytest.raises(probe.GateFailure, match="probe code digest"):
        probe.verify_preregistration(config, ledger=ledger, root=root)

    # 3. An edited contract has another SHA-256, which the frozen text does not name.
    edited = tmp_path / "edited.yaml"
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["dummy_admissibility"]["max_relative_delta"] = 0.5
    edited.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    budget.write_text(budget.read_text().replace("\n# edited after the freeze\n", ""))
    with pytest.raises(probe.GateFailure, match="contract SHA-256"):
        probe.verify_preregistration(load_config(edited), ledger=ledger, root=root)


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


def _frozen(config) -> dict[str, Any]:
    return {"experiment_id": config.experiment_id, "sha256": "f" * 64}


def _lane_finished(run_dir: Path, reason: str = "completed", exit_code: int = 0) -> Path:
    """Write the termination.env the lane's batch script leaves when it exits."""
    path = run_dir / probe.LANE_TERMINATION_FILE
    path.write_text(
        f"job_id=1\nreason={reason}\nexit_code={exit_code}\n"
        "finished_at=2026-10-07T00:40:00Z\ncheckpoint_ready=false\n"
        "checkpoint_marker_present=false\n"
    )
    return path


def test_plan_and_project_cli(tmp_path: Path, capsys) -> None:
    assert probe.main(["plan", "--job", "a"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["phases"][0]["argv"][:2] == ["vllm", "serve"]
    assert plan["pinned_models"] == []
    runner, _server, _engines = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    capsys.readouterr()
    config = runner.config
    _lane_finished(tmp_path / "outputs")
    job_a = tmp_path / "outputs" / "probe"
    projection = probe.project(config, job_a=job_a, job_b=None, job_c=None, prereg_check=_frozen)
    assert projection["q2"]["decision"] in {
        "rescope-before-gauntlet",
        "dossier-overestimated",
        "within-dossier-range",
    }
    assert len(projection["q2"]["cells"]) == 16
    assert projection["preregistration"]["sha256"] == "f" * 64
    assert projection["code"]["digest"] == probe.probe_code_digest()["digest"]
    assert "head" in projection["code"]["git"]
    assert projection["jobs"]["a"]["status"] == "complete"
    assert projection["jobs"]["a"]["acceptance"]["accepted"] is True
    # The CLI checks the real ledger. Before the freeze it refused because the
    # experiment was not frozen; since the freeze it refuses because this small
    # test contract is not the one the frozen registration names. Either way no
    # projection may be written.
    output = tmp_path / "projection.json"
    args = ["project", "--config", str(_small_config(tmp_path)), "--job-a", str(job_a)]
    assert probe.main([*args, "--output", str(output)]) == probe.EXIT_PRE_RESULT
    err = capsys.readouterr().err
    assert "not frozen" in err or "does not name contract SHA-256" in err
    assert not output.exists()
    output.write_text("{}")
    with pytest.raises(SystemExit, match="overwrite"):
        probe.main([*args, "--output", str(output)])


def test_project_refuses_points_from_another_contract_or_job(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    job_a = tmp_path / "outputs" / "probe"
    config = runner.config
    with pytest.raises(probe.ProjectionError, match="job-b"):
        probe.project(config, job_a=job_a, job_b=job_a, job_c=None, prereg_check=_frozen)
    path = job_a / "points" / "a1b.json"
    record = json.loads(path.read_text())
    record["config_sha256"] = "0" * 64
    path.write_text(json.dumps(record))
    with pytest.raises(probe.ProjectionError, match="contract"):
        probe.project(config, job_a=job_a, job_b=None, job_c=None, prereg_check=_frozen)

    def unfrozen(config):
        raise probe.GateFailure("G0.0 preregistration is not frozen: test")

    with pytest.raises(probe.ProjectionError, match="not frozen"):
        probe.project(config, job_a=job_a, job_b=None, job_c=None, prereg_check=unfrozen)


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
        runner.note_signal("SIGTERM")
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_INTERRUPTED
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["status"] == "interrupted" and "pre_result_reason" not in summary
    assert len(engines) == 1
    marker = tmp_path / "outputs" / "checkpoint.ready"
    assert lane_confirms(marker, "TERM") and not lane_confirms(marker, "USR1")


# --- Review regressions -----------------------------------------------------


class _FailOnce(FakeVllm):
    """Answers chat request number ``fail_at`` with a 400, once."""

    def __init__(self, fail_at: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.fail_at = fail_at

    async def handle(self, request):
        import httpx

        if request.url.path == "/v1/chat/completions" and self.requests + 1 == self.fail_at:
            self.requests += 1
            return httpx.Response(400, text="transient")
        return await super().handle(request)


def test_a_failed_replay_request_is_invalid_and_rerun(tmp_path: Path) -> None:
    # Requests 1-4 are a-smoke and 5-8 a1a; request 9 is r1's first.
    runner, _server, _engines = _runner(tmp_path, server=_FailOnce(9))
    assert runner.run() == probe.EXIT_OK
    record = _points(tmp_path / "outputs" / "probe")["r1"]
    assert record["status"] in {"valid", "valid-flagged"}
    assert [a["status"] for a in record["attempts"]] == ["invalid", record["status"]]
    first = record["superseded_attempts"][0]
    assert first["status"] == "invalid" and first["stop_reason"] is None
    assert first["result"]["request_errors"] == 1
    assert first["result"]["planned"] == 4 and first["result"]["completed"] < 4


def test_superseded_attempts_keep_their_metrics(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path, server=_FailOnce(6))
    assert runner.run() == probe.EXIT_OK
    record = _points(tmp_path / "outputs" / "probe")["a1a"]
    assert len(record["superseded_attempts"]) == 1
    first = record["superseded_attempts"][0]
    assert first["attempt"] == 1 and first["status"] == "invalid"
    assert first["result"]["request_errors"] == 1 and "gpu" in first and "counters" in first
    assert record["attempt"] == 2


def test_assessment_statuses_fail_closed() -> None:
    result = {"failed": 0, "completed": 4, "planned": 4, "short_outputs": 0, "duration_s": 10}
    common = dict(
        counters={"pass": True},
        gpu={"samples": 20, "peak_memory_used_mib": 71000.0},
        reservation_mib=70000.0,
        reservation_required=True,
        margin_mib=2048.0,
        api_cpu_pct=1.0,
        client_cpu_pct=1.0,
        flag_pct=90.0,
        stop_reason=None,
        ran_to_end=True,
        caches_ok=True,
        min_samples=4,
    )
    assert probe.assess_point(result, **common)[0] == "valid"
    status, flags, _ = probe.assess_point(result, **{**common, "api_cpu_pct": 95.0})
    assert status == "valid-flagged" and flags == ["front-end-bound"]
    hot = {**common, "gpu": {"samples": 20, "peak_memory_used_mib": 73000.0}}
    status, _, checks = probe.assess_point(result, **hot)
    assert status == "invalid" and checks["no_contamination"] is False
    signalled = {**common, "ran_to_end": False, "stop_reason": "signal"}
    assert probe.assess_point(result, **signalled)[0] == "interrupted"
    short = {**result, "short_outputs": 1}
    assert probe.assess_point(short, **common)[0] == "invalid"
    no_samples = {**common, "gpu": {"samples": 0}}
    status, _, checks = probe.assess_point(result, **no_samples)
    assert status == "invalid" and not checks["gpu_sampled"]
    sparse = {**common, "gpu": {"samples": 2, "peak_memory_used_mib": 71000.0}}
    assert probe.assess_point(result, **sparse)[0] == "invalid"
    unreserved = {
        **common,
        "reservation_mib": None,
        "gpu": {"samples": 9, "peak_memory_used_mib": 81000.0},
    }
    status, _, checks = probe.assess_point(result, **unreserved)
    assert status == "invalid" and not checks["no_contamination"]
    smoke = {**unreserved, "reservation_required": False}
    assert probe.assess_point(result, **smoke)[0] == "valid"
    assert probe.assess_point(result, **{**common, "caches_ok": False})[0] == "invalid"
    # A point that ended early with no signal and no deadline is invalid, not truncated.
    early = {**result, "failed": 2, "completed": 2, "request_errors": 1}
    assert probe.assess_point(early, **{**common, "ran_to_end": False})[0] == "invalid"
    # A deadline with a request error is invalid too; without one it is truncated.
    cut = {**common, "ran_to_end": False, "stop_reason": "deadline"}
    assert probe.assess_point(early, **cut)[0] == "invalid"
    assert probe.assess_point({**early, "request_errors": 0}, **cut)[0] == "truncated"
    # Leftover outputs from another call (completed above planned) are never valid.
    drained = {**result, "completed": 8, "failed": -4}
    assert probe.assess_point(drained, **common)[0] == "invalid"
    assert probe.min_gpu_samples(60.0, 500.0, 0.2) == 24
    assert probe.min_gpu_samples(0.001, 500.0, 0.2) == 1
    assert probe.caches_reset([{"prefix": True, "mm": True, "encoder": True}], server=True)
    assert not probe.caches_reset([{"prefix": True, "mm": False, "encoder": True}], server=True)
    assert probe.caches_reset([{"prefix": True}], server=False)
    assert not probe.caches_reset([], server=False)


def test_a_dead_sampler_stops_the_phase_after_the_smoke(tmp_path: Path) -> None:
    runner, server, _engines = _runner(tmp_path)
    original_sleep = runner.sleep

    def sleep(seconds: float) -> None:
        # The reservation window follows the smoke; the sampler dies just before it.
        if runner.point_status.get("a-smoke") in {"valid", "valid-flagged"}:
            runner.sampler.dead = True
        original_sleep(seconds)

    runner.sleep = sleep
    assert runner.run() == probe.EXIT_PRE_RESULT
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["gates"]["G0.8"]["real/reservation"]["pass"] is False
    points = _points(tmp_path / "outputs" / "probe")
    assert points["a1a"]["status"] == "not-run"
    assert server.requests == 4


def test_a_failed_cache_reset_invalidates_the_point(tmp_path: Path) -> None:
    runner, _server, engines = _runner(tmp_path)
    original = runner.engine_factory

    def factory(phase, model_dir, log_path):
        engine = original(phase, model_dir, log_path)
        if phase.phase_id == "real":
            engine.mm_reset_failures = {2}  # a1a's first attempt (the smoke is call 1)
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_OK
    record = _points(tmp_path / "outputs" / "probe")["a1a"]
    first = record["superseded_attempts"][0]
    assert first["status"] == "invalid" and first["checks"]["caches_reset"] is False
    assert first["cache_reset"]["mm"] is False
    assert record["status"] in {"valid", "valid-flagged"}


def test_a_failed_reset_between_aa_arms_invalidates_d8(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path)
    original = runner.engine_factory
    order = [p.point_id for p in runner.job.phases[0].points]
    between = order.index("d8") + 2  # d8's own reset, then the one between its arms

    def factory(phase, model_dir, log_path):
        engine = original(phase, model_dir, log_path)
        if phase.phase_id == "real":
            engine.mm_reset_failures = {between, between + 2}
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_OK
    record = _points(tmp_path / "outputs" / "probe")["d8"]
    assert record["status"] == "invalid"
    assert record["cache_reset_between_arms"][0]["mm"] is False
    assert len(record["superseded_attempts"]) == 1


def _job_b_runner(tmp_path: Path, **overrides):
    model_root, receipt_root, pin = _metadata_snapshot(
        tmp_path, "qwen3-8b", "b968826d9c46dd6066d109eabc6255188de91218", "Qwen/Qwen3-8B"
    )
    receipt, root = pin.split(":")
    path = _small_config(tmp_path)
    raw = yaml.safe_load(path.read_text())
    for point_id, values in overrides.items():
        raw["points"][point_id].update(values)
    path.write_text(yaml.safe_dump(raw, sort_keys=False))
    return _runner(
        tmp_path,
        "b",
        pins={"qwen3-8b": (receipt, root)},
        model_root=model_root,
        receipt_root=receipt_root,
        config_path=path,
    )


def test_an_offline_truncation_is_aborted_and_does_not_cascade(tmp_path: Path) -> None:
    runner, _server, engines = _job_b_runner(tmp_path, b2={"max_minutes": 0.02})
    original = runner.engine_factory

    def factory(phase, model_dir, log_path):
        engine = original(phase, model_dir, log_path)
        engine.stall_call = 3  # b-smoke, b1a, then b2
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_OK
    points = _points(tmp_path / "outputs" / "probe")
    assert points["b2"]["status"] == "truncated"
    assert points["b2"]["abort"] == {"aborted_request_ids": 1, "unfinished_after_abort": False}
    for name in ("b6", "b1b", "b1c", "b3"):
        assert points[name]["status"] in {"valid", "valid-flagged"}, name
        assert points[name]["result"]["completed"] == points[name]["result"]["planned"]
    assert engines[0].aborts == 1


def test_an_offline_engine_that_keeps_requests_ends_the_phase(tmp_path: Path) -> None:
    runner, _server, _engines = _job_b_runner(tmp_path, b2={"max_minutes": 0.02})
    original = runner.engine_factory

    def factory(phase, model_dir, log_path):
        engine = original(phase, model_dir, log_path)
        engine.stall_call = 3
        engine.abort_works = False
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_OK
    points = _points(tmp_path / "outputs" / "probe")
    assert points["b2"]["status"] == "truncated"
    assert points["b2"]["abort"]["unfinished_after_abort"] is True
    for name in ("b6", "b1b", "b1c", "b3"):
        assert points[name]["status"] == "not-run" and points[name]["reason"] == "engine failed"


def test_offline_engine_aborts_and_filters_by_request_id(tmp_path: Path, monkeypatch) -> None:
    """The real OfflineEngine against a stand-in for vLLM's LLM request bookkeeping."""
    import types

    from serving_probe_fakes import FakeLLM

    monkeypatch.setitem(sys.modules, "vllm", types.SimpleNamespace(SamplingParams=lambda **kw: kw))
    monkeypatch.setitem(
        sys.modules,
        "vllm.inputs",
        types.SimpleNamespace(TokensPrompt=lambda prompt_token_ids: prompt_token_ids),
    )
    config = load_config(CONFIG_PATH)
    engine = probe.OfflineEngine(
        config.engines["b-offline"], "/m", config, {}, tmp_path / "engine.log"
    )
    engine.llm = FakeLLM(interrupt=probe.ProbeDeadline)
    kwargs = dict(n=2, temperature=1.0, top_p=1.0, max_tokens=3)
    engine.llm.interrupt_next = True
    with pytest.raises(probe.ProbeDeadline):
        engine.generate([[1, 2], [3, 4]], **kwargs)
    assert engine.llm.unfinished == {"0", "1"}
    # Without an abort the next call's outputs would include the leftovers; the
    # request-id filter drops them.
    assert engine.generate([[5]], **kwargs) == [[3, 3]]
    assert engine.llm.unfinished == set()
    engine.llm.interrupt_next = True
    with pytest.raises(probe.ProbeDeadline):
        engine.generate([[6], [7]], **kwargs)
    assert engine.abort_unfinished() == {
        "aborted_request_ids": 2,
        "unfinished_after_abort": False,
    }
    assert engine.alive() and engine.llm.aborted == ["3", "4"]
    engine.llm.interrupt_next = True
    with pytest.raises(probe.ProbeDeadline):
        engine.generate([[8]], **kwargs)
    engine.llm.abort_ignored = True
    assert engine.abort_unfinished()["unfinished_after_abort"] is True
    assert not engine.alive()


def test_g08_is_rechecked_before_the_eager_retry(tmp_path: Path) -> None:
    runner, server, engines = _runner(tmp_path, ready=False)
    assert runner.run() == probe.EXIT_PRE_RESULT
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    attempts = summary["gates"]["G0.5"]["real"]["attempts"]
    assert [a["eager"] for a in attempts] == [False, True]
    assert "G0.8" not in attempts[0]
    assert attempts[1]["G0.8"]["pass"] is True
    assert attempts[1]["memory_release"]["released"] is True
    assert summary["gates"]["G0.8"]["real/eager-retry"]["pass"] is True


def test_a_busy_device_before_the_eager_retry_fails_g08(tmp_path: Path) -> None:
    runner, server, engines = _runner(tmp_path, ready=False)
    original = runner.engine_factory

    def factory(phase, model_dir, log_path):
        engine = original(phase, model_dir, log_path)
        engine.stop = lambda timeout_s=30.0: {"returncode": 0}  # memory never released
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_PRE_RESULT
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["gates"]["G0.8"]["real/eager-retry"]["pass"] is False
    assert len(engines) == 1, "the eager engine is never started"
    assert "G0.8 failed" in summary["pre_result_reason"]


def test_an_eager_fallback_job_is_accepted_and_labelled(tmp_path: Path) -> None:
    runner, _server, engines = _runner(tmp_path)
    original = runner.engine_factory

    def factory(phase, model_dir, log_path):
        engine = original(phase, model_dir, log_path)
        engine.ready = len(engines) > 1  # the first default-mode start fails
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_OK
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    assert summary["eager"] is True
    acceptance = summary["acceptance"]
    assert acceptance["accepted"] is True and acceptance["eager"] is True
    assert acceptance["eager_phases"] == ["dummy-control", "real"]
    assert [engine.eager for engine in engines] == [False, True, True]


def test_cli_refuses_abbreviated_options() -> None:
    parser = probe.build_parser()
    base = ["run", "--config", "c", "--job", "a", "--output-dir", "o", "--allocation-minutes", "40"]
    assert parser.parse_args([*base, "--seeds", "42", "43", "44"]).seeds == [42, 43, 44]
    for abbreviated in ("--see", "--seed"):
        with pytest.raises(SystemExit):
            parser.parse_args([*base, abbreviated, "42", "43", "44"])
    with pytest.raises(SystemExit):
        parser.parse_args(["project", "--job-a", "a", "--out", "x"])


def test_digest_cli_prints_the_contract_and_code_hashes(capsys) -> None:
    assert probe.main(["digest"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contract_sha256"] == probe.sha256_file(CONFIG_PATH)
    assert payload["digest"] == probe.probe_code_digest()["digest"]


def test_an_invalid_smoke_in_a_control_phase_fails_g06_without_rejecting_the_job(
    tmp_path: Path,
) -> None:
    runner, _server, _engines = _runner(tmp_path)
    original = runner.engine_factory

    def factory(phase, model_dir, log_path):
        engine = original(phase, model_dir, log_path)
        if phase.phase_id == "dummy-control":
            engine.mm_reset_failures = {1, 2}  # both smoke attempts
        return engine

    runner.engine_factory = factory
    assert runner.run() == probe.EXIT_OK
    summary = json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())
    verdict = summary["gates"]["G0.6"]["dummy-control"]
    assert verdict["pass"] is False and "caches_reset" in verdict["reason"]
    assert summary["acceptance"]["accepted"] is True
    assert summary["acceptance"]["phase_gate_failures"] == {"dummy-control": ["G0.6"]}
    points = _points(tmp_path / "outputs" / "probe")
    assert {points[name]["status"] for name in ("x1-a1", "x1-r1")} == {"not-run"}
    assert summary["x1"]["outcome"] == "not-run"


# -- job acceptance gates budget entry (preregistration sections 5 and 8, decision D17) --


def _interrupt_after(runner, point_id: str) -> None:
    """Deliver the lane's USR1 right after ``point_id`` is recorded."""
    original = runner._record

    def record(point, rec):
        original(point, rec)
        if point.point_id == point_id:
            runner.note_signal("SIGUSR1")

    runner._record = record


def _complete_job_a(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    runner, _server, _engines = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    _lane_finished(tmp_path / "outputs")
    return runner.config, tmp_path / "outputs" / "probe"


def _project(config, job_a: Path, job_b: Path | None = None, job_c: Path | None = None):
    return probe.project(config, job_a=job_a, job_b=job_b, job_c=job_c, prereg_check=_frozen)


def _offline(completions: int, duration_s: float) -> dict[str, Any]:
    return {
        "status": "valid",
        "result": {
            "completions": completions,
            "duration_s": duration_s,
            "completions_per_s": completions / duration_s,
        },
    }


def _job_b_points() -> dict[str, dict[str, Any]]:
    return {
        "b2": _offline(32, 60.0),
        "b3": _offline(64, 50.0),
        "b6": _offline(24, 90.0),
        "b1a": _offline(64, 30.0),
        "b1b": _offline(64, 30.3),
        "b1c": _offline(64, 30.1),
    }


def test_project_uses_no_point_of_an_interrupted_job_a(tmp_path: Path) -> None:
    runner, _server, _engines = _runner(tmp_path)
    _interrupt_after(runner, "a1c")
    assert runner.run() == probe.EXIT_INTERRUPTED
    _lane_finished(
        tmp_path / "outputs",
        reason="signal_USR1_checkpoint_confirmed",
        exit_code=probe.EXIT_INTERRUPTED,
    )
    job_a = tmp_path / "outputs" / "probe"
    assert _points(job_a)["r1"]["status"] in {"valid", "valid-flagged"}
    projection = _project(runner.config, job_a)
    assert projection["jobs"]["a"]["accepted"] is False
    assert projection["jobs"]["a"]["status"] == "interrupted"
    assert any("signal_USR1" in reason for reason in projection["jobs"]["a"]["reasons"])
    assert projection["x1"]["outcome"] == "not-run"
    assert projection["q2"]["decision"] == "incomplete-re-probe"
    assert "total_gpu_hours" not in projection["q2"]
    assert "job a is not accepted" in projection["q2"]["reason"]
    assert projection["q1"]["decision"] == "incomplete-re-probe"
    # Section 10: A1 stability is still reported, from the job's own summary.
    summary = json.loads((job_a / "summary.json").read_text())
    reported = projection["a1_stability"]
    assert "reported only" in reported["source"]
    assert {k: v for k, v in reported.items() if k != "source"} == summary["a1_stability"]
    assert reported["valid"] == 3 and "noise_multiplier" in reported


def test_project_uses_no_point_of_a_job_without_a_summary(tmp_path: Path) -> None:
    config, job_a = _complete_job_a(tmp_path)
    assert _project(config, job_a)["q2"]["decision"] != "incomplete-re-probe"
    (job_a / "summary.json").unlink()  # the driver was killed before it finished
    projection = _project(config, job_a)
    assert projection["jobs"]["a"]["accepted"] is False
    assert "no summary.json" in projection["jobs"]["a"]["reasons"][0]
    assert projection["q2"]["decision"] == "incomplete-re-probe"
    assert projection["a1_stability"]["recorded"] is None
    assert projection["a1_stability"]["reason"] == "no summary.json"


def test_project_refuses_point_files_changed_after_the_summary(tmp_path: Path) -> None:
    config, job_a = _complete_job_a(tmp_path)
    path = job_a / "points" / "a2.json"
    record = json.loads(path.read_text())
    record["result"]["request_throughput"] *= 10
    path.write_text(json.dumps(record))
    projection = _project(config, job_a)
    assert projection["jobs"]["a"]["accepted"] is False
    assert any("a2" in reason for reason in projection["jobs"]["a"]["reasons"])
    assert projection["q2"]["decision"] == "incomplete-re-probe"


def test_project_recomputes_acceptance_from_the_summary(tmp_path: Path) -> None:
    config, job_a = _complete_job_a(tmp_path)
    path = job_a / "summary.json"
    original = json.loads(path.read_text())
    assert original["point_sha256"] == {
        p.stem: probe.sha256_file(p) for p in (job_a / "points").glob("*.json")
    }
    # A recorded verdict that its own status and gates contradict is not trusted.
    edited = copy.deepcopy(original)
    edited["status"] = "interrupted"
    path.write_text(json.dumps(edited))
    assert _project(config, job_a)["jobs"]["a"]["accepted"] is False
    edited = copy.deepcopy(original)
    del edited["gates"]["G0.3"]
    path.write_text(json.dumps(edited))
    projection = _project(config, job_a)
    assert projection["jobs"]["a"]["accepted"] is False
    assert projection["q2"]["decision"] == "incomplete-re-probe"
    edited = copy.deepcopy(original)
    edited["exit_code"] = probe.EXIT_INTERRUPTED
    path.write_text(json.dumps(edited))
    assert _project(config, job_a)["jobs"]["a"]["accepted"] is False
    path.write_text(json.dumps(original))
    assert _project(config, job_a)["jobs"]["a"]["accepted"] is True


def test_project_uses_no_point_of_an_unaccepted_job_b(tmp_path: Path) -> None:
    config, job_a = _complete_job_a(tmp_path / "a")
    job_b = write_job_dir(tmp_path / "b", config, "b", _job_b_points())
    accepted = _project(config, job_a, job_b)
    assert accepted["jobs"]["b"]["accepted"] is True
    assert accepted["q1"]["decision"] in {"within-cap", "cut-turns-tokens-or-tasks-before-gauntlet"}
    crashed = write_job_dir(
        tmp_path / "b-crashed", config, "b", _job_b_points(), status="crashed", exit_code=1
    )
    projection = _project(config, job_a, crashed)
    assert projection["jobs"]["b"]["accepted"] is False
    assert projection["q1"]["decision"] == "incomplete-re-probe"
    assert "job b is not accepted" in projection["q1"]["reason"]
    # Section 10: B1 stability is reported from the crashed job's own summary.
    assert "admitted points" in accepted["b1_stability"]["source"]
    reported = projection["b1_stability"]
    assert "reported only" in reported["source"]
    assert reported["metric"] == "completions_per_s" and reported["valid"] == 3
    assert reported["noise_multiplier"] == accepted["b1_stability"]["noise_multiplier"]
    assert _project(config, job_a)["b1_stability"] is None  # job b not supplied


def test_project_admits_a_job_only_when_the_lane_recorded_a_clean_exit(tmp_path: Path) -> None:
    # Section 5: the lane's termination.env must record reason=completed, exit_code=0.
    config, job_a = _complete_job_a(tmp_path / "a")
    termination = job_a.parent / probe.LANE_TERMINATION_FILE
    admitted = _project(config, job_a)
    assert admitted["jobs"]["a"]["accepted"] is True
    assert admitted["jobs"]["a"]["lane_termination"]["fields"]["reason"] == "completed"
    assert admitted["q2"]["decision"] != "incomplete-re-probe"
    refused_cases = {
        "missing": None,
        "timeout": "job_id=1\nreason=signal_TERM_checkpoint_missing\nexit_code=143\n",
        "failed": "job_id=1\nreason=completed\nexit_code=1\n",
        "repeated": "job_id=1\nreason=workload_failed\nreason=completed\nexit_code=0\n",
    }
    for case, text in refused_cases.items():
        termination.unlink(missing_ok=True)
        if text is not None:
            termination.write_text(text)
        projection = _project(config, job_a)
        assert projection["jobs"]["a"]["accepted"] is False, case
        assert any(probe.LANE_TERMINATION_FILE in r for r in projection["jobs"]["a"]["reasons"])
        assert projection["q2"]["decision"] == "incomplete-re-probe", case
        assert "reported only" in projection["a1_stability"]["source"], case
    # A link to another run's clean record is not this run's record.
    elsewhere = _lane_finished(tmp_path)
    termination.unlink()
    termination.symlink_to(elsewhere)
    assert _project(config, job_a)["jobs"]["a"]["accepted"] is False
    termination.unlink()
    _lane_finished(job_a.parent)
    assert _project(config, job_a)["jobs"]["a"]["accepted"] is True

    job_b = _job_b_points()
    clean = write_job_dir(tmp_path / "b", config, "b", job_b)
    assert _project(config, job_a, clean)["jobs"]["b"]["accepted"] is True
    unfinished = write_job_dir(tmp_path / "b-unfinished", config, "b", job_b, lane_finished=False)
    projection = _project(config, job_a, unfinished)
    assert projection["jobs"]["b"]["accepted"] is False
    assert projection["q1"]["decision"] == "incomplete-re-probe"
    killed = write_job_dir(
        tmp_path / "b-killed", config, "b", job_b, termination={"reason": "workload_failed"}
    )
    assert _project(config, job_a, killed)["jobs"]["b"]["accepted"] is False


def test_project_treats_an_unaccepted_job_c_as_not_run(tmp_path: Path) -> None:
    config, job_a = _complete_job_a(tmp_path / "a")
    rungs = {
        "c27-a1": {"status": "valid", "result": {"request_throughput": 0.5}},
        "c35-a1": {"status": "valid", "result": {"request_throughput": 3.0}},
    }
    job_c = write_job_dir(tmp_path / "c", config, "c", rungs)
    measured = _project(config, job_a, job_c=job_c)
    assert measured["q2"]["rungs"]["qwen3.5-27b"]["basis"].startswith("job-c open-loop ratio")
    interrupted = write_job_dir(
        tmp_path / "c-int", config, "c", rungs, status="interrupted", exit_code=3
    )
    projection = _project(config, job_a, job_c=interrupted)
    assert projection["jobs"]["c"]["accepted"] is False
    assert "treated as not run" in projection["budget_inputs"]["c"]
    for rung in ("qwen3.5-27b", "qwen3.5-35b-a3b"):
        assert projection["q2"]["rungs"][rung]["basis"].startswith("unmeasured")
    assert projection["q2"]["rungs"]["qwen3.5-27b"]["multiplier"] == pytest.approx(4.5)


def test_job_c_gate_needs_an_accepted_job_a_with_an_x1_pass(tmp_path: Path) -> None:
    config = load_config(CONFIG_PATH)
    passing = write_job_dir(tmp_path / "pass", config, "a", x1_passing_job_a_points())
    assert probe.job_c_gate(config, passing)["submit"] is True
    interrupted = write_job_dir(
        tmp_path / "int", config, "a", x1_passing_job_a_points(), status="interrupted", exit_code=3
    )
    verdict = probe.job_c_gate(config, interrupted)
    assert verdict["submit"] is False and verdict["x1"]["outcome"] == "not-run"
    failing = x1_passing_job_a_points()
    failing["x1-a1"]["result"]["request_throughput"] = 2.5
    verdict = probe.job_c_gate(config, write_job_dir(tmp_path / "fail", config, "a", failing))
    assert verdict["submit"] is False and verdict["x1"]["outcome"] == "fail"
    unfinished = write_job_dir(
        tmp_path / "unfinished", config, "a", x1_passing_job_a_points(), lane_finished=False
    )
    verdict = probe.job_c_gate(config, unfinished)
    assert verdict["submit"] is False and verdict["x1"]["outcome"] == "not-run"


def test_g02_expects_exactly_one_gpu_whatever_the_lane_says(tmp_path: Path, monkeypatch) -> None:
    runner, _server, _engines = _runner(tmp_path)
    runner.output_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("COTCODEC_EXPECTED_GPUS", "2")
    commands: list[list[str]] = []

    class Done:
        pid = 0
        returncode = 0

        def __init__(self, command, **_kwargs):
            commands.append(list(command))

        def poll(self):
            return 0

    monkeypatch.setattr(probe.subprocess, "Popen", Done)
    report = probe.ProbeRunner._default_doctor(runner, tmp_path / "doctor.json", {})
    assert report["pass"] is False  # no report was written
    (command,) = commands
    assert command[command.index("--expected-gpus") + 1] == "1"


def test_offline_points_record_their_preparation_time(tmp_path: Path) -> None:
    model_root, receipt_root, pin = _metadata_snapshot(
        tmp_path, "qwen3-8b", "b968826d9c46dd6066d109eabc6255188de91218", "Qwen/Qwen3-8B"
    )
    receipt, root = pin.split(":")
    runner, _server, _engines = _runner(
        tmp_path,
        "b",
        pins={"qwen3-8b": (receipt, root)},
        model_root=model_root,
        receipt_root=receipt_root,
    )
    assert runner.run() == probe.EXIT_OK
    points = _points(tmp_path / "outputs" / "probe")
    assert all(record["prep_s"] >= 0.0 for record in points.values())
