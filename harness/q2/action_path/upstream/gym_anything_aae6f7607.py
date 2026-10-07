# MIT License
#
# Copyright (c) 2026 cmu-l3
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

#
# Vendored by cotcodec (harness/q2/action_path/upstream/vendor.py).
# CHANGED: this file is an extract. The line ranges below were copied byte for
# byte from the upstream files; the enclosing class is replaced by a minimal
# stand-in and the imports are reduced to those the extract uses. Nothing in
# the copied ranges was modified.
#   https://github.com/cmu-l3/gym-anything @ aae6f7607e0f agents/agents/qwen35vl.py lines 14-23
#   https://github.com/cmu-l3/gym-anything @ aae6f7607e0f agents/agents/qwen35vl.py lines 465-731

import json
import re
from typing import Any, Dict, List, Optional, Tuple

GRID_MAX = 999.0
SCROLL_STEP_LIMIT = 10
COLLAPSED_SCREENSHOT_TEXT = "This screenshot has been collapsed."

# Mouse-family actions where a `keys` parameter means "hold these modifiers
# while performing the action" rather than a chord of its own.
_MOUSE_ACTIONS = {
    "left_click", "click", "right_click", "middle_click", "double_click",
    "triple_click", "left_click_drag", "drag", "scroll", "mouse_move",
}


