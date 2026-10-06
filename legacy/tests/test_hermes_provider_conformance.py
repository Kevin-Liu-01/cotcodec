from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_hermes_provider_conformance import (
    HERMES_GROUPS,
    _parse_junit,
)
from scripts.validate_hermes_provider_experiment import (
    EXPECTED_ROSTER,
    load_and_validate_experiment,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage4-hermes-provider-conformance.yaml"
)


def test_registered_hermes_provider_contract_is_valid() -> None:
    payload, digest = load_and_validate_experiment(EXPERIMENT)
    assert payload["gates"]["exact_provider_roster"] == EXPECTED_ROSTER
    assert len(digest) == 64


def test_every_bundled_provider_has_one_test_group() -> None:
    assert sorted(HERMES_GROUPS) == sorted(set(EXPECTED_ROSTER) - {"memori"})
    assert all(paths for paths in HERMES_GROUPS.values())


def test_junit_parser_counts_testcase_outcomes(tmp_path: Path) -> None:
    junit = tmp_path / "results.xml"
    junit.write_text(
        """<?xml version="1.0"?>
<testsuites><testsuite>
  <testcase name="pass" />
  <testcase name="fail"><failure /></testcase>
  <testcase name="error"><error /></testcase>
  <testcase name="skip"><skipped /></testcase>
</testsuite></testsuites>
""",
        encoding="utf-8",
    )
    assert _parse_junit(junit) == {
        "tests": 4,
        "passed": 1,
        "failed": 1,
        "errors": 1,
        "skipped": 1,
    }


def test_symlink_contract_is_rejected(tmp_path: Path) -> None:
    linked = tmp_path / "experiment.yaml"
    try:
        linked.symlink_to(EXPERIMENT)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="regular non-symlink"):
        load_and_validate_experiment(linked)
