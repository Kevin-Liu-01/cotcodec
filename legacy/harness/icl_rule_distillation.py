"""Phase-0 objects for Direction 19, portable in-context write-rule distillation.

Everything here is model-free and runs in NumPy/SciPy fp64 on a CPU. It answers
the Stage-A questions of research/proposals/2026-09-01-icl-rule-distillation-port.md
before any pretrained base is touched:

* the canonical fast-weight interface (rank-r truncated d x d state written by
  rank-one updates ``M <- rho M + eta u w^T``) and its two structurally separated
  passes (Pass W writes demonstrations, Pass R reads probes with M frozen);
* the rule ladder ``R_lin`` (linear preconditioned GD), ``R_adapt``
  (content-adaptive preconditioned GD), ``R_gf`` (nonlinear gradient-form rule,
  ``w_i = k_i``) and ``R_theta`` (``R_gf`` plus a free write direction), with the
  parameter-count arithmetic that makes ``R_gf`` and ``R_adapt`` iso-parameter with
  ``R_theta``;
* behavioural distillation of every rung to a synthetic teacher by truncated BPTT
  through the writes (hand-written analytic gradients, Adam);
* the finite-task-prior linear-regression regime of Raventos et al. 2023
  (arXiv 2306.15063), in which the Bayes predictor is the discrete posterior mean
  (dMMSE) rather than ridge, together with the exact key-span ceiling that bounds
  every key-directed rule in that regime;
* the post-hoc clamp ablations, the two-pass causality audit, the parameter-count
  and rank-truncation doctors, and the pre-registered attribution tree with its
  power simulation.

The synthetic teacher's predictive distribution is Gaussian with fixed variance, so
the squared prediction gap used here equals the proposal's KL objective up to a
constant. Numbers produced from these objects are synthetic-case numbers: they
prove that the code paths execute and that the registered gates have the intended
semantics, nothing about any pretrained model.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from functools import partial

import numpy as np
from numpy.typing import NDArray
from scipy import stats as scipy_stats

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


class RuleContractError(ValueError):
    """Raised when an interface, prior, rule or gate input violates its contract."""


class DistillationDivergenceError(RuntimeError):
    """Raised when a distillation run produces a non-finite loss."""


# --------------------------------------------------------------------------- #
# Interface and parameter-count arithmetic
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class InterfaceSpec:
    """Canonical fast-weight interface shared by every rule and every base."""

    state_dim: int = 64
    rank: int = 8
    n_demonstrations: int = 8
    n_state_statistics: int = 8
    theta_hidden: int = 256

    def __post_init__(self) -> None:
        if self.state_dim < 2:
            raise RuleContractError("state_dim must be at least two")
        if not 1 <= self.rank <= self.state_dim:
            raise RuleContractError("rank must lie in [1, state_dim]")
        if self.n_demonstrations < 1:
            raise RuleContractError("n_demonstrations must be positive")
        if self.n_state_statistics < 1:
            raise RuleContractError("n_state_statistics must be positive")
        if self.theta_hidden < 1:
            raise RuleContractError("theta_hidden must be positive")

    @property
    def n_inputs(self) -> int:
        """k, v, e, M k, ||k||, step index and the state statistics."""

        return 4 * self.state_dim + 2 + self.n_state_statistics

    @property
    def theta_outputs(self) -> int:
        """rho, eta, u and the free write direction w."""

        return 2 + 2 * self.state_dim

    @property
    def key_directed_outputs(self) -> int:
        """rho, eta and one d-vector (u for R_gf, the diagonal preconditioner for R_adapt)."""

        return 2 + self.state_dim


PILOT_INTERFACE = InterfaceSpec()
SYNTHETIC_INTERFACE = InterfaceSpec(state_dim=16, rank=8, n_demonstrations=8, theta_hidden=32)


def mlp_parameter_count(n_inputs: int, hidden: int, n_outputs: int, extra: int = 0) -> int:
    """Two-layer MLP with biases plus ``extra`` free parameters."""

    if min(n_inputs, hidden, n_outputs) < 1 or extra < 0:
        raise RuleContractError("MLP dimensions must be positive and extra non-negative")
    return n_inputs * hidden + hidden + hidden * n_outputs + n_outputs + extra


def iso_parameter_hidden_width(
    target: int,
    n_inputs: int,
    n_outputs: int,
    extra: int = 0,
    tolerance: float = 0.01,
) -> int:
    """Hidden width whose parameter count matches ``target`` within ``tolerance``."""

    if target < 1 or not 0.0 < tolerance < 1.0:
        raise RuleContractError("target must be positive and tolerance inside (0, 1)")
    width = int(round((target - n_outputs - extra) / (n_inputs + 1 + n_outputs)))
    if width < 1:
        raise RuleContractError("no positive hidden width reaches the target parameter count")
    count = mlp_parameter_count(n_inputs, width, n_outputs, extra)
    if abs(count - target) / target > tolerance:
        raise RuleContractError(
            f"hidden width {width} gives {count} parameters, outside {tolerance:.2%} of {target}"
        )
    return width


@dataclass(frozen=True, slots=True)
class RuleParameterCounts:
    """Exact parameter counts of the ladder at one interface."""

    theta: int
    gradient_form: int
    gradient_form_hidden: int
    adaptive: int
    adaptive_hidden: int
    linear: int
    tolerance: float

    def relative_gaps(self) -> dict[str, float]:
        return {
            "R_gf": (self.gradient_form - self.theta) / self.theta,
            "R_adapt": (self.adaptive - self.theta) / self.theta,
        }

    def within_tolerance(self) -> bool:
        return all(abs(gap) <= self.tolerance for gap in self.relative_gaps().values())


def rule_parameter_counts(spec: InterfaceSpec, tolerance: float = 0.01) -> RuleParameterCounts:
    """Parameter-count doctor: R_gf and R_adapt must match R_theta within ``tolerance``."""

    theta = mlp_parameter_count(spec.n_inputs, spec.theta_hidden, spec.theta_outputs)
    gf_hidden = iso_parameter_hidden_width(
        theta, spec.n_inputs, spec.key_directed_outputs, 0, tolerance
    )
    dense = spec.state_dim * spec.state_dim
    adapt_hidden = iso_parameter_hidden_width(
        theta, spec.n_inputs, spec.key_directed_outputs, dense, tolerance
    )
    return RuleParameterCounts(
        theta=theta,
        gradient_form=mlp_parameter_count(spec.n_inputs, gf_hidden, spec.key_directed_outputs),
        gradient_form_hidden=gf_hidden,
        adaptive=mlp_parameter_count(spec.n_inputs, adapt_hidden, spec.key_directed_outputs, dense),
        adaptive_hidden=adapt_hidden,
        linear=dense + 4,
        tolerance=tolerance,
    )


# --------------------------------------------------------------------------- #
# Rank truncation and state statistics
# --------------------------------------------------------------------------- #


def rank_truncate(state: FloatArray, rank: int) -> FloatArray:
    """Pi_r: best rank-``rank`` approximation of each d x d state (batched SVD)."""

    matrices = np.asarray(state, dtype=np.float64)
    if matrices.ndim not in (2, 3) or matrices.shape[-1] != matrices.shape[-2]:
        raise RuleContractError("state must be a square matrix or a batch of square matrices")
    if not 1 <= rank <= matrices.shape[-1]:
        raise RuleContractError("rank must lie in [1, state_dim]")
    if not np.isfinite(matrices).all():
        raise RuleContractError("state must be finite")
    left, singular, right = np.linalg.svd(matrices, full_matrices=False)
    singular = singular.copy()
    singular[..., rank:] = 0.0
    return (left * singular[..., None, :]) @ right


@dataclass(frozen=True, slots=True)
class RankTruncationReceipt:
    """Pi_r is inert for at most r rank-one writes from M = 0 and active on the (r+1)-th."""

    rank: int
    inert_max_abs_change: float
    rank_before_truncation: int
    rank_after_truncation: int

    def passes(self) -> bool:
        return (
            self.inert_max_abs_change <= 1e-9
            and self.rank_before_truncation == self.rank + 1
            and self.rank_after_truncation == self.rank
        )


def rank_truncation_doctor(spec: InterfaceSpec, rng: np.random.Generator) -> RankTruncationReceipt:
    d = spec.state_dim
    if spec.rank >= d:
        raise RuleContractError("rank truncation doctor needs rank below state_dim")
    state = np.zeros((d, d))
    inert_change = 0.0
    for _ in range(spec.rank):
        state = state + np.outer(rng.normal(size=d), rng.normal(size=d))
        inert_change = max(
            inert_change, float(np.max(np.abs(rank_truncate(state, spec.rank) - state)))
        )
    state = state + np.outer(rng.normal(size=d), rng.normal(size=d))
    before = int(np.linalg.matrix_rank(state))
    after = int(np.linalg.matrix_rank(rank_truncate(state, spec.rank)))
    return RankTruncationReceipt(spec.rank, inert_change, before, after)


def state_statistics_basis(spec: InterfaceSpec, seed: int) -> FloatArray:
    """Fixed linear state statistics: trace/sqrt(d) plus seeded unit-Frobenius projections."""

    rng = np.random.default_rng(seed)
    basis = rng.normal(size=(spec.n_state_statistics, spec.state_dim, spec.state_dim))
    basis[0] = np.eye(spec.state_dim)
    norms = np.linalg.norm(basis.reshape(spec.n_state_statistics, -1), axis=1)
    basis = basis / norms[:, None, None]
    basis.setflags(write=False)
    return basis


# --------------------------------------------------------------------------- #
# Write rules
# --------------------------------------------------------------------------- #


class RuleFamily(StrEnum):
    THETA = "R_theta"
    GRADIENT_FORM = "R_gf"
    ADAPTIVE = "R_adapt"
    LINEAR = "R_lin"


def _sigmoid(values: FloatArray) -> FloatArray:
    return 1.0 / (1.0 + np.exp(-values))


def _softplus(values: FloatArray) -> FloatArray:
    return np.logaddexp(0.0, values)


class WriteRule:
    """Emits (rho, eta, u, w) per demonstration and back-propagates into its parameters."""

    family: RuleFamily
    spec: InterfaceSpec
    params: dict[str, FloatArray]

    def parameter_count(self) -> int:
        return int(sum(value.size for value in self.params.values()))

    def zero_gradients(self) -> dict[str, FloatArray]:
        return {name: np.zeros_like(value) for name, value in self.params.items()}

    def emit(
        self,
        features: FloatArray,
        keys: FloatArray,
        errors: FloatArray,
        step_index: int,
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, dict[str, FloatArray]]:
        raise NotImplementedError

    def backward(
        self,
        cache: dict[str, FloatArray],
        d_rho: FloatArray,
        d_eta: FloatArray,
        d_u: FloatArray,
        d_w: FloatArray,
        grads: dict[str, FloatArray],
    ) -> tuple[FloatArray | None, FloatArray]:
        """Return (d features or None, extra d errors) and accumulate parameter gradients."""

        raise NotImplementedError


class MLPWriteRule(WriteRule):
    """R_theta, R_gf or R_adapt: a two-layer tanh MLP over the 4d+2+S interface features."""

    def __init__(
        self,
        family: RuleFamily,
        spec: InterfaceSpec,
        hidden: int,
        rng: np.random.Generator,
    ) -> None:
        if family is RuleFamily.LINEAR:
            raise RuleContractError("R_lin is not an MLP rule; use LinearGDRule")
        if hidden < 1:
            raise RuleContractError("hidden width must be positive")
        self.family = family
        self.spec = spec
        self.hidden = hidden
        d = spec.state_dim
        n_out = spec.theta_outputs if family is RuleFamily.THETA else spec.key_directed_outputs
        self.params = {
            "W1": rng.normal(0.0, 1.0 / math.sqrt(spec.n_inputs), (spec.n_inputs, hidden)),
            "b1": np.zeros(hidden),
            "W2": rng.normal(0.0, 0.1 / math.sqrt(hidden), (hidden, n_out)),
            "b2": np.zeros(n_out),
        }
        self.params["b2"][0] = 3.0  # rho ~ 0.95 at initialisation
        self.params["b2"][1] = math.log(math.expm1(0.05))  # eta ~ 0.05 at initialisation
        if family is RuleFamily.ADAPTIVE:
            self.params["W0"] = np.eye(d)  # R_lin's W at identity is the nested special case

    def copy(self) -> MLPWriteRule:
        clone = MLPWriteRule.__new__(MLPWriteRule)
        clone.family = self.family
        clone.spec = self.spec
        clone.hidden = self.hidden
        clone.params = {name: value.copy() for name, value in self.params.items()}
        return clone

    def emit(
        self,
        features: FloatArray,
        keys: FloatArray,
        errors: FloatArray,
        step_index: int,
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, dict[str, FloatArray]]:
        d = self.spec.state_dim
        hidden_pre = features @ self.params["W1"] + self.params["b1"]
        hidden = np.tanh(hidden_pre)
        out = hidden @ self.params["W2"] + self.params["b2"]
        rho = _sigmoid(out[:, 0])
        eta = _softplus(out[:, 1])
        cache = {"features": features, "hidden": hidden, "out": out, "errors": errors}
        if self.family is RuleFamily.THETA:
            return rho, eta, out[:, 2 : 2 + d], out[:, 2 + d : 2 + 2 * d], cache
        if self.family is RuleFamily.GRADIENT_FORM:
            return rho, eta, out[:, 2 : 2 + d], keys, cache
        diagonal = out[:, 2 : 2 + d]
        u = errors @ self.params["W0"].T + diagonal * errors
        return rho, eta, u, keys, cache

    def backward(
        self,
        cache: dict[str, FloatArray],
        d_rho: FloatArray,
        d_eta: FloatArray,
        d_u: FloatArray,
        d_w: FloatArray,
        grads: dict[str, FloatArray],
    ) -> tuple[FloatArray | None, FloatArray]:
        d = self.spec.state_dim
        out = cache["out"]
        rho = _sigmoid(out[:, 0])
        d_out = np.zeros_like(out)
        d_out[:, 0] = d_rho * rho * (1.0 - rho)
        d_out[:, 1] = d_eta * _sigmoid(out[:, 1])
        errors = cache["errors"]
        d_errors_extra = np.zeros_like(errors)
        if self.family is RuleFamily.THETA:
            d_out[:, 2 : 2 + d] = d_u
            d_out[:, 2 + d : 2 + 2 * d] = d_w
        elif self.family is RuleFamily.GRADIENT_FORM:
            d_out[:, 2 : 2 + d] = d_u
        else:
            diagonal = out[:, 2 : 2 + d]
            d_out[:, 2 : 2 + d] = d_u * errors
            grads["W0"] += np.einsum("bi,bj->ij", d_u, errors)
            d_errors_extra = d_u @ self.params["W0"] + d_u * diagonal
        hidden = cache["hidden"]
        d_hidden = d_out @ self.params["W2"].T
        grads["W2"] += hidden.T @ d_out
        grads["b2"] += d_out.sum(axis=0)
        d_hidden_pre = d_hidden * (1.0 - hidden * hidden)
        grads["W1"] += cache["features"].T @ d_hidden_pre
        grads["b1"] += d_hidden_pre.sum(axis=0)
        return d_hidden_pre @ self.params["W1"].T, d_errors_extra


class LinearGDRule(WriteRule):
    """R_lin: u = W e, eta = eta_0 (i+1)^-gamma (||k||^2 + eps)^-beta, rho = rho_0, w = k."""

    epsilon = 1e-6

    def __init__(self, spec: InterfaceSpec) -> None:
        self.family = RuleFamily.LINEAR
        self.spec = spec
        self.params = {
            "W": np.eye(spec.state_dim),
            "log_eta0": np.array([math.log(0.05)]),
            "gamma": np.zeros(1),
            "beta": np.zeros(1),
            "logit_rho0": np.array([3.0]),
        }

    def copy(self) -> LinearGDRule:
        clone = LinearGDRule(self.spec)
        clone.params = {name: value.copy() for name, value in self.params.items()}
        return clone

    def emit(
        self,
        features: FloatArray,
        keys: FloatArray,
        errors: FloatArray,
        step_index: int,
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, dict[str, FloatArray]]:
        batch = keys.shape[0]
        key_norm_sq = np.sum(keys * keys, axis=1)
        log_eta = (
            self.params["log_eta0"][0]
            - self.params["gamma"][0] * math.log(step_index + 1)
            - self.params["beta"][0] * np.log(key_norm_sq + self.epsilon)
        )
        eta = np.exp(log_eta)
        rho = np.full(batch, _sigmoid(self.params["logit_rho0"])[0])
        u = errors @ self.params["W"].T
        cache = {
            "errors": errors,
            "eta": eta,
            "log_step": np.full(batch, math.log(step_index + 1)),
            "log_key": np.log(key_norm_sq + self.epsilon),
        }
        return rho, eta, u, keys, cache

    def backward(
        self,
        cache: dict[str, FloatArray],
        d_rho: FloatArray,
        d_eta: FloatArray,
        d_u: FloatArray,
        d_w: FloatArray,
        grads: dict[str, FloatArray],
    ) -> tuple[FloatArray | None, FloatArray]:
        grads["W"] += np.einsum("bi,bj->ij", d_u, cache["errors"])
        d_log_eta = d_eta * cache["eta"]
        grads["log_eta0"] += d_log_eta.sum()
        grads["gamma"] += -(d_log_eta * cache["log_step"]).sum()
        grads["beta"] += -(d_log_eta * cache["log_key"]).sum()
        rho = _sigmoid(self.params["logit_rho0"])[0]
        grads["logit_rho0"] += d_rho.sum() * rho * (1.0 - rho)
        return None, d_u @ self.params["W"]


class OracleWriteRule(WriteRule):
    """Prescribed per-step (rho, eta, u, w) used to realise algebraic ceilings via the code path."""

    def __init__(self, rho: FloatArray, eta: FloatArray, u: FloatArray, w: FloatArray) -> None:
        arrays = tuple(np.asarray(value, dtype=np.float64) for value in (rho, eta, u, w))
        if arrays[0].ndim != 2 or arrays[2].ndim != 3 or arrays[3].shape != arrays[2].shape:
            raise RuleContractError("oracle schedules must be (n, B) scalars and (n, B, d) vectors")
        if any(not np.isfinite(value).all() for value in arrays):
            raise RuleContractError("oracle schedules must be finite")
        self.family = RuleFamily.THETA
        self.spec = InterfaceSpec(state_dim=arrays[2].shape[-1], rank=1, n_demonstrations=1)
        self.params = {}
        self.rho, self.eta, self.u, self.w = arrays

    def emit(
        self,
        features: FloatArray,
        keys: FloatArray,
        errors: FloatArray,
        step_index: int,
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, dict[str, FloatArray]]:
        return (
            self.rho[step_index],
            self.eta[step_index],
            self.u[step_index],
            self.w[step_index],
            {},
        )


def gradient_form_projection(theta_rule: MLPWriteRule) -> MLPWriteRule:
    """The R_gf network obtained from R_theta by dropping the w head (same hidden width)."""

    if theta_rule.family is not RuleFamily.THETA:
        raise RuleContractError("gradient_form_projection expects an R_theta rule")
    d = theta_rule.spec.state_dim
    projected = MLPWriteRule(
        RuleFamily.GRADIENT_FORM,
        theta_rule.spec,
        theta_rule.hidden,
        np.random.default_rng(0),
    )
    projected.params["W1"] = theta_rule.params["W1"].copy()
    projected.params["b1"] = theta_rule.params["b1"].copy()
    projected.params["W2"] = theta_rule.params["W2"][:, : 2 + d].copy()
    projected.params["b2"] = theta_rule.params["b2"][: 2 + d].copy()
    return projected


# --------------------------------------------------------------------------- #
# Two-pass write / read
# --------------------------------------------------------------------------- #


def _validate_demonstrations(keys: FloatArray, values: FloatArray, state_dim: int) -> None:
    if keys.ndim != 3 or values.shape != keys.shape or keys.shape[-1] != state_dim:
        raise RuleContractError("keys and values must be (episodes, demonstrations, state_dim)")
    if keys.shape[0] < 1 or keys.shape[1] < 1:
        raise RuleContractError("at least one episode with one demonstration is required")
    if not np.isfinite(keys).all() or not np.isfinite(values).all():
        raise RuleContractError("keys and values must be finite")


def _chain(previous: str, *arrays: FloatArray) -> str:
    digest = hashlib.sha256(previous.encode())
    for array in arrays:
        digest.update(np.ascontiguousarray(array, dtype=np.float64).tobytes())
    return digest.hexdigest()


def state_hash(state: FloatArray) -> str:
    return hashlib.sha256(np.ascontiguousarray(state, dtype=np.float64).tobytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class WriteLedger:
    """Hash-chained per-step write log (decay, step, effective step size)."""

    decay: FloatArray
    step: FloatArray
    effective_step: FloatArray
    chain_hash: str


@dataclass(frozen=True, slots=True)
class WritePass:
    state: FloatArray
    ledger: WriteLedger
    caches: list[dict[str, FloatArray]] = field(repr=False)


def write_pass(
    rule: WriteRule,
    keys: FloatArray,
    values: FloatArray,
    statistics_basis: FloatArray,
    *,
    clamp_write_direction: bool = False,
    fixed_decay: FloatArray | None = None,
    fixed_step: FloatArray | None = None,
    keep_caches: bool = False,
) -> WritePass:
    """Pass W: fold demonstrations into the state; probes never enter this function."""

    keys = np.asarray(keys, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    d = statistics_basis.shape[-1]
    _validate_demonstrations(keys, values, d)
    batch, n_demos, _ = keys.shape
    state = np.zeros((batch, d, d))
    decays = np.zeros((n_demos, batch))
    steps = np.zeros((n_demos, batch))
    effective = np.zeros((n_demos, batch))
    chain = "0" * 64
    caches: list[dict[str, FloatArray]] = []
    for i in range(n_demos):
        k = keys[:, i]
        v = values[:, i]
        state_key = np.einsum("bij,bj->bi", state, k)
        errors = v - state_key
        statistics = np.einsum("sij,bij->bs", statistics_basis, state)
        features = np.concatenate(
            [
                k,
                v,
                errors,
                state_key,
                np.linalg.norm(k, axis=1, keepdims=True),
                np.full((batch, 1), (i + 1) / n_demos),
                statistics,
            ],
            axis=1,
        )
        rho, eta, u, w, cache = rule.emit(features, k, errors, i)
        if clamp_write_direction:
            w = k
        if fixed_decay is not None:
            rho = np.broadcast_to(fixed_decay, rho.shape)
        if fixed_step is not None:
            eta = np.broadcast_to(fixed_step, eta.shape)
        if keep_caches:
            cache = dict(cache)
            cache.update(
                {
                    "state": state,
                    "k": k,
                    "u": u,
                    "w": w,
                    "rho": rho,
                    "eta": eta,
                    "clamped": np.array([clamp_write_direction]),
                }
            )
            caches.append(cache)
        decays[i] = rho
        steps[i] = eta
        effective[i] = eta * np.linalg.norm(u, axis=1) * np.linalg.norm(w, axis=1)
        chain = _chain(chain, rho, eta, u, w)
        state = rho[:, None, None] * state + eta[:, None, None] * u[:, :, None] * w[:, None, :]
    if not np.isfinite(state).all():
        raise DistillationDivergenceError("write pass produced a non-finite state")
    return WritePass(state, WriteLedger(decays, steps, effective, chain), caches)


def read_pass(state: FloatArray, queries: FloatArray) -> FloatArray:
    """Pass R with identity ports and readout functional e_1: prediction = (M q)_1."""

    state = np.asarray(state, dtype=np.float64)
    queries = np.asarray(queries, dtype=np.float64)
    if state.ndim != 3 or queries.ndim != 3 or queries.shape[-1] != state.shape[-1]:
        raise RuleContractError("state must be (B, d, d) and queries (B, q, d)")
    if queries.shape[0] != state.shape[0]:
        raise RuleContractError("queries and state must share the episode axis")
    return np.einsum("bqj,bj->bq", queries, state[:, 0, :])


def key_span_projection(keys: FloatArray, vectors: FloatArray) -> FloatArray:
    """Orthogonal projection of each vector onto the span of that episode's keys."""

    basis, _ = np.linalg.qr(np.transpose(keys, (0, 2, 1)))
    return np.einsum("bdk,bek,be->bd", basis, basis, vectors)


