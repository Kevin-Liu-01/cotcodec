from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

import scripts.extract_discovery_source_archive as extraction_module
import scripts.verify_compute_provenance as provenance_module
from scripts.create_source_archive import (
    OMITTABLE_SYMLINK_PREFIXES,
    create_archive,
    write_receipt,
)
from scripts.extract_discovery_source_archive import validate_and_extract

REPOSITORY = Path(__file__).resolve().parents[1]


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


def _agent_tooling_repo(tmp_path: Path) -> Path:
    """A repository shaped like main: `.agents/skills/*` links into `.claude/skills/`."""

    root = _repo(tmp_path)
    skill = root / ".claude/skills/demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# demo\n", encoding="utf-8")
    (skill / "references").mkdir()
    (skill / "references/notes.md").write_text("notes\n", encoding="utf-8")
    links = root / ".agents/skills"
    links.mkdir(parents=True)
    (links / "demo").symlink_to("../../.claude/skills/demo")
    (links / "research.py").symlink_to("../../research.py")
    _run(root, "git", "add", ".")
    _run(root, "git", "commit", "-qm", "agent tooling links")
    return root


def _commit_link(root: Path, link: str, target: str | Path) -> None:
    path = root / link
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)
    _run(root, "git", "add", link)
    _run(root, "git", "commit", "-qm", f"link {link}")


def _members(receipt: dict[str, object]) -> list[str]:
    with gzip.open(str(receipt["archive"]), "rb") as stream, tarfile.open(
        fileobj=stream, mode="r:"
    ) as archive:
        return archive.getnames()


