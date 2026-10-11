"""The Stage B request-replay driver (draft registration v2, sections 7.2-7.3 and 11).

It sends stored request bodies (built by ``requests.rebuild``) to an OpenAI-compatible engine
over a Unix socket (``unix:/path``, the bridge socket, D13) or TCP (``tcp:host:port``, tests),
under one of three registered protocols, and appends one JSON line per reply with fsync:

* ``batch1`` (E-det, P0): one request in flight, in a seeded order (seed 42); the encoder cache
  is reset before every request (prefix caching is off in E-det), so the order cannot matter.
  Resume: a fresh job skips every (label, item) already recorded.
* ``coldwarm`` (E-c1): per item, reset the prefix and encoder caches, send (cold), send again
  at once (warm). Resume at item granularity; a half-done item is redone after a fresh reset.
* ``loaded`` (E-s1a, E-nc): one pass = every item once, over ``streams`` client streams; the
  stream assignment, start offsets and exponential think times are drawn from
  ``random.Random(seed)`` before the pass starts, so the schedule is seeded and independent of
  timing; the prefix and encoder caches are reset at the start of every pass. A pass is
  **atomic**: replies go to ``<label>.partial.jsonl`` and the file is renamed to
  ``<label>.jsonl`` only when every item has replied. A fresh job keeps finished passes and
  moves a partial pass to ``void/`` and reruns it whole from its start, because a resumed pass
  would run under different concurrency (wave 1's resume defect).

Each reply line records the reply text (it stays on the host run root; the repository receives
the digests), its SHA-256, the completion token ids and their SHA-256, the IR parsed by the
frozen H-OSW-fixed parser and its ``ir_sha256`` (S1a's definition), the prompt token-id digest
(S1a's little-endian int64 SHA-256), finish reason, latency, time to first token, the top-1
minus top-2 log-probability margin per token when log-probabilities were asked for, and the
client-side in-flight count at send. Standard library plus the S1a harness.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import random
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_stage1.engine import UnixHTTPConnection, token_ids_sha256

CHAT_PATH = "/v1/chat/completions"
TIMEOUT_S = 600.0
STREAMS = 20
S1A_MEAN_INFLIGHT = 3.7  # S1a's 4B bridge samples: 3.5-3.7 requests running on average


def think_mean_for(
    mean_latency_s: float, streams: int = STREAMS, target_inflight: float = S1A_MEAN_INFLIGHT
) -> float:
    """Think time that puts ``target_inflight`` of ``streams`` in flight on average."""
    return mean_latency_s * (streams / target_inflight - 1.0)


# --------------------------------------------------------------------------- transport
def connection(transport: str, timeout: float) -> http.client.HTTPConnection:
    if transport.startswith("unix:"):
        return UnixHTTPConnection(transport[5:], timeout=timeout)
    if transport.startswith("tcp:"):
        host, port = transport[4:].rsplit(":", 1)
        return http.client.HTTPConnection(host, int(port), timeout=timeout)
    raise ValueError(f"unknown transport {transport!r}")


def reset(transport: str, which: str, timeout: float = 30.0) -> int:
    """POST vLLM's dev-mode ``/reset_prefix_cache`` or ``/reset_encoder_cache``."""
    if which not in ("prefix", "encoder"):
        raise ValueError(which)
    conn = connection(transport, timeout)
    try:
        conn.request("POST", f"/reset_{which}_cache", body=b"", headers={"Content-Length": "0"})
        response = conn.getresponse()
        response.read()
        if response.status != 200:
            raise RuntimeError(f"/reset_{which}_cache answered HTTP {response.status}")
        return response.status
    finally:
        conn.close()


