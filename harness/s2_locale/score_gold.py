#!/usr/bin/env python3
"""S2 v3 Phase 0 checker invariance, scoring step: the real OSWorld checker on every cell's saved
gold and do-nothing candidates (goldsave.py), in the metric container's locked OSWorld venv,
through the checker-mutation study's offline scorer (harness/q2_mutation/offline_eval.py).

Usage (metric container, /opt/venv-lock/bin/python): score_gold.py <goldsave_out_dir> <out_dir> [workers]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.q2_mutation import offline_eval as OE  # noqa: E402


def main() -> int:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for line in (src / "score-jobs.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        j = json.loads(line)
        j["files"] = {k: (v if v is None or v.startswith("/") else str(src / v)) for k, v in j["files"].items()}
        # the verdict schema wants the saving build named; goldsave's rows do not carry it
        j["lo_build"] = j.get("lo_build") or f"LibreOffice 7.3.7.2 30(Build:2); libreoffice-core 1:7.3.7-0ubuntu0.22.04.4; cell {j.get('cell')}"
        jobs.append(j)
    (out / "score-jobs-abs.jsonl").write_text("".join(json.dumps(j) + "\n" for j in jobs))
    os.environ.setdefault("PYTHONHASHSEED", "0")
    return OE.main(["--jobs", str(out / "score-jobs-abs.jsonl"), "--out", str(out / "verdicts.jsonl"),
                    "--notes", str(out / "notes.jsonl"), "--osworld", "/inputs/OSWorld",
                    "--file-cache", "/inputs/file_cache_1e112283/files",
                    "--requirements", "/opt/q2/osworld-lock-export.txt", "--dep-set", "lock",
                    "--workers", str(workers), "--repeat", "1", "--timeout", "300"])


if __name__ == "__main__":
    sys.exit(main())
