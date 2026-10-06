from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.memory_trials.schema import canonical_json, sha256_text
from scripts import compare_memory_lifecycle_runs as comparator


def _fixture_bundle(root: Path, runtime: str) -> None:
    root.mkdir()
    for filename in comparator.SEMANTIC_FILENAMES:
        (root / filename).write_text(f"sealed {filename}\n")
    (root / "report.json").write_text(
        json.dumps(
            {
                "runtime": runtime,
                "runtime_receipt": {"profile": runtime},
                "roots": {"trace": "a" * 64},
                "gates": {"all": True},
            }
        )
        + "\n"
    )


def test_cross_runtime_comparison_is_hashed_and_fails_on_semantic_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    _fixture_bundle(left, "host")
    _fixture_bundle(right, "container")

    def validated(root: Path) -> dict[str, str]:
        return {
            "manifest_sha256": ("1" if root == left else "2") * 64,
            "experiment_sha256": "3" * 64,
            "code_root_sha256": "4" * 64,
        }

    monkeypatch.setattr(comparator, "load_and_validate_output", validated)
    result = comparator.compare_lifecycle_outputs(left, right)
    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    digest = result.pop("comparison_sha256")
    assert digest == sha256_text(canonical_json(result))

    (right / "traces.jsonl").write_text("different trace\n")
    drifted = comparator.compare_lifecycle_outputs(left, right)
    assert drifted["status"] == "FAIL"
    assert drifted["gates"]["semantic_artifacts_byte_equal"] is False


def test_comparison_output_is_no_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "comparison.json"
    comparator._write_once(output, {"status": "PASS"})
    with pytest.raises(FileExistsError):
        comparator._write_once(output, {"status": "PASS"})
