"""Lane manifest templates, the filler's budget accounting and the job-kind check."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from harness import dense_headroom_data as dhd
from scripts import fill_dense_headroom_precheck_manifests as filler
from scripts import run_dense_headroom_precheck as entry
from scripts import submit_docker_research_job as submitter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {lane: filler.TEMPLATE_DIR / name for lane, name in filler.TEMPLATES.items()}
FAKE = {"FILL-image-id": "sha256:" + "a" * 64, "FILL-image-git-sha": "b" * 40,
        "FILL-image-source-tar-sha256": "c" * 64, "FILL-preregistration-sha256": "d" * 64}
IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
SMALL, LARGE = dhd.LANES["qwen3-0.6b-base"], dhd.LANES["qwen3.5-4b-base"]


def _filled(lane: str) -> dict:
    text = TEMPLATES[lane].read_text(encoding="utf-8")
    for key, value in FAKE.items():
        text = text.replace(key, value)
    return yaml.safe_load(text)


def _job(run_root: Path, job_id: int, *, seconds: int, reason: str = "workload_failed",
         exit_code: str = "2", checkpoint: bool = False, predecessor: str = "none",
         receipt: bool = False, ended: bool = True) -> Path:
    """A job directory as the batch script leaves it (only the files the filler reads)."""

    path = run_root / str(job_id)
    path.mkdir(parents=True)
    minutes, rest = divmod(seconds, 60)
    (path / "job.env").write_text(f"job_id={job_id}\npredecessor_job_id={predecessor}\n"
                                  "started_at=2026-10-08T10:00:00Z\n", encoding="utf-8")
    if ended:
        (path / "termination.env").write_text(
            f"job_id={job_id}\nreason={reason}\nexit_code={exit_code}\n"
            f"finished_at=2026-10-08T10:{minutes:02d}:{rest:02d}Z\n"
            f"checkpoint_ready={'true' if checkpoint else 'false'}\n", encoding="utf-8")
    if checkpoint:
        (path / dhd.RESUME_SUBPATH).mkdir(parents=True)
        (path / dhd.RESUME_SUBPATH / "dev-artifact.sha256").write_text("e" * 64 + "\n")
    if receipt:
        (path / dhd.OUTPUT_SUBDIR).mkdir(parents=True, exist_ok=True)
        (path / dhd.OUTPUT_SUBDIR / "receipt.json").write_text("{}\n")
    return path


def _checkpointed(run_root: Path, job_id: int, seconds: int) -> Path:
    return _job(run_root, job_id, seconds=seconds, reason="signal_TERM_checkpoint_confirmed",
                exit_code="75", checkpoint=True)


@pytest.mark.parametrize("lane", sorted(dhd.LANES))
def test_templates_are_the_registered_lanes(lane) -> None:
    text = TEMPLATES[lane].read_text(encoding="utf-8")
    assert sorted(set(re.findall(r"FILL-[a-z0-9-]+", text))) == sorted(FAKE)
    assert not IP.search(text)
    manifest = _filled(lane)
    registered = dhd.LANES[lane]
    filler.check_resources(manifest, registered, registered.minutes)
    filler.check_against_template(manifest, yaml.safe_load(text), FAKE)
    command = manifest["command"]
    assert command[command.index("--expected-evidence-sha256") + 1] == dhd.SOURCE_BUNDLE_SHA256
    assert manifest["study_artifact"]["sha256"] == dhd.SOURCE_BUNDLE_SHA256
    assert manifest["study_artifact"]["size_bytes"] == 278_818_734
    assert command[command.index("--expected-receipt-sha256") + 1] == registered.receipt_sha256
    assert command[command.index("--model-dir") + 1].endswith(registered.model_id)
    assert command[command.index("--source-tokenizer") + 1] == (
        "/model-cache/cotcodec-models/qwen3-0.6b-base/tokenizer.json")
    assert command[command.index("--output-dir") + 1] == f"/outputs/{dhd.OUTPUT_SUBDIR}"
    assert command[command.index("--seeds") + 1 :] == ["42", "43", "44"]
    assert command[command.index("--preregistration") + 1] == (
        f"program/preregistrations/{dhd.EXPERIMENT_ID}.md")
    assert manifest["run_root"].endswith(f"/{dhd.EXPERIMENT_ID}/{lane}")


@pytest.mark.parametrize("lane", sorted(dhd.LANES))
def test_filled_templates_pass_the_submitters_validation(lane) -> None:
    validated = submitter.validate_manifest(_filled(lane), verify_claim_files=False)
    registered = dhd.LANES[lane]
    assert validated["gpus"] * validated["minutes"] / 60 <= validated["max_gpu_hours"]
    assert validated["max_gpu_hours"] == registered.cap_gpu_hours
    assert validated["container_profile"] == registered.container_profile
    assert validated["seed_binding"] == {"flag": "--seeds"}


def test_unfilled_templates_fail_closed() -> None:
    for path in TEMPLATES.values():
        with pytest.raises(ValueError):
            submitter.validate_manifest(yaml.safe_load(path.read_text()),
                                        verify_claim_files=False)


def test_the_filled_manifest_must_be_the_template() -> None:
    template = yaml.safe_load(TEMPLATES["qwen3.5-4b-base"].read_text(encoding="utf-8"))
    for mutate in (lambda m: m["command"].append("--device=cpu"),
                   lambda m: m["command"].__setitem__(m["command"].index("--evidence") + 1,
                                                      "/inputs/other.json"),
                   lambda m: m.__setitem__("run_root", "/home/kevin/cotcodec-runs/elsewhere"),
                   lambda m: m["resources"].__setitem__("cpus", 64),
                   lambda m: m["model"].__setitem__("cache_host_path", "/tmp/cache")):
        manifest = _filled("qwen3.5-4b-base")
        mutate(manifest)
        with pytest.raises(filler.FillError):
            filler.check_against_template(manifest, template, FAKE)


def test_check_resources_refuses_drift() -> None:
    manifest = _filled("qwen3.5-4b-base")
    for path, value in ((("resources", "gpus"), 2), (("resources", "minutes"), 30),
                        (("budget", "max_gpu_hours"), 0.5), (("container_profile",), "default"),
                        (("seeds",), [1, 2, 3])):
        tampered = yaml.safe_load(yaml.safe_dump(manifest))
        target = tampered
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with pytest.raises(filler.FillError):
            filler.check_resources(tampered, LARGE, LARGE.minutes)
    other = yaml.safe_load(yaml.safe_dump(manifest))
    other["command"][other["command"].index("--lane") + 1] = "qwen3-0.6b-base"
    with pytest.raises(filler.FillError):
        filler.check_resources(other, LARGE, LARGE.minutes)


def test_budget_caps() -> None:
    filler.check_budget()
    total = sum(lane.gpus * lane.minutes / 60 for lane in dhd.LANES.values())
    assert total == pytest.approx(dhd.TOTAL_CAP_GPU_HOURS)


# --------------------------------------------------------------------------- #
# Every job of a lane counts against the lane's minutes
# --------------------------------------------------------------------------- #


def test_the_first_job_gets_the_lanes_minutes(tmp_path) -> None:
    plan = filler.plan_next_job(SMALL, tmp_path / "absent", None)
    assert (plan.kind, plan.minutes, plan.slot) == ("first", SMALL.minutes, 0)
    with pytest.raises(filler.FillError):
        filler.plan_next_job(SMALL, tmp_path / "absent", "1")


def test_a_re_run_gets_only_the_minutes_left(tmp_path) -> None:
    root = tmp_path / "lane"
    _job(root, 501, seconds=5, reason="foreign_gpu_process", exit_code="75")
    plan = filler.plan_next_job(SMALL, root, None)
    assert (plan.kind, plan.minutes, plan.charged_minutes) == ("re-run", SMALL.minutes - 2, 2)
    with pytest.raises(filler.FillError, match="confirmed signal checkpoint"):
        filler.plan_next_job(SMALL, root, "501")  # a prolog refusal is no checkpoint
    _job(root, 502, seconds=200)  # a void re-run that used 3 min 20 s: charged 5
    with pytest.raises(filler.FillError, match="INCOMPLETE"):
        filler.plan_next_job(SMALL, root, None)  # 9 - 2 - 5 = 2 < 3


def test_a_time_limit_interrupt_leaves_no_continuation(tmp_path) -> None:
    # SIGUSR1 arrives 3 minutes before the limit: at least limit - 3 minutes used.
    for lane in (SMALL, LARGE):
        root = tmp_path / lane.lane_id
        _job(root, 600, seconds=(lane.minutes - 3) * 60 + 10,
             reason="signal_USR1_checkpoint_confirmed", exit_code="75", checkpoint=True)
        with pytest.raises(filler.FillError, match="INCOMPLETE"):
            filler.plan_next_job(lane, root, "600")


def test_an_early_interrupt_continues_once(tmp_path) -> None:
    root = tmp_path / "lane"
    _checkpointed(root, 700, seconds=330)  # 5.5 minutes: charged 7
    plan = filler.plan_next_job(LARGE, root, "700")
    assert (plan.kind, plan.minutes, plan.predecessor_job_id) == ("continuation",
                                                                  LARGE.minutes - 7, "700")
    with pytest.raises(filler.FillError, match="latest"):
        filler.plan_next_job(LARGE, root, "699")
    _job(root, 701, seconds=60, predecessor="700")  # the continuation ran (and failed)
    with pytest.raises(filler.FillError, match="one continuation"):
        filler.plan_next_job(LARGE, root, "701")


def test_unended_jobs_and_receipts_stop_the_lane(tmp_path) -> None:
    running = tmp_path / "running"
    _job(running, 800, seconds=60, ended=False)
    with pytest.raises(filler.FillError, match="has not ended"):
        filler.plan_next_job(SMALL, running, None)
    done = tmp_path / "done"
    _job(done, 801, seconds=240, reason="completed", exit_code="0", receipt=True)
    with pytest.raises(filler.FillError, match="lane receipt"):
        filler.plan_next_job(SMALL, done, None)


def test_a_slot_is_claimed_once_whatever_the_output(tmp_path) -> None:
    root = tmp_path / "lane"
    _checkpointed(root, 900, seconds=120)
    continuation = filler.plan_next_job(LARGE, root, "900")
    manifest = filler.later_job_manifest(_filled("qwen3.5-4b-base"), continuation)
    text = yaml.safe_dump(manifest, sort_keys=False)
    claim = filler.claim_slot(root, LARGE, continuation, text, FAKE["FILL-image-id"])
    assert filler.claim_slot(root, LARGE, continuation, text, FAKE["FILL-image-id"]) == claim
    rerun = filler.plan_next_job(LARGE, root, None)
    rerun_text = yaml.safe_dump(filler.later_job_manifest(_filled("qwen3.5-4b-base"), rerun))
    with pytest.raises(filler.FillError, match="already claimed"):
        filler.claim_slot(root, LARGE, rerun, rerun_text, FAKE["FILL-image-id"])
    # Once another job has ended, the claimed continuation counts as the lane's one.
    _checkpointed(root, 901, seconds=30)
    with pytest.raises(filler.FillError, match="one continuation"):
        filler.plan_next_job(LARGE, root, "901")


# --------------------------------------------------------------------------- #
# The job refuses only manifests the filler cannot have produced
# --------------------------------------------------------------------------- #


def _job_root(tmp_path: Path, manifest: dict, *, resume_receipt: bool,
              checkpoint: bool) -> Path:
    """The container's /outputs for a submitted manifest (as the batch script writes it)."""

    validated = submitter.validate_manifest(manifest, verify_claim_files=False)
    root = tmp_path / "outputs"
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(json.dumps(validated, sort_keys=True))
    if resume_receipt:
        (root / "resume-receipt.json").write_text(json.dumps(
            {"schema_version": 1, "predecessor_job_id": validated["resume_from_job_id"],
             "resume_subpath": validated["resume_subpath"]}))
    if checkpoint:
        (root / dhd.RESUME_SUBPATH).mkdir(parents=True)
        (root / dhd.RESUME_SUBPATH / "dev-artifact.sha256").write_text("e" * 64 + "\n")
    return root


