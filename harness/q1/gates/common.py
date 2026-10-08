"""Shared machinery for Q1 gates: loading, seeding, input processing, comparison.

Every helper here mirrors a specific upstream behavior, named in its
docstring, so gate semantics can be checked line by line against the pinned
sources. Gates are device-generic: the same code runs on CUDA (Stage 0 runs)
and on CPU tensors (the CPU doctor, unit tests, Triton interpreter mode).
"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from harness.q1.gates.outcome import (  # noqa: F401 - re-exported
    PHASE_FD_ENV,
    PHASES,
    GateOutcome,
    channel_seed,
    combine,
    exception_details,
    report_phase,
    worst,
)


def set_seed(seed: int) -> None:
    """KernelBench/KernelGYM ``set_seed``: CPU and current-CUDA-device generators."""
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)


def kernelbench_trial_seeds(seed: int, num_trials: int) -> list[int]:
    """Trial seeds exactly as KernelBench@44130946 ``run_and_check_correctness``."""
    torch.manual_seed(seed)
    return [int(torch.randint(0, 2**32 - 1, (1,)).item()) for _ in range(num_trials)]


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
    makes both errors ``inf``. Computed in fp64 in chunks on the tensors'
    device (``gates.reductions``; the same numbers as a host fp64 copy).
    """
    from harness.q1.gates.reductions import error_stats as chunked

    return chunked(output, reference)


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
