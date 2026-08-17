"""Frozen actor seams for deterministic and imported-model memory studies."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from harness.memory_trials.schema import (
    MemoryOracle,
    MemoryRecord,
    MemoryStratum,
    MemoryTask,
    canonical_json,
)

MEMORY_ACTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "mode": {"type": "string", "enum": ["answer", "tool"]},
        "answer": {"type": ["string", "null"]},
        "tool_name": {"type": ["string", "null"]},
        "tool_arguments": {
            "type": "object",
            "additionalProperties": True,
        },
        "selected_record_id": {"type": ["string", "null"]},
    },
    "required": [
        "mode",
        "answer",
        "tool_name",
        "tool_arguments",
        "selected_record_id",
    ],
    "additionalProperties": False,
}


class ModelAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: str
    answer: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, JsonValue] = Field(default_factory=dict)
    selected_record_id: str | None = None


class ActorOutput(BaseModel):
    """Parsed action plus the exact text emitted by the actor."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: ModelAction
    raw_output: str
    receipt: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class CompletionResult(BaseModel):
    """Text and non-secret scalar provenance returned by a completion backend."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    receipt: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class FrozenMemoryActor(Protocol):
    identity: str
    contract: Mapping[str, Any]

    def act(
        self,
        *,
        prompt: str,
        task: MemoryTask,
        visible_records: tuple[MemoryRecord, ...],
    ) -> ActorOutput: ...


class DeterministicMemoryActor:
    """Rule-based actor used to prove memory event and replay semantics."""

    identity = "deterministic-memory-actor-v1"
    contract = {
        "schema_version": 1,
        "identity": identity,
        "backend": "deterministic-rule-actor",
        "implementation": "harness.memory_trials.models.DeterministicMemoryActor",
    }

    def act(
        self,
        *,
        prompt: str,
        task: MemoryTask,
        visible_records: tuple[MemoryRecord, ...],
    ) -> ActorOutput:
        del prompt
        query_entity = task.events[-1].entity_id.removeprefix("permuted-")
        if task.stratum is MemoryStratum.TEMPORAL_GRAPH:
            first_hops = [
                record
                for record in visible_records
                if record.valid and record.entity_id == query_entity and record.key == "reports_to"
            ]
            first = (
                max(first_hops, key=lambda record: (record.written_step, record.record_id))
                if first_hops
                else None
            )
            second_hops = [
                record
                for record in visible_records
                if first is not None
                and record.valid
                and record.entity_id == first.value
                and record.key == "located_in"
            ]
            second = (
                max(second_hops, key=lambda record: (record.written_step, record.record_id))
                if second_hops
                else None
            )
            action = ModelAction(
                mode="answer",
                answer=second.value if second is not None else "UNKNOWN",
                selected_record_id=(
                    f"{first.record_id}+{second.record_id}"
                    if first is not None and second is not None
                    else None
                ),
            )
            return ActorOutput(action=action, raw_output=action.model_dump_json())
        matching = [
            record
            for record in visible_records
            if record.valid
            and record.entity_id == query_entity
            and record.key == task.oracle.lookup_key
        ]
        if not matching:
            selected = None
            value = "UNKNOWN"
        else:
            selected = max(matching, key=lambda record: (record.written_step, record.record_id))
            value = selected.value
        if task.oracle.mode == "tool":
            tool_arguments = _replace_expected_value(
                task.oracle.tool_arguments or {},
                expected=task.oracle.expected_value,
                replacement=value,
            )
            action = ModelAction(
                mode="tool",
                tool_name=task.oracle.tool_name,
                tool_arguments=tool_arguments,
                selected_record_id=selected.record_id if selected else None,
            )
            return ActorOutput(action=action, raw_output=action.model_dump_json())
        action = ModelAction(
            mode="answer",
            answer=value,
            selected_record_id=selected.record_id if selected else None,
        )
        return ActorOutput(action=action, raw_output=action.model_dump_json())


def _first_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("model output contains no JSON object")


def _replace_expected_value(
    value: JsonValue,
    *,
    expected: str,
    replacement: str,
) -> JsonValue:
    if isinstance(value, dict):
        return {
            key: _replace_expected_value(
                item,
                expected=expected,
                replacement=replacement,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_expected_value(
                item,
                expected=expected,
                replacement=replacement,
            )
            for item in value
        ]
    return replacement if value == expected else value


def memory_action_json_schema(oracle: MemoryOracle | None = None) -> dict[str, Any]:
    """Return the strict action envelope, optionally with task-owned tool arguments."""

    schema = json.loads(json.dumps(MEMORY_ACTION_JSON_SCHEMA))
    if oracle is not None and oracle.mode == "tool":
        schema["properties"]["tool_arguments"] = oracle.tool_input_schema
    return schema


class JsonCompletionMemoryActor:
    """Adapt a text completion function to the strict memory action schema."""

    def __init__(
        self,
        *,
        identity: str,
        complete: Callable[[str], str | CompletionResult],
        contract: Mapping[str, Any],
    ) -> None:
        if not identity.strip():
            raise ValueError("actor identity cannot be empty")
        self.identity = identity
        if not isinstance(contract, Mapping) or contract.get("identity") != identity:
            raise ValueError("actor contract must be a mapping bound to actor identity")
        self.contract = json.loads(canonical_json(dict(contract)))
        self._complete = complete

    def complete_text(self, prompt: str) -> CompletionResult:
        """Return one raw completion with the actor's registered receipt.

        Memory studies normally consume :meth:`act`, which validates the shared
        action envelope.  Retrieval-only answer screens still need the exact
        same pinned model transport without manufacturing a ``MemoryTask``.
        This narrow method exposes that transport while preserving its receipt.
        """

        completed = self._complete(prompt)
        if isinstance(completed, CompletionResult):
            return completed
        if isinstance(completed, str):
            return CompletionResult(text=completed)
        raise TypeError("completion backend must return text or CompletionResult")

    def act(
        self,
        *,
        prompt: str,
        task: MemoryTask,
        visible_records: tuple[MemoryRecord, ...],
    ) -> ActorOutput:
        del task, visible_records
        completed = self.complete_text(prompt)
        raw_output = completed.text
        receipt = completed.receipt
        try:
            payload = _first_json_object(raw_output)
            action = ModelAction.model_validate(payload)
        except (TypeError, ValueError):
            action = ModelAction(mode="invalid")
        return ActorOutput(action=action, raw_output=raw_output, receipt=receipt)


class TransformersMemoryActor(JsonCompletionMemoryActor):
    """Load a pinned local Hugging Face snapshot without executing remote code."""

    @classmethod
    def from_snapshot(
        cls,
        *,
        snapshot: Path,
        model_id: str,
        revision: str,
        artifact_root_sha256: str,
        max_new_tokens: int = 64,
        dtype: str = "bfloat16",
        device_map: str | None = "auto",
        use_chat_template: bool = False,
        deterministic: bool = True,
        attention_implementation: str = "eager",
    ) -> TransformersMemoryActor:
        if not snapshot.is_dir():
            raise ValueError(f"model snapshot does not exist: {snapshot}")
        invalid_revision = len(revision) != 40 or any(
            character not in "0123456789abcdef" for character in revision
        )
        if invalid_revision:
            raise ValueError("revision must be a lowercase 40-character commit")
        if len(artifact_root_sha256) != 64:
            raise ValueError("artifact root must be a SHA-256 digest")
        if max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        if deterministic:
            workspace = os.environ.setdefault(
                "CUBLAS_WORKSPACE_CONFIG",
                ":4096:8",
            )
            if workspace != ":4096:8":
                raise ValueError(
                    "strict deterministic inference requires CUBLAS_WORKSPACE_CONFIG=:4096:8"
                )

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as error:  # pragma: no cover - exercised by the cluster smoke
            raise RuntimeError(
                "TransformersMemoryActor requires the `architecture` dependency extra"
            ) from error

        torch_dtype = getattr(torch, dtype, None)
        if torch_dtype is None:
            raise ValueError(f"unsupported torch dtype: {dtype}")
        if deterministic:
            torch.use_deterministic_algorithms(True)
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.allow_tf32 = False
            torch.backends.cuda.matmul.allow_tf32 = False
            if hasattr(torch.backends.cuda.matmul, "allow_bf16_reduced_precision_reduction"):
                torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = False
            if hasattr(torch.backends.cuda.matmul, "allow_fp16_reduced_precision_reduction"):
                torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
        tokenizer = AutoTokenizer.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
        )
        model = AutoModelForCausalLM.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
            dtype=torch_dtype,
            device_map=device_map,
            attn_implementation=attention_implementation,
        )
        model.eval()
        resolved_device_map = getattr(model, "hf_device_map", None)
        resolved_device_map_sha256 = hashlib.sha256(
            json.dumps(
                resolved_device_map,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode()
        ).hexdigest()

        def complete(prompt: str) -> CompletionResult:
            if use_chat_template:
                encoded = tokenizer.apply_chat_template(
                    [{"role": "user", "content": prompt}],
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                    enable_thinking=False,
                )
            else:
                encoded = tokenizer(prompt, return_tensors="pt")
            model_device = getattr(model, "device", None)
            if model_device is not None:
                encoded = {name: tensor.to(model_device) for name, tensor in encoded.items()}
            prompt_tokens = int(encoded["input_ids"].shape[-1])
            pad_token_id = tokenizer.pad_token_id
            if pad_token_id is None:
                pad_token_id = tokenizer.eos_token_id
            with torch.inference_mode():
                generated = model.generate(
                    **encoded,
                    do_sample=False,
                    max_new_tokens=max_new_tokens,
                    pad_token_id=pad_token_id,
                )
            output_tokens = int(generated.shape[-1]) - prompt_tokens
            prompt_token_ids = encoded["input_ids"][0].detach().cpu().tolist()
            completion_token_ids = generated[0, prompt_tokens:].detach().cpu().tolist()
            text = tokenizer.decode(
                generated[0, prompt_tokens:],
                skip_special_tokens=True,
            )
            return CompletionResult(
                text=text,
                receipt={
                    "backend": "huggingface-transformers",
                    "model_id": model_id,
                    "revision": revision,
                    "artifact_root_sha256": artifact_root_sha256,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": output_tokens,
                    "do_sample": False,
                    "deterministic_algorithms": deterministic,
                    "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
                    "attention_implementation": attention_implementation,
                    "device_map_request": str(device_map),
                    "resolved_device_map_sha256": resolved_device_map_sha256,
                    "torch_version": torch.__version__,
                    "cuda_version": torch.version.cuda,
                    "tf32": False if deterministic else None,
                    "prompt_token_ids_sha256": hashlib.sha256(
                        json.dumps(prompt_token_ids, separators=(",", ":")).encode()
                    ).hexdigest(),
                    "completion_token_ids_sha256": hashlib.sha256(
                        json.dumps(
                            completion_token_ids,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest(),
                    "prompt_format": (
                        "tokenizer_chat_template" if use_chat_template else "base_completion"
                    ),
                },
            )

        identity = f"hf:{model_id}@{revision}#{artifact_root_sha256}"
        contract = {
            "schema_version": 1,
            "identity": identity,
            "backend": "huggingface-transformers",
            "model_id": model_id,
            "revision": revision,
            "artifact_root_sha256": artifact_root_sha256,
            "max_new_tokens": max_new_tokens,
            "dtype": dtype,
            "device_map_request": str(device_map),
            "resolved_device_map_sha256": resolved_device_map_sha256,
            "use_chat_template": use_chat_template,
            "do_sample": False,
            "deterministic_algorithms": deterministic,
            "attention_implementation": attention_implementation,
            "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            "tf32": False if deterministic else None,
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
        }
        return cls(identity=identity, complete=complete, contract=contract)


def action_success(action: ModelAction, oracle: MemoryOracle) -> bool:
    if oracle.mode == "tool":
        return (
            action.mode == "tool"
            and action.tool_name == oracle.tool_name
            and canonical_json(action.tool_arguments) == canonical_json(oracle.tool_arguments)
        )
    return action.mode == "answer" and action.answer == oracle.expected_value
