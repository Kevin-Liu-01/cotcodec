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
    The self-hosted open-weight rater: Qwen3.5-9B at a pinned Hugging Face
    revision, verified against its model receipt by the lane, served by
    ``vllm serve`` on 127.0.0.1 inside the network-less container with fixed
    engine flags; greedy decoding (temperature 0, top_p 1, seed 42),
    ``max_tokens`` 256, thinking off through the chat template.
``args-doctor`` (CPU, inside the vLLM image)
    vLLM's own parsers accept the engine argv and the request payload.
``models`` (anthropic)
    Record the Anthropic model object only.

Rules shared by both raters (preregistration section 9):

* one call per rater per item: an item with any record in ``calls.jsonl`` is
  never sent again, so a resumed run skips it;
* retries only on transport errors (connection failure, timeout, HTTP 408,
  409, 429, 500, 502, 503, 504, 529), at most ``MAX_TRANSPORT_RETRIES``;
  after the last one the item is ``transport_exhausted``;
* the answer is the first word of the reply (``raters.parse_first_token``); a
  refusal, an empty or unparseable reply, a timeout, an exhausted transport
  or a request the provider rejected (HTTP 400 or 413, for example a packet
  over the context window) is ``unsure``; an authentication, permission or
  unknown-model error stops the run instead (nothing is rated);
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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.q2_mutation.raters import (
    RATER_PROMPT_V1,
    RATERS,
    answer_for,
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

ANTHROPIC: Mapping[str, Any] = {
    "rater_id": "model-rater-anthropic",
    "model": "claude-opus-5-5",
    "max_tokens": 16000,
    "effort": "high",
    "timeout_s": 600.0,
    "workers": 4,
}
OPEN_WEIGHT: Mapping[str, Any] = {
    "rater_id": "model-rater-open-weight",
    "model_id": "qwen3.5-9b",
    "repo_id": "Qwen/Qwen3.5-9B",
    "revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
    "receipt_sha256": "0a9e052d561b017c505adf5a1c6fcdc048522660a0db134486b84edbf3de5cb3",
    "artifact_root_sha256": "9845026dbe255e24b105224eebbb5436d315713b9a5c53c434137896b160c5b1",
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
# probes validated this image, model and the image-limit form).
ENGINE_FLAGS: tuple[tuple[str, Any], ...] = (
    ("dtype", "bfloat16"),
    ("seed", 42),
    ("tensor_parallel_size", 1),
    ("max_model_len", 131072),
    ("gpu_memory_utilization", 0.90),
    ("max_num_seqs", 16),
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
    outcome: str  # ok | refusal | empty | request_rejected | timeout | transport_exhausted
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
) -> tuple[Attempt, list[dict[str, Any]]]:
    """Send once, and again only after a transport error, at most ``retries`` times."""
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
        if not is_transport(attempt) or number == retries:
            break
        sleep(BACKOFF_S[min(number, len(BACKOFF_S) - 1)])
    return attempt, log


def anthropic_reply(attempt: Attempt) -> Reply:
    if is_transport(attempt):
        return Reply("timeout" if attempt.timeout else "transport_exhausted")
    if attempt.status != 200 or attempt.response_bytes is None:
        return Reply("request_rejected", extra={"status": attempt.status})
    body = json.loads(attempt.response_bytes)
    texts = [b.get("text", "") for b in body.get("content", []) if b.get("type") == "text"]
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
    body = json.loads(attempt.response_bytes)
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return Reply(
        "ok",
        text=message.get("content"),
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


def read_calls(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    calls: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            calls[row["item_id"]] = row
    return calls


def answers(calls_path: Path, item_ids: Iterable[str]) -> dict[str, tuple[str, str]]:
    """(answer, status) per item; an item without a call record is ``unrated`` (unsure)."""
    calls = read_calls(calls_path)
    out = {}
    for item_id in item_ids:
        row = calls.get(item_id)
        out[item_id] = (row["answer"], row["status"]) if row else answer_for("unrated", None)
    return out


class Runner:
    """Rate every packet once with one rater, append-only, resumable."""

    def __init__(
        self,
        rater_id: str,
        out_dir: Path,
        send: Callable[[str, bytes], Attempt],
        parse: Callable[[Attempt], Reply],
        *,
        workers: int,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.rater_id = rater_id
        self.out_dir = out_dir
        self.send = send
        self.parse = parse
        self.workers = workers
        self.sleep = sleep
        self.calls_path = out_dir / "calls.jsonl"
        self.responses = out_dir / "responses"
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.fatal: str | None = None

    def run(self, packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.responses.mkdir(exist_ok=True)
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
                    lambda: self.send(item_id, payload), sleep=self.sleep
                )
            except FatalRunError as exc:
                self.fatal = str(exc)
                self.stop.set()
                return
            reply = self.parse(attempt)
            record = call_record(self.rater_id, item_id, index, body, attempt, log, reply, started)
            with self.lock:
                if attempt.response_bytes is not None:
                    (self.responses / f"{item_id}.json").write_bytes(attempt.response_bytes)
                with self.calls_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            list(pool.map(one, todo))
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
        }


def write_receipt(out_dir: Path, receipt: Mapping[str, Any]) -> dict[str, Any]:
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
        runner.stop.set()

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
    result = runner.run(packets)
    receipt = write_receipt(
        args.out,
        {
            "rater": dict(RATERS[0]),
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
        },
    )
    print(json.dumps({"calls_sha256": receipt["calls_sha256"], **result}, sort_keys=True))
    return 1 if result["fatal"] else 0


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


def cmd_args_doctor(args: argparse.Namespace) -> int:
    report = args_doctor()
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


def _wait_ready(base_url: str, process: subprocess.Popen[bytes], timeout_s: float) -> bool:
    import httpx

    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        if process.poll() is not None:
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
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    return process.returncode


def cmd_open(args: argparse.Namespace) -> int:
    out: Path = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    packets = load_packets(args.evidence, args.expected_evidence_sha256)
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
    )
    if doctor.returncode != 0:
        (out / "args-doctor.stderr.txt").write_text(doctor.stderr, encoding="utf-8")
        raise SystemExit("vLLM args doctor failed; the engine was not started")
    model_dir = f"{args.model_root}/{OPEN_WEIGHT['model_id']}"
    base_url = f"http://{OPEN_WEIGHT['host']}:{OPEN_WEIGHT['port']}"
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
    engine: dict[str, Any] = {"argv": argv, "env": {k: env[k] for k in ENGINE_ENV}}
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
    try:
        ready = _wait_ready(base_url, process, float(OPEN_WEIGHT["ready_timeout_s"]))
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
        result = runner.run(packets)
    finally:
        engine["exit_code"] = _stop_engine(process)
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
            },
        )
    print(json.dumps(result, sort_keys=True))
    return 1 if result.get("fatal") else 0


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
    open_ = sub.add_parser("open", allow_abbrev=False)
    # The lane mounts the packet file as its study artifact.
    open_.add_argument("--evidence", type=Path, required=True)
    open_.add_argument("--expected-evidence-sha256", required=True)
    open_.add_argument("--output-dir", type=Path, required=True)
    open_.add_argument("--model-root", default=MODEL_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "models": cmd_models,
        "anthropic": cmd_anthropic,
        "args-doctor": cmd_args_doctor,
        "open": cmd_open,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
