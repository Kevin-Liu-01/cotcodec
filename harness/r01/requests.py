"""Stage B request corpus (draft registration v2, section 7.1).

A step-k request is rebuilt by the frozen H-OSW-fixed client (``agents.HOswFixed``, unmodified)
driven by a stub engine that returns S1a's recorded replies for steps 1..k-1, observing the
given raw frames. The body is the one ``engine.EngineClient.body`` sends (S1a's registered
sampling, ``stream``, ``stream_options``, ``return_token_ids``) plus, identically in every arm,
``logprobs`` and ``top_logprobs`` (dropped everywhere if P0 shows they change outputs).

Step 1 carries no earlier reply, so a rebuilt step-1 request is what S1a's engine received at
step 1 up to the screenshot's pixels: the live-decode against fresh-prefill gap of
arXiv 2607.28495 cannot arise there. Step 2 carries S1a's step-1 reply as text, so its cache
path differs from S1a's (disclosed; step 2 is secondary).

Observation composites for a task's boot pair (a, b) and the fitted clock box (section 7.1):

    R = a        C = a with b's clock box      O = b with a's clock box      X = b

so C differs from R only inside the box (clock only), O differs from R only outside it
(non-clock only), and X differs in both (the natural cross-boot difference). At step 2 the
step-1 frame and reply are a's in every variant; only the newest frame varies.

Prompt-id fidelity: vLLM's prompt token ids cover text and image-placeholder counts, not pixels,
so every variant of a request has the reference's ids, and a rebuilt step-k request's ids must
equal S1a's recorded ``prompt_ids_sha256`` for that step (section 7.1's negative control).
Standard library plus the S1a harness (Pillow for the composites).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from harness.q2_stage1 import agents
from harness.q2_stage1.engine import Completion, EngineClient

SAMPLING = {"temperature": 0.0, "top_p": 0.9, "top_k": -1, "max_tokens": 2048}
SERVED_MODEL = "s1a-model"
PROMPT_DATE = "2026-10-08"
LOGPROB_FIELDS = {"logprobs": True, "top_logprobs": 5}
CELLS_STEP1 = ("R", "C", "O", "X")
CELLS_STEP2 = ("R2", "C2", "O2", "X2")


class StubEngine:
    """Returns S1a's recorded replies in order; never touches a socket."""

    def __init__(self, replies: Sequence[str]):
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages: Sequence[Mapping[str, Any]], sampling: Mapping[str, Any]):
        if self.calls >= len(self.replies):
            raise RuntimeError("the stub engine has no recorded reply left")
        text = self.replies[self.calls]
        self.calls += 1
        return Completion(
            content=text,
            finish_reason="stop",
            prompt_tokens=None,
            completion_tokens=None,
            cached_tokens=None,
            prompt_ids_sha256=None,
            prompt_id_count=0,
            latency_s=0.0,
            ttft_s=None,
            tpot_s=None,
            request_sha256="stub",
        )


