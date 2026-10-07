from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from harness.serving_probe_v2.config import load_config
from scripts import render_serving_probe_v2_manifest as renderer
from scripts.render_serving_probe_manifest import read_build_receipt
from scripts.submit_docker_research_job import sbatch_argv, validate_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    PROJECT_ROOT / "experiments" / "manifests" / "serving-throughput-probe-v2" / "a.template.yaml"
)
CONFIG = load_config(PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v2.yaml")


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


def _template() -> dict:
    return yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))


def test_template_is_rejected_by_the_lane_until_rendered() -> None:
    with pytest.raises(ValueError, match="image_id"):
        validate_manifest(_template(), verify_claim_files=False)


def test_rendered_manifest_passes_the_lane_and_binds_the_contract(tmp_path: Path) -> None:
    build = read_build_receipt(_build_receipt(tmp_path))
    manifest = renderer.render(_template(), build=build)
    validated = validate_manifest(dict(manifest), verify_claim_files=False)
    assert validated["minutes"] == CONFIG.job("a").allocation_minutes == 60
    assert validated["gpus"] * validated["minutes"] / 60 == pytest.approx(1.0)
    assert manifest["budget"]["max_gpu_hours"] == 1.0
    assert manifest["container_profile"] == "vllm"
    command = manifest["command"]
    assert command[:3] == ["python", "scripts/run_vllm_throughput_probe_v2.py", "run"]
    assert command[-4:] == ["--seeds", "42", "43", "44"]
    assert command[command.index("--image-variant") + 1] == "cu129"
    assert "--weights-pin" not in command
    argv = sbatch_argv(validated, test_only=True)
    assert "--test-only" in argv and f"--mem={manifest['resources']['memory_gb']}G" in argv


def test_render_refuses_drift(tmp_path: Path) -> None:
    build = read_build_receipt(_build_receipt(tmp_path))
    with pytest.raises(renderer.RenderError, match="cu130 is not in the v2 contract"):
        renderer.render(_template(), build=read_build_receipt(_build_receipt(tmp_path, "cu130")))
    for edit, message in (
        (lambda m: m["resources"].update(minutes=30), "allocation minutes"),
        (lambda m: m.update(seeds=[1, 2, 3]), "seeds"),
        (lambda m: m["resources"].update(gpus=2), "exactly one GPU"),
        (lambda m: m.update(container_profile="default"), "vllm container profile"),
        (lambda m: m.update(run_root="/home/kevin/cotcodec-runs/stage0/other/a"), "run_root"),
        (lambda m: m["command"].__setitem__(1, "scripts/run_vllm_throughput_probe.py"), "must run"),
        (lambda m: m["model"].update(model_id="qwen3-0.6b-base"), "lane model"),
    ):
        template = _template()
        edit(template)
        with pytest.raises(renderer.RenderError, match=message):
            renderer.render(template, build=build)


def test_render_cli_writes_once(tmp_path: Path, capsys) -> None:
    output = tmp_path / "a.yaml"
    args = [
        "--template",
        str(TEMPLATE),
        "--build-receipt",
        str(_build_receipt(tmp_path)),
        "--output",
        str(output),
    ]
    assert renderer.main(args) == 0
    assert output.read_text().startswith("# Rendered from")
    assert yaml.safe_load(output.read_text())["image_id"] == "sha256:" + "1" * 64
    assert renderer.main(args) == 2
    assert "refusing to overwrite" in capsys.readouterr().err


def test_overlay_build_checks_the_v2_plan_and_payload() -> None:
    dockerfile = (PROJECT_ROOT / "infra" / "research" / "Dockerfile.vllm-overlay").read_text()
    assert "python scripts/run_vllm_throughput_probe_v2.py plan --job a" in dockerfile
    builder = (PROJECT_ROOT / "scripts" / "build_vllm_overlay_on_h100.sh").read_text()
    assert "run_vllm_throughput_probe_v2.py vllm-args-doctor" in builder
    assert '"vllm-args-doctor-v2.json"' in builder and '"plan-job-a-v2.json"' in builder
