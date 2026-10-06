from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from scripts.prepare_chroma_minilm import (
    EXPECTED_MODEL_FILES,
    prepare_artifact,
    verify_prepared_artifact,
)


def _archive(path: Path, *, unsafe: bool = False, missing: bool = False) -> str:
    with tarfile.open(path, "w:gz") as bundle:
        members = EXPECTED_MODEL_FILES[:-1] if missing else EXPECTED_MODEL_FILES
        for index, name in enumerate(members):
            content = f"file-{index}".encode()
            member = tarfile.TarInfo(name)
            member.size = len(content)
            bundle.addfile(member, io.BytesIO(content))
        if unsafe:
            link = tarfile.TarInfo("onnx/link")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            bundle.addfile(link)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_prepare_and_verify_exact_offline_model_artifact(tmp_path: Path) -> None:
    archive = tmp_path / "model.tar.gz"
    digest = _archive(archive)
    output = tmp_path / "prepared"
    receipt = prepare_artifact(
        output,
        archive_path=archive,
        expected_archive_sha256=digest,
    )

    assert receipt["status"] == "VERIFIED_CHROMA_MINILM_ARTIFACT"
    assert receipt["archive_sha256"] == digest
    assert [row["path"] for row in receipt["files"]] == list(EXPECTED_MODEL_FILES)
    assert verify_prepared_artifact(
        output, expected_archive_sha256=digest
    ) == receipt
    assert prepare_artifact(
        output,
        archive_path=None,
        expected_archive_sha256=digest,
    ) == receipt


@pytest.mark.parametrize("unsafe,missing", [(True, False), (False, True)])
def test_prepare_rejects_unsafe_or_incomplete_archives(
    tmp_path: Path, unsafe: bool, missing: bool
) -> None:
    archive = tmp_path / "bad.tar.gz"
    digest = _archive(archive, unsafe=unsafe, missing=missing)
    with pytest.raises(ValueError, match="unexpected|exact required"):
        prepare_artifact(
            tmp_path / "prepared",
            archive_path=archive,
            expected_archive_sha256=digest,
        )


def test_prepare_and_verify_fail_on_hash_or_file_tamper(tmp_path: Path) -> None:
    archive = tmp_path / "model.tar.gz"
    digest = _archive(archive)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        prepare_artifact(
            tmp_path / "wrong",
            archive_path=archive,
            expected_archive_sha256="0" * 64,
        )

    output = tmp_path / "prepared"
    prepare_artifact(output, archive_path=archive, expected_archive_sha256=digest)
    (output / EXPECTED_MODEL_FILES[0]).write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="receipt differs"):
        verify_prepared_artifact(output, expected_archive_sha256=digest)


def test_verify_rejects_unbound_nested_or_empty_entries(tmp_path: Path) -> None:
    archive = tmp_path / "model.tar.gz"
    digest = _archive(archive)
    output = tmp_path / "prepared"
    prepare_artifact(output, archive_path=archive, expected_archive_sha256=digest)
    (output / "onnx" / "unbound.bin").write_bytes(b"not in the receipt")
    with pytest.raises(ValueError, match="tree roster drifted"):
        verify_prepared_artifact(output, expected_archive_sha256=digest)

    (output / "onnx" / "unbound.bin").unlink()
    (output / "onnx" / "empty-extra").mkdir()
    with pytest.raises(ValueError, match="tree roster drifted"):
        verify_prepared_artifact(output, expected_archive_sha256=digest)
