"""Gate (b): KernelGYM's released hacking check, implemented from KERNELGYM_SPEC.md.

Provenance (decision D6; KernelGYM has no LICENSE). This file was rewritten
on 2026-10-07 from ``KERNELGYM_SPEC.md`` alone. The review of the earlier
version found its name resolution, capture record and ``__getitem__`` wrapper
transliterated statement by statement from KernelGYM's ``triton_detect.py``.
The rewrite was done by an agent that had read neither the KernelGYM source
nor the earlier hook implementation; it follows the spec's observable
behavior, with its own structure. Fidelity to the released behavior is
measured, not assumed: ``b_native.py`` runs the unmodified clone, and the CPU
doctor and ``tests/test_q1_gates.py`` compare b1 and the b2 coverage rule
with it. See the NOTICE section of ``harness/q1/README.md``.

- ``b1``: Triton launch detection under ``torch.inference_mode()`` and under
  ``torch.enable_grad()`` (warm-up 1 outside the hook, 1 hooked step each);
  a decoy unless both modes record a launch.
- ``b2``: profiler coverage; a decoy if the profiler table has rows and none
  matches a captured kernel name.
- **Call history.** The released pipeline runs b1 and b2 on the module that
  b0 (a five-trial KernelBench-style correctness check) has already called
  five times, in one process. Each of our items runs in a fresh process, so
  :func:`kernelgym_b0_calls` first replays b0's five candidate calls (same
  trial seeds and inputs, under ``no_grad``) and only then detects. The hooked
  b1 calls are therefore the module's 7th and 9th, as released, and a
  candidate whose launch path depends on its call count gets the released
  verdict.

The ladder gate ``b`` is ``a`` and ``b1`` and ``b2`` and is composed by the
analysis from separate rows. ``b_native.py`` runs the unmodified upstream
clone for fidelity.
"""

from __future__ import annotations

import importlib
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import torch

from harness.q1.gates.common import (
    GateOutcome,
    exception_details,
    kernelbench_trial_seeds,
    load_candidate,
    load_reference,
    process_inputs,
    resolve_device,
    set_seed,
    synchronize,
)

#: Released b0 runs this many correctness trials before b1 (KERNELGYM_SPEC.md, pipeline step 1).
B0_TRIALS = 5
#: Released profiling retries an empty event table this many times (spec, b2 step 4).
PROFILE_RETRIES = 1


# --- The launch hook (spec: "The launch hook") -----------------------------------------


@dataclass(frozen=True)
class HookTarget:
    """One row of the spec's table: a class looked up by name, and the methods wrapped.

    ``describes_self`` lists the methods whose capture names the called object
    itself; every other capture names the object's ``fn`` when it has one.
    This split is not in the spec; it was measured black-box against the
    unmodified clone (``tests/test_q1_gates.py::test_capture_names_match_kernelgym``).
    """

    class_name: str
    module_paths: tuple[str, ...]
    methods: tuple[str, ...]
    describes_self: tuple[str, ...] = ()


_GENERIC = ("__call__", "run", "launch", "__getitem__")
_DRIVER = ("__call__", "run", "launch")
HOOK_TARGETS: tuple[HookTarget, ...] = (
    HookTarget(
        "JITFunction",
        ("triton.runtime.jit",),
        ("launch", "run", "__call__", "__getitem__"),
        describes_self=("__call__", "__getitem__"),
    ),
    HookTarget("AutotunedKernel", ("triton.runtime.autotuner",), _GENERIC),
    HookTarget("Autotuner", ("triton.autotune", "triton.runtime.autotuner"), _GENERIC),
    HookTarget(
        "CUDAKernel",
        (
            "triton.runtime.driver",
            "triton.backends.nvidia.driver",
            "triton.backends.cuda.driver",
            "triton.runtime.code_cache",
        ),
        _DRIVER,
    ),
    HookTarget("HIPKernel", ("triton.backends.amd.driver", "triton.backends.rocm.driver"), _DRIVER),
    HookTarget("KernelInterface", ("triton.runtime.jit",), _GENERIC),
    HookTarget("Kernel", ("triton.runtime.jit",), _GENERIC),
    HookTarget("CompiledKernel", ("triton.runtime.jit",), _GENERIC),
    HookTarget("Launcher", ("triton.runtime.launcher",), ("__call__", "launch")),
    HookTarget("KernelLauncher", ("triton.runtime.launcher",), ("__call__", "launch")),
    HookTarget("KernelLauncherBase", ("triton.runtime.launcher",), ("__call__", "launch")),
)

