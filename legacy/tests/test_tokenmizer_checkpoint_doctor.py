from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.validate_tokenmizer_checkpoint_experiment import (
    EXPECTED_STATUS,
    TokenMizerExperimentError,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_tokenmizer_contract_is_provider_free_and_claim_bounded() -> None:
    payload = validate_experiment_contract()
    assert payload["runtime"]["gpu_count_inside_container"] == 0
    assert payload["intervention"]["provider_calls"] == 0
    assert payload["expected_falsification"]["status"] == EXPECTED_STATUS
    assert payload["admission"]["active_inactive_h100_actor"] == (
        "forbidden-for-this-revision"
    )
    assert payload["admission"]["context_compaction_actor"] == (
        "requires-separate-quality-contract"
    )


def test_tokenmizer_container_contract_is_locked_down() -> None:
    dockerfile = (
        PROJECT_ROOT / "infra/memory-baselines/tokenmizer/Dockerfile"
    ).read_text(encoding="utf-8")
    assert "USER 65532:65532" in dockerfile
    assert 'org.cotcodec.discovery-only="true"' in dockerfile
    assert "sudo" not in dockerfile


def test_tokenmizer_source_drift_is_rejected(tmp_path: Path) -> None:
    source = PROJECT_ROOT / "experiments/memory/stage3-tokenmizer-checkpoint-doctor.yaml"
    target = tmp_path / source.name
    shutil.copyfile(source, target)
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            "131e3d1569de3e8f70c198ade4e791b47f63dc41",
            "0" * 40,
        ),
        encoding="utf-8",
    )
    with pytest.raises(TokenMizerExperimentError, match="source contract drifted"):
        validate_experiment_contract(target)