class Qwen35VLAgent:
    """Stand-in for the upstream class: only its response parsing."""

    # ---- Response parsing (reference-consistent) -------------------------------

    @staticmethod
    def _parse_json_tool_call(text: str) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(text.strip())
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict) and parsed.get("name") == "computer_use":
            args = parsed.get("arguments", {})
            return args if isinstance(args, dict) else None
        if isinstance(parsed, dict) and parsed.get("action"):
            return parsed
        return None

    @classmethod
    def _parse_xml_tool_call(cls, xml_content: str) -> Optional[Dict[str, Any]]:
        json_call = cls._parse_json_tool_call(xml_content)
        if json_call is not None:
            return json_call

        func_match = re.search(r"<function=([^>]+)>", xml_content)
        if not func_match or func_match.group(1) != "computer_use":
            return None

        params: Dict[str, Any] = {}
        for match in re.finditer(
            r"<parameter=([^>]+)>(.*?)</parameter>", xml_content, re.DOTALL
        ):
            name = match.group(1)
            value = match.group(2)
            if name == "text":
                # Trim exactly one wrapping newline; inner whitespace is content.
                if value.startswith("\r\n"):
                    value = value[2:]
                elif value.startswith("\n"):
                    value = value[1:]
                if value.endswith("\r\n"):
                    value = value[:-2]
                elif value.endswith("\n"):
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

    @staticmethod
    def _parse_keys(raw_keys: Any) -> List[str]:
        if isinstance(raw_keys, str):
            try:
                raw_keys = json.loads(raw_keys)
            except Exception:
                raw_keys = [raw_keys]
        if isinstance(raw_keys, list):
            return [str(key).strip() for key in raw_keys if str(key).strip()]
        if raw_keys is None:
            return []
        return [str(raw_keys).strip()]

    @staticmethod
    def _parse_coordinate(raw_coord: Any) -> Optional[Tuple[float, float]]:
        if isinstance(raw_coord, str):
            try:
                raw_coord = json.loads(raw_coord)
            except Exception:
                return None
        if isinstance(raw_coord, list) and len(raw_coord) >= 2:
            try:
                return float(raw_coord[0]), float(raw_coord[1])
            except Exception:
                return None
        return None

    @staticmethod
    def _scale_coordinate(
        coord: Tuple[float, float], original_width: int, original_height: int
    ) -> List[int]:
        x, y = coord
        return [int(x * original_width / GRID_MAX), int(y * original_height / GRID_MAX)]

    def _parse_response(
        self, response: str, original_width: int, original_height: int
    ) -> Dict[str, Any]:
        thought = ""
        if not response or not response.strip():
            return {
                "actions": [],
                "metadata": {
                    "thought": thought,
                    "conclusion": "cannot parse; waiting",
                    "action_type": "wait",
                    "is_terminal": False,
                    "wait_time": 1.0,
                    "parse_error": True,
                },
            }
        if "</think>" in response:
            thought = response.split("</think>", 1)[0]
            response = response.split("</think>", 1)[1]

        low_level_instruction = ""
        for line in response.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("action:"):
                low_level_instruction = stripped.split(":", 1)[-1].strip()
                break

        actions: List[Dict[str, Any]] = []
        is_terminal = False
        wait_time: Optional[float] = None
        action_types: List[str] = []
        terminate_status: Optional[str] = None
        answer_text: Optional[str] = None

        def scaled(params: Dict[str, Any], key: str = "coordinate") -> Optional[List[int]]:
            coord = self._parse_coordinate(params.get(key))
            if coord is None:
                return None
            return self._scale_coordinate(coord, original_width, original_height)

        def process_params(params: Dict[str, Any]) -> None:
            nonlocal is_terminal, wait_time, terminate_status, answer_text
            action = str(params.get("action", "")).strip()
            if not action:
                return
            action_types.append(action)

            # Qwen emits `keys` on mouse actions to mean "hold these while
            # performing the action" (shift+click to extend a selection,
            # ctrl+scroll to zoom). Emit an explicit hold around the mouse
            # action; the plain `key` action keeps `keys` as the chord itself.
            mouse_hold = (
                self._parse_keys(params.get("keys", []))
                if action in _MOUSE_ACTIONS
                else []
            )
            if mouse_hold:
                actions.append({"keyboard": {"keys_down": mouse_hold}})
            hold_marker = len(actions)

            if action == "key":
                keys = self._parse_keys(params.get("keys", []))
                if keys:
                    actions.append({"keyboard": {"keys": keys}})
            elif action == "type":
                actions.append({"keyboard": {"text": str(params.get("text", ""))}})
            elif action == "mouse_move":
                point = scaled(params)
                if point:
                    actions.append({"mouse": {"move": point}})
            elif action in {"left_click", "click"}:
                point = scaled(params)
                if point:
                    actions.append({"mouse": {"left_click": point}})
                else:
                    actions.append({"mouse": {"buttons": {"left_down": True, "left_up": True}}})
            elif action == "right_click":
                point = scaled(params)
                if point:
                    actions.append({"mouse": {"right_click": point}})
                else:
                    actions.append({"mouse": {"buttons": {"right_down": True, "right_up": True}}})
            elif action == "middle_click":
                point = scaled(params)
                if point:
                    actions.append({"mouse": {"middle_click": point}})
            elif action == "double_click":
                point = scaled(params)
                if point:
                    actions.append({"mouse": {"double_click": point}})
            elif action == "triple_click":
                point = scaled(params)
                if point:
                    actions.append({"mouse": {"triple_click": point}})
            elif action in {"left_click_drag", "drag"}:
                start = scaled(params)
                end = scaled(params, "coordinate2")
                if start and end:
                    actions.append({"mouse": {"left_click_drag": [start, end]}})
                elif start:
                    # Reference behavior is "drag from the current cursor to
                    # this point"; the runner drag form needs two points, so
                    # degrade to a drag at the target rather than dropping it.
                    actions.append({"mouse": {"left_click_drag": [start, start]}})
            elif action == "scroll":
                try:
                    requested_steps = int(float(params.get("pixels", 0)))
                except Exception:
                    requested_steps = 0
                bounded_steps = max(
                    -SCROLL_STEP_LIMIT, min(SCROLL_STEP_LIMIT, requested_steps)
                )
                point = scaled(params)
                if point:
                    actions.append({"mouse": {"move": point}})
                if bounded_steps:
                    # Qwen uses negative=down; the runner scroll action uses
                    # positive=down.
                    actions.append({"mouse": {"scroll": -bounded_steps}})
            elif action == "wait":
                try:
                    wait_time = float(params.get("time", 1.0))
                except Exception:
                    wait_time = 1.0
            elif action in {"terminate", "answer"}:
                if action == "terminate":
                    terminate_status = str(params.get("status", "success")).strip().lower()
                else:
                    answer_text = str(params.get("text", ""))
                is_terminal = True

            if mouse_hold:
                if len(actions) == hold_marker:
                    # The action produced nothing to hold around; drop the
                    # press so a bare modifier tap never reaches the env.
                    actions.pop()
                else:
                    actions.append({"keyboard": {"keys_up": list(reversed(mouse_hold))}})

        for tool_call_match in re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL):
            params = self._parse_xml_tool_call(tool_call_match.group(1))
            if params:
                process_params(params)

        if not actions and not is_terminal:
            match = re.search(r"(\{\"name\"\s*:\s*\"computer_use\".*\})", response, re.DOTALL)
            if match:
                params = self._parse_json_tool_call(match.group(1))
                if params:
                    process_params(params)

        parse_error = False
        if not actions and not is_terminal and wait_time is None:
            parse_error = True

        if not low_level_instruction:
            if is_terminal:
                low_level_instruction = "Task completed"
            elif wait_time is not None:
                low_level_instruction = "Waiting"
            elif actions:
                low_level_instruction = "Performing action"
            else:
                low_level_instruction = "cannot parse; waiting"
                wait_time = 1.0

        metadata: Dict[str, Any] = {
            "thought": thought,
            "conclusion": low_level_instruction,
            "action_type": action_types[0] if action_types else "wait",
            "is_terminal": is_terminal,
            "wait_time": wait_time,
        }
        if parse_error:
            metadata["parse_error"] = True
        if terminate_status is not None:
            metadata["status"] = terminate_status
        if answer_text is not None:
            metadata["answer"] = answer_text

        return {"actions": actions, "metadata": metadata}
