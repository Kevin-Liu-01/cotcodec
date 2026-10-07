"""Canonical action IR for the Q2 action path (one IR, one executor, every harness).

Both Stage-1 harnesses are patched at their emit boundary to produce this IR,
and a single executor (L0-fixed) turns IR into device input. Upstream
pyautogui strings survive only in the L0-raw control. Keeping the executor
fixed keeps it out of the harness factor (reviewed plan, defect B4).

The vocabulary is the paper's (arXiv 2609.40284, Table 21: left, right,
middle, double and triple click; move; drag; hold or release a button; signed
vertical scroll; type; key or chord; hold or release modifiers; wait;
screenshot; done) plus the few device features the action-path catalog needs
(buttons 8 and 9, horizontal wheel, multi-point drags).

Conventions, fixed here so no adapter has to guess:

* Coordinates are integer screen pixels, origin top-left, inside the screen.
* Buttons are X core button numbers: 1 left, 2 middle, 3 right, 8 back,
  9 forward. Wheel buttons 4-7 are never named directly; use ``scroll``.
* ``scroll.wheel_y > 0`` scrolls DOWN (X button 5) by that many wheel clicks;
  ``< 0`` scrolls up (button 4). ``wheel_x > 0`` scrolls RIGHT (button 7),
  ``< 0`` left (button 6). Every adapter converts its own sign convention.
* Keys are X keysym names (``Return``, ``Control_L``, ``KP_Enter``, ``a``):
  any name X.Org's ``keysymdef.h`` defines (``keysyms.json``, 2,109 names),
  so the IR is never narrower than the paper's "key or chord". Aliases are
  stored under their canonical name (``Page_Up`` becomes ``Prior``). An
  unknown name is an error, never a silent drop. Which keysyms the suite
  *certifies* is a separate, smaller set (``CERTIFIED_KEYSYMS`` in
  ``catalog.py``: those the catalog exercises).
* Harness coordinates are clamped to the screen *before* they become IR
  (``clamp_point``), the rule every adapter applies. Upstream, PyAutoGUI
  passes an off-screen point to XTest and the X server clamps it, so
  ``(999, 999)`` on the 0-999 grid lands on ``(1919, 1079)``; the clamp keeps
  that behaviour while the IR itself stays strict and rejects off-screen
  points.
* ``key`` presses keys in order and releases them in reverse order.
* ``modifiers`` on pointer actions are held for the whole action: pressed in
  order before it and released in reverse order after it.
* ``type`` carries the exact code points to enter; no normalization.

Standard library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCREEN = (1920, 1080)
POINTER_BUTTONS = (1, 2, 3, 8, 9)
MAX_TEXT = 2000
MAX_WAIT_MS = 10_000
MAX_WHEEL = 50

# Every keysym name X.Org defines (xorgproto 2024.1 keysymdef.h, MIT/X11 licence;
# see keysyms.json for the source digest and notice). Name -> value, and the
# canonical name of each value (the first name defined for it, in file order).
_KEYSYM_TABLE = json.loads(
    (Path(__file__).resolve().parent / "keysyms.json").read_text(encoding="ascii")
)["keysyms"]
KEYSYM_VALUES: dict[str, int] = {name: value for name, value in _KEYSYM_TABLE}
CANONICAL_NAME: dict[int, str] = {}
for _name, _value in _KEYSYM_TABLE:
    CANONICAL_NAME.setdefault(_value, _name)

# The HMP-referenced subset: X keysym name -> (keysym value, QEMU qcode for the
# HMP reference path or None). qcodes are from QEMU's QKeyCode enum.
_LETTERS = {chr(c): (c, chr(c)) for c in range(ord("a"), ord("z") + 1)}
_DIGITS = {chr(c): (c, chr(c)) for c in range(ord("0"), ord("9") + 1)}
_FKEYS = {f"F{n}": (0xFFBD + n, f"f{n}") for n in range(1, 13)}
KEYSYMS: dict[str, tuple[int, str | None]] = {
    **_LETTERS,
    **_DIGITS,
    **_FKEYS,
    "space": (0x20, "spc"),
    "comma": (0x2C, "comma"),
    "period": (0x2E, "dot"),
    "slash": (0x2F, "slash"),
    "minus": (0x2D, "minus"),
    "equal": (0x3D, "equal"),
    "less": (0x3C, "less"),
    "BackSpace": (0xFF08, "backspace"),
    "Tab": (0xFF09, "tab"),
    "Return": (0xFF0D, "ret"),
    "Escape": (0xFF1B, "esc"),
    "Delete": (0xFFFF, "delete"),
    "Home": (0xFF50, "home"),
    "Left": (0xFF51, "left"),
    "Up": (0xFF52, "up"),
    "Right": (0xFF53, "right"),
    "Down": (0xFF54, "down"),
    "Prior": (0xFF55, "pgup"),
    "Next": (0xFF56, "pgdn"),
    "End": (0xFF57, "end"),
    "Insert": (0xFF63, "insert"),
    "Menu": (0xFF67, "compose"),  # HMP probe: qcode "menu" yields no event, "compose" yields Menu
    "KP_Enter": (0xFF8D, "kp_enter"),
    "KP_Add": (0xFFAB, "kp_add"),
    "Shift_L": (0xFFE1, "shift"),
    "Shift_R": (0xFFE2, "shift_r"),
    "Control_L": (0xFFE3, "ctrl"),
    "Control_R": (0xFFE4, "ctrl_r"),
    "Caps_Lock": (0xFFE5, "caps_lock"),
    "Alt_L": (0xFFE9, "alt"),
    "Alt_R": (0xFFEA, "alt_r"),
    "Super_L": (0xFFEB, "meta_l"),
    "Super_R": (0xFFEC, "meta_r"),
}
MODIFIERS = frozenset(
    {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Super_L", "Super_R"}
)
OPS = (
    "move", "click", "button_down", "button_up", "drag", "scroll", "key", "key_down",
    "key_up", "type", "wait", "screenshot", "terminate",
)  # fmt: skip
EFFECT_FREE = frozenset({"wait", "screenshot", "terminate"})


class IRError(ValueError):
    """An action is outside the canonical IR."""


@dataclass(frozen=True)
class Action:
    """One canonical action. Only the fields its ``op`` uses may be set."""

    op: str
    x: int | None = None
    y: int | None = None
    button: int | None = None
    count: int | None = None
    path: tuple[tuple[int, int], ...] | None = None
    from_current: bool | None = None
    duration_ms: int | None = None
    wheel_x: int | None = None
    wheel_y: int | None = None
    keys: tuple[str, ...] | None = None
    modifiers: tuple[str, ...] = field(default=())
    text: str | None = None
    ms: int | None = None
    status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"op": self.op}
        for name in (
            "x", "y", "button", "count", "from_current", "duration_ms", "wheel_x", "wheel_y",
            "text", "ms", "status",
        ):  # fmt: skip
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        if self.path is not None:
            out["path"] = [list(point) for point in self.path]
        if self.keys is not None:
            out["keys"] = list(self.keys)
        if self.modifiers:
            out["modifiers"] = list(self.modifiers)
        return out


_ALLOWED: dict[str, set[str]] = {
    "move": {"x", "y"},
    "click": {"x", "y", "button", "count", "modifiers"},
    "button_down": {"x", "y", "button"},
    "button_up": {"x", "y", "button"},
    "drag": {"path", "from_current", "button", "modifiers", "duration_ms"},
    "scroll": {"x", "y", "wheel_x", "wheel_y", "modifiers"},
    "key": {"keys"},
    "key_down": {"keys"},
    "key_up": {"keys"},
    "type": {"text"},
    "wait": {"ms"},
    "screenshot": set(),
    "terminate": {"status"},
}


def _int(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise IRError(f"{name} must be an integer in [{low}, {high}]")
    return value


def _point(x: Any, y: Any, screen: tuple[int, int]) -> tuple[int, int]:
    return _int(x, "x", 0, screen[0] - 1), _int(y, "y", 0, screen[1] - 1)


def canonical_keysym(key: Any) -> str:
    """The canonical X keysym name for ``key``; unknown names raise IRError."""
    if not isinstance(key, str) or key not in KEYSYM_VALUES:
        raise IRError(f"unknown keysym name {key!r}")
    return CANONICAL_NAME[KEYSYM_VALUES[key]]


def _keys(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple) or not value:
        raise IRError(f"{name} must be a non-empty list of keysym names")
    keys = []
    for key in value:
        try:
            keys.append(canonical_keysym(key))
        except IRError as exc:
            raise IRError(f"{exc} in {name}") from exc
    if len(set(keys)) != len(keys):
        raise IRError(f"{name} repeats a key")
    return tuple(keys)


def clamp_point(x: float, y: float, screen: tuple[int, int] = SCREEN) -> tuple[int, int]:
    """The IR-boundary rule for harness coordinates: truncate, then clamp to the screen.

    Both Stage-1 harnesses scale the 0-999 grid with ``int(v * size / 999)``,
    so 999 becomes 1920 or 1080, one pixel off screen. Upstream the X server
    clamps the XTest motion; adapters call this function instead, so the IR
    receives the pixel X would have used. Frozen in the preregistration; the
    regression case R14 checks it.
    """
    return (
        min(max(int(x), 0), screen[0] - 1),
        min(max(int(y), 0), screen[1] - 1),
    )


def parse_action(raw: dict[str, Any], screen: tuple[int, int] = SCREEN) -> Action:
    """Validate one action dict strictly; unknown fields and values raise IRError."""
    if not isinstance(raw, dict) or raw.get("op") not in OPS:
        raise IRError(f"op must be one of {OPS}")
    op = raw["op"]
    extra = set(raw) - {"op"} - _ALLOWED[op]
    if extra:
        raise IRError(f"{op} does not take {sorted(extra)}")
    kwargs: dict[str, Any] = {"op": op}
    has_xy = "x" in raw or "y" in raw
    if has_xy:
        kwargs["x"], kwargs["y"] = _point(raw.get("x"), raw.get("y"), screen)
    if "modifiers" in raw:
        mods = _keys(raw["modifiers"], "modifiers")
        if not set(mods) <= MODIFIERS:
            raise IRError("modifiers must be modifier keysyms")
        kwargs["modifiers"] = mods
    if op == "move":
        if not has_xy:
            raise IRError("move needs x and y")
    elif op == "click":
        kwargs["button"] = raw.get("button", 1)
        if kwargs["button"] not in POINTER_BUTTONS:
            raise IRError(f"click button must be one of {POINTER_BUTTONS}")
        kwargs["count"] = _int(raw.get("count", 1), "count", 1, 3)
    elif op in ("button_down", "button_up"):
        if raw.get("button") not in POINTER_BUTTONS:
            raise IRError(f"{op} button must be one of {POINTER_BUTTONS}")
        kwargs["button"] = raw["button"]
    elif op == "drag":
        path = raw.get("path")
        if not isinstance(path, list | tuple) or not path:
            raise IRError("drag needs a path")
        points = tuple(_point(p[0], p[1], screen) for p in path if isinstance(p, list | tuple))
        if len(points) != len(path) or any(len(p) != 2 for p in path):
            raise IRError("drag path points must be [x, y] pairs")
        from_current = raw.get("from_current", False)
        if not isinstance(from_current, bool):
            raise IRError("from_current must be a boolean")
        if len(points) < (1 if from_current else 2):
            raise IRError("drag needs two points, or one point with from_current")
        kwargs["path"] = points
        kwargs["from_current"] = from_current
        kwargs["button"] = raw.get("button", 1)
        if kwargs["button"] not in (1, 2, 3):
            raise IRError("drag button must be 1, 2 or 3")
        kwargs["duration_ms"] = _int(raw.get("duration_ms", 500), "duration_ms", 0, MAX_WAIT_MS)
    elif op == "scroll":
        wheel_x = _int(raw.get("wheel_x", 0), "wheel_x", -MAX_WHEEL, MAX_WHEEL)
        wheel_y = _int(raw.get("wheel_y", 0), "wheel_y", -MAX_WHEEL, MAX_WHEEL)
        if wheel_x == 0 and wheel_y == 0:
            raise IRError("scroll needs a non-zero wheel_x or wheel_y")
        kwargs["wheel_x"] = wheel_x or None
        kwargs["wheel_y"] = wheel_y or None
    elif op in ("key", "key_down", "key_up"):
        kwargs["keys"] = _keys(raw.get("keys"), "keys")
    elif op == "type":
        text = raw.get("text")
        if not isinstance(text, str) or not text or len(text) > MAX_TEXT:
            raise IRError(f"type needs 1-{MAX_TEXT} characters of text")
        kwargs["text"] = text
    elif op == "wait":
        kwargs["ms"] = _int(raw.get("ms"), "ms", 0, MAX_WAIT_MS)
    elif op == "terminate":
        if raw.get("status") not in ("success", "failure"):
            raise IRError("terminate status must be success or failure")
        kwargs["status"] = raw["status"]
    return Action(**kwargs)


def parse_sequence(raw: list[dict[str, Any]], screen: tuple[int, int] = SCREEN) -> list[Action]:
    if not isinstance(raw, list):
        raise IRError("an action sequence must be a list")
    return [parse_action(item, screen) for item in raw]


def held_after(actions: list[Action]) -> list[str]:
    """Keys still held after a sequence (key_down without a matching key_up)."""
    held: list[str] = []
    for action in actions:
        if action.op == "key_down":
            for key in action.keys or ():
                if key in held:
                    raise IRError(f"{key} pressed twice without release")
                held.append(key)
        elif action.op == "key_up":
            for key in action.keys or ():
                if key not in held:
                    raise IRError(f"{key} released without a press")
                held.remove(key)
    return held


def canonical_json(actions: list[Action]) -> str:
    return json.dumps([a.to_dict() for a in actions], sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)  # fmt: skip
