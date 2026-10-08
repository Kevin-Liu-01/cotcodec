"""Audit stages of the Q2 checker-mutation campaign: sample, packets, summary.

``sample`` (anywhere, stdlib only)
    From a scored mutation run (``score/outcomes.jsonl``, ``score/jobs-saved.jsonl``,
    ``prep/targets.jsonl``) and the control runs whose P1 flips are audited
    (``summary.json``, ``saved/jobs-saved.jsonl``; for the confirmatory audit
    the confirm and the reserve control runs): the candidate pool
    (``raters.audit_candidates``), the stratified sample with shams and every P1
    flip (``raters.draw_audit_sample``), Kevin's spot-check list, and one item
    per sampled key with the files the packet shows. ``sample.jsonl`` carries
    the labels and verdicts and never reaches a rater; ``items.jsonl`` holds
    only an opaque item id, the task and file paths. Item ids are salted with
    the audit's secret salt (``--salt-file``, decision D34); the summary
    records only the salt's SHA-256.
``reach.sh`` on ``baseline-jobs.jsonl`` (LO-VM image)
    The saved starting files: the GUI-faithful save stage on each mutation
    target's starting files, with the target's own starting file as the build
    saved it through ``uno_apply.py`` (``prep/<target>/initial``), so the
    baseline went through the same LibreOffice steps as a mutant and its null
    mutant (one UNO save, then the save stage). P1 flips and do-nothing shams
    use the control run's saved do-nothing files, which went through the same
    single save stage as the saved gold.
``packets`` (LO-VM image: the VM's LibreOffice and ``pdftoppm``)
    One blind ``q2m-audit-packet-v1`` per item: the task instruction (sanitized
    export), every starting file of the task and every end-state file, each
    with its structure listing (``packets.structure_lines``), the end-state
    file's difference against the saved starting file (``packets.artifacts``;
    the raw starting file only where no saved one exists, which the packet
    says), and page renders (100 dpi, at most 20 pages per file and
    ``MAX_PACKET_IMAGES`` per packet, end-state pages first). Each packet is
    fitted to the registered token budget (``fit_packet``: listings are
    shortened, starting-file listings first, and every cut is recorded in the
    packet and stated to the rater). Packets are written to shards of at most
    ``--max-shard-bytes`` so each fits a lane study artifact.
``summarize`` (anywhere)
    Both raters' call records (one ``calls.jsonl`` per shard and rater,
    merged; an item rated in two shards is refused) -> answers ->
    ``raters.summarize`` with Kevin's blind adjudications: kappa, sham
    accuracy, S6 per label class, the K3/K4 groups, P1 flip decisions, and
    ``decisions.jsonl`` (the final decision per mutant, which the headline
    analysis reads to gate P2 and P4), the gold defects (D34) and Kevin's
    blind adjudication pool (``adjudication-pool.jsonl``: item ids only, in
    the pool's seeded order; ``raters.adjudication_pool``).
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import hashlib
import json
import math
import os
import posixpath
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

# Registered packet budget (preregistration section 9). Every packet must fit
# the open-weight rater's context window (``rater_runner.ENGINE_FLAGS``
# max_model_len 139,264 since decision D34) with its reply (``max_tokens``
# 8,192: thinking and answer) and a fixed allowance for the system prompt, chat
# template and answer line. Prompt size is estimated before any rater sees the
# packet: text at 0.55 tokens per UTF-8 byte (the dev smoke measured at most
# 0.49 for these listings with Qwen3.5's tokenizer) and each image at one token
# per 32 x 32 pixel cell plus two.
CONTEXT_TOKENS = 139_264
ANSWER_TOKENS = 8_192
OVERHEAD_TOKENS = 2_048
PACKET_TOKEN_BUDGET = CONTEXT_TOKENS - ANSWER_TOKENS - OVERHEAD_TOKENS
TEXT_TOKENS_PER_BYTE = 0.55
IMAGE_CELL_PX = 32
MIN_SECTION_LINES = 50
FIT_NOTE = "lines not shown: shortened to fit the rater's context window"


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


OFFICE_FAMILIES = ("xlsx", "docx", "pptx")


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
    salt: str,
    build_root: str = "/ro/build/",
) -> dict[str, Any]:
    """Sample rows, item rows, saved-baseline jobs and the spot-check list of one audit.

    ``salt`` is the audit's secret salt (``raters.opaque_item_id``): item ids
    cannot be computed from public mutant or task ids without it.

    ``initial_of(task_id)`` returns the task's starting files (VM path -> local
    path). The P1 flips are the control run's flips under ``primary``
    (``report.p1_flip_tasks``).

    Each item names the starting files its packet compares with
    (``baseline``), saved through the same LibreOffice steps as the item's
    end state:

    * a mutant or a gold sham (the saved null mutant): ``baseline_job``, a
      save-stage job (``reach.sh``) on the target's starting files, the target
      file taken as the build saved it through ``uno_apply.py``
      (``<build_root>prep/<target>/initial/<name>``), the other files raw, as
      the mutant's context files are;
    * a P1 flip (the control's saved gold) or a do-nothing sham: the control
      run's saved do-nothing files (one save stage, as the saved gold). The
      do-nothing sham's end state is that saved do-nothing itself, the end
      state the checker reads when nothing is done.
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
    by_target = {str(t["target_id"]): t for t in targets if t.get("target_id")}
    gold_saved = {str(job["task_id"]): job for job in controls_saved if job.get("kind") == "gold"}
    initial_saved = {
        str(job["task_id"]): job for job in controls_saved if job.get("kind") == "initial"
    }
    baseline_jobs: dict[str, dict[str, Any]] = {}

    def files(job: Mapping[str, Any]) -> dict[str, str | None]:
        return {vm: remap(local, path_map) for vm, local in sorted(job["files"].items())}

    def mutation_baseline(target_id: str | None) -> str | None:
        """Save-stage job of one target's starting files (UNO-saved target file)."""
        target = by_target.get(str(target_id)) if target_id else None
        if target is None:
            return None
        job_id = f"baseline__{target['target_id']}"
        if job_id in baseline_jobs:
            return job_id
        start = initial_of(str(target["task_id"]))
        vm_target = str(target["vm_path"])
        chosen: dict[str, str] = {}
        for vm in sorted({vm_target, *target.get("context_files", {})}):
            if vm != vm_target:
                if start.get(vm):
                    chosen[vm] = str(start[vm])
                continue
            if not target.get("initial"):
                continue
            if target.get("family") in OFFICE_FAMILIES:
                name = posixpath.basename(vm_target)
                prep = f"{build_root.rstrip('/')}/prep/{target['target_id']}/initial/{name}"
                chosen[vm] = str(remap(prep, path_map))
            else:
                chosen[vm] = str(start.get(vm) or remap(str(target["initial"]), path_map))
        if not chosen:
            return None
        baseline_jobs[job_id] = {
            "job_id": job_id,
            "mutant_id": job_id,
            "task_id": str(target["task_id"]),
            "target_id": str(target["target_id"]),
            "kind": "baseline",
            "files": chosen,
        }
        return job_id

    rows: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for entry in sample:
        item_id = raters.opaque_item_id(entry.mutant_id, salt)
        row: dict[str, Any] = {
            **dataclasses.asdict(entry),
            "item_id": item_id,
            "label": None,
            "verdict": None,
        }
        baseline: dict[str, str | None] | None = None
        baseline_job: str | None = None
        control_initial = initial_saved.get(entry.task_id)
        if entry.stratum in raters.STRATA:
            outcome = by_id[entry.mutant_id]
            row["label"] = outcome["label"]
            row["verdict"] = outcome[f"{primary}_verdict"]
            candidate = files(saved[entry.mutant_id])
            baseline_job = mutation_baseline(outcome.get("target_id"))
        elif entry.sham == "gold":
            null = sorted(nulls[entry.task_id], key=lambda j: str(j["mutant_id"]))[0]
            candidate = files(null)
            baseline_job = mutation_baseline(null.get("target_id"))
        elif entry.sham == "do_nothing":
            paths = sorted(
                {
                    str(vm)
                    for target in targets_by_task.get(entry.task_id, [])
                    for vm in [target["vm_path"], *target["context_files"]]
                }
            )
            start = initial_of(entry.task_id)
            if control_initial is not None:
                done = files(control_initial)
                candidate = {vm: done.get(vm, start.get(vm)) for vm in paths}
                baseline = {vm: path for vm, path in candidate.items() if path}
            else:
                candidate = {vm: start.get(vm) for vm in paths}
        else:  # p1_flip
            candidate = files(gold_saved[entry.task_id])
            if control_initial is not None:
                baseline = {vm: p for vm, p in files(control_initial).items() if p}
        rows.append(row)
        source = "mutation_save_stage" if baseline_job else "control_save_stage"
        items.append(
            {
                "item_id": item_id,
                "task_id": entry.task_id,
                "candidate": candidate,
                "initial": initial_of(entry.task_id),
                "baseline": baseline,
                "baseline_job": baseline_job,
                "baseline_source": source if (baseline_job or baseline) else "none",
            }
        )
    spot = raters.human_spot_check(sample, seed=seed)
    return {
        "sample": rows,
        "items": sorted(items, key=lambda r: r["item_id"]),
        "baseline_jobs": [baseline_jobs[k] for k in sorted(baseline_jobs)],
        "spot_check": [raters.opaque_item_id(s.mutant_id, salt) for s in spot],
        "summary": {
            "primary": primary,
            "seed": seed,
            "salt_sha256": raters.salt_sha256(salt),
            "shams": dict(Counter(str(s.sham) for s in sample if s.sham is not None)),
            "pool": len(pool),
            "pool_by_label": dict(Counter(c.label for c in pool)),
            "strata": dict(Counter(s.stratum for s in sample)),
            "p1_flip_tasks": flips,
            "spot_check": len(spot),
            "baseline_jobs": len(baseline_jobs),
            "baseline_sources": dict(Counter(i["baseline_source"] for i in items)),
        },
    }


def controls_inputs(
    runs: Sequence[str],
) -> tuple[dict[str, dict[str, Any]] | None, list[dict[str, Any]]]:
    """Control-run tasks and saved gold jobs of every given control run.

    A control run's saved jobs name files under the save stage's ``/out/``
    (its ``lo/`` directory), so those paths are mapped to ``<run>/lo/``.
    """
    from harness.q2_mutation.report import summarize_run

    if not runs:
        return None, []
    tasks: dict[str, dict[str, Any]] = {}
    saved: list[dict[str, Any]] = []
    for run in runs:
        tasks.update(summarize_run(Path(run))["tasks"])
        for job in read_jsonl(Path(run) / "saved" / "jobs-saved.jsonl"):
            job["files"] = {
                vm: remap(local, [("/out/", f"{run.rstrip('/')}/lo/")])
                for vm, local in job["files"].items()
            }
            saved.append(job)
    return tasks, saved


def cmd_sample(args: argparse.Namespace) -> int:
    run = Path(args.run)
    mapping = [tuple(item.split("=", 1)) for item in args.path_map]
    controls_tasks, controls_saved = controls_inputs(args.controls)
    sanitized = Path(args.sanitized)
    cache = Path(args.file_cache)
    salt = raters.check_salt(Path(args.salt_file).read_text(encoding="ascii").strip())
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
        salt=salt,
        build_root=args.build_root,
    )
    out = Path(args.out)
    digests = {
        "sample.jsonl": write_jsonl(out / "sample.jsonl", built["sample"]),
        "items.jsonl": write_jsonl(out / "items.jsonl", built["items"]),
        "baseline-jobs.jsonl": write_jsonl(out / "baseline-jobs.jsonl", built["baseline_jobs"]),
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


SAVED_START_NOTE = (
    "This starting file is shown as the VM's LibreOffice saves it, through the same save "
    "steps as the end state, so changes the save alone makes are not edits."
)
SAVED_DIFF_NOTE = (
    "Changes are listed against the starting file saved the same way; the LibreOffice save "
    "alone changes {n} items of the raw starting file (for example document defaults), "
    "which are not edits and are not listed."
)
RAW_DIFF_NOTE = (
    "No saved starting file could be produced for this file; changes are listed against the "
    "raw starting file and may include changes the LibreOffice save alone makes."
)


def build_packet(item: Mapping[str, Any], instruction: str, work: Path) -> dict[str, Any]:
    """One blind packet: instruction, starting files, end-state files, renders.

    Where the item has a saved starting file (``item["baseline"]``), the
    starting file is listed and rendered as saved, and the end-state
    difference is against it (``packets.artifacts``). The packet is then
    fitted to the registered token budget (``fit_packet``).
    """
    home = work / "home"
    home.mkdir(parents=True, exist_ok=True)
    initial = {vm: local for vm, local in item["initial"].items() if local is not None}
    baseline = {
        vm: local
        for vm, local in (item.get("baseline") or {}).items()
        if local is not None and vm in initial
    }
    save_failed = item.get("baseline_status") == "save_failed"
    candidate = dict(item["candidate"])
    budget = MAX_PACKET_IMAGES
    end_files = []
    for index, (vm, entry) in enumerate(sorted(artifacts(initial, candidate, baseline).items())):
        pages, notes = _file_pages(candidate.get(vm), work / f"end{index}", home)
        shown = _page_entries(pages, min(RENDER_PAGES, budget))
        budget -= len(shown)
        if len(shown) < len(pages):
            notes.append(f"{len(pages) - len(shown)} more rendered pages not shown (image cap)")
        if entry.get("baseline") == "saved":
            notes.insert(0, SAVED_DIFF_NOTE.format(n=entry.get("save_only_changes", 0)))
        elif entry.get("baseline") == "raw" and save_failed:
            notes.insert(0, RAW_DIFF_NOTE)
        end_files.append({"vm_path": vm, **entry, "pages": shown, "notes": notes})
    start_files = []
    for index, vm in enumerate(sorted(item["initial"])):
        local = baseline.get(vm) or item["initial"][vm]
        structure = structure_lines(Path(local)) if local else ["file absent at the start"]
        pages, notes = _file_pages(local, work / f"start{index}", home)
        shown = _page_entries(pages, min(RENDER_PAGES, budget))
        budget -= len(shown)
        if len(shown) < len(pages):
            notes.append(f"{len(pages) - len(shown)} more rendered pages not shown (image cap)")
        if vm in baseline:
            notes.insert(0, SAVED_START_NOTE)
        start_files.append(
            {
                "vm_path": vm,
                "structure": structure,
                "pages": shown,
                "notes": notes,
                "baseline": "saved" if vm in baseline else "raw",
            }
        )
    packet = raters.make_packet(
        raters.Sampled(item["item_id"], item["task_id"], "packet", 1.0),
        item_id=item["item_id"],
        instruction=instruction,
        initial_files=start_files,
        candidate_artifacts={"files": end_files},
    )
    packet["schema"] = PACKET_SCHEMA
    packet["baseline_status"] = item.get("baseline_status") or ("saved" if baseline else "none")
    fit_packet(packet)
    leaked = raters._leaked_keys(packet)
    if leaked:
        raise ValueError(f"packet leaks checker or operator information: {leaked}")
    return packet


# --- packet budget ------------------------------------------------------------


def image_size(data_b64: str) -> tuple[int, int] | None:
    """(width, height) of a PNG or JPEG page; None if neither header parses."""
    data = base64.b64decode(data_b64)
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] == b"\xff\xd8":
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            length = int.from_bytes(data[index + 2 : index + 4], "big")
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD):
                height = int.from_bytes(data[index + 5 : index + 7], "big")
                width = int.from_bytes(data[index + 7 : index + 9], "big")
                return width, height
            index += 2 + length
    return None


