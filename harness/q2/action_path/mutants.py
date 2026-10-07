"""Suite-mutation kit: the mutants of ``mutation_operators.yaml`` (schema v2) as source patches.

Validity control C3 mutates the code under test and requires the suite to kill
every scored, non-equivalent mutant (preregistration section 8). Each
(operator, layer) pair whose status is ``scored`` is one mutant, defined here
as exact text substitutions on the frozen sources:

* ``L0-fixed``: ``harness/q2/vm/guest/l0_fixed.py`` (the executor);
* ``H-OSW-fixed``: ``upstream/osworld_bfd62bdc_fixed.py`` (the patched parser);
* ``H-GA``: the vendored ``upstream/gym_anything_aae6f7607.py`` parser, or
  its adapter's key-name and translation code (``keynames.py``,
  ``controls.py``), for the operators that act there.

Every substitution must match its anchor exactly ``count`` times, so a
mutant can never silently become the unmutated code when the frozen source
changes. ``build`` returns the patched sources; ``load_layer`` turns them into
a response parser (harness layers) or an executor source string (L0-fixed)
for a mutant run. The detection controls are never mutated. Whether a mutant
is killed or equivalent is decided only by running it (``equivalence_rule``);
the offline tests check that each patch applies and changes the code, and,
for parser mutants, which cells' IR it changes.

Standard library only.
"""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
L0 = "harness/q2/vm/guest/l0_fixed.py"
HOSW = "harness/q2/action_path/upstream/osworld_bfd62bdc_fixed.py"
HGA = "harness/q2/action_path/upstream/gym_anything_aae6f7607.py"
KEYNAMES = "harness/q2/action_path/keynames.py"
CONTROLS = "harness/q2/action_path/controls.py"
MODULE_NAMES = {
    HOSW: "harness.q2.action_path.upstream.osworld_bfd62bdc_fixed",
    HGA: "harness.q2.action_path.upstream.gym_anything_aae6f7607",
    KEYNAMES: "harness.q2.action_path.keynames",
    CONTROLS: "harness.q2.action_path.controls",
}
MAIN_BLOCK_KEYSYMS = "(0xFF8D, 0xFFAB, 0xFF67, 0xFFE5, 0xFFEB)"  # KP_Enter KP_Add Menu Caps Super_L

Patch = tuple[str, str, str, int]  # (path, old, new, expected count)

