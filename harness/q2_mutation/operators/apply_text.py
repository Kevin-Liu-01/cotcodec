"""Apply text and config recipes (families ``text`` and ``config``) in plain Python.

Text files have no application save path to reproduce: the agent's editor
writes the characters it holds. Recipes are therefore either one checked
splice of the original characters or one deterministic transformation.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

INI_KV = re.compile(r"^(\s*)([^=:\s#;\[][^=]*?)\s*=\s*(.*)$")


class TextApplyError(ValueError):
    """A text recipe does not match the document it is applied to."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _dump(value: object, indent: int | str, trailing: bool, newline: str) -> str:
    out = json.dumps(value, indent=indent, ensure_ascii=False)
    if newline != "\n":
        out = out.replace("\n", newline)
    return out + (newline if trailing else "")


def apply_steps(text: str, steps: list[dict]) -> str:
    splices = [s for s in steps if s["op"] == "text.splice"]
    if len(splices) > 1:
        raise TextApplyError("a recipe holds at most one splice")
    newline = _newline(text)
    for step in steps:
        op = step["op"]
        if op == "text.splice":
            start, end = int(step["start"]), int(step["end"])
            if not 0 <= start <= end <= len(text):
                raise TextApplyError("splice out of range")
            if _sha(text[start:end]) != step["expect_sha256"]:
                raise TextApplyError("splice target digest mismatch")
            text = text[:start] + step["new"] + text[end:]
        elif op == "text.set_trailing_newline":
            if step["value"] and not text.endswith("\n"):
                text += newline
            elif not step["value"]:
                if text.endswith("\r\n"):
                    text = text[:-2]
                elif text.endswith("\n"):
                    text = text[:-1]
        elif op == "json.reformat":
            text = _dump(json.loads(text), step["indent"], text.endswith("\n"), newline)
        elif op == "json.reorder":
            data = json.loads(text)
            node = data
            for key in step["path"]:
                node = node[key]
            if not isinstance(node, dict) or sorted(node) != sorted(step["order"]):
                raise TextApplyError("reorder keys do not match the object")
            items = {key: node[key] for key in step["order"]}
            node.clear()
            node.update(items)
            text = _dump(data, step["indent"], text.endswith("\n"), newline)
        elif op == "ini.respace":
            lines = text.split("\n")
            for i, line in enumerate(lines):
                body = line[:-1] if line.endswith("\r") else line
                cr = "\r" if line.endswith("\r") else ""
                match = INI_KV.match(body)
                if match is None or body.lstrip().startswith(("#", ";", "[")):
                    continue
                sep = " = " if step["style"] == "spaced" else "="
                lines[i] = f"{match.group(1)}{match.group(2)}{sep}{match.group(3)}{cr}"
            text = "\n".join(lines)
        else:
            raise TextApplyError(f"unknown text step {op!r}")
    return text


def apply_file(src: str | Path, dst: str | Path, steps: list[dict], input_sha256: str) -> str:
    raw = Path(src).read_bytes()
    if hashlib.sha256(raw).hexdigest() != input_sha256:
        raise TextApplyError("input digest mismatch")
    out = apply_steps(raw.decode("utf-8"), steps).encode("utf-8")
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_bytes(out)
    return hashlib.sha256(out).hexdigest()
