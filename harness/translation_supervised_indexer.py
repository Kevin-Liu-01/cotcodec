"""Phase-0 reference objects for Direction 21, the translation-supervised sparse indexer.

Model-free and NumPy/SciPy-only. The module gives executable, typed forms to the
objects the proposal registers for its Phase-0 CPU doctors:

* the detached top-k indexer ``I_t(s) = sum_j w_tj ReLU(q_tj . k_s)`` with its
  causal softmax and deterministic top-k selection;
* the three label-free distillation targets (head-sum ``hs``, max-pool ``mp``,
  retrieval-head-weighted ``rh``) and the KL distillation loss;
* the fixed reference ``R^U`` (union of every head's own top-k, same k per head)
  and the budget-matched sensitivity row ``U_k``;
* per-condition needle selection recall and the derived statistics ``Delta``,
  ``xi_T``, ``xi^U_T``, ``S_T``, ``Lambda``, the ``T*`` selection rule and ``D``;
* the alignment log-mass loss ``L_x`` with label-mass accounting and its
  permuted-label (``L_perm``) and other-half (``L_half``) controls;
* the bilingual concatenation builder with corpus-given sentence alignment;
* a synthetic bilingual world (two scripts related by a fixed orthogonal map, a
  many-head softmax teacher, a rank-limited ReLU indexer trained by analytic
  gradients) for the excess-gap-and-repair sanity check;
* the three-way passage-id split (development / audit / primary) and the
  Phase-1 decision rule derived from a stated noise model (the wave-5 repair);
* the registered gates and kill conditions as pure functions.

Every number produced here is a synthetic-case number. Nothing in this module
touches a language model, a checkpoint, a tokenizer or real data; a doctor pass
proves executability and gate semantics only.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy import stats

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]

Aggregation = Literal["hs", "mp", "rh"]
LabelMode = Literal["none", "true", "permuted", "half"]
Condition = Literal["ML", "MN", "CS", "CX"]

AGGREGATIONS: tuple[Aggregation, ...] = ("hs", "mp", "rh")
CONDITIONS: tuple[Condition, ...] = ("ML", "MN", "CS", "CX")

# Registered thresholds (proposal, Mechanism and Evaluation sections). Recall
# statistics are expressed in recall points (0-100) throughout this module.
CONFIRM_THRESHOLD_POINTS = 6.0
KILL_CEILING_POINTS = 3.0
LOCALIZATION_CONFIRM_POINTS = 10.0
LOCALIZATION_KILL_POINTS = 5.0
ADEQUACY_TOLERANCE_POINTS = 5.0
MN_BAND_POINTS = 2.0
K2A_EVALUABLE_POINTS = 3.0
K2A_RECOVERY_FRACTION = 0.8
K3_FRACTION = 0.8
K4_FRACTION = 0.5
INERTNESS_TOLERANCE_POINTS = 1.0
LANGUAGE_HARM_POINTS = 2.0
E3_HARM_POINTS = 0.5
PHASE1_SEEDS = (42, 43, 44, 45, 46)


class IndexerContractError(ValueError):
    """Raised when an input violates the registered contract of a Phase-0 object."""


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #


def _finite_array(values: object, *, name: str, ndim: int | None = None) -> FloatArray:
    array = np.array(values, dtype=np.float64, copy=True)
    if ndim is not None and array.ndim != ndim:
        raise IndexerContractError(f"{name} must have {ndim} dimensions, got {array.ndim}")
    if not array.size:
        raise IndexerContractError(f"{name} must be non-empty")
    if not np.isfinite(array).all():
        raise IndexerContractError(f"{name} must be finite")
    return array


def _readonly(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _points(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.floating, np.integer)):
        raise IndexerContractError(f"{name} must be a real number in recall points")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 100.0:
        raise IndexerContractError(f"{name} must lie in [0, 100] recall points")
    return number


def _positive_int(value: object, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise IndexerContractError(f"{name} must be an integer")
    number = int(value)
    if number < minimum:
        raise IndexerContractError(f"{name} must be at least {minimum}")
    return number


def _index_vector(values: object, *, length: int, name: str) -> IntArray:
    array = np.array(values, copy=True)
    if array.ndim != 1 or not array.size:
        raise IndexerContractError(f"{name} must be a non-empty index vector")
    if not np.issubdtype(array.dtype, np.integer):
        raise IndexerContractError(f"{name} must contain integer token positions")
    array = array.astype(np.int64)
    if np.any(array < 0) or np.any(array >= length):
        raise IndexerContractError(f"{name} positions must lie inside the sequence")
    if len(np.unique(array)) != len(array):
        raise IndexerContractError(f"{name} positions must be unique")
    return array


def causal_mask(length: int) -> BoolArray:
    """True where key position s is visible from query position t (s <= t)."""

    length = _positive_int(length, name="length")
    return np.tril(np.ones((length, length), dtype=bool))


# --------------------------------------------------------------------------- #
# Indexer: parameters, forward pass, selection
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class IndexerParameters:
    """Detached indexer weights: per-head queries, one shared key, per-head gates.

    ``I_t(s) = sum_j w_tj * ReLU(q_tj . k_s)`` with ``q_tj = h_t Wq_j``,
    ``k_s = h_s Wk`` and ``w_tj = b_j + h_t Ww[:, j]`` (DSA token form; the block
    form of QSA differs only in the key granularity, which the doctor does not
    model).
    """

    query_projection: FloatArray
    key_projection: FloatArray
    head_gate: FloatArray
    head_bias: FloatArray

    def __post_init__(self) -> None:
        wq = _finite_array(self.query_projection, name="query_projection", ndim=3)
        wk = _finite_array(self.key_projection, name="key_projection", ndim=2)
        ww = _finite_array(self.head_gate, name="head_gate", ndim=2)
        bias = _finite_array(self.head_bias, name="head_bias", ndim=1)
        heads, d_model, rank = wq.shape
        if wk.shape != (d_model, rank):
            raise IndexerContractError("key_projection must be (d_model, rank)")
        if ww.shape != (d_model, heads):
            raise IndexerContractError("head_gate must be (d_model, heads)")
        if bias.shape != (heads,):
            raise IndexerContractError("head_bias must be (heads,)")
        object.__setattr__(self, "query_projection", _readonly(wq))
        object.__setattr__(self, "key_projection", _readonly(wk))
        object.__setattr__(self, "head_gate", _readonly(ww))
        object.__setattr__(self, "head_bias", _readonly(bias))

    @property
    def heads(self) -> int:
        return int(self.query_projection.shape[0])

    @property
    def d_model(self) -> int:
        return int(self.query_projection.shape[1])

    @property
    def rank(self) -> int:
        return int(self.query_projection.shape[2])

    @classmethod
    def random(
        cls,
        d_model: int,
        rank: int,
        heads: int,
        seed: int,
        scale: float = 0.2,
    ) -> IndexerParameters:
        d_model = _positive_int(d_model, name="d_model")
        rank = _positive_int(rank, name="rank")
        heads = _positive_int(heads, name="heads")
        if not math.isfinite(scale) or scale <= 0.0:
            raise IndexerContractError("scale must be positive")
        rng = np.random.default_rng(seed)
        return cls(
            query_projection=rng.normal(0.0, scale / math.sqrt(d_model), (heads, d_model, rank)),
            key_projection=rng.normal(0.0, scale / math.sqrt(d_model), (d_model, rank)),
            head_gate=np.zeros((d_model, heads)),
            head_bias=np.ones(heads),
        )

    def as_vector(self) -> FloatArray:
        return np.concatenate(
            [
                self.query_projection.ravel(),
                self.key_projection.ravel(),
                self.head_gate.ravel(),
                self.head_bias.ravel(),
            ]
        )

    def with_vector(self, vector: FloatArray) -> IndexerParameters:
        vector = _finite_array(vector, name="vector", ndim=1)
        sizes = [
            self.query_projection.size,
            self.key_projection.size,
            self.head_gate.size,
            self.head_bias.size,
        ]
        if vector.size != sum(sizes):
            raise IndexerContractError("parameter vector has the wrong length")
        parts = np.split(vector, np.cumsum(sizes)[:-1])
        return IndexerParameters(
            query_projection=parts[0].reshape(self.query_projection.shape),
            key_projection=parts[1].reshape(self.key_projection.shape),
            head_gate=parts[2].reshape(self.head_gate.shape),
            head_bias=parts[3].reshape(self.head_bias.shape),
        )

    def identity(self) -> str:
        return hashlib.sha256(self.as_vector().tobytes()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class IndexerForward:
    """Intermediate tensors of one batched indexer pass (kept for the backward pass)."""

    scores: FloatArray
    log_probs: FloatArray
    probs: FloatArray
    queries: FloatArray
    keys: FloatArray
    pre_activation: FloatArray
    activation: FloatArray
    gates: FloatArray


def _causal_log_softmax(scores: FloatArray) -> tuple[FloatArray, FloatArray]:
    length = scores.shape[-1]
    mask = causal_mask(length)
    masked = np.where(mask, scores, -np.inf)
    shift = masked.max(axis=-1, keepdims=True)
    exp = np.exp(masked - shift)
    total = exp.sum(axis=-1, keepdims=True)
    log_probs = masked - shift - np.log(total)
    probs = np.where(mask, exp / total, 0.0)
    return log_probs, probs


def indexer_forward(hidden: FloatArray, params: IndexerParameters) -> IndexerForward:
    """Score every visible key for every query token; returns causal softmax too."""

    hidden = _finite_array(hidden, name="hidden", ndim=3)
    if hidden.shape[-1] != params.d_model:
        raise IndexerContractError("hidden width must equal the indexer d_model")
    queries = np.einsum("btd,hdr->bhtr", hidden, params.query_projection)
    keys = np.einsum("btd,dr->btr", hidden, params.key_projection)
    pre_activation = np.einsum("bhtr,bsr->bhts", queries, keys)
    activation = np.maximum(pre_activation, 0.0)
    gates = params.head_bias[None, None, :] + np.einsum("btd,dh->bth", hidden, params.head_gate)
    scores = np.einsum("bth,bhts->bts", gates, activation)
    log_probs, probs = _causal_log_softmax(scores)
    return IndexerForward(
        scores=scores,
        log_probs=log_probs,
        probs=probs,
        queries=queries,
        keys=keys,
        pre_activation=pre_activation,
        activation=activation,
        gates=gates,
    )


def top_k_selection(scores: FloatArray, k: int) -> BoolArray:
    """Causal top-k per query row with a deterministic lower-index tie-break.

    Rows with fewer than ``k`` visible keys select every visible key. The
    result never contains a key after its query (checked by the recall
    functions, which reject non-causal selections).
    """

    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim < 2 or scores.shape[-1] != scores.shape[-2]:
        raise IndexerContractError("scores must end in a square (query, key) matrix")
    length = scores.shape[-1]
    k = _positive_int(k, name="k")
    if k > length:
        raise IndexerContractError("k must not exceed the sequence length")
    mask = causal_mask(length)
    if not np.isfinite(scores[..., mask]).all():
        raise IndexerContractError("scores must be finite on every visible key")
    masked = np.where(mask, scores, -np.inf)
    order = np.argsort(-masked, axis=-1, kind="stable")
    selection = np.zeros(scores.shape, dtype=bool)
    np.put_along_axis(selection, order[..., :k], True, axis=-1)
    return selection & mask


# --------------------------------------------------------------------------- #
# Teacher attention, target aggregations, KL, fixed references
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class TeacherParameters:
    """Many-head softmax teacher; per-head query and key projections."""

    query_projection: FloatArray
    key_projection: FloatArray
    temperature: float = 1.0

    def __post_init__(self) -> None:
        wq = _finite_array(self.query_projection, name="teacher query_projection", ndim=3)
        wk = _finite_array(self.key_projection, name="teacher key_projection", ndim=3)
        if wq.shape != wk.shape:
            raise IndexerContractError("teacher projections must share (heads, d_model, d_head)")
        if not math.isfinite(self.temperature) or self.temperature <= 0.0:
            raise IndexerContractError("teacher temperature must be positive")
        object.__setattr__(self, "query_projection", _readonly(wq))
        object.__setattr__(self, "key_projection", _readonly(wk))

    @property
    def heads(self) -> int:
        return int(self.query_projection.shape[0])


def teacher_attention(hidden: FloatArray, teacher: TeacherParameters) -> FloatArray:
    """Causal per-head attention probabilities, shape (batch, heads, T, T)."""

    hidden = _finite_array(hidden, name="hidden", ndim=3)
    if hidden.shape[-1] != teacher.query_projection.shape[1]:
        raise IndexerContractError("hidden width must equal the teacher d_model")
    queries = np.einsum("btd,hdk->bhtk", hidden, teacher.query_projection)
    keys = np.einsum("btd,hdk->bhtk", hidden, teacher.key_projection)
    scores = np.einsum("bhtk,bhsk->bhts", queries, keys) / teacher.temperature
    _, probs = _causal_log_softmax(scores)
    return probs


def _validate_probabilities(probs: object, *, name: str, ndim: int) -> FloatArray:
    array = _finite_array(probs, name=name, ndim=ndim)
    if array.shape[-1] != array.shape[-2]:
        raise IndexerContractError(f"{name} must end in a square (query, key) matrix")
    if np.any(array < 0.0):
        raise IndexerContractError(f"{name} must be non-negative")
    mask = causal_mask(array.shape[-1])
    if np.any(array[..., ~mask] != 0.0):
        raise IndexerContractError(f"{name} must be causal (zero mass on future keys)")
    row_mass = array.sum(axis=-1)
    if not np.allclose(row_mass, 1.0, atol=1e-6):
        raise IndexerContractError(f"{name} rows must sum to one")
    return array


def retrieval_head_scores(probs: FloatArray, copy_targets: IntArray) -> FloatArray:
    """Copy score per head: mean mass on the literal copy target of each query token.

    ``copy_targets`` is (batch, T) with -1 for query tokens that have no copy
    target. Heads are ranked by this score to form the ``rh`` aggregation.
    """

    probs = _validate_probabilities(probs, name="probs", ndim=4)
    targets = np.asarray(copy_targets)
    if targets.shape != probs.shape[:1] + probs.shape[2:3]:
        raise IndexerContractError("copy_targets must be (batch, T)")
    if not np.issubdtype(targets.dtype, np.integer):
        raise IndexerContractError("copy_targets must be integers")
    batch_idx, query_idx = np.nonzero(targets >= 0)
    if not batch_idx.size:
        raise IndexerContractError("at least one query token needs a copy target")
    key_idx = targets[batch_idx, query_idx]
    if np.any(key_idx > query_idx):
        raise IndexerContractError("copy targets must precede their query tokens")
    mass = probs[batch_idx, :, query_idx, key_idx]
    return mass.mean(axis=0)


def aggregate_target(
    probs: FloatArray,
    aggregation: Aggregation,
    head_weights: FloatArray | None = None,
) -> FloatArray:
    """Row-normalised distillation target P^T_t for one aggregation T."""

    probs = _validate_probabilities(probs, name="probs", ndim=4)
    if aggregation == "hs":
        aggregated = probs.sum(axis=1)
    elif aggregation == "mp":
        aggregated = probs.max(axis=1)
    elif aggregation == "rh":
        if head_weights is None:
            raise IndexerContractError("rh aggregation needs retrieval-head weights")
        weights = _finite_array(head_weights, name="head_weights", ndim=1)
        if weights.shape != (probs.shape[1],) or np.any(weights < 0.0) or weights.sum() <= 0.0:
            raise IndexerContractError("head_weights must be non-negative with positive mass")
        aggregated = np.einsum("h,bhts->bts", weights / weights.sum(), probs)
    else:
        raise IndexerContractError(
            f"unknown aggregation {aggregation!r}; use one of {AGGREGATIONS}"
        )
    return aggregated / aggregated.sum(axis=-1, keepdims=True)


def kl_to_target(target: FloatArray, log_probs: FloatArray) -> float:
    """Mean over query rows of KL(P^T_t || softmax_s I_t(s))."""

    target = _validate_probabilities(target, name="target", ndim=3)
    log_probs = np.asarray(log_probs, dtype=np.float64)
    if log_probs.shape != target.shape:
        raise IndexerContractError("log_probs must match the target shape")
    mask = causal_mask(target.shape[-1])
    if not np.isfinite(log_probs[..., mask]).all():
        raise IndexerContractError("log_probs must be finite on visible keys")
    positive = target > 0.0
    terms = np.zeros_like(target)
    terms[positive] = target[positive] * (np.log(target[positive]) - log_probs[positive])
    return float(terms.sum(axis=-1).mean())


def union_top_k_reference(probs: FloatArray, k: int) -> BoolArray:
    """R^U: union over heads of each head's own causal top-k (same k per head)."""

    probs = _validate_probabilities(probs, name="probs", ndim=4)
    return np.any(top_k_selection(probs, k), axis=1)


