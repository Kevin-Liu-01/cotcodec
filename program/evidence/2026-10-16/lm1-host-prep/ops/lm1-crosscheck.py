#!/usr/bin/env python3
"""LM1 host prep: check each lane receipt against the Hub listing of its allowed files.

For each model id: the receipt's file paths equal the Hub listing's (filtered by the entry's
allow_patterns at the pinned revision); every size matches; every LFS file's SHA-256 equals the
Hub's LFS oid; every small (non-LFS) file is re-read from disk, its git blob SHA-1 equals the Hub's
blob id and its SHA-256 equals the receipt's; the artifact root recomputes; the receipt records
the entry's allow_patterns. As kimi-crosscheck.py did for Kimi-K2.6.
Usage: lm1-crosscheck.py <hub-listings.json> <receipt root> <model root> <output.json> <ids...>
"""

import hashlib
import json
import pathlib
import sys


def artifact_root(files):
    encoded = json.dumps(files, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check(model_id, hub, receipt_root, model_root):
    listing = hub[model_id]
    raw = (receipt_root / f"{model_id}.json").read_bytes()
    receipt = json.loads(raw)
    files = {item["path"]: item for item in receipt["files"]}
    hub_files = {item["path"]: item for item in listing["files"]}
    result = {
        "model_id": model_id,
        "receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "revision_matches": receipt["revision"] == listing["revision"],
        "allow_patterns_recorded": receipt.get("allow_patterns") == listing["allow_patterns"],
        "same_paths": sorted(files) == sorted(hub_files),
        "sizes_match": all(
            files[p]["bytes"] == hub_files[p]["size"] for p in hub_files if p in files
        ),
        "artifact_root_recomputes": artifact_root(receipt["files"])
        == receipt["artifact_root_sha256"],
        "total_bytes": receipt["total_bytes"],
        "hub_total_bytes": listing["total_bytes"],
        "lfs_sha256_match": 0,
        "lfs_files": 0,
        "small_files_match": 0,
        "small_files": 0,
        "mismatches": [],
    }
    for path, item in hub_files.items():
        mine = files.get(path)
        if mine is None:
            result["mismatches"].append(f"missing {path}")
            continue
        if item["lfs_sha256"]:
            result["lfs_files"] += 1
            if mine["sha256"] == item["lfs_sha256"]:
                result["lfs_sha256_match"] += 1
            else:
                result["mismatches"].append(f"lfs sha256 {path}")
        else:
            result["small_files"] += 1
            data = (model_root / model_id / path).read_bytes()
            if (
                git_blob_sha1(data) == item["blobId"]
                and hashlib.sha256(data).hexdigest() == mine["sha256"]
            ):
                result["small_files_match"] += 1
            else:
                result["mismatches"].append(f"blob {path}")
    result["pass"] = (
        result["revision_matches"]
        and result["allow_patterns_recorded"]
        and result["same_paths"]
        and result["sizes_match"]
        and result["artifact_root_recomputes"]
        and result["total_bytes"] == result["hub_total_bytes"]
        and result["lfs_sha256_match"] == result["lfs_files"]
        and result["small_files_match"] == result["small_files"]
        and not result["mismatches"]
    )
    return result


def main():
    hub = json.loads(pathlib.Path(sys.argv[1]).read_text())
    receipt_root, model_root, out = map(pathlib.Path, sys.argv[2:5])
    results = [check(m, hub, receipt_root, model_root) for m in sys.argv[5:]]
    out.write_text(
        json.dumps(
            {"results": results, "pass": all(r["pass"] for r in results)}, indent=2, sort_keys=True
        )
        + "\n"
    )
    for r in results:
        print(r["model_id"], "PASS" if r["pass"] else f"FAIL {r['mismatches']}")
    return 0 if all(r["pass"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