PATCHES: dict[tuple[str, str], list[Patch]] = {
    # --- L0-fixed (the executor) ---------------------------------------------------------
    ("M01-modifier-released-early", "L0-fixed"): [
        (L0, "        pressed = self.press_keys(modifiers) if modifiers else []\n        try:\n"
             "            body()\n",
         "        pressed = self.press_keys(modifiers) if modifiers else []\n"
         "        self.release_keys(pressed)\n        pressed = []\n        try:\n"
         "            body()\n", 1),
    ],
    ("M02-button-swap-left-right", "L0-fixed"): [
        (L0, "self._fake(self.X.ButtonPress, button)",
         "self._fake(self.X.ButtonPress, {1: 3, 3: 1}.get(button, button))", 1),
        (L0, "self._fake(self.X.ButtonRelease, button)",
         "self._fake(self.X.ButtonRelease, {1: 3, 3: 1}.get(button, button))", 1),
    ],
    ("M03-middle-click-noop", "L0-fixed"): [
        (L0, '        button = action.get("button", 1)\n        count = action.get("count", 1)\n',
         '        button = action.get("button", 1)\n        count = action.get("count", 1)\n'
         "        if button == 2:\n            return\n", 1),
    ],
    ("M04-coordinate-shift-5px", "L0-fixed"): [
        (L0, "self._fake(self.X.MotionNotify, x=x, y=y)",
         "self._fake(self.X.MotionNotify, x=x + 5, y=y)", 1),
    ],
    ("M05-scroll-sign-flip", "L0-fixed"): [
        (L0, "(5 if wheel_y > 0 else 4, abs(wheel_y))", "(4 if wheel_y > 0 else 5, abs(wheel_y))", 1),
    ],
    ("M06-scroll-ticks-doubled", "L0-fixed"): [
        (L0, "                for _ in range(ticks):\n", "                for _ in range(2 * ticks):\n", 1),
    ],
    ("M07-text-drop-last-char", "L0-fixed"): [
        (L0, "        for piece in self.segments(text):\n", "        for piece in self.segments(text[:-1]):\n", 1),
    ],
    ("M08-text-nfc-normalize", "L0-fixed"): [
        (L0, "        for piece in self.segments(text):\n", '        for piece in self.segments(__import__("unicodedata").normalize("NFC", text)):\n', 1),
    ],
    ("M09-text-drop-non-ascii", "L0-fixed"): [
        (L0, "        for piece in self.segments(text):\n", '        for piece in self.segments("".join(c for c in text if ord(c) < 0x80)):\n', 1),
    ],
    ("M10-less-to-greater", "L0-fixed"): [
        (L0, "            keycode, shifted = self.resolve(char_keysym(ch))\n",
         "            keycode, shifted = self.resolve(char_keysym(ch))\n"
         '            if ch == "<":\n                shifted = True\n', 1),
    ],
    ("M11-unknown-key-dropped", "L0-fixed"): [
        (L0, "        resolved = [self.resolve(k) for k in keysyms]\n",
         f"        resolved = [self.resolve(k) for k in keysyms if k not in {MAIN_BLOCK_KEYSYMS}]\n", 1),
    ],
    ("M12-triple-to-double", "L0-fixed"): [
        (L0, '        count = action.get("count", 1)\n', '        count = min(action.get("count", 1), 2)\n', 1),
    ],
    ("M13-hscroll-to-vscroll", "L0-fixed"): [
        (L0, "(7 if wheel_x > 0 else 6, abs(wheel_x))", "(5 if wheel_x > 0 else 4, abs(wheel_x))", 1),
    ],
    ("M14-chord-release-order", "L0-fixed"): [
        (L0, "        for keycode in reversed(keycodes):\n", "        for keycode in keycodes:\n", 1),
    ],
    ("M15-duplicate-click", "L0-fixed"): [
        (L0, "            for index in range(count):\n",
         "            for index in range(count if count > 1 else 2):\n", 1),
    ],
    ("M16-double-click-interval-600ms", "L0-fixed"): [
        (L0, "                    time.sleep(CLICK_GAP_S)\n", "                    time.sleep(0.6)\n", 1),
    ],
    ("M17-drag-teleport", "L0-fixed"): [
        (L0, 'drag_points(start, rest, action.get("duration_ms", 500)):',
         'drag_points(start, rest, action.get("duration_ms", 500))[-1:]:', 1),
    ],
    ("M21-hold-not-released", "L0-fixed"): [
        (L0, "        finally:\n            self.release_keys(pressed)\n\n    def click",
         "        finally:\n            self.held_keys = []\n\n    def click", 1),
    ],
    ("M22-keypad-to-main", "L0-fixed"): [
        (L0, '        """(keycode, shift) for a keysym, remapping an owned spare keycode if needed."""\n',
         '        """(keycode, shift) for a keysym, remapping an owned spare keycode if needed."""\n'
         "        keysym = {0xFF8D: 0xFF0D, 0xFFAB: 0x2B}.get(keysym, keysym)\n", 1),
    ],
    ("M23-caps-lock-dropped", "L0-fixed"): [
        (L0, "        resolved = [self.resolve(k) for k in keysyms]\n",
         "        resolved = [self.resolve(k) for k in keysyms if k != 0xFFE5]\n", 1),
    ],
    ("M25-shell-expansion", "L0-fixed"): [
        (L0, "        for piece in self.segments(text):\n",
         '        text = __import__("subprocess").run(["sh", "-c", "printf %s " + text],'
         " capture_output=True, text=True).stdout\n        for piece in self.segments(text):\n", 1),
    ],
    ("M26-newline-dropped", "L0-fixed"): [
        (L0, "        for piece in self.segments(text):\n", '        for piece in self.segments(text.replace("\\n", "")):\n', 1),
    ],
    ("M27-extra-buttons-dropped", "L0-fixed"): [
        (L0, '        button = action.get("button", 1)\n        count = action.get("count", 1)\n',
         '        button = action.get("button", 1)\n        count = action.get("count", 1)\n'
         "        if button in (8, 9):\n            return\n", 1),
    ],
    # --- H-OSW-fixed (the patched OSWorld parser) ------------------------------------------
    ("M01-modifier-released-early", "H-OSW-fixed"): [
        (HOSW, '                if modifiers():\n                    ir["modifiers"] = modifiers()\n'
               "                ir_actions.append(ir)\n",
         "                if modifiers():\n"
         '                    ir_actions.append({"op": "key", "keys": modifiers()})\n'
         "                ir_actions.append(ir)\n", 1),
    ],
    ("M03-middle-click-noop", "H-OSW-fixed"): [
        (HOSW, '            elif action == "middle_click":\n                click(2, 1)\n',
         '            elif action == "middle_click":\n                pass\n', 1),
    ],
    ("M05-scroll-sign-flip", "H-OSW-fixed"): [
        (HOSW, 'ir = {"op": "scroll", "wheel_y": -pixels}', 'ir = {"op": "scroll", "wheel_y": pixels}', 1),
    ],
    ("M11-unknown-key-dropped", "H-OSW-fixed"): [
        (HOSW, '                ir_actions.append({"op": "key", "keys": [map_key(key) for key in keys]})\n',
         "                kept = [map_key(key) for key in keys if map_key(key) not in\n"
         '                        ("KP_Enter", "KP_Add", "Menu", "Caps_Lock", "Super_L")]\n'
         "                if kept:\n"
         '                    ir_actions.append({"op": "key", "keys": kept})\n', 1),
    ],
    ("M12-triple-to-double", "H-OSW-fixed"): [
        (HOSW, "                click(1, 2)  # declared design difference: simulated as double-click\n",
         "                click(1, 2)  # M12: triple sent as double (already declared)\n", 1),
    ],
    ("M13-hscroll-to-vscroll", "H-OSW-fixed"): [
        (HOSW, '            elif action in {"scroll", "hscroll"}:\n',
         '            elif action in {"scroll", "hscroll"}:  # M13: hscroll on the vertical axis\n', 1),
    ],
    ("M18-first-tool-call-only", "H-OSW-fixed"): [
        (HOSW, 'for tool_call_match in re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL):',
         'for tool_call_match in list(re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL))[:1]:',
         1),
    ],
    ("M19-last-tool-call-only", "H-OSW-fixed"): [
        (HOSW, 'for tool_call_match in re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL):',
         'for tool_call_match in list(re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL))[-1:]:',
         1),
    ],
    ("M20-terminate-failure-to-done", "H-OSW-fixed"): [
        (HOSW, '                failed = action == "terminate" and status == "failure"\n',
         "                failed = False\n", 1),
    ],
    ("M22-keypad-to-main", "H-OSW-fixed"): [
        (HOSW, '"kp_enter": "KP_Enter", "kp_add": "KP_Add",', '"kp_enter": "Return", "kp_add": "plus",', 1),
    ],
    ("M24-grid-1000-instead-of-999", "H-OSW-fixed"): [
        (HOSW, "            x_scale = original_width / 999\n            y_scale = original_height / 999\n",
         "            x_scale = original_width / 1000\n            y_scale = original_height / 1000\n", 1),
    ],
    ("M28-modifier-text-ignored", "H-OSW-fixed"): [
        (HOSW, '                if modifiers():\n                    ir["modifiers"] = modifiers()\n'
               "                ir_actions.append(ir)\n",
         "                ir_actions.append(ir)\n", 1),
    ],
    # --- H-GA (the vendored gym-anything parser and its adapter) ----------------------------
    ("M03-middle-click-noop", "H-GA"): [
        (HGA, '                    actions.append({"mouse": {"middle_click": point}})\n',
         "                    pass\n", 1),
    ],
    ("M05-scroll-sign-flip", "H-GA"): [
        (HGA, '                    actions.append({"mouse": {"scroll": -bounded_steps}})\n',
         '                    actions.append({"mouse": {"scroll": bounded_steps}})\n', 1),
    ],
    ("M11-unknown-key-dropped", "H-GA"): [
        (CONTROLS, "    return [gym_anything_keysym(str(name)) for name in names]\n",
         "    return [k for k in (gym_anything_keysym(str(name)) for name in names)\n"
         '            if k not in ("KP_Enter", "KP_Add", "Menu", "Caps_Lock", "Super_L")]\n', 1),
    ],
    ("M12-triple-to-double", "H-GA"): [
        (HGA, '                    actions.append({"mouse": {"triple_click": point}})\n',
         '                    actions.append({"mouse": {"double_click": point}})\n', 1),
    ],
    ("M18-first-tool-call-only", "H-GA"): [
        (HGA, '        for tool_call_match in re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL):\n',
         '        for tool_call_match in list(re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL))[:1]:\n',
         1),
    ],
    ("M19-last-tool-call-only", "H-GA"): [
        (HGA, '        for tool_call_match in re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL):\n',
         '        for tool_call_match in list(re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL))[-1:]:\n',
         1),
    ],
    ("M20-terminate-failure-to-done", "H-GA"): [
        (HGA, '                    terminate_status = str(params.get("status", "success")).strip().lower()\n',
         '                    terminate_status = "success"\n', 1),
    ],
    ("M22-keypad-to-main", "H-GA"): [
        (KEYNAMES, '"kp_enter": "KP_Enter",\n    "kp_add": "KP_Add",', '"kp_enter": "Return",\n    "kp_add": "plus",', 1),
    ],
    ("M24-grid-1000-instead-of-999", "H-GA"): [
        (HGA, "GRID_MAX = 999.0\n", "GRID_MAX = 1000.0\n", 1),
    ],
}  # fmt: skip