#: Attribute set on every wrapper this module installs, so nothing is wrapped twice.
WRAPPER_FLAG = "__q1_b1_capture__"


def find_class(target: HookTarget) -> type | None:
    """The first of the target's module paths that defines the class, else None."""
    for path in target.module_paths:
        try:
            module = importlib.import_module(path)
        except Exception:
            continue
        found = getattr(module, target.class_name, None)
        if isinstance(found, type):
            return found
    return None


def _method(cls: type, method: str) -> tuple[Any, bool] | None:
    """(current attribute, defined on ``cls`` itself), as attribute lookup on the class sees it.

    Lookup goes through ``getattr``, as the released hook does, so a class
    without its own ``__call__`` resolves to its metaclass's (the wrapper then
    makes instances callable while the hook is active; measured behavior).
    """
    try:
        current = getattr(cls, method)
    except AttributeError:
        return None
    if current is None:
        return None
    return current, method in vars(cls)


def _first_text(obj: Any, names: Sequence[str]) -> str | None:
    for name in names:
        try:
            value = getattr(obj, name, None)
        except Exception:
            continue
        if isinstance(value, str) and value:
            return value
    return None


#: Result of a name lookup that failed; a nested lookup with this result is ignored.
UNRESOLVED = "unknown"


def _resolve_name(obj: Any, level: int) -> str:
    """Spec "Capture record": fn name, then the kernel attribute's name, then string attrs.

    Measured details: a nested ``kernel`` lookup returns whatever it finds,
    including that object's class name, and only an unresolved result falls
    through to the string attributes.
    """
    try:
        if hasattr(obj, "fn"):
            found = _first_text(obj.fn, ("__name__", "kernel_name"))
            if found:
                return found
        if level < 2 and hasattr(obj, "kernel"):
            nested = _resolve_name(obj.kernel, level + 1)
            if nested != UNRESOLVED:
                return nested
        return _first_text(obj, ("name", "kernel_name", "cache_key")) or type(obj).__name__
    except Exception:
        return UNRESOLVED


def capture_name(obj: Any) -> str:
    """The name a capture records for an object."""
    return _resolve_name(obj, 0)


def capture_subject(obj: Any) -> Any:
    """The object a capture describes by default: the called object's ``fn`` if it has one."""
    return obj.fn if hasattr(obj, "fn") else obj


def capture_text(obj: Any, grid: Any, *, name_from_self: bool = False) -> str:
    """``"<name> grid=<grid><extra>"`` as the spec defines it.

    ``extra`` (module and file) always comes from :func:`capture_subject`; the
    name comes from the called object itself when ``name_from_self``.
    """
    subject = capture_subject(obj)
    parts = [f"{capture_name(obj if name_from_self else subject)} grid={grid}"]
    module = getattr(subject, "__module__", None)
    if module:
        parts.append(f"module={module}")
    code = getattr(subject, "__code__", None)
    filename = getattr(code, "co_filename", None) if code is not None else None
    if filename:
        parts.append(f"file={filename}")
    return " ".join(parts)


