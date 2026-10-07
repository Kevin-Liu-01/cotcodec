# Copyright the OSWorld authors (xlang-ai/OSWorld). Licensed under the Apache
# License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law
# or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#
# H-OSW-fixed (q2-action-path-v1, Stage-1 harness). MODIFIED by cotcodec, as
# Apache-2.0 section 4(b) requires: this file is derived from
#   https://github.com/xlang-ai/OSWorld @ bfd62bdc5a33 mm_agents/qwen35vl_agent.py
#   lines 373-563 (Qwen35VLAgent.parse_response), vendored unchanged in
#   osworld_bfd62bdc.py.
# Every change is marked "CHANGED (cotcodec)". They are:
#   1. Emit boundary: the parser emits canonical IR action dicts
#      (harness/q2/action_path/ir.py) instead of PyAutoGUI code strings, call
#      for call, with the IR-boundary clamp on every coordinate.
#   2. Own-spec fix: terminate(status=failure) becomes terminate(failure)
#      (upstream emitted DONE for every terminate).
#   3. Own-spec fix: key names go through an explicit map (KEY_MAP) and an
#      unknown name raises (upstream passed names to PyAutoGUI, which drops
#      the names it does not know).
#   4. Own-spec fix: text reaches the IR type action exactly: the `text`
#      parameter keeps its inner and edge whitespace (exactly one wrapping
#      newline, which the chat template adds, is trimmed); upstream stripped
#      all edge whitespace from every parameter.
# Declared design differences of its own prompt stay as they are: triple_click
# is a double click and hscroll is a vertical scroll. `keys` on clicks and a
# coordinate on scroll are not in its prompt and are not added.

import json
import re
from typing import Dict, List, Optional, Tuple

from harness.q2.action_path.ir import MODIFIERS, IRError, canonical_keysym, clamp_point
from harness.q2.action_path.keynames import PYAUTOGUI_NAMED, char_keysym

# CHANGED (cotcodec): the explicit key map of fix 3. PyAutoGUI 0.9.54's names
# (the upstream runtime's vocabulary), plus the names that runtime drops but a
# model uses for keys the prompt's `key` action covers.
KEY_MAP: Dict[str, str] = {name.lower() if len(name) > 1 else name: keysym
                           for name, keysym in PYAUTOGUI_NAMED.items()}
KEY_MAP.update({
    "super": "Super_L", "meta": "Super_L", "cmd": "Super_L", "command": "Super_L",
    "control": "Control_L", "option": "Alt_L", "kp_enter": "KP_Enter", "kp_add": "KP_Add",
    "kp_subtract": "KP_Subtract", "kp_multiply": "KP_Multiply", "kp_divide": "KP_Divide",
    "menu": "Menu", "caps_lock": "Caps_Lock", "num_lock": "Num_Lock", "page_up": "Prior",
    "page_down": "Next", "pgup": "Prior", "pgdn": "Next", "ins": "Insert",
})


def map_key(name: str) -> str:
    """CHANGED (cotcodec): explicit key-name map; unknown names raise."""
    key = name.lower() if len(name) > 1 else name
    if key in KEY_MAP:
        return canonical_keysym(KEY_MAP[key])
    if len(name) == 1:
        return char_keysym(name)
    raise IRError(f"H-OSW-fixed has no key named {name!r}")


