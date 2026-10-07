"""Model-rater runner for the Q2 checker-mutation audit (decisions D9 and D23).

Two raters answer every audit packet once (``raters.RATERS``):

``anthropic`` (runs where the API key is; needs network)
    The Anthropic Messages API, model ``ANTHROPIC["model"]``. The model id the
    API names is recorded before the run (``GET /v1/models/{id}``) and from
    every response. The request carries no sampling parameter: the model
    rejects ``temperature``, ``top_p`` and ``top_k`` and its thinking cannot be
    disabled, so its sampling is the API's fixed default at the registered
    effort and ``max_tokens``. Only packet text and page renders of the
    candidate and starting files are sent; those files are public OSWorld
    task files (Apache-2.0 task configs, apache-2.0 file-cache card) and
    edits of them.
``open`` (runs in the docker-research lane, ``container_profile: vllm``)
    The self-hosted open-weight rater (decision D27): Qwen3.6-35B-A3B at a
    pinned Hugging Face revision, image input enabled, verified against its
    model receipt by the lane, served by ``vllm serve`` on 127.0.0.1 inside
    the network-less container with fixed engine flags on one H100; greedy
    decoding (temperature 0, top_p 1, seed 42), ``max_tokens`` 256, thinking
    off through the chat template. On the lane's checkpoint signal (USR1) or
    TERM it sends nothing more, gives the requests in flight
    ``STOP_GRACE_S`` (a second signal ends the wait), stops the engine,
    writes its receipt and leaves with ``os._exit``, so the container ends
    before the job's limit; an item the stop interrupted gets no record and
    stays ``unrated`` for the rerun.
``args-doctor`` (CPU, inside the vLLM image)
    vLLM's own parsers accept the engine argv and the request payload.
``models`` (anthropic)
    Record the Anthropic model object only.
``export-harness`` / ``ingest-harness`` (decision D25: the Claude rater through
the Claude Code agent harness while no valid API key exists)
    ``export-harness`` writes one blind file per item (``<item>.txt``: the
    fixed rater instructions and the packet's parts in ``packet_parts``
    order, each page image named by its file) with its page images
    (``<item>.pages/``), and ``index.json``, the item ids only, in the rater's
    seeded order. Nothing else goes into that directory; the export manifest
    (digests of every exported file and of the request body rebuilt from the
    packet) is written beside it. ``ingest-harness`` reads the external
    rater's JSON list of ``{item_id, answer, reason, model_id}``, applies the
    registered first-token rule to ``answer``, refuses an item outside the
    export, a second record for an item and a model id other than
    ``ANTHROPIC["model"]``, and writes ``calls.jsonl`` in the shared call
    schema plus ``receipt.json``, with the SHA-256 of every exported file, of
    the answers file and of each record. The answers may also come as the
    rater workflow's wrapper ``{rater, model_id, items}``. Sampling cannot be
    fixed on this path; the receipt says so.
``export-isolated`` / ``ingest-isolated`` (decisions D25 and D27: one agent per
item, each confined to its own directory)
    ``export-isolated`` writes each item into its own fresh directory
    ``<iso-root>/<item>/`` holding only ``packet.txt`` (the fixed instructions
    and the packet's parts) and ``pages/`` (its page images): no index, no
    other item, no label. The manifest (item ids in the rater's seeded order,
    the digest of every file and of each directory) is written outside the
    root. ``ingest-isolated`` takes one answer per item and the harness
    transcript of the agent that gave it; it re-hashes every item directory,
    takes the model id from the transcript, and applies the transcript audit
    (``audit_transcript``): a shell call, a tool that is not a read-only tool
    of the agent harness, or a path outside the item's directory voids that
    item's answer to ``unsure`` (``isolation_void``). Each call record keeps
    the transcript's SHA-256.

Rules shared by both raters (preregistration section 9):

* one call per rater per item: an item with any record in ``calls.jsonl`` is
  never sent again, so a resumed run skips it;
* retries only on transport errors (connection failure, timeout, HTTP 408,
  409, 429, 500, 502, 503, 504, 529), at most ``MAX_TRANSPORT_RETRIES``;
  after the last one the item is ``transport_exhausted``;
* the answer is the first word of the reply (``raters.parse_first_token``); a
  refusal, an empty or unparseable reply, a timeout, an exhausted transport,
  a request the provider rejected (HTTP 400 or 413, for example a packet
  over the context window) or a 200 response whose body is not the
  provider's JSON (``malformed_response``, for example a proxy error page;
  its bytes are saved and hashed like any response) is ``unsure``; an
  authentication, permission or unknown-model error stops the run instead
  (nothing is rated);
* ``receipt.json`` is written however the run ends (``try``/``finally``);
* every request and response is hashed: ``request_sha256`` is the SHA-256 of
  the exact bytes sent, ``body_sha256`` of the canonical request body (which
  ``request_body`` rebuilds from the packet), ``response_sha256`` of the
  exact bytes received. ``receipt.json`` records the code, prompt, packet
  file, model identity and parameters, the outcome counts and the SHA-256 of
  ``calls.jsonl``. Raw responses stay in ``responses/`` beside it (they may
  quote document text) and are never committed.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.q2_mutation.raters import (
    RATER_PROMPT_V1,
    RATERS,
    answer_for,
    parse_first_token,
    rater_order,
)

RUNNER_VERSION = "q2m-rater-runner-v1"
PACKET_SCHEMA = "q2m-audit-packet-v1"
CALL_SCHEMA = "q2m-rater-call-v1"
ANSWER_LINE = (
    "Answer with exactly one of: accept, reject, unsure. Then give one sentence of reasons."
)
MAX_TRANSPORT_RETRIES = 3
BACKOFF_S = (5.0, 20.0, 60.0)
TRANSPORT_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504, 529})
# Errors that mean the run itself cannot rate anything: stop, rate nothing.
FATAL_STATUS = frozenset({401, 403, 404})
ORDER_SEED = 42
# After a stop signal: how long the requests in flight may still finish, and
# how long the engine gets to exit on SIGTERM before SIGKILL. Together they
# stay well inside the lane's 120 s USR1 window and its 180 s lead.
STOP_GRACE_S = 60.0
ENGINE_STOP_S = 30.0

ANTHROPIC: Mapping[str, Any] = {
    "rater_id": "model-rater-anthropic",
    "model": "claude-opus-5-5",
    "max_tokens": 16000,
    "effort": "high",
    "timeout_s": 600.0,
    "workers": 4,
}
# Decision D27: Qwen3.6-35B-A3B replaces Qwen3.5-9B (the dev smokes' rater).
# vLLM 0.31.0 resolves its architecture, Qwen3_5MoeForConditionalGeneration, as
# a multimodal model with image input (Qwen3VLMultiModalProcessor); the
# gauntlet reviewer (Slurm 640) served it text-only at TP=1.
OPEN_WEIGHT: Mapping[str, Any] = {
    "rater_id": "model-rater-open-weight",
    "model_id": "qwen3.6-35b-a3b",
    "repo_id": "Qwen/Qwen3.6-35B-A3B",
    "revision": "995ad96eacd98c81ed38be0c5b274b04031597b0",
    "receipt_sha256": "18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9",
    "artifact_root_sha256": "8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b",
    "served_name": "q2m-rater",
    "host": "127.0.0.1",
    "port": 8000,
    "temperature": 0.0,
    "top_p": 1.0,
    "seed": 42,
    "max_tokens": 256,
    "enable_thinking": False,
    "timeout_s": 600.0,
    "workers": 8,
    "ready_timeout_s": 900.0,
}
# ``vllm serve`` flags, in this order (v0.31.0, cu129 overlay; the throughput
# probes validated this image and the image-limit form). The 35B-A3B weights
# take about 66 GiB of one H100, so memory utilization is 0.95 (as for the
# gauntlet reviewer, Slurm 640/655: KV cache 385,211 tokens text-only) and at
# most 8 sequences run at once.
ENGINE_FLAGS: tuple[tuple[str, Any], ...] = (
    ("dtype", "bfloat16"),
    ("seed", 42),
    ("tensor_parallel_size", 1),
    ("max_model_len", 131072),
    ("gpu_memory_utilization", 0.95),
    ("max_num_seqs", 8),
    ("enable_prefix_caching", False),
    ("generation_config", "vllm"),
    (
        "limit_mm_per_prompt",
        {"image": {"count": 40, "width": 1700, "height": 2200}, "video": 0},
    ),
)
ENGINE_ENV = {
    "VLLM_NO_USAGE_STATS": "1",
    "DO_NOT_TRACK": "1",
    "VLLM_DO_NOT_TRACK": "1",
    "VLLM_HOST_IP": "127.0.0.1",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "PYTHONUNBUFFERED": "1",
    "VLLM_LOGGING_LEVEL": "INFO",
    "VLLM_ENABLE_CUDA_COMPATIBILITY": "0",
}
CACHE_DIRS = {
    "HOME": "home",
    "XDG_CACHE_HOME": "xdg-cache",
    "XDG_CONFIG_HOME": "xdg-config",
    "VLLM_CACHE_ROOT": "vllm",
    "VLLM_CONFIG_ROOT": "vllm-config",
    "VLLM_RPC_BASE_PATH": "rpc",
    "TRITON_CACHE_DIR": "triton",
    "TORCHINDUCTOR_CACHE_DIR": "inductor",
    "TORCH_HOME": "torch",
    "CUDA_CACHE_PATH": "cuda",
    "FLASHINFER_WORKSPACE_BASE": "flashinfer",
    "HF_HOME": "hf",
    "TMPDIR": "tmp",
}
MODEL_ROOT = "/model-cache/cotcodec-models"


def utc_now() -> str:
    # timezone.utc, not datetime.UTC: the manifest renderer imports this on
    # the host's Python 3.10.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: UP017


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def code_digests() -> dict[str, str]:
    here = Path(__file__).resolve().parent
    return {name: sha256_file(here / name) for name in ("raters.py", "rater_runner.py")}


# --- packets ------------------------------------------------------------------


def load_packets(path: Path, expected_sha256: str | None = None) -> list[dict[str, Any]]:
    """Packets of one audit (JSONL, one ``q2m-audit-packet-v1`` object per line)."""
    if expected_sha256 is not None and sha256_file(path) != expected_sha256:
        raise SystemExit(f"{path}: SHA-256 differs from the expected packet digest")
    packets = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        packet = json.loads(line)
        if packet.get("schema") != PACKET_SCHEMA:
            raise SystemExit(f"{path}:{number}: not a {PACKET_SCHEMA} packet")
        if packet["item_id"] in seen:
            raise SystemExit(f"{path}:{number}: duplicate item {packet['item_id']}")
        seen.add(packet["item_id"])
        packets.append(packet)
    return packets


def packet_parts(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The packet as an ordered list of text and image parts (both raters see this)."""
    parts: list[dict[str, Any]] = []

    def text(value: str) -> None:
        if parts and parts[-1]["type"] == "text":
            parts[-1]["text"] += value
        else:
            parts.append({"type": "text", "text": value})

    def pages(kind: str, vm_path: str, entries: Sequence[Mapping[str, Any]]) -> None:
        for page in entries:
            text(f"[{kind} {vm_path}, rendered page {page['page']} of {page['of']}]\n")
            parts.append(
                {
                    "type": "image",
                    "media_type": page["media_type"],
                    "data_b64": page["data_b64"],
                    "sha256": page["sha256"],
                }
            )

    text(f"Task instruction:\n{packet['instruction']}\n\n")
    initial = packet.get("initial_files") or []
    text(f"Starting files ({len(initial)}):\n")
    for entry in initial:
        text(f"--- Starting file {entry['vm_path']} (structure listing) ---\n")
        text("\n".join(entry.get("structure") or []) + "\n")
        for note in entry.get("notes") or []:
            text(f"({note})\n")
        pages("Starting file", entry["vm_path"], entry.get("pages") or [])
    files = (packet.get("candidate") or {}).get("files") or []
    text(f"\nEnd-state files ({len(files)}):\n")
    for entry in files:
        text(f"--- End-state file {entry['vm_path']} (structure listing) ---\n")
        text("\n".join(entry.get("structure") or []) + "\n")
        text(f"--- End-state file {entry['vm_path']} (changes from the starting file) ---\n")
        text("\n".join(entry.get("diff_vs_initial") or []) + "\n")
        for note in entry.get("notes") or []:
            text(f"({note})\n")
        pages("End-state file", entry["vm_path"], entry.get("pages") or [])
    text("\n" + ANSWER_LINE)
    return parts


