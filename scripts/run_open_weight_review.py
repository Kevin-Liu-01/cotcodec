#!/usr/bin/env python3
"""Run one open-weight gauntlet review offline with vLLM and write a receipt.

This is the provider-distinct reviewer of program decisions D23 and D24. A
cached open-weight model, served offline with vLLM's ``LLM.generate`` inside the
vLLM overlay image, reads a review prompt (UTF-8 text: proposal text only, never
code, so D7's untrusted-code rule does not apply) and answers with one JSON
object that must validate against a given JSON schema.

Decoding is greedy (temperature 0) with a fixed token budget. The first declared
seed (42 in every rendered manifest) is the primary review; every further seed
is a replicate of the same request in the same batch, recorded to show whether
the greedy output repeats. A primary reply that does not parse or validate gets
exactly one retry, with the error appended to the prompt.

Subcommands:

* ``pack``: prompt file + schema file -> one request bundle (the lane's study
  artifact, mounted read-only at ``/inputs/study-artifact.json``).
* ``plan``: print the resolved request, engine and sampling settings (CPU).
* ``doctor``: check that the installed vLLM accepts every argument ``run``
  passes (CPU, inside the image).
* ``run``: serve the model, write the raw outputs, the parsed JSON and a receipt.
* ``manifest``: render a docker-research lane manifest for one review job.
* ``verify``: re-hash a finished review directory against its receipt.

Exit codes of ``run``: 0 parsed, 2 bad input or environment, 3 stopped by a
signal (receipt and checkpoint marker written; nothing to resume, resubmit),
4 no valid JSON after the retry, 5 engine failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCHEMA_VERSION = 1
REQUEST_KIND = "open-weight-review-request"
RECEIPT_KIND = "open-weight-review-receipt"
VALIDATOR_ID = "cotcodec-json-schema-subset-v1"
PROMPT_FORMAT_ID = "owr-user-message-v1"

#: Reviewer models a manifest may bind, with the lane memory each needs.
#: qwen3.6-35b-a3b: 64.56 GiB of language-model weights (vision tower and MTP
#: head not loaded), which leaves room for the KV cache on one 80 GB H100.
REVIEWER_MODELS: dict[str, dict[str, int]] = {
    "qwen3.6-35b-a3b": {"memory_gb": 160},
    "qwen3.5-9b": {"memory_gb": 96},
}
DEFAULT_SEEDS = (42, 43, 44)
TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 16384
DEFAULT_MAX_MODEL_LEN = 65536
DEFAULT_GPU_MEMORY_UTILIZATION = 0.90
MAX_NUM_SEQS = 8
MAX_PROMPT_BYTES = 1024 * 1024
MAX_SCHEMA_BYTES = 256 * 1024
MAX_ERROR_CHARS = 1500
#: Upper bound on the engine's graceful shutdown before the process exits anyway.
ENGINE_CLOSE_TIMEOUT_S = 30.0

LANE_EVIDENCE_PATH = "/inputs/study-artifact.json"
LANE_OUTPUT_DIR = "/outputs/review"
LANE_MODEL_ROOT = "/model-cache/cotcodec-models"
LANE_RECEIPT_ROOT = "/model-cache/cotcodec-receipts"
LANE_RUNTIME = "docker-single-node-discovery-v1"
DEFAULT_MODEL_CACHE_HOST = "/home/kevin/cotcodec-runs/hf-cache"
DEFAULT_REQUEST_LICENSE = "LicenseRef-cotcodec-review-request"

THINK_END = "</think>"
SCHEMA_SUFFIX = (
    "\n\n---\n"
    "Answer with exactly one JSON object and nothing else. "
    "It must validate against this JSON Schema:\n"
    "```json\n{schema}\n```\n"
)
RETRY_SUFFIX = (
    "\n\n---\n"
    "Your previous answer to this request could not be used: {error}\n"
    "{hint}Answer again with exactly one JSON object that validates against the schema above.\n"
)
TRUNCATION_HINT = "It ran out of tokens before the JSON object; keep your reasoning short. "

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
LICENSE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$")
FENCE_RE = re.compile(r"```(?:json|JSON)?[ \t]*\n(.*?)\n?```", re.DOTALL)

EXIT_OK, EXIT_INPUT, EXIT_SIGNAL, EXIT_PARSE, EXIT_ENGINE = 0, 2, 3, 4, 5


class InputError(ValueError):
    """A request, schema, model receipt or setting is unusable; nothing was generated."""


class ParseFailure(ValueError):
    """A reply could not be turned into a schema-valid JSON object."""


class ReviewInterrupted(BaseException):  # noqa: N818 - like KeyboardInterrupt
    """A stop signal arrived while the engine was loading or generating.

    A BaseException, so vLLM's own ``except Exception`` handlers cannot swallow it.
    """


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# JSON Schema subset (the same code validates on the Mac and in the image)
# ---------------------------------------------------------------------------

JSON_TYPES = ("object", "array", "string", "number", "integer", "boolean", "null")
ANNOTATIONS = frozenset(
    {"$schema", "$id", "$comment", "title", "description", "default", "examples"}
)
KEYWORDS = ANNOTATIONS | {
    "$defs",
    "$ref",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "minProperties",
    "maxProperties",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "enum",
    "const",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "pattern",
    "anyOf",
    "allOf",
    "oneOf",
}
MAX_SCHEMA_DEPTH = 64


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def check_schema(schema: Any) -> None:
    """Refuse a schema that uses anything outside the supported subset (fail closed)."""

    if not isinstance(schema, dict):
        raise InputError("the response schema must be a JSON object")
    if schema.get("type") != "object":
        raise InputError('the response schema must declare "type": "object" at the top')
    defs = schema.get("$defs", {})
    if not isinstance(defs, dict):
        raise InputError("$defs must be an object")
    _check_node(schema, defs, "$", 0)


def _check_node(node: Any, defs: Mapping[str, Any], path: str, depth: int) -> None:
    if depth > MAX_SCHEMA_DEPTH:
        raise InputError(f"{path}: schema nesting exceeds {MAX_SCHEMA_DEPTH}")
    if isinstance(node, bool):
        return
    if not isinstance(node, dict):
        raise InputError(f"{path}: a subschema must be an object or a boolean")
    unknown = sorted(set(node) - KEYWORDS)
    if unknown:
        raise InputError(f"{path}: unsupported schema keywords {unknown} ({VALIDATOR_ID})")
    if "$defs" in node and path != "$":
        raise InputError(f"{path}: $defs is allowed only at the top level")
    if "type" in node:
        kinds = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not kinds or any(kind not in JSON_TYPES for kind in kinds):
            raise InputError(f"{path}: type must name JSON types {list(JSON_TYPES)}")
    if "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
            raise InputError(f"{path}: only local #/$defs/<name> references are supported")
        if ref[len("#/$defs/") :] not in defs:
            raise InputError(f"{path}: $ref {ref} names no $defs entry")
    for key in ("properties", "$defs"):
        if key in node:
            if not isinstance(node[key], dict):
                raise InputError(f"{path}: {key} must be an object")
            for name, child in node[key].items():
                _check_node(child, defs, f"{path}.{key}.{name}", depth + 1)
    if "required" in node:
        required = node["required"]
        if (
            not isinstance(required, list)
            or not all(isinstance(name, str) for name in required)
            or len(set(required)) != len(required)
        ):
            raise InputError(f"{path}: required must be a list of distinct strings")
    for key in ("additionalProperties", "items"):
        if key in node:
            _check_node(node[key], defs, f"{path}.{key}", depth + 1)
    for key in ("anyOf", "allOf", "oneOf"):
        if key in node:
            if not isinstance(node[key], list) or not node[key]:
                raise InputError(f"{path}: {key} must be a nonempty list")
            for index, child in enumerate(node[key]):
                _check_node(child, defs, f"{path}.{key}[{index}]", depth + 1)
    if "enum" in node and (not isinstance(node["enum"], list) or not node["enum"]):
        raise InputError(f"{path}: enum must be a nonempty list")
    for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        if key in node and not (_is_number(node[key]) and math.isfinite(node[key])):
            raise InputError(f"{path}: {key} must be a finite number")
    for key in ("minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties"):
        if key in node and not _is_count(node[key]):
            raise InputError(f"{path}: {key} must be a nonnegative integer")
    if "uniqueItems" in node and not isinstance(node["uniqueItems"], bool):
        raise InputError(f"{path}: uniqueItems must be a boolean")
    if "pattern" in node:
        try:
            re.compile(node["pattern"])
        except (re.error, TypeError) as exc:
            raise InputError(f"{path}: pattern does not compile: {exc}") from exc


def json_equal(left: Any, right: Any) -> bool:
    """JSON equality: unlike Python's ==, true is not 1 and 1 is 1.0."""

    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if _is_number(left) and _is_number(right):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(json_equal(left[k], right[k]) for k in left)
    return type(left) is type(right) and left == right


