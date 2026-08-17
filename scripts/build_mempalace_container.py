#!/usr/bin/env python3
"""Validate immutable MemPalace build inputs before Docker resolves any base."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.prepare_chroma_minilm import verify_prepared_artifact  # noqa: E402
from scripts.prepare_mempalace_source_context import verify_context  # noqa: E402

IMMUTABLE_IMAGE_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}"
)
ORIGINAL_DOCKERIGNORE = ".cotcodec-original-dockerignore"
TRANSPORT_DOCKERIGNORE = (
    "# CoTCodec verified full-tree transport; restore the original before verification.\n"
)


def validate_base_image_reference(reference: str) -> str:
    if IMMUTABLE_IMAGE_RE.fullmatch(reference) is None:
        raise ValueError(
            "CoTCodec base image must be an immutable name@sha256:<64-hex> reference"
        )
    return reference


def prepare_source_transport(source_context: Path, transport_context: Path) -> Path:
    """Copy a verified source tree without letting its ignore rules erase files.

    BuildKit applies a named local context's own root ``.dockerignore`` before
    the Dockerfile can inspect it. MemPalace intentionally excludes its
    benchmark directory from normal product images, but that directory holds
    the reviewed reproduction runner. The host preflight verifies the exact
    555-file Git tree first; this transport copy then temporarily replaces the
    ignore file and preserves the original under a fixed marker. The Dockerfile
    restores the original before repeating full-tree verification.
    """

    source_context = source_context.resolve(strict=True)
    transport_context = transport_context.resolve()
    if transport_context.exists():
        raise ValueError(f"refusing to overwrite source transport: {transport_context}")
    shutil.copytree(source_context, transport_context, symlinks=True)
    dockerignore = transport_context / ".dockerignore"
    preserved = transport_context / ORIGINAL_DOCKERIGNORE
    if not dockerignore.is_file() or dockerignore.is_symlink() or preserved.exists():
        shutil.rmtree(transport_context, ignore_errors=True)
        raise ValueError("MemPalace source context has an unsafe Docker ignore contract")
    dockerignore.replace(preserved)
    with dockerignore.open("x", encoding="utf-8") as handle:
        handle.write(TRANSPORT_DOCKERIGNORE)
    return transport_context


def build_command(
    *,
    base_image: str,
    source_context: Path,
    minilm_context: Path,
    minilm_artifact_root_sha256: str,
    tag: str,
    project_root: Path = PROJECT_ROOT,
) -> list[str]:
    validate_base_image_reference(base_image)
    if re.fullmatch(r"[0-9a-f]{64}", minilm_artifact_root_sha256) is None:
        raise ValueError("MiniLM artifact root must be one lowercase SHA-256 digest")
    if not tag or tag.startswith("-") or any(character.isspace() for character in tag):
        raise ValueError("output tag is invalid")
    return [
        "docker",
        "buildx",
        "build",
        "--load",
        "--network=host",
        "--build-arg",
        f"COTCODEC_IMAGE={base_image}",
        "--build-arg",
        f"MINILM_ARTIFACT_ROOT_SHA256={minilm_artifact_root_sha256}",
        "--build-context",
        f"mempalace_source={source_context.resolve()}",
        "--build-context",
        f"minilm_model={minilm_context.resolve()}",
        "-f",
        str(project_root / "infra/memory-baselines/mempalace/Dockerfile"),
        "-t",
        tag,
        str(project_root),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cotcodec-image", required=True)
    parser.add_argument("--source-context", type=Path, required=True)
    parser.add_argument("--minilm-context", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        base_image = validate_base_image_reference(args.cotcodec_image)
        if args.source_context.is_symlink() or not args.source_context.is_dir():
            raise ValueError("MemPalace source context must be a regular directory")
        if args.minilm_context.is_symlink() or not args.minilm_context.is_dir():
            raise ValueError("MiniLM context must be a regular directory")
        source_receipt = verify_context(args.source_context)
        model_receipt = verify_prepared_artifact(args.minilm_context)
    except ValueError as exc:
        parser.error(str(exc))
    with tempfile.TemporaryDirectory(prefix="cotcodec-mempalace-transport-") as temporary:
        try:
            transport = prepare_source_transport(
                args.source_context, Path(temporary) / "source"
            )
            command = build_command(
                base_image=base_image,
                source_context=transport,
                minilm_context=args.minilm_context,
                minilm_artifact_root_sha256=model_receipt["artifact_root_sha256"],
                tag=args.tag,
            )
        except ValueError as exc:
            parser.error(str(exc))
        preflight = {
            "schema_version": 1,
            "status": "MEMPALACE_CONTAINER_BUILD_PREFLIGHT_PASS",
            "cotcodec_base_image_reference": base_image,
            "source_receipt_sha256": source_receipt["receipt_sha256"],
            "source_transport": "verified-full-tree-empty-ignore-v1",
            "minilm_receipt_sha256": model_receipt["receipt_sha256"],
            "command": command,
            "executed": args.execute,
        }
        print(json.dumps(preflight, sort_keys=True))
        if args.execute:
            subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
