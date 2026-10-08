"""v2's lane and timing manifests, its limits and caps, and the 4B lane's gates."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import statistics
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
LIMIT_RECHECK = TIMING_2_EVIDENCE.parent / "limit-recheck" / "estimator-sensitivity.json"
# D44's three estimates of the 4B lane, in increasing order, and the analyses' names for them.
ESTIMATES = {"stage_mean_scaling": "registered", "line_fit": "line_fit_compiles_as_registered",
             "per_stage_larger": "larger_of_the_two_per_stage"}


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
    assert lanes.registered_caps_total() == pytest.approx(0.2 + 32 / 60 + 0.2, abs=1e-6)
    assert round(lanes.registered_caps_total(), 3) == 0.933
    assert lanes.registered_caps_total() <= 1.5 + 1e-9
    measured = lanes.SMALL_LANE_MEASURED
    assert lanes.LANES["qwen3-0.6b-base"].minutes >= (
        2 * measured["evaluation_and_statistics_s"] + measured["start_up_s"]) / 60 + 3
    assert lanes.LANES["qwen3-0.6b-base"].minutes == 12
    # The 4B lane's evaluation time is measured on the fixed path by the second
    # timing job (Slurm 810, D42 (ii)); D44: three estimates are computed from it
    # and the limit is the largest of their minutes.
    large = lanes.LARGE_LANE_MEASURED
    assert large["measured"] is True and large["timing_job"] == lanes.LARGE_LANE_TIMING_JOB == "810"
    assert large["units"] == 1160 and all(s["length_ratio"] >= 1.0
                                          for s in lanes.LARGE_LANE_STAGES.values())
    stages = lanes.LARGE_LANE_STAGES
    scaled = {name: s["measured_unit_s"] * s["length_ratio"] for name, s in stages.items()}
    line = {name: s["line_fit_unit_s"] for name, s in stages.items()}
    assert all(line[name] >= s["measured_unit_s"] for name, s in stages.items())
    unit_s = {"stage_mean_scaling": scaled, "line_fit": line,
              "per_stage_larger": {name: max(scaled[name], line[name]) for name in stages}}
    estimates = lanes.LARGE_LANE_ESTIMATES
    assert list(estimates) == list(ESTIMATES) and large["estimates"] is estimates
    extra = large["compile_allowance_s"] + large["statistics_bound_s"]
    for name, per_unit in unit_s.items():
        total = sum(stages[stage]["units"] * per_unit[stage] for stage in stages) + extra
        assert estimates[name]["evaluation_and_statistics_s"] == pytest.approx(total)
        assert estimates[name]["minutes"] == lanes.limit_minutes(total, large["start_up_s"])
        # D36's "at least twice the measured time plus start-up" under every estimate.
        assert lanes.LANES["qwen3.5-4b-base"].minutes >= (
            2 * total + large["start_up_s"]) / 60 + 3
    assert [e["minutes"] for e in estimates.values()] == [30, 31, 32]
    assert lanes.LARGE_LANE_MINUTES == max(e["minutes"] for e in estimates.values()) == 32
    assert lanes.LARGE_LANE_LIMIT_ESTIMATE == large["limit_estimate"] == "per_stage_larger"
    assert large["evaluation_and_statistics_s"] == max(
        e["evaluation_and_statistics_s"] for e in estimates.values())
    assert lanes.LANES["qwen3.5-4b-base"].minutes == 32
    assert lanes.LANES["qwen3.5-4b-base"].cap_gpu_hours == 32 / 60
    # The useful window holds the lane at up to about 1.4 s per unit, more than
    # three times the slowest stage's measured mean.
    break_even = lanes.large_lane_break_even_unit_s()
    assert break_even == pytest.approx((29 * 60 - large["start_up_s"] - 5) / 1160)
    assert 3 * max(s["measured_unit_s"] for s in lanes.LARGE_LANE_STAGES.values()) <= break_even
    for lane in lanes.LANES.values():
        assert lane.cap_gpu_hours == lane.minutes / 60
        assert lane.minutes - dhd.USR1_LEAD_MINUTES >= dhd.MIN_USEFUL_MINUTES
        v1_lane = dhd.LANES[lane.lane_id]
        assert {k: v for k, v in lane.as_dict().items() if k not in ("minutes", "cap_gpu_hours")
                } == {k: v for k, v in v1_lane.as_dict().items()
                      if k not in ("minutes", "cap_gpu_hours")}


def test_the_4b_cap_is_its_minutes_exactly() -> None:
    """D44's cap is 32/60 GPU-h. A cap rounded to 0.5333 would be refused by the
    submitter (1 x 32 minutes is 0.53333 GPU-h) and by the filler's budget check."""

    lane = lanes.LANES["qwen3.5-4b-base"]
    manifest = _filled(TEMPLATES["qwen3.5-4b-base"])
    assert manifest["budget"]["max_gpu_hours"] == lane.cap_gpu_hours == 32 / 60
    assert submitter.validate_manifest(manifest, verify_claim_files=False)["max_gpu_hours"] == (
        32 / 60)
    rounded = copy.deepcopy(manifest)
    rounded["budget"]["max_gpu_hours"] = round(32 / 60, 4)
    with pytest.raises(ValueError, match="above budget"):
        submitter.validate_manifest(rounded, verify_claim_files=False)
    with pytest.raises(v1f.FillError, match="cap must be"):
        v1f.check_resources(rounded, lane, lane.minutes)


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
    # The analysis's rule is the stage-mean scaling estimate (30 minutes); D44
    # sets the limit at the largest of the three (limit-recheck/, 32 minutes).
    scaling = lanes.LARGE_LANE_ESTIMATES["stage_mean_scaling"]
    assert scaling["evaluation_and_statistics_s"] == pytest.approx(
        analysis["rule"]["evaluation_and_statistics_s"], abs=0.5)
    assert analysis["rule"]["minutes"] == scaling["minutes"] == 30
    assert analysis["rule"]["every_stage_measured"] is True
    recheck = json.loads(LIMIT_RECHECK.read_text(encoding="utf-8"))
    for stage, figures in lanes.LARGE_LANE_STAGES.items():
        assert figures["line_fit_unit_s"] == pytest.approx(recheck["rows"][stage]["line_unit_s"],
                                                           abs=5e-5)
    for name, key in ESTIMATES.items():
        row = recheck["estimators"][key]
        estimate = lanes.LARGE_LANE_ESTIMATES[name]
        assert estimate["stages_s"] == pytest.approx(row["stages_s"], abs=0.5)
        assert estimate["evaluation_and_statistics_s"] == pytest.approx(
            row["evaluation_and_statistics_s"], abs=0.5)
        assert estimate["minutes"] == row["minutes"]
    assert lanes.LARGE_LANE_MINUTES == max(recheck["estimators"][k]["minutes"]
                                           for k in ESTIMATES.values()) == 32
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


