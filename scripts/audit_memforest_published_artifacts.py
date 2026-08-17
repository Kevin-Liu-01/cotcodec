#!/usr/bin/env python3
# ruff: noqa: E501 -- immutable hashes and exact claim-boundary text are inline.
"""Audit MemForest's submitted and revision artifacts without model calls.

This is artifact archaeology. It does not regenerate memory stores, retrieval,
answers, judge labels, or native write traces.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REPOSITORY = "https://github.com/Concyclics/MemForest"
REVISION = "fb4320a84d296bf7b0752d7ef1f2ad0726ae0b22"
TREE = "2e30793c77ef0b7fc8b36bd6d3648a1d9f2fecb2"
ARCHIVE_SHA256 = "3809857bcd1f2fb799038a604149a1354277f80dd87893c7f2e3949c743211e0"
STATUS = "MEMFOREST_RELEASED_ARTIFACTS_AUDITED_NOT_REPRODUCED"
SOURCE_FILES = {
    "LICENSE": "f91f1d776c397faf0e8f2b87e23e7e7f9bd312ec0751397ab183752b1b217efc",
    "README.md": "c54efcb0bd821c55f19e859955cfcee034b1df77b151c274eaf86faa7446ca1f",
    "requirements.txt": "e596f2354b4f732fd45bd3e8f958650bf2309bd1511fbc4f69a405ab236b57f4",
    "benchmark/README.md": "f8cb42cf1dd9c049f8ed588b5d27caf237f2ab5a21d888034a3cfa27323daf4e",
    "reproducibility/PROTOCOL.md": "99eed4dd5e2dbd49858f4694072fb90f58fc81625549e4bd25a8db689a1bc52e",
    "reproducibility/RESULTS.md": "e7238566a9799611ef0ef1c0b12c726589a4fad32e3793b1f49cae6c6089956a",
    "reproducibility/SHA256SUMS": "d7502c9be9588a7699a7a198bd03dac02de80a2a71cbc7cdc089f3b2c4f197ef",
    "reproducibility/manifests/revision_release.json": "c49c0a10b6549c1afec2702261500d7eb554307acfdf6658dbe8521ba7353b1d",
    "reproducibility/scripts/verify_release.py": "0e7ac23ab60694a468439e0e47bd97d854c14cee14caf92c0381a2315b669020",
}
SUBMITTED = {
    "benchmark/locomo_per_question_30b.csv": {
        "sha256": "762d62aa33eccdbcbe229cf8c15c06063dde18778e16d8001b7b4773bee08487",
        "size": 42_161_963,
        "rows": {
            "evermemos": 1986,
            "lightmem": 1986,
            "mem0": 1986,
            "memforest": 1986,
            "memoryos": 1986,
            "mempalace": 1986,
        },
    },
    "benchmark/locomo_per_question_4b.csv": {
        "sha256": "2d79981b7960093f2e2393ea3dd4bfc98c9a447b7209f01e9aa37b29c8449689",
        "size": 47_316_325,
        "rows": {
            "evermemos": 1986,
            "lightmem": 1986,
            "mem0": 1986,
            "memforest": 1986,
            "memoryos": 1986,
            "mempalace": 1986,
        },
    },
    "benchmark/longmemeval_per_question_30b.csv": {
        "sha256": "b9798fe18acf61e62bef51db3097cfda7bf0aa0c9c3831f72f8f124d82ee856f",
        "size": 24_573_434,
        "rows": {
            "evermemos": 474,
            "lightmem": 500,
            "mem0": 500,
            "memforest": 500,
            "memoryos": 500,
            "mempalace": 500,
        },
    },
    "benchmark/longmemeval_per_question_4b.csv": {
        "sha256": "03aa56f9d908a8925b86f0b4ac1cb09350944a3b307b767352a6dae9b9e3d9a8",
        "size": 29_277_419,
        "rows": {
            "evermemos": 500,
            "lightmem": 500,
            "mem0": 485,
            "memforest": 500,
            "memoryos": 500,
            "mempalace": 500,
        },
    },
}
CSV_FIELDS = [
    "method",
    "model_size",
    "question_type",
    "qid",
    "question",
    "gold_answer",
] + [field for index in range(1, 9) for field in (f"answer_{index}", f"judge_{index}")]
MAIN_VALUES = {
    ("qwen3_4b", "memforest", "longmemeval", "overall"): 0.726,
    ("qwen3_30b", "memforest", "longmemeval", "overall"): 0.818,
    ("gemma4_12b", "memforest_embed", "longmemeval", "overall"): 0.784,
    ("qwen3_4b", "memforest", "locomo", "cat1-4"): 0.7811688311688312,
    ("qwen3_30b", "memforest", "locomo", "cat1-4"): 0.8409090909090909,
    ("gemma4_12b", "evermemos", "locomo", "cat1-4"): 0.8857142857142857,
}
CLAIM_BOUNDARY = (
    "Exact pinned submitted-CSV integrity and score recomputation, revision-package "
    "checksum integrity, API-free verifier execution, public-judge summary "
    "recomputation, and write-rate coordinate arithmetic; not an independent "
    "regrade, retrieval or construction reproduction, sustained throughput "
    "reproduction, localized-maintenance mechanism effect, memory-quality result, "
    "H100 actor admission, or publication evidence."
)


class MemForestArtifactAuditError(ValueError):
    """Raised when the pinned MemForest artifact surface drifts."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular(path: Path, label: str) -> Path:
    if not path.is_file() or path.is_symlink():
        raise MemForestArtifactAuditError(f"{label} must be a regular non-symlink file")
    return path


