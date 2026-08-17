from __future__ import annotations

from pathlib import Path

import pytest

from scripts.prepare_memory_baseline_context import SourceContextError, _safe_member


@pytest.mark.parametrize(
    "name",
    ["../escape", "/absolute", "safe/../../escape"],
)
def test_source_context_rejects_archive_traversal(name: str) -> None:
    import tarfile

    with pytest.raises(SourceContextError, match="unsafe path"):
        _safe_member(tarfile.TarInfo(name))


def test_source_context_refuses_escaping_symlink() -> None:
    import tarfile

    member = tarfile.TarInfo("nested/link")
    member.type = tarfile.SYMTYPE
    member.linkname = "../../outside"
    with pytest.raises(SourceContextError, match="unsafe link"):
        _safe_member(member)


def test_source_context_rejects_existing_output(tmp_path: Path) -> None:
    from scripts.prepare_memory_baseline_context import prepare_context

    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(SourceContextError, match="already exists"):
        prepare_context("mem0", output)


def test_hindsight_context_excludes_only_registered_absolute_symlink(
    tmp_path: Path,
) -> None:
    from scripts.prepare_memory_baseline_context import prepare_context

    output = tmp_path / "hindsight-context"
    receipt = prepare_context("hindsight", output)
    excluded = "hindsight-integrations/coding-agents/node_modules"
    assert receipt["excluded_unsafe_archive_paths"] == [excluded]
    assert not (output / excluded).exists()
    assert (output / "hindsight-all" / "pyproject.toml").is_file()