def _type_matches(value: Any, kind: str) -> bool:
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    if kind == "number":
        return _is_number(value)
    return _is_number(value) and float(value).is_integer()  # integer


def validate_instance(instance: Any, schema: Mapping[str, Any]) -> list[str]:
    """Return every violation (JSON-path prefixed); an empty list means valid."""

    errors: list[str] = []
    _validate(instance, schema, schema.get("$defs", {}), "$", errors, 0)
    return errors


def _validate(
    value: Any,
    node: Any,
    defs: Mapping[str, Any],
    path: str,
    errors: list[str],
    depth: int,
) -> None:
    if depth > MAX_SCHEMA_DEPTH:
        errors.append(f"{path}: schema recursion exceeds {MAX_SCHEMA_DEPTH}")
        return
    if node is True:
        return
    if node is False:
        errors.append(f"{path}: no value is allowed here")
        return
    if "$ref" in node:
        _validate(value, defs[node["$ref"][len("#/$defs/") :]], defs, path, errors, depth + 1)
    if "type" in node:
        kinds = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not any(_type_matches(value, kind) for kind in kinds):
            errors.append(f"{path}: expected {' or '.join(kinds)}, got {_json_type(value)}")
            return
    if "const" in node and not json_equal(value, node["const"]):
        errors.append(f"{path}: must equal {json.dumps(node['const'])}")
    if "enum" in node and not any(json_equal(value, option) for option in node["enum"]):
        errors.append(f"{path}: must be one of {json.dumps(node['enum'])}")
    if _is_number(value):
        if "minimum" in node and value < node["minimum"]:
            errors.append(f"{path}: {value} is below the minimum {node['minimum']}")
        if "maximum" in node and value > node["maximum"]:
            errors.append(f"{path}: {value} is above the maximum {node['maximum']}")
        if "exclusiveMinimum" in node and value <= node["exclusiveMinimum"]:
            errors.append(f"{path}: {value} must be above {node['exclusiveMinimum']}")
        if "exclusiveMaximum" in node and value >= node["exclusiveMaximum"]:
            errors.append(f"{path}: {value} must be below {node['exclusiveMaximum']}")
    if isinstance(value, str):
        if "minLength" in node and len(value) < node["minLength"]:
            errors.append(f"{path}: shorter than {node['minLength']} characters")
        if "maxLength" in node and len(value) > node["maxLength"]:
            errors.append(f"{path}: longer than {node['maxLength']} characters")
        if "pattern" in node and re.search(node["pattern"], value) is None:
            errors.append(f"{path}: does not match the pattern {node['pattern']!r}")
    if isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            errors.append(f"{path}: fewer than {node['minItems']} items")
        if "maxItems" in node and len(value) > node["maxItems"]:
            errors.append(f"{path}: more than {node['maxItems']} items")
        if node.get("uniqueItems") and any(
            json_equal(value[i], value[j])
            for i in range(len(value))
            for j in range(i + 1, len(value))
        ):
            errors.append(f"{path}: items are not unique")
        if "items" in node:
            for index, item in enumerate(value):
                _validate(item, node["items"], defs, f"{path}[{index}]", errors, depth + 1)
    if isinstance(value, dict):
        if "minProperties" in node and len(value) < node["minProperties"]:
            errors.append(f"{path}: fewer than {node['minProperties']} properties")
        if "maxProperties" in node and len(value) > node["maxProperties"]:
            errors.append(f"{path}: more than {node['maxProperties']} properties")
        errors.extend(
            f"{path}: missing required property {name!r}"
            for name in node.get("required", [])
            if name not in value
        )
        properties = node.get("properties", {})
        for name, item in value.items():
            if name in properties:
                _validate(item, properties[name], defs, f"{path}.{name}", errors, depth + 1)
            elif "additionalProperties" in node:
                if node["additionalProperties"] is False:
                    errors.append(f"{path}: property {name!r} is not allowed")
                else:
                    _validate(
                        item,
                        node["additionalProperties"],
                        defs,
                        f"{path}.{name}",
                        errors,
                        depth + 1,
                    )
    for key in ("allOf", "anyOf", "oneOf"):
        if key not in node:
            continue
        outcomes = []
        for branch in node[key]:
            branch_errors: list[str] = []
            _validate(value, branch, defs, path, branch_errors, depth + 1)
            outcomes.append(branch_errors)
        passed = sum(1 for outcome in outcomes if not outcome)
        if key == "allOf":
            for outcome in outcomes:
                errors.extend(outcome)
        elif key == "anyOf" and passed == 0:
            errors.append(f"{path}: matches none of the anyOf branches")
        elif key == "oneOf" and passed != 1:
            errors.append(f"{path}: matches {passed} oneOf branches, not exactly one")


def _json_type(value: Any) -> str:
    for kind in ("null", "boolean", "integer", "number", "string", "array", "object"):
        if _type_matches(value, kind):
            return kind
    return type(value).__name__


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewRequest:
    prompt: str
    prompt_sha256: str
    prompt_bytes: int
    schema_text: str
    schema: dict[str, Any]
    schema_sha256: str
    label: str
    source: str  # "evidence" (a packed bundle) or "files"
    request_sha256: str | None = None

    def describe(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "label": self.label,
            "request_sha256": self.request_sha256,
            "prompt_sha256": self.prompt_sha256,
            "prompt_bytes": self.prompt_bytes,
            "schema_sha256": self.schema_sha256,
        }


