#!/usr/bin/env python3
"""Snapshot the primary URLs the repaired proposal cites that have no snapshot yet (the wave-1
records are kept as fetched). Reuses ``../snapshot-sources.py``'s URL rule, fetch and extract.

Usage (worktree root): python3 <this> <proposal.md> <snapshot-dir>
"""

from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("snap", HERE.parent / "snapshot-sources.py")
snap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snap)


def main() -> int:
    proposal, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    have = {json.loads(p.read_text())["url"] for p in out_dir.glob("*.json")}
    for url in snap.primary_urls(proposal.read_text(encoding="utf-8")):
        if url in have:
            continue
        body, code, ctype = snap.fetch(url)
        rec = {
            "url": url,
            "fetched_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "http_status": code,
            "content_type": ctype,
            "raw_bytes": len(body),
            "raw_sha256": hashlib.sha256(body).hexdigest(),
            "raw_stored": False,
            "extract": snap.extract(url, body),
            "fetched_by": "D75 repair run",
        }
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[1]).strip("_")[:150] + ".json"
        (out_dir / name).write_text(
            json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        ex = rec["extract"]
        print(
            code,
            url,
            ex.get("citation_date"),
            [h["date"] for h in ex.get("submission_history", [])][:2],
            (ex.get("title") or ex.get("html_title", ""))[:70],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