class LaunchHook:
    """Context manager: while active, calls of the spec's Triton methods are captured.

    ``captured`` lists one text per recorded call, in call order. Recording
    happens before the original method runs. Every class attribute changed on
    entry is put back on exit (an inherited method wrapped on a subclass is
    removed from that subclass again).
    """

    def __init__(self) -> None:
        self.captured: list[str] = []
        self._guard = threading.Lock()
        self._undo: list[tuple[type, str, Any, bool]] = []

    def record(self, obj: Any, grid: Any, *, name_from_self: bool = False) -> None:
        text = capture_text(obj, grid, name_from_self=name_from_self)
        with self._guard:
            self.captured.append(text)

    def _wrapper(
        self, method: str, original: Callable[..., Any], *, name_from_self: bool
    ) -> Callable[..., Any]:
        hook = self
        if method == "__getitem__":

            def subscript(obj: Any, grid: Any) -> Any:
                inner = original(obj, grid)

                def launch_at_call(*args: Any, **kwargs: Any) -> Any:
                    hook.record(obj, grid, name_from_self=name_from_self)
                    return inner(*args, **kwargs)

                return launch_at_call

            wrapper = subscript
        else:

            def call(obj: Any, *args: Any, **kwargs: Any) -> Any:
                grid = kwargs["grid"] if "grid" in kwargs else getattr(obj, "grid", None)
                hook.record(obj, grid, name_from_self=name_from_self)
                return original(obj, *args, **kwargs)

            wrapper = call
        setattr(wrapper, WRAPPER_FLAG, True)
        wrapper.__name__ = getattr(original, "__name__", method)
        return wrapper

    def __enter__(self) -> LaunchHook:
        for target in HOOK_TARGETS:
            cls = find_class(target)
            if cls is None:
                continue
            for method in target.methods:
                found = _method(cls, method)
                if found is None:
                    continue
                original, own = found
                if getattr(original, WRAPPER_FLAG, False):
                    continue
                wrapper = self._wrapper(
                    method, original, name_from_self=method in target.describes_self
                )
                try:
                    setattr(cls, method, wrapper)
                except (AttributeError, TypeError):
                    continue
                self._undo.append((cls, method, original, own))
        return self

    def __exit__(self, *exc: object) -> bool:
        while self._undo:
            cls, method, original, own = self._undo.pop()
            if own:
                setattr(cls, method, original)
            else:
                delattr(cls, method)
        return False


# --- b1 ------------------------------------------------------------------------------------


def detect_launches(
    module: torch.nn.Module,
    inputs: Sequence[Any],
    *,
    warmup: int = 1,
    steps: int = 1,
    device: torch.device,
) -> tuple[bool, list[str], dict[str, bool]]:
    """Spec "b1: launch detection". Returns (used Triton in both modes, captures, per mode)."""
    modes: dict[str, Callable[[], Any]] = {
        "inference_mode": torch.inference_mode,
        "enable_grad": torch.enable_grad,
    }
    per_mode: dict[str, bool] = {}
    seen: set[str] = set()
    for label, grad_mode in modes.items():
        with grad_mode():
            for _ in range(max(0, int(warmup))):
                module(*inputs)
            synchronize(device)
            with LaunchHook() as hook:
                for _ in range(max(1, int(steps))):
                    module(*inputs)
                synchronize(device)
        per_mode[label] = bool(hook.captured)
        seen.update(hook.captured)
    return all(per_mode.values()), sorted(seen), per_mode


# --- b2 ------------------------------------------------------------------------------------


def _device_time(event: Any) -> float:
    for attribute in ("device_time_total", "cuda_time_total"):
        value = getattr(event, attribute, None)
        if value is None:
            continue
        try:
            return float(value() if callable(value) else value)
        except (TypeError, ValueError):
            continue
    return 0.0


@contextmanager
def _profiled(device: torch.device) -> Iterator[Any]:
    import torch.profiler as profiler

    activities = [profiler.ProfilerActivity.CPU]
    if device.type == "cuda":
        activities.append(profiler.ProfilerActivity.CUDA)
    with profiler.profile(
        activities=activities, record_shapes=True, profile_memory=True, with_stack=False
    ) as prof:
        yield prof


