"""Engine and operator tests on toy Triton kernels parsed as source (no GPU, no Triton)."""

from __future__ import annotations

import ast
import difflib

import pytest

from harness.q1.mutate.engine import OperatorFailure, enumerate_mutants, mutant_id
from harness.q1.mutate.operators import OPERATORS, Operator, ScopeContext
from harness.q1.mutate.source import KernelSource, SourceError, normalized_ast_hash
from harness.q1.schema import SITE_RE, validate_mutation
from tests._q1_mutate_support import TOYS, toy_text


@pytest.fixture(scope="module")
def enumerations():
    return {name: enumerate_mutants(toy_text(name)) for name in TOYS}


def _find(enumeration, operator, needle=None):
    hits = [m for m in enumeration.distinct if m.operator == operator]
    if needle is not None:
        hits = [m for m in hits if needle in m.source]
    return hits


def test_every_operator_fires_on_some_toy(enumerations):
    fired = {m.operator for e in enumerations.values() for m in e.distinct}
    assert {op.name for op in OPERATORS} - fired == set()


def test_enumeration_is_deterministic():
    for name in TOYS:
        first = enumerate_mutants(toy_text(name))
        second = enumerate_mutants(toy_text(name))
        assert [(m.key, m.dedup_hash) for m in first.distinct] == [
            (m.key, m.dedup_hash) for m in second.distinct
        ]


def test_mutants_parse_differ_and_are_unique(enumerations):
    for name, enumeration in enumerations.items():
        parent = normalized_ast_hash(toy_text(name))
        hashes = [m.dedup_hash for m in enumeration.distinct]
        assert len(hashes) == len(set(hashes)), name
        for mutant in enumeration.distinct:
            ast.parse(mutant.source)
            assert mutant.dedup_hash == normalized_ast_hash(mutant.source)
            assert mutant.dedup_hash != parent
            assert SITE_RE.fullmatch(mutant.site)


def test_edits_are_local(enumerations):
    """Outside its edits a mutant is byte-identical to the parent."""
    for name, enumeration in enumerations.items():
        parent_lines = toy_text(name).splitlines()
        for mutant in enumeration.distinct:
            changed = [
                line
                for line in difflib.unified_diff(
                    parent_lines, mutant.source.splitlines(), lineterm="", n=0
                )
                if line.startswith("-") and not line.startswith("---")
            ]
            assert 1 <= len(changed) <= 2 * mutant.n_edits, (name, mutant.key)


def test_site_points_at_anchor_line(enumerations):
    for name, enumeration in enumerations.items():
        lines = toy_text(name).splitlines()
        for mutant in enumeration.distinct:
            assert 1 <= mutant.line <= len(lines)
            assert 0 <= mutant.col <= len(lines[mutant.line - 1])


