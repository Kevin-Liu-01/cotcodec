from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from serving_probe_fakes import write_job_dir, x1_passing_job_a_points

from harness.serving_probe.config import load_config
from scripts import render_serving_probe_manifest as renderer
from scripts.submit_docker_research_job import sbatch_argv, validate_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = PROJECT_ROOT / "experiments" / "manifests" / "serving-throughput-probe-v1"
CONFIG = load_config(PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v1.yaml")


def _build_receipt(tmp_path: Path, variant: str = "cu129") -> Path:
    path = tmp_path / "build-receipt.json"
    path.write_text(
        json.dumps(
            {
                "kind": "vllm-overlay-build",
                "overlay_image_id": "sha256:" + "1" * 64,
                "git_sha": "2" * 40,
                "source_sha256": "3" * 64,
                "variant": variant,
            }
        )
    )
    return path


def _metadata_receipt(tmp_path: Path, model_id: str) -> Path:
    path = tmp_path / f"{model_id}.json"
    path.write_text(
        json.dumps(
            {
                "model_id": model_id,
                "mode": "metadata",
                "publication_eligible": False,
                "artifact_root_sha256": hashlib.sha256(model_id.encode()).hexdigest(),
            }
        )
    )
    return path


def _template(job: str) -> dict:
    return yaml.safe_load((TEMPLATES / f"{job}.template.yaml").read_text(encoding="utf-8"))


def _job_a_output(tmp_path: Path, **kwargs) -> Path:
    """A finished job A directory whose control X1 passed (the gate job C needs)."""
    return write_job_dir(tmp_path / "job-a", CONFIG, "a", x1_passing_job_a_points(), **kwargs)


def test_templates_are_rejected_by_the_lane_until_rendered() -> None:
    for job in ("a", "b", "c"):
        with pytest.raises(ValueError, match="image_id"):
            validate_manifest(_template(job), verify_claim_files=False)


@pytest.mark.parametrize("job", ["a", "b", "c"])
def test_rendered_manifests_pass_the_lane_and_bind_the_contract(tmp_path: Path, job: str) -> None:
    build = renderer.read_build_receipt(_build_receipt(tmp_path))
    pins = dict(
        renderer.read_metadata_receipt(_metadata_receipt(tmp_path, model))
        for model in CONFIG.job(job).pinned_models()
    )
    job_a = _job_a_output(tmp_path) if job == "c" else None
    manifest = renderer.render(_template(job), build=build, pins=pins, job_a_output=job_a)
    validated = validate_manifest(dict(manifest), verify_claim_files=False)
    contract_job = CONFIG.job(job)
    assert validated["minutes"] == contract_job.allocation_minutes
    assert validated["gpus"] * validated["minutes"] / 60 <= validated["max_gpu_hours"]
    assert manifest["container_profile"] == "vllm"
    assert manifest["seed_binding"] == {"flag": "--seeds"}
    command = manifest["command"]
    assert command[-4:] == ["--seeds", "42", "43", "44"]
    assert command[command.index("--image-variant") + 1] == "cu129"
    assert not any("memory" in part for part in command)
    for model in contract_job.pinned_models():
        receipt = tmp_path / f"{model}.json"
        receipt_sha = hashlib.sha256(receipt.read_bytes()).hexdigest()
        expected = f"{model}={receipt_sha}:{hashlib.sha256(model.encode()).hexdigest()}"
        assert expected in command
    argv = sbatch_argv(validated, test_only=True)
    assert f"--mem={manifest['resources']['memory_gb']}G" in argv
    assert "--test-only" in argv


def test_core_budget_matches_decision_d8() -> None:
    hours = {
        job: _template(job)["resources"]["minutes"] * _template(job)["resources"]["gpus"] / 60
        for job in ("a", "b", "c")
    }
    assert hours["a"] + hours["b"] == pytest.approx(1.0)
    assert hours["c"] == pytest.approx(0.5)


def test_render_refuses_missing_pins_wrong_receipts_and_drift(tmp_path: Path) -> None:
    build = renderer.read_build_receipt(_build_receipt(tmp_path))
    with pytest.raises(renderer.RenderError, match="no metadata receipt"):
        renderer.render(_template("b"), build=build, pins={})
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({"model_id": "qwen3-8b", "mode": "full", "publication_eligible": True})
    )
    with pytest.raises(renderer.RenderError, match="metadata-mode"):
        renderer.read_metadata_receipt(bad)
    wrong_kind = tmp_path / "wrong.json"
    wrong_kind.write_text(json.dumps({"kind": "source-overlay"}))
    with pytest.raises(renderer.RenderError, match="overlay build receipt"):
        renderer.read_build_receipt(wrong_kind)
    drifted = _template("a")
    drifted["resources"]["minutes"] = 30
    drifted["budget"]["max_gpu_hours"] = 0.5
    with pytest.raises(renderer.RenderError, match="allocation minutes"):
        renderer.render(drifted, build=build, pins={})
    wrong_seeds = _template("a")
    wrong_seeds["seeds"] = [1, 2, 3]
    with pytest.raises(renderer.RenderError, match="seeds"):
        renderer.render(wrong_seeds, build=build, pins={})
    wrong_model = _template("b")
    wrong_model["model"]["model_id"] = "qwen3.5-9b"
    pins = dict([renderer.read_metadata_receipt(_metadata_receipt(tmp_path, "qwen3-8b"))])
    with pytest.raises(renderer.RenderError, match="lane model"):
        renderer.render(wrong_model, build=build, pins=pins)
    default_profile = _template("a")
    default_profile["container_profile"] = "default"
    with pytest.raises(renderer.RenderError, match="vllm container profile"):
        renderer.render(default_profile, build=build, pins={})


