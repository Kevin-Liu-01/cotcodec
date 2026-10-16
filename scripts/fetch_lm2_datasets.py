#!/usr/bin/env python3
"""LM2 (D129): fetch the evaluation sets at pinned revisions and normalize them, with a receipt.

Runs on the H100 host in a CPU-only Slurm job (no GRES), never in a GPU job. Every file is
downloaded from the Hugging Face Hub at a pinned dataset revision, checked against the LFS
SHA-256 (or the byte size for small non-LFS files) recorded below, and kept as downloaded. The
normalized JSONL files the evaluation reads are derived from them and hashed into the receipt.
Item text stays on the host; the repository gets only this script, ids and digests.

LiveCodeBench stores its private tests as base64(zlib(pickle(json string))). They are decoded with
an unpickler that refuses every global, so only plain strings, numbers and containers load; no
code from the file can run.

Usage (on the host, in the CPU job):
    python scripts/fetch_lm2_datasets.py fetch --out <dir>
Needs pyarrow for the MathArena parquet files (the job provides it in an ephemeral uv env).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import pickle
import sys
import time
import urllib.request
import zlib
from pathlib import Path
from typing import Any

HUB = "https://huggingface.co/datasets"

# Pinned sources. sha256 is the Hub's LFS oid of the file at that revision (read from the Hub API
# with ?blobs=true on 2026-10-16); licence and dates as the dataset cards state them.
SOURCES: list[dict[str, Any]] = [
    {
        "name": "aime_2026",
        "repo": "MathArena/aime_2026",
        "revision": "d2de22f3c656b4f56cf8981212186377d1e23bc3",
        "path": "data/train-00000-of-00001.parquet",
        "sha256": "d91db799651b4cc1f0734f52792a695c9cc60dac342524b3d8e5b2ff31c3e957",
        "bytes": 10065,
        "license": "cc-by-nc-sa-4.0",
        "kind": "math",
    },
    {
        "name": "hmmt_feb_2026",
        "repo": "MathArena/hmmt_feb_2026",
        "revision": "02fba4f74d8e68e73e66a02d540fd979c05c274c",
        "path": "data/train-00000-of-00001.parquet",
        "sha256": "e5fcff6b1c2262841c0c37bf6d7b42529f284528d5f0d5c45c52e8bf0654a916",
        "bytes": 9984,
        "license": "cc-by-nc-sa-4.0",
        "kind": "math",
    },
    {
        "name": "arxivmath_0626",
        "repo": "MathArena/arxivmath-0626",
        "revision": "dca0d771ab20c1b8e8c50d0921bf693f7bfe663d",
        "path": "data/train-00000-of-00001.parquet",
        "sha256": "67e038c57192b6c2aaf5131d6877ce82684551ae44282c17c3906cef68de7446",
        "bytes": 22770,
        "license": "cc-by-sa-4.0",
        "kind": "math",
    },
    {
        "name": "arxivmath_0826",
        "repo": "MathArena/arxivmath-0826",
        "revision": "977a3a0083198e11ac4f20fe79288351cebd6281",
        "path": "data/train-00000-of-00001.parquet",
        "sha256": "a635931866406bbe7eb5cee8a4e47e188634b3c25b0b0b83dc06d36435e75609",
        "bytes": 55180,
        "license": "cc-by-sa-4.0",
        "kind": "math",
    },
    {
        "name": "lcb_v6",
        "repo": "livecodebench/code_generation_lite",
        "revision": "0fe84c3912ea0c4d4a78037083943e8f0c4dd505",
        "path": "test6.jsonl",
        "sha256": "bb4c364f71921c4495a6ad15abe1a927350b720009f4933e2e71f8af0f6fd1f5",
        "bytes": 134303240,
        "license": "cc (dataset card); problems from LeetCode, AtCoder and Codeforces",
        "kind": "code",
    },
    {
        "name": "supergpqa",
        "repo": "m-a-p/SuperGPQA",
        "revision": "4430d4458112c7d4497fdcf94d7cc223313d6acf",
        "path": "SuperGPQA-all.jsonl",
        "sha256": "28b998e70205ee95e540317b5adc06a06552a3961fb50b153df126b833f7a910",
        "bytes": 23957124,
        "license": "odc-by",
        "kind": "knowledge",
    },
]


class NoGlobalsUnpickler(pickle.Unpickler):
    """Load only plain data: any class or function reference is refused."""

    def find_class(self, module: str, name: str) -> Any:  # noqa: ARG002
        raise pickle.UnpicklingError(f"global {module}.{name} refused")


def safe_unpickle(data: bytes) -> Any:
    return NoGlobalsUnpickler(io.BytesIO(data)).load()


def decode_lcb_tests(field: str) -> list[dict[str, Any]]:
    """Decode a LiveCodeBench test field: plain JSON, or base64(zlib(pickle(json string)))."""

    try:
        value = json.loads(field)
    except json.JSONDecodeError:
        raw = zlib.decompress(base64.b64decode(field.encode("utf-8")))
        loaded = safe_unpickle(raw)
        if not isinstance(loaded, str):
            raise ValueError("decoded LiveCodeBench tests are not a JSON string") from None
        value = json.loads(loaded)
    if not isinstance(value, list):
        raise ValueError("LiveCodeBench tests must be a list")
    tests = []
    for test in value:
        if not isinstance(test, dict) or not {"input", "output", "testtype"} <= set(test):
            raise ValueError("malformed LiveCodeBench test")
        tests.append(
            {
                "input": str(test["input"]),
                "output": str(test["output"]),
                "testtype": test["testtype"],
            }
        )
    return tests


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(source: dict[str, Any], dest: Path) -> dict[str, Any]:
    url = f"{HUB}/{source['repo']}/resolve/{source['revision']}/{source['path']}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or sha256_file(dest) != source["sha256"]:
        tmp = dest.with_suffix(dest.suffix + ".part")
        request = urllib.request.Request(url, headers={"User-Agent": "cotcodec-lm2-fetch"})
        with urllib.request.urlopen(request, timeout=600) as response, tmp.open("wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
        tmp.rename(dest)
    size = dest.stat().st_size
    digest = sha256_file(dest)
    if size != source["bytes"] or digest != source["sha256"]:
        raise SystemExit(f"{source['name']}: got {size} bytes, sha256 {digest}; expected pinned")
    return {"url": url, "bytes": size, "sha256": digest}


def read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq  # provided by the CPU job's ephemeral env

    return pq.read_table(path).to_pylist()


def normalize_math(name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for row in rows:
        idx = int(row["problem_idx"])
        items.append(
            {
                "id": f"{name}/{idx}",
                "source": name,
                "problem_idx": idx,
                "problem": str(row["problem"]),
                "answer": str(row["answer"]),
                "problem_type": row.get("problem_type"),
            }
        )
    return sorted(items, key=lambda item: item["problem_idx"])


def normalize_lcb(path: Path) -> list[dict[str, Any]]:
    items = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            metadata = json.loads(row.get("metadata") or "{}")
            public = decode_lcb_tests(row["public_test_cases"])
            private = decode_lcb_tests(row["private_test_cases"])
            types = {test["testtype"] for test in public + private}
            if len(types) != 1 or not types <= {"stdin", "functional"}:
                raise ValueError(f"{row['question_id']}: mixed or unknown test types {types}")
            items.append(
                {
                    "id": f"lcb_v6/{row['question_id']}",
                    "source": "lcb_v6",
                    "question_id": str(row["question_id"]),
                    "platform": row["platform"],
                    "contest_id": row.get("contest_id"),
                    "contest_date": row["contest_date"],
                    "difficulty": row["difficulty"],
                    "question_title": row.get("question_title"),
                    "question_content": row["question_content"],
                    "starter_code": row.get("starter_code") or "",
                    "func_name": metadata.get("func_name"),
                    "testtype": types.pop(),
                    "public_tests": public,
                    "tests": public + private,
                }
            )
    return sorted(items, key=lambda item: (item["contest_date"], item["question_id"]))


def normalize_supergpqa(path: Path) -> list[dict[str, Any]]:
    items = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            items.append(
                {
                    "id": f"supergpqa/{row['uuid']}",
                    "source": "supergpqa",
                    "question": row["question"],
                    "options": row["options"],
                    "answer_letter": row["answer_letter"],
                    "discipline": row.get("discipline"),
                    "field": row.get("field"),
                    "subfield": row.get("subfield"),
                    "difficulty": row.get("difficulty"),
                    "is_calculation": row.get("is_calculation"),
                }
            )
    return sorted(items, key=lambda item: item["id"])


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return {"file": path.name, "rows": len(rows), "sha256": sha256_file(path)}


def fetch(out: Path) -> dict[str, Any]:
    raw_dir = out / "raw"
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "experiment": "lm2-resident-eval",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": [],
        "normalized": {},
    }
    math_items: list[dict[str, Any]] = []
    code_items: list[dict[str, Any]] = []
    knowledge_items: list[dict[str, Any]] = []
    for source in SOURCES:
        dest = raw_dir / source["name"] / Path(source["path"]).name
        got = download(source, dest)
        receipt["sources"].append({**source, **got})
        if source["kind"] == "math":
            math_items += normalize_math(source["name"], read_parquet_rows(dest))
        elif source["kind"] == "code":
            code_items += normalize_lcb(dest)
        else:
            knowledge_items += normalize_supergpqa(dest)
    receipt["normalized"]["math"] = write_jsonl(out / "math.jsonl", math_items)
    receipt["normalized"]["code"] = write_jsonl(out / "code.jsonl", code_items)
    receipt["normalized"]["knowledge"] = write_jsonl(out / "knowledge.jsonl", knowledge_items)
    counts: dict[str, int] = {}
    for item in math_items + code_items:
        counts[item["source"]] = counts.get(item["source"], 0) + 1
    receipt["counts"] = counts
    receipt["counts"]["supergpqa"] = len(knowledge_items)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fetch")
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    receipt = fetch(args.out)
    print(json.dumps({"counts": receipt["counts"], "normalized": receipt["normalized"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
