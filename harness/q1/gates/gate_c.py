"""Gate (c): hidden values (c1), shape variation (c2), unaligned remainders (c3).

``c`` = ``b`` and ``c1`` and ``c2`` and ``c3`` (composed by the analysis).

- **c1** follows KernelBench-Verified@3fdf6fec: the problem's own
  ``get_inputs()`` with floating tensors scaled by D1 x1.0, D2 x3.0, D3 x0.01,
  D4 x-1.0, plus each problem's extra hidden configurations (L1/100: D5
  alternating +-1 targets) and minus the ones KBV filtered (L1/90 drops D2,
  L1/98 drops D4); see ``data/kbv_hidden_configs.json``. Documented
  deviations: config ``i`` draws after ``set_seed(1042 + i)`` (KBV inherits
  the global RNG state), and integer tensors keep their dtype (KBV casts every
  tensor to fp32, which makes L1/95's reference raise and the config pass
  vacuously). ``kbv_compat=True`` restores KBV's behavior for the fidelity
  differential.
- **c2/c3** use the committed shape manifest (``data/shape_manifest.json``,
  rules in ``shapes.py``); each config is drawn with D1 and with D4.
- **Validity gate** (per config, before a candidate verdict counts): the fp32
  reference is finite; fp32 reference on the gate device versus the fp64
  oracle is within the gate tolerance; CPU fp32 versus device fp32 is within
  the tolerance. Integer outputs must match exactly. An inadmissible config
  is logged and excluded; a problem with no admissible config in a family is
  unrefereeable there (verdict ``error``).
- Tolerances: primary atol = rtol = 1e-3; secondary ``c_1e-2`` from the same
  outputs; ``c_kbv_raw`` (no validity filter, reference-raised configs pass
  as in KBV) from the same outputs.
"""

from __future__ import annotations

import copy
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import torch

from harness.q1 import problems as problem_lib
from harness.q1.gates.common import (
    GateOutcome,
    allclose_compare,
    channel_seed,
    exception_details,
    first_tensor_outputs,
    load_candidate,
    load_reference,
    process_inputs,
    resolve_device,
    scale_float_inputs,
    set_seed,
    synchronize,
)
from harness.q1.schema import CONFIG_ID_RE

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
C1_BASE, C2_BASE, C3_BASE = 1042, 2042, 3042
PRIMARY_TOL = 1e-3
SECONDARY_TOL = 1e-2
FACTORS = {"D1": 1.0, "D2": 3.0, "D3": 0.01, "D4": -1.0}
SHAPE_DRAWS = ("D1", "D4")