class MutantError(ValueError):
    """A patch whose anchor does not match the frozen source exactly."""


def scored_pairs(operators: dict[str, Any]) -> list[tuple[str, str]]:
    """Every (operator, layer) pair ``mutation_operators.yaml`` scores."""
    pairs = []
    for op in operators["operators"]:
        for layer, spec in op["applies"].items():
            if spec["status"] == "scored":
                pairs.append((op["id"], layer))
    return pairs


def build(operator: str, layer: str, root: Path = ROOT) -> dict[str, str]:
    """The patched sources of one mutant, keyed by repository path."""
    patches = PATCHES.get((operator, layer))
    if patches is None:
        raise MutantError(f"no patch for {operator} on {layer}")
    sources: dict[str, str] = {}
    for path, old, new, count in patches:
        text = sources.get(path)
        if text is None:
            text = (root / path).read_text(encoding="utf-8")
        found = text.count(old)
        if found != count:
            raise MutantError(
                f"{operator}/{layer}: anchor in {path} found {found} times, not {count}"
            )
        sources[path] = text.replace(old, new)
    for path, text in sources.items():
        compile(text, path, "exec")
    return sources


def load_layer(layer: str, sources: dict[str, str]) -> Callable[[str], list[dict[str, Any]]] | str:
    """A mutant's response parser (harness layers) or executor source (L0-fixed).

    Patched modules replace their originals in ``sys.modules`` (and the
    adapter's ``controls`` reference) for the rest of the process, so a mutant
    run uses one fresh runner process per mutant; ``tests`` restore them.
    """
    if layer == "L0-fixed":
        return sources.get(L0) or (ROOT / L0).read_text(encoding="utf-8")
    patched = dict(sources)
    if KEYNAMES in patched and CONTROLS not in patched:
        # controls binds keynames' functions at import; re-execute it against the mutant.
        patched[CONTROLS] = (ROOT / CONTROLS).read_text(encoding="utf-8")
    for path in (KEYNAMES, CONTROLS, HGA, HOSW):
        if path not in patched:
            continue
        module = types.ModuleType(MODULE_NAMES[path])
        module.__file__ = str(ROOT / path)
        sys.modules[MODULE_NAMES[path]] = module
        exec(compile(patched[path], str(ROOT / path), "exec"), module.__dict__)  # noqa: S102
    from harness.q2.action_path import adapters

    if CONTROLS in patched:
        adapters.controls = sys.modules[MODULE_NAMES[CONTROLS]]
    return adapters.LAYERS[layer]
