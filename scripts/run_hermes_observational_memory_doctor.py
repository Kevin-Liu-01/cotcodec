#!/usr/bin/env python3
"""Run the standalone Hermes OM lifecycle doctor in sealed Docker processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_STATUS = "BLOCKED_NO_PROVIDER_NATIVE_DELETE_OR_ERASURE"
EXPECTED_LABELS = {
    "org.opencontainers.image.revision": "a90d5369f76c87c98547d2e283aa26d5cfabf322",
    "ai.cotcodec.hermes.git_tree": "963eb136bfb21fd0b296a40529cbb3575c610874",
    "ai.cotcodec.hermes_observational_memory.git_sha": "90d83c1ff768d80f99f4e3ef4d76269f90e1c808",
    "ai.cotcodec.hermes_observational_memory.git_tree": "5cf00ebd8f4d57673469e2e45f3954ac37d875af",
    "ai.cotcodec.observational_memory.git_sha": "6bbc16e81ad1258ee1e8ba37c9efcc6ce36a0208",
    "ai.cotcodec.observational_memory.git_tree": "96f4288c19b78b0bdda8568efa0c5b1435d64552",
    "ai.cotcodec.study": "hermes-observational-memory-lifecycle-v1",
}


class DoctorRunError(RuntimeError):
    """Fail-closed orchestration error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temp = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(temp, path)
    except FileExistsError as exc:
        raise DoctorRunError(f"refusing to overwrite {path}") from exc
    finally:
        temp.unlink(missing_ok=True)


def _regular_tree(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise DoctorRunError(f"symlink forbidden under run root: {rel}")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise DoctorRunError(f"special file forbidden under run root: {rel}")
        rows.append({"path": rel, "bytes": info.st_size, "sha256": _sha256(path)})
    return rows


def _scan_state(root: Path, canary: str) -> dict[str, Any]:
    matches: list[str] = []
    for row in _regular_tree(root):
        path = root / row["path"]
        if canary.encode() in path.read_bytes():
            matches.append(row["path"])
    return {"files": _regular_tree(root), "canary_paths": matches}


def _safe_purge(root: Path, run_root: Path) -> None:
    resolved_run = run_root.resolve(strict=True)
    resolved = root.resolve(strict=True)
    if resolved.parent.parent != (resolved_run / "state").resolve(strict=True):
        raise DoctorRunError(f"purge target escaped registered state root: {root}")
    if root.is_symlink() or not root.is_dir():
        raise DoctorRunError(f"purge target must be a real directory: {root}")
    shutil.rmtree(root)
    if root.exists():
        raise DoctorRunError(f"operator purge left state root: {root}")


def _inspect_image(image: str, expected_id: str) -> dict[str, Any]:
    proc = subprocess.run(
        ["docker", "image", "inspect", image],
        check=True,
        text=True,
        capture_output=True,
    )
    raw = json.loads(proc.stdout)
    if not isinstance(raw, list) or len(raw) != 1 or raw[0].get("Id") != expected_id:
        raise DoctorRunError("live image ID does not match sealed build receipt")
    labels = (raw[0].get("Config") or {}).get("Labels") or {}
    for key, value in EXPECTED_LABELS.items():
        if labels.get(key) != value:
            raise DoctorRunError(f"image label drifted: {key}")
    return raw[0]


def _docker_phase(
    *, image: str, state_root: Path, phase: str, canary: str, result_root: Path
) -> dict[str, Any]:
    uid = str(os.getuid())
    gid = str(os.getgid())
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
        "--pids-limit",
        "256",
        "--memory",
        "4g",
        "--cpus",
        "4",
        "--user",
        f"{uid}:{gid}",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=256m",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "PYTHONUNBUFFERED=1",
        "--volume",
        f"{state_root.resolve()}:/state:rw",
        image,
        phase,
        "--canary",
        canary,
    ]
    proc = subprocess.run(command, text=True, capture_output=True)
    stem = result_root / phase
    stem.with_suffix(".stdout.log").write_text(proc.stdout)
    stem.with_suffix(".stderr.log").write_text(proc.stderr)
    if proc.returncode != 0:
        raise DoctorRunError(
            f"contained {phase} phase failed ({proc.returncode}); see {stem}.stderr.log"
        )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise DoctorRunError(f"contained {phase} phase did not emit one JSON row")
    payload = json.loads(lines[0])
    if payload.get("phase") != phase:
        raise DoctorRunError(f"contained phase mislabeled itself: {payload.get('phase')}")
    _write_json(stem.with_suffix(".json"), payload)
    return payload


