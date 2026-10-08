"""Memory-aware execution policy ``q1-stage0-exec/2`` (preregistration section 18.9).

Pure Python (no torch). Execution only: it decides how many items share a GPU,
never which kernels, gates, replicates or buckets are scored, and never a
verdict rule.

Why: ``q1-stage0-trim/2`` item 6 (``q1-stage0-exec/1``) gave an item one of a
GPU's 12 capacity units below 0.6 GB of *native input* bytes, 3 from 0.6 to
1 GB and all 12 from 1 GB. The D31 re-pilot (Slurm 713) showed that native
inputs miss what fills the GPU: on L2/59 (4.3 GB of parameters, 0.017 GB of
inputs), L2/100 (3.5 GB output) and L2/87 (2.1 GB output) 97 items met a CUDA
out-of-memory error at 12 per GPU.

The rule: an item's **estimated peak** of GPU memory is

    context + k_params x P + k_inputs x I + k_activation x A + k_output x O + R

with ``P`` the reference model's parameter and buffer bytes, ``I``, ``O`` and
``A`` the input, output and largest single-activation bytes (meta device,
``harness/q1/memory_table.json``, built by ``scripts/q1_memory_table.py``) and
``R`` the fp64 reduction scratch (``gates.reductions``: at most one fp64 chunk
pair and its temporaries). Each gate has a **profile**:

- ``variants-fp64`` (gate c, A1, A2, A3, the audit-hole replay and their
  reference items): sizes are the largest over the native draw and every c2,
  c3 and A3 configuration; gate (c)'s validity gate and the audit's
  ``oracle.build_reference`` hold the reference, the candidate, an fp64 copy of
  the reference and a temporary fp32 copy (``5 P``), the inputs and their fp64
  copies (``3 I``), two live fp64 activations during the oracle forward
  (``4 A``), and the fp64 oracle output with the fp32, TF32 and candidate
  outputs (``4 O``);
- ``native-fp32`` (the gate (a) variants, b1, b2, A4, A4 poison, A5 and its
  reference item, timing): native sizes; reference, candidate and one more
  model copy (A5's rounded reference, A4's reruns; ``4 P``), ``2 I``, ``2 A``,
  ``3 O``;
- ``variants-fp32`` (A4 sanitizer, which runs at a held-out shape): the
  ``native-fp32`` coefficients on the largest sizes.

Any other gate (fidelity gates) takes ``variants-fp64``. When a measured peak
exists (``measured``: ``{"problem|gate": bytes}`` or ``{"problem": bytes}``, e.g.
``measured_peaks`` over the runner's ``memory.jsonl`` from an earlier job), it
replaces the estimate: ``measured x (1 + measured_margin) + context``.

An item then holds ``ceil(peak / unit_bytes)`` capacity units, where
``unit_bytes = device_bytes x usable_fraction / slot_capacity``, never fewer
than ``q1-stage0-exec/1`` gave it (1 below 0.6 GB of native inputs, 3 from 0.6
to 1 GB, all 12 from 1 GB) and never more than ``slot_capacity`` (alone). The
items per GPU of a problem and gate are therefore ``floor(slot_capacity /
units)``, chosen from its memory, not a fixed 12. The runner also checks the
device's reported memory before an item starts (``runner.MemoryGuard``).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

POLICY_VERSION = "q1-stage0-exec/2"
TABLE_SCHEMA = "q1-memory-table/1"
TABLE_PATH = Path(__file__).resolve().parent / "memory_table.json"

#: The registered policy. ``device_bytes`` is the H100 80GB's memory as torch reports
#: it (79.19 GiB in job 713's out-of-memory messages), rounded down.
POLICY: dict[str, Any] = {
    "name": POLICY_VERSION,
    "device_bytes": 85_000_000_000,
    "usable_fraction": 0.8,
    "slot_capacity": 12,
    "context_bytes": 1_000_000_000,
    "profiles": {
        "variants-fp64": {"sizes": "all_configs", "k": [5, 3, 4, 4]},
        "native-fp32": {"sizes": "native", "k": [4, 2, 2, 3]},
        "variants-fp32": {"sizes": "all_configs", "k": [4, 2, 2, 3]},
    },
    "reduction_bytes_max": 2_500_000_000,
    "reduction_per_activation_byte": 5,
    "measured_margin": 0.25,
    # q1-stage0-exec/1 (trim/2 item 6 as first registered) is the floor.
    "floor_small_below_bytes": 600_000_000,
    "floor_units_small": 1,
    "floor_units_medium": 3,
    "floor_exclusive_from_bytes": 1_000_000_000,
}

#: Gate -> memory profile (``POLICY["profiles"]``); unlisted gates take ``variants-fp64``.
GATE_PROFILES: dict[str, str] = {
    **{g: "variants-fp64" for g in ("c", "A1", "A2", "A3", "audit_hole")},
    **{g: "variants-fp64" for g in ("ref_c", "ref_A1", "ref_A2", "ref_A3")},
    **{
        g: "native-fp32"
        for g in (
            "a",
            "a_1e-3",
            "a_head_1e-4",
            "a_head_1e-2",
            "a_static",
            "b1",
            "b2",
            "A4",
            "A4_poison",
            "A5",
            "ref_A5",
            "timing",
        )
    },
    "A4_sanitizer": "variants-fp32",
}
DEFAULT_PROFILE = "variants-fp64"


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != TABLE_SCHEMA:
        raise ValueError(f"{path}: not a {TABLE_SCHEMA} table")
    return data


def table(path: Path | None = None) -> dict[str, Any]:
    return _load(str(path or TABLE_PATH))


def unit_bytes(policy: Mapping[str, Any] = POLICY) -> float:
    return (
        float(policy["device_bytes"])
        * float(policy["usable_fraction"])
        / int(policy["slot_capacity"])
    )


def budget_bytes(policy: Mapping[str, Any] = POLICY) -> int:
    """Device bytes the runner may commit to item estimates."""
    return int(float(policy["device_bytes"]) * float(policy["usable_fraction"]))


def profile_of(gate: str) -> str:
    return GATE_PROFILES.get(gate, DEFAULT_PROFILE)


def _measured(measured: Mapping[str, float] | None, problem_id: str, gate: str) -> float | None:
    if not measured:
        return None
    for key in (f"{problem_id}|{gate}", problem_id):
        if key in measured:
            return float(measured[key])
    return None


def estimated_peak_bytes(
    problem_id: str,
    gate: str,
    *,
    policy: Mapping[str, Any] = POLICY,
    entries: Mapping[str, Any] | None = None,
    measured: Mapping[str, float] | None = None,
) -> int | None:
    """Estimated peak GPU bytes of one item (``None``: the problem is not in the
    table, so the caller runs it alone)."""
    context = int(policy["context_bytes"])
    seen = _measured(measured, problem_id, gate)
    if seen is not None:
        return int(seen * (1 + float(policy["measured_margin"]))) + context
    entries = entries if entries is not None else table()["problems"]
    entry = entries.get(problem_id)
    if entry is None:
        return None
    profile = policy["profiles"][profile_of(gate)]
    sizes = entry[profile["sizes"]]
    k_params, k_inputs, k_activation, k_output = (int(k) for k in profile["k"])
    params = int(entry["params_bytes"])
    inputs = int(sizes["input_bytes"])
    output = int(sizes["output_bytes"] or 0)
    activation = max(int(sizes["max_activation_bytes"] or 0), output)
    if not activation:  # the reference raised on the meta device: assume input-sized
        output = activation = inputs
    reduction = min(
        int(policy["reduction_bytes_max"]),
        int(policy["reduction_per_activation_byte"]) * activation,
    )
    return (
        context
        + k_params * params
        + k_inputs * inputs
        + k_activation * activation
        + k_output * output
        + reduction
    )


def floor_units(native_input_bytes: int | None, policy: Mapping[str, Any] = POLICY) -> int:
    """Units under ``q1-stage0-exec/1`` (native input bytes only)."""
    capacity = int(policy["slot_capacity"])
    if native_input_bytes is None or native_input_bytes >= int(
        policy["floor_exclusive_from_bytes"]
    ):
        return capacity
    if native_input_bytes < int(policy["floor_small_below_bytes"]):
        return int(policy["floor_units_small"])
    return int(policy["floor_units_medium"])


def units_for(
    problem_id: str,
    gate: str,
    native_input_bytes: int | None,
    *,
    policy: Mapping[str, Any] = POLICY,
    entries: Mapping[str, Any] | None = None,
    measured: Mapping[str, float] | None = None,
) -> int:
    """Capacity units of one item under ``q1-stage0-exec/2``."""
    capacity = int(policy["slot_capacity"])
    floor = floor_units(native_input_bytes, policy)
    peak = estimated_peak_bytes(problem_id, gate, policy=policy, entries=entries, measured=measured)
    if peak is None:
        return capacity
    return max(floor, min(capacity, max(1, math.ceil(peak / unit_bytes(policy)))))


def items_per_gpu(units: int, policy: Mapping[str, Any] = POLICY) -> int:
    return max(1, int(policy["slot_capacity"]) // max(1, int(units)))


def load_measured(path: Path | None) -> dict[str, float] | None:
    """A measured-peak table: ``{"problem|gate" or "problem": peak bytes}``, e.g.
    :func:`measured_peaks` over a previous job's ``memory.jsonl``."""
    if path is None:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(k): float(v) for k, v in data.items()}


def measured_peaks(records: list[Mapping[str, Any]]) -> dict[str, float]:
    """Largest ``peak_reserved_bytes`` per ``problem|gate`` over the runner's memory
    records (``runner``'s ``memory.jsonl``)."""
    out: dict[str, float] = {}
    for record in records:
        problem, gate = record.get("problem_id"), record.get("gate")
        peak = record.get("peak_reserved_bytes")
        if problem and gate and peak is not None:
            key = f"{problem}|{gate}"
            out[key] = max(out.get(key, 0.0), float(peak))
    return out


__all__ = [
    "DEFAULT_PROFILE",
    "GATE_PROFILES",
    "POLICY",
    "POLICY_VERSION",
    "TABLE_PATH",
    "TABLE_SCHEMA",
    "budget_bytes",
    "estimated_peak_bytes",
    "floor_units",
    "items_per_gpu",
    "load_measured",
    "measured_peaks",
    "profile_of",
    "table",
    "unit_bytes",
    "units_for",
]
