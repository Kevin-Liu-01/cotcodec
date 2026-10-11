#!/usr/bin/env python3
"""R01 Stage A0: derive a hashes-only per-step table from S1a's host step logs.

Input: a local, read-only copy of S1a's ``steps.jsonl`` and ``replies.jsonl`` for the four A1
VM jobs (host run directories 1045, 1048, 1051 and 1062), laid out as
``<logs>/<run>/episodes/<slot with ':' as '_'>.a<attempt>/{steps,replies}.jsonl``.

Every input file is checked against the committed per-job host listings
(``program/evidence/2026-10-10/q2-stage1-a1/<job>/vm-<run>/raw-sha256sums.txt``) before it is
read; one mismatch or missing file stops the script and writes nothing.

Output (committed beside this script):

* ``s1a-step-digests.jsonl.gz``: one row per episode attempt with its step list. Each step keeps
  the first 16 hex digits of the request, messages, prompt-id, processed-screenshot,
  raw-screenshot and IR digests, the SHA-256 prefix of the full reply text (thinking included),
  the reply length, token counts, latency fields, finish reason, parse-error flag, terminated
  flag and the IR op names. No reply text, screenshot, request body or host name is kept.
* ``derive-report.json``: input verification counts, the output's SHA-256, and descriptive
  reply-text statistics that need the text itself (common-prefix length of the replies of
  byte-identical step requests within a rerun pair whose earlier steps were all identical).

A 16-hex prefix (64 bits) is used only for equality tests inside rerun pairs (at most a few
thousand comparisons); the chance of any false equality is below 1e-12.

Usage (from the worktree root)::

    python3 program/evidence/2026-10-11/r01-stage-a0/derive_digests.py --logs <dir>
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
A1 = ROOT / "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"
JOBS = {"1045": "a1-9b-s1", "1048": "a1-4b-s1", "1051": "a1-9b-s2", "1062": "a1-4b-s2"}
JOB_RUN = {"A1-9B-S1": "1045", "A1-4B-S1": "1048", "A1-9B-S2": "1051", "A1-4B-S2": "1062"}
P = 16  # hex digits kept


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for run, job in JOBS.items():
        listing = (
            ROOT / f"program/evidence/2026-10-10/q2-stage1-a1/{job}/vm-{run}/raw-sha256sums.txt"
        )
        for line in listing.read_text().splitlines():
            digest, _, rel = line.partition("  ")
            if rel.endswith("/steps.jsonl") or rel.endswith("/replies.jsonl"):
                out[f"{run}/{rel.removeprefix('./')}"] = digest
    return out


def cut(value: object) -> str | None:
    return value[:P] if isinstance(value, str) else None


def common_prefix(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logs", type=Path, required=True)
    args = ap.parse_args()
    expected = expected_hashes()
    records = [json.loads(x) for x in A1.read_text().splitlines() if x.strip()]
    rows = []
    texts: dict[tuple, dict[int, str]] = {}
    verified = 0
    for rec in records:
        run = JOB_RUN[rec["job"]]
        rel = f"{run}/episodes/{str(rec['slot']).replace(':', '_')}.a{rec['attempt']}"
        payload = {}
        for name in ("steps.jsonl", "replies.jsonl"):
            path = args.logs / rel / name
            key = f"{rel}/{name}"
            if key not in expected:
                sys.exit(f"no committed hash for {key}")
            data = path.read_bytes()
            if sha(data) != expected[key]:
                sys.exit(f"hash mismatch: {key}")
            verified += 1
            payload[name] = [json.loads(x) for x in data.decode().splitlines() if x.strip()]
        replies = {int(r["step"]): str(r.get("response") or "") for r in payload["replies.jsonl"]}
        ekey = (rec["size"], rec["harness"], rec["session"], rec["task_id"], rec["rerun"])
        texts[ekey] = replies
        steps = []
        for s in payload["steps.jsonl"]:
            c = s.get("completion") or {}
            k = int(s["step"])
            text = replies.get(k)
            steps.append(
                {
                    "k": k,
                    "req": cut(c.get("request_sha256")),
                    "msg": cut(s.get("messages_sha256")),
                    "pid": cut(c.get("prompt_ids_sha256")),
                    "obs": cut(s.get("processed_sha256")),
                    "raw": cut(s.get("screenshot_sha256")),
                    "ir": cut(s.get("ir_sha256")),
                    "rep": sha(text.encode())[:P] if text is not None else None,
                    "rep_len": len(text) if text is not None else None,
                    "ptok": c.get("prompt_tokens"),
                    "ctok": c.get("completion_tokens"),
                    "lat": c.get("latency_s"),
                    "ttft": c.get("ttft_s"),
                    "tpot": c.get("tpot_s"),
                    "cached": c.get("cached_tokens"),
                    "fin": c.get("finish_reason"),
                    "perr": s.get("parse_error") is not None,
                    "term": s.get("terminated"),
                    "ops": [a.get("op") for a in (s.get("ir") or []) if isinstance(a, dict)],
                }
            )
        rows.append(
            {
                "job": rec["job"],
                "slot": rec["slot"],
                "attempt": rec["attempt"],
                "size": rec["size"],
                "harness": rec["harness"],
                "session": rec["session"],
                "rerun": rec["rerun"],
                "task_id": rec["task_id"],
                "steps": steps,
            }
        )
    rows.sort(key=lambda r: (r["size"], r["harness"], r["session"], r["task_id"], r["rerun"]))
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for r in rows:
            gz.write((json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n").encode())
    out = HERE / "s1a-step-digests.jsonl.gz"
    out.write_bytes(buf.getvalue())

    # Descriptive text statistics on natural replays: within-session pairs, steps k whose request
    # digest is equal and every earlier step's request and reply digests were equal.
    by = {(r["size"], r["harness"], r["session"], r["task_id"], r["rerun"]): r for r in rows}
    prefix = []
    for (z, h, s, t, rr), a in by.items():
        if rr != 1 or (z, h, s, t, 2) not in by:
            continue
        b = by[(z, h, s, t, 2)]
        for sa, sb in zip(a["steps"], b["steps"], strict=False):
            if sa["req"] is None or sa["req"] != sb["req"]:
                break
            ta, tb = (
                texts[(z, h, s, t, 1)].get(sa["k"], ""),
                texts[(z, h, s, t, 2)].get(sb["k"], ""),
            )
            cp = common_prefix(ta, tb)
            prefix.append(
                {
                    "size": z,
                    "harness": h,
                    "session": s,
                    "task8": t[:8],
                    "step": sa["k"],
                    "identical_text": ta == tb,
                    "common_prefix_chars": cp,
                    "len_a": len(ta),
                    "len_b": len(tb),
                    "prefix_share_of_shorter": round(cp / max(1, min(len(ta), len(tb))), 4),
                }
            )
            if ta != tb:
                break
    report = {
        "schema": "r01-stage-a0-derive-v1",
        "inputs": {
            "a1_jsonl": str(A1.relative_to(ROOT)),
            "a1_jsonl_sha256": sha(A1.read_bytes()),
            "episode_attempts": len(records),
            "files_verified_against_committed_listings": verified,
            "listings": {
                run: f"program/evidence/2026-10-10/q2-stage1-a1/{job}/vm-{run}/raw-sha256sums.txt"
                for run, job in JOBS.items()
            },
        },
        "output": {
            "path": str(out.relative_to(ROOT)),
            "sha256": sha(out.read_bytes()),
            "rows": len(rows),
            "steps": sum(len(r["steps"]) for r in rows),
            "hash_prefix_hex": P,
        },
        "natural_replay_reply_prefix": prefix,
    }
    (HERE / "derive-report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("inputs", "output")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