def test_the_4b_limits_estimator_sensitivity_is_disclosed() -> None:
    """Recomputed from Slurm 810's receipt: stage-mean scaling gives 30 minutes,
    the first analysis pass's line fit (compiles treated as registered) 31 and the
    larger of the two in every stage 32. D44 sets the limit at the largest. The
    registration says so, and says how the passes differ and when the scaling
    was chosen."""

    analysis = json.loads((TIMING_2_EVIDENCE / "analysis.json").read_text(encoding="utf-8"))
    timing = json.loads((TIMING_2_EVIDENCE / "dense-precheck_timing-receipt.json"
                         ).read_text(encoding="utf-8"))["timing"]
    check_unit = timing["attention_backend_check"]["unit"]
    proportional = line_fit = larger = 0.0
    spans = {}
    for stage in dhd.STAGES:
        units = [u for u in timing["units"] if u["stage"] == stage and u["unit"] != check_unit]
        median = statistics.median(u["seconds"] for u in units)
        regular = [u for u in units if u["seconds"] <= 5 * median]
        x = [float(u["context_tokens"]) for u in regular]
        y = [float(u["seconds"]) for u in regular]
        mx, my = sum(x) / len(x), sum(y) / len(y)
        sxx = sum((v - mx) ** 2 for v in x)
        slope = max(0.0, sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / sxx)
        row = analysis["per_stage"][stage]
        scaled = my * max(1.0, row["lane_tokens_mean"] / mx)
        line = max(my, my + slope * (row["lane_tokens_mean"] - mx))
        proportional += scaled * row["lane_units"]
        line_fit += line * row["lane_units"]
        larger += max(scaled, line) * row["lane_units"]
        spans[stage] = (min(x), max(x), slope)
    extra = analysis["compiles"]["allowance_s"] + 5.0
    start_up = analysis["rule"]["start_up_s"]
    assert proportional == pytest.approx(analysis["cross_checks"]["scaled_without_compiles_s"])
    minutes = [lanes.limit_minutes(s + extra, start_up) for s in (proportional, line_fit, larger)]
    assert minutes == [e["minutes"] for e in lanes.LARGE_LANE_ESTIMATES.values()] == [30, 31, 32]
    assert lanes.LARGE_LANE_MINUTES == max(minutes) == 32
    for estimate, stages_s in zip(lanes.LARGE_LANE_ESTIMATES.values(),
                                  (proportional, line_fit, larger), strict=True):
        assert estimate["stages_s"] == pytest.approx(stages_s, abs=0.5)
    assert (spans["A-main"][0], spans["A-main"][1]) == (3614, 3825)
    assert spans["A-main"][2] == pytest.approx(0.160e-3, abs=5e-7)
    assert spans["B-absent"][2] == pytest.approx(0.048e-3, abs=5e-7)
    text = (PROJECT_ROOT / "program" / "preregistrations" / f"{dv2.EXPERIMENT_ID}.md"
            ).read_text(encoding="utf-8")
    compute = " ".join(text[text.index("## Compute"):text.index("### The development timing jobs")
                            ].split())
    assert "differ only in how the two compiles are treated" not in compute
    assert "That pass differed from it in two ways" in compute
    assert f"the line gives {line_fit:.0f} s instead of {proportional:.0f} s" in compute
    assert "so 31 minutes, not 30" in compute and "only 211 tokens (3,614 to 3,825)" in compute
    assert "chosen after a first analysis pass, kept in the evidence, came out over D36's cap" in (
        compute)
    assert (f"{proportional:.0f} s over the stages and {proportional + extra:.0f} s of evaluation "
            "and statistics: 30 minutes") in compute
    assert f"{line_fit:.0f} s and {line_fit + extra:.0f} s: 31 minutes" in compute
    assert f"{larger:.0f} s and {larger + extra:.0f} s: 32 minutes" in compute
    assert "The 4B limit is the largest, 32 minutes (D44)" in compute
    assert "2 x 824 + 79 s is 29 minutes rounded up; with the 3-minute lead, 32 minutes" in compute
    decision_20 = " ".join(text[text.index("\n20. Limits"):text.index("\n21. ")].split())
    assert "is the conservative choice" not in decision_20
    assert "the line fit gives 31 minutes" in decision_20
    assert "came out over D36's cap" in decision_20
    for estimate in lanes.LARGE_LANE_ESTIMATES.values():
        assert (f"{estimate['evaluation_and_statistics_s']:.0f} s ({estimate['minutes']} minutes)"
                in decision_20)
    assert "D44 sets the limit at the largest, 32 minutes" in decision_20


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