def decode_prompt(data: bytes) -> str:
    if not data.strip():
        raise InputError("the prompt is empty")
    if len(data) > MAX_PROMPT_BYTES:
        raise InputError(f"the prompt exceeds {MAX_PROMPT_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError(f"the prompt is not UTF-8: {exc}") from exc
    if "\x00" in text:
        raise InputError("the prompt contains a NUL character")
    return text


def load_schema_text(data: bytes) -> tuple[str, dict[str, Any]]:
    if len(data) > MAX_SCHEMA_BYTES:
        raise InputError(f"the schema exceeds {MAX_SCHEMA_BYTES} bytes")
    try:
        text = data.decode("utf-8")
        schema = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"the schema is not UTF-8 JSON: {exc}") from exc
    check_schema(schema)
    return text, schema


def request_from_files(prompt_file: Path, schema_file: Path, label: str) -> ReviewRequest:
    if not LABEL_RE.fullmatch(label):
        raise InputError("label must be a lowercase kebab-case slug of at most 48 characters")
    prompt_data = prompt_file.read_bytes()
    schema_data = schema_file.read_bytes()
    prompt = decode_prompt(prompt_data)
    schema_text, schema = load_schema_text(schema_data)
    return ReviewRequest(
        prompt=prompt,
        prompt_sha256=sha256_bytes(prompt_data),
        prompt_bytes=len(prompt_data),
        schema_text=schema_text,
        schema=schema,
        schema_sha256=sha256_bytes(schema_data),
        label=label,
        source="files",
    )


def request_bundle(request: ReviewRequest) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": REQUEST_KIND,
        "label": request.label,
        "prompt": request.prompt,
        "prompt_sha256": request.prompt_sha256,
        "prompt_bytes": request.prompt_bytes,
        "response_schema_text": request.schema_text,
        "response_schema_sha256": request.schema_sha256,
    }


def load_request_bundle(path: Path, expected_sha256: str | None) -> ReviewRequest:
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if expected_sha256 is not None and actual != expected_sha256:
        raise InputError(f"request bundle SHA-256 {actual} differs from {expected_sha256}")
    try:
        bundle = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"the request bundle is not UTF-8 JSON: {exc}") from exc
    expected_keys = set(request_bundle(_EMPTY_REQUEST))
    if not isinstance(bundle, dict) or set(bundle) != expected_keys:
        raise InputError(f"the request bundle must hold exactly {sorted(expected_keys)}")
    if bundle["kind"] != REQUEST_KIND or bundle["schema_version"] != SCHEMA_VERSION:
        raise InputError("the request bundle kind or schema_version is wrong")
    prompt_data = str(bundle["prompt"]).encode("utf-8")
    schema_data = str(bundle["response_schema_text"]).encode("utf-8")
    if sha256_bytes(prompt_data) != bundle["prompt_sha256"]:
        raise InputError("the bundled prompt differs from its recorded SHA-256")
    if len(prompt_data) != bundle["prompt_bytes"]:
        raise InputError("the bundled prompt differs from its recorded size")
    if sha256_bytes(schema_data) != bundle["response_schema_sha256"]:
        raise InputError("the bundled schema differs from its recorded SHA-256")
    if not isinstance(bundle["label"], str) or not LABEL_RE.fullmatch(bundle["label"]):
        raise InputError("the bundled label is not a safe slug")
    prompt = decode_prompt(prompt_data)
    schema_text, schema = load_schema_text(schema_data)
    return ReviewRequest(
        prompt=prompt,
        prompt_sha256=bundle["prompt_sha256"],
        prompt_bytes=bundle["prompt_bytes"],
        schema_text=schema_text,
        schema=schema,
        schema_sha256=bundle["response_schema_sha256"],
        label=bundle["label"],
        source="evidence",
        request_sha256=actual,
    )


_EMPTY_REQUEST = ReviewRequest("", "", 0, "", {}, "", "", "files")


def user_message(request: ReviewRequest, retry_error: str | None = None) -> str:
    """The single user turn the model sees: prompt, schema block, optional retry note."""

    message = request.prompt + SCHEMA_SUFFIX.format(schema=request.schema_text.strip())
    if retry_error is not None:
        error = (
            retry_error
            if len(retry_error) <= MAX_ERROR_CHARS
            else (retry_error[:MAX_ERROR_CHARS] + " [truncated]")
        )
        hint = TRUNCATION_HINT if "finish_reason=length" in retry_error else ""
        message += RETRY_SUFFIX.format(error=error, hint=hint)
    return message


# ---------------------------------------------------------------------------
# Reply parsing
# ---------------------------------------------------------------------------


def _reject_constant(name: str) -> Any:
    raise ParseFailure(f"the JSON uses the non-standard constant {name}")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ParseFailure(f"the JSON object repeats the key {key!r}")
        result[key] = value
    return result


def _loads(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)


def final_answer(text: str, *, thinking: bool, finish_reason: str | None) -> str:
    """The reply after the reasoning block (the whole reply when thinking is off)."""

    if THINK_END in text:
        return text.rsplit(THINK_END, 1)[1]
    if thinking:
        raise ParseFailure(
            f"the reply ended inside its reasoning block (no {THINK_END}; "
            f"finish_reason={finish_reason})"
        )
    return text


def extract_json(answer: str, *, finish_reason: str | None) -> tuple[Any, str]:
    """Parse the answer as bare JSON, else the first fenced block, else from the first brace."""

    stripped = answer.strip()
    if not stripped:
        raise ParseFailure(f"the reply has no answer text (finish_reason={finish_reason})")
    try:
        return _loads(stripped), "bare"
    except json.JSONDecodeError:
        pass
    for match in FENCE_RE.finditer(stripped):
        try:
            return _loads(match.group(1)), "fenced"
        except json.JSONDecodeError:
            continue
    start = stripped.find("{")
    if start < 0:
        raise ParseFailure(f"the reply contains no JSON object (finish_reason={finish_reason})")
    try:
        value, _end = json.JSONDecoder(
            object_pairs_hook=_unique_pairs, parse_constant=_reject_constant
        ).raw_decode(stripped, start)
    except json.JSONDecodeError as exc:
        raise ParseFailure(
            f"the JSON object does not parse: {exc.msg} at character {exc.pos - start} "
            f"(finish_reason={finish_reason})"
        ) from exc
    return value, "embedded"


