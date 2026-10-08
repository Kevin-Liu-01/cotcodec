"""Word-processing (docx, LibreOffice Writer) mutation operators.

Paragraph units are ``body/<i>`` for top-level blocks and
``body/<i>/cell/<r>/<c>/<k>`` for paragraphs inside table cells, in the base
snapshot's coordinates. ``uno_apply.py`` addresses the same paragraph through
the text enumeration and refuses to edit if the paragraph text differs from
``expect_sha256`` (a digest of the expected text).
"""

from __future__ import annotations

import re

from harness.q2_mutation.operators._base import (
    ALT,
    AMBIGUOUS,
    EQUIV,
    EXTRA,
    VIOLATION,
    Build,
    Context,
    Judgement,
    Operator,
    OperatorError,
    judge_alternative,
    judge_equivalence,
    judge_extra,
    judge_violation,
    site,
)
from harness.q2_mutation.operators._common import (
    NON_VIEW_KINDS,
    DocPropertyOperator,
    choose_word_edit,
    judge_text_edit,
    text_sha256,
)
from harness.q2_mutation.operators._diff import resolve
from harness.q2_mutation.operators._purity import Expectation, docx_effective
from harness.q2_mutation.operators._spec import (
    Binding,
    allowed_mentions,
    docx_paragraphs,
    quoted,
    req_text,
)

FAMILY = "docx"

HIGHLIGHT_HEX = {
    "yellow": "FFFF00", "green": "00FF00", "cyan": "00FFFF", "magenta": "FF00FF",
    "blue": "0000FF", "red": "FF0000", "darkBlue": "000080", "darkCyan": "008080",
    "darkGreen": "008000", "darkMagenta": "800080", "darkRed": "800000",
    "darkYellow": "808000", "darkGray": "808080", "lightGray": "C0C0C0", "black": "000000",
    "white": "FFFFFF",
}
DEFAULT_PARA_STYLES = {"", "Normal", "Default Paragraph Style", "Standard", "Default",
                       "LO-normal"}


def address(unit: str) -> dict:
    parts = unit.split("/")
    if parts[0] != "body":
        raise OperatorError(f"not a paragraph unit: {unit}")
    if len(parts) == 2:
        return {"block": int(parts[1])}
    if len(parts) == 6 and parts[2] == "cell":
        return {"block": int(parts[1]), "cell": [int(parts[3]), int(parts[4])],
                "para": int(parts[5])}
    raise OperatorError(f"not a paragraph unit: {unit}")


def paragraph(snap: dict, unit: str) -> dict:
    block = resolve(snap, unit)
    if block.get("type") != "p":
        raise OperatorError(f"{unit} is not a paragraph")
    return block


def bound_paragraphs(ctx: Context, binding: Binding | None) -> list[str]:
    if binding is None:
        return []
    paras = {path for path, _ in docx_paragraphs(ctx.base)}
    return [u for u in binding.units if u in paras]


def outside_paragraphs(ctx: Context, top_level: bool | None = None) -> list[str]:
    out = []
    for path, block in docx_paragraphs(ctx.base):
        is_top = path.count("/") == 1
        if top_level is not None and is_top != top_level:
            continue
        if block["text"].strip() and ctx.is_outside(path):
            out.append(path)
    return out


def deletable(snap: dict, unit: str) -> bool:
    """A non-empty top-level paragraph that neither ends nor starts a section.

    Deleting a paragraph with a section break merges sections, and Writer keeps the
    page style and page-number restart on a section's first paragraph, so deleting
    that paragraph changes the section properties too.
    """
    index = int(unit.split("/")[1])
    block = snap["body"][index]
    if block.get("type") != "p" or not block["text"].strip() or block.get("section_break"):
        return False
    return index > 0 and not snap["body"][index - 1].get("section_break")


def span_offsets(block: dict) -> list[tuple[int, int, dict]]:
    out = []
    pos = 0
    for text, props in block["spans"]:
        out.append((pos, pos + len(text), props))
        pos += len(text)
    return out


def text_step(unit: str, block: dict, start: int, end: int, new: str) -> dict:
    return {"op": "docx.replace_text", **address(unit), "start": start, "end": end,
            "new": new, "expect_sha256": text_sha256(block["text"])}


