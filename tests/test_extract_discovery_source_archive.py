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

OMITTED = [
    {"path": ".agents/skills/demo", "target": "../../.claude/skills/demo"},
    {"path": ".agents/skills/run.py", "target": "../../scripts/run.py"},
]


def _omitted_digest(rows: object) -> str:
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _fixture(
    tmp_path: Path,
    *,
    script: bytes = b"print('ok')\n",
    omitted: list[dict[str, str]] | None = None,
    extra: dict[str, bytes] | None = None,
) -> tuple[Path, Path, str, str, str]:
    """Schema 2 receipt by default; schema 3 with `omitted` links recorded."""

    tmp_path.mkdir(parents=True, exist_ok=True)
    archive_path = tmp_path / "source.tar.gz"
    files = {"scripts/run.py": script, "uv.lock": b"version = 1\n"}
    if omitted is not None:
        files = {".claude/skills/demo/SKILL.md": b"# demo\n", **files}
    files = dict(sorted({**files, **(extra or {})}.items(), key=lambda item: item[0].encode()))
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
    if omitted is not None:
        receipt["schema_version"] = 3
        receipt["omittable_symlink_prefixes"] = [".agents/"]
        receipt["omitted_symlinks"] = omitted
        receipt["omitted_symlinks_sha256"] = _omitted_digest(omitted)
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


def _extract(
    tmp_path: Path, archive: Path, receipt: Path, digest: str, git_sha: str, git_tree: str
) -> tuple[str, ...]:
    output = tmp_path / "context"
    output.mkdir()
    return validate_and_extract(
        archive_path=archive,
        receipt_path=receipt,
        output_dir=output,
        expected_archive_sha256=digest,
        expected_git_sha=git_sha,
        expected_git_tree=git_tree,
    )


def test_schema_3_receipt_with_omitted_links_extracts_regular_files_only(
    tmp_path: Path,
) -> None:
    archive, receipt, digest, git_sha, git_tree = _fixture(tmp_path, omitted=OMITTED)
    members = _extract(tmp_path, archive, receipt, digest, git_sha, git_tree)
    assert members == (".claude/skills/demo/SKILL.md", "scripts/run.py", "uv.lock")
    output = tmp_path / "context"
    assert not any(path.is_symlink() for path in output.rglob("*"))
    assert not (output / ".agents").exists()


def test_schema_3_receipt_with_no_omitted_links_extracts(tmp_path: Path) -> None:
    archive, receipt, digest, git_sha, git_tree = _fixture(tmp_path, omitted=[])
    assert _extract(tmp_path, archive, receipt, digest, git_sha, git_tree)


def _rows(**change: str) -> list[dict[str, str]]:
    return [{**OMITTED[0], **change}]


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda r: r.update(omitted_symlinks=_rows(target="../../../outside")), "not archived"),
        (lambda r: r.update(omitted_symlinks=_rows(target="/etc")), "must be relative"),
        (lambda r: r.update(omitted_symlinks=_rows(target="../../.claude/x")), "not archived"),
        (lambda r: r.update(omitted_symlinks=_rows(target="..")), "not archived"),
        (lambda r: r.update(omitted_symlinks=_rows(target="../..")), "not archived"),
        (lambda r: r.update(omitted_symlinks=_rows(path="scripts/demo")), "outside the rule"),
        (lambda r: r.update(omitted_symlinks=_rows(path=".agents//demo")), "outside the rule"),
        (
            lambda r: r.update(
                omitted_symlinks=[{"path": ".claude/skills/demo/SKILL.md/x", "target": "y"}]
            ),
            "outside the rule",
        ),
        (lambda r: r.update(omitted_symlinks=OMITTED[::-1]), "malformed"),
        (lambda r: r.update(omitted_symlinks=[OMITTED[0], OMITTED[0]]), "malformed"),
        (lambda r: r.update(omitted_symlinks=[{**OMITTED[0], "kind": "dir"}]), "malformed"),
        (lambda r: r.update(omittable_symlink_prefixes=[".agents/", "scripts/"]), "rule"),
        (lambda r: r.pop("omittable_symlink_prefixes"), "rule"),
        (lambda r: r.pop("omitted_symlinks"), "malformed"),
        (lambda r: r.update(schema_version=2), "cannot record omitted symlinks"),
        (lambda r: r.update(schema_version=True), "registered discovery archive"),
        (lambda r: r.update(schema_version=3.0), "registered discovery archive"),
        (lambda r: r.update(schema_version=4), "registered discovery archive"),
    ],
)
def test_schema_3_receipt_rejects_tampered_omission_records(
    tmp_path: Path, mutate, match: str
) -> None:
    archive, receipt, digest, git_sha, git_tree = _fixture(tmp_path, omitted=OMITTED)
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    mutate(payload)
    if isinstance(payload.get("omitted_symlinks"), list):
        payload["omitted_symlinks_sha256"] = _omitted_digest(payload["omitted_symlinks"])
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        _extract(tmp_path, archive, receipt, digest, git_sha, git_tree)
    assert not any((tmp_path / "context").iterdir())


def test_schema_3_receipt_rejects_omitted_link_digest_drift(tmp_path: Path) -> None:
    archive, receipt, digest, git_sha, git_tree = _fixture(tmp_path, omitted=OMITTED)
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["omitted_symlinks"] = _rows(target="../../scripts/run.py")
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="digest drifted"):
        _extract(tmp_path, archive, receipt, digest, git_sha, git_tree)


@pytest.mark.parametrize("link", [".agents/README.md", ".agents/README.md/x", ".agents/docs"])
def test_omitted_link_cannot_shadow_an_archived_path(tmp_path: Path, link: str) -> None:
    rows = [{"path": link, "target": "../scripts/run.py"}]
    archive, receipt, digest, git_sha, git_tree = _fixture(
        tmp_path,
        omitted=rows,
        extra={".agents/README.md": b"readme\n", ".agents/docs/a.md": b"a\n"},
    )
    with pytest.raises(ValueError, match="collides with an archived file"):
        _extract(tmp_path, archive, receipt, digest, git_sha, git_tree)