def parse_reply(
    text: str, schema: Mapping[str, Any], *, thinking: bool, finish_reason: str | None
) -> tuple[dict[str, Any], str]:
    value, extraction = extract_json(
        final_answer(text, thinking=thinking, finish_reason=finish_reason),
        finish_reason=finish_reason,
    )
    errors = validate_instance(value, schema)
    if errors:
        shown = "; ".join(errors[:20]) + ("; ..." if len(errors) > 20 else "")
        raise ParseFailure(f"the JSON does not validate against the schema: {shown}")
    return value, extraction


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineSettings:
    tensor_parallel_size: int = 1
    max_model_len: int = DEFAULT_MAX_MODEL_LEN
    max_tokens: int = DEFAULT_MAX_TOKENS
    gpu_memory_utilization: float = DEFAULT_GPU_MEMORY_UTILIZATION
    enforce_eager: bool = False
    thinking: bool = True
    seeds: tuple[int, ...] = DEFAULT_SEEDS

    def __post_init__(self) -> None:
        if not 1 <= self.tensor_parallel_size <= 8:
            raise InputError("tensor_parallel_size must be in [1, 8]")
        if not 1 <= self.max_tokens < self.max_model_len <= 262144:
            raise InputError("need 1 <= max_tokens < max_model_len <= 262144")
        if not 0.5 <= self.gpu_memory_utilization <= 0.95:
            raise InputError("gpu_memory_utilization must be in [0.5, 0.95]")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds):
            raise InputError("seeds must be distinct")
        if len(self.seeds) > MAX_NUM_SEQS:
            raise InputError(f"at most {MAX_NUM_SEQS} seeds")
        if any(seed < 0 or seed >= 2**32 for seed in self.seeds):
            raise InputError("seeds must be in [0, 2**32)")

    @property
    def primary_seed(self) -> int:
        return self.seeds[0]

    def llm_kwargs(self, model_dir: str) -> dict[str, Any]:
        """Every argument passed to ``vllm.LLM``; the doctor checks each one exists."""
        return {
            "model": model_dir,
            "tokenizer": model_dir,
            "trust_remote_code": False,
            "dtype": "auto",
            "tensor_parallel_size": self.tensor_parallel_size,
            "max_model_len": self.max_model_len,
            "gpu_memory_utilization": self.gpu_memory_utilization,
            "enforce_eager": self.enforce_eager,
            "seed": self.primary_seed,
            "max_num_seqs": MAX_NUM_SEQS,
            "language_model_only": True,
            "disable_log_stats": True,
        }

    def sampling(self, seed: int) -> dict[str, Any]:
        """Every argument passed to ``vllm.SamplingParams`` for one request."""
        return {"temperature": TEMPERATURE, "max_tokens": self.max_tokens, "seed": seed, "n": 1}

    def describe(self) -> dict[str, Any]:
        return {**asdict(self), "seeds": list(self.seeds), "temperature": TEMPERATURE}


@dataclass(frozen=True)
class RenderedPrompt:
    text: str
    token_ids: tuple[int, ...]


@dataclass(frozen=True)
class Completion:
    text: str
    token_ids: tuple[int, ...]
    finish_reason: str | None


class ReviewEngine(Protocol):
    def render(self, message: str, *, thinking: bool) -> RenderedPrompt: ...

    def generate(
        self, prompt: RenderedPrompt, *, seeds: Sequence[int], max_tokens: int
    ) -> list[Completion]: ...

    def facts(self) -> dict[str, Any]: ...

    def close(self) -> None: ...


EngineFactory = Callable[[EngineSettings, Path], ReviewEngine]


class VllmReviewEngine:
    """vLLM's offline engine plus the model's own Hugging Face chat template."""

    def __init__(self, settings: EngineSettings, model_dir: Path) -> None:
        from transformers import AutoTokenizer
        from vllm import LLM

        self.settings = settings
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=False)
        self.llm = LLM(**settings.llm_kwargs(str(model_dir)))

    def render(self, message: str, *, thinking: bool) -> RenderedPrompt:
        text = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": message}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=thinking,
        )
        ids = self.tokenizer.encode(text, add_special_tokens=False)
        return RenderedPrompt(text=text, token_ids=tuple(int(token) for token in ids))

    def generate(
        self, prompt: RenderedPrompt, *, seeds: Sequence[int], max_tokens: int
    ) -> list[Completion]:
        from vllm import SamplingParams
        from vllm.inputs import TokensPrompt

        params = [
            SamplingParams(**{**self.settings.sampling(s), "max_tokens": max_tokens}) for s in seeds
        ]
        prompts = [TokensPrompt(prompt_token_ids=list(prompt.token_ids)) for _ in seeds]
        results = self.llm.generate(prompts, params, use_tqdm=False)
        completions = []
        for result in results:
            output = result.outputs[0]
            completions.append(
                Completion(
                    text=output.text,
                    token_ids=tuple(int(token) for token in output.token_ids),
                    finish_reason=output.finish_reason,
                )
            )
        return completions

    def facts(self) -> dict[str, Any]:
        import torch
        import transformers
        import vllm

        facts: dict[str, Any] = {
            "vllm_version": vllm.__version__,
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "gpu_names": gpu_names(),
            "chat_template_sha256": sha256_bytes(
                str(self.tokenizer.chat_template or "").encode("utf-8")
            ),
        }
        try:  # resolved engine facts are best effort: the attribute layout is internal
            config = self.llm.llm_engine.vllm_config
            facts["resolved"] = {
                "max_model_len": config.model_config.max_model_len,
                "dtype": str(config.model_config.dtype),
                "tensor_parallel_size": config.parallel_config.tensor_parallel_size,
                "enable_prefix_caching": config.cache_config.enable_prefix_caching,
                "num_gpu_blocks": config.cache_config.num_gpu_blocks,
                "block_size": config.cache_config.block_size,
                "enforce_eager": config.model_config.enforce_eager,
            }
        except Exception as exc:  # noqa: BLE001 - record, never fail the review on it
            facts["resolved_error"] = f"{type(exc).__name__}: {exc}"[:300]
        return facts

    def close(self) -> None:
        """Ask the engine-core process to exit (the v1 client's own shutdown)."""
        self.llm.llm_engine.engine_core.shutdown()


def close_engine(engine: Any, timeout_s: float) -> str:
    """Shut the engine down in a daemon thread and give up after ``timeout_s``.

    Smoke job 617 showed why: after a complete review the process hung in
    interpreter shutdown (vLLM teardown) and, as PID 1, outlived its Slurm job.
    The process now exits with ``os._exit`` after this bounded close.
    """

    close = getattr(engine, "close", None)
    if close is None:
        return "no-close"
    outcome: list[str] = []

    def target() -> None:
        try:
            close()
            outcome.append("closed")
        except Exception as exc:  # noqa: BLE001 - recorded in the receipt
            outcome.append(f"error: {type(exc).__name__}: {exc}"[:300])

    thread = threading.Thread(target=target, name="owr-engine-close", daemon=True)
    thread.start()
    thread.join(timeout_s)
    return outcome[0] if outcome else f"timeout after {timeout_s:g} s"


def gpu_names() -> list[str] | str:
    """GPU names from nvidia-smi: unlike torch.cuda, no CUDA context in this process."""

    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {type(exc).__name__}"
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Model receipt
# ---------------------------------------------------------------------------

SPOT_CHECK_FILES = ("config.json", "tokenizer_config.json", "chat_template.jinja")


