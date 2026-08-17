from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.prepare_past_bench_runtime import (
    RUNTIME_OVERLAY,
    PastBenchRuntimeError,
    _context_receipt,
    _git_tree_sha,
    _sha256_bytes,
    build_command,
    prepare_context,
    validate_runtime_contract,
    verify_context,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_CHECKOUT = Path("/tmp/cotcodec-memory-audit.eRYVgA/past-bench")


def _context_fixture(root: Path) -> Path:
    context = root / "context"
    context.mkdir()
    source = context / "src/example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")

    source_manifest = [
        {
            "mode": "100644",
            "path": "src/example.py",
            "sha256": _sha256_bytes(source.read_bytes()),
            "size": source.stat().st_size,
        }
    ]
    overlay = context / ".cotcodec"
    overlay.mkdir()
    overlay_rows = []
    for name in sorted(RUNTIME_OVERLAY):
        path = overlay / name
        if name == "past-bench-source.yaml":
            data = yaml.safe_dump(
                {
                    "revision": "b" * 40,
                    "tree_sha": _git_tree_sha(context, source_manifest),
                    "source_archive_sha256": "c" * 64,
                },
                sort_keys=True,
            ).encode()
        elif name == "past-bench-runtime.yaml":
            data = yaml.safe_dump(
                {
                    "admission": {
                        "source_receipt_sha256": "a" * 64,
                        "runtime_receipt_sha256": "d" * 64,
                    }
                },
                sort_keys=True,
            ).encode()
        else:
            data = f"fixture:{name}\n".encode()
        path.write_bytes(data)
        overlay_rows.append(
            {
                "path": f".cotcodec/{name}",
                "sha256": _sha256_bytes(data),
                "size": len(data),
            }
        )
    source_receipt = {
        "receipt_sha256": "a" * 64,
        "checkout": {
            "revision": "b" * 40,
            "source_archive_sha256": "c" * 64,
        },
    }
    runtime_receipt = {"receipt_sha256": "d" * 64}
    receipt = _context_receipt(
        source_receipt, runtime_receipt, source_manifest, overlay_rows
    )
    (overlay / "source-context-receipt.json").write_text(
        json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8"
    )
    return context


def test_context_verifier_binds_source_and_every_runtime_file(tmp_path: Path) -> None:
    context = _context_fixture(tmp_path)
    receipt = verify_context(context, trusted_project_root=None)

    assert receipt["status"] == "VERIFIED_PAST_BUILD_CONTEXT_NOT_IMAGE"
    assert receipt["scientific_result"] is False
    assert receipt["source_file_count"] == 1
    assert len(receipt["runtime_files"]) == len(RUNTIME_OVERLAY)

    (context / "src/example.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source differs"):
        verify_context(context, trusted_project_root=None)


def test_context_verifier_rejects_self_minted_context(tmp_path: Path) -> None:
    context = _context_fixture(tmp_path)

    with pytest.raises(ValueError, match="registered host file"):
        verify_context(context)


