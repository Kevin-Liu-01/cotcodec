"""Phase-0 objects for Direction 22: translation-equivariant state writes.

Model-free and NumPy-only. Nothing here touches a checkpoint, a corpus, a
tokenizer, an fla kernel or a GPU. The module turns the objects the proposal
pre-registers into typed, validated functions so the registered gates can be
exercised on synthetic inputs before any GPU-hour is spent:

* the Gated DeltaNet head recurrence ``S_t = S_{t-1} a_t (I - b_t k_t k_t^T) + b_t v_t k_t^T``
  in the ``v k^T`` convention (state ``[d_v, d_k]``; fla stores the transpose);
* the pure write ``W(a|c) = S(c+a) - S_{v=0}(c,a)`` (decay and erase kept, writes
  removed), the wave-2 segment delta ``D = S(c+a) - S(c)``, and the A2 control
  ``P(a) = sum_t b_t v_t k_t^T``;
* the fp64 identity ``W == S_{S0=0}(a)``, the prefix-floor ledger (``W`` versus
  ``D``), the G2 distinctness statistic ``mean cos(W, P)``, and the write-norm
  falsifier;
* a seeded two-layer NumPy GDN with a two-language vocabulary that yields
  synthetic translation pairs behind a bitwise-shared prefix;
* synthetic TP-MQAR-v2 prompts with the retrieval-impossible and
  value-permutation leakage controls and the surface-disjoint key filter;
* the phase-1 promotion-rule simulation requested by the wave-4 reviewers.

Passing the doctor built on this module proves executability and gate
semantics only. Every number it produces is a synthetic-case number.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.stats import norm

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


class StateWriteContractError(ValueError):
    """Raised when a span, state, prompt or configuration violates the contract."""


# --------------------------------------------------------------------------- spans


def _finite_array(values: object, *, name: str, ndim: int) -> FloatArray:
    array = np.array(values, dtype=np.float64, copy=True)
    if array.ndim != ndim or not array.size:
        raise StateWriteContractError(f"{name} must be a non-empty {ndim}-d array")
    if not np.isfinite(array).all():
        raise StateWriteContractError(f"{name} must be finite")
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class HeadSpan:
    """Realized per-head GDN projections over one token span (fla convention).

    ``keys`` are ``[T, d_k]``, ``values`` are ``[T, d_v]``, ``beta`` is the write
    strength in ``[0, 1]`` and ``alpha`` the decay in ``(0, 1]``. The span is the
    object the second ``chunk_gated_delta_rule`` call in the proposal consumes:
    the same ``k``, ``alpha`` and ``beta`` with the values optionally zeroed.
    """

    keys: FloatArray
    values: FloatArray
    beta: FloatArray
    alpha: FloatArray
    identity: str = ""

    def __post_init__(self) -> None:
        keys = _finite_array(self.keys, name="keys", ndim=2)
        values = _finite_array(self.values, name="values", ndim=2)
        beta = _finite_array(self.beta, name="beta", ndim=1)
        alpha = _finite_array(self.alpha, name="alpha", ndim=1)
        length = keys.shape[0]
        if values.shape[0] != length or beta.shape[0] != length or alpha.shape[0] != length:
            raise StateWriteContractError("keys, values, beta and alpha must share the span length")
        if np.any(beta < 0.0) or np.any(beta > 1.0):
            raise StateWriteContractError("beta must lie in [0, 1]")
        if np.any(alpha <= 0.0) or np.any(alpha > 1.0):
            raise StateWriteContractError("alpha must lie in (0, 1]")
        object.__setattr__(self, "keys", keys)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "beta", beta)
        object.__setattr__(self, "alpha", alpha)
        if not self.identity:
            digest = hashlib.sha256(
                keys.tobytes() + values.tobytes() + beta.tobytes() + alpha.tobytes()
            ).hexdigest()[:16]
            object.__setattr__(self, "identity", f"span-{length}-{digest}")

    @property
    def length(self) -> int:
        return int(self.keys.shape[0])

    @property
    def key_dim(self) -> int:
        return int(self.keys.shape[1])

    @property
    def value_dim(self) -> int:
        return int(self.values.shape[1])

    @property
    def state_shape(self) -> tuple[int, int]:
        return (self.value_dim, self.key_dim)

    def with_zero_values(self) -> HeadSpan:
        """The ``v = 0`` counterfactual: decay and erase kept, writes removed."""

        return HeadSpan(
            self.keys,
            np.zeros_like(self.values),
            self.beta,
            self.alpha,
            identity=f"{self.identity}-v0",
        )

    def with_scaled_values(self, scale: float) -> HeadSpan:
        """Shrink or grow the writes only; used by the write-shrinkage counterfactual."""

        if not math.isfinite(scale) or scale <= 0.0:
            raise StateWriteContractError("value scale must be finite and positive")
        return HeadSpan(
            self.keys,
            self.values * scale,
            self.beta,
            self.alpha,
            identity=f"{self.identity}-scaled",
        )


def _validate_state(state: object, span: HeadSpan, *, name: str) -> FloatArray:
    array = np.array(state, dtype=np.float64, copy=True)
    if array.shape != span.state_shape:
        raise StateWriteContractError(
            f"{name} must have shape {span.state_shape} (d_v, d_k), got {array.shape}"
        )
    if not np.isfinite(array).all():
        raise StateWriteContractError(f"{name} must be finite")
    return array


# ---------------------------------------------------------------------- recurrence


def run_gdn_head_trajectory(
    span: HeadSpan,
    initial_state: FloatArray | None = None,
) -> FloatArray:
    """Return ``[T + 1, d_v, d_k]`` states; row 0 is the initial state."""

    if initial_state is None:
        state = np.zeros(span.state_shape, dtype=np.float64)
    else:
        state = _validate_state(initial_state, span, name="initial_state")
    trajectory = np.empty((span.length + 1, *span.state_shape), dtype=np.float64)
    trajectory[0] = state
    for step in range(span.length):
        key = span.keys[step]
        write_strength = span.beta[step]
        # S (I - b k k^T) = S - b (S k) k^T, then decay, then write b v k^T.
        erased = state - write_strength * np.outer(state @ key, key)
        state = span.alpha[step] * erased + write_strength * np.outer(span.values[step], key)
        trajectory[step + 1] = state
    return trajectory


def run_gdn_head(span: HeadSpan, initial_state: FloatArray | None = None) -> FloatArray:
    """Final state of one GDN head after the span, starting from ``initial_state``."""

    return run_gdn_head_trajectory(span, initial_state)[-1]


# ------------------------------------------------------------------------- objects


def prefix_carry(prefix_state: FloatArray, span: HeadSpan) -> FloatArray:
    """``S_{v=0}(c, a)``: the prefix state carried through decay and erase only."""

    return run_gdn_head(span.with_zero_values(), prefix_state)


def pure_write(prefix_state: FloatArray, span: HeadSpan) -> FloatArray:
    """``W(a|c) = S(c + a) - S_{v=0}(c, a)`` (the wave-3 supervised object)."""

    return run_gdn_head(span, prefix_state) - prefix_carry(prefix_state, span)


def zero_state_write(span: HeadSpan) -> FloatArray:
    """``S_{S0=0}(a)``: the same span run from the zero state."""

    return run_gdn_head(span, None)


def segment_delta(prefix_state: FloatArray, span: HeadSpan) -> FloatArray:
    """``D = S(c + a) - S(c)`` (the wave-2 object that carries ``(prod a - 1) S(c)``)."""

    validated = _validate_state(prefix_state, span, name="prefix_state")
    return run_gdn_head(span, validated) - validated


def projection_pooling(span: HeadSpan) -> FloatArray:
    """``P(a) = sum_t b_t v_t k_t^T``: the decay-free, erase-free A2 control object."""

    return (span.values * span.beta[:, None]).T @ span.keys


def flat_cosine(left: FloatArray, right: FloatArray) -> float:
    """Cosine between two matrices flattened to vectors; zero norms are rejected."""

    left_flat = np.asarray(left, dtype=np.float64).ravel()
    right_flat = np.asarray(right, dtype=np.float64).ravel()
    if left_flat.shape != right_flat.shape:
        raise StateWriteContractError("cosine operands must share a shape")
    left_norm = float(np.linalg.norm(left_flat))
    right_norm = float(np.linalg.norm(right_flat))
    if left_norm == 0.0 or right_norm == 0.0:
        raise StateWriteContractError("cosine is undefined for a zero-norm object")
    return float(np.dot(left_flat, right_flat) / (left_norm * right_norm))


# --------------------------------------------------------------------- gates: W


@dataclass(frozen=True, slots=True)
class WriteIdentityReport:
    """fp64 check of ``W(a|c) == S_{S0=0}(a)`` for one head."""

    max_abs_residual: float
    max_abs_write: float
    tolerance: float
    passed: bool

    def __post_init__(self) -> None:
        for value in (self.max_abs_residual, self.max_abs_write, self.tolerance):
            if not math.isfinite(value) or value < 0.0:
                raise StateWriteContractError("identity report scalars must be finite and >= 0")


def check_write_identity(
    prefix_state: FloatArray,
    span: HeadSpan,
    tolerance: float = 1e-10,
) -> WriteIdentityReport:
    """Gate: the pure write must equal the zero-initial-state run to ``tolerance``."""

    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise StateWriteContractError("tolerance must be finite and positive")
    write = pure_write(prefix_state, span)
    reference = zero_state_write(span)
    residual = float(np.max(np.abs(write - reference)))
    return WriteIdentityReport(
        max_abs_residual=residual,
        max_abs_write=float(np.max(np.abs(reference))),
        tolerance=tolerance,
        passed=residual <= tolerance,
    )


def states_bitwise_identical(left: FloatArray, right: FloatArray) -> bool:
    """Gate: ``S(c)`` must be bitwise identical for both members of a pair."""

    left_array = np.ascontiguousarray(left, dtype=np.float64)
    right_array = np.ascontiguousarray(right, dtype=np.float64)
    return left_array.shape == right_array.shape and left_array.tobytes() == right_array.tobytes()


@dataclass(frozen=True, slots=True)
class PrefixFloorLedger:
    """Translation-pair cosines against the same-prefix non-translation floor.

    ``pair_cosines`` and ``floor_cosines`` are ``[heads, pairs]``. The registered
    rule accepts the object when the mean margin is at least ``margin_threshold``
    in at least ``head_fraction`` of the heads.
    """

    object_name: str
    pair_cosines: FloatArray
    floor_cosines: FloatArray
    margin_threshold: float = 0.05
    head_fraction: float = 2.0 / 3.0

    def __post_init__(self) -> None:
        pair = _finite_array(self.pair_cosines, name="pair_cosines", ndim=2)
        floor = _finite_array(self.floor_cosines, name="floor_cosines", ndim=2)
        if pair.shape != floor.shape:
            raise StateWriteContractError("pair and floor cosines must share a shape")
        if not self.object_name:
            raise StateWriteContractError("object_name must be non-empty")
        if not 0.0 < self.head_fraction <= 1.0 or not math.isfinite(self.margin_threshold):
            raise StateWriteContractError("ledger thresholds are out of range")
        object.__setattr__(self, "pair_cosines", pair)
        object.__setattr__(self, "floor_cosines", floor)

    @property
    def heads(self) -> int:
        return int(self.pair_cosines.shape[0])

    @property
    def head_margins(self) -> FloatArray:
        return self.pair_cosines.mean(axis=1) - self.floor_cosines.mean(axis=1)

    @property
    def heads_passing(self) -> int:
        return int(np.count_nonzero(self.head_margins >= self.margin_threshold))

    @property
    def required_heads(self) -> int:
        return int(math.ceil(self.head_fraction * self.heads - 1e-12))

    @property
    def passed(self) -> bool:
        return self.heads_passing >= self.required_heads

    def summary(self) -> dict[str, object]:
        return {
            "object": self.object_name,
            "heads": self.heads,
            "pairs": int(self.pair_cosines.shape[1]),
            "mean_pair_cosine": float(self.pair_cosines.mean()),
            "mean_floor_cosine": float(self.floor_cosines.mean()),
            "head_margins": [float(value) for value in self.head_margins],
            "heads_passing": self.heads_passing,
            "required_heads": self.required_heads,
            "margin_threshold": self.margin_threshold,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class DistinctnessReport:
    """Gate G2: ``mean cos(vec W, vec P)`` over heads must not exceed ``threshold``."""

    per_head_cosine: FloatArray
    threshold: float = 0.9

    def __post_init__(self) -> None:
        cosines = _finite_array(self.per_head_cosine, name="per_head_cosine", ndim=1)
        if not 0.0 < self.threshold < 1.0:
            raise StateWriteContractError("distinctness threshold must lie in (0, 1)")
        object.__setattr__(self, "per_head_cosine", cosines)

    @property
    def mean_cosine(self) -> float:
        return float(self.per_head_cosine.mean())

    @property
    def passed(self) -> bool:
        """True means W and P are distinct enough for the A1 - A2 contrast to be read."""

        return self.mean_cosine <= self.threshold

    def summary(self) -> dict[str, object]:
        return {
            "per_head_cosine": [float(value) for value in self.per_head_cosine],
            "mean_cosine": self.mean_cosine,
            "threshold": self.threshold,
            "contrast_interpretable": self.passed,
        }


def distinctness_statistic(spans: Sequence[HeadSpan], threshold: float = 0.9) -> DistinctnessReport:
    """``cos(W, P)`` per head; ``W`` needs no prefix state because ``W == S_{S0=0}(a)``."""

    if not spans:
        raise StateWriteContractError("at least one head span is required")
    cosines = np.array(
        [flat_cosine(zero_state_write(span), projection_pooling(span)) for span in spans]
    )
    return DistinctnessReport(per_head_cosine=cosines, threshold=threshold)


def write_norm_shrinkage(reference_norm: float, current_norm: float) -> float:
    """Fraction by which ``mean ||W||`` shrank; the falsifier fires above 0.3."""

    if not math.isfinite(reference_norm) or reference_norm <= 0.0:
        raise StateWriteContractError("reference write norm must be finite and positive")
    if not math.isfinite(current_norm) or current_norm < 0.0:
        raise StateWriteContractError("current write norm must be finite and non-negative")
    return 1.0 - current_norm / reference_norm


def write_norm_falsifier_fires(shrinkage: float, max_shrinkage: float = 0.3) -> bool:
    if not math.isfinite(shrinkage):
        raise StateWriteContractError("shrinkage must be finite")
    return shrinkage > max_shrinkage


# ------------------------------------------------------------------ tiny GDN model


def _sigmoid(values: FloatArray) -> FloatArray:
    return 1.0 / (1.0 + np.exp(-values))


def _rms_norm(values: FloatArray) -> FloatArray:
    scale = np.sqrt(np.mean(np.square(values), axis=-1, keepdims=True) + 1e-8)
    return values / scale


@dataclass(frozen=True, slots=True)
class TinyGDNConfig:
    """A seeded two-layer GDN with a two-language vocabulary.

    Tokens ``[0, vocab_size / 2)`` are language A; token ``i + vocab_size / 2`` is
    the language-B mirror of token ``i`` whose embedding equals A's plus
    ``translation_noise`` Gaussian noise. This is a synthetic stand-in for an
    aligned bilingual model, not a claim about any trained model.
    """

    vocab_size: int = 64
    hidden: int = 32
    layers: int = 2
    heads: int = 2
    key_dim: int = 8
    value_dim: int = 8
    translation_noise: float = 0.05
    decay_rate: float = 0.02
    beta_bias: float = 0.0
    seed: int = 42

    def __post_init__(self) -> None:
        if self.vocab_size < 4 or self.vocab_size % 2:
            raise StateWriteContractError("vocab_size must be an even integer >= 4")
        for name in ("hidden", "layers", "heads", "key_dim", "value_dim"):
            if getattr(self, name) < 1:
                raise StateWriteContractError(f"{name} must be positive")
        if not math.isfinite(self.translation_noise) or self.translation_noise < 0.0:
            raise StateWriteContractError("translation_noise must be finite and >= 0")
        if not math.isfinite(self.decay_rate) or self.decay_rate <= 0.0:
            raise StateWriteContractError("decay_rate must be finite and positive")
        if not math.isfinite(self.beta_bias):
            raise StateWriteContractError("beta_bias must be finite")

    @property
    def language_offset(self) -> int:
        return self.vocab_size // 2


@dataclass(frozen=True, slots=True)
class ForwardTrace:
    """Final states, realized per-head spans, and optionally the state trajectory."""

    final_states: FloatArray
    spans: tuple[tuple[HeadSpan, ...], ...]
    trajectory: FloatArray | None = None


class TinyGDNModel:
    """Pure-NumPy two-layer GDN used only to realize projections and states."""

    def __init__(self, config: TinyGDNConfig) -> None:
        self.config = config
        rng = np.random.default_rng(config.seed)
        base = rng.standard_normal((config.language_offset, config.hidden))
        mirror = base + config.translation_noise * rng.standard_normal(base.shape)
        self.embedding = np.concatenate([base, mirror], axis=0)
        width = config.hidden
        self.layer_weights: list[dict[str, FloatArray]] = []
        for _layer in range(config.layers):
            key_width = config.heads * config.key_dim
            value_width = config.heads * config.value_dim
            self.layer_weights.append(
                {
                    "wq": rng.standard_normal((width, key_width)) / math.sqrt(width),
                    "wk": rng.standard_normal((width, key_width)) / math.sqrt(width),
                    "wv": rng.standard_normal((width, value_width)) / math.sqrt(width),
                    "wb": rng.standard_normal((width, config.heads)) / math.sqrt(width),
                    "wa": rng.standard_normal((width, config.heads)) / math.sqrt(width),
                    "wo": rng.standard_normal((value_width, width)) / math.sqrt(value_width),
                }
            )

    @property
    def state_shape(self) -> tuple[int, int, int, int]:
        config = self.config
        return (config.layers, config.heads, config.value_dim, config.key_dim)

    def validate_tokens(self, tokens: object) -> IntArray:
        array = np.array(tokens, dtype=np.int64, copy=True)
        if array.ndim != 1 or not array.size:
            raise StateWriteContractError("tokens must be a non-empty 1-d integer sequence")
        if np.any(array < 0) or np.any(array >= self.config.vocab_size):
            raise StateWriteContractError("tokens must lie inside the vocabulary")
        return array

    def translate(self, tokens: object) -> IntArray:
        """Map language-A tokens to their language-B mirrors and vice versa."""

        array = self.validate_tokens(tokens)
        offset = self.config.language_offset
        return np.where(array < offset, array + offset, array - offset)

    def forward(
        self,
        tokens: object,
        initial_states: FloatArray | None = None,
        *,
        trajectory: bool = False,
    ) -> ForwardTrace:
        config = self.config
        token_array = self.validate_tokens(tokens)
        if initial_states is None:
            states = np.zeros(self.state_shape, dtype=np.float64)
        else:
            states = np.array(initial_states, dtype=np.float64, copy=True)
            if states.shape != self.state_shape or not np.isfinite(states).all():
                raise StateWriteContractError(
                    f"initial_states must be finite with shape {self.state_shape}"
                )
        length = token_array.shape[0]
        residual = self.embedding[token_array]
        final_states = np.empty_like(states)
        history = (
            np.empty((length + 1, *self.state_shape), dtype=np.float64) if trajectory else None
        )
        realized: list[tuple[HeadSpan, ...]] = []
        for layer, weights in enumerate(self.layer_weights):
            normed = _rms_norm(residual)
            queries = (normed @ weights["wq"]).reshape(length, config.heads, config.key_dim)
            keys = (normed @ weights["wk"]).reshape(length, config.heads, config.key_dim)
            keys = keys / np.maximum(np.linalg.norm(keys, axis=-1, keepdims=True), 1e-12)
            values = (normed @ weights["wv"]).reshape(length, config.heads, config.value_dim)
            beta = _sigmoid(normed @ weights["wb"] + config.beta_bias)
            alpha = np.exp(-config.decay_rate * 2.0 * _sigmoid(normed @ weights["wa"]))
            outputs = np.empty((length, config.heads, config.value_dim), dtype=np.float64)
            layer_spans: list[HeadSpan] = []
            for head in range(config.heads):
                span = HeadSpan(
                    keys[:, head],
                    values[:, head],
                    beta[:, head],
                    alpha[:, head],
                    identity=f"layer{layer}-head{head}",
                )
                path = run_gdn_head_trajectory(span, states[layer, head])
                outputs[:, head] = np.einsum("tvk,tk->tv", path[1:], queries[:, head])
                final_states[layer, head] = path[-1]
                if history is not None:
                    history[:, layer, head] = path
                layer_spans.append(span)
            realized.append(tuple(layer_spans))
            residual = residual + outputs.reshape(length, -1) @ weights["wo"]
        return ForwardTrace(final_states=final_states, spans=tuple(realized), trajectory=history)


def flatten_spans(trace: ForwardTrace) -> tuple[HeadSpan, ...]:
    return tuple(span for layer in trace.spans for span in layer)


def flatten_states(states: FloatArray) -> tuple[FloatArray, ...]:
    layers, heads = states.shape[0], states.shape[1]
    return tuple(states[layer, head] for layer in range(layers) for head in range(heads))


def object_cosine_ledger(
    object_fn: Callable[[FloatArray, HeadSpan], FloatArray],
    prefix_states: Sequence[FloatArray],
    anchor_spans: Sequence[Sequence[HeadSpan]],
    positive_spans: Sequence[Sequence[HeadSpan]],
    floor_spans: Sequence[Sequence[HeadSpan]],
) -> tuple[FloatArray, FloatArray]:
    """Per-head cosines of an object between anchor/positive and anchor/floor spans.

    ``anchor_spans[pair][head]`` are the realized spans of the language-A member,
    ``positive_spans`` its translation and ``floor_spans`` a same-prefix
    non-translation. Returns ``(pair_cosines, floor_cosines)`` as ``[heads, pairs]``.
    """

    pairs = len(anchor_spans)
    if not pairs or len(positive_spans) != pairs or len(floor_spans) != pairs:
        raise StateWriteContractError("anchor, positive and floor span lists must align")
    heads = len(prefix_states)
    pair_cosines = np.empty((heads, pairs))
    floor_cosines = np.empty((heads, pairs))
    for pair in range(pairs):
        if len(anchor_spans[pair]) != heads or len(positive_spans[pair]) != heads:
            raise StateWriteContractError("every pair must realize one span per head")
        if len(floor_spans[pair]) != heads:
            raise StateWriteContractError("every pair must realize one span per head")
        for head in range(heads):
            anchor = object_fn(prefix_states[head], anchor_spans[pair][head])
            pair_cosines[head, pair] = flat_cosine(
                anchor, object_fn(prefix_states[head], positive_spans[pair][head])
            )
            floor_cosines[head, pair] = flat_cosine(
                anchor, object_fn(prefix_states[head], floor_spans[pair][head])
            )
    return pair_cosines, floor_cosines


# ---------------------------------------------------------- TP-MQAR-v2 controls

CODE_RE = re.compile(r"^[0-9]{4}$")
PROMPT_KINDS = ("positive-control", "retrieval-impossible", "value-permutation")


@dataclass(frozen=True, slots=True)
class RecallPrompt:
    """One synthetic TP-MQAR-v2 prompt: N (key, 4-digit code) facts and one query.

    Keys are integer stand-ins for FLORES+ sentence ids; the real builder will
    carry text in two languages. ``answer`` is the context-consistent code;
    ``leaked_answer`` (value-permutation prompts only) is the code the queried
    key carried before the permutation, so scoring against it must sit at chance.
    """

    facts: tuple[tuple[int, str], ...]
    query_key: int
    answer: str
    kind: str
    leaked_answer: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in PROMPT_KINDS:
            raise StateWriteContractError(f"unknown prompt kind {self.kind!r}")
        if not self.facts:
            raise StateWriteContractError("a prompt needs at least one fact")
        keys = [key for key, _code in self.facts]
        codes = [code for _key, code in self.facts]
        if len(set(keys)) != len(keys) or len(set(codes)) != len(codes):
            raise StateWriteContractError("fact keys and codes must be distinct within a prompt")
        if any(not CODE_RE.fullmatch(code) for code in codes) or not CODE_RE.fullmatch(self.answer):
            raise StateWriteContractError("codes must be exactly four ASCII digits")
        lookup = dict(self.facts)
        if self.kind == "retrieval-impossible":
            if self.query_key in lookup:
                raise StateWriteContractError("retrieval-impossible query must be absent")
        elif self.query_key not in lookup or lookup[self.query_key] != self.answer:
            raise StateWriteContractError("query must name a fact whose code is the answer")
        if self.kind == "value-permutation":
            if self.leaked_answer is None or self.leaked_answer == self.answer:
                raise StateWriteContractError(
                    "value-permutation prompts need a distinct leaked_answer"
                )
        elif self.leaked_answer is not None:
            raise StateWriteContractError("only value-permutation prompts carry leaked_answer")


def _draw_codes(rng: np.random.Generator, count: int) -> list[str]:
    codes = rng.choice(10_000, size=count, replace=False)
    return [f"{int(code):04d}" for code in codes]


def build_recall_manifest(
    rng: np.random.Generator,
    *,
    prompts: int,
    facts_per_prompt: int,
    key_pool: int,
) -> tuple[RecallPrompt, ...]:
    """Positive-control prompts: the queried key is present with its own code."""

    if prompts < 1 or facts_per_prompt < 1:
        raise StateWriteContractError("prompts and facts_per_prompt must be positive")
    if key_pool <= facts_per_prompt:
        raise StateWriteContractError("key_pool must exceed facts_per_prompt")
    manifest = []
    for _index in range(prompts):
        keys = rng.choice(key_pool, size=facts_per_prompt, replace=False)
        codes = _draw_codes(rng, facts_per_prompt)
        facts = tuple((int(key), code) for key, code in zip(keys, codes, strict=True))
        query = int(rng.integers(facts_per_prompt))
        manifest.append(RecallPrompt(facts, facts[query][0], facts[query][1], "positive-control"))
    return tuple(manifest)


def retrieval_impossible_control(
    prompt: RecallPrompt,
    rng: np.random.Generator,
    *,
    key_pool: int,
) -> RecallPrompt:
    """Replace the query with an absent key; the scored answer is a fresh random code."""

    present = {key for key, _code in prompt.facts}
    candidates = np.setdiff1d(np.arange(key_pool), np.fromiter(present, dtype=np.int64))
    if not candidates.size:
        raise StateWriteContractError("key_pool leaves no absent key for the control")
    absent = int(rng.choice(candidates))
    return RecallPrompt(prompt.facts, absent, _draw_codes(rng, 1)[0], "retrieval-impossible")


def value_permutation_control(prompt: RecallPrompt, rng: np.random.Generator) -> RecallPrompt:
    """Derange the codes among the facts; the old code of the queried key is the leak."""

    count = len(prompt.facts)
    if count < 2:
        raise StateWriteContractError("value permutation needs at least two facts")
    while True:
        permutation = rng.permutation(count)
        if not np.any(permutation == np.arange(count)):
            break
    codes = [code for _key, code in prompt.facts]
    facts = tuple(
        (key, codes[int(permutation[index])]) for index, (key, _code) in enumerate(prompt.facts)
    )
    lookup = dict(facts)
    return RecallPrompt(
        facts,
        prompt.query_key,
        lookup[prompt.query_key],
        "value-permutation",
        leaked_answer=dict(prompt.facts)[prompt.query_key],
    )


def lookup_reader(prompt: RecallPrompt) -> str:
    """Oracle reader: the code stored next to the queried key, else a fixed guess."""

    return dict(prompt.facts).get(prompt.query_key, "0000")


def exact_match(
    prompts: Sequence[RecallPrompt],
    reader: Callable[[RecallPrompt], str],
    *,
    against: str = "answer",
) -> float:
    if not prompts:
        raise StateWriteContractError("exact match needs at least one prompt")
    if against not in {"answer", "leaked_answer"}:
        raise StateWriteContractError("against must be answer or leaked_answer")
    hits = 0
    for prompt in prompts:
        target = getattr(prompt, against)
        if target is None:
            raise StateWriteContractError("prompt lacks the requested scoring target")
        hits += int(reader(prompt) == target)
    return hits / len(prompts)


def manifest_sha256(prompts: Sequence[RecallPrompt]) -> str:
    payload = [
        {
            "facts": [[key, code] for key, code in prompt.facts],
            "query_key": prompt.query_key,
            "answer": prompt.answer,
            "kind": prompt.kind,
            "leaked_answer": prompt.leaked_answer,
        }
        for prompt in prompts
    ]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_DIGIT_RE = re.compile(r"[0-9]+")


def surface_disjoint(
    left: str,
    right: str,
    *,
    min_shared_token_chars: int = 3,
    min_shared_subword_chars: int = 4,
) -> bool:
    """Surface-disjoint key filter (NFKC + casefold; tokens, digit strings, subwords).

    The subword clause uses character n-grams inside tokens as a tokenizer-free
    stand-in; the pilot must re-run it under the Qwen3.5 and the 57M tokenizers.
    """

    if min_shared_token_chars < 1 or min_shared_subword_chars < 1:
        raise StateWriteContractError("filter lengths must be positive")
    left_norm = unicodedata.normalize("NFKC", left).casefold()
    right_norm = unicodedata.normalize("NFKC", right).casefold()
    left_tokens = set(_TOKEN_RE.findall(left_norm))
    right_tokens = set(_TOKEN_RE.findall(right_norm))
    if any(len(token) >= min_shared_token_chars for token in left_tokens & right_tokens):
        return False
    if set(_DIGIT_RE.findall(left_norm)) & set(_DIGIT_RE.findall(right_norm)):
        return False

    def grams(tokens: set[str]) -> set[str]:
        width = min_shared_subword_chars
        return {
            token[start : start + width]
            for token in tokens
            for start in range(len(token) - width + 1)
        }

    return not grams(left_tokens) & grams(right_tokens)


# ------------------------------------------------------ promotion-rule simulation


@dataclass(frozen=True, slots=True)
class PromotionRuleConfig:
    """Seed-level noise model for the A1 - A2 primary endpoint (assumptions, not data)."""

    minimum_effect: float = 5.0
    seed_sd: float = 3.0
    seeds: int = 3
    prompts_per_seed: int = 1800
    prompt_sd_points: float = 70.0
    draws: int = 200_000
    confidence: float = 0.95

    def __post_init__(self) -> None:
        for name in ("minimum_effect", "seed_sd", "prompt_sd_points"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise StateWriteContractError(f"{name} must be finite and positive")
        if self.seeds < 2 or self.prompts_per_seed < 1 or self.draws < 1000:
            raise StateWriteContractError("seeds >= 2, prompts >= 1 and draws >= 1000 required")
        if not 0.5 < self.confidence < 1.0:
            raise StateWriteContractError("confidence must lie in (0.5, 1)")

    @property
    def pooled_half_width(self) -> float:
        z_value = float(norm.ppf(0.5 + self.confidence / 2.0))
        return z_value * self.prompt_sd_points / math.sqrt(self.seeds * self.prompts_per_seed)


@dataclass(frozen=True, slots=True)
class RuleOperatingPoint:
    """Monte-Carlo operating characteristics of the two candidate decision rules."""

    delta: float
    all_pairs_promote: float
    all_pairs_analytic: float
    seed_mean_promote: float
    seed_mean_kill: float
    seed_mean_underpowered: float

    def summary(self) -> dict[str, float]:
        return {
            "delta_em_points": self.delta,
            "wave4_rule_all_pairs_promote": self.all_pairs_promote,
            "wave4_rule_all_pairs_analytic": self.all_pairs_analytic,
            "wave5_rule_promote": self.seed_mean_promote,
            "wave5_rule_kill": self.seed_mean_kill,
            "wave5_rule_underpowered": self.seed_mean_underpowered,
        }


def simulate_promotion_rules(
    config: PromotionRuleConfig,
    deltas: Sequence[float],
    rng: np.random.Generator,
) -> tuple[RuleOperatingPoint, ...]:
    """Simulate both rules at each true effect.

    Wave-4 rule: every seed-pair difference >= minimum_effect. Wave-5 rule
    (Reviewer B): promote when the seed mean >= minimum_effect, all pairs are
    positive and the pooled prompt-clustered interval excludes zero; kill when
    any pair is negative or the seed mean is negative; otherwise the band is
    underpowered and goes to the +2-seed line.
    """

    if not deltas:
        raise StateWriteContractError("at least one delta is required")
    points = []
    for delta in deltas:
        if not math.isfinite(delta):
            raise StateWriteContractError("deltas must be finite")
        draws = rng.normal(delta, config.seed_sd, size=(config.draws, config.seeds))
        means = draws.mean(axis=1)
        all_pairs = np.all(draws >= config.minimum_effect, axis=1)
        promote = (
            (means >= config.minimum_effect)
            & np.all(draws > 0.0, axis=1)
            & (means - config.pooled_half_width > 0.0)
        )
        kill = np.any(draws < 0.0, axis=1) | (means < 0.0)
        analytic = float(norm.cdf((delta - config.minimum_effect) / config.seed_sd)) ** config.seeds
        points.append(
            RuleOperatingPoint(
                delta=float(delta),
                all_pairs_promote=float(all_pairs.mean()),
                all_pairs_analytic=analytic,
                seed_mean_promote=float(promote.mean()),
                seed_mean_kill=float(kill.mean()),
                seed_mean_underpowered=float(np.mean(~promote & ~kill)),
            )
        )
    return tuple(points)


# ------------------------------------------------------------ fla cross-check


def fla_cross_check(
    span: HeadSpan,
    initial_state: FloatArray | None = None,
    tolerance: float = 1e-3,
) -> dict[str, object]:
    """Compare the NumPy recurrence with fla's chunked kernel when it is available.

    torch and fla are imported lazily; without them, or without CUDA (fla's
    chunk kernels are Triton kernels), the check reports ``skipped``. This path
    has not been executed anywhere yet and is recorded as such by the doctor.
    """

    try:
        import torch
        from fla.ops.gated_delta_rule import chunk_gated_delta_rule
    except ImportError as exc:  # pragma: no cover - exercised only where fla exists
        return {"status": "skipped", "reason": f"torch/fla not importable: {exc}"}
    if not torch.cuda.is_available():
        return {"status": "skipped", "reason": "fla chunk kernels need a CUDA device"}
    device = torch.device("cuda")  # pragma: no cover - CUDA-only path
    to_tensor = lambda array: torch.as_tensor(  # noqa: E731
        np.asarray(array, dtype=np.float32), device=device
    )
    queries = torch.zeros((1, span.length, 1, span.key_dim), device=device)
    keys = to_tensor(span.keys)[None, :, None, :]
    values = to_tensor(span.values)[None, :, None, :]
    log_alpha = to_tensor(np.log(span.alpha))[None, :, None]
    beta = to_tensor(span.beta)[None, :, None]
    reference = run_gdn_head(span, initial_state)
    start = None
    if initial_state is not None:
        start = to_tensor(_validate_state(initial_state, span, name="initial_state").T)[None, None]
    _output, final_state = chunk_gated_delta_rule(
        queries,
        keys,
        values,
        log_alpha,
        beta,
        scale=1.0,
        initial_state=start,
        output_final_state=True,
    )
    fla_state = final_state[0, 0].float().cpu().numpy().T
    residual = float(np.max(np.abs(fla_state - reference)))
    return {
        "status": "executed",
        "max_abs_residual": residual,
        "tolerance": tolerance,
        "passed": residual <= tolerance,
        "dtype": "float32",
    }


__all__ = [
    "PROMPT_KINDS",
    "DistinctnessReport",
    "ForwardTrace",
    "HeadSpan",
    "PrefixFloorLedger",
    "PromotionRuleConfig",
    "RecallPrompt",
    "RuleOperatingPoint",
    "StateWriteContractError",
    "TinyGDNConfig",
    "TinyGDNModel",
    "WriteIdentityReport",
    "build_recall_manifest",
    "check_write_identity",
    "distinctness_statistic",
    "exact_match",
    "fla_cross_check",
    "flat_cosine",
    "flatten_spans",
    "flatten_states",
    "lookup_reader",
    "manifest_sha256",
    "object_cosine_ledger",
    "prefix_carry",
    "projection_pooling",
    "pure_write",
    "retrieval_impossible_control",
    "run_gdn_head",
    "run_gdn_head_trajectory",
    "segment_delta",
    "simulate_promotion_rules",
    "states_bitwise_identical",
    "surface_disjoint",
    "value_permutation_control",
    "write_norm_falsifier_fires",
    "write_norm_shrinkage",
    "zero_state_write",
]
