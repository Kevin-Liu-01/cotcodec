# ruff: noqa: E501 -- long fixture prose is intentional and easier to audit inline.

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import scripts.research_direction_doctor as doctor
from scripts.research_direction_doctor import DIMENSIONS, DOCTORS, REQUIRED_HEADINGS


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_artifact(directory: Path, name: str, content: str) -> dict[str, object]:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return {"artifact": name, "sha256": _digest(path)}


def _proposal_text() -> str:
    urls = [
        "https://arxiv.org/abs/2405.21060",
        "https://arxiv.org/abs/2407.04620",
        "https://arxiv.org/abs/2412.06464",
        "https://github.com/ramp-public/portallib",
        "https://proceedings.mlr.press/v139/sandler21a.html",
        "https://openreview.net/forum?id=Gvex75bPMI",
        "https://aclanthology.org/2026.eacl-long.145/",
        "https://labs.ramp.com/research/portal-portable-task-adaptation/",
    ]
    evidence = "\n".join(f"- [primary source {index}]({url})" for index, url in enumerate(urls))
    doctor_rows = "\n".join(
        f"| {name} | PASS | evidence/{name.lower()}.json records concrete checks | none |"
        for name in DOCTORS
    )
    score_rows = "\n".join(
        f"| {name} | 10 | 10 | signed reviewer artifacts identify no remaining defect |"
        for name in DIMENSIONS
    )
    sections = {
        "Claim and Research Question": "A precise research question with one intervention and one measurable outcome.",
        "Strategic Fit and Why Now": "This mechanism directly tests the project thesis and has a time-sensitive empirical opening.",
        "Primary-Source Evidence": evidence,
        "Closest Prior Work": "The cited primary works define occupied axes and the exact comparison boundary for this claim.",
        "Novelty Ledger": "No direct prior art found through 2026-08-10 under primary papers, code, and citation-graph coverage.",
        "Mechanism and Falsifiable Predictions": "The mechanism has one state transition. Reject if the registered primary endpoint is below zero.",
        "Cheapest Decisive Pilot": "Run one bounded pilot with sealed task families and a single primary endpoint before scaling.",
        "Controls, Baselines, and Ablations": "Use matched parameters, evidence, update counts, state bytes, wall time, and oracle controls.",
        "Evaluation, Statistics, and Leakage Checks": "Use sealed task and model families, paired seeds, confidence intervals, and a fixed threshold.",
        "Compute and Reproducibility": (
            "image: registry.example/cotcodec@sha256:" + "a" * 64 + "\n\n"
            "launch: sbatch --export=NONE infra/slurm/research.sbatch\n\n"
            "seeds: [42, 43, 44]\n\ngpu_hours: 8\n\nCheckpoints and outputs are immutable."
        ),
        "Safety, Data Rights, and Monitorability": "Test poisoning, isolation, deletion, refusal consistency, licensing, and state probes.",
        "Negative-Result Value": "A clean null result rules out this portability mechanism under a matched information budget.",
        "Preflight Doctors": (
            "| Doctor | Status | Evidence | Remediation |\n|---|---|---|---|\n" + doctor_rows
        ),
        "Independent Adversarial Reviews": (
            "Reviewer A: PASS | provider=provider-a | model=model-a | run_id=run-a | artifact=review-a.json\n\n"
            "Reviewer B: PASS | provider=provider-b | model=model-b | run_id=run-b | artifact=review-b.json"
        ),
        "Scorecard": (
            "| Dimension | Reviewer A | Reviewer B | Defect/evidence |\n|---|---:|---:|---|\n"
            + score_rows
        ),
        "Iteration Log": "| Wave | Score | Defect | Change | Result |\n|---:|---:|---|---|---|\n| 1 | 100 | none | signed evidence verified | terminate |",
    }
    assert set(sections) == set(REQUIRED_HEADINGS)
    body = "\n\n".join(f"## {name}\n\n{sections[name]}" for name in REQUIRED_HEADINGS)
    return (
        "# Research Direction: fixture\n\n"
        "**Status:** pilot-ready  \n**Owner:** fixture  \n"
        "**Source cutoff:** 2026-08-10  \n"
        "**Coverage limits:** authenticated X unavailable; primary sources captured  \n"
        "**Budgets:** queries=20; wall_minutes=60; tokens=10000; dollars=10; waves=2; gpu_hours=8  \n"
        "**Novelty verdict:** NO_DIRECT_PRIOR_FOUND  \n"
        "**Safety verdict:** PASS  \n"
        "**Evidence bundle:** evidence/bundle.json\n\n" + body
    )


def _public_key_b64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode()


