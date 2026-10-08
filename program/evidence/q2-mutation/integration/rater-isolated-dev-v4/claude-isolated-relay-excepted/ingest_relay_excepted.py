"""Sensitivity ingest: the registered ``ingest-isolated`` with one exception.

Not a registered path. The workflow was resumed after the session ended, and
the resumed harness put one extra user turn before each later rater agent's
task: its relay of the session user's request (byte-identical in all 110
agents, SHA-256 ``RELAY_SHA256`` below). The registered transcript audit
takes the first non-tool-result user turn as the agent's prompt, so it voids
those 110 items. This script runs the same ``rater_runner.ingest_isolated``
(every other check unchanged: tools, paths, model, item id, packet read,
directory digests, answer source) with that one turn, and only a turn
byte-identical to it, treated as a non-prompt, so the computed-task turn that
follows is checked against the rendered template as the first prompt.

Usage: ``python ingest_relay_excepted.py <packets> <manifest> <iso root>
<answers dir> <transcripts dir> <out dir>`` from the repository root.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from harness.q2_mutation import rater_runner

RELAY_SHA256 = "8e7dbd00c14db448bb1272f7bbf2c908dbd8b4a39d83445792b7d5f8cb6fe5fa"

_registered_prompt_text = rater_runner._prompt_text
excepted = 0


def prompt_text(content):
    global excepted
    text = _registered_prompt_text(content)
    if text is not None and hashlib.sha256(text.encode("utf-8")).hexdigest() == RELAY_SHA256:
        excepted += 1
        return None
    return text


rater_runner._prompt_text = prompt_text

packets_path, manifest_path, iso_root, answers, transcripts, out = map(Path, sys.argv[1:7])
packets = rater_runner._load_shards([packets_path])
manifest = json.loads(manifest_path.read_bytes())
records, digests = rater_runner.isolated_answers(answers)
result = rater_runner.ingest_isolated(packets, manifest, iso_root, records, transcripts, out)
result["relay_turns_excepted"] = excepted
result["relay_sha256"] = RELAY_SHA256
result["calls_sha256"] = rater_runner.sha256_file(out / "calls.jsonl")
result["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
result["answers_files_sha256"] = digests
(out / "sensitivity-result.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "answers_files_sha256"}, sort_keys=True))
