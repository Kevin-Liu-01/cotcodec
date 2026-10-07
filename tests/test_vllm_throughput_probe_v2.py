"""End-to-end tests of the v2 driver on CPU with a fake vLLM server and fake samplers."""

from __future__ import annotations

import copy
import json
import re
import shutil
import signal
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from serving_probe_fakes import WordTokenizer
from serving_probe_v2_fakes import (
    GPU_UUID,
    FakeApps,
    FakeEngine,
    FakeSampler,
    FakeVllmIds,
)

from harness.serving_probe_v2.config import load_config
from harness.serving_probe_v2.contamination import OTHER, UNRESOLVED, AppRow
from scripts import preregister
from scripts import run_vllm_throughput_probe as v1
from scripts import run_vllm_throughput_probe_v2 as probe

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v2.yaml"
#: CPU flags (front-end-bound, client-bound) can mark a point valid-flagged on a busy host.
VALID = {"valid", "valid-flagged"}
PREREG = PROJECT_ROOT / "program" / "preregistrations" / "serving-throughput-probe-v2.md"
V1_PREREG = PROJECT_ROOT / "program" / "preregistrations" / "serving-throughput-probe-v1.md"
ORDER = [
    "a-smoke",
    "a-warmup",
    "a1a",
    "r1",
    "r3",
    "r4",
    "a1b",
    "a1c",
    "r2",
    "a2",
    "f1",
    "x1-smoke",
    "x1-warmup",
    "x1-a1",
    "x1-r1",
]


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
    raw = copy.deepcopy(yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")))
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
    raw["sampling"]["apps_interval_s"] = 0.01
    raw["screenshot"] = {"width": 64, "height": 36}
    raw["budget"]["q2"]["image_tokens"] = 2040
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
        }.items():
            if key in point:
                point[key] = value
        if point.get("kind") == "replay" and point.get("role") != "warm-up":
            point["steps"] = 4 if point_id == "r3" else 2
            if point.get("a11y_tokens"):
                point["a11y_tokens"] = 6
            if point.get("start_depth"):
                point["start_depth"] = 2
        if point.get("role") == "warm-up":
            point["start_depth"] = 19
            point["steps"] = 1
            point["t_env_s"] = 0
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def _lane_outputs(root: Path, config, *, started: datetime | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    job = config.job("a")
    model = config.models[job.lane_model]
    (root / "provenance-verification.txt").write_text(json.dumps({"status": "PASS"}))
    (root / "container-doctor.txt").write_text("STATUS PASS mode=container\n")
    (root / "model-verification.txt").write_text(
        json.dumps(
            {
                "model_id": job.lane_model,
                "revision": model["revision"],
                "mode": "full",
                "artifact_root_sha256": model["artifact_root_sha256"],
            }
        )
    )
    stamp = (started or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    (root / "job.env").write_text(f"job_id=1\nstarted_at={stamp}\n")


def _doctor_pass(output: Path, env) -> dict[str, Any]:
    report = {"pass": True, "G0.2": {"pass": True}, "G0.3": {"pass": True}, "G0.4": {"pass": True}}
    output.write_text(json.dumps(report))
    return report


def _runner(
    tmp_path: Path,
    *,
    mode: str = "host",
    server: FakeVllmIds | None = None,
    config_path: Path | None = None,
    started: datetime | None = None,
    memory: float = 74301.0,
):
    config = load_config(config_path or _small_config(tmp_path))
    outputs = tmp_path / "outputs"
    if not (outputs / "job.env").exists():
        _lane_outputs(outputs, config, started=started)
    sampler = FakeSampler()
    apps = FakeApps(sampler, mode=mode)
    server = server or FakeVllmIds()
    engines: list[FakeEngine] = []

    def factory(phase, model_dir, log_path):
        engine = FakeEngine(server, model_dir, sampler, apps, memory=memory)
        engines.append(engine)
        return engine

    runner = probe.ProbeRunnerV2(
        config=config,
        job=config.job("a"),
        output_dir=outputs / "probe",
        outputs_root=outputs,
        model_root=tmp_path / "models",
        receipt_root=tmp_path / "receipts",
        pins={},
        image_variant="cu129",
        seeds=[42, 43, 44],
        argv=["test"],
        engine_factory=factory,
        sampler_factory=lambda path: sampler,
        apps_sampler_factory=lambda path, pids: apps,
        doctor=_doctor_pass,
        tokenizer_loader=lambda model_dir: WordTokenizer(),
        prereg_check=lambda config: {"experiment_id": config.experiment_id},
        marker_path=outputs / "checkpoint.ready",
    )
    return runner, server, sampler, apps


def _points(output: Path) -> dict[str, dict[str, Any]]:
    return {p.stem: json.loads(p.read_text()) for p in (output / "points").glob("*.json")}


def _summary(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / "outputs" / "probe" / "summary.json").read_text())


def _inject_during(runner, apps: FakeApps, sampler: FakeSampler, point_id: str, row: AppRow):
    """List ``row`` on the GPU (and add its memory) during ``point_id``'s first attempt."""
    original = runner._server_point
    calls = {"n": 0}

    def wrapped(point, *args, **kwargs):
        if point.point_id != point_id or calls["n"]:
            return original(point, *args, **kwargs)
        calls["n"] += 1
        sampler.set_memory(sampler.memory + float(row.used_mib or 0.0))
        apps.set_extra((row,))
        try:
            return original(point, *args, **kwargs)
        finally:
            apps.set_extra(())
            sampler.set_memory(sampler.memory - float(row.used_mib or 0.0))

    runner._server_point = wrapped


def test_job_a_runs_every_point_in_ledger_order(tmp_path: Path) -> None:
    runner, server, _sampler, _apps = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    summary = _summary(tmp_path)
    points = _points(tmp_path / "outputs" / "probe")
    assert sorted(points) == sorted(ORDER)
    assert {record["status"] for record in points.values()} <= {"valid", "valid-flagged"}
    launched = [d["point"] for d in summary["launch_decisions"] if d["launched"]]
    assert launched == ORDER
    assert summary["status"] == "complete"
    assert summary["acceptance"]["accepted"] is True
    for phase in ("real", "dummy-control"):
        verdict = summary["gates"]["G0.9"][phase]
        assert verdict["pass"] is True and verdict["mode"] == "pid"
        assert verdict["basis"].startswith("host-namespace PIDs")
        assert summary["gates"]["G0.8"][phase]["compute_apps"]["status"] == "empty"
    # Every measured point carries the v2 contamination checks, not v1's.
    for name in ORDER:
        checks = points[name]["checks"]
        assert "no_contamination" not in checks
        if name.endswith(("smoke", "warmup")):
            assert "no_foreign_process" not in checks
        else:
            assert checks["no_foreign_process"] and checks["no_unattributed_memory"]
    # Prompt token ids are digested request by request; replays use prebuilt history.
    identity = summary["x1"]["identity"]
    assert identity["a1a/x1-a1"]["identical"] and identity["r1/x1-r1"]["identical"]
    assert identity["r1/x1-r1"]["basis"] == "prompt-token-ids"
    assert summary["x1"]["outcome"] in {"pass", "fail", "underpowered"}
    assert all(body["return_token_ids"] for body in server.bodies)
    assert "text" not in json.dumps(points["r1"]["result"])
    assert not (tmp_path / "outputs" / "checkpoint.ready").exists()
    plan = json.loads((tmp_path / "outputs" / "probe" / "plan.json").read_text())
    assert plan["launch_window"]["worst_case_slack_minutes"] == pytest.approx(7.5)


def test_v1_false_contamination_does_not_recur_with_own_growth(tmp_path: Path) -> None:
    """v1: the engine grew from 74,301 to 76,611 MiB under 20-screenshot prompts.

    Here the engine's own footprint jumps to 76,611 MiB during r3 (after the
    warm-up's reservation). The only PID on the GPU is the engine's, so v2 keeps
    r3 valid and flags the growth; v1's rule would have rejected it.
    """
    runner, _server, sampler, apps = _runner(tmp_path)
    original = runner._server_point

    def grow(point, *args, **kwargs):
        if point.point_id == "r3":
            sampler.set_memory(76611.0)
            apps.engine_started(76611.0)
        return original(point, *args, **kwargs)

    runner._server_point = grow
    assert runner.run() == probe.EXIT_OK
    points = _points(tmp_path / "outputs" / "probe")
    r3 = points["r3"]
    assert r3["status"] == "valid-flagged"
    assert "own-footprint-above-reservation" in r3["flags"]
    assert r3["gpu"]["peak_memory_used_mib"] == 76611.0
    reservation = _summary(tmp_path)["gates"]["G0.9"]["real"]["device_mib"]
    assert reservation == 74301.0
    assert not v1.assess_point(
        r3["result"],
        counters=r3["counter_check"],
        gpu=r3["gpu"],
        reservation_mib=reservation,
        reservation_required=True,
        margin_mib=2048,
        api_cpu_pct=None,
        client_cpu_pct=None,
        flag_pct=90,
        stop_reason=None,
        ran_to_end=True,
        caches_ok=True,
        min_samples=1,
    )[2]["no_contamination"]


def test_a_foreign_pid_invalidates_a_point_and_its_rerun_waits_for_slack(tmp_path: Path) -> None:
    runner, _server, sampler, apps = _runner(tmp_path)
    foreign = AppRow(GPU_UUID, 99, "[Not Found]", 600.0, UNRESOLVED)
    _inject_during(runner, apps, sampler, "a1b", foreign)
    assert runner.run() == probe.EXIT_OK
    points = _points(tmp_path / "outputs" / "probe")
    a1b = points["a1b"]
    assert a1b["status"] in VALID
    first = a1b["superseded_attempts"][0]
    assert first["status"] == "invalid"
    assert first["checks"]["no_foreign_process"] is False
    assert first["contamination"]["foreign_pids"] == [99]
    # 600 MiB is far inside v1's 2,048 MiB device margin: only the PID rule sees it.
    assert first["gpu"]["peak_memory_used_mib"] < 74301.0 + 2048
    decisions = [(d["point"], d["kind"]) for d in _summary(tmp_path)["launch_decisions"]]
    # The rerun runs after every required first attempt (a1c), before optional points.
    assert decisions.index(("a1c", "required-first-attempt")) < decisions.index(("a1b", "rerun"))
    assert decisions.index(("a1b", "rerun")) < decisions.index(("r2", "optional"))
    assert [a["status"] in VALID for a in a1b["attempts"]] == [False, True]


def test_an_unlisted_foreign_process_is_unattributed_memory(tmp_path: Path) -> None:
    runner, _server, sampler, _apps = _runner(tmp_path)
    original = runner._server_point

    def hidden(point, *args, **kwargs):
        if point.point_id != "a1c":
            return original(point, *args, **kwargs)
        sampler.set_memory(sampler.memory + 1500.0)
        try:
            return original(point, *args, **kwargs)
        finally:
            sampler.set_memory(sampler.memory - 1500.0)

    runner._server_point = hidden
    assert runner.run() == probe.EXIT_OK
    a1c = _points(tmp_path / "outputs" / "probe")["a1c"]
    assert a1c["status"] == "invalid"
    assert a1c["checks"]["no_unattributed_memory"] is False
    assert a1c["checks"]["no_foreign_process"] is True
    # The hidden process stayed for the rerun too: both attempts are invalid.
    assert [attempt["status"] for attempt in a1c["attempts"]] == ["invalid", "invalid"]
    assert a1c["rerun_pending"] is False


def test_device_mode_when_nvml_lists_no_process(tmp_path: Path) -> None:
    runner, _server, sampler, _apps = _runner(tmp_path, mode="empty")
    assert runner.run() == probe.EXIT_OK
    summary = _summary(tmp_path)
    verdict = summary["gates"]["G0.9"]["real"]
    assert verdict["mode"] == "device"
    assert verdict["basis"] == "NVML lists no compute process in this container"
    points = _points(tmp_path / "outputs" / "probe")
    assert set(points["r3"]["checks"]) >= {"no_contamination"}
    assert points["r3"]["status"] in VALID


def test_device_mode_reservation_is_taken_after_the_largest_shape(tmp_path: Path) -> None:
    """Without attribution, own growth at the largest shape is inside the reservation."""
    runner, _server, sampler, _apps = _runner(tmp_path, mode="empty")
    original = runner._server_point

    def grow(point, *args, **kwargs):
        if point.point_id in {"a-warmup", "x1-warmup"}:
            sampler.set_memory(76611.0)
        return original(point, *args, **kwargs)

    runner._server_point = grow
    assert runner.run() == probe.EXIT_OK
    summary = _summary(tmp_path)
    assert summary["gates"]["G0.9"]["real"]["device_mib"] == 76611.0
    points = _points(tmp_path / "outputs" / "probe")
    assert points["r3"]["status"] in VALID
    assert points["r3"]["contamination"]["device_ceiling_mib"] == 76611.0 + 2048


def test_apps_query_failures_fall_back_to_device_mode(tmp_path: Path) -> None:
    runner, _server, _sampler, _apps = _runner(tmp_path, mode="broken")
    assert runner.run() == probe.EXIT_OK
    summary = _summary(tmp_path)
    assert summary["gates"]["G0.9"]["real"]["mode"] == "device"
    assert summary["gates"]["G0.8"]["real"]["compute_apps"]["status"] == "unavailable"


def test_a_process_listed_before_the_engine_starts_fails_g08(tmp_path: Path) -> None:
    runner, _server, _sampler, apps = _runner(tmp_path)
    apps.set_extra((AppRow(GPU_UUID, 77, "[Not Found]", 900.0, UNRESOLVED),))
    assert runner.run() == probe.EXIT_PRE_RESULT
    summary = _summary(tmp_path)
    verdict = summary["gates"]["G0.8"]["real"]
    assert verdict["pass"] is False and verdict["compute_apps"]["pids"] == [77]
    assert summary["acceptance"]["accepted"] is False


def test_a_container_process_outside_the_engine_fails_g09(tmp_path: Path) -> None:
    runner, _server, sampler, apps = _runner(tmp_path)
    _inject_during(runner, apps, sampler, "a-warmup", AppRow(GPU_UUID, 12, "python", 500.0, OTHER))
    original_reserve = runner._reserve

    def reserve_with_extra(record):
        apps.set_extra((AppRow(GPU_UUID, 12, "python", 500.0, OTHER),))
        try:
            return original_reserve(record)
        finally:
            apps.set_extra(())

    runner._reserve = reserve_with_extra
    assert runner.run() == probe.EXIT_PRE_RESULT
    summary = _summary(tmp_path)
    assert summary["gates"]["G0.9"]["real"]["pass"] is False
    assert "outside the engine" in summary["gates"]["G0.9"]["real"]["reason"]
    points = _points(tmp_path / "outputs" / "probe")
    assert points["r3"]["status"] == "not-run"


def test_reruns_and_optional_points_never_take_reserved_time(tmp_path: Path) -> None:
    """Started 38.8 min ago: the real phase's bound (40 min) is 1.2 min away.

    Every required first attempt still launches; a rerun (cap 1.5 min) and the
    optional points (caps 1.5 to 3.5 min) do not fit before the bound, so they
    are not launched, and the dummy-control phase keeps its 11 reserved minutes.
    """
    started = datetime.now(UTC) - timedelta(minutes=38, seconds=48)
    runner, _server, sampler, apps = _runner(tmp_path, started=started)
    _inject_during(runner, apps, sampler, "a1b", AppRow(GPU_UUID, 99, "[N]", 600.0, UNRESOLVED))
    assert runner.run() == probe.EXIT_OK
    summary = _summary(tmp_path)
    points = _points(tmp_path / "outputs" / "probe")
    for name in ("a-smoke", "a-warmup", "a1a", "r1", "r3", "r4", "a1c"):
        assert points[name]["status"] in VALID, name
    assert points["a1b"]["status"] == "invalid"
    assert points["a1b"]["rerun"] == "not launched: no slack"
    for name in ("r2", "a2", "f1"):
        assert points[name]["status"] == "not-run"
        assert points[name]["reason"] == "launch window: no slack for an optional point"
    for name in ("x1-smoke", "x1-warmup", "x1-a1", "x1-r1"):
        assert points[name]["status"] in VALID, name
    assert summary["status"] == "complete-with-cuts"
    assert summary["phases"]["real"]["reruns_not_launched"] == ["a1b"]


def test_a_failed_warmup_fails_g09_and_ends_the_job(tmp_path: Path) -> None:
    runner, _server, _sampler, _apps = _runner(tmp_path)
    original = runner._server_point

    def broken(point, *args, **kwargs):
        if point.get("role") == "warm-up":
            raise RuntimeError("engine died during the warm-up")
        return original(point, *args, **kwargs)

    runner._server_point = broken
    assert runner.run() == probe.EXIT_PRE_RESULT
    summary = _summary(tmp_path)
    assert summary["gates"]["G0.9"]["real"]["pass"] is False
    assert summary["pre_result_reason"] == "G0.9 failed in phase real"
    points = _points(tmp_path / "outputs" / "probe")
    assert points["a-warmup"]["status"] == "failed-infra"
    assert points["r3"]["status"] == "not-run"


def test_project_prices_q2_from_job_a_only(tmp_path: Path) -> None:
    runner, _server, _sampler, _apps = _runner(tmp_path)
    assert runner.run() == probe.EXIT_OK
    run_dir = tmp_path / "outputs"
    (run_dir / v1.LANE_TERMINATION_FILE).write_text(
        "job_id=1\nreason=completed\nexit_code=0\nfinished_at=2026-10-07T00:00:00Z\n"
    )
    projection = probe.project(
        runner.config,
        job_a=run_dir / "probe",
        prereg_check=lambda config: {"experiment_id": config.experiment_id, "sha256": "f" * 64},
    )
    assert projection["jobs"]["a"]["accepted"] is True
    assert projection["q1"]["decision"] == "not-projected"
    assert projection["q2"]["decision"] in {
        "rescope-before-gauntlet",
        "dossier-overestimated",
        "within-dossier-range",
    }
    assert len(projection["q2"]["cells"]) == 16
    rungs = projection["q2"]["rungs"]
    assert rungs["qwen3.5-27b"]["multiplier"] == pytest.approx(4.5)
    assert rungs["qwen3.5-35b-a3b"]["multiplier"] == pytest.approx(1.5)
    assert projection["code"]["digest"] == probe.probe_code_digest()["digest"]
    # A lane record that is not a clean exit keeps every point out of the budget.
    (run_dir / v1.LANE_TERMINATION_FILE).write_text("reason=workload_failed\nexit_code=1\n")
    refused = probe.project(runner.config, job_a=run_dir / "probe", prereg_check=lambda config: {})
    assert refused["q2"]["decision"] == "incomplete-re-probe"
    assert refused["x1"]["outcome"] == "not-run"


def test_acceptance_treats_g09_as_a_phase_gate() -> None:
    gates = {gate: {"pass": True} for gate in probe.JOB_GATES}
    gates["G0.9"] = {"dummy-control": {"pass": False, "reason": "x"}}
    verdict = probe.job_acceptance({"status": "complete", "gates": gates})
    assert verdict["accepted"] is True
    assert verdict["phase_gate_failures"] == {"dummy-control": ["G0.9"]}
    # v1's acceptance would have counted the per-phase G0.9 map as a failed job gate.
    assert v1.job_acceptance({"status": "complete", "gates": gates})["accepted"] is False


def test_run_cli_refuses_wrong_seeds_and_allocation(capsys) -> None:
    base = ["run", "--config", str(CONFIG_PATH), "--job", "a", "--output-dir", "/tmp/x"]
    assert probe.main([*base, "--allocation-minutes", "60", "--seeds", "1", "2", "3"]) == 2
    assert "differ from the contract's primary seeds" in capsys.readouterr().err
    assert probe.main([*base, "--allocation-minutes", "40", "--seeds", "42", "43", "44"]) == 2
    assert "differs from the contract's 60" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        probe.main(["run", "--conf", str(CONFIG_PATH)])


def test_plan_and_digest_cli(capsys) -> None:
    assert probe.main(["plan", "--job", "a"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["launch_window"]["reserved_minutes"] == pytest.approx(43.5)
    assert plan["required_points"]["dummy-control"] == ["x1-smoke", "x1-warmup", "x1-a1", "x1-r1"]
    assert plan["warmup_dominance"]["real"]["max_images"] == 20
    assert probe.main(["digest"]) == 0
    digest = json.loads(capsys.readouterr().out)
    assert digest["contract_sha256"] == v1.sha256_file(CONFIG_PATH)
    assert digest["digest"] == probe.probe_code_digest()["digest"]


# ---------------------------------------------------------------------------
# The registration, G0.0 binding, and v1 left untouched
# ---------------------------------------------------------------------------


def test_preregistration_names_the_live_contract_hash_and_code_digest() -> None:
    text = PREREG.read_text(encoding="utf-8")
    assert v1.sha256_file(CONFIG_PATH) in text
    code = probe.probe_code_digest()
    assert code["digest"] in text
    assert "harness/serving_probe_v2/contamination.py" in code["files"]
    assert "scripts/run_vllm_throughput_probe.py" in code["files"]


def test_v1_registration_and_code_digest_are_untouched() -> None:
    v1_text = V1_PREREG.read_text(encoding="utf-8")
    assert v1.probe_code_digest()["digest"] in v1_text
    assert "15b7a73b39dca0bf03959b8943450dc1d862ed6f5a158adcbca8fe763c817277" in v1_text
    v1_contract = PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v1.yaml"
    assert v1.sha256_file(v1_contract) in v1_text


def test_preregistration_reads_as_frozen_and_states_the_rules_as_coded() -> None:
    raw = PREREG.read_text(encoding="utf-8")
    text = " ".join(raw.split())
    status = raw.split("\n## 1.", 1)[0]
    assert "Status: frozen in program/preregistrations/ledger.jsonl" in status
    for stale in ("DRAFT", "Draft", "TBD", "TODO", "placeholder", "Not frozen", "not frozen"):
        assert stale not in raw, stale
    config = load_config(CONFIG_PATH)
    assert f"{config.job('a').allocation_minutes} minutes" in text
    assert "1.0 GPU-h" in text
    numbers = [int(n) for n in re.findall(r"^(\d+)\. \*\*", raw, flags=re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1)), "design decisions stay numbered in order"


def test_preregistration_draft_freezes_cleanly_and_the_gate_checks_the_ledger(
    tmp_path: Path,
) -> None:
    config = load_config(CONFIG_PATH)
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(probe.GateFailure, match="not frozen"):
        probe.verify_preregistration(config, ledger=ledger)
    row = preregister.freeze(PREREG, config.experiment_id, ledger=ledger, root=PROJECT_ROOT)
    assert probe.verify_preregistration(config, ledger=ledger)["sha256"] == row["sha256"]


def test_g00_refuses_edited_v1_or_v2_code_after_the_freeze(tmp_path: Path) -> None:
    config = load_config(CONFIG_PATH)
    root = tmp_path / "repo"
    for pattern in (*probe.PROBE_CODE_GLOBS, "program/preregistrations/*v2.md"):
        for path in PROJECT_ROOT.glob(pattern):
            target = root / path.relative_to(PROJECT_ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    ledger = tmp_path / "ledger.jsonl"
    prereg = root / config.preregistration
    preregister.freeze(prereg, config.experiment_id, ledger=ledger, root=root)
    assert probe.verify_preregistration(config, ledger=ledger, root=root)
    for edited in ("harness/serving_probe/budget.py", "harness/serving_probe_v2/x1.py"):
        path = root / edited
        saved = path.read_text()
        path.write_text(saved + "\n# edited after the freeze\n")
        with pytest.raises(probe.GateFailure, match="probe code digest"):
            probe.verify_preregistration(config, ledger=ledger, root=root)
        path.write_text(saved)


def test_a_signal_checkpoints_and_a_resumed_job_finishes(tmp_path: Path) -> None:
    runner, _server, _sampler, _apps = _runner(tmp_path)
    original = runner._server_point

    def interrupt(point, *args, **kwargs):
        if point.point_id == "r4":
            runner.note_signal("SIGUSR1")
        return original(point, *args, **kwargs)

    runner._server_point = interrupt
    assert runner.run() == probe.EXIT_INTERRUPTED
    marker = (tmp_path / "outputs" / "checkpoint.ready").read_text()
    assert marker.splitlines()[0] == "trigger=SIGUSR1"
    points = _points(tmp_path / "outputs" / "probe")
    assert points["r4"]["status"] == "interrupted"
    assert points["r3"]["status"] in VALID
    summary = _summary(tmp_path)
    assert summary["status"] == "interrupted" and summary["acceptance"]["accepted"] is False

    resumed, _server, _sampler, _apps = _runner(tmp_path, config_path=runner.config.path)
    assert resumed.run() == probe.EXIT_OK
    points = _points(tmp_path / "outputs" / "probe")
    assert {record["status"] for record in points.values()} <= {"valid", "valid-flagged"}
    summary = _summary(tmp_path)
    assert "r3" in summary["resumed_terminal_points"]
    launched = [d["point"] for d in summary["launch_decisions"] if d["launched"]]
    assert "r3" not in launched and "r4" in launched