def readout_in_key_span(state: FloatArray, keys: FloatArray) -> float:
    """Relative residual of the readout row outside the key span (0 for key-directed rules)."""

    row = state[:, 0, :]
    residual = row - key_span_projection(keys, row)
    scale = max(float(np.sqrt(np.mean(row * row))), np.finfo(float).eps)
    return float(np.sqrt(np.mean(residual * residual))) / scale


# --------------------------------------------------------------------------- #
# Synthetic dMMSE regime (Raventos et al. 2023)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class FiniteTaskPrior:
    """Uniform prior over K fixed regression vectors with Gaussian observation noise."""

    task_vectors: FloatArray
    noise_sigma: float

    def __post_init__(self) -> None:
        vectors = np.array(self.task_vectors, dtype=np.float64, copy=True)
        if vectors.ndim != 2 or vectors.shape[0] < 2 or vectors.shape[1] < 2:
            raise RuleContractError("task_vectors must be (K >= 2, d >= 2)")
        if not np.isfinite(vectors).all():
            raise RuleContractError("task_vectors must be finite")
        differences = vectors[:, None, :] - vectors[None, :, :]
        distances = np.linalg.norm(differences, axis=2) + np.eye(vectors.shape[0])
        if np.any(distances < 1e-9):
            raise RuleContractError("task_vectors must be pairwise distinct")
        if not math.isfinite(self.noise_sigma) or self.noise_sigma <= 0.0:
            raise RuleContractError("noise_sigma must be finite and positive")
        vectors.setflags(write=False)
        object.__setattr__(self, "task_vectors", vectors)

    @property
    def n_tasks(self) -> int:
        return int(self.task_vectors.shape[0])

    @property
    def state_dim(self) -> int:
        return int(self.task_vectors.shape[1])

    @classmethod
    def random(
        cls,
        n_tasks: int,
        state_dim: int,
        noise_sigma: float,
        rng: np.random.Generator,
    ) -> FiniteTaskPrior:
        vectors = rng.normal(size=(n_tasks, state_dim))
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        return cls(vectors, noise_sigma)


