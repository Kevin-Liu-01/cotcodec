#!/usr/bin/env python3
"""Seal the contained Graphiti/FalkorDBLite architecture admission probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402

EXPECTED = {
    "architecture": "arm64",
    "adapter": "graphiti-explicit-triplet-lifecycle-v1",
    "experiment_sha256": "6dfb4bf7f415378b8351870aeedda80881bb8842523bfc6ae4d7a1365d10526c",
    "graphiti_revision": "401c59a65bdeb22a44136901ff30231e6998a7fe",
    "runner_sha256": "6dece39c429cca3cb2d7dc87b1c6a845c479733930980aae50ffee90be03f450",
    "source_archive_sha256": "9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303",
}
STATUS = "BLOCKED_FALKORDBLITE_ARM64_MODULE_ARCHITECTURE_MISMATCH"
MODULE_PROBE = r"""
import json
import struct
from pathlib import Path

root = Path('/workspace/cotcodec/.venv/lib/python3.12/site-packages/redislite/bin')
result = {}
for name in ('redis-server', 'falkordb.so'):
    path = root / name
    data = path.read_bytes()[:20]
    if data[:4] != b'\x7fELF':
        raise SystemExit(f'{name} is not ELF')
    result[name] = {
        'elf_class': data[4],
        'elf_data': data[5],
        'e_machine': struct.unpack('<H', data[18:20])[0],
        'sha256': __import__('hashlib').sha256(path.read_bytes()).hexdigest(),
        'size': path.stat().st_size,
    }
print(json.dumps(result, sort_keys=True, separators=(',', ':')))
"""


class ProbeError(ValueError):
    """Raised when the container probe cannot establish its exact contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _run(argv: list[str], *, timeout: float = 120.0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv, capture_output=True, check=False, timeout=timeout)


def _docker_run_options() -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/arm64",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--cpus",
        "2",
        "--memory",
        "2560m",
        "--user",
        "65532:65532",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m,uid=65532,gid=65532,mode=0700",
        "--tmpfs",
        "/state:rw,noexec,nosuid,nodev,size=1g,uid=65532,gid=65532,mode=0700",
        "--tmpfs",
        "/outputs:rw,noexec,nosuid,nodev,size=64m,uid=65532,gid=65532,mode=0700",
    ]


def classify_probe(
    inspect: dict[str, Any], module_probe: dict[str, Any], runs: list[dict[str, Any]]
) -> dict[str, bool]:
    labels = inspect.get("Config", {}).get("Labels", {})
    image_id = inspect.get("Id")
    return {
        "image_id_immutable": isinstance(image_id, str)
        and image_id.startswith("sha256:")
        and len(image_id) == 71,
        "image_architecture_arm64": inspect.get("Architecture") == EXPECTED["architecture"],
        "graphiti_revision_exact": labels.get("org.opencontainers.image.revision")
        == EXPECTED["graphiti_revision"],
        "source_archive_exact": labels.get("org.cotcodec.source-archive-sha256")
        == EXPECTED["source_archive_sha256"],
        "adapter_exact": labels.get("org.cotcodec.memory-lifecycle-adapter")
        == EXPECTED["adapter"],
        "runner_exact": labels.get("org.cotcodec.graphiti-lifecycle-doctor-sha256")
        == EXPECTED["runner_sha256"],
        "experiment_exact": labels.get(
            "org.cotcodec.graphiti-lifecycle-experiment-sha256"
        )
        == EXPECTED["experiment_sha256"],
        "scientific_result_false": labels.get("org.cotcodec.scientific-result")
        == "false",
        "redis_server_is_aarch64": module_probe.get("redis-server", {}).get("e_machine")
        == 183,
        "falkordb_module_is_x86_64": module_probe.get("falkordb.so", {}).get("e_machine")
        == 62,
        "two_clean_failures_reproduced": len(runs) == 2
        and all(
            run.get("exit_code") == 1
            and run.get("container_receipt", {}).get("state", {}).get("exit_code") == 1
            for run in runs
        ),
        "distinct_container_receipts": len(runs) == 2
        and len(
            {
                (
                    run.get("container_receipt", {}).get("container_id"),
                    run.get("container_receipt", {}).get("created_at"),
                    run.get("container_receipt", {}).get("state", {}).get("started_at"),
                )
                for run in runs
            }
        )
        == 2
        and all(
            isinstance(run.get("container_receipt", {}).get("container_id"), str)
            and len(run["container_receipt"]["container_id"]) == 64
            and run.get("container_receipt", {}).get("state", {}).get("status")
            == "exited"
            for run in runs
        ),
        "failure_is_native_server_start": len(runs) == 2
        and all(
            "The redis-server process failed to start" in run.get("stderr", "")
            for run in runs
        ),
        "runtime_network_none": len(runs) == 2
        and all(
            "--network" in run.get("create_argv", [])
            and "none" in run.get("create_argv", [])
            for run in runs
        ),
    }