def load_model_receipt(path: Path, expected_sha256: str, model_dir: Path) -> dict[str, Any]:
    """Bind the run to the lane-verified model receipt and spot-check the snapshot."""

    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != expected_sha256:
        raise InputError(f"model receipt SHA-256 {actual} differs from {expected_sha256}")
    receipt = json.loads(data)
    model_id = receipt.get("model_id")
    if model_id != model_dir.name:
        raise InputError(
            f"model receipt is for {model_id!r}, the model directory is {model_dir.name}"
        )
    if receipt.get("backend") != "huggingface" or receipt.get("mode") != "full":
        raise InputError("the reviewer needs a full Hugging Face snapshot receipt")
    if not GIT_RE.fullmatch(str(receipt.get("revision"))):
        raise InputError("model receipt revision is not a 40-hex commit")
    if not SHA_RE.fullmatch(str(receipt.get("artifact_root_sha256"))):
        raise InputError("model receipt artifact root is not a 64-hex digest")
    listed = {entry["path"]: entry["sha256"] for entry in receipt.get("files", [])}
    checked = []
    for name in SPOT_CHECK_FILES:
        if name not in listed:
            continue
        local = model_dir / name
        if not local.is_file() or sha256_file(local) != listed[name]:
            raise InputError(f"{name} in the model directory differs from the model receipt")
        checked.append(name)
    if "config.json" not in checked:
        raise InputError("the model receipt does not list config.json")
    lane_model = os.environ.get("COTCODEC_MODEL_ID")
    if lane_model not in (None, model_id):
        raise InputError(f"the lane bound model {lane_model}, not {model_id}")
    return {
        "model_id": model_id,
        "repo_id": receipt.get("repo_id"),
        "revision": receipt["revision"],
        "receipt_sha256": actual,
        "artifact_root_sha256": receipt["artifact_root_sha256"],
        "total_bytes": receipt.get("total_bytes"),
        "publication_eligible": receipt.get("publication_eligible"),
        "spot_checked_files": checked,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


STOP_SIGNALS = ("SIGUSR1", "SIGTERM", "SIGINT")


@dataclass
class SignalState:
    """USR1, TERM and INT: recorded always, raised only while loading or generating.

    The workload is PID 1 in the lane container, where a signal without a handler
    is ignored, so the handlers are installed before anything else runs.
    """

    received: list[str] = field(default_factory=list)
    blocking: bool = False
    _previous: dict[str, Any] = field(default_factory=dict)

    def handle(self, signum: int, _frame: Any) -> None:
        name = signal.Signals(signum).name
        self.received.append(name)
        if self.blocking:
            raise ReviewInterrupted(name)

    def install(self) -> None:
        for name in STOP_SIGNALS:
            previous = signal.signal(getattr(signal, name), self.handle)
            self._previous.setdefault(name, previous)

    def restore(self) -> None:
        for name, previous in self._previous.items():
            signal.signal(getattr(signal, name), previous)
        self._previous.clear()


class ReviewRun:
    """One review: load inputs, generate, parse, retry once, write every artifact."""

    def __init__(
        self,
        *,
        request: ReviewRequest,
        model: dict[str, Any],
        model_dir: Path,
        settings: EngineSettings,
        output_dir: Path,
        engine_factory: EngineFactory,
        signals: SignalState,
        marker_path: Path | None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.request = request
        self.model = model
        self.model_dir = model_dir
        self.settings = settings
        self.output_dir = output_dir
        self.engine_factory = engine_factory
        self.signals = signals
        self.marker_path = marker_path
        self.clock = clock
        self.files: dict[str, str] = {}
        self.receipt: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "kind": RECEIPT_KIND,
            "status": "RUNNING",
            "started_at": utc_now(),
            "model": model,
            "request": request.describe(),
            "prompt_sha256": request.prompt_sha256,
            "engine": settings.describe(),
            "llm_kwargs": settings.llm_kwargs(str(model_dir)),
            "sampling": {"temperature": TEMPERATURE, "max_tokens": settings.max_tokens},
            "prompt_format": PROMPT_FORMAT_ID,
            "validator": VALIDATOR_ID,
            "lane": {
                key: os.environ.get(f"COTCODEC_{key.upper()}")
                for key in ("git_sha", "source_sha256", "model_id", "expected_gpus")
            },
            "attempts": [],
            "replicates": [],
            "signals_received": signals.received,
        }

    def _write(self, name: str, data: bytes) -> str:
        atomic_write_bytes(self.output_dir / name, data)
        digest = sha256_bytes(data)
        self.files[name] = digest
        return digest

    def execute(self) -> int:
        self._write("prompt.txt", self.request.prompt.encode("utf-8"))
        self._write("schema.json", self.request.schema_text.encode("utf-8"))
        code = EXIT_ENGINE
        engine: ReviewEngine | None = None
        try:
            self.signals.blocking = True
            if self.signals.received:
                raise ReviewInterrupted(self.signals.received[-1])
            started = self.clock()
            engine = self.engine_factory(self.settings, self.model_dir)
            # Re-assert the handlers in case the engine replaced them while loading.
            self.signals.install()
            self.receipt["timings_s"] = {"engine_init": round(self.clock() - started, 3)}
            self.receipt["runtime"] = engine.facts()
            code = self._review(engine)
        except ReviewInterrupted as exc:
            self.receipt["status"] = "INTERRUPTED"
            self.receipt["error"] = f"stopped by {exc}; a review has no resumable state, resubmit"
            code = EXIT_SIGNAL
        except InputError as exc:
            self.receipt["status"] = "INPUT_ERROR"
            self.receipt["error"] = str(exc)
            code = EXIT_INPUT
        except Exception as exc:  # noqa: BLE001 - every engine failure is recorded
            self.receipt["status"] = "ENGINE_FAILED"
            self.receipt["error"] = f"{type(exc).__name__}: {exc}"[:2000]
            code = EXIT_ENGINE
        finally:
            self.signals.blocking = False
        if engine is not None and code != EXIT_SIGNAL:
            # After a signal the lane is waiting for the marker: do not spend time on it.
            self.receipt["engine_close"] = close_engine(engine, ENGINE_CLOSE_TIMEOUT_S)
        self._finish()
        return code

    def _attempt(
        self, engine: ReviewEngine, number: int, message: str, seeds: Sequence[int]
    ) -> list[Completion]:
        rendered = engine.render(message, thinking=self.settings.thinking)
        budget = len(rendered.token_ids) + self.settings.max_tokens
        if budget > self.settings.max_model_len:
            raise InputError(
                f"attempt {number}: {len(rendered.token_ids)} prompt tokens plus "
                f"{self.settings.max_tokens} output tokens exceed max_model_len "
                f"{self.settings.max_model_len}"
            )
        message_name = f"user-message-attempt-{number}.txt"
        self._write(message_name, message.encode("utf-8"))
        started = self.clock()
        completions = engine.generate(rendered, seeds=seeds, max_tokens=self.settings.max_tokens)
        elapsed = round(self.clock() - started, 3)
        if len(completions) != len(seeds):
            raise RuntimeError(f"the engine returned {len(completions)} of {len(seeds)} outputs")
        primary = completions[0]
        output_name = f"raw-output-attempt-{number}.txt"
        record = {
            "attempt": number,
            "seed": seeds[0],
            "user_message_file": message_name,
            "user_message_sha256": self.files[message_name],
            "rendered_prompt_sha256": sha256_bytes(rendered.text.encode("utf-8")),
            "prompt_token_count": len(rendered.token_ids),
            "prompt_token_ids_sha256": _ids_digest(rendered.token_ids),
            "output_file": output_name,
            "output_sha256": self._write(output_name, primary.text.encode("utf-8")),
            "output_token_count": len(primary.token_ids),
            "output_token_ids_sha256": _ids_digest(primary.token_ids),
            "finish_reason": primary.finish_reason,
            "generate_s": elapsed,
            "batch_size": len(seeds),
        }
        self.receipt["attempts"].append(record)
        return completions

    def _review(self, engine: ReviewEngine) -> int:
        seeds = list(self.settings.seeds)
        completions = self._attempt(engine, 1, user_message(self.request), seeds)
        primary = completions[0]
        for seed, completion in zip(seeds[1:], completions[1:], strict=True):
            name = f"replicate-seed-{seed}.txt"
            self.receipt["replicates"].append(
                {
                    "seed": seed,
                    "output_file": name,
                    "output_sha256": self._write(name, completion.text.encode("utf-8")),
                    "output_token_count": len(completion.token_ids),
                    "output_token_ids_sha256": _ids_digest(completion.token_ids),
                    "finish_reason": completion.finish_reason,
                    "identical_to_primary": completion.token_ids == primary.token_ids,
                }
            )
        self.receipt["replicates_identical"] = all(
            row["identical_to_primary"] for row in self.receipt["replicates"]
        )
        parsed, error = self._parse(primary, self.receipt["attempts"][0])
        if parsed is None:
            retry = self._attempt(
                engine, 2, user_message(self.request, retry_error=error), [seeds[0]]
            )[0]
            parsed, error = self._parse(retry, self.receipt["attempts"][1])
        final = self.receipt["attempts"][-1]
        self.receipt["output_sha256"] = final["output_sha256"]
        self.receipt["output_file"] = final["output_file"]
        if parsed is None:
            self.receipt["status"] = "PARSE_FAILED"
            self.receipt["error"] = error
            return EXIT_PARSE
        self.receipt["parsed_file"] = "parsed.json"
        self.receipt["parsed_sha256"] = self._write("parsed.json", canonical_json(parsed))
        self.receipt["status"] = "PARSED"
        return EXIT_OK

    def _parse(
        self, completion: Completion, record: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str | None]:
        try:
            value, extraction = parse_reply(
                completion.text,
                self.request.schema,
                thinking=self.settings.thinking,
                finish_reason=completion.finish_reason,
            )
        except ParseFailure as exc:
            record["parse"] = {"ok": False, "error": str(exc)}
            return None, str(exc)
        record["parse"] = {"ok": True, "extraction": extraction}
        return value, None

    def _finish(self) -> None:
        self.receipt["finished_at"] = utc_now()
        self.receipt["signals_received"] = list(self.signals.received)
        self.receipt["files"] = dict(sorted(self.files.items()))
        receipt_bytes = canonical_json(self.receipt)
        atomic_write_bytes(self.output_dir / "receipt.json", receipt_bytes)
        sums = {**self.files, "receipt.json": sha256_bytes(receipt_bytes)}
        atomic_write_bytes(
            self.output_dir / "SHA256SUMS",
            "".join(f"{digest}  {name}\n" for name, digest in sorted(sums.items())).encode(),
        )
        if self.signals.received and self.marker_path is not None:
            # The lane's signal contract (docs/operations.md): save first, then the marker.
            lines = [f"trigger={name}" for name in dict.fromkeys(self.signals.received)]
            lines += [
                f"written_at={utc_now()}",
                f"kind={RECEIPT_KIND}",
                f"status={self.receipt['status']}",
                f"receipt_sha256={sums['receipt.json']}",
            ]
            atomic_write_bytes(self.marker_path, ("\n".join(lines) + "\n").encode())


def _ids_digest(ids: Sequence[int]) -> str:
    return sha256_bytes(json.dumps(list(ids), separators=(",", ":")).encode())


# ---------------------------------------------------------------------------
# Lane manifest (host side)
# ---------------------------------------------------------------------------


def read_build_receipt(path: Path) -> dict[str, str]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("kind") != "vllm-overlay-build":
        raise InputError("the build receipt is not a vLLM overlay build receipt")
    values = {
        "image_id": str(receipt.get("overlay_image_id")),
        "git_sha": str(receipt.get("git_sha")),
        "source_sha256": str(receipt.get("source_sha256")),
        "variant": str(receipt.get("variant")),
        "vllm_version": str(receipt.get("vllm_version")),
    }
    if not IMAGE_ID_RE.fullmatch(values["image_id"]):
        raise InputError("build receipt overlay_image_id is malformed")
    if not GIT_RE.fullmatch(values["git_sha"]) or not SHA_RE.fullmatch(values["source_sha256"]):
        raise InputError("build receipt git_sha or source_sha256 is malformed")
    if values["variant"] != "cu129":
        raise InputError("the reviewer runs on the validated cu129 overlay only")
    return values


def registry_revision(model_id: str) -> str:
    import yaml

    registry = yaml.safe_load((PROJECT_ROOT / "models/registry.yaml").read_text(encoding="utf-8"))
    entry = registry["models"].get(model_id)
    if entry is None:
        raise InputError(f"{model_id} is not in models/registry.yaml")
    if entry.get("license") != "apache-2.0" or entry.get("trust_remote_code") is not False:
        raise InputError(f"{model_id} is not a permissively licensed, no-remote-code model")
    return str(entry["revision"])


def model_binding(model_id: str, model_cache_host: str) -> dict[str, str]:
    if model_id not in REVIEWER_MODELS:
        raise InputError(f"reviewer models are {sorted(REVIEWER_MODELS)}")
    path = Path(model_cache_host) / "cotcodec-receipts" / f"{model_id}.json"
    data = path.read_bytes()
    receipt = json.loads(data)
    revision = registry_revision(model_id)
    if receipt.get("model_id") != model_id or receipt.get("revision") != revision:
        raise InputError(f"{path.name} does not match the registry revision {revision}")
    if receipt.get("mode") != "full" or receipt.get("publication_eligible") is not True:
        raise InputError(f"{path.name} is not a full, publication-eligible receipt")
    return {
        "cache_host_path": model_cache_host,
        "model_id": model_id,
        "revision": revision,
        "receipt_sha256": sha256_bytes(data),
        "artifact_root_sha256": str(receipt["artifact_root_sha256"]),
    }


def render_manifest(
    *,
    name: str,
    build: Mapping[str, str],
    request_host_path: str,
    request_sha256: str,
    request_size: int,
    request_revision: str,
    request_license: str,
    model: Mapping[str, str],
    run_root: str,
    minutes: int,
    cpus: int,
    memory_gb: int | None,
    settings: EngineSettings,
) -> dict[str, Any]:
    if not NAME_RE.fullmatch(name):
        raise InputError("name must be a lowercase kebab-case slug of at most 40 characters")
    if not GIT_RE.fullmatch(request_revision):
        raise InputError("request revision must be a 40-hex commit")
    if not LICENSE_RE.fullmatch(request_license):
        raise InputError("request license must be a safe SPDX-style identifier")
    model_id = model["model_id"]
    gpus = settings.tensor_parallel_size
    hours = gpus * minutes / 60
    cap = round(hours, 6)
    if cap < hours:
        cap = round(cap + 1e-6, 6)
    command = [
        "python",
        "scripts/run_open_weight_review.py",
        "run",
        "--evidence",
        LANE_EVIDENCE_PATH,
        "--expected-evidence-sha256",
        request_sha256,
        "--model-dir",
        f"{LANE_MODEL_ROOT}/{model_id}",
        "--model-receipt",
        f"{LANE_RECEIPT_ROOT}/{model_id}.json",
        "--expected-model-receipt-sha256",
        model["receipt_sha256"],
        "--output-dir",
        LANE_OUTPUT_DIR,
        "--tensor-parallel-size",
        str(gpus),
        "--max-model-len",
        str(settings.max_model_len),
        "--max-tokens",
        str(settings.max_tokens),
        "--gpu-memory-utilization",
        str(settings.gpu_memory_utilization),
        "--thinking",
        "on" if settings.thinking else "off",
    ]
    if settings.enforce_eager:
        command.append("--enforce-eager")
    command += ["--seeds", *(str(seed) for seed in settings.seeds)]
    return {
        "runtime": LANE_RUNTIME,
        "name": name,
        "image_id": build["image_id"],
        "git_sha": build["git_sha"],
        "source_sha256": build["source_sha256"],
        "run_root": run_root,
        "container_profile": "vllm",
        "resources": {
            "gpu_type": "h100",
            "gpus": gpus,
            "cpus": cpus,
            "memory_gb": memory_gb or REVIEWER_MODELS[model_id]["memory_gb"],
            "minutes": minutes,
        },
        "budget": {"max_gpu_hours": cap},
        "randomness_contract": "assignment-seed-matrix",
        "seeds": list(settings.seeds),
        "seed_binding": {"flag": "--seeds"},
        "model": dict(model),
        "study_artifact": {
            "source_id": f"owr-request-{request_sha256[:12]}",
            "revision": request_revision,
            "license": request_license,
            "host_path": request_host_path,
            "sha256": request_sha256,
            "size_bytes": request_size,
        },
        "command": command,
    }


def checkout_head() -> str:
    completed = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify_output(directory: Path) -> dict[str, Any]:
    receipt_path = directory / "receipt.json"
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    problems: list[str] = []
    sums: dict[str, str] = {}
    for line in (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        sums[name] = digest
    expected = {**receipt.get("files", {}), "receipt.json": sha256_bytes(receipt_bytes)}
    if sums != expected:
        problems.append("SHA256SUMS differs from the receipt's file list")
    for name, digest in sums.items():
        path = directory / name
        if not path.is_file() or sha256_file(path) != digest:
            problems.append(f"{name} is missing or differs from its SHA-256")
    for record in receipt.get("attempts", []):
        if receipt.get("files", {}).get(record.get("output_file")) != record.get("output_sha256"):
            problems.append(f"attempt {record.get('attempt')} output hash is inconsistent")
    return {
        "ok": not problems,
        "problems": problems,
        "status": receipt.get("status"),
        "model_id": receipt.get("model", {}).get("model_id"),
        "revision": receipt.get("model", {}).get("revision"),
        "model_receipt_sha256": receipt.get("model", {}).get("receipt_sha256"),
        "vllm_version": receipt.get("runtime", {}).get("vllm_version"),
        "prompt_sha256": receipt.get("prompt_sha256"),
        "output_sha256": receipt.get("output_sha256"),
        "parsed_sha256": receipt.get("parsed_sha256"),
        "replicates_identical": receipt.get("replicates_identical"),
        "receipt_sha256": sha256_bytes(receipt_bytes),
    }


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


def doctor(settings: EngineSettings) -> dict[str, Any]:
    """Check the installed vLLM accepts every LLM and SamplingParams argument the run passes."""

    import dataclasses
    import inspect

    import transformers
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.engine.arg_utils import EngineArgs
    from vllm.inputs import TokensPrompt

    explicit = set(inspect.signature(LLM.__init__).parameters)
    engine_fields = {item.name for item in dataclasses.fields(EngineArgs)}
    missing = sorted(
        key
        for key in settings.llm_kwargs("/model")
        if key not in explicit and key not in engine_fields
    )
    sampling_error = None
    try:
        SamplingParams(**settings.sampling(settings.primary_seed))
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        sampling_error = f"{type(exc).__name__}: {exc}"
    TokensPrompt(prompt_token_ids=[1, 2, 3])
    return {
        "pass": not missing and sampling_error is None,
        "vllm_version": vllm.__version__,
        "transformers_version": transformers.__version__,
        "missing_llm_arguments": missing,
        "sampling_error": sampling_error,
        "llm_kwargs": sorted(settings.llm_kwargs("/model")),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _settings(args: argparse.Namespace) -> EngineSettings:
    return EngineSettings(
        tensor_parallel_size=args.tensor_parallel_size,
        max_model_len=args.max_model_len,
        max_tokens=args.max_tokens,
        gpu_memory_utilization=args.gpu_memory_utilization,
        enforce_eager=args.enforce_eager,
        thinking=args.thinking == "on",
        seeds=tuple(args.seeds),
    )


def _add_engine_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--max-model-len", type=int, default=DEFAULT_MAX_MODEL_LEN)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--gpu-memory-utilization", type=float, default=DEFAULT_GPU_MEMORY_UTILIZATION
    )
    parser.add_argument("--enforce-eager", action="store_true")
    parser.add_argument("--thinking", choices=("on", "off"), default="on")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))


