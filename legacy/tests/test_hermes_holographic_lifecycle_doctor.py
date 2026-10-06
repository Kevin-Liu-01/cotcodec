from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
import yaml

from scripts.validate_hermes_holographic_experiment import (
    DEFAULT_EXPERIMENT,
    HolographicExperimentError,
    validate_experiment_contract,
)

PROJECT_ROOT = DEFAULT_EXPERIMENT.parents[2]
HERMES_ROOT = PROJECT_ROOT / "raw/baselines/hermes-agent"
PLUGIN_ROOT = HERMES_ROOT / "plugins/memory/holographic"


def test_registered_holographic_lifecycle_contract_is_valid() -> None:
    payload = validate_experiment_contract()
    assert payload["expected_falsification"]["session_scoped_isolation_supported"] is False
    assert payload["admission"]["memory_lifecycle_h100"] == "forbidden-for-this-revision"


def test_holographic_contract_drift_fails_closed(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["admission"]["memory_lifecycle_h100"] = "allowed"
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(HolographicExperimentError, match="admission contract drifted"):
        validate_experiment_contract(path)


def test_pinned_native_store_restarts_and_retains_deleted_plaintext(tmp_path: Path) -> None:
    sys.path[:0] = [str(PLUGIN_ROOT), str(HERMES_ROOT)]
    from retrieval import FactRetriever
    from store import MemoryStore

    database = tmp_path / "memory-store.db"
    canary = "HOLOGRAPHIC_TEST_CANARY_43B9 Alice owns Project Zephyr"
    store = MemoryStore(database, hrr_dim=64)
    fact_id = store.add_fact(canary, category="project")
    assert store.add_fact(canary, category="project") == fact_id
    assert FactRetriever(store, hrr_weight=0.0).search("Project Zephyr")[0][
        "fact_id"
    ] == fact_id
    store.close()

    reopened = MemoryStore(database, hrr_dim=64)
    assert reopened.list_facts()[0]["content"] == canary
    assert reopened.remove_fact(fact_id) is True
    assert reopened.list_facts() == []
    reopened.close()
    assert canary.encode() in database.read_bytes()


def test_pinned_holographic_source_hashes_match_contract() -> None:
    payload = validate_experiment_contract()
    source = payload["source"]
    expected = {
        "license_sha256": HERMES_ROOT / "LICENSE",
        "hermes_state_sha256": HERMES_ROOT / "hermes_state.py",
        "store_sha256": PLUGIN_ROOT / "store.py",
        "retrieval_sha256": PLUGIN_ROOT / "retrieval.py",
        "holographic_sha256": PLUGIN_ROOT / "holographic.py",
        "provider_sha256": PLUGIN_ROOT / "__init__.py",
    }
    for field, path in expected.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source[field]
