"""Strict TRAIN-only procedure-induction artifacts.

This module does not call a model.  It validates two immutable JSONL streams:
source trajectories with executable correctness receipts, and deterministic
procedure-generation receipts.  Only a complete registered TRAIN roster may be
compiled into inputs for the frozen procedural bank.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.memory_trials.procedural_bank import (
    REASONINGBANK_ARCHIVE_SHA256,
    REASONINGBANK_REPOSITORY,
    REASONINGBANK_REVISION,
    ProceduralBankItemInput,
    ProceduralOutcome,
    ProceduralSplitManifest,
)
from harness.memory_trials.schema import canonical_json, sha256_text

_MAX_JSONL_BYTES = 64 * 1024 * 1024
_MAX_JSONL_LINE_BYTES = 2 * 1024 * 1024
_MAX_JSONL_ROWS = 100_000

TrajectoryEventKind = Literal[
    "observation",
    "reasoning_summary",
    "action",
    "tool_result",
    "final_response",
]


class TrajectoryEvent(BaseModel):
    """One framework-visible event retained from a training trajectory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int = Field(ge=0)
    kind: TrajectoryEventKind
    content: str = Field(min_length=1)


class CorrectnessDecision(BaseModel):
    """Executable or sealed evaluator decision for one trajectory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: ProceduralOutcome
    score: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    details: str = Field(min_length=1)


class CorrectnessReceipt(BaseModel):
    """Content-addressed decision binding one task to one trajectory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["procedural-correctness-receipt-v1"] = (
        "procedural-correctness-receipt-v1"
    )
    task_id: str = Field(min_length=1)
    trajectory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluator_id: str = Field(min_length=1)
    evaluator_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluator_input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: CorrectnessDecision
    evaluator_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_receipt(self) -> CorrectnessReceipt:
        expected_input = sha256_text(
            canonical_json(
                {
                    "task_id": self.task_id,
                    "trajectory_sha256": self.trajectory_sha256,
                }
            )
        )
        if self.evaluator_input_sha256 != expected_input:
            raise ValueError("correctness evaluator input digest drifted")
        expected_output = sha256_text(canonical_json(self.decision.model_dump(mode="json")))
        if self.evaluator_output_sha256 != expected_output:
            raise ValueError("correctness evaluator output digest drifted")
        unsigned = self.model_dump(mode="json", exclude={"receipt_sha256"})
        if self.receipt_sha256 != sha256_text(canonical_json(unsigned)):
            raise ValueError("correctness receipt digest drifted")
        return self


class TrainTrajectoryRecord(BaseModel):
    """One canonical TRAIN trajectory with no evaluation-split fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["procedural-train-trajectory-v1"] = (
        "procedural-train-trajectory-v1"
    )
    split: Literal["train"] = "train"
    source_dataset_id: str = Field(min_length=1)
    source_dataset_revision: str = Field(min_length=1)
    source_dataset_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(min_length=1)
    workflow_family_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    events: tuple[TrajectoryEvent, ...] = Field(min_length=1)
    outcome: ProceduralOutcome
    trajectory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    correctness_receipt: CorrectnessReceipt
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_record(self) -> TrainTrajectoryRecord:
        if tuple(event.sequence for event in self.events) != tuple(
            range(len(self.events))
        ):
            raise ValueError("trajectory event sequence must be contiguous from zero")
        trajectory_payload = self.model_dump(
            mode="json",
            exclude={"trajectory_sha256", "correctness_receipt", "record_sha256"},
        )
        if self.trajectory_sha256 != sha256_text(canonical_json(trajectory_payload)):
            raise ValueError("trajectory digest drifted")
        correctness = self.correctness_receipt
        if (
            correctness.task_id != self.task_id
            or correctness.trajectory_sha256 != self.trajectory_sha256
            or correctness.decision.outcome != self.outcome
        ):
            raise ValueError("correctness receipt does not bind the trajectory")
        unsigned = self.model_dump(mode="json", exclude={"record_sha256"})
        if self.record_sha256 != sha256_text(canonical_json(unsigned)):
            raise ValueError("trajectory record digest drifted")
        return self


class DeterministicGenerationConfig(BaseModel):
    """Decoding settings required for the induction admission cell."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    do_sample: Literal[False] = False
    temperature: Literal[0.0] = 0.0
    top_p: Literal[1.0] = 1.0
    seed: int = Field(ge=0)
    max_new_tokens: int = Field(ge=1, le=4096)


