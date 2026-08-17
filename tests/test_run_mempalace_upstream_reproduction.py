from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

import scripts.audit_mempalace_port_equivalence as equivalence_module
from harness.memory_trials import MemPalaceRuntimeIdentity
from scripts.audit_mempalace_port_equivalence import (
    _run_equivalence_audit_for_test,
    run_equivalence_audit,
)
from scripts.compare_mempalace_reproductions import (
    PairTargets,
    _rankings_and_metrics,
    _write_report,
    compare_reproductions,
)
from scripts.mempalace_upstream_adapter import PinnedUpstreamMemPalaceAdapter
from scripts.run_mempalace_upstream_reproduction import (
    ReproductionExpectations,
    _load_upstream_retriever,
    run_reproduction,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path):
    source = tmp_path / "source"
    (source / "benchmarks").mkdir(parents=True)
    for relative, content in {
        "benchmarks/longmemeval_bench.py": "runner",
        "uv.lock": "lock",
        "LICENSE": "license",
        "pyproject.toml": "project",
    }.items():
        (source / relative).write_text(content, encoding="utf-8")
    dataset = tmp_path / "dataset.json"
    rows = [
        {
            "question_id": f"q{index}",
            "question_type": "single_hop",
            "question": f"question {index}",
            "question_date": "2026-01-03",
            "answer": f"answer {index}",
            "answer_session_ids": [f"s{index}-a"],
            "has_answer": True,
            "future_answerability_label": f"label-{index}",
            "haystack_sessions": [
                [{"role": "user", "content": f"text a {index}"}],
                [{"role": "user", "content": f"text b {index}"}],
            ],
            "haystack_session_ids": [f"s{index}-a", f"s{index}-b"],
            "haystack_dates": ["2026-01-01", "2026-01-02"],
        }
        for index in range(3)
    ]
    dataset.write_text(json.dumps(rows), encoding="utf-8")
    expectations = ReproductionExpectations(
        runner_sha256=_sha(source / "benchmarks/longmemeval_bench.py"),
        lock_sha256=_sha(source / "uv.lock"),
        license_sha256=_sha(source / "LICENSE"),
        pyproject_sha256=_sha(source / "pyproject.toml"),
        source_archive_sha256=(
            "efbc106cb344a1c5031268909adc2fb5c11cc783ec61adccbe3da0867b4d25c7"
        ),
        dataset_sha256=_sha(dataset),
        dataset_size=dataset.stat().st_size,
    )
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "VERIFIED_OFFLINE_MEMPALACE_RUNTIME",
                "repository_revision": "906b918a7c6ebb2a9198a6bf5a78f30a173fea56",
                "repository_tree": "98789ad017781f52550b511fcedd9e00c3346761",
                "source_archive_sha256": expectations.source_archive_sha256,
                "runner_sha256": expectations.runner_sha256,
                "uv_lock_sha256": expectations.lock_sha256,
                "chromadb_version": "1.5.7",
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_archive_sha256": (
                    "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
                ),
                "execution_provider": "CPUExecutionProvider",
                "network_policy": "none",
                "image_id": "sha256:" + "e" * 64,
                "cotcodec_base_image_reference": "registry.invalid/cotcodec@sha256:"
                + "a" * 64,
                "image_repo_digest": "registry.invalid/mempalace@sha256:" + "b" * 64,
                "image_sbom_sha256": "f" * 64,
                "embedding_artifact_root_sha256": "a" * 64,
                "minilm_receipt_sha256": "c" * 64,
            }
        ),
        encoding="utf-8",
    )

    def retrieve(entry):
        assert set(entry) == {
            "question",
            "haystack_sessions",
            "haystack_session_ids",
            "haystack_dates",
        }
        index = entry["question"].split()[-1]
        corpus = [f"text a {index}", f"text b {index}"]
        ids = [f"s{index}-a", f"s{index}-b"]
        return [0, 1], corpus, ids, entry["haystack_dates"]

    return source, dataset, runtime, expectations, retrieve


