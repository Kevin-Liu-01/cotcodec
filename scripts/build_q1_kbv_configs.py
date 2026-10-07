#!/usr/bin/env python3
"""Extract KernelBench-Verified's per-problem hidden configurations as data.

Reads ``hidden_tests/level{1,2}/<n>_hidden.py`` from an unmodified
``facebookresearch/kernel_bench_verified`` checkout (MIT) and records, for
each problem, the ordered list of distribution labels its
``get_hidden_inputs()`` returns (D1 x1.0, D2 x3.0, D3 x0.01, D4 x-1.0, plus any
problem-specific extra such as L1/100's D5 structured targets), the
configurations KBV filtered out, and each file's SHA-256. Pure stdlib; no code
is executed.

    python scripts/build_q1_kbv_configs.py /path/to/kernel_bench_verified \\
        --output harness/q1/data/kbv_hidden_configs.json
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1.schema import KBV_REVISION  # noqa: E402

FACTORS = {1.0: "D1", 3.0: "D2", 0.01: "D3", -1.0: "D4"}
#: Problem-specific extra configurations Q1 knows how to reproduce.
EXTRAS = {("L1/100_HingeLoss", "D5"): "D5-alternating-targets"}
LABEL_RE = re.compile(r"^\s*#\s*(D\d+):\s*(.*)$")
FILTER_RE = re.compile(r"^\s+(D\d+) \(([^)]*)\): (.*)$")
PROB_RE = re.compile(r"_PROB_PATH = .*KernelBench/level(\d)/([^']+)\.py")


def parse_hidden_test(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = PROB_RE.search(text)
    if not match:
        raise SystemExit(f"{path}: no _PROB_PATH")
    problem_id = f"L{match.group(1)}/{match.group(2)}"
    tree = ast.parse(text)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "get_hidden_inputs"
    )
    lines = text.splitlines()
    body_lines = lines[function.lineno - 1 : function.end_lineno]
    labels = [m.group(1) for line in body_lines if (m := LABEL_RE.match(line))]
    appends = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "append"
    ]
    appends.sort(key=lambda node: (node.lineno, node.col_offset))
    if len(labels) != len(appends):
        raise SystemExit(f"{path}: {len(labels)} labels for {len(appends)} configs")
    configs = []
    for label, call in zip(labels, appends, strict=True):
        arg = call.args[0]
        if isinstance(arg, ast.Call) and getattr(arg.func, "id", "") == "_get_inputs":
            factor_label = "D1"
        elif isinstance(arg, ast.Call) and getattr(arg.func, "id", "") == "_scale":
            factor = ast.literal_eval(arg.args[1])
            factor_label = FACTORS.get(float(factor))
        else:
            factor_label = None
        if factor_label is not None:
            if factor_label != label:
                raise SystemExit(f"{path}: comment {label} disagrees with factor {factor_label}")
            configs.append(label)
            continue
        extra = EXTRAS.get((problem_id, label))
        if extra is None:
            raise SystemExit(f"{path}: unknown extra configuration {label}")
        configs.append(extra)
    filtered = {
        m.group(1): m.group(3).strip() for line in text.splitlines() if (m := FILTER_RE.match(line))
    }
    return {
        "problem_id": problem_id,
        "configs": configs,
        "filtered": filtered,
        "hidden_test_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "hidden_test_path": path.relative_to(path.parents[2]).as_posix(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kbv_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        revision = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", str(args.kbv_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    if revision != KBV_REVISION:
        print(f"FAIL: KBV checkout at {revision}, expected {KBV_REVISION}", file=sys.stderr)
        return 1
    problems: dict[str, object] = {}
    for level in (1, 2):
        for path in sorted((args.kbv_root / "hidden_tests" / f"level{level}").glob("*_hidden.py")):
            entry = parse_hidden_test(path)
            problems[str(entry.pop("problem_id"))] = entry
    out = {
        "schema": "q1-kbv-hidden-configs/1",
        "kbv_repo": "https://github.com/facebookresearch/kernel_bench_verified",
        "kbv_revision": KBV_REVISION,
        "license": "MIT",
        "factors": {label: factor for factor, label in FACTORS.items()},
        "extras": {
            "D5-alternating-targets": (
                "L1/100 only: replace the targets with torch.ones(batch_size) and set every "
                "second entry to -1.0 (KBV hidden_tests/level1/100_hidden.py)"
            )
        },
        "problems": dict(sorted(problems.items())),
    }
    args.output.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"problems": len(problems)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
