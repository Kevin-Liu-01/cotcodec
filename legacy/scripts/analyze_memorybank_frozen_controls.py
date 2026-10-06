#!/usr/bin/env python3
"""Measure the executable treatment contrast in frozen MemoryBank controls."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    FrozenMemorySystem,
    GeneratedMemoryTaskSource,
    MemoryBudget,
    run_memory_system,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402

ARM_FILES = {
    "corrected": "corrected.json",
    "no_decay": "no-decay.json",
    "upstream_precedence": "upstream-precedence.json",
}
EXPECTED_SYSTEM_IDS = {
    "corrected": "memorybank-corrected-decay-v1",
    "no_decay": "memorybank-no-decay-v1",
    "upstream_precedence": "memorybank-upstream-precedence-v1",
}
TASK_COUNT = 200
SOURCE_SEED = 7


def _atomic_write_once(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError(f"refusing to overwrite analysis: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def analyze_frozen_controls(bundle_root: Path) -> dict[str, Any]:
    if bundle_root.is_symlink() or not bundle_root.is_dir():
        raise ValueError("bundle root must be a regular directory")
    systems = {
        arm: FrozenMemorySystem(bundle_root / filename)
        for arm, filename in ARM_FILES.items()
    }
    for arm, system in systems.items():
        if system.receipt.system_id != EXPECTED_SYSTEM_IDS[arm]:
            raise ValueError(f"{arm}: frozen memory system identity drifted")

    budget = MemoryBudget(
        active_slots=4,
        max_archive_reads=1,
        retrieval_top_k=4,
        max_injected_tokens=256,
    )
    source = GeneratedMemoryTaskSource(
        seed=SOURCE_SEED,
        episode_count=TASK_COUNT,
        budget=budget,
    )
    rows: list[dict[str, Any]] = []
    for task_id in source.ids():
        task = source.load(task_id)
        for treatment_mode in ("storage_and_service", "serve_only"):
            for visibility in ("serve", "holdout"):
                runs = {
                    arm: run_memory_system(
                        system,
                        task,
                        visibility=visibility,
                        treatment_mode=treatment_mode,
                    )
                    for arm, system in systems.items()
                }
                rows.append(
                    {
                        "task_id": task.task_id,
                        "stratum": task.stratum.value,
                        "treatment_mode": treatment_mode,
                        "visibility": visibility,
                        "candidate_served": {
                            arm: run.candidate_served_to_actor
                            for arm, run in runs.items()
                        },
                        "run_sha256": {arm: run.run_sha256 for arm, run in runs.items()},
                    }
                )

    serve_rows = [
        row
        for row in rows
        if row["visibility"] == "serve"
        and row["treatment_mode"] == "storage_and_service"
    ]
    candidate_counts = {
        arm: sum(bool(row["candidate_served"][arm]) for row in serve_rows)
        for arm in ARM_FILES
    }
    pairwise: dict[str, dict[str, Any]] = {}
    arm_names = tuple(ARM_FILES)
    for index, left in enumerate(arm_names):
        for right in arm_names[index + 1 :]:
            different = [
                row
                for row in serve_rows
                if row["candidate_served"][left]
                != row["candidate_served"][right]
            ]
            pairwise[f"{left}_vs_{right}"] = {
                "candidate_service_disagreements": len(different),
                "by_stratum": dict(
                    sorted(Counter(row["stratum"] for row in different).items())
                ),
            }
    gates = {
        "all_holdout_requests_hide_candidate": all(
            not any(row["candidate_served"].values())
            for row in rows
            if row["visibility"] == "holdout"
        ),
        "corrected_differs_from_upstream": candidate_counts["corrected"]
        > candidate_counts["upstream_precedence"],
        "no_decay_is_registered_upper_control": candidate_counts["no_decay"]
        == TASK_COUNT,
        "upstream_precedence_is_registered_failure_control": candidate_counts[
            "upstream_precedence"
        ]
        == 0,
    }
    payload = {
        "schema_version": 1,
        "study": "memorybank-frozen-control-contrast-v1",
        "status": (
            "MEMORYBANK_FROZEN_CONTROL_CONTRAST_PASS"
            if all(gates.values())
            else "MEMORYBANK_FROZEN_CONTROL_CONTRAST_FAIL"
        ),
        "scientific_result": False,
        "publication_ready": False,
        "source_seed": SOURCE_SEED,
        "task_count": TASK_COUNT,
        "task_source": dict(source.provenance),
        "bundle_semantic_sha256s": {
            arm: system.bundle_sha256 for arm, system in systems.items()
        },
        "candidate_served_on_all_serve_storage_and_service": candidate_counts,
        "pairwise": pairwise,
        "gates": gates,
        "claim_boundary": (
            "This proves a deterministic ranking/exposure contrast only. A frozen "
            "model actor is required to measure executable task utility."
        ),
    }
    payload["rows_sha256"] = sha256_text(canonical_json(rows))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze_frozen_controls(args.bundle_root)
    if args.output is None:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _atomic_write_once(args.output, report)
        print(report["status"])
    return 0 if report["status"].endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
