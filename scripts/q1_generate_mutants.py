#!/usr/bin/env python3
"""Generate the Q1 mutant corpus and hack-emulating controls.

Steps (each refuses to overwrite its output):

``pool``      enumerate distinct CPU-side mutants of every substrate
``compile``   compile parents and candidates at recorded specializations
              (run inside a GPU-less container; needs Triton)
``select``    compile filter, family-stratified cap, frozen split, mutant layout
``controls``  hack-emulating wrapper controls (needs a KernelBench checkout)
``table``     print the operator registry or the KernelBench-M rule mapping

Typical run::

    uv run python scripts/q1_generate_mutants.py pool \
        --substrates-root data/q1/substrates --pool-root data/q1/pool
    # in a GPU-less container with the research image:
    python scripts/q1_generate_mutants.py compile \
        --pool-root data/q1/pool --specializations-root data/q1/specializations
    uv run python scripts/q1_generate_mutants.py select --pool-root data/q1/pool \
        --substrates-root data/q1/substrates --out-root data/q1/mutants \
        --controls-root data/q1/controls-mutants --seed 42 --cap 40
    uv run python scripts/q1_generate_mutants.py controls \
        --substrates-root data/q1/substrates --kernelbench-root ~/src/KernelBench \
        --out-root data/q1/controls-hacks

Exit codes: 0 success, 2 bad input or refused overwrite, 3 internal failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1.mutate import corpus  # noqa: E402
from harness.q1.mutate.engine import OperatorFailure  # noqa: E402
from harness.q1.mutate.operators import registry_table  # noqa: E402
from harness.q1.mutate.rules import mapping_markdown  # noqa: E402
from harness.q1.mutate.sampling import DEFAULT_CAP, DEFAULT_SEED  # noqa: E402
from harness.q1.mutate.source import SourceError  # noqa: E402
from harness.q1.schema import SchemaError  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pool = sub.add_parser("pool", help="enumerate distinct CPU-side mutants")
    pool.add_argument("--substrates-root", type=Path, required=True)
    pool.add_argument("--pool-root", type=Path, required=True)

    comp = sub.add_parser("compile", help="compile filter (GPU-less container, Triton)")
    comp.add_argument("--pool-root", type=Path, required=True)
    comp.add_argument("--specializations-root", type=Path, required=True)
    comp.add_argument("--workers", type=int, default=8)
    comp.add_argument("--timeout-s", type=int, default=3600)

    sel = sub.add_parser("select", help="cap, split and write the mutant layout")
    sel.add_argument("--pool-root", type=Path, required=True)
    sel.add_argument("--substrates-root", type=Path, required=True)
    sel.add_argument("--out-root", type=Path, required=True)
    sel.add_argument("--controls-root", type=Path)
    sel.add_argument("--seed", type=int, default=DEFAULT_SEED)
    sel.add_argument("--cap", type=int, default=DEFAULT_CAP)
    sel.add_argument(
        "--no-require-compile",
        action="store_true",
        help="allow a CPU-only preview without compile.jsonl (manifest records it)",
    )

    ctl = sub.add_parser("controls", help="hack-emulating wrapper controls")
    ctl.add_argument("--substrates-root", type=Path, required=True)
    ctl.add_argument("--kernelbench-root", type=Path, required=True)
    ctl.add_argument("--out-root", type=Path, required=True)
    ctl.add_argument("--kind", action="append", dest="kinds")

    table = sub.add_parser("table", help="print the operator table or the rule mapping")
    table.add_argument("which", choices=("operators", "rules"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "pool":
            result = corpus.build_pool(args.substrates_root, args.pool_root)
            print(
                json.dumps(
                    {"n_candidates": result["n_candidates"], "pool_sha256": result["pool_sha256"]}
                )
            )
        elif args.command == "compile":
            out = corpus.compile_pool(
                args.pool_root,
                args.specializations_root,
                workers=args.workers,
                timeout_s=args.timeout_s,
            )
            print(json.dumps({"compile_jsonl": str(out)}))
        elif args.command == "select":
            result = corpus.select(
                args.pool_root,
                args.substrates_root,
                args.out_root,
                seed=args.seed,
                cap=args.cap,
                require_compile=not args.no_require_compile,
                controls_root=args.controls_root,
            )
            print(json.dumps(result["totals"], sort_keys=True))
        elif args.command == "controls":
            result = corpus.build_controls(
                args.substrates_root, args.kernelbench_root, args.out_root, kinds=args.kinds
            )
            print(
                json.dumps({"controls": len(result["controls"]), "skipped": len(result["skipped"])})
            )
        else:
            if args.which == "operators":
                print(json.dumps(registry_table(), indent=1))
            else:
                print(mapping_markdown())
    except (corpus.CorpusError, SchemaError, SourceError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OperatorFailure as exc:
        print(f"internal error: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
