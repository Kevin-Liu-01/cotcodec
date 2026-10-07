#!/usr/bin/env python3
"""Derive the Q1 pilot corpus from the smoke job's outputs (CPU, GPU-less container).

Input: the smoke job's output directory (``run_q1_gpu_pilot.py --job smoke``),
read-only: the admitted pilot substrates, their recorded specializations, the
hack-emulating and core controls, the selection record and the admission rows.

Steps (the mutator's own commands, in order): ``pool`` (CPU-distinct mutants of
every pilot evaluation substrate), ``compile`` (the compile filter at the
recorded specializations, ``TRITON_DISABLE_LINE_INFO=1``, sm_90, in this
GPU-less container), ``select`` (cap 40 per substrate, cap seed 42, content-hash
dev/test split, hack-emulating mutant controls), then ``corpus_recipe.json``:
every kernel directory with the SHA-256 of each file, every mutant's recipe
(operator, site, dedup hash, family, weight) and the hashes of the pool,
compile filter and selection manifests. The recipe holds hashes only, so it can
be committed; the corpus itself reaches the pilot job as a study artifact.

    python scripts/q1_prepare_pilot_corpus.py --smoke-out S --work W [--workers 32]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1.mutate import corpus as mutate_corpus  # noqa: E402
from harness.q1.schema import iter_kernel_dirs, sha256_file  # noqa: E402

RECIPE_SCHEMA = "q1-pilot-corpus-recipe/1"
COPIED = (
    "pilot-substrates",
    "pilot-calibration",
    "specializations",
    "controls-hacks",
    "controls-core",
    "pilot_selection.json",
    "corpus_manifest.json",
)


def _files(directory: Path) -> list[dict[str, str]]:
    return [
        {"path": p.relative_to(directory).as_posix(), "sha256": sha256_file(p)}
        for p in sorted(directory.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    ]


def recipe(corpus: Path, pool: Path) -> dict[str, Any]:
    kernels = []
    for folder in (
        "pilot-substrates",
        "pilot-calibration",
        "mutants",
        "controls-hacks",
        "controls-mutants",
        "controls-core",
    ):
        if not (corpus / folder).is_dir():
            continue
        for kernel in iter_kernel_dirs(corpus / folder):
            entry: dict[str, Any] = {
                "folder": folder,
                "kernel_id": kernel.kernel_id,
                "kind": kernel.kind,
                "problem_id": kernel.problem_id,
                "files": _files(kernel.path),
            }
            if kernel.mutation:
                entry["mutation"] = {
                    key: kernel.mutation[key]
                    for key in ("parent_substrate_id", "operator", "family", "site", "dedup_hash")
                }
            kernels.append(entry)
    selected = {
        row["mutant_id"]: row
        for row in map(json.loads, (corpus / "mutants" / "mutants.jsonl").read_text().splitlines())
        if row
    }
    for entry in kernels:
        if entry["kernel_id"] in selected:
            row = selected[entry["kernel_id"]]
            entry["selection"] = {k: row[k] for k in ("split", "weight", "rule_origin")}
    body = {
        "schema": RECIPE_SCHEMA,
        "pool_sha256": sha256_file(pool / "pool.jsonl"),
        "pool_manifest_sha256": sha256_file(pool / "pool_manifest.json"),
        "compile_sha256": sha256_file(pool / "compile.jsonl")
        if (pool / "compile.jsonl").exists()
        else None,
        "mutants_manifest_sha256": sha256_file(corpus / "mutants" / "manifest.json"),
        "selection_sha256": sha256_file(corpus / "pilot_selection.json"),
        "specializations": _files(corpus / "specializations"),
        "kernels": kernels,
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return {**body, "recipe_sha256": digest}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--smoke-out", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--compile-batch-size", type=int, default=1)
    parser.add_argument("--cap", type=int, default=40)
    parser.add_argument("--cap-seed", type=int, default=42)
    parser.add_argument("--no-require-compile", action="store_true", help="CPU preview only")
    args = parser.parse_args(argv)
    corpus, pool = args.work / "corpus", args.work / "pool"
    if args.work.exists():
        print(f"error: {args.work} exists", file=sys.stderr)
        return 2
    corpus.mkdir(parents=True)
    for name in COPIED:
        source = args.smoke_out / name
        if source.is_dir():
            shutil.copytree(source, corpus / name)
        elif source.is_file():
            shutil.copyfile(source, corpus / name)
        else:
            print(f"error: {source} is missing", file=sys.stderr)
            return 2
    hook = args.smoke_out / "substrates-built" / "admission_hook.jsonl"
    if hook.exists():
        shutil.copyfile(hook, corpus / "admission_hook.jsonl")
    pool_manifest = mutate_corpus.build_pool(corpus / "pilot-substrates", pool)
    print(json.dumps({"pool": pool_manifest["n_candidates"]}), flush=True)
    if not args.no_require_compile:
        mutate_corpus.compile_pool(
            pool,
            corpus / "specializations",
            workers=args.workers,
            batch_size=args.compile_batch_size,
        )
    result = mutate_corpus.select(
        pool,
        corpus / "pilot-substrates",
        corpus / "mutants",
        seed=args.cap_seed,
        cap=args.cap,
        require_compile=not args.no_require_compile,
        controls_root=corpus / "controls-mutants",
    )
    shutil.copyfile(pool / "pool_manifest.json", corpus / "pool_manifest.json")
    if (pool / "compile.jsonl").exists():
        shutil.copyfile(pool / "compile.jsonl", corpus / "compile.jsonl")
    record = recipe(corpus, pool)
    (corpus / "corpus_recipe.json").write_text(json.dumps(record, indent=1, sort_keys=True))
    print(
        json.dumps(
            {
                "selected": result["totals"],
                "recipe_sha256": record["recipe_sha256"],
                "kernels": len(record["kernels"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
