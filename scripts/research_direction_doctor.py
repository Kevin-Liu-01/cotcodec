#!/usr/bin/env python3
"""Validate a Research Gauntlet proposal and its hashed evidence bundle."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:  # direct `python scripts/...` execution
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.submit_research_job import validate_manifest  # noqa: E402

REQUIRED_HEADINGS = (
    "Claim and Research Question",
    "Strategic Fit and Why Now",
    "Primary-Source Evidence",
    "Closest Prior Work",
    "Novelty Ledger",
    "Mechanism and Falsifiable Predictions",
    "Cheapest Decisive Pilot",
    "Controls, Baselines, and Ablations",
    "Evaluation, Statistics, and Leakage Checks",
    "Compute and Reproducibility",
    "Safety, Data Rights, and Monitorability",
    "Negative-Result Value",
    "Preflight Doctors",
    "Independent Adversarial Reviews",
    "Scorecard",
    "Iteration Log",
)

DOCTORS = ("Source", "Citation", "Novelty", "Design", "Compute", "Safety")

DIMENSIONS = (
    "Question and strategic fit",
    "Primary-source evidence",
    "Defensible novelty delta",
    "Mechanism and falsifiability",
    "Controls and causal identification",
    "Evaluation and statistics",
    "Feasibility and information per GPU-hour",
    "Reproducibility and artifact contract",
    "Safety, data rights, and monitorability",
    "Independent adversarial review quality",
)

PRIMARY_DOMAINS = {
    "aclanthology.org",
    "arxiv.org",
    "deepmind.google",
    "github.com",
    "huggingface.co",
    "labs.ramp.com",
    "openai.com",
    "openreview.net",
    "proceedings.mlr.press",
    "proceedings.neurips.cc",
    "research.google",
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OCI_DIGEST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$")
PLACEHOLDER_RE = re.compile(r"<[^>]+>|\bYYYY-MM-DD\b|\bTBD\b", re.IGNORECASE)
REPO_ROOT = Path(__file__).resolve().parents[1]
_external_trust_store = os.environ.get("COTCODEC_TRUSTED_ATTESTORS_PATH")
TRUST_STORE_EXPECTED_SHA256 = os.environ.get("COTCODEC_TRUSTED_ATTESTORS_SHA256")
TRUST_STORE_PATH = (
    Path(_external_trust_store).expanduser().resolve()
    if _external_trust_store
    else REPO_ROOT / "research/proposals/trusted-attestors.json"
)
TRUST_STORE_PROTECTED = (
    _external_trust_store is not None and os.environ.get("COTCODEC_PROTECTED_CI") == "1"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sections(text: str) -> tuple[dict[str, str], list[str]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    duplicates: list[str] = []
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if name in sections:
            duplicates.append(name)
        else:
            sections[name] = text[start:end].strip()
    return sections, duplicates


def _table_rows(text: str) -> tuple[dict[str, list[str]], list[str]]:
    rows: dict[str, list[str]] = {}
    duplicates: list[str] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [re.sub(r"[*`]", "", cell.strip()) for cell in line.strip().strip("|").split("|")]
        if not cells or not cells[0]:
            continue
        key = cells[0].casefold()
        if key in rows:
            duplicates.append(cells[0])
        else:
            rows[key] = cells[1:]
    return rows, duplicates


def _parse_score(value: str) -> int | None:
    match = re.fullmatch(r"\s*(10|[0-9])(?:\s*/\s*10)?\s*", value)
    return int(match.group(1)) if match else None


def _metadata(text: str, label: str) -> str | None:
    match = re.search(
        rf"^\*\*{re.escape(label)}:\*\*\s*(.+?)\s*$",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _safe_bundle_path(proposal: Path, raw: str) -> Path | None:
    candidate = (proposal.parent / raw.strip("` ")).resolve()
    proposal_root = proposal.parent.resolve()
    if not candidate.is_relative_to(proposal_root):
        return None
    return candidate


def _artifact_path(bundle_dir: Path, raw: str) -> Path | None:
    candidate = (bundle_dir / raw).resolve()
    if not candidate.is_relative_to(bundle_dir.resolve()):
        return None
    return candidate


def _verify_artifact(
    record: dict[str, Any],
    bundle_dir: Path,
    label: str,
    issues: list[str],
) -> Path | None:
    raw_path = record.get("artifact")
    expected_hash = record.get("sha256")
    if not isinstance(raw_path, str) or not isinstance(expected_hash, str):
        issues.append(f"{label} lacks artifact and sha256")
        return None
    if not SHA256_RE.fullmatch(expected_hash):
        issues.append(f"{label} has invalid sha256")
        return None
    path = _artifact_path(bundle_dir, raw_path)
    if path is None or not path.is_file():
        issues.append(f"{label} artifact missing or escapes bundle: {raw_path}")
        return None
    if path.stat().st_size < 64:
        issues.append(f"{label} artifact is implausibly small: {raw_path}")
        return None
    if _sha256(path) != expected_hash:
        issues.append(f"{label} artifact hash mismatch: {raw_path}")
        return None
    return path


def _validate_audit_log(
    path: Path,
    expected_final: str,
    proposal_hash: str,
    budgets: dict[str, int],
    issues: list[str],
) -> None:
    previous = "0" * 64
    rows = []
    try:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (json.JSONDecodeError, OSError) as exc:
        issues.append(f"invalid audit JSONL: {exc}")
        return
    if not rows:
        issues.append("audit log is empty")
        return
    best_score = -1
    previous_counters = {
        key: 0.0 for key in ("queries", "wall_minutes", "tokens", "dollars", "gpu_hours")
    }
    for index, row in enumerate(rows, start=1):
        if row.get("previous_hash") != previous:
            issues.append(f"audit row {index} breaks previous_hash chain")
            return
        claimed = row.get("hash")
        payload = {key: value for key, value in row.items() if key != "hash"}
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if claimed != computed:
            issues.append(f"audit row {index} hash mismatch")
            return
        previous = claimed
        if row.get("wave") != index:
            issues.append(f"audit row {index} has a nonsequential wave")
        if not isinstance(row.get("run_id"), str) or not row["run_id"]:
            issues.append(f"audit row {index} lacks run_id")
        if row.get("candidate_sha256") != proposal_hash:
            issues.append(f"audit row {index} candidate hash does not match proposal")
        score = row.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
            issues.append(f"audit row {index} has an invalid score")
        else:
            best_score = max(best_score, score)
            if row.get("best_score") != best_score:
                issues.append(f"audit row {index} best_score is inconsistent")
        for key, prior in previous_counters.items():
            value = row.get(key)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                or float(value) < prior
                or float(value) > budgets[key]
            ):
                issues.append(f"audit row {index} has invalid cumulative {key}")
            else:
                previous_counters[key] = float(value)
        if index < len(rows) and row.get("termination_reason") not in {None, ""}:
            issues.append(f"audit row {index} terminates before the final wave")
    if previous != expected_final:
        issues.append("audit final_hash does not match chain")
    if len(rows) > budgets["waves"]:
        issues.append("audit exceeds the declared wave budget")
    if rows[-1].get("termination_reason") != "all_doctors_and_reviews_passed":
        issues.append("audit final row lacks the successful termination state")


def _evidence_root(bundle: dict[str, Any]) -> str:
    payload = {
        key: bundle.get(key)
        for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _review_signature_payload(review: dict[str, Any]) -> bytes:
    fields = (
        "provider",
        "model",
        "run_id",
        "verdict",
        "candidate_sha256",
        "evidence_root_sha256",
        "prompt_sha256",
        "artifact",
        "sha256",
        "signed_at",
        "key_id",
    )
    payload = {field: review.get(field) for field in fields}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _trusted_attestors(issues: list[str]) -> dict[str, dict[str, Any]]:
    if not TRUST_STORE_PROTECTED:
        issues.append(
            "protected external trust store is not configured; "
            "set COTCODEC_TRUSTED_ATTESTORS_PATH in trusted CI"
        )
        return {}
    resolved = TRUST_STORE_PATH.resolve()
    if resolved.is_relative_to(REPO_ROOT.resolve()):
        issues.append("trusted-attestor store must be outside the proposal repository")
        return {}
    try:
        mode = resolved.stat().st_mode
    except OSError as exc:
        issues.append(f"invalid trusted-attestor store: {exc}")
        return {}
    if mode & 0o022:
        issues.append("trusted-attestor store must not be group/world writable")
        return {}
    if not SHA256_RE.fullmatch(str(TRUST_STORE_EXPECTED_SHA256 or "")):
        issues.append("protected CI must pin COTCODEC_TRUSTED_ATTESTORS_SHA256")
        return {}
    if _sha256(resolved) != TRUST_STORE_EXPECTED_SHA256:
        issues.append("trusted-attestor store does not match the CI-pinned digest")
        return {}
    try:
        trust = json.loads(TRUST_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"invalid trusted-attestor store: {exc}")
        return {}
    if trust.get("schema_version") != 1 or not isinstance(trust.get("attestors"), list):
        issues.append("trusted-attestor store has invalid schema")
        return {}
    records = {}
    for record in trust["attestors"]:
        if isinstance(record, dict) and isinstance(record.get("key_id"), str):
            records[record["key_id"]] = record
    return records


def _verify_review_signature(
    review: dict[str, Any],
    trust: dict[str, dict[str, Any]],
    label: str,
    issues: list[str],
) -> bool:
    key_id = review.get("key_id")
    signature = review.get("signature")
    trusted = trust.get(str(key_id))
    if trusted is None:
        issues.append(f"{label} key_id is not in the protected trust store")
        return False
    if trusted.get("provider") != review.get("provider") or "reviewer" not in trusted.get(
        "roles", []
    ):
        issues.append(f"{label} key is not trusted for this provider/role")
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(trusted["public_key_base64"], validate=True)
        )
        public_key.verify(
            base64.b64decode(str(signature), validate=True),
            _review_signature_payload(review),
        )
    except (InvalidSignature, ValueError, TypeError, KeyError):
        issues.append(f"{label} has an invalid Ed25519 signature")
        return False
    return True


def _validate_bundle(
    bundle_path: Path,
    proposal: Path,
    primary_urls: list[str],
    reviewer_scores: dict[str, dict[str, int | None]],
    proposal_budgets: dict[str, int],
    proposal_seeds: list[int],
    issues: list[str],
) -> dict[str, Any] | None:
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"invalid evidence bundle: {exc}")
        return None
    if bundle.get("schema_version") != 1:
        issues.append("evidence bundle schema_version must be 1")

    proposal_hash = _sha256(proposal)
    if bundle.get("proposal_sha256") != proposal_hash:
        issues.append("evidence bundle proposal_sha256 does not match proposal")

    bundle_dir = bundle_path.parent
    sources = bundle.get("source_snapshots")
    if not isinstance(sources, list):
        issues.append("evidence bundle lacks source_snapshots array")
        sources = []
    source_urls: set[str] = set()
    for index, record in enumerate(sources):
        if not isinstance(record, dict):
            issues.append(f"source snapshot {index} is not an object")
            continue
        url = record.get("url")
        if isinstance(url, str):
            source_urls.add(url)
        if record.get("http_status") != 200:
            issues.append(f"source snapshot {index} did not resolve with HTTP 200")
        _verify_artifact(record, bundle_dir, f"source snapshot {index}", issues)
    missing_snapshots = sorted(set(primary_urls) - source_urls)
    if missing_snapshots:
        issues.append(f"primary URLs lack hashed snapshots: {', '.join(missing_snapshots[:3])}")

    query_log = bundle.get("query_log")
    if not isinstance(query_log, dict):
        issues.append("evidence bundle lacks query_log artifact")
    else:
        _verify_artifact(query_log, bundle_dir, "query log", issues)

    computed_evidence_root = _evidence_root(bundle)
    if bundle.get("evidence_root_sha256") != computed_evidence_root:
        issues.append("evidence_root_sha256 does not match the evidence bundle")

    reviews = bundle.get("reviews")
    if not isinstance(reviews, list) or len(reviews) != 2:
        issues.append("evidence bundle requires exactly two review artifacts")
        reviews = []
    providers: set[str] = set()
    run_ids: set[str] = set()
    verified_key_ids: set[str] = set()
    trust = _trusted_attestors(issues)
    for index, review in enumerate(reviews):
        if not isinstance(review, dict):
            issues.append(f"review {index} is not an object")
            continue
        providers.add(str(review.get("provider", "")))
        run_ids.add(str(review.get("run_id", "")))
        if review.get("verdict") != "PASS":
            issues.append(f"review {index} verdict is not PASS")
        if review.get("candidate_sha256") != proposal_hash:
            issues.append(f"review {index} candidate hash does not match proposal")
        if review.get("evidence_root_sha256") != computed_evidence_root:
            issues.append(f"review {index} evidence root does not match bundle")
        if not SHA256_RE.fullmatch(str(review.get("prompt_sha256", ""))):
            issues.append(f"review {index} prompt_sha256 is invalid")
        review_path = _verify_artifact(review, bundle_dir, f"review {index}", issues)
        if _verify_review_signature(review, trust, f"review {index}", issues):
            verified_key_ids.add(str(review.get("key_id")))
        if review_path is not None:
            try:
                review_output = json.loads(review_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                issues.append(f"review {index} artifact is not structured JSON: {exc}")
                review_output = {}
            reviewer_id = "A" if index == 0 else "B"
            expected_scores = reviewer_scores[reviewer_id]
            if review_output.get("verdict") != review.get("verdict"):
                issues.append(f"review {index} artifact verdict does not match receipt")
            if review_output.get("provider_request_id") in {None, ""}:
                issues.append(f"review {index} lacks provider_request_id")
            if review_output.get("model") != review.get("model"):
                issues.append(f"review {index} artifact model does not match receipt")
            if not re.fullmatch(
                r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
                str(review_output.get("timestamp", "")),
            ):
                issues.append(f"review {index} lacks an ISO UTC timestamp")
            if review_output.get("scores") != expected_scores:
                issues.append(f"review {index} scores do not match Markdown scorecard")
    if len(providers - {""}) < 2:
        issues.append("reviewers must use different providers; degraded review cannot score 100")
    if len(run_ids - {""}) < 2:
        issues.append("reviewers must have distinct nonempty run IDs")
    if len(verified_key_ids) < 2:
        issues.append("two distinct trusted reviewer signatures are required for 100")

    compute = bundle.get("compute")
    if not isinstance(compute, dict):
        issues.append("evidence bundle lacks compute attestations")
    else:
        if not OCI_DIGEST_RE.fullmatch(str(compute.get("image_digest", ""))):
            issues.append("compute image_digest must be a full immutable OCI digest")
        if compute.get("real_model_loop") is not True:
            issues.append("compute attestation says the real model loop is not executable")
        if compute.get("benchmark_adapter") in {None, "", "stub"}:
            issues.append("compute attestation lacks a non-stub benchmark adapter")
        adapter_path = REPO_ROOT / str(compute.get("benchmark_adapter", ""))
        if not adapter_path.is_file():
            issues.append("compute benchmark_adapter path does not exist")
        else:
            adapter_text = adapter_path.read_text(encoding="utf-8")
            if "NotImplementedError" in adapter_text or re.search(
                r"^\s*pass\s*$", adapter_text, re.MULTILINE
            ):
                issues.append("compute benchmark adapter still contains a stub")

        runner_path = REPO_ROOT / "harness/runner.py"
        runner_text = runner_path.read_text(encoding="utf-8") if runner_path.is_file() else ""
        if (
            "agent loop not yet implemented" in runner_text
            or "TODO: Execute agent loop" in runner_text
            or not runner_text
        ):
            issues.append("repository real model loop is still a stub")

        manifest_record = compute.get("manifest")
        if not isinstance(manifest_record, dict):
            issues.append("compute lacks a hashed Slurm manifest")
        else:
            manifest_path = _verify_artifact(
                manifest_record, bundle_dir, "compute manifest", issues
            )
            if manifest_path is not None:
                try:
                    manifest_raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                    if not isinstance(manifest_raw, dict):
                        raise ValueError("manifest must be an object")
                    manifest = validate_manifest(manifest_raw)
                    manifest_gpu_hours = manifest["max_gpu_hours"]
                    manifest_seeds = manifest["seeds"]
                except (TypeError, ValueError, yaml.YAMLError) as exc:
                    issues.append(f"compute manifest is invalid: {exc}")
                else:
                    if not (0 < manifest_gpu_hours <= proposal_budgets["gpu_hours"]):
                        issues.append("Slurm manifest GPU-hour ceiling exceeds proposal budget")
                    if manifest_seeds != proposal_seeds:
                        issues.append("Slurm manifest seeds do not match proposal seeds")
                    if manifest["image"] != compute.get("image_digest"):
                        issues.append("Slurm manifest image does not match compute image digest")
        for label in ("container_smoke", "slurm_test", "provenance_verification"):
            attestation = compute.get(label)
            if not isinstance(attestation, dict):
                issues.append(f"compute lacks {label} attestation")
                continue
            if attestation.get("status") != "PASS" or attestation.get("return_code") != 0:
                issues.append(f"compute {label} did not pass")
            _verify_artifact(attestation, bundle_dir, f"compute {label}", issues)

    doctors = bundle.get("doctors")
    if not isinstance(doctors, list):
        issues.append("evidence bundle lacks doctor artifacts")
        doctors = []
    doctor_names: set[str] = set()
    for index, doctor in enumerate(doctors):
        if not isinstance(doctor, dict):
            issues.append(f"doctor artifact {index} is not an object")
            continue
        doctor_names.add(str(doctor.get("name", "")))
        if doctor.get("status") != "PASS":
            issues.append(f"doctor artifact {index} did not pass")
        _verify_artifact(doctor, bundle_dir, f"doctor artifact {index}", issues)
    missing_doctors = sorted(set(DOCTORS) - doctor_names)
    if missing_doctors:
        issues.append(f"evidence bundle missing doctors: {', '.join(missing_doctors)}")

    audit = bundle.get("audit_log")
    if not isinstance(audit, dict):
        issues.append("evidence bundle lacks audit_log artifact")
    else:
        audit_path = _verify_artifact(audit, bundle_dir, "audit log", issues)
        final_hash = str(audit.get("final_hash", ""))
        if not SHA256_RE.fullmatch(final_hash):
            issues.append("audit final_hash is invalid")
        elif audit_path is not None:
            _validate_audit_log(
                audit_path,
                final_hash,
                proposal_hash,
                proposal_budgets,
                issues,
            )
    return bundle


def inspect(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    caps: list[int] = []

    sections, duplicate_headings = _sections(text)
    if duplicate_headings:
        issues.append(f"duplicate headings: {', '.join(sorted(set(duplicate_headings)))}")
    missing_headings = [heading for heading in REQUIRED_HEADINGS if heading not in sections]
    if missing_headings:
        issues.append(f"missing headings: {', '.join(missing_headings)}")
    for heading in REQUIRED_HEADINGS:
        content = sections.get(heading, "")
        if len(content) < 40 or PLACEHOLDER_RE.search(content):
            issues.append(f"section is empty or contains placeholders: {heading}")

    cutoff = _metadata(text, "Source cutoff")
    coverage = _metadata(text, "Coverage limits")
    budgets = _metadata(text, "Budgets")
    bundle_raw = _metadata(text, "Evidence bundle")
    if not cutoff or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", cutoff):
        issues.append("Source cutoff must be an ISO date")
    if not coverage or PLACEHOLDER_RE.search(coverage):
        issues.append("Coverage limits must be explicit")
    budget_keys = ("queries", "wall_minutes", "tokens", "dollars", "waves", "gpu_hours")
    budget_matches = {key: re.search(rf"\b{key}=(\d+)", budgets or "") for key in budget_keys}
    if not budgets or any(match is None for match in budget_matches.values()):
        issues.append(f"Budgets must declare integer values for: {', '.join(budget_keys)}")
        proposal_budgets = {key: 0 for key in budget_keys}
    else:
        proposal_budgets = {
            key: int(match.group(1)) for key, match in budget_matches.items() if match is not None
        }
        if any(value <= 0 for value in proposal_budgets.values()):
            issues.append("all declared budgets must be positive")

    if _metadata(text, "Novelty verdict") != "NO_DIRECT_PRIOR_FOUND":
        issues.append("Novelty verdict must be NO_DIRECT_PRIOR_FOUND; otherwise reject")
        caps.append(0)
    if _metadata(text, "Safety verdict") != "PASS":
        issues.append("Safety verdict must be PASS; otherwise reject")
        caps.append(0)

    doctor_rows, doctor_duplicates = _table_rows(sections.get("Preflight Doctors", ""))
    if doctor_duplicates:
        issues.append("duplicate doctor rows")
    doctor_status: dict[str, str] = {}
    for doctor in DOCTORS:
        cells = doctor_rows.get(doctor.casefold(), [])
        status = cells[0].upper() if cells else "MISSING"
        evidence = cells[1] if len(cells) > 1 else ""
        doctor_status[doctor] = status
        if status != "PASS" or len(evidence) < 12 or PLACEHOLDER_RE.search(evidence):
            issues.append(f"{doctor} doctor lacks PASS plus concrete evidence")

    score_rows, score_duplicates = _table_rows(sections.get("Scorecard", ""))
    if score_duplicates:
        issues.append("duplicate score rows")
    reviewer_scores: dict[str, dict[str, int | None]] = {"A": {}, "B": {}}
    for dimension in DIMENSIONS:
        cells = score_rows.get(dimension.casefold(), [])
        if len(cells) < 3:
            issues.append(f"missing score row or defect evidence: {dimension}")
            reviewer_scores["A"][dimension] = None
            reviewer_scores["B"][dimension] = None
            continue
        score_a = _parse_score(cells[0])
        score_b = _parse_score(cells[1])
        defect = cells[2]
        reviewer_scores["A"][dimension] = score_a
        reviewer_scores["B"][dimension] = score_b
        if score_a is None or score_b is None or len(defect) < 8 or PLACEHOLDER_RE.search(defect):
            issues.append(f"invalid scores or defect evidence for: {dimension}")

    totals = {
        reviewer: sum(score for score in scores.values() if score is not None)
        for reviewer, scores in reviewer_scores.items()
    }

    review_section = sections.get("Independent Adversarial Reviews", "")
    for reviewer in ("A", "B"):
        pattern = rf"Reviewer {reviewer}:\s*PASS\s*\|.*provider=\S+.*run_id=\S+.*artifact=\S+"
        if not re.search(pattern, review_section, flags=re.IGNORECASE):
            issues.append(f"Reviewer {reviewer} lacks structured PASS attestation")
            caps.append(89)

    urls = sorted(set(re.findall(r"https?://[^\s)>|]+", text)))
    primary_urls = [
        url
        for url in urls
        if urlparse(url).netloc.casefold().removeprefix("www.") in PRIMARY_DOMAINS
        and len(urlparse(url).path.strip("/")) >= 5
    ]
    if len(urls) < 8 or len(primary_urls) < 5:
        issues.append(
            f"source coverage too small: {len(urls)} URLs, "
            f"{len(primary_urls)} recognized primary URLs"
        )
        caps.append(74)

    mechanism = sections.get("Mechanism and Falsifiable Predictions", "")
    if not re.search(
        r"\bfalsif(?:y|ier|iable|ication)|\bkill criterion|\breject if\b",
        mechanism,
        flags=re.IGNORECASE,
    ):
        issues.append("mechanism section lacks an explicit falsifier or kill criterion")
        caps.append(59)

    novelty = sections.get("Novelty Ledger", "")
    if not re.search(r"No direct prior art found through 20\d{2}-\d{2}-\d{2} under", novelty):
        issues.append("novelty ledger lacks bounded no-direct-prior wording")
        caps.append(74)

    compute_text = sections.get("Compute and Reproducibility", "")
    has_oci_digest = any(
        OCI_DIGEST_RE.fullmatch(token.strip("`.,;")) for token in compute_text.split()
    )
    if not has_oci_digest:
        issues.append("compute section lacks a full immutable OCI digest")
        caps.append(79)
    if not re.search(r"\bsbatch\b", compute_text):
        issues.append("compute section lacks an sbatch launch command")
        caps.append(79)
    seed_match = re.search(r"\bseeds?\s*[:=]\s*\[([^]]+)\]", compute_text, flags=re.IGNORECASE)
    seed_values = (
        [int(value) for value in re.findall(r"\d+", seed_match.group(1))] if seed_match else []
    )
    if len(set(seed_values)) < 3:
        issues.append("compute section requires at least three explicit seeds")
        caps.append(79)
    if not re.search(r"\bgpu[_ -]?hours?\s*[:=]\s*\d+", compute_text, flags=re.IGNORECASE):
        issues.append("compute section lacks a numeric GPU-hour ceiling")
        caps.append(79)

    bundle: dict[str, Any] | None = None
    if not bundle_raw:
        issues.append("proposal lacks Evidence bundle metadata")
        caps.append(0)
    else:
        bundle_path = _safe_bundle_path(path, bundle_raw)
        if bundle_path is None or not bundle_path.is_file():
            issues.append("Evidence bundle is missing or escapes the proposal directory")
            caps.append(0)
        else:
            bundle = _validate_bundle(
                bundle_path,
                path,
                primary_urls,
                reviewer_scores,
                proposal_budgets,
                seed_values,
                issues,
            )

    raw_lower_score = min(totals.values()) if totals else 0
    accepted_score = min([raw_lower_score, *caps]) if caps else raw_lower_score
    if issues:
        accepted_score = min(accepted_score, 99)
    ready = not issues and totals == {"A": 100, "B": 100} and accepted_score == 100

    return {
        "path": str(path),
        "status": "PASS" if ready else "FAIL",
        "acceptedScore": accepted_score,
        "reviewerTotals": totals,
        "doctorStatus": doctor_status,
        "sourceCounts": {
            "allUrls": len(urls),
            "recognizedPrimaryUrls": len(primary_urls),
        },
        "evidenceBundleLoaded": bundle is not None,
        "hardCaps": sorted(set(caps)),
        "issues": issues,
        "remediation": issues[:1] or ["none"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal", type=Path)
    args = parser.parse_args()
    if not args.proposal.is_file():
        parser.error(f"not a file: {args.proposal}")
    report = inspect(args.proposal.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
