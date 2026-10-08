"""Gate (a): the official KernelBench correctness check and its variants.

Primary ``a`` follows ``KernelBench@44130946 src/eval.py``
(``eval_kernel_against_ref`` + ``run_and_check_correctness``) with
``num_correct_trials=5, seed_num=42, backend="triton"``: atol = rtol = 1e-2,
inputs moved to the device without a dtype cast (integer targets keep their
dtype), models left in training mode, the same input objects passed to the
reference and then to the candidate, and every trial required to pass.

The transcription below is device-generic so it also runs on CPU tensors. Its
fidelity to the verbatim vendored upstream (``third_party/kernelbench``) is
tested by ``upstream_gate_a`` (GPU) and by the CPU differential in the tests.

Variants (secondary gates, preregistered):

| gate | code | inputs | tolerance |
|---|---|---|---|
| ``a`` | 44130946 | preserve dtypes | 1e-2 |
| ``a_1e-3`` | 44130946 | preserve dtypes | 1e-3 (tolerance-matched to gate c) |
| ``a_head_1e-4`` | 423217d9 | every tensor cast to fp32 | 1e-4 (HEAD default) |
| ``a_head_1e-2`` | 423217d9 | every tensor cast to fp32 | 1e-2 |
| ``a_static`` | ``a`` and HEAD ``validate_kernel_static`` | | |

A reference that raises (for example L1/95 CrossEntropy under the HEAD fp32
cast) makes the item unrefereeable: verdict ``error`` with
``details.reason = "reference-raised"``; upstream would report the candidate
incorrect, recorded as ``details.upstream_equivalent``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import torch

from harness.q1.gates.common import (
    GateOutcome,
    allclose_compare,
    exception_details,
    kernelbench_trial_seeds,
    load_candidate,
    load_reference,
    process_inputs,
    resolve_device,
    set_seed,
    synchronize,
)


@dataclass(frozen=True)
class GateAVariant:
    gate: str
    revision: str
    cast_mode: str
    tolerance: float
    cast_models_to_fp32: bool
    static_check: bool = False


VARIANTS: dict[str, GateAVariant] = {
    "a": GateAVariant("a", "44130946", "preserve", 1e-2, False),
    "a_1e-3": GateAVariant("a_1e-3", "44130946", "preserve", 1e-3, False),
    "a_head_1e-4": GateAVariant("a_head_1e-4", "423217d9", "fp32", 1e-4, True),
    "a_head_1e-2": GateAVariant("a_head_1e-2", "423217d9", "fp32", 1e-2, True),
    "a_static": GateAVariant("a_static", "44130946+423217d9-static", "preserve", 1e-2, False, True),
}


def static_check(kernel_source: str) -> tuple[bool, list[str], list[str]]:
    """HEAD ``kernel_static_checker.validate_kernel_static`` (Triton, fp32)."""
    from harness.q1.third_party.kernelbench.kb_423217d9 import kernel_static_checker

    valid, errors, warnings = kernel_static_checker.validate_kernel_static(
        kernel_source, backend="triton", precision="fp32"
    )
    return bool(valid), list(errors), list(warnings)


def run_gate_a(
    problem_source: str,
    kernel_source: str,
    *,
    variant: str = "a",
    seed: int = 42,
    num_trials: int = 5,
    device: str | torch.device | None = None,
    config_id: str | None = None,
) -> GateOutcome:
    """Run one gate (a) variant on a candidate in this process."""
    spec = VARIANTS[variant]
    dev = resolve_device(device)
    config_id = config_id or f"native/trials-{num_trials}/seed-{seed}"
    start = time.perf_counter()
    details: dict[str, Any] = {
        "revision": spec.revision,
        "cast_mode": spec.cast_mode,
        "num_trials": num_trials,
        "seed": seed,
        "device": str(dev),
    }

    def outcome(verdict: str, **extra: Any) -> GateOutcome:
        details.update(extra.pop("details", {}))
        return GateOutcome(
            gate=spec.gate,
            config_id=config_id,
            verdict=verdict,
            tolerance=spec.tolerance,
            details=details,
            wall_seconds=time.perf_counter() - start,
            **extra,
        )

    if spec.static_check:
        valid, errors, warnings = static_check(kernel_source)
        details["static_errors"] = errors
        details["static_warnings"] = warnings
        if not valid:
            return outcome("reject", details={"reason": "static-check"})

    model_dtype = torch.float32 if spec.cast_models_to_fp32 else None
    Model, get_init_inputs, get_inputs = load_reference(problem_source)
    set_seed(seed)
    init_inputs = process_inputs(get_init_inputs(), dev, spec.cast_mode)
    with torch.no_grad():
        set_seed(seed)
        original = Model(*init_inputs)

    try:
        loaded = load_candidate(kernel_source)
        synchronize(dev)
    except Exception as exc:  # compilation failure, as upstream records it
        return outcome("reject", details={"reason": "compile-failure", **exception_details(exc)})

    try:
        try:
            with torch.no_grad():
                set_seed(seed)
                custom = loaded.model_class(*init_inputs)
                original = original.to(device=dev, dtype=model_dtype)
                custom = custom.to(device=dev, dtype=model_dtype)
                synchronize(dev)
        except Exception as exc:
            # Upstream catches only RuntimeError here and lets other exceptions
            # escape the harness; either way the candidate does not pass.
            return outcome(
                "reject",
                details={
                    "reason": "load-failure",
                    "upstream_equivalent": "reject"
                    if isinstance(exc, RuntimeError)
                    else "harness-exception",
                    **exception_details(exc),
                },
            )
        return _trials(
            original,
            custom,
            get_inputs,
            spec=spec,
            seed=seed,
            num_trials=num_trials,
            device=dev,
            model_dtype=model_dtype,
            outcome=outcome,
        )
    finally:
        loaded.cleanup()


def _trials(
    original: torch.nn.Module,
    custom: torch.nn.Module,
    get_inputs: Any,
    *,
    spec: GateAVariant,
    seed: int,
    num_trials: int,
    device: torch.device,
    model_dtype: torch.dtype | None,
    outcome: Any,
) -> GateOutcome:
    trial_seeds = kernelbench_trial_seeds(seed, num_trials)
    passes = 0
    max_abs: list[float | None] = []
    max_rel: list[float | None] = []
    failed_trials: list[int] = []
    with torch.no_grad():
        for trial, trial_seed in enumerate(trial_seeds):
            set_seed(trial_seed)
            inputs = process_inputs(get_inputs(), device, spec.cast_mode)
            set_seed(trial_seed)
            model = original.to(device=device, dtype=model_dtype)
            set_seed(trial_seed)
            model_new = custom.to(device=device, dtype=model_dtype)
            try:
                output = model(*inputs)
                synchronize(device)
            except Exception as exc:
                return outcome(
                    "error",
                    details={
                        "reason": "reference-raised",
                        "upstream_equivalent": "reject",
                        "trial": trial,
                        "trial_seeds": trial_seeds,
                        **exception_details(exc),
                    },
                )
            try:
                output_new = model_new(*inputs)
                synchronize(device)
                comparison = allclose_compare(output_new, output, spec.tolerance, spec.tolerance)
            except Exception as exc:
                return outcome(
                    "reject",
                    details={
                        "reason": "runtime-error",
                        "trial": trial,
                        "trial_seeds": trial_seeds,
                        **exception_details(exc),
                    },
                )
            if comparison.max_abs_err is None:  # shape mismatch returns at once
                return outcome(
                    "reject",
                    details={
                        "reason": "shape-mismatch",
                        "message": comparison.reason,
                        "trial": trial,
                        "trial_seeds": trial_seeds,
                    },
                )
            max_abs.append(comparison.max_abs_err)
            max_rel.append(comparison.max_rel_err)
            if comparison.passed:
                passes += 1
            else:
                failed_trials.append(trial)
    abs_err = max((v for v in max_abs if v is not None), default=None)
    rel_err = max((v for v in max_rel if v is not None), default=None)
    verdict = "accept" if passes == num_trials else "reject"
    return outcome(
        verdict,
        max_abs_err=abs_err,
        max_rel_err=rel_err,
        details={
            "correctness_trials": f"({passes} / {num_trials})",
            "failed_trials": failed_trials,
            "trial_seeds": trial_seeds,
            "reason": "" if verdict == "accept" else "output-mismatch",
        },
    )


def upstream_gate_a(
    problem_source: str,
    kernel_source: str,
    *,
    revision: str = "44130946",
    seed: int = 42,
    num_trials: int = 5,
    device: int = 0,
    backend: str = "triton",
) -> dict[str, Any]:
    """Run the verbatim vendored upstream ``eval_kernel_against_ref`` (CUDA only).

    Used for the fidelity differential; returns the upstream result as a dict
    with ``correctness``, ``compiled`` and stringified ``metadata``.
    """
    if revision == "44130946":
        from harness.q1.third_party.kernelbench.kb_44130946 import eval as upstream

        result = upstream.eval_kernel_against_ref(
            problem_source,
            kernel_source,
            seed_num=seed,
            num_correct_trials=num_trials,
            measure_performance=False,
            device=device,
            backend=backend,
        )
    elif revision == "423217d9":
        from harness.q1.third_party.kernelbench.kb_423217d9 import eval as upstream

        result = upstream.eval_kernel_against_ref(
            problem_source,
            kernel_source,
            seed_num=seed,
            num_correct_trials=num_trials,
            measure_performance=False,
            device=device,
            backend=backend,
            precision=torch.float32,
        )
    else:
        raise ValueError(f"unknown KernelBench revision {revision}")
    if result is None:  # upstream's lock-file retry signal
        return {"compiled": None, "correctness": None, "metadata": {"retry": True}}
    return {
        "compiled": bool(result.compiled),
        "correctness": bool(result.correctness),
        "metadata": {key: str(value)[:2000] for key, value in result.metadata.items()},
    }


def upstream_run_and_check_correctness_cpu(
    problem_source: str, kernel_source: str, *, seed: int = 42, num_trials: int = 5
) -> bool:
    """Call the verbatim 44130946 ``run_and_check_correctness`` on CPU tensors.

    Upstream calls ``torch.cuda.synchronize``; on a CPU-only process this is
    replaced by a no-op for the duration of the call (the only change). Model
    construction mirrors ``eval_kernel_against_ref``. Used by the CPU
    differential test of the transcription above.
    """
    from harness.q1.third_party.kernelbench.kb_44130946 import eval as upstream

    Model, get_init_inputs, get_inputs = load_reference(problem_source)
    upstream.set_seed(seed)
    init_inputs = get_init_inputs()
    with torch.no_grad():
        upstream.set_seed(seed)
        original = Model(*init_inputs)
    loaded = load_candidate(kernel_source)
    original_sync = torch.cuda.synchronize
    try:
        with torch.no_grad():
            upstream.set_seed(seed)
            custom = loaded.model_class(*init_inputs)
        torch.cuda.synchronize = lambda *args, **kwargs: None
        result = upstream.run_and_check_correctness(
            original,
            custom,
            get_inputs,
            metadata={},
            num_correct_trials=num_trials,
            seed=seed,
            device=torch.device("cpu"),
            backend="triton",
        )
        return bool(result.correctness)
    finally:
        torch.cuda.synchronize = original_sync
        loaded.cleanup()