def _check(root: Path, lane: dhd.Lane) -> dict:
    return entry.check_batch_manifest(root, lane, list(dhd.SEEDS), lane.receipt_sha256,
                                      dhd.SOURCE_BUNDLE_SHA256,
                                      root / dhd.OUTPUT_SUBDIR / "checkpoints")


def test_a_filled_continuation_passes_the_jobs_manifest_check(tmp_path) -> None:
    runs = tmp_path / "runs"
    _checkpointed(runs, 950, seconds=300)
    plan = filler.plan_next_job(LARGE, runs, "950")
    manifest = filler.later_job_manifest(_filled("qwen3.5-4b-base"), plan)
    root = _job_root(tmp_path / "ok", manifest, resume_receipt=True, checkpoint=True)
    assert _check(root, LARGE) == {"kind": "continuation", "predecessor_job_id": "950",
                                   "minutes": plan.minutes}
    bare = _job_root(tmp_path / "bare", manifest, resume_receipt=False, checkpoint=True)
    with pytest.raises(entry.StartupError, match="resume receipt"):
        _check(bare, LARGE)
    empty = _job_root(tmp_path / "empty", manifest, resume_receipt=True, checkpoint=False)
    with pytest.raises(entry.StartupError, match="pinned development artifact"):
        _check(empty, LARGE)
    greedy = json.loads(json.dumps(manifest))
    greedy["resources"]["minutes"] = LARGE.minutes - 1
    over = _job_root(tmp_path / "over", greedy, resume_receipt=True, checkpoint=True)
    with pytest.raises(entry.StartupError, match="minutes"):
        _check(over, LARGE)


