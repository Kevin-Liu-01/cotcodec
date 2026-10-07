#!/usr/bin/env python3
"""Build (or check) the committed Q1 shape manifest for gate c2/c3 and audit A3.

Runs on CPU only. Input sizes are measured with ``get_inputs()`` on the meta
device, so no tensor memory is allocated. Each config also records whether
``get_init_inputs()`` is unchanged (it must be) and whether the reference
forward runs on the meta device (advisory only; the run-time validity gate is
authoritative).

    python scripts/build_q1_shape_manifest.py --write
    python scripts/build_q1_shape_manifest.py --check
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

from harness.q1 import problems, shapes  # noqa: E402
from harness.q1.schema import KERNELBENCH_PROBLEMS_REVISION, sha256_file  # noqa: E402

MANIFEST_PATH = PROJECT_ROOT / "harness" / "q1" / "data" / "shape_manifest.json"
GENERATOR_FILES = (
    "harness/q1/problems.py",
    "harness/q1/shapes.py",
    "scripts/build_q1_shape_manifest.py",
)


def _meta_forward(source: str) -> str:
    import torch

    try:
        context = problems.exec_problem(source)
        with torch.device("meta"):
            init = context["get_init_inputs"]()
            model = context["Model"](*init)
            inputs = context["get_inputs"]()
            with torch.no_grad():
                model(*inputs)
        return "ok"
    except Exception as exc:  # advisory only
        return f"error: {type(exc).__name__}: {str(exc)[:160]}"


class _ProblemFacts:
    """Memoised meta-device facts for one problem's override variants."""

    def __init__(self, problem_id: str) -> None:
        self.source = problems.load_problem_source(problem_id)
        self.analysis = problems.analyze_problem(problem_id, self.source)
        self.native_init = problems.init_inputs_value(self.source)
        self.cache: dict[tuple[tuple[str, int], ...], dict[str, Any]] = {}

    def summary(self, overrides: dict[str, int]) -> dict[str, Any]:
        key = tuple(sorted(overrides.items()))
        if key not in self.cache:
            variant = problems.override_constants(self.source, self.analysis, overrides)
            facts = problems.meta_input_summary(variant)
            facts["init_inputs_unchanged"] = problems.init_inputs_value(variant) == self.native_init
            facts["meta_forward"] = _meta_forward(variant)
            self.cache[key] = facts
        return self.cache[key]

    def input_bytes(self, overrides: dict[str, int]) -> int:
        return int(self.summary(dict(overrides))["input_bytes"])

    def describe(self, overrides: dict[str, int]) -> dict[str, Any]:
        facts = self.summary(dict(overrides))
        return {
            "input_shapes": facts["input_shapes"],
            "init_inputs_unchanged": facts["init_inputs_unchanged"],
            "meta_forward": facts["meta_forward"],
        }


def build(problem_ids: list[str]) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for problem_id in problem_ids:
        facts = _ProblemFacts(problem_id)
        entry = shapes.build_problem_manifest(
            facts.analysis,
            problem_sha256=problems.problem_hashes()[problem_id],
            input_bytes=facts.input_bytes,
            describe=facts.describe,
        )
        for family in ("c2", "c3", "A3"):
            for config in entry[family]:
                if not config["init_inputs_unchanged"]:
                    raise SystemExit(f"{problem_id} {config['config_id']}: init inputs changed")
        entries[problem_id] = entry
    return {
        "schema": shapes.MANIFEST_SCHEMA,
        "kernelbench_revision": KERNELBENCH_PROBLEMS_REVISION,
        "generator_sha256": {path: sha256_file(PROJECT_ROOT / path) for path in GENERATOR_FILES},
        "excluded_problems": problems.EXCLUDED_PROBLEMS,
        "problems": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args(argv)
    manifest = build(problems.list_problem_ids((1, 2)))
    text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    if args.write:
        args.output.write_text(text, encoding="utf-8")
        counts = {
            family: sum(len(e[family]) for e in manifest["problems"].values())
            for family in ("c2", "c3", "A3")
        }
        print(json.dumps({"problems": len(manifest["problems"]), "configs": counts}))
        return 0
    current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
    if current != text:
        print("FAIL: shape manifest is stale; rebuild with --write", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
