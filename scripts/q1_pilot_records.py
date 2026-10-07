#!/usr/bin/env python3
"""Bind the Q1 pilot's run records by hash and list what the pilot exposed (CPU).

    python scripts/q1_pilot_records.py --job RUNS/474 --job RUNS/518 --job RUNS/548 \\
        --corpus RUNS/518/q1/inputs/corpus \\
        --records program/evidence/2026-10-07/q1-pilot/run-records.json \\
        --exposed harness/q1/data/pilot_exposed.json

``--job`` is a lane run directory (the driver's ``q1/`` tree and the lane files).

``--records``: the SHA-256 and size of every file of each job's run directory
except the unpacked study artifact (``q1/inputs``, bound by the artifact's own
hash) and the study artifact copy itself, with a tree hash per job, so later
drift in the journals, plans, phases or summaries the committed evidence was
computed from is detectable. Items a time box killed left an ``item.json`` and
no journal row; their file times (the only record of when they ran in these
jobs) are listed with the hashes.

``--exposed``: every kernel with a verdict row (or a killed item) in any pilot
phase, classified with the pilot corpus: evaluation substrates and their
independent units, calibration substrates, mutants (with split, family and
dedup hash), controls. The trimming rule (``harness.q1.trim``) removes the
exposed mutants from its sampling frames, and the analysis reports a
sensitivity analysis without the exposed units (preregistration section 18.6).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SKIP_TOP = {"study-artifact.json"}
#: Units whose primary-audit status a data-motivated audit change would alter
#: (preregistration section 18.6, decision D26): the TF32 tl.dot threshold change
#: proposed after the pilot saw the tutorial matmul fail A3 (finding 18.3.6).
DATA_MOTIVATED_UNITS = {
    "tf32-tl-dot-threshold": [
        "triton-tutorials:python/tutorials/03-matrix-multiplication.py:matmul_kernel"
    ],
    "a5-refusal-classification": [],
    "tf32-convolution-tolerance-cap": [],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def job_records(job: Path) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in job.rglob("*") if p.is_file()):
        rel = path.relative_to(job).as_posix()
        if rel in SKIP_TOP or rel.startswith("q1/inputs/") or "/cache/" in f"/{rel}":
            continue
        files.append({"path": rel, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    tree = hashlib.sha256()
    for entry in files:
        tree.update(f"{entry['path']}\0{entry['sha256']}\n".encode())
    killed = []
    for journal in sorted((job / "q1").glob("*/journal.jsonl")):
        phase = journal.parent
        keys = {
            json.loads(line)["details"]["item_key"]
            for line in journal.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        summary = phase / "summary.json"
        for item_path in sorted(phase.glob("items/*/item.json")):
            item = json.loads(item_path.read_text(encoding="utf-8"))
            if item.get("item_key") in keys:
                continue
            killed.append(
                {
                    "phase": phase.name,
                    "item_key": item.get("item_key"),
                    "item_json": item_path.relative_to(job).as_posix(),
                    "item_json_mtime": round(item_path.stat().st_mtime, 3),
                    "summary_mtime": round(summary.stat().st_mtime, 3)
                    if summary.exists()
                    else None,
                    "bound_from": "file mtimes (the pilot runner did not record kill times)",
                }
            )
    return {
        "job": job.name,
        "files": files,
        "file_count": len(files),
        "tree_sha256": tree.hexdigest(),
        "killed_items": killed,
    }


def _kind_from_id(kernel_id: str) -> str:
    if kernel_id.startswith("ctl-") or ".hack." in kernel_id or kernel_id.endswith(".control"):
        return "control"
    return "mutant" if "." in kernel_id else "substrate"


def exposure(jobs: list[Path], corpus: Path | None) -> dict[str, Any]:
    from harness.q1 import analysis

    table: dict[str, dict[str, Any]] = {}
    if corpus is not None:
        roots = [p for p in sorted(corpus.iterdir()) if p.is_dir() and p.name != "specializations"]
        roots = [
            p
            for p in roots
            if p.name
            in {
                "pilot-substrates",
                "pilot-calibration",
                "mutants",
                "controls-core",
                "controls-hacks",
                "controls-mutants",
            }
        ]
        table = analysis.kernel_table(roots)
    halves = analysis.substrate_halves(table, analysis.s1_split())
    seen: dict[str, dict[str, Any]] = {}
    for job in jobs:
        for journal in sorted((job / "q1").glob("*/journal.jsonl")):
            phase = journal.parent.name
            for line in journal.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                kernel_id = row["kernel_id"]
                entry = seen.setdefault(
                    kernel_id,
                    {"phases": set(), "gates": set(), "seeds": set(), "verdicts": Counter()},
                )
                entry["phases"].add(f"{job.name}/{phase}")
                entry["gates"].add(
                    row["details"].get("item_key", "||").split("|")[1] or row["gate"]
                )
                entry["seeds"].add(int(row.get("seed") or 42))
                entry["verdicts"][row["verdict"]] += 1
        for item_path in sorted((job / "q1").glob("*/items/*/item.json")):
            item = json.loads(item_path.read_text(encoding="utf-8"))
            entry = seen.setdefault(
                item["kernel_id"],
                {"phases": set(), "gates": set(), "seeds": set(), "verdicts": Counter()},
            )
            entry["phases"].add(f"{job.name}/{item_path.parent.parent.parent.name}")
            entry["gates"].add(item["gate"])
            entry["seeds"].add(int(item["seed"]))
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    units: dict[str, list[str]] = defaultdict(list)
    for kernel_id, entry in sorted(seen.items()):
        facts = table.get(kernel_id, {})
        kind = facts.get("kind") or _kind_from_id(kernel_id)
        record = {
            "kernel_id": kernel_id,
            "problem_id": facts.get("problem_id"),
            "phases": sorted(entry["phases"]),
            "gates": sorted(entry["gates"]),
            "seeds": sorted(entry["seeds"]),
            "verdict_rows": dict(sorted(entry["verdicts"].items())),
        }
        if kind == "substrate":
            if kernel_id in halves["calibration"]:
                out["calibration_substrates"].append(record)
            else:
                unit = facts.get("kernel_family") or kernel_id
                out["evaluation_substrates"].append({**record, "unit": unit})
                units[unit].append(kernel_id)
        elif kind == "mutant":
            out["mutants"].append(
                {
                    **record,
                    "parent": facts.get("parent_substrate_id"),
                    "family": facts.get("family"),
                    "split": facts.get("split"),
                    "dedup_hash": _dedup(corpus, kernel_id),
                }
            )
        else:
            out["controls"].append({**record, "control_kind": facts.get("control_kind")})
    return {
        "schema": "q1-pilot-exposed/1",
        "what": "kernels with a verdict row or a killed item in pilot jobs "
        + ", ".join(j.name for j in jobs)
        + " (any phase); the trimming rule removes exposed mutants from its frames and the "
        "analysis reports every primary quantity without the exposed units as a "
        "pre-specified sensitivity analysis (preregistration section 18.6)",
        "jobs": [j.name for j in jobs],
        "evaluation_substrates": out["evaluation_substrates"],
        "evaluation_units": {u: sorted(k) for u, k in sorted(units.items())},
        "calibration_substrates": out["calibration_substrates"],
        "mutants": out["mutants"],
        "controls": out["controls"],
        "data_motivated_units": DATA_MOTIVATED_UNITS,
    }


def _dedup(corpus: Path | None, kernel_id: str) -> str | None:
    if corpus is None:
        return None
    path = corpus / "mutants" / kernel_id / "mutation.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("dedup_hash")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--job", type=Path, action="append", required=True)
    parser.add_argument("--corpus", type=Path, default=None)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--exposed", type=Path, required=True)
    args = parser.parse_args(argv)
    records = {
        "schema": "q1-pilot-run-records/1",
        "what": "SHA-256 of every file of each pilot job's run directory (unpacked study "
        "artifact excluded; it is bound by its own hash), and the killed items with the file "
        "times their censored costs were read from",
        "jobs": [job_records(job) for job in args.job],
    }
    args.records.parent.mkdir(parents=True, exist_ok=True)
    args.records.write_text(json.dumps(records, indent=1, sort_keys=True) + "\n")
    exposed = exposure(args.job, args.corpus)
    args.exposed.write_text(json.dumps(exposed, indent=1, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "records_sha256": _sha256(args.records),
                "exposed_sha256": _sha256(args.exposed),
                "evaluation_units": list(exposed["evaluation_units"]),
                "mutants": len(exposed["mutants"]),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
