"""v2's lane and timing manifests, its limits and caps, and the 4B lane's gates."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

from harness import dense_headroom_data as dhd
from harness import dense_headroom_v2 as dv2
from harness import dense_headroom_v2_lanes as lanes
from scripts import fill_dense_headroom_precheck_manifests as v1f
from scripts import fill_dense_headroom_precheck_v2_manifests as filler
from scripts import run_dense_headroom_precheck_v2 as entry
from scripts import submit_docker_research_job as submitter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {lane: filler.TEMPLATE_DIR / name for lane, name in filler.TEMPLATES.items()}
TIMING = filler.TEMPLATE_DIR / filler.TIMING_TEMPLATE
TIMING_2 = filler.TEMPLATE_DIR / filler.TIMING_TEMPLATES[2]
FAKE = {"FILL-image-id": "sha256:" + "a" * 64, "FILL-image-git-sha": "b" * 40,
        "FILL-image-source-tar-sha256": "c" * 64, "FILL-preregistration-sha256": "d" * 64}
IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
TIMING_2_EVIDENCE = (PROJECT_ROOT / "program" / "evidence" / "2026-10-08"
                     / "q3-dense-headroom-precheck-v2-build" / "timing-2" / "timing-810")


def _filled(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    for key, value in FAKE.items():
        text = text.replace(key, value)
    return yaml.safe_load(text)


def _v1_template(lane: str) -> dict:
    return yaml.safe_load((v1f.TEMPLATE_DIR / v1f.TEMPLATES[lane]).read_text(encoding="utf-8"))


@pytest.mark.parametrize("lane", sorted(lanes.LANES))
def test_lane_templates_are_v1s_lanes_on_v2s_entry_point(lane: str) -> None:
    text = TEMPLATES[lane].read_text(encoding="utf-8")
    assert not IP.search(text)
    assert sorted(set(re.findall(r"FILL-[a-z0-9-]+", text))) == sorted(FAKE)
    manifest = _filled(TEMPLATES[lane])
    registered = lanes.LANES[lane]
    v1f.check_resources(manifest, registered, registered.minutes)
    v1 = _v1_template(lane)
    # Everything but the name, limit, cap, run root, entry point and registration is v1's.
    for key in ("runtime", "container_profile", "randomness_contract", "seeds",
                "seed_binding", "model", "study_artifact"):
        assert manifest[key] == v1[key], key
    assert {k: v for k, v in manifest["resources"].items() if k != "minutes"} == {
        k: v for k, v in v1["resources"].items() if k != "minutes"}
    expected = [part.replace("scripts/run_dense_headroom_precheck.py",
                             "scripts/run_dense_headroom_precheck_v2.py")
                .replace(f"{dv2.V1_EXPERIMENT_ID}.md", f"{dv2.EXPERIMENT_ID}.md")
                for part in v1["command"]]
    expected[expected.index("--expected-preregistration-sha256") + 1] = "d" * 64
    assert manifest["command"] == expected
    assert manifest["run_root"].endswith(f"/{dv2.EXPERIMENT_ID}/{lane}")
    assert manifest["resources"]["minutes"] == registered.minutes
    assert manifest["budget"]["max_gpu_hours"] == registered.cap_gpu_hours
    validated = submitter.validate_manifest(manifest, verify_claim_files=False)
    assert validated["gpus"] * validated["minutes"] / 60 <= validated["max_gpu_hours"] + 1e-9


def test_the_timing_template_runs_the_4b_lane_with_the_timing_profile() -> None:
    text = TIMING.read_text(encoding="utf-8")
    assert sorted(set(re.findall(r"FILL-[a-z0-9-]+", text))) == sorted(filler.TIMING_VALUES)
    manifest = _filled(TIMING)
    filler.check_timing_resources(manifest)
    lane = _filled(TEMPLATES["qwen3.5-4b-base"])
    command = manifest["command"]
    assert command[command.index("--profile") + 1] == "timing"
    assert "--preregistration" not in command
    shared = [c for c in lane["command"] if c not in (
        "--preregistration", f"program/preregistrations/{dv2.EXPERIMENT_ID}.md",
        "--expected-preregistration-sha256", "d" * 64)]
    assert [c for c in command if c not in ("--profile", "timing")] == shared
    for key in ("model", "study_artifact", "container_profile", "seeds"):
        assert manifest[key] == lane[key]
    assert manifest["resources"]["minutes"] == lanes.TIMING_MINUTES == 6
    assert manifest["budget"]["max_gpu_hours"] == lanes.TIMING_CAP_GPU_HOURS == 0.1
    submitter.validate_manifest(manifest, verify_claim_files=False)


def test_the_second_timing_job_is_the_first_in_its_own_run_root() -> None:
    """D42 (ii): the fixed path's timing job runs the first's manifest in a fresh
    run root under its own name, so it is filled, claimed and charged apart."""

    first, second = _filled(TIMING), _filled(TIMING_2)
    filler.check_timing_resources(second)
    submitter.validate_manifest(second, verify_claim_files=False)
    assert set(filler.TIMING_TEMPLATES) == {1, 2} and filler.TIMING_TEMPLATES[1] == TIMING.name
    assert len(filler.TIMING_TEMPLATES) == lanes.TIMING_JOBS
    assert second["name"] == "q3-dense-headroom-v2-timing-2-4b" != first["name"]
    assert second["run_root"].endswith(f"/{dv2.EXPERIMENT_ID}/timing-2-qwen3.5-4b-base")
    assert second["run_root"] != first["run_root"]
    assert {k: v for k, v in second.items() if k not in ("name", "run_root")} == {
        k: v for k, v in first.items() if k not in ("name", "run_root")}
    text = TIMING_2.read_text(encoding="utf-8")
    assert not IP.search(text)
    assert sorted(set(re.findall(r"FILL-[a-z0-9-]+", text))) == sorted(filler.TIMING_VALUES)
    assert f"{filler.TEMPLATE_PREFIX}/{TIMING_2.name}" in filler.BOUND_PATHS


@pytest.mark.parametrize("job", [1, 2])
def test_each_timing_job_is_filled_once(tmp_path: Path, job: int) -> None:
    image = tmp_path / "receipt.json"
    image.write_text(json.dumps({"image_id": FAKE["FILL-image-id"],
                                 "git_sha": FAKE["FILL-image-git-sha"],
                                 "source_tar_sha256": FAKE["FILL-image-source-tar-sha256"]}))
    run_root = tmp_path / "timing-root"
    target = filler.fill_timing(image, tmp_path / "out", run_root=run_root, job=job)
    assert target.name == filler.TIMING_TEMPLATES[job]
    assert (run_root / "fill-claims" / "after-0.json").is_file()
    assert not re.findall(r"FILL-[a-z0-9-]+", target.read_text())
    with pytest.raises(filler.FillError, match="allows one"):
        filler.fill_timing(image, tmp_path / "other", run_root=run_root, job=job)
    with pytest.raises(filler.FillError, match="no development timing job"):
        filler.fill_timing(image, tmp_path / "third", run_root=tmp_path / "r3", job=3)


def test_limits_follow_d36_and_fit_the_cap() -> None:
    filler.check_budget()
    assert lanes.TOTAL_CAP_GPU_HOURS == 1.5
    assert lanes.registered_caps_total() == pytest.approx(0.90)
    assert lanes.registered_caps_total() <= 1.5 + 1e-9
    measured = lanes.SMALL_LANE_MEASURED
    assert lanes.LANES["qwen3-0.6b-base"].minutes >= (
        2 * measured["evaluation_and_statistics_s"] + measured["start_up_s"]) / 60 + 3
    assert lanes.LANES["qwen3-0.6b-base"].minutes == 12
    # The 4B lane's evaluation time is measured on the fixed path by the second
    # timing job (Slurm 810, D42 (ii)) and enters D36's arithmetic once.
    large = lanes.LARGE_LANE_MEASURED
    assert large["measured"] is True and large["timing_job"] == lanes.LARGE_LANE_TIMING_JOB == "810"
    assert large["evaluation_and_statistics_s"] == pytest.approx(
        sum(s["units"] * s["measured_unit_s"] * s["length_ratio"]
            for s in lanes.LARGE_LANE_STAGES.values())
        + large["compile_allowance_s"] + large["statistics_bound_s"])
    assert large["units"] == 1160 and all(s["length_ratio"] >= 1.0
                                          for s in lanes.LARGE_LANE_STAGES.values())
    assert lanes.LANES["qwen3.5-4b-base"].minutes >= (
        2 * large["evaluation_and_statistics_s"] + large["start_up_s"]) / 60 + 3
    assert lanes.LANES["qwen3.5-4b-base"].minutes == 30
    assert lanes.LANES["qwen3.5-4b-base"].cap_gpu_hours == 0.5
    # The useful window holds the lane at up to about 1.3 s per unit, three
    # times the slowest stage's measured mean.
    break_even = lanes.large_lane_break_even_unit_s()
    assert break_even == pytest.approx((27 * 60 - large["start_up_s"] - 5) / 1160)
    assert 3 * max(s["measured_unit_s"] for s in lanes.LARGE_LANE_STAGES.values()) <= break_even
    for lane in lanes.LANES.values():
        assert lane.cap_gpu_hours == pytest.approx(lane.minutes / 60, abs=1e-4)
        assert lane.minutes - dhd.USR1_LEAD_MINUTES >= dhd.MIN_USEFUL_MINUTES
        v1_lane = dhd.LANES[lane.lane_id]
        assert {k: v for k, v in lane.as_dict().items() if k not in ("minutes", "cap_gpu_hours")
                } == {k: v for k, v in v1_lane.as_dict().items()
                      if k not in ("minutes", "cap_gpu_hours")}


def test_the_4b_measurement_is_the_second_timing_jobs() -> None:
    """The lanes module's 4B figures are the committed analysis of Slurm 810's
    receipt, which ran the fixed path (cuDNN's attention off) at the code head."""

    analysis = json.loads((TIMING_2_EVIDENCE / "analysis.json").read_text(encoding="utf-8"))
    for stage, figures in lanes.LARGE_LANE_STAGES.items():
        row = analysis["per_stage"][stage]
        assert figures["units"] == row["lane_units"]
        assert figures["measured_unit_s"] == pytest.approx(row["regular_mean_s"], abs=5e-5)
        assert figures["length_ratio"] == pytest.approx(row["length_ratio"], abs=5e-5)
    large = lanes.LARGE_LANE_MEASURED
    assert large["compile_allowance_s"] == pytest.approx(analysis["compiles"]["allowance_s"],
                                                         abs=0.05)
    assert large["start_up_s"] == pytest.approx(analysis["rule"]["start_up_s"], abs=0.05)
    assert large["evaluation_and_statistics_s"] == pytest.approx(
        analysis["rule"]["evaluation_and_statistics_s"], abs=0.5)
    assert analysis["rule"]["minutes"] == lanes.LARGE_LANE_MINUTES
    assert analysis["rule"]["every_stage_measured"] is True
    receipt = json.loads((TIMING_2_EVIDENCE / "dense-precheck_timing-receipt.json"
                          ).read_text(encoding="utf-8"))
    timing = receipt["timing"]
    assert (receipt["slurm_job_id"], receipt["slurm_job_id_source"]) == ("810", "job.env")
    assert receipt["profile"] == "timing" and timing["status"] == "TIMING_INTERRUPTED"
    assert timing["attention_backends"]["cudnn"] is False
    assert timing["attention_backends_after_check"]["cudnn"] is False
    assert timing["attention_backend_check"]["unit"] == "c320-q0"
    assert timing["backend_check_started_after_s"] < timing["evaluation_started_after_s"]
    assert timing["subset_complete"] is True
    assert len(timing["reference"]) == 5 and all(r["bitwise_equal"] for r in timing["reference"])
    assert timing["dev_artifact_matches_v1_job_730"] is True
    assert receipt["hashes"]["code"]["scripts/run_dense_headroom_precheck_v2.py"] == (
        hashlib.sha256((PROJECT_ROOT / "scripts" / "run_dense_headroom_precheck_v2.py"
                        ).read_bytes()).hexdigest())


def _small_receipt() -> dict:
    receipt = copy.deepcopy(dv2.load_v1_small_lane_receipt(PROJECT_ROOT))
    receipt.update({"experiment_id": dv2.EXPERIMENT_ID, "slurm_job_id": "900",
                    "slurm_job_id_source": "job.env"})
    receipt["hashes"]["preregistration_sha256"] = "d" * 64
    return receipt


def test_the_4b_lane_waits_on_both_reproductions(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    good = _small_receipt()
    path.write_text(json.dumps(good))
    assert filler.check_small_lane_receipt(path, "d" * 64, PROJECT_ROOT)["v1_job_727"] == (
        "REPRODUCED")
    with pytest.raises(filler.FillError):
        filler.check_small_lane_receipt(None, "d" * 64, PROJECT_ROOT)
    for mutate, message in (
        (lambda r: r.__setitem__("slurm_job_id", None), "not bound"),
        (lambda r: r.__setitem__("slurm_job_id_source", "none"), "not bound"),
        (lambda r: r["report"]["smoke_452_reproduction"].__setitem__("status", "FAILED"),
         "smoke"),
        (lambda r: r["report"]["headroom"].__setitem__(
            "h1_cx_points", r["report"]["headroom"]["h1_cx_points"] + 1e-3), "job-727"),
        (lambda r: r["hashes"].__setitem__("dev_artifact_sha256", "0" * 64), "job-727"),
        (lambda r: r.__setitem__("experiment_id", dv2.V1_EXPERIMENT_ID), "not a completed"),
    ):
        bad = copy.deepcopy(good)
        mutate(bad)
        path.write_text(json.dumps(bad))
        with pytest.raises(filler.FillError, match=message):
            filler.check_small_lane_receipt(path, "d" * 64, PROJECT_ROOT)


def test_v1_reproduction_lists_registered_fields_and_tolerance() -> None:
    v1 = dv2.load_v1_small_lane_receipt(PROJECT_ROOT)
    result = dv2.v1_reproduction(v1, v1)
    assert result["status"] == "REPRODUCED" and result["max_numeric_gap"] == 0.0
    assert result["fields"] == ["report", "decisions", "coverage", "artifact_counts",
                                "selectors", "attention_layers", "hashes.dev_artifact_sha256"]
    assert dv2.V1_REPRODUCTION_TOLERANCE == 1e-6
    assert v1["hashes"]["dev_artifact_sha256"] == dv2.V1_SMALL_LANE_ARTIFACT_SHA256
    shorter = copy.deepcopy(v1)
    shorter["selectors"] = shorter["selectors"][:-1]
    assert dv2.v1_reproduction(shorter, v1)["status"] == "FAILED"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module in ("harness", "scripts"):
                found.update(f"{node.module}.{alias.name}" for alias in node.names)
            else:
                found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return {name for name in found if name.split(".")[0] in ("harness", "scripts")}


def test_the_entry_points_code_files_are_its_project_import_closure() -> None:
    seen: set[str] = set()
    todo = ["scripts.run_dense_headroom_precheck_v2"]
    while todo:
        module = todo.pop()
        if module in seen:
            continue
        seen.add(module)
        path = PROJECT_ROOT / (module.replace(".", "/") + ".py")
        todo.extend(_imports(path) - seen)
    assert {name.replace(".", "/") + ".py" for name in seen} == set(entry.CODE_FILES)
