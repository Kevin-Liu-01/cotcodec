from __future__ import annotations

import copy
import hashlib
import json

import pytest
import yaml

import scripts.validate_memory_sources as source_validator
from scripts.validate_gaama_h100_evidence import (
    GaamaH100EvidenceError,
    validate_gaama_h100_evidence,
)
from scripts.validate_memoria_lifecycle_evidence import (
    MemoriaEvidenceError,
    validate_memoria_lifecycle_evidence,
)
from scripts.validate_memory_sources import (
    DEFAULT_LEDGER,
    PROJECT_ROOT,
    MemorySourceError,
    build_reproducibility_audit,
    load_and_validate,
    validate_source,
)
from scripts.validate_mnemon_h100_evidence import (
    MnemonH100EvidenceError,
    validate_mnemon_h100_evidence,
)
from scripts.validate_recmem_consolidation_evidence import (
    RecMemEvidenceError,
    validate_recmem_consolidation_evidence,
)
from scripts.validate_timem_core_evidence import (
    TiMemEvidenceError,
    validate_timem_core_evidence,
)
from scripts.validate_tokenmizer_checkpoint_evidence import (
    TokenMizerEvidenceError,
    validate_tokenmizer_checkpoint_evidence,
)


def test_live_memory_source_ledger_is_valid_and_pinned() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    assert "graphiti" in ledger["sources"]
    assert "memgpt-letta" in ledger["sources"]
    assert "memory-r2" in ledger["sources"]
    assert "verifiable-memory" in ledger["sources"]
    assert "memeval-harness" in ledger["sources"]
    assert "memoryagentbench" in ledger["sources"]
    assert "ripplemem" in ledger["sources"]
    assert "refind-raw-chat" in ledger["sources"]
    assert "evomembench" in ledger["sources"]
    assert "streammembench" in ledger["sources"]
    assert "pm-bench" in ledger["sources"]
    assert "sodamem" in ledger["sources"]
    assert "timem" in ledger["sources"]
    assert "memforest" in ledger["sources"]
    assert "infini-memory" in ledger["sources"]
    assert "deltamem" in ledger["sources"]
    assert "h-mem" in ledger["sources"]
    assert "mempalace" in ledger["sources"]
    assert "reme" in ledger["sources"]
    assert "agentmemory" in ledger["sources"]
    assert "honcho" in ledger["sources"]
    assert "acontext" in ledger["sources"]
    assert "memu" in ledger["sources"]
    assert "rememr1" in ledger["sources"]
    assert "tencentdb-agent-memory" in ledger["sources"]
    assert "memgraphrag" in ledger["sources"]
    assert "erskill" in ledger["sources"]
    assert "router-mem" in ledger["sources"]
    assert "lightmem2" in ledger["sources"]
    assert "jiuwen-memory" in ledger["sources"]
    assert "shodh-memory" in ledger["sources"]
    assert "sage-wiki" in ledger["sources"]
    assert "memory-stress" in ledger["sources"]
    assert "mnemon" in ledger["sources"]
    assert "fidelis" in ledger["sources"]
    assert "total-recall-oss" in ledger["sources"]
    assert "magic-context" in ledger["sources"]
    assert "gaama" in ledger["sources"]
    assert "arigraph" in ledger["sources"]
    assert "adamem" in ledger["sources"]
    assert "treemem-credit-assignment" in ledger["sources"]
    assert "omnimemeval" in ledger["sources"]
    assert "owasp-agent-memory-guard" in ledger["sources"]
    assert "agentmembench-systematic" in ledger["sources"]
    assert "horizon-gap-survey" in ledger["sources"]
    assert "hermes-provider-conformance" in ledger["sources"]
    assert "hermes-holographic" in ledger["sources"]
    assert "hermes-hindsight-native" in ledger["sources"]
    assert "hermes-byterover-cli" in ledger["sources"]
    assert "consolidator-persistent-routed-memory" in ledger["sources"]
    assert "mnemosyne-oss" in ledger["sources"]
    assert "icarus-memory-infra" in ledger["sources"]
    assert "palimpsest-bitemporal-memory" in ledger["sources"]
    assert "mem0-lifecycle-adapter" in ledger["sources"]
    assert "all-mem" in ledger["sources"]
    assert "mage-execution-state-manager" in ledger["sources"]
    assert "memory-as-metabolism" in ledger["sources"]
    assert "eywa-provenance-grounded-memory" in ledger["sources"]
    assert "jordan-agentmemory-v4" in ledger["sources"]
    assert "agentra-agentic-memory" in ledger["sources"]
    assert "experience-os-lab" in ledger["sources"]
    assert "dsh-memory-system" in ledger["sources"]
    assert "longform-memory" in ledger["sources"]
    assert "e2mem-episodic-event-hierarchy" in ledger["sources"]
    assert "canon-governed-decision-memory" in ledger["sources"]
    assert "palimpsest-cockroach-agent-memory" in ledger["sources"]
    assert "lgoyal6-memharness" in ledger["sources"]
    assert "evolvebank" in ledger["sources"]
    assert "astra-working-set" in ledger["sources"]
    assert "memoria-matrixorigin" in ledger["sources"]
    assert "agent-recall" in ledger["sources"]
    assert "memorygraph-typed-coding-memory" in ledger["sources"]
    assert "tokenmizer" in ledger["sources"]
    assert "activegraph-event-sourced-runtime" in ledger["sources"]
    assert "memforge" in ledger["sources"]
    assert "agenticow" in ledger["sources"]
    assert "hermes-observational-memory" in ledger["sources"]
    assert "longmemeval-natural-session-topology" in ledger["sources"]
    assert ledger["sources"]["longmemeval"]["artifacts"][0]["sha256"] == (
        "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c"
    )
    assert len(ledger["sources"]) == 229
    assert ledger["sources"]["memharness"]["repositories"][0] == {
        "role": "implementation",
        "url": "https://github.com/KnowledgeXLab/MemHarness",
        "revision": "31329e8e084c7fdf20556874950f6c2100b8b28e",
        "license": "Apache-2.0",
    }
    assert ledger["sources"]["verifiable-memory"]["repositories"][0][
        "revision"
    ] == "4782751c79faa08421a27c23b4d02c591bc3357d"
    assert ledger["sources"]["v-mem"]["repositories"][0] == {
        "role": "implementation-and-evaluation",
        "url": "https://github.com/Dingyi-Kang/V-Mem",
        "revision": "36916b14dc5241e04acbf5cd0f3c40799bc09550",
        "license": "MIT",
    }
    assert ledger["sources"]["prograph-memhop"]["repositories"][0][
        "revision"
    ] == "535e5839f730cab82f4ccdbe0678d7cd91ad9bb5"
    assert ledger["sources"]["superlocalmemory-v4"]["repositories"][0][
        "revision"
    ] == "9283b82f7b12e9a8a5e659be2e5f2619948e7199"
    assert ledger["sources"]["foresightkv"]["repositories"][0]["revision"] == (
        "fdb541fadf0633ef1b909b40b9c3ecd5b40f558d"
    )
    assert ledger["sources"]["timem"]["repositories"][0]["revision"] == (
        "6d279a5f5d40ee229e1995df15c182cb2062c71c"
    )
    assert ledger["sources"]["lightmem2"]["repositories"][0] == {
        "role": "implementation-tests-adapters-and-evaluation-drivers",
        "url": "https://github.com/zjunlp/LightMem2",
        "revision": "dfc67e8bc9373ca5b31bb412298565c9d65b29b6",
        "license": "MIT",
    }
    assert ledger["sources"]["memoria-matrixorigin"]["repositories"][0][
        "revision"
    ] == "efd3d6515969971dfa894737272b8317bcb643e7"
    assert ledger["sources"]["agent-recall"]["repositories"][0][
        "revision"
    ] == "dcf21b5cc9691e1371299917e2e474fb82e07cab"
    assert ledger["sources"]["memorygraph-typed-coding-memory"]["repositories"][0][
        "revision"
    ] == "4f834c01765dc52b66c621fa42928fb0b52208cb"
    assert ledger["sources"]["tokenmizer"]["repositories"][0][
        "revision"
    ] == "131e3d1569de3e8f70c198ade4e791b47f63dc41"
    assert ledger["sources"]["activegraph-event-sourced-runtime"]["repositories"][0][
        "revision"
    ] == "8aedb1866cf5dce056af97529152ffd6f468a1ed"
    assert ledger["sources"]["memforge"]["repositories"][0]["revision"] == (
        "16e2f15c5881a38911f64ca81b3dc0b25d6207ec"
    )
    assert ledger["sources"]["agenticow"]["repositories"][0]["revision"] == (
        "dd4f437b92d2dbbc1f40dfa00023eed6e9c3bd84"
    )
    assert ledger["sources"]["hermes-observational-memory"]["repositories"][1][
        "revision"
    ] == "6bbc16e81ad1258ee1e8ba37c9efcc6ce36a0208"
    assert ledger["sources"]["fidelis"]["repositories"][0]["revision"] == (
        "0950ff3e6d377b08f02a26045a6508c58a07a1eb"
    )
    assert ledger["sources"]["memforest"]["repositories"][0]["license"] == "MIT"
    assert ledger["sources"]["infini-memory"]["repositories"][0]["license"] == (
        "Apache-2.0"
    )
    assert ledger["sources"]["deltamem"]["repositories"][0]["license"] == (
        "unresolved"
    )
    assert ledger["sources"]["mempalace"]["repositories"][0] == {
        "role": "implementation-benchmarks-and-per-question-outputs",
        "url": "https://github.com/MemPalace/mempalace",
        "revision": "906b918a7c6ebb2a9198a6bf5a78f30a173fea56",
        "license": "MIT",
    }
    assert ledger["sources"]["reme"]["repositories"][0]["revision"] == (
        "fd2894f9399206645b3adc634982f88c32f36dd9"
    )
    assert ledger["sources"]["agentmemory"]["repositories"][0]["license"] == (
        "Apache-2.0"
    )
    assert ledger["sources"]["honcho"]["repositories"][0]["license"] == (
        "AGPL-3.0"
    )
    assert ledger["sources"]["acontext"]["repositories"][0]["revision"] == (
        "259d73bfdebeed35ec2d4211ddc060a2d4126bc6"
    )
    assert ledger["sources"]["memu"]["repositories"][0]["revision"] == (
        "96fd3ec08853b40a9e4c743794446553df0a3bc4"
    )
    assert ledger["sources"]["rememr1"]["repositories"][0]["revision"] == (
        "cc514c092ca968a50c52cdcc2e2ba96362fce25a"
    )
    assert ledger["sources"]["tencentdb-agent-memory"]["repositories"][0][
        "revision"
    ] == "4dca55c41bf11cb19b49728dbe495c8e05d25abb"


