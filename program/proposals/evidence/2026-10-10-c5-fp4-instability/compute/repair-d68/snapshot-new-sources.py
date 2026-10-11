#!/usr/bin/env python3
"""Snapshot the URLs the D68 repair adds to the proposal, with wave 1's snapshot code unchanged.

Imports fetch() and extract() from compute/snapshot-sources.py and writes one record per URL in the
same format, so wave 1's 47 snapshots are not refetched (their fetch times and hashes stay as recorded).

Usage: python snapshot-new-sources.py <snapshot-dir> <url> [<url> ...]
"""
import datetime
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("snap", Path(__file__).resolve().parents[1] / "snapshot-sources.py")
snap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snap)

out_dir = Path(sys.argv[1])
for url in sys.argv[2:]:
    body, code, ctype = snap.fetch(url)
    rec = {"url": url, "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "http_status": code, "content_type": ctype, "raw_bytes": len(body),
           "raw_sha256": hashlib.sha256(body).hexdigest(), "raw_stored": False, "extract": snap.extract(url, body)}
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[1]).strip("_")[:150] + ".json"
    (out_dir / name).write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(code, url, (rec["extract"].get("title") or rec["extract"].get("html_title", ""))[:80])
