"""Synthetic prompts and harness message policies for the serving probe.

Text is random tokens of the served model's tokenizer, sized like vLLM's random
dataset (decode, re-encode, truncate). Two harness policies rebuild the exact
message layout of the agents Stage 1 would run:

* ``h1`` follows OSWorld ``mm_agents/qwen3vl_agent.py`` @b138d348: a system
  prompt, a sliding window of ``history_n`` previous screenshots and responses,
  the instruction on the first windowed user turn with the actions that fell out
  of the window, then the current screenshot.
* ``h2`` follows cua-speedrun ``agents/qwen35/agent.py`` @be17c72c: all
  responses kept (``history_n`` 100), screenshots beyond ``image_max`` folded in
  blocks of ``fold_size`` into a fixed placeholder, tool-response wrappers
  around later screenshots.

Generated text from the server is used as the assistant history, as the real
harnesses do, but it is never parsed, executed or written to disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

COLLAPSED_SCREENSHOT_TEXT = "This screenshot has been collapsed."
#: Chat-template tokens around one image for Qwen3.5 (vision_start, vision_end).
IMAGE_WRAPPER_TOKENS = 2


class Tokenizer(Protocol):
    vocab_size: int
    all_special_ids: list[int]

    def encode(self, text: str, add_special_tokens: bool = ...) -> list[int]: ...

    def decode(self, ids: Sequence[int]) -> str: ...


def allowed_token_ids(tokenizer: Tokenizer) -> np.ndarray:
    """Return the non-special token ids random text is drawn from."""
    special = set(int(token) for token in tokenizer.all_special_ids)
    allowed = np.array(
        [token for token in range(int(tokenizer.vocab_size)) if token not in special],
        dtype=np.int64,
    )
    if allowed.size == 0:
        raise ValueError("tokenizer has no non-special tokens")
    return allowed


def random_token_ids(allowed: np.ndarray, rng: np.random.Generator, count: int) -> list[int]:
    if count <= 0:
        return []
    return allowed[rng.integers(0, allowed.size, size=count)].tolist()


def random_text(
    tokenizer: Tokenizer, allowed: np.ndarray, rng: np.random.Generator, n_tokens: int
) -> str:
    """Return text that re-encodes to ``n_tokens`` tokens (bounded retries)."""
    if n_tokens <= 0:
        return ""
    ids = random_token_ids(allowed, rng, n_tokens)
    text = tokenizer.decode(ids)
    for _attempt in range(8):
        encoded = tokenizer.encode(text, add_special_tokens=False)
        if len(encoded) == n_tokens:
            return text
        if len(encoded) > n_tokens:
            text = tokenizer.decode(encoded[:n_tokens])
        else:
            text = text + tokenizer.decode(random_token_ids(allowed, rng, n_tokens - len(encoded)))
    return text


def text_rng(seed: int, *stream: int) -> np.random.Generator:
    """Independent text stream: the image stream never perturbs the text."""
    return np.random.default_rng([seed, 1, *stream])


def image_seed(seed: int, *stream: int) -> tuple[int, ...]:
    return (seed, 2, *stream)


def image_part(url: str) -> dict[str, Any]:
    return {"type": "image_url", "image_url": {"url": url}}


def text_part(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def open_loop_messages(prefix: str, body: str, image_urls: Sequence[str]) -> list[dict[str, Any]]:
    """Shared system prefix, then one user turn with the body text and images last."""
    content = [text_part(body)] + [image_part(url) for url in image_urls]
    return [
        {"role": "system", "content": [text_part(prefix)]},
        {"role": "user", "content": content},
    ]


def h1_instruction(task: str, actions_outside_window: Sequence[str]) -> str:
    previous = "\n".join(
        f"Step {index + 1}: {action}" for index, action in enumerate(actions_outside_window)
    )
    return (
        "\nPlease generate the next move according to the UI screenshot, instruction "
        "and previous actions.\n\n"
        f"Instruction: {task}\n\nPrevious actions:\n{previous}"
    )


def h1_messages(
    *,
    system: str,
    task: str,
    screenshots: Sequence[str],
    responses: Sequence[str],
    actions: Sequence[str],
    history_n: int,
    a11y: str = "",
) -> list[dict[str, Any]]:
    """OSWorld qwen3vl_agent layout; ``screenshots[-1]`` is the current one."""
    if len(screenshots) != len(responses) + 1:
        raise ValueError("h1 needs one more screenshot than responses")
    current_step = len(responses)
    history_start = max(0, current_step - history_n)
    instruction = h1_instruction(task, actions[:history_start])
    messages: list[dict[str, Any]] = [{"role": "system", "content": [text_part(system)]}]
    history_len = min(history_n, len(responses))
    current_parts: list[dict[str, Any]] = [image_part(screenshots[-1])]
    if history_len > 0:
        history_responses = responses[-history_len:]
        history_screens = screenshots[-history_len - 1 : -1]
        for index in range(history_len):
            parts = [image_part(history_screens[index])]
            if index == 0:
                parts.append(text_part(instruction))
            messages.append({"role": "user", "content": parts})
            messages.append({"role": "assistant", "content": [text_part(history_responses[index])]})
    else:
        current_parts.append(text_part(instruction))
    if a11y:
        current_parts.append(text_part(f"\nAccessibility tree:\n{a11y}"))
    messages.append({"role": "user", "content": current_parts})
    return messages


def folded_prefix(total_screenshots: int, image_max: int, fold_size: int) -> int:
    """cua-speedrun ``_folded_prefix_for``: screenshots replaced by the placeholder."""
    folded = 0
    while total_screenshots - folded > image_max:
        folded += fold_size
    return min(folded, total_screenshots)


def h2_instruction(task: str, actions_before_window: Sequence[str]) -> str:
    previous = "\n".join(
        f"Step {index + 1}: {action}" for index, action in enumerate(actions_before_window)
    )
    return (
        "\nPlease generate the next move according to the UI screenshot, instruction "
        "and previous actions.\n\n"
        f"Instruction: {task}\n\nPrevious actions:\n{previous or 'None'}"
    )


def _tool_response(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [text_part("<tool_response>\n"), *parts, text_part("\n</tool_response>")]


def h2_messages(
    *,
    system: str,
    task: str,
    screenshots: Sequence[str],
    responses: Sequence[str],
    actions: Sequence[str],
    history_n: int,
    image_max: int,
    fold_size: int,
    a11y: str = "",
) -> list[dict[str, Any]]:
    """cua-speedrun build_messages layout with screenshot folding."""
    total = len(screenshots)
    if total != len(responses) + 1:
        raise ValueError("h2 needs one more screenshot than responses")
    folded = folded_prefix(total, image_max, fold_size)
    start_step = max(1, total - history_n)
    instruction = h2_instruction(task, actions[: max(0, min(start_step - 1, len(actions)))])
    messages: list[dict[str, Any]] = [{"role": "system", "content": [text_part(system)]}]
    for step in range(start_step, total + 1):
        first = step == start_step
        if step <= folded:
            if first:
                content = [text_part(instruction)]
            else:
                content = _tool_response([text_part(COLLAPSED_SCREENSHOT_TEXT)])
        else:
            image = image_part(screenshots[step - 1])
            content = [image, text_part(instruction)] if first else _tool_response([image])
        if step == total and a11y:
            content = [*content, text_part(f"\nAccessibility tree:\n{a11y}")]
        messages.append({"role": "user", "content": content})
        if step <= total - 1:
            messages.append({"role": "assistant", "content": [text_part(responses[step - 1])]})
    return messages


def count_images(messages: Sequence[dict[str, Any]]) -> int:
    return sum(
        1
        for message in messages
        for part in message.get("content", [])
        if isinstance(part, dict) and part.get("type") == "image_url"
    )


@dataclass(frozen=True)
class HarnessShape:
    """Token sizes used to model prompt length at unmeasured steps."""

    harness: str
    system_tokens: int
    task_tokens: int
    action_tokens: int
    response_tokens: int
    a11y_tokens: int
    image_tokens: int
    history_n: int
    image_max: int = 20
    fold_size: int = 10


def visible_images(shape: HarnessShape, step: int) -> int:
    """Screenshots carried as images in the prompt at 1-based ``step``."""
    if step < 1:
        raise ValueError("steps are 1-based")
    if shape.harness == "h1":
        return min(step, shape.history_n + 1)
    window_start = max(1, step - shape.history_n)
    folded = folded_prefix(step, shape.image_max, shape.fold_size)
    return step - max(folded, window_start - 1)


def modeled_prompt_tokens(shape: HarnessShape, step: int) -> int:
    """Approximate prompt tokens at ``step`` (used only to extrapolate costs)."""
    images = visible_images(shape, step)
    base = shape.system_tokens + shape.task_tokens + shape.a11y_tokens
    image_tokens = images * (shape.image_tokens + IMAGE_WRAPPER_TOKENS)
    if shape.harness == "h1":
        responses = min(step - 1, shape.history_n)
        actions = max(0, step - 1 - shape.history_n)
        return (
            base + image_tokens + responses * shape.response_tokens + actions * shape.action_tokens
        )
    window = min(step - 1, shape.history_n)
    actions = max(0, step - 1 - shape.history_n)
    return base + image_tokens + window * shape.response_tokens + actions * shape.action_tokens
