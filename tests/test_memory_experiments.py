from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

import scripts.validate_reasoningbank_frozen_bank_experiment as frozen_bank_validator
from scripts.fetch_open_model import load_registry
from scripts.validate_memory_experiments import (
    DEFAULT_EXPERIMENT_DIR,
    MemoryExperimentError,
    validate_directory,
    validate_experiment_path,
    validate_memory_experiment,
)
from scripts.validate_memory_sources import MemorySourceError, load_and_validate


def test_live_memory_experiment_contracts_are_valid() -> None:
    paths = validate_directory(DEFAULT_EXPERIMENT_DIR)
    assert {path.name for path in paths} == {
        "stage3-astra-native-lifecycle-doctor.yaml",
        "stage3-activegraph-fork-lifecycle-doctor.yaml",
        "stage3-agenticow-branch-lifecycle-doctor.yaml",
        "stage3-agent-recall-scope-lifecycle-doctor.yaml",
        "stage3-allmem-topology-recovery-doctor.yaml",
        "stage0-oracle.yaml",
        "stage1-longmemeval-screen.yaml",
        "stage1-model-transport.yaml",
        "stage1-qwen-screen.yaml",
        "stage1-smollm2-smoke.yaml",
        "stage2-oss-baselines.yaml",
        "stage3-lifecycle-mechanism-screen.yaml",
        "stage3-hippo-retention-cross-tenant-doctor.yaml",
        "stage3-icarus-lifecycle-doctor.yaml",
        "stage3-jiuwen-memory-file-lifecycle-doctor.yaml",
        "stage3-langmem-native-lifecycle-doctor.yaml",
        "stage3-lightmem2-context-paging-doctor.yaml",
        "stage3-lightmem-offline-consolidation-doctor.yaml",
        "stage3-memoria-transactional-lifecycle-doctor.yaml",
        "stage3-gaama-graph-component-doctor.yaml",
        "stage3-gaama-h100-actor-screen.yaml",
        "stage3-gaama-natural-graph-doctor.yaml",
        "stage3-gbrain-brainbench-conformance-doctor.yaml",
        "stage3-graphiti-native-lifecycle-doctor.yaml",
        "stage3-magic-context-paging-doctor.yaml",
        "stage3-memforge-fresh-install-doctor.yaml",
        "stage3-memorybank-corrected-decay-doctor.yaml",
        "stage3-memorybank-corrected-decay-h100-screen.yaml",
        "stage3-mem0-native-lifecycle-doctor.yaml",
        "stage3-mnemosyne-lifecycle-doctor.yaml",
        "stage3-mnemosyne-cognitive-lifecycle-doctor.yaml",
        "stage3-mnemon-active-space-admission-doctor.yaml",
        "stage3-mnemon-static-space-h100-actor.yaml",
        "stage3-neo4j-preference-supersession-doctor.yaml",
        "stage3-neo4j-identical-tuple-flat-parity.yaml",
        "stage3-palimpsest-bitemporal-doctor.yaml",
        "stage3-shodh-tier-admission-doctor.yaml",
        "stage3-sodamem-published-artifact-audit.yaml",
        "stage3-reasoningbank-source-admission-doctor.yaml",
        "stage3-reasoningbank-frozen-bank-cpu-doctor.yaml",
        "stage3-sage-wiki-published-artifact-audit.yaml",
        "stage3-recmem-consolidation-doctor.yaml",
        "stage3-tokenmizer-checkpoint-doctor.yaml",
        "stage3-timem-core-doctor.yaml",
        "stage3-total-recall-lifecycle-doctor.yaml",
        "stage4-hermes-provider-conformance.yaml",
        "stage4-hermes-byterover-offline-doctor.yaml",
        "stage4-hermes-hindsight-lifecycle-doctor.yaml",
        "stage4-hermes-holographic-lifecycle-doctor.yaml",
        "stage4-hermes-observational-memory-lifecycle-doctor.yaml",
        "stage4-hermes-openviking-lifecycle-doctor.yaml",
        "stage4-supermemory-local-binary-doctor.yaml",
        "stage-b-past-sm01-checkpoint.yaml",
    }


def test_selected_generated_experiment_does_not_open_unrelated_evidence(
    tmp_path: Path,
) -> None:
    ledger = yaml.safe_load(
        (Path("research") / "memory-sources.yaml").read_text(encoding="utf-8")
    )
    ledger["sources"]["recmem"]["reproduction_receipt"]["artifact_path"] = (
        "data/results/does-not-exist/recmem.json"
    )
    ledger_path = tmp_path / "memory-sources.yaml"
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
    selected = DEFAULT_EXPERIMENT_DIR / "stage1-model-transport.yaml"

    assert validate_experiment_path(selected, ledger_path=ledger_path) == selected
    with pytest.raises(MemorySourceError, match="reproduction artifact is missing"):
        load_and_validate(ledger_path)


def test_routed_past_contract_is_valid_and_drift_fails_closed(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage-b-past-sm01-checkpoint.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["source"]["revision"] = "0" * 40
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="scientific contract drifted"):
        validate_directory(tmp_path)