def anthropic_body(packet: Mapping[str, Any]) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for part in packet_parts(packet):
        if part["type"] == "text":
            content.append({"type": "text", "text": part["text"]})
        else:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": part["media_type"],
                        "data": part["data_b64"],
                    },
                }
            )
    return {
        "model": ANTHROPIC["model"],
        "max_tokens": ANTHROPIC["max_tokens"],
        "system": RATER_PROMPT_V1,
        "messages": [{"role": "user", "content": content}],
        "output_config": {"effort": ANTHROPIC["effort"]},
    }


def openai_body(packet: Mapping[str, Any]) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for part in packet_parts(packet):
        if part["type"] == "text":
            content.append({"type": "text", "text": part["text"]})
        else:
            url = f"data:{part['media_type']};base64,{part['data_b64']}"
            content.append({"type": "image_url", "image_url": {"url": url}})
    return {
        "model": OPEN_WEIGHT["served_name"],
        "messages": [
            {"role": "system", "content": RATER_PROMPT_V1},
            {"role": "user", "content": content},
        ],
        "temperature": OPEN_WEIGHT["temperature"],
        "top_p": OPEN_WEIGHT["top_p"],
        "max_tokens": OPEN_WEIGHT["max_tokens"],
        "seed": OPEN_WEIGHT["seed"],
        "chat_template_kwargs": {"enable_thinking": OPEN_WEIGHT["enable_thinking"]},
        "stream": False,
    }


def request_body(rater_id: str, packet: Mapping[str, Any]) -> dict[str, Any]:
    if rater_id == ANTHROPIC["rater_id"]:
        return anthropic_body(packet)
    if rater_id == OPEN_WEIGHT["rater_id"]:
        return openai_body(packet)
    raise ValueError(f"unknown rater {rater_id!r}")


# --- calls --------------------------------------------------------------------


class FatalRunError(RuntimeError):
    """The run cannot rate anything (authentication, permission, unknown model)."""


@dataclass
class Attempt:
    """What one send produced (transport problems are kept apart from replies)."""

    status: int | None = None
    request_bytes: bytes | None = None
    response_bytes: bytes | None = None
    transport_error: str | None = None
    timeout: bool = False
    seconds: float = 0.0


