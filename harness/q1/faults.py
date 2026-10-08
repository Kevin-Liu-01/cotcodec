"""GPU resource-failure text shared by the runner, the reference store and the gates.

Pure Python (no torch). One list, so the runner's contention rule
(``runner.contention_failure``), its health check (``runner.classify_health``)
and the reference store (``refstore.resource_failure``) can never disagree about
what a resource failure is (D31 review, finding 1).

A resource failure is an exception or log text that depends on what else holds
GPU or host memory at that moment: CUDA out-of-memory, and the cuBLAS, cuDNN,
cuFFT, cuSOLVER and cuSPARSE allocation failures (and the handle-creation and
internal errors cuBLAS and cuDNN report when their workspace cannot be
allocated). It is never a property of a kernel by itself: the runner retries a
shared item that shows one alone, and a reference item that meets one writes no
entry.
"""

from __future__ import annotations

from collections.abc import Iterable

#: Lower-case substrings of CUDA out-of-memory errors.
OOM_MARKERS: tuple[str, ...] = (
    "outofmemoryerror",
    "out of memory",
    "cudaerrormemoryallocation",
    "cuda_error_out_of_memory",
)

#: Lower-case substrings of library allocation and initialisation failures that
#: follow memory pressure (cuBLAS cannot create its handle or workspace; cuDNN
#: cannot allocate a workspace for any algorithm).
LIBRARY_RESOURCE_MARKERS: tuple[str, ...] = (
    "cublas_status_alloc_failed",
    "cublas_status_not_initialized",
    "cudnn_status_alloc_failed",
    "cudnn_status_internal_error",
    "cudnn_status_not_initialized",
    "unable to find a valid cudnn algorithm",
    "cufft_alloc_failed",
    "cusolver_status_alloc_failed",
    "cusparse_status_alloc_failed",
)

#: Host memory exhaustion (``MemoryError`` is matched by type as well).
HOST_MARKERS: tuple[str, ...] = ("cannot allocate memory", "memoryerror")

RESOURCE_MARKERS: tuple[str, ...] = OOM_MARKERS + LIBRARY_RESOURCE_MARKERS + HOST_MARKERS

#: Lower-case substrings of faults that a fresh process does not clear: the device
#: or driver is broken (Xid events, ECC, a GPU that fell off the bus) or absent.
DEVICE_FAULT_MARKERS: tuple[str, ...] = (
    "xid",
    "uncorrectable ecc",
    "ecc error",
    "fallen off the bus",
    "gpu is lost",
    "no cuda gpus are available",
    "cuda driver version is insufficient",
    "cudaerrornodevice",
    "cuda_error_no_device",
    "unknown error",
    "device-side assert",
    "illegal memory access",
    "unspecified launch failure",
    "launch timed out",
)


def is_resource_text(text: str) -> bool:
    """Whether ``text`` shows a resource failure (case-insensitive)."""
    lowered = text.lower()
    return any(marker in lowered for marker in RESOURCE_MARKERS)


def is_resource_exception(exc: BaseException) -> bool:
    return isinstance(exc, MemoryError) or is_resource_text(f"{type(exc).__name__}: {exc}")


def first_marker(text: str, markers: Iterable[str]) -> str | None:
    lowered = text.lower()
    return next((marker for marker in markers if marker in lowered), None)


__all__ = [
    "DEVICE_FAULT_MARKERS",
    "HOST_MARKERS",
    "LIBRARY_RESOURCE_MARKERS",
    "OOM_MARKERS",
    "RESOURCE_MARKERS",
    "first_marker",
    "is_resource_exception",
    "is_resource_text",
]
