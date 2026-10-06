from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.prepare_mempalace_source_context import (
    SourceExpectations,
    _manifest_sha256,
    git_file_manifest,
    prepare_context,
    verify_context,
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *arguments], text=True).strip()


def _fixture(tmp_path: Path) -> tuple[Path, SourceExpectations]:
    origin = tmp_path / "official.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    checkout = tmp_path / "checkout"
    subprocess.run(["git", "init", str(checkout)], check=True, capture_output=True)
    (checkout / "runner.py").write_text("runner\n", encoding="utf-8")
    (checkout / "nested").mkdir()
    (checkout / "nested" / "data.txt").write_text("data\n", encoding="utf-8")
    # This sibling catches the distinction between directory traversal order
    # and canonical ordering of complete relative file names.
    (checkout / "nested-peer.txt").write_text("peer\n", encoding="utf-8")
    (checkout / "link").symlink_to("runner.py")
    subprocess.run(["git", "-C", str(checkout), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(checkout),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@invalid",
            "commit",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(checkout), "remote", "add", "origin", str(origin)], check=True
    )
    revision = _git(checkout, "rev-parse", "HEAD")
    tree = _git(checkout, "rev-parse", "HEAD^{tree}")
    manifest = git_file_manifest(checkout, revision)
    archive = tmp_path / "source.tar"
    with archive.open("wb") as handle:
        subprocess.run(
            ["git", "-C", str(checkout), "archive", "--format=tar", revision],
            check=True,
            stdout=handle,
        )
    expectations = SourceExpectations(
        repository=str(origin),
        revision=revision,
        tree=tree,
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        manifest_sha256=_manifest_sha256(manifest),
        file_count=len(manifest),
    )
    return checkout, expectations


def test_prepare_context_binds_every_git_file_and_safe_symlink(tmp_path: Path) -> None:
    checkout, expectations = _fixture(tmp_path)
    output = tmp_path / "context"
    receipt = prepare_context(checkout, output, expectations=expectations)

    assert receipt["status"] == "VERIFIED_MEMPALACE_SOURCE_CONTEXT"
    assert receipt["file_count"] == 4
    assert (output / "link").is_symlink()
    assert verify_context(output, expectations=expectations) == receipt


def test_context_verifier_rejects_any_unbound_file_or_receipt_drift(tmp_path: Path) -> None:
    checkout, expectations = _fixture(tmp_path)
    output = tmp_path / "context"
    prepare_context(checkout, output, expectations=expectations)
    (output / "nested" / "unbound.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="pinned Git tree"):
        verify_context(output, expectations=expectations)

    (output / "nested" / "unbound.txt").unlink()
    receipt_path = output / ".cotcodec-mempalace-source.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["source_archive_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="receipt differs"):
        verify_context(output, expectations=expectations)


def test_prepare_context_rejects_dirty_checkout_or_wrong_origin(tmp_path: Path) -> None:
    checkout, expectations = _fixture(tmp_path)
    (checkout / "dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(ValueError, match="completely clean"):
        prepare_context(checkout, tmp_path / "dirty-context", expectations=expectations)

    (checkout / "dirty.txt").unlink()
    wrong = SourceExpectations(**{**expectations.__dict__, "repository": "other"})
    with pytest.raises(ValueError, match="official repository"):
        prepare_context(checkout, tmp_path / "wrong-context", expectations=wrong)
