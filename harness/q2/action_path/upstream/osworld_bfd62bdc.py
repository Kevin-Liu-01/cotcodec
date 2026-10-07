# Copyright the OSWorld authors (xlang-ai/OSWorld). Licensed under the Apache
# License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law
# or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

#
# Vendored by cotcodec (harness/q2/action_path/upstream/vendor.py).
# CHANGED: this file is an extract. The line ranges below were copied byte for
# byte from the upstream files; the enclosing class is replaced by a minimal
# stand-in and the imports are reduced to those the extract uses. Nothing in
# the copied ranges was modified.
#   https://github.com/xlang-ai/OSWorld @ bfd62bdc5a33 mm_agents/qwen35vl_agent.py lines 104-106
#   https://github.com/xlang-ai/OSWorld @ bfd62bdc5a33 mm_agents/qwen35vl_agent.py lines 373-563

import json
import re
from typing import Dict, List, Optional, Tuple


class Qwen35VLAgent:
    """Stand-in for the upstream class: only what parse_response uses."""

    def __init__(self, coordinate_type: str = "relative"):
        self.coordinate_type = coordinate_type

    @staticmethod
    def _py_string(text: str) -> str:
        return json.dumps("" if text is None else str(text), ensure_ascii=False)

    def parse_response(
        self,
        response: str,
        original_width: int = None,
        original_height: int = None,
        processed_width: int = None,
        processed_height: int = None,
    ) -> Tuple[str, List[str]]:
        low_level_instruction = ""
        pyautogui_code: List[str] = []

        if not response or not response.strip():
            return low_level_instruction, pyautogui_code

        def adjust_coordinates(x: float, y: float) -> Tuple[int, int]:
            if not (original_width and original_height):
                return int(x), int(y)
            if self.coordinate_type == "absolute":
                if processed_width and processed_height:
                    x_scale = original_width / processed_width
                    y_scale = original_height / processed_height
                    return int(x * x_scale), int(y * y_scale)
                return int(x), int(y)
            x_scale = original_width / 999
            y_scale = original_height / 999
            return int(x * x_scale), int(y * y_scale)

        def parse_xml_tool_call(xml_content: str) -> Optional[Dict]:
            params: Dict = {}
            func_match = re.search(r"<function=([^>]+)>", xml_content)
            if not func_match or func_match.group(1) != "computer_use":
                return None

            for match in re.finditer(r"<parameter=([^>]+)>\s*(.*?)\s*</parameter>", xml_content, re.DOTALL):
                name = match.group(1)
                value = match.group(2).strip()
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

            def press_modifier_keys() -> None:
                if text:
                    for key in str(text).split("+"):
                        key = key.strip().lower()
                        if key:
                            pyautogui_code.append(f"pyautogui.keyDown({self._py_string(key)})")

            def release_modifier_keys() -> None:
                if text:
                    keys = [key.strip().lower() for key in str(text).split("+") if key.strip()]
                    for key in reversed(keys):
                        pyautogui_code.append(f"pyautogui.keyUp({self._py_string(key)})")

            if action == "left_click":
                press_modifier_keys()
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    pyautogui_code.append(f"pyautogui.click({x}, {y})")
                else:
                    pyautogui_code.append("pyautogui.click()")
                release_modifier_keys()
            elif action == "right_click":
                press_modifier_keys()
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    pyautogui_code.append(f"pyautogui.rightClick({x}, {y})")
                else:
                    pyautogui_code.append("pyautogui.rightClick()")
                release_modifier_keys()
            elif action == "middle_click":
                press_modifier_keys()
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    pyautogui_code.append(f"pyautogui.middleClick({x}, {y})")
                else:
                    pyautogui_code.append("pyautogui.middleClick()")
                release_modifier_keys()
            elif action == "double_click":
                press_modifier_keys()
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    pyautogui_code.append(f"pyautogui.doubleClick({x}, {y})")
                else:
                    pyautogui_code.append("pyautogui.doubleClick()")
                release_modifier_keys()
            elif action == "triple_click":
                press_modifier_keys()
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    pyautogui_code.append(f"pyautogui.doubleClick({x}, {y})")
                else:
                    pyautogui_code.append("pyautogui.doubleClick()")
                release_modifier_keys()
            elif action == "type":
                text = params.get("text", "")
                pyautogui_code.append(f"pyautogui.typewrite({self._py_string(text)})")
            elif action == "key":
                keys = parse_keys(params.get("keys", []))
                keys_str = ", ".join(self._py_string(key) for key in keys)
                if len(keys) > 1:
                    pyautogui_code.append(f"pyautogui.hotkey({keys_str})")
                else:
                    pyautogui_code.append(f"pyautogui.press({keys_str})")
            elif action in {"scroll", "hscroll"}:
                press_modifier_keys()
                pixels = params.get("pixels", 0)
                try:
                    pixels = int(float(pixels))
                except Exception:
                    pixels = 0
                pyautogui_code.append(f"pyautogui.scroll({pixels})")
                release_modifier_keys()
            elif action == "wait":
                pyautogui_code.append("WAIT")
            elif action in {"terminate", "answer"}:
                pyautogui_code.append("DONE")
            elif action == "mouse_move":
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    pyautogui_code.append(f"pyautogui.moveTo({x}, {y})")
                else:
                    pyautogui_code.append("pyautogui.moveTo(0, 0)")
            elif action == "left_click_drag":
                if coordinate:
                    x, y = adjust_coordinates(*coordinate)
                    duration = 0.5
                    if "duration" in params:
                        try:
                            duration = float(params["duration"])
                        except Exception:
                            duration = 0.5
                    pyautogui_code.append(f"pyautogui.dragTo({x}, {y}, duration={duration})")
                else:
                    pyautogui_code.append("pyautogui.dragTo(0, 0)")

        for line in response.split("\n"):
            stripped = line.strip()
            if stripped.lower().startswith("action:"):
                low_level_instruction = stripped.split("Action:", 1)[-1].strip()
                break

        for tool_call_match in re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL):
            params = parse_xml_tool_call(tool_call_match.group(1))
            if params:
                process_tool_call_params(params)

        if not low_level_instruction and pyautogui_code:
            first_code = pyautogui_code[0]
            if first_code == "DONE":
                low_level_instruction = "Task completed"
            elif first_code == "WAIT":
                low_level_instruction = "Waiting"
            elif "." in first_code:
                low_level_instruction = f"Performing {first_code.split('.', 1)[1].split('(', 1)[0]} action"
            else:
                low_level_instruction = "Performing action"

        return low_level_instruction, pyautogui_code