@lru_cache(maxsize=1)
def kbv_configs() -> dict[str, Any]:
    return json.loads((DATA_ROOT / "kbv_hidden_configs.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def shape_manifest() -> dict[str, Any]:
    return json.loads((DATA_ROOT / "shape_manifest.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ConfigSpec:
    family: str
    config_id: str
    draw: str
    seed: int | None
    overrides: Mapping[str, int] = field(default_factory=dict)


def c_configs(
    problem_id: str,
    *,
    families: Sequence[str] = ("c1", "c2", "c3"),
    replicate_seed: int = 42,
    manifest: Mapping[str, Any] | None = None,
    kbv: Mapping[str, Any] | None = None,
) -> list[ConfigSpec]:
    """The preregistered gate (c) configurations for one problem, in order."""
    manifest = manifest if manifest is not None else shape_manifest()
    kbv = kbv if kbv is not None else kbv_configs()
    specs: list[ConfigSpec] = []
    if "c1" in families:
        labels = kbv["problems"].get(problem_id, {}).get("configs", ["D1", "D2", "D3", "D4"])
        for index, label in enumerate(labels):
            seed = channel_seed(C1_BASE, replicate_seed, index)
            specs.append(ConfigSpec("c1", f"c1/{label}/seed-{seed}", label, seed))
    entry = manifest["problems"].get(problem_id, {})
    for family, base in (("c2", C2_BASE), ("c3", C3_BASE)):
        if family not in families:
            continue
        index = 0
        for config in entry.get(family, []):
            for draw in SHAPE_DRAWS:
                seed = channel_seed(base, replicate_seed, index)
                specs.append(
                    ConfigSpec(
                        family,
                        f"{config['config_id']}/{draw}/seed-{seed}",
                        draw,
                        seed,
                        dict(config["overrides"]),
                    )
                )
                index += 1
    # Fail closed before any candidate is loaded: a config id the verdict schema
    # refuses would otherwise crash the worker after the candidate ran, and the
    # runner would charge that harness fault to the candidate.
    bad = [spec.config_id for spec in specs if not CONFIG_ID_RE.fullmatch(spec.config_id)]
    if bad:
        raise ValueError(f"{problem_id}: config ids not allowed by schema.CONFIG_ID_RE: {bad[:5]}")
    return specs


def transform_inputs(inputs: list[Any], draw: str) -> list[Any]:
    if draw in FACTORS:
        return scale_float_inputs(inputs, FACTORS[draw])
    if draw == "D5-alternating-targets":
        inputs = list(inputs)
        batch = inputs[1].shape[0]
        targets = torch.ones(batch)
        targets[::2] = -1.0
        inputs[1] = targets
        return inputs
    raise ValueError(f"unknown draw {draw}")


# --- Validity --------------------------------------------------------------------


def _within(a: torch.Tensor, b: torch.Tensor, tol: float) -> bool:
    """``|a - b| <= tol + tol * |b|`` in fp64; integers and bools must be equal."""
    from harness.q1.gates.reductions import allclose_fp64, equal_int64

    if a.shape != b.shape:
        return False
    if not a.is_floating_point() or not b.is_floating_point():
        return equal_int64(a, b)
    return allclose_fp64(a, b, tol)


def validity_check(
    reference: torch.nn.Module,
    inputs: Sequence[Any],
    reference_output: Any,
    *,
    device: torch.device,
    tolerance: float,
) -> dict[str, Any]:
    """The per-config validity gate. ``reference_output`` is fp32 on ``device``."""
    outputs = first_tensor_outputs(reference_output)
    reasons: list[str] = []
    if any(o.is_floating_point() and not bool(torch.isfinite(o).all()) for o in outputs):
        reasons.append("reference-nonfinite")
    with torch.no_grad():
        oracle = copy.deepcopy(reference).double()
        oracle_inputs = [
            x.double() if isinstance(x, torch.Tensor) and x.is_floating_point() else x
            for x in inputs
        ]
        r64 = first_tensor_outputs(oracle(*oracle_inputs))
        synchronize(device)
        if not all(_within(o, r, tolerance) for o, r in zip(outputs, r64, strict=True)):
            reasons.append("device-fp32-vs-fp64")
        if device.type != "cpu":
            cpu_model = copy.deepcopy(reference).to("cpu")
            cpu_inputs = [x.cpu() if isinstance(x, torch.Tensor) else x for x in inputs]
            r_cpu = first_tensor_outputs(cpu_model(*cpu_inputs))
            if not all(_within(c, o, tolerance) for c, o in zip(r_cpu, outputs, strict=True)):
                reasons.append("cpu-fp32-vs-device-fp32")
    return {
        "admissible": not reasons,
        "reasons": reasons,
        "cpu_check": device.type != "cpu",
        "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
        "matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
    }


# --- Gate ---------------------------------------------------------------------------


def _compare(output: Any, reference: Any, tol: float) -> tuple[bool, float | None, float | None]:
    result = allclose_compare(output, reference, tol, tol)
    return result.passed, result.max_abs_err, result.max_rel_err


def run_gate_c(
    problem_id: str,
    kernel_source: str,
    *,
    problem_source: str | None = None,
    families: Sequence[str] = ("c1", "c2", "c3"),
    replicate_seed: int = 42,
    device: str | torch.device | None = None,
    tolerance: float = PRIMARY_TOL,
    secondary_tolerance: float = SECONDARY_TOL,
    validity: str = "inline",
    validity_table: Mapping[str, Mapping[str, Any]] | None = None,
    manifest: Mapping[str, Any] | None = None,
    kbv_compat: bool = False,
) -> list[GateOutcome]:
    """Run gate (c) families on one candidate. Returns per-config rows and aggregates.

    ``validity``: ``inline`` computes the validity gate here; ``table`` reads
    precomputed results from ``validity_table[config_id]``; ``off`` admits
    every config (used for ``kbv_compat``).
    """
    if validity not in {"inline", "table", "off"}:
        raise ValueError("validity must be inline, table or off")
    dev = resolve_device(device)
    if problem_source is None:
        problem_source = problem_lib.load_problem_source(problem_id)
    analysis = problem_lib.analyze_problem(problem_id, problem_source)
    specs = c_configs(
        problem_id, families=families, replicate_seed=replicate_seed, manifest=manifest
    )
    cast_mode = "fp32" if kbv_compat else "preserve"
    rows: list[GateOutcome] = []

    Model, get_init_inputs, native_get_inputs = load_reference(problem_source)
    set_seed(replicate_seed)
    init_inputs = process_inputs(get_init_inputs(), dev, cast_mode)
    with torch.no_grad():
        set_seed(replicate_seed)
        reference = Model(*init_inputs)
    loaded = load_candidate(kernel_source)
    try:
        with torch.no_grad():
            set_seed(replicate_seed)
            candidate = loaded.model_class(*init_inputs)
        reference = reference.to(device=dev)
        candidate = candidate.to(device=dev)
        variants: dict[tuple[tuple[str, int], ...], Any] = {(): native_get_inputs}
        if kbv_compat:
            raw_draws = _kbv_compat_draws(specs, native_get_inputs)
        for position, spec in enumerate(specs):
            start = time.perf_counter()
            key = tuple(sorted(spec.overrides.items()))
            if key not in variants:
                variant_source = problem_lib.override_constants(
                    problem_source, analysis, spec.overrides
                )
                variants[key] = load_reference(variant_source)[2]
            if kbv_compat:
                raw = raw_draws[position]
            else:
                set_seed(spec.seed)
                raw = transform_inputs(list(variants[key]()), spec.draw)
            inputs = process_inputs(raw, dev, cast_mode)
            details: dict[str, Any] = {
                "draw": spec.draw,
                "seed": spec.seed,
                "overrides": dict(spec.overrides),
                "kbv_compat": kbv_compat,
            }
            rows.append(
                _one_config(
                    spec,
                    reference,
                    candidate,
                    inputs,
                    details,
                    dev,
                    tolerance,
                    secondary_tolerance,
                    validity,
                    validity_table,
                    start,
                )
            )
    finally:
        loaded.cleanup()
    rows.extend(aggregate(rows, families, tolerance, secondary_tolerance))
    return rows


def _kbv_compat_draws(specs: Sequence[ConfigSpec], get_inputs: Any) -> list[list[Any]]:
    """KBV ``get_hidden_inputs``: all configs drawn back to back from the current RNG."""
    draws = []
    for spec in specs:
        if spec.family != "c1":
            raise ValueError("kbv_compat applies to c1 only")
        draws.append(transform_inputs(list(get_inputs()), spec.draw))
    return draws


def _one_config(
    spec: ConfigSpec,
    reference: torch.nn.Module,
    candidate: torch.nn.Module,
    inputs: list[Any],
    details: dict[str, Any],
    device: torch.device,
    tolerance: float,
    secondary_tolerance: float,
    validity: str,
    validity_table: Mapping[str, Mapping[str, Any]] | None,
    start: float,
) -> GateOutcome:
    def done(verdict: str, **extra: Any) -> GateOutcome:
        return GateOutcome(
            spec.family,
            spec.config_id,
            verdict,
            tolerance=tolerance,
            details=details,
            wall_seconds=time.perf_counter() - start,
            **extra,
        )

    with torch.no_grad():
        try:
            ref_out = reference(*inputs)
            synchronize(device)
        except Exception as exc:
            details.update(
                {
                    "admissible": False,
                    "reference_raised": True,
                    "validity_reasons": ["reference-raised"],
                    **exception_details(exc),
                }
            )
            details["kbv_raw_pass"] = True  # KBV skips a config whose reference raises
            return done("error")
        if validity == "inline":
            check = validity_check(reference, inputs, ref_out, device=device, tolerance=tolerance)
        elif validity == "table":
            check = dict(
                (validity_table or {}).get(
                    spec.config_id, {"admissible": False, "reasons": ["no-entry"]}
                )
            )
        else:
            check = {"admissible": True, "reasons": []}
        details["admissible"] = bool(check["admissible"])
        details["validity_reasons"] = list(check.get("reasons", []))
        try:
            out = candidate(*inputs)
            synchronize(device)
            passed, max_abs, max_rel = _compare(out, ref_out, tolerance)
            passed_secondary, _, _ = _compare(out, ref_out, secondary_tolerance)
        except Exception as exc:
            details.update({"reason": "candidate-raised", **exception_details(exc)})
            details["pass_secondary"] = False
            details["kbv_raw_pass"] = False
            return done("reject")
    details["pass_secondary"] = bool(passed_secondary)
    details["kbv_raw_pass"] = bool(passed)
    if max_abs is None:
        details["reason"] = "shape-mismatch"
    return done("accept" if passed else "reject", max_abs_err=max_abs, max_rel_err=max_rel)


def aggregate(
    rows: Sequence[GateOutcome],
    families: Sequence[str],
    tolerance: float,
    secondary_tolerance: float,
) -> list[GateOutcome]:
    """Per-family aggregates (``c1``, ``c2``, ``c3``) and, over all run families,
    ``c_1e-2`` (secondary tolerance) and ``c_kbv_raw`` (no validity filter).

    The ladder gates ``c = b and c1 and c2 and c3`` (and the same for the two
    secondaries) are composed by the analysis from these rows and ``b``'s.
    """
    out: list[GateOutcome] = []

    def summarize(gate: str, members: list[GateOutcome], key: str) -> GateOutcome:
        admissible = [r for r in members if r.details.get("admissible")]
        if key == "kbv_raw":
            failed = [r.config_id for r in members if not r.details.get("kbv_raw_pass", False)]
            verdict = "reject" if failed else "accept"
            if not members:
                verdict = "error"
        else:
            if key == "primary":
                failed = [r.config_id for r in admissible if r.verdict != "accept"]
            else:
                failed = [r.config_id for r in admissible if not r.details.get("pass_secondary")]
            verdict = "reject" if failed else ("accept" if admissible else "error")
        abs_errs = [r.max_abs_err for r in admissible if r.max_abs_err is not None]
        rel_errs = [r.max_rel_err for r in admissible if r.max_rel_err is not None]
        return GateOutcome(
            gate,
            "aggregate",
            verdict,
            max_abs_err=max(abs_errs) if abs_errs else None,
            max_rel_err=max(rel_errs) if rel_errs else None,
            tolerance=secondary_tolerance if key == "secondary" else tolerance,
            details={
                "configs": len(members),
                "admissible": len(admissible),
                "failed_configs": failed[:100],
                "reason": "" if admissible or key == "kbv_raw" else "no-admissible-config",
            },
            wall_seconds=sum(r.wall_seconds for r in members),
        )

    for family in families:
        out.append(summarize(family, [r for r in rows if r.gate == family], "primary"))
    everything = [r for r in rows if r.gate in families]
    # Conjunctions over the families run here; the ladder adds ``b`` in the analysis.
    out.append(summarize("c_1e-2", everything, "secondary"))
    out.append(summarize("c_kbv_raw", everything, "kbv_raw"))
    return out
