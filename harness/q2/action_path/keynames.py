"""Key-name resolution of the upstream runtimes the harness translators reproduce.

Two upstream conventions turn a model's key names into X keysyms:

* PyAutoGUI 0.9.54 (``pyautogui/_pyautogui_x11.py`` ``keyboardMapping``), the
  runtime of OSWorld's harnesses. Names longer than one character are
  lowercased first (``press``, ``keyDown``, ``keyUp`` and ``hotkey`` in
  ``pyautogui/__init__.py``). A name without a mapping is dropped silently
  (``_keyDown`` returns without sending anything): ``pyautogui_keysym``
  returns None for it.
* gym-anything ``aae6f7607`` (``_KEYBOARD_XLIB_PREAMBLE`` in
  ``src/gym_anything/runtime/runners/qemu_apptainer.py``, MIT, Copyright (c)
  2026 cmu-l3): the ``_NAME`` table, then any X keysym name, then a single
  character's own keysym. ``gym_anything_keysym`` follows it; where the
  preamble would find no keysym it raises ``IRError`` (the IR boundary never
  drops a key silently).

The tables are data copied from those files (names and keysym names only).
Standard library only.
"""

from __future__ import annotations

from harness.q2.action_path.ir import CANONICAL_NAME, KEYSYM_VALUES, IRError, canonical_keysym

# PyAutoGUI 0.9.54 keyboardMapping entries with a value (name -> X keysym name).
PYAUTOGUI_NAMED = {
    "backspace": "BackSpace",
    "\b": "BackSpace",
    "tab": "Tab",
    "enter": "Return",
    "return": "Return",
    "shift": "Shift_L",
    "ctrl": "Control_L",
    "alt": "Alt_L",
    "pause": "Pause",
    "capslock": "Caps_Lock",
    "esc": "Escape",
    "escape": "Escape",
    "pgup": "Page_Up",
    "pgdn": "Page_Down",
    "pageup": "Page_Up",
    "pagedown": "Page_Down",
    "end": "End",
    "home": "Home",
    "left": "Left",
    "up": "Up",
    "right": "Right",
    "down": "Down",
    "select": "Select",
    "print": "Print",
    "execute": "Execute",
    "prtsc": "Print",
    "prtscr": "Print",
    "prntscrn": "Print",
    "printscreen": "Print",
    "insert": "Insert",
    "del": "Delete",
    "delete": "Delete",
    "help": "Help",
    "win": "Super_L",
    "winleft": "Super_L",
    "winright": "Super_R",
    "apps": "Menu",
    "multiply": "KP_Multiply",
    "add": "KP_Add",
    "separator": "KP_Separator",
    "subtract": "KP_Subtract",
    "decimal": "KP_Decimal",
    "divide": "KP_Divide",
    "numlock": "Num_Lock",
    "scrolllock": "Scroll_Lock",
    "shiftleft": "Shift_L",
    "shiftright": "Shift_R",
    "ctrlleft": "Control_L",
    "ctrlright": "Control_R",
    "altleft": "Alt_L",
    "altright": "Alt_R",
    " ": "space",
    "space": "space",
    "\t": "Tab",
    "\n": "Return",
    "\r": "Return",
    "\\e": "Escape",
    "!": "exclam",
    "#": "numbersign",
    "%": "percent",
    "$": "dollar",
    "&": "ampersand",
    '"': "quotedbl",
    "'": "apostrophe",
    "(": "parenleft",
    ")": "parenright",
    "*": "asterisk",
    "=": "equal",
    "+": "plus",
    ",": "comma",
    "-": "minus",
    ".": "period",
    "/": "slash",
    ":": "colon",
    ";": "semicolon",
    "<": "less",
    ">": "greater",
    "?": "question",
    "@": "at",
    "[": "bracketleft",
    "]": "bracketright",
    "\\": "backslash",
    "^": "asciicircum",
    "_": "underscore",
    "`": "grave",
    "{": "braceleft",
    "|": "bar",
    "}": "braceright",
    "~": "asciitilde",
}
PYAUTOGUI_NAMED.update({f"num{d}": f"KP_{d}" for d in range(10)})
PYAUTOGUI_NAMED.update({f"f{n}": f"F{n}" for n in range(1, 25)})
for _c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890":
    PYAUTOGUI_NAMED[_c] = _c

# gym-anything aae6f7607 _KEYBOARD_XLIB_PREAMBLE _NAME (lowercase name -> keysym name).
GYM_ANYTHING_NAMES = {
    "ctrl": "Control_L",
    "control": "Control_L",
    "shift": "Shift_L",
    "alt": "Alt_L",
    "super": "Super_L",
    "win": "Super_L",
    "meta": "Super_L",
    "cmd": "Super_L",
    "command": "Super_L",
    "enter": "Return",
    "return": "Return",
    "esc": "Escape",
    "escape": "Escape",
    "tab": "Tab",
    "space": "space",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "pagedown": "Next",
    "pgup": "Prior",
    "pgdn": "Next",
    "page_up": "Prior",
    "page_down": "Next",
    "insert": "Insert",
    "ins": "Insert",
    "kp_enter": "KP_Enter",
    "kp_add": "KP_Add",
    "kp_subtract": "KP_Subtract",
    "kp_multiply": "KP_Multiply",
    "kp_divide": "KP_Divide",
    "menu": "Menu",
    "caps_lock": "Caps_Lock",
    "capslock": "Caps_Lock",
    "num_lock": "Num_Lock",
    "numlock": "Num_Lock",
    "print": "Print",
}
GYM_ANYTHING_NAMES.update({f"f{n}": f"F{n}" for n in range(1, 13)})


def pyautogui_keysym(name: str) -> str | None:
    """The canonical keysym PyAutoGUI 0.9.54 presses for ``name``, or None (dropped)."""
    key = name.lower() if len(name) > 1 else name
    keysym = PYAUTOGUI_NAMED.get(key)
    return canonical_keysym(keysym) if keysym is not None else None


def char_keysym(ch: str) -> str:
    """The canonical keysym name of one character (Latin-1 value, else 0x01000000 + cp)."""
    cp = ord(ch)
    value = cp if cp <= 0xFF else cp | 0x01000000
    name = CANONICAL_NAME.get(value)
    if name is None:
        raise IRError(f"no keysym name for {ch!r}")
    return name


def gym_anything_keysym(name: str) -> str:
    """The canonical keysym gym-anything's runner presses for ``name`` (unknown names raise)."""
    resolved = GYM_ANYTHING_NAMES.get(name.lower(), name)
    if resolved in KEYSYM_VALUES:
        return canonical_keysym(resolved)
    if len(name) == 1:
        return char_keysym(name)
    raise IRError(f"gym-anything resolves no keysym for {name!r}")