def budget_matched_reference(probs: FloatArray, k: int) -> BoolArray:
    """U_k: each head keeps floor(k / H) keys so the union holds at most k keys."""

    probs = _validate_probabilities(probs, name="probs", ndim=4)
    heads = probs.shape[1]
    k = _positive_int(k, name="k")
    if k < heads:
        raise IndexerContractError("budget-matched reference needs k of at least one key per head")
    return np.any(top_k_selection(probs, k // heads), axis=1)


def brute_force_union_top_k(probs: FloatArray, k: int) -> BoolArray:
    """Loop reference for ``union_top_k_reference`` on one prompt (heads, T, T)."""

    probs = _validate_probabilities(probs, name="probs", ndim=3)
    heads, length, _ = probs.shape
    k = _positive_int(k, name="k")
    if k > length:
        raise IndexerContractError("k must not exceed the sequence length")
    selection = np.zeros((length, length), dtype=bool)
    for head in range(heads):
        for query in range(length):
            visible = list(range(query + 1))
            visible.sort(key=lambda key: (-probs[head, query, key], key))
            for key in visible[:k]:
                selection[query, key] = True
    return selection


# --------------------------------------------------------------------------- #
# Selection recall and derived statistics (recall points)
# --------------------------------------------------------------------------- #


def selection_recall(
    selection: BoolArray, query_tokens: IntArray, needle_tokens: IntArray
) -> float:
    """Mean over query tokens of |S_t intersect N| / |N| (fraction in [0, 1])."""

    selection = np.asarray(selection)
    if (
        selection.dtype != np.bool_
        or selection.ndim != 2
        or selection.shape[0] != selection.shape[1]
    ):
        raise IndexerContractError("selection must be a square boolean (query, key) matrix")
    length = selection.shape[0]
    if np.any(selection & ~causal_mask(length)):
        raise IndexerContractError("selection is not causal: a key after its query is selected")
    queries = _index_vector(query_tokens, length=length, name="query_tokens")
    needle = _index_vector(needle_tokens, length=length, name="needle_tokens")
    if needle.max() >= queries.min():
        raise IndexerContractError("every needle token must precede every query token")
    hits = selection[np.ix_(queries, needle)].sum(axis=1)
    return float(hits.mean() / len(needle))


@dataclass(frozen=True, slots=True)
class ConditionRecall:
    """Recall in points of one selector under the four query conditions."""

    ml: float
    mn: float
    cx: float
    cs: float | None = None

    def __post_init__(self) -> None:
        for name in ("ml", "mn", "cx"):
            object.__setattr__(self, name, _points(getattr(self, name), name=name))
        if self.cs is not None:
            object.__setattr__(self, "cs", _points(self.cs, name="cs"))

    @property
    def delta(self) -> float:
        """Cross-lingual gap Delta_A = R_A(MN) - R_A(CX)."""

        return self.mn - self.cx

    @property
    def literalness_gap(self) -> float:
        """Lambda = R(ML) - R(MN), reported separately and never inside xi."""

        return self.ml - self.mn


def own_target_excess(indexer: ConditionRecall, target: ConditionRecall) -> float:
    """xi_T = Delta_ind^T - Delta_T (the indexer's excess gap over its own target)."""

    return indexer.delta - target.delta


def reference_excess(indexer: ConditionRecall, reference: ConditionRecall) -> float:
    """xi^U_T = Delta_ind^T - Delta_U (excess over the fixed reference)."""

    return indexer.delta - reference.delta


def absolute_shortfall(reference_cx: float, indexer_cx: float) -> float:
    """S_T = R^U(CX) - R_ind^T(CX) in points."""

    return _points(reference_cx, name="reference_cx") - _points(indexer_cx, name="indexer_cx")


def primary_gain(treatment_cx: float, counterfactual_cx: float) -> float:
    """D = R_c(CX) - R_b(CX), the absolute paired gain in points."""

    return _points(treatment_cx, name="treatment_cx") - _points(
        counterfactual_cx, name="counterfactual_cx"
    )


@dataclass(frozen=True, slots=True)
class TargetSelection:
    """Outcome of the T* rule: argmax CX recall inside the MN band."""

    selected: str
    eligible: tuple[str, ...]
    mn_ceiling: float
    band: float


def select_target_aggregation(
    candidates: Mapping[str, ConditionRecall],
    band: float = MN_BAND_POINTS,
    preference: Sequence[str] = AGGREGATIONS,
) -> TargetSelection:
    """T* = argmax_T R_ind^T(CX) subject to R_ind^T(MN) >= max_T' R_ind^T'(MN) - band.

    Ties are broken by ``preference`` order (registered aggregations hs, mp, rh
    by default, then lexical), so the rule is deterministic. The lambda_x
    development-language pre-step uses the same rule with lambda values as
    candidates.
    """

    if not candidates:
        raise IndexerContractError("selection needs at least one candidate")
    if not math.isfinite(band) or band < 0.0:
        raise IndexerContractError("MN band must be a finite non-negative number of points")
    mn_ceiling = max(recall.mn for recall in candidates.values())
    eligible = tuple(name for name, recall in candidates.items() if recall.mn >= mn_ceiling - band)
    order = {name: index for index, name in enumerate(preference)}
    selected = min(
        eligible,
        key=lambda name: (-candidates[name].cx, order.get(name, len(order)), name),
    )
    return TargetSelection(selected=selected, eligible=eligible, mn_ceiling=mn_ceiling, band=band)


# --------------------------------------------------------------------------- #
# Alignment loss L_x, bilingual concatenation, label controls
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class AlignmentLossResult:
    """L_x with its per-query label-mass accounting."""

    loss: float
    label_mass: FloatArray = field(repr=False)
    query_count: int

    def __post_init__(self) -> None:
        mass = _finite_array(self.label_mass, name="label_mass", ndim=1)
        if np.any(mass <= 0.0) or np.any(mass > 1.0 + 1e-9):
            raise IndexerContractError("label mass per query must lie in (0, 1]")
        if not math.isfinite(self.loss) or self.loss < -1e-9:
            raise IndexerContractError("L_x must be finite and non-negative")
        object.__setattr__(self, "label_mass", _readonly(mass))


def alignment_log_mass_loss(
    log_probs: FloatArray,
    label_mask: BoolArray,
    query_rows: BoolArray,
) -> AlignmentLossResult:
    """L_x = -(1/|Q|) sum_{t in Q} log sum_{s in N(A(t))} softmax_s I_t(s).

    Rejects labels on keys at or after their query token (a causality leak) and
    query rows without labels (undefined mass).
    """

    log_probs = np.asarray(log_probs, dtype=np.float64)
    labels = np.asarray(label_mask)
    rows = np.asarray(query_rows)
    if log_probs.ndim != 3 or log_probs.shape[-1] != log_probs.shape[-2]:
        raise IndexerContractError("log_probs must be (batch, T, T)")
    if labels.dtype != np.bool_ or labels.shape != log_probs.shape:
        raise IndexerContractError("label_mask must be a boolean (batch, T, T) array")
    if rows.dtype != np.bool_ or rows.shape != log_probs.shape[:2]:
        raise IndexerContractError("query_rows must be a boolean (batch, T) array")
    length = log_probs.shape[-1]
    if np.any(labels & ~causal_mask(length)[None, :, :]):
        raise IndexerContractError("aligned keys must precede the query token (causality leak)")
    if np.any(labels[~rows]):
        raise IndexerContractError("labels appear on rows that are not query rows")
    if not rows.any():
        raise IndexerContractError("L_x needs at least one query row")
    if np.any(labels[rows].sum(axis=-1) == 0):
        raise IndexerContractError("every query row needs at least one aligned key")
    probs = np.where(labels, np.exp(np.where(labels, log_probs, -np.inf)), 0.0)
    mass = probs.sum(axis=-1)[rows]
    mass = np.minimum(mass, 1.0)
    return AlignmentLossResult(
        loss=float(-np.log(mass).mean()),
        label_mass=mass,
        query_count=int(rows.sum()),
    )


@dataclass(frozen=True, slots=True)
class BilingualConcatenation:
    """C = [D_key ; SEP ; D_query] with corpus-given sentence alignment labels."""

    tokens: IntArray
    half: IntArray
    sentence_id: IntArray
    query_rows: BoolArray
    label_mask: BoolArray = field(repr=False)
    alignment: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        tokens = np.asarray(self.tokens)
        length = len(tokens)
        if self.label_mask.shape != (length, length):
            raise IndexerContractError("label_mask must be (T, T)")
        if np.any(self.label_mask & ~causal_mask(length)):
            raise IndexerContractError("concatenation labels must be causal")
        object.__setattr__(self, "tokens", _readonly(tokens.astype(np.int64)))
        object.__setattr__(self, "half", _readonly(np.asarray(self.half, dtype=np.int64)))
        object.__setattr__(
            self, "sentence_id", _readonly(np.asarray(self.sentence_id, dtype=np.int64))
        )
        object.__setattr__(self, "query_rows", _readonly(np.asarray(self.query_rows, dtype=bool)))
        object.__setattr__(self, "label_mask", _readonly(np.asarray(self.label_mask, dtype=bool)))

    @property
    def length(self) -> int:
        return int(len(self.tokens))


def _sentence_layout(
    sentences: Sequence[Sequence[int]], *, name: str
) -> tuple[list[int], list[int]]:
    tokens: list[int] = []
    ids: list[int] = []
    if not sentences:
        raise IndexerContractError(f"{name} must contain at least one sentence")
    for index, sentence in enumerate(sentences):
        if not sentence:
            raise IndexerContractError(f"{name} sentence {index} is empty")
        for token in sentence:
            if isinstance(token, bool) or not isinstance(token, (int, np.integer)) or token < 0:
                raise IndexerContractError(f"{name} tokens must be non-negative integers")
            tokens.append(int(token))
            ids.append(index)
    return tokens, ids


def label_mask_from_alignment(
    half: IntArray,
    sentence_id: IntArray,
    alignment: Sequence[tuple[int, int]],
) -> BoolArray:
    """Labels for query tokens (half 2) pointing at aligned key sentences (half 0).

    Raises when any aligned key would sit after its query token, which is the
    causality leak the concatenation order exists to prevent.
    """

    half = np.asarray(half, dtype=np.int64)
    sentence_id = np.asarray(sentence_id, dtype=np.int64)
    if half.shape != sentence_id.shape or half.ndim != 1:
        raise IndexerContractError("half and sentence_id must be matching vectors")
    if not alignment:
        raise IndexerContractError("alignment must contain at least one sentence pair")
    length = len(half)
    mask = np.zeros((length, length), dtype=bool)
    for pair in alignment:
        if len(pair) != 2:
            raise IndexerContractError("alignment pairs must be (query_sentence, key_sentence)")
        query_sentence, key_sentence = int(pair[0]), int(pair[1])
        query_positions = np.nonzero((half == 2) & (sentence_id == query_sentence))[0]
        key_positions = np.nonzero((half == 0) & (sentence_id == key_sentence))[0]
        if not query_positions.size or not key_positions.size:
            raise IndexerContractError("alignment references a sentence that is not present")
        if key_positions.max() >= query_positions.min():
            raise IndexerContractError("aligned keys must precede the query token (causality leak)")
        mask[np.ix_(query_positions, key_positions)] = True
    return mask


def build_bilingual_concatenation(
    key_sentences: Sequence[Sequence[int]],
    query_sentences: Sequence[Sequence[int]],
    alignment: Sequence[tuple[int, int]],
    separator_token: int,
) -> BilingualConcatenation:
    """Build C = [D_key ; SEP ; D_query]; queries are the second half by construction."""

    key_tokens, key_ids = _sentence_layout(key_sentences, name="key_sentences")
    query_tokens, query_ids = _sentence_layout(query_sentences, name="query_sentences")
    if isinstance(separator_token, bool) or not isinstance(separator_token, (int, np.integer)):
        raise IndexerContractError("separator_token must be an integer")
    tokens = np.array(key_tokens + [int(separator_token)] + query_tokens, dtype=np.int64)
    half = np.array([0] * len(key_tokens) + [1] + [2] * len(query_tokens), dtype=np.int64)
    sentence_id = np.array(key_ids + [-1] + query_ids, dtype=np.int64)
    pairs = tuple((int(q), int(k)) for q, k in alignment)
    seen_queries = {q for q, _ in pairs}
    if len(seen_queries) != len(pairs):
        raise IndexerContractError("each query sentence may carry one alignment label set")
    mask = label_mask_from_alignment(half, sentence_id, pairs)
    query_rows = mask.any(axis=1)
    return BilingualConcatenation(
        tokens=tokens,
        half=half,
        sentence_id=sentence_id,
        query_rows=query_rows,
        label_mask=mask,
        alignment=pairs,
    )


def permuted_label_mask(concat: BilingualConcatenation, seed: int) -> BoolArray:
    """L_perm: the aligned key sentences are deranged among the aligned queries."""

    pairs = list(concat.alignment)
    if len(pairs) < 2:
        raise IndexerContractError("permuting labels needs at least two aligned sentences")
    rng = np.random.default_rng(seed)
    keys = [k for _, k in pairs]
    for _attempt in range(1000):
        shuffled = list(rng.permutation(keys))
        if all(int(a) != int(b) for a, b in zip(shuffled, keys, strict=True)):
            break
    else:  # pragma: no cover - a derangement always exists for n >= 2
        raise IndexerContractError("could not derange the alignment labels")
    permuted = [(q, int(k)) for (q, _), k in zip(pairs, shuffled, strict=True)]
    return label_mask_from_alignment(concat.half, concat.sentence_id, permuted)


def other_half_label_mask(concat: BilingualConcatenation) -> BoolArray:
    """L_half: every aligned query token is labelled with the whole key half."""

    key_positions = np.nonzero(concat.half == 0)[0]
    mask = np.zeros_like(concat.label_mask)
    mask[np.ix_(np.nonzero(concat.query_rows)[0], key_positions)] = True
    return mask


# --------------------------------------------------------------------------- #
# Synthetic bilingual world
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SyntheticWorldConfig:
    """Two scripts related by a fixed orthogonal map; three languages; two forms."""

    topics: int = 8
    concepts_per_topic: int = 12
    forms: int = 2
    scripts: tuple[int, ...] = (0, 1, 1)
    topic_weight: float = 0.75
    d_sem: int = 32
    d_lang: int = 8
    d_form: int = 16
    same_language_heads: int = 6
    hub_heads: int = 1
    literal_heads: int = 1
    beta_sem: float = 6.0
    beta_lang: float = 4.0
    beta_hub: float = 8.0
    beta_form: float = 8.0

    def __post_init__(self) -> None:
        for name in ("topics", "concepts_per_topic", "forms", "d_sem", "d_lang", "d_form"):
            _positive_int(getattr(self, name), name=name)
        if self.topics < 3 or self.concepts_per_topic < 4:
            raise IndexerContractError("the synthetic world needs at least 3 topics of 4 concepts")
        if not math.isfinite(self.topic_weight) or not 0.0 < self.topic_weight < 1.0:
            raise IndexerContractError("topic_weight must lie in (0, 1)")
        if len(self.scripts) < 2 or set(self.scripts) != {0, 1}:
            raise IndexerContractError(
                "scripts must list at least two languages using scripts 0 and 1"
            )
        for name in ("same_language_heads", "hub_heads", "literal_heads"):
            _positive_int(getattr(self, name), name=name)
        for name in ("beta_sem", "beta_lang", "beta_hub", "beta_form"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise IndexerContractError(f"{name} must be positive")

    @property
    def languages(self) -> int:
        return len(self.scripts)

    @property
    def concepts(self) -> int:
        return self.topics * self.concepts_per_topic

    @property
    def d_model(self) -> int:
        return self.d_sem + self.d_lang + self.d_form

    def topic_of(self, concept: int) -> int:
        if not 0 <= concept < self.concepts:
            raise IndexerContractError("concept out of range")
        return concept // self.concepts_per_topic

    @property
    def teacher_heads(self) -> int:
        return self.same_language_heads + self.hub_heads + self.literal_heads


@dataclass(frozen=True, slots=True)
class SyntheticBilingualWorld:
    """Vocabulary, embeddings, cross-script map and teacher for the toy."""

    config: SyntheticWorldConfig
    embeddings: FloatArray = field(repr=False)
    concept_slots: IntArray = field(repr=False)
    rotation: FloatArray = field(repr=False)
    teacher: TeacherParameters = field(repr=False)
    seed: int

    @property
    def separator_token(self) -> int:
        return int(self.embeddings.shape[0] - 1)

    @property
    def vocabulary(self) -> int:
        return int(self.embeddings.shape[0])

    def symbol(self, language: int, concept: int, form: int) -> int:
        cfg = self.config
        if not 0 <= language < cfg.languages:
            raise IndexerContractError("language out of range")
        if not 0 <= concept < cfg.concepts:
            raise IndexerContractError("concept out of range")
        if not 0 <= form < cfg.forms:
            raise IndexerContractError("form out of range")
        slot = int(self.concept_slots[language, concept])
        return (language * cfg.concepts + slot) * cfg.forms + form

    def embed(self, tokens: IntArray) -> FloatArray:
        tokens = np.asarray(tokens, dtype=np.int64)
        if np.any(tokens < 0) or np.any(tokens >= self.vocabulary):
            raise IndexerContractError("token id outside the synthetic vocabulary")
        return self.embeddings[tokens]

    def identity(self) -> str:
        return hashlib.sha256(self.embeddings.tobytes()).hexdigest()[:16]


def _unit_rows(rng: np.random.Generator, shape: tuple[int, ...]) -> FloatArray:
    vectors = rng.normal(size=shape)
    return vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)


def build_synthetic_world(
    config: SyntheticWorldConfig,
    seed: int,
    rotation: FloatArray | None = None,
) -> SyntheticBilingualWorld:
    """Build the toy: shared semantics, a script rotation, language and form vectors.

    Concepts group into topics: a needle passage is a run of same-topic tokens
    and a non-literal query is a different run from the same topic, so retrieval
    is semantic, not literal. Script-1 languages carry their semantic vector
    rotated by one fixed orthogonal map, so same-script matching is an identity
    bilinear form and cross-script matching needs the map; the teacher's hub
    heads know it, its same-language heads do not. ``rotation`` may be supplied to build a
    "shifted-script" world (the negative control).
    """

    rng = np.random.default_rng(seed)
    topic_vectors = _unit_rows(rng, (config.topics, config.d_sem))
    concept_vectors = _unit_rows(rng, (config.concepts, config.d_sem))
    topic_index = np.arange(config.concepts) // config.concepts_per_topic
    sem = (
        math.sqrt(config.topic_weight) * topic_vectors[topic_index]
        + math.sqrt(1.0 - config.topic_weight) * concept_vectors
    )
    sem = sem / np.linalg.norm(sem, axis=-1, keepdims=True)
    lang = _unit_rows(rng, (config.languages, config.d_lang))
    form = _unit_rows(rng, (config.languages, config.concepts, config.forms, config.d_form))
    gaussian = rng.normal(size=(config.d_sem, config.d_sem))  # always drawn: keeps the rng aligned
    if rotation is None:
        # A random reflection through a random half-dimensional subspace: symmetric,
        # orthogonal and an involution (R^2 = I), so one bilinear form serves both
        # query directions and has near-zero trace (no accidental same-script match).
        basis, _ = np.linalg.qr(gaussian)
        signs = np.where(np.arange(config.d_sem) < config.d_sem // 2, 1.0, -1.0)
        rotation_matrix = (basis * signs) @ basis.T
    else:
        rotation_matrix = _finite_array(rotation, name="rotation", ndim=2)
        if (
            rotation_matrix.shape != (config.d_sem, config.d_sem)
            or not np.allclose(rotation_matrix @ rotation_matrix.T, np.eye(config.d_sem), atol=1e-8)
            or not np.allclose(rotation_matrix, rotation_matrix.T, atol=1e-8)
        ):
            raise IndexerContractError(
                "rotation must be a symmetric orthogonal d_sem x d_sem matrix"
            )
    slots = np.stack(
        [
            np.arange(config.concepts) if language == 0 else rng.permutation(config.concepts)
            for language in range(config.languages)
        ]
    ).astype(np.int64)

    vocabulary = config.languages * config.concepts * config.forms + 1
    embeddings = np.zeros((vocabulary, config.d_model))
    for language in range(config.languages):
        semantic = sem @ rotation_matrix if config.scripts[language] == 1 else sem
        for concept in range(config.concepts):
            for f in range(config.forms):
                index = (
                    language * config.concepts + int(slots[language, concept])
                ) * config.forms + f
                embeddings[index] = np.concatenate(
                    [semantic[concept], lang[language], form[language, concept, f]]
                )
    embeddings[-1] = _unit_rows(rng, (config.d_model,)) * 0.1  # separator

    d = config.d_model
    sem_slice = slice(0, config.d_sem)
    lang_slice = slice(config.d_sem, config.d_sem + config.d_lang)
    form_slice = slice(config.d_sem + config.d_lang, d)
    heads = config.teacher_heads
    wq = np.zeros((heads, d, d))
    wk = np.zeros((heads, d, d))
    head = 0
    for _ in range(config.same_language_heads):
        wq[head, sem_slice, sem_slice] = math.sqrt(config.beta_sem) * np.eye(config.d_sem)
        wk[head, sem_slice, sem_slice] = math.sqrt(config.beta_sem) * np.eye(config.d_sem)
        wq[head, lang_slice, lang_slice] = math.sqrt(config.beta_lang) * np.eye(config.d_lang)
        wk[head, lang_slice, lang_slice] = math.sqrt(config.beta_lang) * np.eye(config.d_lang)
        head += 1
    for _ in range(config.hub_heads):
        # score = sem_t . (sem_s R) = sem_t R sem_s^T; with R symmetric and R^2 = I this
        # is |sem|^2 for a cross-script pair in either direction and near zero otherwise
        wq[head, sem_slice, sem_slice] = math.sqrt(config.beta_hub) * np.eye(config.d_sem)
        wk[head, sem_slice, sem_slice] = math.sqrt(config.beta_hub) * rotation_matrix
        head += 1
    for _ in range(config.literal_heads):
        wq[head, form_slice, form_slice] = math.sqrt(config.beta_form) * np.eye(config.d_form)
        wk[head, form_slice, form_slice] = math.sqrt(config.beta_form) * np.eye(config.d_form)
        head += 1
    teacher = TeacherParameters(query_projection=wq, key_projection=wk, temperature=1.0)
    return SyntheticBilingualWorld(
        config=config,
        embeddings=_readonly(embeddings),
        concept_slots=_readonly(slots),
        rotation=_readonly(rotation_matrix),
        teacher=teacher,
        seed=int(seed),
    )


# --------------------------------------------------------------------------- #
# Evaluation prompts: four conditions sharing (haystack, needle, position)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PromptLedgerEntry:
    """Per-prompt achieved-token ledger (symbol counts; the toy has one tokenizer)."""

    haystack_tokens: int
    needle_tokens: int
    query_tokens: int
    achieved_k: int
    budget_fraction: float
    needle_position: int
    needle_language: int
    query_language: int
    condition: str


@dataclass(frozen=True, slots=True)
class EvaluationPrompt:
    tokens: IntArray
    needle_positions: IntArray
    query_positions: IntArray
    ledger: PromptLedgerEntry


@dataclass(frozen=True, slots=True)
class PromptFamily:
    """One (H, N, p) shared by the query conditions that differ only in Q."""

    needle_language: int
    prompts: Mapping[str, EvaluationPrompt]


def achieved_budget(haystack_tokens: int, fraction: float) -> int:
    """k = round(rho * |H|) in the model tokenizer (symbols here); at least one."""

    haystack_tokens = _positive_int(haystack_tokens, name="haystack_tokens")
    if not math.isfinite(fraction) or not 0.0 < fraction <= 1.0:
        raise IndexerContractError("budget fraction must lie in (0, 1]")
    return max(1, int(round(fraction * haystack_tokens)))


def make_prompt_family(
    world: SyntheticBilingualWorld,
    rng: np.random.Generator,
    needle_language: int,
    cross_script_language: int,
    same_script_language: int | None,
    position_fraction: float,
    haystack_length: int = 115,
    needle_length: int = 5,
    budget_fraction: float = 0.125,
) -> PromptFamily:
    """Build ML / MN / CX (and CS when a same-script partner exists) prompts.

    ML copies the needle verbatim; MN, CS and CX use a disjoint same-topic run
    of concepts (non-literal) and differ only in query language, so the four
    conditions share (haystack, needle, position) and the literalness gap is
    confined to the ML row.
    """

    cfg = world.config
    if cfg.scripts[needle_language] == cfg.scripts[cross_script_language]:
        raise IndexerContractError("cross-script language must use the other script")
    if same_script_language is not None and (
        cfg.scripts[same_script_language] != cfg.scripts[needle_language]
        or same_script_language == needle_language
    ):
        raise IndexerContractError("same-script language must share the needle script and differ")
    if not 0.0 <= position_fraction <= 1.0:
        raise IndexerContractError("position fraction must lie in [0, 1]")
    needle_length = _positive_int(needle_length, name="needle_length")
    haystack_length = _positive_int(
        haystack_length, name="haystack_length", minimum=needle_length + 1
    )
    if 2 * needle_length > cfg.concepts_per_topic:
        raise IndexerContractError("a topic must hold a needle run and a disjoint query run")
    topic = int(rng.integers(0, cfg.topics))
    topic_concepts = rng.permutation(
        np.arange(topic * cfg.concepts_per_topic, (topic + 1) * cfg.concepts_per_topic)
    )
    needle_concepts = topic_concepts[:needle_length]
    query_concepts = topic_concepts[needle_length : 2 * needle_length]
    background = np.array([c for c in range(cfg.concepts) if cfg.topic_of(c) != topic])
    needle_forms = rng.integers(0, cfg.forms, size=needle_length)
    haystack_concepts = rng.choice(background, size=haystack_length, replace=True)
    haystack_forms = rng.integers(0, cfg.forms, size=haystack_length)
    haystack = [
        world.symbol(needle_language, int(c), int(f))
        for c, f in zip(haystack_concepts, haystack_forms, strict=True)
    ]
    needle = [
        world.symbol(needle_language, int(c), int(f))
        for c, f in zip(needle_concepts, needle_forms, strict=True)
    ]
    insert_at = int(round(position_fraction * haystack_length))
    context = haystack[:insert_at] + needle + haystack[insert_at:]
    needle_positions = np.arange(insert_at, insert_at + needle_length, dtype=np.int64)
    context_length = len(context)
    k = achieved_budget(context_length, budget_fraction)

    def query_tokens(language: int, concepts: IntArray, forms: IntArray) -> list[int]:
        return [
            world.symbol(language, int(c), int(f)) for c, f in zip(concepts, forms, strict=True)
        ]

    query_forms = rng.integers(0, cfg.forms, size=needle_length)
    variants: dict[str, tuple[int, list[int]]] = {
        "ML": (needle_language, query_tokens(needle_language, needle_concepts, needle_forms)),
        "MN": (needle_language, query_tokens(needle_language, query_concepts, query_forms)),
        "CX": (
            cross_script_language,
            query_tokens(cross_script_language, query_concepts, query_forms),
        ),
    }
    if same_script_language is not None:
        variants["CS"] = (
            same_script_language,
            query_tokens(same_script_language, query_concepts, query_forms),
        )
    prompts: dict[str, EvaluationPrompt] = {}
    for condition, (language, query) in variants.items():
        tokens = np.array(context + [world.separator_token] + query, dtype=np.int64)
        query_positions = np.arange(context_length + 1, len(tokens), dtype=np.int64)
        prompts[condition] = EvaluationPrompt(
            tokens=_readonly(tokens),
            needle_positions=_readonly(needle_positions.copy()),
            query_positions=_readonly(query_positions),
            ledger=PromptLedgerEntry(
                haystack_tokens=context_length,
                needle_tokens=needle_length,
                query_tokens=len(query),
                achieved_k=k,
                budget_fraction=budget_fraction,
                needle_position=insert_at,
                needle_language=needle_language,
                query_language=language,
                condition=condition,
            ),
        )
    return PromptFamily(needle_language=needle_language, prompts=prompts)


def literal_copy_targets(prompt: EvaluationPrompt) -> IntArray:
    """Copy target per query token for an ML prompt (the needle token it copies)."""

    targets = np.full(len(prompt.tokens), -1, dtype=np.int64)
    if len(prompt.query_positions) != len(prompt.needle_positions):
        raise IndexerContractError("copy targets need one needle token per query token")
    targets[prompt.query_positions] = prompt.needle_positions
    return targets


# --------------------------------------------------------------------------- #
# Training data (bilingual concatenations) and the analytic-gradient trainer
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Registered toy training recipe for one indexer arm."""

    aggregation: Aggregation = "hs"
    label_mode: LabelMode = "none"
    lambda_x: float = 0.5
    steps: int = 120
    batch_size: int = 4
    learning_rate: float = 0.02
    sentences: int = 5
    sentence_length: int = 4
    rank: int = 16
    heads: int = 4
    training_languages: tuple[int, int] = (0, 1)
    bilingual_fraction: float = 0.5

    def __post_init__(self) -> None:
        if not math.isfinite(self.bilingual_fraction) or not 0.0 < self.bilingual_fraction <= 1.0:
            raise IndexerContractError("bilingual_fraction must lie in (0, 1]")
        if self.aggregation not in AGGREGATIONS:
            raise IndexerContractError(f"aggregation must be one of {AGGREGATIONS}")
        if self.label_mode not in ("none", "true", "permuted", "half"):
            raise IndexerContractError("label_mode must be none, true, permuted or half")
        if not math.isfinite(self.lambda_x) or self.lambda_x < 0.0:
            raise IndexerContractError("lambda_x must be finite and non-negative")
        if self.label_mode != "none" and self.lambda_x == 0.0:
            raise IndexerContractError("a labelled arm needs lambda_x above zero")
        for name in ("steps", "batch_size", "sentences", "sentence_length", "rank", "heads"):
            _positive_int(getattr(self, name), name=name)
        if self.sentences < 2:
            raise IndexerContractError("at least two sentences are needed for permuted labels")
        if not math.isfinite(self.learning_rate) or self.learning_rate <= 0.0:
            raise IndexerContractError("learning_rate must be positive")
        if (
            len(self.training_languages) != 2
            or self.training_languages[0] == self.training_languages[1]
        ):
            raise IndexerContractError("training_languages must name two distinct languages")


@dataclass(frozen=True, slots=True)
class TrainingBatch:
    hidden: FloatArray
    target: FloatArray
    label_mask: BoolArray
    query_rows: BoolArray


def make_training_batch(
    world: SyntheticBilingualWorld,
    rng: np.random.Generator,
    config: TrainingConfig,
    head_weights: FloatArray | None,
    label_seed: int,
) -> TrainingBatch:
    """Bilingual concatenations with corpus-given alignment, mixed with monolingual text.

    A fraction ``bilingual_fraction`` of the items are [D_b ; SEP ; D_a] pairs (both
    orders alternate); the rest are monolingual two-document sequences in one of
    the training languages with no labels, mirroring the Phase-0a stream (half
    bilingual concatenations, half monolingual text).
    """

    cfg = world.config
    lang_a, lang_b = config.training_languages
    sequences: list[BilingualConcatenation] = []
    masks: list[BoolArray] = []
    bilingual_flags: list[bool] = []
    for item in range(config.batch_size):
        bilingual = bool(rng.random() < config.bilingual_fraction)
        bilingual_flags.append(bilingual)
        if not bilingual:
            language = lang_a if item % 2 == 0 else lang_b
            docs = []
            for _ in range(2):
                topics = rng.integers(0, cfg.topics, size=config.sentences)
                docs.append(
                    [
                        [
                            world.symbol(language, int(c), int(f))
                            for c, f in zip(
                                rng.choice(
                                    np.arange(
                                        t * cfg.concepts_per_topic, (t + 1) * cfg.concepts_per_topic
                                    ),
                                    size=config.sentence_length,
                                    replace=False,
                                ),
                                rng.integers(0, cfg.forms, size=config.sentence_length),
                                strict=True,
                            )
                        ]
                        for t in topics
                    ]
                )
            # identity alignment only fixes the layout; monolingual items carry no labels
            concat = build_bilingual_concatenation(
                docs[0], docs[1], [(j, j) for j in range(config.sentences)], world.separator_token
            )
            sequences.append(concat)
            masks.append(np.zeros_like(concat.label_mask))
            continue
        sentence_topics = rng.integers(0, cfg.topics, size=config.sentences)
        concepts = np.stack(
            [
                rng.choice(
                    np.arange(t * cfg.concepts_per_topic, (t + 1) * cfg.concepts_per_topic),
                    size=config.sentence_length,
                    replace=False,
                )
                for t in sentence_topics
            ]
        )
        forms_a = rng.integers(0, cfg.forms, size=concepts.shape)
        forms_b = rng.integers(0, cfg.forms, size=concepts.shape)
        sentences_a = [
            [world.symbol(lang_a, int(c), int(f)) for c, f in zip(row_c, row_f, strict=True)]
            for row_c, row_f in zip(concepts, forms_a, strict=True)
        ]
        order = rng.permutation(config.sentences)
        sentences_b = [
            [
                world.symbol(lang_b, int(c), int(f))
                for c, f in zip(concepts[source], forms_b[source], strict=True)
            ]
            for source in order
        ]
        # sentence_b[j] translates sentence_a[order[j]]
        if item % 2 == 0:
            alignment = [(int(order[j]), j) for j in range(config.sentences)]
            concat = build_bilingual_concatenation(
                sentences_b, sentences_a, alignment, world.separator_token
            )
        else:
            alignment = [(j, int(order[j])) for j in range(config.sentences)]
            concat = build_bilingual_concatenation(
                sentences_a, sentences_b, alignment, world.separator_token
            )
        sequences.append(concat)
        if config.label_mode == "true":
            masks.append(concat.label_mask)
        elif config.label_mode == "permuted":
            masks.append(permuted_label_mask(concat, label_seed + item))
        elif config.label_mode == "half":
            masks.append(other_half_label_mask(concat))
        else:
            masks.append(np.zeros_like(concat.label_mask))
    hidden = np.stack([world.embed(seq.tokens) for seq in sequences])
    probs = teacher_attention(hidden, world.teacher)
    target = aggregate_target(probs, config.aggregation, head_weights)
    query_rows = np.stack(
        [
            seq.query_rows
            if (config.label_mode != "none" and flag)
            else np.zeros(seq.length, dtype=bool)
            for seq, flag in zip(sequences, bilingual_flags, strict=True)
        ]
    )
    return TrainingBatch(
        hidden=hidden,
        target=target,
        label_mask=np.stack(masks),
        query_rows=query_rows,
    )


@dataclass(frozen=True, slots=True)
class LossBreakdown:
    kl: float
    alignment: float
    total: float
    label_mass_min: float
    label_mass_mean: float


def loss_and_gradient(
    params: IndexerParameters,
    batch: TrainingBatch,
    lambda_x: float,
) -> tuple[LossBreakdown, FloatArray]:
    """Return KL + lambda_x L_x and its analytic gradient as a flat vector."""

    forward = indexer_forward(batch.hidden, params)
    target = _validate_probabilities(batch.target, name="target", ndim=3)
    kl = kl_to_target(target, forward.log_probs)
    rows = batch.hidden.shape[0] * batch.hidden.shape[1]
    grad_scores = (forward.probs - target) / rows
    alignment = 0.0
    mass_min, mass_mean = 1.0, 1.0
    if batch.query_rows.any():
        if lambda_x <= 0.0:
            raise IndexerContractError("labelled query rows need lambda_x above zero")
        result = alignment_log_mass_loss(forward.log_probs, batch.label_mask, batch.query_rows)
        alignment = result.loss
        mass_min = float(result.label_mass.min())
        mass_mean = float(result.label_mass.mean())
        labelled = np.where(batch.label_mask, forward.probs, 0.0)
        mass = labelled.sum(axis=-1, keepdims=True)
        mass = np.where(batch.query_rows[..., None], mass, 1.0)
        gx = np.where(
            batch.query_rows[..., None],
            forward.probs - labelled / mass,
            0.0,
        )
        grad_scores = grad_scores + lambda_x * gx / result.query_count
    grad_gates = np.einsum("bts,bhts->bth", grad_scores, forward.activation)
    grad_activation = np.einsum("bts,bth->bhts", grad_scores, forward.gates)
    grad_pre = grad_activation * (forward.pre_activation > 0.0)
    grad_queries = np.einsum("bhts,bsr->bhtr", grad_pre, forward.keys)
    grad_keys = np.einsum("bhts,bhtr->bsr", grad_pre, forward.queries)
    grad_wq = np.einsum("btd,bhtr->hdr", batch.hidden, grad_queries)
    grad_wk = np.einsum("bsd,bsr->dr", batch.hidden, grad_keys)
    grad_ww = np.einsum("btd,bth->dh", batch.hidden, grad_gates)
    grad_bias = grad_gates.sum(axis=(0, 1))
    gradient = np.concatenate(
        [grad_wq.ravel(), grad_wk.ravel(), grad_ww.ravel(), grad_bias.ravel()]
    )
    total = kl + lambda_x * alignment
    return LossBreakdown(
        kl=kl, alignment=alignment, total=total, label_mass_min=mass_min, label_mass_mean=mass_mean
    ), gradient


@dataclass(frozen=True, slots=True)
class TrainedIndexer:
    params: IndexerParameters
    config: TrainingConfig
    seed: int
    first_loss: LossBreakdown
    final_loss: LossBreakdown


def train_indexer(
    world: SyntheticBilingualWorld,
    config: TrainingConfig,
    seed: int,
    head_weights: FloatArray | None = None,
) -> TrainedIndexer:
    """Adam on KL(+ lambda_x L_x) with fresh seeded bilingual batches each step."""

    if config.aggregation == "rh" and head_weights is None:
        raise IndexerContractError("rh training needs retrieval-head weights")
    rng = np.random.default_rng([seed, 21])
    params = IndexerParameters.random(world.config.d_model, config.rank, config.heads, seed)
    vector = params.as_vector()
    first_moment = np.zeros_like(vector)
    second_moment = np.zeros_like(vector)
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    lambda_x = config.lambda_x if config.label_mode != "none" else 0.0
    first: LossBreakdown | None = None
    last: LossBreakdown | None = None
    for step in range(1, config.steps + 1):
        batch = make_training_batch(world, rng, config, head_weights, label_seed=seed * 1000 + step)
        loss, gradient = loss_and_gradient(params, batch, lambda_x)
        first = first or loss
        last = loss
        first_moment = beta1 * first_moment + (1.0 - beta1) * gradient
        second_moment = beta2 * second_moment + (1.0 - beta2) * gradient**2
        m_hat = first_moment / (1.0 - beta1**step)
        v_hat = second_moment / (1.0 - beta2**step)
        vector = vector - config.learning_rate * m_hat / (np.sqrt(v_hat) + eps)
        params = params.with_vector(vector)
    assert first is not None and last is not None
    return TrainedIndexer(
        params=params, config=config, seed=int(seed), first_loss=first, final_loss=last
    )


def retrieval_head_weights(
    world: SyntheticBilingualWorld,
    seed: int,
    prompts: int = 12,
) -> FloatArray:
    """Head copy scores measured on language-0 literal-copy (ML) prompts."""

    rng = np.random.default_rng([seed, 7])
    cross = next(i for i, s in enumerate(world.config.scripts) if s == 1)
    families = [
        make_prompt_family(world, rng, 0, cross, None, rng.uniform(0.1, 0.9))
        for _ in range(prompts)
    ]
    hidden = np.stack([world.embed(f.prompts["ML"].tokens) for f in families])
    targets = np.stack([literal_copy_targets(f.prompts["ML"]) for f in families])
    return retrieval_head_scores(teacher_attention(hidden, world.teacher), targets)


# --------------------------------------------------------------------------- #
# Evaluation of selectors on prompt families
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SelectorRecalls:
    """Recall points per selector: indexer, its own target, R^U and U_k."""

    indexer: ConditionRecall
    target: ConditionRecall
    union_reference: ConditionRecall
    budget_matched_reference: ConditionRecall
    prompt_count: int
    achieved_k: int


def evaluate_selectors(
    world: SyntheticBilingualWorld,
    params: IndexerParameters,
    aggregation: Aggregation,
    families: Sequence[PromptFamily],
    head_weights: FloatArray | None = None,
) -> SelectorRecalls:
    """Compute R_A(cond) for A in {ind^T, T, U, U_k} on shared (H, N, p) prompts."""

    if not families:
        raise IndexerContractError("evaluation needs at least one prompt family")
    totals: dict[str, dict[str, list[float]]] = {
        name: {cond: [] for cond in CONDITIONS} for name in ("ind", "target", "union", "budget")
    }
    k_values: set[int] = set()
    for family in families:
        for condition, prompt in family.prompts.items():
            hidden = world.embed(prompt.tokens)[None]
            k = prompt.ledger.achieved_k
            k_values.add(k)
            probs = teacher_attention(hidden, world.teacher)
            target = aggregate_target(probs, aggregation, head_weights)
            forward = indexer_forward(hidden, params)
            selections = {
                "ind": top_k_selection(forward.scores[0], k),
                "target": top_k_selection(target[0], k),
                "union": union_top_k_reference(probs, k)[0],
                "budget": budget_matched_reference(probs, k)[0],
            }
            for name, selection in selections.items():
                totals[name][condition].append(
                    100.0
                    * selection_recall(selection, prompt.query_positions, prompt.needle_positions)
                )
    if len(k_values) != 1:
        raise IndexerContractError("every prompt family must share one achieved budget k")

    def recall(name: str) -> ConditionRecall:
        values = totals[name]
        return ConditionRecall(
            ml=float(np.mean(values["ML"])),
            mn=float(np.mean(values["MN"])),
            cx=float(np.mean(values["CX"])),
            cs=float(np.mean(values["CS"])) if values["CS"] else None,
        )

    return SelectorRecalls(
        indexer=recall("ind"),
        target=recall("target"),
        union_reference=recall("union"),
        budget_matched_reference=recall("budget"),
        prompt_count=sum(len(f.prompts) for f in families),
        achieved_k=k_values.pop(),
    )


def evaluation_families(
    world: SyntheticBilingualWorld,
    seed: int,
    language: int,
    same_script_language: int | None = None,
    count: int = 8,
) -> list[PromptFamily]:
    """Cross-script families in both directions: (N = language, Q = script-0) and reverse.

    ``language`` must use script 1. Pass ``same_script_language`` to add the CS
    row; leave it None for development prompts so they never touch a held-out
    language.
    """

    cfg = world.config
    if cfg.scripts[language] != 1:
        raise IndexerContractError("the evaluated language must use script 1 in this toy")
    count = _positive_int(count, name="count")
    rng = np.random.default_rng([seed, 13, language])
    positions = (0.15, 0.5, 0.85)
    families: list[PromptFamily] = []
    for index in range(count):
        position = positions[index % len(positions)]
        families.append(make_prompt_family(world, rng, language, 0, same_script_language, position))
        families.append(make_prompt_family(world, rng, 0, language, None, position))
    return families


# --------------------------------------------------------------------------- #
# Passage-id split (development / audit / primary)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PassageSplit:
    """Three disjoint passage-id sets; every language variant of a passage follows its id."""

    development: frozenset[str]
    audit: frozenset[str]
    primary: frozenset[str]
    seed: int

    def __post_init__(self) -> None:
        sets = (self.development, self.audit, self.primary)
        if any(not s for s in sets):
            raise IndexerContractError("every split partition must be non-empty")
        if (
            self.development & self.audit
            or self.development & self.primary
            or self.audit & self.primary
        ):
            raise IndexerContractError("split partitions must be disjoint")

    def partition_of(self, passage_id: str) -> str:
        if passage_id in self.development:
            return "development"
        if passage_id in self.audit:
            return "audit"
        if passage_id in self.primary:
            return "primary"
        raise IndexerContractError(f"passage id {passage_id!r} is not in the split")


def split_passage_ids(
    passage_ids: Sequence[str],
    seed: int,
    development_fraction: float = 0.25,
    audit_fraction: float = 0.25,
) -> PassageSplit:
    """Deterministic hash-ordered split: development, Phase-0 audit, Phase-1 primary.

    Gate statistics (K1, K2a, adequacy, sigma-hat, se_D) read only the audit
    partition; the primary contrast D reads only the primary partition, exactly
    once.
    """

    ids = [str(p) for p in passage_ids]
    if len(ids) < 3:
        raise IndexerContractError("at least three passage ids are needed")
    if len(set(ids)) != len(ids):
        raise IndexerContractError("passage ids must be unique")
    for name, fraction in (
        ("development_fraction", development_fraction),
        ("audit_fraction", audit_fraction),
    ):
        if not math.isfinite(fraction) or not 0.0 < fraction < 1.0:
            raise IndexerContractError(f"{name} must lie in (0, 1)")
    if development_fraction + audit_fraction >= 1.0:
        raise IndexerContractError("development and audit fractions must leave a primary partition")
    ordered = sorted(ids, key=lambda p: hashlib.sha256(f"{p}|{seed}".encode()).hexdigest())
    n_dev = max(1, int(round(development_fraction * len(ordered))))
    n_audit = max(1, int(round(audit_fraction * len(ordered))))
    if n_dev + n_audit >= len(ordered):
        raise IndexerContractError("too few passage ids for the requested fractions")
    return PassageSplit(
        development=frozenset(ordered[:n_dev]),
        audit=frozenset(ordered[n_dev : n_dev + n_audit]),
        primary=frozenset(ordered[n_dev + n_audit :]),
        seed=int(seed),
    )


def assert_reads_within(passage_ids: Iterable[str], split: PassageSplit, partition: str) -> None:
    """Fail closed when a read touches passages outside the declared partition."""

    allowed = {
        "development": split.development,
        "audit": split.audit,
        "primary": split.primary,
    }.get(partition)
    if allowed is None:
        raise IndexerContractError("partition must be development, audit or primary")
    offending = sorted(p for p in passage_ids if p not in allowed)
    if offending:
        raise IndexerContractError(
            f"{len(offending)} passage id(s) read outside the {partition} partition "
            f"(first: {offending[0]!r}); the gate/primary separation is violated"
        )


# --------------------------------------------------------------------------- #
# Noise model and the Phase-1 decision rule (wave-5 repair)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PooledSeedSD:
    sigma_hat: float
    degrees_of_freedom: int
    configurations: int


def pooled_seed_sd(per_configuration_recalls: Mapping[str, Sequence[float]]) -> PooledSeedSD:
    """Pooled within-configuration seed SD with honest df = sum_c (n_c - 1)."""

    if not per_configuration_recalls:
        raise IndexerContractError("pooled seed SD needs at least one configuration")
    sum_squares = 0.0
    df = 0
    for name, values in per_configuration_recalls.items():
        array = _finite_array(values, name=f"recalls[{name}]", ndim=1)
        if len(array) < 2:
            raise IndexerContractError(f"configuration {name!r} needs at least two seeds")
        sum_squares += float(((array - array.mean()) ** 2).sum())
        df += len(array) - 1
    return PooledSeedSD(
        sigma_hat=math.sqrt(sum_squares / df),
        degrees_of_freedom=df,
        configurations=len(per_configuration_recalls),
    )


def sigma_upper_bound(sigma_hat: float, degrees_of_freedom: int, confidence: float = 0.80) -> float:
    """One-sided upper (1 - alpha) confidence bound on sigma from a chi-square pivot."""

    if not math.isfinite(sigma_hat) or sigma_hat < 0.0:
        raise IndexerContractError("sigma_hat must be finite and non-negative")
    df = _positive_int(degrees_of_freedom, name="degrees_of_freedom")
    if not 0.5 <= confidence < 1.0:
        raise IndexerContractError("confidence must lie in [0.5, 1)")
    quantile = stats.chi2.ppf(1.0 - confidence, df)
    return float(sigma_hat * math.sqrt(df / quantile))


def paired_cluster_bootstrap_se(
    differences: FloatArray,
    clusters: Sequence[object],
    replicates: int = 2000,
    seed: int = 42,
) -> float:
    """SE of the seed-averaged paired mean difference under passage-cluster resampling.

    ``differences`` is (seeds, prompts); seeds are paired blocks (kept fixed),
    passage clusters are resampled with replacement.
    """

    diffs = _finite_array(differences, name="differences", ndim=2)
    labels = np.asarray(clusters)
    if labels.ndim != 1 or len(labels) != diffs.shape[1]:
        raise IndexerContractError("clusters must label every prompt column")
    replicates = _positive_int(replicates, name="replicates", minimum=100)
    unique, inverse = np.unique(labels, return_inverse=True)
    if len(unique) < 2:
        raise IndexerContractError("at least two clusters are needed to bootstrap")
    rng = np.random.default_rng(seed)
    cluster_sums = np.zeros((diffs.shape[0], len(unique)))
    np.add.at(cluster_sums.T, inverse, diffs.T)
    cluster_counts = np.bincount(inverse, minlength=len(unique)).astype(np.float64)
    draws = rng.integers(0, len(unique), size=(replicates, len(unique)))
    estimates = np.empty(replicates)
    for index in range(replicates):
        picked = draws[index]
        total = cluster_sums[:, picked].sum(axis=1)
        count = cluster_counts[picked].sum()
        estimates[index] = (total / count).mean()
    return float(estimates.std(ddof=1))


@dataclass(frozen=True, slots=True)
class DecisionRule:
    """Confirm / kill / inconclusive regions derived from a stated noise model."""

    confirm: float
    kill_ceiling: float
    sigma_hat: float
    sigma_df: int
    sigma_upper: float
    se_prompt: float
    n_seeds: int
    se_seed_upper: float
    se_d_upper: float
    kappa: float
    separation: float
    regions_separated: bool
    phase1_withheld: bool
    minimum_detectable_effect: float


def minimum_detectable_effect(se: float, alpha: float = 0.01, power: float = 0.8) -> float:
    """Two-sided normal-approximation MDE = (z_{1-alpha/2} + z_power) * se."""

    if not math.isfinite(se) or se < 0.0:
        raise IndexerContractError("se must be finite and non-negative")
    if not 0.0 < alpha < 1.0 or not 0.0 < power < 1.0:
        raise IndexerContractError("alpha and power must lie in (0, 1)")
    return float((stats.norm.ppf(1.0 - alpha / 2.0) + stats.norm.ppf(power)) * se)


def derive_decision_rule(
    sigma_hat: float,
    sigma_df: int,
    se_prompt: float,
    n_seeds: int = len(PHASE1_SEEDS),
    confirm: float = CONFIRM_THRESHOLD_POINTS,
    kill_ceiling: float = KILL_CEILING_POINTS,
    confidence: float = 0.80,
) -> DecisionRule:
    """kappa = max(0, min(kill_ceiling, confirm - 2 * se_D_upper)).

    se_D_upper combines the seed component at the upper confidence bound of
    sigma (two arms, n_seeds each) with the paired passage-cluster bootstrap SE
    of the primary prompt sample: se_D^2 = 2 sigma_up^2 / n_seeds + se_prompt^2.
    The confirm-kill separation is at least 2 * se_D_upper unless kappa hits 0,
    in which case Phase 1 is withheld.
    """

    if not math.isfinite(se_prompt) or se_prompt < 0.0:
        raise IndexerContractError("se_prompt must be finite and non-negative")
    n_seeds = _positive_int(n_seeds, name="n_seeds", minimum=2)
    if not math.isfinite(confirm) or confirm <= 0.0:
        raise IndexerContractError("confirm threshold must be positive")
    if not math.isfinite(kill_ceiling) or not 0.0 <= kill_ceiling < confirm:
        raise IndexerContractError("kill ceiling must lie in [0, confirm)")
    sigma_up = sigma_upper_bound(sigma_hat, sigma_df, confidence)
    se_seed = sigma_up * math.sqrt(2.0 / n_seeds)
    se_d = math.sqrt(se_seed**2 + se_prompt**2)
    kappa = max(0.0, min(kill_ceiling, confirm - 2.0 * se_d))
    separation = confirm - kappa
    return DecisionRule(
        confirm=confirm,
        kill_ceiling=kill_ceiling,
        sigma_hat=float(sigma_hat),
        sigma_df=int(sigma_df),
        sigma_upper=sigma_up,
        se_prompt=float(se_prompt),
        n_seeds=n_seeds,
        se_seed_upper=se_seed,
        se_d_upper=se_d,
        kappa=kappa,
        separation=separation,
        regions_separated=separation >= 2.0 * se_d - 1e-12,
        phase1_withheld=kappa <= 0.0,
        minimum_detectable_effect=minimum_detectable_effect(se_d),
    )


def classify_primary_gain(gain: float, rule: DecisionRule, interval_excludes_zero: bool) -> str:
    """confirm when D >= confirm and the interval excludes zero; kill when D <= kappa.

    Anything between kappa and confirm is the pre-registered inconclusive band.
    """

    if not math.isfinite(gain):
        raise IndexerContractError("D must be finite")
    if rule.phase1_withheld:
        return "withheld"
    if gain >= rule.confirm and interval_excludes_zero:
        return "confirm"
    if gain <= rule.kappa:
        return "kill"
    return "inconclusive"


# --------------------------------------------------------------------------- #
# Registered gates and kill conditions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class GateVerdict:
    name: str
    evaluable: bool
    fired: bool
    statistic: float
    threshold: float
    note: str


def adequacy_gate(
    indexer_ml: float, target_ml: float, tolerance: float = ADEQUACY_TOLERANCE_POINTS
) -> GateVerdict:
    """Bug detector: English literal recall of the indexer within `tolerance` of R^T(ML)."""

    shortfall = _points(target_ml, name="target_ml") - _points(indexer_ml, name="indexer_ml")
    return GateVerdict(
        name="adequacy",
        evaluable=True,
        fired=shortfall > tolerance,
        statistic=shortfall,
        threshold=tolerance,
        note="fired means the indexer is inadequate; Phase 0 is inconclusive, never K1",
    )


def bug_tell(indexer_ml: float, target_ml: float, tolerance: float = 0.0) -> GateVerdict:
    """Indexer above its own target on the literal leg is a bug tell, not a result."""

    excess = _points(indexer_ml, name="indexer_ml") - _points(target_ml, name="target_ml")
    return GateVerdict(
        name="bug-tell",
        evaluable=True,
        fired=excess > tolerance,
        statistic=excess,
        threshold=tolerance,
        note="fired means investigate; the literal leg must not beat its own target",
    )


def phase0_localization(xi_by_configuration: Mapping[str, float]) -> GateVerdict:
    """P1 holds when xi_T >= 10 for at least one (base, form, aggregation)."""

    if not xi_by_configuration:
        raise IndexerContractError("localization needs at least one xi value")
    best = max(float(v) for v in xi_by_configuration.values())
    if not math.isfinite(best):
        raise IndexerContractError("xi values must be finite")
    return GateVerdict(
        name="P1-localization",
        evaluable=True,
        fired=best >= LOCALIZATION_CONFIRM_POINTS,
        statistic=best,
        threshold=LOCALIZATION_CONFIRM_POINTS,
        note="fired means an excess cross-script gap of at least 10 points exists somewhere",
    )


def k1_localization_negative(xi_by_configuration: Mapping[str, float]) -> GateVerdict:
    """K1 kills when xi_T <= 5 for every aggregation, base and indexer form."""

    if not xi_by_configuration:
        raise IndexerContractError("K1 needs at least one xi value")
    values = [float(v) for v in xi_by_configuration.values()]
    if not all(math.isfinite(v) for v in values):
        raise IndexerContractError("xi values must be finite")
    return GateVerdict(
        name="K1",
        evaluable=True,
        fired=max(values) <= LOCALIZATION_KILL_POINTS,
        statistic=max(values),
        threshold=LOCALIZATION_KILL_POINTS,
        note="fired means the indexer adds no cross-lingual bottleneck beyond its target",
    )


def k2a_target_aggregation_artifact(
    reference_cx: float,
    head_sum_indexer_cx: float,
    best_label_free_cx: float,
) -> GateVerdict:
    """K2a on absolute shortfall: evaluable when S_hs >= 3; fires at 80 percent recovery."""

    shortfall = absolute_shortfall(reference_cx, head_sum_indexer_cx)
    recovery = _points(best_label_free_cx, name="best_label_free_cx") - _points(
        head_sum_indexer_cx, name="head_sum_indexer_cx"
    )
    evaluable = shortfall >= K2A_EVALUABLE_POINTS
    return GateVerdict(
        name="K2a",
        evaluable=evaluable,
        fired=evaluable and recovery >= K2A_RECOVERY_FRACTION * shortfall,
        statistic=recovery / shortfall if shortfall > 0.0 else float("nan"),
        threshold=K2A_RECOVERY_FRACTION,
        note=f"S_hs={shortfall:.3f} points; not evaluable below {K2A_EVALUABLE_POINTS}",
    )


def k2b_weak_alignment_effect(
    gain: float, rule: DecisionRule, interval_excludes_zero: bool
) -> GateVerdict:
    """K2b fires when D <= kappa; kappa under D under confirm is inconclusive."""

    verdict = classify_primary_gain(gain, rule, interval_excludes_zero)
    return GateVerdict(
        name="K2b",
        evaluable=not rule.phase1_withheld,
        fired=verdict == "kill",
        statistic=float(gain),
        threshold=rule.kappa,
        note=f"classification={verdict}; confirm at {rule.confirm}, kappa={rule.kappa:.3f}",
    )


def inertness_holds(
    control_mn: float, counterfactual_mn: float, tolerance: float = INERTNESS_TOLERANCE_POINTS
) -> bool:
    """Precondition |R_control(MN) - R_b(MN)| <= 1 before a loss-form control counts."""

    return (
        abs(
            _points(control_mn, name="control_mn")
            - _points(counterfactual_mn, name="counterfactual_mn")
        )
        <= tolerance
    )


def k3_loss_form(
    gain: float, permuted_gain: float, half_gain: float, inertness: bool
) -> GateVerdict:
    """K3 fires (with inertness) when L_perm or L_half reaches 80 percent of D."""

    if gain <= 0.0:
        return GateVerdict(
            "K3", False, False, float("nan"), K3_FRACTION, "not evaluable: D is not positive"
        )
    fraction = max(permuted_gain, half_gain) / gain
    return GateVerdict(
        name="K3",
        evaluable=inertness,
        fired=inertness and fraction >= K3_FRACTION,
        statistic=fraction,
        threshold=K3_FRACTION,
        note="inertness failed: loss-form question unresolved" if not inertness else "",
    )


def k4_semantic_sharpening(gain: float, semantic_gain: float) -> GateVerdict:
    """K4 fires when monolingual semantic supervision reaches 50 percent of D."""

    if gain <= 0.0:
        return GateVerdict(
            "K4", False, False, float("nan"), K4_FRACTION, "not evaluable: D is not positive"
        )
    fraction = semantic_gain / gain
    return GateVerdict("K4", True, fraction >= K4_FRACTION, fraction, K4_FRACTION, "")


def k8_language_harm(
    per_language_drop: Mapping[str, float],
    e3_drop: float,
) -> GateVerdict:
    """K8 fires when any held-out language loses over 2 points or English E3 loses over 0.5."""

    if not per_language_drop:
        raise IndexerContractError("K8 needs at least one language")
    worst = max(float(v) for v in per_language_drop.values())
    if not math.isfinite(worst) or not math.isfinite(e3_drop):
        raise IndexerContractError("drops must be finite")
    fired = worst > LANGUAGE_HARM_POINTS or e3_drop > E3_HARM_POINTS
    return GateVerdict("K8", True, fired, worst, LANGUAGE_HARM_POINTS, f"e3_drop={e3_drop:.3f}")


__all__ = [
    "AGGREGATIONS",
    "CONDITIONS",
    "PHASE1_SEEDS",
    "AlignmentLossResult",
    "BilingualConcatenation",
    "ConditionRecall",
    "DecisionRule",
    "EvaluationPrompt",
    "GateVerdict",
    "IndexerContractError",
    "IndexerForward",
    "IndexerParameters",
    "LossBreakdown",
    "PassageSplit",
    "PooledSeedSD",
    "PromptFamily",
    "PromptLedgerEntry",
    "SelectorRecalls",
    "SyntheticBilingualWorld",
    "SyntheticWorldConfig",
    "TargetSelection",
    "TeacherParameters",
    "TrainedIndexer",
    "TrainingBatch",
    "TrainingConfig",
    "absolute_shortfall",
    "achieved_budget",
    "adequacy_gate",
    "aggregate_target",
    "alignment_log_mass_loss",
    "assert_reads_within",
    "brute_force_union_top_k",
    "budget_matched_reference",
    "bug_tell",
    "build_bilingual_concatenation",
    "build_synthetic_world",
    "causal_mask",
    "classify_primary_gain",
    "derive_decision_rule",
    "evaluate_selectors",
    "evaluation_families",
    "indexer_forward",
    "inertness_holds",
    "k1_localization_negative",
    "k2a_target_aggregation_artifact",
    "k2b_weak_alignment_effect",
    "k3_loss_form",
    "k4_semantic_sharpening",
    "k8_language_harm",
    "kl_to_target",
    "label_mask_from_alignment",
    "literal_copy_targets",
    "loss_and_gradient",
    "make_prompt_family",
    "make_training_batch",
    "minimum_detectable_effect",
    "other_half_label_mask",
    "own_target_excess",
    "paired_cluster_bootstrap_se",
    "permuted_label_mask",
    "phase0_localization",
    "pooled_seed_sd",
    "primary_gain",
    "reference_excess",
    "retrieval_head_scores",
    "retrieval_head_weights",
    "select_target_aggregation",
    "selection_recall",
    "sigma_upper_bound",
    "split_passage_ids",
    "teacher_attention",
    "top_k_selection",
    "train_indexer",
    "union_top_k_reference",
]
