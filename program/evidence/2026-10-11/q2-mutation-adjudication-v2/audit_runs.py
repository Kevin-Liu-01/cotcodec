"""Equivalent isolation audit of one D81 adjudication workflow run (no frozen code changed).

Adjudicated by an isolated model on the owner's instruction (D80); not
human-validated.

The registered audit is ``rater_runner collect-transcripts`` followed by
``rater_runner ingest-isolated`` (section 9 of q2-evaluator-mutation-v1). Two
of its fixed parameters do not fit two of D81's runs, for reasons that are not
isolation failures:

- run (b) uses ``claude-fable-5-1``; ``ingest_isolated`` refuses the whole
  ingest when a transcript names any model other than ``claude-opus-5-5``
  (``ANTHROPIC["model"]``, the registered rater's pin);
- run (c) starts each agent with the rendered template plus D81's fixed
  notation sentence; ``collect_transcripts`` maps a transcript to its item
  only when a user turn is the bare rendered template, so it refuses every
  transcript of that run.

This script applies the same checks by calling the frozen functions of a git
archive of ``65bc2e2`` (imported from ``--src``, never edited or patched at
run time) with the two parameters made explicit: ``--model`` (the model every
agent turn must name) and ``--suffix-file`` (text appended to the rendered
template, which becomes the expected task turn). With ``--model
claude-opus-5-5`` and no suffix it is the registered audit; the README shows
that it reproduces the frozen ingest on run (a) and on the 2026-10-08 rating.

Checks, in the order the frozen collector and ingest apply them:
collector (``collect_transcripts``): export manifest schema and template
digest; the journal read by ``read_journal`` (no agent started twice, no
result for an unstarted agent); every ``agent-*.jsonl`` belongs to a started
agent and every started agent has one; each transcript maps to exactly one
exported item by its task turn (``task_text`` of ``_text_user_turns``).
Ingest (``ingest_isolated``): each exported packet's rebuilt request equals
the export (with ``--packets``); answer records hold only registered keys,
name an exported item, once; the item directory re-hashes equal to the
export (``hash_tree``); every transcript of the item passes
``audit_transcript`` with the expected task turn and the export's item ids
(shell calls, tools other than Read and the neutral ones, Read paths outside
the item directory, user turns other than the task turn and one relay frame,
unregistered entry or attachment types, a structured answer naming another
item, the packet not read); at most one transcript answers (an attempt
without a journal result only through a structured answer); the answer is
the one the answering transcript returned (``_answer_source``); a record's
``model_id``, if any, is ``--model``; every agent turn names ``--model`` (the
frozen ingest refuses the whole run otherwise; this script lists each such
transcript under ``refusals``); relay frames byte-identical across the run.

Writes counts, digests, void reasons (tool names and paths) and answers only;
no reason text and no document content. Standard library only:

    python audit_runs.py --src <archive of 65bc2e2> --run-dir <workflow run dir> \
        --manifest <iso-manifest.json> --iso-root <isolation root> \
        --answers <dir of <item_id>.json> --model claude-opus-5-5 \
        [--suffix-file <text appended to the rendered template>] \
        [--packets <shard> ...] --out <audit.json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

LABEL = "adjudicated by an isolated model on the owner's instruction (D80); not human-validated"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--iso-root", type=Path, required=True)
    ap.add_argument("--answers", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--suffix-file", type=Path)
    ap.add_argument("--packets", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    sys.path.insert(0, str(args.src.resolve()))
    from harness.q2_mutation import rater_runner as rr  # the frozen module, unmodified

    suffix = args.suffix_file.read_text(encoding="utf-8") if args.suffix_file else ""
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema") != rr.ISOLATED_SCHEMA:
        raise SystemExit("not a q2m isolated export manifest")
    if manifest.get("prompt_template_sha256") not in (None, rr.ISOLATED_PROMPT_TEMPLATE_SHA256):
        raise SystemExit("the export registered another rater prompt template")
    exported = dict(manifest["items"])

    # Packets (ingest): every exported item's rebuilt request equals the export.
    packets_checked = None
    if args.packets:
        by_id = {str(p["item_id"]): p for p in rr._load_shards(args.packets)}
        for item, entry in exported.items():
            if item not in by_id:
                raise SystemExit(f"exported item {item} is not in the packets")
            body = rr.sha256_bytes(rr.canonical_bytes(rr.isolated_body(by_id[item])))
            if body != entry["body_sha256"]:
                raise SystemExit(f"item {item}: the packet differs from the exported file")
        packets_checked = [
            {"path": str(p), "sha256": rr.sha256_file(p)} for p in args.packets
        ]

    # Collector: expected task turn per item, journal, transcripts, mapping.
    expected: dict[str, str] = {}
    by_text: dict[str, str] = {}
    for item, entry in exported.items():
        rendered = rr.render_isolated_prompt(f"{manifest['iso_root']}/{entry['dir']}", str(item))
        if entry.get("prompt_sha256") not in (None, rr.sha256_bytes(rendered.encode("utf-8"))):
            raise SystemExit(f"item {item}: the rendered prompt differs from the export's")
        expected[item] = rendered + suffix
        by_text[rr._normalized_prompt(expected[item])] = str(item)
    journal = args.run_dir / rr.JOURNAL
    started, answered = rr.read_journal(journal)
    files: dict[str, Path] = {}
    for path in sorted(args.run_dir.rglob("agent-*.jsonl")):
        match = rr.AGENT_TRANSCRIPT.match(path.name)
        if match is None or not path.is_file():
            raise SystemExit(f"{path}: not an agent transcript of the run")
        if match.group(1) in files:
            raise SystemExit(f"agent {match.group(1)} has two transcripts")
        files[match.group(1)] = path
    unstarted = sorted(set(files) - set(started))
    missing = [a for a in started if a not in files]
    if unstarted or missing:
        raise SystemExit(f"unstarted transcripts {unstarted[:5]}, started without one {missing[:5]}")
    agents: list[dict] = []
    for agent in started:
        data = files[agent].read_bytes()
        bodies = (rr.task_text(turn) for turn in rr._text_user_turns(data))
        items = sorted({by_text[b] for b in bodies if b in by_text})
        if len(items) != 1:
            raise SystemExit(f"agent {agent}: maps to {items[:3] or 'no exported item'}")
        agents.append(
            {"agent_id": agent, "item_id": items[0], "path": files[agent], "data": data,
             "answered": agent in answered}
        )
    by_item: dict[str, list[dict]] = {}
    for row in agents:
        by_item.setdefault(row["item_id"], []).append(row)

    # Ingest: answer records, tree re-hash, transcript audit, answer source, model.
    records, answer_digests = rr.isolated_answers(args.answers)
    seen: set[str] = set()
    relay_frames: Counter[str] = Counter()
    attachments: Counter[str] = Counter()
    rows: list[dict] = []
    refusals: list[str] = []
    for number, rec in enumerate(records):
        if not isinstance(rec, dict) or set(rec) - rr.ISOLATED_ANSWER_KEYS or "item_id" not in rec:
            raise SystemExit(f"record {number}: keys must be within {sorted(rr.ISOLATED_ANSWER_KEYS)}")
        item = str(rec["item_id"])
        if item not in exported:
            raise SystemExit(f"record {number}: item {item} was not exported")
        if item in seen:
            raise SystemExit(f"record {number}: a second answer for item {item}")
        seen.add(item)
        entry = exported[item]
        folder = args.iso_root / entry["dir"]
        void: list[str] = []
        current = rr.hash_tree(folder) if folder.is_dir() else None
        if current is None:
            void.append("the item directory is missing")
        elif current != entry["files"]:
            void.append("the item directory differs from its export")
        audited = []
        for row in by_item.get(item, []):
            result = rr.audit_transcript(
                row["data"], folder, item_id=item, expected_prompt=expected[item],
                item_ids=exported,
            )
            result["journal_result"] = row["answered"]
            if not row["answered"]:
                result["answers"] = bool(result["structured_answers"])
            others = sorted(set(result["models"]) - {args.model})
            if others:
                refusals.append(f"item {item}: transcript names model(s) {others}, not {args.model!r}")
            audited.append((row, result))
            relay_frames.update(result["relay_frames_sha256"])
            attachments.update(result["attachment_types"])
        answering = [a for a in audited if a[1]["answers"]]
        primary = answering[0] if answering else (audited[0] if len(audited) == 1 else None)
        if not audited:
            void.append("no harness transcript for this item")
        elif len(answering) > 1:
            void.append(f"{len(answering)} transcripts of this item answer; at most one may")
        elif primary is None:
            void.append("no transcript of this item answers")
        for row, result in audited:
            keep = [r for r in result["void_reasons"]
                    if (primary is not None and row is primary[0]) or r not in rr.ANSWER_ONLY_REASONS]
            void.extend(keep)
        audit = primary[1] if primary else {"models": {}, "tool_calls": {}, "void_reasons": []}
        answer = rec.get("answer") if isinstance(rec.get("answer"), str) else None
        source = rr._answer_source(answer or "", audit) if primary is not None else None
        if primary is not None and source == "not_found":
            void.append("the answer is not the one the transcript returned")
        claimed = rec.get("model_id")
        if claimed is not None and audit["models"] and claimed != args.model:
            void.append(f"the record claims model {claimed!r}; the transcript names {args.model!r}")
        images = [i["name"] for i in entry["images"]]
        opened = set()
        packet_reads = 0
        for row, _ in audited:
            for line in row["data"].decode("utf-8", errors="replace").splitlines():
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                for use in rr._tool_uses(e):
                    if use.get("name") == "Read" and isinstance(use.get("input"), dict):
                        p = str(use["input"].get("file_path", ""))
                        base = f"{folder}/"
                        if p.startswith(base):
                            opened.add(p[len(base):])
                        packet_reads += p == f"{folder}/{rr.ISOLATED_TEXT}"
        rows.append(
            {
                "item_id": item,
                "outcome": "isolation_void" if void else "ok",
                "answer": rr.answer_for("isolation_void" if void else "ok", answer)[0],
                "answer_given": answer,
                "void_reasons": void,
                "answer_source": source,
                "tree_rehashed_equals_export": current == entry["files"],
                "transcripts": [
                    {"agent_id": row["agent_id"], "sha256": sha256_bytes(row["data"]),
                     "bytes": len(row["data"]), "journal_result": row["answered"],
                     "answers": result["answers"], "models": result["models"],
                     "tool_calls": result["tool_calls"], "user_turns": result["user_turns"],
                     "task_turns": result["task_turns"], "other_user_turns": result["other_user_turns"],
                     "relay_frames": result["relay_frames"], "packet_read": result["packet_read"],
                     "attachment_types": result["attachment_types"]}
                    for row, result in audited
                ],
                "page_images": len(images),
                "page_images_opened": sum(1 for n in images if n in opened),
                "packet_reads": packet_reads,
                "answer_file_sha256": answer_digests.get(f"{item}.json"),
            }
        )
    if len(relay_frames) > 1:
        for row in rows:
            if any(t["relay_frames"] for t in row["transcripts"]):
                row["void_reasons"].append(rr.RELAY_MISMATCH)
                row["outcome"], row["answer"] = "isolation_void", "unsure"
    agents_of_unanswered = sorted(i for i in by_item if i not in seen)
    out = {
        "schema": "q2m-d81-run-audit-v1",
        "label": LABEL,
        "frozen_source": str(args.src),
        "template_sha256": rr.ISOLATED_PROMPT_TEMPLATE_SHA256,
        "suffix_sha256": sha256_bytes(suffix.encode("utf-8")) if suffix else None,
        "suffix": suffix or None,
        "model_required": args.model,
        "run_dir": str(args.run_dir),
        "journal_sha256": rr.sha256_file(journal),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "packets_checked": packets_checked,
        "agents_started": len(started),
        "agents_with_result": len(answered),
        "items_mapped": len(by_item),
        "items_with_answer_record": len(seen),
        "transcripts_of_items_without_answer_record": agents_of_unanswered,
        "refusals": refusals,
        "outcomes": dict(Counter(r["outcome"] for r in rows)),
        "answers": dict(Counter(r["answer"] for r in rows)),
        "models": dict(sum((Counter(t["models"]) for r in rows for t in r["transcripts"]), Counter())),
        "tool_calls": dict(sum((Counter(t["tool_calls"]) for r in rows for t in r["transcripts"]), Counter())),
        "attachment_types": dict(sorted(attachments.items())),
        "unregistered_attachment_types": sorted(set(attachments) - set(rr.HARNESS_ATTACHMENT_TYPES)),
        "relay_frames": dict(relay_frames),
        "page_images": sum(r["page_images"] for r in rows),
        "page_images_opened": sum(r["page_images_opened"] for r in rows),
        "items_opening_every_page_image": sum(r["page_images_opened"] == r["page_images"] for r in rows),
        "items": sorted(rows, key=lambda r: r["item_id"]),
    }
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("agents_started", "items_mapped", "outcomes", "answers",
                                          "models", "tool_calls", "refusals",
                                          "unregistered_attachment_types", "relay_frames")},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
