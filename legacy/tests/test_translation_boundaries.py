from __future__ import annotations

import numpy as np
import pytest
from scipy.optimize import minimize

from harness.translation_boundaries import (
    BoundaryContractError,
    BoundaryTransportConfig,
    BoundaryView,
    SpanLink,
    TransportConvergenceError,
    transport_boundary_mass,
)


def profile(byte_length: int, centers: tuple[float, ...]) -> np.ndarray:
    positions = np.arange(1, byte_length, dtype=float) / byte_length
    values = np.full_like(positions, 0.02)
    for center in centers:
        values += np.exp(-0.5 * np.square((positions - center) / 0.035))
    return values


def test_aligned_unequal_length_boundaries_beat_shifted_control() -> None:
    left = BoundaryView(65, profile(65, (0.20, 0.54, 0.83)))
    aligned = BoundaryView(91, profile(91, (0.20, 0.54, 0.83)))
    shifted = BoundaryView(91, profile(91, (0.08, 0.38, 0.69)))
    link = (SpanLink(0, 65, 0, 91),)
    aligned_result = transport_boundary_mass(left, aligned, link)
    shifted_result = transport_boundary_mass(left, shifted, link)
    assert aligned_result.loss < 0.8 * shifted_result.loss
    assert aligned_result.coupling.shape == (64, 90)
    assert not aligned_result.coupling.flags.writeable


def test_fractional_one_to_many_links_are_supported() -> None:
    left = BoundaryView(65, profile(65, (0.25, 0.75)))
    right = BoundaryView(91, profile(91, (0.20, 0.45, 0.80)))
    result = transport_boundary_mass(
        left,
        right,
        (
            SpanLink(0, 65, 0, 46, left_fraction=0.5),
            SpanLink(0, 65, 46, 91, left_fraction=0.5),
        ),
    )
    assert np.isfinite(result.loss)
    assert result.transported_mass > 0.0
    assert result.left_unaligned_mass == pytest.approx(0.0)
    assert result.right_unaligned_mass == pytest.approx(0.0)


def test_overallocated_alignment_fails_closed() -> None:
    left = BoundaryView(20, np.ones(19))
    right = BoundaryView(20, np.ones(19))
    with pytest.raises(BoundaryContractError, match="more than once"):
        transport_boundary_mass(
            left,
            right,
            (
                SpanLink(0, 20, 0, 20, left_fraction=0.75, right_fraction=0.75),
                SpanLink(0, 20, 0, 20, left_fraction=0.75, right_fraction=0.75),
            ),
        )


def test_nonconvergence_is_not_silently_accepted() -> None:
    left = BoundaryView(20, profile(20, (0.2, 0.8)))
    right = BoundaryView(25, profile(25, (0.3, 0.7)))
    config = BoundaryTransportConfig(max_iterations=1, tolerance=1e-20)
    with pytest.raises(TransportConvergenceError, match="did not converge"):
        transport_boundary_mass(left, right, (SpanLink(0, 20, 0, 25),), config)


def test_reported_cross_objective_satisfies_primal_stationarity() -> None:
    left_mass = np.asarray([0.4, 0.7, 0.2])
    right_mass = np.asarray([0.3, 0.6, 0.5, 0.2])
    config = BoundaryTransportConfig()
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

    def objective(flat: np.ndarray) -> float:
        coupling = flat.reshape(reference.shape)
        rows = coupling.sum(axis=1)
        columns = coupling.sum(axis=0)

        def kl(first: np.ndarray, second: np.ndarray) -> float:
            return float(np.sum(first * np.log(first / second) - first + second))

        return float(
            np.sum(coupling * cost)
            + config.entropy * kl(coupling, reference)
            + config.mass_penalty * kl(rows, left_mass)
            + config.mass_penalty * kl(columns, right_mass)
        )

    optimized = minimize(
        objective,
        reference.ravel(),
        method="L-BFGS-B",
        bounds=[(1e-12, None)] * reference.size,
        options={"ftol": 1e-13, "gtol": 1e-9, "maxiter": 5_000},
    )
    cross_objective = (
        result.transport_cost + result.mass_penalty + result.entropy_penalty
    )
    assert optimized.success
    assert cross_objective == pytest.approx(optimized.fun, abs=2e-6)


def test_confidence_does_not_turn_linked_mass_into_unaligned_mass() -> None:
    left = BoundaryView(20, profile(20, (0.2, 0.8)))
    right = BoundaryView(20, profile(20, (0.3, 0.65)))
    full = transport_boundary_mass(left, right, (SpanLink(0, 20, 0, 20),))
    low_confidence = transport_boundary_mass(
        left,
        right,
        (SpanLink(0, 20, 0, 20, confidence=0.1),),
    )
    assert low_confidence.left_unaligned_mass == 0.0
    assert low_confidence.right_unaligned_mass == 0.0
    assert full.loss > 0.0
    assert low_confidence.loss == pytest.approx(0.1 * full.loss)


def test_adjacent_spans_own_the_shared_phrase_edge_once() -> None:
    left = BoundaryView(6, np.ones(5))
    right = BoundaryView(8, np.ones(7))
    result = transport_boundary_mass(
        left,
        right,
        (
            SpanLink(0, 3, 0, 4),
            SpanLink(3, 6, 4, 8),
        ),
    )
    assert result.left_unaligned_mass == 0.0
    assert result.right_unaligned_mass == 0.0


def test_exact_zero_mass_is_continuous_with_epsilon_mass() -> None:
    left = BoundaryView(4, np.ones(3))
    exact_zero = transport_boundary_mass(
        left,
        BoundaryView(4, np.zeros(3)),
        (SpanLink(0, 4, 0, 4),),
    )
    epsilon = transport_boundary_mass(
        left,
        BoundaryView(4, np.full(3, 1e-12)),
        (SpanLink(0, 4, 0, 4),),
    )
    assert exact_zero.loss == pytest.approx(epsilon.loss, abs=1e-6)
