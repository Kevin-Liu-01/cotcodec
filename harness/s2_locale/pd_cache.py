"""S2 v4 PD: the planted-document file-cache variant (registration P0.3, K0's I1-doc).

PD is the ER image with the task's first document replaced by its planted copy. The VM lane
mounts this variant directory instead of the pinned file cache for PD slots only; it holds every
file the dev tasks' own setup downloads (copied byte for byte from the pinned cache), with each
task's first document planted by ``capture.plant_document`` (the S2 v3 pilot's function: the
first text run of the document's main part becomes "S2V3 PLANTED CHANGE").

Which document. The first ``download`` of the task's setup whose file ``plant_document`` supports
(``.xlsx``, ``.docx``, ``.pptx``, ``.odt``, ``.ods``, ``.odp``). The rule for a plant that the
VM's view does not show (registration P0.7, fixed before the freeze): the variant is
development, decided on the dev tasks only. If the dev smoke shows the planted run off screen on
one of the 15 named tasks (O5 does not flag PD there), the plant of that task moves to the first
text run that the task's E render shows, chosen on the dev render, and the variant is rebuilt and
re-pinned before the freeze; K0's list of 15 never changes. The variant's manifest (every file's
SHA-256 and the plants) is committed, and ``vm_lane`` pins its digest.

Standard library only (the host's Python 3.10), run from an export:
  python3 -m harness.s2_locale.pd_cache --file-cache DIR --osworld DIR --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "s2v4-pd-cache-v1"
SUPPORTED = (".xlsx", ".docx", ".pptx", ".odt", ".ods", ".odp")
ROOT = Path(__file__).resolve().parents[2]


def plant_function() -> Callable[[Path], dict[str, Any]]:
    """``capture.plant_document`` (the pilot's plant), imported the way the pilot ran it."""
    for sub in ("harness/s2_locale", "harness/q2_mutation"):
        path = str(ROOT / sub)
        if path not in sys.path:
            sys.path.insert(0, path)
    import capture  # noqa: PLC0415

    return capture.plant_document


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def downloads(raw: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(file-cache rel path, VM path) of every ``download`` in the task's setup, in order."""
    from harness.s2_locale.golds import rel_of

    out = []
    for step in raw.get("config", []):
        if step.get("type") != "download":
            continue
        for item in step.get("parameters", {}).get("files", []):
            out.append((rel_of(str(item["url"])), str(item["path"])))
    return out


def build(file_cache: Path, osworld: Path, tasks: Sequence[str], out: Path,
          plant: Callable[[Path], dict[str, Any]] | None = None) -> dict[str, Any]:  # fmt: skip
    """Copy every download of ``tasks`` into ``out`` and plant each task's first document."""
    from harness.q2_mutation.offline_eval import load_task

    plant = plant or plant_function()
    files: dict[str, str] = {}
    planted = []
    for task_id in tasks:
        items = downloads(load_task(osworld, task_id))
        first = next((rel for rel, _ in items if Path(rel).suffix.lower() in SUPPORTED), None)
        for rel, _ in items:
            if rel in files:
                # another dev task downloads the same file: a later copy could undo a plant
                raise ValueError(f"{task_id}: {rel} is shared with another dev task")
            src, dst = file_cache / rel, out / rel
            if not src.is_file() or src.is_symlink():
                raise FileNotFoundError(f"{task_id}: {rel} is not in the pinned file cache")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            files[rel] = sha256_file(dst)
        row: dict[str, Any] = {"task_id": task_id, "document": first}
        if first is not None:
            row["original_sha256"] = files[first]
            row.update(plant(out / first))
            files[first] = row["planted_sha256"] = sha256_file(out / first)
        planted.append(row)
    manifest = {"schema": SCHEMA, "files": dict(sorted(files.items())), "plants": planted}
    manifest["files_sha256"] = files_digest(manifest["files"])
    return manifest


def files_digest(files: Mapping[str, str]) -> str:
    """The variant's identity: SHA-256 over sorted ``rel\\0sha256\\n`` lines."""
    text = "".join(f"{rel}\0{sha}\n" for rel, sha in sorted(files.items()))
    return hashlib.sha256(text.encode()).hexdigest()


def verify(directory: Path, files: Mapping[str, str]) -> list[str]:
    """Files of a variant directory that are missing or differ from the manifest."""
    bad = [rel for rel, sha in files.items()
           if not (directory / rel).is_file() or sha256_file(directory / rel) != sha]
    return sorted(bad)


def main(argv: list[str] | None = None) -> int:
    from harness.s2_locale.golds import POOL, pool_tasks

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file-cache", type=Path, required=True)
    parser.add_argument("--osworld", type=Path, required=True)
    parser.add_argument("--pool", type=Path, default=ROOT / POOL)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; a variant is built once into a new directory")
    tasks = [t["task_id"] for t in pool_tasks(json.loads(args.pool.read_text(encoding="utf-8")))
             if t["split"] == "dev"]
    manifest = build(args.file_cache, args.osworld, tasks, args.out / "files")
    (args.out / "pd-cache-manifest.json").write_text(json.dumps(manifest, indent=1,
                                                                sort_keys=True))  # fmt: skip
    print(json.dumps({"tasks": len(tasks), "files": len(manifest["files"]),
                      "files_sha256": manifest["files_sha256"],
                      "unplanted": [p["task_id"] for p in manifest["plants"]
                                    if not p.get("planted")]}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
