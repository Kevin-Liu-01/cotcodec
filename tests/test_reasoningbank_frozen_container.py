from __future__ import annotations

import copy
import os
from collections.abc import Sequence
from pathlib import Path

import pytest

import scripts.run_reasoningbank_frozen_bank_container as container_module
from harness.memory_trials.dense_control import (
    BGE_POOLING_STRATEGY,
    DenseEmbeddingIdentity,
    InProcessDenseEmbeddingClient,
)
from harness.memory_trials.procedural_bank import (
    FrozenProceduralBankRetriever,
    freeze_procedural_bank,
)
from scripts.run_reasoningbank_frozen_bank_container import (
    ContainerDoctorError,
    _validate_container,
    _validate_retrieval_rows,
)
from scripts.run_reasoningbank_frozen_bank_doctor import _fixture


class _TopicEncoder:
    dimensions = 384
    maximum_tokens = 512
    pooling_strategy = BGE_POOLING_STRATEGY

    def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]:
        vectors: list[list[float]] = []
        for text in texts:
            lowered = text.casefold()
            row = [0.0] * self.dimensions
            if any(
                word in lowered
                for word in ("password", "credential", "authentication", "authenticate")
            ):
                row[0] = 1.0
            elif any(word in lowered for word in ("schema", "migration")):
                row[1] = 1.0
            elif any(
                word in lowered
                for word in (
                    "reflog",
                    "lost git",
                    "accidental reset",
                    "hard reset",
                    "version history",
                    "versioned storage",
                    "document version",
                )
            ):
                row[2] = 1.0
            elif any(word in lowered for word in ("merge conflict", "conflict")):
                row[3] = 1.0
            elif any(
                word in lowered
                for word in (
                    "flight",
                    "airline",
                    "ticket",
                    "fare rules",
                    "rental car",
                    "conference registration",
                )
            ):
                row[4] = 1.0
            elif any(
                word in lowered
                for word in (
                    "hotel",
                    "reservation",
                    "cancellation deadline",
                )
            ):
                row[5] = 1.0
            else:
                raise AssertionError(f"unclassified fixture text: {text}")
            vectors.append(row)
        return vectors, sum(len(text.split()) for text in texts)


def _fixture_rows():
    items, split, queries = _fixture()
    identity = DenseEmbeddingIdentity(
        artifact_root_sha256="1" * 64,
        model_receipt_sha256="2" * 64,
    )
    embedding = InProcessDenseEmbeddingClient(_TopicEncoder(), identity)
    bank = freeze_procedural_bank(items, split_manifest=split, embedding=embedding)
    retriever = FrozenProceduralBankRetriever(bank, embedding)
    rows = [
        {
            "query": query.model_dump(mode="json"),
            "expected_source_task_id": expected,
            "retrieval": retriever.retrieve(query).model_dump(mode="json"),
        }
        for query, expected in queries
    ]
    return bank, rows


def _inspect(model_root: Path, receipt_root: Path, output: Path) -> dict:
    return {
        "Image": "sha256:" + "a" * 64,
        "Config": {
            "User": f"{os.getuid()}:{os.getgid()}",
            "Env": ["USER=cotcodec-doctor", "LOGNAME=cotcodec-doctor"],
        },
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges"],
            "PidsLimit": 256,
            "NanoCpus": 4_000_000_000,
            "Memory": 4 * 1024**3,
            "DeviceRequests": None,
        },
        "State": {"Running": False, "ExitCode": 0, "OOMKilled": False},
        "Mounts": [
            {"Destination": "/models", "Source": str(model_root), "RW": False},
            {"Destination": "/receipts", "Source": str(receipt_root), "RW": False},
            {"Destination": "/outputs", "Source": str(output), "RW": True},
        ],
    }


def test_live_container_contract_accepts_exact_isolation(tmp_path: Path) -> None:
    model_root = (tmp_path / "models").resolve()
    receipt_root = (tmp_path / "receipts").resolve()
    output = (tmp_path / "output").resolve()
    projection = _validate_container(
        _inspect(model_root, receipt_root, output),
        image_id="sha256:" + "a" * 64,
        model_root=model_root,
        receipt_root=receipt_root,
        output=output,
        require_stopped=True,
    )
    assert projection["network_mode"] == "none"
    assert projection["device_requests"] is None
    assert projection["exit_code"] == 0


@pytest.mark.parametrize(
    ("path", "value"),
    (("NetworkMode", "bridge"), ("ReadonlyRootfs", False), ("DeviceRequests", [{}])),
)
def test_live_container_contract_rejects_isolation_drift(
    tmp_path: Path,
    path: str,
    value: object,
) -> None:
    model_root = (tmp_path / "models").resolve()
    receipt_root = (tmp_path / "receipts").resolve()
    output = (tmp_path / "output").resolve()
    inspect = copy.deepcopy(_inspect(model_root, receipt_root, output))
    inspect["HostConfig"][path] = value
    with pytest.raises(ContainerDoctorError, match="isolation or resource"):
        _validate_container(
            inspect,
            image_id="sha256:" + "a" * 64,
            model_root=model_root,
            receipt_root=receipt_root,
            output=output,
            require_stopped=True,
        )


def test_live_container_contract_rejects_writable_model_mount(tmp_path: Path) -> None:
    model_root = (tmp_path / "models").resolve()
    receipt_root = (tmp_path / "receipts").resolve()
    output = (tmp_path / "output").resolve()
    inspect = _inspect(model_root, receipt_root, output)
    inspect["Mounts"][0]["RW"] = True
    with pytest.raises(ContainerDoctorError, match="mount drifted: /models"):
        _validate_container(
            inspect,
            image_id="sha256:" + "a" * 64,
            model_root=model_root,
            receipt_root=receipt_root,
            output=output,
            require_stopped=True,
        )


def test_host_recomputes_registered_retrieval_roster_and_top_one() -> None:
    bank, rows = _fixture_rows()
    _validate_retrieval_rows(rows, bank=bank)
    tampered = copy.deepcopy(rows)
    tampered[0]["expected_source_task_id"] = "train-db-migration"
    with pytest.raises(ContainerDoctorError, match="roster or oracle"):
        _validate_retrieval_rows(tampered, bank=bank)


def test_host_rejects_retrieval_receipt_not_bound_to_query() -> None:
    bank, rows = _fixture_rows()
    tampered = copy.deepcopy(rows)
    tampered[0]["retrieval"]["query_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="retrieval digest mismatch"):
        _validate_retrieval_rows(tampered, bank=bank)


def test_image_validator_rejects_label_compatible_unpinned_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspect = {
        "Id": "sha256:" + "0" * 64,
        "Architecture": "arm64",
        "Os": "linux",
        "Config": {
            "Labels": {
                "org.opencontainers.image.title": container_module.EXPECTED_IMAGE_TITLE,
                "org.opencontainers.image.cotcodec-base-image": (
                    container_module.EXPECTED_BASE_IMAGE
                ),
                "org.opencontainers.image.cotcodec-code-sha256": (
                    container_module.EXPECTED_CODE_SHA256
                ),
                "org.opencontainers.image.cotcodec-torch-cpu-wheel-sha256": (
                    container_module.EXPECTED_TORCH_WHEEL_SHA256
                ),
                "org.opencontainers.image.cotcodec-scientific-result": "false",
            }
        },
    }
    monkeypatch.setattr(container_module, "_one_inspect", lambda *_: inspect)
    with pytest.raises(ContainerDoctorError, match="frozen contract"):
        container_module._validate_image("mutable-tag")
