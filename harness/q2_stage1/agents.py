"""The two S1a harness clients: upstream message layouts, image processing and turn rules.

Registration sections 3.1 item 3, 5.2, 5.3 and 7.2. Each client reproduces its upstream
agent's prompt and history so the model sees what it would see upstream; parsing goes
through the certified action path (the H-OSW-fixed parser and the H-GA adapter, frozen in
the action-path v2 executor addendum) to canonical IR.

* **H-OSW-fixed**: OSWorld ``bfd62bdc`` ``mm_agents/qwen35vl_agent.py``
  (``Qwen35VLAgent.predict``): ``process_image`` (``smart_resize`` with factor 32 and
  ``max_pixels = 16*16*4*12800``, PIL ``resize``, PNG, base64), the tool definition and system
  prompt (with today's date), the instruction prompt, ``history_n = 100``,
  ``image_max = 20``, ``fold_size = 10``, collapsed screenshots as text, later screenshots
  wrapped in ``<tool_response>``, every earlier response passed back as an assistant turn.
* **H-GA**: gym-anything ``aae6f7607`` ``agents/agents/qwen35vl.py``
  (``Qwen35VLAgent.build_messages`` and ``step``) with its runner's instruction suffix
  (``agents/evaluation/run_single.py``: "Unless explicitly mentioned, ..."), the same layout
  and its context-variant fallback (``_context_variants``): a model call that fails is
  retried with ``(60, 12, 6)``, ``(24, 8, 4)`` and ``(8, 4, 2)``. Under S1a only a
  context-length rejection may trigger it; any other failure is an infrastructure loss
  (``engine_context_fallback``, section 7.2).

Both harnesses send the registered sampling (``plan.sampling``) and keep their own parser
rule for a reply that does not yield valid IR: H-OSW-fixed takes no action that step, H-GA
waits one second (section 7.2). A parser or IR exception raised by model output is such a
reply, counted per turn (``parse_error``), never an infrastructure loss.

The prompt strings below are copied from the two upstream files: OSWorld (Apache-2.0,
Copyright the OSWorld authors; http://www.apache.org/licenses/LICENSE-2.0) and gym-anything
(MIT License, Copyright (c) 2026 cmu-l3: permission is granted to use, copy, modify and
distribute with this notice). ``tests/test_q2_stage1_agents.py`` checks the layouts against
messages recorded from the unmodified upstream code (``tests/fixtures/q2_stage1/``).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from harness.q2_stage1.engine import Completion, ContextLengthError, EngineClient, EngineError

HARNESSES = ("H-OSW-fixed", "H-GA")
COLLAPSED_SCREENSHOT_TEXT = "This screenshot has been collapsed."
GA_INSTRUCTION_SUFFIX = (
    "\nUnless explicitly mentioned, you are required to use the UI to complete the task not "
    "terminal."
)
HISTORY_N, IMAGE_MAX, FOLD_SIZE = 100, 20, 10
GA_CONTEXT_VARIANTS = ((100, 20, 10), (60, 12, 6), (24, 8, 4), (8, 4, 2))
GA_PARSE_ERROR_WAIT = {"op": "wait", "ms": 1000}
TOOL_CALL = re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL)
SMART_FACTOR = 32
SMART_MAX_PIXELS = 16 * 16 * 4 * 12800

_DESCRIPTION_LINES = (
    "Use a mouse and keyboard to interact with a computer, and take screenshots.",
    "* This is an interface to a desktop GUI. You do not have access to a terminal or "
    "applications menu. You must click on desktop icons to start applications.",
    "* Some applications may take time to start or process actions, so you may need to wait "
    "and take successive screenshots to see the results of your actions.",
    "* The screen's resolution is 1000x1000.",
    "* Whenever you intend to move the cursor to click on an element like an icon, you should "
    "consult a screenshot to determine the coordinates of the element before moving the cursor.",
    "* If you tried clicking on a program or link but it failed to load, even after waiting, "
    "try adjusting your cursor position so that the tip of the cursor visually falls on the "
    "element that you want to click.",
    "* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of "
    "the element. Don't click boxes on their edges unless asked.",
)

_OSW_ACTIONS = """
* `key`: Performs key down presses on the arguments passed in order, then performs key releases in reverse order.
* `type`: Type a string of text on the keyboard.
* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.
* `left_click`: Click the left mouse button at a specified (x, y) pixel coordinate on the screen. Optional `text` parameter can specify modifier keys (e.g., "ctrl", "shift", "ctrl+shift") that will be held during the click.
* `left_click_drag`: Click and drag the cursor to a specified (x, y) coordinate.
* `right_click`: Click the right mouse button at a specified (x, y) pixel coordinate on the screen. Optional `text` parameter can specify modifier keys that will be held during the click.
* `middle_click`: Click the middle mouse button at a specified (x, y) pixel coordinate on the screen. Optional `text` parameter can specify modifier keys that will be held during the click.
* `double_click`: Double-click the left mouse button at a specified (x, y) pixel coordinate on the screen. Optional `text` parameter can specify modifier keys that will be held during the click.
* `triple_click`: Triple-click the left mouse button at a specified (x, y) pixel coordinate on the screen (simulated as double-click since it's the closest action). Optional `text` parameter can specify modifier keys that will be held during the click.
* `scroll`: Performs a scroll of the mouse scroll wheel. Optional `text` parameter can specify a modifier key (e.g., "shift", "ctrl") that will be held during scrolling.
* `hscroll`: Performs a horizontal scroll (mapped to regular scroll). Optional `text` parameter can specify a modifier key that will be held during scrolling.
* `wait`: Wait specified seconds for the change to happen.
* `terminate`: Terminate the current task and report its completion status.
* `answer`: Answer a question."""  # noqa: E501 - upstream text, byte for byte

_GA_ACTIONS = """
* `key`: Performs key down presses on the arguments passed in order, then performs key releases in reverse order.
* `type`: Type a string of text on the keyboard.
* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.
* `left_click`: Click the left mouse button at a specified (x, y) pixel coordinate on the screen.
* `left_click_drag`: Drag from `coordinate` to `coordinate2`.
* `right_click`: Click the right mouse button at a specified (x, y) pixel coordinate on the screen.
* `middle_click`: Click the middle mouse button at a specified (x, y) pixel coordinate on the screen.
* `double_click`: Double-click the left mouse button at a specified (x, y) pixel coordinate on the screen.
* `triple_click`: Triple-click the left mouse button at a specified (x, y) pixel coordinate on the screen.
* `scroll`: Performs a vertical mouse-wheel scroll. Pass `pixels` as signed wheel steps: negative scrolls down, positive scrolls up, and the magnitude must be between 1 and 10.
* `wait`: Wait specified seconds for the change to happen.
* `terminate`: Terminate the current task and report its completion status.
* `answer`: Answer a question."""  # noqa: E501 - upstream text, byte for byte

_ENUM_COMMON = ["key", "type", "mouse_move", "left_click", "left_click_drag", "right_click",
                "middle_click", "double_click", "triple_click", "scroll"]  # fmt: skip


def _osw_tools_def() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "computer_use",
            "description": "\n".join(_DESCRIPTION_LINES),
            "parameters": {
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "description": _OSW_ACTIONS,
                        "enum": [*_ENUM_COMMON, "hscroll", "wait", "terminate", "answer"],
                    },
                    "keys": {"type": "array", "description": "Required only by `action=key`."},
                    "text": {
                        "type": "string",
                        "description": "Required by `action=type` and `action=answer`. Optional "
                        "for click actions (left_click, right_click, middle_click, double_click, "
                        "triple_click) to specify modifier keys (e.g., 'ctrl', 'shift', "
                        "'ctrl+shift'). Optional for scroll actions (scroll, hscroll) to specify "
                        "a modifier key (e.g., 'shift', 'ctrl') to hold during scrolling.",
                    },
                    "coordinate": {"type": "array", "description": "(x, y) coordinates."},
                    "pixels": {"type": "number", "description": "Scroll amount."},
                    "time": {"type": "number", "description": "Seconds to wait."},
                    "status": {
                        "type": "string",
                        "description": "Task status for terminate.",
                        "enum": ["success", "failure"],
                    },
                },
            },
        },
    }


def _ga_tools_def() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "computer_use",
            "description": "\n".join(_DESCRIPTION_LINES),
            "parameters": {
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "description": _GA_ACTIONS,
                        "enum": [*_ENUM_COMMON, "wait", "terminate", "answer"],
                    },
                    "keys": {"type": "array", "description": "Required only by `action=key`."},
                    "text": {
                        "type": "string",
                        "description": "Required by `action=type` and `action=answer`.",
                    },
                    "coordinate": {"type": "array", "description": "(x, y) coordinates."},
                    "coordinate2": {
                        "type": "array",
                        "description": "Drag-end (x, y) coordinates; required by "
                        "`action=left_click_drag`.",
                    },
                    "pixels": {
                        "type": "number",
                        "description": "Signed wheel steps: negative scrolls down, positive "
                        "scrolls up; use a magnitude from 1 to 10.",
                    },
                    "time": {"type": "number", "description": "Seconds to wait."},
                    "status": {
                        "type": "string",
                        "description": "Task status for terminate.",
                        "enum": ["success", "failure"],
                    },
                },
            },
        },
    }


def system_prompt(tools_json: str, today: datetime) -> str:
    """The system prompt both upstream agents build around their tool definition."""
    return (
        "You are a multi-purpose intelligent assistant. Based on my requests, you can use tools "
        "to help me complete various tasks.\n\n"
        "# Tools\n\n"
        "You have access to the following functions:\n\n"
        "<tools>\n" + tools_json + "\n</tools>\n\n"
        "If you choose to call a function ONLY reply in the following format with NO suffix:\n\n"
        "<tool_call>\n"
        "<function=example_function_name>\n"
        "<parameter=example_parameter_1>\n"
        "value_1\n"
        "</parameter>\n"
        "<parameter=example_parameter_2>\n"
        "This is the value for the second parameter\n"
        "that can span\n"
        "multiple lines\n"
        "</parameter>\n"
        "</function>\n"
        "</tool_call>\n\n"
        "<IMPORTANT>\n"
        "Reminder:\n"
        "- Function calls MUST follow the specified format: an inner <function=...></function> "
        "block must be nested within <tool_call></tool_call> XML tags\n"
        "- Required parameters MUST be specified\n"
        "- You may provide optional reasoning for your function call in natural language BEFORE "
        "the function call, but NOT after\n"
        "- If there is no function call available, answer the question like normal with your "
        "current knowledge and do not tell the user about function calls\n"
        f"- The current date is {today.strftime('%A, %B %d, %Y')}.\n"
        f"- Collapsed screenshots appear as text: {COLLAPSED_SCREENSHOT_TEXT}\n"
        "</IMPORTANT>\n\n"
        "# Response format\n\n"
        "Response format for every step:\n"
        "1) Action: a short imperative describing what to do in the UI.\n"
        "2) A single <tool_call>...</tool_call> block.\n\n"
        "Rules:\n"
        "- Output exactly in the order: Action, <tool_call>.\n"
        "- Be brief: one sentence for Action.\n"
        "- Do not output anything else outside those parts.\n"
        "- If finishing, use action=terminate in the tool call."
    )


def osw_system_prompt(today: datetime) -> str:
    return system_prompt(json.dumps(_osw_tools_def()), today)


def ga_system_prompt(today: datetime) -> str:
    return system_prompt(json.dumps(_ga_tools_def(), ensure_ascii=False), today)


# --------------------------------------------------------------------------- images


def smart_resize(height: int, width: int) -> tuple[int, int]:
    """OSWorld's ``qwen_vl_utils.smart_resize`` at factor 32 and the agents' ``max_pixels``
    (gym-anything's ``_smart_resize`` gives the same size for every screen S1a runs)."""
    if height < 2 or width < 2:
        raise ValueError(f"height:{height} or width:{width} must be larger than factor")
    if max(height, width) / min(height, width) > 200:
        raise ValueError("absolute aspect ratio must be smaller than 200")
    factor, max_pixels, min_pixels = SMART_FACTOR, SMART_MAX_PIXELS, 56 * 56
    if max(height, width) > 8192:
        beta = max(height, width) / 8192
        height, width = int(height / beta), int(width / beta)
    h_bar = round(height / factor) * factor
    w_bar = round(width / factor) * factor
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = math.floor(height / beta / factor) * factor
        w_bar = math.floor(width / beta / factor) * factor
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = math.ceil(height * beta / factor) * factor
        w_bar = math.ceil(width * beta / factor) * factor
    return h_bar, w_bar


@dataclass(frozen=True)
class Screenshot:
    """One observation as the model sees it."""

    b64: str
    original: tuple[int, int]
    processed: tuple[int, int]
    raw_sha256: str
    processed_sha256: str


def process_image(png: bytes) -> Screenshot:
    """Resize and re-encode a screenshot as both upstream agents do (PIL, PNG, base64)."""
    from PIL import Image

    image = Image.open(io.BytesIO(png))
    width, height = image.size
    new_h, new_w = smart_resize(height, width)
    resized = image.resize((new_w, new_h))
    buffer = io.BytesIO()
    resized.save(buffer, format="PNG")
    data = buffer.getvalue()
    return Screenshot(
        b64=base64.b64encode(data).decode("utf-8"),
        original=(width, height),
        processed=(new_w, new_h),
        raw_sha256=hashlib.sha256(png).hexdigest(),
        processed_sha256=hashlib.sha256(data).hexdigest(),
    )


# --------------------------------------------------------------------------- layout


def folded_prefix(total: int, image_max: int, fold_size: int) -> int:
    folded = 0
    while total - folded > image_max:
        folded += fold_size
    return min(folded, total)


def wrap_tool_response(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return (
        [{"type": "text", "text": "<tool_response>\n"}]
        + parts
        + [{"type": "text", "text": "\n</tool_response>"}]
    )


def build_messages(
    *,
    system: str,
    instruction: str,
    screenshots: Sequence[str],
    responses: Sequence[str],
    previous: Sequence[str],
    history_n: int = HISTORY_N,
    image_max: int = IMAGE_MAX,
    fold_size: int = FOLD_SIZE,
) -> list[dict[str, Any]]:
    """The upstream message list (both agents share it): ``screenshots`` already holds the
    current one; ``previous`` is the per-step action summary shown for steps outside the
    history window."""
    history_n, image_max, fold_size = max(1, history_n), max(1, image_max), max(1, fold_size)
    total = len(screenshots)
    folded = folded_prefix(total, image_max, fold_size)
    start = max(1, total - history_n)
    shown = [f"Step {i + 1}: {previous[i]}" for i in range(0, min(start - 1, len(previous)))]
    instruction_prompt = (
        "\nPlease generate the next move according to the UI screenshot, instruction and "
        f"previous actions.\n\nInstruction: {instruction}\n\nPrevious actions:\n"
        + ("\n".join(shown) if shown else "None")
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": [{"type": "text", "text": system}]}
    ]
    for step in range(start, total + 1):
        first = step == start
        if step <= folded:
            if first:
                content = [{"type": "text", "text": instruction_prompt}]
            else:
                content = wrap_tool_response([{"type": "text", "text": COLLAPSED_SCREENSHOT_TEXT}])
        else:
            image = {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshots[step - 1]}"},
            }
            if first:
                content = [image, {"type": "text", "text": instruction_prompt}]
            else:
                content = wrap_tool_response([image])
        messages.append({"role": "user", "content": content})
        if step <= total - 1 and (step - 1) < len(responses):
            messages.append(
                {"role": "assistant", "content": [{"type": "text", "text": responses[step - 1]}]}
            )
    return messages


def messages_sha256(messages: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


# --------------------------------------------------------------------------- turns


class InfraLoss(RuntimeError):
    """An infrastructure loss of the episode (``records.INFRASTRUCTURE_TYPES``)."""

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


@dataclass
class Turn:
    """One model turn: what was sent, what came back and what will run."""

    response: str
    completion: dict[str, Any] | None
    ir: list[dict[str, Any]]
    parse_error: str | None
    low_level: str
    truncated: bool
    complete_tool_call: bool
    messages_sha256: str
    context_variant: tuple[int, int, int]
    context_fallbacks: int = 0
    fallback_errors: list[str] = field(default_factory=list)


def complete_tool_call(text: str) -> bool:
    return bool(TOOL_CALL.search(text or ""))


def hit_token_cap(completion: Completion, max_tokens: int) -> bool:
    return completion.finish_reason == "length" or (completion.completion_tokens or 0) >= max_tokens


class HarnessClient:
    """Shared state of a harness client over one episode."""

    name = ""

    def __init__(
        self,
        instruction: str,
        engine: EngineClient,
        sampling: Mapping[str, Any],
        today: datetime | None = None,
    ):
        self.instruction = instruction
        self.engine = engine
        self.sampling = dict(sampling)
        self.today = today or datetime.today()
        self.screenshots: list[str] = []
        self.responses: list[str] = []
        self.previous: list[str] = []
        self.last: Screenshot | None = None

    @property
    def date_line(self) -> str:
        return self.today.strftime("%A, %B %d, %Y")

    def observe(self, png: bytes) -> Screenshot:
        shot = process_image(png)
        self.screenshots.append(shot.b64)
        self.last = shot
        return shot

    def messages(self, variant: tuple[int, int, int] = (HISTORY_N, IMAGE_MAX, FOLD_SIZE)):
        raise NotImplementedError

    def parse(self, response: str) -> tuple[str, list[dict[str, Any]]]:
        raise NotImplementedError

    def on_parse_error(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def _finish(self, response: str, completion: Completion, messages, variant, fallbacks, errors):
        from harness.q2.action_path import controls

        self.responses.append(response)
        parse_error = None
        try:
            low_level, raw = self.parse(response)
            ir = [action.to_dict() for action in controls.to_ir(raw)]
        except Exception as exc:  # noqa: BLE001 - a reply that yields no valid IR (section 7.2)
            parse_error = f"{type(exc).__name__}: {str(exc)[:300]}"
            low_level, ir = "", self.on_parse_error()
        self.previous.append(low_level)
        max_tokens = int(self.sampling["max_tokens"])
        return Turn(
            response=response,
            completion=completion.as_dict(),
            ir=ir,
            parse_error=parse_error,
            low_level=low_level,
            truncated=hit_token_cap(completion, max_tokens),
            complete_tool_call=complete_tool_call(response),
            messages_sha256=messages_sha256(messages),
            context_variant=variant,
            context_fallbacks=fallbacks,
            fallback_errors=errors,
        )


class HOswFixed(HarnessClient):
    """OSWorld ``bfd62bdc`` ``Qwen35VLAgent`` with the H-OSW-fixed parser."""

    name = "H-OSW-fixed"

    def messages(self, variant: tuple[int, int, int] = (HISTORY_N, IMAGE_MAX, FOLD_SIZE)):
        return build_messages(
            system=osw_system_prompt(self.today),
            instruction=self.instruction,
            screenshots=self.screenshots,
            responses=self.responses,
            previous=self.previous,
            history_n=variant[0],
            image_max=variant[1],
            fold_size=variant[2],
        )

    def parse(self, response: str) -> tuple[str, list[dict[str, Any]]]:
        from harness.q2.action_path.ir import SCREEN
        from harness.q2.action_path.upstream.osworld_bfd62bdc_fixed import Qwen35VLAgent

        width, height = self.last.original if self.last else SCREEN
        return Qwen35VLAgent(coordinate_type="relative").parse_response(
            response or "",
            original_width=width,
            original_height=height,
            processed_width=width,
            processed_height=height,
        )

    def on_parse_error(self) -> list[dict[str, Any]]:
        return []  # upstream: no action that step

    def act(self) -> Turn:
        variant = (HISTORY_N, IMAGE_MAX, FOLD_SIZE)
        messages = self.messages(variant)
        try:
            completion = self.engine.chat(messages, self.sampling)
        except EngineError as exc:
            raise InfraLoss("engine_request", f"{exc.kind}: {exc}") from exc
        return self._finish(completion.content, completion, messages, variant, 0, [])


class HGa(HarnessClient):
    """gym-anything ``aae6f7607`` ``Qwen35VLAgent`` and its runner's instruction suffix."""

    name = "H-GA"

    def __init__(self, instruction: str, *args: Any, **kwargs: Any):
        super().__init__(instruction + GA_INSTRUCTION_SUFFIX, *args, **kwargs)

    def messages(self, variant: tuple[int, int, int] = (HISTORY_N, IMAGE_MAX, FOLD_SIZE)):
        return build_messages(
            system=ga_system_prompt(self.today),
            instruction=self.instruction,
            screenshots=self.screenshots,
            responses=self.responses,
            previous=self.previous,
            history_n=variant[0],
            image_max=variant[1],
            fold_size=variant[2],
        )

    def parse(self, response: str) -> tuple[str, list[dict[str, Any]]]:
        from harness.q2.action_path import controls
        from harness.q2.action_path.ir import SCREEN
        from harness.q2.action_path.upstream.gym_anything_aae6f7607 import Qwen35VLAgent

        width, height = self.last.original if self.last else SCREEN
        parsed = Qwen35VLAgent()._parse_response(response, width, height)
        conclusion = str((parsed.get("metadata") or {}).get("conclusion", ""))
        return conclusion, controls.translate_ga_dicts(parsed)

    def on_parse_error(self) -> list[dict[str, Any]]:
        return [dict(GA_PARSE_ERROR_WAIT)]  # one-second wait (section 5.2)

    def act(self) -> Turn:
        errors: list[str] = []
        for fallbacks, variant in enumerate(GA_CONTEXT_VARIANTS):
            messages = self.messages(variant)
            try:
                completion = self.engine.chat(messages, self.sampling)
            except ContextLengthError as exc:
                errors.append(str(exc)[:300])
                continue
            except EngineError as exc:
                # Upstream would retry with a shorter history; under S1a a fallback that a
                # context-length rejection did not cause is an infrastructure loss.
                raise InfraLoss("engine_context_fallback", f"{exc.kind}: {exc}") from exc
            content = completion.content
            return self._finish(content, completion, messages, variant, fallbacks, errors)
        raise InfraLoss("engine_request", "every context variant was rejected as too long")


CLIENTS: dict[str, type[HarnessClient]] = {"H-OSW-fixed": HOswFixed, "H-GA": HGa}


def make_client(
    harness: str,
    instruction: str,
    engine: EngineClient,
    sampling: Mapping[str, Any],
    today: datetime | None = None,
) -> HarnessClient:
    if harness not in CLIENTS:
        raise ValueError(f"unknown harness {harness}")
    return CLIENTS[harness](instruction, engine, sampling, today)


def today_from(text: str | None) -> Callable[[], datetime] | None:
    """A fixed clock for tests and replays (``YYYY-MM-DD``); None keeps the upstream clock."""
    if not text:
        return None
    fixed = datetime.strptime(text, "%Y-%m-%d")
    return lambda: fixed
