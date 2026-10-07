"""Lane manifest templates and the filler of the dense headroom pre-check."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from harness import dense_headroom_data as dhd
from scripts import fill_dense_headroom_precheck_manifests as filler
from scripts import submit_docker_research_job as submitter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {lane: filler.TEMPLATE_DIR / name for lane, name in filler.TEMPLATES.items()}
FAKE = {"FILL-image-id": "sha256:" + "a" * 64, "FILL-image-git-sha": "b" * 40,
        "FILL-image-source-tar-sha256": "c" * 64, "FILL-preregistration-sha256": "d" * 64}
IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def _filled(lane: str) -> dict:
    text = TEMPLATES[lane].read_text(encoding="utf-8")
    for key, value in FAKE.items():
        text = text.replace(key, value)
    return yaml.safe_load(text)


@pytest.mark.parametrize("lane", sorted(dhd.LANES))
def test_templates_are_the_registered_lanes(lane) -> None:
    text = TEMPLATES[lane].read_text(encoding="utf-8")
    assert sorted(set(re.findall(r"FILL-[a-z0-9-]+", text))) == sorted(FAKE)
    assert not IP.search(text)
    manifest = _filled(lane)
    registered = dhd.LANES[lane]
    filler.check_resources(manifest, registered, registered.minutes)
    command = manifest["command"]
    assert command[command.index("--expected-evidence-sha256") + 1] == dhd.SOURCE_BUNDLE_SHA256
    assert manifest["study_artifact"]["sha256"] == dhd.SOURCE_BUNDLE_SHA256
    assert manifest["study_artifact"]["size_bytes"] == 278_818_734
    assert command[command.index("--expected-receipt-sha256") + 1] == registered.receipt_sha256
    assert command[command.index("--model-dir") + 1].endswith(registered.model_id)
    assert command[command.index("--source-tokenizer") + 1] == (
        "/model-cache/cotcodec-models/qwen3-0.6b-base/tokenizer.json")
    assert command[command.index("--output-dir") + 1] == "/outputs/dense-precheck"
    assert command[command.index("--seeds") + 1 :] == ["42", "43", "44"]
    assert command[command.index("--preregistration") + 1] == (
        f"program/preregistrations/{dhd.EXPERIMENT_ID}.md")


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


def test_budget_and_continuation_rules() -> None:
    filler.check_budget()
    total = sum(lane.gpus * lane.minutes / 60 for lane in dhd.LANES.values())
    assert total == pytest.approx(dhd.TOTAL_CAP_GPU_HOURS)
    small = dhd.LANES["qwen3-0.6b-base"]
    assert filler.continuation_minutes(small, 4.2) == 9 - 6
    with pytest.raises(filler.FillError):
        filler.continuation_minutes(small, 5.5)


def test_check_resources_refuses_drift() -> None:
    lane = dhd.LANES["qwen3.5-4b-base"]
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
            filler.check_resources(tampered, lane, lane.minutes)
    other = yaml.safe_load(yaml.safe_dump(manifest))
    other["command"][other["command"].index("--lane") + 1] = "qwen3-0.6b-base"
    with pytest.raises(filler.FillError):
        filler.check_resources(other, lane, lane.minutes)


def test_filler_refuses_before_the_freeze(tmp_path) -> None:
    receipt = tmp_path / "image.json"
    receipt.write_text('{"image_id": "sha256:' + "a" * 64 + '", "git_sha": "' + "b" * 40
                       + '", "source_tar_sha256": "' + "c" * 64 + '"}')
    from scripts import preregister

    try:
        preregister.verify(dhd.EXPERIMENT_ID)
    except preregister.PreregistrationError:
        assert filler.main(["--lane", "qwen3-0.6b-base", "--image-receipt", str(receipt),
                            "--output", str(tmp_path / "out")]) == 2
    else:
        pytest.skip("the registration is frozen; the image commit checks apply instead")