@pytest.mark.parametrize(
    ("toy", "operator", "needle"),
    [
        ("relu_where", "relu-where-remove", "    y = x\n"),
        ("relu_where", "mask-drop", "x = tl.load(x_ptr + offsets)\n"),
        ("relu_where", "ceil2floor", '(n // meta["BLOCK_SIZE"])'),
        ("relu_where", "lt2le", "mask = (offsets <= n_elements)"),
        ("relu_where", "mask-bound-minus1", "mask = offsets < (n_elements - 1)"),
        ("relu_where", "program-id-axis-swap", "tl.program_id(axis=1)"),
        ("relu_where", "block-size-to-num-programs", "pid * tl.num_programs(0)"),
        ("relu_inductor", "relu-max-zero-first-remove", "tmp2 = tmp0\n"),
        ("relu_inductor", "const0to1", "tl.full([1], 1, tl.int32)"),
        ("softmax_rows", "softmax-max-subtraction-remove", "row_minus_max = row\n"),
        ("softmax_rows", "div-fast", "tl.fdiv(numerator, denominator)"),
        ("softmax_rows", "sentinel-zero", "other=0.0)"),
        ("softmax_rows", "loop-step-double", "(2 * row_step)"),
        ("softmax_rows", "launch-stride-swap", "x.stride(1), y.stride(0)"),
        ("layernorm", "epsilon-remove", "tl.sqrt(var)"),
        ("layernorm", "epsilon-halve", "tl.sqrt(var + (eps * 0.5))"),
        ("layernorm", "variance-unbiased-count", "var = tl.sum(_var, axis=0) / (N - 1)"),
        ("layernorm", "loop-bound-minus1", "range(0, (N - BLOCK_SIZE), BLOCK_SIZE)"),
        ("layernorm", "loop-start-1", "range((0 + BLOCK_SIZE), N, BLOCK_SIZE)"),
        ("layernorm", "where-guard-drop", "x = (x - mean)"),
        ("matmul", "dot-tf32", 'input_precision="tf32"'),
        ("matmul", "acc-overwrite", 'tl.dot(a, b, input_precision="ieee")'),
        ("matmul", "block-size-swap", "pid_m * BLOCK_SIZE_N"),
        ("matmul", "stride-param-swap", "offs_am[:, None] * stride_ak"),
        ("matmul", "dim-param-swap-decode", "% N\n"),
        ("matmul", "bound-dim-swap", "(offs_cm[:, None] < N)"),
        ("argmax_rows", "argmax-tie-last", "tl.argmax(x, axis=0, tie_break_left=False)"),
        ("argmax_rows", "return-guard-drop", "    pass\n"),
        ("argmax_rows", "sentinel-zero-min", "tl.full([BLOCK_N], 0.0, tl.float32)"),
        ("argmax_rows", "reduce-min-tie-order", "m = tl.where(x < m, x, m)"),
        ("gelu_erf", "erf-to-tanh-approx", "tl.exp(-2.0 * (1.1283791670955126"),
        ("gelu_erf", "exp-fast", "1.0 + tl.exp(-2.0 * inner)"),
        ("gelu_erf", "named-constant-perturb", "0.044759715"),
        ("splitk_atomic", "atomic-add-to-store", "tl.store(out_ptr + row, tl.sum(acc, axis=0))"),
        ("splitk_atomic", "atomic-rmw-split", "tl.load(out_ptr + row) + tl.sum(acc, axis=0)"),
        ("splitk_atomic", "debug-barrier-remove", "    pass\n"),
        ("activations", "clamp-nested-drop-upper", "hardtanh = tl.maximum(x, -1.0)"),
        ("activations", "clamp-lower-negunit-remove", "hardtanh = tl.minimum(x, 1.0)"),
        ("activations", "clamp-bound-perturb", "tl.maximum(x, -1.0), 0.999)"),
        ("activations", "abs-remove", "softsign = x / (1.0 + x)"),
        ("activations", "positive-cutoff-nudge", "tl.where(x > -1e-06, x, alpha"),
        ("activations", "cutoff-shift", "x > 8.0"),
        ("reductions_misc", "nan-propagation-drop", "safe = tl.maximum(run_max, 0.0)\n"),
        ("reductions_misc", "reduce-max-tie-order", "tl.where(blk > run_max, blk, run_max)"),
        ("reductions_misc", "argmin-tie-last", "tie_break_left=False"),
    ],
)
def test_operator_rewrites(enumerations, toy, operator, needle):
    assert _find(enumerations[toy], operator, needle), f"{operator} on {toy}"


def test_acc_fp16_rewrites_declaration_and_updates(enumerations):
    (mutant,) = _find(enumerations["matmul"], "acc-fp16")
    assert "dtype=tl.float16)" in mutant.source
    assert "out_dtype=tl.float16" in mutant.source
    assert mutant.n_edits == 2
    layer = _find(enumerations["layernorm"], "acc-fp16")
    assert any("_mean += (a).to(tl.float16)" in m.source for m in layer)


def test_duplicates_keep_the_earlier_operator(enumerations):
    rejected = enumerations["relu_where"].rejected
    duplicates = [r for r in rejected if r.reason == "duplicate"]
    assert [(r.operator, r.duplicate_of.split("@")[0]) for r in duplicates] == [
        ("where-guard-drop", "relu-where-remove")
    ]


def test_sentinels_do_not_rewrite_whole_full_calls(enumerations):
    for mutant in _find(enumerations["argmax_rows"], "sentinel-zero-min"):
        assert "m = 0.0" not in mutant.source


