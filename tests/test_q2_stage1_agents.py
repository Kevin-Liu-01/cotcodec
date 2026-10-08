"""S1a harness clients against the unmodified upstream agents (registration 3.1 item 3)."""

from __future__ import annotations

import io
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from harness.q2_stage1 import agents
from harness.q2_stage1.engine import EngineClient
from harness.q2_stage1.fake_engine import FakeEngine

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/q2_stage1/upstream_messages.json").read_text())
DAY = datetime.fromisoformat(FIXTURE["fixed_day"])
SAMPLING = {"temperature": 0.0, "top_p": 0.9, "top_k": -1, "max_tokens": 2048}
TEMPLATE = FIXTURE["response_template"]


def normalize(messages: list[dict[str, Any]], systems: list[str]) -> list[dict[str, Any]]:
    out = []
    for message in messages:
        if message["role"] == "system":
            out.append(
                {
                    "role": "system",
                    "content": f"<system {systems.index(message['content'][0]['text'])}>",
                }
            )
            continue
        parts = []
        for part in message["content"]:
            if part.get("type") == "image_url":
                index = int(part["image_url"]["url"].rsplit("IMG", 1)[1])
                parts.append({"type": "image_url", "screenshot": index})
            else:
                parts.append(part)
        out.append({"role": message["role"], "content": parts})
    return out


def test_fixture_was_made_from_the_pinned_upstream_files():
    sources = FIXTURE["sources"]
    assert sources["osworld_agent"]["sha256"] == (
        "1f39be92cf5461d9671ab9307a69c05691abf0226aa6b53d2af332003a5096fe"
    )
    assert sources["ga_agent"]["sha256"] == (
        "93666f2751d99dfee0034700f65385ca2db1544e3d9a0d194807050d2edea1a5"
    )


def test_system_prompts_equal_upstream_at_a_fixed_day():
    assert FIXTURE["osworld"]["system_prompts"] == [agents.osw_system_prompt(DAY)]
    assert FIXTURE["gym_anything"]["system_prompt"] == agents.ga_system_prompt(DAY)
    # The two harnesses share every word of the prompt but the tool description.
    assert agents.osw_system_prompt(DAY) != agents.ga_system_prompt(DAY)
    assert "The current date is Thursday, October 08, 2026." in agents.ga_system_prompt(DAY)


@pytest.mark.parametrize("step", FIXTURE["kept_steps"])
def test_osworld_layout_equals_upstream(step):
    steps = FIXTURE["steps"]
    responses = [TEMPLATE.format(k=k, x=100 + k) for k in range(1, steps + 1)]
    previous = FIXTURE["osworld"]["actions"]
    mine = agents.build_messages(
        system=agents.osw_system_prompt(DAY),
        instruction=FIXTURE["instruction"],
        screenshots=[f"IMG{i}" for i in range(step)],
        responses=responses[: step - 1],
        previous=previous[: step - 1],
    )
    systems = FIXTURE["osworld"]["system_prompts"]
    assert normalize(mine, systems) == FIXTURE["osworld"]["messages"][str(step)]


@pytest.mark.parametrize("variant", agents.GA_CONTEXT_VARIANTS)
@pytest.mark.parametrize("step", FIXTURE["kept_steps"])
def test_gym_anything_layout_equals_upstream_for_every_context_variant(variant, step):
    instruction = FIXTURE["instruction"] + agents.GA_INSTRUCTION_SUFFIX
    responses = [TEMPLATE.format(k=k + 1, x=101 + k) for k in range(step - 1)]
    mine = agents.build_messages(
        system=agents.ga_system_prompt(DAY),
        instruction=instruction,
        screenshots=[f"IMG{i}" for i in range(step)],
        responses=responses,
        previous=[f"conclusion {k + 1}" for k in range(step - 1)],
        history_n=variant[0],
        image_max=variant[1],
        fold_size=variant[2],
    )
    systems = FIXTURE["gym_anything"]["system_prompts"]
    key = ",".join(map(str, variant))
    assert (
        normalize(mine, systems) == FIXTURE["gym_anything"]["messages_by_variant"][key][str(step)]
    )