def verify_file(path: Path, expected_sha: str, expected_size: int | None = None) -> None:
    regular(path, str(path))
    if expected_size is not None and path.stat().st_size != expected_size:
        raise MemForestArtifactAuditError(f"size mismatch: {path}")
    if sha256_file(path) != expected_sha:
        raise MemForestArtifactAuditError(f"SHA-256 mismatch: {path}")


def git(source_root: Path, *arguments: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=False,
        capture_output=True,
        text=not binary,
    )
    if completed.returncode:
        stderr = (
            completed.stderr if isinstance(completed.stderr, str) else completed.stderr.decode()
        )
        raise MemForestArtifactAuditError(f"git {' '.join(arguments)} failed: {stderr.strip()}")
    return completed.stdout


def normalize_repository(value: str) -> str:
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized


def verify_source(source_root: Path) -> dict[str, Any]:
    if not source_root.is_dir() or source_root.is_symlink():
        raise MemForestArtifactAuditError("source root must be a regular directory")
    for relative, expected in SOURCE_FILES.items():
        verify_file(source_root / relative, expected)
    actual = {
        "repository": normalize_repository(str(git(source_root, "remote", "get-url", "origin"))),
        "revision": str(git(source_root, "rev-parse", "HEAD")).strip(),
        "tree": str(git(source_root, "rev-parse", "HEAD^{tree}")).strip(),
    }
    if actual != {"repository": REPOSITORY, "revision": REVISION, "tree": TREE}:
        raise MemForestArtifactAuditError("source identity drifted")
    if str(git(source_root, "status", "--porcelain", "--untracked-files=all")).strip():
        raise MemForestArtifactAuditError("source checkout must be clean")
    archive = git(source_root, "archive", "--format=tar", "HEAD", binary=True)
    if not isinstance(archive, bytes) or sha256_bytes(archive) != ARCHIVE_SHA256:
        raise MemForestArtifactAuditError("source archive bytes drifted")
    return {**actual, "git_archive_tar_sha256": ARCHIVE_SHA256, "files": SOURCE_FILES}


