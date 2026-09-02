"""Phase-0 objects for Direction 20, semantic-clock gate parity.

Model-free NumPy/SciPy reference implementation of the objects the proposal
pre-registers for its training-free phase-0 pilot:

* the Gated DeltaNet gate parametrization, the constant, span-oracle and write
  clock surgeries, and a batched delta-rule scan on which the r = 1 identity
  and the token-duplication checks run;
* the per-language cumulative forgetting and write ledger with its parity
  ratios R_F and R_W (prediction P1, kill K1);
* the prefix-blind within-sentence attention window and the query-only mask,
  with an analytic zero-gradient audit and a bitwise perturbation probe;
* the anchored log-ratio span-parity loss reserved for phase 1, with its
  analytic gradient (finite-difference and rescale-invariance checks);
* the common-dose estimand G_L = EM_L(r = 2) - EM_L(r = 1) on the EM-point and
  logit scales, the two-regressor partial fertility slope with an
  episode-clustered paired bootstrap, the synthetic-fertility English
  comparator, and the registered decision rules (P3 with the re-segmented
  English token-count comparator, K2 pooled kill, K7/K7b holds, K8, K9,
  K10/K10b, K11 disagreement rule).

Nothing here loads a checkpoint, a tokenizer or a dataset. Every number the
objects produce on the doctor's registered cases is a synthetic-case number.
A torch implementation of the hooks must sit behind the same typed inputs; it
is imported lazily by callers and never at module import time.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy import stats
from scipy.special import expit, logit, ndtri

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]


class GateContractError(ValueError):
    """Raised when a phase-0 input violates the registered contract."""


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #


def _finite_vector(values: object, *, name: str, minimum_length: int = 1) -> FloatArray:
    array = np.array(values, dtype=np.float64, copy=True)
    if array.ndim != 1 or array.size < minimum_length:
        raise GateContractError(f"{name} must be a vector with at least {minimum_length} entries")
    if not np.isfinite(array).all():
        raise GateContractError(f"{name} must be finite")
    return array


def _log_decay_vector(values: object, *, name: str = "log_decay") -> FloatArray:
    array = _finite_vector(values, name=name)
    if np.any(array > 0.0):
        raise GateContractError(
            f"{name} must be non-positive (g_t = log alpha_t with alpha_t <= 1)"
        )
    return array


def _write_gate_vector(values: object, *, name: str = "write_gate") -> FloatArray:
    array = _finite_vector(values, name=name)
    if np.any(array <= 0.0) or np.any(array > 1.0):
        raise GateContractError(f"{name} must lie in (0, 1]")
    return array


def _positive_scalar(value: object, *, name: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise GateContractError(f"{name} must be a real number") from exc
    if not math.isfinite(number) or number <= 0.0:
        raise GateContractError(f"{name} must be finite and positive")
    return number


def _finite_scalar(value: object, *, name: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise GateContractError(f"{name} must be a real number") from exc
    if not math.isfinite(number):
        raise GateContractError(f"{name} must be finite")
    return number


def _bool_outcomes(values: object, *, name: str) -> BoolArray:
    array = np.asarray(values)
    if array.ndim != 1 or array.size < 2:
        raise GateContractError(f"{name} must be a vector of at least two paired outcomes")
    if array.dtype != np.bool_:
        if not np.isin(array, (0, 1)).all():
            raise GateContractError(f"{name} must contain only 0/1 or boolean outcomes")
        array = array.astype(bool)
    return np.array(array, dtype=np.bool_, copy=True)


# --------------------------------------------------------------------------- #
# Gate parametrization and clock surgery
# --------------------------------------------------------------------------- #


def log_decay_from_preactivation(a: object, a_log: float, dt_bias: float) -> FloatArray:
    """g_t = -exp(A_log) * softplus(a_t + dt_bias), the transformers qwen3_5 form."""

    preactivation = _finite_vector(a, name="a")
    scale = math.exp(_finite_scalar(a_log, name="A_log"))
    bias = _finite_scalar(dt_bias, name="dt_bias")
    return -scale * np.logaddexp(0.0, preactivation + bias)


def write_gate_from_preactivation(b: object) -> FloatArray:
    """beta_t = sigmoid(b_t)."""

    preactivation = _finite_vector(b, name="b")
    return _write_gate_vector(expit(preactivation), name="sigmoid(b)")


def constant_decay_surgery(log_decay: object, ratio: float) -> FloatArray:
    """g'_t = g_t / r for every token (constant surgery; r = 1 is the identity)."""

    g = _log_decay_vector(log_decay)
    r = _positive_scalar(ratio, name="decay ratio r")
    return g / r


def span_oracle_decay_surgery(log_decay: object, ratios: object) -> FloatArray:
    """g'_t = g_t / r_s with a per-token span ratio r_s (aligned-sentence oracle)."""

    g = _log_decay_vector(log_decay)
    per_token = _finite_vector(ratios, name="span ratios")
    if per_token.shape != g.shape:
        raise GateContractError("span ratios must be given per token")
    if np.any(per_token <= 0.0):
        raise GateContractError("span ratios must be positive")
    return g / per_token


def write_surgery(write_gate: object, ratio: float) -> FloatArray:
    """beta'_t = 1 - (1 - beta_t)^(1/r), so that (1 - beta')^r = 1 - beta."""

    beta = _write_gate_vector(write_gate)
    r = _positive_scalar(ratio, name="write ratio r")
    return 1.0 - np.power(1.0 - beta, 1.0 / r)


# --------------------------------------------------------------------------- #
# Ledger: cumulative forgetting and write mass with parity ratios
# --------------------------------------------------------------------------- #


def forgetting_mass(log_decay: object) -> float:
    """F(s) = -sum_{t in s} g_t."""

    return float(-_log_decay_vector(log_decay).sum())


def write_mass(write_gate: object) -> float:
    """W(s) = sum_{t in s} beta_t."""

    return float(_write_gate_vector(write_gate).sum())


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """Cumulative gate mass for one language's translation of a fixed span."""

    language: str
    fertility: float
    tokens: int
    forgetting_mass: float
    write_mass: float
    forgetting_ratio: float
    write_ratio: float

    def __post_init__(self) -> None:
        if not self.language:
            raise GateContractError("ledger language must be named")
        for name in (
            "fertility",
            "forgetting_mass",
            "write_mass",
            "forgetting_ratio",
            "write_ratio",
        ):
            _positive_scalar(getattr(self, name), name=name)
        if self.tokens < 1:
            raise GateContractError("ledger tokens must be positive")


@dataclass(frozen=True, slots=True)
class GateVerdict:
    """One registered gate evaluated on concrete numbers.

    ``kind`` is ``prediction`` (verdict True means the prediction holds),
    ``kill``/``hold``/``exclusion`` (verdict True means the condition fires) or
    ``classification`` (verdict True means the rule reached a decision).
    """

    name: str
    kind: str
    verdict: bool
    statistics: dict[str, float] = field(default_factory=dict)
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {"prediction", "kill", "hold", "exclusion", "classification"}:
            raise GateContractError(f"unknown gate kind {self.kind!r}")
        for key, value in self.statistics.items():
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise GateContractError(f"gate statistic {key} must be numeric")


