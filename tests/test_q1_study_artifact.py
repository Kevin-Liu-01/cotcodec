"""Study artifact: pack, verify, unpack and tamper detection (pure Python)."""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

import pytest

from harness.q1 import study_artifact as sa


def _git_repo(root: Path) -> str:
    root.mkdir()
    (root / "pkg").mkdir()
    (root / "pkg" / "mod.py").write_text("X = 1\n")
    (root / "run.sh").write_text("#!/bin/sh\necho hi\n")
    (root / "run.sh").chmod(0o755)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
    }
    for argv in (["init", "-q"], ["add", "."], ["commit", "-qm", "init"]):
        subprocess.run(["git", "-C", str(root), *argv], check=True, env=env)
    (root / "pkg" / "mod.py").write_text("X = 2  # local edit, not committed\n")
    (root / "untracked.txt").write_text("not in the tree\n")
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _pack(tmp_path: Path) -> tuple[Path, dict]:
    head = _git_repo(tmp_path / "clone")
    corpus = tmp_path / "corpus"
    (corpus / "sub" / "__pycache__").mkdir(parents=True)
    (corpus / "sub" / "kernel.py").write_text("print('k')\n")
    (corpus / "sub" / "__pycache__" / "x.pyc").write_bytes(b"\0")
    document = sa.build(
        {
            "clone": sa.git_tree(tmp_path / "clone", head, source="example/clone", licence="none"),
            "corpus": sa.dir_tree(corpus, source="q1-pilot-corpus", licence="mixed"),
        },
        repo_revision="0" * 40,
    )
    out = tmp_path / "artifact.json"
    receipt = sa.write(document, out)
    return out, receipt


def test_pack_reads_the_commit_not_the_working_tree(tmp_path: Path) -> None:
    out, receipt = _pack(tmp_path)
    document = sa.load(out, receipt["sha256"])
    clone = document["trees"]["clone"]
    paths = {f["path"]: f for f in clone["files"]}
    assert set(paths) == {"pkg/mod.py", "run.sh"}
    assert base64.b64decode(paths["pkg/mod.py"]["b64"]) == b"X = 1\n"
    assert paths["run.sh"]["mode"] == 0o755
    corpus_paths = [f["path"] for f in document["trees"]["corpus"]["files"]]
    assert corpus_paths == ["sub/kernel.py"]


def test_unpack_writes_read_only_trees_with_revision_marker(tmp_path: Path) -> None:
    out, receipt = _pack(tmp_path)
    document = sa.load(out, receipt["sha256"])
    result = sa.unpack(document, tmp_path / "inputs")
    clone = tmp_path / "inputs" / "clone"
    assert (clone / "pkg" / "mod.py").read_text() == "X = 1\n"
    assert (clone / "REVISION").read_text().strip() == document["trees"]["clone"]["revision"]
    assert result["trees"]["clone"]["added"] == ["REVISION"]
    assert not (clone / "pkg" / "mod.py").stat().st_mode & 0o222
    with pytest.raises(sa.ArtifactError):
        sa.unpack(document, tmp_path / "inputs")


def test_tampering_is_refused(tmp_path: Path) -> None:
    out, receipt = _pack(tmp_path)
    with pytest.raises(sa.ArtifactError, match="SHA-256"):
        sa.load(out, "f" * 64)
    document = json.loads(out.read_bytes())
    document["trees"]["corpus"]["files"][0]["b64"] = base64.b64encode(b"evil\n").decode()
    tampered = tmp_path / "tampered.json"
    tampered.write_bytes(json.dumps(document).encode())
    with pytest.raises(sa.ArtifactError, match="content hash"):
        sa.load(tampered, sa.sha256_bytes(tampered.read_bytes()))
    document = json.loads(out.read_bytes())
    document["trees"]["corpus"]["licence"] = "MIT"
    tampered.write_bytes(json.dumps(document).encode())
    with pytest.raises(sa.ArtifactError, match="manifest"):
        sa.load(tampered, sa.sha256_bytes(tampered.read_bytes()))


def test_unsafe_paths_are_refused() -> None:
    for bad in ("../x", "/etc/passwd", "a/../b", ""):
        with pytest.raises(sa.ArtifactError):
            sa._safe_relpath(bad)
