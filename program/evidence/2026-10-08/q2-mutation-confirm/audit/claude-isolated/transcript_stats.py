"""Diligence aggregates of the isolated Claude rating (not a void condition).

Reads the collected transcripts (outside the repository: they quote document
text) and the isolation root, and writes counts only: tools, models, page
images read against page images exported, read truncation notices and the
one out-of-directory Read the registered audit voided. Run with the session's
paths:

    python transcript_stats.py <transcripts dir> <iso root> <calls.jsonl> <out.json>
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter


def main(transcripts: str, iso_root: str, calls_path: str, out: str) -> None:
    tools: Counter[str] = Counter()
    models: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    pages_exported = pages_read = items_all_pages = 0
    items_truncation = truncation_notices = 0
    outside_reads: list[dict[str, object]] = []
    for line in open(calls_path, encoding="utf-8"):
        call = json.loads(line)
        item = call["item_id"]
        extra = call["extra"]
        outcomes[call["outcome"]] += 1
        tools.update(extra["tool_calls"])
        models.update(extra["transcript_models"])
        notices = extra["transcripts"][0]["attachment_types"].get("read_truncation_notice", 0)
        truncation_notices += notices
        items_truncation += bool(notices)
        item_dir = os.path.join(iso_root, item)
        pages = set(os.listdir(os.path.join(item_dir, "pages")))
        read: set[str] = set()
        for entry_line in open(os.path.join(transcripts, f"{item}.jsonl"), encoding="utf-8"):
            entry = json.loads(entry_line)
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if block.get("type") != "tool_use" or block.get("name") != "Read":
                    continue
                path = str(block.get("input", {}).get("file_path", ""))
                if path.startswith(os.path.join(item_dir, "pages") + "/"):
                    read.add(os.path.basename(path))
                elif not path.startswith(item_dir + "/"):
                    outside_reads.append(
                        {
                            "item_id": item,
                            "path_relative_to_session_root": os.path.relpath(
                                path, os.path.dirname(os.path.dirname(iso_root))
                            ),
                            "exists": os.path.exists(path),
                        }
                    )
        pages_exported += len(pages)
        pages_read += len(read & pages)
        items_all_pages += pages <= read
    result = {
        "schema": "q2m-confirm-transcript-stats-v1",
        "items": sum(outcomes.values()),
        "outcomes": dict(outcomes),
        "tool_calls": dict(tools),
        "agent_turn_models": dict(models),
        "page_images_exported": pages_exported,
        "page_images_read": pages_read,
        "items_reading_every_page_image": items_all_pages,
        "items_with_read_truncation_notice": items_truncation,
        "read_truncation_notices": truncation_notices,
        "reads_outside_item_directory": outside_reads,
        "role": "diligence aggregates; the registered transcript audit is rater_runner.audit_transcript",
    }
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(*sys.argv[1:5])
