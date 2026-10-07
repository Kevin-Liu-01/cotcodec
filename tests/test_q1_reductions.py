"""Chunked device reductions equal the earlier whole-tensor host implementations."""

from __future__ import annotations

import math

import pytest

torch = pytest.importorskip("torch")

from harness.q1.audit import contracts, oracle  # noqa: E402
from harness.q1.gates import reductions as red  # noqa: E402

# --- the previous implementations, verbatim (host fp64 copies) -------------------


def old_error_stats(output, reference):
    out = output.detach().to("cpu", torch.float64)
    ref = reference.detach().to("cpu", torch.float64)
    if out.shape != ref.shape:
        return math.inf, math.inf
    if out.numel() == 0:
        return 0.0, 0.0
    both_finite = torch.isfinite(out) & torch.isfinite(ref)
    same_nonfinite = (torch.isnan(out) & torch.isnan(ref)) | (
        torch.isinf(out) & torch.isinf(ref) & (torch.sign(out) == torch.sign(ref))
    )
    if bool((~both_finite & ~same_nonfinite).any()):
        return math.inf, math.inf
    if not bool(both_finite.any()):
        return 0.0, 0.0
    diff = (out - ref).abs()[both_finite]
    denom = ref.abs()[both_finite]
    nonzero = denom > 0
    max_rel = float((diff[nonzero] / denom[nonzero]).max()) if bool(nonzero.any()) else 0.0
    return float(diff.max()), max_rel


def old_within(a, b, tol):
    if a.shape != b.shape:
        return False
    if not a.is_floating_point() or not b.is_floating_point():
        return bool(torch.equal(a.cpu().to(torch.int64), b.cpu().to(torch.int64)))
    return bool(
        torch.allclose(a.detach().cpu().double(), b.detach().cpu().double(), atol=tol, rtol=tol)
    )


def old_masks_equal(x, r64):
    x = x.detach().cpu().double()
    r = r64.detach().cpu().double()
    if x.shape != r.shape:
        return False
    return bool(
        torch.equal(torch.isnan(x), torch.isnan(r))
        and torch.equal(torch.isposinf(x), torch.isposinf(r))
        and torch.equal(torch.isneginf(x), torch.isneginf(r))
    )


def old_scaled_error(x, r64, kappa=oracle.KAPPA):
    x = x.detach().cpu().double()
    r = r64.detach().cpu().double()
    if x.shape != r.shape:
        return math.inf
    finite = torch.isfinite(x) & torch.isfinite(r)
    if not bool(finite.any()):
        return 0.0
    r_finite = r[finite]
    norm = float(r_finite.abs().max())
    denom = r_finite.abs() + kappa * norm
    diff = (x[finite] - r_finite).abs()
    zero = denom == 0
    if bool(zero.any()):
        if bool((diff[zero] > 0).any()):
            return math.inf
        diff, denom = diff[~zero], denom[~zero]
        if diff.numel() == 0:
            return 0.0
    return float((diff / denom).max())


# --- cases ------------------------------------------------------------------------


def _cases():
    g = torch.Generator().manual_seed(0)
    base = torch.randn(7, 13, generator=g)
    near = base + 1e-4 * torch.randn(7, 13, generator=g)
    special = base.clone()
    special[0, 0] = float("nan")
    special[3, 5] = float("inf")
    special[6, 12] = float("-inf")
    zeros = torch.zeros(7, 13)
    zeros_off = zeros.clone()
    zeros_off[2, 2] = 1e-3
    yield base, base.clone()
    yield near, base
    yield special, special.clone()
    yield special, base
    yield base, special
    yield zeros, zeros.clone()
    yield zeros_off, zeros
    yield torch.full((7, 13), float("nan")), torch.full((7, 13), float("nan"))
    yield base, base.t().contiguous()  # shape mismatch
    yield torch.empty(0), torch.empty(0)
    yield base[:, ::2], near[:, ::2]  # non-contiguous


@pytest.mark.parametrize("chunk", [1, 5, 13, 1 << 26])
def test_error_metrics_match_previous_implementations(chunk: int) -> None:
    for out, ref in _cases():
        assert red.error_stats(out, ref, chunk=chunk) == old_error_stats(out, ref)
        ref64 = ref.double()
        assert red.masks_equal(out, ref64, chunk=chunk) == old_masks_equal(out, ref64)
        assert red.scaled_error(out, ref64, oracle.KAPPA, chunk=chunk) == old_scaled_error(
            out, ref64
        )
        for tol in (1e-3, 1e-2):
            new = red.allclose_fp64(out, ref, tol, chunk=chunk) if out.shape == ref.shape else False
            assert new == old_within(out, ref, tol)


def test_integer_and_mixed_equality_match() -> None:
    a = torch.tensor([1, 2, 3, -4])
    b = a.clone()
    assert red.equal_int64(a, b) == old_within(a, b, 1e-3) is True
    c = torch.tensor([1.9, 2.0, 3.0, -4.2])
    assert red.equal_int64(c, a) == old_within(c, a, 1e-3)
    assert red.equal_int64(a, torch.tensor([1, 2, 3, 5])) is False


def test_oracle_and_gate_wrappers_delegate() -> None:
    out, ref = torch.randn(4, 4), torch.randn(4, 4)
    assert oracle.scaled_error(out, ref.double()) == old_scaled_error(out, ref.double())
    assert oracle.masks_equal(out, ref.double()) == old_masks_equal(out, ref.double())


def test_byte_snapshots_compare_like_host_bytes() -> None:
    x = torch.randn(3, 5)
    values = [x, 3, x.t()]
    same = [x.clone(), 7, x.t().clone()]
    assert (
        contracts.same_bytes(values, same)
        == (contracts._snapshot(values) == contracts._snapshot(same))
        is True
    )
    changed = [x.clone(), 3, x.t().clone()]
    changed[0][1, 1] += 1
    assert contracts.same_bytes(values, changed) is False
    assert contracts._snapshot(values) != contracts._snapshot(changed)
    assert contracts.same_bytes([x], [x.view(torch.int32)]) == (
        contracts._snapshot([x]) == contracts._snapshot([x.view(torch.int32)])
    )
    assert contracts.same_bytes([x], [x, x]) is False
    assert contracts.same_bytes([torch.empty(0)], [torch.empty(0, 3)]) is True


def test_determinism_contract_still_flags_nondeterminism_and_mutation() -> None:
    class Counter(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def forward(self, x):
            self.calls += 1
            return x * self.calls

    class Mutating(torch.nn.Module):
        def forward(self, x):
            x.add_(1.0)
            return x.clone()

    x = torch.randn(4, 4)
    results = {
        r.name: r.passed
        for r in contracts.check_determinism_and_aliasing(
            Counter(), [x], device=torch.device("cpu")
        )
    }
    assert results["determinism"] is False and results["inputs_unmodified"] is True
    results = {
        r.name: r.passed
        for r in contracts.check_determinism_and_aliasing(
            Mutating(), [x], device=torch.device("cpu")
        )
    }
    assert results["inputs_unmodified"] is False and results["determinism"] is True