def test_routed_lifecycle_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-lifecycle-mechanism-screen.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["source"]["episodes_per_active_slot_cell"] = 63
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="scientific contract drifted"):
        validate_directory(tmp_path)


def test_routed_gbrain_conformance_contract_fails_closed(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-gbrain-brainbench-conformance-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["gates"]["matched_pull_retrieval_arm_present"] = True
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="GBrain gates contract drifted"):
        validate_directory(tmp_path)


def test_routed_sage_wiki_artifact_contract_fails_closed(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-sage-wiki-published-artifact-audit.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["gates"]["binary_bound_to_revision"] = True
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="Sage Wiki gates contract drifted"):
        validate_directory(tmp_path)


def test_unrecognized_memory_experiment_schema_is_rejected(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage1-qwen-screen.yaml"
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    del payload["study_id"]
    path = tmp_path / source.name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="unrecognized memory experiment contract"):
        validate_directory(tmp_path)


def test_routed_timem_core_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-timem-core-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["admission"]["h100_actor"] = "allowed"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="admission contract drifted"):
        validate_directory(tmp_path)


def test_routed_hermes_provider_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage4-hermes-provider-conformance.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["providers"]["bundled"]["openviking"] = "native-service-reproduced"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="roster or evidence classes drifted"):
        validate_directory(tmp_path)


def test_routed_hermes_byterover_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage4-hermes-byterover-offline-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["admission"]["memory_lifecycle_h100"] = "allowed"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="claim boundary drifted"):
        validate_directory(tmp_path)


def test_routed_hermes_openviking_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage4-hermes-openviking-lifecycle-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["expected_falsification"]["physical_zero_plaintext_residue"] = True
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="falsification contract drifted"):
        validate_directory(tmp_path)


def test_routed_hermes_observational_memory_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = (
        DEFAULT_EXPERIMENT_DIR
        / "stage4-hermes-observational-memory-lifecycle-doctor.yaml"
    )
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["contract"]["sealed_bundled_roster_unchanged"] = False
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="lifecycle contract drifted"):
        validate_directory(tmp_path)


def test_routed_hermes_hindsight_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage4-hermes-hindsight-lifecycle-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["expected_falsification"]["physical_zero_plaintext_residue"] = True
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="falsification contract drifted"):
        validate_directory(tmp_path)


def test_routed_total_recall_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-total-recall-lifecycle-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["source"]["revision"] = "0" * 40
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="source contract drifted"):
        validate_directory(tmp_path)


def test_routed_mnemosyne_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-mnemosyne-lifecycle-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["admission"]["h100_actor"] = "allowed"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="admission contract drifted"):
        validate_directory(tmp_path)


def test_routed_mnemosyne_cognitive_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = (
        DEFAULT_EXPERIMENT_DIR / "stage3-mnemosyne-cognitive-lifecycle-doctor.yaml"
    )
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["admission"]["h100_actor"] = "allowed"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="admission contract drifted"):
        validate_directory(tmp_path)


def test_routed_icarus_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-icarus-lifecycle-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["admission"]["h100_actor"] = "allowed"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="H100 admission drifted"):
        validate_directory(tmp_path)


def test_routed_hippo_falsification_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-hippo-retention-cross-tenant-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["admission"]["active_inactive_h100"] = "allowed"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="H100 admission must stay forbidden"):
        validate_directory(tmp_path)


def test_routed_gaama_component_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-gaama-graph-component-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["contract"]["require_no_cross_task_edges"] = False
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="component contract drifted"):
        validate_directory(tmp_path)


def test_routed_gaama_natural_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-gaama-natural-graph-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["contract"]["test_sample_ids"].reverse()
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="retrieval contract drifted"):
        validate_directory(tmp_path)


def test_routed_gaama_actor_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-gaama-h100-actor-screen.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["execution"]["gpus"] = 8
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="execution contract drifted"):
        validate_directory(tmp_path)


def test_routed_graphiti_lifecycle_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-graphiti-native-lifecycle-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["source"]["revision"] = "0" * 40
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="source contract drifted"):
        validate_directory(tmp_path)


def test_routed_reasoningbank_source_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = (
        DEFAULT_EXPERIMENT_DIR / "stage3-reasoningbank-source-admission-doctor.yaml"
    )
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["release_findings"]["scaling_reward_label_is_inverted"] = False
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="findings drifted"):
        validate_directory(tmp_path)


def test_routed_reasoningbank_frozen_bank_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = (
        DEFAULT_EXPERIMENT_DIR
        / "stage3-reasoningbank-frozen-bank-cpu-doctor.yaml"
    )
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["admission"]["h100_admission"] = "allowed"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="admission contract drifted"):
        validate_directory(tmp_path)


