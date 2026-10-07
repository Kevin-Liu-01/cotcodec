"""Detection-control translators for validity control C1 (frozen in the inputs addendum).

C1 runs two upstream parsers that carry known defects, unmodified, and must
see them fail (preregistration section 8). Their outputs are not IR, so each
gets a fixed translator that maps its output call for call to the canonical
IR, reproducing what the upstream runtime would do with it; the IR then runs
on the frozen L0-fixed executor.

* **H-OSW-up**: OSWorld ``bfd62bdc`` ``Qwen35VLAgent.parse_response``
  (vendored unmodified in ``upstream/osworld_bfd62bdc.py``) returns PyAutoGUI
  code strings plus ``WAIT`` and ``DONE``. ``translate_hosw_up`` parses each
  string as one Python call expression (``ast``, never ``eval``) and maps it:
  ``click``/``rightClick``/``middleClick``/``doubleClick`` (optional x, y) to
  ``click``; ``moveTo`` to ``move``; ``dragTo(x, y, duration=d)`` to a drag
  from the current pointer; ``scroll(n)`` to a vertical scroll at the current
  pointer (PyAutoGUI: positive is up, so ``wheel_y = -n``; ``n == 0`` sends
  nothing); ``typewrite(s)`` to ``type``; ``press``/``hotkey``/``keyDown``/
  ``keyUp`` to key actions with PyAutoGUI's own name resolution, dropping the
  names PyAutoGUI drops (``keynames.pyautogui_keysym``); ``WAIT`` to a zero
  wait (``DesktopEnv.step('WAIT', pause=0.0)`` sleeps ``pause``); ``DONE`` to
  ``terminate(success)``; ``FAIL`` to ``terminate(failure)``.
* **H-GA-buggy**: gym-anything ``bf965cde0`` ``Qwen35VLAgent._parse_response``
  (vendored unmodified in ``upstream/gym_anything_bf965cde0.py``) returns
  gym-anything runner action dicts and metadata. ``translate_ga_dicts`` maps
  ``keyboard.keys``/``keys_down``/``keys_up``/``text`` and ``mouse.move``/
  ``left_click``/``right_click``/``middle_click``/``double_click``/
  ``triple_click``/``left_click_drag``/``buttons``/``scroll`` (the runner's
  convention: positive scrolls down, ``int(value)`` ticks) with gym-anything's
  key-name resolution; ``{"action": "screenshot"}`` and ``{"action": "wait"}``
  become ``screenshot`` and ``wait``; ``metadata.is_terminal`` becomes
  ``terminate`` with ``metadata.status``.

Both apply the IR-boundary clamp to coordinates (``ir.clamp_point``) so the
IR stays valid; neither fixes anything else. The H-GA (Stage-1) adapter
reuses ``translate_ga_dicts`` (gym-anything ``aae6f7607`` emits the same
action-dict vocabulary), which is why it lives here, frozen before any
executor code.
"""

from __future__ import annotations

import ast
from typing import Any

from harness.q2.action_path.ir import Action, IRError, clamp_point, parse_action
from harness.q2.action_path.keynames import gym_anything_keysym, pyautogui_keysym

SCREEN = (1920, 1080)
DRAG_MS_DEFAULT = 500  # IR default; gym-anything's runner drag has no duration


class TranslationError(ValueError):
    """An upstream output the translator has no mapping for."""


def _point(x: Any, y: Any) -> dict[str, int]:
    px, py = clamp_point(float(x), float(y))
    return {"x": px, "y": py}


def _call(code: str) -> tuple[str, list[Any], dict[str, Any]]:
    try:
        tree = ast.parse(code.strip(), mode="eval")
    except SyntaxError as exc:
        raise TranslationError(f"not a call expression: {code!r}") from exc
    node = tree.body
    if (
        not isinstance(node, ast.Call)
        or not isinstance(node.func, ast.Attribute)
        or not isinstance(node.func.value, ast.Name)
        or node.func.value.id != "pyautogui"
    ):
        raise TranslationError(f"not a pyautogui call: {code!r}")
    try:
        args = [ast.literal_eval(arg) for arg in node.args]
        kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords if kw.arg}
    except ValueError as exc:
        raise TranslationError(f"non-literal argument in {code!r}") from exc
    return node.func.attr, args, kwargs


def _keys(names: list[str]) -> list[str]:
    out = []
    for name in names:
        keysym = pyautogui_keysym(str(name))
        if keysym is not None:
            out.append(keysym)
    return out


def translate_pyautogui(code: str) -> list[dict[str, Any]]:
    """IR dicts for one H-OSW-up output string."""
    if code == "WAIT":
        return [{"op": "wait", "ms": 0}]
    if code == "DONE":
        return [{"op": "terminate", "status": "success"}]
    if code == "FAIL":
        return [{"op": "terminate", "status": "failure"}]
    name, args, kwargs = _call(code)
    clicks = {"click": (1, 1), "rightClick": (3, 1), "middleClick": (2, 1), "doubleClick": (1, 2)}
    if name in clicks:
        button, count = clicks[name]
        out: dict[str, Any] = {"op": "click", "button": button, "count": count}
        if len(args) >= 2:
            out.update(_point(args[0], args[1]))
        return [out]
    if name == "moveTo":
        return [{"op": "move", **_point(args[0], args[1])}]
    if name == "dragTo":
        duration = float(kwargs.get("duration", args[2] if len(args) > 2 else 0.0))
        target = _point(args[0], args[1])
        return [
            {
                "op": "drag",
                "path": [[target["x"], target["y"]]],
                "from_current": True,
                "duration_ms": int(round(duration * 1000)),
            }
        ]
    if name == "scroll":
        clicks_n = int(args[0])
        return [{"op": "scroll", "wheel_y": -clicks_n}] if clicks_n else []
    if name in ("typewrite", "write"):
        text = str(args[0])
        return [{"op": "type", "text": text}] if text else []
    if name in ("press", "hotkey"):
        names = list(args[0]) if len(args) == 1 and isinstance(args[0], list) else list(args)
        keys = _keys(names)
        return [{"op": "key", "keys": keys}] if keys else []
    if name in ("keyDown", "keyUp"):
        keys = _keys([args[0]])
        op = "key_down" if name == "keyDown" else "key_up"
        return [{"op": op, "keys": keys}] if keys else []
    raise TranslationError(f"H-OSW-up translator has no mapping for pyautogui.{name}")


