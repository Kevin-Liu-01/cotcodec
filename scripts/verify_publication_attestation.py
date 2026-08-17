#!/usr/bin/env python3
"""Verify a complete publication claim signature against the protected trust store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness.publication_attestation import verify_publication_claim_attestation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capsule", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--wave", type=Path, required=True)
    parser.add_argument("--batch-script", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--trust-store", type=Path, required=True)
    parser.add_argument("--expected-trust-store-sha256", required=True)
    args = parser.parse_args()
    wave = json.loads(args.wave.read_text(encoding="utf-8"))
    if not isinstance(wave, dict):
        raise SystemExit("wave must contain a JSON object")
    receipt = verify_publication_claim_attestation(
        capsule_path=args.capsule,
        matrix_path=args.matrix,
        experiment_path=args.experiment,
        wave=wave,
        batch_script_path=args.batch_script,
        attestation_path=args.attestation,
        trust_store_path=args.trust_store,
        expected_trust_store_sha256=args.expected_trust_store_sha256,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
