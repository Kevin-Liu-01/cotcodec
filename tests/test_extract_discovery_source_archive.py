from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

import scripts.extract_discovery_source_archive as extraction_module
from scripts.extract_discovery_source_archive import validate_and_extract


def _fixture(
    tmp_path: Path, *, script: bytes = b"print('ok')\n"
) -> tuple[Path, Path, str, str, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    archive_path = tmp_path / "source.tar.gz"
    files = {"scripts/run.py": script, "uv.lock": b"version = 1\n"}
    with (
        archive_path.open("xb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive,
    ):
        for name, contents in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            info.mode = 0o644
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(contents))
    archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    git_sha = "7" * 40
    git_tree = "8" * 40
    manifest = list(files)
    receipt = {
        "schema_version": 2,
        "mode": "discovery",
        "archive": str(archive_path),
        "archive_sha256": archive_sha256,
        "archive_format": "normalized-worktree-tar+gzip-mtime-zero",
        "file_count": len(manifest),
        "file_manifest_sha256": hashlib.sha256(
            json.dumps(manifest, separators=(",", ":")).encode()
        ).hexdigest(),
        "file_manifest": manifest,
        "git_sha": git_sha,
        "git_tree": git_tree,
        "selected_ref": "HEAD",
        "uv_lock_sha256": hashlib.sha256(files["uv.lock"]).hexdigest(),
        "worktree_clean": False,
        "data_excluded": True,
        "metadata_normalized": True,
    }
    receipt_path = tmp_path / "source.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return archive_path, receipt_path, archive_sha256, git_sha, git_tree


def test_validate_and_extract_requires_exact_receipt_and_archive(tmp_path: Path) -> None:
    archive, receipt, digest, git_sha, git_tree = _fixture(tmp_path)
    output = tmp_path / "context"
    output.mkdir()
    members = validate_and_extract(
        archive_path=archive,
        receipt_path=receipt,
        output_dir=output,
        expected_archive_sha256=digest,
        expected_git_sha=git_sha,
        expected_git_tree=git_tree,
    )
    assert members == ("scripts/run.py", "uv.lock")
    assert (output / "scripts/run.py").read_text(encoding="utf-8") == "print('ok')\n"


def test_validate_and_extract_rejects_stale_output_and_receipt_drift(
    tmp_path: Path,
) -> None:
    archive, receipt, digest, git_sha, git_tree = _fixture(tmp_path)
    output = tmp_path / "context"
    output.mkdir()
    (output / "stale").write_text("old", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        validate_and_extract(
            archive_path=archive,
            receipt_path=receipt,
            output_dir=output,
            expected_archive_sha256=digest,
            expected_git_sha=git_sha,
            expected_git_tree=git_tree,
        )

    output = tmp_path / "fresh"
    output.mkdir()
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["git_tree"] = "9" * 40
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="receipt"):
        validate_and_extract(
            archive_path=archive,
            receipt_path=receipt,
            output_dir=output,
            expected_archive_sha256=digest,
            expected_git_sha=git_sha,
            expected_git_tree=git_tree,
        )


def test_validate_and_extract_uses_the_exact_hashed_archive_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, receipt, digest, git_sha, git_tree = _fixture(tmp_path / "good")
    evil, _evil_receipt, _evil_digest, _evil_git_sha, _evil_git_tree = _fixture(
        tmp_path / "evil", script=b"print('no')\n"
    )
    output = tmp_path / "context"
    output.mkdir()
    real_tar_open = extraction_module.tarfile.open

    def swap_after_snapshot(*args: object, **kwargs: object):
        archive.unlink()
        archive.write_bytes(evil.read_bytes())
        return real_tar_open(*args, **kwargs)

    monkeypatch.setattr(extraction_module.tarfile, "open", swap_after_snapshot)
    validate_and_extract(
        archive_path=archive,
        receipt_path=receipt,
        output_dir=output,
        expected_archive_sha256=digest,
        expected_git_sha=git_sha,
        expected_git_tree=git_tree,
    )
    assert (output / "scripts/run.py").read_text(encoding="utf-8") == "print('ok')\n"
