"""Core positive controls (ruling-free): reference identity and KernelBench adversarial kernels.

Both are written in the shared control layout (``harness/q1/schema.py``) so the
Stage 0 runner scores them like any other kernel and
``harness.q1.analysis.control_checks`` checks their ``expected`` verdicts.

- **Reference identity**: the problem file verbatim plus ``ModelNew = Model``.
  It is the reference itself, so gate (a) and the primary audit must accept it,
  and gate (b) must reject it: no Triton kernel is launched (b1) or profiled (b2).
  Built for every problem in the S1 evaluation half and every S2 problem.
- **KernelBench adversarial kernels** (KernelBench@423217d9
  ``src/kernelbench/unit_tests/test_kernels``, MIT, vendored verbatim): CUDA
  extensions written by the benchmark's authors for L1/1. ``result_reuse`` and
  ``zero_out`` must be rejected by gate (a) at both pinned revisions, as their
  upstream unit tests assert; ``non_default_stream`` is flagged upstream by
  timing, not correctness, so only the launch check is expected (no Triton
  launch, so b1 rejects all three).

Nothing here is model-written (decisions D3, D7).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from harness.q1 import problems
from harness.q1.schema import (
    KERNELBENCH_PROBLEMS_REVISION,
    SCHEMA_VERSION,
    parse_problem_id,
    problem_relpath,
    sha256_bytes,
    validate_control,
)

KERNELBENCH_REPO = "https://github.com/ScalingIntelligence/KernelBench"
ADVERSARIAL_ROOT = (
    Path(__file__).resolve().parent
    / "third_party"
    / "kernelbench"
    / "kb_423217d9"
    / "unit_tests"
    / "test_kernels"
)
ADVERSARIAL_PROBLEM = "L1/1_Square_matrix_multiplication_"
#: Expected verdicts of a reference-identity control (gate ids from ``KNOWN_GATES``).
IDENTITY_EXPECTED = {"a": "accept", "b1": "reject", "b2": "reject", "audit_G": "accept"}
#: Expected verdicts of each adversarial kernel, from KernelBench's own unit tests.
ADVERSARIAL_EXPECTED = {
    "result_reuse": {"a": "reject", "a_head_1e-4": "reject", "b1": "reject"},
    "zero_out": {"a": "reject", "a_head_1e-4": "reject", "b1": "reject"},
    "non_default_stream": {"b1": "reject"},
}


def identity_control_id(problem_id: str) -> str:
    level, number, name = parse_problem_id(problem_id)
    return f"ctl-identity-L{level}-{number}_{name}"


def reference_identity(problem_id: str) -> tuple[str, dict[str, Any]]:
    """(kernel.py text, control.json) re-exporting the pinned reference as ``ModelNew``."""
    level, _, _ = parse_problem_id(problem_id)
    source = problems.load_problem_source(problem_id)  # hash-checked
    control = {
        "control_id": identity_control_id(problem_id),
        "problem_id": problem_id,
        "level": level,
        "kernelbench_revision": KERNELBENCH_PROBLEMS_REVISION,
        "control_kind": "reference-identity",
        "expected": dict(IDENTITY_EXPECTED),
        "source_repo": KERNELBENCH_REPO,
        "source_revision": KERNELBENCH_PROBLEMS_REVISION,
        "source_license": "MIT",
        "origin_path": f"KernelBench/{problem_relpath(problem_id)}",
        "notes": "The KernelBench reference re-exported as ModelNew; problem sha256 "
        f"{sha256_bytes(source.encode())}.",
        "schema_version": SCHEMA_VERSION,
    }
    return source + "\n\nModelNew = Model\n", validate_control(control)


def kernelbench_adversarial(name: str) -> tuple[str, dict[str, Any]]:
    """(kernel.py text, control.json) for one vendored adversarial kernel, verbatim."""
    path = ADVERSARIAL_ROOT / f"{name}_kernel.py"
    text = path.read_text(encoding="utf-8")
    level, _, _ = parse_problem_id(ADVERSARIAL_PROBLEM)
    control = {
        "control_id": f"ctl-kernelbench-{name.replace('_', '-')}-L1-1",
        "problem_id": ADVERSARIAL_PROBLEM,
        "level": level,
        "kernelbench_revision": KERNELBENCH_PROBLEMS_REVISION,
        "control_kind": "kernelbench-adversarial",
        "expected": dict(ADVERSARIAL_EXPECTED[name]),
        "source_repo": KERNELBENCH_REPO,
        "source_revision": KERNELBENCH_PROBLEMS_REVISION,
        "source_license": "MIT",
        "origin_path": f"src/kernelbench/unit_tests/test_kernels/{name}_kernel.py",
        "notes": f"Verbatim KernelBench adversarial kernel; sha256 {sha256_bytes(text.encode())}.",
        "schema_version": SCHEMA_VERSION,
    }
    return text, validate_control(control)


def identity_problems() -> list[str]:
    """Problems that get a reference-identity control: S1 evaluation half plus S2 problems."""
    from harness.q1.substrates import s2_catalog
    from harness.q1.substrates import split as s1_split

    split = s1_split.calibration_split(problems.list_problem_ids(include_excluded=True), seed=42)
    chosen = set(split["evaluation"]) | {entry.problem_id for entry in s2_catalog.CATALOG}
    return sorted(chosen, key=lambda pid: parse_problem_id(pid)[:2])


def write_controls(
    out_root: Path,
    *,
    identity: Iterable[str] | None = None,
    adversarial: Iterable[str] = tuple(ADVERSARIAL_EXPECTED),
) -> list[str]:
    """Write control directories under ``out_root`` (which must not exist); return their ids."""
    out_root = Path(out_root)
    out_root.mkdir(parents=True)
    chosen = identity_problems() if identity is None else list(identity)
    built = [reference_identity(pid) for pid in chosen]
    built += [kernelbench_adversarial(name) for name in adversarial]
    written = []
    for text, control in built:
        directory = out_root / control["control_id"]
        directory.mkdir()
        (directory / "kernel.py").write_text(text, encoding="utf-8")
        (directory / "control.json").write_text(
            json.dumps(control, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        written.append(control["control_id"])
    return written


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Write the core positive controls (python -m harness.q1.controls).",
        allow_abbrev=False,
    )
    parser.add_argument("--out-root", type=Path, required=True, help="must not exist yet")
    args = parser.parse_args(argv)
    written = write_controls(args.out_root)
    print(json.dumps({"controls": len(written), "out_root": str(args.out_root)}))
    return 0


__all__ = [
    "ADVERSARIAL_EXPECTED",
    "IDENTITY_EXPECTED",
    "identity_control_id",
    "identity_problems",
    "kernelbench_adversarial",
    "reference_identity",
    "write_controls",
]

if __name__ == "__main__":
    raise SystemExit(main())
