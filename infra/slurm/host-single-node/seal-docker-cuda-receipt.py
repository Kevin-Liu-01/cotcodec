#!/usr/bin/env python3
"""Seal a successful single-node Docker CUDA doctor as immutable JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import socket
import subprocess
from datetime import datetime, timezone


def _command(*argv: str) -> str:
    return subprocess.check_output(argv, text=True).strip()


def _json_command(*argv: str) -> object:
    return json.loads(_command(*argv))


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def _write_exclusive(path: pathlib.Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        path.chmod(0o444)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor-json", required=True)
    parser.add_argument("--doctor-script", type=pathlib.Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()

    job_id = _required_environment("SLURM_JOB_ID")
    step_gpus = _required_environment("SLURM_STEP_GPUS")
    gpus_on_node = _required_environment("SLURM_GPUS_ON_NODE")
    visible_devices = _required_environment("CUDA_VISIBLE_DEVICES")
    if gpus_on_node != "1" or "," in visible_devices:
        raise SystemExit("receipt requires an exactly one-GPU Slurm allocation")

    try:
        doctor = json.loads(args.doctor_json)
    except json.JSONDecodeError as error:
        raise SystemExit("doctor output was not one JSON object") from error
    if doctor.get("status") != "DOCKER_CUDA_DOCTOR_PASS":
        raise SystemExit("refusing to seal a non-passing doctor")
    if str(doctor.get("slurm_job_id")) != job_id:
        raise SystemExit("doctor job id does not match the allocation")

    output_dir = args.output_dir.expanduser().resolve()
    home = pathlib.Path.home().resolve()
    if output_dir == home or home not in output_dir.parents:
        raise SystemExit("receipt directory must be a dedicated path below the user home")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if output_dir.is_symlink():
        raise SystemExit("receipt directory cannot be a symlink")

    doctor_script = args.doctor_script.resolve(strict=True)
    seal_script = pathlib.Path(__file__).resolve(strict=True)
    slurm_config = pathlib.Path("/etc/slurm/slurm.conf")
    gres_config = pathlib.Path("/etc/slurm/gres.conf")
    for source in (doctor_script, seal_script, slurm_config, gres_config):
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"untrusted receipt source: {source}")

    gpu_fields = _command(
        "nvidia-smi",
        f"--id={visible_devices}",
        "--query-gpu=index,uuid,name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ).split(", ")
    if len(gpu_fields) != 5:
        raise SystemExit("unexpected nvidia-smi receipt format")

    image_inspect = _json_command(
        "docker",
        "image",
        "inspect",
        args.image,
        "--format",
        "{{json .}}",
    )
    if not isinstance(image_inspect, dict) or args.image.split("@", 1)[1] not in {
        digest.split("@", 1)[1]
        for digest in image_inspect.get("RepoDigests", [])
        if "@" in digest
    }:
        raise SystemExit("local image metadata does not bind the requested digest")

    receipt = {
        "schema_version": 1,
        "status": "DOCKER_CUDA_DOCTOR_PASS",
        # Host bootstrap supports Ubuntu's Python 3.10; datetime.UTC is 3.11+.
        "sealed_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "host": {
            "hostname": socket.gethostname(),
            "kernel": _command("uname", "-srvmo"),
        },
        "slurm": {
            "job_id": int(job_id),
            "job_name": os.environ.get("SLURM_JOB_NAME"),
            "node_list": os.environ.get("SLURM_JOB_NODELIST"),
            "partition": os.environ.get("SLURM_JOB_PARTITION"),
            "cpus_per_task": int(_required_environment("SLURM_CPUS_PER_TASK")),
            "step_gpus": step_gpus,
            "gpus_on_node": int(gpus_on_node),
            "cuda_visible_devices": visible_devices,
            "slurm_conf_sha256": _sha256(slurm_config),
            "gres_conf_sha256": _sha256(gres_config),
        },
        "gpu": {
            "physical_index": int(gpu_fields[0]),
            "uuid": gpu_fields[1],
            "name": gpu_fields[2],
            "memory_mib": int(gpu_fields[3]),
            "driver_version": gpu_fields[4],
        },
        "container": {
            "image": args.image,
            "image_id": image_inspect.get("Id"),
            "repo_digests": image_inspect.get("RepoDigests"),
            "docker_server": _json_command("docker", "version", "--format", "{{json .Server}}"),
            "security_options": _json_command(
                "docker", "info", "--format", "{{json .SecurityOptions}}"
            ),
            "network": "none",
            "read_only_root": True,
            "host_mounts": [],
            "capabilities": [],
            "no_new_privileges": True,
            "container_user": "65534:65534",
        },
        "source": {
            "doctor_script": str(doctor_script),
            "doctor_script_sha256": _sha256(doctor_script),
            "seal_script": str(seal_script),
            "seal_script_sha256": _sha256(seal_script),
        },
        "doctor": doctor,
    }
    payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    receipt_path = output_dir / f"docker-cuda-doctor-job-{job_id}.json"
    try:
        _write_exclusive(receipt_path, payload)
    except FileExistsError as error:
        raise SystemExit(f"receipt already exists: {receipt_path}") from error
    receipt_sha256 = _sha256(receipt_path)
    print(
        json.dumps(
            {
                "receipt_path": str(receipt_path),
                "receipt_sha256": receipt_sha256,
                "status": "DOCKER_CUDA_RECEIPT_SEALED",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
