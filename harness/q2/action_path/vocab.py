"""Stage-1 harness vocabularies and the gating set G (reviewed plan, defect B13).

The suite gates Stage 1 only on entries that a Stage-1 harness can express;
everything else runs and is reported but does not gate. Each harness's
vocabulary is read from its own system-prompt tool description, the reviewed
plan's spec rule:

* H-OSW: OSWorld branch ``dev_djlu/qwen35vl_agent`` at bfd62bdc,
  ``mm_agents/qwen35vl_agent.py`` (Apache-2.0). The ``computer_use`` action
  enum is key, type, mouse_move, left_click, left_click_drag, right_click,
  middle_click, double_click, triple_click, scroll, hscroll, wait, terminate,
  answer. ``text`` may name modifiers held during click and scroll actions.
  ``left_click_drag`` drags from the current cursor to ``coordinate``. The
  prompt itself declares two deviations: triple_click is "simulated as
  double-click" and hscroll is "mapped to regular scroll".
* H-GA: gym-anything at aae6f7607 (MIT), ``agents/agents/qwen35vl.py``. The
  enum is key, type, mouse_move, left_click, left_click_drag, right_click,
  middle_click, double_click, triple_click, scroll, wait, terminate, answer.
  ``left_click_drag`` goes from ``coordinate`` to ``coordinate2``; scroll is
  vertical with a magnitude of 1 to 10 per call. The prompt documents no
  modifier parameter for mouse actions (the parser accepts ``keys`` anyway,
  which is a design difference, not vocabulary).

Rule: where a prompt is silent, the paper's Table 21 semantics apply; where a
prompt declares a deviation, the deviation is a logged design difference of
that harness, and the action is not counted as expressible by it. An entry is
in G when every one of its actions is expressible by at least one Stage-1
harness (the union of the vocabularies).
"""

from __future__ import annotations

from harness.q2.action_path.ir import Action

HARNESSES = {
    "H-OSW": {
        "source": "https://github.com/xlang-ai/OSWorld/blob/"
        "bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06/mm_agents/qwen35vl_agent.py",
        "license": "Apache-2.0",
        "declared_deviations": [
            "triple_click simulated as double_click",
            "hscroll mapped to scroll",
        ],
    },
    "H-GA": {
        "source": "https://github.com/cmu-l3/gym-anything/blob/"
        "aae6f7607e0f3d9d6306e1fefbad92bda99ca99a/agents/agents/qwen35vl.py",
        "license": "MIT",
        "declared_deviations": ["scroll magnitude 1..10 per call"],
    },
}


def expressible(harness: str, action: Action) -> tuple[bool, str]:
    """Whether one IR action is in a harness's documented vocabulary, with the reason."""
    op = action.op
    if op in ("type", "key", "wait", "screenshot", "terminate", "move"):
        return True, f"{op} is in the action enum"
    if op in ("button_down", "button_up"):
        return False, "no action holds or releases a mouse button"
    if op in ("key_down", "key_up"):
        return False, "no action holds a key across actions"
    if op == "click":
        if action.button not in (1, 2, 3):
            return False, f"no click action for button {action.button}"
        if action.count == 3 and harness == "H-OSW":
            return False, "prompt declares triple_click simulated as double_click"
        if action.count in (2, 3) and action.button != 1:
            return False, "double and triple click are left-button only"
        if action.modifiers and harness == "H-GA":
            return False, "prompt documents no modifier parameter for clicks"
        return True, "click action with documented parameters"
    if op == "drag":
        if action.button != 1:
            return False, "only left_click_drag exists"
        if action.modifiers:
            return False, "no documented modifier parameter for drags"
        points = len(action.path or ())
        if harness == "H-OSW":
            ok = points == 2 or (action.from_current and points == 1)
            return ok, "drag from current cursor (after mouse_move)" if ok else "multi-point drag"
        if action.from_current:
            return False, "left_click_drag needs coordinate and coordinate2"
        return points == 2, "two-point drag" if points == 2 else "multi-point drag"
    if op == "scroll":
        if action.wheel_x:
            return False, (
                "prompt maps hscroll to vertical scroll"
                if harness == "H-OSW"
                else "no horizontal scroll action"
            )
        if action.modifiers and harness == "H-GA":
            return False, "prompt documents no modifier parameter for scroll"
        return True, "vertical scroll (after mouse_move to the position)"
    return False, f"unknown op {op}"


def entry_gating(actions: list[Action]) -> tuple[bool, list[str]]:
    """An entry gates when each action is expressible by at least one harness."""
    reasons: list[str] = []
    gating = True
    for index, action in enumerate(actions):
        verdicts = {name: expressible(name, action) for name in HARNESSES}
        if not any(ok for ok, _ in verdicts.values()):
            gating = False
            reasons.append(
                f"action {index} ({action.op}): "
                + "; ".join(f"{name}: {why}" for name, (_, why) in verdicts.items())
            )
    return gating, reasons