def post_stream(
    transport: str,
    body: Mapping[str, Any],
    timeout: float = TIMEOUT_S,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Send one stored body and fold its SSE stream."""
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    conn = connection(transport, timeout)
    started = clock()
    out: dict[str, Any] = {
        "content": "",
        "prompt_token_ids": None,
        "completion_ids": [],
        "margins": [],
        "finish_reason": None,
        "usage": None,
        "t_first": None,
        "done": False,
    }
    pieces: list[str] = []
    try:
        conn.request(
            "POST",
            CHAT_PATH,
            body=payload,
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        )
        response = conn.getresponse()
        if response.status != 200:
            text = response.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"HTTP {response.status}: {text}")
        while True:
            raw = response.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                out["done"] = True
                break
            chunk = json.loads(data)
            if "error" in chunk and not chunk.get("choices"):
                raise RuntimeError(f"engine error in stream: {json.dumps(chunk['error'])[:300]}")
            if out["prompt_token_ids"] is None and chunk.get("prompt_token_ids") is not None:
                out["prompt_token_ids"] = [int(t) for t in chunk["prompt_token_ids"]]
            if chunk.get("usage"):
                out["usage"] = chunk["usage"]
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    if out["t_first"] is None:
                        out["t_first"] = clock()
                    pieces.append(delta["content"])
                out["completion_ids"].extend(int(t) for t in choice.get("token_ids") or [])
                for entry in (choice.get("logprobs") or {}).get("content") or []:
                    tops = sorted(
                        (t.get("logprob", 0.0) for t in entry.get("top_logprobs") or []),
                        reverse=True,
                    )
                    out["margins"].append(round(tops[0] - tops[1], 5) if len(tops) >= 2 else None)
                if choice.get("finish_reason"):
                    out["finish_reason"] = choice["finish_reason"]
    finally:
        conn.close()
    if not out["done"]:
        raise RuntimeError("the stream ended before [DONE]")
    out["content"] = "".join(pieces)
    out["latency_s"] = round(clock() - started, 4)
    out["ttft_s"] = None if out["t_first"] is None else round(out["t_first"] - started, 4)
    return out


# --------------------------------------------------------------------------- replies
def ir_of(
    response: str, original: tuple[int, int] = (1920, 1080)
) -> tuple[list[dict[str, Any]], str, str | None]:
    """The canonical IR of an H-OSW-fixed reply, as ``agents.HOswFixed`` derives it (a reply
    that yields no valid IR gives ``[]``, the harness's no-action rule) and S1a's
    ``ir_sha256`` of it."""
    from harness.q2.action_path import controls
    from harness.q2.action_path.upstream.osworld_bfd62bdc_fixed import Qwen35VLAgent
    from harness.q2_stage1 import agents
    from harness.q2_stage1.driver import sha256_json

    width, height = original
    try:
        _, raw = Qwen35VLAgent(coordinate_type="relative").parse_response(
            response or "",
            original_width=width,
            original_height=height,
            processed_width=width,
            processed_height=height,
        )
        ir = [action.to_dict() for action in controls.to_ir(raw)]
        agents.check_typeable(ir)
        error = None
    except Exception as exc:  # noqa: BLE001 - the harness's no-action rule
        ir, error = [], f"{type(exc).__name__}: {str(exc)[:200]}"
    return ir, sha256_json(ir), error


def reply_record(
    item: Mapping[str, Any], label: str, result: Mapping[str, Any], **extra: Any
) -> dict[str, Any]:
    ir, ir_sha, error = ir_of(result["content"])
    ids = result.get("prompt_token_ids")
    comp = result.get("completion_ids") or []
    return {
        "label": label,
        "item": item["id"],
        "cell": item.get("cell"),
        "task": item.get("task"),
        "pair": item.get("pair"),
        "step": item.get("step"),
        "body_sha256": item.get("body_sha256"),
        "content": result["content"],
        "content_sha256": hashlib.sha256(result["content"].encode("utf-8")).hexdigest(),
        "completion_ids": comp,
        "completion_ids_sha256": token_ids_sha256(comp) if comp else None,
        "ir": ir,
        "ir_sha256": ir_sha,
        "parse_error": error,
        "prompt_ids_sha256": token_ids_sha256(ids) if ids is not None else None,
        "prompt_id_count": len(ids) if ids is not None else 0,
        "finish_reason": result.get("finish_reason"),
        "latency_s": result.get("latency_s"),
        "ttft_s": result.get("ttft_s"),
        "margins": result.get("margins") or None,
        "usage": result.get("usage"),
        **extra,
    }


class Appender:
    """Append-only JSONL with fsync after every line (thread-safe)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def write(self, record: Mapping[str, Any]) -> None:
        line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
        with self.lock, open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                break  # a torn last line from a cut job: ignored, the item reruns
    return out


def load_items(corpus: Path) -> list[dict[str, Any]]:
    """Corpus lines: ``{"id", "cell", "task", "pair", "step", "body_sha256", "body_path"}``; the
    body file must hash to ``body_sha256`` (canonical JSON) or the item is refused."""
    from harness.r01.requests import body_sha256

    items = []
    for row in read_jsonl(corpus):
        path = Path(row["body_path"])
        if not path.is_absolute():
            path = Path(corpus).parent / path
        body = json.loads(path.read_text(encoding="utf-8"))
        if body_sha256(body) != row["body_sha256"]:
            raise ValueError(f"body of {row['id']} does not match its digest")
        items.append({**row, "body": body})
    return items


def seeded_order(items: Sequence[Mapping[str, Any]], seed: int) -> list[Mapping[str, Any]]:
    order = sorted(items, key=lambda it: it["id"])
    random.Random(seed).shuffle(order)
    return order


# --------------------------------------------------------------------------- protocols
def run_batch1(
    transport: str,
    items: Sequence[Mapping[str, Any]],
    *,
    label: str,
    seed: int,
    out: Path,
    reset_encoder: bool = True,
    body_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    post: Callable[..., dict[str, Any]] = post_stream,
) -> dict[str, Any]:
    done = {r["item"] for r in read_jsonl(out) if r.get("label") == label and "error" not in r}
    app = Appender(out)
    sent = 0
    for item in seeded_order(items, seed):
        if item["id"] in done:
            continue
        if reset_encoder:
            reset(transport, "encoder")
        body = body_fn(item["body"]) if body_fn else item["body"]
        try:
            result = post(transport, body)
        except Exception as exc:  # noqa: BLE001 - recorded; the missing-data rule reads it
            app.write(
                {
                    "label": label,
                    "item": item["id"],
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                }
            )
            continue
        app.write(reply_record(item, label, result, protocol="batch1", inflight_client=1))
        sent += 1
    return {"label": label, "sent": sent, "skipped": len(done)}


def run_coldwarm(
    transport: str,
    items: Sequence[Mapping[str, Any]],
    *,
    label: str,
    seed: int,
    out: Path,
    post: Callable[..., dict[str, Any]] = post_stream,
) -> dict[str, Any]:
    rows = read_jsonl(out)
    roles: dict[str, set[str]] = {}
    for r in rows:
        if r.get("label") == label and "error" not in r:
            roles.setdefault(r["item"], set()).add(r.get("role"))
    done = {k for k, v in roles.items() if {"cold", "warm"} <= v}
    app = Appender(out)
    sent = 0
    for item in seeded_order(items, seed):
        if item["id"] in done:
            continue
        reset(transport, "prefix")
        reset(transport, "encoder")
        for role in ("cold", "warm"):
            result = post(transport, item["body"])
            app.write(
                reply_record(item, label, result, protocol="coldwarm", role=role, inflight_client=1)
            )
            sent += 1
    return {"label": label, "sent": sent, "skipped": len(done)}


def loaded_schedule(
    item_ids: Sequence[str], *, seed: int, streams: int, think_mean_s: float
) -> dict[str, Any]:
    """The seeded schedule of one loaded pass: items dealt to streams after a seeded shuffle,
    a start offset per stream (uniform on [0, think_mean)) and an exponential think time after
    every item, all drawn before the pass starts."""
    rng = random.Random(seed)
    order = sorted(item_ids)
    rng.shuffle(order)
    lanes = [order[s::streams] for s in range(streams)]
    offsets = [rng.uniform(0.0, think_mean_s) for _ in range(streams)]
    thinks = [
        [rng.expovariate(1.0 / think_mean_s) if think_mean_s > 0 else 0.0 for _ in lane]
        for lane in lanes
    ]
    return {"lanes": lanes, "offsets": offsets, "thinks": thinks}


def run_loaded_pass(
    transport: str,
    items: Sequence[Mapping[str, Any]],
    *,
    label: str,
    seed: int,
    out_dir: Path,
    streams: int = STREAMS,
    think_mean_s: float,
    sleep: Callable[[float], None] = time.sleep,
    post: Callable[..., dict[str, Any]] = post_stream,
    sample_every_s: float | None = 1.0,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    final, partial = out_dir / f"{label}.jsonl", out_dir / f"{label}.partial.jsonl"
    if final.exists():
        return {"label": label, "status": "kept", "replies": len(read_jsonl(final))}
    voided = None
    if partial.exists():
        void = out_dir / "void"
        void.mkdir(parents=True, exist_ok=True)
        voided = void / f"{label}.{int(time.time())}.jsonl"
        partial.rename(voided)
    by_id = {it["id"]: it for it in items}
    schedule = loaded_schedule(list(by_id), seed=seed, streams=streams, think_mean_s=think_mean_s)
    reset(transport, "prefix")
    reset(transport, "encoder")
    app = Appender(partial)
    lock = threading.Lock()
    state = {"inflight": 0, "errors": 0, "samples": []}
    stop = threading.Event()

    def sampler() -> None:
        while not stop.is_set():
            with lock:
                state["samples"].append(state["inflight"])
            stop.wait(sample_every_s or 1.0)

    def lane(s: int) -> None:
        sleep(schedule["offsets"][s])
        lane_items = schedule["lanes"][s]
        for index, (item_id, think) in enumerate(
            zip(lane_items, schedule["thinks"][s], strict=True)
        ):
            item = by_id[item_id]
            with lock:
                state["inflight"] += 1
                inflight = state["inflight"]
            try:
                result = post(transport, item["body"])
                app.write(
                    reply_record(
                        item,
                        label,
                        result,
                        protocol="loaded",
                        stream=s,
                        inflight_client=inflight,
                        seed=seed,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - an incomplete pass is voided below
                with lock:
                    state["errors"] += 1
                app.write(
                    {
                        "label": label,
                        "item": item_id,
                        "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                    }
                )
            finally:
                with lock:
                    state["inflight"] -= 1
            if index < len(lane_items) - 1:  # the pass ends at its last reply
                sleep(think)

    threads = [threading.Thread(target=lane, args=(s,), daemon=True) for s in range(streams)]
    sample_thread = threading.Thread(target=sampler, daemon=True) if sample_every_s else None
    if sample_thread:
        sample_thread.start()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    stop.set()
    rows = read_jsonl(partial)
    ok = {r["item"] for r in rows if "error" not in r}
    complete = ok == set(by_id) and state["errors"] == 0
    summary = {
        "label": label,
        "replies": len(ok),
        "items": len(by_id),
        "errors": state["errors"],
        "voided_previous": str(voided) if voided else None,
        "inflight_mean": round(sum(state["samples"]) / len(state["samples"]), 3)
        if state["samples"]
        else None,
        "inflight_max": max(state["samples"]) if state["samples"] else None,
    }
    if complete:
        partial.rename(final)
        summary["status"] = "complete"
    else:
        summary["status"] = "incomplete (rerun the whole pass in a fresh job)"
    (out_dir / f"{label}.summary.json").write_text(json.dumps(summary, indent=1))
    return summary


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--transport", required=True, help="unix:/engine/engine.sock or tcp:host:port")
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--protocol", choices=("batch1", "coldwarm", "loaded"), required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument(
        "--out",
        type=Path,
        required=True,
        help="results JSONL (batch1, coldwarm) or directory (loaded)",
    )
    ap.add_argument("--cells", default=None, help="comma-separated cells to send (default: all)")
    ap.add_argument("--streams", type=int, default=STREAMS)
    ap.add_argument("--think-mean-s", type=float, default=None)
    ap.add_argument("--no-logprobs", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)
    items = load_items(args.corpus)
    if args.cells:
        keep = set(args.cells.split(","))
        items = [it for it in items if it["cell"] in keep]
    if args.no_logprobs:
        from harness.r01.requests import without_logprobs

        items = [{**it, "body": without_logprobs(it["body"])} for it in items]
    if args.protocol == "batch1":
        summary = run_batch1(args.transport, items, label=args.label, seed=args.seed, out=args.out)
    elif args.protocol == "coldwarm":
        summary = run_coldwarm(
            args.transport, items, label=args.label, seed=args.seed, out=args.out
        )
    else:
        if args.think_mean_s is None:
            raise SystemExit("--think-mean-s is required for the loaded protocol")
        summary = run_loaded_pass(
            args.transport,
            items,
            label=args.label,
            seed=args.seed,
            out_dir=args.out,
            streams=args.streams,
            think_mean_s=args.think_mean_s,
        )
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
