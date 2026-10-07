"""Mapping from every KernelBench-M rule to its Triton port or a reason it has none.

KernelBench-M (HF dataset Elfsong/KernelBench-M@d04d6fc7, the artifact of
arXiv 2609.22220) declares no licence. Its rule files were read as a
behavioural reference only. Nothing here is copied from them except the rule
*names* (identifiers, also printed in the paper's Table 7) and their family
labels, which this table needs to state what was and was not ported. Every
Triton rewrite in ``operators/`` is an independent implementation written from
the paper's description and the rules' observable behaviour.

Statuses:

- ``ported``: the rule is the primary rule of one operator;
- ``subsumed``: a CUDA-specific spelling whose Triton form is produced by the
  named operator (listed in that operator's ``ports``);
- ``not-applicable``: no Triton analogue, with the reason.
"""

from __future__ import annotations

from harness.q1.mutate.operators import OPERATORS

# All 127 rule definitions loaded by the released mutator (its pattern-level
# dedup leaves 124 active; the paper's Table 7 lists 120). Family labels are
# KernelBench-M's; "sync" is this repository's "synchronization".
KERNELBENCH_M_RULES: dict[str, str] = {
    # pipeline/mutator.py
    "ceil2floor": "boundary",
    "ceil2floor-lit": "boundary",
    "lt2le": "boundary",
    "le2lt": "boundary",
    "ge2gt": "boundary",
    "guard-drop-if": "boundary",
    "guard-drop-ternary": "boundary",
    "loop-bound-minus1": "boundary",
    "loop-start-1": "boundary",
    "sync-remove": "synchronization",
    "acc-fp16": "precision",
    "store-fp16": "precision",
    "expf-fast": "precision",
    "fdividef-fast": "precision",
    "tidx2tidy": "indexing",
    "bidx2bidy": "indexing",
    "bdim2gdim": "indexing",
    "plus2minus": "arithmetic",
    "acc-overwrite": "semantic",
    "acc-minus": "semantic",
    "fmax2fmin": "semantic",
    "fmin2fmax": "semantic",
    "sentinel-zero": "semantic",
    "const0to1": "semantic",
    "lt2gt": "boundary",
    "gt2ge": "boundary",
    "return-guard-drop": "boundary",
    "mul2div": "arithmetic",
    "mul2plus": "arithmetic",
    "minus2plus": "arithmetic",
    "negate-store": "arithmetic",
    "sync2syncwarp": "synchronization",
    "reduce-shift2": "boundary",
    "smem-index-off1": "indexing",
    "warpsize-16": "indexing",
    # rules/structural_rules.py
    "argmax-tie-last": "semantic",
    "argmin-tie-last": "semantic",
    "argmax-tie-nan-form": "semantic",
    "argmax-nan-policy-drop": "semantic",
    "argmax-seed-from-second": "boundary",
    "reduce-fmax-tie-order": "semantic",
    "reduce-fmin-tie-order": "semantic",
    "reduce-seed-first-element": "boundary",
    "reduce-seed-first-element-min": "boundary",
    "gelu-tanh-const-perturb": "precision",
    "gelu-sqrt2pi-perturb": "precision",
    "invsqrt2-perturb": "precision",
    "selu-alpha-perturb": "precision",
    "selu-scale-perturb": "precision",
    "erf-to-tanh-approx": "precision",
    "softplus-cutoff-shift": "precision",
    "relu-threshold-shift": "semantic",
    "hardsigmoid-slope-perturb": "precision",
    "clamp-bound-perturb": "precision",
    "elementwise-guard-minus1": "boundary",
    "elementwise-guard-plus1": "boundary",
    "grid-stride-step-double": "boundary",
    # rules/fine_rules.py
    "output-elements-one-extra-lane": "boundary",
    "line-count-one-extra-lane": "boundary",
    "flat-n-one-extra-lane": "boundary",
    "matmul-a-last-k-drop": "boundary",
    "matmul-a-transposed-last-k-drop": "boundary",
    "matmul-b-last-k-drop": "boundary",
    "arg-reduction-last-row-drop": "boundary",
    "min-reduction-last-row-drop": "boundary",
    "cumsum-last-output-drop": "boundary",
    "pool2d-last-tap-drop": "boundary",
    "groupnorm-sum-tail-scalar-drop": "boundary",
    "groupnorm-sqdev-tail-scalar-drop": "boundary",
    "matmul-after-load-warp-barrier": "synchronization",
    "matmul-after-compute-warp-barrier": "synchronization",
    "groupnorm-sum-store-warp-barrier": "synchronization",
    "groupnorm-sqdev-store-warp-barrier": "synchronization",
    "groupnorm-final-output-warp-barrier": "synchronization",
    "batchnorm-local-stats-warp-barrier": "synchronization",
    "batchnorm-merge-warp-barrier": "synchronization",
    "batchnorm-output-warp-barrier": "synchronization",
    "avgpool121-denom-perturb": "precision",
    "hardsigmoid-six-denom-perturb": "precision",
    "hardsigmoid-half-ulpish-perturb": "precision",
    "softplus-cutoff-tiny-shift": "precision",
    "selu-scale-small-perturb": "precision",
    "selu-alpha-small-perturb": "precision",
    "groupnorm-epsilon-halved": "precision",
    "batchnorm-epsilon-small-bias": "precision",
    "matmul-acc-store-fma-nudge": "precision",
    "argmax-final-row-alias": "indexing",
    "argmax-final-row-value-alias": "indexing",
    "selu-positive-cutoff-nudge": "semantic",
    "elu-positive-cutoff-nudge": "semantic",
    "softsign-positive-fabs-elide": "semantic",
    # rules/mined_rules.py
    "relu-fmax-zero-remove": "semantic",
    "relu-fmax-zero-first-remove": "semantic",
    "upper-unit-clamp-remove": "semantic",
    "upper-unit-clamp-first-remove": "semantic",
    "lower-negunit-clamp-remove": "semantic",
    "nested-unit-clamp-drop-upper": "semantic",
    "fabs-simple-remove": "semantic",
    "rsqrt-epsilon-remove": "precision",
    "sqrt-epsilon-remove": "precision",
    "literal-epsilon-remove": "precision",
    "softmax-max-subtraction-remove": "precision",
    "softmax-max-subtraction-fast-remove": "precision",
    "welford-second-delta-reuse": "precision",
    "variance-unbiased-count": "precision",
    "kahan-compensation-drop": "precision",
    "last-row-reduction-skip": "boundary",
    "last-row-reduction-skip-start1": "boundary",
    "strided-tail-drop": "boundary",
    "tile-last-iteration-skip": "boundary",
    "literal-loop-last-skip": "boundary",
    "tail-guard-tighten": "boundary",
    "shared-denom-use-local": "synchronization",
    "shared-sqrt-use-local": "synchronization",
    "reduction-barrier-move-before-store": "synchronization",
    "welford-count-merge-early": "synchronization",
    "reduction-partner-half-offset": "indexing",
    "row-store-stride-k": "indexing",
    "a-row-stride-n": "indexing",
    "b-row-stride-k": "indexing",
    "matrix-row-bound-use-n": "boundary",
    "matrix-col-bound-use-m": "boundary",
    "height-bound-use-width": "boundary",
    "width-bound-use-height": "boundary",
    "flatten-height-use-width": "indexing",
    "output-position-height-first": "indexing",
    "grid-x-use-block-y": "indexing",
}

