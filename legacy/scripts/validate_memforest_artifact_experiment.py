#!/usr/bin/env python3
"""Validate the exact MemForest published-artifact audit contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-memforest-published-artifact-audit.yaml"
)


class MemForestArtifactExperimentError(ValueError):
    """Raised when the registered MemForest artifact contract drifts."""


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MemForestArtifactExperimentError(
            f"cannot load MemForest artifact experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise MemForestArtifactExperimentError("MemForest experiment must be a mapping")
    return payload


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    """Require byte-semantically exact equality with the canonical contract."""
    payload = _load(path)
    expected = _load(DEFAULT_EXPERIMENT)
    if payload != expected:
        sections = sorted(set(payload) | set(expected))
        drifted = next(
            (section for section in sections if payload.get(section) != expected.get(section)),
            "contract",
        )
        raise MemForestArtifactExperimentError(f"MemForest {drifted} contract drifted")
    if (
        payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("execution", {}).get("h100_admission") != "not-granted-by-artifact-audit"
    ):
        raise MemForestArtifactExperimentError(
            "MemForest artifact audit must remain non-scientific and non-admitting"
        )
    return payload


def main() -> int:
    validate_experiment_contract()
    print("MemForest artifact experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
