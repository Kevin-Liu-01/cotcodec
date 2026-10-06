from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_mempalace_container import (
    ORIGINAL_DOCKERIGNORE,
    build_command,
    prepare_source_transport,
    validate_base_image_reference,
)


def test_mempalace_build_preflight_rejects_mutable_or_malformed_base() -> None:
    for reference in (
        "cotcodec:latest",
        "sha256:" + "a" * 64,
        "registry.invalid/cotcodec@sha256:" + "A" * 64,
        "registry.invalid/cotcodec@sha256:" + "a" * 63,
    ):
        with pytest.raises(ValueError, match="immutable"):
            validate_base_image_reference(reference)


def test_mempalace_build_command_binds_only_validated_inputs(tmp_path: Path) -> None:
    base = "registry.invalid/cotcodec@sha256:" + "a" * 64
    source = tmp_path / "source"
    model = tmp_path / "model"
    source.mkdir()
    model.mkdir()
    command = build_command(
        base_image=base,
        source_context=source,
        minilm_context=model,
        minilm_artifact_root_sha256="b" * 64,
        tag="cotcodec-mempalace:test",
        project_root=tmp_path,
    )

    assert command[:5] == [
        "docker",
        "buildx",
        "build",
        "--load",
        "--network=host",
    ]
    assert f"COTCODEC_IMAGE={base}" in command
    assert f"mempalace_source={source}" in command
    assert f"minilm_model={model}" in command
    assert command[-1] == str(tmp_path)


def test_source_transport_preserves_original_ignore_and_includes_full_tree(
    tmp_path: Path,
) -> None:
    source = tmp_path / "verified-source"
    source.mkdir()
    (source / ".dockerignore").write_text("benchmarks/\n", encoding="utf-8")
    (source / "benchmarks").mkdir()
    (source / "benchmarks/runner.py").write_text("pass\n", encoding="utf-8")
    transport = prepare_source_transport(source, tmp_path / "transport")

    assert (transport / "benchmarks/runner.py").read_text(encoding="utf-8") == "pass\n"
    assert (transport / ORIGINAL_DOCKERIGNORE).read_text(encoding="utf-8") == (
        "benchmarks/\n"
    )
    assert "benchmarks/" not in (transport / ".dockerignore").read_text(
        encoding="utf-8"
    )


def test_source_transport_rejects_missing_or_unsafe_ignore(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ValueError, match="ignore contract"):
        prepare_source_transport(source, tmp_path / "transport")
