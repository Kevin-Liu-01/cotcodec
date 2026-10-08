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
    problem_id: str | None = None,
    reference_store: str | None = None,
) -> GateOutcome:
    """Run one gate (a) variant on a candidate in this process.

    With ``reference_store`` (and ``problem_id``), the reference outputs of the five
    trials are read from the store entry a reference item wrote for this problem,
    replicate and variant family (``harness.q1.refstore``, decision D31) instead of
    being recomputed; without a usable entry they are computed here as always."""
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
        stored = None
        if reference_store and problem_id:
            from harness.q1 import refstore

            stored = refstore.lookup(
                reference_store,
                reference_payload(
                    problem_id,
                    problem_source,
                    variant=variant,
                    seed=seed,
                    num_trials=num_trials,
                    device=dev,
                ),
                draws=num_trials,
                ends_at_raise=True,
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
            stored=stored,
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
    stored: Any = None,
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
            record = stored.take(trial, device) if stored is not None else None
            if record is None:
                stored = None
                try:
                    output = model(*inputs)
                    synchronize(device)
                except Exception as exc:
                    return _reference_raised(outcome, trial, trial_seeds, exception_details(exc))
            elif record.kind == "raised":
                return _reference_raised(outcome, trial, trial_seeds, record.error)
            else:
                output = record.value
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


def _reference_raised(
    outcome: Any, trial: int, trial_seeds: list[int], error: dict[str, str]
) -> GateOutcome:
    return outcome(
        "error",
        details={
            "reason": "reference-raised",
            "upstream_equivalent": "reject",
            "trial": trial,
            "trial_seeds": trial_seeds,
            **error,
        },
    )


# --- reference store (decision D31) ---------------------------------------------------


def reference_channel(variant: str) -> str:
    """Store channel of a variant: ``a`` (44130946 semantics, no cast; ``a``,
    ``a_1e-3``, ``a_static``) or ``a_head`` (423217d9, fp32 cast; both HEAD variants)."""
    return "a_head" if VARIANTS[variant].cast_models_to_fp32 else "a"


def reference_payload(
    problem_id: str,
    problem_source: str,
    *,
    variant: str,
    seed: int,
    num_trials: int,
    device: torch.device,
) -> dict[str, Any]:
    from harness.q1 import refstore

    spec = VARIANTS[variant]
    return refstore.key_payload(
        reference_channel(variant),
        problem_id=problem_id,
        problem_source=problem_source,
        seed=seed,
        device_type=device.type,
        params={
            "cast_mode": spec.cast_mode,
            "cast_models_to_fp32": spec.cast_models_to_fp32,
            "num_trials": int(num_trials),
        },
    )


def reference_trials(
    problem_source: str,
    *,
    variant: str,
    seed: int,
    num_trials: int,
    device: torch.device,
) -> Any:
    """The reference side of :func:`run_gate_a` and ``_trials``, without a candidate:
    the same construction (``set_seed(seed)`` before the inputs and the model), the
    same move, and per trial the same seeds, draw and reference call. A trial
    whose reference raises is stored as raised and ends the list, as it ends the
    gate."""
    from harness.q1 import refstore

    spec = VARIANTS[variant]
    model_dtype = torch.float32 if spec.cast_models_to_fp32 else None
    Model, get_init_inputs, get_inputs = load_reference(problem_source)
    set_seed(seed)
    init_inputs = process_inputs(get_init_inputs(), device, spec.cast_mode)
    with torch.no_grad():
        set_seed(seed)
        original = Model(*init_inputs)
        original = original.to(device=device, dtype=model_dtype)
        synchronize(device)
    built = refstore.Built(draws=[])
    trial_seeds = kernelbench_trial_seeds(seed, num_trials)
    with torch.no_grad():
        for trial, trial_seed in enumerate(trial_seeds):
            set_seed(trial_seed)
            inputs = process_inputs(get_inputs(), device, spec.cast_mode)
            set_seed(trial_seed)
            model = original.to(device=device, dtype=model_dtype)
            set_seed(trial_seed)

            def call(model: Any = model, inputs: list[Any] = inputs) -> Any:
                out = model(*inputs)
                synchronize(device)
                return out

            try:
                output = refstore.checked_call(call, inputs, device, built.problems)
            except Exception as exc:
                if refstore.resource_failure(exc):
                    built.problems.append(f"trial {trial}: resource failure")
                built.draws.append(
                    refstore.Draw(
                        {"kind": "raised", "trial": trial, "error": exception_details(exc)}
                    )
                )
                break
            built.draws.append(
                refstore.Draw({"kind": "ok", "trial": trial}, refstore.to_cpu(output))
            )
    return built


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
