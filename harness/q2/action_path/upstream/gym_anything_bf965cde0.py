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
#   https://github.com/cmu-l3/gym-anything @ bf965cde02f4 agents/shared/qwen_computer_use.py lines 25-218
#   https://github.com/cmu-l3/gym-anything @ bf965cde02f4 agents/agents/qwen35vl.py lines 28-39
#   https://github.com/cmu-l3/gym-anything @ bf965cde02f4 agents/agents/qwen35vl.py lines 246-398
#   https://github.com/cmu-l3/gym-anything @ bf965cde02f4 agents/agents/qwen35vl.py lines 401-414

import json
import re
from typing import Any, Dict, List, Optional, Tuple


def convert_point_format_qwen3vl(x, y, scale_dims=True, scale_dims_ratio=(1920 / 1000, 1080 / 1000)):
    if scale_dims:
        x = x * scale_dims_ratio[0]
        y = y * scale_dims_ratio[1]
    return int(x), int(y)


def parse_qwen3vl_response(response, scale_dims=True, scale_dims_ratio=(1920 / 1000, 1080 / 1000)):
    if not response or not isinstance(response, str):
        return {
            "actions": [{"action": "screenshot"}],
            "metadata": {
                "thought": "Empty or invalid response",
                "conclusion": "Retrying with screenshot",
                "action_type": "screenshot",
                "is_terminal": False,
                "wait_time": None,
                "parse_error": True,
            },
        }

    thought = response.split("</think>")[0]
    conclusion = None
    if "</think>" in response:
        response = response.split("</think>")[1]

    printable_ratio = sum(1 for c in response if c.isprintable() or c.isspace()) / max(len(response), 1)
    if printable_ratio < 0.5:
        print(f"[parse_qwen3vl_response] Warning: Response appears garbled (printable ratio: {printable_ratio:.2f})")
        return {
            "actions": [{"action": "screenshot"}],
            "metadata": {
                "thought": "Garbled response detected",
                "conclusion": "Retrying with screenshot",
                "action_type": "screenshot",
                "is_terminal": False,
                "wait_time": None,
                "parse_error": True,
            },
        }

    if "<tool_call>" in response and "</tool_call>" in response:
        action = response.split("<tool_call>")[-1].split("</tool_call>")[0]
    else:
        try:
            action = '{"name": "computer_use"' + response.split('{"name": "computer_use"')[1].split("}}")[0] + "}}"
        except Exception as exc:
            print(f"[parse_qwen3vl_response] Error parsing action, switching to wait: {exc}", response)
            action = '{"action": "wait", "time": 1.0}'
            conclusion = "cannot parse action. waiting for 1 second and trying again"

    for line in response.split("\n"):
        if "Action:" in line:
            conclusion = line.split("Action:")[-1].strip()
    if conclusion is None:
        conclusion = response.split("<tool_call>")[0].strip()

    try:
        parsed_action = json.loads(action.strip("\n"))
        if "arguments" in parsed_action:
            action_json = parsed_action["arguments"]
        elif "action" in parsed_action:
            action_json = parsed_action
        else:
            raise ValueError("No 'arguments' or 'action' key in parsed JSON")
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        print(f"[parse_qwen3vl_response] Error parsing action JSON: {exc}", action)
        return {
            "actions": [{"action": "screenshot"}],
            "metadata": {
                "thought": thought,
                "conclusion": f"Parse error: {exc}",
                "action_type": "screenshot",
                "is_terminal": False,
                "wait_time": None,
                "parse_error": True,
            },
        }

    if "action" not in action_json:
        print(f"[parse_qwen3vl_response] Missing 'action' key in: {action_json}")
        return {
            "actions": [{"action": "screenshot"}],
            "metadata": {
                "thought": thought,
                "conclusion": "Missing action key",
                "action_type": "screenshot",
                "is_terminal": False,
                "wait_time": None,
                "parse_error": True,
            },
        }

    metadata = {
        "thought": thought,
        "conclusion": conclusion,
        "action_type": action_json["action"],
        "is_terminal": False,
        "wait_time": None,
    }

    if action_json["action"] == "key":
        actions = [{"keyboard": {"keys": action_json["keys"]}}]
    elif action_json["action"] == "type":
        actions = []
        if action_json.get("clear"):
            actions.append({"keyboard": {"keys": ["ctrl", "a"]}})
        actions.append({"keyboard": {"text": action_json["text"]}})
        if action_json.get("enter"):
            actions.append({"keyboard": {"keys": ["Return"]}})
    elif action_json["action"] == "mouse_move":
        x, y = convert_point_format_qwen3vl(
            action_json["coordinate"][0],
            action_json["coordinate"][1],
            scale_dims,
            scale_dims_ratio,
        )
        actions = [{"mouse": {"move": [x, y]}}]
    elif action_json["action"] in {"left_click", "click"}:
        x, y = convert_point_format_qwen3vl(
            action_json["coordinate"][0],
            action_json["coordinate"][1],
            scale_dims,
            scale_dims_ratio,
        )
        actions = [{"mouse": {"left_click": [x, y]}}]
    elif action_json["action"] == "right_click":
        x, y = convert_point_format_qwen3vl(
            action_json["coordinate"][0],
            action_json["coordinate"][1],
            scale_dims,
            scale_dims_ratio,
        )
        actions = [{"mouse": {"right_click": [x, y]}}]
    elif action_json["action"] == "double_click":
        x, y = convert_point_format_qwen3vl(
            action_json["coordinate"][0],
            action_json["coordinate"][1],
            scale_dims,
            scale_dims_ratio,
        )
        actions = [{"mouse": {"double_click": [x, y]}}]
    elif action_json["action"] == "triple_click":
        x, y = convert_point_format_qwen3vl(
            action_json["coordinate"][0],
            action_json["coordinate"][1],
            scale_dims,
            scale_dims_ratio,
        )
        actions = [{"mouse": {"triple_click": [x, y]}}]
    elif action_json["action"] in {"left_click_drag", "drag"}:
        x1, y1 = convert_point_format_qwen3vl(
            action_json["coordinate"][0],
            action_json["coordinate"][1],
            scale_dims,
            scale_dims_ratio,
        )
        try:
            x2, y2 = convert_point_format_qwen3vl(
                action_json["coordinate2"][0],
                action_json["coordinate2"][1],
                scale_dims,
                scale_dims_ratio,
            )
        except Exception as exc:
            print(f"[parse_qwen3vl_response] Error parsing coordinate2: {exc}")
            print("Action json: ", action_json)
            x2, y2 = x1, y1
        actions = [{"mouse": {"left_click_drag": [[x1, y1], [x2, y2]]}}]
    elif action_json["action"] == "scroll":
        if "coordinate" in action_json:
            x, y = convert_point_format_qwen3vl(
                action_json["coordinate"][0],
                action_json["coordinate"][1],
                scale_dims,
                scale_dims_ratio,
            )
            actions = [
                {"mouse": {"move": [x, y]}},
                {"mouse": {"scroll": action_json["pixels"] if "pixels" in action_json else action_json.get("scroll", 0)}},
            ]
        else:
            actions = [{"mouse": {"scroll": action_json["pixels"] if "pixels" in action_json else action_json.get("scroll", 0)}}]
    elif action_json["action"] == "wait":
        actions = []
        metadata["wait_time"] = action_json.get("time", 1.0)
    elif action_json["action"] == "terminate":
        actions = []
        metadata["is_terminal"] = True
        metadata["status"] = action_json.get("status", "success")
    else:
        actions = []

    return {"actions": actions, "metadata": metadata}