def _container_receipt(inspect: dict[str, Any]) -> dict[str, Any]:
    host = inspect.get("HostConfig", {})
    state = inspect.get("State", {})
    return {
        "container_id": inspect.get("Id"),
        "created_at": inspect.get("Created"),
        "image_id": inspect.get("Image"),
        "mounts": inspect.get("Mounts"),
        "host_config": {
            "auto_remove": host.get("AutoRemove"),
            "cap_drop": host.get("CapDrop"),
            "memory": host.get("Memory"),
            "nano_cpus": host.get("NanoCpus"),
            "network_mode": host.get("NetworkMode"),
            "pids_limit": host.get("PidsLimit"),
            "readonly_rootfs": host.get("ReadonlyRootfs"),
            "security_opt": host.get("SecurityOpt"),
            "tmpfs": host.get("Tmpfs"),
        },
        "state": {
            "error": state.get("Error"),
            "exit_code": state.get("ExitCode"),
            "finished_at": state.get("FinishedAt"),
            "running": state.get("Running"),
            "started_at": state.get("StartedAt"),
            "status": state.get("Status"),
        },
    }


def probe(image: str, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise ProbeError("output directory already exists")
    inspect_result = _run(["docker", "image", "inspect", image], timeout=30)
    if inspect_result.returncode:
        raise ProbeError(inspect_result.stderr.decode(errors="replace").strip())
    inspected = json.loads(inspect_result.stdout)
    if not isinstance(inspected, list) or len(inspected) != 1:
        raise ProbeError("docker inspect did not resolve exactly one image")
    inspect = inspected[0]
    image_id = inspect.get("Id")
    if image != image_id:
        raise ProbeError("probe requires the immutable image ID, not a tag")

    module_argv = [
        *_docker_run_options(),
        "--entrypoint",
        "/workspace/cotcodec/.venv/bin/python",
        image,
        "-c",
        MODULE_PROBE,
    ]
    module_result = _run(module_argv, timeout=30)
    if module_result.returncode:
        raise ProbeError(module_result.stderr.decode(errors="replace").strip())
    module_probe = json.loads(module_result.stdout)

    runs: list[dict[str, Any]] = []
    for index in (1, 2):
        create_argv = [
            *_docker_run_options(),
            image,
            "--state-root",
            "/state/run",
            "--output-dir",
            "/outputs",
        ]
        create_argv[1] = "create"
        create_argv.remove("--rm")
        created = _run(create_argv, timeout=30)
        if created.returncode:
            raise ProbeError(created.stderr.decode(errors="replace").strip())
        container_id = created.stdout.decode().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", container_id):
            raise ProbeError("docker create did not return an immutable container ID")
        start_argv = ["docker", "start", "--attach", container_id]
        inspect_argv = ["docker", "container", "inspect", container_id]
        remove_argv = ["docker", "container", "rm", container_id]
        try:
            result = _run(start_argv)
            inspected_container = _run(inspect_argv, timeout=30)
            if inspected_container.returncode:
                raise ProbeError(
                    inspected_container.stderr.decode(errors="replace").strip()
                )
            inspected_values = json.loads(inspected_container.stdout)
            if not isinstance(inspected_values, list) or len(inspected_values) != 1:
                raise ProbeError("docker container inspect returned an invalid roster")
            container_receipt = _container_receipt(inspected_values[0])
        finally:
            removed = _run(remove_argv, timeout=30)
            if removed.returncode:
                raise ProbeError(removed.stderr.decode(errors="replace").strip())
        runs.append(
            {
                "index": index,
                "create_argv": create_argv,
                "start_argv": start_argv,
                "inspect_argv": inspect_argv,
                "remove_argv": remove_argv,
                "container_receipt": container_receipt,
                "exit_code": result.returncode,
                "stdout": result.stdout.decode(errors="replace"),
                "stderr": result.stderr.decode(errors="replace"),
            }
        )

    checks = classify_probe(inspect, module_probe, runs)
    if not all(checks.values()):
        raise ProbeError(f"Graphiti container probe did not match its blocker: {checks}")
    output_dir.mkdir(parents=True, mode=0o700)
    inspect_path = output_dir / "image-inspect.json"
    probe_path = output_dir / "module-architecture.json"
    _write_once(inspect_path, (json.dumps(inspect, indent=2, sort_keys=True) + "\n").encode())
    _write_once(probe_path, (json.dumps(module_probe, indent=2, sort_keys=True) + "\n").encode())
    run_files: list[dict[str, str]] = []
    for run in runs:
        path = output_dir / f"run-{run['index']}.json"
        _write_once(path, (json.dumps(run, indent=2, sort_keys=True) + "\n").encode())
        run_files.append({"path": path.name, "sha256": _sha256(path)})
    report = {
        "schema_version": "1.0",
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "forbidden",
        "image_id": image_id,
        "checks": checks,
        "module_architecture": module_probe,
        "implication": (
            "FalkorDBLite 0.10.0 built ARM64 Redis binaries but packaged an x86-64 "
            "Falkor module; the contained native Graphiti lifecycle cannot start."
        ),
    }
    report_path = output_dir / "report.json"
    _write_once(report_path, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
    manifest = {
        "schema_version": "1.0",
        "status": STATUS,
        "image_inspect_sha256": _sha256(inspect_path),
        "module_architecture_sha256": _sha256(probe_path),
        "report_sha256": _sha256(report_path),
        "runs": run_files,
    }
    manifest["manifest_sha256"] = sha256_text(canonical_json(manifest))
    _write_once(
        output_dir / "manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = probe(args.image, args.output_dir.resolve())
    print(canonical_json({"status": report["status"], "checks": report["checks"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
