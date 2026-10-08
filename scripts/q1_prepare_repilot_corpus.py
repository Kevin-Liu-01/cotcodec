#!/usr/bin/env python3
"""Build the Q1 re-pilot corpus (decision D31; rule ``harness/q1/repilot.py``) on the CPU.

Runs in a GPU-less, network-less container of the Q1 image (the mock-H100
codegen refuses to run when a GPU is visible). Steps:

1. **Problems.** The rule's candidates: S1 calibration-half problems with no S2
   substrate, admitted to the Stage 0 planning corpus's S1-cal set (``--counts``,
   ``calibration_substrates``), below 0.6 GB of native inputs, in five strata by
   level and size, each in ``sha256("q1-repilot/1/" + id)`` order.
2. **Substrates.** For each candidate in order, until each stratum is filled:
   mock-H100 TorchInductor codegen (``q1_build_substrates.py s1-codegen``) and
   conversion (``inductor_convert``); a candidate that does not build is replaced
   by the next and listed.
3. **Controls.** The reference-identity control of each chosen problem
   (``harness.q1.controls``; no adversarial control: those live on L1/1, which
   carries evaluation units).
4. **Mutants.** The mutator's CPU-distinct pool of the chosen substrates and
   its capped selection without the compile filter (S1-cal specializations were
   never recorded); per parent, the first selected mutant in
   ``sha256("q1-repilot/1/mutant/" + id)`` order.
5. **Record.** ``repilot_selection.json`` (the rule, the bins, every candidate
   tried) and ``repilot_recipe.json`` (SHA-256 of every file of every kernel
   directory), then the study artifact (``harness/q1/study_artifact.py``) that
   carries the corpus to the GPU job.

    python scripts/q1_prepare_repilot_corpus.py --counts COUNTS.json --work W \\
        --repo-revision SHA [--jobs 8]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import problems, repilot, study_artifact  # noqa: E402
from harness.q1.schema import iter_kernel_dirs, sha256_file  # noqa: E402

RECIPE_SCHEMA = "q1-repilot-corpus-recipe/1"
TREES = ("substrates", "controls", "mutants")


def _files(directory: Path) -> list[dict[str, str]]:
    return [
        {"path": p.relative_to(directory).as_posix(), "sha256": sha256_file(p)}
        for p in sorted(directory.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    ]


def build_one(problem_id: str, work: Path, timeout: int) -> dict[str, Any]:
    """Mock-H100 codegen and conversion of one problem; the substrate directory on success."""
    from harness.q1.substrates import inductor_convert

    records = work / "records"
    records.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "q1_build_substrates.py"),
        "s1-codegen",
        "--kernelbench-root",
        str(problems.PROBLEMS_ROOT),
        "--records-dir",
        str(records),
        "--problems",
        problem_id,
        "--mode",
        "mock-h100",
        "--jobs",
        "1",
        "--timeout",
        str(timeout),
    ]
    run = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 60)
    record_path = records / (problem_id.replace("/", "__") + ".json")
    if run.returncode != 0 or not record_path.exists():
        return {
            "problem_id": problem_id,
            "built": False,
            "reason": "codegen",
            "log": run.stdout[-800:],
        }
    try:
        converted = inductor_convert.convert_record(json.loads(record_path.read_text()))
    except Exception as exc:  # a conversion refusal is a recorded outcome
        return {"problem_id": problem_id, "built": False, "reason": f"convert: {exc}"[:300]}
    out = work / "substrates" / converted.substrate_id
    out.mkdir(parents=True)
    for name, text in converted.files().items():
        (out / name).write_text(text, encoding="utf-8")
    (out / "substrate.json").write_text(
        json.dumps(converted.substrate_json, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"problem_id": problem_id, "built": True, "substrate_id": converted.substrate_id}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--counts", type=Path, required=True, help="Stage 0 planning counts")
    parser.add_argument("--work", type=Path, required=True, help="must not exist yet")
    parser.add_argument("--repo-revision", required=True)
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args(argv)
    if args.work.exists():
        parser.error(f"{args.work} exists; use a fresh directory")
    args.work.mkdir(parents=True)
    from harness.q1 import controls
    from harness.q1.mutate import corpus as mutate_corpus
    from harness.q1.substrates import s2_catalog
    from harness.q1.substrates import split as s1_split

    counts = json.loads(args.counts.read_text(encoding="utf-8"))
    eligible = {
        sid.removeprefix("s1-inductor-").replace("-", "/", 1)
        for sid in counts["calibration_substrates"]
    }
    split = s1_split.calibration_split(problems.list_problem_ids(include_excluded=True), seed=42)
    ordered = repilot.candidates(
        split["calibration"],
        s2_problems={entry.problem_id for entry in s2_catalog.CATALOG},
        eligible=eligible,
        excluded=problems.EXCLUDED_PROBLEMS,
    )
    builds: dict[str, dict[str, Any]] = {}

    def built(problem_id: str) -> bool:
        builds[problem_id] = build_one(problem_id, args.work, args.timeout)
        return bool(builds[problem_id]["built"])

    selection = repilot.pick(ordered, built)
    # Discard substrates built for candidates the rule did not take (none should exist).
    chosen = selection["problems"]
    substrate_ids = [builds[p]["substrate_id"] for p in chosen]
    for directory in (args.work / "substrates").iterdir():
        if directory.name not in substrate_ids:
            shutil.rmtree(directory)
    controls.write_controls(args.work / "controls", identity=chosen, adversarial=())
    mutate_corpus.build_pool(args.work / "substrates", args.work / "pool")
    mutate_corpus.select(
        args.work / "pool",
        args.work / "substrates",
        args.work / "mutants-selected",
        require_compile=False,
    )
    selected = list(iter_kernel_dirs(args.work / "mutants-selected"))
    (args.work / "mutants").mkdir()
    mutants = {}
    for parent in substrate_ids:
        ids = [k.kernel_id for k in selected if k.mutation["parent_substrate_id"] == parent]
        first = repilot.first_mutant(ids)
        mutants[parent] = first
        if first is not None:
            shutil.copytree(args.work / "mutants-selected" / first, args.work / "mutants" / first)
    order = [
        {
            "problem_id": problem_id,
            "native_input_bytes": problems_bytes(problem_id),
            "kernels": [
                substrate_id,
                controls.identity_control_id(problem_id),
                *([mutants[substrate_id]] if mutants[substrate_id] else []),
            ],
        }
        for problem_id, substrate_id in zip(chosen, substrate_ids, strict=True)
    ]
    record = {
        **selection,
        "candidates": ordered,
        "strata_rule": [list(s) for s in repilot.STRATA],
        "builds": builds,
        "order": order,
        "mutants": mutants,
        "repo_revision": args.repo_revision,
    }
    (args.work / "selection").mkdir()
    (args.work / "selection" / "repilot_selection.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    recipe = {
        "schema": RECIPE_SCHEMA,
        "rule": repilot.RULE,
        "repo_revision": args.repo_revision,
        "kernels": [
            {
                "tree": tree,
                "kernel_id": k.kernel_id,
                "kind": k.kind,
                "problem_id": k.problem_id,
                "files": _files(k.path),
                **({"mutation": k.mutation} if k.mutation else {}),
            }
            for tree in TREES
            for k in iter_kernel_dirs(args.work / tree)
        ],
        "selection_sha256": sha256_file(args.work / "selection" / "repilot_selection.json"),
        "pool_manifest_sha256": sha256_file(args.work / "pool" / "pool_manifest.json"),
    }
    (args.work / "repilot_recipe.json").write_text(
        json.dumps(recipe, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    trees = {
        name: study_artifact.dir_tree(
            args.work / name,
            source="q1-repilot-corpus",
            licence="LicenseRef-q1-mixed",
        )
        for name in (*TREES, "selection")
    }
    artifact = args.work / "q1-repilot-inputs.json"
    receipt = study_artifact.write(
        study_artifact.build(trees, repo_revision=args.repo_revision), artifact
    )
    (args.work / "q1-repilot-inputs.receipt.json").write_text(
        json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "problems": chosen,
                "kernels": sum(len(o["kernels"]) for o in order),
                "artifact": str(artifact),
                "artifact_sha256": receipt["sha256"],
                "artifact_bytes": receipt.get("size_bytes"),
            },
            indent=1,
        )
    )
    return 0


def problems_bytes(problem_id: str) -> int | None:
    from harness.q1 import pilot

    return pilot.native_input_bytes(problem_id)


if __name__ == "__main__":
    raise SystemExit(main())