def text_edit_build(ctx: Context, unit: str, rng, prefer: list[str]) -> Build:
    block = paragraph(ctx.base, unit)
    choice = choose_word_edit(block["text"], rng, prefer)
    if choice is None:
        raise OperatorError("no editable word")
    start, end, old, new, inside = choice
    new_text = block["text"][:start] + new + block["text"][end:]
    return Build(
        steps=[text_step(unit, block, start, end, new)],
        expectation=Expectation(
            allow=[f"{unit}/text", f"{unit}/spans"],
            must_change=[f"{unit}/text"],
            must_equal=[(f"{unit}/text", new_text)],
        ),
        facts={"unit": unit, "old": old, "new": new, "inside_hint": inside},
    )


# --------------------------------------------------------------------------- E


class DocProperty(DocPropertyOperator):
    name = "docx.eq.doc_property"
    family = FAMILY
    description = "Set the document's Title, Subject or Keywords property."


class ViewZoom(Operator):
    name = "docx.eq.view_zoom"
    family = FAMILY
    label_class = EQUIV
    target = "document"
    aspects = ("zoom",)
    description = "Change the document zoom level saved in the settings part."

    def sites(self, ctx, req, binding):
        current = (ctx.base.get("settings") or {}).get("zoom")
        return [site("settings/zoom", zoom=z) for z in (80, 120, 150) if str(z) != current]

    def build(self, ctx, where, rng):
        zoom = where.info["zoom"]
        return Build(
            steps=[{"op": "docx.set_view", "zoom": zoom}],
            expectation=Expectation(
                allow=["settings/*"],
                must_change=["settings/zoom"],
                must_equal=[("settings/zoom", str(zoom))],
                forbid_kinds=NON_VIEW_KINDS,
            ),
            facts={"zoom": zoom},
        )

    def judge(self, ctx, where, built):
        return judge_equivalence(
            ctx, self.aspects, f"sets the document zoom to {built.facts['zoom']}%"
        )


# --------------------------------------------------------------------------- A


_CHAR_ATTRS = {
    "bold": ("b", lambda v: v is True, {"bold": False}),
    "italic": ("i", lambda v: v is True, {"italic": False}),
    "underline": ("u", lambda v: v not in (None, "none"), {"underline": False}),
    "color": ("color", lambda v: v not in (None, "auto", "000000"), {"color": None}),
    "highlight": ("highlight", lambda v: v not in (None, "none"), {"highlight": None}),
}