def _port_adapter(
    *, image_digest: str = "sha256:" + "e" * 64
) -> PinnedUpstreamMemPalaceAdapter:
    def retrieve(entry):
        corpus = [session[0]["content"] for session in entry["haystack_sessions"]]
        return (
            list(range(len(corpus))),
            corpus,
            entry["haystack_session_ids"],
            entry["haystack_dates"],
        )

    return PinnedUpstreamMemPalaceAdapter.from_retriever(
        identity=MemPalaceRuntimeIdentity(
            model_artifact_root_sha256="a" * 64,
            model_receipt_sha256="c" * 64,
            image_digest=image_digest,
            implementation_kind="in_process_reference",
        ),
        retrieve=retrieve,
    )


def test_matched_port_equivalence_audit_seals_exact_rankings(tmp_path: Path) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    direct = tmp_path / "direct"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=direct,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    output = tmp_path / "equivalence"
    result = _run_equivalence_audit_for_test(
        source_root=source,
        dataset_path=dataset,
        direct_bundle=direct,
        direct_runtime_receipt_path=runtime,
        expected_direct_runtime_receipt_sha256=_sha(runtime),
        port_runtime_receipt_path=runtime,
        expected_port_runtime_receipt_sha256=_sha(runtime),
        output_dir=output,
        resume=False,
        retrieval=_port_adapter(),
        expectations=expectations,
    )
    assert result["all_gates_pass"] is True
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "EXACT_MATCHED_PORT_EQUIVALENCE_PASS"
    assert report["exact_counts"]["ranking_exact"] == 3

    resumed = _run_equivalence_audit_for_test(
        source_root=source,
        dataset_path=dataset,
        direct_bundle=direct,
        direct_runtime_receipt_path=runtime,
        expected_direct_runtime_receipt_sha256=_sha(runtime),
        port_runtime_receipt_path=runtime,
        expected_port_runtime_receipt_sha256=_sha(runtime),
        output_dir=output,
        resume=True,
        retrieval=_port_adapter(),
        expectations=expectations,
    )
    assert resumed == result
    journal = output / "journal.jsonl"
    with journal.open("ab") as handle:
        handle.write(b'{"partial":')
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="finalized journal"):
        _run_equivalence_audit_for_test(
            source_root=source,
            dataset_path=dataset,
            direct_bundle=direct,
            direct_runtime_receipt_path=runtime,
            expected_direct_runtime_receipt_sha256=_sha(runtime),
            port_runtime_receipt_path=runtime,
            expected_port_runtime_receipt_sha256=_sha(runtime),
            output_dir=output,
            resume=True,
            retrieval=_port_adapter(),
            expectations=expectations,
        )
    assert journal.read_bytes() == before


def test_matched_port_equivalence_preserves_repeated_session_occurrences(
    tmp_path: Path,
) -> None:
    source, dataset, runtime, expectations, _retrieve = _fixture(tmp_path)
    rows = json.loads(dataset.read_text(encoding="utf-8"))
    rows[0]["haystack_session_ids"] = ["shared-session", "shared-session"]
    dataset.write_text(json.dumps(rows), encoding="utf-8")
    expectations = ReproductionExpectations(
        **{
            **expectations.__dict__,
            "dataset_sha256": _sha(dataset),
            "dataset_size": dataset.stat().st_size,
        }
    )

    def retrieve(entry: dict[str, object]):
        sessions = entry["haystack_sessions"]
        assert isinstance(sessions, list)
        corpus = [session[0]["content"] for session in sessions]
        return (
            list(range(len(corpus))),
            corpus,
            entry["haystack_session_ids"],
            entry["haystack_dates"],
        )

    direct = tmp_path / "direct-duplicate-session"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=direct,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    output = tmp_path / "equivalence-duplicate-session"
    result = _run_equivalence_audit_for_test(
        source_root=source,
        dataset_path=dataset,
        direct_bundle=direct,
        direct_runtime_receipt_path=runtime,
        expected_direct_runtime_receipt_sha256=_sha(runtime),
        port_runtime_receipt_path=runtime,
        expected_port_runtime_receipt_sha256=_sha(runtime),
        output_dir=output,
        resume=False,
        retrieval=_port_adapter(),
        expectations=expectations,
    )

    assert result["all_gates_pass"] is True
    first = json.loads((output / "journal.jsonl").read_text().splitlines()[0])[
        "result"
    ]
    assert first["direct_session_count"] == first["port_session_count"] == 2
    assert len(set(first["translated_direct_ranked_ids"])) == 2
    assert first["direct_ranked_sessions"] == [
        {"corpus_id": "shared-session", "timestamp": "2026-01-01"},
        {"corpus_id": "shared-session", "timestamp": "2026-01-02"},
    ]