def test_reproducibility_audit_exposes_paper_and_license_gaps() -> None:
    audit = build_reproducibility_audit(load_and_validate(DEFAULT_LEDGER))
    assert audit["source_count"] >= 113
    assert "foresightkv" in audit["pinned_repository_sources"]
    assert "lycheememory-v2" in audit["paper_only_sources"]
    assert "sodamem" in audit["pinned_repository_sources"]
    assert any(
        item.startswith("foresightkv:")
        for item in audit["unresolved_repositories"]
    )
    assert audit["scientific_result_reproduced_source_count"] == 0
    assert audit["scientific_result_reproduced_sources"] == []
    assert audit["local_conformance_reproduced_sources"] == [
        "astra-working-set",
        "hermes-provider-conformance",
        "neo4j-agent-memory",
    ]
    assert audit["local_negative_reproduced_sources"] == [
        "activegraph-event-sourced-runtime",
        "agent-recall",
        "agenticow",
        "all-mem",
        "gaama",
        "graphiti-native-lifecycle-adapter",
        "hermes-byterover-cli",
        "hermes-hindsight-native",
        "hermes-holographic",
        "hermes-observational-memory",
        "hippo-memory",
        "icarus-memory-infra",
        "lightmem",
        "lightmem2",
        "longmemeval-natural-session-topology",
        "magic-context",
        "mem0-lifecycle-adapter",
        "memforge",
        "memoria-matrixorigin",
        "memorybank-siliconfriend",
        "mnemon",
        "mnemosyne-cognitive-os",
        "mnemosyne-oss",
        "openviking",
        "palimpsest-bitemporal-memory",
        "recmem",
        "shodh-memory",
        "supermemory",
        "timem",
        "tokenmizer",
        "total-recall-oss",
    ]


