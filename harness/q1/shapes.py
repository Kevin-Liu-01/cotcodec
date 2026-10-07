"""Shape-override rules for gate c2/c3 and audit A3, and the committed shape manifest.

Rules (preregistered; ``d`` is a free root's native value, see ``problems.py``):

c2, shape variation (each drawn with D1 and D4 at run time):
- ``S-half``: leading root -> ``max(1, d // 2)``;
- ``S-double``: inner root -> ``2 d``, reduced to the largest value whose input
  bytes stay within 2x native;
- ``S-small``: every free root -> ``max(1, d // 8)``.

c3, unaligned remainders (each drawn with D1 and D4):
- ``U1/<root>``: one root -> ``d + 1``;
- ``U2/<root>``: one root -> ``(d - d mod 128) + 17``;
- ``U3``: leading root -> 3;
- matmul problems only: ``MM1``: every free root -> ``(d - d mod 64) + 1``;
  ``MM17``: every free root -> ``(d - d mod 64) + 17``.

A3, held-out prime shapes for the audit (never seen by a gate):
- ``lead1``, ``lead5``: leading root -> 1, 5;
- ``inner37``: inner root -> largest prime <= ``round(0.37 d)``;
- ``inner137``: inner root -> smallest prime >= ``round(1.37 d)``, reduced to
  the largest prime within 2x native input bytes (a held-out shape larger
  than native, so kernels that only cover sizes up to native are exposed);
- ``allprime``: every free root -> largest prime <= ``round(0.37 d)``.

Every config is dropped (and logged) if it equals the native shape or exceeds
2x native input bytes. A3 configs must be disjoint from c: no A3 value may
equal any value c uses for the same root; colliding values move to the next
smaller prime (``inner37``/``allprime``) or the next larger prime
(``lead1``/``lead5``).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any

from harness.q1.problems import ProblemAnalysis

MANIFEST_SCHEMA = "q1-shape-manifest/1"
BYTE_CAP = 2.0


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    return all(n % k for k in range(3, math.isqrt(n) + 1, 2))


def prev_prime(n: int) -> int:
    """Largest prime <= n (n >= 2)."""
    n = max(2, n)
    while not is_prime(n):
        n -= 1
    return n


def next_prime(n: int) -> int:
    """Smallest prime >= n."""
    n = max(2, n)
    while not is_prime(n):
        n += 1
    return n


def _config(family: str, name: str, overrides: Mapping[str, int]) -> dict[str, Any]:
    return {"config_id": f"{family}/{name}", "overrides": dict(sorted(overrides.items()))}


def c2_rules(analysis: ProblemAnalysis) -> list[dict[str, Any]]:
    native = analysis.native_values()
    if not native:
        return []
    lead, inner = analysis.leading, analysis.inner
    assert lead is not None and inner is not None
    return [
        _config("c2", "S-half", {lead: max(1, native[lead] // 2)}),
        _config("c2", "S-double", {inner: 2 * native[inner]}),
        _config("c2", "S-small", {root: max(1, d // 8) for root, d in native.items()}),
    ]


def c3_rules(analysis: ProblemAnalysis) -> list[dict[str, Any]]:
    native = analysis.native_values()
    if not native:
        return []
    configs = []
    for root, d in native.items():
        configs.append(_config("c3", f"U1/{root}", {root: d + 1}))
        configs.append(_config("c3", f"U2/{root}", {root: (d - d % 128) + 17}))
    assert analysis.leading is not None
    configs.append(_config("c3", "U3", {analysis.leading: 3}))
    if analysis.is_matmul:
        configs.append(_config("c3", "MM1", {r: (d - d % 64) + 1 for r, d in native.items()}))
        configs.append(_config("c3", "MM17", {r: (d - d % 64) + 17 for r, d in native.items()}))
    return configs


def a3_rules(analysis: ProblemAnalysis, c_values: Mapping[str, set[int]]) -> list[dict[str, Any]]:
    native = analysis.native_values()
    if not native:
        return []
    lead, inner = analysis.leading, analysis.inner
    assert lead is not None and inner is not None

    def up(root: str, value: int) -> int:
        value = value if value == 1 and 1 not in c_values.get(root, set()) else next_prime(value)
        while value in c_values.get(root, set()) or value == native[root]:
            value = next_prime(value + 1)
        return value

    def down(root: str, d: int) -> int:
        value = prev_prime(max(2, round(0.37 * d)))
        while (value in c_values.get(root, set()) or value == native[root]) and value > 2:
            value = prev_prime(value - 1)
        return value

    def grow(root: str, d: int) -> int:
        value = next_prime(max(2, round(1.37 * d)))
        while value in c_values.get(root, set()) or value == native[root]:
            value = next_prime(value + 1)
        return value

    return [
        _config("A3", "lead1", {lead: up(lead, 1)}),
        _config("A3", "lead5", {lead: up(lead, 5)}),
        _config("A3", "inner37", {inner: down(inner, native[inner])}),
        _config("A3", "inner137", {inner: grow(inner, native[inner])}),
        _config("A3", "allprime", {root: down(root, d) for root, d in native.items()}),
    ]


def build_problem_manifest(
    analysis: ProblemAnalysis,
    *,
    problem_sha256: str,
    input_bytes: Callable[[Mapping[str, int]], int],
    describe: Callable[[Mapping[str, int]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply the rules to one problem.

    ``input_bytes(overrides)`` returns the total input bytes with the given
    overrides (computed on the meta device by the build script).
    ``describe(overrides)`` optionally returns extra per-config facts
    (input shapes); both receive ``{}`` for the native shape.
    """
    native_values = analysis.native_values()
    native_bytes = input_bytes({})
    cap = int(BYTE_CAP * native_bytes)
    kept: dict[str, list[dict[str, Any]]] = {"c2": [], "c3": [], "A3": []}
    excluded: list[dict[str, Any]] = []
    seen_vectors: set[tuple[tuple[str, int], ...]] = {tuple(sorted(native_values.items()))}

    def vector(overrides: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
        merged = dict(native_values)
        merged.update(overrides)
        return tuple(sorted(merged.items()))

    def admit(family: str, config: dict[str, Any]) -> None:
        overrides = config["overrides"]
        key = vector(overrides)
        if key in seen_vectors:
            excluded.append({**config, "reason": "duplicates native or an earlier config"})
            return
        size = input_bytes(overrides)
        if size > cap:
            excluded.append({**config, "reason": f"input bytes {size} exceed 2x native"})
            return
        seen_vectors.add(key)
        entry = {**config, "input_bytes": size}
        if describe is not None:
            entry.update(describe(overrides))
        kept[family].append(entry)

    for config in c2_rules(analysis):
        if config["config_id"] == "c2/S-double":
            config = _fit_double(config, analysis, input_bytes, cap)
        admit("c2", config)
    for config in c3_rules(analysis):
        admit("c3", config)
    c_values: dict[str, set[int]] = {}
    for config in kept["c2"] + kept["c3"]:
        for root, value in config["overrides"].items():
            c_values.setdefault(root, set()).add(value)
    for config in a3_rules(analysis, c_values):
        if config["config_id"] == "A3/inner137":
            config = _fit_prime_up(config, analysis, input_bytes, cap, c_values)
        admit("A3", config)
    return {
        "problem_sha256": problem_sha256,
        "free_roots": list(analysis.free_roots),
        "leading": analysis.leading,
        "inner": analysis.inner,
        "init_bound": sorted(analysis.init_bound),
        "model_bound": sorted(analysis.model_bound),
        "is_matmul": analysis.is_matmul,
        "notes": list(analysis.notes),
        "native": {
            "values": native_values,
            "input_bytes": native_bytes,
            **(describe({}) if describe is not None else {}),
        },
        "c2": kept["c2"],
        "c3": kept["c3"],
        "A3": kept["A3"],
        "excluded": excluded,
    }


def _fit_double(
    config: dict[str, Any],
    analysis: ProblemAnalysis,
    input_bytes: Callable[[Mapping[str, int]], int],
    cap: int,
) -> dict[str, Any]:
    ((root, doubled),) = config["overrides"].items()
    native = analysis.native_values()[root]
    if input_bytes({root: doubled}) <= cap:
        return config
    low, high = native, doubled  # largest value in [native, doubled] within the cap
    while low < high:
        mid = (low + high + 1) // 2
        if input_bytes({root: mid}) <= cap:
            low = mid
        else:
            high = mid - 1
    return {**config, "overrides": {root: low}, "capped_from": doubled}


def _fit_prime_up(
    config: dict[str, Any],
    analysis: ProblemAnalysis,
    input_bytes: Callable[[Mapping[str, int]], int],
    cap: int,
    c_values: Mapping[str, set[int]],
) -> dict[str, Any]:
    """Largest prime above native (and below the requested one) within the byte cap."""
    ((root, wanted),) = config["overrides"].items()
    native = analysis.native_values()[root]
    if input_bytes({root: wanted}) <= cap:
        return config
    value = prev_prime(wanted - 1)
    while value > native and (
        input_bytes({root: value}) > cap or value in c_values.get(root, set())
    ):
        value = prev_prime(value - 1)
    if value <= native:
        return {**config, "overrides": {root: native}, "capped_from": wanted}
    return {**config, "overrides": {root: value}, "capped_from": wanted}


def config_index(manifest_entry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Map config ids (``c2/S-half`` ...) to their manifest entries."""
    index: dict[str, dict[str, Any]] = {}
    for family in ("c2", "c3", "A3"):
        for config in manifest_entry.get(family, []):
            index[config["config_id"]] = dict(config)
    return index
