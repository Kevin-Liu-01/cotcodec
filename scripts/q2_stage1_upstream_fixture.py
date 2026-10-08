#!/usr/bin/env python3
"""Record the message lists the unmodified upstream agents build (S1a test fixture).

``harness/q2_stage1/agents.py`` re-implements the message layout of OSWorld ``bfd62bdc``
``mm_agents/qwen35vl_agent.py`` and gym-anything ``aae6f7607`` ``agents/agents/qwen35vl.py``.
This script runs the upstream code itself, with its model client and file system stubbed,
and writes what it would send: the system prompt (at a fixed date), the instruction and the
message structure over a scripted episode, with every screenshot replaced by its index (so
the fixture does not depend on the PNG encoder). ``tests/test_q2_stage1_agents.py`` checks
the re-implementation against it.

Inputs are the pinned upstream files (``git show REV:PATH``; the registration's section 4
lists their SHA-256). Run it with the repository's Python (Pillow and requests installed):

    python scripts/q2_stage1_upstream_fixture.py --osworld-agent qwen35vl_agent.py \\
        --osworld-qwen-utils qwen_vl_utils.py --ga-agent qwen35vl.py \\
        --out tests/fixtures/q2_stage1/upstream_messages.json
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
from datetime import datetime
from pathlib import Path
from typing import Any

PINS = {
    "osworld_agent": "1f39be92cf5461d9671ab9307a69c05691abf0226aa6b53d2af332003a5096fe",
    "ga_agent": "93666f2751d99dfee0034700f65385ca2db1544e3d9a0d194807050d2edea1a5",
}
FIXED_DAY = datetime(2026, 10, 8, 9, 30)
INSTRUCTION = "Make the title bold and save the file."
STEPS = 23  # past image_max = 20, so the fold of 10 shows up
KEEP = (1, 2, 3, 15, 20, 21, 22, 23)  # the steps whose message lists the fixture keeps
RESPONSES = [
    "<think>\nstep {k}\n</think>\n\nAction: Click the title.\n<tool_call>\n"
    "<function=computer_use>\n<parameter=action>\nleft_click\n</parameter>\n"
    "<parameter=coordinate>\n[{x}, 120]\n</parameter>\n</function>\n</tool_call>"
]


class _FixedDateTime(datetime):
    @classmethod
    def today(cls) -> datetime:  # type: ignore[override]
        return FIXED_DAY


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png(index: int) -> bytes:
    from PIL import Image

    image = Image.new("RGB", (1920, 1080), (index * 9 % 256, 40, 80))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def strip_images(
    messages: list[dict[str, Any]], index_of: dict[str, int], system: list[str]
) -> list[dict[str, Any]]:
    """Screenshots as their index; the system prompt as a marker (kept once in ``system``)."""
    out = []
    for message in messages:
        if message["role"] == "system":
            text = message["content"][0]["text"]
            if text not in system:
                system.append(text)
            out.append({"role": "system", "content": f"<system {system.index(text)}>"})
            continue
        parts = []
        for part in message["content"]:
            if part.get("type") == "image_url":
                b64 = part["image_url"]["url"].split("base64,", 1)[1]
                parts.append({"type": "image_url", "screenshot": index_of[b64]})
            else:
                parts.append(part)
        out.append({"role": message["role"], "content": parts})
    return out


def load(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def osworld_run(agent_path: Path, utils_path: Path) -> dict[str, Any]:
    sys.modules.setdefault("openai", types.ModuleType("openai"))
    for name in ("mm_agents", "mm_agents.utils"):
        sys.modules.setdefault(name, types.ModuleType(name))
    load(utils_path, "mm_agents.utils.qwen_vl_utils")
    module = load(agent_path, "osw_qwen35vl_agent")
    module.datetime = _FixedDateTime
    agent = module.Qwen35VLAgent()
    captured: list[list[dict[str, Any]]] = []

    def call_llm(payload: dict[str, Any], model: str) -> str:
        captured.append(payload["messages"])
        k = len(captured)
        return RESPONSES[0].format(k=k, x=100 + k)

    agent.call_llm = call_llm
    shots = [png(i) for i in range(STEPS)]
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            for shot in shots:
                agent.predict(INSTRUCTION, {"screenshot": shot})
        finally:
            os.chdir(cwd)
    index_of = {b64: i for i, b64 in enumerate(agent.screenshots)}
    system: list[str] = []
    kept = {str(k): strip_images(captured[k - 1], index_of, system) for k in KEEP}
    first_png = base64.b64decode(agent.screenshots[0])
    from PIL import Image

    size = Image.open(io.BytesIO(first_png)).size
    return {
        "processed_size": list(size),
        "system_prompts": system,
        "messages": kept,
        "responses": agent.responses,
        "actions": agent.actions,
    }


def ga_run(agent_path: Path) -> dict[str, Any]:
    base = types.ModuleType("agents.agents.qwen3vl")

    class Qwen3VLAgent:
        def __init__(self, *args: Any, **kwargs: Any):
            self.agent_args = kwargs.get("agent_args", {})
            self.history: list[str] = []
            self.screenshots: list[str] = []
            self.responses: list[str] = []

    base.Qwen3VLAgent = Qwen3VLAgent
    for name in ("agents", "agents.agents"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["agents.agents.qwen3vl"] = base
    module = load(agent_path, "ga_qwen35vl")
    module.datetime = _FixedDateTime
    agent = module.Qwen35VLAgent(agent_args={})
    agent.task_description = (
        INSTRUCTION
        + "\nUnless explicitly mentioned, you are required to use the UI to complete the task "
        "not terminal."
    )
    runs: dict[str, dict[str, list[dict[str, Any]]]] = {}
    system: list[str] = []
    for variant in agent._context_variants():
        agent.screenshots, agent.responses, agent.history = [], [], []
        seq = {}
        for k in range(STEPS):
            b64 = base64.b64encode(f"shot-{k}".encode()).decode()
            agent.screenshots.append(b64)
            messages = agent.build_messages(b64, *variant)
            index_of = {s: i for i, s in enumerate(agent.screenshots)}
            if k + 1 in KEEP:
                seq[str(k + 1)] = strip_images(messages, index_of, system)
            agent.responses.append(RESPONSES[0].format(k=k + 1, x=101 + k))
            agent.history.append(f"conclusion {k + 1}")
        runs[",".join(map(str, variant))] = seq
    return {
        "system_prompt": agent.get_system_prompt(),
        "system_prompts": system,
        "context_variants": [list(v) for v in agent._context_variants()],
        "messages_by_variant": runs,
        "smart_resize_1920x1080": list(agent._smart_resize(height=1080, width=1920)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--osworld-agent", type=Path, required=True)
    parser.add_argument("--osworld-qwen-utils", type=Path, required=True)
    parser.add_argument("--ga-agent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if sha256(args.osworld_agent) != PINS["osworld_agent"]:
        raise SystemExit("the OSWorld agent file is not the pinned bfd62bdc file")
    if sha256(args.ga_agent) != PINS["ga_agent"]:
        raise SystemExit("the gym-anything agent file is not the pinned aae6f7607 file")
    fixture = {
        "schema": "q2-stage1a-upstream-messages-v1",
        "generator": "scripts/q2_stage1_upstream_fixture.py",
        "sources": {
            "osworld_agent": {
                "rev": "bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06",
                "path": "mm_agents/qwen35vl_agent.py",
                "sha256": sha256(args.osworld_agent),
            },
            "osworld_qwen_utils": {
                "rev": "bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06",
                "path": "mm_agents/utils/qwen_vl_utils.py",
                "sha256": sha256(args.osworld_qwen_utils),
            },
            "ga_agent": {
                "rev": "aae6f7607e0f3d9d6306e1fefbad92bda99ca99a",
                "path": "agents/agents/qwen35vl.py",
                "sha256": sha256(args.ga_agent),
            },
        },  # fmt: skip
        "fixed_day": FIXED_DAY.isoformat(),
        "instruction": INSTRUCTION,
        "steps": STEPS,
        "kept_steps": list(KEEP),
        "response_template": RESPONSES[0],
        "osworld": osworld_run(args.osworld_agent, args.osworld_qwen_utils),
        "gym_anything": ga_run(args.ga_agent),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(fixture, ensure_ascii=False, separators=(",", ":"))
    args.out.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "sha256": sha256(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
