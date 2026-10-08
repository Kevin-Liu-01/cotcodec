"""Regression corpus: catalog entries and R cases rendered as Qwen3.5 model responses.

Preregistration section 3 ("Corpus"). Each harness-expressible catalog entry
and each R case is rendered as model responses in the format of the official
chat template of ``Qwen/Qwen3.5-9B`` at ``c202236235762e1c871ad0ccb60c8ee5ba337b9a``
(``chat_template.jinja``, SHA-256 ``TEMPLATE_SHA256``): an assistant turn's
tool calls are

    <tool_call>\\n<function=NAME>\\n<parameter=K>\\nV\\n</parameter>\\n...</function>\\n</tool_call>

with later calls of the same turn prefixed by ``\\n``, list and mapping values
rendered as JSON (``tojson``: ``json.dumps(ensure_ascii=False)``), and other
values as ``str``. ``render_turn`` reproduces that rendering;
``tests/test_q2_corpus.py`` checks it against the template itself where
jinja2 is installed (the H100 host's system Python has it).

A catalog entry becomes one turn per tool call, because both Stage-1 prompts
ask for a single tool call per step; the few IR actions a prompt can only
express as two calls (H-OSW: a positioned scroll is ``mouse_move`` then
``scroll``; a two-point drag is ``mouse_move`` then ``left_click_drag``) take
two turns. Multi-call turns appear only in the R cases that test them (R05,
R06, R07). A catalog pixel is rendered as the 0-999 grid value whose scaled
pixel, under that harness's own scaling, is nearest to it (ties to the smaller
value); the error is at most one pixel, inside the +-2 px tolerance.

Perturbations (``VARIANTS``): ``action`` puts an ``Action:`` sentence before
the calls, ``think`` a closed think block, and ``json`` (H-GA only, which
documents it) renders each call as the JSON fallback
``{"name": "computer_use", "arguments": {...}}`` inside ``<tool_call>``.
A perturbation must parse to exactly the IR of the plain rendering (checked
offline by the tests; the same IR runs on the same executor).

R cases (section 3, Table 20 call forms) carry Table 21 expectations, and for
H-OSW's two declared deviations (R08, R10) the declared behaviour. Their
coordinates are grid values; expected pixels follow each harness's scaling.
Standard library only.
"""

from __future__ import annotations

import json
from typing import Any

from harness.q2.action_path.ir import SCREEN, Action, parse_sequence

TEMPLATE = {
    "repo": "Qwen/Qwen3.5-9B",
    "revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
    "file": "chat_template.jinja",
    "sha256": "a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715",
    "bytes": 7756,
}
TEMPLATE_SHA256 = TEMPLATE["sha256"]
VARIANTS = {"H-OSW": ("plain", "action", "think"), "H-GA": ("plain", "action", "think", "json")}
ACTION_SENTENCE = "Action: Perform the next step."
THINK_BLOCK = "<think>\nThe next step is clear.\n</think>\n\n"

# The key names the corpus renders for each certified keysym (lowercase, as a model
# writes them); both Stage-1 harnesses map every one of them.
MODEL_KEY_NAMES = {
    "Return": "enter",
    "Escape": "esc",
    "Tab": "tab",
    "BackSpace": "backspace",
    "Delete": "delete",
    "Insert": "insert",
    "Home": "home",
    "End": "end",
    "Prior": "pageup",
    "Next": "pagedown",
    "Up": "up",
    "Down": "down",
    "Left": "left",
    "Right": "right",
    "space": "space",
    "Control_L": "ctrl",
    "Shift_L": "shift",
    "Alt_L": "alt",
    "Super_L": "super",
    "Menu": "menu",
    "KP_Enter": "kp_enter",
    "KP_Add": "kp_add",
    "Caps_Lock": "capslock",
    "F1": "f1",
    "F4": "f4",
    "F5": "f5",
    "F9": "f9",
    "F12": "f12",
}


