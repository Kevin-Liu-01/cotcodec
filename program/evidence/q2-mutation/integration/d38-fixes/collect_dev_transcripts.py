"""Scratch-only rerun of the D38 transcript collector and audit over the dev rating.

Decision D38 registers ``rater_runner collect-transcripts``. This script copies
the 158 rater transcripts of the D34 development rating (workflow run
``wf_65ce9899-24a``: 142 completed agents, 16 interrupted attempts) and the
journal lines of those agents into a scratch run directory, runs the collector
on that copy against the development export manifest, and applies the
registered transcript audit (``audit_transcript``) to every collected
transcript with the ingest's answering rule (D38: an attempt without a
journal result answers only through a structured answer). It writes counts
only. Nothing is ingested: the development packets predate the
difference-first order, so ``ingest-isolated`` refuses them, and the
registered development result (kappa 0.066) stays as recorded.

    python collect_dev_transcripts.py <workflow-run-dir> <export-manifest> <scratch-dir> \
        [<hand-copied transcript dir> ...]

The optional directories are the transcripts copied by hand for the sixth
review (``{item}.jsonl`` and ``{item}.{agent}.jsonl``); the collected layout is
compared with them file by file. The collector is also run on the whole
workflow run, whose fix, audit and review agents are not raters, to record
that it refuses a run with an agent it cannot map.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

from harness.q2_mutation import rater_runner as rr


def main(run: Path, manifest_path: Path, scratch: Path, hand: list[Path]) -> dict:
    manifest = json.loads(manifest_path.read_bytes())
    # The rating phase's agents only: the workflow run also held one fix, one
    # audit and one review agent, which are not raters.
    raters = {
        agent
        for agent in (
            json.loads(line)
            for line in (run / "journal.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        if agent.get("type") == "started" and agent.get("phase") == "Rate"
        for agent in [agent["agentId"]]
    }
    copy = scratch / "run"
    copy.mkdir(parents=True)
    kept = []
    for line in (run / "journal.jsonl").read_text(encoding="utf-8").splitlines():
        entry = json.loads(line) if line.strip() else {}
        if entry.get("type") == "launched" or entry.get("agentId") in raters:
            kept.append(line + "\n")
    (copy / "journal.jsonl").write_text("".join(kept), encoding="utf-8")
    for agent in sorted(raters):
        shutil.copyfile(run / f"agent-{agent}.jsonl", copy / f"agent-{agent}.jsonl")
    out = scratch / "collected"
    collection = rr.collect_transcripts(copy, manifest, out)
    try:
        rr.collect_transcripts(run, manifest, scratch / "whole-run")
        whole_run = "collected (not expected)"
    except SystemExit as exc:
        whole_run = f"refused: {exc}"
    rows = {row["file"]: row for row in collection["agents"]}
    voids: Counter[str] = Counter()
    relay: Counter[str] = Counter()
    answering = Counter()
    items_answering: Counter[int] = Counter()
    for item, entry in manifest["items"].items():
        folder = Path(manifest["iso_root"]) / entry["dir"]
        expected = rr.render_isolated_prompt(f"{manifest['iso_root']}/{entry['dir']}", item)
        audited = []
        for path in rr.item_transcripts([out], item):
            result = rr.audit_transcript(
                path.read_bytes(), folder, item_id=item, expected_prompt=expected,
                item_ids=manifest["items"],
            )
            if not rows[path.name]["answered"]:
                result["answers"] = bool(result["structured_answers"])
            audited.append((path, result))
            relay.update(result["relay_frames_sha256"])
            answering[(rows[path.name]["answered"], result["answers"])] += 1
        primary = next((p for p, r in audited if r["answers"]), None)
        items_answering[sum(1 for _, r in audited if r["answers"])] += 1
        for path, result in audited:
            for reason in result["void_reasons"]:
                if path == primary or reason not in rr.ANSWER_ONLY_REASONS:
                    voids[reason] += 1
    comparison = None
    if hand:
        mine = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.jsonl")}
        theirs = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in hand
            for p in folder.glob("*.jsonl")
        }
        comparison = {
            "hand_copied": len(theirs),
            "same_name_and_sha256": sum(1 for n, d in mine.items() if theirs.get(n) == d),
            "only_collected": sorted(set(mine) - set(theirs)),
            "only_hand_copied": sorted(set(theirs) - set(mine)),
        }
    return {
        "kind": (
            "scratch-only rerun of the D38 collector (rater_runner.collect_transcripts) and the "
            "registered transcript audit over copies of the 158 D34 development rater "
            "transcripts; counts only, nothing ingested, the registered dev result stays"
        ),
        "rater_agents": len(raters),
        "collected": collection["transcripts"],
        "answered_in_journal": collection["answered"],
        "items": collection["items"],
        "exported_items_without_transcript": collection["exported_items_without_transcript"],
        "files": dict(Counter("item" if n.count(".") == 1 else "item.agent" for n in rows)),
        "transcripts_answering": sum(v for (_, a), v in answering.items() if a),
        "answering_by_journal_result": {
            f"journal_result={j}, answers={a}": v for (j, a), v in sorted(answering.items())
        },
        "items_by_answering_transcripts": dict(sorted(items_answering.items())),
        "void_reasons": dict(voids),
        "relay_frames": {sha[:8]: n for sha, n in relay.items()},
        "hand_copied_comparison": comparison,
        "whole_run_with_non_rater_agents": whole_run,
        "commit": None,
    }


if __name__ == "__main__":
    run_dir, manifest_file, scratch_dir, *hand_dirs = sys.argv[1:]
    record = main(
        Path(run_dir), Path(manifest_file), Path(scratch_dir), [Path(d) for d in hand_dirs]
    )
    record["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    print(json.dumps(record, indent=1, sort_keys=True))