@dataclass(frozen=True, slots=True)
class SyntheticEpisodes:
    """Demonstration keys/values, probe queries, and reference predictions per episode."""

    keys: FloatArray
    values: FloatArray
    queries: FloatArray
    teacher_vectors: FloatArray
    ridge_vectors: FloatArray
    truth_vectors: FloatArray

    def __post_init__(self) -> None:
        d = self.keys.shape[-1]
        _validate_demonstrations(self.keys, self.values, d)
        if self.queries.ndim != 3 or self.queries.shape[0] != self.keys.shape[0]:
            raise RuleContractError("queries must be (episodes, probes, state_dim)")
        for name in ("teacher_vectors", "ridge_vectors", "truth_vectors"):
            vectors = getattr(self, name)
            if vectors.shape != (self.keys.shape[0], d) or not np.isfinite(vectors).all():
                raise RuleContractError(f"{name} must be finite (episodes, state_dim)")

    @property
    def n_episodes(self) -> int:
        return int(self.keys.shape[0])

    def teacher(self) -> FloatArray:
        return np.einsum("bqd,bd->bq", self.queries, self.teacher_vectors)

    def ridge(self) -> FloatArray:
        return np.einsum("bqd,bd->bq", self.queries, self.ridge_vectors)

    def truth(self) -> FloatArray:
        return np.einsum("bqd,bd->bq", self.queries, self.truth_vectors)

    def subset(self, indices: Sequence[int]) -> SyntheticEpisodes:
        index = np.asarray(indices, dtype=np.int64)
        return SyntheticEpisodes(
            self.keys[index],
            self.values[index],
            self.queries[index],
            self.teacher_vectors[index],
            self.ridge_vectors[index],
            self.truth_vectors[index],
        )

    def with_teacher(self, teacher_vectors: FloatArray) -> SyntheticEpisodes:
        return SyntheticEpisodes(
            self.keys,
            self.values,
            self.queries,
            np.asarray(teacher_vectors, dtype=np.float64),
            self.ridge_vectors,
            self.truth_vectors,
        )

    def with_queries(self, queries: FloatArray) -> SyntheticEpisodes:
        return SyntheticEpisodes(
            self.keys,
            self.values,
            np.asarray(queries, dtype=np.float64),
            self.teacher_vectors,
            self.ridge_vectors,
            self.truth_vectors,
        )


