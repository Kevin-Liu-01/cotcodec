from __future__ import annotations

import gzip
import subprocess
import tarfile
from pathlib import Path

import pytest

from scripts.create_source_archive import create_archive, write_receipt


def _run(root: Path, *args: str) -> None:
    subprocess.run(args, cwd=root, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _run(root, "git", "init", "-q")
    _run(root, "git", "config", "user.email", "test@example.com")
    _run(root, "git", "config", "user.name", "Test")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (root / "research.py").write_text("print('sealed')\n", encoding="utf-8")
    _run(root, "git", "add", ".")
    _run(root, "git", "commit", "-qm", "initial")
    return root


def test_publication_archive_is_commit_only_and_deterministic(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    first = create_archive(
        root,
        tmp_path / "first.tar.gz",
        mode="publication",
        ref=head,
    )
    second = create_archive(
        root,
        tmp_path / "second.tar.gz",
        mode="publication",
        ref=head,
    )
    assert first["archive_sha256"] == second["archive_sha256"]
    assert first["file_manifest_sha256"] == second["file_manifest_sha256"]
    assert first["git_sha"] == head
    assert first["worktree_clean"] is True
    assert first["mode"] == "publication"
    with gzip.open(first["archive"], "rb") as stream, tarfile.open(
        fileobj=stream, mode="r:"
    ) as archive:
        assert sorted(archive.getnames()) == ["research.py", "uv.lock"]


@pytest.mark.parametrize("dirty_kind", ["modified", "staged", "untracked"])
def test_publication_archive_rejects_every_dirty_state(
    tmp_path: Path, dirty_kind: str
) -> None:
    root = _repo(tmp_path)
    if dirty_kind == "untracked":
        (root / "untracked.txt").write_text("no\n", encoding="utf-8")
    else:
        (root / "research.py").write_text("print('drift')\n", encoding="utf-8")
        if dirty_kind == "staged":
            _run(root, "git", "add", "research.py")
    with pytest.raises(ValueError, match="completely clean"):
        create_archive(
            root,
            tmp_path / f"{dirty_kind}.tar.gz",
            mode="publication",
        )


def test_publication_ref_must_be_checked_out_head(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    old = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    (root / "research.py").write_text("print('next')\n", encoding="utf-8")
    _run(root, "git", "add", "research.py")
    _run(root, "git", "commit", "-qm", "next")
    with pytest.raises(ValueError, match="checked-out HEAD"):
        create_archive(
            root,
            tmp_path / "stale.tar.gz",
            mode="publication",
            ref=old,
        )


def test_discovery_archive_remains_explicit_and_includes_untracked(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "draft.py").write_text("draft = True\n", encoding="utf-8")
    receipt = create_archive(
        root,
        tmp_path / "discovery.tar.gz",
        mode="discovery",
    )
    assert receipt["mode"] == "discovery"
    assert receipt["worktree_clean"] is False
    with gzip.open(receipt["archive"], "rb") as stream, tarfile.open(
        fileobj=stream, mode="r:"
    ) as archive:
        assert "draft.py" in archive.getnames()


def test_source_receipt_is_durable_and_never_overwritten(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    receipt = create_archive(
        root,
        tmp_path / "discovery.tar.gz",
        mode="discovery",
    )
    receipt_path = tmp_path / "receipt.json"
    write_receipt(receipt_path, receipt)
    before = receipt_path.read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        write_receipt(receipt_path, receipt)
    assert receipt_path.read_bytes() == before


@pytest.mark.parametrize("attribute", ["export-ignore", "export-subst"])
def test_publication_rejects_git_archive_transformations(
    tmp_path: Path, attribute: str
) -> None:
    root = _repo(tmp_path)
    target = "research.py"
    if attribute == "export-subst":
        (root / target).write_text("$Format:%H$\n", encoding="utf-8")
    (root / ".gitattributes").write_text(
        f"{target} {attribute}\n", encoding="utf-8"
    )
    _run(root, "git", "add", ".")
    _run(root, "git", "commit", "-qm", attribute)
    with pytest.raises(ValueError, match="differ from the committed file tree"):
        create_archive(
            root,
            tmp_path / f"{attribute}.tar.gz",
            mode="publication",
        )