def test_context_variants_and_resize_equal_upstream():
    assert [list(v) for v in agents.GA_CONTEXT_VARIANTS] == FIXTURE["gym_anything"][
        "context_variants"
    ]
    assert (
        list(agents.smart_resize(1080, 1920)) == FIXTURE["gym_anything"]["smart_resize_1920x1080"]
    )
    assert list(agents.smart_resize(1080, 1920))[::-1] == FIXTURE["osworld"]["processed_size"]


def test_no_fold_and_no_history_cut_at_fifteen_steps():
    msgs = agents.build_messages(
        system="s", instruction="i", screenshots=[f"IMG{i}" for i in range(15)],
        responses=["r"] * 14, previous=["p"] * 14,
    )  # fmt: skip
    images = [p for m in msgs for p in m["content"] if p.get("type") == "image_url"]
    assert len(images) == 15
    assert "Previous actions:\nNone" in msgs[1]["content"][1]["text"]


def png(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (1920, 1080), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_process_image_resizes_to_1920x1088_png():
    import base64

    from PIL import Image

    shot = agents.process_image(png())
    assert shot.original == (1920, 1080) and shot.processed == (1920, 1088)
    image = Image.open(io.BytesIO(base64.b64decode(shot.b64)))
    assert image.format == "PNG" and image.size == (1920, 1088)


def tool_call(action: str, **params: Any) -> str:
    body = "".join(f"<parameter={k}>\n{v}\n</parameter>\n" for k, v in params.items())
    return (
        "<think>\nok\n</think>\n\nAction: do it.\n<tool_call>\n<function=computer_use>\n"
        f"<parameter=action>\n{action}\n</parameter>\n{body}</function>\n</tool_call>"
    )


def run_turns(harness: str, replies: list[Any]) -> list[agents.Turn]:
    sock = tempfile.mkdtemp(prefix="s1a", dir="/tmp") + "/e.sock"
    with FakeEngine(sock, {"replies": replies}):
        client = agents.make_client(
            harness, "Do the task.", EngineClient(sock, "m", sleep=lambda s: None), SAMPLING, DAY
        )
        turns = []
        for _ in replies:
            client.observe(png())
            turns.append(client.act())
        return turns


def test_hosw_turns_click_terminate_and_parse_failures():
    turns = run_turns(
        "H-OSW-fixed",
        [
            tool_call("left_click", coordinate="[500, 500]"),
            "no tool call at all",
            tool_call("key", keys='["nosuchkey"]'),
            tool_call("terminate", status="failure"),
        ],
    )
    click, none, bad, end = turns
    assert click.ir == [{"op": "click", "button": 1, "count": 1, "x": 960, "y": 540}]
    assert click.parse_error is None and click.complete_tool_call and not click.truncated
    assert none.ir == [] and none.parse_error is None and not none.complete_tool_call
    assert bad.ir == [] and "IRError" in bad.parse_error  # no action that step
    assert end.ir == [{"op": "terminate", "status": "failure"}]


def test_hga_turns_wait_on_failures_and_report_terminal_status():
    turns = run_turns(
        "H-GA",
        [
            tool_call("left_click", coordinate="[500, 500]"),
            "no tool call at all",
            tool_call("key", keys='["nosuchkey"]'),
            tool_call("terminate", status="success"),
        ],
    )
    click, none, bad, end = turns
    assert click.ir[-1]["op"] == "click"
    assert none.ir == [{"op": "wait", "ms": 1000}] and none.parse_error is None
    assert bad.ir == [{"op": "wait", "ms": 1000}] and bad.parse_error  # one-second wait
    assert end.ir[-1] == {"op": "terminate", "status": "success"}


def test_hga_appends_the_runner_suffix_and_hosw_does_not():
    sock = tempfile.mkdtemp(prefix="s1a", dir="/tmp") + "/e.sock"
    with FakeEngine(sock, {"replies": ["x"]}) as fake:
        for harness in agents.HARNESSES:
            client = agents.make_client(harness, "Task.", EngineClient(sock, "m"), SAMPLING, DAY)
            client.observe(png())
            client.act()
    texts = [r["messages"][1]["content"][1]["text"] for r in fake.requests]
    assert "Instruction: Task.\n\nPrevious" in texts[0]
    assert "Instruction: Task." + agents.GA_INSTRUCTION_SUFFIX + "\n\nPrevious" in texts[1]


def test_truncation_is_the_token_cap_and_tool_call_completeness():
    truncated = {"text": "<think>\nloop loop", "finish_reason": "length", "completion_tokens": 2048}
    (turn,) = run_turns("H-OSW-fixed", [truncated])
    assert turn.truncated and not turn.complete_tool_call and turn.ir == []


def test_hga_context_fallback_only_on_context_rejection():
    context = {"status": 400, "message": "maximum context length is 131072 tokens"}
    sock = tempfile.mkdtemp(prefix="s1a", dir="/tmp") + "/e.sock"
    calls = {"n": 0}

    class Scripted(FakeEngine):
        def reply_for(self, messages):
            calls["n"] += 1
            return context if calls["n"] == 1 else {"text": tool_call("wait", time="2")}

    with Scripted(sock, {"replies": []}):
        client = agents.HGa("t", EngineClient(sock, "m"), SAMPLING, DAY)
        client.observe(png())
        turn = client.act()
    assert turn.context_fallbacks == 1 and turn.context_variant == (60, 12, 6)
    assert turn.ir == [{"op": "wait", "ms": 2000}]

    with FakeEngine(sock, {"replies": [{"status": 500}]}):
        client = agents.HGa("t", EngineClient(sock, "m", sleep=lambda s: None), SAMPLING, DAY)
        client.observe(png())
        with pytest.raises(agents.InfraLoss) as info:
            client.act()
    assert info.value.kind == "engine_context_fallback"


def test_hosw_engine_failure_is_an_infrastructure_loss():
    sock = tempfile.mkdtemp(prefix="s1a", dir="/tmp") + "/e.sock"
    with FakeEngine(sock, {"replies": [{"status": 503}]}):
        client = agents.HOswFixed("t", EngineClient(sock, "m", sleep=lambda s: None), SAMPLING, DAY)
        client.observe(png())
        with pytest.raises(agents.InfraLoss) as info:
            client.act()
    assert info.value.kind == "engine_request"


def test_untypeable_is_the_guest_executors_rule():
    """``agents.untypeable`` refuses exactly the code points L0-fixed's ``char_keysym``
    raises for (``harness/q2/vm/guest/l0_fixed.py``, frozen with the action path)."""
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "harness/q2/vm/guest/l0_fixed.py"
    spec = importlib.util.spec_from_file_location("l0_fixed_rule", path)
    l0 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(l0)

    def refused(ch: str) -> bool:
        try:
            l0.char_keysym(ch)
        except ValueError:
            return True
        return False

    points = [*range(0x0, 0x800), 0x2028, 0xFEFF, 0xFFFD, 0x1F600, 0x10FFFF]
    for cp in points:
        assert bool(agents.untypeable(chr(cp))) == refused(chr(cp)), hex(cp)


CRLF_REPLY = (
    "<think>\nok\n</think>\n\nAction: type the table.\n<tool_call>\n<function=computer_use>\n"
    "<parameter=action>\ntype\n</parameter>\n"
    "<parameter=text>\r\nName,Age\r\nBob,3\r\n</parameter>\n</function>\n</tool_call>"
)


@pytest.mark.parametrize("harness", ["H-OSW-fixed", "H-GA"])
def test_control_characters_in_typed_text_are_the_harness_unparseable_reply(harness):
    lines = tool_call("type", text="Name,Age\nBob,3\tok")
    crlf, escape, fine = run_turns(harness, [CRLF_REPLY, tool_call("type", text="a\x1bb"), lines])
    unparseable = [] if harness == "H-OSW-fixed" else [{"op": "wait", "ms": 1000}]
    assert crlf.ir == unparseable and "IRError" in crlf.parse_error
    assert "U+000D" in crlf.parse_error
    assert escape.ir == unparseable and "U+001B" in escape.parse_error
    typed = [a for a in fine.ir if a["op"] == "type"]
    assert fine.parse_error is None and typed and "\n" in typed[0]["text"]