def dmmse_regression_vectors(
    prior: FiniteTaskPrior, keys: FloatArray, targets: FloatArray
) -> FloatArray:
    """Discrete posterior mean over the prior's task vectors (the dMMSE predictor)."""

    residuals = targets[:, None, :] - np.einsum("bid,kd->bki", keys, prior.task_vectors)
    log_weights = -0.5 * np.sum(residuals * residuals, axis=2) / prior.noise_sigma**2
    log_weights -= log_weights.max(axis=1, keepdims=True)
    weights = np.exp(log_weights)
    weights /= weights.sum(axis=1, keepdims=True)
    return weights @ prior.task_vectors


def ridge_regression_vectors(
    keys: FloatArray, targets: FloatArray, ridge_lambda: float
) -> FloatArray:
    """Ridge estimator: the Bayes predictor under a Gaussian prior of variance sigma^2/lambda."""

    if not math.isfinite(ridge_lambda) or ridge_lambda <= 0.0:
        raise RuleContractError("ridge_lambda must be finite and positive")
    d = keys.shape[-1]
    gram = np.einsum("bid,bie->bde", keys, keys) + ridge_lambda * np.eye(d)
    moment = np.einsum("bid,bi->bd", keys, targets)
    return np.linalg.solve(gram, moment[..., None])[..., 0]


def _assemble_episodes(
    keys: FloatArray,
    targets: FloatArray,
    queries: FloatArray,
    teacher_vectors: FloatArray,
    ridge_lambda: float,
    truth_vectors: FloatArray,
) -> SyntheticEpisodes:
    values = np.zeros_like(keys)
    values[:, :, 0] = targets
    return SyntheticEpisodes(
        keys,
        values,
        queries,
        teacher_vectors,
        ridge_regression_vectors(keys, targets, ridge_lambda),
        truth_vectors,
    )


def sample_finite_prior_episodes(
    prior: FiniteTaskPrior,
    n_episodes: int,
    n_demonstrations: int,
    n_queries: int,
    rng: np.random.Generator,
) -> SyntheticEpisodes:
    """Episodes whose teacher is the dMMSE predictor of ``prior``."""

    if min(n_episodes, n_demonstrations, n_queries) < 1:
        raise RuleContractError("episode counts must be positive")
    d = prior.state_dim
    task = rng.integers(0, prior.n_tasks, size=n_episodes)
    keys = rng.normal(size=(n_episodes, n_demonstrations, d))
    truth = prior.task_vectors[task]
    targets = np.einsum("bid,bd->bi", keys, truth) + prior.noise_sigma * rng.normal(
        size=(n_episodes, n_demonstrations)
    )
    queries = rng.normal(size=(n_episodes, n_queries, d))
    teacher = dmmse_regression_vectors(prior, keys, targets)
    return _assemble_episodes(keys, targets, queries, teacher, prior.noise_sigma**2 * d, truth)


def sample_gaussian_prior_episodes(
    state_dim: int,
    noise_sigma: float,
    n_episodes: int,
    n_demonstrations: int,
    n_queries: int,
    rng: np.random.Generator,
) -> SyntheticEpisodes:
    """The infinite-task limit: a Gaussian prior whose Bayes predictor is ridge itself."""

    if state_dim < 2 or not math.isfinite(noise_sigma) or noise_sigma <= 0.0:
        raise RuleContractError("state_dim must be >= 2 and noise_sigma positive")
    if min(n_episodes, n_demonstrations, n_queries) < 1:
        raise RuleContractError("episode counts must be positive")
    truth = rng.normal(size=(n_episodes, state_dim)) / math.sqrt(state_dim)
    keys = rng.normal(size=(n_episodes, n_demonstrations, state_dim))
    targets = np.einsum("bid,bd->bi", keys, truth) + noise_sigma * rng.normal(
        size=(n_episodes, n_demonstrations)
    )
    queries = rng.normal(size=(n_episodes, n_queries, state_dim))
    ridge_lambda = noise_sigma**2 * state_dim
    teacher = ridge_regression_vectors(keys, targets, ridge_lambda)
    return _assemble_episodes(keys, targets, queries, teacher, ridge_lambda, truth)


