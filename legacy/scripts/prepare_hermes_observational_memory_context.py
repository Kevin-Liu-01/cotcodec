#!/usr/bin/env python3
"""Safely materialize the exact Hermes Observational Memory Docker context."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path, PurePosixPath

EXPECTED = {
    "hermes_archive": "2a2934d3c8379816b2e3919f4cf1191f04e93f136da6f2128246d368644a9514",
    "plugin_archive": "33d6bc75ff850fdf9140d225bc6636c3cc22f0c015f897c546ce226b7cc551c4",
    "core_archive": "0d103be2c781b0ac546a5fa16cb81c1f877513675b83ca33b06cd7fa4d8312f0",
    "observational_memory_wheel": (
        "d743b32823af544468fc666621850931ae77c0225d8c162db43b878cbdb5f4e4"
    ),
    "rank_bm25_wheel": "7bd4a95571adadfc271746fa146a4bcfd89c0cf731e49c3d1ad863290adbe8ae",
    "numpy_wheel": "e7dd01a46700b1967487141a66ac1a3cf0dd8ebf1f08db37d46389401512ca97",
    "pyyaml_wheel": "ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc",
}
MAX_MEMBERS = 20_000
MAX_BYTES = 512 * 1024 * 1024


class ContextError(RuntimeError):
    """Invalid or drifting build input."""


def _sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ContextError(f"input must be a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_members(archive: Path) -> list[tarfile.TarInfo]:
    members: list[tarfile.TarInfo] = []
    names: set[str] = set()
    total = 0
    with tarfile.open(archive, "r:*") as tar:
        for member in tar.getmembers():
            if len(members) >= MAX_MEMBERS:
                raise ContextError("source archive member ceiling exceeded")
            pure = PurePosixPath(member.name)
            if (
                not member.name
                or pure.is_absolute()
                or ".." in pure.parts
                or member.name in names
            ):
                raise ContextError(f"unsafe archive member: {member.name!r}")
            if not (member.isdir() or member.isreg()):
                raise ContextError(f"archive links/special files forbidden: {member.name}")
            if member.size < 0:
                raise ContextError("negative archive member size")
            total += member.size
            if total > MAX_BYTES:
                raise ContextError("source archive byte ceiling exceeded")
            names.add(member.name)
            members.append(member)
    return members


def _extract(archive: Path, destination: Path) -> None:
    members = _validated_members(archive)
    destination.mkdir(mode=0o700)
    with tarfile.open(archive, "r:*") as tar:
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            if source is None:
                raise ContextError(f"regular member had no payload: {member.name}")
            with target.open("xb") as output:
                shutil.copyfileobj(source, output)
                output.flush()
                os.fsync(output.fileno())
            target.chmod(0o755 if member.mode & 0o111 else 0o644)


def _copy(source: Path, destination: Path) -> str:
    digest = _sha256(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer)
        writer.flush()
        os.fsync(writer.fileno())
    destination.chmod(0o644)
    return digest


def prepare(args: argparse.Namespace) -> dict:
    inputs = {
        "hermes_archive": args.hermes_archive,
        "plugin_archive": args.plugin_archive,
        "core_archive": args.core_archive,
        "observational_memory_wheel": args.observational_memory_wheel,
        "rank_bm25_wheel": args.rank_bm25_wheel,
        "numpy_wheel": args.numpy_wheel,
        "pyyaml_wheel": args.pyyaml_wheel,
    }
    for name, path in inputs.items():
        observed = _sha256(path)
        if observed != EXPECTED[name]:
            raise ContextError(f"{name} digest drifted: {observed}")
    for helper in (args.dockerfile, args.doctor):
        _sha256(helper)
    if args.output_dir.exists():
        raise ContextError("context output already exists")
    args.output_dir.mkdir(parents=True, mode=0o700)
    _extract(args.hermes_archive, args.output_dir / "hermes")
    _extract(args.plugin_archive, args.output_dir / "plugin")
    _copy(args.dockerfile, args.output_dir / "Dockerfile")
    _copy(args.doctor, args.output_dir / "doctor.py")
    _copy(
        args.observational_memory_wheel,
        args.output_dir / "wheels" / "observational_memory-0.10.0-py3-none-any.whl",
    )
    _copy(
        args.rank_bm25_wheel,
        args.output_dir / "wheels" / "rank_bm25-0.2.2-py3-none-any.whl",
    )
    _copy(
        args.numpy_wheel,
        args.output_dir
        / "wheels"
        / "numpy-2.4.3-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
    )
    _copy(
        args.pyyaml_wheel,
        args.output_dir
        / "wheels"
        / (
            "pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64."
            "manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"
        ),
    )
    receipt = {
        "schema_version": 1,
        "inputs": {name: EXPECTED[name] for name in sorted(EXPECTED)},
        "dockerfile_sha256": _sha256(args.dockerfile),
        "doctor_sha256": _sha256(args.doctor),
    }
    (args.output_dir / "context-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-archive", type=Path, required=True)
    parser.add_argument("--plugin-archive", type=Path, required=True)
    parser.add_argument("--core-archive", type=Path, required=True)
    parser.add_argument("--observational-memory-wheel", type=Path, required=True)
    parser.add_argument("--rank-bm25-wheel", type=Path, required=True)
    parser.add_argument("--numpy-wheel", type=Path, required=True)
    parser.add_argument("--pyyaml-wheel", type=Path, required=True)
    parser.add_argument("--dockerfile", type=Path, required=True)
    parser.add_argument("--doctor", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
