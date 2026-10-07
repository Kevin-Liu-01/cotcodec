#!/usr/bin/env python3
"""Zero-GPU priors for Q1: reanalyse lethe's released per-row audit verdicts.

Inputs (both MIT, read from local copies; nothing is executed):

- ``results/audit_rows.jsonl.gz`` from ``RishiShah99/lethe@eaff0bb6``: one row
  per Dr. Kernel cold-start kernel with lethe's gate statuses;
- ``drkernel-coldstart-8k.parquet`` from ``hkust-nlp/drkernel-coldstart-8k@cba0ef06``:
  the reference PyTorch code (``original_python_code``) and ``final_speedup``
  for each ``uuid``; lethe's row ``id`` is that ``uuid``.

Outputs a JSON summary: per-gate and per-op-class failure rates with
Clopper-Pearson 95% intervals, the CMP-01-or-CMP-03 union the reviewed plan
quotes, the same after excluding problems whose semantics change under
``.eval()`` (BatchNorm, Dropout, ``self.training``, running-stat
InstanceNorm; lethe's adapter calls ``.eval()``, KernelBench does not), and
the subset with ``final_speedup > 0`` (a proxy for KernelGYM acceptance).

    uv run --with pyarrow==21.0.0 --with scipy python scripts/q1_lethe_priors.py \\
        --rows lethe/results/audit_rows.jsonl.gz \\
        --coldstart drkernel-coldstart-8k.parquet --output priors.json
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

LETHE_REVISION = "eaff0bb6bd6d3a1c510fa7b4708ceb0f07a5ac9e"
COLDSTART_REVISION = "cba0ef06a5b1e3c307b7acfa8b6acb7a46578105"
EVAL_SENSITIVE = re.compile(
    r"BatchNorm|Dropout|self\.training|track_running_stats\s*=\s*True|"
    r"functional\.dropout|F\.dropout|batch_norm\(|AlphaDropout"
)
CHANNELS = (
    "CMP-01",
    "CMP-03",
    "ORD-01",
    "ORD-02",
    "ORD-03",
    "PRC-01",
    "PRC-02",
    "EXC-01",
    "EXC-02",
    "RES-01",
)


def clopper_pearson(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    from scipy.stats import beta

    if n == 0:
        return (0.0, 1.0)
    alpha = 1 - level
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def rate(k: int, n: int) -> dict[str, Any]:
    lo, hi = clopper_pearson(k, n)
    return {"k": k, "n": n, "rate": (k / n) if n else None, "ci95": [lo, hi]}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gated = [r for r in rows if r["status"] == "gated"]
    n = len(gated)

    def fails(row: dict[str, Any], gate: str) -> bool:
        return row["gates"].get(gate, {}).get("status") == "fail"

    union = sum(fails(r, "CMP-01") or fails(r, "CMP-03") for r in gated)
    tolerance_free = sum(
        fails(r, "EXC-01") or fails(r, "ORD-02") or bool(r.get("output_aliasing")) for r in gated
    )
    by_class: dict[str, Any] = {}
    for op_class in sorted({r.get("op_class") for r in gated}):
        subset = [r for r in gated if r.get("op_class") == op_class]
        by_class[str(op_class)] = {
            "cmp01_or_cmp03": rate(
                sum(fails(r, "CMP-01") or fails(r, "CMP-03") for r in subset), len(subset)
            ),
            "any_channel": rate(
                sum(any(fails(r, g) for g in CHANNELS) for r in subset), len(subset)
            ),
        }
    return {
        "rows": len(rows),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "gated": n,
        "per_channel_fail": {g: rate(sum(fails(r, g) for r in gated), n) for g in CHANNELS},
        "cmp01_or_cmp03": rate(union, n),
        "tolerance_free_exc01_ord02_aliasing": rate(tolerance_free, n),
        "any_channel": rate(sum(any(fails(r, g) for g in CHANNELS) for r in gated), n),
        "by_op_class": by_class,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--coldstart", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    import pyarrow.parquet as pq

    with gzip.open(args.rows, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    table = pq.read_table(args.coldstart, columns=["uuid", "original_python_code", "final_speedup"])
    references = {
        int(u): (code, speed)
        for u, code, speed in zip(
            table.column("uuid").to_pylist(),
            table.column("original_python_code").to_pylist(),
            table.column("final_speedup").to_pylist(),
            strict=True,
        )
    }
    missing = [r["id"] for r in rows if int(r["id"]) not in references]
    for row in rows:
        code, speed = references.get(int(row["id"]), ("", None))
        row["eval_sensitive"] = bool(EVAL_SENSITIVE.search(code or ""))
        row["final_speedup_dataset"] = speed
    eval_free = [r for r in rows if not r["eval_sensitive"]]
    accepted = [r for r in rows if (r["final_speedup_dataset"] or 0) > 0]
    accepted_eval_free = [r for r in accepted if not r["eval_sensitive"]]
    out = {
        "schema": "q1-lethe-priors/1",
        "sources": {
            "lethe": {
                "repo": "https://github.com/RishiShah99/lethe",
                "revision": LETHE_REVISION,
                "path": "results/audit_rows.jsonl.gz",
                "sha256": sha256(args.rows),
                "bytes": args.rows.stat().st_size,
                "license": "MIT",
            },
            "coldstart": {
                "repo": "https://huggingface.co/datasets/hkust-nlp/drkernel-coldstart-8k",
                "revision": COLDSTART_REVISION,
                "path": "drkernel-coldstart-8k.parquet",
                "sha256": sha256(args.coldstart),
                "bytes": args.coldstart.stat().st_size,
                "license": "MIT",
            },
        },
        "join": {
            "rows_without_reference": len(missing),
            "eval_sensitive_rows": sum(r["eval_sensitive"] for r in rows),
            "eval_sensitive_pattern": EVAL_SENSITIVE.pattern,
        },
        "all_rows": summarize(rows),
        "excluding_eval_sensitive": summarize(eval_free),
        "final_speedup_positive": summarize(accepted),
        "final_speedup_positive_excluding_eval_sensitive": summarize(accepted_eval_free),
        "caveats": [
            "lethe ran on B200 with torch 2.12 / Triton 3.7, not the Q1 H100 stack",
            "lethe perturbs only the first float input and compares in fp32 with "
            "sqrt(numel)-scaled tolerances; CMP-01/CMP-03 are not the Q1 audit",
            "the cold-start corpus is teacher-model output, not Dr. Kernel-8B samples",
            "final_speedup > 0 is a proxy for KernelGYM acceptance, not the acceptance flag",
        ],
    }
    args.output.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    head = out["excluding_eval_sensitive"]["cmp01_or_cmp03"]
    print(json.dumps({"all": out["all_rows"]["cmp01_or_cmp03"], "eval_free": head}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
