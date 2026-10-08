"""Fetch each cited primary URL once and record status, raw-body SHA-256 and a metadata extract.

Bodies are not stored. arXiv extracts (title, authors, dates, abstract) are CC0 metadata; other
pages keep only their HTML title. Usage: python snapshot_sources.py <out_dir> <url> [<url> ...]
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def extract(url: str, body: str) -> dict:
    title = re.search(r"<title>(.*?)</title>", body, re.S)
    out = {"html_title": html.unescape(title.group(1).strip()) if title else None}
    if "arxiv.org/abs/" in url:

        def meta(name: str) -> list[str]:
            pattern = rf'<meta name="{name}" content="([^"]*)"'
            return [html.unescape(v) for v in re.findall(pattern, body)]

        out.update(
            {
                "title": (meta("citation_title") or [None])[0],
                "authors": meta("citation_author"),
                "citation_date": (meta("citation_date") or [None])[0],
                "submission_history": re.findall(r"<strong>\[(v\d+)\]</strong>\s*([^<(]+)", body),
                "abstract": (meta("citation_abstract") or [None])[0],
                "extract_licence": "arXiv metadata (title, authors, abstract) is CC0 1.0",
            }
        )
    return out


def main() -> None:
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for url in sys.argv[2:]:
        req = urllib.request.Request(url, headers={"User-Agent": "cotcodec-gauntlet-snapshot/1"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            status, ctype = resp.status, resp.headers.get("Content-Type")
        rec = {
            "url": url,
            "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "http_status": status,
            "content_type": ctype,
            "raw_bytes": len(raw),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_stored": False,
            "extract": extract(url, raw.decode("utf-8", "ignore")),
        }
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[1]).strip("_")[:150] + ".json"
        path = out_dir / name
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        index.append(
            {
                "url": url,
                "http_status": status,
                "fetched_at": rec["fetched_at"],
                "raw_sha256": rec["raw_sha256"],
                "raw_bytes": len(raw),
                "artifact": f"snapshots/{name}",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
        print(status, url, file=sys.stderr)
    print(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