def test_render_cli_writes_once(tmp_path: Path, capsys) -> None:
    output = tmp_path / "a.yaml"
    args = [
        "--template",
        str(TEMPLATES / "a.template.yaml"),
        "--build-receipt",
        str(_build_receipt(tmp_path, "cu130")),
        "--output",
        str(output),
    ]
    assert renderer.main(args) == 0
    rendered = yaml.safe_load(output.read_text())
    assert rendered["image_id"] == "sha256:" + "1" * 64
    assert rendered["command"][rendered["command"].index("--image-variant") + 1] == "cu130"
    assert output.read_text().startswith("# Rendered from")
    assert renderer.main(args) == 2
    assert "refusing to overwrite" in capsys.readouterr().err


def _job_c_pins(tmp_path: Path) -> dict:
    return dict(
        renderer.read_metadata_receipt(_metadata_receipt(tmp_path, model))
        for model in CONFIG.job("c").pinned_models()
    )


def test_job_c_renders_only_after_an_accepted_job_a_with_an_x1_pass(tmp_path: Path) -> None:
    # Design decisions 21 and 33: job C is submitted only after control X1 passed.
    build = renderer.read_build_receipt(_build_receipt(tmp_path))
    pins = _job_c_pins(tmp_path)
    with pytest.raises(renderer.RenderError, match="job A"):
        renderer.render(_template("c"), build=build, pins=pins)
    interrupted = write_job_dir(
        tmp_path / "interrupted",
        CONFIG,
        "a",
        x1_passing_job_a_points(),
        status="interrupted",
        exit_code=3,
    )
    with pytest.raises(renderer.RenderError, match="not accepted"):
        renderer.render(_template("c"), build=build, pins=pins, job_a_output=interrupted)
    failing = x1_passing_job_a_points()
    failing["x1-r1"]["result"]["e2el_ms"]["mean"] *= 1.2
    failed = write_job_dir(tmp_path / "failed", CONFIG, "a", failing)
    with pytest.raises(renderer.RenderError, match="X1 fail"):
        renderer.render(_template("c"), build=build, pins=pins, job_a_output=failed)
    rendered = renderer.render(
        _template("c"), build=build, pins=pins, job_a_output=_job_a_output(tmp_path)
    )
    assert rendered["command"][rendered["command"].index("--job") + 1] == "c"


def test_render_refuses_more_than_one_gpu(tmp_path: Path) -> None:
    build = renderer.read_build_receipt(_build_receipt(tmp_path))
    two = _template("a")
    two["resources"]["gpus"] = 2
    two["budget"]["max_gpu_hours"] = 2.0
    with pytest.raises(renderer.RenderError, match="exactly one GPU"):
        renderer.render(two, build=build, pins={})


def test_render_cli_takes_the_job_a_output_for_job_c(tmp_path: Path) -> None:
    receipts = [
        arg
        for model in CONFIG.job("c").pinned_models()
        for arg in ("--metadata-receipt", str(_metadata_receipt(tmp_path, model)))
    ]
    base = [
        "--template",
        str(TEMPLATES / "c.template.yaml"),
        "--build-receipt",
        str(_build_receipt(tmp_path)),
        *receipts,
    ]
    assert renderer.main([*base, "--output", str(tmp_path / "c-none.yaml")]) == 2
    job_a = ["--job-a-output", str(_job_a_output(tmp_path))]
    assert renderer.main([*base, *job_a, "--output", str(tmp_path / "c.yaml")]) == 0