def _add_request_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--evidence", type=Path, help="a packed request bundle")
    parser.add_argument("--expected-evidence-sha256")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--schema-file", type=Path)
    parser.add_argument("--label", default="direct")


def _request(args: argparse.Namespace) -> ReviewRequest:
    if args.evidence is not None:
        if args.prompt_file is not None or args.schema_file is not None:
            raise InputError("give --evidence or --prompt-file/--schema-file, not both")
        if args.expected_evidence_sha256 is None:
            raise InputError("--evidence needs --expected-evidence-sha256")
        return load_request_bundle(args.evidence, args.expected_evidence_sha256)
    if args.prompt_file is None or args.schema_file is None:
        raise InputError("give --evidence, or both --prompt-file and --schema-file")
    return request_from_files(args.prompt_file, args.schema_file, args.label)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)

    pack = sub.add_parser("pack", allow_abbrev=False, help="bundle a prompt and a schema")
    pack.add_argument("--prompt-file", type=Path, required=True)
    pack.add_argument("--schema-file", type=Path, required=True)
    pack.add_argument("--label", required=True)
    pack.add_argument("--output", type=Path, required=True)

    plan = sub.add_parser("plan", allow_abbrev=False, help="print the resolved settings")
    _add_request_options(plan)
    _add_engine_options(plan)

    doc = sub.add_parser("doctor", allow_abbrev=False, help="check the vLLM API (CPU)")
    _add_engine_options(doc)

    run = sub.add_parser("run", allow_abbrev=False, help="generate one review")
    _add_request_options(run)
    run.add_argument("--model-dir", type=Path, required=True)
    run.add_argument("--model-receipt", type=Path, required=True)
    run.add_argument("--expected-model-receipt-sha256", required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    _add_engine_options(run)

    manifest = sub.add_parser("manifest", allow_abbrev=False, help="render a lane manifest")
    manifest.add_argument("--build-receipt", type=Path, required=True)
    manifest.add_argument("--request", type=Path, required=True)
    manifest.add_argument("--model-id", choices=sorted(REVIEWER_MODELS), required=True)
    manifest.add_argument("--model-cache-host", default=DEFAULT_MODEL_CACHE_HOST)
    manifest.add_argument("--name", required=True)
    manifest.add_argument("--run-root", required=True)
    manifest.add_argument("--minutes", type=int, required=True)
    manifest.add_argument("--cpus", type=int, default=16)
    manifest.add_argument("--memory-gb", type=int)
    manifest.add_argument("--request-revision", help="commit the prompt was made from")
    manifest.add_argument("--request-license", default=DEFAULT_REQUEST_LICENSE)
    manifest.add_argument("--output", type=Path, required=True)
    _add_engine_options(manifest)

    verify = sub.add_parser("verify", allow_abbrev=False, help="re-hash a review directory")
    verify.add_argument("--output-dir", type=Path, required=True)
    return parser


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _exclusive_write(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def command_pack(args: argparse.Namespace) -> int:
    request = request_from_files(args.prompt_file, args.schema_file, args.label)
    data = canonical_json(request_bundle(request))
    _exclusive_write(args.output, data)
    _print(
        {
            "output": str(args.output),
            "sha256": sha256_bytes(data),
            "size_bytes": len(data),
            "prompt_sha256": request.prompt_sha256,
            "schema_sha256": request.schema_sha256,
        }
    )
    return EXIT_OK


def command_plan(args: argparse.Namespace) -> int:
    request = _request(args)
    settings = _settings(args)
    _print(
        {
            "request": request.describe(),
            "engine": settings.describe(),
            "llm_kwargs": settings.llm_kwargs("<model-dir>"),
            "sampling": [settings.sampling(seed) for seed in settings.seeds],
            "user_message_sha256": sha256_bytes(user_message(request).encode("utf-8")),
            "prompt_format": PROMPT_FORMAT_ID,
            "validator": VALIDATOR_ID,
        }
    )
    return EXIT_OK


def command_run(
    args: argparse.Namespace,
    *,
    engine_factory: EngineFactory = VllmReviewEngine,
    signals: SignalState | None = None,
) -> int:
    # The handlers stay installed until the process exits: as PID 1 in the lane
    # container, a default disposition would ignore the lane's USR1 and TERM.
    signals = signals or SignalState()
    signals.install()
    return _run(args, engine_factory=engine_factory, signals=signals)


def _run(args: argparse.Namespace, *, engine_factory: EngineFactory, signals: SignalState) -> int:
    settings = _settings(args)
    expected_gpus = os.environ.get("COTCODEC_EXPECTED_GPUS")
    if expected_gpus is not None and int(expected_gpus) != settings.tensor_parallel_size:
        raise InputError(
            f"the lane allocated {expected_gpus} GPUs for tensor parallel size "
            f"{settings.tensor_parallel_size}"
        )
    request = _request(args)
    model = load_model_receipt(
        args.model_receipt, args.expected_model_receipt_sha256, args.model_dir
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    review = ReviewRun(
        request=request,
        model=model,
        model_dir=args.model_dir,
        settings=settings,
        output_dir=args.output_dir,
        engine_factory=engine_factory,
        signals=signals,
        marker_path=Path(marker) if marker else None,
    )
    code = review.execute()
    _print(
        {
            "status": review.receipt["status"],
            "output_dir": str(args.output_dir),
            "receipt_sha256": sha256_file(args.output_dir / "receipt.json"),
            "error": review.receipt.get("error"),
        }
    )
    return code


def command_manifest(args: argparse.Namespace) -> int:
    import yaml

    from scripts.submit_docker_research_job import validate_manifest

    build = read_build_receipt(args.build_receipt)
    head = checkout_head()
    if head != build["git_sha"]:
        raise InputError(
            f"the image was built from {build['git_sha']}, this checkout is at {head}; "
            "render from a clean clone of the image's commit"
        )
    request = load_request_bundle(args.request, None)
    request_data = args.request.read_bytes()
    settings = _settings(args)
    manifest = render_manifest(
        name=args.name,
        build=build,
        request_host_path=str(args.request.resolve()),
        request_sha256=sha256_bytes(request_data),
        request_size=len(request_data),
        request_revision=args.request_revision or build["git_sha"],
        request_license=args.request_license,
        model=model_binding(args.model_id, args.model_cache_host),
        run_root=args.run_root,
        minutes=args.minutes,
        cpus=args.cpus,
        memory_gb=args.memory_gb,
        settings=settings,
    )
    validate_manifest(dict(manifest), verify_claim_files=False)
    header = (
        "# Rendered by scripts/run_open_weight_review.py manifest\n"
        f"# build receipt sha256 {sha256_file(args.build_receipt)}\n"
        f"# request label {request.label}, prompt sha256 {request.prompt_sha256}\n"
    )
    _exclusive_write(
        args.output, (header + yaml.safe_dump(manifest, sort_keys=False)).encode("utf-8")
    )
    _print(
        {
            "output": str(args.output),
            "name": manifest["name"],
            "gpu_hours_cap": manifest["budget"]["max_gpu_hours"],
        }
    )
    return EXIT_OK


def main(
    argv: Sequence[str] | None = None,
    *,
    engine_factory: EngineFactory = VllmReviewEngine,
    signals: SignalState | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "pack":
            return command_pack(args)
        if args.command == "plan":
            return command_plan(args)
        if args.command == "doctor":
            report = doctor(_settings(args))
            _print(report)
            return EXIT_OK if report["pass"] else EXIT_INPUT
        if args.command == "run":
            return command_run(args, engine_factory=engine_factory, signals=signals)
        if args.command == "manifest":
            return command_manifest(args)
        report = verify_output(args.output_dir)
        _print(report)
        return EXIT_OK if report["ok"] else EXIT_INPUT
    except (InputError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return EXIT_INPUT


def entrypoint(
    argv: Sequence[str] | None = None, *, engine_factory: EngineFactory = VllmReviewEngine
) -> None:
    """Run the CLI and leave with ``os._exit``, never through interpreter shutdown.

    Every output is written and closed before ``main`` returns. Interpreter
    shutdown would join vLLM's threads and processes, which hung smoke job 617
    for the rest of its allocation; as PID 1 the exit ends the container and
    with it every process the engine started.
    """

    code = main(argv, engine_factory=engine_factory)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    entrypoint()
