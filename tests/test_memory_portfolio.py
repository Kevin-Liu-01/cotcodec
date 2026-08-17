from __future__ import annotations

import copy

import pytest
import yaml

from scripts.validate_memory_portfolio import (
    DEFAULT_PORTFOLIO,
    MemoryPortfolioError,
    _blocked_lifecycle_contract,
    assert_revision_admitted,
    load_and_validate_portfolio,
)


def test_live_memory_portfolio_is_bound_and_contained() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    assert result["wave_count"] == 6
    assert result["candidate_count"] >= 25
    assert result["blocked_license_candidate_count"] >= 8
    assert result["portfolio_max_gpu_hours"] == 84
    assert len(result["matrix_sha256"]) == 64


def _write_portfolio(tmp_path, payload):
    path = tmp_path / "portfolio.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_portfolio_rejects_matrix_drift(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["matrix_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="differs from live source matrix"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_portfolio_rejects_unlicensed_import(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = copy.deepcopy(
        next(
            candidate
            for wave in payload["waves"]
            for candidate in wave["candidates"]
            if candidate["mode"] == "blocked-license"
        )
    )
    candidate["mode"] = "contained-import"
    candidate["status"] = "planned"
    candidate.pop("blocked_by")
    original = next(
        original
        for wave in payload["waves"]
        for original in wave["candidates"]
        if original["source_id"] == candidate["source_id"]
    )
    original.clear()
    original.update(candidate)
    with pytest.raises(MemoryPortfolioError, match="cannot reuse unresolved-license code"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_portfolio_rejects_uncontained_h100_wave(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(
        wave for wave in payload["waves"] if wave["compute_class"] == "contained-h100-screen"
    )
    wave["containment"] = "bare-host"
    with pytest.raises(MemoryPortfolioError, match="require docker-under-slurm"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_data_rights_block_cannot_be_executable(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "streammembench"
    )
    candidate["status"] = "planned"
    with pytest.raises(MemoryPortfolioError, match="licensed code and blocked status"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_safety_budget_funds_attack_and_defense_pair() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    safety = next(
        wave for wave in result["portfolio"]["waves"] if wave["id"] == "safety-and-governance"
    )
    capacity = int(safety["max_wave_gpu_hours"] // safety["max_gpu_hours_per_candidate"])
    assert safety["execution_order"][:capacity] == [
        "agentpoison",
        "owasp-agent-memory-guard",
    ]


def test_portfolio_rejects_unbound_total_gpu_budget(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["portfolio_max_gpu_hours"] = 109
    with pytest.raises(MemoryPortfolioError, match="must equal the finite wave ceilings"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_gaama_actor_negative_requires_bound_evidence(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["status"] == "actor-translation-killed"
    )
    candidate["evidence_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="actor negative differs from source receipt"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_fidelis_cpu_retrieval_requires_bound_evidence(tmp_path) -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    candidate = next(
        candidate
        for wave in result["portfolio"]["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "fidelis"
    )
    assert candidate["status"] == "cpu-retrieval-reproduced"

    payload = copy.deepcopy(result["portfolio"])
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "fidelis"
    )
    candidate["evidence_sha256"] = "0" * 64
    with pytest.raises(
        MemoryPortfolioError, match="CPU retrieval evidence differs from source receipt"
    ):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_sodamem_artifact_audit_requires_bound_non_reproduction_evidence(
    tmp_path,
) -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    candidates = [
        candidate
        for wave in result["portfolio"]["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "sodamem"
    ]
    assert len(candidates) == 2
    assert all(
        candidate["status"] == "artifact-audited-not-reproduced"
        for candidate in candidates
    )

    payload = copy.deepcopy(result["portfolio"])
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "sodamem"
    )
    candidate["evidence_sha256"] = "0" * 64
    with pytest.raises(
        MemoryPortfolioError, match="artifact audit differs from source receipt"
    ):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_sage_wiki_artifact_audit_requires_bound_non_reproduction_evidence(
    tmp_path,
) -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    candidate = next(
        candidate
        for wave in result["portfolio"]["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "sage-wiki"
    )
    assert candidate["status"] == "artifact-audited-not-reproduced"

    payload = copy.deepcopy(result["portfolio"])
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "sage-wiki"
    )
    candidate["evidence_sha256"] = "0" * 64
    with pytest.raises(
        MemoryPortfolioError, match="artifact audit differs from source receipt"
    ):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_gbrain_conformance_requires_bound_non_actor_evidence(tmp_path) -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    candidate = next(
        candidate
        for wave in result["portfolio"]["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "gbrain"
    )
    assert candidate["status"] == "source-admission-blocked"

    payload = copy.deepcopy(result["portfolio"])
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "gbrain"
    )
    candidate["evidence_sha256"] = "0" * 64
    with pytest.raises(
        MemoryPortfolioError, match="GBrain conformance differs from source receipt"
    ):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_portfolio_rejects_declared_ledger_drift(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["ledger"] = "research/not-the-validated-ledger.yaml"
    with pytest.raises(MemoryPortfolioError, match="declared ledger differs"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_collision_reference_cannot_enter_priority_queue(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["mode"] == "collision-reference"
    )
    candidate["priority"] = "primary"
    with pytest.raises(MemoryPortfolioError, match="must use boundary priority"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_discovery_kill_requires_bound_negative_evidence(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["status"] == "discovery-killed"
    )
    candidate["negative_evidence"]["receipt_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="artifact SHA-256 drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_discovery_kill_rejects_artifact_hash_drift(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["status"] == "discovery-killed"
    )
    candidate["negative_evidence"]["artifact_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="artifact SHA-256 drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_total_recall_kill_status_cannot_be_relabelled(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "total-recall-oss"
    )
    candidate["negative_evidence"]["status"] = (
        "PAST_SM01_RESTART_EQUIVALENCE_FALSIFIED"
    )
    with pytest.raises(MemoryPortfolioError, match="negative terminal status drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_killed_revision_cannot_be_reinserted_into_h100_queue(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(
        wave
        for wave in payload["waves"]
        if any(
            candidate["source_id"] == "total-recall-oss"
            for candidate in wave["candidates"]
        )
    )
    candidate = next(
        candidate
        for candidate in wave["candidates"]
        if candidate["source_id"] == "total-recall-oss"
    )
    candidate["status"] = "planned"
    candidate.pop("negative_evidence")
    wave["execution_order"].append("total-recall-oss")
    with pytest.raises(MemoryPortfolioError, match="cannot be relabelled or re-admitted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_direct_revision_admission_rejects_total_recall_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_NATIVE_RESTART"):
        assert_revision_admitted(
            result["portfolio"],
            "total-recall-oss",
            "a2630f671be9b12df8b8ac78df9d26f7053d2fa9",
        )


def test_direct_revision_admission_rejects_astra_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="BLOCKED_NONDETERMINISTIC_RECALL_ACCESS_ACCOUNTING",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "astra-working-set",
            "644f9d4e65f4e725996025834c91531592ab6166",
        )


def test_direct_revision_admission_rejects_mnemon_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="MNEMON_STATIC_ROUTING_KILLED"):
        assert_revision_admitted(
            result["portfolio"],
            "mnemon",
            "88d2981edeb18a5ebe048af472f6f96527615454",
        )


def test_direct_revision_admission_rejects_recmem_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_NON_IDEMPOTENT_WRITE"):
        assert_revision_admitted(
            result["portfolio"],
            "recmem",
            "a84252f6e5587fd4a8caac03ec9f6c732b7a7f35",
        )


def test_direct_revision_admission_rejects_hippo_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_CROSS_TENANT"):
        assert_revision_admitted(
            result["portfolio"],
            "hippo-memory",
            "4aeb04c68ff079ff1713c977ac4d2a96757cff44",
        )


def test_direct_revision_admission_rejects_mnemosyne_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="BLOCKED_CONSOLIDATED_FORGET_AND_NO_REACTIVATION",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "mnemosyne-oss",
            "a0e14243e04dbe3fc29287e58126ff5dc0e02b35",
        )


def test_direct_revision_admission_rejects_icarus_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="BLOCKED_NON_IDEMPOTENT_PROMOTION_AND_NO_NATIVE_PURGE",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "icarus-memory-infra",
            "6e348708dcddb7cf1ad47726cb287cd4c9183c40",
        )


def test_direct_revision_admission_rejects_graphiti_runtime_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="BLOCKED_FALKORDBLITE_ARM64_MODULE_ARCHITECTURE_MISMATCH",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "graphiti-native-lifecycle-adapter",
            "401c59a65bdeb22a44136901ff30231e6998a7fe",
        )


def test_direct_revision_admission_rejects_palimpsest_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="BLOCKED_BITEMPORAL_RESTART_AND_NO_NATIVE_PURGE",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "palimpsest-bitemporal-memory",
            "0f83e166b0512a5ca9f38c2559f68749b35e994d",
        )


def test_direct_revision_admission_rejects_tokenmizer_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="TOKENMIZER_ACTIVE_INACTIVE_ADMISSION_KILLED",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "tokenmizer",
            "131e3d1569de3e8f70c198ade4e791b47f63dc41",
        )


def test_direct_revision_admission_rejects_timem_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="TIMEM_CORE_RUNTIME_ADMISSION_KILLED",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "timem",
            "6d279a5f5d40ee229e1995df15c182cb2062c71c",
        )


def test_direct_revision_admission_rejects_graphiti_source_alias() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="BLOCKED_FALKORDBLITE_ARM64_MODULE_ARCHITECTURE_MISMATCH",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "graphiti",
            "401c59a65bdeb22a44136901ff30231e6998a7fe",
        )


def test_graphiti_killed_revision_requires_source_alias(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    record = next(
        record
        for record in payload["killed_revisions"]
        if record["source_id"] == "graphiti-native-lifecycle-adapter"
    )
    record.pop("source_aliases")
    with pytest.raises(MemoryPortfolioError, match="killed source aliases drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_hermes_provider_contract_cannot_drop_failed_probe(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["provider_conformance_contracts"]["hermes"]["failed_groups"].pop()
    with pytest.raises(MemoryPortfolioError, match="failed_groups drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_hermes_holographic_followup_cannot_be_upgraded(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["provider_conformance_contracts"]["hermes"]["native_followups"][
        "holographic"
    ]["status"] = "PASS"
    with pytest.raises(MemoryPortfolioError, match="native_followups drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_hermes_byterover_followup_cannot_be_upgraded(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["provider_conformance_contracts"]["hermes"]["native_followups"][
        "byterover"
    ]["status"] = "PASS"
    with pytest.raises(MemoryPortfolioError, match="native_followups drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_hermes_openviking_followup_cannot_be_upgraded(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["provider_conformance_contracts"]["hermes"]["native_followups"][
        "openviking"
    ]["status"] = "PASS"
    with pytest.raises(MemoryPortfolioError, match="native_followups drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_direct_revision_admission_rejects_holographic_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_GLOBAL_SESSION"):
        assert_revision_admitted(
            result["portfolio"],
            "hermes-holographic",
            "a90d5369f76c87c98547d2e283aa26d5cfabf322",
        )


def test_direct_revision_admission_rejects_openviking_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_NATIVE_PHYSICAL_PURGE"):
        assert_revision_admitted(
            result["portfolio"],
            "openviking",
            "eeff5a497360aa4481cf32e18a0d9376f4412f4c",
        )


def test_direct_revision_admission_rejects_byterover_killed_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_OFFLINE_DAEMON"):
        assert_revision_admitted(
            result["portfolio"],
            "hermes-byterover-cli",
            "1f4609c18ca735810860b3ba9178cae2dd8a67b0",
        )


def test_direct_revision_admission_rejects_mem0_blocked_pin() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_ADAPTER_CRASH_RECOVERY"):
        assert_revision_admitted(
            result["portfolio"],
            "mem0",
            "71f2ebefa3494da21550fb525216818776cde67f",
        )


def test_direct_revision_admission_rejects_mem0_lifecycle_alias() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_ADAPTER_CRASH_RECOVERY"):
        assert_revision_admitted(
            result["portfolio"],
            "mem0-lifecycle-adapter",
            "71f2ebefa3494da21550fb525216818776cde67f",
        )


def test_portfolio_requires_native_lifecycle_contracts(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload.pop("native_lifecycle_conformance_contracts")
    with pytest.raises(
        MemoryPortfolioError,
        match="Mem0, Supermemory, and Neo4j native lifecycle",
    ):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_mem0_lifecycle_contract_cannot_claim_h100_admission(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["native_lifecycle_conformance_contracts"]["mem0_lifecycle_adapter"][
        "h100_admission"
    ] = "allowed"
    with pytest.raises(MemoryPortfolioError, match="h100_admission drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_supermemory_lifecycle_contract_cannot_claim_h100_admission(
    tmp_path,
) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["native_lifecycle_conformance_contracts"]["supermemory_local_binary"][
        "h100_admission"
    ] = "allowed"
    with pytest.raises(MemoryPortfolioError, match="h100_admission drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_direct_revision_admission_rejects_supermemory_binary() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "supermemory",
            "82dae50ef458139823b3bfd3ebaaaac90ffd8a7c",
        )


def test_direct_release_revision_admission_rejects_supermemory_binary() -> None:
    result = load_and_validate_portfolio(DEFAULT_PORTFOLIO)
    with pytest.raises(
        MemoryPortfolioError,
        match="BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL",
    ):
        assert_revision_admitted(
            result["portfolio"],
            "supermemory",
            "39ef7e1e5ea01b34d2cdd1801d0d227d445a985d",
        )


def test_supermemory_release_revision_alias_is_blocked() -> None:
    release_revision = "39ef7e1e5ea01b34d2cdd1801d0d227d445a985d"
    repository = "https://github.com/supermemoryai/supermemory"
    contract = _blocked_lifecycle_contract(
        {
            "native_lifecycle_conformance_contracts": {
                "supermemory": {
                    "candidate_source_id": "supermemory",
                    "source_id": "supermemory",
                    "source_revision": "82dae50ef458139823b3bfd3ebaaaac90ffd8a7c",
                    "release_revision": release_revision,
                    "h100_admission": "blocked",
                    "status": "BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL",
                }
            }
        },
        {
            "supermemory": {"repositories": [{"url": repository}]},
            "supermemory-alias": {
                "repositories": [
                    {"url": repository, "revision": release_revision}
                ],
            },
        },
        source_id="supermemory-alias",
        revision=release_revision,
        repository=(repository, release_revision),
    )
    assert contract is not None
    assert contract["status"] == "BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL"


def test_cpu_lifecycle_blocked_candidate_cannot_enter_h100_execution_order(
    tmp_path,
) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(wave for wave in payload["waves"] if wave["id"] == "native-system-spine")
    wave["execution_order"].insert(0, "mem0")
    with pytest.raises(MemoryPortfolioError, match="executable candidate"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_mem0_status_relabel_cannot_readmit_blocked_revision(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(wave for wave in payload["waves"] if wave["id"] == "native-system-spine")
    candidate = next(
        candidate for candidate in wave["candidates"] if candidate["source_id"] == "mem0"
    )
    candidate["status"] = "planned"
    wave["execution_order"].insert(0, "mem0")
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_ADAPTER_CRASH_RECOVERY"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_mem0_mode_relabel_cannot_hide_blocked_revision(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(wave for wave in payload["waves"] if wave["id"] == "native-system-spine")
    candidate = next(
        candidate for candidate in wave["candidates"] if candidate["source_id"] == "mem0"
    )
    candidate["mode"] = "paper-reimplementation"
    candidate["status"] = "planned"
    candidate.pop("repository_role")
    wave["execution_order"].insert(0, "mem0")
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_ADAPTER_CRASH_RECOVERY"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_mem0_adapter_alias_cannot_readmit_blocked_revision(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(wave for wave in payload["waves"] if wave["id"] == "native-system-spine")
    wave["candidates"].append(
        {
            "source_id": "mem0-lifecycle-adapter",
            "mode": "contained-import",
            "repository_role": "reviewed-native-backend-target",
            "status": "planned",
            "priority": "primary",
            "scientific_role": "alias attack regression",
            "next_gate": "must remain blocked at the reproduced native revision",
        }
    )
    wave["execution_order"].insert(0, "mem0-lifecycle-adapter")
    with pytest.raises(MemoryPortfolioError, match="BLOCKED_ADAPTER_CRASH_RECOVERY"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_neo4j_lifecycle_contract_cannot_drift_report(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    payload["native_lifecycle_conformance_contracts"]["neo4j_agent_memory"][
        "report_sha256"
    ] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="report_sha256 drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_execution_order_must_cover_all_executable_candidates(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(
        wave for wave in payload["waves"] if wave["compute_class"] == "contained-h100-screen"
    )
    wave["execution_order"].pop()
    with pytest.raises(MemoryPortfolioError, match="rank every executable candidate"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_reasoningbank_source_block_cannot_enter_h100_order(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(wave for wave in payload["waves"] if wave["id"] == "external-validity")
    candidate = next(
        candidate
        for candidate in wave["candidates"]
        if candidate["source_id"] == "reasoningbank"
    )
    assert candidate["status"] == "source-admission-blocked"
    wave["execution_order"].insert(0, "reasoningbank")
    with pytest.raises(MemoryPortfolioError, match="rank every executable candidate"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_first_budget_feasible_candidates_must_be_primary(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    wave = next(
        wave for wave in payload["waves"] if wave["compute_class"] == "contained-h100-screen"
    )
    first_id = wave["execution_order"][0]
    candidate = next(
        candidate
        for candidate in wave["candidates"]
        if candidate["source_id"] == first_id
    )
    candidate["priority"] = "secondary"
    with pytest.raises(MemoryPortfolioError, match="must have primary priority"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_mnemon_requires_exact_h100_negative_evidence(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "mnemon"
    )
    candidate["negative_evidence"]["receipt_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="artifact SHA-256 drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_memorybank_requires_exact_h100_negative_evidence(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "memorybank-siliconfriend"
    )
    candidate["negative_evidence"]["receipt_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="artifact SHA-256 drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_recmem_requires_exact_negative_evidence(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "recmem"
    )
    candidate["negative_evidence"]["receipt_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="artifact SHA-256 drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_tokenmizer_requires_exact_negative_evidence(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "tokenmizer"
    )
    candidate["negative_evidence"]["receipt_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="artifact SHA-256 drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))


def test_timem_requires_exact_negative_evidence(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_PORTFOLIO.read_text(encoding="utf-8"))
    candidate = next(
        candidate
        for wave in payload["waves"]
        for candidate in wave["candidates"]
        if candidate["source_id"] == "timem"
    )
    candidate["negative_evidence"]["receipt_sha256"] = "0" * 64
    with pytest.raises(MemoryPortfolioError, match="artifact SHA-256 drifted"):
        load_and_validate_portfolio(_write_portfolio(tmp_path, payload))
