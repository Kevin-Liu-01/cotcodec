"""A4: tolerance-free contracts (adapted from lethe's ORD-02 idea, reimplemented).

- **determinism**: five calls on byte-identical inputs give byte-identical
  outputs (compared as raw bytes, so NaN payloads compare too);
- **no reuse, no aliasing**: the five live outputs occupy distinct storage,
  and no output shares storage with any input;
- **input immutability**: every input is byte-identical after each call;
- **dual poison**: outputs are byte-identical when fresh allocations are
  filled with 0x00 and with 0xFF. Two mechanisms: ``factory`` patches
  ``torch.empty``/``empty_like``/``empty_strided``/``Tensor.new_empty`` in the
  candidate's process (CPU and GPU); ``allocator`` loads
  ``poison_alloc.so`` as a ``CUDAPluggableAllocator`` in a fresh process (GPU
  only; every CUDA allocation is memset, so the caching allocator cannot hand
  back stale bytes);
- **compute-sanitizer**: ``compute-sanitizer --tool memcheck`` on one call at
  the smallest A3 shape (GPU only; command built by :func:`sanitizer_command`);
- **watchdog**: enforced by the runner (a timeout is an A4 failure).
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import torch

from harness.q1.gates.common import first_tensor_outputs, synchronize

POISON_BYTES = (0x00, 0xFF)
SANITIZER_EXIT_CODE = 86


def tensor_bytes(t: torch.Tensor) -> bytes:
    t = t.detach().contiguous().cpu()
    if t.numel() == 0:
        return b""
    return t.reshape(-1).view(torch.uint8).numpy().tobytes()


def _snapshot(values: Sequence[Any]) -> list[bytes | None]:
    return [tensor_bytes(v) if isinstance(v, torch.Tensor) else None for v in values]


def _clone_inputs(values: Sequence[Any]) -> list[Any]:
    return [v.clone() if isinstance(v, torch.Tensor) else v for v in values]


def _storage_span(t: torch.Tensor) -> tuple[int, int]:
    storage = t.untyped_storage()
    start = storage.data_ptr()
    return start, start + storage.nbytes()


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1] and a[0] != a[1] and b[0] != b[1]


@dataclass
class ContractResult:
    name: str
    passed: bool | None  # None = not run on this device
    details: dict[str, Any] = field(default_factory=dict)


def check_determinism_and_aliasing(
    candidate: torch.nn.Module,
    inputs: Sequence[Any],
    *,
    device: torch.device,
    runs: int = 5,
) -> list[ContractResult]:
    """determinism, no-reuse/no-aliasing and input-immutability in one pass."""
    reference_bytes = _snapshot(inputs)
    live_outputs: list[list[torch.Tensor]] = []
    live_inputs: list[list[Any]] = []
    output_bytes: list[list[bytes]] = []
    mutated: list[int] = []
    with torch.no_grad():
        for run in range(runs):
            run_inputs = _clone_inputs(inputs)
            outputs = first_tensor_outputs(candidate(*run_inputs))
            synchronize(device)
            if _snapshot(run_inputs) != reference_bytes:
                mutated.append(run)
            live_inputs.append(run_inputs)
            live_outputs.append(outputs)
            output_bytes.append([tensor_bytes(o) for o in outputs])
    deterministic = all(b == output_bytes[0] for b in output_bytes[1:])
    spans = [[_storage_span(o) for o in outs if o.numel() > 0] for outs in live_outputs]
    reuse = any(
        _overlaps(a, b)
        for i in range(runs)
        for j in range(i + 1, runs)
        for a in spans[i]
        for b in spans[j]
    )
    aliasing = any(
        _overlaps(span, _storage_span(x))
        for run in range(runs)
        for span in spans[run]
        for x in live_inputs[run]
        if isinstance(x, torch.Tensor) and x.numel() > 0
    )
    return [
        ContractResult("determinism", deterministic, {"runs": runs}),
        ContractResult("no_output_reuse", not reuse, {}),
        ContractResult("no_input_aliasing", not aliasing, {}),
        ContractResult("inputs_unmodified", not mutated, {"mutated_runs": mutated}),
    ]


@contextlib.contextmanager
def factory_poison(byte: int) -> Iterator[None]:
    """Fill every tensor from the ``empty`` factories with ``byte`` (both devices)."""
    originals: dict[str, Callable[..., torch.Tensor]] = {
        "empty": torch.empty,
        "empty_like": torch.empty_like,
        "empty_strided": torch.empty_strided,
    }
    original_new_empty = torch.Tensor.new_empty

    def poisoned(fn: Callable[..., torch.Tensor]) -> Callable[..., torch.Tensor]:
        def wrapper(*args: Any, **kwargs: Any) -> torch.Tensor:
            out = fn(*args, **kwargs)
            if out.numel() > 0:
                with torch.no_grad():
                    out.untyped_storage().fill_(byte)
            return out

        return wrapper

    try:
        for name, fn in originals.items():
            setattr(torch, name, poisoned(fn))
        torch.Tensor.new_empty = poisoned(original_new_empty)  # type: ignore[method-assign]
        yield
    finally:
        for name, fn in originals.items():
            setattr(torch, name, fn)
        torch.Tensor.new_empty = original_new_empty  # type: ignore[method-assign]


def check_factory_poison(
    candidate: torch.nn.Module, inputs: Sequence[Any], *, device: torch.device
) -> ContractResult:
    results: list[list[bytes]] = []
    with torch.no_grad():
        for byte in POISON_BYTES:
            with factory_poison(byte):
                outputs = first_tensor_outputs(candidate(*_clone_inputs(inputs)))
                synchronize(device)
            results.append([tensor_bytes(o) for o in outputs])
    same = results[0] == results[1]
    return ContractResult("dual_poison_factory", same, {"bytes": list(POISON_BYTES)})


def poison_allocator_env(byte: int, so_path: str) -> dict[str, str]:
    """Environment for a worker that installs the pluggable poison allocator."""
    return {"Q1_POISON_BYTE": str(byte), "Q1_POISON_ALLOC_SO": so_path}


def install_poison_allocator_from_env() -> int | None:
    """Call at worker start-up, before any CUDA allocation. Returns the byte or None."""
    byte = os.environ.get("Q1_POISON_BYTE")
    so_path = os.environ.get("Q1_POISON_ALLOC_SO")
    if byte is None or so_path is None:
        return None
    value = int(byte)
    os.environ["Q1_POISON_VALUE"] = str(value)
    allocator = torch.cuda.memory.CUDAPluggableAllocator(
        so_path, "q1_poison_malloc", "q1_poison_free"
    )
    torch.cuda.memory.change_current_allocator(allocator)
    return value


def sanitizer_command(
    worker_argv: Sequence[str], executable: str = "compute-sanitizer"
) -> list[str]:
    """Wrap a worker command in ``compute-sanitizer --tool memcheck``."""
    return [
        executable,
        "--tool",
        "memcheck",
        "--error-exitcode",
        str(SANITIZER_EXIT_CODE),
        "--print-limit",
        "20",
        "--target-processes",
        "all",
        *worker_argv,
    ]


def interpret_sanitizer(returncode: int) -> ContractResult:
    if returncode == 0:
        return ContractResult("compute_sanitizer", True, {"returncode": 0})
    if returncode == SANITIZER_EXIT_CODE:
        return ContractResult("compute_sanitizer", False, {"returncode": returncode})
    return ContractResult(
        "compute_sanitizer", None, {"returncode": returncode, "reason": "sanitizer-did-not-run"}
    )