def test_discovery_omits_tracked_agent_links_into_the_repository_and_records_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _agent_tooling_repo(tmp_path)
    receipt = create_archive(root, tmp_path / "linked.tar.gz", mode="discovery")
    expected_rows = [
        {"path": ".agents/skills/demo", "target": "../../.claude/skills/demo"},
        {"path": ".agents/skills/research.py", "target": "../../research.py"},
    ]
    assert receipt["schema_version"] == 3
    assert receipt["worktree_clean"] is True
    assert receipt["omittable_symlink_prefixes"] == [".agents/"]
    assert receipt["omitted_symlinks"] == expected_rows
    assert receipt["omitted_symlinks_sha256"] == hashlib.sha256(
        json.dumps(expected_rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    names = _members(receipt)
    assert names == receipt["file_manifest"] == [
        ".claude/skills/demo/SKILL.md",
        ".claude/skills/demo/references/notes.md",
        "research.py",
        "uv.lock",
    ]

    # Omission is identity-neutral: the archive equals one built after removing the links.
    again = create_archive(root, tmp_path / "again.tar.gz", mode="discovery")
    assert again["archive_sha256"] == receipt["archive_sha256"]
    _run(root, "git", "rm", "-rq", ".agents")
    removed = create_archive(root, tmp_path / "removed.tar.gz", mode="discovery")
    assert removed["archive_sha256"] == receipt["archive_sha256"]
    assert removed["file_manifest_sha256"] == receipt["file_manifest_sha256"]
    assert removed["omitted_symlinks"] == []
    assert removed["worktree_clean"] is False

    # The extractor accepts the receipt and yields regular files only.
    receipt_path = tmp_path / "linked.json"
    write_receipt(receipt_path, receipt)
    output = tmp_path / "context"
    output.mkdir()
    members = validate_and_extract(
        archive_path=Path(str(receipt["archive"])),
        receipt_path=receipt_path,
        output_dir=output,
        expected_archive_sha256=str(receipt["archive_sha256"]),
        expected_git_sha=str(receipt["git_sha"]),
        expected_git_tree=str(receipt["git_tree"]),
    )
    assert list(members) == receipt["file_manifest"]
    assert not any(path.is_symlink() for path in output.rglob("*"))
    assert not (output / ".agents").exists()

    # The identity pair the lane binds still verifies inside an image.
    embedded = tmp_path / "cotcodec-provenance.json"
    subprocess.run(
        [sys.executable, str(REPOSITORY / "infra/research/write_provenance.py"), str(embedded)],
        check=True,
        env={
            **os.environ,
            "GIT_SHA_VALUE": str(receipt["git_sha"]),
            "SOURCE_SHA_VALUE": str(receipt["archive_sha256"]),
        },
    )
    monkeypatch.setattr(provenance_module, "PROVENANCE_PATH", embedded)
    monkeypatch.setenv("COTCODEC_GIT_SHA", str(receipt["git_sha"]))
    monkeypatch.setenv("COTCODEC_SOURCE_SHA256", str(receipt["archive_sha256"]))
    provenance_module.main()
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


@pytest.mark.parametrize("kind", ["relative", "absolute"])
def test_discovery_refuses_agent_link_pointing_outside_the_repository(
    tmp_path: Path, kind: str
) -> None:
    root = _repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("no\n", encoding="utf-8")
    target = "../../../outside" if kind == "relative" else outside
    _commit_link(root, ".agents/skills/outside", target)
    match = "escapes the repository" if kind == "relative" else "must be relative"
    with pytest.raises(ValueError, match=match):
        create_archive(root, tmp_path / "outside.tar.gz", mode="discovery")
    assert not (tmp_path / "outside.tar.gz").exists()


def test_discovery_refuses_dangling_agent_link(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _commit_link(root, ".agents/skills/gone", "../../.claude/skills/gone")
    with pytest.raises(ValueError, match="dangling"):
        create_archive(root, tmp_path / "dangling.tar.gz", mode="discovery")


def test_discovery_refuses_links_outside_the_reviewed_prefixes(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _commit_link(root, "scripts/alias.py", "../research.py")
    with pytest.raises(ValueError, match="reviewed agent-tooling prefixes"):
        create_archive(root, tmp_path / "alias.tar.gz", mode="discovery")


def test_discovery_refuses_untracked_agent_link(tmp_path: Path) -> None:
    root = _agent_tooling_repo(tmp_path)
    (root / ".agents/skills/draft").symlink_to("../../.claude/skills/demo")
    with pytest.raises(ValueError, match="not tracked as links"):
        create_archive(root, tmp_path / "untracked.tar.gz", mode="discovery")


@pytest.mark.parametrize(
    ("target", "match"),
    [
        ("../..", "names its root"),
        ("..", "contains the link itself"),
        ("demo", "passes through another symlink"),
        ("../../data/raw.txt", "not a tracked regular file"),
        ("../../draft.py", "not a tracked regular file"),
        ("../../research.py/inner", "dangling"),
    ],
)
def test_discovery_refuses_agent_links_that_do_not_name_archived_content(
    tmp_path: Path, target: str, match: str
) -> None:
    root = _agent_tooling_repo(tmp_path)
    (root / "data").mkdir()
    (root / "data/raw.txt").write_text("raw\n", encoding="utf-8")
    _run(root, "git", "add", "-f", "data/raw.txt")
    _run(root, "git", "commit", "-qm", "data")
    (root / "draft.py").write_text("draft = True\n", encoding="utf-8")
    _commit_link(root, ".agents/skills/bad", target)
    with pytest.raises(ValueError, match=match):
        create_archive(root, tmp_path / "bad.tar.gz", mode="discovery")


def test_publication_still_refuses_every_tracked_symlink(tmp_path: Path) -> None:
    root = _agent_tooling_repo(tmp_path)
    with pytest.raises(ValueError, match="only regular committed files"):
        create_archive(root, tmp_path / "publication.tar.gz", mode="publication")


def test_extractor_holds_the_same_omission_rule() -> None:
    assert extraction_module.OMITTABLE_SYMLINK_PREFIXES == OMITTABLE_SYMLINK_PREFIXES
