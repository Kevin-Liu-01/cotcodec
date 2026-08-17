#!/usr/bin/env python3
"""Freeze a deterministic Mnemon static-space actor panel in contained Docker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data/results/mnemon-static-space-panel/2026-08-16-local-docker-v1"
)
PANEL_SCRIPT = (
    PROJECT_ROOT / "infra/memory-baselines/mnemon/freeze-actor-panel.mjs"
)
ADMISSION_EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/mnemon-active-space-admission-v1.json"
)
ADMISSION_EVIDENCE_SHA256 = (
    "27d7d55c664748bf7bc5fb6e1ad53d17cb35a50d9497329851dc1eaa4155debb"
)
IMAGE_ID = (
    "sha256:758216ed7cf9fa7794ab4e63efac2a08b4af92a78b99ae378ab6b512e6d9db5f"
)
MARKER = "COTCODEC_MNEMON_ACTOR_PANEL="


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _strict_object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise ValueError(f"{owner} contains non-finite JSON constant {value}")

    value = json.loads(data, parse_constant=reject)
    if not isinstance(value, dict):
        raise ValueError(f"{owner} must be one JSON object")
    return value


def _write(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _run_once() -> tuple[bytes, dict[str, Any]]:
    command = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "65532:65532",
        "--cpus",
        "4",
        "--memory",
        "4g",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=1g",
        "--entrypoint",
        "node",
        "-v",
        f"{PANEL_SCRIPT}:/opt/cotcodec/freeze-actor-panel.mjs:ro",
        IMAGE_ID,
        "/opt/cotcodec/freeze-actor-panel.mjs",
    ]
    completed = subprocess.run(command, check=True, capture_output=True)
    rows = [
        line[len(MARKER) :]
        for line in completed.stdout.splitlines()
        if line.startswith(MARKER.encode())
    ]
    if len(rows) != 1:
        raise ValueError("Mnemon actor freezer did not emit exactly one panel marker")
    panel = _strict_object(rows[0], "Mnemon actor panel")
    return completed.stdout, panel


def _validate_panel(panel: dict[str, Any]) -> None:
    if (
        panel.get("schema_version") != 1
        or panel.get("study") != "mnemon-static-space-h100-actor-v1"
        or panel.get("source_id") != "mnemon"
        or panel.get("task_count") != 32
        or panel.get("group_count") != 32
        or panel.get("arms")
        != ["no_memory", "all_spaces", "lexical_router", "oracle_space"]
        or panel.get("retrieval_top_k") != 4
        or panel.get("fixed_slot_characters") != 160
        or panel.get("retrieval_calls_per_nonempty_arm") != 1
        or panel.get("router_inputs") != ["question"]
        or panel.get("answer_labels_available_to_router") is not False
        or panel.get("padding_is_memory_evidence") is not False
        or panel.get("scientific_result") is not False
        or panel.get("publication_ready") is not False
    ):
        raise ValueError("Mnemon actor panel contract drifted")
    items = panel.get("items")
    if not isinstance(items, list) or len(items) != 32:
        raise ValueError("Mnemon actor panel task roster drifted")
    expected_ids = [f"mnemon-static-{index:03d}" for index in range(32)]
    if [item.get("task_id") for item in items] != expected_ids:
        raise ValueError("Mnemon actor panel task identities drifted")
    for item in items:
        arms = item.get("arms")
        if (
            not isinstance(arms, dict)
            or set(arms) != set(panel["arms"])
            or arms["no_memory"] != []
            or len(arms["all_spaces"]) != 4
            or len(arms["lexical_router"]) != 4
            or arms["lexical_router"] != arms["oracle_space"]
            or item.get("routed_space") != item.get("target_space")
            or any(
                slot.get("source_space") != item["target_space"]
                for slot in arms["lexical_router"]
                if not slot.get("is_padding")
            )
        ):
            raise ValueError(f"Mnemon actor task drifted: {item.get('task_id')}")


def freeze(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to overwrite Mnemon actor panel: {output}")
    from scripts.seal_mnemon_active_space_evidence import validate_evidence

    if _sha(ADMISSION_EVIDENCE.read_bytes()) != ADMISSION_EVIDENCE_SHA256:
        raise ValueError("Mnemon admission evidence SHA-256 drifted")
    validate_evidence(ADMISSION_EVIDENCE)
    script_sha256 = _sha(PANEL_SCRIPT.read_bytes())
    run_one, panel_one = _run_once()
    run_two, panel_two = _run_once()
    _validate_panel(panel_one)
    _validate_panel(panel_two)
    if panel_one != panel_two:
        raise ValueError("Mnemon clean actor-panel freezes differ")

    inspection = subprocess.run(
        ["docker", "image", "inspect", IMAGE_ID],
        check=True,
        capture_output=True,
    ).stdout
    image_rows = json.loads(inspection)
    if (
        not isinstance(image_rows, list)
        or len(image_rows) != 1
        or image_rows[0].get("Id") != IMAGE_ID
    ):
        raise ValueError("Mnemon actor-panel image inspection drifted")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        panel_bytes = _canonical(panel_one)
        _write(temporary / "panel.json", panel_bytes)
        _write(temporary / "repeat-1.txt", run_one)
        _write(temporary / "repeat-2.txt", run_two)
        _write(temporary / "image-inspect.json", inspection)
        report = {
            "schema_version": 1,
            "study": "mnemon-static-space-panel-freeze-v1",
            "status": "MNEMON_STATIC_SPACE_PANEL_FROZEN",
            "scientific_result": False,
            "publication_ready": False,
            "h100_actor_admission": "bounded-static-selection-cell-only",
            "image_id": IMAGE_ID,
            "admission_evidence_sha256": ADMISSION_EVIDENCE_SHA256,
            "freezer_sha256": script_sha256,
            "panel_sha256": _sha(panel_bytes),
            "run_count": 2,
            "task_count": 32,
            "case_count": 128,
        }
        _write(temporary / "report.json", _canonical(report))
        files = {}
        for path in sorted(temporary.iterdir()):
            data = path.read_bytes()
            files[path.name] = {"bytes": len(data), "sha256": _sha(data)}
        manifest = {
            "schema_version": 1,
            "status": report["status"],
            "files": files,
        }
        manifest["root_sha256"] = _sha(_canonical(manifest))
        _write(temporary / "manifest.json", _canonical(manifest))
        os.replace(temporary, output)
        directory = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(freeze(args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