#: Defined in KernelBench-M but dropped by its loader because their regex equals
#: an earlier rule's (127 defined - 3 = 124 active). In Triton they are distinct
#: mutations, so the port keeps them.
KERNELBENCH_M_INACTIVE = frozenset(
    {"argmin-tie-last", "argmax-seed-from-second", "elementwise-guard-plus1"}
)

_NO_BARRIER = (
    "Triton inserts its own barriers and has no warp-level or named barrier in the "
    "language, so a __syncthreads -> __syncwarp weakening has no analogue."
)
_NO_TREE = (
    "Triton block reductions (tl.sum, tl.max, tl.reduce) hide the explicit shared-memory "
    "tree, its partner index, its shift and its warp-size start."
)
_NO_SHARED = "Triton block programs have no per-thread versus shared-memory distinction to confuse."

NOT_APPLICABLE: dict[str, str] = {
    "tidx2tidy": "Triton has no thread index; a program instance owns the whole block.",
    "warpsize-16": _NO_TREE,
    "reduce-shift2": _NO_TREE,
    "reduction-partner-half-offset": _NO_TREE,
    "sync2syncwarp": _NO_BARRIER,
    "matmul-after-load-warp-barrier": _NO_BARRIER,
    "matmul-after-compute-warp-barrier": _NO_BARRIER,
    "groupnorm-sum-store-warp-barrier": _NO_BARRIER,
    "groupnorm-sqdev-store-warp-barrier": _NO_BARRIER,
    "groupnorm-final-output-warp-barrier": _NO_BARRIER,
    "batchnorm-local-stats-warp-barrier": _NO_BARRIER,
    "batchnorm-merge-warp-barrier": _NO_BARRIER,
    "batchnorm-output-warp-barrier": _NO_BARRIER,
    "reduction-barrier-move-before-store": _NO_BARRIER,
    "shared-denom-use-local": _NO_SHARED,
    "shared-sqrt-use-local": _NO_SHARED,
    "welford-count-merge-early": _NO_SHARED,
    "welford-second-delta-reuse": (
        "Matches one CUDA Welford spelling (a named second delta); Triton substrates "
        "compute moments by two-pass sums or tl.reduce combine functions. Not ported."
    ),
    "kahan-compensation-drop": (
        "No compensated summation appears in Triton substrates; Triton accumulates in "
        "fp32 registers. Not ported."
    ),
    "argmax-final-row-alias": (
        "Targets an explicit per-row argmax loop; Triton arg-reductions are whole-block "
        "tl.argmax calls with no final-row index to alias. Not ported."
    ),
    "argmax-final-row-value-alias": (
        "Targets an explicit per-row argmax loop (value read); see argmax-final-row-alias."
    ),
    "avgpool121-denom-perturb": (
        "Perturbs the literal 121-tap divisor of one CUDA pooling kernel; Triton pooling "
        "divisors are runtime values. Not ported."
    ),
}


