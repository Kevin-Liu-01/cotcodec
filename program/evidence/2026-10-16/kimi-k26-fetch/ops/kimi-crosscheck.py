#!/usr/bin/env python3
"""Kimi-K2.6 fetch: check the lane's receipt against the Hub's own file listing at the pinned
revision (hub/tree.json, fetched anonymously before the download). Every path, every size, every
LFS file's SHA-256 (the Hub's LFS oid) and, for the small non-LFS files, the git blob SHA-1
recomputed from the bytes on disk must match. Also recomputes the artifact root from the receipt's
file list. Usage: kimi-crosscheck.py <receipt.json> <tree.json> <snapshot dir> <output json>"""
import hashlib
import json
import pathlib
import sys

receipt = json.loads(pathlib.Path(sys.argv[1]).read_text())
tree = json.loads(pathlib.Path(sys.argv[2]).read_text())
snap, out = pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
hub = {x["path"]: x for x in tree if x["type"] == "file"}
mine = {x["path"]: x for x in receipt["files"]}
bad = []
for p in sorted(set(hub) | set(mine)):
    h, m = hub.get(p), mine.get(p)
    if h is None or m is None:
        bad.append({"path": p, "issue": "only in hub" if m is None else "only in receipt"})
        continue
    if h["size"] != m["bytes"]:
        bad.append({"path": p, "issue": "size", "hub": h["size"], "receipt": m["bytes"]})
    if h.get("lfs"):
        if h["lfs"]["oid"] != m["sha256"]:
            bad.append({"path": p, "issue": "lfs sha256"})
    else:
        data = (snap / p).read_bytes()
        blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        if blob != h["oid"]:
            bad.append({"path": p, "issue": "git blob sha1"})
        if hashlib.sha256(data).hexdigest() != m["sha256"]:
            bad.append({"path": p, "issue": "sha256 on disk differs from receipt"})
encoded = json.dumps(receipt["files"], separators=(",", ":"), sort_keys=True).encode()
result = {
    "receipt_revision": receipt["revision"],
    "files_hub": len(hub), "files_receipt": len(mine),
    "lfs_files_checked": sum(1 for x in hub.values() if x.get("lfs")),
    "non_lfs_files_checked": sum(1 for x in hub.values() if not x.get("lfs")),
    "bytes_hub": sum(x["size"] for x in hub.values()), "bytes_receipt": receipt["total_bytes"],
    "artifact_root_recomputed": hashlib.sha256(encoded).hexdigest(),
    "artifact_root_receipt": receipt["artifact_root_sha256"],
    "mismatches": bad,
}
result["pass"] = (not bad and result["bytes_hub"] == result["bytes_receipt"]
                  and result["artifact_root_recomputed"] == result["artifact_root_receipt"])
out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "mismatches"} | {"n_mismatches": len(bad)}, indent=1))
sys.exit(0 if result["pass"] else 1)
