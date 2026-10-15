"""AM3 post hoc diagnostics (EXPLORATORY; added after the declared outputs were read; they decide
nothing). Run on the host from the clean checkout (``uv run --locked --offline python
<this file>``); prints text-free JSON (counts only, no reply text):

1. Judge replay at the item level: for every (question, response, source) judge item that AM3's
   job 1466 shares with the pilot's job 1411 (compiled) and job 1441 (eager), whether each judge
   gave the same label.
2. Abstention-pattern coverage per reader: the first matching AM1d pattern over the 4-subset
   replies; among unflagged replies, how many match a broader post hoc list of abstention-like
   phrases (and how many of those the primary judge called correct), and how many normalized
   unflagged replies recur verbatim in at least 5 questions.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

sys.path[:0] = [".", "scripts"]
import memcredit_am3 as am3  # noqa: E402
import memcredit_label_free as lf  # noqa: E402

from harness import memcredit as mc  # noqa: E402

RUNS = Path("/home/kevin/cotcodec-runs/stage0")
AM3 = RUNS / "am3-reader-replication/runs/main/1466/am3"
PILOT = RUNS / "am1-study/runs/main/1411/am1"
EAGER = RUNS / "am1-study/runs/eager/1441/am1"
ARTIFACT = RUNS / "am1-study/runs/main/1411/study-artifact.json"
BROADER = re.compile(
    r"\b(?:not sure|unsure|unclear|no record|no mention|not clear|don t have|do not have|"
    r"doesn t say|does not say|not specified|can t be determined|cannot be determined|unknown|"
    r"sorry|no specific|not possible to)\b"
)


def key(item: dict) -> tuple:
    return (item["question_index"], item["response"], item["source"])


def main() -> None:
    out: dict = {"note": "post hoc; text-free counts", "judge_replay": {}, "abstention": {}}
    mine = json.loads((AM3 / "judge-items.json").read_text())
    labels = {
        "primary": am3.labels_from_pass(am3.load_pass(AM3 / "sessions" / "judge32")),
        "secondary": am3.labels_from_pass(am3.load_pass(AM3 / "sessions" / "judge8")),
    }
    mine_key = {key(i): i["index"] for i in mine}
    for name, run, judges in (
        ("pass_1411_compiled", PILOT, (("primary", "judge32-gpu0"), ("secondary", "judge8-gpu0"))),
        ("pass_1441_eager", EAGER, (("primary", "judge32-gpu0"),)),
    ):
        items = json.loads((run / "judge-items.json").read_text())
        pilot_key = {key(i): i["index"] for i in items}
        shared = sorted(set(pilot_key) & set(mine_key))
        for judge, step in judges:
            pl = am3.labels_from_pass(am3.load_pass(run / "sessions" / step))
            pairs = [(pl.get(pilot_key[k]), labels[judge].get(mine_key[k])) for k in shared]
            out["judge_replay"][f"{name}:{judge}"] = {
                "shared_items": len(shared),
                "shared_reader_items": sum(1 for k in shared if k[2] == "reader"),
                "same_label": sum(a == b for a, b in pairs),
                "pilot_yes_am3_no": sum(a == 1 and b == 0 for a, b in pairs),
                "pilot_no_am3_yes": sum(a == 0 and b == 1 for a, b in pairs),
            }
    artifact = json.loads(ARTIFACT.read_text())
    item_of = am3.item_index(mine)
    requests = [r for r in am3.request_table(artifact) if r["mask"] != am3.FULL]
    for step in ("rd-qwen3-8b", "rd-olmo2", "rd-qwen35-9b-default"):
        rows = am3.load_pass(AM3 / "sessions" / step)["rows"]
        patterns: collections.Counter = collections.Counter()
        broader = broader_right = 0
        recur: dict = collections.defaultdict(set)
        for r in requests:
            text = rows[r["index"]]["text"]
            abstains, pattern = lf.abstention(text)
            patterns[pattern or "none"] += 1
            if abstains:
                continue
            norm = mc.normalize_answer(text.strip())
            if BROADER.search(norm):
                broader += 1
                u = labels["primary"].get(item_of.get((r["question_index"], text.strip())))
                broader_right += u == 1
            recur[norm].add(r["question_index"])
        out["abstention"][step] = {
            "four_subset_replies": len(requests),
            "first_pattern": dict(sorted(patterns.items())),
            "unflagged_matching_broader_list": broader,
            "of_which_primary_judge_correct": broader_right,
            "unflagged_normalized_replies_in_5_or_more_questions": sum(
                1 for v in recur.values() if len(v) >= 5
            ),
        }
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
