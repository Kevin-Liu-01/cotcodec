from __future__ import annotations

import math

import pytest

from harness.memory_trials.memorybank_decay import (
    DecayCandidate,
    retention_probability,
    score_candidates,
)
from scripts.run_memorybank_decay_container import _container_argv
from scripts.run_memorybank_decay_doctor import (
    STATUS,
    build_report,
)
from scripts.validate_memorybank_decay_experiment import (
    DEFAULT_EXPERIMENT,
    MemoryBankExperimentError,
    validate_experiment_contract,
)


def test_corrected_retention_is_monotonic_in_time_and_strength() -> None:
    assert retention_probability(0, 1) == 1.0
    assert retention_probability(10, 1) < retention_probability(5, 1)
    assert retention_probability(10, 1) < retention_probability(10, 4)
    assert 0 < retention_probability(10, 2) < 1


def test_upstream_precedence_expression_reverses_strength() -> None:
    assert retention_probability(
        10, 1, formula="upstream-precedence"
    ) > retention_probability(10, 4, formula="upstream-precedence")


def test_rank_is_deterministic_and_strength_can_preserve_old_relevant_item() -> None:
    items = (
        DecayCandidate("old", 20, 7, 1),
        DecayCandidate("recent", 1, 0, 0),
    )
    assert score_candidates(items) == score_candidates(items)
    assert score_candidates(items)[0].item_id == "old"
    assert score_candidates(items, formula="upstream-precedence")[0].item_id == "recent"


@pytest.mark.parametrize(
    ("elapsed", "strength"),
    [(-1, 1), (math.inf, 1), (1, 0), (1, math.nan)],
)
def test_invalid_retention_inputs_fail_closed(elapsed: float, strength: float) -> None:
    with pytest.raises(ValueError):
        retention_probability(elapsed, strength)


def test_doctor_report_is_explicitly_non_scientific_and_h100_blocked() -> None:
    report = build_report()
    assert report["status"] == STATUS
    assert all(report["checks"].values())
    assert report["scientific_result"] is False
    assert report["publication_ready"] is False
    assert report["h100_actor_admission"].startswith("blocked-")


def test_experiment_is_clean_room_cpu_only_and_h100_blocked() -> None:
    payload = validate_experiment_contract()
    assert payload["source"]["upstream_code_imported"] is False
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["runtime"]["provider_calls"] == 0
    assert payload["admission"]["h100_actor"].startswith("blocked-")


def test_experiment_drift_fails_closed(tmp_path) -> None:
    import yaml

    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["method"]["corrected_formula"] = "exp(-elapsed / 5 * strength)"
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryBankExperimentError, match="method contract drifted"):
        validate_experiment_contract(path)


def test_container_argv_is_networkless_nonroot_and_has_no_gpu() -> None:
    argv = _container_argv()
    assert argv[argv.index("--network") + 1] == "none"
    assert "--read-only" in argv
    assert argv[argv.index("--cap-drop") + 1] == "ALL"
    assert "no-new-privileges" in argv
    assert argv[argv.index("--user") + 1] == "65534:65534"
    assert "--gpus" not in argv
    assert "sudo" not in argv
