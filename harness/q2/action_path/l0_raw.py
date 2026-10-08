"""L0-raw control translator: one IR action -> one natural PyAutoGUI 0.9.54 command.

The L0-raw layer is a control (validity control C2), not a system under test.
Each IR action becomes the call an upstream harness would naturally write, and
is sent unchanged as one ``DesktopEnv.step(command, pause=0.0)`` of OSWorld
b138d348, which runs ``python -c PYAUTOGUI_PKGS_PREFIX + command`` in the guest.
Its predicted failing set is ``l0_raw_prediction.yaml``, written from code
reading. This module is frozen with the main preregistration (its SHA-256 is
listed there), so the translation that decides C2 cannot be chosen after C2 is
seen (review finding: it used to be frozen only after development).

Names, fixed here and mirrored in ``l0_raw_prediction.yaml`` (a test checks the
two agree):

* Keys use PyAutoGUI's own names where one exists (``KEY_NAMES``); otherwise
  the lowercase keysym name is sent unchanged, as an upstream harness would.
* Buttons use PyAutoGUI's own names: 1 ``'left'``, 2 ``'middle'``, 3
  ``'right'``. Buttons 8 and 9 have no PyAutoGUI name and are passed as the
  integer. (PyAutoGUI 0.9.54 ``_normalizeButton`` calls ``button.lower()``
  before any range check, so *every* integer button raises AttributeError;
  passing 1-3 as integers would make every click fail for a reason that has
  nothing to do with the runtime path.)
* Strings are embedded with ``json.dumps(..., ensure_ascii=False)``, the
  convention of OSWorld bfd62bdc's Qwen3.5 agent.

Standard library only.
"""

from __future__ import annotations

import json

from harness.q2.action_path.ir import Action

# IR keysym -> PyAutoGUI 0.9.54 key name (pyautogui/_pyautogui_x11.py keyboardMapping).
KEY_NAMES: dict[str, str] = {
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
    "Super_L": "winleft",
    "Menu": "apps",
    "KP_Add": "add",
    "KP_Enter": "kp_enter",
    "Caps_Lock": "capslock",
    "F1": "f1",
    "F4": "f4",
    "F5": "f5",
    "F9": "f9",
    "F12": "f12",
}
# IR button -> PyAutoGUI button argument. 8 and 9 have no name: the int is passed.
BUTTON_NAMES: dict[int, str | int] = {1: "left", 2: "middle", 3: "right", 8: 8, 9: 9}


class L0RawError(ValueError):
    """An IR action the L0-raw control has no translation for."""


def _lit(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def key_name(keysym: str) -> str:
    return KEY_NAMES.get(keysym, keysym.lower())


def button_arg(button: int) -> str:
    if button not in BUTTON_NAMES:
        raise L0RawError(f"no L0-raw button for {button}")
    return _lit(BUTTON_NAMES[button])


def _seconds(ms: float) -> str:
    return repr(round(ms / 1000.0, 6))


def _held(mods: tuple[str, ...], inner: list[str]) -> list[str]:
    down = [f"pyautogui.keyDown({_lit(key_name(m))})" for m in mods]
    up = [f"pyautogui.keyUp({_lit(key_name(m))})" for m in reversed(mods)]
    return down + inner + up


def translate(action: Action) -> str:
    """The Python command for one ``DesktopEnv.step`` (without OSWorld's prefix)."""
    op = action.op
    if op == "move":
        calls = [f"pyautogui.moveTo({action.x}, {action.y})"]
    elif op == "click":
        button = button_arg(int(action.button or 1))
        if action.count == 3:
            inner = f"pyautogui.tripleClick({action.x}, {action.y}, button={button})"
        else:
            inner = (
                f"pyautogui.click({action.x}, {action.y}, clicks={action.count or 1}, "
                f"button={button})"
            )
        calls = _held(action.modifiers, [inner])
    elif op in ("button_down", "button_up"):
        call = "mouseDown" if op == "button_down" else "mouseUp"
        button = button_arg(int(action.button or 0))
        calls = [f"pyautogui.{call}({action.x}, {action.y}, button={button})"]
    elif op == "drag":
        path = list(action.path or ())
        button = button_arg(int(action.button or 1))
        inner = []
        if not action.from_current:
            x0, y0 = path.pop(0)
            inner.append(f"pyautogui.moveTo({x0}, {y0})")
        inner.append(f"pyautogui.mouseDown(button={button})")
        segment = _seconds((action.duration_ms or 0) / len(path))
        inner += [f"pyautogui.moveTo({x}, {y}, duration={segment})" for x, y in path]
        inner.append(f"pyautogui.mouseUp(button={button})")
        calls = _held(action.modifiers, inner)
    elif op == "scroll":
        inner = []
        if action.wheel_y:
            inner.append(f"pyautogui.scroll({-action.wheel_y}, {action.x}, {action.y})")
        if action.wheel_x:
            inner.append(f"pyautogui.hscroll({action.wheel_x}, {action.x}, {action.y})")
        calls = _held(action.modifiers, inner)
    elif op == "key":
        names = [_lit(key_name(k)) for k in action.keys or ()]
        call = "press" if len(names) == 1 else "hotkey"
        calls = [f"pyautogui.{call}({', '.join(names)})"]
    elif op in ("key_down", "key_up"):
        call = "keyDown" if op == "key_down" else "keyUp"
        calls = [f"pyautogui.{call}({_lit(key_name(k))})" for k in action.keys or ()]
    elif op == "type":
        calls = [f"pyautogui.typewrite({_lit(action.text)})"]
    elif op == "wait":
        calls = [f"time.sleep({_seconds(action.ms or 0)})"]
    else:
        # screenshot and terminate never reach the device; the catalog has none.
        raise L0RawError(f"L0-raw has no device translation for {op}")
    return "; ".join(calls)


def translate_entry(actions: list[Action]) -> list[str]:
    """One command per IR action, in order (one ``DesktopEnv.step`` each)."""
    return [translate(action) for action in actions]
