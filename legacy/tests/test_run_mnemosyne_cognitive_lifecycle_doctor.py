from __future__ import annotations

import json

import pytest

from scripts.run_mnemosyne_cognitive_lifecycle_doctor import (
    MnemosyneCognitiveRunnerError,
    _doctor_argv,
    _strict_report,
)


def _report(phase: str) -> dict[str, object]:
    projection = {"checks": {"registered_failure": True}}
    encoded = json.dumps(projection, separators=(",", ":"), sort_keys=True).encode()
    import hashlib

    return {
        "schema_version": 1,
        "source_revision": "5506aae7cec9ada5523099fd5ab858a4eee593b6",
        "phase": phase,
        "status": "MNEMOSYNE_COGNITIVE_ACTIVE_INACTIVE_ADMISSION_KILLED",
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": False,
        "provider_calls": 0,
        "model_backend_calls": 0,
        "projection": projection,
        "projection_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def test_strict_report_accepts_registered_negative_and_rejects_upgrade() -> None:
    report = _report("initial")
    assert _strict_report(json.dumps(report).encode(), "initial") == report
    report["scientific_result"] = True
    with pytest.raises(MnemosyneCognitiveRunnerError, match="semantics drifted"):
        _strict_report(json.dumps(report).encode(), "initial")


def test_doctor_argv_is_locked_down_without_gpu_or_host_network() -> None:
    argv = _doctor_argv(
        image_id="sha256:" + "1" * 64,
        network="internal-network",
        qdrant_name="qdrant",
        collection="collection",
        phase="restart",
    )
    assert "--read-only" in argv
    assert argv[
        argv.index("--cap-drop") : argv.index("--cap-drop") + 2
    ] == ["--cap-drop", "ALL"]
    assert "no-new-privileges" in argv
    assert "--gpus" not in argv
    assert "host" not in argv
    assert argv[-2:] == ["--phase", "restart"]
