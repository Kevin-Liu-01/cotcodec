#!/usr/bin/env python3
"""Create an immutable, integrity-checked analysis of a frontier screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.causal_memory_trials import TrialBundle  # noqa: E402
from scripts.run_memory_model_screen import summarize_screen  # noqa: E402


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _verify_bundle(bundle_root: Path, expected_manifest_sha256: str) -> TrialBundle:
    manifest_path = bundle_root / "manifest.json"
    actual_manifest_sha256 = _sha256_file(manifest_path)
    if actual_manifest_sha256 != expected_manifest_sha256:
        raise ValueError("bundle manifest no longer matches the original report")
    manifest = _read_json(manifest_path)
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("bundle manifest has no file hash map")
    for name, expected in files.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError("bundle manifest file entry is malformed")
        if _sha256_file(bundle_root / name) != expected:
            raise ValueError(f"bundle artifact changed: {name}")
    return TrialBundle(
        root=bundle_root,
        manifest_sha256=actual_manifest_sha256,
    )


def _failure_rows(bundle: TrialBundle, *, visibility: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    observed_path = bundle.root / "observed_trials.jsonl"
    for line in observed_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        outcome = row["outcome"]
        if outcome["visibility"] != visibility or outcome["success"]:
            continue
        frame = json.loads(outcome["memory_frame_json"])
        trace = json.loads(outcome["tool_trace_json"])
        rows.append(
            {
                "trial_id": row["trial_id"],
                "stratum": frame["stratum"],
                "expected": trace["expected"],
                "actual": trace["actual"],
                "candidate_records": [
                    record for record in frame["records"] if record["candidate"]
                ],
            }
        )
    return rows


def reanalyze_frontier_screen(
    run_root: Path,
    output_dir: Path,
    *,
    config_path: Path,
) -> dict[str, Any]:
    run_root = run_root.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty analysis root: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    _fsync_dir(output_dir.parent)

    original_report_path = run_root / "frontier-screen-report.json"
    preflight_path = run_root / "provider-preflight.json"
    aa_path = run_root / "aa-drift.json"
    original = _read_json(original_report_path)
    preflight = _read_json(preflight_path)
    aa = _read_json(aa_path)
    bundle = _verify_bundle(
        run_root / "collection" / "bundle",
        str(original["bundle_manifest_sha256"]),
    )
    if _sha256_file(preflight_path) != original["provider_preflight_sha256"]:
        raise ValueError("provider preflight no longer matches the original report")
    if _sha256_file(aa_path) != original["aa_drift_sha256"]:
        raise ValueError("A/A artifact no longer matches the original report")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    gates_config = config["eligibility_gates"]
    metrics = summarize_screen(bundle)
    stratum_successes = [
        cell["served_oracle_success"] for cell in metrics["by_stratum"].values()
    ]
    minimum_success = float(gates_config["minimum_oracle_memory_success"])
    revised_gates = {
        "valid_action_json_rate": metrics["valid_action_rate"]
        >= float(gates_config["minimum_valid_action_json_rate"]),
        "model_receipts_bound": metrics["model_receipt_rate"] == 1.0,
        "aa_success_drift": aa["absolute_success_rate_drift_points"]
        <= float(gates_config["maximum_aa_success_drift_points"]),
        "served_oracle_success": metrics["served_oracle_success"] >= minimum_success,
        "every_stratum_has_served_evidence": all(
            value is not None for value in stratum_successes
        ),
        "per_stratum_oracle_success": all(
            value is not None and value >= minimum_success
            for value in stratum_successes
        ),
    }
    source_receipt_present = isinstance(preflight.get("source"), dict)
    report = {
        "schema_version": 2,
        "status": (
            "POSTHOC_COMPETENCE_TRANSPORT_PASS"
            if all(revised_gates.values())
            else "POSTHOC_COMPETENCE_TRANSPORT_FAIL"
        ),
        "scientific_result": False,
        "model_id": original["model_id"],
        "scope": "post-hoc competence transport analysis; no memory-policy effect",
        "limitations": [
            "The run used single-arm randomized service, not paired counterfactual replay.",
            "The generated competence source did not exercise the safety suite.",
            "The revised per-stratum gates were applied after collection.",
            (
                "The original preflight predates source receipts, so exact source-tree "
                "publication provenance is unavailable."
                if not source_receipt_present
                else "The original source receipt is available in provider-preflight.json."
            ),
        ],
        "source_receipt_present": source_receipt_present,
        "inputs": {
            "run_root": str(run_root),
            "original_report_sha256": _sha256_file(original_report_path),
            "provider_preflight_sha256": _sha256_file(preflight_path),
            "aa_drift_sha256": _sha256_file(aa_path),
            "bundle_manifest_sha256": bundle.manifest_sha256,
            "analysis_config_sha256": _sha256_file(config_path),
            "analyzer_sha256": _sha256_file(Path(__file__).resolve()),
        },
        "metrics": metrics,
        "aa_drift_summary": {
            key: aa[key]
            for key in (
                "trials",
                "first_success_rate",
                "second_success_rate",
                "absolute_success_rate_drift_points",
                "action_disagreement_rate",
            )
        },
        "served_failures": _failure_rows(bundle, visibility="serve"),
        "holdout_failures": _failure_rows(bundle, visibility="holdout"),
        "revised_gates": revised_gates,
        "usage": original["usage"],
    }
    report_sha256 = _atomic_json(output_dir / "analysis.json", report)
    manifest = {
        "schema_version": 1,
        "status": "SEALED",
        "files": {"analysis.json": report_sha256},
        "input_bundle_manifest_sha256": bundle.manifest_sha256,
    }
    _atomic_json(output_dir / "manifest.json", manifest)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "experiments" / "memory" / "stage1-model-transport.yaml",
    )
    args = parser.parse_args()
    report = reanalyze_frontier_screen(
        args.run_root,
        args.output_dir,
        config_path=args.config,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