def test_matched_port_equivalence_binds_distinct_direct_and_port_runtimes(
    tmp_path: Path,
) -> None:
    source, dataset, direct_runtime, expectations, retrieve = _fixture(tmp_path)
    direct = tmp_path / "direct"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=direct_runtime,
        output_dir=direct,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    port_runtime = tmp_path / "port-runtime.json"
    port_receipt = json.loads(direct_runtime.read_text(encoding="utf-8"))
    port_receipt["image_id"] = "sha256:" + "d" * 64
    port_receipt["image_repo_digest"] = (
        "registry.invalid/mempalace@sha256:" + "1" * 64
    )
    port_receipt["image_sbom_sha256"] = "2" * 64
    port_runtime.write_text(json.dumps(port_receipt), encoding="utf-8")

    output = tmp_path / "equivalence-distinct-runtimes"
    result = _run_equivalence_audit_for_test(
        source_root=source,
        dataset_path=dataset,
        direct_bundle=direct,
        direct_runtime_receipt_path=direct_runtime,
        expected_direct_runtime_receipt_sha256=_sha(direct_runtime),
        port_runtime_receipt_path=port_runtime,
        expected_port_runtime_receipt_sha256=_sha(port_runtime),
        output_dir=output,
        resume=False,
        retrieval=_port_adapter(image_digest="sha256:" + "d" * 64),
        expectations=expectations,
    )

    assert result["all_gates_pass"] is True
    contract = json.loads((output / "contract.json").read_text(encoding="utf-8"))
    assert contract["schema_version"] == 2
    assert contract["direct_reproduction"]["runtime_receipt_sha256"] == _sha(
        direct_runtime
    )
    assert contract["port"]["runtime_receipt_sha256"] == _sha(port_runtime)
    assert contract["direct_reproduction"]["runtime"] == json.loads(
        direct_runtime.read_text(encoding="utf-8")
    )
    assert contract["port"]["runtime"] == port_receipt
    assert contract["port"]["runtime_identity"]["image_digest"] == (
        "sha256:" + "d" * 64
    )
    assert contract["direct_reproduction"]["runtime"]["image_id"] != contract[
        "port"
    ]["runtime"]["image_id"]
    assert set(contract["port"]["code_sha256"]) == {
        "harness/memory_trials/mempalace_control.py",
        "harness/memory_trials/public_sources.py",
        "harness/memory_trials/schema.py",
        "harness/memory_trials/systems.py",
        "scripts/audit_mempalace_port_equivalence.py",
        "scripts/compare_mempalace_reproductions.py",
        "scripts/mempalace_upstream_adapter.py",
        "scripts/run_mempalace_upstream_reproduction.py",
    }


def test_production_equivalence_constructs_port_from_registered_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    direct = tmp_path / "direct"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=direct,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    captured: dict[str, object] = {}

    def construct_adapter(**kwargs: object) -> PinnedUpstreamMemPalaceAdapter:
        captured.update(kwargs)
        return _port_adapter()

    monkeypatch.setattr(
        equivalence_module, "PinnedUpstreamMemPalaceAdapter", construct_adapter
    )
    result = run_equivalence_audit(
        source_root=source,
        dataset_path=dataset,
        direct_bundle=direct,
        direct_runtime_receipt_path=runtime,
        expected_direct_runtime_receipt_sha256=_sha(runtime),
        port_runtime_receipt_path=runtime,
        expected_port_runtime_receipt_sha256=_sha(runtime),
        output_dir=tmp_path / "production-equivalence",
        resume=False,
        expectations=expectations,
    )

    assert result["all_gates_pass"] is True
    assert captured == {
        "source_root": source,
        "runtime_receipt_path": runtime,
        "expected_runtime_receipt_sha256": _sha(runtime),
        "implementation_kind": "in_process_reference",
    }


