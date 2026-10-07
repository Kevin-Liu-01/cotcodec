"""Replay plans with fixed (prebuilt) history for v2.

v1's replays fed each step's generated text back as the next step's assistant
history, so two engines (real and dummy weights) sent different prompts from
step 2 on. v2 prebuilds every response: response ``k`` of an episode is random
text of ``prebuilt_response_tokens`` tokens from the stream
``text_rng(seed, episode, 3, k)`` (v1's stream for its prebuilt history), so a
step's prompt depends only on the point's seed and parameters. The message
layouts are v1's (``harness.serving_probe.prompts``).

A warm-up may list its steps (``step_list``) instead of a contiguous range, so
one episode can replay r3's first steps and then the largest shape.
"""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from harness.serving_probe.client import EpisodePlan
from harness.serving_probe.config import PointSpec
from harness.serving_probe.images import data_url, make_image
from harness.serving_probe.prompts import (
    h1_messages,
    h2_messages,
    image_seed,
    random_text,
    text_rng,
)


def _images(
    kind: str, width: int, height: int, seeds: Sequence[tuple[int, ...]], pool: ThreadPoolExecutor
) -> list[str]:
    return [
        data_url(blob) for blob in pool.map(lambda s: make_image(kind, width, height, s), seeds)
    ]


def replay_steps(params: Any) -> list[int]:
    """The steps a replay sends: ``step_list`` when given, else start_depth+1 .. +steps."""
    listed = params.get("step_list")
    if listed is not None:
        return [int(step) for step in listed]
    depth = int(params["start_depth"])
    return list(range(depth + 1, depth + int(params["steps"]) + 1))


def build_fixed_replay_plans(
    point: PointSpec,
    tokenizer: Any,
    allowed: np.ndarray,
    size: tuple[int, int],
    pool: ThreadPoolExecutor,
) -> list[EpisodePlan]:
    """Episode plans whose every step is built from prebuilt responses only."""
    if point.get("history") != "prebuilt":
        raise ValueError(f"point {point.point_id} does not declare prebuilt history")
    width, height = size
    params = point.params
    episodes = int(params["episodes"])
    measured = replay_steps(params)
    total = max(measured)
    system = random_text(tokenizer, allowed, text_rng(point.seed), int(params["system_tokens"]))
    all_screens = _images(
        "png-rendered",
        width,
        height,
        [image_seed(point.seed, e, step) for e in range(episodes) for step in range(1, total + 1)],
        pool,
    )
    plans: list[EpisodePlan] = []
    for episode in range(episodes):
        task = random_text(
            tokenizer, allowed, text_rng(point.seed, episode, 0), int(params["task_tokens"])
        )
        screens = all_screens[episode * total : (episode + 1) * total]
        actions = [
            random_text(
                tokenizer,
                allowed,
                text_rng(point.seed, episode, 1, step),
                int(params["action_tokens"]),
            )
            for step in range(1, total + 1)
        ]
        a11y = (
            {
                step: random_text(
                    tokenizer,
                    allowed,
                    text_rng(point.seed, episode, 2, step),
                    int(params["a11y_tokens"]),
                )
                for step in measured
            }
            if int(params["a11y_tokens"]) > 0
            else {}
        )
        responses = [
            random_text(
                tokenizer,
                allowed,
                text_rng(point.seed, episode, 3, step),
                int(params["prebuilt_response_tokens"]),
            )
            for step in range(1, total)
        ]

        def build(
            step: int,
            _history: list[str],
            *,
            _screens: list[str] = screens,
            _actions: list[str] = actions,
            _a11y: dict[int, str] = a11y,
            _task: str = task,
            _responses: list[str] = responses,
        ) -> list[dict[str, Any]]:
            # The history argument is ignored: every step uses the prebuilt responses.
            common = {
                "system": system,
                "task": _task,
                "screenshots": _screens[:step],
                "responses": _responses[: step - 1],
                "actions": _actions[: step - 1],
                "history_n": int(params["history_n"]),
                "a11y": _a11y.get(step, ""),
            }
            if params["harness"] == "h1":
                return h1_messages(**common)
            return h2_messages(
                **common, image_max=int(params["image_max"]), fold_size=int(params["fold_size"])
            )

        plans.append(
            EpisodePlan(
                episode=episode,
                start_offset_s=float(params["stagger_s"]) * episode / episodes,
                steps=measured,
                prebuilt_responses=list(responses),
                build=build,
                output_tokens=int(params["output_tokens"]),
                thinking=bool(params["thinking"]),
                t_env_s=float(params["t_env_s"]),
            )
        )
    return plans