def scale_hosw(v: float, size: int) -> int:
    """OSWorld bfd62bdc ``adjust_coordinates`` (relative): ``int(x * (size / 999))``."""
    return int(v * (size / 999))


def scale_hga(v: float, size: int) -> int:
    """gym-anything aae6f7607 ``_scale_coordinate``: ``int(x * size / 999.0)``."""
    return int(v * size / 999.0)


SCALES = {"H-OSW": scale_hosw, "H-GA": scale_hga}


def grid_value(pixel: int, size: int, scale) -> int:
    """The 0-999 grid value whose scaled pixel is nearest to ``pixel`` (ties: smaller)."""
    return min(range(1000), key=lambda v: (abs(scale(v, size) - pixel), v))


def grid_point(harness: str, x: int, y: int) -> list[int]:
    scale = SCALES[harness]
    return [grid_value(x, SCREEN[0], scale), grid_value(y, SCREEN[1], scale)]


def render_value(value: Any) -> str:
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render_turn(
    calls: list[dict[str, Any]], content: str = "", reasoning: str | None = None
) -> str:
    """One assistant turn as the template renders it (after ``<|im_start|>assistant\\n``)."""
    out = ""
    if reasoning is not None:
        out += "<think>\n" + reasoning + "\n</think>\n\n"
    out += content
    for index, call in enumerate(calls):
        if index == 0:
            out += (
                "\n\n<tool_call>\n<function=computer_use>\n"
                if content.strip()
                else ("<tool_call>\n<function=computer_use>\n")
            )
        else:
            out += "\n<tool_call>\n<function=computer_use>\n"
        for name, value in call.items():
            out += f"<parameter={name}>\n{render_value(value)}\n</parameter>\n"
        out += "</function>\n</tool_call>"
    return out


def render_json_turn(calls: list[dict[str, Any]]) -> str:
    """H-GA's documented JSON fallback: one JSON object per <tool_call> block."""
    return "\n".join(
        "<tool_call>\n"
        + json.dumps({"name": "computer_use", "arguments": call}, ensure_ascii=False)
        + "\n</tool_call>"
        for call in calls
    )


def render_variant(turns: list[list[dict[str, Any]]], variant: str) -> list[str]:
    if variant == "plain":
        return [render_turn(calls) for calls in turns]
    if variant == "action":
        return [render_turn(calls, content=ACTION_SENTENCE) for calls in turns]
    if variant == "think":
        return [render_turn(calls, reasoning="The next step is clear.") for calls in turns]
    if variant == "json":
        return [render_json_turn(calls) for calls in turns]
    raise ValueError(f"unknown variant {variant}")


def _modifier_text(modifiers: tuple[str, ...]) -> str:
    return "+".join(MODEL_KEY_NAMES[m] for m in modifiers)


def calls_for_action(harness: str, action: Action) -> list[list[dict[str, Any]]]:
    """The turns (each a list of tool calls) one IR action renders to for a harness."""

    def pt(x: int, y: int) -> list[int]:
        return grid_point(harness, x, y)

    op = action.op
    if op == "move":
        return [[{"action": "mouse_move", "coordinate": pt(action.x, action.y)}]]
    if op == "click":
        name = {1: "left_click", 2: "middle_click", 3: "right_click"}[action.button]
        if action.count == 2:
            name = "double_click"
        elif action.count == 3:
            name = "triple_click"
        call: dict[str, Any] = {"action": name}
        if action.x is not None:
            call["coordinate"] = pt(action.x, action.y)
        if action.modifiers:
            call["text"] = _modifier_text(action.modifiers)
        return [[call]]
    if op == "drag":
        path = list(action.path or ())
        if harness == "H-OSW":
            turns = []
            if not action.from_current:
                turns.append([{"action": "mouse_move", "coordinate": pt(*path[0])}])
            turns.append([{"action": "left_click_drag", "coordinate": pt(*path[-1])}])
            return turns
        return [
            [{"action": "left_click_drag", "coordinate": pt(*path[0]), "coordinate2": pt(*path[1])}]
        ]
    if op == "scroll":
        call = {"action": "scroll", "pixels": -int(action.wheel_y or 0)}
        if action.modifiers:
            call["text"] = _modifier_text(action.modifiers)
        if harness == "H-OSW":
            turns = []
            if action.x is not None:
                turns.append([{"action": "mouse_move", "coordinate": pt(action.x, action.y)}])
            return turns + [[call]]
        if action.x is not None:
            call = {
                "action": "scroll",
                "coordinate": pt(action.x, action.y),
                "pixels": call["pixels"],
            }
        return [[call]]
    if op == "key":
        return [[{"action": "key", "keys": [MODEL_KEY_NAMES.get(k, k) for k in action.keys or ()]}]]
    if op == "type":
        return [[{"action": "type", "text": action.text}]]
    if op == "wait":
        return [[{"action": "wait", "time": round((action.ms or 0) / 1000.0, 3)}]]
    if op == "terminate":
        return [[{"action": "terminate", "status": action.status}]]
    raise ValueError(f"{op} has no {harness} rendering")


