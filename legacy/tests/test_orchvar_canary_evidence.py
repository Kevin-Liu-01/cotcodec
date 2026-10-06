from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.run_orchvar_canary_proof import run_proof
from scripts.seal_orchvar_canary_evidence import (
    OrchVarCanaryEvidenceError,
    seal,
    validate_evidence,
)


def test_orchvar_canary_evidence_is_portable_and_tamper_detecting(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "proof"
    run_proof(run_root)
    output = tmp_path / "evidence.json"
    bundle = seal(run_root, output)

    projection = validate_evidence(output)
    assert projection["completed_cells"] == 120
    assert projection["byte_identical_scientific_outputs"] is True
    assert projection["safety_canary_stable"] is True

    tampered = deepcopy(bundle)
    receipt = tampered["scientific_outputs"][
        "results/orchvar-canary-admission-v1_summary.json"
    ]
    encoded = receipt["content_gzip_base64"]
    receipt["content_gzip_base64"] = ("A" if encoded[0] != "A" else "B") + encoded[1:]
    with pytest.raises(OrchVarCanaryEvidenceError):
        validate_evidence(tampered)