def test_fresh_jobs_pass_and_inconsistent_ones_are_refused(tmp_path) -> None:
    first = _job_root(tmp_path / "first", _filled("qwen3-0.6b-base"), resume_receipt=False,
                      checkpoint=False)
    assert _check(first, SMALL)["kind"] == "fresh"
    runs = tmp_path / "runs"
    _job(runs, 990, seconds=5, reason="foreign_gpu_process", exit_code="75")
    rerun = filler.later_job_manifest(_filled("qwen3-0.6b-base"),
                                      filler.plan_next_job(SMALL, runs, None))
    assert _check(_job_root(tmp_path / "rerun", rerun, resume_receipt=False,
                            checkpoint=False), SMALL)["minutes"] == SMALL.minutes - 2
    stale = _job_root(tmp_path / "stale", _filled("qwen3-0.6b-base"), resume_receipt=False,
                      checkpoint=True)
    with pytest.raises(entry.StartupError, match="checkpoints"):
        _check(stale, SMALL)
    too_long = _filled("qwen3-0.6b-base")
    too_long["resources"]["minutes"] = SMALL.minutes + 1
    too_long["budget"]["max_gpu_hours"] = 0.2
    with pytest.raises(entry.StartupError, match="minutes"):
        _check(_job_root(tmp_path / "long", too_long, resume_receipt=False, checkpoint=False),
               SMALL)


def test_filler_refuses_before_the_freeze(tmp_path) -> None:
    receipt = tmp_path / "image.json"
    receipt.write_text('{"image_id": "sha256:' + "a" * 64 + '", "git_sha": "' + "b" * 40
                       + '", "source_tar_sha256": "' + "c" * 64 + '"}')
    from scripts import preregister

    try:
        preregister.verify(dhd.EXPERIMENT_ID)
    except preregister.PreregistrationError:
        assert filler.main(["--lane", "qwen3-0.6b-base", "--image-receipt", str(receipt),
                            "--output", str(tmp_path / "out"),
                            "--run-root", str(tmp_path / "runs")]) == 2
    else:
        pytest.skip("the registration is frozen; the image commit checks apply instead")
