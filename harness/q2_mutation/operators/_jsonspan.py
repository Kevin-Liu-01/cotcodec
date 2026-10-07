"""A position-tracking JSON(C) parser for surgical config edits.

Config mutants must change only the targeted value, so edits splice the
original text instead of re-serializing the file (which would also change
whitespace, key order and comments). Comments and trailing commas (VS Code
style JSONC) are accepted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


class JsonSpanError(ValueError):
    """The text is not JSON(C) this parser understands."""


@dataclass
class Member:
    key: str
    key_start: int
    value: Node
    start: int  # start of the key token
    end: int  # end of the value


@dataclass
class Node:
    kind: str  # object | array | string | number | literal
    start: int
    end: int
    members: list[Member] = field(default_factory=list)
    items: list[Node] = field(default_factory=list)

    def text(self, source: str) -> str:
        return source[self.start : self.end]


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def skip(self) -> None:
        text = self.text
        while self.pos < len(text):
            char = text[self.pos]
            if char in " \t\r\n﻿":
                self.pos += 1
            elif text.startswith("//", self.pos):
                end = text.find("\n", self.pos)
                self.pos = len(text) if end == -1 else end
            elif text.startswith("/*", self.pos):
                end = text.find("*/", self.pos + 2)
                if end == -1:
                    raise JsonSpanError("unterminated comment")
                self.pos = end + 2
            else:
                break

    def value(self) -> Node:
        self.skip()
        if self.pos >= len(self.text):
            raise JsonSpanError("unexpected end of text")
        char = self.text[self.pos]
        if char == "{":
            return self.obj()
        if char == "[":
            return self.arr()
        if char == '"':
            start = self.pos
            self.string()
            return Node("string", start, self.pos)
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] not in ",]}/ \t\r\n":
            self.pos += 1
        token = self.text[start : self.pos]
        if token in {"true", "false", "null"}:
            return Node("literal", start, self.pos)
        try:
            float(token)
        except ValueError as exc:
            raise JsonSpanError(f"bad token {token!r} at {start}") from exc
        return Node("number", start, self.pos)

    def string(self) -> str:
        start = self.pos
        self.pos += 1
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == "\\":
                self.pos += 2
                continue
            self.pos += 1
            if char == '"':
                return json.loads(self.text[start : self.pos])
        raise JsonSpanError("unterminated string")

    def obj(self) -> Node:
        node = Node("object", self.pos, self.pos)
        self.pos += 1
        while True:
            self.skip()
            if self.pos < len(self.text) and self.text[self.pos] == "}":
                self.pos += 1
                node.end = self.pos
                return node
            if self.pos >= len(self.text) or self.text[self.pos] != '"':
                raise JsonSpanError(f"expected a key at {self.pos}")
            key_start = self.pos
            key = self.string()
            self.skip()
            if self.pos >= len(self.text) or self.text[self.pos] != ":":
                raise JsonSpanError(f"expected ':' at {self.pos}")
            self.pos += 1
            value = self.value()
            node.members.append(Member(key, key_start, value, key_start, value.end))
            self.skip()
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1

    def arr(self) -> Node:
        node = Node("array", self.pos, self.pos)
        self.pos += 1
        while True:
            self.skip()
            if self.pos < len(self.text) and self.text[self.pos] == "]":
                self.pos += 1
                node.end = self.pos
                return node
            node.items.append(self.value())
            self.skip()
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1


def parse(text: str) -> Node:
    parser = _Parser(text)
    root = parser.value()
    parser.skip()
    if parser.pos != len(text):
        raise JsonSpanError(f"trailing content at {parser.pos}")
    return root


def find(root: Node, path: list[str]) -> tuple[Node, Node | None, int]:
    """Return (value node, parent object node, member index) for a key path."""
    node, parent, index = root, None, -1
    for key in path:
        if node.kind != "object":
            raise JsonSpanError(f"{key!r}: parent is not an object")
        matches = [i for i, m in enumerate(node.members) if m.key == key]
        if not matches:
            raise JsonSpanError(f"key {key!r} not found")
        parent, index = node, matches[-1]
        node = node.members[index].value
    return node, parent, index


def delete_span(text: str, parent: Node, index: int) -> tuple[int, int]:
    """Span to remove so that member ``index`` disappears and the object stays valid."""
    members = parent.members
    member = members[index]
    if index + 1 < len(members):
        return member.start, members[index + 1].start
    if index > 0:
        return members[index - 1].end, member.end
    return member.start, member.end


def leaf_paths(root: Node, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Node]]:
    """Every scalar leaf reachable through object keys only."""
    out: list[tuple[tuple[str, ...], Node]] = []
    if root.kind != "object":
        return out
    seen: dict[str, int] = {}
    for i, member in enumerate(root.members):
        seen[member.key] = i
    for key, i in seen.items():
        node = root.members[i].value
        path = (*prefix, key)
        if node.kind == "object":
            out.extend(leaf_paths(node, path))
        elif node.kind in {"string", "number", "literal"}:
            out.append((path, node))
    return out