def test_reasoningbank_frozen_bank_validator_rehashes_retained_run_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = frozen_bank_validator._sha_path

    def drift_execution_receipt(path: Path) -> str:
        if path.name == "execution-receipt.json":
            return "0" * 64
        return original(path)

    monkeypatch.setattr(
        frozen_bank_validator,
        "_sha_path",
        drift_execution_receipt,
    )
    with pytest.raises(
        frozen_bank_validator.ReasoningBankFrozenBankExperimentError,
        match="retained run file hash drifted",
    ):
        frozen_bank_validator._load_evidence()


def test_routed_magic_context_contract_is_valid_and_drift_fails_closed(
    tmp_path: Path,
) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage3-magic-context-paging-doctor.yaml"
    valid_path = tmp_path / source.name
    valid_path.write_bytes(source.read_bytes())
    assert validate_directory(tmp_path) == [valid_path]

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["admission"]["semantic_memory_h100"] = "allowed"
    valid_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="admission contract drifted"):
        validate_directory(tmp_path)


def test_non_string_external_contract_name_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unknown.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "name": ["not", "a", "route"]}),
        encoding="utf-8",
    )
    with pytest.raises(MemoryExperimentError, match="unrecognized memory experiment contract"):
        validate_directory(tmp_path)


def test_unpinned_model_is_rejected(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage1-qwen-screen.yaml"
    payload = copy.deepcopy(yaml.safe_load(source.read_text(encoding="utf-8")))
    payload["model"]["model_id"] = "mutable-latest"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="is not pinned"):
        validate_memory_experiment(
            path,
            model_ids=set(load_registry()["models"]),
            source_ids=set(load_and_validate()["sources"]),
        )


def test_nonfinite_gpu_budget_is_rejected(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage1-qwen-screen.yaml"
    payload = copy.deepcopy(yaml.safe_load(source.read_text(encoding="utf-8")))
    payload["execution"]["max_gpu_hours"] = float("nan")
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="must be finite"):
        validate_memory_experiment(
            path,
            model_ids=set(load_registry()["models"]),
            source_ids=set(load_and_validate()["sources"]),
        )


def test_candidate_count_cannot_silently_change_estimand(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage0-oracle.yaml"
    payload = copy.deepcopy(yaml.safe_load(source.read_text(encoding="utf-8")))
    payload["causal_design"]["candidates_per_episode"] = 2
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="exactly one candidate"):
        validate_memory_experiment(
            path,
            model_ids=set(load_registry()["models"]),
            source_ids=set(load_and_validate()["sources"]),
        )


def test_generated_source_version_cannot_silently_drift(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage0-oracle.yaml"
    payload = copy.deepcopy(yaml.safe_load(source.read_text(encoding="utf-8")))
    payload["source"]["generator_version"] = "memory-events-v2"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="must use memory-events-v3"):
        validate_memory_experiment(
            path,
            model_ids=set(load_registry()["models"]),
            source_ids=set(load_and_validate()["sources"]),
        )


def test_registered_family_split_contract_cannot_drift(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage0-oracle.yaml"
    payload = copy.deepcopy(yaml.safe_load(source.read_text(encoding="utf-8")))
    payload["source"]["split_contract"][
        "entity_and_value_namespaces_are_family_scoped"
    ] = False
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="family split contract drifted"):
        validate_memory_experiment(
            path,
            model_ids=set(load_registry()["models"]),
            source_ids=set(load_and_validate()["sources"]),
        )


def test_full_prefix_ceiling_cannot_enter_matched_budget(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage1-model-transport.yaml"
    payload = copy.deepcopy(yaml.safe_load(source.read_text(encoding="utf-8")))
    payload["diagnostic_ceiling"]["eligible_for_primary"] = True
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="diagnostic ceiling contract drifted"):
        validate_memory_experiment(
            path,
            model_ids=set(load_registry()["models"]),
            source_ids=set(load_and_validate()["sources"]),
            provider_model_ids={
                "gpt-5.6-sol",
                "claude-opus-5",
                "gemini-3.5-flash",
                "deepseek-v4-pro",
                "kimi-k2.6",
                "claude-fable-5",
            },
        )


def test_public_benchmark_hash_cannot_drift(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage1-longmemeval-screen.yaml"
    payload = copy.deepcopy(yaml.safe_load(source.read_text(encoding="utf-8")))
    payload["source"]["dataset_sha256"] = "0" * 64
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="differs from the source ledger"):
        validate_memory_experiment(
            path,
            model_ids=set(load_registry()["models"]),
            source_ids=set(load_and_validate()["sources"]),
        )


def test_public_benchmark_requires_frozen_bundle(tmp_path: Path) -> None:
    source = DEFAULT_EXPERIMENT_DIR / "stage1-longmemeval-screen.yaml"
    payload = copy.deepcopy(yaml.safe_load(source.read_text(encoding="utf-8")))
    payload["execution"]["require_frozen_selection_bundle"] = False
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(MemoryExperimentError, match="requires a frozen selection bundle"):
        validate_memory_experiment(
            path,
            model_ids=set(load_registry()["models"]),
            source_ids=set(load_and_validate()["sources"]),
        )
