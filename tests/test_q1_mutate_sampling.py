"""Family-stratified cap and frozen split."""

from __future__ import annotations

import hashlib
from collections import Counter

import pytest

from harness.q1.mutate.sampling import problem_split_of, split_of, stratified_cap, waterfill


@pytest.mark.parametrize(
    ("caps", "total", "expected"),
    [
        ([10, 10, 10], 9, [3, 3, 3]),
        ([1, 10, 10], 9, [1, 4, 4]),
        ([2, 3], 40, [2, 3]),
        ([5, 5, 5], 10, [4, 3, 3]),
        ([0, 7], 4, [0, 4]),
        ([], 5, []),
    ],
)
def test_waterfill(caps, total, expected):
    assert waterfill(caps, total) == expected


def test_waterfill_properties():
    for seed in range(50):
        caps = [int(c, 16) for c in hashlib.sha256(str(seed).encode()).hexdigest()[:6]]
        alloc = waterfill(caps, 9)
        assert sum(alloc) == min(9, sum(caps))
        assert all(a <= c for a, c in zip(alloc, caps, strict=True))
        unsaturated = [a for a, c in zip(alloc, caps, strict=True) if a < c]
        if unsaturated:
            assert max(alloc) - min(unsaturated) <= 1


def _items(spec):
    out = []
    for family, operator, n in spec:
        for i in range(n):
            digest = hashlib.sha256(f"{family}/{operator}/{i}".encode()).hexdigest()
            out.append({"family": family, "operator": operator, "hash": digest})
    return out


def _cap(items, seed=42, cap=40, substrate="s"):
    return stratified_cap(
        items,
        family=lambda r: r["family"],
        operator=lambda r: r["operator"],
        content_key=lambda r: r["hash"],
        substrate_id=substrate,
        cap=cap,
        seed=seed,
    )


POOL = [
    ("arithmetic", "plus2minus", 60),
    ("arithmetic", "mul2div", 30),
    ("boundary", "lt2le", 25),
    ("boundary", "mask-drop", 3),
    ("precision", "store-fp16", 2),
    ("semantic", "max2min", 9),
]


def test_cap_respects_limit_and_keeps_every_family():
    chosen = _cap(_items(POOL))
    assert len(chosen) == 40
    families = Counter(c.family for c in chosen)
    assert families == {"arithmetic": 15, "boundary": 14, "precision": 2, "semantic": 9}
    operators = Counter(c.operator for c in chosen)
    assert operators["mask-drop"] == 3 and operators["lt2le"] == 11


def test_small_pools_are_kept_whole():
    items = _items([("boundary", "lt2le", 5), ("semantic", "max2min", 4)])
    chosen = _cap(items)
    assert len(chosen) == 9
    assert all(c.inclusion_probability == 1.0 and c.weight == 1.0 for c in chosen)


def test_inclusion_probabilities_and_weights_are_exact():
    chosen = _cap(_items(POOL))
    for c in chosen:
        assert c.inclusion_probability == c.k_operator_stratum / c.n_operator_stratum
    weight_by_operator = Counter()
    for c in chosen:
        weight_by_operator[c.operator] += c.weight
    sizes = {operator: n for _, operator, n in POOL}
    for operator, total in weight_by_operator.items():
        assert total == pytest.approx(sizes[operator])


def test_cap_is_deterministic_and_seed_sensitive():
    items = _items(POOL)
    first = [c.item["hash"] for c in _cap(items)]
    assert first == [c.item["hash"] for c in _cap(list(reversed(items)))]
    assert first != [c.item["hash"] for c in _cap(items, seed=43)]
    assert first != [c.item["hash"] for c in _cap(items, substrate="other")]


def test_cap_rejects_unknown_family_and_bad_cap():
    with pytest.raises(ValueError):
        _cap(_items([("hack", "x", 1)]))
    with pytest.raises(ValueError):
        _cap(_items(POOL), cap=0)


def test_split_is_a_pure_function_of_content_and_seed():
    assert split_of("s", "a" * 64) == split_of("s", "a" * 64)
    hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(4000)]
    counts = Counter(split_of("sub", h) for h in hashes)
    assert set(counts) == {"dev", "test"}
    assert 0.46 < counts["dev"] / 4000 < 0.54
    other_seed = Counter(split_of("sub", h, seed=43) == split_of("sub", h) for h in hashes)
    assert 0.4 < other_seed[True] / 4000 < 0.6
    assert problem_split_of("L1/19_ReLU") in {"dev", "test"}
    assert problem_split_of("L1/19_ReLU") == problem_split_of("L1/19_ReLU")
