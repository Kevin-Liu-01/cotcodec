"""Descriptive per-entry table of the S2 v5 development confirmation (decides nothing).

Reads each campaign directory's session configs and trial records (standard library only):
per (image, entry) the passes out of the trials, and for Writer's two pointer composites every
trial's read-back, expected text, session and the cells file the session's runner was given.
The registered reading is ap_delta_v5's confirm-read (confirm-reading.json); this is a view.

    python3 -I summarize.py JOB_DIR [JOB_DIR ...] --source-dir EXPORT > confirm-summary.json
"""
import json
import sys
from pathlib import Path


def main(argv):
    src = Path(argv[argv.index("--source-dir") + 1])
    jobs = [Path(a) for a in argv[: argv.index("--source-dir")]]
    out = {"campaigns": []}
    for job in jobs:
        for sub in sorted(p for p in job.iterdir() if (p / "apdelta.json").is_file()):
            meta = json.loads((sub / "apdelta.json").read_text())
            cell = meta["cells"][0]
            entries, writer = {}, []
            cells_paths = set()
            for cfg in sorted((sub / "cycles").glob("config-*.json")):
                c = json.loads(cfg.read_text())
                cells_paths.add(c.get("cells_path"))
                tr = sub / "cycles" / cfg.name.replace("config-", "cycle-").replace(".json", ".trials.jsonl")
                if not tr.is_file():
                    continue
                for line in tr.read_text().splitlines():
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    e = entries.setdefault(t["cell"], {"passed": 0, "trials": 0})
                    e["trials"] += 1
                    e["passed"] += bool(t.get("pass"))
                    if t["cell"] in ("writer:drag_select_word", "writer:triple_click_line"):
                        writer.append({"session": c.get("cycle"), "seq": t.get("seq"),
                                       "cell": t["cell"], "pass": t.get("pass"),
                                       "expect": t.get("expect"), "text": t.get("text"),
                                       "infra": t.get("infra"), "errors": t.get("errors")})
            targets = {}
            for p in cells_paths:
                rel = (p or "").removeprefix("/src/")
                f = src / rel
                if rel and f.is_file():
                    targets[rel] = json.loads(f.read_text())["canary"]["apps"]["writer"]["targets"]
            out["campaigns"].append({
                "job": job.name, "dir": sub.name, "cell": cell,
                "cells_file": meta.get("cells_file"), "session_cells_paths": sorted(cells_paths),
                "writer_targets_in_cells_file": targets,
                "entries": len(entries), "trials": sum(e["trials"] for e in entries.values()),
                "passed": sum(e["passed"] for e in entries.values()),
                "not_5_of_5": {k: v for k, v in entries.items() if (v["passed"], v["trials"]) != (5, 5)},
                "writer_trials": writer,
            })
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    print()


if __name__ == "__main__":
    main(sys.argv[1:])
