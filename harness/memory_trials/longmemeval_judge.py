"""Content-addressed LongMemEval judge packets and score aggregation.

The official LongMemEval evaluator is an LLM judge.  This module ports only its
category-specific prompt contract and label rule from the pinned MIT repository.
It does not call a provider.  Provider transport lives in a script so packet
construction and score verification remain deterministic and CPU-only.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.causal_memory_trials import TrialOutcome
from harness.memory_trials.frozen import task_manifest_sha256
from harness.memory_trials.public_sources import (
    LONGMEMEVAL_DATASET_ID,
    LONGMEMEVAL_OFFICIAL_EVALUATOR_SHA256,
    LONGMEMEVAL_REPOSITORY_REVISION,
    LongMemEvalTaskSource,
)
from harness.memory_trials.quality import QualityCollectionError, load_quality_outcomes
from harness.memory_trials.schema import canonical_json, sha256_text

LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION = (
    "longmemeval-evaluate-qa-get-anscheck-prompt-v1"
)
LONGMEMEVAL_OFFICIAL_JUDGE_MODEL = "gpt-4o-2024-08-06"
LONGMEMEVAL_OFFICIAL_JUDGE_ENDPOINT = "/chat/completions"
_SUPPORTED_QUESTION_TYPES = frozenset(
    {
        "single-session-user",
        "single-session-assistant",
        "single-session-preference",
        "multi-session",
        "temporal-reasoning",
        "knowledge-update",
    }
)


class LongMemEvalJudgeError(ValueError):
    """Raised when a judge packet, result, or source bundle is invalid."""


class LongMemEvalJudgeContract(BaseModel):
    """Exact provider and decoding contract used by the official evaluator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    provider: Literal["openai"] = "openai"
    requested_model: Literal["gpt-4o-2024-08-06"] = (
        LONGMEMEVAL_OFFICIAL_JUDGE_MODEL
    )
    endpoint: Literal["/chat/completions"] = LONGMEMEVAL_OFFICIAL_JUDGE_ENDPOINT
    provider_api_version: Literal["v1"] = "v1"
    temperature: Literal[0] = 0
    n: Literal[1] = 1
    max_tokens: Literal[10] = 10
    sdk_package: Literal["openai"] = "openai"
    sdk_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    prompt_version: Literal[
        "longmemeval-evaluate-qa-get-anscheck-prompt-v1"
    ] = LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION
    evaluator_repository_revision: Literal[
        "9e0b455f4ef0e2ab8f2e582289761153549043fc"
    ] = LONGMEMEVAL_REPOSITORY_REVISION
    evaluator_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> LongMemEvalJudgeContract:
        if self.evaluator_source_sha256 != LONGMEMEVAL_OFFICIAL_EVALUATOR_SHA256:
            raise ValueError("judge contract changed the official evaluator source")
        payload = self.model_dump(mode="json", exclude={"contract_sha256"})
        if sha256_text(canonical_json(payload)) != self.contract_sha256:
            raise ValueError("contract_sha256 does not bind judge contract")
        return self