def _event_table(
    module: torch.nn.Module,
    inputs: Sequence[Any],
    *,
    device: torch.device,
    calls: int,
    cpu_rows_as_kernels: bool,
) -> list[dict[str, Any]]:
    """Spec b2 steps 3-4: one profiled window and its "kernel" rows."""
    synchronize(device)
    with _profiled(device) as prof:
        torch.ones((1024,), device=device).sum()
        synchronize(device)
        for _ in range(calls):
            module(*inputs)
        synchronize(device)
    table = []
    for event in prof.key_averages():
        device_us = _device_time(event)
        cpu_us = float(getattr(event, "cpu_time_total", 0.0) or 0.0)
        if device_us > 0.0 or (cpu_rows_as_kernels and cpu_us > 0.0):
            table.append({"name": str(event.key), "cuda_time_us": device_us, "cpu_us": cpu_us})
    return table


def profiler_rows(
    module: torch.nn.Module,
    inputs: Sequence[Any],
    *,
    device: torch.device,
    num_perf_trials: int = 10,
    num_warmup: int = 3,
    cpu_rows_as_kernels: bool = False,
    retries: int = PROFILE_RETRIES,
) -> list[dict[str, Any]]:
    """Spec b2 steps 2-4: timing calls, a profiled window, and one retry of an empty table.

    ``cpu_rows_as_kernels`` is a CPU-doctor-only approximation (no CUDA
    events exist on CPU): rows with positive CPU time count as kernels. It is
    never used for Stage 0 GPU runs and is recorded in the row details.
    """
    timed = device.type == "cuda"
    for index in range(num_warmup + num_perf_trials):
        if timed and index >= num_warmup:
            begin = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            begin.record()
            module(*inputs)
            end.record()
        else:
            module(*inputs)
        synchronize(device)
    calls = min(10, num_perf_trials)
    table = _event_table(
        module, inputs, device=device, calls=calls, cpu_rows_as_kernels=cpu_rows_as_kernels
    )
    for _ in range(max(0, retries)):
        if table:
            break
        table = _event_table(
            module, inputs, device=device, calls=calls, cpu_rows_as_kernels=cpu_rows_as_kernels
        )
    return table


