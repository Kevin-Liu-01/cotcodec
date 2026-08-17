from __future__ import annotations

import base64
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts.seal_memory_evidence import EvidenceError, seal_supermemory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    PROJECT_ROOT
    / "experiments"
    / "memory"
    / "stage4-supermemory-local-binary-doctor.yaml"
)
EVIDENCE = (
    PROJECT_ROOT
    / "research"
    / "evidence"
    / "memory"
    / "supermemory-local-binary-v1.json"
)


@pytest.fixture
def result_root(tmp_path: Path) -> Path:
    root = tmp_path / "sealed-result-fixture"
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for name, receipt in payload["files"].items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(receipt["content_base64"], validate=True))
    return root


def _canonical_sha(payload: object) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _rewrite_manifest(root: Path) -> None:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files: dict[str, dict[str, int | str]] = {}
    for path in sorted(root.rglob("*")):
        if path == manifest_path or not path.is_file():
            continue
        data = path.read_bytes()
        files[path.relative_to(root).as_posix()] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    manifest["files"] = files
    manifest["root_sha256"] = _canonical_sha(files)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_supermemory_negative_seals_with_binary_only_boundary(
    result_root: Path,
) -> None:
    payload = seal_supermemory(result_root, EXPERIMENT)
    assert payload == json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL"
    assert payload["evidence_grade"] == "local-negative-reproduced"
    assert payload["scientific_result"] is False
    assert payload["publication_ready"] is False
    assert payload["run_count"] == 2
    assert payload["claim_boundary"] == {
        "binary_only": True,
        "h100_admission": "forbidden-for-this-release",
        "local_server_source_available": False,
        "release_revision": "39ef7e1e5ea01b34d2cdd1801d0d227d445a985d",
    }
    restart = payload["stable_projection"]["restart"]
    assert restart["checks"]["acknowledged_tenant_a_survives_sigkill"] is False
    assert restart["checks"]["acknowledged_tenant_b_survives_sigkill"] is False


def test_supermemory_raw_artifact_tamper_fails_closed(
    tmp_path: Path,
    result_root: Path,
) -> None:
    copied = tmp_path / "supermemory"
    shutil.copytree(result_root, copied)
    restart_path = copied / "run-1" / "restart.json"
    restart = json.loads(restart_path.read_text(encoding="utf-8"))
    restart["counts"]["tenant_a_latest_after_sigkill"] = 1
    restart_path.write_text(
        json.dumps(restart, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(EvidenceError, match="artifact receipt drifted"):
        seal_supermemory(copied, EXPERIMENT)


def test_supermemory_self_consistent_publication_upgrade_fails_closed(
    tmp_path: Path,
    result_root: Path,
) -> None:
    copied = tmp_path / "supermemory"
    shutil.copytree(result_root, copied)
    report_path = copied / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["publication_ready"] = True
    report["scientific_result"] = True
    report["admission"]["memory_lifecycle_h100"] = "allowed"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _rewrite_manifest(copied)
    with pytest.raises(EvidenceError, match="negative result semantics drifted"):
        seal_supermemory(copied, EXPERIMENT)


def test_supermemory_self_consistent_crash_recovery_upgrade_fails_closed(
    tmp_path: Path,
    result_root: Path,
) -> None:
    copied = tmp_path / "supermemory"
    shutil.copytree(result_root, copied)
    restart_path = copied / "run-1" / "restart.json"
    projection_path = copied / "run-1" / "stable-projection.json"
    report_path = copied / "report.json"
    restart = json.loads(restart_path.read_text(encoding="utf-8"))
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    restart["checks"]["acknowledged_tenant_a_survives_sigkill"] = True
    restart["counts"]["tenant_a_latest_after_sigkill"] = 1
    projection["restart"] = {
        "checks": restart["checks"],
        "counts": restart["counts"],
    }
    report["findings"]["acknowledged_writes_survive_sigkill_restart"] = True
    report["stable_projection_sha256"] = _canonical_sha(projection)
    restart_path.write_text(
        json.dumps(restart, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    projection_path.write_text(
        json.dumps(projection, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _rewrite_manifest(copied)
    with pytest.raises(EvidenceError, match="negative result semantics drifted"):
        seal_supermemory(copied, EXPERIMENT)


def test_supermemory_self_consistent_root_user_argv_fails_closed(
    tmp_path: Path,
    result_root: Path,
) -> None:
    copied = tmp_path / "supermemory"
    shutil.copytree(result_root, copied)
    argv_path = copied / "run-1" / "prepare.argv.json"
    argv = json.loads(argv_path.read_text(encoding="utf-8"))
    argv[argv.index("65532:65532")] = "0:0"
    argv_path.write_text(
        json.dumps(argv, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _rewrite_manifest(copied)
    with pytest.raises(EvidenceError, match="contained execution argv drifted"):
        seal_supermemory(copied, EXPERIMENT)


def test_supermemory_self_consistent_entrypoint_tamper_fails_closed(
    tmp_path: Path,
    result_root: Path,
) -> None:
    copied = tmp_path / "supermemory"
    shutil.copytree(result_root, copied)
    inspect_path = copied / "image-inspect.json"
    inspect = json.loads(inspect_path.read_text(encoding="utf-8"))
    inspect["Config"]["Entrypoint"] = ["sh", "-c"]
    inspect_path.write_text(
        json.dumps(inspect, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _rewrite_manifest(copied)
    with pytest.raises(EvidenceError, match="image receipt drifted"):
        seal_supermemory(copied, EXPERIMENT)


def test_supermemory_copied_run_with_renamed_volume_fails_closed(
    tmp_path: Path,
    result_root: Path,
) -> None:
    copied = tmp_path / "supermemory"
    shutil.copytree(result_root, copied)
    for name in (
        "prepare.json",
        "prepare.stderr",
        "restart.json",
        "restart.stderr",
        "forget.json",
        "forget.stderr",
        "stable-projection.json",
    ):
        shutil.copyfile(copied / "run-1" / name, copied / "run-2" / name)
    _rewrite_manifest(copied)
    with pytest.raises(EvidenceError, match="run semantics drifted"):
        seal_supermemory(copied, EXPERIMENT)
