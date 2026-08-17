"""Verify administrator signatures over complete publication claim waves."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from harness.memory_trials.schema import canonical_json, sha256_text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_TRUST_ROOT = Path("/etc/cotcodec/trust")
PUBLICATION_TRUST_STORE = PUBLICATION_TRUST_ROOT / "publication-attestors.json"
ATTESTATION_DOMAIN = b"cotcodec-publication-claim-attestation-v2\0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _object(path: Path, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{owner} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{owner} must contain one JSON object")
    return value


def _semantic_root(payload: dict[str, Any], field: str, owner: str) -> str:
    expected = payload.get(field)
    unsigned = {key: value for key, value in payload.items() if key != field}
    actual = sha256_text(canonical_json(unsigned))
    if expected != actual:
        raise ValueError(f"{owner} semantic root is invalid")
    return actual


def publication_claim_message(bindings: dict[str, Any]) -> bytes:
    """Return the domain-separated message signed by a publication administrator."""

    return ATTESTATION_DOMAIN + canonical_json(bindings).encode()


def publication_claim_bindings(
    *,
    capsule_path: Path,
    matrix_path: Path,
    experiment_path: Path,
    wave: dict[str, Any],
    batch_script_path: Path,
) -> dict[str, Any]:
    """Recompute every file and semantic root covered by one claim signature."""

    capsule_path = capsule_path.resolve(strict=True)
    matrix_path = matrix_path.resolve(strict=True)
    experiment_path = experiment_path.resolve(strict=True)
    batch_script_path = batch_script_path.resolve(strict=True)
    for path, owner in (
        (capsule_path, "publication capsule"),
        (matrix_path, "control matrix"),
        (experiment_path, "publication experiment"),
        (batch_script_path, "publication batch script"),
    ):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"{owner} must be a regular non-symlink file")
    capsule = _object(capsule_path, "publication capsule")
    matrix = _object(matrix_path, "control matrix")
    capsule_sha256 = _semantic_root(capsule, "capsule_sha256", "publication capsule")
    matrix_sha256 = _semantic_root(matrix, "matrix_sha256", "control matrix")
    wave_sha256 = _semantic_root(wave, "wave_sha256", "publication wave")
    wave_bytes = (json.dumps(wave, indent=2, sort_keys=True) + "\n").encode()
    batch_script_sha256 = sha256_file(batch_script_path)
    runtime = capsule.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("batch_script_sha256") != (
        batch_script_sha256
    ):
        raise ValueError("publication batch script differs from the signed source capsule")
    if wave.get("batch_script_sha256") != batch_script_sha256:
        raise ValueError("publication wave batch script differs from the signed source capsule")
    return {
        "schema_version": 2,
        "capsule_sha256": capsule_sha256,
        "capsule_file_sha256": sha256_file(capsule_path),
        "control_matrix_sha256": matrix_sha256,
        "control_matrix_file_sha256": sha256_file(matrix_path),
        "experiment_sha256": sha256_file(experiment_path),
        "wave_sha256": wave_sha256,
        "wave_file_sha256": hashlib.sha256(wave_bytes).hexdigest(),
        "batch_script_sha256": batch_script_sha256,
        "eligible_controls_sha256": sha256_text(
            canonical_json(wave.get("eligible_controls"))
        ),
    }


def _protected_trust_store(
    trust_store_path: Path, expected_trust_store_sha256: str
) -> tuple[dict[str, Any], str]:
    trust_store_path = trust_store_path.resolve(strict=True)
    trust_root = PUBLICATION_TRUST_ROOT.resolve(strict=True)
    if trust_store_path != (trust_root / PUBLICATION_TRUST_STORE.name):
        raise ValueError("publication trust store must use the protected fixed path")
    if trust_store_path == PROJECT_ROOT or PROJECT_ROOT in trust_store_path.parents:
        raise ValueError("publication trust store must be outside the source repository")
    if not trust_store_path.is_file() or trust_store_path.is_symlink():
        raise ValueError("publication trust store must be a regular non-symlink file")
    trust_stat = trust_store_path.stat()
    if trust_stat.st_mode & 0o022:
        raise ValueError("publication trust store must not be group/world writable")
    if os.geteuid() != 0 and trust_stat.st_uid == os.geteuid():
        raise ValueError("publication trust store must be administered outside the job user")
    trust_sha256 = sha256_file(trust_store_path)
    if trust_sha256 != expected_trust_store_sha256:
        raise ValueError("publication trust store differs from the protected digest")
    trust = _object(trust_store_path, "publication trust store")
    if trust.get("schema_version") != 1 or trust.get("status") != (
        "TRUSTED_PUBLICATION_ATTESTORS"
    ):
        raise ValueError("publication trust store schema is invalid")
    return trust, trust_sha256


def verify_publication_claim_attestation(
    *,
    capsule_path: Path,
    matrix_path: Path,
    experiment_path: Path,
    wave: dict[str, Any],
    batch_script_path: Path,
    attestation_path: Path,
    trust_store_path: Path,
    expected_trust_store_sha256: str,
) -> dict[str, Any]:
    """Verify a complete claim signature against the protected external trust root."""

    attestation_path = attestation_path.resolve(strict=True)
    if not attestation_path.is_file() or attestation_path.is_symlink():
        raise ValueError("publication attestation must be a regular non-symlink file")
    bindings = publication_claim_bindings(
        capsule_path=capsule_path,
        matrix_path=matrix_path,
        experiment_path=experiment_path,
        wave=wave,
        batch_script_path=batch_script_path,
    )
    trust, trust_sha256 = _protected_trust_store(
        trust_store_path, expected_trust_store_sha256
    )
    keys = trust.get("keys")
    if not isinstance(keys, list):
        raise ValueError("publication trust store keys are invalid")
    attestation = _object(attestation_path, "publication attestation")
    attested_bindings = attestation.get("bindings")
    if (
        attestation.get("schema_version") != 2
        or attestation.get("status") != "PUBLICATION_CLAIM_ATTESTED"
        or attestation.get("algorithm") != "ed25519"
        or attested_bindings != bindings
    ):
        raise ValueError("publication attestation does not bind the complete claim wave")
    key_id = attestation.get("key_id")
    matches = [
        key
        for key in keys
        if isinstance(key, dict)
        and key.get("key_id") == key_id
        and key.get("algorithm") == "ed25519"
        and "publication-claim" in key.get("roles", [])
    ]
    if len(matches) != 1:
        raise ValueError("publication claim attestation key is not uniquely trusted")
    try:
        public_bytes = base64.b64decode(matches[0]["public_key_base64"], validate=True)
        signature = base64.b64decode(attestation["signature_base64"], validate=True)
        if len(public_bytes) != 32 or len(signature) != 64:
            raise ValueError
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(
            signature,
            publication_claim_message(bindings),
        )
    except (KeyError, TypeError, ValueError, InvalidSignature) as exc:
        raise ValueError("publication claim has an invalid Ed25519 attestation") from exc
    return {
        "schema_version": 2,
        "status": "PUBLICATION_CLAIM_ATTESTATION_VERIFIED",
        "bindings": bindings,
        "attestation_file_sha256": sha256_file(attestation_path),
        "trust_store_sha256": trust_sha256,
        "key_id": key_id,
    }


# Compatibility aliases deliberately retain the old import surface while changing
# its semantics from a capsule-only signature to a complete claim signature.
attestation_message = publication_claim_message
verify_publication_attestation = verify_publication_claim_attestation
