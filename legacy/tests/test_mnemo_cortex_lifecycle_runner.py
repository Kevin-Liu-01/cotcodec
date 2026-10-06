from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from scripts.run_mnemo_cortex_lifecycle_doctor import (
    MnemoCortexLifecycleRunnerError,
    _extract_source_archive,
    _parse_phase,
    _wheelhouse_contract,
)


def _archive(name: str, data: bytes = b"payload") -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:") as archive:
        member = tarfile.TarInfo(name)
        member.size = len(data)
        archive.addfile(member, io.BytesIO(data))
    return output.getvalue()


def _symlink_archive(name: str, target: str) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:") as archive:
        member = tarfile.TarInfo(name)
        member.type = tarfile.SYMTYPE
        member.linkname = target
        archive.addfile(member)
    return output.getvalue()


def _wheelhouse(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "transport"
    wheels = root / "wheels"
    wheels.mkdir(parents=True)
    lock = b"package==1.0\n"
    wheel = b"wheel-payload"
    lock_name = "requirements-linux-x86_64-cp312.txt"
    wheel_name = "package-1.0-py3-none-any.whl"
    (root / lock_name).write_bytes(lock)
    (wheels / wheel_name).write_bytes(wheel)
    manifest = {
        "schema_version": 1,
        "requirements": {
            "filename": lock_name,
            "bytes": len(lock),
            "sha256": hashlib.sha256(lock).hexdigest(),
        },
        "wheel_count": 1,
        "total_wheel_bytes": len(wheel),
        "wheels": [
            {
                "filename": wheel_name,
                "bytes": len(wheel),
                "sha256": hashlib.sha256(wheel).hexdigest(),
            }
        ],
    }
    manifest_raw = (json.dumps(manifest, sort_keys=True) + "\n").encode()
    expected = tmp_path / "expected-manifest.json"
    expected.write_bytes(manifest_raw)
    (root / "wheelhouse-manifest.json").write_bytes(manifest_raw)
    return root, expected


def test_extract_source_archive_accepts_regular_file(tmp_path: Path) -> None:
    _extract_source_archive(_archive("source/file.txt"), tmp_path)
    assert (tmp_path / "source/file.txt").read_bytes() == b"payload"


def test_extract_source_archive_accepts_confined_relative_symlink(tmp_path: Path) -> None:
    (tmp_path / "source").mkdir()
    (tmp_path / "target.txt").write_text("target", encoding="utf-8")
    _extract_source_archive(_symlink_archive("source/link.txt", "../target.txt"), tmp_path)
    assert (tmp_path / "source/link.txt").resolve() == tmp_path / "target.txt"


def test_wheelhouse_contract_accepts_exact_transport(tmp_path: Path) -> None:
    root, expected = _wheelhouse(tmp_path)
    receipt = _wheelhouse_contract(root, expected_manifest_path=expected)
    assert receipt["wheel_count"] == 1
    assert receipt["total_wheel_bytes"] == len(b"wheel-payload")


def test_wheelhouse_contract_rejects_wheel_drift(tmp_path: Path) -> None:
    root, expected = _wheelhouse(tmp_path)
    next((root / "wheels").iterdir()).write_bytes(b"changed")
    with pytest.raises(MnemoCortexLifecycleRunnerError, match="artifact drifted"):
        _wheelhouse_contract(root, expected_manifest_path=expected)


def test_wheelhouse_contract_rejects_unreceipted_file(tmp_path: Path) -> None:
    root, expected = _wheelhouse(tmp_path)
    (root / "extra.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(MnemoCortexLifecycleRunnerError, match="top-level"):
        _wheelhouse_contract(root, expected_manifest_path=expected)


def test_parse_phase_preserves_unexpected_false_check() -> None:
    payload = {
        "phase": 2,
        "checks": {"unexpected_source_behavior": False},
        "metrics": {"observed": True},
    }
    raw = (
        b"COTCODEC_MNEMO_CORTEX_PHASE="
        + json.dumps(payload).encode()
        + b"\nMnemo Cortex doctor checks failed\n"
    )
    assert _parse_phase(raw, 2) == payload


def test_parse_phase_rejects_non_boolean_check() -> None:
    payload = {
        "phase": 1,
        "checks": {"invalid": "true"},
        "metrics": {},
    }
    raw = b"COTCODEC_MNEMO_CORTEX_PHASE=" + json.dumps(payload).encode()
    with pytest.raises(MnemoCortexLifecycleRunnerError, match="report drifted"):
        _parse_phase(raw, 1)


@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt"])
def test_extract_source_archive_rejects_path_escape(tmp_path: Path, name: str) -> None:
    with pytest.raises(MnemoCortexLifecycleRunnerError, match="unsafe"):
        _extract_source_archive(_archive(name), tmp_path)


@pytest.mark.parametrize("target", ["../../escape.txt", "/absolute.txt"])
def test_extract_source_archive_rejects_symlink_escape(
    tmp_path: Path, target: str
) -> None:
    with pytest.raises(MnemoCortexLifecycleRunnerError, match="unsafe"):
        _extract_source_archive(_symlink_archive("source/link.txt", target), tmp_path)