def test_distinct_runtime_resume_rejects_each_receipt_drift_without_mutation(
    tmp_path: Path,
) -> None:
    source, dataset, direct_runtime, expectations, retrieve = _fixture(tmp_path)
    direct = tmp_path / "direct"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=direct_runtime,
        output_dir=direct,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    port_runtime = tmp_path / "port-runtime.json"
    port_receipt = json.loads(direct_runtime.read_text(encoding="utf-8"))
    port_receipt["image_id"] = "sha256:" + "d" * 64
    port_runtime.write_text(json.dumps(port_receipt), encoding="utf-8")
    output = tmp_path / "partial-equivalence"
    partial = _run_equivalence_audit_for_test(
        source_root=source,
        dataset_path=dataset,
        direct_bundle=direct,
        direct_runtime_receipt_path=direct_runtime,
        expected_direct_runtime_receipt_sha256=_sha(direct_runtime),
        port_runtime_receipt_path=port_runtime,
        expected_port_runtime_receipt_sha256=_sha(port_runtime),
        output_dir=output,
        resume=False,
        retrieval=_port_adapter(image_digest="sha256:" + "d" * 64),
        stop_requested=lambda: True,
        expectations=expectations,
    )
    assert partial["status"] == "CHECKPOINTED"
    journal = output / "journal.jsonl"
    journal_before = journal.read_bytes()
    direct_before = direct_runtime.read_bytes()

    direct_drift = json.loads(direct_before)
    direct_drift["image_sbom_sha256"] = "3" * 64
    direct_runtime.write_text(json.dumps(direct_drift), encoding="utf-8")
    with pytest.raises(ValueError):
        _run_equivalence_audit_for_test(
            source_root=source,
            dataset_path=dataset,
            direct_bundle=direct,
            direct_runtime_receipt_path=direct_runtime,
            expected_direct_runtime_receipt_sha256=_sha(direct_runtime),
            port_runtime_receipt_path=port_runtime,
            expected_port_runtime_receipt_sha256=_sha(port_runtime),
            output_dir=output,
            resume=True,
            retrieval=_port_adapter(image_digest="sha256:" + "d" * 64),
            expectations=expectations,
        )
    assert journal.read_bytes() == journal_before
    direct_runtime.write_bytes(direct_before)

    port_drift = json.loads(port_runtime.read_text(encoding="utf-8"))
    port_drift["image_sbom_sha256"] = "4" * 64
    port_runtime.write_text(json.dumps(port_drift), encoding="utf-8")
    with pytest.raises(ValueError, match="resume contract"):
        _run_equivalence_audit_for_test(
            source_root=source,
            dataset_path=dataset,
            direct_bundle=direct,
            direct_runtime_receipt_path=direct_runtime,
            expected_direct_runtime_receipt_sha256=_sha(direct_runtime),
            port_runtime_receipt_path=port_runtime,
            expected_port_runtime_receipt_sha256=_sha(port_runtime),
            output_dir=output,
            resume=True,
            retrieval=_port_adapter(image_digest="sha256:" + "d" * 64),
            expectations=expectations,
        )
    assert journal.read_bytes() == journal_before


