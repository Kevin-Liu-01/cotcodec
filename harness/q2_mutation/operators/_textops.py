"""Plain-text and configuration-file mutation operators (families ``text`` and ``config``).

Text files have no document model to go through, so recipes are applied by
``apply_text.py``: either a splice of the original characters (value edits,
key deletions, line edits) or a deterministic transformation (re-indent,
key reorder, key/value spacing). Splices never re-serialize the file, so only
the targeted characters change.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from harness.q2_mutation.operators import _jsonspan as js
from harness.q2_mutation.operators._base import (
    ALT,
    EQUIV,
    EXTRA,
    VIOLATION,
    Build,
    Context,
    Operator,
    OperatorError,
    judge_alternative,
    judge_equivalence,
    judge_extra,
    judge_violation,
    site,
)
from harness.q2_mutation.operators._common import choose_word_edit, judge_text_edit, perturb_word
from harness.q2_mutation.operators._diff import seg, unseg
from harness.q2_mutation.operators._purity import Expectation
from harness.q2_mutation.operators._spec import quoted, req_text


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source(ctx: Context) -> str:
    text = getattr(ctx, "source_text", None)
    if text is None:
        raise OperatorError("text operators need the source text")
    return text


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset)


def splice_step(text: str, start: int, end: int, new: str) -> dict:
    return {"op": "text.splice", "start": start, "end": end, "new": new,
            "expect_sha256": digest(text[start:end])}


def lines_between(text: str, start: int, end: int) -> list[str]:
    first, last = line_of(text, start), line_of(text, max(start, end - 1))
    return [f"lines/{i}" for i in range(first, last + 1)]


# --------------------------------------------------------------------------- config addressing


@dataclass(frozen=True)
class Leaf:
    unit: str
    start: int
    end: int
    kind: str  # json-string | json-number | json-literal | ini
    raw: str
    value: object
    delete: tuple[int, int]


def _json_leaves(text: str) -> list[Leaf]:
    try:
        root = js.parse(text)
    except js.JsonSpanError:
        return []
    out = []
    for path, node in js.leaf_paths(root):
        _value, parent, index = js.find(root, list(path))
        unit = "parsed/value/" + "/".join(seg(k) for k in path)
        raw = node.text(text)
        out.append(Leaf(unit, node.start, node.end, f"json-{node.kind}", raw, json.loads(raw),
                        js.delete_span(text, parent, index) if parent is not None else (0, 0)))
    return out


_INI_LINE = re.compile(r"^(\s*)([^=:\s#;\[][^=:]*?)(\s*)([=:])(\s*)(.*?)(\s*)$")


def _ini_leaves(text: str) -> list[Leaf]:
    out = []
    section = "__root__"
    offset = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        body = line[:-1] if line.endswith("\r") else line
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
        elif stripped and stripped[0] not in "#;":
            match = _INI_LINE.match(body)
            follows = lines[i + 1] if i + 1 < len(lines) else ""
            continuation = bool(follows) and follows[0] in " \t" and follows.strip()
            if match and not continuation:
                value_start = offset + match.start(6)
                value_end = offset + match.end(6)
                key = match.group(2).strip()
                line_end = offset + len(line) + (1 if i + 1 < len(lines) else 0)
                out.append(Leaf(f"parsed/value/{seg(section)}/{seg(key)}", value_start,
                                value_end, "ini", match.group(6), match.group(6),
                                (offset, line_end)))
        offset += len(line) + 1
    return out


def leaves(ctx: Context) -> list[Leaf]:
    fmt = ctx.base.get("format")
    if fmt == "json":
        return _json_leaves(source(ctx))
    if fmt == "ini":
        return _ini_leaves(source(ctx))
    return []


def _leaf(ctx: Context, unit: str) -> Leaf:
    for leaf in leaves(ctx):
        if leaf.unit == unit:
            return leaf
    raise OperatorError(f"no config leaf {unit}")


_BOOLS = {"true": "false", "false": "true", "yes": "no", "no": "yes", "on": "off", "off": "on",
          "1": "0", "0": "1"}


def changed_raw(leaf: Leaf, rng) -> str:
    """A different value of the same type, as source text."""
    if leaf.kind == "json-number":
        value = leaf.value
        if isinstance(value, int):
            return str(value + rng.choice([1, 2, -1]) if value > 1 else value + 1)
        return json.dumps(round(float(value) + 0.5, 6))
    if leaf.kind == "json-literal":
        if leaf.value is None:
            raise OperatorError("null leaf")
        return "false" if leaf.value else "true"
    if leaf.kind == "json-string":
        text = str(leaf.value)
        if text.lower() in _BOOLS:
            new = _BOOLS[text.lower()]
            return json.dumps(new.upper() if text.isupper() else new)
        return json.dumps(_perturb_text(text, rng))
    text = leaf.raw
    if re.fullmatch(r"-?\d+", text):
        return str(int(text) + 1)
    if text.lower() in _BOOLS:
        new = _BOOLS[text.lower()]
        return new.capitalize() if text[:1].isupper() else new
    return _perturb_text(text, rng)


def _perturb_text(text: str, rng) -> str:
    words = [m.span() for m in re.finditer(r"[A-Za-z]{3,}", text)]
    if words:
        start, end = rng.choice(words)
        return text[:start] + perturb_word(text[start:end], rng) + text[end:]
    numbers = [m.span() for m in re.finditer(r"\d+", text)]
    if numbers:
        start, end = rng.choice(numbers)
        return text[:start] + str(int(text[start:end]) + 1) + text[end:]
    return text + "x"


def _parsed_value(raw: str, kind: str) -> object:
    return json.loads(raw) if kind.startswith("json") else raw


def bound_leaves(ctx: Context, binding) -> list[Leaf]:
    if binding is None:
        return []
    units = set(binding.units)
    return [leaf for leaf in leaves(ctx) if leaf.unit in units]


def outside_leaves(ctx: Context) -> list[Leaf]:
    return [leaf for leaf in leaves(ctx) if ctx.is_outside(leaf.unit)]


def _key_label(unit: str) -> str:
    return "/".join(unseg(p) for p in unit.split("/")[2:])


# --------------------------------------------------------------------------- E


class _TrailingNewline(Operator):
    label_class = EQUIV
    target = "document"
    aspects = ("newline",)
    description = "Add or remove the final newline."

    def sites(self, ctx, req, binding):
        return [site("trailing_newline")]

    def build(self, ctx, where, rng):
        value = not ctx.base["trailing_newline"]
        return Build(
            steps=[{"op": "text.set_trailing_newline", "value": value}],
            expectation=Expectation(
                allow=["trailing_newline", "lines/*"],
                must_change=["trailing_newline"],
                must_equal=[("trailing_newline", value)],
                preserve=["parsed"] if ctx.base.get("parsed") is not None else [],
            ),
            facts={"value": value},
        )

    def judge(self, ctx, where, built):
        action = "adds" if built.facts["value"] else "removes"
        return judge_equivalence(ctx, self.aspects, f"{action} the final newline of the file")


class TextTrailingNewline(_TrailingNewline):
    name = "text.eq.trailing_newline"
    family = "text"


class ConfigTrailingNewline(_TrailingNewline):
    name = "config.eq.trailing_newline"
    family = "config"


def _indent_of(text: str) -> int | str:
    for line in text.split("\n"):
        match = re.match(r"^([ \t]+)\S", line)
        if match:
            ws = match.group(1)
            return "\t" if ws.startswith("\t") else len(ws)
    return 0


def _strict_json(text: str) -> object | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


class JsonReformat(Operator):
    name = "config.eq.json_reformat"
    family = "config"
    label_class = EQUIV
    target = "document"
    aspects = ("whitespace",)
    description = "Re-indent a JSON file (same keys, order and values)."

    def sites(self, ctx, req, binding):
        if ctx.base.get("format") != "json" or _strict_json(source(ctx)) is None:
            return []
        return [site("lines")]

    def build(self, ctx, where, rng):
        current = _indent_of(source(ctx))
        indent = 2 if current == 4 else 4
        return Build(
            steps=[{"op": "json.reformat", "indent": indent}],
            expectation=Expectation(
                allow=["lines/*", "trailing_newline", "newline"],
                must_change=["lines/*"],
                preserve=["parsed/value"],
            ),
            facts={"before": current, "after": indent},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_equivalence(ctx, self.aspects, f"re-indents the JSON from {f['before']!r} "
                                 f"to {f['after']} spaces without changing any key or value")


class JsonKeyReorder(Operator):
    name = "config.eq.json_key_reorder"
    family = "config"
    label_class = EQUIV
    target = "document"
    aspects = ("key_order",)
    description = "Reverse the key order of one JSON object (objects are unordered)."

    def sites(self, ctx, req, binding):
        data = _strict_json(source(ctx)) if ctx.base.get("format") == "json" else None
        out = []

        def walk(node, path):
            if isinstance(node, dict):
                if len(node) >= 2:
                    out.append(site("parsed/key_order", path=list(path)))
                for key, child in node.items():
                    walk(child, (*path, key))

        walk(data, ())
        return out

    def build(self, ctx, where, rng):
        path = where.info["path"]
        node = _strict_json(source(ctx))
        for key in path:
            node = node[key]
        order = list(reversed(list(node)))
        return Build(
            steps=[{"op": "json.reorder", "path": path, "order": order,
                    "indent": _indent_of(source(ctx)) or 2}],
            expectation=Expectation(
                allow=["lines/*", "parsed/key_order", "trailing_newline"],
                must_change=["parsed/key_order"],
                preserve=["parsed/value"],
            ),
            facts={"path": "/".join(path) or "<root>", "keys": len(order)},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_equivalence(ctx, self.aspects, f"reverses the order of the {f['keys']} "
                                 f"keys of object {f['path']!r}; values are unchanged")


class IniKeyValueSpacing(Operator):
    name = "config.eq.ini_kv_spacing"
    family = "config"
    label_class = EQUIV
    target = "document"
    aspects = ("whitespace",)
    description = "Toggle spaces around '=' in key = value lines of an INI-style file."

    def sites(self, ctx, req, binding):
        if ctx.base.get("format") != "ini" or not _ini_leaves(source(ctx)):
            return []
        return [site("lines")]

    def build(self, ctx, where, rng):
        spaced = sum(1 for line in source(ctx).split("\n") if re.search(r"\S\s+=\s+", line))
        compact = sum(1 for line in source(ctx).split("\n") if re.search(r"\S=\S", line))
        style = "compact" if spaced >= compact else "spaced"
        return Build(
            steps=[{"op": "ini.respace", "style": style}],
            expectation=Expectation(
                allow=["lines/*"],
                must_change=["lines/*"],
                preserve=["parsed/value"],
            ),
            facts={"style": style},
        )

    def judge(self, ctx, where, built):
        return judge_equivalence(ctx, self.aspects, f"rewrites key = value lines in the "
                                 f"{built.facts['style']} style; parsed values are unchanged")


# --------------------------------------------------------------------------- A


class JsonNumberRepr(Operator):
    name = "config.alt.json_number_repr"
    family = "config"
    label_class = ALT
    target = "requirement"
    check_kinds = ("config_value",)
    aspects = ("number_type",)
    description = "Write a bound integer value as the equal decimal (20 -> 20.0)."

    def sites(self, ctx, req, binding):
        return [site(leaf.unit, req.req_id) for leaf in bound_leaves(ctx, binding)
                if leaf.kind == "json-number" and isinstance(leaf.value, int)
                and not isinstance(leaf.value, bool)]

    def build(self, ctx, where, rng):
        leaf = _leaf(ctx, where.unit)
        text = source(ctx)
        new = f"{leaf.value}.0"
        return Build(
            steps=[splice_step(text, leaf.start, leaf.end, new)],
            expectation=Expectation(
                allow=[leaf.unit, *lines_between(text, leaf.start, leaf.end)],
                must_change=[leaf.unit],
                preserve=[leaf.unit],
            ),
            facts={"key": _key_label(leaf.unit), "before": leaf.raw, "after": new},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_alternative(
            ctx, ctx.requirement(where.req_id), self.aspects,
            f"writes {f['key']} as {f['after']} instead of {f['before']} (numerically equal)",
        )


# --------------------------------------------------------------------------- R


class ConfigValueChange(Operator):
    name = "config.viol.value_change"
    family = "config"
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("config_value",)
    description = "Change a bound configuration value to a different value of the same type."

    def sites(self, ctx, req, binding):
        return [site(leaf.unit, req.req_id) for leaf in bound_leaves(ctx, binding)
                if leaf.value is not None]

    def build(self, ctx, where, rng):
        leaf = _leaf(ctx, where.unit)
        text = source(ctx)
        new = changed_raw(leaf, rng)
        return Build(
            steps=[splice_step(text, leaf.start, leaf.end, new)],
            expectation=Expectation(
                allow=[leaf.unit, *lines_between(text, leaf.start, leaf.end)],
                must_change=[leaf.unit],
                must_equal=[(leaf.unit, _parsed_value(new, leaf.kind))],
            ),
            facts={"key": _key_label(leaf.unit), "before": leaf.raw, "after": new},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), (), f"sets {f['key']} to {f['after']} "
            f"(gold has {f['before']})", ctx.bindings.get(where.req_id),
            implied_by_kind=("config_value",),
        )


class ConfigKeyDelete(Operator):
    name = "config.viol.key_delete"
    family = "config"
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("config_value",)
    description = "Delete a bound configuration key."

    def sites(self, ctx, req, binding):
        return [site(leaf.unit, req.req_id) for leaf in bound_leaves(ctx, binding)
                if leaf.delete != (0, 0)]

    def build(self, ctx, where, rng):
        leaf = _leaf(ctx, where.unit)
        text = source(ctx)
        start, end = leaf.delete
        return Build(
            steps=[splice_step(text, start, end, "")],
            expectation=Expectation(
                allow=[leaf.unit, *lines_between(text, start, end), "lines/+*",
                       "trailing_newline"],
                must_change=[leaf.unit],
            ),
            facts={"key": _key_label(leaf.unit)},
        )

    def judge(self, ctx, where, built):
        return judge_violation(
            ctx.requirement(where.req_id), (), f"deletes the key {built.facts['key']}",
            ctx.bindings.get(where.req_id), implied_by_kind=("config_value",),
        )


def _bound_lines(ctx: Context, binding) -> list[int]:
    if binding is None:
        return []
    out = []
    for unit in binding.units:
        parts = unit.split("/")
        if parts[0] == "lines" and len(parts) == 2:
            out.append(int(parts[1]))
    return out


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for i, char in enumerate(text):
        if char == "\n":
            offsets.append(i + 1)
    return offsets


def _line_edit(ctx: Context, line: int, rng, prefer: list[str]) -> Build:
    text = source(ctx)
    content = ctx.base["lines"][line]
    choice = choose_word_edit(content, rng, prefer)
    if choice is None:
        raise OperatorError("no editable word")
    start, end, old, new, inside = choice
    base = _line_offsets(text)[line]
    return Build(
        steps=[splice_step(text, base + start, base + end, new)],
        expectation=Expectation(
            allow=[f"lines/{line}", "parsed", "parsed/*"],
            must_change=[f"lines/{line}"],
            must_equal=[(f"lines/{line}", content[:start] + new + content[end:])],
        ),
        facts={"line": line + 1, "old": old, "new": new, "inside_hint": inside},
    )


class TextLineEdit(Operator):
    name = "text.viol.line_edit"
    family = "text"
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("text_run", "other", "config_value")
    description = "Change one letter of a word on a bound line (preferring quoted text)."

    def sites(self, ctx, req, binding):
        return [site(f"lines/{i}", req.req_id) for i in _bound_lines(ctx, binding)
                if re.search(r"[A-Za-z]{3}", ctx.base["lines"][i])]

    def build(self, ctx, where, rng):
        line = int(where.unit.split("/")[1])
        return _line_edit(ctx, line, rng, quoted(req_text(ctx.requirement(where.req_id))))

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_text_edit(
            ctx.requirement(where.req_id), ctx.bindings.get(where.req_id),
            f"changes {f['old']!r} to {f['new']!r} on line {f['line']}", f["old"],
        )


# --------------------------------------------------------------------------- F


class ConfigUnrelatedValue(Operator):
    name = "config.extra.unrelated_value_change"
    family = "config"
    label_class = EXTRA
    target = "outside"
    description = "Change a configuration value that no requirement reads."

    def sites(self, ctx, req, binding):
        return [site(leaf.unit) for leaf in outside_leaves(ctx) if leaf.value is not None][:200]

    def build(self, ctx, where, rng):
        return ConfigValueChange().build(ctx, where, rng)

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(ctx, (), f"sets the unrelated key {f['key']} to {f['after']} "
                           f"(was {f['before']})", harmful=True)


class ConfigUnrelatedKeyDelete(Operator):
    name = "config.extra.unrelated_key_delete"
    family = "config"
    label_class = EXTRA
    target = "outside"
    description = "Delete a configuration key that no requirement reads."

    def sites(self, ctx, req, binding):
        return [site(leaf.unit) for leaf in outside_leaves(ctx) if leaf.delete != (0, 0)][:200]

    def build(self, ctx, where, rng):
        return ConfigKeyDelete().build(ctx, where, rng)

    def judge(self, ctx, where, built):
        return judge_extra(ctx, (), f"deletes the unrelated key {built.facts['key']}",
                           harmful=True)


def _outside_lines(ctx: Context) -> list[int]:
    return [
        i for i, line in enumerate(ctx.base["lines"])
        if re.search(r"[A-Za-z]{3}", line) and ctx.is_outside(f"lines/{i}")
    ]


class TextUnrelatedLineEdit(Operator):
    name = "text.extra.unrelated_line_edit"
    family = "text"
    label_class = EXTRA
    target = "outside"
    description = "Change one letter of a word on a line no requirement reads."

    def sites(self, ctx, req, binding):
        return [site(f"lines/{i}") for i in _outside_lines(ctx)][:200]

    def build(self, ctx, where, rng):
        return _line_edit(ctx, int(where.unit.split("/")[1]), rng, [])

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(ctx, (), f"changes {f['old']!r} to {f['new']!r} on unrelated line "
                           f"{f['line']}", harmful=True)


class TextUnrelatedLineDelete(Operator):
    name = "text.extra.unrelated_line_delete"
    family = "text"
    label_class = EXTRA
    target = "outside"
    description = "Delete a non-empty line no requirement reads."

    def sites(self, ctx, req, binding):
        return [site(f"lines/{i}") for i in _outside_lines(ctx)][:200]

    def build(self, ctx, where, rng):
        text = source(ctx)
        line = int(where.unit.split("/")[1])
        offsets = _line_offsets(text)
        start = offsets[line]
        end = offsets[line + 1] if line + 1 < len(offsets) else len(text)
        return Build(
            steps=[splice_step(text, start, end, "")],
            expectation=Expectation(
                allow=[f"lines/{line}", "trailing_newline"],
                must_change=[f"lines/{line}"],
            ),
            facts={"line": line + 1},
        )

    def judge(self, ctx, where, built):
        return judge_extra(ctx, (), f"deletes unrelated line {built.facts['line']}",
                           harmful=True)