class LongMemEvalJudgeCase(BaseModel):
    """One immutable official-prompt evaluation case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    sequence: int = Field(ge=1)
    trial_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    question_type: str = Field(min_length=1)
    question: str = Field(min_length=1)
    reference_answer: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    abstention: bool
    visibility: Literal["serve", "holdout"]
    evaluation_mode: Literal["randomized-causal", "all-serve-system-quality"]
    assignment_seed: int | None
    source_bundle_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_task_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_world_provenance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_model_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_model_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_version: Literal[
        "longmemeval-evaluate-qa-get-anscheck-prompt-v1"
    ] = LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION
    prompt: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_hashes(self) -> LongMemEvalJudgeCase:
        if self.question_type not in _SUPPORTED_QUESTION_TYPES:
            raise ValueError("unsupported LongMemEval question type")
        if sha256_text(self.prompt) != self.prompt_sha256:
            raise ValueError("prompt_sha256 does not bind prompt")
        payload = self.model_dump(mode="json", exclude={"case_sha256"})
        if sha256_text(canonical_json(payload)) != self.case_sha256:
            raise ValueError("case_sha256 does not bind judge case")
        return self


class LongMemEvalJudgment(BaseModel):
    """One judge response bound to a case and immutable judge receipt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    sequence: int = Field(ge=1)
    case_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    judge_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    judge_model_id: Literal["gpt-4o-2024-08-06"] = (
        LONGMEMEVAL_OFFICIAL_JUDGE_MODEL
    )
    openai_sdk_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    provider_api_version: Literal["v1"] = "v1"
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_response_json: str = Field(min_length=2)
    provider_response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    judge_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_response: str = Field(min_length=1)
    raw_response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    official_label: bool
    response_well_formed: bool
    provider_response_id: str | None = None
    system_fingerprint: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    judgment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_hashes(self) -> LongMemEvalJudgment:
        if sha256_text(self.raw_response) != self.raw_response_sha256:
            raise ValueError("raw_response_sha256 does not bind raw_response")
        expected_label, expected_well_formed = parse_official_judgment(
            self.raw_response
        )
        if (self.official_label, self.response_well_formed) != (
            expected_label,
            expected_well_formed,
        ):
            raise ValueError("stored judgment does not match official label parsing")
        if sha256_text(self.provider_response_json) != self.provider_response_sha256:
            raise ValueError("provider_response_sha256 does not bind provider response")
        try:
            response = json.loads(self.provider_response_json)
            content = response["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ValueError("provider response is not an OpenAI chat completion") from exc
        if response.get("model") != self.judge_model_id or content != self.raw_response:
            raise ValueError("provider response changed model or judgment text")
        if self.provider_response_id != response.get("id"):
            raise ValueError("provider response ID does not match sealed response")
        if self.system_fingerprint != response.get("system_fingerprint"):
            raise ValueError("provider system fingerprint does not match sealed response")
        usage = response.get("usage") or {}
        if self.input_tokens != usage.get("prompt_tokens") or self.output_tokens != usage.get(
            "completion_tokens"
        ):
            raise ValueError("provider token counts do not match sealed response")
        receipt = {
            "judge_contract_sha256": self.judge_contract_sha256,
            "judge_model_id": self.judge_model_id,
            "openai_sdk_version": self.openai_sdk_version,
            "provider_api_version": self.provider_api_version,
            "request_sha256": self.request_sha256,
            "provider_response_sha256": self.provider_response_sha256,
            "provider_response_id": self.provider_response_id,
            "system_fingerprint": self.system_fingerprint,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }
        if sha256_text(canonical_json(receipt)) != self.judge_receipt_sha256:
            raise ValueError("judge_receipt_sha256 does not bind the response receipt")
        payload = self.model_dump(mode="json", exclude={"judgment_sha256"})
        if sha256_text(canonical_json(payload)) != self.judgment_sha256:
            raise ValueError("judgment_sha256 does not bind judgment")
        return self


def official_answer_check_prompt(
    question_type: str,
    question: str,
    answer: str,
    response: str,
    *,
    abstention: bool,
) -> str:
    """Port ``get_anscheck_prompt`` from the pinned official evaluator."""

    if abstention:
        template = (
            "I will give you an unanswerable question, an explanation, and a response "
            "from a model. Please answer yes if the model correctly identifies the "
            "question as unanswerable. The model could say that the information is "
            "incomplete, or some other information is given but the asked information "
            "is not.\n\nQuestion: {}\n\nExplanation: {}\n\nModel Response: "
            "{}\n\nDoes the model correctly identify the question as unanswerable? "
            "Answer yes or no only."
        )
        return template.format(question, answer, response)
    if question_type in {
        "single-session-user",
        "single-session-assistant",
        "multi-session",
    }:
        template = (
            "I will give you a question, a correct answer, and a response from a "
            "model. Please answer yes if the response contains the correct answer. "
            "Otherwise, answer no. If the response is equivalent to the correct "
            "answer or contains all the intermediate steps to get the correct answer, "
            "you should also answer yes. If the response only contains a subset of the "
            "information required by the answer, answer no. \n\nQuestion: "
            "{}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response "
            "correct? Answer yes or no only."
        )
    elif question_type == "temporal-reasoning":
        template = (
            "I will give you a question, a correct answer, and a response from a "
            "model. Please answer yes if the response contains the correct answer. "
            "Otherwise, answer no. If the response is equivalent to the correct "
            "answer or contains all the intermediate steps to get the correct answer, "
            "you should also answer yes. If the response only contains a subset of the "
            "information required by the answer, answer no. In addition, do not "
            "penalize off-by-one errors for the number of days. If the question asks "
            "for the number of days/weeks/months, etc., and the model makes off-by-one "
            "errors (e.g., predicting 19 days when the answer is 18), the model's "
            "response is still correct. \n\nQuestion: {}\n\nCorrect Answer: "
            "{}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or "
            "no only."
        )
    elif question_type == "knowledge-update":
        template = (
            "I will give you a question, a correct answer, and a response from a "
            "model. Please answer yes if the response contains the correct answer. "
            "Otherwise, answer no. If the response contains some previous information "
            "along with an updated answer, the response should be considered as correct "
            "as long as the updated answer is the required answer.\n\nQuestion: "
            "{}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response "
            "correct? Answer yes or no only."
        )
    elif question_type == "single-session-preference":
        template = (
            "I will give you a question, a rubric for desired personalized response, "
            "and a response from a model. Please answer yes if the response satisfies "
            "the desired response. Otherwise, answer no. The model does not need to "
            "reflect all the points in the rubric. The response is correct as long as "
            "it recalls and utilizes the user's personal information correctly."
            "\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}\n\nIs the "
            "model response correct? Answer yes or no only."
        )
    else:
        raise LongMemEvalJudgeError(
            f"unsupported LongMemEval question type: {question_type}"
        )
    return template.format(question, answer, response)


def parse_official_judgment(response: str) -> tuple[bool, bool]:
    """Return the official substring label plus a stricter format diagnostic."""

    normalized = response.strip().casefold().rstrip(".")
    return "yes" in response.casefold(), normalized in {"yes", "no"}


def seal_judge_case(payload: Mapping[str, Any]) -> LongMemEvalJudgeCase:
    rendered = dict(payload)
    rendered["case_sha256"] = sha256_text(canonical_json(rendered))
    return LongMemEvalJudgeCase.model_validate(rendered)


def seal_official_judge_contract(
    sdk_version: str | None = None,
) -> LongMemEvalJudgeContract:
    """Bind the pinned evaluator to the OpenAI SDK present in the image."""

    payload = {
        "schema_version": "1.0",
        "provider": "openai",
        "requested_model": LONGMEMEVAL_OFFICIAL_JUDGE_MODEL,
        "endpoint": LONGMEMEVAL_OFFICIAL_JUDGE_ENDPOINT,
        "provider_api_version": "v1",
        "temperature": 0,
        "n": 1,
        "max_tokens": 10,
        "sdk_package": "openai",
        "sdk_version": sdk_version or importlib.metadata.version("openai"),
        "prompt_version": LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION,
        "evaluator_repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
        "evaluator_source_sha256": LONGMEMEVAL_OFFICIAL_EVALUATOR_SHA256,
    }
    payload["contract_sha256"] = sha256_text(canonical_json(payload))
    return LongMemEvalJudgeContract.model_validate(payload)


def official_judge_request_payload(
    case: LongMemEvalJudgeCase,
    contract: LongMemEvalJudgeContract,
) -> dict[str, Any]:
    """Render the exact official Chat Completions request for one case."""

    return {
        "model": contract.requested_model,
        "messages": [{"role": "user", "content": case.prompt}],
        "temperature": contract.temperature,
        "n": contract.n,
        "max_tokens": contract.max_tokens,
    }


def seal_judgment(payload: Mapping[str, Any]) -> LongMemEvalJudgment:
    rendered = dict(payload)
    try:
        provider_response = json.loads(rendered["provider_response_json"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise LongMemEvalJudgeError("judgment requires a JSON provider response") from exc
    rendered.setdefault("provider_api_version", "v1")
    rendered["system_fingerprint"] = provider_response.get("system_fingerprint")
    rendered["raw_response_sha256"] = sha256_text(rendered["raw_response"])
    rendered["provider_response_sha256"] = sha256_text(
        rendered["provider_response_json"]
    )
    official_label, well_formed = parse_official_judgment(rendered["raw_response"])
    rendered["official_label"] = official_label
    rendered["response_well_formed"] = well_formed
    receipt = {
        "judge_contract_sha256": rendered["judge_contract_sha256"],
        "judge_model_id": rendered["judge_model_id"],
        "openai_sdk_version": rendered["openai_sdk_version"],
        "provider_api_version": rendered["provider_api_version"],
        "request_sha256": rendered["request_sha256"],
        "provider_response_sha256": rendered["provider_response_sha256"],
        "provider_response_id": rendered.get("provider_response_id"),
        "system_fingerprint": rendered["system_fingerprint"],
        "input_tokens": rendered.get("input_tokens"),
        "output_tokens": rendered.get("output_tokens"),
    }
    rendered["judge_receipt_sha256"] = sha256_text(canonical_json(receipt))
    rendered["judgment_sha256"] = sha256_text(canonical_json(rendered))
    return LongMemEvalJudgment.model_validate(rendered)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LongMemEvalJudgeError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise LongMemEvalJudgeError(f"JSON artifact must be an object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise LongMemEvalJudgeError(f"JSONL row must be an object: {path}")
            rows.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LongMemEvalJudgeError(f"invalid JSONL artifact: {path}") from exc
    return rows


def _resolve_bundle_root(root: Path) -> Path:
    root = root.resolve()
    if (root / "manifest.json").is_file():
        return root
    if (root / "bundle" / "manifest.json").is_file():
        return root / "bundle"
    raise LongMemEvalJudgeError("source root has no sealed bundle manifest")


def _verify_bundle(root: Path) -> tuple[Path, dict[str, Any], str]:
    bundle_root = _resolve_bundle_root(root)
    manifest_path = bundle_root / "manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("status") != "COMPLETE":
        raise LongMemEvalJudgeError("source bundle is not complete")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise LongMemEvalJudgeError("source bundle omitted file hashes")
    for name, expected in files.items():
        path = bundle_root / name
        if not path.is_file() or _sha256_file(path) != expected:
            raise LongMemEvalJudgeError(f"source bundle file failed hash check: {name}")
    if "observed_trials.jsonl" not in files:
        raise LongMemEvalJudgeError("source bundle omitted observed trials")
    return bundle_root, manifest, _sha256_file(manifest_path)


def _hypothesis_from_outcome(outcome: TrialOutcome) -> str:
    if outcome.tool_trace_json is None or outcome.model_output_json is None:
        raise LongMemEvalJudgeError("observed trial omitted detailed model artifacts")
    try:
        tool_trace = json.loads(outcome.tool_trace_json)
    except json.JSONDecodeError as exc:
        raise LongMemEvalJudgeError("observed tool trace is invalid JSON") from exc
    actual = tool_trace.get("actual") if isinstance(tool_trace, dict) else None
    if isinstance(actual, dict) and actual.get("mode") == "answer":
        answer = actual.get("answer")
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
    raw = outcome.model_output_json.strip()
    if not raw:
        raise LongMemEvalJudgeError("observed model output is empty")
    return raw


def prepare_longmemeval_judge_cases(
    source: LongMemEvalTaskSource,
    bundle_root: Path,
) -> tuple[LongMemEvalJudgeCase, ...]:
    """Build judge cases from a sealed model bundle and benchmark source."""

    root, manifest, manifest_sha256 = _verify_bundle(bundle_root)
    provenance = manifest.get("world_provenance")
    if not isinstance(provenance, dict):
        raise LongMemEvalJudgeError("source bundle omitted world provenance")
    source_binding_fields = (
        "source",
        "dataset_id",
        "dataset_revision",
        "dataset_filename",
        "dataset_sha256",
        "dataset_size",
        "dataset_license",
        "adapter_version",
        "artifact_role",
        "candidate_policy",
        "candidate_seed",
        "selected_raw_task_ids_sha256",
        "task_count",
    )
    mismatched = [
        field
        for field in source_binding_fields
        if provenance.get(field) != source.provenance.get(field)
    ]
    if mismatched:
        raise LongMemEvalJudgeError(
            f"source bundle and benchmark adapter differ: {mismatched}"
        )
    runtime_binding_fields = (
        "world",
        "actor",
        "snapshot_owner",
        "tool_tape_owner",
        "memory_system",
        "memory_treatment_mode",
    )
    missing_runtime = [
        field for field in runtime_binding_fields if field not in provenance
    ]
    if missing_runtime:
        raise LongMemEvalJudgeError(
            f"source bundle omitted runtime provenance: {missing_runtime}"
        )
    plan = manifest.get("plan")
    if not isinstance(plan, dict):
        raise LongMemEvalJudgeError("source bundle omitted evaluation plan")
    if plan.get("mode") == "all-serve":
        evaluation_mode = "all-serve-system-quality"
        if plan.get("assignment_seed") is not None:
            raise LongMemEvalJudgeError("all-SERVE bundle cannot have an assignment seed")
    else:
        evaluation_mode = "randomized-causal"
        if not isinstance(plan.get("assignment_seed"), int):
            raise LongMemEvalJudgeError("randomized bundle omitted assignment seed")
    planned_ids = plan.get("trial_ids")
    if not isinstance(planned_ids, list) or not all(
        isinstance(value, str) for value in planned_ids
    ):
        raise LongMemEvalJudgeError("source bundle omitted ordered trial IDs")
    if planned_ids != list(source.ids()):
        raise LongMemEvalJudgeError("source bundle trial IDs differ from benchmark source")
    if len(planned_ids) != int(source.provenance["task_count"]):
        raise LongMemEvalJudgeError("source bundle does not cover the complete source")
    if evaluation_mode == "all-serve-system-quality":
        if manifest.get("mode") != "all-serve-system-quality":
            raise LongMemEvalJudgeError("all-SERVE plan lacks a quality-bundle contract")
        if manifest.get("task_count") != len(planned_ids) or manifest.get(
            "served_task_count"
        ) != len(planned_ids):
            raise LongMemEvalJudgeError("all-SERVE bundle task counts are incomplete")
        try:
            load_quality_outcomes(root)
        except QualityCollectionError as exc:
            raise LongMemEvalJudgeError(str(exc)) from exc
    rows = _read_jsonl(root / "observed_trials.jsonl")
    if [row.get("trial_id") for row in rows] != planned_ids:
        raise LongMemEvalJudgeError("observed trial order differs from the plan")
    cases: list[LongMemEvalJudgeCase] = []
    source_task_manifest = task_manifest_sha256(source)
    world_provenance_sha256 = sha256_text(canonical_json(provenance))
    for sequence, row in enumerate(rows, start=1):
        trial_id = row["trial_id"]
        reference = source.evaluation_reference(trial_id)
        try:
            outcome = TrialOutcome.model_validate(row["outcome"])
        except (KeyError, ValueError) as exc:
            raise LongMemEvalJudgeError(f"invalid outcome for {trial_id}") from exc
        if evaluation_mode == "all-serve-system-quality" and (
            outcome.visibility != "serve" or not outcome.candidate_visible
        ):
            raise LongMemEvalJudgeError(
                "all-SERVE bundle contains a hidden-candidate outcome"
            )
        hypothesis = _hypothesis_from_outcome(outcome)
        prompt = official_answer_check_prompt(
            str(reference["question_type"]),
            str(reference["question"]),
            str(reference["answer"]),
            hypothesis,
            abstention=bool(reference["abstention"]),
        )
        cases.append(
            seal_judge_case(
                {
                    "schema_version": "1.0",
                    "sequence": sequence,
                    "trial_id": trial_id,
                    "question_id": reference["question_id"],
                    "question_type": reference["question_type"],
                    "question": reference["question"],
                    "reference_answer": reference["answer"],
                    "hypothesis": hypothesis,
                    "abstention": reference["abstention"],
                    "visibility": outcome.visibility,
                    "evaluation_mode": evaluation_mode,
                    "assignment_seed": plan["assignment_seed"],
                    "source_bundle_manifest_sha256": manifest_sha256,
                    "source_task_manifest_sha256": source_task_manifest,
                    "source_world_provenance_sha256": world_provenance_sha256,
                    "source_model_output_sha256": outcome.model_output_sha256,
                    "source_model_receipt_sha256": outcome.model_receipt_sha256,
                    "prompt_version": LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION,
                    "prompt": prompt,
                    "prompt_sha256": sha256_text(prompt),
                }
            )
        )
    return tuple(cases)


def summarize_longmemeval_judgments(
    cases: Sequence[LongMemEvalJudgeCase],
    judgments: Sequence[LongMemEvalJudgment],
    contract: LongMemEvalJudgeContract,
) -> dict[str, Any]:
    """Validate a complete judgment set and compute native score slices."""

    if not cases or len(cases) != len(judgments):
        raise LongMemEvalJudgeError("judgments must cover every non-empty case")
    if [case.sequence for case in cases] != list(range(1, len(cases) + 1)):
        raise LongMemEvalJudgeError("judge case sequence is not contiguous")
    if [item.sequence for item in judgments] != list(range(1, len(cases) + 1)):
        raise LongMemEvalJudgeError("judgment sequence is not contiguous")
    if [case.case_sha256 for case in cases] != [
        item.case_sha256 for item in judgments
    ]:
        raise LongMemEvalJudgeError("judgments do not bind the ordered judge cases")
    evaluation_modes = {case.evaluation_mode for case in cases}
    source_manifests = {case.source_bundle_manifest_sha256 for case in cases}
    source_task_manifests = {case.source_task_manifest_sha256 for case in cases}
    source_provenance = {case.source_world_provenance_sha256 for case in cases}
    if not all(
        len(values) == 1
        for values in (
            evaluation_modes,
            source_manifests,
            source_task_manifests,
            source_provenance,
        )
    ):
        raise LongMemEvalJudgeError("score report mixes source or evaluation contracts")
    evaluation_mode = next(iter(evaluation_modes))
    if evaluation_mode == "all-serve-system-quality" and (
        any(case.visibility != "serve" for case in cases)
        or any(case.assignment_seed is not None for case in cases)
    ):
        raise LongMemEvalJudgeError("all-SERVE score contains randomized or hidden cases")
    if any(
        item.judge_contract_sha256 != contract.contract_sha256
        or item.judge_model_id != contract.requested_model
        or item.openai_sdk_version != contract.sdk_version
        or item.provider_api_version != contract.provider_api_version
        for item in judgments
    ):
        raise LongMemEvalJudgeError("judgments differ from the immutable judge contract")
    for case, judgment in zip(cases, judgments, strict=True):
        request = official_judge_request_payload(case, contract)
        if sha256_text(canonical_json(request)) != judgment.request_sha256:
            raise LongMemEvalJudgeError("judgment request does not bind the case prompt")
    by_type: dict[str, dict[str, int | float]] = {}
    by_visibility: dict[str, dict[str, int | float]] = {}
    for case, judgment in zip(cases, judgments, strict=True):
        for key, table in (
            (case.question_type, by_type),
            (case.visibility, by_visibility),
        ):
            cell = table.setdefault(key, {"count": 0, "correct": 0})
            cell["count"] = int(cell["count"]) + 1
            cell["correct"] = int(cell["correct"]) + int(judgment.official_label)
    for table in (by_type, by_visibility):
        for cell in table.values():
            cell["accuracy"] = int(cell["correct"]) / int(cell["count"])
    correct = sum(item.official_label for item in judgments)
    well_formed = sum(item.response_well_formed for item in judgments)
    reason = (
        "Official LongMemEval prompt contract over a complete sealed all-SERVE "
        "source slice; matched controls and a registered full-benchmark run remain "
        "required before a memory-quality claim."
        if evaluation_mode == "all-serve-system-quality"
        else "Official LongMemEval prompt contract over a randomized causal "
        "transport panel; this is not a full benchmark or memory-quality result."
    )
    return {
        "schema_version": "1.0",
        "status": (
            "OFFICIAL_PROMPT_SCORE_VALID"
            if well_formed == len(judgments)
            else "MALFORMED_JUDGE_OUTPUT"
        ),
        "scientific_result": False,
        "reason": reason,
        "evaluation_mode": evaluation_mode,
        "source_bundle_manifest_sha256": next(iter(source_manifests)),
        "source_task_manifest_sha256": next(iter(source_task_manifests)),
        "source_world_provenance_sha256": next(iter(source_provenance)),
        "prompt_port": {
            "version": LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION,
            "repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
            "source_sha256": LONGMEMEVAL_OFFICIAL_EVALUATOR_SHA256,
        },
        "judge_contract": contract.model_dump(mode="json"),
        "judge_contract_sha256": contract.contract_sha256,
        "judge_model_id": contract.requested_model,
        "cases": len(cases),
        "correct": correct,
        "accuracy": correct / len(cases),
        "well_formed_responses": well_formed,
        "well_formed_response_rate": well_formed / len(cases),
        "question_type_counts": dict(Counter(case.question_type for case in cases)),
        "by_question_type": dict(sorted(by_type.items())),
        "by_visibility": dict(sorted(by_visibility.items())),
        "case_root_sha256": sha256_text(
            canonical_json([case.case_sha256 for case in cases])
        ),
        "judgment_root_sha256": sha256_text(
            canonical_json([item.judgment_sha256 for item in judgments])
        ),
    }


def atomic_write(path: Path, data: bytes) -> str:
    """Write one immutable artifact and fsync its containing directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise LongMemEvalJudgeError(f"refusing to overwrite artifact: {path}")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(data)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return hashlib.sha256(data).hexdigest()


def write_judge_packet(
    output_dir: Path,
    source: LongMemEvalTaskSource,
    cases: Sequence[LongMemEvalJudgeCase],
    contract: LongMemEvalJudgeContract,
    *,
    experiment_sha256: str,
    preparation_mode: Literal["transport-panel", "full-benchmark"],
) -> dict[str, Any]:
    """Persist an immutable packet that can be judged in a separate container."""

    if not cases:
        raise LongMemEvalJudgeError("judge packet requires at least one case")
    if not isinstance(experiment_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", experiment_sha256
    ):
        raise LongMemEvalJudgeError("judge packet requires an experiment SHA-256")
    if [case.sequence for case in cases] != list(range(1, len(cases) + 1)):
        raise LongMemEvalJudgeError("judge packet case sequence is not contiguous")
    if len({case.trial_id for case in cases}) != len(cases):
        raise LongMemEvalJudgeError("judge packet contains duplicate trial IDs")
    evaluation_modes = {case.evaluation_mode for case in cases}
    assignment_seeds = {case.assignment_seed for case in cases}
    source_manifests = {case.source_bundle_manifest_sha256 for case in cases}
    source_task_manifests = {case.source_task_manifest_sha256 for case in cases}
    source_provenance = {case.source_world_provenance_sha256 for case in cases}
    if len(evaluation_modes) != 1 or len(assignment_seeds) != 1:
        raise LongMemEvalJudgeError("judge packet mixes evaluation contracts")
    if not all(
        len(values) == 1
        for values in (source_manifests, source_task_manifests, source_provenance)
    ):
        raise LongMemEvalJudgeError("judge packet mixes source bundles")
    evaluation_mode = next(iter(evaluation_modes))
    assignment_seed = next(iter(assignment_seeds))
    expected_evaluation_mode = (
        "all-serve-system-quality"
        if preparation_mode == "full-benchmark"
        else "randomized-causal"
    )
    if evaluation_mode != expected_evaluation_mode:
        raise LongMemEvalJudgeError("judge packet mode differs from evaluation bundle")
    if evaluation_mode == "all-serve-system-quality":
        if assignment_seed is not None or any(
            case.visibility != "serve" for case in cases
        ):
            raise LongMemEvalJudgeError("all-SERVE judge packet mixes visibility")
        if len(cases) != int(source.provenance["task_count"]):
            raise LongMemEvalJudgeError("all-SERVE judge packet is incomplete")
    elif not isinstance(assignment_seed, int):
        raise LongMemEvalJudgeError("randomized judge packet omitted assignment seed")

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise LongMemEvalJudgeError(f"refusing to overwrite packet: {output_dir}")
    output_dir.mkdir(parents=True)
    descriptor = os.open(output_dir.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    case_bytes = "".join(
        canonical_json(case.model_dump(mode="json")) + "\n" for case in cases
    ).encode()
    cases_sha256 = atomic_write(output_dir / "judge-cases.jsonl", case_bytes)
    manifest = {
        "schema_version": "1.0",
        "status": "PREPARED_OFFICIAL_PROMPT_PACKET",
        "scientific_result": False,
        "preparation_mode": preparation_mode,
        "experiment_sha256": experiment_sha256,
        "dataset": {
            "dataset_id": LONGMEMEVAL_DATASET_ID,
            "revision": source.provenance["dataset_revision"],
            "sha256": source.provenance["dataset_sha256"],
            "size": source.provenance["dataset_size"],
        },
        "prompt_port": {
            "version": LONGMEMEVAL_OFFICIAL_PROMPT_PORT_VERSION,
            "repository_revision": LONGMEMEVAL_REPOSITORY_REVISION,
            "source_sha256": LONGMEMEVAL_OFFICIAL_EVALUATOR_SHA256,
        },
        "judge_contract": contract.model_dump(mode="json"),
        "judge_contract_sha256": contract.contract_sha256,
        "evaluation_mode": evaluation_mode,
        "assignment_seed": assignment_seed,
        "task_manifest_sha256": next(iter(source_task_manifests)),
        "source_world_provenance_sha256": next(iter(source_provenance)),
        "case_count": len(cases),
        "ordered_trial_id_root_sha256": sha256_text(
            canonical_json([case.trial_id for case in cases])
        ),
        "case_root_sha256": sha256_text(
            canonical_json([case.case_sha256 for case in cases])
        ),
        "question_type_counts": dict(Counter(case.question_type for case in cases)),
        "source_bundle_manifest_sha256": next(iter(source_manifests)),
        "model_output_root_sha256": sha256_text(
            canonical_json([case.source_model_output_sha256 for case in cases])
        ),
        "model_receipt_root_sha256": sha256_text(
            canonical_json([case.source_model_receipt_sha256 for case in cases])
        ),
        "files": {"judge-cases.jsonl": cases_sha256},
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    atomic_write(output_dir / "manifest.json", manifest_bytes)
    return manifest