class ProcedureGenerationResponse(BaseModel):
    """Strict model response; one trajectory may yield up to three procedures."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    procedural_items: tuple[str, ...] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_items(self) -> ProcedureGenerationResponse:
        if any(item != item.strip() or not item for item in self.procedural_items):
            raise ValueError("procedural items must be nonempty trimmed strings")
        if len(set(self.procedural_items)) != len(self.procedural_items):
            raise ValueError("procedural items must be unique within a response")
        return self


class ProcedureGenerationReceipt(BaseModel):
    """Two-pass deterministic generation receipt for one TRAIN trajectory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["procedural-generation-receipt-v1"] = (
        "procedural-generation-receipt-v1"
    )
    task_id: str = Field(min_length=1)
    trajectory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_template_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_model_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_kind: Literal["contained-pinned-local-model"] = (
        "contained-pinned-local-model"
    )
    decoding: DeterministicGenerationConfig
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response: ProcedureGenerationResponse
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    repeat_response: ProcedureGenerationResponse
    repeat_response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_attempts: Literal[2] = 2
    api_calls: Literal[0] = 0
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    repeat_output_tokens: int = Field(ge=0)
    receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_receipt(self) -> ProcedureGenerationReceipt:
        request_payload = {
            "task_id": self.task_id,
            "trajectory_sha256": self.trajectory_sha256,
            "prompt_template_sha256": self.prompt_template_sha256,
            "generator_model_receipt_sha256": self.generator_model_receipt_sha256,
            "generator_code_sha256": self.generator_code_sha256,
            "execution_kind": self.execution_kind,
            "decoding": self.decoding.model_dump(mode="json"),
        }
        if self.request_sha256 != sha256_text(canonical_json(request_payload)):
            raise ValueError("procedure-generation request digest drifted")
        expected_response = sha256_text(
            canonical_json(self.response.model_dump(mode="json"))
        )
        expected_repeat = sha256_text(
            canonical_json(self.repeat_response.model_dump(mode="json"))
        )
        if self.response_sha256 != expected_response or (
            self.repeat_response_sha256 != expected_repeat
            or self.repeat_response != self.response
        ):
            raise ValueError("deterministic procedure-generation replay drifted")
        if self.output_tokens != self.repeat_output_tokens:
            raise ValueError("deterministic procedure-generation token count drifted")
        unsigned = self.model_dump(mode="json", exclude={"receipt_sha256"})
        if self.receipt_sha256 != sha256_text(canonical_json(unsigned)):
            raise ValueError("procedure-generation receipt digest drifted")
        return self


