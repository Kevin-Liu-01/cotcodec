#!/usr/bin/env python3
"""Build (or check) the Q1 problem memory table for the memory-aware execution policy.

CPU only, on the meta device (no tensor memory is allocated and no kernel runs):
for every vendored KernelBench problem, the bytes of the reference model's
parameters and buffers, and for the native ``get_inputs()`` and every c2, c3 and
A3 configuration of the committed shape manifest the input bytes, the output
bytes and the largest single tensor any aten op produced during the reference
forward (``max_activation_bytes``). ``harness.q1.memory`` turns these into an
estimated peak of GPU memory per item and the capacity units an item holds
(execution policy ``q1-stage0-exec/2``, preregistration section 18.9).

The table is execution data, not gate data: it lives beside ``memory.py``
(``harness/q1/memory_table.json``, in ``driver_sha256``), never under
``harness/q1/data``.

    python scripts/q1_memory_table.py --write
    python scripts/q1_memory_table.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import memory, problems  # noqa: E402
from harness.q1.schema import sha256_file  # noqa: E402

GENERATOR_FILES = (
    "harness/q1/problems.py",
    "harness/q1/data/shape_manifest.json",
    "scripts/q1_memory_table.py",
)


def _tensors(value: Any) -> list[Any]:
    import torch

    if isinstance(value, torch.Tensor):
        return [value]
    if isinstance(value, list | tuple):
        return [t for item in value for t in _tensors(item)]
    return []


def _nbytes(values: Any) -> int:
    return sum(int(t.numel()) * int(t.element_size()) for t in _tensors(values))


def meta_facts(source: str) -> dict[str, Any]:
    """Parameter, input, output and largest-activation bytes of one problem source."""
    import torch
    from torch.utils._python_dispatch import TorchDispatchMode

    class Largest(TorchDispatchMode):
        def __init__(self) -> None:
            super().__init__()
            self.largest = 0

        def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
            out = func(*args, **(kwargs or {}))
            self.largest = max(self.largest, _nbytes(out))
            return out

    context = problems.exec_problem(source)
    with torch.device("meta"):
        torch.manual_seed(0)
        model = context["Model"](*context["get_init_inputs"]())
        inputs = context["get_inputs"]()
    params = sum(int(p.numel()) * int(p.element_size()) for p in model.parameters())
    params += sum(int(b.numel()) * int(b.element_size()) for b in model.buffers())
    facts: dict[str, Any] = {"params_bytes": params, "input_bytes": _nbytes(inputs)}
    try:
        recorder = Largest()
        with torch.no_grad(), recorder:
            output = model(*inputs)
        facts["output_bytes"] = _nbytes(output)
        facts["max_activation_bytes"] = max(recorder.largest, facts["output_bytes"])
        facts["meta_forward"] = "ok"
    except Exception as exc:  # the reference raises at this shape (advisory)
        facts["output_bytes"] = None
        facts["max_activation_bytes"] = None
        facts["meta_forward"] = f"error: {type(exc).__name__}"
    return facts


def problem_entry(problem_id: str, manifest_entry: dict[str, Any]) -> dict[str, Any]:
    source = problems.load_problem_source(problem_id)
    analysis = problems.analyze_problem(problem_id, source)
    native = meta_facts(source)
    variants: list[dict[str, Any]] = []
    for family in ("c2", "c3", "A3"):
        for config in manifest_entry.get(family, []):
            variant = problems.override_constants(source, analysis, config["overrides"])
            facts = meta_facts(variant)
            variants.append({"config_id": config["config_id"], **facts})

    def largest(key: str) -> int:
        values = [native[key]] + [v[key] for v in variants]
        return max((int(v) for v in values if v is not None), default=0)

    return {
        "params_bytes": native["params_bytes"],
        "native": {
            k: native[k]
            for k in ("input_bytes", "output_bytes", "max_activation_bytes", "meta_forward")
        },
        "all_configs": {
            "input_bytes": largest("input_bytes"),
            "output_bytes": largest("output_bytes"),
            "max_activation_bytes": largest("max_activation_bytes"),
            "configs": 1 + len(variants),
            "meta_forward_errors": sum(1 for v in [native, *variants] if v["meta_forward"] != "ok"),
        },
    }


def build() -> dict[str, Any]:
    import torch

    manifest = json.loads(
        (PROJECT_ROOT / "harness" / "q1" / "data" / "shape_manifest.json").read_text()
    )
    entries = {
        problem_id: problem_entry(problem_id, manifest["problems"].get(problem_id, {}))
        for problem_id in problems.list_problem_ids((1, 2))
    }
    return {
        "schema": memory.TABLE_SCHEMA,
        "torch": torch.__version__.split("+")[0],
        "generator_sha256": {path: sha256_file(PROJECT_ROOT / path) for path in GENERATOR_FILES},
        "problems": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=memory.TABLE_PATH)
    args = parser.parse_args(argv)
    table = build()
    text = json.dumps(table, indent=1, sort_keys=True) + "\n"
    if args.write:
        args.output.write_text(text, encoding="utf-8")
        print(json.dumps({"problems": len(table["problems"])}))
        return 0
    current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
    if current != text:
        print("FAIL: memory table is stale; rebuild with --write", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
