from __future__ import annotations

import copy
import hashlib
import json
import shutil

import pytest

import scripts.validate_memory_sources as source_validator
from scripts.seal_memory_evidence import (
    EvidenceError,
    seal_astra,
    seal_byterover,
    seal_gaama,
    seal_gaama_natural,
    seal_graphiti,
    seal_hermes,
    seal_hindsight,
    seal_hippo,
    seal_holographic,
    seal_magic_context,
    seal_neo4j,
    seal_openviking,
    seal_total_recall,
)
from scripts.validate_memory_sources import DEFAULT_LEDGER, MemorySourceError, load_and_validate

PROJECT_ROOT = DEFAULT_LEDGER.parents[1]
TOTAL_PRIMARY = (
    PROJECT_ROOT
    / "data/results/total-recall-lifecycle/2026-08-14-restart-doctor-v3"
)
TOTAL_REPLICATION = (
    PROJECT_ROOT
    / "data/results/total-recall-lifecycle/2026-08-14-restart-doctor-v3-replication"
)
TOTAL_EVIDENCE = PROJECT_ROOT / "research/evidence/memory/total-recall-restart-v3.json"
HERMES_ROOT = (
    PROJECT_ROOT / "data/results/hermes-memory-providers/2026-08-14-arm64-v2"
)
HERMES_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage4-hermes-provider-conformance.yaml"
)
HERMES_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/hermes-provider-conformance-v2.json"
)
NEO4J_ROOT = (
    PROJECT_ROOT
    / "data/results/neo4j-preference-lifecycle/2026-08-14-doctor-v1"
)
NEO4J_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-neo4j-preference-supersession-doctor.yaml"
)
NEO4J_EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/memory/neo4j-preference-lifecycle-local-arm64-v1.json"
)
HIPPO_ROOT = PROJECT_ROOT / "data/results/hippo-retention/2026-08-14-doctor-v1"
HIPPO_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-hippo-retention-cross-tenant-doctor.yaml"
)
HIPPO_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/hippo-retention-cross-tenant-v1.json"
)
MAGIC_CONTEXT_ROOT = (
    PROJECT_ROOT / "data/results/magic-context/2026-08-14-doctor-v1"
)
MAGIC_CONTEXT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-magic-context-paging-doctor.yaml"
)
MAGIC_CONTEXT_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/magic-context-paging-v1.json"
)
GAAMA_ROOT = PROJECT_ROOT / "data/results/gaama-component/2026-08-14-doctor-v1"
GAAMA_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-gaama-graph-component-doctor.yaml"
)
GAAMA_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/gaama-graph-component-v1.json"
)
GAAMA_NATURAL_ROOT = (
    PROJECT_ROOT / "data/results/gaama-natural/2026-08-14-doctor-v6"
)
GAAMA_NATURAL_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-gaama-natural-graph-doctor.yaml"
)
GAAMA_NATURAL_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/gaama-natural-graph-v5.json"
)
HOLOGRAPHIC_ROOT = (
    PROJECT_ROOT / "data/results/hermes-holographic/2026-08-14-lifecycle-doctor-v1"
)
HOLOGRAPHIC_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage4-hermes-holographic-lifecycle-doctor.yaml"
)
HOLOGRAPHIC_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/hermes-holographic-lifecycle-v1.json"
)
BYTEROVER_ROOT = (
    PROJECT_ROOT / "data/results/hermes-byterover/2026-08-14-offline-doctor-v1"
)
BYTEROVER_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage4-hermes-byterover-offline-doctor.yaml"
)
BYTEROVER_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/hermes-byterover-offline-v1.json"
)
OPENVIKING_ROOT = (
    PROJECT_ROOT / "data/results/hermes-openviking/2026-08-14-lifecycle-doctor-v2"
)
OPENVIKING_REPLICATION = (
    PROJECT_ROOT / "data/results/hermes-openviking/2026-08-14-lifecycle-doctor-v3"
)
OPENVIKING_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage4-hermes-openviking-lifecycle-doctor.yaml"
)
OPENVIKING_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/hermes-openviking-lifecycle-v3.json"
)
HINDSIGHT_ROOT = (
    PROJECT_ROOT / "data/results/hermes-hindsight/2026-08-14-lifecycle-doctor-run-1"
)
HINDSIGHT_REPLICATION = (
    PROJECT_ROOT / "data/results/hermes-hindsight/2026-08-14-lifecycle-doctor-run-2"
)
HINDSIGHT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage4-hermes-hindsight-lifecycle-doctor.yaml"
)
HINDSIGHT_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/hermes-hindsight-lifecycle-v1.json"
)
GRAPHITI_ROOT = (
    PROJECT_ROOT
    / "data/results/graphiti-native-lifecycle/2026-08-15-container-preflight-v2"
)
GRAPHITI_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-graphiti-native-lifecycle-doctor.yaml"
)
GRAPHITI_EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/memory/graphiti-falkordblite-arm64-v2.json"
)
ASTRA_ROOT = PROJECT_ROOT / "data/results/astra-working-set/2026-08-15-core-v1"
ASTRA_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/astra-working-set-core-v1.json"
)


