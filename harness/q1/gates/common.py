"""Shared machinery for Q1 gates: loading, seeding, input processing, comparison.

Every helper here mirrors a specific upstream behavior, named in its
docstring, so gate semantics can be checked line by line against the pinned
sources. Gates are device-generic: the same code runs on CUDA (Stage 0 runs)
and on CPU tensors (the CPU doctor, unit tests, Triton interpreter mode).
"""

from __future__ import annotations

import contextlib
import importlib.util
import math
import os
import sys
import tempfile
import time
import traceback
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

from harness.q1.schema import make_verdict_row

PHASE_FD_ENV = "Q1_PHASE_FD"
PHASES = ("compile", "correctness", "timing")


def report_phase(name: str) -> None:
    """Tell the runner's watchdog which phase this worker entered.

    Writes ``<name>\n`` to the file descriptor in ``Q1_PHASE_FD`` when set
    (a pipe owned by the runner). Phases only move forward; the runner caps
    each at its own timeout, so a candidate that forges a phase message can at
    most move to a later phase with a bounded limit.
    """
    if name not in PHASES:
        raise ValueError(f"unknown phase {name}")
    fd = os.environ.get(PHASE_FD_ENV)
    if fd is None:
        return
    with contextlib.suppress(OSError):
        os.write(int(fd), f"{name}\n".encode())


def set_seed(seed: int) -> None:
    """KernelBench/KernelGYM ``set_seed``: CPU and current-CUDA-device generators."""
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)


def kernelbench_trial_seeds(seed: int, num_trials: int) -> list[int]:
    """Trial seeds exactly as KernelBench@44130946 ``run_and_check_correctness``."""
    torch.manual_seed(seed)
    return [int(torch.randint(0, 2**32 - 1, (1,)).item()) for _ in range(num_trials)]


def channel_seed(base: int, replicate_seed: int, index: int) -> int:
    """Seed for input draw ``index`` of a gate or audit channel.

    ``base`` is the channel's seed at replicate 42 and index 0 (c1: 1042, c2:
    2042, c3: 3042, A2: 4042, A3: 5042, A1 native draws: 6042, A5: 7042).
    Replicates 43 and 44 shift by 100, so draws never collide while index < 100.
    """
    if not 0 <= index < 100:
        raise ValueError("channel draw index must be in [0, 100)")
    return base + index + 100 * (replicate_seed - 42)


def synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device=device)


def resolve_device(device: str | int | torch.device | None) -> torch.device:
    if device is None:
        return torch.device("cuda", 0) if torch.cuda.is_available() else torch.device("cpu")
    if isinstance(device, int):
        return torch.device("cuda", device)
    return torch.device(device)


# --- Loading ---------------------------------------------------------------------


def load_reference(source: str) -> tuple[type, Callable[[], list], Callable[[], list]]:
    """KernelBench ``load_original_model_and_inputs``: ``exec`` into a fresh dict."""
    context: dict[str, Any] = {}
    compile(source, "<string>", "exec")
    exec(source, context)  # noqa: S102 - hashed KernelBench problem source
    return context["Model"], context["get_init_inputs"], context["get_inputs"]


@dataclass
class LoadedCandidate:
    model_class: type
    module_name: str
    tempfile_path: Path

    def cleanup(self) -> None:
        sys.modules.pop(self.module_name, None)
        with contextlib.suppress(FileNotFoundError):
            self.tempfile_path.unlink()


