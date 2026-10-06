#!/usr/bin/env python3
"""Emit the deterministic corrected-MemoryBank CPU contract receipt."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from itertools import pairwise
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.memorybank_decay import (  # noqa: E402
    DecayCandidate,
    retention_probability,
    score_candidates,
)

STATUS = "MEMORYBANK_CORRECTED_DECAY_CONTRACT_PASS"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict[str, Any]:
    elapsed_grid = (0.0, 1.0, 5.0, 20.0)
    strength_grid = (1.0, 2.0, 4.0, 8.0)
    corrected = {
        f"t={elapsed}:s={strength}": retention_probability(elapsed, strength)
        for elapsed in elapsed_grid
        for strength in strength_grid
    }
    upstream = {
        f"t={elapsed}:s={strength}": retention_probability(
            elapsed,
            strength,
            formula="upstream-precedence",
        )
        for elapsed in elapsed_grid
        for strength in strength_grid
    }
    candidates = (
        DecayCandidate(
            item_id="old-strengthened-relevant",
            elapsed_steps=20.0,
            prior_accesses=7,
            query_overlap=1,
        ),
        DecayCandidate(
            item_id="recent-unaccessed-distractor",
            elapsed_steps=1.0,
            prior_accesses=0,
            query_overlap=0,
        ),
    )
    corrected_rank = score_candidates(candidates)
    upstream_rank = score_candidates(candidates, formula="upstream-precedence")
    checks = {
        "corrected_probability_bounds": all(
            math_value >= 0.0 and math_value <= 1.0
            for math_value in corrected.values()
        ),
        "zero_elapsed_retention_is_one": all(
            corrected[f"t=0.0:s={strength}"] == 1.0 for strength in strength_grid
        ),
        "corrected_decay_is_monotonic_in_elapsed_time": all(
            corrected[f"t={left}:s={strength}"]
            >= corrected[f"t={right}:s={strength}"]
            for strength in strength_grid
            for left, right in pairwise(elapsed_grid)
        ),
        "corrected_retention_is_monotonic_in_strength": all(
            corrected[f"t={elapsed}:s={left}"]
            <= corrected[f"t={elapsed}:s={right}"]
            for elapsed in elapsed_grid[1:]
            for left, right in pairwise(strength_grid)
        ),
        "upstream_precedence_reverses_strength_effect": all(
            upstream[f"t={elapsed}:s={left}"]
            >= upstream[f"t={elapsed}:s={right}"]
            for elapsed in elapsed_grid[1:]
            for left, right in pairwise(strength_grid)
        ),
        "corrected_control_prefers_strengthened_relevant_item": (
            corrected_rank[0].item_id == "old-strengthened-relevant"
        ),
        "upstream_precedence_prefers_recent_distractor": (
            upstream_rank[0].item_id == "recent-unaccessed-distractor"
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"MemoryBank decay contract failed: {checks}")
    return {
        "schema_version": 1,
        "status": STATUS,
        "source": {
            "paper": "arXiv:2305.10250",
            "repository": "https://github.com/zhongwanjun/MemoryBank-SiliconFriend",
            "repository_revision": "cf61c4196e4cfdb0f2b7a0316249fa40312dc3a9",
            "upstream_code_imported": False,
        },
        "formula": {
            "corrected": "exp(-elapsed / (5 * strength))",
            "upstream_precedence_negative": "exp(-(elapsed / 5) * strength)",
            "strength": "1 + prior_access_count",
            "ranking": "(1 + query_token_overlap) * retention_probability",
        },
        "checks": checks,
        "corrected_grid": corrected,
        "upstream_precedence_grid": upstream,
        "corrected_ranking": [asdict(item) for item in corrected_rank],
        "upstream_precedence_ranking": [asdict(item) for item in upstream_rank],
        "code_sha256": {
            "harness/memory_trials/memorybank_decay.py": _sha(
                PROJECT_ROOT / "harness/memory_trials/memorybank_decay.py"
            ),
            "scripts/run_memorybank_decay_doctor.py": _sha(Path(__file__)),
        },
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "blocked-pending-frozen-system-integration",
    }


def main() -> int:
    print(json.dumps(build_report(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
