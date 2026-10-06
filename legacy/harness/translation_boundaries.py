"""Reference transport loss for translation-equivariant byte boundaries.

The implementation is intentionally model-free. It answers the first question
in Direction 18: is the proposed boundary objective mathematically executable,
length tolerant, and sensitive to alignment? A production BLT experiment should
replace this NumPy solver with a differentiable implementation behind the same
typed inputs.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


class BoundaryContractError(ValueError):
    """Raised when boundary mass or byte-span alignment is invalid."""


class TransportConvergenceError(RuntimeError):
    """Raised when the registered Sinkhorn budget does not converge."""


FloatArray = NDArray[np.float64]


def _readonly_vector(values: object, *, name: str) -> FloatArray:
    array = np.array(values, dtype=np.float64, copy=True)
    if array.ndim != 1 or not array.size:
        raise BoundaryContractError(f"{name} must be a non-empty vector")
    if not np.isfinite(array).all() or np.any(array < 0.0):
        raise BoundaryContractError(f"{name} must contain finite non-negative mass")
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class BoundaryView:
    """Causal boundary mass for the gaps inside one byte sequence."""

    byte_length: int
    boundary_mass: FloatArray
    identity: str = ""

    def __post_init__(self) -> None:
        if self.byte_length < 2:
            raise BoundaryContractError("byte_length must be at least two")
        mass = _readonly_vector(self.boundary_mass, name="boundary_mass")
        if len(mass) != self.byte_length - 1:
            raise BoundaryContractError(
                "boundary_mass must contain exactly byte_length - 1 gap values"
            )
        object.__setattr__(self, "boundary_mass", mass)
        if not self.identity:
            digest = hashlib.sha256(mass.tobytes()).hexdigest()[:16]
            object.__setattr__(self, "identity", f"bytes-{self.byte_length}-{digest}")


@dataclass(frozen=True, slots=True)
class SpanLink:
    """One frozen half-open byte-span alignment.

    Confidence weights the block objective. Fractions allocate source and target
    boundary mass independently, which is necessary for one-to-many links.
    """

    left_start: int
    left_end: int
    right_start: int
    right_end: int
    confidence: float = 1.0
    left_fraction: float = 1.0
    right_fraction: float = 1.0

    def __post_init__(self) -> None:
        if self.left_start < 0 or self.right_start < 0:
            raise BoundaryContractError("span starts must be non-negative")
        if self.left_end <= self.left_start or self.right_end <= self.right_start:
            raise BoundaryContractError("span links must be non-empty and half-open")
        fractions = (self.confidence, self.left_fraction, self.right_fraction)
        if any(not math.isfinite(value) or not 0.0 < value <= 1.0 for value in fractions):
            raise BoundaryContractError(
                "confidence and span-link fractions must each be in (0, 1]"
            )


@dataclass(frozen=True, slots=True)
class BoundaryTransportConfig:
    """Registered solver and null-mass prices for the CPU doctor."""

    entropy: float = 0.05
    mass_penalty: float = 0.25
    unlinked_penalty: float = 0.5
    max_iterations: int = 2_000
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        finite_positive = (
            self.entropy,
            self.mass_penalty,
            self.unlinked_penalty,
            self.tolerance,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in finite_positive):
            raise BoundaryContractError("transport prices and tolerance must be positive")
        if self.max_iterations < 1:
            raise BoundaryContractError("max_iterations must be positive")


@dataclass(frozen=True, slots=True)
class BoundaryTransportResult:
    """Auditable outputs from one span-local unbalanced transport solve."""

    loss: float
    transport_cost: float
    mass_penalty: float
    entropy_penalty: float
    self_bias_correction: float
    mass_difference_correction: float
    transported_mass: float
    left_unaligned_mass: float
    right_unaligned_mass: float
    left_destroyed_mass: float
    right_destroyed_mass: float
    left_created_mass: float
    right_created_mass: float
    iterations: int
    residual: float
    coupling: FloatArray = field(repr=False)

    def __post_init__(self) -> None:
        scalars = (
            self.loss,
            self.transport_cost,
            self.mass_penalty,
            self.entropy_penalty,
            self.self_bias_correction,
            self.mass_difference_correction,
            self.transported_mass,
            self.left_unaligned_mass,
            self.right_unaligned_mass,
            self.left_destroyed_mass,
            self.right_destroyed_mass,
            self.left_created_mass,
            self.right_created_mass,
            self.residual,
        )
        if any(not math.isfinite(value) or value < 0.0 for value in scalars):
            raise BoundaryContractError("transport result scalars must be finite and non-negative")
        if self.iterations < 0:
            raise BoundaryContractError("transport iterations must be non-negative")
        coupling = np.array(self.coupling, dtype=np.float64, copy=True)
        if (
            coupling.ndim != 2
            or not np.isfinite(coupling).all()
            or np.any(coupling < 0.0)
        ):
            raise BoundaryContractError("coupling must be a finite non-negative matrix")
        coupling.setflags(write=False)
        object.__setattr__(self, "coupling", coupling)


def _owned_gap_indices(
    start: int,
    end: int,
    byte_length: int,
) -> NDArray[np.int64]:
    """Return gaps inside a byte span, assigning a shared edge to the left span."""

    return np.arange(start, min(end, byte_length - 1), dtype=np.int64)


def _generalized_kl(left: FloatArray, right: FloatArray) -> float:
    positive = left > 0.0
    if np.any(positive & (right <= 0.0)):
        return math.inf
    terms = np.array(right - left, copy=True)
    terms[positive] += left[positive] * np.log(left[positive] / right[positive])
    return float(terms.sum())


def _uot_block(
    left_mass: FloatArray,
    right_mass: FloatArray,
    cost: FloatArray,
    config: BoundaryTransportConfig,
) -> tuple[FloatArray, int, float, float, float, float]:
    """Entropic unbalanced Sinkhorn for one locally monotone span pair."""

    if left_mass.sum() == 0.0 or right_mass.sum() == 0.0:
        return (
            np.zeros((len(left_mass), len(right_mass)), dtype=np.float64),
            0,
            0.0,
            0.0,
            config.mass_penalty * float(left_mass.sum() + right_mass.sum()),
            0.0,
        )
    reference = left_mass[:, None] * right_mass[None, :]
    kernel = reference * np.exp(-cost / config.entropy)
    kernel = np.maximum(kernel, np.finfo(np.float64).tiny)
    exponent = config.mass_penalty / (config.mass_penalty + config.entropy)
    left_scale = np.ones_like(left_mass)
    right_scale = np.ones_like(right_mass)
    residual = math.inf

    for _iteration in range(1, config.max_iterations + 1):
        next_left = np.power(
            left_mass / np.maximum(kernel @ right_scale, np.finfo(float).tiny),
            exponent,
        )
        next_right = np.power(
            right_mass / np.maximum(kernel.T @ next_left, np.finfo(float).tiny),
            exponent,
        )
        residual = float(
            max(
                np.max(np.abs(next_left - left_scale)),
                np.max(np.abs(next_right - right_scale)),
            )
        )
        left_scale = next_left
        right_scale = next_right
        if residual <= config.tolerance:
            break
    else:
        raise TransportConvergenceError(
            f"unbalanced Sinkhorn did not converge in {config.max_iterations} iterations; "
            f"residual={residual:.3e}"
        )

    coupling = left_scale[:, None] * kernel * right_scale[None, :]
    rows = coupling.sum(axis=1)
    columns = coupling.sum(axis=0)
    transport_cost = float(np.sum(coupling * cost))
    marginal_divergence = config.mass_penalty * (
        _generalized_kl(rows, left_mass) + _generalized_kl(columns, right_mass)
    )
    entropy_divergence = config.entropy * _generalized_kl(
        coupling.ravel(),
        reference.ravel(),
    )
    return (
        coupling,
        _iteration,
        residual,
        transport_cost,
        marginal_divergence,
        entropy_divergence,
    )


def transport_boundary_mass(
    left: BoundaryView,
    right: BoundaryView,
    links: tuple[SpanLink, ...],
    config: BoundaryTransportConfig | None = None,
) -> BoundaryTransportResult:
    """Transport boundary mass within frozen aligned spans.

    The cost uses normalized positions inside each span. That makes unequal byte
    lengths comparable and favors position-consistent matches. Linked-mass
    creation/destruction is priced once by marginal KL; genuinely unaligned mass
    receives a separate explicit penalty.
    """

    if not links:
        raise BoundaryContractError("at least one span link is required")
    config = config or BoundaryTransportConfig()
    coupling = np.zeros(
        (len(left.boundary_mass), len(right.boundary_mass)),
        dtype=np.float64,
    )
    left_allocation = np.zeros_like(left.boundary_mass)
    right_allocation = np.zeros_like(right.boundary_mass)
    transport_cost = 0.0
    marginal_divergence = 0.0
    entropy_divergence = 0.0
    debiased_block_loss = 0.0
    self_bias_correction = 0.0
    mass_difference_correction = 0.0
    iterations = 0
    residual = 0.0

    for link in links:
        if link.left_end > left.byte_length or link.right_end > right.byte_length:
            raise BoundaryContractError("span link exceeds a byte-sequence boundary")
        left_indices = _owned_gap_indices(
            link.left_start,
            link.left_end,
            left.byte_length,
        )
        right_indices = _owned_gap_indices(
            link.right_start,
            link.right_end,
            right.byte_length,
        )
        if not len(left_indices) or not len(right_indices):
            raise BoundaryContractError(
                "span link owns no byte gaps; boundary transport is undefined"
            )
        left_allocation[left_indices] += link.left_fraction
        right_allocation[right_indices] += link.right_fraction
        if np.any(left_allocation > 1.0 + 1e-12) or np.any(
            right_allocation > 1.0 + 1e-12
        ):
            raise BoundaryContractError(
                "overlapping span-link fractions allocate a boundary more than once"
            )
        left_positions = (
            (left_indices + 1 - link.left_start)
            / (link.left_end - link.left_start)
        )
        right_positions = (
            (right_indices + 1 - link.right_start)
            / (link.right_end - link.right_start)
        )
        cost = np.abs(left_positions[:, None] - right_positions[None, :])
        left_mass = left.boundary_mass[left_indices] * link.left_fraction
        right_mass = right.boundary_mass[right_indices] * link.right_fraction
        (
            block,
            used,
            block_residual,
            block_cost,
            block_marginal_divergence,
            block_entropy_divergence,
        ) = _uot_block(
            left_mass,
            right_mass,
            cost,
            config,
        )
        left_self = _uot_block(
            left_mass,
            left_mass,
            np.abs(left_positions[:, None] - left_positions[None, :]),
            config,
        )
        right_self = _uot_block(
            right_mass,
            right_mass,
            np.abs(right_positions[:, None] - right_positions[None, :]),
            config,
        )
        cross_value = (
            block_cost + block_marginal_divergence + block_entropy_divergence
        )
        block_self_bias = 0.5 * (sum(left_self[3:]) + sum(right_self[3:]))
        block_mass_correction = 0.5 * config.entropy * float(
            np.square(left_mass.sum() - right_mass.sum())
        )
        block_divergence = cross_value - block_self_bias + block_mass_correction
        if block_divergence < -1e-7:
            raise BoundaryContractError(
                "debiased unbalanced transport became materially negative"
            )
        coupling[np.ix_(left_indices, right_indices)] += block
        transport_cost += link.confidence * block_cost
        marginal_divergence += link.confidence * block_marginal_divergence
        entropy_divergence += link.confidence * block_entropy_divergence
        debiased_block_loss += link.confidence * max(block_divergence, 0.0)
        self_bias_correction += link.confidence * block_self_bias
        mass_difference_correction += link.confidence * block_mass_correction
        iterations = max(iterations, used, left_self[1], right_self[1])
        residual = max(block_residual, residual, left_self[2], right_self[2])

    row_mass = coupling.sum(axis=1)
    column_mass = coupling.sum(axis=0)
    linked_left = left.boundary_mass * left_allocation
    linked_right = right.boundary_mass * right_allocation
    left_unaligned = float((left.boundary_mass * (1.0 - left_allocation)).sum())
    right_unaligned = float((right.boundary_mass * (1.0 - right_allocation)).sum())
    left_destroyed = float(np.maximum(linked_left - row_mass, 0.0).sum())
    right_destroyed = float(np.maximum(linked_right - column_mass, 0.0).sum())
    left_created = float(np.maximum(row_mass - linked_left, 0.0).sum())
    right_created = float(np.maximum(column_mass - linked_right, 0.0).sum())
    unaligned_cost = config.unlinked_penalty * (left_unaligned + right_unaligned)
    scale = max(
        0.5 * (left.boundary_mass.sum() + right.boundary_mass.sum()),
        np.finfo(float).eps,
    )
    total_loss = float((debiased_block_loss + unaligned_cost) / scale)
    return BoundaryTransportResult(
        loss=total_loss,
        transport_cost=transport_cost,
        mass_penalty=marginal_divergence + unaligned_cost,
        entropy_penalty=entropy_divergence,
        self_bias_correction=self_bias_correction,
        mass_difference_correction=mass_difference_correction,
        transported_mass=float(coupling.sum()),
        left_unaligned_mass=left_unaligned,
        right_unaligned_mass=right_unaligned,
        left_destroyed_mass=left_destroyed,
        right_destroyed_mass=right_destroyed,
        left_created_mass=left_created,
        right_created_mass=right_created,
        iterations=iterations,
        residual=residual,
        coupling=coupling,
    )


__all__ = [
    "BoundaryContractError",
    "BoundaryTransportConfig",
    "BoundaryTransportResult",
    "BoundaryView",
    "SpanLink",
    "TransportConvergenceError",
    "transport_boundary_mass",
]
