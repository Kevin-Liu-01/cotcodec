"""Independent strict audit of the isolated Claude rater transcripts (D25, D27).

Usage: ``python audit_transcripts.py <workflow run dir> <iso root> <out dir>
<item-answer list>``. The workflow run directory holds ``journal.jsonl`` and one
``agent-<id>.jsonl`` transcript (with ``agent-<id>.meta.json``) per agent; the
rater agents are the journal's ``rate:*`` labels. The item-answer list is the
``<item_id> <answer>`` lines the orchestrator handed over for ingest.

For every rater agent: every tool call, the transcript SHA-256, the item the
task prompt assigned, and this audit's rule, stricter than the registered
``rater_runner.audit_transcript``: the agent may call only Read, on paths
inside its own item directory, plus the answer channel StructuredOutput
exactly once, for its own item; any other tool, any path outside, a second
answer, an answer for another item, a model other than claude-opus-5-5, or an
answer that differs from the journal's result or the handed-over list voids
the rating (``unsure``).

Writes ``<out>/answers/<item>.json`` and ``<out>/transcripts/<item>.jsonl``
(byte copies) for ``rater_runner ingest-isolated``, which stay outside the
repository because they quote document text, and ``<out>/strict-audit.json``:
tool names, paths relative to the item directory, counts and digests only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

WF = Path(sys.argv[1])
ISO = Path(sys.argv[2])
OUT = Path(sys.argv[3])
TASK_ANSWERS = Path(sys.argv[4])

ANSWER_CHANNEL = "StructuredOutput"
ALLOWED = {"Read", ANSWER_CHANNEL}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inside(value: object, folder: Path) -> bool:
    if not isinstance(value, str) or not value.startswith("/") or "\x00" in value:
        return False
    target = os.path.realpath(value)
    base = os.path.realpath(folder)
    return target == base or target.startswith(base.rstrip("/") + "/")


def tool_uses(node):
    if isinstance(node, dict):
        if node.get("type") == "tool_use" and isinstance(node.get("name"), str):
            yield node
        for v in node.values():
            yield from tool_uses(v)
    elif isinstance(node, list):
        for v in node:
            yield from tool_uses(v)


journal = [json.loads(line) for line in (WF / "journal.jsonl").read_text().splitlines() if line]
started = {e["agentId"]: e for e in journal if e["type"] == "started" and e.get("phase") == "Rate"}
results = {
    e["agentId"]: e["result"]
    for e in journal
    if e["type"] == "result" and e.get("agentId") in started
}
task = dict(line.split() for line in TASK_ANSWERS.read_text().splitlines() if line.strip())

answers_dir = OUT / "answers"
transcripts_dir = OUT / "transcripts"
answers_dir.mkdir(parents=True, exist_ok=True)
transcripts_dir.mkdir(parents=True, exist_ok=True)

records = []
problems_total = Counter()
for agent_id, start in sorted(started.items(), key=lambda kv: int(kv[1]["label"].split(":")[1])):
    path = WF / f"agent-{agent_id}.jsonl"
    meta = json.loads((WF / f"agent-{agent_id}.meta.json").read_text())
    data = path.read_bytes()
    lines = [json.loads(x) for x in data.decode("utf-8").splitlines() if x.strip()]
    prompt = lines[0]["message"]["content"]
    prompt = prompt if isinstance(prompt, str) else json.dumps(prompt)
    m_item = re.findall(r"item_id is ([0-9a-f]{16})", prompt)
    m_dirs = sorted(set(re.findall(r"q2m-iso/([0-9a-f]{16})/", prompt)))
    item = m_item[0] if len(m_item) == 1 else None
    folder = ISO / item if item else None
    problems: list[str] = []
    if item is None or m_dirs != [item]:
        problems.append(f"prompt does not name exactly one item: ids={m_item} dirs={m_dirs}")
    calls = []
    models = Counter()
    for entry in lines:
        msg = entry.get("message")
        if entry.get("type") == "assistant" and isinstance(msg, dict):
            mdl = msg.get("model")
            if isinstance(mdl, str):
                models[mdl] += 1
        for use in tool_uses(entry):
            name = use["name"]
            raw = use.get("input") or {}
            where = entry.get("type")
            if name == "Read":
                fp = raw.get("file_path")
                ok = folder is not None and inside(fp, folder)
                rel = (
                    os.path.relpath(os.path.realpath(fp), os.path.realpath(folder))
                    if ok
                    else str(fp)
                )
                extra = sorted(set(raw) - {"file_path"})
                calls.append(
                    {"tool": name, "path": rel, "inside": ok, "other_params": extra, "in": where}
                )
                if not ok:
                    problems.append(f"Read outside the item directory: {fp}")
            elif name == ANSWER_CHANNEL:
                calls.append(
                    {
                        "tool": name,
                        "item_id": raw.get("item_id"),
                        "answer": raw.get("answer"),
                        "in": where,
                    }
                )
            else:
                calls.append({"tool": name, "params": sorted(raw), "in": where})
                problems.append(f"tool {name} is not Read")
    so = [c for c in calls if c["tool"] == ANSWER_CHANNEL and c["in"] == "assistant"]
    if len(so) != 1:
        problems.append(f"{len(so)} StructuredOutput calls")
    so_answer = so[-1]["answer"] if so else None
    so_item = so[-1]["item_id"] if so else None
    if so and so_item != item:
        problems.append(f"StructuredOutput names item {so_item}, the prompt {item}")
    res = results.get(agent_id)
    if res is None:
        problems.append("no journal result")
    else:
        if res.get("item_id") != item:
            problems.append(f"journal result item {res.get('item_id')} != {item}")
        so_input = next(
            (
                u.get("input")
                for e in lines
                if e.get("type") == "assistant"
                for u in tool_uses(e)
                if u["name"] == ANSWER_CHANNEL
            ),
            None,
        )
        if so_input != res:
            problems.append("journal result differs from the transcript's StructuredOutput input")
    if task.get(item) != so_answer:
        problems.append(f"task answer {task.get(item)} != transcript answer {so_answer}")
    if set(models) != {"claude-opus-5-5"}:
        problems.append(f"models {dict(models)}")
    tools = Counter(c["tool"] for c in calls)
    void = bool(problems)
    for p in problems:
        problems_total[p.split(":")[0]] += 1
    # answer record (registered keys) and the transcript copy for ingest-isolated
    if item is not None and res is not None:
        rec = {k: res[k] for k in ("item_id", "answer", "reason", "model_id") if k in res}
        (answers_dir / f"{item}.json").write_text(json.dumps(rec, sort_keys=True) + "\n")
        shutil.copyfile(path, transcripts_dir / f"{item}.jsonl")
        assert sha((transcripts_dir / f"{item}.jsonl").read_bytes()) == sha(data)
    ts = [e.get("timestamp") for e in lines if e.get("timestamp")]
    named_pages: set[str] = set()
    if folder is not None and (folder / "pages").is_dir():
        named_pages = {f"pages/{p.name}" for p in (folder / "pages").iterdir()}
    opened = {c["path"] for c in calls if c["tool"] == "Read" and c["inside"]}
    records.append(
        {
            "label": start["label"],
            "agent_id": agent_id,
            "meta_description": meta.get("description"),
            "item_id": item,
            "transcript_file": path.name,
            "transcript_sha256": sha(data),
            "transcript_bytes": len(data),
            "transcript_lines": len(lines),
            "first_timestamp": min(ts) if ts else None,
            "last_timestamp": max(ts) if ts else None,
            "models": dict(models),
            "tool_counts": dict(tools),
            "tool_calls": [{k: v for k, v in c.items() if k not in ("answer",)} for c in calls],
            "reads_inside_item_dir": sum(1 for c in calls if c["tool"] == "Read" and c["inside"]),
            "reads_outside_item_dir": sum(
                1 for c in calls if c["tool"] == "Read" and not c["inside"]
            ),
            "packet_text_opened": "packet.txt" in opened,
            "pages_in_item_dir": len(named_pages),
            "pages_not_opened": len(named_pages - opened),
            "answer": so_answer,
            "strict_void": void,
            "strict_void_reasons": problems,
        }
    )

totals = {
    "raters": len(records),
    "items": len({r["item_id"] for r in records}),
    "strict_void": sum(r["strict_void"] for r in records),
    "problems": dict(problems_total),
    "tool_totals": dict(sum((Counter(r["tool_counts"]) for r in records), Counter())),
    "answers": dict(Counter(r["answer"] for r in records)),
    "reads_inside": sum(r["reads_inside_item_dir"] for r in records),
    "reads_outside": sum(r["reads_outside_item_dir"] for r in records),
    "packet_text_opened": sum(r["packet_text_opened"] for r in records),
    "raters_not_opening_every_page": sum(1 for r in records if r["pages_not_opened"]),
    "pages_not_opened": sum(r["pages_not_opened"] for r in records),
    "models": dict(sum((Counter(r["models"]) for r in records), Counter())),
    "first": min(r["first_timestamp"] for r in records),
    "last": max(r["last_timestamp"] for r in records),
}
audit = {
    "schema": "q2m-isolated-transcript-audit-v1",
    "workflow_run": WF.name,
    "iso_root": str(ISO),
    "rule": (
        "void (unsure) unless every tool call is Read on a path inside the agent's own "
        "item directory or the single StructuredOutput answer for its own item, the "
        "transcript names only claude-opus-5-5, and the answer equals the journal result "
        "and the handed-over list"
    ),
    "allowed_tools": sorted(ALLOWED),
    "task_answers_sha256": sha(TASK_ANSWERS.read_bytes()),
    "totals": totals,
    "raters": records,
}
(OUT / "strict-audit.json").write_text(json.dumps(audit, indent=1, sort_keys=True) + "\n")
print(json.dumps(totals, indent=1))
