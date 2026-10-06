#!/usr/bin/env python3
"""Run the frozen GAAMA graph-vs-flat answer screen on a pinned H100 model."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import signal
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.gaama_actor import (  # noqa: E402
    AA_QUESTIONS,
    FrozenGaamaInput,
    analyze_rows,
    answer_scores,
    build_node_map,
    canonical_bytes,
    compile_panel,
    expected_case_keys,
    load_frozen_input,
    render_prompt,
    sha256_bytes,
)
from harness.memory_trials.models import (  # noqa: E402
    JsonCompletionMemoryActor,
    TransformersMemoryActor,
)
from scripts.fetch_open_model import (  # noqa: E402
    DEFAULT_MODEL_ROOT,
    DEFAULT_RECEIPT_ROOT,
    DEFAULT_REGISTRY,
    load_registry,
    verify_receipt,
)
from scripts.validate_gaama_actor_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)

CHECKPOINT_SCHEMA_VERSION = 1


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def _write_once(path: Path, value: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(value)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _load_json(path: Path, owner: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{owner} must be a regular non-symlink file")

    def reject(value: str) -> None:
        raise ValueError(f"{owner} contains non-finite JSON constant {value}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{owner} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{owner} must be one JSON object")
    return value


def _checkpoint_payload(
    *,
    contract: dict[str, Any],
    rows: list[dict[str, Any]],
    actor_contract: dict[str, Any] | None,
    status: str,
) -> dict[str, Any]:
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "status": status,
        "contract": contract,
        "actor_contract": actor_contract,
        "completed_cases": len(rows),
        "journal_root_sha256": (
            rows[-1]["record_sha256"] if rows else "0" * 64
        ),
    }


def _write_checkpoint(
    output_dir: Path,
    *,
    contract: dict[str, Any],
    rows: list[dict[str, Any]],
    actor_contract: dict[str, Any] | None,
    status: str = "IN_PROGRESS",
) -> None:
    _atomic_write(
        output_dir / "checkpoint.json",
        canonical_bytes(
            _checkpoint_payload(
                contract=contract,
                rows=rows,
                actor_contract=actor_contract,
                status=status,
            )
        ),
    )


def _acknowledge_checkpoint(
    output_dir: Path,
    *,
    contract: dict[str, Any],
    rows: list[dict[str, Any]],
    actor_contract: dict[str, Any] | None,
    total_cases: int,
) -> None:
    _write_checkpoint(
        output_dir,
        contract=contract,
        rows=rows,
        actor_contract=actor_contract,
    )
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    if marker:
        _atomic_write(
            Path(marker),
            canonical_bytes(
                {
                    "schema_version": 1,
                    "status": "CHECKPOINT_READY",
                    "checkpoint": "gaama-actor/checkpoint.json",
                    "completed_cases": len(rows),
                    "total_cases": total_cases,
                }
            ),
        )


def _load_progress(
    output_dir: Path,
    *,
    contract: dict[str, Any],
    expected_keys: tuple[tuple[str, str], ...],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    checkpoint_path = output_dir / "checkpoint.json"
    panel_path = output_dir / "panel.json"
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return [], None
    existing = {path.name for path in output_dir.iterdir()}
    if not existing:
        return [], None
    if "report.json" in existing or "manifest.json" in existing:
        raise ValueError("GAAMA actor output is already finalized")
    if not existing <= {"panel.json", "checkpoint.json", "predictions.jsonl"}:
        raise ValueError("GAAMA actor output contains an unrecognized partial artifact")
    if not panel_path.is_file() or not checkpoint_path.is_file():
        raise ValueError("GAAMA actor partial output lacks panel or checkpoint")
    payload = _load_json(checkpoint_path, "GAAMA actor checkpoint")
    if (
        payload.get("schema_version") != CHECKPOINT_SCHEMA_VERSION
        or payload.get("contract") != contract
        or payload.get("status") not in {"IN_PROGRESS", "COMPLETE"}
    ):
        raise ValueError("GAAMA actor checkpoint contract drifted")
    predictions_path = output_dir / "predictions.jsonl"
    rows = _read_journal(predictions_path) if predictions_path.exists() else []
    actual_keys = tuple((row.get("question_id"), row.get("arm")) for row in rows)
    if actual_keys != expected_keys[: len(actual_keys)]:
        raise ValueError("GAAMA actor checkpoint is not a contiguous plan prefix")
    if payload.get("completed_cases") != len(rows):
        raise ValueError("GAAMA actor checkpoint count drifted")
    expected_root = rows[-1]["record_sha256"] if rows else "0" * 64
    if payload.get("journal_root_sha256") != expected_root:
        raise ValueError("GAAMA actor checkpoint journal root drifted")
    if payload.get("status") == "COMPLETE" and len(rows) != len(expected_keys):
        raise ValueError("GAAMA actor complete checkpoint is truncated")
    actor_contract = payload.get("actor_contract")
    if actor_contract is not None and not isinstance(actor_contract, dict):
        raise ValueError("GAAMA actor runtime contract is malformed")
    return [dict(row) for row in rows], actor_contract


def _read_journal(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("GAAMA actor journal is not a regular file")
    rows: list[dict[str, Any]] = []
    previous = "0" * 64
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("GAAMA actor journal contains invalid JSON") from exc
        if not isinstance(row, dict) or row.get("previous_sha256") != previous:
            raise ValueError("GAAMA actor journal hash chain is invalid")
        record_sha256 = row.get("record_sha256")
        unhashed = {
            key: value
            for key, value in row.items()
            if key not in {"previous_sha256", "record_sha256"}
        }
        expected_record = sha256_bytes(canonical_bytes(unhashed))
        if record_sha256 != expected_record:
            raise ValueError(f"GAAMA actor journal row {line_number} digest drifted")
        previous = record_sha256
        rows.append(row)
    return rows


def _append_journal(path: Path, row: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    previous = rows[-1]["record_sha256"] if rows else "0" * 64
    stored = dict(row)
    stored["previous_sha256"] = previous
    stored["record_sha256"] = sha256_bytes(canonical_bytes(row))
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        value = (
            json.dumps(stored, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        view = memoryview(value)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError(f"short journal append: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    rows.append(stored)


def _validate_completed(
    output_dir: Path,
    *,
    contract: dict[str, Any],
    panel: dict[str, Any],
) -> dict[str, Any]:
    expected_children = {
        "checkpoint.json",
        "panel.json",
        "predictions.jsonl",
        "report.json",
        "manifest.json",
    }
    if (
        output_dir.is_symlink()
        or not output_dir.is_dir()
        or {path.name for path in output_dir.iterdir()} != expected_children
    ):
        raise ValueError("GAAMA actor finalized artifact roster drifted")
    manifest = _load_json(output_dir / "manifest.json", "GAAMA actor manifest")
    if manifest.get("schema_version") != 1 or manifest.get("status") not in {
        "GAAMA_H100_ACTOR_PASS",
        "GAAMA_H100_ACTOR_KILLED",
    }:
        raise ValueError("GAAMA actor manifest status is invalid")
    files = manifest.get("files")
    expected_names = {
        "checkpoint.json",
        "panel.json",
        "predictions.jsonl",
        "report.json",
    }
    if not isinstance(files, dict) or set(files) != expected_names:
        raise ValueError("GAAMA actor manifest file roster drifted")
    manifest_root = manifest.get("root_sha256")
    unhashed_manifest = dict(manifest)
    unhashed_manifest.pop("root_sha256", None)
    if manifest_root != sha256_bytes(canonical_bytes(unhashed_manifest)):
        raise ValueError("GAAMA actor manifest root drifted")
    for name, receipt in files.items():
        path = output_dir / name
        if (
            not isinstance(receipt, dict)
            or path.is_symlink()
            or not path.is_file()
            or receipt.get("bytes") != path.stat().st_size
            or receipt.get("sha256") != _sha_file(path)
        ):
            raise ValueError(f"GAAMA actor artifact {name} drifted")
    report = _load_json(output_dir / "report.json", "GAAMA actor report")
    if report.get("status") != manifest["status"]:
        raise ValueError("GAAMA actor report and manifest disagree")
    checkpoint = _load_json(output_dir / "checkpoint.json", "GAAMA actor checkpoint")
    if (
        checkpoint.get("schema_version") != CHECKPOINT_SCHEMA_VERSION
        or checkpoint.get("status") != "COMPLETE"
        or checkpoint.get("contract") != contract
    ):
        raise ValueError("GAAMA actor finalized checkpoint contract drifted")
    if (output_dir / "panel.json").read_bytes() != canonical_bytes(panel):
        raise ValueError("GAAMA actor finalized panel drifted")
    rows = _read_journal(output_dir / "predictions.jsonl")
    expected_keys = expected_case_keys(panel)
    actual_keys = tuple((row.get("question_id"), row.get("arm")) for row in rows)
    if actual_keys != expected_keys:
        raise ValueError("GAAMA actor finalized journal does not cover the frozen plan")
    expected_root = rows[-1]["record_sha256"] if rows else "0" * 64
    if (
        checkpoint.get("completed_cases") != len(rows)
        or checkpoint.get("journal_root_sha256") != expected_root
        or checkpoint.get("actor_contract") != report.get("actor_contract")
    ):
        raise ValueError("GAAMA actor finalized checkpoint state drifted")
    recomputed = analyze_rows(rows, panel=panel)
    expected_report_keys = set(recomputed) | {
        "experiment_sha256",
        "evidence_sha256",
        "actor_identity",
        "actor_contract",
        "predictions_sha256",
        "completed_cases",
        "total_cases",
    }
    if set(report) != expected_report_keys:
        raise ValueError("GAAMA actor report schema drifted")
    if any(report.get(key) != value for key, value in recomputed.items()):
        raise ValueError("GAAMA actor report analysis does not reproduce")
    if (
        report.get("experiment_sha256") != contract["experiment_sha256"]
        or report.get("evidence_sha256") != contract["evidence_sha256"]
        or report.get("predictions_sha256")
        != _sha_file(output_dir / "predictions.jsonl")
        or report.get("completed_cases") != len(rows)
        or report.get("total_cases") != len(expected_keys)
    ):
        raise ValueError("GAAMA actor report provenance drifted")
    return report


def _materialize_dataset(frozen: FrozenGaamaInput, directory: Path) -> Path:
    path = directory / "locomo10.json"
    path.write_bytes(frozen.dataset_bytes)
    return path


def _make_actor(
    *,
    config: dict[str, Any],
    registry_path: Path,
    model_root: Path,
    receipt_root: Path,
) -> JsonCompletionMemoryActor:
    model_contract = config["model"]
    model_id = model_contract["model_id"]
    registry = load_registry(registry_path)
    entry = registry["models"].get(model_id)
    if (
        not isinstance(entry, dict)
        or entry.get("revision") != model_contract["revision"]
        or entry.get("trust_remote_code") is not False
        or entry.get("publication_eligible") is not True
    ):
        raise ValueError("GAAMA actor model registry identity drifted")
    receipt = verify_receipt(model_id, entry, model_root, receipt_root)
    if (
        receipt.get("mode") != "full"
        or receipt.get("artifact_root_sha256")
        != model_contract["artifact_root_sha256"]
    ):
        raise ValueError("GAAMA actor model receipt drifted")
    return TransformersMemoryActor.from_snapshot(
        snapshot=model_root / model_id,
        model_id=model_id,
        revision=model_contract["revision"],
        artifact_root_sha256=model_contract["artifact_root_sha256"],
        max_new_tokens=model_contract["max_new_tokens"],
        dtype=model_contract["dtype"],
        use_chat_template=model_contract["use_chat_template"],
        deterministic=True,
        attention_implementation=model_contract["attention_implementation"],
    )


def run_screen(
    *,
    config_path: Path,
    evidence_path: Path,
    expected_evidence_sha256: str,
    output_dir: Path,
    registry_path: Path = DEFAULT_REGISTRY,
    model_root: Path = DEFAULT_MODEL_ROOT,
    receipt_root: Path = DEFAULT_RECEIPT_ROOT,
    actor: JsonCompletionMemoryActor | None = None,
    stop_requested: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Execute or resume the exact registered screen."""

    config = validate_experiment_contract(config_path)
    if expected_evidence_sha256 != config["input"]["evidence_sha256"]:
        raise ValueError("GAAMA actor expected evidence digest differs from the experiment")
    frozen = load_frozen_input(
        evidence_path,
        expected_sha256=expected_evidence_sha256,
    )
    panel = compile_panel(
        frozen,
        panel_size=config["panel"]["questions"],
        panel_seed=config["panel"]["seed"],
    )
    contract = {
        "schema_version": 1,
        "experiment_sha256": config["experiment_sha256"],
        "evidence_sha256": expected_evidence_sha256,
        "panel_sha256": panel["panel_sha256"],
        "model_id": config["model"]["model_id"],
        "model_revision": config["model"]["revision"],
        "model_artifact_root_sha256": config["model"]["artifact_root_sha256"],
        "deterministic": True,
        "attention_implementation": "eager",
    }
    if (output_dir / "manifest.json").exists():
        return _validate_completed(output_dir, contract=contract, panel=panel)
    expected_keys = expected_case_keys(panel)
    rows, checkpoint_actor_contract = _load_progress(
        output_dir,
        contract=contract,
        expected_keys=expected_keys,
    )
    panel_path = output_dir / "panel.json"
    panel_bytes = canonical_bytes(panel)
    if panel_path.exists():
        if panel_path.is_symlink() or panel_path.read_bytes() != panel_bytes:
            raise ValueError("GAAMA actor frozen panel drifted on resume")
    else:
        _write_once(panel_path, panel_bytes)
        _write_checkpoint(
            output_dir,
            contract=contract,
            rows=rows,
            actor_contract=checkpoint_actor_contract,
        )
    should_stop = stop_requested or (lambda: False)
    if should_stop():
        _acknowledge_checkpoint(
            output_dir,
            contract=contract,
            rows=rows,
            actor_contract=checkpoint_actor_contract,
            total_cases=len(expected_keys),
        )
        return {
            "schema_version": 1,
            "status": "CHECKPOINTED",
            "completed_cases": len(rows),
            "total_cases": len(expected_keys),
            "scientific_result": False,
        }

    runtime_actor = actor or _make_actor(
        config=config,
        registry_path=registry_path,
        model_root=model_root,
        receipt_root=receipt_root,
    )
    actor_contract = json.loads(json.dumps(dict(runtime_actor.contract), sort_keys=True))
    if checkpoint_actor_contract is not None and checkpoint_actor_contract != actor_contract:
        raise ValueError("GAAMA actor runtime contract drifted across resume")

    completed = len(rows)
    item_by_id = {item["question_id"]: item for item in panel["items"]}
    aa_question_ids = {
        item["question_id"] for item in panel["items"][:AA_QUESTIONS]
    }
    with tempfile.TemporaryDirectory(prefix="cotcodec-gaama-actor-") as temporary:
        dataset_path = _materialize_dataset(frozen, Path(temporary))
        nodes = build_node_map(frozen, dataset_path)
        for question_id, arm in expected_keys[completed:]:
            item = item_by_id[question_id]
            prompt = render_prompt(item, arm=arm, nodes=nodes)
            started = time.perf_counter()
            completion = runtime_actor.complete_text(prompt)
            latency_seconds = time.perf_counter() - started
            receipt = completion.receipt
            required_receipt = {
                "model_id": config["model"]["model_id"],
                "revision": config["model"]["revision"],
                "artifact_root_sha256": config["model"]["artifact_root_sha256"],
                "do_sample": False,
                "deterministic_algorithms": True,
                "attention_implementation": "eager",
            }
            if any(receipt.get(key) != value for key, value in required_receipt.items()):
                raise ValueError("GAAMA actor completion receipt drifted")
            if not all(
                isinstance(receipt.get(field), int)
                and not isinstance(receipt.get(field), bool)
                and int(receipt[field]) >= 0
                for field in ("prompt_tokens", "completion_tokens")
            ):
                raise ValueError("GAAMA actor token receipt is malformed")
            exact, token_f1 = answer_scores(completion.text, item["answer"])
            evidence = set(item["evidence_ids"])
            ranking = item["rankings"][arm]
            row: dict[str, Any] = {
                "question_id": question_id,
                "sample_id": item["sample_id"],
                "category": item["category"],
                "arm": arm,
                "prompt_sha256": sha256_bytes(prompt.encode()),
                "prediction": completion.text,
                "prediction_sha256": sha256_bytes(completion.text.encode()),
                "answer": item["answer"],
                "exact_match": exact,
                "token_f1": token_f1,
                "evidence_recall_all_at_10": float(evidence <= set(ranking)),
                "latency_seconds": latency_seconds,
                "receipt": receipt,
                "aa_checked": False,
                "aa_text_exact": None,
            }
            if arm == "flat" and question_id in aa_question_ids:
                repeated = runtime_actor.complete_text(prompt)
                row["aa_checked"] = True
                row["aa_text_exact"] = (
                    repeated.text == completion.text
                    and repeated.receipt.get("prompt_token_ids_sha256")
                    == receipt.get("prompt_token_ids_sha256")
                    and repeated.receipt.get("completion_token_ids_sha256")
                    == receipt.get("completion_token_ids_sha256")
                )
                row["aa_repeat_prediction_sha256"] = sha256_bytes(repeated.text.encode())
                row["aa_repeat_receipt"] = repeated.receipt
            _append_journal(output_dir / "predictions.jsonl", row, rows)
            _write_checkpoint(
                output_dir,
                contract=contract,
                rows=rows,
                actor_contract=actor_contract,
            )
            if should_stop():
                _acknowledge_checkpoint(
                    output_dir,
                    contract=contract,
                    rows=rows,
                    actor_contract=actor_contract,
                    total_cases=len(expected_keys),
                )
                return {
                    "schema_version": 1,
                    "status": "CHECKPOINTED",
                    "completed_cases": len(rows),
                    "total_cases": len(expected_keys),
                    "scientific_result": False,
                }

    analysis = analyze_rows(rows, panel=panel)
    predictions_bytes = (output_dir / "predictions.jsonl").read_bytes()
    report = {
        **analysis,
        "experiment_sha256": config["experiment_sha256"],
        "evidence_sha256": expected_evidence_sha256,
        "actor_identity": runtime_actor.identity,
        "actor_contract": actor_contract,
        "predictions_sha256": sha256_bytes(predictions_bytes),
        "completed_cases": len(rows),
        "total_cases": len(expected_keys),
    }
    _write_checkpoint(
        output_dir,
        contract=contract,
        rows=rows,
        actor_contract=actor_contract,
        status="COMPLETE",
    )
    _write_once(output_dir / "report.json", canonical_bytes(report))
    file_names = (
        "checkpoint.json",
        "panel.json",
        "predictions.jsonl",
        "report.json",
    )
    manifest = {
        "schema_version": 1,
        "status": report["status"],
        "scientific_result": False,
        "publication_ready": False,
        "discovery_only": True,
        "files": {
            name: {
                "bytes": (output_dir / name).stat().st_size,
                "sha256": _sha_file(output_dir / name),
            }
            for name in file_names
        },
    }
    manifest["root_sha256"] = sha256_bytes(canonical_bytes(manifest))
    _write_once(output_dir / "manifest.json", canonical_bytes(manifest))
    return _validate_completed(output_dir, contract=contract, panel=panel)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--expected-evidence-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    stop = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGUSR1, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    report = run_screen(
        config_path=args.config,
        evidence_path=args.evidence,
        expected_evidence_sha256=args.expected_evidence_sha256,
        output_dir=args.output_dir,
        registry_path=args.registry,
        model_root=args.model_root,
        receipt_root=args.receipt_root,
        stop_requested=lambda: stop,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_gates and report["status"] == "GAAMA_H100_ACTOR_KILLED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