@dataclass
class Reply:
    # ok | refusal | request_rejected | timeout | transport_exhausted | malformed_response
    outcome: str
    text: str | None = None
    model: str | None = None
    stop_reason: str | None = None
    usage: Mapping[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def is_transport(attempt: Attempt) -> bool:
    return attempt.transport_error is not None or attempt.status in TRANSPORT_STATUS


def call_with_retries(
    send: Callable[[], Attempt],
    *,
    sleep: Callable[[float], None] = time.sleep,
    retries: int = MAX_TRANSPORT_RETRIES,
    stopping: Callable[[], bool] = lambda: False,
) -> tuple[Attempt, list[dict[str, Any]]]:
    """Send once, and again only after a transport error, at most ``retries`` times.

    No retry starts once ``stopping()`` is true (the run was told to stop).
    """
    log: list[dict[str, Any]] = []
    attempt = Attempt()
    for number in range(retries + 1):
        attempt = send()
        log.append(
            {
                "n": number + 1,
                "status": attempt.status,
                "transport_error": attempt.transport_error,
                "timeout": attempt.timeout,
                "seconds": round(attempt.seconds, 3),
            }
        )
        if attempt.status in FATAL_STATUS:
            raise FatalRunError(f"HTTP {attempt.status}: the run cannot rate items")
        if not is_transport(attempt) or number == retries or stopping():
            break
        sleep(BACKOFF_S[min(number, len(BACKOFF_S) - 1)])
        if stopping():
            break
    return attempt, log


def _json_object(data: bytes) -> dict[str, Any] | None:
    """The response body as a JSON object, or None when it is not one."""
    try:
        body = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        return None
    return body if isinstance(body, dict) else None


def malformed(error: str) -> Reply:
    return Reply("malformed_response", extra={"error": error})


def anthropic_reply(attempt: Attempt) -> Reply:
    if is_transport(attempt):
        return Reply("timeout" if attempt.timeout else "transport_exhausted")
    if attempt.status != 200 or attempt.response_bytes is None:
        return Reply("request_rejected", extra={"status": attempt.status})
    body = _json_object(attempt.response_bytes)
    if body is None or not isinstance(body.get("content", []), list):
        return malformed("the 200 response body is not a Messages API JSON object")
    blocks = [b for b in body.get("content", []) if isinstance(b, dict)]
    texts = [str(b.get("text", "")) for b in blocks if b.get("type") == "text"]
    stop = body.get("stop_reason")
    reply = Reply(
        "ok",
        text="".join(texts),
        model=body.get("model"),
        stop_reason=stop,
        usage=body.get("usage"),
        extra={"stop_details": body.get("stop_details"), "message_id": body.get("id")},
    )
    if stop == "refusal":
        reply.outcome = "refusal"
    return reply


def openai_reply(attempt: Attempt) -> Reply:
    if is_transport(attempt):
        return Reply("timeout" if attempt.timeout else "transport_exhausted")
    if attempt.status != 200 or attempt.response_bytes is None:
        return Reply("request_rejected", extra={"status": attempt.status})
    body = _json_object(attempt.response_bytes)
    choices = body.get("choices") if body is not None else None
    if body is None or not isinstance(choices, list) or not choices:
        return malformed("the 200 response body is not a chat completion JSON object")
    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        return malformed("the reply content is not a string")
    return Reply(
        "ok",
        text=content,
        model=body.get("model"),
        stop_reason=choice.get("finish_reason"),
        usage=body.get("usage"),
    )


def call_record(
    rater_id: str,
    item_id: str,
    order_index: int,
    body: Mapping[str, Any],
    attempt: Attempt,
    attempts: list[dict[str, Any]],
    reply: Reply,
    started: str,
) -> dict[str, Any]:
    answer, status = answer_for(reply.outcome, reply.text)
    return {
        "schema": CALL_SCHEMA,
        "rater_id": rater_id,
        "item_id": item_id,
        "order_index": order_index,
        "model_requested": body.get("model"),
        "model_returned": reply.model,
        "body_sha256": sha256_bytes(canonical_bytes(body)),
        "request_sha256": (
            sha256_bytes(attempt.request_bytes) if attempt.request_bytes is not None else None
        ),
        "response_sha256": (
            sha256_bytes(attempt.response_bytes) if attempt.response_bytes is not None else None
        ),
        "http_status": attempt.status,
        "outcome": reply.outcome,
        "answer": answer,
        "status": status,
        "stop_reason": reply.stop_reason,
        "usage": reply.usage,
        "extra": reply.extra,
        "attempts": attempts,
        "started_at": started,
        "finished_at": utc_now(),
    }


CALL_KEYS = frozenset({"schema", "rater_id", "item_id", "answer", "status", "outcome"})


def read_calls(path: Path) -> dict[str, dict[str, Any]]:
    """The call records of one ``calls.jsonl``, keyed by item.

    A file holds one record per item ("one call per rater per item"): a second
    record for an item, a record without the call schema's keys (a missing
    ``rater_id`` included) or of another schema is refused, never resolved by
    keeping one of them.
    """
    if not path.is_file():
        return {}
    calls: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not set(row) >= CALL_KEYS:
            raise SystemExit(f"{path}:{number}: not a call record (keys {sorted(CALL_KEYS)})")
        if row["schema"] != CALL_SCHEMA:
            raise SystemExit(f"{path}:{number}: schema {row['schema']!r}, not {CALL_SCHEMA}")
        if not row["rater_id"]:
            raise SystemExit(f"{path}:{number}: record without a rater_id")
        if row["item_id"] in calls:
            raise SystemExit(
                f"{path}:{number}: a second record for item {row['item_id']} "
                "(one call per rater per item)"
            )
        calls[row["item_id"]] = row
    return calls


def answers(calls_path: Path, item_ids: Iterable[str]) -> dict[str, tuple[str, str]]:
    """(answer, status) per item; an item without a call record is ``unrated`` (unsure)."""
    return merged_answers([calls_path], item_ids, strict=False)


def merge_calls(paths: Sequence[Path], rater_id: str | None = None) -> dict[str, dict[str, Any]]:
    """The call records of one rater over its shards (one ``calls.jsonl`` per shard).

    Shards hold disjoint items, so an item with records in two shards breaks
    "one call per rater per item" and is refused, as is a record of another
    rater.
    """
    merged: dict[str, dict[str, Any]] = {}
    origin: dict[str, str] = {}
    for path in paths:
        for item_id, row in read_calls(path).items():
            if rater_id is not None and row["rater_id"] != rater_id:
                raise SystemExit(f"{path}: record of {row['rater_id']}, not {rater_id}")
            if item_id in merged:
                raise SystemExit(
                    f"item {item_id} has call records in {origin[item_id]} and {path}: "
                    "one call per rater per item"
                )
            merged[item_id] = row
            origin[item_id] = str(path)
    return merged


def merged_answers(
    paths: Sequence[Path],
    item_ids: Iterable[str],
    rater_id: str | None = None,
    *,
    strict: bool = True,
) -> dict[str, tuple[str, str]]:
    """(answer, status) per item over every shard; an item no shard rated is ``unrated``.

    With ``strict`` (the audit summary), a record for an item outside
    ``item_ids`` means a calls file from another audit and is refused.
    """
    wanted = list(item_ids)
    calls = merge_calls(paths, rater_id)
    stray = sorted(set(calls) - set(wanted))
    if stray and strict:
        raise SystemExit(f"call records for items outside the sample: {stray[:5]}")
    out = {}
    for item_id in wanted:
        row = calls.get(item_id)
        out[item_id] = (row["answer"], row["status"]) if row else answer_for("unrated", None)
    return out


def calls_files_record(paths: Sequence[Path]) -> list[dict[str, Any]]:
    """SHA-256 and record count of each shard's calls file (for the audit summary)."""
    return [
        {
            "path": str(path),
            "sha256": sha256_file(path) if path.is_file() else None,
            "records": len(read_calls(path)),
        }
        for path in paths
    ]


class Runner:
    """Rate every packet once with one rater, append-only, resumable.

    ``stop`` (set by the lane's USR1 or TERM, or by a fatal error) means no new
    request is sent and no transport retry starts; the requests in flight get
    ``grace_s`` to finish (``hurry``, a second signal, ends the wait). After
    that the run is closed: a request that finishes later writes nothing, and
    one that failed in transport after the stop writes nothing either, so its
    item stays ``unrated`` for the rerun instead of becoming a spent
    ``transport_exhausted`` call.
    """

    def __init__(
        self,
        rater_id: str,
        out_dir: Path,
        send: Callable[[str, bytes], Attempt],
        parse: Callable[[Attempt], Reply],
        *,
        workers: int,
        sleep: Callable[[float], None] = time.sleep,
        grace_s: float = STOP_GRACE_S,
    ) -> None:
        self.rater_id = rater_id
        self.out_dir = out_dir
        self.send = send
        self.parse = parse
        self.workers = workers
        self.sleep = sleep
        self.grace_s = grace_s
        self.calls_path = out_dir / "calls.jsonl"
        self.responses = out_dir / "responses"
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.hurry = threading.Event()
        self.closed = False
        self.fatal: str | None = None
        self.dropped_after_stop: list[str] = []

    def signal_stop(self) -> None:
        """First call: stop sending. A later call also ends the grace wait."""
        if self.stop.is_set():
            self.hurry.set()
        self.stop.set()

    def _write(self, item_id: str, record: Mapping[str, Any], response: bytes | None) -> None:
        with self.lock:
            if self.closed:
                self.dropped_after_stop.append(item_id)
                return
            if response is not None:
                (self.responses / f"{item_id}.json").write_bytes(response)
            with self.calls_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def run(self, packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.responses.mkdir(exist_ok=True)
        with self.lock:
            self.closed = False
        by_id = {p["item_id"]: p for p in packets}
        done = read_calls(self.calls_path)
        order = rater_order(list(by_id), self.rater_id, ORDER_SEED)
        todo = [(i, item_id) for i, item_id in enumerate(order) if item_id not in done]

        def one(entry: tuple[int, str]) -> None:
            index, item_id = entry
            if self.stop.is_set():
                return
            body = request_body(self.rater_id, by_id[item_id])
            payload = canonical_bytes(body)
            started = utc_now()
            try:
                attempt, log = call_with_retries(
                    lambda: self.send(item_id, payload),
                    sleep=self.sleep,
                    stopping=self.stop.is_set,
                )
            except FatalRunError as exc:
                self.fatal = str(exc)
                self.stop.set()
                return
            if self.stop.is_set() and is_transport(attempt):
                # Cut off by the stop (or the engine shutting down after it):
                # not a call the rater answered, so the item stays unrated.
                with self.lock:
                    self.dropped_after_stop.append(item_id)
                return
            try:
                reply = self.parse(attempt)
            except Exception as exc:  # noqa: BLE001 - any unreadable body is unsure, not a crash
                reply = malformed(f"{type(exc).__name__}: {str(exc)[:200]}")
            record = call_record(self.rater_id, item_id, index, body, attempt, log, reply, started)
            self._write(item_id, record, attempt.response_bytes)

        pool = ThreadPoolExecutor(max_workers=self.workers)
        futures = [pool.submit(one, entry) for entry in todo]
        pending = set(futures)
        deadline: float | None = None
        while pending:
            finished, pending = wait(pending, timeout=0.5)
            for future in finished:
                future.result()
            if self.stop.is_set():
                if deadline is None:
                    deadline = time.monotonic() + self.grace_s
                if self.hurry.is_set() or time.monotonic() >= deadline:
                    break
        with self.lock:
            self.closed = True
        pool.shutdown(wait=not pending, cancel_futures=True)
        calls = read_calls(self.calls_path)
        return {
            "items": len(by_id),
            "rated_now": sum(1 for _, item_id in todo if item_id in calls),
            "rated_before": len(done),
            "unrated": sorted(set(by_id) - set(calls)),
            "outcomes": dict(Counter(c["outcome"] for c in calls.values())),
            "answers": dict(Counter(c["answer"] for c in calls.values())),
            "models_returned": dict(Counter(str(c["model_returned"]) for c in calls.values())),
            "fatal": self.fatal,
            "stopped": self.stop.is_set(),
            "in_flight_abandoned": len(pending),
            "dropped_after_stop": sorted(set(self.dropped_after_stop)),
        }


def write_receipt(out_dir: Path, receipt: Mapping[str, Any]) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    calls = out_dir / "calls.jsonl"
    full = {
        "schema": "q2m-rater-receipt-v1",
        "runner_version": RUNNER_VERSION,
        "code_sha256": code_digests(),
        "prompt_sha256": sha256_bytes(RATER_PROMPT_V1.encode()),
        "answer_line_sha256": sha256_bytes(ANSWER_LINE.encode()),
        "calls_sha256": sha256_file(calls) if calls.is_file() else None,
        "git_sha": os.environ.get("COTCODEC_GIT_SHA"),
        "finished_at": utc_now(),
        **receipt,
    }
    (out_dir / "receipt.json").write_text(
        json.dumps(full, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return full


def _install_stop(runner: Runner) -> None:
    def handler(signum: int, _frame: Any) -> None:
        runner.signal_stop()

    for sig in (signal.SIGTERM, signal.SIGUSR1, signal.SIGINT):
        signal.signal(sig, handler)


def _packets_record(path: Path, packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256_file(path), "items": len(packets)}


# --- anthropic ----------------------------------------------------------------


def _anthropic_client() -> Any:
    import anthropic

    return anthropic.Anthropic(max_retries=0, timeout=ANTHROPIC["timeout_s"])


def anthropic_model_record(client: Any) -> dict[str, Any]:
    model = client.models.retrieve(ANTHROPIC["model"])
    return {
        "requested": ANTHROPIC["model"],
        "id": model.id,
        "display_name": getattr(model, "display_name", None),
        "created_at": str(getattr(model, "created_at", None)),
    }


def anthropic_sender(client: Any) -> Callable[[str, bytes], Attempt]:
    import anthropic

    def send(_item_id: str, payload: bytes) -> Attempt:
        body = json.loads(payload)
        started = time.monotonic()
        try:
            raw = client.messages.with_raw_response.create(**body)
            return Attempt(
                status=raw.status_code,
                request_bytes=raw.http_request.content,
                response_bytes=raw.content,
                seconds=time.monotonic() - started,
            )
        except anthropic.APITimeoutError as exc:
            return Attempt(
                transport_error=type(exc).__name__, timeout=True, seconds=time.monotonic() - started
            )
        except anthropic.APIConnectionError as exc:
            return Attempt(transport_error=type(exc).__name__, seconds=time.monotonic() - started)
        except anthropic.APIStatusError as exc:
            request = getattr(exc.response, "request", None)
            return Attempt(
                status=exc.status_code,
                request_bytes=getattr(request, "content", None),
                response_bytes=exc.response.content,
                seconds=time.monotonic() - started,
            )

    return send


def cmd_models(args: argparse.Namespace) -> int:
    record = anthropic_model_record(_anthropic_client())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, sort_keys=True))
    return 0


def cmd_anthropic(args: argparse.Namespace) -> int:
    packets = load_packets(args.packets, args.expected_packets_sha256)
    client = _anthropic_client()
    model = anthropic_model_record(client)
    if model["id"] != ANTHROPIC["model"]:
        raise SystemExit(f"the API names the model {model['id']!r}, not {ANTHROPIC['model']!r}")
    runner = Runner(
        ANTHROPIC["rater_id"],
        args.out,
        anthropic_sender(client),
        anthropic_reply,
        workers=int(ANTHROPIC["workers"]),
    )
    _install_stop(runner)
    started = utc_now()
    result: dict[str, Any] = {}
    error: str | None = None
    try:
        result = runner.run(packets)
    except BaseException as exc:
        error = f"{type(exc).__name__}: {str(exc)[:400]}"
        raise
    finally:
        receipt = write_receipt(
            args.out,
            {
                "rater": dict(RATERS[0]),
                "path": "Anthropic Messages API",
                "provider_endpoint": "Anthropic Messages API (POST /v1/messages)",
                "model": model,
                "params": {k: ANTHROPIC[k] for k in ("model", "max_tokens", "effort", "timeout_s")},
                "sampling": "no sampling parameter sent (the model rejects them); API default",
                "data_sent": (
                    "packet text and page renders of public OSWorld task files and edits of them"
                ),
                "packets": _packets_record(args.packets, packets),
                "started_at": started,
                "result": result,
                "run_error": error,
            },
        )
    print(json.dumps({"calls_sha256": receipt["calls_sha256"], **result}, sort_keys=True))
    return 1 if result["fatal"] else 0


# --- agent harness (decision D25) ----------------------------------------------

HARNESS_SCHEMA = "q2m-harness-export-v1"
HARNESS_PATH = "Claude Code agent harness (decision D25)"
HARNESS_NOTE = """\
How to read this item: everything you may use is in this file and in the page
images it names (PNG or JPEG files in the folder named after this item, next to
this file); open every image it names. You have no other information about the
task, and nothing outside this file and its images is part of it. Rate this
item on its own.
"""
HARNESS_INSTRUCTIONS = RATER_PROMPT_V1 + "\n" + HARNESS_NOTE
HARNESS_ANSWER_KEYS = frozenset({"item_id", "answer", "reason", "model_id"})


def _image_bytes(part: Mapping[str, Any]) -> bytes:
    import base64

    return base64.b64decode(part["data_b64"])


def harness_text(
    packet: Mapping[str, Any],
    instructions: str | None = None,
    image_dir: str | None = None,
) -> tuple[str, list[tuple[str, bytes]]]:
    """The exported item file and its images, in ``packet_parts`` order.

    ``image_dir`` is the folder the text names the images by: ``<item>.pages``
    on the shared-directory path (D25), ``pages`` on the isolated path (D27).
    """
    item = str(packet["item_id"])
    folder = image_dir if image_dir is not None else f"{item}.pages"
    chunks = [
        "RATER INSTRUCTIONS\n\n",
        HARNESS_INSTRUCTIONS if instructions is None else instructions,
        f"\nITEM {item}\n\n",
    ]
    images: list[tuple[str, bytes]] = []
    for part in packet_parts(packet):
        if part["type"] == "text":
            chunks.append(part["text"])
            continue
        suffix = ".png" if part["media_type"] == "image/png" else ".jpg"
        name = f"{folder}/p{len(images) + 1:02d}{suffix}"
        images.append((name, _image_bytes(part)))
        chunks.append(f"(image file: {name})\n")
    return "".join(chunks) + "\n", images


def harness_body(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical request of the harness path, rebuilt from the packet (digest only)."""
    text, images = harness_text(packet)
    return {
        "path": HARNESS_PATH,
        "model": ANTHROPIC["model"],
        "text": text,
        "images": [{"name": n, "sha256": sha256_bytes(b)} for n, b in images],
    }


def export_harness(packets: Sequence[Mapping[str, Any]], out_dir: Path) -> dict[str, Any]:
    """Blind item files for the agent-harness rater; returns the export manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} is not empty; export into a new directory")
    items: dict[str, Any] = {}
    for packet in packets:
        item = str(packet["item_id"])
        text, images = harness_text(packet)
        data = text.encode("utf-8")
        (out_dir / f"{item}.txt").write_bytes(data)
        for name, blob in images:
            path = out_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
        items[item] = {
            "file": f"{item}.txt",
            "file_sha256": sha256_bytes(data),
            "body_sha256": sha256_bytes(canonical_bytes(harness_body(packet))),
            "images": [{"name": n, "sha256": sha256_bytes(b)} for n, b in images],
        }
    order = rater_order(list(items), str(ANTHROPIC["rater_id"]), ORDER_SEED)
    index = (json.dumps(order, indent=1) + "\n").encode("utf-8")
    (out_dir / "index.json").write_bytes(index)
    return {
        "schema": HARNESS_SCHEMA,
        "path": HARNESS_PATH,
        "rater_id": ANTHROPIC["rater_id"],
        "model": ANTHROPIC["model"],
        "instructions_sha256": sha256_bytes(HARNESS_INSTRUCTIONS.encode()),
        "prompt_sha256": sha256_bytes(RATER_PROMPT_V1.encode()),
        "answer_line_sha256": sha256_bytes(ANSWER_LINE.encode()),
        "index_sha256": sha256_bytes(index),
        "order": order,
        "items": items,
        "exported_at": utc_now(),
    }


HARNESS_WRAPPER_KEYS = frozenset({"rater", "model_id", "items"})


def answer_records(answers_bytes: bytes) -> list[dict[str, Any]]:
    """The answer records of an answers file, as a list.

    Two registered forms: a bare JSON list of records, or the rater workflow's
    wrapper ``{"rater": ..., "model_id": ..., "items": [...]}`` (exactly these
    keys). A record of the wrapper without ``model_id`` takes the wrapper's; a
    record whose own ``model_id`` differs from the wrapper's is refused.
    """
    try:
        data = json.loads(answers_bytes)
    except ValueError as exc:
        raise SystemExit(f"the answers file is not JSON: {exc}") from exc
    if isinstance(data, list):
        return data
    if not isinstance(data, dict) or set(data) != HARNESS_WRAPPER_KEYS:
        raise SystemExit(
            "the answers file must hold a JSON list or the wrapper "
            f"{sorted(HARNESS_WRAPPER_KEYS)}"
        )
    if not isinstance(data["items"], list):
        raise SystemExit("the wrapper's items must be a JSON list")
    records = []
    for number, rec in enumerate(data["items"]):
        if not isinstance(rec, dict):
            raise SystemExit(f"record {number}: not a JSON object")
        if "model_id" in rec and rec["model_id"] != data["model_id"]:
            raise SystemExit(
                f"record {number}: model {rec['model_id']!r} differs from the wrapper's "
                f"{data['model_id']!r}"
            )
        records.append({**rec, "model_id": data["model_id"]})
    return records


def ingest_harness(
    packets: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    answers_bytes: bytes,
    out_dir: Path,
) -> dict[str, Any]:
    """Call records of the agent-harness rater from its JSON list of answers.

    Every exported body is rebuilt from the packets and checked against the
    export manifest first. One record per item: a second record, an item
    outside the export or a model id other than ``ANTHROPIC["model"]`` is
    refused and nothing is written. An exported item without a record stays
    unrated (``unsure``).
    """
    if manifest.get("schema") != HARNESS_SCHEMA:
        raise SystemExit("not a q2m harness export manifest")
    by_id = {str(p["item_id"]): p for p in packets}
    exported = dict(manifest["items"])
    for item, entry in exported.items():
        if item not in by_id:
            raise SystemExit(f"exported item {item} is not in the packets")
        if sha256_bytes(canonical_bytes(harness_body(by_id[item]))) != entry["body_sha256"]:
            raise SystemExit(f"item {item}: the packet differs from the exported file")
    records = answer_records(answers_bytes)
    order = {item: index for index, item in enumerate(manifest["order"])}
    seen: set[str] = set()
    calls: list[dict[str, Any]] = []
    for number, rec in enumerate(records):
        if not isinstance(rec, dict) or set(rec) - HARNESS_ANSWER_KEYS or "item_id" not in rec:
            raise SystemExit(f"record {number}: keys must be {sorted(HARNESS_ANSWER_KEYS)}")
        item = str(rec["item_id"])
        if item not in exported:
            raise SystemExit(f"record {number}: item {item} was not exported")
        if item in seen:
            raise SystemExit(f"record {number}: a second record for item {item}")
        seen.add(item)
        if rec.get("model_id") != ANTHROPIC["model"]:
            raise SystemExit(
                f"record {number}: model {rec.get('model_id')!r}, not {ANTHROPIC['model']!r}"
            )
        answer_text = rec.get("answer")
        answer, status = answer_for("ok", answer_text if isinstance(answer_text, str) else None)
        reason = rec.get("reason")
        calls.append(
            {
                "schema": CALL_SCHEMA,
                "rater_id": ANTHROPIC["rater_id"],
                "item_id": item,
                "order_index": order[item],
                "model_requested": ANTHROPIC["model"],
                "model_returned": rec.get("model_id"),
                "body_sha256": exported[item]["body_sha256"],
                "request_sha256": exported[item]["file_sha256"],
                "response_sha256": sha256_bytes(canonical_bytes(rec)),
                "http_status": None,
                "outcome": "ok",
                "answer": answer,
                "status": status,
                "stop_reason": None,
                "usage": None,
                "extra": {
                    "path": "agent_harness",
                    "images_sha256": [i["sha256"] for i in exported[item]["images"]],
                    "reason_sha256": (
                        sha256_bytes(str(reason).encode()) if reason is not None else None
                    ),
                },
                "attempts": [],
                "started_at": None,
                "finished_at": utc_now(),
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "calls.jsonl"
    if calls_path.exists():
        raise SystemExit(f"{calls_path} exists: one ingest per export (one call per item)")
    responses = out_dir / "responses"
    responses.mkdir(exist_ok=True)
    for rec in records:
        (responses / f"{rec['item_id']}.json").write_bytes(canonical_bytes(rec))
    calls.sort(key=lambda c: c["order_index"])
    calls_path.write_text(
        "".join(json.dumps(c, sort_keys=True) + "\n" for c in calls), encoding="utf-8"
    )
    return {
        "items": len(exported),
        "rated": len(calls),
        "unrated": sorted(set(exported) - seen),
        "outcomes": dict(Counter(c["outcome"] for c in calls)),
        "answers": dict(Counter(c["answer"] for c in calls)),
        "statuses": dict(Counter(c["status"] for c in calls)),
        "models_returned": dict(Counter(str(c["model_returned"]) for c in calls)),
    }


def _load_shards(paths: Sequence[Path]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        for packet in load_packets(path):
            if packet["item_id"] in seen:
                raise SystemExit(f"{path}: item {packet['item_id']} is in two shards")
            seen.add(packet["item_id"])
            packets.append(packet)
    return packets


def cmd_export_harness(args: argparse.Namespace) -> int:
    packets = _load_shards(args.packets)
    manifest = export_harness(packets, args.out)
    manifest["packets"] = [_packets_record(p, load_packets(p)) for p in args.packets]
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"items": len(manifest["items"]), "index_sha256": manifest["index_sha256"]}))
    return 0


def cmd_ingest_harness(args: argparse.Namespace) -> int:
    packets = _load_shards(args.packets)
    manifest_bytes = args.export_manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    answers_bytes = args.answers.read_bytes()
    result = ingest_harness(packets, manifest, answers_bytes, args.out)
    receipt = write_receipt(
        args.out,
        {
            "rater": dict(RATERS[0]),
            "path": HARNESS_PATH,
            "model": {"requested": ANTHROPIC["model"], "returned": result["models_returned"]},
            "params": {"model": ANTHROPIC["model"]},
            "sampling": (
                "not fixed on this path: the agent harness sets the model's sampling and "
                "thinking (disclosed under D25); the open-weight rater stays seeded"
            ),
            "data_sent": (
                "packet text and page renders of public OSWorld task files and edits of them, "
                "read from exported files by a Claude subagent"
            ),
            "export_manifest_sha256": sha256_bytes(manifest_bytes),
            "index_sha256": manifest["index_sha256"],
            "instructions_sha256": manifest["instructions_sha256"],
            "answers_sha256": sha256_bytes(answers_bytes),
            "packets": [_packets_record(p, load_packets(p)) for p in args.packets],
            "result": result,
        },
    )
    print(json.dumps({"calls_sha256": receipt["calls_sha256"], **result}, sort_keys=True))
    return 0


# --- isolated agent harness (decisions D25 and D27) ----------------------------

ISOLATED_SCHEMA = "q2m-isolated-export-v1"
ISOLATED_PATH = (
    "Claude Code agent harness, one agent per item confined to its own directory "
    "(decisions D25 and D27)"
)
ISOLATED_TEXT = "packet.txt"
ISOLATED_PAGES = "pages"
ISOLATED_NOTE = """\
How to read this item: everything you may use is this file and the page images
it names, which are in the folder `pages` next to this file; open every image it
names. You have no other information about the task, and nothing outside this
file's folder is part of it. Use only the Read tool, and only on this file and
the images it names. Run no command and open nothing else: an answer given
after any other tool call is void.
"""
ISOLATED_INSTRUCTIONS = RATER_PROMPT_V1 + "\n" + ISOLATED_NOTE
# The transcript audit (``audit_transcript``). Read-only tools with the inputs
# that name what they touch; every path must lie inside the item's directory.
READ_TOOLS: Mapping[str, tuple[str, ...]] = {
    "Read": ("file_path",),
    "Glob": ("path",),
    "Grep": ("path",),
    "LS": ("path",),
}
# Tools that touch no file: returning the answer and the harness's bookkeeping.
NEUTRAL_TOOLS = frozenset({"StructuredOutput", "ToolSearch", "TodoWrite"})
SHELL_MARKERS = ("bash", "shell", "terminal", "powershell")
SYNTHETIC_MODELS = frozenset({"<synthetic>"})
ISOLATED_ANSWER_KEYS = frozenset({"item_id", "answer", "reason", "model_id"})


def isolated_body(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical request of the isolated path, rebuilt from the packet (digest only)."""
    text, images = harness_text(packet, ISOLATED_INSTRUCTIONS, ISOLATED_PAGES)
    return {
        "path": ISOLATED_PATH,
        "model": ANTHROPIC["model"],
        "text": text,
        "images": [{"name": n, "sha256": sha256_bytes(b)} for n, b in images],
    }


def tree_digest(files: Mapping[str, str]) -> str:
    """SHA-256 of the sorted lines ``<sha256>  <relative path>`` of a directory."""
    lines = "".join(f"{files[name]}  {name}\n" for name in sorted(files))
    return sha256_bytes(lines.encode("utf-8"))


def hash_tree(root: Path) -> dict[str, str]:
    """Every file under ``root`` (hidden files and links included) by relative path."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            out[rel] = "symlink:" + os.readlink(path)
        elif path.is_file():
            out[rel] = sha256_file(path)
    return out


def export_isolated(packets: Sequence[Mapping[str, Any]], iso_root: Path) -> dict[str, Any]:
    """One fresh directory per item holding only its packet text and page images.

    ``<iso_root>/<item>/packet.txt`` and ``<iso_root>/<item>/pages/pNN.png``:
    no index, no other item, no label, verdict, operator or other rater's
    answer. Files are made read-only. Returns the manifest, which the caller
    writes outside ``iso_root``.
    """
    if iso_root.exists() and any(iso_root.iterdir()):
        raise SystemExit(f"{iso_root} is not empty; export into a new directory")
    iso_root.mkdir(parents=True, exist_ok=True)
    items: dict[str, Any] = {}
    for packet in packets:
        item = str(packet["item_id"])
        if not item or "/" in item or item.startswith("."):
            raise SystemExit(f"item id {item!r} cannot name a directory")
        text, images = harness_text(packet, ISOLATED_INSTRUCTIONS, ISOLATED_PAGES)
        data = text.encode("utf-8")
        folder = iso_root / item
        folder.mkdir()
        (folder / ISOLATED_TEXT).write_bytes(data)
        for name, blob in images:
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
        files = hash_tree(folder)
        for path in sorted(folder.rglob("*"), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        folder.chmod(0o555)
        items[item] = {
            "dir": item,
            "text": ISOLATED_TEXT,
            "text_sha256": sha256_bytes(data),
            "body_sha256": sha256_bytes(canonical_bytes(isolated_body(packet))),
            "images": [{"name": n, "sha256": sha256_bytes(b)} for n, b in images],
            "files": files,
            "tree_sha256": tree_digest(files),
        }
    order = rater_order(list(items), str(ANTHROPIC["rater_id"]), ORDER_SEED)
    return {
        "schema": ISOLATED_SCHEMA,
        "path": ISOLATED_PATH,
        "rater_id": ANTHROPIC["rater_id"],
        "model": ANTHROPIC["model"],
        "iso_root": str(iso_root),
        "instructions_sha256": sha256_bytes(ISOLATED_INSTRUCTIONS.encode()),
        "prompt_sha256": sha256_bytes(RATER_PROMPT_V1.encode()),
        "answer_line_sha256": sha256_bytes(ANSWER_LINE.encode()),
        "order": order,
        "items": items,
        "exported_at": utc_now(),
    }


def _tool_uses(node: Any) -> Iterable[Mapping[str, Any]]:
    """Every ``tool_use`` block anywhere in one transcript entry."""
    if isinstance(node, Mapping):
        if node.get("type") == "tool_use" and isinstance(node.get("name"), str):
            yield node
        for value in node.values():
            yield from _tool_uses(value)
    elif isinstance(node, list):
        for value in node:
            yield from _tool_uses(value)


def _inside(value: str, folder: Path) -> bool:
    """``value`` is an absolute path that resolves inside ``folder``."""
    if not value.startswith("/") or "\x00" in value:
        return False
    target = os.path.realpath(value)
    base = os.path.realpath(folder)
    return target == base or target.startswith(base.rstrip("/") + "/")


def _check_read_tool(name: str, raw: Any, folder: Path) -> list[str]:
    problems: list[str] = []
    params = raw if isinstance(raw, Mapping) else {}
    for key in READ_TOOLS[name]:
        value = params.get(key)
        if not isinstance(value, str) or not _inside(value, folder):
            problems.append(f"{name} {key}={str(value)[:200]!r} is not inside the item directory")
    for key, value in params.items():
        if not isinstance(value, str) or key in READ_TOOLS[name]:
            continue
        if name == "Grep" and key == "pattern":
            continue  # a regular expression, not a path
        # Glob's pattern and Grep's glob filter are file patterns under the path.
        file_pattern = (name == "Glob" and key == "pattern") or key == "glob"
        if file_pattern and ".." in value:
            problems.append(f"{name} {key}={value[:200]!r} climbs out of the item directory")
        if value.startswith(("/", "~")) and not _inside(value, folder):
            problems.append(f"{name} {key}={value[:200]!r} is outside the item directory")
    return problems


def audit_transcript(transcript: bytes, folder: Path) -> dict[str, Any]:
    """The registered transcript audit of one isolated rating (decision D27).

    The answer is void (``unsure``) if the agent made a shell call, called a
    tool that is neither a read-only tool (``READ_TOOLS``) nor one that
    touches no file (``NEUTRAL_TOOLS``), or gave a read-only tool a path
    outside its item's directory. The model id is the one the harness
    recorded on the agent's turns.
    """
    tools: Counter[str] = Counter()
    models: Counter[str] = Counter()
    void: list[str] = []
    answers: list[Any] = []
    final_texts: list[str] = []
    lines = transcript.decode("utf-8", errors="replace").splitlines()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            void.append(f"line {number}: not JSON")
            continue
        message = entry.get("message") if isinstance(entry, Mapping) else None
        if isinstance(message, Mapping) and (
            entry.get("type") == "assistant" or message.get("role") == "assistant"
        ):
            model = message.get("model")
            if isinstance(model, str) and model not in SYNTHETIC_MODELS:
                models[model] += 1
            content = message.get("content")
            texts = [
                str(b.get("text", ""))
                for b in content
                if isinstance(b, Mapping) and b.get("type") == "text"
            ] if isinstance(content, list) else ([content] if isinstance(content, str) else [])
            if any(t.strip() for t in texts):
                final_texts = texts
        for use in _tool_uses(entry):
            name = str(use["name"])
            tools[name] += 1
            raw = use.get("input")
            if any(marker in name.lower() for marker in SHELL_MARKERS):
                void.append(f"shell call {name}")
            elif name in READ_TOOLS:
                void.extend(_check_read_tool(name, raw, folder))
            elif name in NEUTRAL_TOOLS:
                if name == "StructuredOutput" and isinstance(raw, Mapping):
                    answers.append(raw.get("answer"))
            else:
                void.append(f"tool {name} is not a read-only tool of the item directory")
    if not models:
        void.append("the transcript names no model")
    return {
        "models": dict(models),
        "tool_calls": dict(tools),
        "void_reasons": void,
        "structured_answers": answers,
        "final_text_sha256": sha256_bytes("".join(final_texts).encode()) if final_texts else None,
        "final_text": "".join(final_texts),
        "lines": len(lines),
    }


def _answer_source(record_answer: str, audit: Mapping[str, Any]) -> str:
    """Where the record's answer appears in the transcript, or ``not_found``."""
    if audit["structured_answers"]:
        last = audit["structured_answers"][-1]
        return "structured_output" if last == record_answer else "not_found"
    final = str(audit.get("final_text") or "")
    if record_answer and record_answer.strip() and record_answer.strip() in final:
        return "final_text"
    return "not_found"


def isolated_answers(path: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Answer records from a JSON file (list or wrapper) or a directory of per-item files.

    A directory holds ``<item_id>.json``, each one record object whose
    ``item_id`` is the file's stem. Returns the records and the SHA-256 of
    every file read.
    """
    if path.is_dir():
        records = []
        digests = {}
        for file in sorted(path.glob("*.json")):
            data = file.read_bytes()
            digests[file.name] = sha256_bytes(data)
            try:
                rec = json.loads(data)
            except ValueError as exc:
                raise SystemExit(f"{file}: not JSON: {exc}") from exc
            if not isinstance(rec, dict) or str(rec.get("item_id")) != file.stem:
                raise SystemExit(f"{file}: must hold one record for item {file.stem}")
            records.append(rec)
        return records, digests
    data = path.read_bytes()
    return answer_records(data), {path.name: sha256_bytes(data)}


def ingest_isolated(
    packets: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    iso_root: Path,
    records: Sequence[Mapping[str, Any]],
    transcripts: Path,
    out_dir: Path,
) -> dict[str, Any]:
    """Call records of the isolated Claude rater (one agent per item).

    Refused, and nothing written: a manifest of another schema, a packet that
    differs from its export, an answer for an item outside the export, a second
    answer for an item, a record with other keys, or a transcript whose agent
    turns name a model other than ``ANTHROPIC["model"]``. Void (``unsure``,
    outcome ``isolation_void``), each with its reasons: an item whose directory
    no longer matches its export, whose transcript is missing or names no
    model, fails the transcript audit, or whose answer is not the one the
    transcript returned. An exported item without an answer stays unrated.
    """
    if manifest.get("schema") != ISOLATED_SCHEMA:
        raise SystemExit("not a q2m isolated export manifest")
    by_id = {str(p["item_id"]): p for p in packets}
    exported = dict(manifest["items"])
    for item, entry in exported.items():
        if item not in by_id:
            raise SystemExit(f"exported item {item} is not in the packets")
        if sha256_bytes(canonical_bytes(isolated_body(by_id[item]))) != entry["body_sha256"]:
            raise SystemExit(f"item {item}: the packet differs from the exported file")
    order = {item: index for index, item in enumerate(manifest["order"])}
    root_entries = sorted(p.name for p in iso_root.iterdir()) if iso_root.is_dir() else []
    seen: set[str] = set()
    calls: list[dict[str, Any]] = []
    responses: dict[str, bytes] = {}
    for number, rec in enumerate(records):
        if not isinstance(rec, Mapping) or set(rec) - ISOLATED_ANSWER_KEYS or "item_id" not in rec:
            raise SystemExit(f"record {number}: keys must be within {sorted(ISOLATED_ANSWER_KEYS)}")
        item = str(rec["item_id"])
        if item not in exported:
            raise SystemExit(f"record {number}: item {item} was not exported")
        if item in seen:
            raise SystemExit(f"record {number}: a second answer for item {item}")
        seen.add(item)
        entry = exported[item]
        void: list[str] = []
        folder = iso_root / entry["dir"]
        current = hash_tree(folder) if folder.is_dir() else None
        if current is None:
            void.append("the item directory is missing")
        elif current != entry["files"]:
            void.append("the item directory differs from its export")
        transcript_path = transcripts / f"{item}.jsonl"
        transcript = transcript_path.read_bytes() if transcript_path.is_file() else None
        audit: dict[str, Any] = {"models": {}, "tool_calls": {}, "void_reasons": []}
        if transcript is None:
            void.append("no harness transcript for this item")
        else:
            audit = audit_transcript(transcript, folder)
            others = sorted(set(audit["models"]) - {ANTHROPIC["model"]})
            if others:
                raise SystemExit(
                    f"item {item}: the transcript names model(s) {others}, "
                    f"not {ANTHROPIC['model']!r}"
                )
            void.extend(audit["void_reasons"])
        answer_text = rec.get("answer")
        answer_text = answer_text if isinstance(answer_text, str) else None
        source = _answer_source(answer_text or "", audit) if transcript is not None else None
        if transcript is not None and source == "not_found":
            void.append("the answer is not the one the transcript returned")
        claimed = rec.get("model_id")
        model = ANTHROPIC["model"] if audit["models"] else None
        if claimed is not None and model is not None and claimed != model:
            void.append(f"the record claims model {claimed!r}; the transcript names {model!r}")
        outcome = "isolation_void" if void else "ok"
        answer, status = answer_for(outcome, answer_text)
        reason = rec.get("reason")
        response = canonical_bytes(dict(rec))
        responses[item] = response
        calls.append(
            {
                "schema": CALL_SCHEMA,
                "rater_id": ANTHROPIC["rater_id"],
                "item_id": item,
                "order_index": order[item],
                "model_requested": ANTHROPIC["model"],
                "model_returned": model,
                "body_sha256": entry["body_sha256"],
                "request_sha256": entry["text_sha256"],
                "response_sha256": sha256_bytes(response),
                "http_status": None,
                "outcome": outcome,
                "answer": answer,
                "status": status,
                "stop_reason": None,
                "usage": None,
                "extra": {
                    "path": "agent_harness_isolated",
                    "tree_sha256": entry["tree_sha256"],
                    "tree_rehashed_sha256": tree_digest(current) if current is not None else None,
                    "images_sha256": [i["sha256"] for i in entry["images"]],
                    "reason_sha256": (
                        sha256_bytes(str(reason).encode()) if reason is not None else None
                    ),
                    "first_token_answer": parse_first_token(answer_text)[0],
                    "transcript_sha256": sha256_bytes(transcript) if transcript else None,
                    "transcript_bytes": len(transcript) if transcript else None,
                    "transcript_models": audit["models"],
                    "tool_calls": audit["tool_calls"],
                    "answer_source": source,
                    "void_reasons": void,
                },
                "attempts": [],
                "started_at": None,
                "finished_at": utc_now(),
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "calls.jsonl"
    if calls_path.exists():
        raise SystemExit(f"{calls_path} exists: one ingest per export (one call per item)")
    folder = out_dir / "responses"
    folder.mkdir(exist_ok=True)
    for item, data in responses.items():
        (folder / f"{item}.json").write_bytes(data)
    calls.sort(key=lambda c: c["order_index"])
    calls_path.write_text(
        "".join(json.dumps(c, sort_keys=True) + "\n" for c in calls), encoding="utf-8"
    )
    voided = [c for c in calls if c["outcome"] == "isolation_void"]
    return {
        "items": len(exported),
        "rated": len(calls),
        "unrated": sorted(set(exported) - seen),
        "void": len(voided),
        "void_reasons": dict(
            Counter(r.split(":")[0][:80] for c in voided for r in c["extra"]["void_reasons"])
        ),
        "outcomes": dict(Counter(c["outcome"] for c in calls)),
        "answers": dict(Counter(c["answer"] for c in calls)),
        "statuses": dict(Counter(c["status"] for c in calls)),
        "models_returned": dict(Counter(str(c["model_returned"]) for c in calls)),
        "root_entries_not_exported": sorted(set(root_entries) - set(exported)),
    }


def cmd_export_isolated(args: argparse.Namespace) -> int:
    iso_root = args.iso_root.resolve()
    manifest_out = args.manifest_out.resolve()
    if manifest_out == iso_root or iso_root in manifest_out.parents:
        raise SystemExit("the manifest must be written outside the isolation root")
    packets = _load_shards(args.packets)
    manifest = export_isolated(packets, iso_root)
    manifest["packets"] = [_packets_record(p, load_packets(p)) for p in args.packets]
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "items": len(manifest["items"]),
                "iso_root": str(iso_root),
                "manifest_sha256": sha256_file(manifest_out),
                "order": manifest["order"],
            }
        )
    )
    return 0


def cmd_ingest_isolated(args: argparse.Namespace) -> int:
    packets = _load_shards(args.packets)
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    records, answer_digests = isolated_answers(args.answers)
    result = ingest_isolated(
        packets, manifest, args.iso_root, records, args.transcripts, args.out
    )
    receipt = write_receipt(
        args.out,
        {
            "rater": dict(RATERS[0]),
            "path": ISOLATED_PATH,
            "model": {
                "requested": ANTHROPIC["model"],
                "from_transcripts": result["models_returned"],
            },
            "params": {"model": ANTHROPIC["model"]},
            "sampling": (
                "not fixed on this path: the agent harness sets the model's sampling and "
                "thinking (disclosed under D25); the open-weight rater stays seeded"
            ),
            "isolation": {
                "protocol": (
                    "one agent per item; read-only access to its own directory only; no shell; "
                    "transcript audit voids an answer after a shell call, a tool that is not "
                    "read-only, or a path outside the item directory (decision D27)"
                ),
                "read_tools": {k: list(v) for k, v in READ_TOOLS.items()},
                "neutral_tools": sorted(NEUTRAL_TOOLS),
                "iso_root": str(args.iso_root),
            },
            "data_sent": (
                "packet text and page renders of public OSWorld task files and edits of them, "
                "read from one item directory by one Claude subagent"
            ),
            "manifest_sha256": sha256_bytes(manifest_bytes),
            "instructions_sha256": manifest["instructions_sha256"],
            "answers_files_sha256": answer_digests,
            "packets": [_packets_record(p, load_packets(p)) for p in args.packets],
            "result": result,
        },
    )
    print(json.dumps({"calls_sha256": receipt["calls_sha256"], **result}, sort_keys=True))
    return 0


# --- open-weight (vLLM) -------------------------------------------------------


def engine_argv(model_dir: str) -> list[str]:
    argv = [
        "vllm",
        "serve",
        model_dir,
        "--served-model-name",
        str(OPEN_WEIGHT["served_name"]),
        "--host",
        str(OPEN_WEIGHT["host"]),
        "--port",
        str(OPEN_WEIGHT["port"]),
        "--disable-uvicorn-access-log",
    ]
    for key, value in ENGINE_FLAGS:
        option = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            argv.append(option if value else "--no-" + key.replace("_", "-"))
        elif isinstance(value, Mapping):
            argv.extend([option, json.dumps(value, sort_keys=True, separators=(",", ":"))])
        else:
            argv.extend([option, str(value)])
    return argv


def engine_env(out_dir: Path) -> dict[str, str]:
    cache = out_dir / "cache"
    env = {key: str(cache / sub) for key, sub in CACHE_DIRS.items()}
    for path in env.values():
        Path(path).mkdir(parents=True, exist_ok=True)
    return {**os.environ, **env, **ENGINE_ENV}


def args_doctor() -> dict[str, Any]:
    """CPU-only: vLLM's parsers accept the engine argv and the request payload."""
    import vllm.platforms
    from vllm.platforms.cpu import CpuPlatform

    vllm.platforms._current_platform = CpuPlatform()  # parse only; nothing runs on a device
    from vllm.entrypoints.launchers.cli_args import make_arg_parser, validate_parsed_serve_args
    from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
    from vllm.utils.argparse_utils import FlexibleArgumentParser

    argv = engine_argv(f"{MODEL_ROOT}/{OPEN_WEIGHT['model_id']}")
    parsed = make_arg_parser(FlexibleArgumentParser()).parse_args(argv[2:])
    validate_parsed_serve_args(parsed)
    values = vars(parsed)
    problems = [
        f"{key}: wanted {value!r}, parsed {values.get(key)!r}"
        for key, value in ENGINE_FLAGS
        if key != "limit_mm_per_prompt" and values.get(key) != value
    ]
    packet = {
        "schema": PACKET_SCHEMA,
        "item_id": "doctor",
        "instruction": "x",
        "initial_files": [],
        "candidate": {
            "files": [
                {
                    "vm_path": "/a",
                    "structure": ["x"],
                    "diff_vs_initial": [],
                    "pages": [
                        {
                            "page": 1,
                            "of": 1,
                            "media_type": "image/png",
                            "sha256": "0",
                            "data_b64": "AA==",
                        }
                    ],
                }
            ]
        },
    }
    request = ChatCompletionRequest(**openai_body(packet))
    payload_ok = (
        request.temperature == 0.0
        and request.max_tokens == OPEN_WEIGHT["max_tokens"]
        and request.seed == OPEN_WEIGHT["seed"]
        and request.chat_template_kwargs == {"enable_thinking": False}
    )
    if not payload_ok:
        problems.append("request payload fields differ after vLLM's parser")
    return {"argv": argv, "problems": problems, "pass": not problems}


# The registered token budget (``audit.fit_packet``) counts an image as one
# token per 32 x 32 pixel cell plus two; the doctor checks that the rater's
# processor does not produce more for a 100-dpi letter page.
DOCTOR_PAGE_PX = (850, 1100)


def image_input_doctor(model_dir: str) -> dict[str, Any]:
    """CPU-only: vLLM takes the rater model as multimodal and turns one page into image tokens.

    Reads only the model's configuration, tokenizer and processor files (no
    weights): vLLM's registry must resolve the architecture with multimodal
    support, the model config must keep image input on under the registered
    ``limit_mm_per_prompt``, and vLLM's own processor must expand one rendered
    page of ``DOCTOR_PAGE_PX`` into image placeholder tokens, no more than the
    registered token budget assumes.
    """
    import vllm.platforms
    from vllm.platforms.cpu import CpuPlatform

    vllm.platforms._current_platform = CpuPlatform()  # nothing runs on a device
    from PIL import Image
    from transformers import AutoTokenizer
    from vllm.engine.arg_utils import EngineArgs
    from vllm.model_executor.models.registry import ModelRegistry
    from vllm.multimodal import MULTIMODAL_REGISTRY
    from vllm.multimodal.processing.context import TimingContext
    from vllm.multimodal.processing.inputs import ProcessorInputs

    flags = dict(ENGINE_FLAGS)
    config = EngineArgs(
        model=model_dir,
        tokenizer=model_dir,
        max_model_len=int(flags["max_model_len"]),
        seed=int(flags["seed"]),
        limit_mm_per_prompt=flags["limit_mm_per_prompt"],
    ).create_model_config()
    arch = config.architectures[0]
    inspected = ModelRegistry._try_inspect_model_cls(arch)
    mm_config = getattr(config, "multimodal_config", None)
    report: dict[str, Any] = {
        "architecture": arch,
        "supports_multimodal": bool(getattr(inspected, "supports_multimodal", False)),
        "is_multimodal_model": bool(getattr(config, "is_multimodal_model", False)),
        "language_model_only": getattr(mm_config, "language_model_only", None),
    }
    processor = MULTIMODAL_REGISTRY.create_processor(config)
    report["processor"] = type(processor).__name__
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    messages = [
        {"role": "system", "content": RATER_PROMPT_V1},
        {"role": "user", "content": [{"type": "text", "text": "page"}, {"type": "image"}]},
    ]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    page = Image.new("RGB", DOCTOR_PAGE_PX, (255, 255, 255))
    items = processor.info.parse_mm_data({"image": [page]})
    result = processor.apply(ProcessorInputs(prompt=ids, mm_data_items=items), TimingContext())
    get = result.get if isinstance(result, Mapping) else lambda k: getattr(result, k, None)
    placeholders = (get("mm_placeholders") or {}).get("image") or []
    lengths = [int(getattr(p, "length", None) or p.get("length")) for p in placeholders]
    cells = -(-DOCTOR_PAGE_PX[0] // 32) * -(-DOCTOR_PAGE_PX[1] // 32)
    report.update(
        {
            "page_px": list(DOCTOR_PAGE_PX),
            "prompt_tokens_text_only": len(ids),
            "prompt_tokens_with_page": len(get("prompt_token_ids") or []),
            "image_placeholder_tokens": lengths,
            "registered_estimate_tokens": cells + 2,
        }
    )
    problems = []
    if not (report["supports_multimodal"] and report["is_multimodal_model"]):
        problems.append(f"vLLM does not take {arch} as a multimodal model")
    if report["language_model_only"]:
        problems.append("the model config runs the language model only (no image input)")
    if len(lengths) != 1 or lengths[0] <= 0:
        problems.append(f"one page gave image placeholders {lengths}")
    elif lengths[0] > cells + 2:
        problems.append(f"one page is {lengths[0]} tokens, over the registered {cells + 2}")
    report["problems"] = problems
    report["pass"] = not problems
    return report


def cmd_args_doctor(args: argparse.Namespace) -> int:
    report = args_doctor()
    if args.model_dir:
        try:
            image = image_input_doctor(str(args.model_dir))
        except Exception as exc:  # noqa: BLE001 - the doctor reports, the run stops
            image = {"pass": False, "problems": [f"{type(exc).__name__}: {str(exc)[:400]}"]}
        report["image_input"] = image
        report["problems"] = list(report["problems"]) + [
            f"image input: {p}" for p in image["problems"]
        ]
        report["pass"] = bool(report["pass"] and image["pass"])
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["pass"] else 1


def openai_sender(base_url: str) -> Callable[[str, bytes], Attempt]:
    import httpx

    def send(_item_id: str, payload: bytes) -> Attempt:
        started = time.monotonic()
        try:
            with httpx.Client(
                base_url=base_url, timeout=float(OPEN_WEIGHT["timeout_s"]), trust_env=False
            ) as client:
                response = client.post(
                    "/v1/chat/completions",
                    content=payload,
                    headers={"content-type": "application/json"},
                )
            return Attempt(
                status=response.status_code,
                request_bytes=payload,
                response_bytes=response.content,
                seconds=time.monotonic() - started,
            )
        except httpx.TimeoutException as exc:
            return Attempt(
                transport_error=type(exc).__name__,
                timeout=True,
                request_bytes=payload,
                seconds=time.monotonic() - started,
            )
        except httpx.TransportError as exc:
            return Attempt(
                transport_error=type(exc).__name__,
                request_bytes=payload,
                seconds=time.monotonic() - started,
            )

    return send


def _wait_ready(
    base_url: str,
    process: subprocess.Popen[bytes],
    timeout_s: float,
    stopping: Callable[[], bool] = lambda: False,
) -> bool:
    import httpx

    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        if process.poll() is not None or stopping():
            return False
        try:
            with httpx.Client(base_url=base_url, timeout=5.0, trust_env=False) as client:
                if client.get("/health").status_code == 200:
                    return True
        except httpx.HTTPError:
            pass
        time.sleep(2.0)
    return False


def _stop_engine(process: subprocess.Popen[bytes]) -> int | None:
    if process.poll() is None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=ENGINE_STOP_S)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    return process.returncode


def cmd_open(args: argparse.Namespace) -> int:
    """Rate one packet shard with the open-weight rater inside the lane container.

    Exit codes: 0 every item has a record; 3 stopped by a signal with items
    left ``unrated`` (rerun them); 1 a fatal provider error; 2 the run could
    not start (doctor, engine). ``main`` leaves with ``os._exit`` so no thread
    or engine child keeps the container alive.
    """
    out: Path = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    packets = load_packets(args.evidence, args.expected_evidence_sha256)
    base_url = f"http://{OPEN_WEIGHT['host']}:{OPEN_WEIGHT['port']}"
    runner = Runner(
        str(OPEN_WEIGHT["rater_id"]),
        out,
        openai_sender(base_url),
        openai_reply,
        workers=int(OPEN_WEIGHT["workers"]),
    )
    _install_stop(runner)
    started = utc_now()
    result: dict[str, Any] = {}
    engine: dict[str, Any] = {}
    process: subprocess.Popen[bytes] | None = None
    log = None
    error: str | None = None
    try:
        try:
            doctor = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "harness.q2_mutation.rater_runner",
                    "args-doctor",
                    "--out",
                    str(out / "args-doctor.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            raise SystemExit("vLLM args doctor timed out; the engine was not started") from exc
        if doctor.returncode != 0:
            (out / "args-doctor.stderr.txt").write_text(doctor.stderr, encoding="utf-8")
            raise SystemExit("vLLM args doctor failed; the engine was not started")
        if runner.stop.is_set():
            raise SystemExit("stopped by a signal before the engine started; nothing was rated")
        model_dir = f"{args.model_root}/{OPEN_WEIGHT['model_id']}"
        argv = engine_argv(model_dir)
        env = engine_env(out)
        log = (out / "engine.log").open("ab")
        started_engine = time.monotonic()
        process = subprocess.Popen(
            argv,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
            cwd=env["TMPDIR"],
        )
        engine.update({"argv": argv, "env": {k: env[k] for k in ENGINE_ENV}})
        ready = _wait_ready(
            base_url, process, float(OPEN_WEIGHT["ready_timeout_s"]), runner.stop.is_set
        )
        engine["ready_s"] = round(time.monotonic() - started_engine, 1)
        if not ready:
            engine["ready"] = False
            raise SystemExit("the vLLM engine did not become ready; nothing was rated")
        engine["ready"] = True
        import httpx

        with httpx.Client(base_url=base_url, timeout=30.0, trust_env=False) as client:
            listing = client.get("/v1/models")
            engine["models_response_sha256"] = sha256_bytes(listing.content)
            engine["models"] = [m.get("id") for m in listing.json().get("data", [])]
            try:
                version = client.get("/version")
                engine["vllm_version"] = (
                    version.json().get("version") if version.is_success else None
                )
            except (httpx.HTTPError, ValueError):
                engine["vllm_version"] = None
        if engine["models"] != [OPEN_WEIGHT["served_name"]]:
            raise SystemExit(f"the engine serves {engine['models']}, not the rater model")
        rating_started = time.monotonic()
        result = runner.run(packets)
        engine["rating_s"] = round(time.monotonic() - rating_started, 1)
    except BaseException as exc:
        error = f"{type(exc).__name__}: {str(exc)[:400]}"
        raise
    finally:
        if process is not None:
            stop_started = time.monotonic()
            engine["exit_code"] = _stop_engine(process)
            engine["stop_s"] = round(time.monotonic() - stop_started, 1)
        if log is not None:
            log.close()
        write_receipt(
            out,
            {
                "rater": dict(RATERS[1]),
                "model": {
                    k: OPEN_WEIGHT[k]
                    for k in (
                        "model_id",
                        "repo_id",
                        "revision",
                        "receipt_sha256",
                        "artifact_root_sha256",
                    )
                },
                "lane_model_id": os.environ.get("COTCODEC_MODEL_ID"),
                "params": {
                    k: OPEN_WEIGHT[k]
                    for k in (
                        "temperature",
                        "top_p",
                        "seed",
                        "max_tokens",
                        "enable_thinking",
                        "timeout_s",
                        "workers",
                    )
                },
                "engine": engine,
                "packets": _packets_record(args.evidence, packets),
                "started_at": started,
                "result": result,
                "run_error": error,
                "stop": {
                    "signalled": runner.stop.is_set(),
                    "grace_s": runner.grace_s,
                    "engine_stop_s": ENGINE_STOP_S,
                },
            },
        )
    print(json.dumps(result, sort_keys=True))
    if result.get("fatal"):
        return 1
    return 3 if result.get("unrated") else 0


def _hard_exit(code: int) -> None:
    """Leave now: no interpreter shutdown that a stray thread or child could hold up."""
    with contextlib.suppress(Exception):
        sys.stdout.flush()
        sys.stderr.flush()
    os._exit(code)


# --- CLI ----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    models = sub.add_parser("models", allow_abbrev=False)
    models.add_argument("--out", type=Path, required=True)
    anth = sub.add_parser("anthropic", allow_abbrev=False)
    anth.add_argument("--packets", type=Path, required=True)
    anth.add_argument("--expected-packets-sha256", required=True)
    anth.add_argument("--out", type=Path, required=True)
    doctor = sub.add_parser("args-doctor", allow_abbrev=False)
    doctor.add_argument("--out", type=Path)
    doctor.add_argument(
        "--model-dir",
        type=Path,
        help="also check image input with the model's config, tokenizer and processor files",
    )
    open_ = sub.add_parser("open", allow_abbrev=False)
    # The lane mounts the packet file as its study artifact.
    open_.add_argument("--evidence", type=Path, required=True)
    open_.add_argument("--expected-evidence-sha256", required=True)
    open_.add_argument("--output-dir", type=Path, required=True)
    open_.add_argument("--model-root", default=MODEL_ROOT)
    export = sub.add_parser("export-harness", allow_abbrev=False)
    export.add_argument("--packets", type=Path, nargs="+", required=True)
    export.add_argument("--out", type=Path, required=True, help="new, empty export directory")
    export.add_argument("--manifest-out", type=Path, required=True)
    iso = sub.add_parser("export-isolated", allow_abbrev=False)
    iso.add_argument("--packets", type=Path, nargs="+", required=True)
    iso.add_argument(
        "--iso-root", type=Path, required=True, help="new or empty root; one directory per item"
    )
    iso.add_argument(
        "--manifest-out", type=Path, required=True, help="outside the isolation root"
    )
    ingest_iso = sub.add_parser("ingest-isolated", allow_abbrev=False)
    ingest_iso.add_argument("--packets", type=Path, nargs="+", required=True)
    ingest_iso.add_argument("--manifest", type=Path, required=True)
    ingest_iso.add_argument("--iso-root", type=Path, required=True)
    ingest_iso.add_argument(
        "--answers",
        type=Path,
        required=True,
        help="a JSON list or wrapper of answers, or a directory of <item_id>.json answers",
    )
    ingest_iso.add_argument(
        "--transcripts",
        type=Path,
        required=True,
        help="directory of <item_id>.jsonl: the harness transcript of the agent that rated it",
    )
    ingest_iso.add_argument("--out", type=Path, required=True)
    ingest = sub.add_parser("ingest-harness", allow_abbrev=False)
    ingest.add_argument("--packets", type=Path, nargs="+", required=True)
    ingest.add_argument("--export-manifest", type=Path, required=True)
    ingest.add_argument("--answers", type=Path, required=True)
    ingest.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "models": cmd_models,
        "anthropic": cmd_anthropic,
        "args-doctor": cmd_args_doctor,
        "open": cmd_open,
        "export-harness": cmd_export_harness,
        "ingest-harness": cmd_ingest_harness,
        "export-isolated": cmd_export_isolated,
        "ingest-isolated": cmd_ingest_isolated,
    }
    if args.command != "open":
        return handlers[args.command](args)
    # The lane container's PID 1: whatever happens, the process ends here.
    code = 2
    try:
        code = cmd_open(args)
    except SystemExit as exc:
        print(f"rater_runner open: {exc}", file=sys.stderr)
        code = exc.code if isinstance(exc.code, int) else 2
    except BaseException as exc:  # noqa: BLE001 - report, then leave
        print(f"rater_runner open: {type(exc).__name__}: {exc}", file=sys.stderr)
        code = 2
    _hard_exit(code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