def test_total_recall_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_total_recall(TOTAL_PRIMARY, TOTAL_REPLICATION)
    expected = json.loads(TOTAL_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_astra_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_astra(ASTRA_ROOT)
    expected = json.loads(ASTRA_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_astra_sealer_rejects_failed_or_drifted_replication(tmp_path) -> None:
    copied = tmp_path / "astra"
    shutil.copytree(ASTRA_ROOT, copied)
    run = copied / "vitest-run2.json"
    payload = json.loads(run.read_text(encoding="utf-8"))
    payload["numPassedTests"] = 25
    payload["numFailedTests"] = 1
    payload["success"] = False
    run.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceError, match="Vitest summary drifted"):
        seal_astra(copied)


def test_total_recall_sealer_requires_distinct_runs() -> None:
    with pytest.raises(EvidenceError, match="must differ"):
        seal_total_recall(TOTAL_PRIMARY, TOTAL_PRIMARY)


def test_total_recall_sealer_rejects_copied_replication(tmp_path) -> None:
    copied = tmp_path / "copied-replication"
    shutil.copytree(TOTAL_PRIMARY, copied)
    with pytest.raises(EvidenceError, match="distinct execution identities"):
        seal_total_recall(TOTAL_PRIMARY, copied)


def test_hermes_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_hermes(HERMES_ROOT, HERMES_EXPERIMENT)
    expected = json.loads(HERMES_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_neo4j_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_neo4j(NEO4J_ROOT, NEO4J_EXPERIMENT)
    expected = json.loads(NEO4J_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_hippo_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_hippo(HIPPO_ROOT, HIPPO_EXPERIMENT)
    expected = json.loads(HIPPO_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_magic_context_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_magic_context(MAGIC_CONTEXT_ROOT, MAGIC_CONTEXT_EXPERIMENT)
    expected = json.loads(MAGIC_CONTEXT_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_gaama_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_gaama(GAAMA_ROOT, GAAMA_EXPERIMENT)
    expected = json.loads(GAAMA_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_gaama_natural_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_gaama_natural(GAAMA_NATURAL_ROOT, GAAMA_NATURAL_EXPERIMENT)
    expected = json.loads(GAAMA_NATURAL_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_holographic_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_holographic(HOLOGRAPHIC_ROOT, HOLOGRAPHIC_EXPERIMENT)
    expected = json.loads(HOLOGRAPHIC_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_byterover_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_byterover(BYTEROVER_ROOT, BYTEROVER_EXPERIMENT)
    expected = json.loads(BYTEROVER_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_openviking_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_openviking(
        OPENVIKING_ROOT, OPENVIKING_REPLICATION, OPENVIKING_EXPERIMENT
    )
    expected = json.loads(OPENVIKING_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_hindsight_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_hindsight(
        HINDSIGHT_ROOT, HINDSIGHT_REPLICATION, HINDSIGHT_EXPERIMENT
    )
    expected = json.loads(HINDSIGHT_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_graphiti_sealer_reproduces_tracked_bundle() -> None:
    actual = seal_graphiti(GRAPHITI_ROOT, GRAPHITI_EXPERIMENT)
    expected = json.loads(GRAPHITI_EVIDENCE.read_text(encoding="utf-8"))
    assert actual == expected


def test_graphiti_sealer_rejects_architecture_drift(tmp_path) -> None:
    copied = tmp_path / "graphiti"
    shutil.copytree(GRAPHITI_ROOT, copied)
    architecture_path = copied / "module-architecture.json"
    architecture = json.loads(architecture_path.read_text(encoding="utf-8"))
    architecture["falkordb.so"]["e_machine"] = 183
    architecture_path.write_text(
        json.dumps(architecture, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(EvidenceError, match="manifest or child receipt drifted"):
        seal_graphiti(copied, GRAPHITI_EXPERIMENT)


def test_hippo_sealer_rejects_purge_residue_drift(tmp_path) -> None:
    copied = tmp_path / "hippo"
    shutil.copytree(HIPPO_ROOT, copied)
    purge_path = copied / "run-1/purge.json"
    purge = json.loads(purge_path.read_text(encoding="utf-8"))
    purge["plaintext_residue_reproduced"] = False
    purge_path.write_text(json.dumps(purge, indent=2, sort_keys=True) + "\n")
    with pytest.raises(EvidenceError, match="artifact receipt drifted"):
        seal_hippo(copied, HIPPO_EXPERIMENT)


def test_magic_context_sealer_rejects_alias_drift(tmp_path) -> None:
    copied = tmp_path / "magic-context"
    shutil.copytree(MAGIC_CONTEXT_ROOT, copied)
    alias_path = copied / "run-1/alias.json"
    alias = json.loads(alias_path.read_text(encoding="utf-8"))
    alias["same_session_id_cross_harness_alias_reproduced"] = False
    alias_path.write_text(json.dumps(alias, indent=2, sort_keys=True) + "\n")
    with pytest.raises(EvidenceError, match="artifact receipt drifted"):
        seal_magic_context(copied, MAGIC_CONTEXT_EXPERIMENT)


def test_gaama_sealer_rejects_component_drift(tmp_path) -> None:
    copied = tmp_path / "gaama"
    shutil.copytree(GAAMA_ROOT, copied)
    component_path = copied / "run-1/report.json"
    component = json.loads(component_path.read_text(encoding="utf-8"))
    component["true_graph_hits"] = 23
    component_path.write_text(
        json.dumps(component, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(EvidenceError, match="artifact receipt drifted"):
        seal_gaama(copied, GAAMA_EXPERIMENT)


def test_gaama_natural_sealer_recomputes_metrics_from_rankings(tmp_path) -> None:
    copied = tmp_path / "gaama-natural"
    shutil.copytree(GAAMA_NATURAL_ROOT, copied)
    report_path = copied / "run-1/report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    stored = report["rows"]["true_graph"][0]["metrics"]["all_at_10"]
    report["rows"]["true_graph"][0]["metrics"]["all_at_10"] = 1.0 - stored
    report_without_hash = dict(report)
    report_without_hash.pop("report_sha256")
    report["report_sha256"] = hashlib.sha256(
        (json.dumps(report_without_hash, indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_path = copied / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report_bytes = report_path.read_bytes()
    manifest["files"]["run-1/report.json"] = {
        "bytes": len(report_bytes),
        "sha256": hashlib.sha256(report_bytes).hexdigest(),
    }
    manifest["root_sha256"] = hashlib.sha256(
        (json.dumps(manifest["files"], indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(EvidenceError, match="row semantics drifted"):
        seal_gaama_natural(copied, GAAMA_NATURAL_EXPERIMENT)


def test_holographic_sealer_rejects_restart_drift(tmp_path) -> None:
    copied = tmp_path / "holographic"
    shutil.copytree(HOLOGRAPHIC_ROOT, copied)
    restart_path = copied / "run-1/restart.json"
    restart = json.loads(restart_path.read_text(encoding="utf-8"))
    restart["session_scoped_isolation_supported"] = True
    restart_path.write_text(
        json.dumps(restart, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(EvidenceError, match="artifact receipt drifted"):
        seal_holographic(copied, HOLOGRAPHIC_EXPERIMENT)


def test_byterover_sealer_rejects_offline_result_drift(tmp_path) -> None:
    copied = tmp_path / "byterover"
    shutil.copytree(BYTEROVER_ROOT, copied)
    restart_path = copied / "run-1/restart.json"
    restart = json.loads(restart_path.read_text(encoding="utf-8"))
    restart["offline_search"]["timed_out"] = False
    restart_path.write_text(
        json.dumps(restart, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(EvidenceError, match="artifact receipt drifted"):
        seal_byterover(copied, BYTEROVER_EXPERIMENT)


def test_openviking_sealer_rejects_residue_proof_drift(tmp_path) -> None:
    copied = tmp_path / "openviking"
    shutil.copytree(OPENVIKING_ROOT, copied)
    report_path = copied / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    canary = next(iter(report["state"]["plaintext_residue_proofs"]))
    report["state"]["plaintext_residue_proofs"][canary][0]["window_base64"] = "eA=="
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_path = copied / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(EvidenceError, match="residue proof drifted"):
        seal_openviking(copied, OPENVIKING_REPLICATION, OPENVIKING_EXPERIMENT)


def test_hindsight_sealer_rejects_residue_proof_drift(tmp_path) -> None:
    copied = tmp_path / "hindsight"
    shutil.copytree(HINDSIGHT_ROOT, copied)
    report_path = copied / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    canary = next(iter(report["state"]["plaintext_residue_proofs"]))
    report["state"]["plaintext_residue_proofs"][canary][0]["window_base64"] = "eA=="
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_path = copied / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(EvidenceError, match="residue proof drifted"):
        seal_hindsight(copied, HINDSIGHT_REPLICATION, HINDSIGHT_EXPERIMENT)


def test_neo4j_sealer_rejects_purge_drift(tmp_path) -> None:
    copied = tmp_path / "neo4j"
    shutil.copytree(NEO4J_ROOT, copied)
    report_path = copied / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["repeats"][0]["verify_empty"]["nodes"] = 1
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path = copied / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report_bytes = report_path.read_bytes()
    manifest["artifacts"]["report.json"] = {
        "bytes": len(report_bytes),
        "sha256": hashlib.sha256(report_bytes).hexdigest(),
    }
    manifest_without_root = dict(manifest)
    manifest_without_root.pop("manifest_sha256")
    manifest["manifest_sha256"] = hashlib.sha256(
        (json.dumps(manifest_without_root, indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(EvidenceError, match="restart, purge, or model-call"):
        seal_neo4j(copied, NEO4J_EXPERIMENT)


def test_hermes_sealer_rejects_removed_pass_log(tmp_path) -> None:
    copied = tmp_path / "hermes"
    shutil.copytree(HERMES_ROOT, copied)
    (copied / "logs/byterover.log").unlink()
    manifest_path = copied / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["log_sha256s"].pop("byterover.log")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(EvidenceError, match="file roster drifted"):
        seal_hermes(copied, HERMES_EXPERIMENT)


def test_embedded_evidence_tamper_fails_source_validation(
    tmp_path, monkeypatch
) -> None:
    ledger = load_and_validate(DEFAULT_LEDGER)
    entry = copy.deepcopy(ledger["sources"]["total-recall-oss"])
    bundle = json.loads(TOTAL_EVIDENCE.read_text(encoding="utf-8"))
    bundle["runs"][0]["files"]["report.json"]["content_base64"] = "e30="
    evidence = tmp_path / "evidence.json"
    encoded = (json.dumps(bundle, sort_keys=True) + "\n").encode()
    evidence.write_bytes(encoded)
    entry["reproduction_receipt"] = {
        "artifact_path": "evidence.json",
        "receipt_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    monkeypatch.setattr(source_validator, "PROJECT_ROOT", tmp_path)
    with pytest.raises(MemorySourceError, match="byte count drifted"):
        source_validator.validate_source(
            "total-recall-oss",
            entry,
            allowed_layers=set(ledger["controlled_vocabulary"]["memory_layers"]),
        )
