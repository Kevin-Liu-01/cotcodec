#!/usr/bin/env python3
"""Validate and submit a CPU-only VM campaign (decision D12) to Slurm.

This is the submitter-side validator for ``vm-campaign.sbatch`` manifests. It
is separate from the shared GPU submitter on purpose: that one requires at
least one GPU, and a VM campaign must request none.

Run it on the H100 host from the exported source directory named in the
manifest, so the batch script digest and the source tree digest it checks are
the ones the job will execute:

    python3 scripts/submit_vm_campaign.py MANIFEST.yaml --dry-run
    python3 scripts/submit_vm_campaign.py MANIFEST.yaml --test-only
    python3 scripts/submit_vm_campaign.py MANIFEST.yaml

``--offline`` validates the manifest's shape only (no host files, no Docker);
use it on a laptop or in CI. Python 3.10 compatible; needs PyYAML.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q2.vm.manifest import (  # noqa: E402
    ManifestError,
    canonical_json,
    manifest_sha256,
    source_tree_sha256,
    validate_manifest,
)

BATCH_SCRIPT = PROJECT_ROOT / "infra/slurm/host-single-node/vm-campaign.sbatch"
RUNTIME = "vm-campaign-cpu-only-v1"
FORBIDDEN_SBATCH_PREFIXES = ("--gres", "--gpus", "--gpu", "-G")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_host(manifest: dict[str, Any]) -> dict[str, Any]:
    """Host-side checks: files exist and match, images are present locally."""
    source = manifest["source"]
    source_dir = Path(source["host_dir"])
    if not source_dir.is_dir() or source_dir.is_symlink():
        raise ManifestError("source.host_dir does not exist on this host")
    if source_dir.resolve() != PROJECT_ROOT.resolve():
        raise ManifestError("run the submitter from the exported source directory it names")
    actual_tree = source_tree_sha256(str(source_dir))
    if actual_tree != source["tree_sha256"]:
        raise ManifestError(f"source tree digest mismatch: {actual_tree}")
    prereg = source_dir / manifest["preregistration"]["path"]
    if manifest["preregistration"]["status"] != "absent" and (
        not prereg.is_file() or sha256_file(prereg) != manifest["preregistration"]["sha256"]
    ):
        raise ManifestError("preregistration file is missing or its digest drifted")
    qcow2 = manifest["vm"]["qcow2"]
    path = Path(qcow2["host_path"])
    if not path.is_file() or path.is_symlink():
        raise ManifestError("vm.qcow2.host_path is not a regular file")
    if path.stat().st_size != qcow2["size_bytes"]:
        raise ManifestError("vm.qcow2 size does not match")
    if os.access(path, os.W_OK):
        raise ManifestError("vm.qcow2 must be read-only (chmod a-w) so no job can modify it")
    run_root = Path(manifest["run_root"])
    run_root.mkdir(parents=True, exist_ok=True)
    found = {}
    for key, image in (
        ("vm", manifest["vm"]["image_id"]),
        ("runner", manifest["runner"]["image_id"]),
    ):
        completed = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0 or completed.stdout.strip() != image:
            raise ManifestError(f"{key} image {image} is not present locally")
        found[key] = image
    return {"source_tree_sha256": actual_tree, "images": found}


def sbatch_argv(manifest: dict[str, Any], *, test_only: bool) -> list[str]:
    hours, minutes = divmod(manifest["slurm"]["minutes"], 60)
    exported = {
        "COTCODEC_VM_MANIFEST_JSON_HEX": canonical_json(manifest).encode("utf-8").hex(),
        "COTCODEC_VM_MANIFEST_SHA256": manifest_sha256(manifest),
        "COTCODEC_BATCH_SHA256": sha256_file(BATCH_SCRIPT),
        "COTCODEC_SOURCE_HOST_HEX": manifest["source"]["host_dir"].encode().hex(),
        "COTCODEC_SOURCE_TREE_SHA256": manifest["source"]["tree_sha256"],
        "COTCODEC_RUN_ROOT_HEX": manifest["run_root"].encode().hex(),
    }
    argv = [
        "sbatch",
        "--parsable",
        "--partition=research",
        "--nodes=1",
        "--ntasks=1",
        f"--job-name={manifest['name']}",
        f"--cpus-per-task={manifest['slurm']['cpus']}",
        f"--mem={manifest['slurm']['memory_gb']}G",
        f"--time={hours:02d}:{minutes:02d}:00",
        "--signal=B:USR1@120",
        f"--output={manifest['run_root']}/slurm-%j.out",
        "--export=" + ",".join(f"{key}={value}" for key, value in exported.items()),
    ]
    if test_only:
        argv.append("--test-only")
    argv.append(str(BATCH_SCRIPT))
    for arg in argv:
        if arg.startswith(FORBIDDEN_SBATCH_PREFIXES):
            raise ManifestError(f"refusing to render a GPU request: {arg}")
    return argv


def load_manifest(path: Path) -> dict[str, Any]:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ManifestError("manifest must be a YAML mapping")
    return validate_manifest(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--offline", action="store_true", help="validate shape only")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        if args.offline:
            print(json.dumps({"status": "VALID", "manifest_sha256": manifest_sha256(manifest)}))
            return 0
        host = check_host(manifest)
        argv_out = sbatch_argv(manifest, test_only=args.test_only)
    except ManifestError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        shown = [a if not a.startswith("--export=") else "--export=<6 variables>" for a in argv_out]
        print(
            json.dumps(
                {
                    "argv": shown,
                    "runtime": RUNTIME,
                    "host": host,
                    "manifest_sha256": manifest_sha256(manifest),
                    "batch_sha256": sha256_file(BATCH_SCRIPT),
                },
                indent=2,
            )
        )
        return 0
    completed = subprocess.run(argv_out, capture_output=True, text=True, timeout=120)
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