def test_kbm_rule_override_per_site(enumerations):
    rules = {m.kbm_rule for m in _find(enumerations["gelu_erf"], "named-constant-perturb")}
    assert {"gelu-tanh-const-perturb", "gelu-sqrt2pi-perturb", "invsqrt2-perturb"} <= rules
    eps = _find(enumerations["layernorm"], "epsilon-remove")
    assert {m.kbm_rule for m in eps} == {"sqrt-epsilon-remove"}


def test_scope_analysis_separates_pointers_dims_and_strides():
    src = KernelSource(toy_text("matmul"))
    ctx = ScopeContext.device(src, src.jit_functions()[0])
    assert ctx.pointer_params == {"a_ptr", "b_ptr", "c_ptr"}
    assert ctx.dim_params == ["M", "N", "K"]
    assert ctx.stride_params[:2] == ["stride_am", "stride_ak"]
    assert ctx.constexpr_params == ["BLOCK_SIZE_M", "BLOCK_SIZE_N", "BLOCK_SIZE_K"]
    argmax = KernelSource(toy_text("argmax_rows"))
    actx = ScopeContext.device(argmax, argmax.jit_functions()[0])
    assert actx.dim_params == ["n_rows", "n_cols"]


def test_alias_resolution_for_inductor_and_libdevice():
    src = KernelSource(toy_text("relu_inductor"))
    calls = {src.call_name(n) for n in ast.walk(src.tree) if isinstance(n, ast.Call)}
    assert "triton_helpers.maximum" in calls
    gelu = KernelSource(toy_text("gelu_erf"))
    assert "libdevice.erf" in {gelu.call_name(n) for n in ast.walk(gelu.tree)}


def test_utf8_columns_are_converted_to_characters():
    text = "def f(a, b):\n    s = 'é'; y = a + b\n    return y\n"
    src = KernelSource(text)
    binop = next(n for n in ast.walk(src.tree) if isinstance(n, ast.BinOp))
    assert src.segment(binop) == "a + b"
    assert src.site(binop) == (2, text.splitlines()[1].index("a + b"))


def test_formatting_and_comments_do_not_change_the_dedup_hash():
    text = toy_text("relu_where")
    reformatted = text.replace("mask = offsets < n_elements", "mask = (offsets < n_elements)  # g")
    assert normalized_ast_hash(text) == normalized_ast_hash(reformatted)


def test_source_without_jit_function_is_rejected():
    with pytest.raises(SourceError):
        enumerate_mutants("import torch\n\nclass ModelNew:\n    pass\n")


def test_operator_bug_fails_closed():
    def broken(ctx):
        raise ValueError("boom")
        yield  # pragma: no cover

    bad = Operator("broken-op", "arithmetic", "triton-only", None, ("device",), "x", broken)
    with pytest.raises(OperatorFailure, match="broken-op"):
        enumerate_mutants(toy_text("relu_where"), operators=[bad])


def test_operator_metadata_is_validated():
    with pytest.raises(ValueError):
        Operator("x", "nonsense", "paper", "plus2minus", ("device",), "d", lambda c: [])
    with pytest.raises(ValueError):
        Operator("x", "arithmetic", "paper", None, ("device",), "d", lambda c: [])
    with pytest.raises(ValueError):
        Operator("x", "arithmetic", "triton-only", "plus2minus", ("device",), "d", lambda c: [])


def test_mutant_ids_are_schema_valid_and_unique(enumerations):
    taken: set[str] = set()
    for mutant in enumerations["matmul"].distinct:
        ident = mutant_id("toy-matmul", mutant, taken)
        validate_mutation(
            {
                "mutant_id": ident,
                "parent_substrate_id": "toy-matmul",
                "operator": mutant.operator,
                "family": mutant.family,
                "site": mutant.site,
                "seed": 42,
                "triton_disable_line_info": True,
                "dedup_hash": mutant.dedup_hash,
                "rule_origin": mutant.rule_origin,
                "kernelbench_m_rule": mutant.kbm_rule,
            }
        )
    assert len(taken) == len(enumerations["matmul"].distinct)
    long_id = mutant_id("s" * 150, enumerations["matmul"].distinct[0], set())
    assert len(long_id) <= 160