def _submitted_metrics(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    verify_file(path, str(expected["sha256"]), int(expected["size"]))
    counts: Counter[str] = Counter()
    qids: dict[str, set[str]] = defaultdict(set)
    correct_first: Counter[str] = Counter()
    correct_all: Counter[str] = Counter()
    labels_all: Counter[str] = Counter()
    empty_gold: Counter[str] = Counter()
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CSV_FIELDS:
            raise MemForestArtifactAuditError(f"submitted CSV schema drifted: {path}")
        for row in reader:
            method = row["method"]
            if not method or not row["qid"] or not row["question"]:
                raise MemForestArtifactAuditError(f"submitted CSV identity cell is empty: {path}")
            if not row["gold_answer"].strip():
                empty_gold[method] += 1
            counts[method] += 1
            qids[method].add(row["qid"])
            labels = [row[f"judge_{index}"].strip().upper() for index in range(1, 9)]
            if any(label not in {"CORRECT", "WRONG"} for label in labels):
                raise MemForestArtifactAuditError(f"submitted judge label drifted: {path}")
            if any(not row[f"answer_{index}"].strip() for index in range(1, 9)):
                raise MemForestArtifactAuditError(f"submitted answer is empty: {path}")
            labels_all.update(labels)
            correct_first[method] += int(labels[0] == "CORRECT")
            correct_all[method] += sum(label == "CORRECT" for label in labels)
    if dict(sorted(counts.items())) != dict(sorted(expected["rows"].items())):
        raise MemForestArtifactAuditError(f"submitted method coverage drifted: {path}")
    if any(len(qids[method]) != count for method, count in counts.items()):
        raise MemForestArtifactAuditError(f"submitted method has duplicate qids: {path}")
    return {
        "sha256": expected["sha256"],
        "size": expected["size"],
        "method_rows": dict(sorted(counts.items())),
        "empty_gold_rows": dict(sorted(empty_gold.items())),
        "labels": dict(sorted(labels_all.items())),
        "methods": {
            method: {
                "rows": counts[method],
                "pass1_correct": correct_first[method],
                "pass1": correct_first[method] / counts[method],
                "eight_sample_correct": correct_all[method],
                "eight_sample_accuracy": correct_all[method] / (8 * counts[method]),
            }
            for method in sorted(counts)
        },
    }


def audit_submitted(source_root: Path) -> dict[str, Any]:
    result = {
        relative: _submitted_metrics(source_root / relative, expected)
        for relative, expected in SUBMITTED.items()
    }
    headline = result["benchmark/longmemeval_per_question_30b.csv"]["methods"]["memforest"]
    if headline["pass1_correct"] != 399 or headline["rows"] != 500 or headline["pass1"] != 0.798:
        raise MemForestArtifactAuditError("submitted MemForest 30B headline drifted")
    return result


def verify_checksum_manifest(source_root: Path) -> dict[str, Any]:
    manifest = regular(source_root / "reproducibility/SHA256SUMS", "checksum manifest")
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        relative = relative.strip().lstrip("*")
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts or relative in entries:
            raise MemForestArtifactAuditError("unsafe or duplicate checksum manifest path")
        entries[relative] = expected
    if len(entries) != 154:
        raise MemForestArtifactAuditError("revision checksum manifest count drifted")
    for relative, expected in entries.items():
        verify_file(source_root / relative, expected)
    benchmark_entries = sorted(path for path in entries if path.startswith("benchmark/"))
    if benchmark_entries:
        raise MemForestArtifactAuditError(
            "submitted snapshot unexpectedly entered revision manifest"
        )
    return {
        "declared_files": len(entries),
        "manifest_sha256": sha256_file(manifest),
        "submitted_snapshot_paths_declared": benchmark_entries,
    }


def run_upstream_verifier(source_root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [os.environ.get("PYTHON", "python3"), "reproducibility/scripts/verify_release.py"],
        cwd=source_root,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONHASHSEED": "0"},
    )
    if completed.returncode or completed.stdout.strip() != "revision release verification: PASS":
        raise MemForestArtifactAuditError(
            f"upstream release verifier failed: {completed.stdout}{completed.stderr}"
        )
    return {
        "command": "python3 reproducibility/scripts/verify_release.py",
        "stdout": completed.stdout.strip(),
        "exit_code": completed.returncode,
        "verifier_sha256": SOURCE_FILES["reproducibility/scripts/verify_release.py"],
    }


def _read_csv(path: Path, fields: Iterable[str]) -> list[dict[str, str]]:
    regular(path, str(path))
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(fields):
            raise MemForestArtifactAuditError(f"CSV schema drifted: {path}")
        return list(reader)


def _slice(rows: list[dict[str, str]], benchmark: str, name: str) -> list[dict[str, str]]:
    if name == "overall":
        return rows
    if benchmark == "locomo" and name == "cat1-4":
        return [row for row in rows if row["question_type"] != "adversarial"]
    return [row for row in rows if row["question_type"] == name]


def audit_public_summary(source_root: Path) -> dict[str, Any]:
    root = source_root / "reproducibility/results/public_judge_three_backbone"
    label_fields = [
        "model",
        "method",
        "benchmark",
        "qid",
        "question_type",
        "strict_label",
        "public_label",
        "correct_votes",
        "wrong_votes",
        "complete_repetitions",
        "answer_source",
    ]
    summary_fields = [
        "model",
        "method",
        "benchmark",
        "slice",
        "n",
        "public_evaluated_n",
        "public_correct",
        "public_accuracy",
        "strict_paired_n",
        "strict_paired_accuracy",
        "public_paired_accuracy",
    ]
    labels = _read_csv(root / "per_question_labels.csv", label_fields)
    summaries = _read_csv(root / "summary.csv", summary_fields)
    if len(labels) != 59_664 or len(summaries) != 336:
        raise MemForestArtifactAuditError("public judge row count drifted")
    identities = {(row["model"], row["method"], row["benchmark"], row["qid"]) for row in labels}
    if len(identities) != len(labels):
        raise MemForestArtifactAuditError("public judge identities are duplicated")
    if any(
        row["strict_label"] not in {"", "CORRECT", "WRONG"}
        or row["public_label"] not in {"CORRECT", "WRONG"}
        or row["complete_repetitions"] != "True"
        or not row["answer_source"]
        for row in labels
    ):
        raise MemForestArtifactAuditError("public judge label completeness drifted")
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in labels:
        grouped[(row["model"], row["method"], row["benchmark"])].append(row)
    values: dict[tuple[str, str, str, str], float] = {}
    for summary in summaries:
        group_key = (summary["model"], summary["method"], summary["benchmark"])
        selected = _slice(grouped[group_key], summary["benchmark"], summary["slice"])
        n = len(selected)
        public_correct = sum(row["public_label"] == "CORRECT" for row in selected)
        strict_selected = [row for row in selected if row["strict_label"]]
        strict_correct = sum(row["strict_label"] == "CORRECT" for row in strict_selected)
        paired_public_correct = sum(row["public_label"] == "CORRECT" for row in strict_selected)
        public_accuracy = public_correct / n
        strict_accuracy = strict_correct / len(strict_selected) if strict_selected else 0.0
        paired_public_accuracy = (
            paired_public_correct / len(strict_selected) if strict_selected else 0.0
        )
        observed = {
            "n": int(summary["n"]),
            "public_evaluated_n": int(summary["public_evaluated_n"]),
            "public_correct": int(summary["public_correct"]),
            "public_accuracy": float(summary["public_accuracy"]),
            "strict_paired_n": int(summary["strict_paired_n"]),
            "strict_paired_accuracy": (
                float(summary["strict_paired_accuracy"])
                if summary["strict_paired_accuracy"]
                else None
            ),
            "public_paired_accuracy": (
                float(summary["public_paired_accuracy"])
                if summary["public_paired_accuracy"]
                else None
            ),
        }
        expected = {
            "n": n,
            "public_evaluated_n": n,
            "public_correct": public_correct,
            "public_accuracy": public_accuracy,
            "strict_paired_n": len(strict_selected),
            "strict_paired_accuracy": strict_accuracy if strict_selected else None,
            "public_paired_accuracy": paired_public_accuracy if strict_selected else None,
        }
        for key in ("n", "public_evaluated_n", "public_correct", "strict_paired_n"):
            if observed[key] != expected[key]:
                raise MemForestArtifactAuditError(
                    f"public summary integer drifted: {group_key} {key}"
                )
        for key in ("public_accuracy", "strict_paired_accuracy", "public_paired_accuracy"):
            if observed[key] is None or expected[key] is None:
                if observed[key] is not expected[key]:
                    raise MemForestArtifactAuditError(
                        f"public summary optional accuracy drifted: {group_key} {key}"
                    )
            elif abs(float(observed[key]) - float(expected[key])) > 1e-15:
                raise MemForestArtifactAuditError(
                    f"public summary accuracy drifted: {group_key} {key}"
                )
        values[(*group_key, summary["slice"])] = public_accuracy
    for key, expected in MAIN_VALUES.items():
        if abs(values[key] - expected) > 1e-15:
            raise MemForestArtifactAuditError(f"selected main-table value drifted: {key}")
    return {
        "label_rows": len(labels),
        "summary_rows_recomputed": len(summaries),
        "unresolved_rows": 0,
        "unique_question_method_rows": len(identities),
        "selected_main_values": {
            "|".join(key): value for key, value in sorted(MAIN_VALUES.items())
        },
    }


def audit_write_rates(source_root: Path) -> dict[str, Any]:
    fields = [
        "benchmark",
        "method",
        "model",
        "source_id",
        "source_turns",
        "build_seconds",
        "build_rate_turns_per_second",
        "timing_n",
        "cross_instance_concurrency",
        "measurement_scope",
        "source_artifact",
    ]
    path = source_root / "reproducibility/results/write_path_traces/summary.csv"
    rows = _read_csv(path, fields)
    if len(rows) != 10:
        raise MemForestArtifactAuditError("write-rate coordinate count drifted")
    coordinates: dict[str, dict[str, Any]] = {}
    for row in rows:
        recomputed = float(row["source_turns"]) / float(row["build_seconds"])
        published = float(row["build_rate_turns_per_second"])
        if abs(recomputed - published) > 1e-8:
            raise MemForestArtifactAuditError("write-rate arithmetic drifted")
        key = f"{row['benchmark']}|{row['method']}"
        coordinates[key] = {
            "published": published,
            "recomputed": recomputed,
            "timing_n": int(row["timing_n"]),
            "cross_instance_concurrency": row["cross_instance_concurrency"],
            "measurement_scope": row["measurement_scope"],
        }
    if {row["source_id"] for row in rows if row["benchmark"] == "locomo"} != {"conv-43"}:
        raise MemForestArtifactAuditError("LoCoMo write-rate source scope drifted")
    return {
        "rows": len(rows),
        "coordinates": dict(sorted(coordinates.items())),
        "sustained_concurrent_throughput": False,
    }


def audit_memforest_published_artifacts(source_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the deterministic report and compact semantic projection."""
    source = verify_source(source_root)
    submitted = audit_submitted(source_root)
    revision_checksums = verify_checksum_manifest(source_root)
    upstream_verifier = run_upstream_verifier(source_root)
    public_summary = audit_public_summary(source_root)
    write_rates = audit_write_rates(source_root)
    projection = {
        "_meta": {
            "schema_version": 1,
            "source_id": "memforest",
            "revision": REVISION,
            "status": STATUS,
        },
        "submitted": submitted,
        "revision_checksums": revision_checksums,
        "public_summary": public_summary,
        "write_rates": write_rates,
        "claim_gates": {
            "independent_rejudge_completed": False,
            "retrieval_or_construction_reproduced": False,
            "sustained_concurrent_throughput_reproduced": False,
        },
    }
    projection_sha = sha256_bytes(canonical(projection))
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": "not-granted-by-artifact-audit",
        "source": source,
        "submitted": submitted,
        "revision_checksums": revision_checksums,
        "upstream_verifier": upstream_verifier,
        "public_summary": public_summary,
        "write_rates": write_rates,
        "semantic_projection_sha256": projection_sha,
        "claim_boundary": CLAIM_BOUNDARY,
        "limitations": [
            "The submitted EverMemOS 30B LongMemEval CSV covers 474/500 questions and the submitted Mem0 4B CSV covers 485/500; no missing rows are imputed.",
            "The 59,664 public-judge labels are recomputed from frozen labels, not independently regraded; the recorded API key is absent.",
            "The revision package does not distribute the external benchmark datasets or every construction/retrieval store required for an end-to-end rerun.",
            "The ten write-rate coordinates mix per-instance and benchmark-harness scopes; the release explicitly says they are not sustained multi-instance serving throughput.",
            "Direct dependencies are pinned in requirements.txt, but there is no transitive lockfile for a byte-identical runtime reconstruction.",
        ],
    }
    semantic = dict(report)
    report["report_sha256"] = sha256_bytes(canonical(semantic))
    return report, projection


def write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o644)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    report, projection = audit_memforest_published_artifacts(arguments.source_root.resolve())
    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_once(
        output / "report.json", json.dumps(report, indent=2, sort_keys=True).encode() + b"\n"
    )
    write_once(
        output / "projection.json",
        json.dumps(projection, indent=2, sort_keys=True).encode() + b"\n",
    )
    print(json.dumps({"status": STATUS, "report_sha256": report["report_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