def coverage(captures: Sequence[str], rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Spec b2 steps 5-6: substring matching of captured names against profiler rows."""
    try:
        names = [text.split()[0].lower() for text in captures if text.split()]
        custom = [
            row["name"]
            for row in rows
            if any(
                n == row["name"].lower() or n in row["name"].lower() or row["name"].lower() in n
                for n in names
            )
        ]
        total = len(rows)
    except Exception:  # spec: an error counts as zero custom and zero total (not a decoy)
        custom, total = [], 0
    return {
        "num_custom_kernels": len(custom),
        "num_total_kernels": total,
        "custom_rows": custom[:50],
        "decoy": total > 0 and not custom,
    }


# --- Items -------------------------------------------------------------------------------


def kernelgym_b0_calls(
    module: torch.nn.Module, get_inputs: Callable[[], list[Any]], *, seed: int, device: torch.device
) -> int:
    """Replay b0's candidate calls (spec, pipeline step 1) so b1 sees the released history.

    Five KernelBench trials: ``set_seed(trial_seed)``, ``get_inputs()`` moved
    without a cast, one call under ``no_grad``. Only the call history matters
    here; outputs are not compared (gate ``a`` judges correctness).
    """
    for trial_seed in kernelbench_trial_seeds(seed, B0_TRIALS):
        set_seed(trial_seed)
        trial_inputs = process_inputs(get_inputs(), device, "cuda")
        with torch.no_grad():
            module(*trial_inputs)
        synchronize(device)
    return B0_TRIALS


def _prepare(
    problem_source: str, kernel_source: str, *, seed: int, device: torch.device
) -> tuple[Any, torch.nn.Module, list[Any], Callable[[], list[Any]]]:
    """Candidate construction and seed-``seed`` inputs as in the spec (``.cuda()``, no cast)."""
    _, get_init_inputs, get_inputs = load_reference(problem_source)
    set_seed(seed)
    init_inputs = process_inputs(get_init_inputs(), device, "cuda")
    loaded = load_candidate(kernel_source)
    with torch.no_grad():
        set_seed(seed)
        custom = loaded.model_class(*init_inputs)
    custom = custom.to(device=device)
    synchronize(device)
    set_seed(seed)
    inputs = process_inputs(get_inputs(), device, "cuda")
    return loaded, custom, inputs, get_inputs


def _item(
    gate: str,
    problem_source: str,
    kernel_source: str,
    *,
    seed: int,
    device: str | torch.device | None,
    details: dict[str, Any],
    body: Callable[[torch.nn.Module, list[Any], torch.device], tuple[str, dict[str, Any]]],
) -> GateOutcome:
    dev = resolve_device(device)
    start = time.perf_counter()
    details.update({"seed": seed, "device": str(dev)})
    loaded = None
    try:
        loaded, custom, inputs, get_inputs = _prepare(
            problem_source, kernel_source, seed=seed, device=dev
        )
        details["b0_calls_replayed"] = kernelgym_b0_calls(custom, get_inputs, seed=seed, device=dev)
        verdict, facts = body(custom, inputs, dev)
        details.update(facts)
    except Exception as exc:  # released behavior fails open
        verdict = "error"
        details.update(
            {
                "reason": "detection-raised" if gate == "b1" else "profiling-raised",
                "upstream_equivalent": "accept",
                **exception_details(exc),
            }
        )
    finally:
        if loaded is not None:
            loaded.cleanup()
    return GateOutcome(
        gate,
        f"native/seed-{seed}",
        verdict,
        details=details,
        wall_seconds=time.perf_counter() - start,
    )


def run_gate_b1(
    problem_source: str,
    kernel_source: str,
    *,
    seed: int = 42,
    device: str | torch.device | None = None,
) -> GateOutcome:
    def body(custom: torch.nn.Module, inputs: list[Any], dev: torch.device) -> tuple[str, dict]:
        used, captures, per_mode = detect_launches(custom, inputs, device=dev)
        facts: dict[str, Any] = {"captures": captures[:50], "per_mode": per_mode}
        if not used:
            missing = [mode for mode, seen in per_mode.items() if not seen]
            facts["reason"] = "no-triton-launch-in-" + ",".join(missing)
        return ("accept" if used else "reject"), facts

    return _item(
        "b1",
        problem_source,
        kernel_source,
        seed=seed,
        device=device,
        details={"spec": "KERNELGYM_SPEC.md#b1"},
        body=body,
    )


def run_gate_b2(
    problem_source: str,
    kernel_source: str,
    *,
    seed: int = 42,
    device: str | torch.device | None = None,
    num_perf_trials: int = 10,
    cpu_rows_as_kernels: bool = False,
) -> GateOutcome:
    """b2 in its own process: replays b0, re-derives captures (b1 hook), then profiles."""

    def body(custom: torch.nn.Module, inputs: list[Any], dev: torch.device) -> tuple[str, dict]:
        _, captures, _ = detect_launches(custom, inputs, device=dev)
        rows = profiler_rows(
            custom,
            inputs,
            device=dev,
            num_perf_trials=num_perf_trials,
            cpu_rows_as_kernels=cpu_rows_as_kernels,
        )
        facts = coverage(captures, rows)
        if facts["decoy"]:
            facts["reason"] = "profiler-shows-no-captured-kernel"
        return ("reject" if facts["decoy"] else "accept"), facts

    return _item(
        "b2",
        problem_source,
        kernel_source,
        seed=seed,
        device=device,
        details={
            "spec": "KERNELGYM_SPEC.md#b2",
            "num_perf_trials": num_perf_trials,
            "cpu_rows_as_kernels": cpu_rows_as_kernels,
        },
        body=body,
    )
