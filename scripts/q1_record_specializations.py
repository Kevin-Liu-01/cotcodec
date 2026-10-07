#!/usr/bin/env python3
"""Record each admitted substrate's native Triton specializations (GPU side).

For every substrate this runs one native forward pass (KernelBench@423217d9
``get_init_inputs``/``get_inputs`` with seed 42, tensors created directly on
the GPU with the problem's dtypes) inside
``harness.q1.mutate.compiled.record_specializations`` and writes
``<out-root>/<substrate_id>/specializations.json``. The mutator's compile
filter then replays those specializations for every mutant on the CPU, in a
GPU-less container, with ``TRITON_DISABLE_LINE_INFO=1``.

Only parent substrates run here (admitted, reviewed code); no mutant is ever
executed by this script. ``--dry-run`` validates the inputs without importing
torch or Triton.

Exit codes: 0 success, 2 bad input or refused overwrite, 3 a substrate failed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1.mutate.corpus import CorpusError, load_substrates, staged_output  # noqa: E402
from harness.q1.schema import SchemaError, problem_relpath  # noqa: E402

NATIVE_SEED = 42


def _problem_path(kernelbench_root: Path | None, problem_id: str) -> Path:
    """A checkout (``<root>/KernelBench/levelN``), a problem tree (``<root>/levelN``),
    or, with no root, the vendored KernelBench@423217d9 file after its hash check."""
    if kernelbench_root is None:
        from harness.q1 import problems

        try:
            problems.load_problem_source(problem_id)  # verifies the pinned SHA-256
        except problems.ProblemError as exc:
            raise CorpusError(str(exc)) from exc
        return problems.problem_path(problem_id)
    relative = problem_relpath(problem_id)
    for candidate in (kernelbench_root / "KernelBench" / relative, kernelbench_root / relative):
        if candidate.is_file():
            return candidate
    return kernelbench_root / "KernelBench" / relative


def _record_one(substrate, problem_path: Path, device: str) -> tuple[list, str]:
    import importlib.util

    import torch
    import triton

    from harness.q1.mutate.compiled import dump_specializations, record_specializations

    def load(path: Path, name: str):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    problem = load(problem_path, f"q1_problem_{substrate.kernel_id.replace('-', '_')}")
    kernel = load(substrate.kernel_path, f"q1_substrate_{substrate.kernel_id.replace('-', '_')}")
    torch.manual_seed(NATIVE_SEED)
    init = problem.get_init_inputs()
    torch.manual_seed(NATIVE_SEED)
    model = kernel.ModelNew(*init).to(device)
    with torch.device(device):
        torch.manual_seed(NATIVE_SEED)
        inputs = problem.get_inputs()
    inputs = [x.to(device) if torch.is_tensor(x) else x for x in inputs]
    with torch.no_grad(), record_specializations() as records:
        model(*inputs)
        torch.cuda.synchronize()
    if not records:
        raise RuntimeError("no Triton kernel was compiled during the native forward pass")
    return records, dump_specializations(records, triton.__version__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--substrates-root", type=Path, required=True)
    parser.add_argument(
        "--kernelbench-root",
        type=Path,
        default=None,
        help="KernelBench checkout or problem tree; default: the vendored, hash-checked problems",
    )
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        substrates = load_substrates(args.substrates_root)
        for sub in substrates:
            path = _problem_path(args.kernelbench_root, sub.problem_id)
            if not path.is_file():
                raise CorpusError(f"{sub.problem_id}: {path} not found")
    except (CorpusError, SchemaError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({"substrates": len(substrates), "dry_run": True}))
        return 0
    # Must be set before Triton is imported (inside _record_one): compiled
    # dedup hashes cubins built without line info.
    os.environ["TRITON_DISABLE_LINE_INFO"] = "1"
    failures = []
    try:
        with staged_output(args.out_root) as staging:
            for sub in substrates:
                try:
                    _, text = _record_one(
                        sub, _problem_path(args.kernelbench_root, sub.problem_id), args.device
                    )
                except Exception as exc:  # noqa: BLE001 - reported, then fail the run
                    failures.append({"substrate_id": sub.kernel_id, "error": repr(exc)[:500]})
                    continue
                target = staging / sub.kernel_id
                target.mkdir()
                (target / "specializations.json").write_text(text + "\n")
            (staging / "record_summary.json").write_text(
                json.dumps(
                    {"recorded": len(substrates) - len(failures), "failures": failures},
                    indent=1,
                    sort_keys=True,
                )
                + "\n"
            )
            if failures:
                raise RuntimeError(f"{len(failures)} substrates failed")
    except CorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"error: {exc}: {failures[:3]}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
