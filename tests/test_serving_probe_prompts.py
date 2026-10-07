from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from serving_probe_fakes import WordTokenizer

from harness.serving_probe.prompts import (
    COLLAPSED_SCREENSHOT_TEXT,
    HarnessShape,
    allowed_token_ids,
    count_images,
    folded_prefix,
    h1_messages,
    h2_messages,
    modeled_prompt_tokens,
    open_loop_messages,
    random_text,
    text_rng,
    visible_images,
)


def _texts(messages):
    return [part["text"] for m in messages for part in m["content"] if part["type"] == "text"]


def test_random_text_has_exact_token_count_and_no_special_tokens() -> None:
    tokenizer = WordTokenizer()
    allowed = allowed_token_ids(tokenizer)
    assert not set(tokenizer.all_special_ids) & set(allowed.tolist())
    text = random_text(tokenizer, allowed, text_rng(42), 1536)
    assert len(tokenizer.encode(text)) == 1536
    assert text == random_text(tokenizer, allowed, text_rng(42), 1536)
    assert text != random_text(tokenizer, allowed, text_rng(43), 1536)
    assert random_text(tokenizer, allowed, text_rng(1), 0) == ""


def test_text_and_image_streams_are_independent() -> None:
    first = text_rng(42, 3).integers(0, 1 << 30, 4)
    again = text_rng(42, 3).integers(0, 1 << 30, 4)
    other = np.random.default_rng([42, 2, 3]).integers(0, 1 << 30, 4)
    assert np.array_equal(first, again)
    assert not np.array_equal(first, other)


def test_open_loop_layout_puts_images_last() -> None:
    messages = open_loop_messages("prefix", "body", ["data:a", "data:b"])
    assert messages[0]["role"] == "system"
    assert [p["type"] for p in messages[1]["content"]] == ["text", "image_url", "image_url"]


def _h1(step: int, history_n: int = 4, a11y: str = ""):
    shots = [f"img{i}" for i in range(1, step + 1)]
    responses = [f"resp{i}" for i in range(1, step)]
    actions = [f"act{i}" for i in range(1, step)]
    return h1_messages(
        system="sys",
        task="task",
        screenshots=shots,
        responses=responses,
        actions=actions,
        history_n=history_n,
        a11y=a11y,
    )


def test_h1_matches_osworld_window_layout() -> None:
    first = _h1(1)
    assert [m["role"] for m in first] == ["system", "user"]
    assert count_images(first) == 1
    assert "Instruction: task" in first[1]["content"][1]["text"]
    seventh = _h1(7)
    assert count_images(seventh) == 5
    roles = [m["role"] for m in seventh]
    assert roles == ["system"] + ["user", "assistant"] * 4 + ["user"]
    instruction = seventh[1]["content"][1]["text"]
    assert "Step 1: act1" in instruction and "Step 2: act2" in instruction
    assert "act3" not in instruction
    assert [m["content"][0]["text"] for m in seventh if m["role"] == "assistant"] == [
        "resp3",
        "resp4",
        "resp5",
        "resp6",
    ]
    with_tree = _h1(3, a11y="tree")
    assert with_tree[-1]["content"][-1]["text"].endswith("tree")


def test_h2_folding_follows_cua_speedrun() -> None:
    assert folded_prefix(20, 20, 10) == 0
    assert folded_prefix(21, 20, 10) == 10
    assert folded_prefix(30, 20, 10) == 10
    assert folded_prefix(31, 20, 10) == 20
    total = 21
    messages = h2_messages(
        system="sys",
        task="task",
        screenshots=[f"img{i}" for i in range(1, total + 1)],
        responses=[f"r{i}" for i in range(1, total)],
        actions=[f"a{i}" for i in range(1, total)],
        history_n=100,
        image_max=20,
        fold_size=10,
    )
    assert count_images(messages) == 11
    texts = _texts(messages)
    assert texts.count(COLLAPSED_SCREENSHOT_TEXT) == 9
    assert messages[1]["content"] == [{"type": "text", "text": messages[1]["content"][0]["text"]}]
    assert "Previous actions:\nNone" in messages[1]["content"][0]["text"]
    assert messages[-1]["content"][0]["text"] == "<tool_response>\n"
    assert messages[-1]["content"][-1]["text"] == "\n</tool_response>"
    assert sum(1 for m in messages if m["role"] == "assistant") == total - 1


@pytest.mark.parametrize("harness", ["h1", "h2"])
def test_visible_image_model_matches_built_messages(harness: str) -> None:
    shape = HarnessShape(harness, 1536, 64, 16, 300, 0, 2040, 4 if harness == "h1" else 100)
    for step in range(1, 45):
        shots = [f"img{i}" for i in range(1, step + 1)]
        common = dict(
            system="s",
            task="t",
            screenshots=shots,
            responses=[f"r{i}" for i in range(1, step)],
            actions=[f"a{i}" for i in range(1, step)],
            history_n=shape.history_n,
        )
        if harness == "h1":
            messages = h1_messages(**common)
        else:
            messages = h2_messages(**common, image_max=20, fold_size=10)
        assert count_images(messages) == visible_images(shape, step), step


def test_modeled_prompt_tokens_drop_at_folds_and_grow_between() -> None:
    shape = HarnessShape("h2", 1536, 64, 16, 300, 0, 2040, 100)
    tokens = [modeled_prompt_tokens(shape, step) for step in range(1, 32)]
    assert tokens[19] > tokens[20]  # step 21 folds ten screenshots
    assert all(tokens[i] < tokens[i + 1] for i in range(20, 29))
    h1 = HarnessShape("h1", 1536, 64, 16, 300, 6144, 2040, 4)
    assert modeled_prompt_tokens(h1, 6) == modeled_prompt_tokens(h1, 5) + 16
    with pytest.raises(ValueError):
        visible_images(h1, 0)


def test_no_unlicensed_harness_text_is_reproduced() -> None:
    # cua-speedrun has no LICENSE file: its placeholder sentence must not appear.
    import harness.serving_probe.prompts as prompts

    source = Path(prompts.__file__).read_text(encoding="utf-8")
    assert "has been collapsed" not in source
    assert COLLAPSED_SCREENSHOT_TEXT == "Earlier screen image omitted here."
    assert "Apache License 2.0" in source and "OSWorld" in source