class CharStyleForDirect(Operator):
    name = "docx.alt.char_style_for_direct"
    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("text_run",)
    aspects = ("style",)
    description = (
        "Move a bound run's direct bold/italic/underline/colour into a new character style."
    )

    def sites(self, ctx, req, binding):
        out = []
        for unit in bound_paragraphs(ctx, binding):
            for index, (start, end, props) in enumerate(span_offsets(paragraph(ctx.base, unit))):
                if "rStyle" in props:
                    continue
                attrs = [a for a, (key, on, _p) in _CHAR_ATTRS.items()
                         if a != "highlight" and on(props.get(key))]
                if attrs and end > start:
                    out.append(site(unit, req.req_id, span=index, start=start, end=end,
                                    attrs=attrs))
        return out

    def build(self, ctx, where, rng):
        info = where.info
        block = paragraph(ctx.base, where.unit)
        name = f"Q2M Char {rng.randrange(1000, 9999)}"
        return Build(
            steps=[{"op": "docx.direct_to_char_style", **address(where.unit),
                    "start": info["start"], "end": info["end"], "attrs": info["attrs"],
                    "style_name": name, "expect_sha256": text_sha256(block["text"])}],
            expectation=Expectation(
                allow=[f"{where.unit}/spans", "styles/char/*", "styles/*"],
                must_change=[f"{where.unit}/spans"],
                preserve=[f"{where.unit}/text"],
                appearance=[where.unit],
            ),
            facts={"unit": where.unit, "attrs": info["attrs"], "style_name": name,
                   "text": block["text"][info["start"]:info["end"]]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_alternative(
            ctx, ctx.requirement(where.req_id), self.aspects,
            f"applies {'/'.join(f['attrs'])} to {f['text']!r} through a new character style "
            f"{f['style_name']!r} instead of direct formatting (resolved appearance unchanged)",
            (r"direct(ly)? format",),
        )


class ParaDirectForStyle(Operator):
    name = "docx.alt.para_direct_for_style"
    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("paragraph_format", "text_run")
    aspects = ("style",)
    description = (
        "Replace a bound paragraph's named style with the default style plus direct formatting "
        "that reproduces its appearance."
    )

    def sites(self, ctx, req, binding):
        return [
            site(u, req.req_id) for u in bound_paragraphs(ctx, binding)
            if paragraph(ctx.base, u)["style"] not in DEFAULT_PARA_STYLES
            and paragraph(ctx.base, u)["text"].strip()
        ]

    def build(self, ctx, where, rng):
        block = paragraph(ctx.base, where.unit)
        return Build(
            steps=[{"op": "docx.para_style_to_direct", **address(where.unit),
                    "expect_sha256": text_sha256(block["text"])}],
            expectation=Expectation(
                allow=[f"{where.unit}/style", f"{where.unit}/ppr", f"{where.unit}/ppr/*",
                       f"{where.unit}/spans", "styles/*"],
                must_change=[f"{where.unit}/style"],
                preserve=[f"{where.unit}/text"],
                appearance=[where.unit],
            ),
            facts={"unit": where.unit, "style": block["style"], "text": block["text"][:80]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_alternative(
            ctx, ctx.requirement(where.req_id), self.aspects,
            f"formats the paragraph {f['text']!r} directly instead of with the style "
            f"{f['style']!r}; the resolved appearance is unchanged but the outline level and "
            "style name are not",
            (r"\bstyles?\b", r"\bheading\s*\d", r"\boutline"),
        )


class HighlightAsShading(Operator):
    name = "docx.alt.highlight_as_shading"
    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("text_run",)
    aspects = ("highlight",)
    description = "Replace a bound run's highlighting with character shading of the same colour."

    def sites(self, ctx, req, binding):
        out = []
        for unit in bound_paragraphs(ctx, binding):
            for index, (start, end, props) in enumerate(span_offsets(paragraph(ctx.base, unit))):
                colour = props.get("highlight")
                if isinstance(colour, str) and colour in HIGHLIGHT_HEX and end > start:
                    out.append(site(unit, req.req_id, span=index, start=start, end=end,
                                    colour=colour))
        return out

    def build(self, ctx, where, rng):
        info = where.info
        block = paragraph(ctx.base, where.unit)
        return Build(
            steps=[{"op": "docx.set_char_props", **address(where.unit), "start": info["start"],
                    "end": info["end"], "expect_sha256": text_sha256(block["text"]),
                    "props": {"highlight": None, "back_color": HIGHLIGHT_HEX[info["colour"]]}}],
            expectation=Expectation(
                allow=[f"{where.unit}/spans"],
                must_change=[f"{where.unit}/spans"],
                preserve=[f"{where.unit}/text"],
            ),
            facts={"unit": where.unit, "colour": info["colour"],
                   "text": block["text"][info["start"]:info["end"]]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_alternative(
            ctx, ctx.requirement(where.req_id), self.aspects,
            f"shows {f['text']!r} on a {f['colour']} character background (shading) instead of "
            "a highlight; the rendered colours are the same",
        )


_UPPER_SEGMENT = re.compile(r"[A-Z][A-Z ]{3,}[A-Z]")


class CaseViaFormat(Operator):
    name = "docx.alt.case_via_format"
    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("text_run",)
    aspects = ("case",)
    description = (
        "Retype an upper-case run in lower case and apply the UPPERCASE case effect, so it "
        "renders the same."
    )

    def sites(self, ctx, req, binding):
        out = []
        for unit in bound_paragraphs(ctx, binding):
            for match in _UPPER_SEGMENT.finditer(paragraph(ctx.base, unit)["text"]):
                out.append(site(unit, req.req_id, start=match.start(), end=match.end()))
        return out

    def build(self, ctx, where, rng):
        info = where.info
        block = paragraph(ctx.base, where.unit)
        old = block["text"][info["start"]:info["end"]]
        new = old.lower()
        new_text = block["text"][: info["start"]] + new + block["text"][info["end"]:]
        return Build(
            steps=[
                text_step(where.unit, block, info["start"], info["end"], new),
                {"op": "docx.set_char_props", **address(where.unit), "start": info["start"],
                 "end": info["start"] + len(new), "expect_sha256": text_sha256(new_text),
                 "props": {"case_map": "upper"}},
            ],
            expectation=Expectation(
                allow=[f"{where.unit}/text", f"{where.unit}/spans"],
                must_change=[f"{where.unit}/text", f"{where.unit}/spans"],
                must_equal=[(f"{where.unit}/text", new_text)],
            ),
            facts={"unit": where.unit, "old": old, "new": new},
        )

    def judge(self, ctx, where, built):
        return judge_case_via_format(ctx, ctx.requirement(where.req_id), built.facts)


def judge_case_via_format(ctx: Context, req, facts: dict) -> Judgement:
    allowed = allowed_mentions(ctx.spec, "case")
    change = (
        f"stores {facts['old']!r} as {facts['new']!r} with the UPPERCASE case effect, so it "
        "renders identically but the stored characters differ"
    )
    if allowed:
        cites = "; ".join(f"allowed_variations[{i}] {t!r}" for i, t, _ in allowed)
        return Judgement(ALT, f"W-A-ALLOWED: {change}; the spec leaves case mechanism open "
                         f"({cites}).", "W-A-ALLOWED", (req.req_id,))
    return Judgement(
        AMBIGUOUS,
        f"W-A-REPRESENTATION: {change}; whether {req.req_id}'s observable reads stored or "
        "rendered text is not stated.",
        "W-A-REPRESENTATION",
        (req.req_id,),
    )


# --------------------------------------------------------------------------- R


class TextEdit(Operator):
    name = "docx.viol.text_edit"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("text_run", "paragraph_format", "other")
    description = "Change one letter of a word in a bound paragraph (preferring quoted text)."

    def sites(self, ctx, req, binding):
        return [site(u, req.req_id) for u in bound_paragraphs(ctx, binding)
                if paragraph(ctx.base, u)["text"].strip()]

    def build(self, ctx, where, rng):
        return text_edit_build(ctx, where.unit, rng,
                               quoted(req_text(ctx.requirement(where.req_id))))

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_text_edit(
            ctx.requirement(where.req_id), ctx.bindings.get(where.req_id),
            f"changes {f['old']!r} to {f['new']!r} in {f['unit']}", f["old"],
        )


class DropCharFormat(Operator):
    name = "docx.viol.drop_char_format"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("text_run",)
    description = "Remove bold, italic, underline, colour or highlight from a bound run."

    def sites(self, ctx, req, binding):
        out = []
        for unit in bound_paragraphs(ctx, binding):
            block = paragraph(ctx.base, unit)
            effective = docx_effective(ctx.base, block)["spans"]
            for start, end, props in _offsets(effective):
                for attr, (key, on, _p) in _CHAR_ATTRS.items():
                    if on(props.get(key)) and end > start:
                        out.append(site(unit, req.req_id, attr=attr, start=start, end=end))
        return out

    def build(self, ctx, where, rng):
        info = where.info
        block = paragraph(ctx.base, where.unit)
        return Build(
            steps=[{"op": "docx.set_char_props", **address(where.unit), "start": info["start"],
                    "end": info["end"], "expect_sha256": text_sha256(block["text"]),
                    "props": _CHAR_ATTRS[info["attr"]][2]}],
            expectation=Expectation(
                allow=[f"{where.unit}/spans"],
                must_change=[f"{where.unit}/spans"],
                preserve=[f"{where.unit}/text"],
            ),
            facts={"unit": where.unit, "attr": info["attr"],
                   "text": block["text"][info["start"]:info["end"]]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), (f["attr"],),
            f"removes {f['attr']} from {f['text']!r}", ctx.bindings.get(where.req_id),
        )


def _offsets(spans: list) -> list[tuple[int, int, dict]]:
    out = []
    pos = 0
    for text, props in spans:
        out.append((pos, pos + len(text), props))
        pos += len(text)
    return out


_ALIGN = {"left": ("left", "start"), "center": ("center",), "right": ("right", "end"),
          "block": ("both", "distribute")}


class ParaAlignChange(Operator):
    name = "docx.viol.para_align_change"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("paragraph_format",)
    description = "Change a bound paragraph's alignment."

    def sites(self, ctx, req, binding):
        return [site(u, req.req_id) for u in bound_paragraphs(ctx, binding)]

    def build(self, ctx, where, rng):
        block = paragraph(ctx.base, where.unit)
        jc = docx_effective(ctx.base, block)["ppr"].get("jc")
        current = (jc or {}).get("attrs", {}).get("val", "left") if isinstance(jc, dict) else "left"
        options = [name for name, vals in _ALIGN.items() if current not in vals]
        new = rng.choice(options)
        return Build(
            steps=[{"op": "docx.set_para_props", **address(where.unit),
                    "expect_sha256": text_sha256(block["text"]), "props": {"adjust": new}}],
            expectation=Expectation(
                allow=[f"{where.unit}/ppr", f"{where.unit}/ppr/*"],
                must_change=[f"{where.unit}/ppr*"],
                preserve=[f"{where.unit}/text"],
            ),
            facts={"unit": where.unit, "before": current, "after": new},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), ("alignment",),
            f"changes the alignment of {f['unit']} from {f['before']} to {f['after']}",
            ctx.bindings.get(where.req_id),
        )


class LineSpacingChange(Operator):
    name = "docx.viol.line_spacing_change"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("paragraph_format",)
    description = "Change a bound paragraph's proportional line spacing."

    def sites(self, ctx, req, binding):
        return [site(u, req.req_id) for u in bound_paragraphs(ctx, binding)]

    def build(self, ctx, where, rng):
        block = paragraph(ctx.base, where.unit)
        spacing = docx_effective(ctx.base, block)["ppr"].get("spacing")
        attrs = spacing.get("attrs", {}) if isinstance(spacing, dict) else {}
        current = None
        if attrs.get("lineRule", "auto") == "auto" and attrs.get("line"):
            current = round(int(attrs["line"]) / 240 * 100)
        new = rng.choice([v for v in (100, 150, 200) if v != (current or 100)])
        return Build(
            steps=[{"op": "docx.set_para_props", **address(where.unit),
                    "expect_sha256": text_sha256(block["text"]),
                    "props": {"line_spacing": {"mode": "prop", "value": new}}}],
            expectation=Expectation(
                allow=[f"{where.unit}/ppr", f"{where.unit}/ppr/*"],
                must_change=[f"{where.unit}/ppr*"],
                preserve=[f"{where.unit}/text"],
            ),
            facts={"unit": where.unit, "before": current, "after": new},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), ("spacing",),
            f"sets the line spacing of {f['unit']} to {f['after']}% (was {f['before']})",
            ctx.bindings.get(where.req_id),
        )


class DeleteBoundParagraph(Operator):
    name = "docx.viol.delete_bound_paragraph"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("text_run", "paragraph_format")
    description = "Delete a bound, non-empty top-level paragraph."

    def sites(self, ctx, req, binding):
        return [
            site(u, req.req_id) for u in bound_paragraphs(ctx, binding)
            if u.count("/") == 1 and deletable(ctx.base, u)
        ]

    def build(self, ctx, where, rng):
        block = paragraph(ctx.base, where.unit)
        if len(ctx.base["body"]) < 2:
            raise OperatorError("cannot delete the only paragraph")
        return Build(
            steps=[{"op": "docx.delete_block", **address(where.unit),
                    "expect_sha256": text_sha256(block["text"])}],
            expectation=Expectation(allow=[where.unit], must_change=[where.unit]),
            facts={"unit": where.unit, "text": block["text"][:80]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), (),
            f"deletes the paragraph {f['text']!r}", ctx.bindings.get(where.req_id),
            implied_by_kind=("text_run", "paragraph_format"),
        )


# --------------------------------------------------------------------------- F


class EditUnrelatedParagraph(Operator):
    name = "docx.extra.edit_unrelated_paragraph"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    description = "Change one letter of a word in a paragraph no requirement reads."

    def sites(self, ctx, req, binding):
        return [site(u) for u in outside_paragraphs(ctx, top_level=True)]

    def build(self, ctx, where, rng):
        return text_edit_build(ctx, where.unit, rng, [])

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(ctx, (), f"changes {f['old']!r} to {f['new']!r} in the unrelated "
                           f"paragraph {f['unit']}", harmful=True)


class DeleteUnrelatedParagraph(Operator):
    name = "docx.extra.delete_unrelated_paragraph"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    description = "Delete a non-empty paragraph no requirement reads."

    def sites(self, ctx, req, binding):
        if len(ctx.base["body"]) < 2:
            return []
        return [site(u) for u in outside_paragraphs(ctx, top_level=True)
                if deletable(ctx.base, u)]

    def build(self, ctx, where, rng):
        block = paragraph(ctx.base, where.unit)
        return Build(
            steps=[{"op": "docx.delete_block", **address(where.unit),
                    "expect_sha256": text_sha256(block["text"])}],
            expectation=Expectation(allow=[where.unit], must_change=[where.unit]),
            facts={"unit": where.unit, "text": block["text"][:80]},
        )

    def judge(self, ctx, where, built):
        return judge_extra(ctx, (), f"deletes the unrelated paragraph {built.facts['text']!r}",
                           harmful=True)


class EditUnrelatedTableCell(Operator):
    name = "docx.extra.edit_unrelated_table_cell"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    provenance = "probe_informed"
    description = "Change one letter of a word in a table cell no requirement reads."

    def sites(self, ctx, req, binding):
        out = []
        for unit in outside_paragraphs(ctx, top_level=False):
            table = resolve(ctx.base, "/".join(unit.split("/")[:2]))
            if not table.get("merged"):
                out.append(site(unit))
        return out

    def build(self, ctx, where, rng):
        return text_edit_build(ctx, where.unit, rng, [])

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(ctx, (), f"changes {f['old']!r} to {f['new']!r} in the unrelated "
                           f"table cell {f['unit']}", harmful=True)


class FormatUnrelatedRun(Operator):
    name = "docx.extra.format_unrelated_run"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    aspects = ("bold",)
    description = "Make one word of an unrelated paragraph bold."

    def sites(self, ctx, req, binding):
        return [site(u) for u in outside_paragraphs(ctx, top_level=True)]

    def build(self, ctx, where, rng):
        block = paragraph(ctx.base, where.unit)
        candidates = [
            (start, end) for start, end, props in _offsets(
                docx_effective(ctx.base, block)["spans"]
            )
            if props.get("b") is not True
        ]
        words = [m.span() for m in re.finditer(r"[A-Za-z]{3,}", block["text"])
                 if any(s <= m.start() and m.end() <= e for s, e in candidates)]
        if not words:
            raise OperatorError("no non-bold word")
        start, end = rng.choice(words)
        return Build(
            steps=[{"op": "docx.set_char_props", **address(where.unit), "start": start,
                    "end": end, "expect_sha256": text_sha256(block["text"]),
                    "props": {"bold": True}}],
            expectation=Expectation(
                allow=[f"{where.unit}/spans"],
                must_change=[f"{where.unit}/spans"],
                preserve=[f"{where.unit}/text"],
            ),
            facts={"unit": where.unit, "word": block["text"][start:end]},
        )

    def judge(self, ctx, where, built):
        return judge_extra(ctx, self.aspects,
                           f"makes {built.facts['word']!r} bold in an unrelated paragraph",
                           harmful=False)


OPERATORS: tuple[type[Operator], ...] = (
    DocProperty,
    ViewZoom,
    CharStyleForDirect,
    ParaDirectForStyle,
    HighlightAsShading,
    CaseViaFormat,
    TextEdit,
    DropCharFormat,
    ParaAlignChange,
    LineSpacingChange,
    DeleteBoundParagraph,
    EditUnrelatedParagraph,
    DeleteUnrelatedParagraph,
    EditUnrelatedTableCell,
    FormatUnrelatedRun,
)