def entry_turns(harness: str, actions: list[Action]) -> list[list[dict[str, Any]]]:
    turns: list[list[dict[str, Any]]] = []
    for action in actions:
        turns += calls_for_action(harness, action)
    return turns


UNICODE_STRINGS = ("type_unicode_bmp", "type_emoji", "type_rtl", "type_combining", "type_emoji_zwj")


def _px(harness: str, gx: int, gy: int) -> list[int]:
    scale = SCALES[harness]
    return [min(scale(gx, SCREEN[0]), SCREEN[0] - 1), min(scale(gy, SCREEN[1]), SCREEN[1] - 1)]


def r_cases(catalog_text: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Every R case: its turns and, per harness, its status and expectation."""

    def clicks(button: int, point: list[int], n: int) -> list[list[Any]]:
        return [[k, button, *point] for _ in range(n) for k in ("ButtonPress", "ButtonRelease")]

    def held(keys: list[str], inner: list[list[Any]]) -> list[list[Any]]:
        return [["KeyPress", k] for k in keys] + inner + [["KeyRelease", k] for k in reversed(keys)]

    cases: dict[str, dict[str, Any]] = {}

    def case(cid, name, turns, status, build, observable="app", side_effects=(), terminal=None):
        cases[cid] = {
            "name": name,
            "turns": turns,
            "status": status,
            "observable": observable,
            "side_effects": list(side_effects),
            "terminal": terminal,
            "build": build,
        }

    case(
        "R01",
        "middle_click",
        [[{"action": "middle_click", "coordinate": [600, 400]}]],
        {"H-OSW": "gating", "H-GA": "gating"},
        lambda h, d: {"events": clicks(2, _px(h, 600, 400), 1)},
    )
    case(
        "R02",
        "ctrl_click_text",
        [[{"action": "left_click", "coordinate": [300, 250], "text": "ctrl"}]],
        {"H-OSW": "gating", "H-GA": "outside"},
        lambda h, d: {
            "events": held(["Control_L"], clicks(1, _px(h, 300, 250), 1)),
            "button_state_includes": ["Control"],
        },
    )
    case(
        "R03",
        "ctrl_click_keys",
        [[{"action": "left_click", "coordinate": [300, 300], "keys": ["ctrl"]}]],
        {"H-OSW": "outside", "H-GA": "outside"},
        lambda h, d: {
            "events": held(["Control_L"], clicks(1, _px(h, 300, 300), 1)),
            "button_state_includes": ["Control"],
        },
    )
    case(
        "R04",
        "shift_alt_ctrl_shift_clicks",
        [
            [{"action": "left_click", "coordinate": [350, 350], "text": "shift"}],
            [{"action": "left_click", "coordinate": [400, 350], "text": "alt"}],
            [{"action": "left_click", "coordinate": [450, 350], "text": "ctrl+shift"}],
        ],
        {"H-OSW": "gating", "H-GA": "outside"},
        lambda h, d: {
            "events": held(["Shift_L"], clicks(1, _px(h, 350, 350), 1))
            + held(["Alt_L"], clicks(1, _px(h, 400, 350), 1))
            + held(["Control_L", "Shift_L"], clicks(1, _px(h, 450, 350), 1))
        },
    )
    case(
        "R05",
        "move_then_scroll",
        [[{"action": "mouse_move", "coordinate": [480, 600]}, {"action": "scroll", "pixels": -2}]],
        {"H-OSW": "gating", "H-GA": "gating"},
        lambda h, d: {"events": clicks(5, _px(h, 480, 600), 2), "final_pointer": _px(h, 480, 600)},
    )
    case(
        "R06",
        "move_then_drag",
        [
            [
                {"action": "mouse_move", "coordinate": [250, 700]},
                {"action": "left_click_drag", "coordinate": [400, 750]},
            ]
        ],
        {"H-OSW": "gating", "H-GA": "outside"},
        lambda h, d: {
            "events": [
                ["ButtonPress", 1, *_px(h, 250, 700)],
                ["ButtonRelease", 1, *_px(h, 400, 750)],
            ],
            "min_motion_events": 3,
            "final_pointer": _px(h, 400, 750),
        },
    )
    case(
        "R07",
        "three_calls_one_turn",
        [
            [
                {"action": "left_click", "coordinate": [520, 450]},
                {"action": "type", "text": "r7 ok"},
                {"action": "key", "keys": ["enter"]},
            ]
        ],
        {"H-OSW": "gating", "H-GA": "gating"},
        lambda h, d: {
            "events": clicks(1, _px(h, 520, 450), 1),
            "events_scope": "pointer",
            "text": "r7 ok\n",
        },
    )

    def triple(h, declared):
        n = 2 if declared else 3
        out = {"events": clicks(1, _px(h, 560, 650), n), "max_gap_ms": [[0, 2, 300]]}
        if n == 3:
            out["max_gap_ms"].append([2, 4, 300])
        return out

    case(
        "R08",
        "triple_click",
        [[{"action": "triple_click", "coordinate": [560, 650]}]],
        {"H-OSW": "declared", "H-GA": "gating"},
        triple,
    )
    case(
        "R09",
        "scroll_at_coordinate",
        [[{"action": "scroll", "coordinate": [700, 300], "pixels": -3}]],
        {"H-OSW": "outside", "H-GA": "outside"},
        lambda h, d: {"events": clicks(5, _px(h, 700, 300), 3), "final_pointer": _px(h, 700, 300)},
    )

    def hscroll(h, declared):
        button = 5 if declared else 6  # declared: pyautogui.scroll(-3) is down; Table 21: left
        return {"events": clicks(button, _px(h, 520, 520), 3), "final_pointer": _px(h, 520, 520)}

    case(
        "R10",
        "hscroll",
        [
            [{"action": "mouse_move", "coordinate": [520, 520]}],
            [{"action": "hscroll", "pixels": -3}],
        ],
        {"H-OSW": "declared", "H-GA": "outside"},
        hscroll,
    )
    case(
        "R11",
        "terminate_failure",
        [[{"action": "terminate", "status": "failure"}]],
        {"H-OSW": "gating", "H-GA": "gating"},
        lambda h, d: {"events": [], "max_motion_events": 0},
        terminal="failure",
    )
    case(
        "R12",
        "non_ascii_type",
        [[{"action": "type", "text": catalog_text[e]}] for e in UNICODE_STRINGS],
        {"H-OSW": "gating", "H-GA": "gating"},
        lambda h, d: {"text": "".join(catalog_text[e] for e in UNICODE_STRINGS)},
    )
    case(
        "R13",
        "named_keys",
        [
            [{"action": "key", "keys": ["kp_enter"]}],
            [{"action": "key", "keys": ["menu"]}],
            [{"action": "key", "keys": ["super"]}],
        ],
        {"H-OSW": "gating", "H-GA": "gating"},
        lambda h, d: {
            "events": [
                ["KeyPress", "KP_Enter"],
                ["KeyRelease", "KP_Enter"],
                ["KeyPress", "Menu"],
                ["KeyRelease", "Menu"],
                ["KeyPress", "Super_L"],
                ["KeyRelease", "Super_L"],
            ]
        },
        observable="raw-only",
        side_effects=["hot_corner"],
    )
    case(
        "R14",
        "corner_999",
        [[{"action": "left_click", "coordinate": [999, 999]}]],
        {"H-OSW": "gating", "H-GA": "gating"},
        lambda h, d: {"events": clicks(1, [1919, 1079], 1), "tolerance_px": 0},
    )
    return cases


def r_expect(case: dict[str, Any], harness: str, table21: bool = False) -> dict[str, Any]:
    """The expectation of an R case for a harness (Table 21 unless a declared deviation)."""
    declared = case["status"].get(harness) == "declared" and not table21
    expect = {"oracle": "catalog", "tolerance_px": 2, **case["build"](harness, declared)}
    return expect


def harness_cells(
    data: dict[str, Any], expressible: dict[str, Any], harness: str
) -> list[dict[str, Any]]:
    """The A2/C3 cells of one Stage-1 harness: expressible entries, then R cases."""
    by_id = {e["id"]: e for e in data["entries"]}
    text = {e: by_id[e]["expect"]["text"] for e in UNICODE_STRINGS}
    cells = []
    for entry_id in expressible[harness]["expressible"]:
        entry = by_id[entry_id]
        turns = entry_turns(harness, parse_sequence(entry["actions"]))
        cells.append(
            {
                "id": entry_id,
                "source": "catalog",
                "status": "gating",
                "observable": entry["observable"],
                "side_effects": entry.get("side_effects") or [],
                "turns": render_variant(turns, "plain"),
                "variants": {
                    v: render_variant(turns, v) for v in VARIANTS[harness] if v != "plain"
                },
                "expect": entry["expect"],
                "terminal": None,
                **({"control": "no_action"} if entry_id == "no_action_control" else {}),
            }
        )
    for cid, case in r_cases(text).items():
        cells.append(
            {
                "id": cid,
                "source": "r-case",
                "name": case["name"],
                "status": case["status"][harness],
                "observable": case["observable"],
                "side_effects": case["side_effects"],
                "turns": render_variant(case["turns"], "plain"),
                "variants": {
                    v: render_variant(case["turns"], v) for v in VARIANTS[harness] if v != "plain"
                },
                "expect": r_expect(case, harness),
                "table21_expect": r_expect(case, harness, table21=True),
                "terminal": case["terminal"],
            }
        )
    return cells


def control_cells(data: dict[str, Any], harness: str) -> list[dict[str, Any]]:
    """C1 cells: the R cases, judged against Table 21 (rendered as plain turns)."""
    by_id = {e["id"]: e for e in data["entries"]}
    text = {e: by_id[e]["expect"]["text"] for e in UNICODE_STRINGS}
    base = "H-OSW" if harness == "H-OSW-up" else "H-GA"
    cells = []
    for cid, case in r_cases(text).items():
        cells.append(
            {
                "id": cid,
                "source": "r-case",
                "name": case["name"],
                "status": "control",
                "observable": case["observable"],
                "side_effects": case["side_effects"],
                "turns": render_variant(case["turns"], "plain"),
                "expect": r_expect(case, base, table21=True),
                "terminal": case["terminal"],
            }
        )
    return cells


def l0_cells(data: dict[str, Any], gating: list[str]) -> list[dict[str, Any]]:
    cells = []
    for entry in data["entries"]:
        cells.append(
            {
                "id": entry["id"],
                "source": "catalog",
                "status": "gating" if entry["id"] in gating else "non-gating",
                "observable": entry["observable"],
                "side_effects": entry.get("side_effects") or [],
                "actions": [a.to_dict() for a in parse_sequence(entry["actions"])],
                "expect": entry["expect"],
                "terminal": None,
                **({"control": "no_action"} if entry["id"] == "no_action_control" else {}),
            }
        )
    return cells
