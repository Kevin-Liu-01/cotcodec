"""G3b post hoc (EXPLORATORY; host CPU, reads token ids only; text-free output): G3's repetition
measure (scripts/analyze_g3_accuracy.py distinct_ngram_share: distinct 16-grams over all 16-grams
in the last 8,192 tokens; 1.0 means no repeat) for the main run's rollouts, by arm and by how they
ended: reached 81,920, cut by the time budget, ended on their own past 32,768 tokens.
Usage: python posthoc_repetition.py <worker dir> [<worker dir> ...] > posthoc-repetition.json"""

import json
import sys
from pathlib import Path

import numpy as np


def share(tokens: np.ndarray, n: int = 16, window: int = 8192) -> float | None:
    t = tokens[-window:]
    if len(t) < n:
        return None
    grams = {tuple(t[i : i + n].tolist()) for i in range(len(t) - n + 1)}
    return len(grams) / (len(t) - n + 1)


def main() -> None:
    out = {}
    for d in map(Path, sys.argv[1:]):
        rec = json.loads((d / "records.json").read_text())
        tok = np.load(d / "tokens.npz")
        off, ids = tok["offsets"], tok["token_ids"]
        groups: dict[str, list[float]] = {
            "reached_81920": [],
            "time_cut": [],
            "ended_past_32768": [],
        }
        for i, r in enumerate(rec["requests"]):
            s = share(ids[off[i] : off[i + 1]])
            if s is None:
                continue
            if r["finish_reason"] == "length":
                groups["reached_81920"].append(s)
            elif r["finish_reason"] == "cut_at_time_budget":
                groups["time_cut"].append(s)
            elif r["finish_reason"] == "stop" and r["completion_len"] > 32768:
                groups["ended_past_32768"].append(s)
        out[rec["arm"]] = {
            k: {
                "n": len(v),
                "median": float(np.median(v)) if v else None,
                "min": float(np.min(v)) if v else None,
                "below_0_5": sum(1 for x in v if x < 0.5),
            }
            for k, v in groups.items()
        }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