def load_candidate(source: str, entry_point: str = "ModelNew") -> LoadedCandidate:
    """KernelBench ``load_custom_model_with_tempfile`` (Triton backend).

    The source is written to a fresh ``.py`` temp file and imported under the
    module name ``temp_module``, as upstream does, so ``@triton.jit`` can read
    its source. Each load gets a fresh module object.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as handle:
        handle.write(source)
    path = Path(handle.name)
    spec = importlib.util.spec_from_file_location("temp_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import candidate from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    loaded = LoadedCandidate(getattr(module, entry_point), "temp_module", path)
    report_phase("correctness")
    return loaded


# --- Input processing ----------------------------------------------------------

#: How each upstream moves inputs to the device.
#: ``preserve``: KernelBench@44130946 (``.to(device)``, no cast, ints kept).
#: ``fp32``: KernelBench HEAD and KBV (every tensor cast to fp32, ints included).
#: ``cuda``: KernelGYM (``.cuda()``/``.to(device)``, no cast).
CAST_MODES = ("preserve", "fp32", "cuda")


def process_input(value: Any, device: torch.device, cast_mode: str) -> Any:
    if cast_mode not in CAST_MODES:
        raise ValueError(f"unknown cast mode {cast_mode}")
    if not isinstance(value, torch.Tensor):
        return value
    if cast_mode == "fp32":
        value = value.to(dtype=torch.float32)
    return value.to(device=device)


def process_inputs(values: Sequence[Any], device: torch.device, cast_mode: str) -> list[Any]:
    return [process_input(value, device, cast_mode) for value in values]


def scale_float_inputs(values: Sequence[Any], factor: float) -> list[Any]:
    """KBV ``_scale``: multiply floating tensors by ``factor``; leave the rest."""
    return [
        value * factor if isinstance(value, torch.Tensor) and value.is_floating_point() else value
        for value in values
    ]


# --- Comparison ------------------------------------------------------------------


@dataclass(frozen=True)
class Comparison:
    passed: bool
    max_abs_err: float | None
    max_rel_err: float | None
    reason: str = ""


def error_stats(output: torch.Tensor, reference: torch.Tensor) -> tuple[float, float]:
    """Max absolute and relative error over positions where both are finite.

    Relative error divides by ``|reference|`` and skips exact-zero references.
    A non-finite mismatch (NaN or infinity where the other side differs)
    makes both errors ``inf``.
    """
    out = output.detach().to("cpu", torch.float64)
    ref = reference.detach().to("cpu", torch.float64)
    if out.shape != ref.shape:
        return math.inf, math.inf
    if out.numel() == 0:
        return 0.0, 0.0
    both_finite = torch.isfinite(out) & torch.isfinite(ref)
    same_nonfinite = (torch.isnan(out) & torch.isnan(ref)) | (
        torch.isinf(out) & torch.isinf(ref) & (torch.sign(out) == torch.sign(ref))
    )
    if bool((~both_finite & ~same_nonfinite).any()):
        return math.inf, math.inf
    if not bool(both_finite.any()):
        return 0.0, 0.0
    diff = (out - ref).abs()[both_finite]
    denom = ref.abs()[both_finite]
    nonzero = denom > 0
    max_rel = float((diff[nonzero] / denom[nonzero]).max()) if bool(nonzero.any()) else 0.0
    return float(diff.max()), max_rel


def allclose_compare(output: Any, reference: Any, atol: float, rtol: float) -> Comparison:
    """``torch.allclose(reference, output, atol, rtol)`` as KernelBench calls it.

    Shape mismatch fails first (KernelBench checks shapes before values). Any
    exception from ``allclose`` (dtype mismatch, non-tensor output) propagates
    to the caller, which treats it as a candidate runtime error, as upstream.
    """
    if output.shape != reference.shape:
        return Comparison(
            False,
            None,
            None,
            f"Output shape mismatch: Expected {tuple(reference.shape)}, got {tuple(output.shape)}",
        )
    passed = bool(torch.allclose(reference, output, atol=atol, rtol=rtol))
    max_abs, max_rel = error_stats(output, reference)
    return Comparison(passed, max_abs, max_rel, "" if passed else "Output mismatch")


# --- Outcomes and rows -------------------------------------------------------------


@dataclass
class GateOutcome:
    gate: str
    config_id: str
    verdict: str
    max_abs_err: float | None = None
    max_rel_err: float | None = None
    tolerance: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    wall_seconds: float = 0.0

    def to_row(
        self,
        kernel_id: str,
        *,
        tf32_policy: str = "torch-default",
        gpu_seconds: float | None = None,
        **optional: Any,
    ) -> dict[str, Any]:
        return make_verdict_row(
            kernel_id=kernel_id,
            gate=self.gate,
            config_id=self.config_id,
            verdict=self.verdict,
            tf32_policy=tf32_policy,
            max_abs_err=self.max_abs_err,
            max_rel_err=self.max_rel_err,
            tolerance=self.tolerance,
            gpu_seconds=self.wall_seconds if gpu_seconds is None else gpu_seconds,
            wall_seconds=self.wall_seconds,
            details=self.details,
            **optional,
        )


def worst(values: Sequence[float | None]) -> float | None:
    finite = [v for v in values if v is not None]
    if any(v is not None and math.isinf(v) for v in values):
        return math.inf
    return max(finite) if finite else None


def combine(gate: str, config_id: str, parts: Sequence[GateOutcome]) -> GateOutcome:
    """Conjunction of component outcomes.

    Order of precedence: any ``reject`` rejects; otherwise any ``timeout``
    times out; otherwise any ``error`` errors; otherwise any ``refuse``
    refuses; otherwise accept.
    """
    verdicts = [part.verdict for part in parts]
    for verdict in ("reject", "timeout", "error", "refuse"):
        if verdict in verdicts:
            break
    else:
        verdict = "accept"
    return GateOutcome(
        gate=gate,
        config_id=config_id,
        verdict=verdict,
        max_abs_err=worst([part.max_abs_err for part in parts]),
        max_rel_err=worst([part.max_rel_err for part in parts]),
        tolerance=None,
        details={"components": {part.gate: part.verdict for part in parts}},
        wall_seconds=sum(part.wall_seconds for part in parts),
    )


def exception_details(exc: BaseException, limit: int = 2000) -> dict[str, str]:
    text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    return {
        "error_name": f"{type(exc).__module__}.{type(exc).__name__}",
        "error": text[:limit],
    }


@contextmanager
def timed() -> Iterator[list[float]]:
    holder = [0.0]
    start = time.perf_counter()
    try:
        yield holder
    finally:
        holder[0] = time.perf_counter() - start


@contextmanager
def env_var(name: str, value: str | None) -> Iterator[None]:
    old = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


def first_tensor_outputs(output: Any) -> list[torch.Tensor]:
    """Flatten a model output into its tensors (tuples and lists are walked)."""
    if isinstance(output, torch.Tensor):
        return [output]
    if isinstance(output, tuple | list):
        tensors: list[torch.Tensor] = []
        for item in output:
            tensors.extend(first_tensor_outputs(item))
        return tensors
    raise TypeError(f"model output of type {type(output).__name__} holds no tensor")
