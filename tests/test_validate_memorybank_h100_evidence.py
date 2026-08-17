from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_memorybank_h100_evidence import (
    MemoryBankH100EvidenceError,
    validate_memorybank_h100_evidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    PROJECT_ROOT / "research/evidence/memory/memorybank-h100-actor-v1.json"
)


def _bundle() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_memorybank_h100_evidence_recomputes() -> None:
    validate_memorybank_h100_evidence(_bundle(), project_root=PROJECT_ROOT)


def test_memorybank_h100_evidence_rejects_outcome_upgrade() -> None:
    bundle = copy.deepcopy(_bundle())
    bundle["outcome"]["corrected_minus_no_decay_points"] = 1.0
    with pytest.raises(MemoryBankH100EvidenceError, match="registered outcome drifted"):
        validate_memorybank_h100_evidence(bundle, project_root=PROJECT_ROOT)
