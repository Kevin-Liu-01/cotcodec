#!/usr/bin/env python3
"""Snapshot the primary URLs the repaired proposal cites that wave 1 did not (wave-1 snapshots are kept).

Uses wave 1's compute/snapshot_sources.py functions unchanged; writes a record only for URLs that
have no snapshot file yet. Usage: python snapshot_new_sources.py <proposal.md> <snapshot-dir>
"""
import datetime
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("snap_w1", HERE.parent / "snapshot_sources.py")
w1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w1)


def main() -> int:
    proposal, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    for url in w1.primary_urls(proposal.read_text(encoding="utf-8")):
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[1]).strip("_")[:150] + ".json"
        if (out_dir / name).exists():
            continue
        body, code, ctype = w1.fetch(url)
        rec = {"url": url, "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "http_status": code, "content_type": ctype, "raw_bytes": len(body),
               "raw_sha256": hashlib.sha256(body).hexdigest(), "raw_stored": False, "extract": w1.extract(url, body),
               "snapshot_run": "run 2 (D68 repair)"}
        (out_dir / name).write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        title = rec["extract"].get("title") or rec["extract"].get("html_title", "")
        print(code, url, title[:80], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