def image_tokens(data_b64: str) -> int:
    """Registered estimate: one token per 32 x 32 pixel cell plus two (unknown: 1700 x 2200)."""
    size = image_size(data_b64) or (1700, 2200)
    return math.ceil(size[0] / IMAGE_CELL_PX) * math.ceil(size[1] / IMAGE_CELL_PX) + 2


def estimate_tokens(packet: Mapping[str, Any]) -> int:
    """Registered prompt-size estimate of the packet's parts (``rater_runner.packet_parts``)."""
    from harness.q2_mutation.rater_runner import packet_parts

    text = 0
    images = 0
    for part in packet_parts(packet):
        if part["type"] == "text":
            text += len(part["text"].encode("utf-8"))
        else:
            images += image_tokens(part["data_b64"])
    return math.ceil(TEXT_TOKENS_PER_BYTE * text) + images


def fit_packet(packet: dict[str, Any], budget: int = PACKET_TOKEN_BUDGET) -> dict[str, Any]:
    """Shorten a packet to the registered token budget and record every cut.

    Order: starting-file listings, then end-state listings, then end-state
    differences, each cut from its end down to at least ``MIN_SECTION_LINES``
    lines with a closing line that says how many lines are not shown; if the
    text alone cannot fit, rendered pages are dropped, starting-file pages
    first. ``packet["fit"]`` records the estimate before and after, the cuts
    and whether the packet fits.
    """
    estimate = estimate_tokens(packet)
    fit: dict[str, Any] = {
        "budget_tokens": budget,
        "estimated_tokens": estimate,
        "cuts": [],
        "images_dropped": 0,
    }
    initial = packet.get("initial_files") or []
    end = (packet.get("candidate") or {}).get("files") or []
    sections = [("starting file", e, "structure") for e in initial]
    sections += [("end-state file", e, "structure") for e in end]
    sections += [("end-state file", e, "diff_vs_initial") for e in end]
    for kind, entry, key in sections:
        if estimate <= budget:
            break
        lines = list(entry.get(key) or [])
        keep = len(lines)
        while estimate > budget and keep > MIN_SECTION_LINES:
            # Bytes to remove for the excess, plus room for the closing note.
            need = math.ceil((estimate - budget) / TEXT_TOKENS_PER_BYTE) + 2 * len(FIT_NOTE)
            removed = 0
            while keep > MIN_SECTION_LINES and removed < need:
                keep -= 1
                removed += len(lines[keep].encode("utf-8")) + 1
            entry[key] = [*lines[:keep], f"... {len(lines) - keep} more {FIT_NOTE}"]
            estimate = estimate_tokens(packet)
        if keep < len(lines):
            fit["cuts"].append(
                {
                    "file": entry.get("vm_path"),
                    "kind": kind,
                    "section": key,
                    "kept_lines": keep,
                    "dropped_lines": len(lines) - keep,
                }
            )
    for entry in [*reversed(initial), *reversed(end)]:
        dropped_pages = 0
        while estimate > budget and entry.get("pages"):
            entry["pages"].pop()
            dropped_pages += 1
            estimate = estimate_tokens(packet)
        if dropped_pages:
            fit["images_dropped"] += dropped_pages
            entry.setdefault("notes", []).append(
                f"{dropped_pages} rendered pages not shown: shortened to fit the rater's "
                "context window"
            )
            estimate = estimate_tokens(packet)
    fit["estimated_tokens_after"] = estimate
    fit["fits"] = estimate <= budget
    packet["fit"] = fit
    return fit