def build_gate_ledger(
    log_decay_by_language: Mapping[str, object],
    write_gate_by_language: Mapping[str, object],
    fertility_by_language: Mapping[str, float],
    *,
    reference: str = "en",
) -> tuple[LedgerEntry, ...]:
    """Per-language F and W over one aligned span, with ratios against ``reference``."""

    if reference not in log_decay_by_language or reference not in write_gate_by_language:
        raise GateContractError(f"reference language {reference!r} missing from the traces")
    if set(log_decay_by_language) != set(write_gate_by_language):
        raise GateContractError("decay and write traces must cover the same languages")
    if set(fertility_by_language) != set(log_decay_by_language):
        raise GateContractError("fertility must be given for exactly the traced languages")
    reference_fertility = _positive_scalar(
        fertility_by_language[reference], name="reference fertility"
    )
    if not math.isclose(reference_fertility, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise GateContractError("reference fertility must be 1 by definition of fertility")
    reference_f = forgetting_mass(log_decay_by_language[reference])
    reference_w = write_mass(write_gate_by_language[reference])
    if reference_f <= 0.0 or reference_w <= 0.0:
        raise GateContractError("reference span must carry positive forgetting and write mass")
    entries = []
    for language in sorted(log_decay_by_language):
        g = _log_decay_vector(log_decay_by_language[language], name=f"log_decay[{language}]")
        beta = _write_gate_vector(write_gate_by_language[language], name=f"write_gate[{language}]")
        if g.shape != beta.shape:
            raise GateContractError(f"decay and write traces for {language} differ in length")
        f_mass = float(-g.sum())
        w_mass = float(beta.sum())
        entries.append(
            LedgerEntry(
                language=language,
                fertility=_positive_scalar(fertility_by_language[language], name="fertility"),
                tokens=int(g.size),
                forgetting_mass=f_mass,
                write_mass=w_mass,
                forgetting_ratio=f_mass / reference_f,
                write_ratio=w_mass / reference_w,
            )
        )
    return tuple(entries)


def p1_ledger_prediction(
    ledger: Sequence[LedgerEntry],
    *,
    high_fertility: float = 1.5,
    floor_fraction: float = 0.8,
) -> GateVerdict:
    """P1: R_F(L) >= 0.8 f_L and R_W(L) >= 0.8 f_L for every high-fertility language."""

    high = [entry for entry in ledger if entry.fertility >= high_fertility]
    if not high:
        raise GateContractError("P1 needs at least one high-fertility language in the ledger")
    worst_f = min(entry.forgetting_ratio / entry.fertility for entry in high)
    worst_w = min(entry.write_ratio / entry.fertility for entry in high)
    return GateVerdict(
        name="P1-ledger-tracks-fertility",
        kind="prediction",
        verdict=bool(worst_f >= floor_fraction and worst_w >= floor_fraction),
        statistics={
            "high_fertility_languages": float(len(high)),
            "min_forgetting_ratio_over_fertility": worst_f,
            "min_write_ratio_over_fertility": worst_w,
            "floor_fraction": floor_fraction,
        },
        note="holds when both cumulative gate masses scale with fertility for every f_L >= 1.5",
    )


def k1_warp_invariance_kill(
    ledger: Sequence[LedgerEntry],
    *,
    high_fertility: float = 1.5,
    tolerance: float = 0.15,
) -> GateVerdict:
    """K1: fires when R_F is within 15 percent of 1 for every high-fertility language."""

    high = [entry for entry in ledger if entry.fertility >= high_fertility]
    if not high:
        raise GateContractError("K1 needs at least one high-fertility language in the ledger")
    max_deviation = max(abs(entry.forgetting_ratio - 1.0) for entry in high)
    return GateVerdict(
        name="K1-gates-already-warp-invariant",
        kind="kill",
        verdict=bool(max_deviation <= tolerance),
        statistics={
            "high_fertility_languages": float(len(high)),
            "max_abs_forgetting_ratio_minus_one": max_deviation,
            "tolerance": tolerance,
        },
        note="fires when LM training already realized Tallec-Ollivier time-warp invariance",
    )


# --------------------------------------------------------------------------- #
# Gated DeltaNet scan (batched NumPy reference)
# --------------------------------------------------------------------------- #


def _batched(array: object, *, name: str, rank: int) -> FloatArray:
    values = np.array(array, dtype=np.float64, copy=True)
    if values.ndim == rank - 1:
        values = values[None, ...]
    if values.ndim != rank:
        raise GateContractError(f"{name} must have rank {rank} (or {rank - 1} for one episode)")
    if not np.isfinite(values).all():
        raise GateContractError(f"{name} must be finite")
    return values


def gated_delta_scan(
    keys: object,
    values: object,
    log_decay: object,
    write_gate: object,
    queries: object | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Run S_t = alpha_t S_{t-1} (I - beta_t k_t k_t^T) + beta_t v_t k_t^T over a batch.

    Shapes: keys [B, T, d_k], values [B, T, d_v], log_decay and write_gate
    [B, T], optional queries [B, T, d_k]. Returns (outputs [B, T, d_v] with
    o_t = S_t q_t, or an empty array when no queries are given; final state
    [B, d_v, d_k]).
    """

    k = _batched(keys, name="keys", rank=3)
    v = _batched(values, name="values", rank=3)
    g = _batched(log_decay, name="log_decay", rank=2)
    beta = _batched(write_gate, name="write_gate", rank=2)
    batch, length, key_dim = k.shape
    if (
        v.shape[:2] != (batch, length)
        or g.shape != (batch, length)
        or beta.shape != (batch, length)
    ):
        raise GateContractError("keys, values, log_decay and write_gate must agree on [B, T]")
    if np.any(g > 0.0):
        raise GateContractError("log_decay must be non-positive")
    if np.any(beta <= 0.0) or np.any(beta > 1.0):
        raise GateContractError("write_gate must lie in (0, 1]")
    q: FloatArray | None = None
    if queries is not None:
        q = _batched(queries, name="queries", rank=3)
        if q.shape != k.shape:
            raise GateContractError("queries must match keys in shape")
    value_dim = v.shape[2]
    state = np.zeros((batch, value_dim, key_dim), dtype=np.float64)
    outputs = (
        np.zeros((batch, length, value_dim), dtype=np.float64)
        if q is not None
        else np.zeros((batch, 0, value_dim), dtype=np.float64)
    )
    for t in range(length):
        k_t = k[:, t, :]
        v_t = v[:, t, :]
        alpha_t = np.exp(g[:, t])[:, None, None]
        beta_t = beta[:, t][:, None, None]
        state_k = np.einsum("bvk,bk->bv", state, k_t)
        erased = state - beta_t * state_k[:, :, None] * k_t[:, None, :]
        state = alpha_t * erased + beta_t * v_t[:, :, None] * k_t[:, None, :]
        if q is not None:
            outputs[:, t, :] = np.einsum("bvk,bk->bv", state, q[:, t, :])
    return outputs, state


def duplicate_tokens(array: object, repeats: int) -> FloatArray:
    """Repeat every token ``repeats`` times along the time axis (rank 2 or 3 arrays)."""

    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise GateContractError("repeats must be a positive integer")
    values = np.array(array, dtype=np.float64, copy=True)
    if values.ndim not in (2, 3):
        raise GateContractError("token arrays must have rank 2 ([B, T]) or 3 ([B, T, d])")
    return np.repeat(values, repeats, axis=1)


# --------------------------------------------------------------------------- #
# Synthetic recall episodes on the simulator (mechanistic positive control)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RecallSimulatorConfig:
    """Synthetic translation-paired recall episode for the NumPy simulator.

    An episode writes ``facts`` random (key, value) pairs, then
    ``distractor_sentences`` sentences whose content is ``english_tokens_per_
    sentence`` random tokens; a language of fertility f spreads the same
    content over round(f * english_tokens_per_sentence) tokens, so token count
    and only token count changes with fertility. The query reads the state with
    one fact key; exact match is the argmax over the fact values after adding a
    fertility-independent readout noise drawn once per episode (paired across
    surgery settings) so that English sits below the K7 ceiling.
    """

    facts: int = 8
    distractor_sentences: int = 16
    english_tokens_per_sentence: int = 6
    key_dim: int = 48
    value_dim: int = 16
    per_token_log_decay: float = -0.006
    fact_write_gate: float = 0.95
    distractor_write_gate: float = 0.1
    readout_noise: float = 0.0

    def __post_init__(self) -> None:
        if min(self.facts, self.distractor_sentences, self.english_tokens_per_sentence) < 1:
            raise GateContractError("episode counts must be positive")
        if min(self.key_dim, self.value_dim) < 2:
            raise GateContractError("key and value dimensions must be at least 2")
        if not math.isfinite(self.per_token_log_decay) or self.per_token_log_decay > 0.0:
            raise GateContractError("per_token_log_decay must be finite and non-positive")
        if not math.isfinite(self.readout_noise) or self.readout_noise < 0.0:
            raise GateContractError("readout_noise must be finite and non-negative")
        for name in ("fact_write_gate", "distractor_write_gate"):
            value = getattr(self, name)
            if not 0.0 < value <= 1.0:
                raise GateContractError(f"{name} must lie in (0, 1]")

    def tokens_per_sentence(self, fertility: float) -> int:
        f = _positive_scalar(fertility, name="fertility")
        return max(1, round(f * self.english_tokens_per_sentence))


def _unit_rows(rng: np.random.Generator, shape: tuple[int, ...]) -> FloatArray:
    raw = rng.standard_normal(shape)
    return raw / np.linalg.norm(raw, axis=-1, keepdims=True)


@dataclass(frozen=True, slots=True)
class EpisodeBank:
    """Episode content drawn once per seed so every (language, r) cell is paired by id."""

    fact_keys: FloatArray
    fact_values: FloatArray
    content_keys: FloatArray
    content_values: FloatArray
    query_fact: IntArray
    readout_noise: FloatArray

    @property
    def episodes(self) -> int:
        return int(self.fact_keys.shape[0])


def draw_episode_bank(
    rng: np.random.Generator,
    config: RecallSimulatorConfig,
    episodes: int,
) -> EpisodeBank:
    if episodes < 2:
        raise GateContractError("at least two episodes are needed")
    content = config.distractor_sentences * config.english_tokens_per_sentence
    return EpisodeBank(
        fact_keys=_unit_rows(rng, (episodes, config.facts, config.key_dim)),
        fact_values=_unit_rows(rng, (episodes, config.facts, config.value_dim)),
        content_keys=_unit_rows(rng, (episodes, content, config.key_dim)),
        content_values=_unit_rows(rng, (episodes, content, config.value_dim)),
        query_fact=rng.integers(0, config.facts, size=episodes, dtype=np.int64),
        readout_noise=rng.standard_normal((episodes, config.facts)),
    )


def simulate_recall_exact_match(
    bank: EpisodeBank,
    config: RecallSimulatorConfig,
    *,
    fertility: float,
    decay_ratio: float,
    write_ratio: float = 1.0,
    readout_noise_multiplier: float = 1.0,
) -> BoolArray:
    """Exact-match recall per episode for one (token fertility, surgery) cell.

    ``fertility`` drives the token count only. ``readout_noise_multiplier``
    scales the fertility-independent readout noise and exists so a negative
    control can install a language-identity difficulty without touching token
    count.
    """

    multiplier = _positive_scalar(readout_noise_multiplier, name="readout_noise_multiplier")
    per_sentence = config.tokens_per_sentence(fertility)
    content_index = np.floor(
        np.arange(per_sentence) * config.english_tokens_per_sentence / per_sentence
    ).astype(np.int64)
    sentence_offsets = np.repeat(
        np.arange(config.distractor_sentences) * config.english_tokens_per_sentence, per_sentence
    )
    token_content = sentence_offsets + np.tile(content_index, config.distractor_sentences)
    keys = np.concatenate([bank.fact_keys, bank.content_keys[:, token_content, :]], axis=1)
    values = np.concatenate([bank.fact_values, bank.content_values[:, token_content, :]], axis=1)
    length = keys.shape[1]
    log_decay = np.full((bank.episodes, length), config.per_token_log_decay)
    write_gate = np.concatenate(
        [
            np.full((bank.episodes, config.facts), config.fact_write_gate),
            np.full((bank.episodes, length - config.facts), config.distractor_write_gate),
        ],
        axis=1,
    )
    surged_decay = np.stack([constant_decay_surgery(row, decay_ratio) for row in log_decay], axis=0)
    surged_write = np.stack([write_surgery(row, write_ratio) for row in write_gate], axis=0)
    _, state = gated_delta_scan(keys, values, surged_decay, surged_write)
    query_keys = bank.fact_keys[np.arange(bank.episodes), bank.query_fact, :]
    readout = np.einsum("bvk,bk->bv", state, query_keys)
    scores = np.einsum("bfv,bv->bf", bank.fact_values, readout)
    scores = scores + multiplier * config.readout_noise * bank.readout_noise
    return np.asarray(scores.argmax(axis=1) == bank.query_fact, dtype=np.bool_)


# --------------------------------------------------------------------------- #
# Attention windows: prefix-blind within-sentence window and query-only mask
# --------------------------------------------------------------------------- #


def _sentence_ids(values: object) -> IntArray:
    ids = np.asarray(values)
    if ids.ndim != 1 or ids.size < 1 or not np.issubdtype(ids.dtype, np.integer):
        raise GateContractError("sentence ids must be a non-empty integer vector")
    if np.any(np.diff(ids) < 0):
        raise GateContractError("sentence ids must be non-decreasing along the episode")
    return ids.astype(np.int64)


def causal_mask(length: int) -> BoolArray:
    if length < 1:
        raise GateContractError("length must be positive")
    return np.tril(np.ones((length, length), dtype=np.bool_))


def sentence_window_mask(sentence_ids: object) -> BoolArray:
    """Pass B: token t may attend to s only if s <= t and both lie in the same sentence."""

    ids = _sentence_ids(sentence_ids)
    return causal_mask(ids.size) & (ids[:, None] == ids[None, :])


def query_only_mask(sentence_ids: object, query_sentence: int) -> BoolArray:
    """Pass A secondary readout: causal, but query tokens attend only within the query."""

    ids = _sentence_ids(sentence_ids)
    if query_sentence not in set(ids.tolist()):
        raise GateContractError("query sentence id is not present in the episode")
    mask = causal_mask(ids.size)
    is_query = ids == query_sentence
    mask[is_query, :] &= is_query[None, :]
    return mask


def _validated_mask(mask: object, length: int) -> BoolArray:
    values = np.asarray(mask)
    if values.shape != (length, length) or values.dtype != np.bool_:
        raise GateContractError("mask must be a boolean [T, T] matrix")
    if np.any(~values.any(axis=1)):
        raise GateContractError("every token needs at least one permitted key")
    if np.any(values & ~causal_mask(length)):
        raise GateContractError("mask must not permit attention to future tokens")
    return values


def mask_is_prefix_blind(mask: object, sentence_ids: object) -> bool:
    """True when no permitted (query, key) pair crosses a sentence boundary."""

    ids = _sentence_ids(sentence_ids)
    values = _validated_mask(mask, ids.size)
    crosses = ids[:, None] != ids[None, :]
    return not bool(np.any(values & crosses))


def masked_attention(queries: object, keys: object, values: object, mask: object) -> FloatArray:
    """Single-head softmax attention with -inf masking (exact zeros for forbidden keys)."""

    q = _batched(queries, name="queries", rank=2)
    k = _batched(keys, name="keys", rank=2)
    v = _batched(values, name="values", rank=2)
    if q.shape != k.shape or v.shape[0] != k.shape[0]:
        raise GateContractError("queries, keys and values must share the token axis")
    allowed = _validated_mask(mask, q.shape[0])
    logits = (q @ k.T) / math.sqrt(q.shape[1])
    logits = np.where(allowed, logits, -np.inf)
    logits -= logits.max(axis=1, keepdims=True)
    weights = np.exp(logits)
    weights /= weights.sum(axis=1, keepdims=True)
    return weights @ v


def attention_window_gradients(
    queries: object,
    keys: object,
    values: object,
    mask: object,
    cotangent: object,
) -> tuple[FloatArray, FloatArray]:
    """Per-pair gradient magnitudes of <out_t, u_t> with respect to k_s and v_s.

    Returns ([T, T] key gradient norms, [T, T] value gradient norms). With
    -inf masking the softmax weight of a forbidden key is exactly zero, so both
    gradients are exactly zero outside the permitted window; the doctor checks
    that literally.
    """

    q = _batched(queries, name="queries", rank=2)
    k = _batched(keys, name="keys", rank=2)
    v = _batched(values, name="values", rank=2)
    u = _batched(cotangent, name="cotangent", rank=2)
    if u.shape != v.shape:
        raise GateContractError("cotangent must match the value array")
    allowed = _validated_mask(mask, q.shape[0])
    scale = 1.0 / math.sqrt(q.shape[1])
    logits = np.where(allowed, (q @ k.T) * scale, -np.inf)
    logits -= logits.max(axis=1, keepdims=True)
    weights = np.exp(logits)
    weights /= weights.sum(axis=1, keepdims=True)
    out = weights @ v
    value_dot = v @ u.T  # [s, t] -> v_s . u_t
    out_dot = np.einsum("td,td->t", out, u)  # out_t . u_t
    key_grad = (
        np.abs(weights * (value_dot.T - out_dot[:, None])) * np.linalg.norm(q, axis=1)[:, None]
    )
    key_grad *= scale
    value_grad = weights * np.linalg.norm(u, axis=1)[:, None]
    return key_grad, value_grad


@dataclass(frozen=True, slots=True)
class AttentionWindowAudit:
    """Zero-gradient and bitwise-perturbation audit of one attention mask."""

    prefix_blind: bool
    max_outside_key_gradient: float
    max_outside_value_gradient: float
    mean_inside_value_gradient: float
    outside_pairs: int
    perturbation_max_abs_change: float

    @property
    def zero_gradient_outside_window(self) -> bool:
        return (
            self.max_outside_key_gradient == 0.0
            and self.max_outside_value_gradient == 0.0
            and self.perturbation_max_abs_change == 0.0
        )


def audit_attention_window(
    rng: np.random.Generator,
    mask: object,
    sentence_ids: object,
    *,
    model_dim: int = 8,
) -> AttentionWindowAudit:
    """Analytic zero-gradient check plus a bitwise perturbation probe for a mask."""

    ids = _sentence_ids(sentence_ids)
    allowed = _validated_mask(mask, ids.size)
    length = ids.size
    q = rng.standard_normal((length, model_dim))
    k = rng.standard_normal((length, model_dim))
    v = rng.standard_normal((length, model_dim))
    u = _unit_rows(rng, (length, model_dim))
    key_grad, value_grad = attention_window_gradients(q, k, v, allowed, u)
    outside = ~allowed
    baseline = masked_attention(q, k, v, allowed)
    perturbation = 0.0
    for t in range(length):
        forbidden = np.flatnonzero(outside[t])
        if forbidden.size == 0:
            continue
        k_perturbed = k.copy()
        v_perturbed = v.copy()
        k_perturbed[forbidden] += rng.standard_normal((forbidden.size, model_dim))
        v_perturbed[forbidden] += rng.standard_normal((forbidden.size, model_dim))
        changed = masked_attention(q, k_perturbed, v_perturbed, allowed)[t]
        perturbation = max(perturbation, float(np.max(np.abs(changed - baseline[t]))))
    return AttentionWindowAudit(
        prefix_blind=mask_is_prefix_blind(allowed, ids),
        max_outside_key_gradient=float(key_grad[outside].max()) if outside.any() else 0.0,
        max_outside_value_gradient=float(value_grad[outside].max()) if outside.any() else 0.0,
        mean_inside_value_gradient=float(value_grad[allowed].mean()),
        outside_pairs=int(outside.sum()),
        perturbation_max_abs_change=perturbation,
    )


# --------------------------------------------------------------------------- #
# Phase-1 anchored log-ratio span-parity loss (gradient and invariances)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SpanParityConfig:
    parity_weight: float = 1.0
    write_weight: float = 1.0
    anchor_weight: float = 1.0
    epsilon: float = 1e-8

    def __post_init__(self) -> None:
        for name in ("parity_weight", "write_weight", "anchor_weight"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise GateContractError(f"{name} must be finite and non-negative")
        if not math.isfinite(self.epsilon) or self.epsilon <= 0.0:
            raise GateContractError("epsilon must be finite and positive")


@dataclass(frozen=True, slots=True)
class SpanParityResult:
    loss: float
    parity_term: float
    write_term: float
    anchor_term: float
    grad_log_decay: FloatArray = field(repr=False)
    grad_write_gate: FloatArray = field(repr=False)


def _spans(spans: Sequence[tuple[int, int]], length: int) -> tuple[tuple[int, int], ...]:
    if not spans:
        raise GateContractError("at least one span is required")
    checked = []
    for start, end in spans:
        if not 0 <= start < end <= length:
            raise GateContractError("spans must be non-empty half-open ranges inside the trace")
        checked.append((int(start), int(end)))
    return tuple(checked)


def span_parity_loss(
    log_decay: object,
    write_gate: object,
    spans: Sequence[tuple[int, int]],
    pairs: Sequence[tuple[int, int]],
    *,
    anchor_span: int,
    anchor_value: float,
    config: SpanParityConfig | None = None,
) -> SpanParityResult:
    """Anchored log-ratio span-parity loss with its analytic gradient.

    L = lam * sum_pairs (log(F_a + eps) - log(F_b + eps))^2
        + lam_W * (same with W) + kappa * (mean_{t in anchor span} g_t - anchor)^2
    """

    cfg = config or SpanParityConfig()
    g = _log_decay_vector(log_decay)
    beta = _write_gate_vector(write_gate)
    if g.shape != beta.shape:
        raise GateContractError("log_decay and write_gate must share the token axis")
    owned = _spans(spans, g.size)
    if not pairs:
        raise GateContractError("at least one span pair is required")
    if not 0 <= anchor_span < len(owned):
        raise GateContractError("anchor_span must index a span")
    anchor = _finite_scalar(anchor_value, name="anchor_value")
    f_mass = np.array([-g[s:e].sum() for s, e in owned])
    w_mass = np.array([beta[s:e].sum() for s, e in owned])
    grad_f = np.zeros_like(f_mass)
    grad_w = np.zeros_like(w_mass)
    parity = 0.0
    write = 0.0
    for a, b in pairs:
        if not (0 <= a < len(owned) and 0 <= b < len(owned)) or a == b:
            raise GateContractError("pairs must index two distinct spans")
        diff_f = math.log(f_mass[a] + cfg.epsilon) - math.log(f_mass[b] + cfg.epsilon)
        diff_w = math.log(w_mass[a] + cfg.epsilon) - math.log(w_mass[b] + cfg.epsilon)
        parity += diff_f**2
        write += diff_w**2
        grad_f[a] += 2.0 * diff_f / (f_mass[a] + cfg.epsilon)
        grad_f[b] -= 2.0 * diff_f / (f_mass[b] + cfg.epsilon)
        grad_w[a] += 2.0 * diff_w / (w_mass[a] + cfg.epsilon)
        grad_w[b] -= 2.0 * diff_w / (w_mass[b] + cfg.epsilon)
    grad_g = np.zeros_like(g)
    grad_beta = np.zeros_like(beta)
    for index, (s, e) in enumerate(owned):
        grad_g[s:e] += -cfg.parity_weight * grad_f[index]  # dF/dg_t = -1
        grad_beta[s:e] += cfg.write_weight * grad_w[index]  # dW/dbeta_t = +1
    s, e = owned[anchor_span]
    mean_anchor = float(g[s:e].mean())
    anchor_term = (mean_anchor - anchor) ** 2
    grad_g[s:e] += cfg.anchor_weight * 2.0 * (mean_anchor - anchor) / (e - s)
    return SpanParityResult(
        loss=cfg.parity_weight * parity
        + cfg.write_weight * write
        + cfg.anchor_weight * anchor_term,
        parity_term=parity,
        write_term=write,
        anchor_term=anchor_term,
        grad_log_decay=grad_g,
        grad_write_gate=grad_beta,
    )


def span_parity_gradient_error(
    log_decay: object,
    write_gate: object,
    spans: Sequence[tuple[int, int]],
    pairs: Sequence[tuple[int, int]],
    *,
    anchor_span: int,
    anchor_value: float,
    config: SpanParityConfig | None = None,
    step: float = 1e-6,
) -> float:
    """Max relative error between the analytic gradient and central differences."""

    g = _log_decay_vector(log_decay)
    beta = _write_gate_vector(write_gate)
    result = span_parity_loss(
        g, beta, spans, pairs, anchor_span=anchor_span, anchor_value=anchor_value, config=config
    )
    worst = 0.0

    def evaluate(gg: FloatArray, bb: FloatArray) -> float:
        return span_parity_loss(
            gg, bb, spans, pairs, anchor_span=anchor_span, anchor_value=anchor_value, config=config
        ).loss

    for index in range(g.size):
        plus = g.copy()
        minus = g.copy()
        plus[index] = min(plus[index] + step, 0.0)
        minus[index] -= step
        numeric = (evaluate(plus, beta) - evaluate(minus, beta)) / (plus[index] - minus[index])
        worst = max(worst, abs(numeric - result.grad_log_decay[index]) / (1.0 + abs(numeric)))
    for index in range(beta.size):
        plus = beta.copy()
        minus = beta.copy()
        plus[index] = min(plus[index] + step, 1.0)
        minus[index] = max(minus[index] - step, 1e-12)
        numeric = (evaluate(g, plus) - evaluate(g, minus)) / (plus[index] - minus[index])
        worst = max(worst, abs(numeric - result.grad_write_gate[index]) / (1.0 + abs(numeric)))
    return worst


# --------------------------------------------------------------------------- #
# Common-dose estimand, two-scale partial fertility slope, decision rules
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CommonDoseCell:
    """Episode-paired exact-match outcomes for one language at r = 1 and r = 2."""

    language: str
    fertility: float
    cc_share_percent: float
    em_reference: BoolArray = field(repr=False)
    em_dose: BoolArray = field(repr=False)

    def __post_init__(self) -> None:
        if not self.language:
            raise GateContractError("cell language must be named")
        _positive_scalar(self.fertility, name="fertility")
        _positive_scalar(self.cc_share_percent, name="cc_share_percent")
        reference = _bool_outcomes(self.em_reference, name="em_reference")
        dose = _bool_outcomes(self.em_dose, name="em_dose")
        if reference.shape != dose.shape:
            raise GateContractError("em_reference and em_dose must be paired episode by episode")
        reference.setflags(write=False)
        dose.setflags(write=False)
        object.__setattr__(self, "em_reference", reference)
        object.__setattr__(self, "em_dose", dose)

    @property
    def episodes(self) -> int:
        return int(self.em_reference.size)


def _smoothed_logit(successes: FloatArray, trials: float) -> FloatArray:
    return np.asarray(logit((successes + 0.5) / (trials + 1.0)), dtype=np.float64)


def common_dose_gain(cell: CommonDoseCell) -> tuple[float, float]:
    """G_L in EM points (0-100) and on the smoothed logit scale."""

    n = float(cell.episodes)
    reference = float(cell.em_reference.sum())
    dose = float(cell.em_dose.sum())
    em_points = 100.0 * (dose - reference) / n
    logit_gain = float(_smoothed_logit(np.array(dose), n) - _smoothed_logit(np.array(reference), n))
    return em_points, logit_gain


@dataclass(frozen=True, slots=True)
class SlopeFit:
    """Two-regressor fit y_L = a + beta_f log f_L + beta_c log CC_L over languages.

    ``lower``/``upper`` are the decision interval: the union of the analytic
    OLS t-interval (which carries between-language scatter) and the
    episode-clustered paired bootstrap percentile interval (which carries the
    within-language sampling noise), so the decision is conservative.
    """

    scale: str
    estimate: float
    standard_error: float
    ols_lower: float
    ols_upper: float
    bootstrap_lower: float
    bootstrap_upper: float
    lower: float
    upper: float
    resource_estimate: float
    marginal_estimate: float
    marginal_lower: float
    marginal_upper: float
    n_languages: int
    resamples: int

    def excludes_zero_positively(self) -> bool:
        return self.lower > 0.0

    def excludes_zero_negatively(self) -> bool:
        return self.upper < 0.0


def _design(log_f: FloatArray, log_cc: FloatArray | None) -> FloatArray:
    columns = [np.ones_like(log_f), log_f]
    if log_cc is not None:
        columns.append(log_cc)
    return np.column_stack(columns)


def _ols(design: FloatArray, y: FloatArray) -> tuple[FloatArray, FloatArray, int]:
    n, p = design.shape
    if n <= p:
        raise GateContractError(f"the fit needs more languages ({n}) than parameters ({p})")
    gram = design.T @ design
    if np.linalg.cond(gram) > 1e12:
        raise GateContractError("regressors are collinear or constant; the slope is not identified")
    inverse = np.linalg.inv(gram)
    coef = inverse @ design.T @ y
    residual = y - design @ coef
    df = n - p
    sigma2 = float(residual @ residual) / df
    se = np.sqrt(np.diag(inverse) * sigma2)
    return coef, se, df


def _cells_matrix(
    cells: Sequence[CommonDoseCell],
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    if len(cells) < 4:
        raise GateContractError("the two-regressor fit needs at least four languages")
    names = [cell.language for cell in cells]
    if len(set(names)) != len(names):
        raise GateContractError("languages must be distinct")
    n = cells[0].episodes
    if any(cell.episodes != n for cell in cells):
        raise GateContractError(
            "episode ids are paired across languages; every cell needs the same n"
        )
    reference = np.stack([cell.em_reference for cell in cells]).astype(np.float64)
    dose = np.stack([cell.em_dose for cell in cells]).astype(np.float64)
    log_f = np.log(np.array([cell.fertility for cell in cells]))
    log_cc = np.log(np.array([cell.cc_share_percent for cell in cells]))
    if np.ptp(log_f) == 0.0:
        raise GateContractError(
            "fertility is constant across languages; the slope is not identified"
        )
    return reference, dose, log_f, log_cc


def _gains(reference_sum: FloatArray, dose_sum: FloatArray, n: float, scale: str) -> FloatArray:
    if scale == "em":
        return 100.0 * (dose_sum - reference_sum) / n
    if scale == "logit":
        return _smoothed_logit(dose_sum, n) - _smoothed_logit(reference_sum, n)
    raise GateContractError("scale must be 'em' or 'logit'")


def fit_partial_fertility_slope(
    cells: Sequence[CommonDoseCell],
    *,
    scale: str,
    rng: np.random.Generator,
    resamples: int = 2000,
    confidence: float = 0.95,
    fertility_override: Sequence[float] | None = None,
    partial: bool = True,
) -> SlopeFit:
    """Partial (or marginal) fertility slope of the common-dose gain with a paired bootstrap."""

    if resamples < 50:
        raise GateContractError("at least 50 bootstrap resamples are required")
    if not 0.5 < confidence < 1.0:
        raise GateContractError("confidence must lie in (0.5, 1)")
    reference, dose, log_f, log_cc = _cells_matrix(cells)
    if fertility_override is not None:
        override = _finite_vector(fertility_override, name="fertility_override")
        if override.shape != log_f.shape or np.any(override <= 0.0):
            raise GateContractError("fertility_override must give one positive value per language")
        log_f = np.log(override)
    n = float(reference.shape[1])
    y = _gains(reference.sum(axis=1), dose.sum(axis=1), n, scale)
    partial_design = _design(log_f, log_cc if partial else None)
    marginal_design = _design(log_f, None)
    coef, se, df = _ols(partial_design, y)
    m_coef, m_se, m_df = _ols(marginal_design, y)
    t_partial = stats.t.ppf(0.5 + confidence / 2.0, df)
    t_marginal = stats.t.ppf(0.5 + confidence / 2.0, m_df)
    projector = np.linalg.solve(partial_design.T @ partial_design, partial_design.T)
    m_projector = np.linalg.solve(marginal_design.T @ marginal_design, marginal_design.T)
    indices = rng.integers(0, int(n), size=(resamples, int(n)))
    boot_slopes = np.empty(resamples)
    boot_marginal = np.empty(resamples)
    for b in range(resamples):
        take = indices[b]
        gains = _gains(reference[:, take].sum(axis=1), dose[:, take].sum(axis=1), n, scale)
        boot_slopes[b] = (projector @ gains)[1]
        boot_marginal[b] = (m_projector @ gains)[1]
    alpha = 1.0 - confidence
    b_lower, b_upper = np.quantile(boot_slopes, [alpha / 2.0, 1.0 - alpha / 2.0])
    mb_lower, mb_upper = np.quantile(boot_marginal, [alpha / 2.0, 1.0 - alpha / 2.0])
    ols_lower = float(coef[1] - t_partial * se[1])
    ols_upper = float(coef[1] + t_partial * se[1])
    return SlopeFit(
        scale=scale,
        estimate=float(coef[1]),
        standard_error=float(se[1]),
        ols_lower=ols_lower,
        ols_upper=ols_upper,
        bootstrap_lower=float(b_lower),
        bootstrap_upper=float(b_upper),
        lower=min(ols_lower, float(b_lower)),
        upper=max(ols_upper, float(b_upper)),
        resource_estimate=float(coef[2]) if partial else 0.0,
        marginal_estimate=float(m_coef[1]),
        marginal_lower=min(float(m_coef[1] - t_marginal * m_se[1]), float(mb_lower)),
        marginal_upper=max(float(m_coef[1] + t_marginal * m_se[1]), float(mb_upper)),
        n_languages=int(len(cells)),
        resamples=int(resamples),
    )


def synthetic_fertility_baseline_cost(
    cells: Sequence[CommonDoseCell],
    *,
    rng: np.random.Generator,
    resamples: int = 2000,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Slope of the smoothed logit EM at r = 1 on log f over synthetic-fertility English cells.

    Returns (estimate, lower, upper) with the same conservative union interval.
    Under the clock hypothesis token count costs recall with language fixed, so
    the upper bound should sit below zero.
    """

    if resamples < 50:
        raise GateContractError("at least 50 bootstrap resamples are required")
    if len(cells) < 3:
        raise GateContractError("the baseline-cost slope needs at least three fertility values")
    n = cells[0].episodes
    if any(cell.episodes != n for cell in cells):
        raise GateContractError("synthetic-fertility cells must share episode ids")
    reference = np.stack([cell.em_reference for cell in cells]).astype(np.float64)
    log_f = np.log(np.array([cell.fertility for cell in cells]))
    if np.ptp(log_f) == 0.0:
        raise GateContractError("synthetic fertility values must vary")
    design = _design(log_f, None)
    y = _smoothed_logit(reference.sum(axis=1), float(n))
    coef, se, df = _ols(design, y)
    t_value = stats.t.ppf(0.5 + confidence / 2.0, df)
    projector = np.linalg.solve(design.T @ design, design.T)
    indices = rng.integers(0, n, size=(resamples, n))
    boot = np.array(
        [
            (projector @ _smoothed_logit(reference[:, take].sum(axis=1), float(n)))[1]
            for take in indices
        ]
    )
    alpha = 1.0 - confidence
    b_lower, b_upper = np.quantile(boot, [alpha / 2.0, 1.0 - alpha / 2.0])
    return (
        float(coef[1]),
        min(float(coef[1] - t_value * se[1]), float(b_lower)),
        max(float(coef[1] + t_value * se[1]), float(b_upper)),
    )


def fit_tracking_slope(
    cells: Sequence[CommonDoseCell],
    synthetic_cells: Sequence[CommonDoseCell],
    *,
    scale: str,
    rng: np.random.Generator,
    resamples: int = 2000,
    confidence: float = 0.95,
    match_tolerance: float = 1e-9,
) -> SlopeFit:
    """Slope on log f of D_L = G_L - G_syn(f_L), the gain not reproduced by token count.

    Every grid language is matched to the re-segmented English cell with the
    same fertility (English itself matches the canonical f = 1 cell). Under the
    clock hypothesis the residual dose-response D_L has no fertility slope;
    under headroom or language-identity alternatives it carries the whole
    cross-language slope. Episodes are resampled jointly across the real and
    synthetic cells (shared episode ids).
    """

    if resamples < 50:
        raise GateContractError("at least 50 bootstrap resamples are required")
    reference, dose, log_f, _ = _cells_matrix(cells)
    if len(synthetic_cells) < 3:
        raise GateContractError("tracking needs at least three synthetic-fertility cells")
    n = cells[0].episodes
    if any(cell.episodes != n for cell in synthetic_cells):
        raise GateContractError("synthetic cells must share episode ids with the grid cells")
    synthetic_f = np.array([cell.fertility for cell in synthetic_cells])
    matched = []
    for cell in cells:
        hits = np.flatnonzero(np.abs(synthetic_f - cell.fertility) <= match_tolerance)
        if hits.size != 1:
            raise GateContractError(
                f"language {cell.language} needs exactly one synthetic cell at fertility "
                f"{cell.fertility}"
            )
        matched.append(int(hits[0]))
    syn_reference = np.stack([synthetic_cells[i].em_reference for i in matched]).astype(np.float64)
    syn_dose = np.stack([synthetic_cells[i].em_dose for i in matched]).astype(np.float64)
    design = _design(log_f, None)
    count = float(n)
    y = _gains(reference.sum(axis=1), dose.sum(axis=1), count, scale) - _gains(
        syn_reference.sum(axis=1), syn_dose.sum(axis=1), count, scale
    )
    coef, se, df = _ols(design, y)
    t_value = stats.t.ppf(0.5 + confidence / 2.0, df)
    projector = np.linalg.solve(design.T @ design, design.T)
    indices = rng.integers(0, n, size=(resamples, n))
    boot = np.empty(resamples)
    for b in range(resamples):
        take = indices[b]
        residual = _gains(
            reference[:, take].sum(axis=1), dose[:, take].sum(axis=1), count, scale
        ) - _gains(syn_reference[:, take].sum(axis=1), syn_dose[:, take].sum(axis=1), count, scale)
        boot[b] = (projector @ residual)[1]
    alpha = 1.0 - confidence
    b_lower, b_upper = np.quantile(boot, [alpha / 2.0, 1.0 - alpha / 2.0])
    ols_lower = float(coef[1] - t_value * se[1])
    ols_upper = float(coef[1] + t_value * se[1])
    return SlopeFit(
        scale=scale,
        estimate=float(coef[1]),
        standard_error=float(se[1]),
        ols_lower=ols_lower,
        ols_upper=ols_upper,
        bootstrap_lower=float(b_lower),
        bootstrap_upper=float(b_upper),
        lower=min(ols_lower, float(b_lower)),
        upper=max(ols_upper, float(b_upper)),
        resource_estimate=0.0,
        marginal_estimate=float(coef[1]),
        marginal_lower=min(ols_lower, float(b_lower)),
        marginal_upper=max(ols_upper, float(b_upper)),
        n_languages=int(len(cells)),
        resamples=int(resamples),
    )


def logit_conjunct_sensitivity(
    fit_em: SlopeFit,
    fit_logit: SlopeFit,
    *,
    minimum_em_points: float = 3.0,
    minimum_logit: float = 0.15,
) -> GateVerdict:
    """Reported sensitivity (not decision-bearing): both scales clear their minimum slope.

    This is the wave-4 reviewers' proposed conjunct. The doctor's simulator
    case shows the logit gain of a pure per-token clock is form-dependent (an
    exponential-retention readout gives a nearly flat logit gain over the
    grid), so the conjunct can refuse a true clock; it is therefore reported
    next to the decision-bearing token-count comparator, never as a kill.
    """

    if fit_em.scale != "em" or fit_logit.scale != "logit":
        raise GateContractError("the sensitivity needs one EM-scale fit and one logit-scale fit")
    em_ok = fit_em.excludes_zero_positively() and fit_em.estimate >= minimum_em_points
    logit_ok = fit_logit.excludes_zero_positively() and fit_logit.estimate >= minimum_logit
    return GateVerdict(
        name="logit-conjunct-sensitivity",
        kind="classification",
        verdict=bool(em_ok and logit_ok),
        statistics={
            "em_estimate": fit_em.estimate,
            "em_lower": fit_em.lower,
            "em_upper": fit_em.upper,
            "logit_estimate": fit_logit.estimate,
            "logit_lower": fit_logit.lower,
            "logit_upper": fit_logit.upper,
            "minimum_em_points": minimum_em_points,
            "minimum_logit": minimum_logit,
            "em_scale_alone_would_claim": float(em_ok),
            "logit_scale_alone_would_claim": float(logit_ok),
        },
        note="reviewer-proposed two-scale conjunct, reported as headroom sensitivity",
    )


def p3_common_dose_prediction(
    fit_em: SlopeFit,
    synthetic_em_fit: SlopeFit,
    tracking_em_fit: SlopeFit,
    *,
    minimum_em_points: float = 3.0,
) -> GateVerdict:
    """P3 (wave 5): the cross-language slope clears AND re-segmented English reproduces it.

    (a) partial fertility slope of G_L: lower bound above 0, estimate at least
        ``minimum_em_points``;
    (b) the slope of G_syn on log f over re-segmented English (token count
        changed; language, tokenizer, resource share and translation quality
        fixed): lower bound above 0, estimate at least ``minimum_em_points``;
    (c) tracking: the slope of the residual D_L = G_L - G_syn(f_L) has a point
        estimate inside (-minimum, +minimum), so the cross-language
        dose-response matches the token-count dose-response to within the
        minimum worthwhile slope. A residual whose interval lies entirely
        outside [-minimum, +minimum] is a significant mismatch (K11); a
        residual estimate outside the band whose interval still reaches the
        band is the pre-registered inconclusive band (second episode block).
    """

    if fit_em.scale != "em" or synthetic_em_fit.scale != "em" or tracking_em_fit.scale != "em":
        raise GateContractError("P3 is decided on EM-point-scale fits")
    cross_ok = fit_em.excludes_zero_positively() and fit_em.estimate >= minimum_em_points
    synthetic_ok = (
        synthetic_em_fit.excludes_zero_positively()
        and synthetic_em_fit.estimate >= minimum_em_points
    )
    tracking_ok = abs(tracking_em_fit.estimate) < minimum_em_points
    mismatch = (
        tracking_em_fit.lower > minimum_em_points or tracking_em_fit.upper < -minimum_em_points
    )
    return GateVerdict(
        name="P3-common-dose-slope-reproduced-by-token-count",
        kind="prediction",
        verdict=bool(cross_ok and synthetic_ok and tracking_ok),
        statistics={
            "cross_language_estimate": fit_em.estimate,
            "cross_language_lower": fit_em.lower,
            "cross_language_upper": fit_em.upper,
            "synthetic_english_estimate": synthetic_em_fit.estimate,
            "synthetic_english_lower": synthetic_em_fit.lower,
            "synthetic_english_upper": synthetic_em_fit.upper,
            "tracking_estimate": tracking_em_fit.estimate,
            "tracking_lower": tracking_em_fit.lower,
            "tracking_upper": tracking_em_fit.upper,
            "minimum_em_points": minimum_em_points,
            "cross_language_clears": float(cross_ok),
            "synthetic_english_clears": float(synthetic_ok),
            "tracking_clears": float(tracking_ok),
            "tracking_mismatch_significant": float(mismatch),
        },
        note="all three conditions are required on every co-primary subject",
    )


def k2_pooled_kill(
    fits_by_subject: Mapping[str, SlopeFit],
    *,
    minimum_em_points: float = 3.0,
    heterogeneity_alpha: float = 0.1,
) -> GateVerdict:
    """K2: pooled EM-scale slope has an upper bound below the minimum and no subject is positive."""

    if len(fits_by_subject) < 2:
        raise GateContractError("the pooled kill needs at least two co-primary subjects")
    estimates = np.array([fit.estimate for fit in fits_by_subject.values()])
    ses = np.array([fit.standard_error for fit in fits_by_subject.values()])
    if np.any(ses <= 0.0) or any(fit.scale != "em" for fit in fits_by_subject.values()):
        raise GateContractError("pooled kill needs EM-scale fits with positive standard errors")
    weights = 1.0 / ses**2
    pooled = float((weights * estimates).sum() / weights.sum())
    pooled_se = float(1.0 / math.sqrt(weights.sum()))
    q_statistic = float((weights * (estimates - pooled) ** 2).sum())
    q_p = float(stats.chi2.sf(q_statistic, df=len(estimates) - 1))
    heterogeneous = q_p < heterogeneity_alpha
    z = stats.norm.ppf(0.975)
    pooled_upper = pooled + z * pooled_se
    any_positive = any(fit.excludes_zero_positively() for fit in fits_by_subject.values())
    if heterogeneous:
        fires = (
            all(fit.upper < minimum_em_points for fit in fits_by_subject.values())
            and not any_positive
        )
    else:
        fires = pooled_upper < minimum_em_points and not any_positive
    return GateVerdict(
        name="K2-clock-not-the-bottleneck",
        kind="kill",
        verdict=bool(fires),
        statistics={
            "pooled_estimate": pooled,
            "pooled_standard_error": pooled_se,
            "pooled_upper": float(pooled_upper),
            "cochran_q": q_statistic,
            "cochran_q_p_value": q_p,
            "reverted_to_per_subject": float(heterogeneous),
            "minimum_em_points": minimum_em_points,
        },
        note="Cochran's Q below alpha 0.1 reverts the kill to per-subject intervals",
    )


def k8_resourcedness_kill(fit: SlopeFit) -> GateVerdict:
    """K8: the marginal slope excludes 0 but the partial slope's interval includes 0."""

    fires = fit.marginal_lower > 0.0 and fit.lower <= 0.0 <= fit.upper
    return GateVerdict(
        name="K8-effect-is-resourcedness",
        kind="kill",
        verdict=bool(fires),
        statistics={
            "marginal_lower": fit.marginal_lower,
            "partial_lower": fit.lower,
            "partial_upper": fit.upper,
        },
        note="fires when only the marginal slope excludes 0",
    )


def k9_sign_disagreement(fit_a: SlopeFit, fit_b: SlopeFit) -> GateVerdict:
    """K9: the two co-primary subjects' intervals exclude 0 with opposite signs."""

    fires = (fit_a.excludes_zero_positively() and fit_b.excludes_zero_negatively()) or (
        fit_a.excludes_zero_negatively() and fit_b.excludes_zero_positively()
    )
    return GateVerdict(
        name="K9-subject-specific-sign-disagreement",
        kind="kill",
        verdict=bool(fires),
        statistics={
            "estimate_a": fit_a.estimate,
            "lower_a": fit_a.lower,
            "upper_a": fit_a.upper,
            "estimate_b": fit_b.estimate,
            "lower_b": fit_b.lower,
            "upper_b": fit_b.upper,
        },
        note="no portable recipe is claimed when the subjects disagree in sign",
    )


def k11_synthetic_fertility_disagreement(
    fit_em: SlopeFit,
    synthetic_em_fit: SlopeFit,
    tracking_em_fit: SlopeFit,
    *,
    minimum_em_points: float = 3.0,
) -> GateVerdict:
    """K11 (wave-5 repair): the cross-language slope clears but token count does not reproduce it.

    Fires when the partial fertility slope of G_L clears its minimum while
    re-segmented English either shows no dose-response slope of its own or
    differs from the cross-language dose-response by a residual slope whose
    interval lies entirely outside the minimum worthwhile band; the fertility
    slope is then language identity or headroom, not the clock, and the outcome
    is K2-class with no claim.
    """

    p3 = p3_common_dose_prediction(
        fit_em, synthetic_em_fit, tracking_em_fit, minimum_em_points=minimum_em_points
    )
    cross_ok = p3.statistics["cross_language_clears"] == 1.0
    synthetic_ok = p3.statistics["synthetic_english_clears"] == 1.0
    mismatch = p3.statistics["tracking_mismatch_significant"] == 1.0
    return GateVerdict(
        name="K11-fertility-slope-is-not-the-clock",
        kind="kill",
        verdict=bool(cross_ok and (not synthetic_ok or mismatch)),
        statistics=dict(p3.statistics),
        note=(
            "token count manipulated with language, tokenizer and resource share fixed "
            "must reproduce the dose-response"
        ),
    )


def classify_common_dose_outcome(
    fit_em: SlopeFit,
    synthetic_em_fit: SlopeFit,
    tracking_em_fit: SlopeFit,
    *,
    minimum_em_points: float = 3.0,
) -> GateVerdict:
    """Pre-registered decision tree for one subject; the label is stored in ``note``."""

    p3 = p3_common_dose_prediction(
        fit_em, synthetic_em_fit, tracking_em_fit, minimum_em_points=minimum_em_points
    )
    k11 = k11_synthetic_fertility_disagreement(
        fit_em, synthetic_em_fit, tracking_em_fit, minimum_em_points=minimum_em_points
    )
    cross_ok = p3.statistics["cross_language_clears"] == 1.0
    synthetic_ok = p3.statistics["synthetic_english_clears"] == 1.0
    tracking_ok = p3.statistics["tracking_clears"] == 1.0
    if p3.verdict:
        label = "CLAIM"
    elif k11.verdict:
        label = "K11_NOT_THE_CLOCK"
    elif cross_ok:
        label = "INCONCLUSIVE_TRACKING_BAND_SECOND_EPISODE_BLOCK"
    elif synthetic_ok:
        label = "K2_CLOCK_REAL_BUT_NOT_CROSS_LINGUAL_BOTTLENECK"
    else:
        label = "K2_NO_FERTILITY_SLOPE"
    return GateVerdict(
        name="common-dose-outcome",
        kind="classification",
        verdict=True,
        statistics={
            "cross_language_clears": float(cross_ok),
            "synthetic_english_clears": float(synthetic_ok),
            "tracking_clears": float(tracking_ok),
            "tracking_mismatch_significant": p3.statistics["tracking_mismatch_significant"],
        },
        note=label,
    )


def k7_ceiling_hold(em_en_d128_percent: float, *, ceiling: float = 95.0) -> GateVerdict:
    value = _finite_scalar(em_en_d128_percent, name="EM(en) at d = 128")
    return GateVerdict(
        name="K7-probe-on-ceiling",
        kind="hold",
        verdict=bool(value > ceiling),
        statistics={"em_en_d128_percent": value, "ceiling": ceiling},
    )


def k7b_floor_hold(em_en_d8_percent: float, *, floor: float = 60.0) -> GateVerdict:
    value = _finite_scalar(em_en_d8_percent, name="EM(en) at d = 8")
    return GateVerdict(
        name="K7b-prefix-blind-floor",
        kind="hold",
        verdict=bool(value < floor),
        statistics={"em_en_d8_percent": value, "floor": floor},
    )


def k10_language_exclusion(
    redraw_rate_percent: Mapping[str, float],
    em_d8_percent: Mapping[str, float],
    *,
    redraw_cap: float = 25.0,
    floor: float = 60.0,
    minimum_languages: int = 12,
) -> GateVerdict:
    """K10: exclude translation-limited or floor-failing languages.

    The verdict is True when fewer than ``minimum_languages`` remain, so the
    subject cannot carry the primary.
    """

    if set(redraw_rate_percent) != set(em_d8_percent) or not redraw_rate_percent:
        raise GateContractError("redraw rates and floor EM must cover the same languages")
    excluded = sorted(
        language
        for language in redraw_rate_percent
        if _finite_scalar(redraw_rate_percent[language], name="redraw") > redraw_cap
        or _finite_scalar(em_d8_percent[language], name="EM d8") < floor
    )
    remaining = len(redraw_rate_percent) - len(excluded)
    return GateVerdict(
        name="K10-language-exclusion",
        kind="exclusion",
        verdict=bool(remaining < minimum_languages),
        statistics={
            "languages": float(len(redraw_rate_percent)),
            "excluded": float(len(excluded)),
            "remaining": float(remaining),
            "minimum_languages": float(minimum_languages),
        },
        note=",".join(excluded) if excluded else "none excluded",
    )


def k10b_subject_fallback(*, qwen_carries_primary: bool, rwkv7_carries_primary: bool) -> str:
    """Symmetric fallback (wave-5 repair): who carries the primary after K7b and K10."""

    if qwen_carries_primary and rwkv7_carries_primary:
        return "conjunction-on-both-subjects"
    if rwkv7_carries_primary:
        return "rwkv7-sole-primary-no-gdn-portability-claim"
    if qwen_carries_primary:
        return "qwen-prefix-blind-sole-primary-no-gdn-rwkv7-portability-claim"
    return "redesign-probe-before-any-surgery-claim"


def k3_uniform_effect_kill(
    gain_minus_english_at_r2: Mapping[str, float],
    interaction_at_fertility: Mapping[str, float],
    *,
    threshold: float = 2.0,
) -> GateVerdict:
    """K3: both interactions at most 2 EM points for every high-fertility language."""

    if not gain_minus_english_at_r2 or set(gain_minus_english_at_r2) != set(
        interaction_at_fertility
    ):
        raise GateContractError(
            "both interaction tables must cover the same high-fertility languages"
        )
    worst = max(
        max(
            _finite_scalar(gain_minus_english_at_r2[lang], name="G_L - G_en"),
            _finite_scalar(interaction_at_fertility[lang], name="r = f_L interaction"),
        )
        for lang in gain_minus_english_at_r2
    )
    return GateVerdict(
        name="K3-forget-less-helps-everyone-equally",
        kind="kill",
        verdict=bool(worst <= threshold),
        statistics={"max_interaction_em_points": worst, "threshold": threshold},
    )


def k4_script_gap_kill(
    gaps_em_points: Mapping[str, float],
    *,
    controls: Sequence[str] = ("tha", "kor", "zho-CN", "msa"),
    references: Sequence[str] = ("tam", "ben"),
    tolerance: float = 3.0,
) -> GateVerdict:
    """K4: low-fertility control gaps within 3 points of the Tamil and Bengali gaps."""

    missing = [lang for lang in (*controls, *references) if lang not in gaps_em_points]
    if missing:
        raise GateContractError(f"gap table lacks languages: {', '.join(missing)}")
    reference_gap = float(np.mean([gaps_em_points[lang] for lang in references]))
    worst = max(abs(gaps_em_points[lang] - reference_gap) for lang in controls)
    return GateVerdict(
        name="K4-gap-is-script-or-data",
        kind="kill",
        verdict=bool(worst <= tolerance),
        statistics={
            "max_abs_gap_difference": worst,
            "reference_gap": reference_gap,
            "tolerance": tolerance,
        },
    )


# --------------------------------------------------------------------------- #
# Parametric dose-response worlds (synthetic doctor cases only)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class LanguageCovariate:
    """Frozen covariates for one grid language; ``identity_offset`` is a non-clock logit offset."""

    language: str
    fertility: float
    cc_share_percent: float
    identity_offset: float = 0.0

    def __post_init__(self) -> None:
        if not self.language:
            raise GateContractError("language must be named")
        _positive_scalar(self.fertility, name="fertility")
        _positive_scalar(self.cc_share_percent, name="cc_share_percent")
        _finite_scalar(self.identity_offset, name="identity_offset")


@dataclass(frozen=True, slots=True)
class DoseResponseWorld:
    """Bernoulli readout model used only to exercise the decision rules.

    logit p(r = 1) = baseline_logit + identity_offset - identity_level_slope * log f * [real]
                     - clock_cost * (f - 1)
    logit p(r = 2) = logit p(r = 1) + uniform_gain + identity_gain_slope * log f * [real]
                     + clock_cost * f / 2
    ``[real]`` is 1 for a grid language and 0 for re-segmented (synthetic-
    fertility) English, whose token count changes while its identity does not.
    """

    kind: str
    baseline_logit: float = 0.85
    clock_cost: float = 0.0
    uniform_gain: float = 0.0
    identity_level_slope: float = 0.0
    identity_gain_slope: float = 0.0
    episode_correlation: float = 0.5

    def __post_init__(self) -> None:
        if self.kind not in {"clock", "headroom", "identity", "null"}:
            raise GateContractError("world kind must be clock, headroom, identity or null")
        for name in (
            "baseline_logit",
            "clock_cost",
            "uniform_gain",
            "identity_level_slope",
            "identity_gain_slope",
        ):
            _finite_scalar(getattr(self, name), name=name)
        if not 0.0 <= self.episode_correlation < 1.0:
            raise GateContractError("episode_correlation must lie in [0, 1)")

    def success_logits(
        self, fertility: float, identity_offset: float, *, real_language: bool
    ) -> tuple[float, float]:
        f = _positive_scalar(fertility, name="fertility")
        indicator = 1.0 if real_language else 0.0
        reference = (
            self.baseline_logit
            + identity_offset
            - self.identity_level_slope * math.log(f) * indicator
            - self.clock_cost * (f - 1.0)
        )
        dose = (
            reference
            + self.uniform_gain
            + self.identity_gain_slope * math.log(f) * indicator
            + self.clock_cost * f / 2.0
        )
        return reference, dose


def _paired_bernoulli(
    rng: np.random.Generator,
    p_reference: float,
    p_dose: float,
    episodes: int,
    correlation: float,
) -> tuple[BoolArray, BoolArray]:
    shared = rng.standard_normal(episodes)
    noise = rng.standard_normal((2, episodes))
    z = math.sqrt(correlation) * shared[None, :] + math.sqrt(1.0 - correlation) * noise
    reference = z[0] < ndtri(p_reference)
    dose = z[1] < ndtri(p_dose)
    return reference.astype(np.bool_), dose.astype(np.bool_)


def simulate_common_dose_cells(
    rng: np.random.Generator,
    grid: Sequence[LanguageCovariate],
    world: DoseResponseWorld,
    *,
    episodes: int,
) -> tuple[CommonDoseCell, ...]:
    """Synthetic paired outcomes for every grid language (real-language semantics)."""

    if episodes < 2:
        raise GateContractError("at least two episodes are required")
    cells = []
    for covariate in grid:
        reference_logit, dose_logit = world.success_logits(
            covariate.fertility, covariate.identity_offset, real_language=True
        )
        reference, dose = _paired_bernoulli(
            rng,
            float(expit(reference_logit)),
            float(expit(dose_logit)),
            episodes,
            world.episode_correlation,
        )
        cells.append(
            CommonDoseCell(
                language=covariate.language,
                fertility=covariate.fertility,
                cc_share_percent=covariate.cc_share_percent,
                em_reference=reference,
                em_dose=dose,
            )
        )
    return tuple(cells)


def simulate_synthetic_fertility_english(
    rng: np.random.Generator,
    fertilities: Sequence[float],
    world: DoseResponseWorld,
    *,
    episodes: int,
    english_cc_share_percent: float,
) -> tuple[CommonDoseCell, ...]:
    """Synthetic paired outcomes for English re-segmented to each fertility (identity fixed)."""

    if episodes < 2:
        raise GateContractError("at least two episodes are required")
    values = _finite_vector(fertilities, name="fertilities", minimum_length=3)
    if np.any(values <= 0.0):
        raise GateContractError("fertilities must be positive")
    cells = []
    for index, fertility in enumerate(values.tolist()):
        reference_logit, dose_logit = world.success_logits(fertility, 0.0, real_language=False)
        reference, dose = _paired_bernoulli(
            rng,
            float(expit(reference_logit)),
            float(expit(dose_logit)),
            episodes,
            world.episode_correlation,
        )
        cells.append(
            CommonDoseCell(
                language=f"en-resegmented-{index:02d}",
                fertility=fertility,
                cc_share_percent=english_cc_share_percent,
                em_reference=reference,
                em_dose=dose,
            )
        )
    return tuple(cells)


__all__ = [
    "AttentionWindowAudit",
    "CommonDoseCell",
    "DoseResponseWorld",
    "EpisodeBank",
    "GateContractError",
    "GateVerdict",
    "LanguageCovariate",
    "LedgerEntry",
    "RecallSimulatorConfig",
    "SlopeFit",
    "SpanParityConfig",
    "SpanParityResult",
    "attention_window_gradients",
    "audit_attention_window",
    "build_gate_ledger",
    "causal_mask",
    "classify_common_dose_outcome",
    "common_dose_gain",
    "constant_decay_surgery",
    "draw_episode_bank",
    "duplicate_tokens",
    "fit_partial_fertility_slope",
    "fit_tracking_slope",
    "forgetting_mass",
    "gated_delta_scan",
    "k1_warp_invariance_kill",
    "k2_pooled_kill",
    "k3_uniform_effect_kill",
    "k4_script_gap_kill",
    "k7_ceiling_hold",
    "k7b_floor_hold",
    "k8_resourcedness_kill",
    "k9_sign_disagreement",
    "k10_language_exclusion",
    "k10b_subject_fallback",
    "k11_synthetic_fertility_disagreement",
    "log_decay_from_preactivation",
    "logit_conjunct_sensitivity",
    "mask_is_prefix_blind",
    "masked_attention",
    "p1_ledger_prediction",
    "p3_common_dose_prediction",
    "query_only_mask",
    "sentence_window_mask",
    "simulate_common_dose_cells",
    "simulate_recall_exact_match",
    "simulate_synthetic_fertility_english",
    "span_oracle_decay_surgery",
    "span_parity_gradient_error",
    "span_parity_loss",
    "synthetic_fertility_baseline_cost",
    "write_gate_from_preactivation",
    "write_mass",
    "write_surgery",
]
