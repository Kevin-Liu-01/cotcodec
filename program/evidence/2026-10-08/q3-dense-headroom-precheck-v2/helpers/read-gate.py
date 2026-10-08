#!/usr/bin/env python3
"""Operator read of a q3-dense-headroom-precheck-v2 Qwen3-0.6B-Base receipt (read only).

Run from the frozen clone: uv run --locked python <this> RECEIPT. It calls the registered
functions unchanged (harness.dense_headroom_v2.v1_reproduction against the committed job-727
receipt, refused unless its bytes are bfe4a7c3...) and prints the receipt's own
smoke_452_reproduction, binding and status fields. It decides nothing; the filler and the
summariser apply the gates.
"""

import hashlib
import json
import sys
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root))
from harness import dense_headroom_v2 as dv2  # noqa: E402

path = Path(sys.argv[1])
raw = path.read_bytes()
receipt = json.loads(raw)
v1 = dv2.load_v1_small_lane_receipt(root)
gate = dv2.v1_reproduction(receipt, v1)
smoke = (receipt.get("report") or {}).get("smoke_452_reproduction")
out = {
    "receipt": str(path),
    "receipt_sha256": hashlib.sha256(raw).hexdigest(),
    "experiment_id": receipt.get("experiment_id"),
    "status": receipt.get("status"),
    "profile": receipt.get("profile"),
    "lane": (receipt.get("lane") or {}).get("lane_id"),
    "slurm_job_id": receipt.get("slurm_job_id"),
    "slurm_job_id_source": receipt.get("slurm_job_id_source"),
    "hashes": receipt.get("hashes"),
    "decisions": receipt.get("decisions"),
    "smoke_452_reproduction": smoke,
    "v1_job_727_reproduction": gate,
    "v1_dev_artifact_sha256": (v1.get("hashes") or {}).get("dev_artifact_sha256"),
}
print(json.dumps(out, indent=2, sort_keys=True, default=str))
