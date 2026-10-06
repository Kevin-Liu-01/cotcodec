#!/usr/bin/env python3
"""Exercise the Direction-18 boundary-transport loss before model training."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.translation_boundaries import (  # noqa: E402
    BoundaryTransportConfig,
    BoundaryTransportResult,
    BoundaryView,
    SpanLink,
    transport_boundary_mass,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _profile(byte_length: int, centers: tuple[float, ...]) -> np.ndarray:
    positions = np.arange(1, byte_length, dtype=np.float64) / byte_length
    mass = np.full_like(positions, 0.02)
    for center in centers:
        mass += np.exp(-0.5 * np.square((positions - center) / 0.035))
    return mass


def _receipt(result: BoundaryTransportResult) -> dict[str, float | int]:
    return {
        "loss": result.loss,
        "transport_cost": result.transport_cost,
        "mass_penalty": result.mass_penalty,
        "entropy_penalty": result.entropy_penalty,
        "self_bias_correction": result.self_bias_correction,
        "mass_difference_correction": result.mass_difference_correction,
        "transported_mass": result.transported_mass,
        "left_unaligned_mass": result.left_unaligned_mass,
        "right_unaligned_mass": result.right_unaligned_mass,
        "left_destroyed_mass": result.left_destroyed_mass,
        "right_destroyed_mass": result.right_destroyed_mass,
        "left_created_mass": result.left_created_mass,
        "right_created_mass": result.right_created_mass,
        "iterations": result.iterations,
        "residual": result.residual,
    }


def _primal_equivalence(
    config: BoundaryTransportConfig,
) -> dict[str, float | bool]:
    left_mass = np.asarray([0.4, 0.7, 0.2])
    right_mass = np.asarray([0.3, 0.6, 0.5, 0.2])
    result = transport_boundary_mass(
        BoundaryView(4, left_mass),
        BoundaryView(5, right_mass),
        (SpanLink(0, 4, 0, 5),),
        config,
    )
    left_positions = np.arange(1, 4) / 4
    right_positions = np.arange(1, 5) / 5
    cost = np.abs(left_positions[:, None] - right_positions[None, :])
    reference = left_mass[:, None] * right_mass[None, :]

    def kl(first: np.ndarray, second: np.ndarray) -> float:
        return float(np.sum(first * np.log(first / second) - first + second))

    def objective(flat: np.ndarray) -> float:
        coupling = flat.reshape(reference.shape)
        return float(
            np.sum(coupling * cost)
            + config.entropy * kl(coupling, reference)
            + config.mass_penalty * kl(coupling.sum(axis=1), left_mass)
            + config.mass_penalty * kl(coupling.sum(axis=0), right_mass)
        )

    optimized = minimize(
        objective,
        reference.ravel(),
        method="L-BFGS-B",
        bounds=[(1e-12, None)] * reference.size,
        options={"ftol": 1e-13, "gtol": 1e-9, "maxiter": 5_000},
    )
    reported = result.transport_cost + result.mass_penalty + result.entropy_penalty
    return {
        "optimizer_success": bool(optimized.success),
        "reported_cross_primal": reported,
        "independent_optimum": float(optimized.fun),
        "absolute_difference": abs(reported - float(optimized.fun)),
    }


def main() -> int:
    args = parse_args()
    config = BoundaryTransportConfig()
    left = BoundaryView(65, _profile(65, (0.20, 0.54, 0.83)), "source")
    aligned = BoundaryView(91, _profile(91, (0.20, 0.54, 0.83)), "aligned")
    shifted = BoundaryView(91, _profile(91, (0.08, 0.38, 0.69)), "shifted")
    aligned_result = transport_boundary_mass(
        left,
        aligned,
        (SpanLink(0, 65, 0, 91),),
        config,
    )
    shifted_result = transport_boundary_mass(
        left,
        shifted,
        (SpanLink(0, 65, 0, 91),),
        config,
    )
    correct_links = (
        SpanLink(0, 33, 0, 46),
        SpanLink(33, 65, 46, 91),
    )
    wrong_links = (
        SpanLink(0, 33, 46, 91),
        SpanLink(33, 65, 0, 46),
    )
    correct_link_result = transport_boundary_mass(left, aligned, correct_links, config)
    wrong_link_result = transport_boundary_mass(left, aligned, wrong_links, config)
    one_to_many = transport_boundary_mass(
        left,
        aligned,
        (
            SpanLink(0, 65, 0, 46, left_fraction=0.5),
            SpanLink(0, 65, 46, 91, left_fraction=0.5),
        ),
        config,
    )
    primal = _primal_equivalence(config)
    gates = {
        "aligned_beats_shifted": aligned_result.loss < 0.8 * shifted_result.loss,
        "correct_links_beat_permuted_links": (
            correct_link_result.loss < 0.8 * wrong_link_result.loss
        ),
        "unequal_lengths_supported": math.isfinite(aligned_result.loss),
        "fractional_one_to_many_accounted": (
            math.isfinite(one_to_many.loss)
            and one_to_many.left_unaligned_mass < 1e-10
            and one_to_many.right_unaligned_mass < 1e-10
        ),
        "solver_converged": max(
            aligned_result.residual,
            shifted_result.residual,
            one_to_many.residual,
        )
        <= config.tolerance,
        "tiny_primal_matches_scipy": (
            primal["optimizer_success"] is True
            and primal["absolute_difference"] <= 2e-6
        ),
    }
    payload = {
        "schema_version": "1.0",
        "doctor": "translation-boundary-transport",
        "status": (
            "REFERENCE_OBJECTIVE_DOCTOR_PASS"
            if all(gates.values())
            else "REFERENCE_OBJECTIVE_DOCTOR_FAIL"
        ),
        "config": {
            "entropy": config.entropy,
            "mass_penalty": config.mass_penalty,
            "unlinked_penalty": config.unlinked_penalty,
            "max_iterations": config.max_iterations,
            "tolerance": config.tolerance,
        },
        "cases": {
            "aligned_unequal_length": _receipt(aligned_result),
            "shifted_control": _receipt(shifted_result),
            "correct_span_links": _receipt(correct_link_result),
            "permuted_span_links": _receipt(wrong_link_result),
            "fractional_one_to_many": _receipt(one_to_many),
            "tiny_primal_equivalence": primal,
        },
        "gates": gates,
        "provenance": {
            "implementation_sha256": hashlib.sha256(
                (PROJECT_ROOT / "harness" / "translation_boundaries.py").read_bytes()
            ).hexdigest(),
            "numpy_version": np.__version__,
            "left_identity": left.identity,
            "aligned_identity": aligned.identity,
            "shifted_identity": shifted.identity,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["payload_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with args.output.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "REFERENCE_OBJECTIVE_DOCTOR_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
