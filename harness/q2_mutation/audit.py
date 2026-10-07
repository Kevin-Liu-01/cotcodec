"""Audit stages of the Q2 checker-mutation campaign: sample, packets, summary.

``sample`` (anywhere, stdlib only)
    From a scored mutation run (``score/outcomes.jsonl``, ``score/jobs-saved.jsonl``,
    ``prep/targets.jsonl``) and, optionally, the control run of the same split
    (``summary.json``, ``saved/jobs-saved.jsonl``): the candidate pool
    (``raters.audit_candidates``), the stratified sample with shams and every P1
    flip (``raters.draw_audit_sample``), Kevin's spot-check list, and one item
    per sampled key with the files the packet shows. ``sample.jsonl`` carries
    the labels and verdicts and never reaches a rater; ``items.jsonl`` holds
    only an opaque item id, the task and file paths.
``packets`` (LO-VM image: the VM's LibreOffice and ``pdftoppm``)
    One blind ``q2m-audit-packet-v1`` per item: the task instruction (sanitized
    export), every starting file of the task and every end-state file, each
    with its structure listing (``packets.structure_lines``), the end-state
    file's difference against the starting file, and page renders (100 dpi,
    at most 20 pages per file and ``MAX_PACKET_IMAGES`` per packet, end-state
    pages first). Packets are written to shards of at most ``--max-shard-bytes``
    so each fits a lane study artifact.
``summarize`` (anywhere)
    Both raters' call records -> answers -> ``raters.summarize`` with Kevin's
    blind adjudications: kappa, sham accuracy, S6 per label class, the K3/K4
    groups, P1 flip decisions, and ``decisions.jsonl`` (the final decision per
    mutant, which the headline analysis reads to gate P2 and P4).
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from harness.q2_mutation import raters
from harness.q2_mutation.packets import (
    RENDER_DPI,
    RENDER_PAGES,
    artifacts,
    structure_lines,
)

PACKET_SCHEMA = "q2m-audit-packet-v1"
MAX_PACKET_IMAGES = 40
MAX_SHARD_BYTES = 480 * 1024**2
RENDER_SUFFIXES = frozenset({".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".pdf"})
IMAGE_MEDIA = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAX_IMAGE_BYTES = 4 * 1024**2
RENDER_TIMEOUT_S = 180


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remap(path: str | None, mapping: Sequence[tuple[str, str]]) -> str | None:
    if path is None:
        return None
    for old, new in mapping:
        if path.startswith(old):
            return new + path[len(old) :]
    return path


def task_initial_files(
    sanitized_dir: Path, file_cache: Path, task_id: str
) -> dict[str, str | None]:
    """VM path -> local file-cache path of every starting file of a task."""
    from harness.q2_mutation.offline_eval import file_cache_local
    from harness.q2_mutation.tasks import resolve_vm_path

    task = json.loads((sanitized_dir / f"{task_id}.json").read_text(encoding="utf-8"))
    out: dict[str, str | None] = {}
    for entry in task.get("initial_files") or []:
        vm = resolve_vm_path(str(entry["path_in_vm"]))
        try:
            out[vm] = str(file_cache_local(file_cache, str(entry["url"])))
        except Exception:  # noqa: BLE001 - a missing cache file is shown as absent
            out[vm] = None
    return out


# --- sample -------------------------------------------------------------------


def build_sample(
    outcomes: Sequence[Mapping[str, Any]],
    saved_jobs: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    *,
    initial_of: Any,
    controls_tasks: Mapping[str, Mapping[str, Any]] | None = None,
    controls_saved: Sequence[Mapping[str, Any]] = (),
    path_map: Sequence[tuple[str, str]] = (),
    primary: str = "lock",
    seed: int = 42,
) -> dict[str, Any]:
    """Sample rows, item rows and the spot-check list of one audit.

    ``initial_of(task_id)`` returns the task's starting files (VM path -> local
    path). The P1 flips are the control run's flips under ``primary``
    (``report.p1_flip_tasks``).
    """
    from harness.q2_mutation.report import p1_flip_tasks

    pool = raters.audit_candidates(outcomes, primary)
    flips = p1_flip_tasks(controls_tasks, primary) if controls_tasks else []
    sample = raters.draw_audit_sample(pool, seed=seed, p1_flip_tasks=flips)
    by_id = {r["mutant_id"]: r for r in outcomes}
    saved = {job["mutant_id"]: job for job in saved_jobs}
    nulls: dict[str, list[Mapping[str, Any]]] = {}
    for job in saved_jobs:
        if job.get("kind") == "null":
            nulls.setdefault(str(job["task_id"]), []).append(job)
    targets_by_task: dict[str, list[Mapping[str, Any]]] = {}
    for target in targets:
        targets_by_task.setdefault(str(target["task_id"]), []).append(target)
    gold_saved = {str(job["task_id"]): job for job in controls_saved if job.get("kind") == "gold"}

    def files(job: Mapping[str, Any]) -> dict[str, str | None]:
        return {vm: remap(local, path_map) for vm, local in sorted(job["files"].items())}

    rows: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for entry in sample:
        item_id = raters.opaque_item_id(entry.mutant_id, seed)
        row: dict[str, Any] = {
            **dataclasses.asdict(entry),
            "item_id": item_id,
            "label": None,
            "verdict": None,
        }
        if entry.stratum in raters.STRATA:
            outcome = by_id[entry.mutant_id]
            row["label"] = outcome["label"]
            row["verdict"] = outcome[f"{primary}_verdict"]
            candidate = files(saved[entry.mutant_id])
        elif entry.sham == "gold":
            null = sorted(nulls[entry.task_id], key=lambda j: str(j["mutant_id"]))[0]
            candidate = files(null)
        elif entry.sham == "do_nothing":
            paths = sorted(
                {
                    str(vm)
                    for target in targets_by_task.get(entry.task_id, [])
                    for vm in [target["vm_path"], *target["context_files"]]
                }
            )
            start = initial_of(entry.task_id)
            candidate = {vm: start.get(vm) for vm in paths}
        else:  # p1_flip
            candidate = files(gold_saved[entry.task_id])
        rows.append(row)
        items.append(
            {
                "item_id": item_id,
                "task_id": entry.task_id,
                "candidate": candidate,
                "initial": initial_of(entry.task_id),
            }
        )
    spot = raters.human_spot_check(sample, seed=seed)
    return {
        "sample": rows,
        "items": sorted(items, key=lambda r: r["item_id"]),
        "spot_check": [raters.opaque_item_id(s.mutant_id, seed) for s in spot],
        "summary": {
            "primary": primary,
            "seed": seed,
            "pool": len(pool),
            "pool_by_label": dict(Counter(c.label for c in pool)),
            "strata": dict(Counter(s.stratum for s in sample)),
            "p1_flip_tasks": flips,
            "spot_check": len(spot),
        },
    }


def cmd_sample(args: argparse.Namespace) -> int:
    from harness.q2_mutation.report import summarize_run

    run = Path(args.run)
    mapping = [tuple(item.split("=", 1)) for item in args.path_map]
    controls_tasks = None
    controls_saved: list[dict[str, Any]] = []
    if args.controls:
        controls_tasks = summarize_run(Path(args.controls))["tasks"]
        controls_saved = read_jsonl(Path(args.controls) / "saved" / "jobs-saved.jsonl")
    sanitized = Path(args.sanitized)
    cache = Path(args.file_cache)
    built = build_sample(
        read_jsonl(run / "score" / "outcomes.jsonl"),
        read_jsonl(run / "score" / "jobs-saved.jsonl"),
        read_jsonl(run / "prep" / "targets.jsonl"),
        initial_of=lambda task: task_initial_files(sanitized, cache, task),
        controls_tasks=controls_tasks,
        controls_saved=controls_saved,
        path_map=mapping,
        primary=args.primary,
        seed=args.seed,
    )
    out = Path(args.out)
    digests = {
        "sample.jsonl": write_jsonl(out / "sample.jsonl", built["sample"]),
        "items.jsonl": write_jsonl(out / "items.jsonl", built["items"]),
        "spot-check.jsonl": write_jsonl(
            out / "spot-check.jsonl", [{"item_id": i} for i in built["spot_check"]]
        ),
    }
    summary = {**built["summary"], "files_sha256": digests}
    (out / "sample-summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


# --- packets ------------------------------------------------------------------


def _page_entries(paths: Sequence[Path], limit: int) -> list[dict[str, Any]]:
    entries = []
    for number, path in enumerate(paths[:limit], 1):
        data = path.read_bytes()
        entries.append(
            {
                "page": number,
                "of": len(paths),
                "media_type": "image/png",
                "sha256": hashlib.sha256(data).hexdigest(),
                "data_b64": base64.b64encode(data).decode("ascii"),
            }
        )
    return entries


def render_pages(document: Path, work: Path, profile_home: Path) -> list[Path]:
    """PNG pages (100 dpi, at most 20) of an office file or PDF; [] if it cannot render."""
    work.mkdir(parents=True, exist_ok=True)
    suffix = document.suffix.lower()
    if suffix == ".pdf":
        pdf = document
    else:
        local = work / f"doc{suffix}"
        shutil.copyfile(document, local)
        env = {**os.environ, "HOME": str(profile_home)}
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                str(work),
                str(local),
            ],
            env=env,
            capture_output=True,
            timeout=RENDER_TIMEOUT_S,
            check=False,
        )
        pdf = work / "doc.pdf"
        if not pdf.is_file():
            return []
    subprocess.run(
        [
            "pdftoppm",
            "-r",
            str(RENDER_DPI),
            "-l",
            str(RENDER_PAGES),
            "-png",
            str(pdf),
            str(work / "page"),
        ],
        capture_output=True,
        timeout=RENDER_TIMEOUT_S,
        check=False,
    )
    return sorted(work.glob("page*.png"), key=lambda p: (len(p.name), p.name))


def _file_pages(local: str | None, work: Path, home: Path) -> tuple[list[Path], list[str]]:
    if local is None:
        return [], []
    path = Path(local)
    suffix = path.suffix.lower()
    if suffix in IMAGE_MEDIA:
        if path.stat().st_size > MAX_IMAGE_BYTES:
            return [], ["image file over the packet's size limit; not shown"]
        return [path], []
    if suffix in RENDER_SUFFIXES:
        pages = render_pages(path, work, home)
        return pages, ([] if pages else ["the file could not be rendered"])
    return [], []


def build_packet(item: Mapping[str, Any], instruction: str, work: Path) -> dict[str, Any]:
    """One blind packet: instruction, starting files, end-state files, renders."""
    home = work / "home"
    home.mkdir(parents=True, exist_ok=True)
    initial = {vm: local for vm, local in item["initial"].items() if local is not None}
    candidate = dict(item["candidate"])
    budget = MAX_PACKET_IMAGES
    end_files = []
    for index, (vm, entry) in enumerate(sorted(artifacts(initial, candidate).items())):
        pages, notes = _file_pages(candidate.get(vm), work / f"end{index}", home)
        shown = _page_entries(pages, min(RENDER_PAGES, budget))
        budget -= len(shown)
        if len(shown) < len(pages):
            notes.append(f"{len(pages) - len(shown)} more rendered pages not shown (image cap)")
        end_files.append({"vm_path": vm, **entry, "pages": shown, "notes": notes})
    start_files = []
    for index, vm in enumerate(sorted(item["initial"])):
        local = item["initial"][vm]
        structure = structure_lines(Path(local)) if local else ["file absent at the start"]
        pages, notes = _file_pages(local, work / f"start{index}", home)
        shown = _page_entries(pages, min(RENDER_PAGES, budget))
        budget -= len(shown)
        if len(shown) < len(pages):
            notes.append(f"{len(pages) - len(shown)} more rendered pages not shown (image cap)")
        start_files.append({"vm_path": vm, "structure": structure, "pages": shown, "notes": notes})
    packet = raters.make_packet(
        raters.Sampled(item["item_id"], item["task_id"], "packet", 1.0),
        instruction=instruction,
        initial_files=start_files,
        candidate_artifacts={"files": end_files},
        seed=0,
    )
    # The item id is already opaque; keep it rather than hashing it again.
    packet["item_id"] = item["item_id"]
    packet["schema"] = PACKET_SCHEMA
    return packet


def cmd_packets(args: argparse.Namespace) -> int:
    items = read_jsonl(Path(args.items))
    sanitized = Path(args.sanitized)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="q2m-packets-"))

    def one(index_item: tuple[int, Mapping[str, Any]]) -> dict[str, Any]:
        index, item = index_item
        task = json.loads((sanitized / f"{item['task_id']}.json").read_text(encoding="utf-8"))
        work = scratch / f"item{index}"
        try:
            return build_packet(item, str(task["instruction"]), work)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        packets = list(pool.map(one, enumerate(items)))
    shards: list[dict[str, Any]] = []
    current: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal current, size
        if not current:
            return
        path = out / f"packets-{len(shards):03d}.jsonl"
        text = "".join(current)
        path.write_text(text, encoding="utf-8")
        shards.append(
            {
                "path": path.name,
                "items": len(current),
                "bytes": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
        current, size = [], 0

    for packet in sorted(packets, key=lambda p: p["item_id"]):
        line = json.dumps(packet, sort_keys=True, ensure_ascii=False) + "\n"
        if current and size + len(line.encode("utf-8")) > args.max_shard_bytes:
            flush()
        current.append(line)
        size += len(line.encode("utf-8"))
    flush()
    shutil.rmtree(scratch, ignore_errors=True)
    images = Counter(
        len(f["pages"]) for p in packets for f in [*p["initial_files"], *p["candidate"]["files"]]
    )
    manifest = {
        "schema": PACKET_SCHEMA,
        "items": len(packets),
        "shards": shards,
        "images_per_file": dict(sorted(images.items())),
        "render": {
            "dpi": RENDER_DPI,
            "pages_per_file": RENDER_PAGES,
            "images_per_packet": MAX_PACKET_IMAGES,
        },
    }
    (out / "packets-manifest.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, sort_keys=True))
    return 0


# --- summarize ----------------------------------------------------------------


def load_sample(path: Path) -> tuple[list[raters.Sampled], dict[str, str], dict[str, str]]:
    """Sampled entries, labels per key and item id per key from ``sample.jsonl``."""
    sample, labels, item_of = [], {}, {}
    for row in read_jsonl(path):
        sample.append(
            raters.Sampled(
                row["mutant_id"],
                row["task_id"],
                row["stratum"],
                row["inclusion_probability"],
                row.get("sham"),
            )
        )
        if row.get("label"):
            labels[row["mutant_id"]] = row["label"]
        item_of[row["mutant_id"]] = row["item_id"]
    return sample, labels, item_of


def summary_dict(summary: raters.AuditSummary) -> dict[str, Any]:
    data = dataclasses.asdict(summary)
    data.pop("decisions")
    return data


def cmd_summarize(args: argparse.Namespace) -> int:
    from harness.q2_mutation.rater_runner import answers

    sample, labels, item_of = load_sample(Path(args.sample))
    first = answers(Path(args.calls[0]), item_of.values())
    second = answers(Path(args.calls[1]), item_of.values())
    ratings = {key: (first[item][0], second[item][0]) for key, item in item_of.items()}
    adjudicated: dict[str, str] = {}
    if args.adjudications:
        key_of = {item: key for key, item in item_of.items()}
        for row in read_jsonl(Path(args.adjudications)):
            adjudicated[key_of[row["item_id"]]] = row["answer"]
    summary = raters.summarize(
        sample, labels, ratings, adjudicated=adjudicated, n_boot=args.n_boot, seed=args.seed
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    statuses = {
        rid: dict(Counter(status for _, status in calls.values()))
        for rid, calls in zip(raters.RATER_IDS, (first, second), strict=True)
    }
    result = {
        **summary_dict(summary),
        "raters": [dict(r) for r in raters.RATERS],
        "answer_status": statuses,
        "human_spot_check": "pending",
        "label": "model raters (decisions D9, D23); the human spot check is pending",
    }
    (out / "audit-summary.json").write_text(
        json.dumps(result, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    write_jsonl(
        out / "decisions.jsonl",
        [
            {"key": key, "decision": decision, "first": ratings[key][0], "second": ratings[key][1]}
            for key, decision in sorted(summary.decisions.items())
        ],
    )
    print(
        json.dumps(
            {k: result[k] for k in ("kappa", "k3_fires", "k4_fires", "n_items")},
            sort_keys=True,
            default=str,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    sample = sub.add_parser("sample", allow_abbrev=False)
    sample.add_argument("--run", required=True, help="scored mutation run directory")
    sample.add_argument("--controls", help="control run directory of the same split")
    sample.add_argument("--sanitized", required=True, help="sanitized task export directory")
    sample.add_argument("--file-cache", required=True, help="file-cache files directory")
    sample.add_argument("--out", required=True)
    sample.add_argument("--path-map", action="append", default=[], help="OLD=NEW path prefix")
    sample.add_argument("--primary", default="lock")
    sample.add_argument("--seed", type=int, default=42)
    packets = sub.add_parser("packets", allow_abbrev=False)
    packets.add_argument("--items", required=True)
    packets.add_argument("--sanitized", required=True)
    packets.add_argument("--out", required=True)
    packets.add_argument("--workers", type=int, default=4)
    packets.add_argument("--max-shard-bytes", type=int, default=MAX_SHARD_BYTES)
    summ = sub.add_parser("summarize", allow_abbrev=False)
    summ.add_argument("--sample", required=True)
    summ.add_argument(
        "--calls",
        nargs=2,
        required=True,
        help="calls.jsonl of the Anthropic rater, then of the open-weight rater",
    )
    summ.add_argument("--adjudications", help="JSONL of Kevin's blind answers: item_id, answer")
    summ.add_argument("--out", required=True)
    summ.add_argument("--n-boot", type=int, default=10_000)
    summ.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    return {"sample": cmd_sample, "packets": cmd_packets, "summarize": cmd_summarize}[args.command](
        args
    )


if __name__ == "__main__":
    raise SystemExit(main())