def test_partial_equivalence_rejects_symlinked_child(tmp_path: Path) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    direct = tmp_path / "direct"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=direct,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    output = tmp_path / "partial-symlink"
    _run_equivalence_audit_for_test(
        source_root=source,
        dataset_path=dataset,
        direct_bundle=direct,
        direct_runtime_receipt_path=runtime,
        expected_direct_runtime_receipt_sha256=_sha(runtime),
        port_runtime_receipt_path=runtime,
        expected_port_runtime_receipt_sha256=_sha(runtime),
        output_dir=output,
        resume=False,
        retrieval=_port_adapter(),
        stop_requested=lambda: True,
        expectations=expectations,
    )
    contract = output / "contract.json"
    target = tmp_path / "contract-target.json"
    target.write_bytes(contract.read_bytes())
    contract.unlink()
    contract.symlink_to(target)

    with pytest.raises(ValueError, match="regular non-symlink"):
        _run_equivalence_audit_for_test(
            source_root=source,
            dataset_path=dataset,
            direct_bundle=direct,
            direct_runtime_receipt_path=runtime,
            expected_direct_runtime_receipt_sha256=_sha(runtime),
            port_runtime_receipt_path=runtime,
            expected_port_runtime_receipt_sha256=_sha(runtime),
            output_dir=output,
            resume=True,
            retrieval=_port_adapter(),
            expectations=expectations,
        )


def test_matched_port_equivalence_reports_ranking_drift(tmp_path: Path) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    direct = tmp_path / "direct"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=direct,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    def reverse_retrieve(entry):
        corpus = [session[0]["content"] for session in entry["haystack_sessions"]]
        return (
            list(reversed(range(len(corpus)))),
            corpus,
            entry["haystack_session_ids"],
            entry["haystack_dates"],
        )

    drifting_port = PinnedUpstreamMemPalaceAdapter.from_retriever(
        identity=_port_adapter().identity,
        retrieve=reverse_retrieve,
    )
    output = tmp_path / "equivalence-drift"
    result = _run_equivalence_audit_for_test(
        source_root=source,
        dataset_path=dataset,
        direct_bundle=direct,
        direct_runtime_receipt_path=runtime,
        expected_direct_runtime_receipt_sha256=_sha(runtime),
        port_runtime_receipt_path=runtime,
        expected_port_runtime_receipt_sha256=_sha(runtime),
        output_dir=output,
        resume=False,
        retrieval=drifting_port,
        expectations=expectations,
    )
    assert result["all_gates_pass"] is False
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["exact_counts"]["session_order_exact"] == 3
    assert report["exact_counts"]["session_text_exact"] == 3
    assert report["exact_counts"]["ranking_exact"] == 0


def test_reproduction_checkpoints_and_resumes_byte_identically(tmp_path: Path) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    output = tmp_path / "output"
    calls = 0

    def stop_after_one() -> bool:
        nonlocal calls
        calls += 1
        return calls >= 1

    checkpoint = tmp_path / "checkpoint.marker"
    partial = run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=output,
        retrieve=retrieve,
        resume=False,
        stop_requested=stop_after_one,
        checkpoint_marker=checkpoint,
        expectations=expectations,
    )
    assert partial["status"] == "CHECKPOINTED"
    assert partial["completed"] == 1
    assert checkpoint.read_text(encoding="utf-8") == "checkpointed\n"

    manifest = run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=output,
        retrieve=retrieve,
        resume=True,
        expectations=expectations,
    )
    assert manifest["status"] == "MEMPALACE_CURRENT_LOCK_REPRODUCTION_COMPLETE"
    assert manifest["task_count"] == 3
    assert len((output / "results.jsonl").read_text(encoding="utf-8").splitlines()) == 3

    fresh = tmp_path / "fresh"
    fresh_manifest = run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=fresh,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    assert fresh_manifest["results_sha256"] == manifest["results_sha256"]
    assert (fresh / "results.jsonl").read_bytes() == (output / "results.jsonl").read_bytes()