def _build_valid_fixture(root: Path, monkeypatch) -> tuple[Path, Path]:
    proposal = root / "proposal.md"
    evidence_dir = root / "evidence"
    evidence_dir.mkdir()
    proposal.write_text(_proposal_text(), encoding="utf-8")

    repo_root = root / "repo"
    adapter_path = repo_root / "harness/benchmarks/fixture.py"
    adapter_path.parent.mkdir(parents=True)
    adapter_path.write_text("class FixtureAdapter:\n    ready = True\n", encoding="utf-8")
    runner_path = repo_root / "harness/runner.py"
    runner_path.write_text(
        "async def run_experiment(config):\n    return {'ok': True}\n", encoding="utf-8"
    )
    monkeypatch.setattr(doctor, "REPO_ROOT", repo_root)

    urls = sorted(set(__import__("re").findall(r"https?://[^\s)>|]+", proposal.read_text())))
    snapshots = []
    for index, url in enumerate(urls):
        record = _write_artifact(
            evidence_dir,
            f"source-{index}.txt",
            f"Captured primary source URL: {url}\n" + "verified content " * 12,
        )
        record.update({"url": url, "http_status": 200})
        snapshots.append(record)

    query_log = _write_artifact(
        evidence_dir,
        "queries.json",
        json.dumps({"queries": ["portable update rules", "closest prior work"]}) + " " * 80,
    )
    proposal_hash = _digest(proposal)

    manifest = _write_artifact(
        evidence_dir,
        "manifest.yaml",
        (
            "name: fixture\nimage: registry.example/cotcodec@sha256:"
            + "a" * 64
            + "\ncommand: [python, -m, harness.runner, experiments/fixture.yaml]\n"
            "run_root: /shared/runs\ngit_sha: "
            + "b" * 40
            + "\nsource_sha256: "
            + "c" * 64
            + "\nseeds: [42, 43, 44]\n"
            "resources: {gpu_type: h100, gpus: 1, cpus: 16, memory_gb: 64, minutes: 120}\n"
            "budget: {max_gpu_hours: 2}\n"
        ),
    )
    compute: dict[str, object] = {
        "image_digest": "registry.example/cotcodec@sha256:" + "a" * 64,
        "real_model_loop": True,
        "benchmark_adapter": "harness/benchmarks/fixture.py",
        "manifest": manifest,
    }
    for label in ("container_smoke", "slurm_test", "provenance_verification"):
        attestation = _write_artifact(
            evidence_dir,
            f"{label}.txt",
            f"{label} completed with return code zero and artifact validation. " * 3,
        )
        attestation.update({"status": "PASS", "return_code": 0})
        compute[label] = attestation

    doctors = []
    for name in DOCTORS:
        record = _write_artifact(
            evidence_dir,
            f"{name.lower()}.json",
            json.dumps({"doctor": name, "checks": ["one", "two"], "status": "PASS"}) + " " * 80,
        )
        record.update({"name": name, "status": "PASS"})
        doctors.append(record)

    audit_payload = {
        "wave": 1,
        "score": 100,
        "best_score": 100,
        "run_id": "gauntlet-fixture-run",
        "candidate_sha256": proposal_hash,
        "queries": 20,
        "wall_minutes": 60,
        "tokens": 10000,
        "dollars": 10,
        "gpu_hours": 8,
        "termination_reason": "all_doctors_and_reviews_passed",
        "previous_hash": "0" * 64,
    }
    audit_payload["hash"] = hashlib.sha256(
        json.dumps(audit_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    audit_path = evidence_dir / "audit.jsonl"
    audit_path.write_text(json.dumps(audit_payload, sort_keys=True) + "\n", encoding="utf-8")
    audit = {
        "artifact": "audit.jsonl",
        "sha256": _digest(audit_path),
        "final_hash": audit_payload["hash"],
    }

    bundle: dict[str, object] = {
        "schema_version": 1,
        "proposal_sha256": proposal_hash,
        "source_snapshots": snapshots,
        "query_log": query_log,
        "compute": compute,
        "doctors": doctors,
        "audit_log": audit,
    }
    evidence_root = doctor._evidence_root(bundle)
    bundle["evidence_root_sha256"] = evidence_root

    trust_records = []
    reviews = []
    for reviewer, provider in (("a", "provider-a"), ("b", "provider-b")):
        private_key = Ed25519PrivateKey.generate()
        key_id = f"key-{reviewer}"
        trust_records.append(
            {
                "key_id": key_id,
                "provider": provider,
                "roles": ["reviewer"],
                "public_key_base64": _public_key_b64(private_key),
            }
        )
        review_output = {
            "verdict": "PASS",
            "model": f"model-{reviewer}",
            "provider_request_id": f"request-{reviewer}",
            "timestamp": "2026-08-10T20:00:00Z",
            "scores": {dimension: 10 for dimension in DIMENSIONS},
        }
        record = _write_artifact(
            evidence_dir,
            f"review-{reviewer}.json",
            json.dumps(review_output, indent=2, sort_keys=True),
        )
        record.update(
            {
                "provider": provider,
                "model": f"model-{reviewer}",
                "run_id": f"run-{reviewer}",
                "verdict": "PASS",
                "candidate_sha256": proposal_hash,
                "evidence_root_sha256": evidence_root,
                "prompt_sha256": reviewer * 64,
                "signed_at": "2026-08-10T20:01:00Z",
                "key_id": key_id,
            }
        )
        record["signature"] = base64.b64encode(
            private_key.sign(doctor._review_signature_payload(record))
        ).decode()
        reviews.append(record)
    bundle["reviews"] = reviews

    trust_path = root / "trusted-attestors.json"
    trust_path.write_text(
        json.dumps({"schema_version": 1, "attestors": trust_records}), encoding="utf-8"
    )
    monkeypatch.setattr(doctor, "TRUST_STORE_PATH", trust_path)
    monkeypatch.setattr(doctor, "TRUST_STORE_PROTECTED", True)
    monkeypatch.setattr(doctor, "TRUST_STORE_EXPECTED_SHA256", _digest(trust_path))

    bundle_path = evidence_dir / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    return proposal, evidence_dir / "review-a.json"


def test_empty_self_attested_proposal_cannot_manufacture_100(tmp_path: Path) -> None:
    proposal = tmp_path / "fake.md"
    headings = "\n".join(f"## {heading}\n\nplaceholder content" for heading in REQUIRED_HEADINGS)
    proposal.write_text(headings + "\n\nFalsifier Docker Slurm seeds\n", encoding="utf-8")
    report = doctor.inspect(proposal)
    assert report["status"] == "FAIL"
    assert report["acceptedScore"] == 0
    assert report["evidenceBundleLoaded"] is False


def test_signed_hashed_bundle_passes_and_tampering_fails(tmp_path: Path, monkeypatch) -> None:
    proposal, review_path = _build_valid_fixture(tmp_path, monkeypatch)
    report = doctor.inspect(proposal)
    assert report["status"] == "PASS", report["issues"]

    review_path.write_text(review_path.read_text() + "tampered", encoding="utf-8")
    tampered = doctor.inspect(proposal)
    assert tampered["status"] == "FAIL"
    assert tampered["acceptedScore"] <= 99
    assert any("hash mismatch" in issue for issue in tampered["issues"])


def test_locally_rehashed_review_cannot_bypass_trusted_signature(
    tmp_path: Path, monkeypatch
) -> None:
    proposal, review_path = _build_valid_fixture(tmp_path, monkeypatch)
    payload = json.loads(review_path.read_text(encoding="utf-8"))
    payload["verdict"] = "FAIL"
    review_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    bundle_path = tmp_path / "evidence/bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["reviews"][0]["sha256"] = _digest(review_path)
    bundle["reviews"][0]["verdict"] = "FAIL"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")

    report = doctor.inspect(proposal)
    assert report["status"] == "FAIL"
    assert any("invalid Ed25519 signature" in issue for issue in report["issues"])


def test_repo_local_trust_store_is_rejected(tmp_path: Path, monkeypatch) -> None:
    proposal, _ = _build_valid_fixture(tmp_path, monkeypatch)
    repo_trust = doctor.REPO_ROOT / "trusted-attestors.json"
    repo_trust.write_bytes(doctor.TRUST_STORE_PATH.read_bytes())
    monkeypatch.setattr(doctor, "TRUST_STORE_PATH", repo_trust)
    monkeypatch.setattr(doctor, "TRUST_STORE_EXPECTED_SHA256", _digest(repo_trust))

    report = doctor.inspect(proposal)
    assert report["status"] == "FAIL"
    assert any("outside the proposal repository" in issue for issue in report["issues"])


def test_doctor_reuses_real_slurm_manifest_validator(tmp_path: Path, monkeypatch) -> None:
    proposal, _ = _build_valid_fixture(tmp_path, monkeypatch)
    manifest_path = tmp_path / "evidence/manifest.yaml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace("git_sha: " + "b" * 40 + "\n", ""),
        encoding="utf-8",
    )
    bundle_path = tmp_path / "evidence/bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["compute"]["manifest"]["sha256"] = _digest(manifest_path)
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")

    report = doctor.inspect(proposal)
    assert report["status"] == "FAIL"
    assert any("git_sha must be" in issue for issue in report["issues"])


def test_audit_counters_cannot_exceed_declared_budget(tmp_path: Path, monkeypatch) -> None:
    proposal, _ = _build_valid_fixture(tmp_path, monkeypatch)
    audit_path = tmp_path / "evidence/audit.jsonl"
    row = json.loads(audit_path.read_text(encoding="utf-8"))
    row["queries"] = 21
    row_without_hash = {key: value for key, value in row.items() if key != "hash"}
    row["hash"] = hashlib.sha256(
        json.dumps(row_without_hash, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    audit_path.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    bundle_path = tmp_path / "evidence/bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["audit_log"]["sha256"] = _digest(audit_path)
    bundle["audit_log"]["final_hash"] = row["hash"]
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")

    report = doctor.inspect(proposal)
    assert report["status"] == "FAIL"
    assert any("invalid cumulative queries" in issue for issue in report["issues"])