def test_local_reproduction_receipt_must_match_artifact_bytes(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_LEDGER.read_text(encoding="utf-8"))
    payload["sources"]["total-recall-oss"]["reproduction_receipt"][
        "receipt_sha256"
    ] = "0" * 64
    path = tmp_path / "memory-sources.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemorySourceError, match="does not match receipt"):
        load_and_validate(path)


def test_mem0_top_level_crash_proof_roots_are_bound(tmp_path, monkeypatch) -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["mem0-lifecycle-adapter"])
    receipt = entry["reproduction_receipt"]
    bundle = json.loads((PROJECT_ROOT / receipt["artifact_path"]).read_text(encoding="utf-8"))
    bundle["crash_scope_plaintext_proof_roots"] = ["0" * 64, "1" * 64]
    encoded = (json.dumps(bundle, sort_keys=True) + "\n").encode()
    (tmp_path / "evidence.json").write_bytes(encoded)
    entry["reproduction_receipt"] = {
        "artifact_path": "evidence.json",
        "receipt_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    monkeypatch.setattr(source_validator, "PROJECT_ROOT", tmp_path)
    with pytest.raises(MemorySourceError, match="Mem0 lifecycle evidence receipt drifted"):
        source_validator.validate_source(
            "mem0-lifecycle-adapter",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )


def test_hermes_provider_reproduction_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    receipt = result["sources"]["hermes-provider-conformance"][
        "reproduction_receipt"
    ]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_hermes_byterover_negative_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    receipt = result["sources"]["hermes-byterover-cli"]["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_hippo_negative_reproduction_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    receipt = result["sources"]["hippo-memory"]["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_graphiti_native_negative_reproduction_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    entry = result["sources"]["graphiti-native-lifecycle-adapter"]
    receipt = entry["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_memorybank_h100_negative_reproduction_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    entry = result["sources"]["memorybank-siliconfriend"]
    receipt = entry["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert receipt["receipt_sha256"] == (
        "bd069e22e2014bf548d23c718a35ea10868213fd343a07814826bf0e0b55aff2"
    )
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_icarus_negative_reproduction_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    entry = result["sources"]["icarus-memory-infra"]
    receipt = entry["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_palimpsest_negative_reproduction_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    entry = result["sources"]["palimpsest-bitemporal-memory"]
    receipt = entry["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_memoria_negative_reproduction_receipt_is_bound() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = ledger["sources"]["memoria-matrixorigin"]
    receipt = entry["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert receipt["receipt_sha256"] == (
        "92c8427e8c6a40e38e958b61c7cca5af935f0a2da793240c10ed3a1d3797a990"
    )
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_memoria_negative_rejects_semantic_tampering() -> None:
    path = (
        PROJECT_ROOT
        / "research/evidence/memory/memoria-transactional-lifecycle-negative-v1.json"
    )
    bundle = json.loads(path.read_text())
    bundle["findings"]["purge_residue_survived_restart"] = False
    with pytest.raises(MemoriaEvidenceError, match="identity drifted"):
        validate_memoria_lifecycle_evidence(bundle, project_root=PROJECT_ROOT)


def test_shodh_negative_reproduction_receipt_is_bound() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = ledger["sources"]["shodh-memory"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert entry["reproduction_receipt"]["receipt_sha256"] == (
        "e8805c42e64847eb82858b09d7d56b83b7fd71afd8a1633d840afcf272f278ad"
    )


def test_mnemon_h100_negative_receipt_is_bound() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = ledger["sources"]["mnemon"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert entry["reproduction_receipt"]["receipt_sha256"] == (
        "e94b3ece8a972d35da0f60b454cf2dbce34916abfdfbcb8152761c68cf399846"
    )


def test_mnemon_h100_negative_rejects_semantic_tampering() -> None:
    path = PROJECT_ROOT / "research/evidence/memory/mnemon-h100-static-space-negative-v1.json"
    bundle = json.loads(path.read_text())
    bundle["outcome"]["lexical_minus_all_token_f1"] = 1.0
    with pytest.raises(MnemonH100EvidenceError, match="report semantics drifted"):
        validate_mnemon_h100_evidence(bundle, project_root=PROJECT_ROOT)


def test_recmem_negative_receipt_is_bound() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = ledger["sources"]["recmem"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert entry["reproduction_receipt"]["receipt_sha256"] == (
        "d870b8d1b02eb4b5998037c36310c721c8dd9ac4dc094ed34645322b2a0f78b9"
    )


def test_recmem_negative_rejects_semantic_tampering() -> None:
    path = PROJECT_ROOT / "research/evidence/memory/recmem-consolidation-negative-v1.json"
    bundle = json.loads(path.read_text())
    bundle["claim_boundary"]["failed_merge_loses_prior_episode"] = False
    with pytest.raises(RecMemEvidenceError, match="identity drifted"):
        validate_recmem_consolidation_evidence(bundle, project_root=PROJECT_ROOT)


def test_tokenmizer_negative_receipt_is_bound() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = ledger["sources"]["tokenmizer"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert entry["reproduction_receipt"]["receipt_sha256"] == (
        "932bb2c0d897bbea7356ab5a07cd2d436adaecfd394980e9dd5a768072340e1b"
    )


def test_tokenmizer_negative_rejects_semantic_tampering() -> None:
    path = PROJECT_ROOT / "research/evidence/memory/tokenmizer-checkpoint-negative-v1.json"
    bundle = json.loads(path.read_text())
    bundle["claim_boundary"]["context_compaction_quality_evaluated"] = True
    with pytest.raises(TokenMizerEvidenceError, match="identity drifted"):
        validate_tokenmizer_checkpoint_evidence(bundle, project_root=PROJECT_ROOT)


def test_timem_negative_receipt_is_bound() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = ledger["sources"]["timem"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert entry["reproduction_receipt"]["receipt_sha256"] == (
        "742f0f6745aeef2599d1bc8a3f52f33b9c8be724aa7797ad34f41b0e247f2f1c"
    )


def test_timem_negative_rejects_semantic_tampering() -> None:
    path = PROJECT_ROOT / "research/evidence/memory/timem-core-runtime-negative-v1.json"
    bundle = json.loads(path.read_text())
    bundle["claim_boundary"]["hierarchy_quality_evaluated"] = True
    with pytest.raises(TiMemEvidenceError, match="identity drifted"):
        validate_timem_core_evidence(bundle, project_root=PROJECT_ROOT)


def test_hermes_observational_memory_negative_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    entry = result["sources"]["hermes-observational-memory"]
    receipt = entry["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_gaama_h100_negative_receipt_is_bound() -> None:
    result = load_and_validate(DEFAULT_LEDGER)
    entry = result["sources"]["gaama"]
    receipt = entry["reproduction_receipt"]
    artifact = PROJECT_ROOT / receipt["artifact_path"]
    assert entry["evidence_grade"] == "local-negative-reproduced"
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == receipt["receipt_sha256"]


def test_gaama_h100_negative_rejects_semantic_tampering() -> None:
    bundle_path = (
        PROJECT_ROOT / "research/evidence/memory/gaama-h100-actor-negative-v1.json"
    )
    bundle = json.loads(bundle_path.read_text())
    bundle["outcome"]["true_token_f1"] = 1.0
    with pytest.raises(GaamaH100EvidenceError, match="report semantics drifted"):
        validate_gaama_h100_evidence(bundle, project_root=PROJECT_ROOT)


def test_repository_revision_must_be_immutable() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["graphiti"])
    entry["repositories"][0]["revision"] = "main"
    with pytest.raises(MemorySourceError, match="40-char commit"):
        validate_source(
            "graphiti",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )


def test_repository_must_be_bound_by_primary_source() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["graphiti"])
    entry["repositories"][0]["url"] = "https://github.com/example/unbound"
    with pytest.raises(MemorySourceError, match="must be bound by primary_sources"):
        validate_source(
            "graphiti",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )


def test_public_artifact_digest_must_be_immutable() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["longmemeval"])
    entry["artifacts"][0]["sha256"] = "latest"
    with pytest.raises(MemorySourceError, match="lowercase SHA-256"):
        validate_source(
            "longmemeval",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )


def test_benchmark_claim_must_label_evidence_grade() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["hindsight"])
    del entry["benchmark_claims"][0]["evidence_grade"]
    with pytest.raises(MemorySourceError, match="evidence_grade"):
        validate_source(
            "hindsight",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )


def test_reproduced_claim_requires_reproduction_receipt() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["hindsight"])
    entry["benchmark_claims"][0]["evidence_grade"] = "local-reproduced"
    with pytest.raises(MemorySourceError, match="requires reproduction"):
        validate_source(
            "hindsight",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )


def test_reproduced_source_requires_reproduction_receipt() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["hindsight"])
    entry["evidence_grade"] = "local-reproduced"
    with pytest.raises(MemorySourceError, match="requires reproduction_receipt"):
        validate_source(
            "hindsight",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )


def test_duplicate_yaml_source_id_is_rejected(tmp_path) -> None:
    path = tmp_path / "duplicate.yaml"
    path.write_text(
        """\
schema_version: 1
verified_at: "2026-08-13"
controlled_vocabulary:
  memory_layers: [controller]
  evidence_grades:
    - mechanism-only
    - paper-reported
    - vendor-reported
    - open-harness-reported
    - externally-reproduced
    - local-reproduced
sources:
  repeated: {kind: first}
  repeated: {kind: second}
""",
        encoding="utf-8",
    )
    with pytest.raises(MemorySourceError, match="duplicate YAML key: 'repeated'"):
        load_and_validate(path)


def test_unknown_residency_transition_is_rejected() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["memgpt-letta"])
    entry["residency_transition"] = "marketing-tier"
    with pytest.raises(MemorySourceError, match="unknown residency_transition"):
        validate_source(
            "memgpt-letta",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )


def test_graph_semantics_requires_graph_representation() -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["memgpt-letta"])
    entry["graph_semantics"] = "temporal-validity"
    with pytest.raises(MemorySourceError, match="requires temporal_graph"):
        validate_source(
            "memgpt-letta",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )
