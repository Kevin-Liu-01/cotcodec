from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTOR_PATH = ROOT / "infra/memory-baselines/timem/doctor.py"


def _doctor_module():
    spec = importlib.util.spec_from_file_location("timem_core_doctor", DOCTOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doctor_identity_is_frozen() -> None:
    doctor = _doctor_module()
    assert doctor.EXPECTED_REVISION == "6d279a5f5d40ee229e1995df15c182cb2062c71c"
    assert doctor.EXPECTED_STATUS == "TIMEM_CORE_RUNTIME_ADMISSION_KILLED"


def test_doctor_rejects_incomplete_source(tmp_path: Path) -> None:
    doctor = _doctor_module()
    try:
        doctor.run(tmp_path)
    except RuntimeError as exc:
        assert "source is incomplete" in str(exc)
    else:
        raise AssertionError("incomplete TiMem source was accepted")


def test_dockerfile_is_nonroot_and_pinned() -> None:
    text = (ROOT / "infra/memory-baselines/timem/Dockerfile").read_text()
    assert "@sha256:" in text
    assert "USER 65532:65532" in text
    assert "discovery-only" in text
    assert "apt-get" not in text