def translate_hosw_up(codes: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for code in codes:
        out.extend(translate_pyautogui(code))
    return out


def _ga_keys(value: Any) -> list[str]:
    names = [value] if isinstance(value, str) else list(value or [])
    return [gym_anything_keysym(str(name)) for name in names]


def translate_ga_action(action: dict[str, Any]) -> list[dict[str, Any]]:
    """IR dicts for one gym-anything runner action dict."""
    if action.get("action") == "screenshot":
        return [{"op": "screenshot"}]
    if action.get("action") == "wait":
        return [{"op": "wait", "ms": int(round(float(action.get("time", 1.0)) * 1000))}]
    out: list[dict[str, Any]] = []
    keyboard = action.get("keyboard")
    if keyboard is not None:
        if "text" in keyboard and str(keyboard["text"]):
            out.append({"op": "type", "text": str(keyboard["text"])})
        if "keys" in keyboard and _ga_keys(keyboard["keys"]):
            out.append({"op": "key", "keys": _ga_keys(keyboard["keys"])})
        if "keys_down" in keyboard:
            out.append({"op": "key_down", "keys": _ga_keys(keyboard["keys_down"])})
        if "keys_up" in keyboard:
            out.append({"op": "key_up", "keys": _ga_keys(keyboard["keys_up"])})
        return out
    mouse = action.get("mouse")
    if mouse is None:
        raise TranslationError(f"unknown action dict {action!r}")
    if "move" in mouse:
        out.append({"op": "move", **_point(*mouse["move"])})
    for key, button, count in (
        ("left_click", 1, 1),
        ("right_click", 3, 1),
        ("middle_click", 2, 1),
        ("double_click", 1, 2),
        ("triple_click", 1, 3),
    ):
        if key in mouse:
            out.append({"op": "click", "button": button, "count": count, **_point(*mouse[key])})
    if "left_click_drag" in mouse:
        (x1, y1), (x2, y2) = mouse["left_click_drag"]
        start, end = _point(x1, y1), _point(x2, y2)
        out.append(
            {
                "op": "drag",
                "path": [[start["x"], start["y"]], [end["x"], end["y"]]],
                "duration_ms": DRAG_MS_DEFAULT,
            }
        )
    buttons = mouse.get("buttons") or {}
    for name, number in (("left", 1), ("right", 3), ("middle", 2)):
        down, up = buttons.get(name + "_down"), buttons.get(name + "_up")
        if down and up:
            out.append({"op": "click", "button": number, "count": 1})
        elif down:
            out.append({"op": "button_down", "button": number})
        elif up:
            out.append({"op": "button_up", "button": number})
    if "scroll" in mouse:
        ticks = int(float(mouse["scroll"]))
        if ticks:
            out.append({"op": "scroll", "wheel_y": ticks})
    return out


def ga_step_actions(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """The action dicts gym-anything's ``Qwen35VLAgent.step`` returns for a parse result.

    Both revisions (bf965cde0 and aae6f7607) return every action when the
    response is terminal, and only ``{"action": "wait"}`` when the parse set a
    wait time, dropping the response's other actions.
    """
    metadata = parsed.get("metadata") or {}
    if metadata.get("is_terminal"):
        return list(parsed.get("actions") or [])
    if metadata.get("wait_time") is not None:
        return [{"action": "wait", "time": metadata["wait_time"]}]
    return list(parsed.get("actions") or [])


def translate_ga_dicts(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """IR dicts for one gym-anything parse result ({"actions": [...], "metadata": {...}})."""
    out: list[dict[str, Any]] = []
    for action in ga_step_actions(parsed):
        out.extend(translate_ga_action(action))
    metadata = parsed.get("metadata") or {}
    if metadata.get("is_terminal"):
        status = str(metadata.get("status", "success")).strip().lower()
        out.append({"op": "terminate", "status": "failure" if status == "failure" else "success"})
    return out


def to_ir(dicts: list[dict[str, Any]]) -> list[Action]:
    """Validate translated dicts as IR; the first invalid one raises IRError."""
    actions = []
    for raw in dicts:
        try:
            actions.append(parse_action(raw, SCREEN))
        except IRError as exc:
            raise IRError(f"{exc} in {raw!r}") from exc
    return actions


def run_hosw_up(response: str, width: int = 1920, height: int = 1080) -> list[dict[str, Any]]:
    """H-OSW-up end to end: the unmodified upstream parser, then the translator."""
    from harness.q2.action_path.upstream.osworld_bfd62bdc import Qwen35VLAgent

    _, codes = Qwen35VLAgent(coordinate_type="relative").parse_response(
        response,
        original_width=width,
        original_height=height,
        processed_width=width,
        processed_height=height,
    )
    return translate_hosw_up(codes)


def run_ga_buggy(response: str) -> list[dict[str, Any]]:
    """H-GA-buggy end to end: the unmodified bf965cde0 parser, then the translator."""
    from harness.q2.action_path.upstream.gym_anything_bf965cde0 import Qwen35VLAgent

    parsed = Qwen35VLAgent()._parse_response(response)
    return translate_ga_dicts(parsed)
