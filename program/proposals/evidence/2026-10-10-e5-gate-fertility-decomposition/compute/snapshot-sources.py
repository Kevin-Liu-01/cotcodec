#!/usr/bin/env python3
"""Snapshot every primary URL the proposal cites (metadata extract plus body hash).

Adapted from the C3 gauntlet bundle's script. Reads the proposal, selects URLs
the way scripts/research_direction_doctor.py does (recognised primary domains,
path of at least 5 characters), fetches each once with curl, and writes one
JSON record per URL: HTTP status, fetch time, SHA-256 and size of the full
response body, and a metadata extract. arXiv extracts (title, authors, dates,
version history, abstract) are CC0; other pages keep only their HTML title.
Page bodies are not stored. Existing records are kept unless --refresh is given,
so a re-run only fetches URLs added to the proposal since the last run.

Usage: python snapshot-sources.py <proposal.md> <snapshot-dir> [--refresh] [--extra URL ...]
"""

from __future__ import annotations

import datetime
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

PRIMARY_DOMAINS = {
    "aclanthology.org", "arxiv.org", "deepmind.google", "github.com", "huggingface.co",
    "labs.ramp.com", "openai.com", "openreview.net", "proceedings.mlr.press",
    "proceedings.neurips.cc", "research.google",
}


def primary_urls(text: str) -> list[str]:
    urls = sorted(set(re.findall(r"https?://[^\s)>|]+", text)))
    return [u for u in urls if urlparse(u).netloc.casefold().removeprefix("www.") in PRIMARY_DOMAINS
            and len(urlparse(u).path.strip("/")) >= 5]


def fetch(url: str) -> tuple[bytes, int, str]:
    proc = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "60", "-A", "Mozilla/5.0 (cotcodec research snapshot)",
         "-w", "\n%{http_code}\n%{content_type}", url],
        capture_output=True, timeout=90, check=False)
    body, code, ctype = proc.stdout.rsplit(b"\n", 2)
    return body, int(code or 0), ctype.decode(errors="replace")


def extract(url: str, body: bytes) -> dict:
    text = body.decode("utf-8", "replace")
    if urlparse(url).netloc.endswith("arxiv.org"):
        def metas(name: str) -> list[str]:
            return [html.unescape(m) for m in re.findall(rf'<meta name="{name}" content="([^"]*)"', text)]
        abs_m = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', text, re.S)
        abstract = re.sub(r"<[^>]+>", "", abs_m.group(1)).replace("Abstract:", "").strip() if abs_m else ""
        hist = re.findall(r"<strong>(?:<a[^>]*>)?\[(v\d+)\](?:</a>)?</strong>\s*([^<(]+?)\s*\(", text)
        return {"title": (metas("citation_title") or [""])[0], "authors": metas("citation_author"),
                "citation_date": (metas("citation_date") or [""])[0],
                "submission_history": [{"version": v, "date": d.strip()} for v, d in hist],
                "abstract": " ".join(html.unescape(abstract).split()),
                "extract_licence": "arXiv metadata (title, authors, abstract) is CC0 1.0"}
    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    return {"html_title": " ".join(html.unescape(title.group(1)).split()) if title else ""}


def record_name(url: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[1]).strip("_")[:150] + ".json"


def main() -> int:
    args = sys.argv[1:]
    refresh = "--refresh" in args
    extra: list[str] = []
    if "--extra" in args:
        extra = args[args.index("--extra") + 1:]
        args = args[:args.index("--extra")]
    args = [a for a in args if a != "--refresh"]
    proposal, out_dir = Path(args[0]), Path(args[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    urls = sorted(set(primary_urls(proposal.read_text(encoding="utf-8")) + extra))
    for url in urls:
        path = out_dir / record_name(url)
        if path.is_file() and not refresh:
            continue
        body, code, ctype = fetch(url)
        rec = {"url": url,
               "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "http_status": code, "content_type": ctype, "raw_bytes": len(body),
               "raw_sha256": hashlib.sha256(body).hexdigest(), "raw_stored": False,
               "extract": extract(url, body)}
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        title = rec["extract"].get("title") or rec["extract"].get("html_title", "")
        print(code, url, title[:80])
    return 0


if __name__ == "__main__":
    sys.exit(main())