def _projection(phase: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": phase["phase"],
        "provider": phase["provider"],
        "versions": phase["versions"],
        "tool_names": phase["tool_names"],
        "provider_native_delete_methods": phase["provider_native_delete_methods"],
        "provider_native_delete_or_forget_tool": phase[
            "provider_native_delete_or_forget_tool"
        ],
        "provider_native_physical_erasure_contract": phase[
            "provider_native_physical_erasure_contract"
        ],
        "before_contains_canary": phase["before_contains_canary"],
        "direct_contains_canary": phase["direct_contains_canary"],
        "tool_contains_canary": phase["tool_contains_canary"],
        "context_contains_canary": phase["context_contains_canary"],
        "budget_blocked": phase["budget_probe"]["blocked"],
        "api_credentials_present": phase["api_credentials_present"],
        "model_calls": phase["model_calls"],
        "external_calls": phase["external_calls"],
    }


def run(
    *,
    image: str,
    expected_image_id: str,
    image_archive: Path,
    sbom: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if not IMAGE_ID_RE.fullmatch(expected_image_id):
        raise DoctorRunError("expected image ID must be sha256:<64 lowercase hex>")
    for path, label in ((image_archive, "image archive"), (sbom, "SBOM")):
        if not path.is_file() or path.is_symlink():
            raise DoctorRunError(f"{label} must be a regular file")
    if output_dir.exists():
        raise DoctorRunError("output directory already exists")
    output_dir.mkdir(parents=True, mode=0o700)
    (output_dir / "state").mkdir()
    inspect = _inspect_image(image, expected_image_id)
    _write_json(output_dir / "image-inspect.json", inspect)

    repeat_projections: list[dict[str, Any]] = []
    repeats: list[dict[str, Any]] = []
    for repeat in range(2):
        canary = f"COTCODEC_HERMES_OM_CANARY_REPEAT_{repeat}_7F6C9D2A"
        repeat_result = output_dir / f"repeat-{repeat}"
        repeat_result.mkdir()
        a_root = output_dir / "state" / f"repeat-{repeat}" / "tenant-a"
        b_root = output_dir / "state" / f"repeat-{repeat}" / "tenant-b"
        a_root.mkdir(parents=True)
        b_root.mkdir(parents=True)
        prepare = _docker_phase(
            image=image,
            state_root=a_root,
            phase="prepare",
            canary=canary,
            result_root=repeat_result,
        )
        restart = _docker_phase(
            image=image,
            state_root=a_root,
            phase="restart",
            canary=canary,
            result_root=repeat_result,
        )
        isolated = _docker_phase(
            image=image,
            state_root=b_root,
            phase="isolated",
            canary=canary,
            result_root=repeat_result,
        )
        before_a = _scan_state(a_root, canary)
        before_b = _scan_state(b_root, canary)
        if not before_a["canary_paths"] or before_b["canary_paths"]:
            raise DoctorRunError("retained-file or tenant-isolation scan failed")
        _safe_purge(a_root, output_dir)
        _safe_purge(b_root, output_dir)
        after = {
            "tenant_a_exists": a_root.exists(),
            "tenant_b_exists": b_root.exists(),
        }
        if any(after.values()):
            raise DoctorRunError("operator-scoped root purge left residue")
        projection = {
            "prepare": _projection(prepare),
            "restart": _projection(restart),
            "isolated": _projection(isolated),
            "explicit_note_restart_persistence": restart["direct_contains_canary"],
            "separate_memory_root_isolation": not isolated["direct_contains_canary"],
            "operator_purge": after,
        }
        _write_json(repeat_result / "state-before-purge.json", {"a": before_a, "b": before_b})
        _write_json(repeat_result / "state-after-purge.json", after)
        _write_json(repeat_result / "projection.json", projection)
        repeat_projections.append(projection)
        repeats.append(
            {
                "repeat": repeat,
                "projection_sha256": _sha256(repeat_result / "projection.json"),
                "state_before_purge_sha256": _sha256(
                    repeat_result / "state-before-purge.json"
                ),
                "state_after_purge_sha256": _sha256(
                    repeat_result / "state-after-purge.json"
                ),
            }
        )

    semantic_match = repeat_projections[0] == repeat_projections[1]
    if not semantic_match:
        raise DoctorRunError("two clean lifecycle projections differ")
    report = {
        "schema_version": 1,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "image": image,
        "image_id": expected_image_id,
        "image_archive_sha256": _sha256(image_archive),
        "sbom_sha256": _sha256(sbom),
        "repeat_count": 2,
        "two_repetition_semantic_projection_match": semantic_match,
        "explicit_note_restart_persistence": True,
        "separate_memory_root_isolation": True,
        "provider_native_delete_or_forget_tool": False,
        "provider_native_physical_erasure_contract": False,
        "operator_scoped_root_purge": True,
        "h100_actor_admission": "forbidden-for-this-revision",
        "repeats": repeats,
    }
    _write_json(output_dir / "report.json", report)
    files = _regular_tree(output_dir)
    _write_json(
        output_dir / "manifest.json",
        {
            "schema_version": 1,
            "report_sha256": _sha256(output_dir / "report.json"),
            "files": files,
        },
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--expected-image-id", required=True)
    parser.add_argument("--image-archive", type=Path, required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        image=args.image,
        expected_image_id=args.expected_image_id,
        image_archive=args.image_archive,
        sbom=args.sbom,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
