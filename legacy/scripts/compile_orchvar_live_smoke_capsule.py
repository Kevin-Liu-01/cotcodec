#!/usr/bin/env python3
"""Compile the dirty live-smoke source into a deterministic hashed capsule."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXED_PATHS = {
    Path("experiments/degradation_canary_qwen35_4b_live_smoke.yaml"),
    Path("experiments/degradation_canary_qwen35_4b_live_v2_smoke.yaml"),
    Path("experiments/orchvar_qwen35_iterative_live_smoke.yaml"),
    Path("experiments/orchvar_qwen35_iterative_structural_live_smoke.yaml"),
    Path("experiments/orchvar_message_action_transport_audit.yaml"),
    Path("experiments/orchvar_qwen35_two_stage_live_smoke.yaml"),
    Path("harness/benchmarks/specs/orchvar_canary_tasks.yaml"),
    Path("harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml"),
    Path("infra/slurm/host-single-node/orchvar-live-smoke.sbatch"),
    Path("models/registry.yaml"),
    Path("research/evidence/harness/orchvar-live-task-interface-v2-admission.json"),
    Path(
        "research/evidence/harness/"
        "orchvar-iterative-tool-result-cpu-admission-v2.json"
    ),
    Path(
        "research/evidence/harness/"
        "orchvar-iterative-structural-json-v2-cpu-admission.json"
    ),
    Path(
        "research/evidence/harness/"
        "orchvar-message-action-transport-audit-v1.json"
    ),
    Path(
        "research/evidence/harness/"
        "orchvar-two-stage-message-action-cpu-admission-v3.json"
    ),
    Path("scripts/fetch_open_model.py"),
    Path("scripts/run_orchvar_live_task_v2_admission.py"),
    Path("scripts/run_orchvar_iterative_cpu_admission.py"),
    Path("scripts/seal_orchvar_iterative_cpu_admission.py"),
    Path("scripts/validate_orchvar_iterative_live_experiment.py"),
    Path("scripts/validate_orchvar_iterative_structural_live_experiment.py"),
    Path("scripts/validate_orchvar_live_smoke_experiment.py"),
    Path("scripts/validate_orchvar_live_tasks_v2.py"),
    Path("scripts/validate_orchvar_live_v2_smoke_experiment.py"),
    Path("scripts/validate_orchvar_two_stage_live_experiment.py"),
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def source_paths() -> list[Path]:
    paths = FIXED_PATHS | {
        path.relative_to(PROJECT_ROOT)
        for path in (PROJECT_ROOT / "harness").rglob("*.py")
    }
    missing = [path.as_posix() for path in sorted(paths) if not (PROJECT_ROOT / path).is_file()]
    if missing:
        raise ValueError(f"live-smoke capsule inputs are missing: {missing}")
    return sorted(paths)


def compile_capsule(output_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    payloads: dict[Path, bytes] = {}
    for relative in source_paths():
        absolute = PROJECT_ROOT / relative
        if absolute.is_symlink():
            raise ValueError(f"capsule input cannot be a symlink: {relative}")
        payload = absolute.read_bytes()
        payloads[relative] = payload
        rows.append(
            {
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
            }
        )
    source_root = hashlib.sha256(canonical_json(rows).encode()).hexdigest()
    manifest = {
        "schema_version": 1,
        "capsule_type": "orchvar-live-smoke-source-v1",
        "source_root_sha256": source_root,
        "files": rows,
        "claim_status": "NON_SCIENTIFIC_LIVE_SMOKE",
    }
    manifest_payload = (canonical_json(manifest) + "\n").encode()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"orchvar-live-smoke-source-{source_root}.tar.gz"
    with (
        archive.open("wb") as raw_handle,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as zipped,
        tarfile.open(fileobj=zipped, mode="w") as bundle,
    ):
        for relative, payload in sorted(payloads.items()):
            info = tarfile.TarInfo(relative.as_posix())
            info.size = len(payload)
            info.mode = 0o644
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            bundle.addfile(info, io.BytesIO(payload))
        info = tarfile.TarInfo("CAPSULE-MANIFEST.json")
        info.size = len(manifest_payload)
        info.mode = 0o644
        info.mtime = 0
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        bundle.addfile(info, io.BytesIO(manifest_payload))
    result = {
        "archive": str(archive),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "source_root_sha256": source_root,
        "manifest": manifest,
    }
    receipt = output_dir / f"orchvar-live-smoke-source-{source_root}.receipt.json"
    receipt.write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: compile_orchvar_live_smoke_capsule.py OUTPUT_DIR", file=sys.stderr)
        return 2
    result = compile_capsule(Path(sys.argv[1]).resolve())
    print(canonical_json({key: value for key, value in result.items() if key != "manifest"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
