"""Vendoring and licence boundaries for the Q1 stack. Pure Python."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.q1.gates import b_native

ROOT = Path(__file__).resolve().parents[1]
Q1 = ROOT / "harness" / "q1"
KB = Q1 / "third_party" / "kernelbench"


def test_vendored_kernelbench_files_match_their_recorded_hashes() -> None:
    sources = json.loads((KB / "SOURCES.json").read_text())
    assert sources["license"] == "MIT"
    assert hashlib.sha256((KB / "LICENSE").read_bytes()).hexdigest() == sources["license_sha256"]
    assert "MIT License" in (KB / "LICENSE").read_text()
    for entry in sources["files"]:
        data = (KB / entry["local"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["local"]
        assert len(data) == entry["bytes"]


def test_no_unlicensed_upstream_code_is_vendored() -> None:
    # Distinctive identifiers of KernelGYM's triton_detect.py and KernelBench-M's
    # mutator; neither repository carries a licence (decisions D5/D6).
    forbidden = (
        "_kb_patched",
        "TritonKernelLaunchHook",
        "_resolve_triton_jitfunction",
        "_existing = {r.pattern",
    )
    for path in Q1.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".c", ".json", ".md"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            for marker in forbidden:
                assert marker not in text, f"{marker} found in {path.relative_to(ROOT)}"


def test_b_native_refuses_a_clone_inside_the_repository(tmp_path: Path) -> None:
    with pytest.raises(b_native.NativeKernelGymError, match="outside"):
        b_native.resolve_clone(ROOT / "harness")
    with pytest.raises(b_native.NativeKernelGymError, match="not a KernelGYM"):
        b_native.resolve_clone(tmp_path)
    fake = tmp_path / "KernelGYM"
    (fake / "kernelgym" / "toolkit" / "kernelbench").mkdir(parents=True)
    (fake / "kernelgym" / "toolkit" / "kernelbench" / "triton_detect.py").write_text("")
    (fake / "REVISION").write_text("0" * 40)
    with pytest.raises(b_native.NativeKernelGymError, match="expected"):
        b_native.resolve_clone(fake)
    assert b_native.resolve_clone(fake, check_revision=False) == fake.resolve()


def test_kernelgym_spec_states_the_released_behaviour() -> None:
    spec = (Q1 / "gates" / "KERNELGYM_SPEC.md").read_text()
    for phrase in (
        "inference_mode",
        "enable_grad",
        "warmup = 1",
        "substring",
        "3a84417f8c0efaadb215ef638b37d12e71ed20f3",
    ):
        assert phrase in spec