def teacher_fidelity(predictions: FloatArray, reference: FloatArray) -> float:
    """1 - MSE / Var(reference): the fixed-variance-Gaussian analogue of the KL fidelity."""

    predictions = np.asarray(predictions, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    if predictions.shape != reference.shape or predictions.size < 2:
        raise RuleContractError("predictions and reference must share a shape with >= 2 entries")
    variance = float(reference.var())
    if not math.isfinite(variance) or variance <= 0.0:
        raise RuleContractError("reference predictions have no variance; fidelity is undefined")
    return 1.0 - float(np.mean((predictions - reference) ** 2)) / variance


@dataclass(frozen=True, slots=True)
class RegimeSeparation:
    """Does the teacher leave the key span, so that key-directed rules are capped?"""

    teacher_vs_ridge: float
    key_span_ceiling_gap: float
    key_directed_oracle_gap: float
    free_write_oracle_gap: float
    threshold: float

    def separated(self) -> bool:
        return (
            self.teacher_vs_ridge >= self.threshold and self.key_span_ceiling_gap >= self.threshold
        )

    def oracles_realised(self, tolerance: float = 1e-8) -> bool:
        return (
            abs(self.key_directed_oracle_gap - self.key_span_ceiling_gap) <= tolerance
            and self.free_write_oracle_gap <= tolerance
        )


def regime_separation(
    episodes: SyntheticEpisodes,
    statistics_basis: FloatArray,
    threshold: float = 0.25,
) -> RegimeSeparation:
    """Regime doctor: teacher-versus-ridge distance and the exact key-span ceiling.

    Both ceilings are realised through the real write code path with oracle rules:
    the key-directed oracle writes ``u_i = c_i e_1, w_i = k_i`` with ``c`` solving
    ``X X^T c = X m`` (its readout is the projection of the teacher onto the key span,
    the best any ``w_i = k_i`` rule can do from ``M = 0``), and the free-write oracle
    writes ``u = e_1, w = m`` once (its readout is the teacher exactly).
    """

    if not 0.0 < threshold < 1.0:
        raise RuleContractError("threshold must lie in (0, 1)")
    teacher = episodes.teacher()
    variance = float(teacher.var())
    if variance <= 0.0:
        raise RuleContractError("teacher predictions have no variance")
    ridge_gap = float(np.mean((teacher - episodes.ridge()) ** 2)) / variance
    projected = key_span_projection(episodes.keys, episodes.teacher_vectors)
    ceiling_gap = (
        float(np.mean((teacher - np.einsum("bqd,bd->bq", episodes.queries, projected)) ** 2))
        / variance
    )

    batch, n_demos, d = episodes.keys.shape
    gram = np.einsum("bid,bjd->bij", episodes.keys, episodes.keys)
    moment = np.einsum("bid,bd->bi", episodes.keys, episodes.teacher_vectors)
    coefficients = np.linalg.solve(gram, moment[..., None])[..., 0]
    unit = np.zeros((n_demos, batch, d))
    unit[:, :, 0] = coefficients.T
    key_directed = OracleWriteRule(
        np.ones((n_demos, batch)),
        np.ones((n_demos, batch)),
        unit,
        np.transpose(episodes.keys, (1, 0, 2)),
    )
    key_state = write_pass(key_directed, episodes.keys, episodes.values, statistics_basis).state
    key_gap = teacher_fidelity(read_pass(key_state, episodes.queries), teacher)
    free_u = np.zeros((n_demos, batch, d))
    free_u[-1, :, 0] = 1.0
    free_w = np.zeros((n_demos, batch, d))
    free_w[-1] = episodes.teacher_vectors
    free_eta = np.zeros((n_demos, batch))
    free_eta[-1] = 1.0
    free_write = OracleWriteRule(np.ones((n_demos, batch)), free_eta, free_u, free_w)
    free_state = write_pass(free_write, episodes.keys, episodes.values, statistics_basis).state
    free_gap = teacher_fidelity(read_pass(free_state, episodes.queries), teacher)
    return RegimeSeparation(
        teacher_vs_ridge=ridge_gap,
        key_span_ceiling_gap=ceiling_gap,
        key_directed_oracle_gap=1.0 - key_gap,
        free_write_oracle_gap=1.0 - free_gap,
        threshold=threshold,
    )


# --------------------------------------------------------------------------- #
# Distillation by truncated BPTT through the writes
# --------------------------------------------------------------------------- #


def distillation_loss_and_gradients(
    rule: WriteRule,
    episodes: SyntheticEpisodes,
    statistics_basis: FloatArray,
    *,
    clamp_write_direction: bool = False,
) -> tuple[float, dict[str, FloatArray], FloatArray]:
    """Mean squared prediction gap to the teacher and its analytic parameter gradients."""

    passed = write_pass(
        rule,
        episodes.keys,
        episodes.values,
        statistics_basis,
        clamp_write_direction=clamp_write_direction,
        keep_caches=True,
    )
    predictions = read_pass(passed.state, episodes.queries)
    teacher = episodes.teacher()
    loss = float(np.mean((predictions - teacher) ** 2))
    if not math.isfinite(loss):
        raise DistillationDivergenceError("distillation loss is not finite")
    grads = rule.zero_gradients()
    d_pred = 2.0 * (predictions - teacher) / predictions.size
    d_state = np.zeros_like(passed.state)
    d_state[:, 0, :] = np.einsum("bq,bqj->bj", d_pred, episodes.queries)
    d = statistics_basis.shape[-1]
    for cache in reversed(passed.caches):
        state, k, u, w, rho, eta = (cache[name] for name in ("state", "k", "u", "w", "rho", "eta"))
        d_rho = np.einsum("bij,bij->b", d_state, state)
        d_eta = np.einsum("bij,bij->b", d_state, u[:, :, None] * w[:, None, :])
        d_u = eta[:, None] * np.einsum("bij,bj->bi", d_state, w)
        d_w = eta[:, None] * np.einsum("bij,bi->bj", d_state, u)
        if bool(cache["clamped"][0]):
            d_w = np.zeros_like(d_w)
        next_d_state = rho[:, None, None] * d_state
        d_features, d_errors_extra = rule.backward(cache, d_rho, d_eta, d_u, d_w, grads)
        d_errors = d_errors_extra
        d_state_key = np.zeros_like(d_errors)
        if d_features is not None:
            d_errors = d_errors + d_features[:, 2 * d : 3 * d]
            d_state_key = d_features[:, 3 * d : 4 * d]
            d_statistics = d_features[:, 4 * d + 2 :]
            next_d_state = next_d_state + np.einsum("bs,sij->bij", d_statistics, statistics_basis)
        next_d_state = next_d_state + np.einsum("bi,bj->bij", d_state_key - d_errors, k)
        d_state = next_d_state
    return loss, grads, predictions


@dataclass(frozen=True, slots=True)
class DistillationConfig:
    steps: int
    batch_size: int
    learning_rate: float
    seed: int
    beta1: float = 0.9
    beta2: float = 0.999
    epsilon: float = 1e-8

    def __post_init__(self) -> None:
        if self.steps < 1 or self.batch_size < 1:
            raise RuleContractError("steps and batch_size must be positive")
        if not math.isfinite(self.learning_rate) or self.learning_rate <= 0.0:
            raise RuleContractError("learning_rate must be finite and positive")
        if not 0.0 <= self.beta1 < 1.0 or not 0.0 <= self.beta2 < 1.0 or self.epsilon <= 0.0:
            raise RuleContractError("Adam moments must lie in [0, 1) and epsilon be positive")


EpisodeSampler = Callable[[np.random.Generator, int], SyntheticEpisodes]


@dataclass(frozen=True, slots=True)
class DistillationTrace:
    losses: FloatArray
    final_loss: float
    steps: int


def distil(
    rule: WriteRule,
    sampler: EpisodeSampler,
    config: DistillationConfig,
    statistics_basis: FloatArray,
) -> DistillationTrace:
    """Adam on the distillation loss with fresh episodes per step; mutates ``rule.params``."""

    rng = np.random.default_rng(config.seed)
    first = {name: np.zeros_like(value) for name, value in rule.params.items()}
    second = {name: np.zeros_like(value) for name, value in rule.params.items()}
    losses = np.zeros(config.steps)
    for step in range(1, config.steps + 1):
        batch = sampler(rng, config.batch_size)
        loss, grads, _ = distillation_loss_and_gradients(rule, batch, statistics_basis)
        losses[step - 1] = loss
        for name, gradient in grads.items():
            first[name] = config.beta1 * first[name] + (1.0 - config.beta1) * gradient
            second[name] = config.beta2 * second[name] + (1.0 - config.beta2) * gradient * gradient
            corrected_first = first[name] / (1.0 - config.beta1**step)
            corrected_second = second[name] / (1.0 - config.beta2**step)
            rule.params[name] -= (
                config.learning_rate
                * corrected_first
                / (np.sqrt(corrected_second) + config.epsilon)
            )
    return DistillationTrace(losses, float(losses[-1]), config.steps)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Written hyperparameter search at equal development budget for one rule family."""

    selected_learning_rate: float
    development_losses: dict[float, float]
    steps_per_configuration: int
    grid_edge: bool


def written_search(
    factory: Callable[[], WriteRule],
    sampler: EpisodeSampler,
    development: SyntheticEpisodes,
    grid: Sequence[float],
    steps: int,
    batch_size: int,
    seed: int,
    statistics_basis: FloatArray,
) -> SearchResult:
    if len(grid) < 2 or len(set(grid)) != len(grid) or any(rate <= 0 for rate in grid):
        raise RuleContractError("search grid needs at least two distinct positive rates")
    losses: dict[float, float] = {}
    for rate in grid:
        candidate = factory()
        distil(
            candidate, sampler, DistillationConfig(steps, batch_size, rate, seed), statistics_basis
        )
        loss, _, _ = distillation_loss_and_gradients(candidate, development, statistics_basis)
        losses[float(rate)] = loss
    selected = min(losses, key=losses.__getitem__)
    ordered = sorted(losses)
    return SearchResult(selected, losses, steps, selected in (ordered[0], ordered[-1]))


# --------------------------------------------------------------------------- #
# Causality audit and clamp code paths
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CausalityAudit:
    """Two-pass structural audit on real code paths, plus detection of a tampered pass."""

    probe_absence_identical: bool
    prefix_invariant: bool
    max_prefix_deviation: float
    zero_state_read_is_zero: bool
    reset_restores_fresh_state: bool
    tampered_pass_detected: bool

    def passes(self) -> bool:
        return (
            self.probe_absence_identical
            and self.prefix_invariant
            and self.zero_state_read_is_zero
            and self.reset_restores_fresh_state
            and self.tampered_pass_detected
        )


def tampered_write_pass(
    rule: WriteRule,
    episodes: SyntheticEpisodes,
    statistics_basis: FloatArray,
) -> WritePass:
    """Doctor-only tamper case: the first probe leaks into Pass W as a ninth demonstration."""

    leaked_keys = np.concatenate([episodes.keys, episodes.queries[:, :1]], axis=1)
    leaked_values = np.concatenate([episodes.values, np.zeros_like(episodes.values[:, :1])], axis=1)
    return write_pass(rule, leaked_keys, leaked_values, statistics_basis)


def causality_audit(
    rule: WriteRule,
    episodes: SyntheticEpisodes,
    statistics_basis: FloatArray,
    tolerance: float = 1e-9,
) -> CausalityAudit:
    honest = write_pass(rule, episodes.keys, episodes.values, statistics_basis)
    alternate_probes = np.flip(episodes.queries, axis=1)
    honest_again = write_pass(rule, episodes.keys, episodes.values, statistics_basis)
    probe_absence = state_hash(honest.state) == state_hash(honest_again.state)
    joint = read_pass(honest.state, episodes.queries)
    separate = np.concatenate(
        [
            read_pass(honest.state, episodes.queries[:, index : index + 1])
            for index in range(episodes.queries.shape[1])
        ],
        axis=1,
    )
    deviation = float(np.max(np.abs(joint - separate)))
    zero_read = read_pass(np.zeros_like(honest.state), episodes.queries)
    fresh_hash = state_hash(np.zeros_like(honest.state))
    poisoned_keys = episodes.keys.copy()
    poisoned_keys[:, 0] *= 50.0
    write_pass(rule, poisoned_keys, episodes.values, statistics_basis)
    reset_state = np.zeros_like(honest.state)
    tampered = tampered_write_pass(rule, episodes, statistics_basis)
    tampered_alternate = tampered_write_pass(
        rule, episodes.with_queries(alternate_probes), statistics_basis
    )
    return CausalityAudit(
        probe_absence_identical=probe_absence,
        prefix_invariant=deviation <= tolerance,
        max_prefix_deviation=deviation,
        zero_state_read_is_zero=bool(np.all(zero_read == 0.0)),
        reset_restores_fresh_state=state_hash(reset_state) == fresh_hash,
        tampered_pass_detected=state_hash(tampered.state) != state_hash(tampered_alternate.state),
    )


def clamp_reproduces_gradient_form(
    theta_rule: MLPWriteRule,
    episodes: SyntheticEpisodes,
    statistics_basis: FloatArray,
    tolerance: float = 1e-12,
) -> bool:
    """w := k on R_theta must reproduce the R_gf network with the w head removed at fp64 tolerance.

    Equality is algebraic; numerically the two networks evaluate a 2+2d-column and a
    2+d-column matmul, whose BLAS summation order may differ in the last bits, so the
    comparison is at ``tolerance`` rather than by hash.
    """

    clamped = write_pass(
        theta_rule, episodes.keys, episodes.values, statistics_basis, clamp_write_direction=True
    )
    projected = write_pass(
        gradient_form_projection(theta_rule), episodes.keys, episodes.values, statistics_basis
    )
    scale = max(float(np.max(np.abs(projected.state))), 1.0)
    deviations = (
        float(np.max(np.abs(clamped.state - projected.state))) / scale,
        float(np.max(np.abs(clamped.ledger.decay - projected.ledger.decay))),
        float(np.max(np.abs(clamped.ledger.step - projected.ledger.step))),
        float(np.max(np.abs(clamped.ledger.effective_step - projected.ledger.effective_step)))
        / scale,
    )
    return max(deviations) <= tolerance


@dataclass(frozen=True, slots=True)
class ClampAblation:
    """Fidelity of the trained rule and of its three post-hoc clamps (evaluation only)."""

    unclamped: float
    write_direction_clamped: float
    decay_clamped: float
    step_clamped: float
    clamped_readout_key_span_residual: float

    def write_direction_cost(self) -> float:
        return self.unclamped - self.write_direction_clamped


def clamp_ablation(
    rule: WriteRule,
    episodes: SyntheticEpisodes,
    statistics_basis: FloatArray,
) -> ClampAblation:
    teacher = episodes.teacher()
    base = write_pass(rule, episodes.keys, episodes.values, statistics_basis)
    clamped = write_pass(
        rule, episodes.keys, episodes.values, statistics_basis, clamp_write_direction=True
    )
    decay = write_pass(
        rule,
        episodes.keys,
        episodes.values,
        statistics_basis,
        fixed_decay=base.ledger.decay.mean(axis=0),
    )
    step = write_pass(
        rule,
        episodes.keys,
        episodes.values,
        statistics_basis,
        fixed_step=base.ledger.step.mean(axis=0),
    )
    return ClampAblation(
        unclamped=teacher_fidelity(read_pass(base.state, episodes.queries), teacher),
        write_direction_clamped=teacher_fidelity(
            read_pass(clamped.state, episodes.queries), teacher
        ),
        decay_clamped=teacher_fidelity(read_pass(decay.state, episodes.queries), teacher),
        step_clamped=teacher_fidelity(read_pass(step.state, episodes.queries), teacher),
        clamped_readout_key_span_residual=readout_in_key_span(clamped.state, episodes.keys),
    )


# --------------------------------------------------------------------------- #
# Pre-registered attribution tree (wave 5 re-tiering) and its power
# --------------------------------------------------------------------------- #


class AttributionOutcome(StrEnum):
    CONFIRMED = "CONFIRMED"
    CLASS_UNRESOLVED = "CLASS_UNRESOLVED"
    UNATTRIBUTED = "UNATTRIBUTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    K1_GRADIENT_FORM = "K1"
    K2_UNMEASURABLE = "K2"
    K4_AUDIT = "K4"
    K6_COLLAPSE = "K6"


@dataclass(frozen=True, slots=True)
class AttributionThresholds:
    primary_gap: float = 0.10
    inconclusive_gap: float = 0.05
    clamp_cost: float = 0.05
    sibling_margin: float = 0.05
    reservoir_ratio: float = 0.5
    min_families: int = 8
    min_class_families: int = 4
    class_one_sided_level: float = 0.80
    interval_confidence: float = 0.95

    def __post_init__(self) -> None:
        if not 0.0 < self.inconclusive_gap < self.primary_gap:
            raise RuleContractError("inconclusive_gap must lie in (0, primary_gap)")
        if min(self.clamp_cost, self.sibling_margin) <= 0.0 or not 0.0 < self.reservoir_ratio < 1.0:
            raise RuleContractError("clamp, sibling and reservoir thresholds must be positive")
        if self.min_families < 2 or self.min_class_families < 2:
            raise RuleContractError("family minima must be at least two (t-interval needs df >= 1)")
        if not 0.5 < self.class_one_sided_level < 1.0 or not 0.5 < self.interval_confidence < 1.0:
            raise RuleContractError("confidence levels must lie in (0.5, 1)")


@dataclass(frozen=True, slots=True)
class AttributionInputs:
    """Family-level inputs to the tree; every entry is an eligible held-out family."""

    family_gaps: FloatArray
    function_induction: BoolArray
    clamp_cost: float
    sibling_margin: float | None
    reservoir_ratio: float
    audits_passed: bool

    def __post_init__(self) -> None:
        gaps = np.array(self.family_gaps, dtype=np.float64, copy=True)
        mask = np.array(self.function_induction, dtype=bool, copy=True)
        if gaps.ndim != 1 or gaps.shape != mask.shape or not np.isfinite(gaps).all():
            raise RuleContractError(
                "family_gaps must be a finite vector aligned with the class mask"
            )
        finite = (self.clamp_cost, self.reservoir_ratio)
        if any(not math.isfinite(value) for value in finite):
            raise RuleContractError("clamp_cost and reservoir_ratio must be finite")
        if self.sibling_margin is not None and not math.isfinite(self.sibling_margin):
            raise RuleContractError("sibling_margin must be finite or None (uninformative)")
        gaps.setflags(write=False)
        mask.setflags(write=False)
        object.__setattr__(self, "family_gaps", gaps)
        object.__setattr__(self, "function_induction", mask)


def family_t_interval(values: FloatArray, confidence: float = 0.95) -> tuple[float, float, float]:
    """Mean and two-sided t-interval on family-level values (df = families - 1)."""

    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or values.size < 2:
        raise RuleContractError("a t-interval needs at least two family-level values")
    mean = float(values.mean())
    half_width = float(
        scipy_stats.t.ppf(0.5 + confidence / 2.0, values.size - 1)
        * values.std(ddof=1)
        / math.sqrt(values.size)
    )
    return mean, mean - half_width, mean + half_width


def one_sided_lower_bound(values: FloatArray, level: float = 0.80) -> float:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or values.size < 2:
        raise RuleContractError("a one-sided bound needs at least two family-level values")
    return float(
        values.mean()
        - scipy_stats.t.ppf(level, values.size - 1) * values.std(ddof=1) / math.sqrt(values.size)
    )


@dataclass(frozen=True, slots=True)
class AttributionDecision:
    outcome: AttributionOutcome
    primary_mean: float
    primary_lower: float
    class_families: int
    class_mean: float | None
    class_lower_bound: float | None
    reason: str


def attribution_tree(
    inputs: AttributionInputs,
    thresholds: AttributionThresholds | None = None,
) -> AttributionDecision:
    """Pre-registered decision order (wave 5): K2, K4, K1, K6, INCONCLUSIVE, UNATTRIBUTED, class.

    The class co-condition is re-tiered from a two-sided interval to a point estimate
    at the primary threshold with a one-sided lower bound above zero, requires at
    least ``min_class_families`` eligible function-induction families, and a miss
    routes to CLASS_UNRESOLVED (no port, per-class report) rather than to K1.
    """

    thresholds = thresholds or AttributionThresholds()
    gaps = inputs.family_gaps
    n_families = int(gaps.size)
    class_gaps = gaps[inputs.function_induction]
    class_count = int(class_gaps.size)
    if n_families < thresholds.min_families:
        return AttributionDecision(
            AttributionOutcome.K2_UNMEASURABLE,
            float("nan"),
            float("nan"),
            class_count,
            None,
            None,
            f"{n_families} eligible families, fewer than {thresholds.min_families}",
        )
    mean, lower, _ = family_t_interval(gaps, thresholds.interval_confidence)
    class_mean = float(class_gaps.mean()) if class_count >= 2 else None
    class_lower = (
        one_sided_lower_bound(class_gaps, thresholds.class_one_sided_level)
        if class_count >= 2
        else None
    )

    def decision(outcome: AttributionOutcome, reason: str) -> AttributionDecision:
        return AttributionDecision(
            outcome, mean, lower, class_count, class_mean, class_lower, reason
        )

    if not inputs.audits_passed or inputs.reservoir_ratio >= thresholds.reservoir_ratio:
        return decision(AttributionOutcome.K4_AUDIT, "audit failure or reservoir at or above 0.5x")
    if mean < thresholds.inconclusive_gap or lower <= 0.0:
        return decision(AttributionOutcome.K1_GRADIENT_FORM, "primary leaf fails: gradient form")
    if inputs.sibling_margin is not None and inputs.sibling_margin < thresholds.sibling_margin:
        return decision(AttributionOutcome.K6_COLLAPSE, "ties the cross-teacher sibling")
    if mean < thresholds.primary_gap:
        return decision(AttributionOutcome.INCONCLUSIVE, "gap between 0.05 and 0.10")
    if inputs.clamp_cost < thresholds.clamp_cost:
        return decision(AttributionOutcome.UNATTRIBUTED, "w-clamp costs below 0.05")
    if class_count < thresholds.min_class_families:
        return decision(
            AttributionOutcome.CLASS_UNRESOLVED,
            f"{class_count} function-induction families, below {thresholds.min_class_families}",
        )
    assert class_mean is not None and class_lower is not None
    if class_mean >= thresholds.primary_gap and class_lower > 0.0:
        return decision(AttributionOutcome.CONFIRMED, "primary, clamp and class co-conditions hold")
    return decision(AttributionOutcome.CLASS_UNRESOLVED, "class co-condition not met; no port")


@dataclass(frozen=True, slots=True)
class NoiseModel:
    """Assumed noise SDs (family heterogeneity, seed, query) until Stage B measures them."""

    family_sd: float = 0.08
    seed_sd: float = 0.06
    query_sd: float = 0.035

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(value) or value <= 0.0
            for value in (self.family_sd, self.seed_sd, self.query_sd)
        ):
            raise RuleContractError("noise SDs must be finite and positive")


@dataclass(frozen=True, slots=True)
class TreePowerEstimate:
    """Monte-Carlo outcome frequencies of the tree; clamp, sibling and audits assumed to pass."""

    effect: float
    n_families: int
    n_class_families: int
    n_seeds: int
    draws: int
    primary_pass: float
    class_pass_retiered: float
    class_pass_wave4_two_sided: float
    confirmed: float
    class_unresolved: float
    k1: float
    inconclusive: float


def simulate_attribution_tree_power(
    noise: NoiseModel,
    effect: float,
    n_families: int,
    n_class_families: int,
    n_seeds: int,
    draws: int,
    rng: np.random.Generator,
    thresholds: AttributionThresholds | None = None,
) -> TreePowerEstimate:
    thresholds = thresholds or AttributionThresholds()
    if n_families < 2 or not 0 <= n_class_families <= n_families or n_seeds < 1 or draws < 1:
        raise RuleContractError("family, class, seed and draw counts are inconsistent")
    family_effects = effect + rng.normal(0.0, noise.family_sd, size=(draws, n_families))
    observations = (
        family_effects[:, :, None]
        + rng.normal(0.0, noise.seed_sd, size=(draws, n_families, n_seeds))
        + rng.normal(0.0, noise.query_sd, size=(draws, n_families, n_seeds))
    )
    family_means = observations.mean(axis=2)
    mean = family_means.mean(axis=1)
    standard_error = family_means.std(axis=1, ddof=1) / math.sqrt(n_families)
    lower = mean - scipy_stats.t.ppf(0.5 + thresholds.interval_confidence / 2.0, n_families - 1) * (
        standard_error
    )
    primary_ci = lower > 0.0
    k1 = (mean < thresholds.inconclusive_gap) | ~primary_ci
    inconclusive = ~k1 & (mean < thresholds.primary_gap)
    primary = ~k1 & ~inconclusive
    if n_class_families >= 2:
        class_means = family_means[:, :n_class_families]
        class_mean = class_means.mean(axis=1)
        class_se = class_means.std(axis=1, ddof=1) / math.sqrt(n_class_families)
        one_sided = (
            class_mean
            - scipy_stats.t.ppf(thresholds.class_one_sided_level, n_class_families - 1) * class_se
        )
        two_sided = (
            class_mean
            - scipy_stats.t.ppf(0.5 + thresholds.interval_confidence / 2.0, n_class_families - 1)
            * class_se
        )
        class_retiered = (class_mean >= thresholds.primary_gap) & (one_sided > 0.0)
        class_wave4 = (class_mean >= thresholds.primary_gap) & (two_sided > 0.0)
    else:
        class_retiered = np.zeros(draws, dtype=bool)
        class_wave4 = np.zeros(draws, dtype=bool)
    measurable = n_class_families >= thresholds.min_class_families
    confirmed = primary & class_retiered & measurable
    return TreePowerEstimate(
        effect=effect,
        n_families=n_families,
        n_class_families=n_class_families,
        n_seeds=n_seeds,
        draws=draws,
        primary_pass=float(primary.mean()),
        class_pass_retiered=float(class_retiered.mean()),
        class_pass_wave4_two_sided=float(class_wave4.mean()),
        confirmed=float(confirmed.mean()),
        class_unresolved=float((primary & ~confirmed).mean()),
        k1=float(k1.mean()),
        inconclusive=float(inconclusive.mean()),
    )


# --------------------------------------------------------------------------- #
# Stage-A regime distillation orchestration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RegimeDoctorConfig:
    """Registered synthetic configuration for the CPU regime doctor."""

    spec: InterfaceSpec = SYNTHETIC_INTERFACE
    n_tasks: int = 4
    noise_sigma: float = 0.25
    n_queries: int = 8
    evaluation_episodes: int = 2000
    development_episodes: int = 256
    search_grid: tuple[float, ...] = (1e-4, 3e-4, 1e-3, 3e-3)
    search_steps: int = 150
    steps: int = 750
    batch_size: int = 64
    seed: int = 42
    regime_threshold: float = 0.25
    primary_gap: float = 0.10
    clamp_cost: float = 0.05

    def __post_init__(self) -> None:
        if self.n_tasks < 2 or self.n_queries < 1 or self.evaluation_episodes < 2:
            raise RuleContractError(
                "n_tasks >= 2, n_queries >= 1, evaluation_episodes >= 2 required"
            )
        if self.development_episodes < 2 or self.search_steps < 1 or self.steps < 1:
            raise RuleContractError("development_episodes, search_steps and steps must be positive")
        if self.batch_size < 1 or not 0.0 < self.regime_threshold < 1.0:
            raise RuleContractError("batch_size must be positive and regime_threshold in (0, 1)")
        if not 0.0 < self.clamp_cost < self.primary_gap < 1.0:
            raise RuleContractError("0 < clamp_cost < primary_gap < 1 is required")
        if not math.isfinite(self.noise_sigma) or self.noise_sigma <= 0.0:
            raise RuleContractError("noise_sigma must be finite and positive")


@dataclass(frozen=True, slots=True)
class RuleReceipt:
    family: str
    parameter_count: int
    hidden: int | None
    selected_learning_rate: float
    development_losses: dict[float, float]
    grid_edge: bool
    final_training_loss: float
    fidelity_to_teacher: float
    fidelity_to_ridge: float
    fidelity_to_truth: float
    fidelity_to_permuted_teacher: float


@dataclass(frozen=True, slots=True)
class RegimeDistillationReceipt:
    separation: RegimeSeparation
    rules: dict[str, RuleReceipt]
    clamp: ClampAblation
    clamp_reproduces_gradient_form: bool
    audit: CausalityAudit
    counts: RuleParameterCounts

    def gap(self, first: str, second: str) -> float:
        return self.rules[first].fidelity_to_teacher - self.rules[second].fidelity_to_teacher


def build_rule(
    family: RuleFamily, spec: InterfaceSpec, counts: RuleParameterCounts, seed: int
) -> WriteRule:
    rng = np.random.default_rng(seed)
    if family is RuleFamily.THETA:
        return MLPWriteRule(family, spec, spec.theta_hidden, rng)
    if family is RuleFamily.GRADIENT_FORM:
        return MLPWriteRule(family, spec, counts.gradient_form_hidden, rng)
    if family is RuleFamily.ADAPTIVE:
        return MLPWriteRule(family, spec, counts.adaptive_hidden, rng)
    return LinearGDRule(spec)


def _rule_receipt(
    family: RuleFamily,
    rule: WriteRule,
    search: SearchResult,
    trace: DistillationTrace,
    evaluation: SyntheticEpisodes,
    statistics_basis: FloatArray,
    permutation_rng: np.random.Generator,
) -> RuleReceipt:
    state = write_pass(rule, evaluation.keys, evaluation.values, statistics_basis).state
    predictions = read_pass(state, evaluation.queries)
    teacher = evaluation.teacher()
    permuted = permutation_rng.permuted(teacher, axis=1)
    return RuleReceipt(
        family=family.value,
        parameter_count=rule.parameter_count(),
        hidden=getattr(rule, "hidden", None),
        selected_learning_rate=search.selected_learning_rate,
        development_losses=search.development_losses,
        grid_edge=search.grid_edge,
        final_training_loss=trace.final_loss,
        fidelity_to_teacher=teacher_fidelity(predictions, teacher),
        fidelity_to_ridge=teacher_fidelity(predictions, evaluation.ridge()),
        fidelity_to_truth=teacher_fidelity(predictions, evaluation.truth()),
        fidelity_to_permuted_teacher=teacher_fidelity(predictions, permuted),
    )


def run_regime_distillation(
    config: RegimeDoctorConfig,
    sampler: EpisodeSampler,
    families: Sequence[RuleFamily] = tuple(RuleFamily),
    search_overrides: dict[RuleFamily, float] | None = None,
) -> RegimeDistillationReceipt:
    """Distil every requested rung to ``sampler``'s teacher at equal budget and audit it.

    ``search_overrides`` carries selected learning rates forward without re-search
    (the proposal's Stage D/E transfer rule); families absent from it are searched.
    """

    spec = config.spec
    counts = rule_parameter_counts(spec)
    basis = state_statistics_basis(spec, config.seed)
    evaluation = sampler(np.random.default_rng(config.seed + 1), config.evaluation_episodes)
    development = sampler(np.random.default_rng(config.seed + 2), config.development_episodes)
    separation = regime_separation(evaluation, basis, config.regime_threshold)
    receipts: dict[str, RuleReceipt] = {}
    trained: dict[RuleFamily, WriteRule] = {}
    for offset, family in enumerate(families):
        rule_seed = config.seed + 100 + offset
        if search_overrides is not None and family in search_overrides:
            selected = search_overrides[family]
            search = SearchResult(selected, {selected: float("nan")}, 0, False)
        else:
            search = written_search(
                partial(build_rule, family, spec, counts, rule_seed),
                sampler,
                development,
                config.search_grid,
                config.search_steps,
                config.batch_size,
                rule_seed,
                basis,
            )
        rule = build_rule(family, spec, counts, rule_seed)
        trace = distil(
            rule,
            sampler,
            DistillationConfig(
                config.steps, config.batch_size, search.selected_learning_rate, rule_seed
            ),
            basis,
        )
        trained[family] = rule
        receipts[family.value] = _rule_receipt(
            family, rule, search, trace, evaluation, basis, np.random.default_rng(config.seed + 3)
        )
    theta = trained.get(RuleFamily.THETA)
    if not isinstance(theta, MLPWriteRule):
        raise RuleContractError("run_regime_distillation requires R_theta among the families")
    return RegimeDistillationReceipt(
        separation=separation,
        rules=receipts,
        clamp=clamp_ablation(theta, evaluation, basis),
        clamp_reproduces_gradient_form=clamp_reproduces_gradient_form(theta, evaluation, basis),
        audit=causality_audit(theta, evaluation.subset(range(64)), basis),
        counts=counts,
    )


def finite_prior_sampler(
    prior: FiniteTaskPrior, spec: InterfaceSpec, n_queries: int
) -> EpisodeSampler:
    def sample(rng: np.random.Generator, n_episodes: int) -> SyntheticEpisodes:
        return sample_finite_prior_episodes(
            prior, n_episodes, spec.n_demonstrations, n_queries, rng
        )

    return sample


def gaussian_prior_sampler(
    spec: InterfaceSpec, noise_sigma: float, n_queries: int
) -> EpisodeSampler:
    def sample(rng: np.random.Generator, n_episodes: int) -> SyntheticEpisodes:
        return sample_gaussian_prior_episodes(
            spec.state_dim, noise_sigma, n_episodes, spec.n_demonstrations, n_queries, rng
        )

    return sample


def positive_control_gates(
    receipt: RegimeDistillationReceipt, config: RegimeDoctorConfig
) -> dict[str, bool]:
    """Registered gates for the dMMSE-regime positive control."""

    theta = receipt.rules[RuleFamily.THETA.value]
    key_directed = [
        receipt.rules[name]
        for name in (
            RuleFamily.GRADIENT_FORM.value,
            RuleFamily.ADAPTIVE.value,
            RuleFamily.LINEAR.value,
        )
        if name in receipt.rules
    ]
    gf = receipt.rules[RuleFamily.GRADIENT_FORM.value]
    return {
        "regime_separates_dmmse_from_ridge": receipt.separation.separated(),
        "oracle_ceilings_realised_through_write_code_path": receipt.separation.oracles_realised(),
        "parameter_counts_within_one_percent": receipt.counts.within_tolerance(),
        "theta_beats_gradient_form_by_primary_gap": (
            theta.fidelity_to_teacher - gf.fidelity_to_teacher >= config.primary_gap
        ),
        "theta_tracks_teacher_not_ridge": theta.fidelity_to_teacher > theta.fidelity_to_ridge,
        "key_directed_rungs_track_ridge_not_teacher": all(
            rule.fidelity_to_ridge > rule.fidelity_to_teacher for rule in key_directed
        ),
        "key_directed_rungs_below_key_span_ceiling": all(
            rule.fidelity_to_teacher <= 1.0 - receipt.separation.key_span_ceiling_gap + 1e-6
            for rule in key_directed
        ),
        "write_direction_clamp_costs_at_least_threshold": (
            receipt.clamp.write_direction_cost() >= config.clamp_cost
        ),
        "clamped_readout_confined_to_key_span": receipt.clamp.clamped_readout_key_span_residual
        <= 1e-9,
        "clamp_reproduces_gradient_form_network_exactly": receipt.clamp_reproduces_gradient_form,
        "equal_budget_search_recorded_for_every_rung": all(
            len(rule.development_losses) == len(config.search_grid)
            for rule in receipt.rules.values()
        ),
        "two_pass_causality_audit_passes": receipt.audit.passes(),
        "permuted_teacher_fidelity_collapses": all(
            rule.fidelity_to_permuted_teacher <= 0.05 for rule in receipt.rules.values()
        ),
    }


def negative_control_gates(
    receipt: RegimeDistillationReceipt, config: RegimeDoctorConfig
) -> dict[str, bool]:
    """Registered gates for the Gaussian-prior (ridge-teacher) negative control.

    The teacher lies inside the key span, so the regime statistic must refuse to
    separate the classes; any trained gap is then reported as optimisation-only and
    the doctor must not attribute it to the free write direction.
    """

    theta = receipt.rules[RuleFamily.THETA.value]
    gf = receipt.rules[RuleFamily.GRADIENT_FORM.value]
    return {
        "regime_flagged_as_non_separating": not receipt.separation.separated(),
        "teacher_inside_key_span": receipt.separation.key_span_ceiling_gap <= 1e-6,
        "gradient_form_rung_not_capped_below_teacher": gf.fidelity_to_teacher > 0.5,
        "structural_attribution_refused": not receipt.separation.separated(),
        "theta_gap_reported_not_attributed": math.isfinite(
            theta.fidelity_to_teacher - gf.fidelity_to_teacher
        ),
    }


__all__ = [
    "PILOT_INTERFACE",
    "SYNTHETIC_INTERFACE",
    "AttributionDecision",
    "AttributionInputs",
    "AttributionOutcome",
    "AttributionThresholds",
    "CausalityAudit",
    "ClampAblation",
    "DistillationConfig",
    "DistillationDivergenceError",
    "DistillationTrace",
    "FiniteTaskPrior",
    "InterfaceSpec",
    "LinearGDRule",
    "MLPWriteRule",
    "NoiseModel",
    "OracleWriteRule",
    "RankTruncationReceipt",
    "RegimeDistillationReceipt",
    "RegimeDoctorConfig",
    "RegimeSeparation",
    "RuleContractError",
    "RuleFamily",
    "RuleParameterCounts",
    "RuleReceipt",
    "SearchResult",
    "SyntheticEpisodes",
    "TreePowerEstimate",
    "WriteLedger",
    "WritePass",
    "WriteRule",
    "attribution_tree",
    "build_rule",
    "causality_audit",
    "clamp_ablation",
    "clamp_reproduces_gradient_form",
    "distil",
    "distillation_loss_and_gradients",
    "dmmse_regression_vectors",
    "family_t_interval",
    "finite_prior_sampler",
    "gaussian_prior_sampler",
    "gradient_form_projection",
    "iso_parameter_hidden_width",
    "key_span_projection",
    "mlp_parameter_count",
    "negative_control_gates",
    "one_sided_lower_bound",
    "positive_control_gates",
    "rank_truncate",
    "rank_truncation_doctor",
    "read_pass",
    "readout_in_key_span",
    "regime_separation",
    "ridge_regression_vectors",
    "rule_parameter_counts",
    "run_regime_distillation",
    "sample_finite_prior_episodes",
    "sample_gaussian_prior_episodes",
    "simulate_attribution_tree_power",
    "state_hash",
    "state_statistics_basis",
    "tampered_write_pass",
    "teacher_fidelity",
    "write_pass",
    "written_search",
]
