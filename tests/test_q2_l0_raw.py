"""Q2 L0-raw control: the frozen translator and its predicted failing set (control C2)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from harness.q2.action_path import catalog as cat
from harness.q2.action_path import l0_raw
from harness.q2.action_path.ir import parse_action, parse_sequence

HERE = Path(cat.__file__).resolve().parent


@pytest.fixture(scope="module")
def prediction():
    return yaml.safe_load((HERE / "l0_raw_prediction.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def entries():
    return {e["id"]: parse_sequence(e["actions"]) for e in cat.load()["entries"]}


def test_every_catalog_entry_translates_to_one_command_per_action(entries):
    for entry_id, actions in entries.items():
        commands = l0_raw.translate_entry(actions)
        assert len(commands) == len(actions), entry_id
        for command in commands:
            compile(command, entry_id, "exec")  # valid Python for `python -c`


def test_pyautogui_buttons_are_named_never_integers_for_1_to_3(entries):
    """Review finding: PyAutoGUI 0.9.54 _normalizeButton calls button.lower() first,

    so an integer button raises AttributeError; passing 1-3 as integers would
    make every click, drag and hold fail for a reason unrelated to the runtime.
    """
    assert l0_raw.BUTTON_NAMES == {1: "left", 2: "middle", 3: "right", 8: 8, 9: 9}
    click = parse_action({"op": "click", "x": 10, "y": 20, "button": 2, "count": 2})
    assert l0_raw.translate(click) == 'pyautogui.click(10, 20, clicks=2, button="middle")'
    hold = parse_action({"op": "button_down", "x": 1, "y": 2, "button": 3})
    assert l0_raw.translate(hold) == 'pyautogui.mouseDown(1, 2, button="right")'
    back = parse_action({"op": "click", "x": 1, "y": 2, "button": 8})
    assert l0_raw.translate(back) == "pyautogui.click(1, 2, clicks=1, button=8)"
    integer_button = re.compile(r"button=\d")
    for entry_id, actions in entries.items():
        uses_8_or_9 = any(a.button in (8, 9) for a in actions)
        for command in l0_raw.translate_entry(actions):
            assert bool(integer_button.search(command)) == uses_8_or_9, (entry_id, command)


def test_prediction_file_mirrors_the_translator(prediction):
    assert prediction["translation"]["module"] == "harness/q2/action_path/l0_raw.py"
    assert prediction["key_names"] == l0_raw.KEY_NAMES
    assert prediction["button_names"] == l0_raw.BUTTON_NAMES


def test_predicted_failing_set_follows_the_stated_mechanisms(prediction, entries):
    """Only non-ASCII text, KP_Enter and buttons 8/9 are predicted to fail."""

    # PyAutoGUI 0.9.54 knows every mapped name except 'kp_enter', and single characters.
    known = set(l0_raw.KEY_NAMES.values()) - {"kp_enter"}

    def predicted(actions):
        for action in actions:
            if action.op == "type" and any(
                not (0x20 <= ord(ch) < 0x7F or ch in "\n\t") for ch in action.text or ""
            ):
                return True
            names = [l0_raw.key_name(k) for k in action.keys or ()]
            if any(len(name) > 1 and name not in known for name in names):
                return True
            if action.button in (8, 9):
                return True
        return False

    computed = {entry_id for entry_id, actions in entries.items() if predicted(actions)}
    assert computed == set(prediction["predicted_fail"])
    pointer_1_3 = {
        e for e, actions in entries.items()
        if any(a.button in (1, 2, 3) for a in actions if a.op != "scroll")
    }  # fmt: skip
    assert pointer_1_3 and not pointer_1_3 & set(prediction["predicted_fail"])
    assert "AttributeError" in prediction["reasons"]["click_button_back"]


def test_translation_details(entries):
    drag = parse_action({"op": "drag", "path": [[5, 5], [9, 9], [20, 9]], "duration_ms": 900})
    assert l0_raw.translate(drag) == (
        "pyautogui.moveTo(5, 5); "
        'pyautogui.mouseDown(button="left"); '
        "pyautogui.moveTo(9, 9, duration=0.45); "
        "pyautogui.moveTo(20, 9, duration=0.45); "
        'pyautogui.mouseUp(button="left")'
    )
    current = parse_action({"op": "drag", "path": [[7, 8]], "from_current": True})
    assert l0_raw.translate(current).startswith('pyautogui.mouseDown(button="left")')
    scroll = parse_action(
        {"op": "scroll", "x": 3, "y": 4, "wheel_y": 3, "modifiers": ["Control_L"]}
    )
    assert l0_raw.translate(scroll) == (
        'pyautogui.keyDown("ctrl"); pyautogui.scroll(-3, 3, 4); pyautogui.keyUp("ctrl")'
    )
    chord = parse_action({"op": "key", "keys": ["Super_L", "d"]})
    assert l0_raw.translate(chord) == 'pyautogui.hotkey("winleft", "d")'
    text = parse_action({"op": "type", "text": 'é "x"'})
    assert l0_raw.translate(text) == 'pyautogui.typewrite("é \\"x\\"")'
    assert l0_raw.translate(parse_action({"op": "wait", "ms": 600})) == "time.sleep(0.6)"
    with pytest.raises(l0_raw.L0RawError):
        l0_raw.translate(parse_action({"op": "terminate", "status": "success"}))