def resolve_baselines(
    items: Sequence[dict[str, Any]],
    jobs: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Fill each item's saved starting files from the baseline save-stage rows.

    A baseline job whose save raised, has no row or did not write every office
    file (``reachability.save_failures``) gives no saved starting file: its
    items compare with the raw starting file and say so (``save_failed``).
    """
    from harness.q2_mutation.reachability import save_failures

    by_job = {str(job["job_id"]): job for job in jobs}
    by_row = {str(row["job_id"]): row for row in rows}
    saved: dict[str, dict[str, str | None] | None] = {}
    failed: dict[str, str] = {}
    for job_id, job in by_job.items():
        row = by_row.get(job_id)
        problems = (
            ["no save-stage row"]
            if row is None
            else [str(row["infra_error"])]
            if row.get("infra_error")
            else save_failures(job["files"], row)
        )
        if problems:
            saved[job_id] = None
            failed[job_id] = "; ".join(problems)[:400]
            continue
        outputs = dict(row.get("outputs") or {})
        saved[job_id] = {vm: outputs.get(vm, local) for vm, local in job["files"].items()}
    for item in items:
        job_id = item.get("baseline_job")
        if job_id:
            item["baseline"] = saved.get(job_id)
            item["baseline_status"] = "saved" if item["baseline"] else "save_failed"
        else:
            item["baseline_status"] = "saved" if item.get("baseline") else "none"
    return {
        "jobs": len(by_job),
        "saved": sum(1 for v in saved.values() if v),
        "failed": failed,
        "items": dict(Counter(str(i["baseline_status"]) for i in items)),
    }


def cmd_packets(args: argparse.Namespace) -> int:
    items = read_jsonl(Path(args.items))
    baselines: dict[str, Any] = {"jobs": 0}
    if args.baseline_jobs:
        rows = [row for path in args.baseline_rows for row in read_jsonl(Path(path))]
        baselines = resolve_baselines(items, read_jsonl(Path(args.baseline_jobs)), rows)
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
    fits = [p["fit"] for p in packets]
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
        "baselines": baselines,
        "fit": {
            "budget_tokens": PACKET_TOKEN_BUDGET,
            "text_tokens_per_byte": TEXT_TOKENS_PER_BYTE,
            "image_cell_px": IMAGE_CELL_PX,
            "packets_shortened": sum(1 for f in fits if f["cuts"] or f["images_dropped"]),
            "lines_dropped": sum(c["dropped_lines"] for f in fits for c in f["cuts"]),
            "images_dropped": sum(f["images_dropped"] for f in fits),
            "max_estimated_tokens_before": max((f["estimated_tokens"] for f in fits), default=0),
            "max_estimated_tokens_after": max(
                (f["estimated_tokens_after"] for f in fits), default=0
            ),
            "not_fitting": sorted(p["item_id"] for p in packets if not p["fit"]["fits"]),
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
    from harness.q2_mutation.rater_runner import calls_files_record, merged_answers

    sample, labels, item_of = load_sample(Path(args.sample))
    shards = {
        raters.RATER_IDS[0]: [Path(p) for p in args.anthropic_calls],
        raters.RATER_IDS[1]: [Path(p) for p in args.open_calls],
    }
    first = merged_answers(shards[raters.RATER_IDS[0]], item_of.values(), raters.RATER_IDS[0])
    second = merged_answers(shards[raters.RATER_IDS[1]], item_of.values(), raters.RATER_IDS[1])
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
    pool = raters.adjudication_pool(sample, labels, ratings, seed=args.seed)
    write_jsonl(out / "adjudication-pool.jsonl", [{"item_id": item_of[key]} for key, _ in pool])
    statuses = {
        rid: dict(Counter(status for _, status in calls.values()))
        for rid, calls in zip(raters.RATER_IDS, (first, second), strict=True)
    }
    result = {
        **summary_dict(summary),
        "raters": [dict(r) for r in raters.RATERS],
        "calls_files": {rid: calls_files_record(paths) for rid, paths in shards.items()},
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
            for key, decision in sorted(
                {**summary.decisions, **summary.sham_decisions}.items()
            )
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
    sample.add_argument(
        "--controls",
        action="append",
        default=[],
        help="control run directory (repeat: the confirm and the reserve control runs, "
        "whose P1 flips are all audited)",
    )
    sample.add_argument("--sanitized", required=True, help="sanitized task export directory")
    sample.add_argument("--file-cache", required=True, help="file-cache files directory")
    sample.add_argument("--out", required=True)
    sample.add_argument("--path-map", action="append", default=[], help="OLD=NEW path prefix")
    sample.add_argument("--primary", default="lock")
    sample.add_argument("--seed", type=int, default=42)
    sample.add_argument(
        "--salt-file",
        required=True,
        help="the audit's secret salt (64 hex characters), kept outside the repository",
    )
    sample.add_argument(
        "--build-root",
        default="/ro/build/",
        help="the mutation build directory as its saved jobs name it (before --path-map)",
    )
    packets = sub.add_parser("packets", allow_abbrev=False)
    packets.add_argument("--items", required=True)
    packets.add_argument("--sanitized", required=True)
    packets.add_argument("--out", required=True)
    packets.add_argument("--workers", type=int, default=4)
    packets.add_argument("--max-shard-bytes", type=int, default=MAX_SHARD_BYTES)
    packets.add_argument("--baseline-jobs", help="baseline-jobs.jsonl written by sample")
    packets.add_argument(
        "--baseline-rows",
        nargs="*",
        default=[],
        help="reachability-*.jsonl of the save stage run on the baseline jobs",
    )
    summ = sub.add_parser("summarize", allow_abbrev=False)
    summ.add_argument("--sample", required=True)
    summ.add_argument(
        "--anthropic-calls",
        nargs="+",
        required=True,
        help="calls.jsonl of the Anthropic rater, one per shard (API or agent-harness path)",
    )
    summ.add_argument(
        "--open-calls",
        nargs="+",
        required=True,
        help="calls.jsonl of the open-weight rater, one per shard (one lane job per shard)",
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