class Qwen35VLAgent:
    """Stand-in for the upstream class: only its response parsing."""

    _TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
    _FUNCTION_RE = re.compile(r"<function=([^>]+)>")
    _PARAMETER_RE = re.compile(r"<parameter=([^>]+)>\s*(.*?)\s*</parameter>", re.DOTALL)

    _CLICK_ACTIONS = {
        "left_click",
        "right_click",
        "middle_click",
        "double_click",
        "triple_click",
    }
    _SCROLL_ACTIONS = {"scroll", "hscroll"}

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse a Qwen3.5-VL response and return the same shape as
        parse_qwen3vl_response. We extract the XML tool call into an
        ``action_json`` dict, remap Qwen3.5-only verbs (`hscroll`, `answer`)
        onto verbs the upstream parser already handles, then reuse it for
        action dispatch.
        """
        if not response or not isinstance(response, str):
            return _empty_screenshot_action("Empty or invalid response")

        action_json, conclusion = self._extract_action_json(response)
        if action_json is None:
            return _empty_screenshot_action(
                conclusion or "Failed to parse Qwen3.5-VL XML tool call",
                parse_error=True,
            )

        modifier_text = action_json.pop("__modifier_text", None)
        answer_text = action_json.pop("__answer_text", None)

        synthetic = self._format_as_qwen3vl_jsonxml(action_json, conclusion)
        parsed = parse_qwen3vl_response(synthetic)

        if modifier_text:
            # The runner action API has no held-modifier primitive, so the
            # closest we can get is press the chord immediately before the
            # click/scroll. Logged for visibility; intent is preserved even
            # though hold-during-click isn't.
            parsed = self._apply_modifier_keys(parsed, modifier_text)

        if answer_text is not None:
            parsed.setdefault("metadata", {})["answer"] = answer_text

        return parsed

    def _extract_action_json(
        self, response: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        body = response
        if "</think>" in body:
            body = body.split("</think>", 1)[1]

        conclusion: Optional[str] = None
        for line in body.split("\n"):
            stripped = line.strip()
            if stripped.lower().startswith("action:"):
                conclusion = stripped.split("Action:", 1)[-1].strip()
                break

        match = self._TOOL_CALL_RE.search(body)
        if not match:
            return None, conclusion

        inner = match.group(1)
        func_match = self._FUNCTION_RE.search(inner)
        if not func_match or func_match.group(1).strip() != "computer_use":
            return None, conclusion

        params: Dict[str, Any] = {}
        for pmatch in self._PARAMETER_RE.finditer(inner):
            name = pmatch.group(1).strip()
            params[name] = self._coerce_value(pmatch.group(2))

        if "action" not in params:
            return None, conclusion

        params = self._normalize_action_json(params)
        return params, conclusion

    @staticmethod
    def _coerce_value(raw: str) -> Any:
        text = raw.strip()
        if text.startswith("[") or text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return text

    @classmethod
    def _normalize_action_json(cls, action_json: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(action_json)
        action = result.get("action")

        # Pull modifier-text aside: parse_qwen3vl_response treats `text` as the
        # typed string for action=type, so leaving it on a click would corrupt
        # dispatch. We re-inject it as a chord-press in _apply_modifier_keys.
        if action in cls._CLICK_ACTIONS or action in cls._SCROLL_ACTIONS:
            text = result.get("text")
            if text:
                result["__modifier_text"] = text
            result.pop("text", None)

        # hscroll has no upstream verb; the OSWorld 3.5 agent also maps it to
        # plain scroll, so do the same.
        if action == "hscroll":
            result["action"] = "scroll"

        # answer is a terminate-with-payload variant. Stash the text in
        # metadata and dispatch as terminate so the loop stops cleanly.
        if action == "answer":
            result["__answer_text"] = result.get("text", "")
            result["action"] = "terminate"
            result.setdefault("status", "success")
            result.pop("text", None)

        # XML-encoded values arrive as strings; coerce the ones the upstream
        # dispatcher expects to be lists/numbers.
        for key in ("coordinate", "coordinate2"):
            value = result.get(key)
            if isinstance(value, str):
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result.pop(key, None)
        for key in ("pixels", "time"):
            value = result.get(key)
            if isinstance(value, str):
                try:
                    result[key] = float(value)
                except ValueError:
                    result.pop(key, None)
        keys_value = result.get("keys")
        if isinstance(keys_value, str):
            try:
                parsed_keys = json.loads(keys_value)
                result["keys"] = parsed_keys if isinstance(parsed_keys, list) else [keys_value]
            except json.JSONDecodeError:
                result["keys"] = [keys_value]

        return result

    @staticmethod
    def _format_as_qwen3vl_jsonxml(
        action_json: Dict[str, Any],
        conclusion: Optional[str],
    ) -> str:
        clean = {k: v for k, v in action_json.items() if not k.startswith("__")}
        payload = {"name": "computer_use", "arguments": clean}
        head = f"Action: {conclusion}\n" if conclusion else ""
        return head + "<tool_call>\n" + json.dumps(payload) + "\n</tool_call>"

    @staticmethod
    def _apply_modifier_keys(parsed: Dict[str, Any], modifier_text: str) -> Dict[str, Any]:
        keys = [k.strip().lower() for k in str(modifier_text).split("+") if k.strip()]
        if not keys:
            return parsed
        result = dict(parsed)
        prefix: List[Dict[str, Any]] = [{"keyboard": {"keys": keys}}]
        result["actions"] = prefix + list(result.get("actions", []))
        result.setdefault("metadata", {})["modifier_keys"] = keys
        return result


def _empty_screenshot_action(conclusion: str, *, parse_error: bool = False) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "thought": "",
        "conclusion": conclusion,
        "action_type": "screenshot",
        "is_terminal": False,
        "wait_time": None,
    }
    if parse_error:
        metadata["parse_error"] = True
    return {
        "actions": [{"action": "screenshot"}],
        "metadata": metadata,
    }