def canonical(body: Mapping[str, Any]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def body_sha256(body: Mapping[str, Any]) -> str:
    """The digest S1a's ``engine.request_sha256`` computes (canonical JSON)."""
    return hashlib.sha256(canonical(body)).hexdigest()


def rebuild(
    instruction: str,
    frames: Sequence[bytes],
    replies: Sequence[str],
    *,
    date: str = PROMPT_DATE,
    sampling: Mapping[str, Any] = SAMPLING,
    served_model: str = SERVED_MODEL,
    logprobs: bool = True,
) -> dict[str, Any]:
    """The step-``len(frames)`` request of an H-OSW-fixed episode whose earlier replies were
    ``replies`` (``len(replies) == len(frames) - 1``)."""
    if len(frames) < 1 or len(replies) != len(frames) - 1:
        raise ValueError("a step-k request needs k frames and k-1 earlier replies")
    stub = StubEngine(replies)
    today = datetime.strptime(date, "%Y-%m-%d")
    client = agents.make_client("H-OSW-fixed", instruction, stub, dict(sampling), today)  # type: ignore[arg-type]
    shots = []
    for i, png in enumerate(frames):
        shots.append(client.observe(png))
        if i < len(frames) - 1:
            client.act()
    messages = client.messages()
    body = EngineClient("/unused", served_model).body(messages, dict(sampling))
    if logprobs:
        body.update(LOGPROB_FIELDS)
    return {
        "step": len(frames),
        "body": body,
        "body_sha256": body_sha256(body),
        "messages_sha256": agents.messages_sha256(messages),
        "raw_sha256": [s.raw_sha256 for s in shots],
        "processed_sha256": [s.processed_sha256 for s in shots],
        "date_line": client.date_line,
    }


def without_logprobs(body: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in body.items() if k not in LOGPROB_FIELDS}


def composites(a: bytes, b: bytes, box: Any) -> dict[str, bytes]:
    """The 2 x 2 of region provenance for frames ``a`` (reference) and ``b`` (other boot)."""
    from harness.r01.regions import swap_box

    return {"R": a, "C": swap_box(a, b, box), "O": swap_box(b, a, box), "X": b}


def pair_requests(
    instruction: str,
    a_step1: bytes,
    b_step1: bytes,
    box: Any,
    *,
    reply1: str | None = None,
    a_step2: bytes | None = None,
    b_step2: bytes | None = None,
    logprobs: bool = True,
) -> dict[str, dict[str, Any]]:
    """Every cell's request for one boot pair: R, C, O, X at step 1 and, when the step-2 frames
    and S1a's step-1 reply are given, R2, C2, O2, X2 (step-1 frame a and the reply fixed)."""
    out: dict[str, dict[str, Any]] = {}
    for cell, frame in composites(a_step1, b_step1, box).items():
        out[cell] = rebuild(instruction, [frame], [], logprobs=logprobs)
    if reply1 is not None and a_step2 is not None and b_step2 is not None:
        for cell, frame in composites(a_step2, b_step2, box).items():
            out[cell + "2"] = rebuild(instruction, [a_step1, frame], [reply1], logprobs=logprobs)
    return out


def check_composites(a: bytes, b: bytes, box: Any) -> dict[str, bool]:
    """The manipulation checks each pair must pass before its requests enter the corpus:
    C differs from R only inside the box, O from R only outside it, and the pair's clock
    boxes differ (otherwise the clock factor is absent for that pair: reported, dropped from
    the clock cells)."""
    from harness.r01.regions import differs_inside, differs_outside

    comp = composites(a, b, box)
    return {
        "clock_differs": differs_inside(a, b, box),
        "C_inside_only": not differs_outside(comp["R"], comp["C"], box),
        "O_outside_only": not differs_inside(comp["R"], comp["O"], box),
        "nonclock_differs": differs_outside(a, b, box),
    }


def fidelity(observed: Mapping[str, str | None], recorded: Mapping[str, str]) -> dict[str, Any]:
    """Section 7.1's prompt-id check: ``observed`` and ``recorded`` map request ids to prompt
    token-id digests. A request fails when its digest is missing or differs. More than 10%
    failing stops Stage B before any estimand is read."""
    failing = sorted(k for k in recorded if observed.get(k) is None or observed[k] != recorded[k])
    n = len(recorded)
    share = len(failing) / n if n else 0.0
    return {"n": n, "failing": failing, "share": round(share, 4), "stop": share > 0.10}


def choose_episode(
    task_id: str, candidates: Sequence[Mapping[str, Any]], seed: int = 42
) -> Mapping[str, Any]:
    """Seeded choice of the S1a episode whose step-1 reply builds a task's step-2 requests:
    among 4B H-OSW-fixed episodes with at least two steps, a step-1 IR that is a non-empty,
    non-terminal action list and no parse error, the one with the smallest
    SHA-256(seed, task, session, rerun)."""
    ok = [
        c
        for c in candidates
        if c.get("steps", 0) >= 2
        and c.get("step1_ir")
        and not c.get("step1_parse_error")
        and all(a.get("op") != "terminate" for a in c["step1_ir"])
    ]
    if not ok:
        raise ValueError(f"task {task_id} has no eligible episode")

    def rank(c: Mapping[str, Any]) -> str:
        return hashlib.sha256(f"{seed}:{task_id}:{c['session']}:{c['rerun']}".encode()).hexdigest()

    return min(ok, key=rank)