def test_context_verifier_rejects_runtime_overlay_drift(tmp_path: Path) -> None:
    context = _context_fixture(tmp_path)
    (context / ".cotcodec/requirements.lock").write_text(
        "tampered\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="runtime overlay differs"):
        verify_context(context, trusted_project_root=None)


def test_build_command_rejects_self_minted_context(tmp_path: Path) -> None:
    context = _context_fixture(tmp_path)

    with pytest.raises(ValueError, match="registered host file"):
        build_command(context, tag="cotcodec-past:test")


def test_registered_dockerfile_has_no_mutable_runtime_inputs() -> None:
    dockerfile = (
        PROJECT_ROOT / "infra/research/past-bench/Dockerfile"
    ).read_text(encoding="utf-8")

    assert "FROM docker.io/library/python@sha256:" in dockerfile
    assert ":latest" not in dockerfile
    assert "apt-get" not in dockerfile
    assert "--require-hashes" in dockerfile
    assert "--no-deps" in dockerfile
    assert "--no-build-isolation" in dockerfile
    assert "--runtime container" not in dockerfile
    assert "--self-contained" in dockerfile
    assert "apply_checkpoint_overlay.py" in dockerfile
    assert "checkpoint_runtime_selftest.py" in dockerfile
    assert "episode-boundary-v1" in dockerfile


def test_registered_slurm_builder_is_h100_and_candidate_only() -> None:
    batch = (
        PROJECT_ROOT / "infra/slurm/host-single-node/past-bench-build.sbatch"
    ).read_text(encoding="utf-8")

    assert "#SBATCH --gres=gpu:h100:1" in batch
    assert "${SLURM_JOB_ID" in batch
    assert "--network none" in batch
    assert "--read-only" in batch
    assert "--cap-drop ALL" in batch
    assert "--security-opt no-new-privileges" in batch
    assert "--user 65534:65534" in batch
    assert "HOST_STDLIB_RECEIPT_PRECHECK_ONLY" in batch
    assert "full_context_verification" in batch
    assert "PAST_DISCOVERY_IMAGE_BUILT_NOT_SCIENTIFIC_RESULT" in batch
    assert '"publication_ready": False' in batch
    assert "checkpoint_runtime_selftest.py" in batch
    assert "checkpoint-cli-help.txt" in batch
    assert "real SM01 stop/resume equivalence" in batch


def test_runtime_contract_is_explicitly_candidate_only() -> None:
    contract = yaml.safe_load(
        (PROJECT_ROOT / "research/source-contracts/past-bench-runtime.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert contract["status"] == "LOCKED_BUILD_INPUTS_NOT_EXECUTION"
    assert contract["scientific_result"] is False
    assert contract["execution"]["publication_ready"] is False
    assert contract["execution"]["runtime_mode"] == (
        "whole-process-local-inside-docker"
    )
    assert contract["execution"]["model_transport"] == "not-implemented"
    assert contract["execution"]["upstream_nested_runtime_container_supported"] is False
    assert contract["lock"]["upstream_test_file_count"] == 36
    assert len(contract["admission"]["source_receipt_sha256"]) == 64
    assert len(contract["admission"]["runtime_receipt_sha256"]) == 64


@pytest.mark.skipif(not LIVE_CHECKOUT.is_dir(), reason="pinned PAST checkout unavailable")
def test_live_runtime_contract_binds_lock_requirements_and_test_roster() -> None:
    receipt = validate_runtime_contract(LIVE_CHECKOUT)

    assert receipt["status"] == "VALIDATED_LOCKED_BUILD_INPUTS_NOT_EXECUTION"
    assert receipt["locked_package_count"] == 106
    assert receipt["upstream_requirement_count"] == 31
    assert receipt["upstream_test_file_count"] == 36


@pytest.mark.skipif(not LIVE_CHECKOUT.is_dir(), reason="pinned PAST checkout unavailable")
def test_live_context_compiler_materializes_the_complete_git_tree(
    tmp_path: Path,
) -> None:
    output = tmp_path / "past-context"
    try:
        receipt = prepare_context(LIVE_CHECKOUT, output)
    except PastBenchRuntimeError as exc:
        if str(exc) != "PAST source-doctor receipt is not registered":
            raise
        pytest.skip(
            "retained live checkout is not bound to the current evolving source ledger"
        )

    assert receipt["status"] == "VERIFIED_PAST_BUILD_CONTEXT_NOT_IMAGE"
    assert receipt["source_revision"] == "f8223517ae7491e776b69793d9f11e9d074ab42e"
    assert receipt["source_file_count"] == 2159
    assert verify_context(output) == receipt

    command = build_command(output, tag="cotcodec-past:test")
    assert command[:7] == [
        "docker",
        "buildx",
        "build",
        "--load",
        "--platform",
        "linux/amd64",
        "--network",
    ]
    assert (
        f"PAST_RUNTIME_CONTRACT_SHA256={receipt['runtime_receipt_sha256']}" in command
    )
    assert f"PAST_SOURCE_RECEIPT_SHA256={receipt['source_receipt_sha256']}" in command
