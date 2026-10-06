#!/usr/bin/env python3
"""Validate the exact Sage Wiki published-artifact audit contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-sage-wiki-published-artifact-audit.yaml"
)


class SageWikiArtifactExperimentError(ValueError):
    """Raised when the registered Sage Wiki artifact-audit contract drifts."""


def _expected() -> dict[str, Any]:
    path = DEFAULT_EXPERIMENT
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise SageWikiArtifactExperimentError(
            f"cannot load canonical Sage Wiki contract: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SageWikiArtifactExperimentError("canonical Sage Wiki contract must be a mapping")
    return payload


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise SageWikiArtifactExperimentError(
            f"cannot load Sage Wiki artifact experiment: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SageWikiArtifactExperimentError("Sage Wiki experiment must be a mapping")
    expected = _expected()
    if payload != expected:
        sections = sorted(set(payload) | set(expected))
        drifted = next(
            (
                section
                for section in sections
                if payload.get(section) != expected.get(section)
            ),
            "contract",
        )
        raise SageWikiArtifactExperimentError(f"Sage Wiki {drifted} contract drifted")
    if (
        payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
    ):
        raise SageWikiArtifactExperimentError(
            "Sage Wiki artifact audit cannot be scientific or publication ready"
        )
    return payload


def main() -> int:
    validate_experiment_contract()
    print("Sage Wiki artifact experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