class Qwen35VLAgent:
    """Stand-in for the upstream class: only what parse_response uses."""

    def __init__(self, coordinate_type: str = "relative"):
        self.coordinate_type = coordinate_type

    def parse_response(
        self,
        response: str,
        original_width: int = None,
        original_height: int = None,
        processed_width: int = None,
        processed_height: int = None,
    ) -> Tuple[str, List[dict]]:
        low_level_instruction = ""
        ir_actions: List[dict] = []  # CHANGED (cotcodec): IR dicts, not pyautogui strings

        if not response or not response.strip():
            return low_level_instruction, ir_actions

        def adjust_coordinates(x: float, y: float) -> Tuple[int, int]:
            if not (original_width and original_height):
                return clamp_point(x, y)  # CHANGED (cotcodec): IR-boundary clamp
            if self.coordinate_type == "absolute":
                if processed_width and processed_height:
                    x_scale = original_width / processed_width
                    y_scale = original_height / processed_height
                    return clamp_point(x * x_scale, y * y_scale)  # CHANGED (cotcodec)
                return clamp_point(x, y)  # CHANGED (cotcodec)
            x_scale = original_width / 999
            y_scale = original_height / 999
            return clamp_point(x * x_scale, y * y_scale)  # CHANGED (cotcodec)

        def parse_xml_tool_call(xml_content: str) -> Optional[Dict]:
            params: Dict = {}
            func_match = re.search(r"<function=([^>]+)>", xml_content)
            if not func_match or func_match.group(1) != "computer_use":
                return None

            # CHANGED (cotcodec), fix 4: capture the raw value; `text` keeps its whitespace.
            for match in re.finditer(r"<parameter=([^>]+)>(.*?)</parameter>", xml_content, re.DOTALL):
                name = match.group(1)
                value = match.group(2)
                if name == "text":
                    if value.startswith("\n"):
                        value = value[1:]
                    if value.endswith("\n"):
                        value = value[:-1]
                else:
                    value = value.strip()
                if value.startswith("[") or value.startswith("{"):
                    try:
                        params[name] = json.loads(value)
                        continue
                    except json.JSONDecodeError:
                        pass
                params[name] = value
            return params

        def parse_keys(raw_keys):
            if isinstance(raw_keys, str):
                try:
                    raw_keys = json.loads(raw_keys)
                except Exception:
                    raw_keys = [raw_keys]
            if isinstance(raw_keys, list):
                return [str(key).strip() for key in raw_keys]
            return [str(raw_keys).strip()]

        def parse_coordinate(raw_coord):
            if isinstance(raw_coord, str):
                try:
                    raw_coord = json.loads(raw_coord)
                except Exception:
                    return None
            if isinstance(raw_coord, list) and len(raw_coord) >= 2:
                return raw_coord[0], raw_coord[1]
            return None

        def process_tool_call_params(params: Dict) -> None:
            action = params.get("action")
            if not action:
                return

            coordinate = parse_coordinate(params.get("coordinate"))
            text = params.get("text")

            # CHANGED (cotcodec): modifiers in `text` become the IR action's held
            # modifiers (pressed in order before it, released in reverse after
            # it), the same events upstream's keyDown/keyUp pair produced.
            def modifiers() -> List[str]:
                if not text:
                    return []
                keys = [map_key(key.strip().lower()) for key in str(text).split("+") if key.strip()]
                if not set(keys) <= MODIFIERS:
                    raise IRError(f"click/scroll text {text!r} names a non-modifier key")
                return keys

            def point() -> dict:
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    return {"x": x, "y": y}
                return {}

            def click(button: int, count: int) -> None:
                ir = {"op": "click", "button": button, "count": count, **point()}
                if modifiers():
                    ir["modifiers"] = modifiers()
                ir_actions.append(ir)

            if action == "left_click":
                click(1, 1)
            elif action == "right_click":
                click(3, 1)
            elif action == "middle_click":
                click(2, 1)
            elif action == "double_click":
                click(1, 2)
            elif action == "triple_click":
                click(1, 2)  # declared design difference: simulated as double-click
            elif action == "type":
                text = params.get("text", "")
                if text:
                    ir_actions.append({"op": "type", "text": str(text)})
            elif action == "key":
                keys = parse_keys(params.get("keys", []))
                ir_actions.append({"op": "key", "keys": [map_key(key) for key in keys]})
            elif action in {"scroll", "hscroll"}:
                pixels = params.get("pixels", 0)
                try:
                    pixels = int(float(pixels))
                except Exception:
                    pixels = 0
                if pixels:
                    # pyautogui.scroll(n): positive scrolls up; IR wheel_y > 0 is down.
                    ir = {"op": "scroll", "wheel_y": -pixels}
                    if modifiers():
                        ir["modifiers"] = modifiers()
                    ir_actions.append(ir)
            elif action == "wait":
                ir_actions.append({"op": "wait", "ms": 0})  # DesktopEnv.step("WAIT", pause=0.0)
            elif action in {"terminate", "answer"}:
                # CHANGED (cotcodec), fix 2: terminate(status=failure) is a failure.
                status = str(params.get("status", "success")).strip().lower()
                failed = action == "terminate" and status == "failure"
                ir_actions.append({"op": "terminate", "status": "failure" if failed else "success"})
            elif action == "mouse_move":
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    ir_actions.append({"op": "move", "x": x, "y": y})
                else:
                    ir_actions.append({"op": "move", "x": 0, "y": 0})
            elif action == "left_click_drag":
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    duration = 0.5
                    if "duration" in params:
                        try:
                            duration = float(params["duration"])
                        except Exception:
                            duration = 0.5
                else:
                    x, y, duration = 0, 0, 0.0
                ir_actions.append({"op": "drag", "path": [[x, y]], "from_current": True,
                                   "duration_ms": int(round(duration * 1000))})

        for line in response.split("\n"):
            stripped = line.strip()
            if stripped.lower().startswith("action:"):
                low_level_instruction = stripped.split("Action:", 1)[-1].strip()
                break

        for tool_call_match in re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL):
            params = parse_xml_tool_call(tool_call_match.group(1))
            if params:
                process_tool_call_params(params)

        if not low_level_instruction and ir_actions:
            low_level_instruction = f"Performing {ir_actions[0]['op']} action"

        return low_level_instruction, ir_actions