def rule_mapping() -> dict[str, dict[str, str]]:
    """Every KernelBench-M rule -> {status, operator or reason, family}."""
    mapping: dict[str, dict[str, str]] = {}
    for op in OPERATORS:
        if op.kbm_rule:
            mapping.setdefault(
                op.kbm_rule, {"status": "ported", "operator": op.name, "family": op.family}
            )
    for op in OPERATORS:
        for rule in op.ports:
            mapping.setdefault(
                rule, {"status": "subsumed", "operator": op.name, "family": op.family}
            )
    for rule, reason in NOT_APPLICABLE.items():
        mapping.setdefault(
            rule,
            {"status": "not-applicable", "reason": reason, "family": KERNELBENCH_M_RULES[rule]},
        )
    return {rule: mapping[rule] for rule in KERNELBENCH_M_RULES if rule in mapping}


def unmapped_rules() -> list[str]:
    mapping = rule_mapping()
    return [rule for rule in KERNELBENCH_M_RULES if rule not in mapping]


def mapping_markdown() -> str:
    """The mapping as a Markdown table (for README regeneration and review)."""
    lines = [
        "| KernelBench-M rule | KBM family | Status | Triton operator or reason |",
        "|---|---|---|---|",
    ]
    for rule, entry in rule_mapping().items():
        target = entry.get("operator") or entry.get("reason", "")
        lines.append(f"| `{rule}` | {KERNELBENCH_M_RULES[rule]} | {entry['status']} | {target} |")
    return "\n".join(lines)