def test_upstream_runner_hash_is_verified_before_module_execution(tmp_path: Path) -> None:
    source, _dataset, _runtime, expectations, _retrieve = _fixture(tmp_path)
    marker = tmp_path / "executed"
    (source / "benchmarks/longmemeval_bench.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        _load_upstream_retriever(source, expectations)
    assert not marker.exists()


def test_reproduction_rejects_journal_or_runtime_drift(tmp_path: Path) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    output = tmp_path / "output"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=output,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    journal = output / "journal.jsonl"
    journal.write_text(
        journal.read_text(encoding="utf-8").replace('"question_id":"q0"', '"question_id":"x"'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="journal"):
        run_reproduction(
            source_root=source,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            output_dir=output,
            retrieve=retrieve,
            resume=True,
            expectations=expectations,
        )

    # A self-consistent-looking manifest cannot bypass recomputation on resume.
    clean_output = tmp_path / "clean-output"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=clean_output,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    manifest_path = clean_output / "manifest.json"
    forged = json.loads(manifest_path.read_text(encoding="utf-8"))
    forged["results_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(forged), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest differs"):
        run_reproduction(
            source_root=source,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            output_dir=clean_output,
            retrieve=retrieve,
            resume=True,
            expectations=expectations,
        )

    runtime_payload = json.loads(runtime.read_text(encoding="utf-8"))
    runtime_payload["execution_provider"] = "CUDAExecutionProvider"
    runtime.write_text(json.dumps(runtime_payload), encoding="utf-8")
    with pytest.raises(ValueError, match="execution_provider"):
        run_reproduction(
            source_root=source,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            output_dir=tmp_path / "different",
            retrieve=retrieve,
            resume=False,
            expectations=expectations,
        )

    runtime_payload["execution_provider"] = "CPUExecutionProvider"
    runtime_payload["cotcodec_base_image_reference"] = "cotcodec:latest"
    runtime.write_text(json.dumps(runtime_payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not immutable"):
        run_reproduction(
            source_root=source,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            output_dir=tmp_path / "mutable-base",
            retrieve=retrieve,
            resume=False,
            expectations=expectations,
        )


def test_reproduction_truncates_only_an_incomplete_tail(tmp_path: Path) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    output = tmp_path / "output"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=output,
        retrieve=retrieve,
        resume=False,
        stop_requested=lambda: True,
        expectations=expectations,
    )
    journal = output / "journal.jsonl"
    with journal.open("ab") as handle:
        handle.write(b'{"partial":')
    manifest = run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=output,
        retrieve=retrieve,
        resume=True,
        expectations=expectations,
    )
    assert manifest["task_count"] == 3
    assert journal.read_bytes().endswith(b"\n")


def test_completed_reproduction_rejects_tail_without_mutating(tmp_path: Path) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    output = tmp_path / "output"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=output,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    journal = output / "journal.jsonl"
    with journal.open("ab") as handle:
        handle.write(b'{"partial":')
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="finalized journal"):
        run_reproduction(
            source_root=source,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            output_dir=output,
            retrieve=retrieve,
            resume=True,
            expectations=expectations,
        )
    assert journal.read_bytes() == before


def test_reproduction_and_equivalence_reject_symlinked_roots(tmp_path: Path) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    output_target = tmp_path / "output-target"
    output_target.mkdir()
    output_link = tmp_path / "output-link"
    output_link.symlink_to(output_target, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic links"):
        run_reproduction(
            source_root=source,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            output_dir=output_link,
            retrieve=retrieve,
            resume=True,
            expectations=expectations,
        )

    direct = tmp_path / "direct"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=direct,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )
    direct_link = tmp_path / "direct-link"
    direct_link.symlink_to(direct, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic links"):
        _run_equivalence_audit_for_test(
            source_root=source,
            dataset_path=dataset,
            direct_bundle=direct_link,
            direct_runtime_receipt_path=runtime,
            expected_direct_runtime_receipt_sha256=_sha(runtime),
            port_runtime_receipt_path=runtime,
            expected_port_runtime_receipt_sha256=_sha(runtime),
            output_dir=tmp_path / "equivalence",
            resume=False,
            retrieval=_port_adapter(),
            expectations=expectations,
        )


def test_pair_auditor_requires_identical_rankings_and_released_targets(
    tmp_path: Path,
) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output in (first, second):
        run_reproduction(
            source_root=source,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            output_dir=output,
            retrieve=retrieve,
            resume=False,
            expectations=expectations,
        )
    report = compare_reproductions(
        bundle_a=first,
        bundle_b=second,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        expected_runtime_receipt_sha256=_sha(runtime),
        expectations=expectations,
        targets=PairTargets(
            released_recall_any_at_5_count=3,
            released_recall_any_at_10_count=3,
        ),
    )
    assert report["status"] == "MEMPALACE_CURRENT_LOCK_PAIR_REPRODUCTION_PASS"
    assert all(report["gates"].values())
    with pytest.raises(ValueError, match="external runtime receipt digest"):
        compare_reproductions(
            bundle_a=first,
            bundle_b=second,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            expected_runtime_receipt_sha256="0" * 64,
            expectations=expectations,
            targets=PairTargets(3, 3),
        )

    divergent = tmp_path / "divergent"

    def retrieve_divergently(entry):
        rankings, corpus, ids, timestamps = retrieve(entry)
        return list(reversed(rankings)), corpus, ids, timestamps

    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=divergent,
        retrieve=retrieve_divergently,
        resume=False,
        expectations=expectations,
    )
    failed = compare_reproductions(
        bundle_a=first,
        bundle_b=divergent,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        expected_runtime_receipt_sha256=_sha(runtime),
        expectations=expectations,
        targets=PairTargets(
            released_recall_any_at_5_count=3,
            released_recall_any_at_10_count=3,
        ),
    )
    assert failed["status"] == "MEMPALACE_CURRENT_LOCK_PAIR_REPRODUCTION_FAIL"
    assert not failed["gates"]["ordered_rankings_identical"]
    assert failed["first_ranking_mismatch_question_id"] == "q0"

    tampered_journal = second / "journal.jsonl"
    before = tampered_journal.read_bytes() + b'{"partial":'
    tampered_journal.write_bytes(before)
    with pytest.raises(ValueError, match="incomplete"):
        compare_reproductions(
            bundle_a=first,
            bundle_b=second,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            expected_runtime_receipt_sha256=_sha(runtime),
            expectations=expectations,
            targets=PairTargets(3, 3),
        )
    assert tampered_journal.read_bytes() == before


def test_pair_auditor_rejects_impossible_corpus_ids_and_report_overwrite(
    tmp_path: Path,
) -> None:
    source, dataset, runtime, expectations, retrieve = _fixture(tmp_path)
    valid = tmp_path / "valid"
    invalid = tmp_path / "invalid"
    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=valid,
        retrieve=retrieve,
        resume=False,
        expectations=expectations,
    )

    def retrieve_impossible(entry):
        rankings, corpus, ids, timestamps = retrieve(entry)
        ids[0] = "not-in-source-corpus"
        return rankings, corpus, ids, timestamps

    run_reproduction(
        source_root=source,
        dataset_path=dataset,
        runtime_receipt_path=runtime,
        output_dir=invalid,
        retrieve=retrieve_impossible,
        resume=False,
        expectations=expectations,
    )
    with pytest.raises(ValueError, match="source corpus"):
        compare_reproductions(
            bundle_a=valid,
            bundle_b=invalid,
            dataset_path=dataset,
            runtime_receipt_path=runtime,
            expected_runtime_receipt_sha256=_sha(runtime),
            expectations=expectations,
            targets=PairTargets(3, 3),
        )

    report_path = tmp_path / "report.json"
    _write_report(report_path, {"status": "first"})
    before = report_path.read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        _write_report(report_path, {"status": "second"})
    assert report_path.read_bytes() == before

    valid_records = [
        json.loads(line)
        for line in (valid / "journal.jsonl").read_text().splitlines()
    ]
    truncated = deepcopy(valid_records)
    truncated[0]["result"]["retrieval_results"]["ranked_items"] = truncated[0][
        "result"
    ]["retrieval_results"]["ranked_items"][:1]
    source_rows = json.loads(dataset.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="ranking length"):
        _rankings_and_metrics(truncated, source_rows)