class ProceduralInductionArtifact(BaseModel):
    """Immutable join of an exact TRAIN trajectory and generation roster."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["procedural-induction-artifact-v1"] = (
        "procedural-induction-artifact-v1"
    )
    source_repository: Literal[
        "https://github.com/google-research/reasoning-bank"
    ] = REASONINGBANK_REPOSITORY
    source_revision: Literal[
        "ed80611788292ea739f1effd31f16c53823b8a0d"
    ] = REASONINGBANK_REVISION
    source_archive_sha256: Literal[
        "d85d169c84f82782cefc50044adc192ab1d28956f36e177de0bf213d48298e09"
    ] = REASONINGBANK_ARCHIVE_SHA256
    split_manifest: ProceduralSplitManifest
    source_dataset_id: str = Field(min_length=1)
    source_dataset_revision: str = Field(min_length=1)
    source_dataset_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    correctness_evaluator_id: str = Field(min_length=1)
    correctness_evaluator_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_template_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_model_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_decoding: DeterministicGenerationConfig
    trajectory_jsonl_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_jsonl_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    train_task_ids: tuple[str, ...] = Field(min_length=1)
    trajectory_count: int = Field(ge=1)
    generation_count: int = Field(ge=1)
    procedure_count: int = Field(ge=1)
    items: tuple[ProceduralBankItemInput, ...] = Field(min_length=1)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_artifact(self) -> ProceduralInductionArtifact:
        registered = {
            row.task_id: row.workflow_family_id for row in self.split_manifest.train
        }
        if self.train_task_ids != tuple(sorted(registered)):
            raise ValueError("induction TRAIN task roster differs from split manifest")
        if self.trajectory_count != len(registered):
            raise ValueError("induction trajectory count drifted")
        if self.generation_count != len(registered):
            raise ValueError("induction generation count drifted")
        if self.procedure_count != len(self.items):
            raise ValueError("induction procedure count drifted")
        if tuple(
            sorted(
                self.items,
                key=lambda item: (
                    item.source_task_id,
                    item.procedural_text,
                    item.generator_receipt_sha256,
                ),
            )
        ) != self.items:
            raise ValueError("induced procedural items are not canonically sorted")
        if any(
            registered.get(item.source_task_id) != item.source_family_id
            for item in self.items
        ):
            raise ValueError("induced item lineage escapes the TRAIN manifest")
        unsigned = self.model_dump(mode="json", exclude={"artifact_sha256"})
        if self.artifact_sha256 != sha256_text(canonical_json(unsigned)):
            raise ValueError("procedural induction artifact digest drifted")
        return self


ModelT = TypeVar("ModelT", bound=BaseModel)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_regular_file(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"cannot open JSONL input: {path}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"JSONL input is not a regular file: {path}")
        if metadata.st_size <= 0 or metadata.st_size > _MAX_JSONL_BYTES:
            raise ValueError(f"JSONL input size is outside the registered bounds: {path}")
        chunks: list[bytes] = []
        remaining = metadata.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError(f"JSONL input changed while being read: {path}")
            chunks.append(chunk)
            remaining -= len(chunk)
        final_metadata = os.fstat(descriptor)
        stable_fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns")
        if any(
            getattr(final_metadata, field) != getattr(metadata, field)
            for field in stable_fields
        ):
            raise ValueError(f"JSONL input metadata changed while being read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def load_canonical_jsonl(path: Path, model: type[ModelT]) -> tuple[tuple[ModelT, ...], str]:
    """Read a canonical, bounded, duplicate-key-free JSONL artifact once."""

    encoded = _read_regular_file(path)
    if not encoded.endswith(b"\n") or b"\r" in encoded or b"\x00" in encoded:
        raise ValueError("canonical JSONL must end in LF and contain no CR or NUL")
    raw_lines = encoded.splitlines()
    if not raw_lines or len(raw_lines) > _MAX_JSONL_ROWS:
        raise ValueError("canonical JSONL row count is outside the registered bounds")
    rows: list[ModelT] = []
    for line_number, raw_line in enumerate(raw_lines, start=1):
        if not raw_line or len(raw_line) > _MAX_JSONL_LINE_BYTES:
            raise ValueError(f"line {line_number}: invalid canonical JSONL line size")
        try:
            text = raw_line.decode("utf-8")
            payload = json.loads(
                text,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"invalid JSON constant: {value}")
                ),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"line {line_number}: record must be an object")
        if text != canonical_json(payload):
            raise ValueError(f"line {line_number}: record is not canonical JSON")
        try:
            rows.append(model.model_validate(payload))
        except ValueError as exc:
            raise ValueError(f"line {line_number}: record failed validation") from exc
    return tuple(rows), hashlib.sha256(encoded).hexdigest()


def compile_procedural_induction(
    *,
    trajectory_jsonl: Path,
    generation_jsonl: Path,
    split_manifest: ProceduralSplitManifest,
    expected_split_manifest_sha256: str,
) -> ProceduralInductionArtifact:
    """Compile one row per task in an externally registered TRAIN split."""

    if not re.fullmatch(r"[0-9a-f]{64}", expected_split_manifest_sha256):
        raise ValueError("expected split-manifest digest must be lowercase SHA-256")
    if split_manifest.manifest_sha256 != expected_split_manifest_sha256:
        raise ValueError("split manifest differs from the externally registered digest")

    trajectories, trajectory_sha = load_canonical_jsonl(
        trajectory_jsonl, TrainTrajectoryRecord
    )
    generations, generation_sha = load_canonical_jsonl(
        generation_jsonl, ProcedureGenerationReceipt
    )
    trajectory_by_task = {row.task_id: row for row in trajectories}
    generation_by_task = {row.task_id: row for row in generations}
    if len(trajectory_by_task) != len(trajectories):
        raise ValueError("trajectory JSONL contains duplicate task IDs")
    if len(generation_by_task) != len(generations):
        raise ValueError("generation JSONL contains duplicate task IDs")
    registered = {
        row.task_id: row.workflow_family_id for row in split_manifest.train
    }
    if set(trajectory_by_task) != set(registered):
        raise ValueError("trajectory JSONL must cover the exact TRAIN task roster")
    if set(generation_by_task) != set(registered):
        raise ValueError("generation JSONL must cover the exact TRAIN task roster")

    source_contracts = {
        (
            row.source_dataset_id,
            row.source_dataset_revision,
            row.source_dataset_receipt_sha256,
        )
        for row in trajectories
    }
    evaluator_contracts = {
        (
            row.correctness_receipt.evaluator_id,
            row.correctness_receipt.evaluator_revision_sha256,
        )
        for row in trajectories
    }
    generator_contracts = {
        (
            row.prompt_template_sha256,
            row.generator_model_receipt_sha256,
            row.generator_code_sha256,
            canonical_json(row.decoding.model_dump(mode="json")),
        )
        for row in generations
    }
    if len(source_contracts) != 1:
        raise ValueError("trajectory JSONL mixes source dataset contracts")
    if len(evaluator_contracts) != 1:
        raise ValueError("trajectory JSONL mixes correctness evaluator contracts")
    if len(generator_contracts) != 1:
        raise ValueError("generation JSONL mixes generator contracts")
    source_dataset_id, source_dataset_revision, source_dataset_receipt = next(
        iter(source_contracts)
    )
    evaluator_id, evaluator_revision = next(iter(evaluator_contracts))
    prompt_sha, generator_model_receipt, generator_code_sha, decoding_json = next(
        iter(generator_contracts)
    )

    items: list[ProceduralBankItemInput] = []
    for task_id in sorted(registered):
        trajectory = trajectory_by_task[task_id]
        generation = generation_by_task[task_id]
        if trajectory.workflow_family_id != registered[task_id]:
            raise ValueError("trajectory workflow family differs from TRAIN manifest")
        if generation.trajectory_sha256 != trajectory.trajectory_sha256:
            raise ValueError("generation receipt does not bind its trajectory")
        for procedural_text in generation.response.procedural_items:
            items.append(
                ProceduralBankItemInput(
                    source_task_id=task_id,
                    source_family_id=trajectory.workflow_family_id,
                    source_query=trajectory.query,
                    outcome=trajectory.outcome,
                    procedural_text=procedural_text,
                    source_trajectory_sha256=trajectory.trajectory_sha256,
                    correctness_receipt_sha256=(
                        trajectory.correctness_receipt.receipt_sha256
                    ),
                    generator_receipt_sha256=generation.receipt_sha256,
                )
            )
    sorted_items = tuple(
        sorted(
            items,
            key=lambda item: (
                item.source_task_id,
                item.procedural_text,
                item.generator_receipt_sha256,
            ),
        )
    )
    if len({canonical_json(item.model_dump(mode="json")) for item in sorted_items}) != len(
        sorted_items
    ):
        raise ValueError("induction produced duplicate procedural items")
    unsigned = {
        "schema_version": "procedural-induction-artifact-v1",
        "source_repository": REASONINGBANK_REPOSITORY,
        "source_revision": REASONINGBANK_REVISION,
        "source_archive_sha256": REASONINGBANK_ARCHIVE_SHA256,
        "split_manifest": split_manifest.model_dump(mode="json"),
        "source_dataset_id": source_dataset_id,
        "source_dataset_revision": source_dataset_revision,
        "source_dataset_receipt_sha256": source_dataset_receipt,
        "correctness_evaluator_id": evaluator_id,
        "correctness_evaluator_revision_sha256": evaluator_revision,
        "prompt_template_sha256": prompt_sha,
        "generator_model_receipt_sha256": generator_model_receipt,
        "generator_code_sha256": generator_code_sha,
        "generation_decoding": json.loads(decoding_json),
        "trajectory_jsonl_sha256": trajectory_sha,
        "generation_jsonl_sha256": generation_sha,
        "train_task_ids": sorted(registered),
        "trajectory_count": len(trajectories),
        "generation_count": len(generations),
        "procedure_count": len(sorted_items),
        "items": [item.model_dump(mode="json") for item in sorted_items],
    }
    return ProceduralInductionArtifact.model_validate(
        {**unsigned, "artifact_sha256": sha256_text(canonical_json(unsigned))}
    )


def canonical_jsonl(records: Sequence[BaseModel]) -> bytes:
    """Serialize model records in the only JSONL form accepted by the compiler."""

    if not records:
        raise ValueError("canonical JSONL requires at least one record")
    return (
        "".join(
            canonical_json(record.model_dump(mode="json")) + "\n" for record in records
        )
    ).encode("utf-8")
