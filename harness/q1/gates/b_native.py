"""``b_native``: run the UNMODIFIED KernelGYM clone, for fidelity measurement only.

KernelGYM@3a84417f has no LICENSE file, so none of its code is in this
repository. This module imports it at run time from a scratch clone outside
the repository (``KERNELGYM_SRC`` or an explicit path), checks the clone's git
revision, and calls its own functions. Nothing it returns feeds a ladder
gate; ``b_native`` rows exist to measure agreement of our ``b1``/``b2`` with
upstream and to report ``a``-versus-``b0`` disagreements.

Import note: the package ``kernelgym/__init__.py`` imports the server stack
(scheduler, workflow), which the evaluation path does not use. We register
namespace stubs for ``kernelgym``, ``kernelgym.toolkit`` and
``kernelgym.toolkit.kernelbench`` so that the evaluation modules import
without executing those package ``__init__`` files; the module files
themselves load unmodified. ``kernelgym.config`` needs ``pydantic_settings``
(test-only dependency of the derived image).
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

from harness.q1.gates.common import GateOutcome, exception_details
from harness.q1.schema import KERNELGYM_REVISION

REPO_ROOT = Path(__file__).resolve().parents[3]


class NativeKernelGymError(RuntimeError):
    """Raised when the upstream clone is missing, misplaced or at the wrong revision."""


def resolve_clone(
    path: str | os.PathLike[str] | None = None, *, check_revision: bool = True
) -> Path:
    raw = path if path is not None else os.environ.get("KERNELGYM_SRC")
    if not raw:
        raise NativeKernelGymError("set KERNELGYM_SRC to an unmodified KernelGYM clone")
    clone = Path(raw).resolve()
    if clone == REPO_ROOT or REPO_ROOT in clone.parents:
        raise NativeKernelGymError("the KernelGYM clone must live outside this repository")
    if not (clone / "kernelgym" / "toolkit" / "kernelbench" / "triton_detect.py").is_file():
        raise NativeKernelGymError(f"{clone} is not a KernelGYM checkout")
    if check_revision:
        revision = clone_revision(clone)
        if revision != KERNELGYM_REVISION:
            raise NativeKernelGymError(
                f"KernelGYM clone is at {revision}, expected {KERNELGYM_REVISION}"
            )
    return clone


def clone_revision(clone: Path) -> str | None:
    """Git HEAD of the clone, or the ``REVISION`` file of an exported tree."""
    try:
        completed = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", str(clone), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        marker = clone / "REVISION"
        return marker.read_text(encoding="utf-8").strip() if marker.is_file() else None


def _stub_packages(clone: Path) -> None:
    for name, relative in (
        ("kernelgym", "kernelgym"),
        ("kernelgym.toolkit", "kernelgym/toolkit"),
        ("kernelgym.toolkit.kernelbench", "kernelgym/toolkit/kernelbench"),
    ):
        if name in sys.modules:
            continue
        module = types.ModuleType(name)
        module.__path__ = [str(clone / relative)]  # type: ignore[attr-defined]
        sys.modules[name] = module


def load_upstream_module(clone: Path, dotted: str) -> types.ModuleType:
    """Import ``kernelgym.toolkit.kernelbench.<dotted>`` from the clone, unmodified."""
    _stub_packages(clone)
    return importlib.import_module(f"kernelgym.toolkit.kernelbench.{dotted}")


def load_triton_detect_standalone(clone: Path) -> types.ModuleType:
    """Load ``triton_detect.py`` by path (it imports only torch and the stdlib)."""
    path = clone / "kernelgym" / "toolkit" / "kernelbench" / "triton_detect.py"
    spec = importlib.util.spec_from_file_location("_q1_upstream_triton_detect", path)
    if spec is None or spec.loader is None:
        raise NativeKernelGymError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_b_native(
    problem_source: str,
    kernel_source: str,
    *,
    clone: str | os.PathLike[str] | None = None,
    seed: int = 42,
    num_correct_trials: int = 5,
    num_perf_trials: int = 10,
    device: int = 0,
) -> GateOutcome:
    """Call upstream ``pipeline.eval_kernel_against_ref`` as the Dr. Kernel reward path does."""
    start = time.perf_counter()
    details: dict[str, Any] = {
        "kernelgym_revision": KERNELGYM_REVISION,
        "seed": seed,
        "num_correct_trials": num_correct_trials,
        "num_perf_trials": num_perf_trials,
    }
    try:
        root = resolve_clone(clone)
        pipeline = load_upstream_module(root, "pipeline")
        result = pipeline.eval_kernel_against_ref(
            problem_source,
            kernel_source,
            seed_num=seed,
            num_correct_trials=num_correct_trials,
            num_perf_trials=num_perf_trials,
            verbose=False,
            measure_performance=True,
            device=device,
            backend="triton",
            enable_profiling=True,
            enable_triton_detection=True,
        )
    except NativeKernelGymError:
        raise
    except Exception as exc:
        details.update({"reason": "upstream-raised", **exception_details(exc)})
        return GateOutcome(
            "b_native",
            f"native/seed-{seed}",
            "error",
            details=details,
            wall_seconds=time.perf_counter() - start,
        )
    if result is None:
        details["reason"] = "upstream-retry-signal"
        verdict = "error"
    else:
        metadata = dict(result.metadata)
        details.update(
            {
                "b0_correctness": bool(result.correctness),
                "compiled": bool(result.compiled),
                "decoy_kernel": bool(result.decoy_kernel),
                "b1_used": metadata.get("triton_profiler_used"),
                "b1_matches": [str(m) for m in metadata.get("triton_profiler_matches", [])][:50],
                "b2_num_custom_kernels": metadata.get("num_custom_kernels"),
                "b2_num_total_kernels": metadata.get("num_total_kernels"),
            }
        )
        verdict = "accept" if result.correctness and not result.decoy_kernel else "reject"
    return GateOutcome(
        "b_native",
        f"native/seed-{seed}",
        verdict,
        tolerance=1e-2,
        details=details,
        wall_seconds=time.perf_counter() - start,
    )
