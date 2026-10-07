"""Presentation (pptx, LibreOffice Impress) mutation operators.

Shape units are ``slides/<s>/shapes/<k>`` (top-level shapes in z-order) and
table cells ``slides/<s>/shapes/<k>/table/rows/<r>/<c>``. ``uno_apply.py``
addresses the same shape as draw page ``s``, index ``k`` and checks the
shape text against ``expect_sha256`` (a digest of the expected text) before editing.
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
    judge_equivalence,
    judge_extra,
    judge_violation,
    site,
)
from harness.q2_mutation.operators._common import (
    DocPropertyOperator,
    choose_word_edit,
    judge_text_edit,
    neutral_phrase,
    perturb_word,
    text_sha256,
)
from harness.q2_mutation.operators._diff import resolve
from harness.q2_mutation.operators._purity import Expectation
from harness.q2_mutation.operators._spec import (
    Binding,
    mentions,
    pptx_shapes,
    quoted,
    req_text,
)

FAMILY = "pptx"
EMU_PER_HMM = 360  # LibreOffice positions are in 1/100 mm
NUDGE_EMU = EMU_PER_HMM
MOVE_EMU = 540_000  # 1.5 cm
TEXT_PLACEHOLDERS = {"title", "ctrTitle", "subTitle", "body", "obj"}


def shape_address(unit: str) -> dict:
    parts = unit.split("/")
    if len(parts) < 4 or parts[0] != "slides" or parts[2] != "shapes":
        raise OperatorError(f"not a shape unit: {unit}")
    out = {"slide": int(parts[1]), "shape": int(parts[3])}
    if len(parts) == 8 and parts[4] == "table" and parts[5] == "rows":
        out["cell"] = [int(parts[6]), int(parts[7])]
    return out


def shape_unit(unit: str) -> str:
    return "/".join(unit.split("/")[:4])


def movable(shape: dict) -> bool:
    """Has an explicit offset and no rotation or flip (LibreOffice positions a rotated
    shape by its bounding box, so a move does not map one-to-one onto the offset)."""
    if not shape.get("off"):
        return False
    rotated = shape.get("rot") not in (None, "0")
    flipped = any(shape.get(k) in {"1", "true"} for k in ("flipH", "flipV"))
    return not rotated and not flipped


def get_shape(snap: dict, unit: str) -> dict:
    return resolve(snap, shape_unit(unit))


def bound_shapes(ctx: Context, binding: Binding | None, with_text: bool = False) -> list[str]:
    if binding is None:
        return []
    out = []
    for unit in binding.units:
        parts = unit.split("/")
        if len(parts) == 4 and parts[2] == "shapes":
            shape = get_shape(ctx.base, unit)
            if not with_text or (shape.get("text") or "").strip():
                out.append(unit)
        elif len(parts) == 2 and parts[0] == "slides":
            slide = ctx.base["slides"][int(parts[1])]
            for k, shape in enumerate(slide["shapes"]):
                if not with_text or (shape.get("text") or "").strip():
                    out.append(f"{unit}/shapes/{k}")
    return out


def outside_shapes(ctx: Context, with_text: bool = True) -> list[str]:
    return [
        path for path, shape in pptx_shapes(ctx.base)
        if ctx.is_outside(path) and (not with_text or (shape.get("text") or "").strip())
        and shape["kind"] in {"sp", "table"}
    ]


def para_word_edit(shape: dict, rng, prefer: list[str]) -> tuple[int, int, int, str, str, bool]:
    paras = [
        i for i, p in enumerate(shape.get("paras", [])) if re.search(r"[A-Za-z]{3}", p["text"])
    ]
    if not paras:
        raise OperatorError("no editable word")
    hinted = [i for i in paras if any(h.strip() and h.strip() in shape["paras"][i]["text"]
                                      for h in prefer)]
    index = rng.choice(hinted or paras)
    choice = choose_word_edit(shape["paras"][index]["text"], rng, prefer)
    if choice is None:
        raise OperatorError("no editable word")
    start, end, old, new, inside = choice
    return index, start, end, old, new, inside


def shape_text_build(ctx: Context, unit: str, rng, prefer: list[str]) -> Build:
    shape = get_shape(ctx.base, unit)
    index, start, end, old, new, inside = para_word_edit(shape, rng, prefer)
    paras = [p["text"] for p in shape["paras"]]
    paras[index] = paras[index][:start] + new + paras[index][end:]
    new_text = "\n".join(paras)
    return Build(
        steps=[{"op": "pptx.replace_text", **shape_address(unit), "para": index,
                "start": start, "end": end, "new": new,
                "expect_sha256": text_sha256(shape["text"])}],
        expectation=Expectation(
            allow=[f"{unit}/text", f"{unit}/paras/*"],
            must_change=[f"{unit}/text"],
            must_equal=[(f"{unit}/text", new_text)],
        ),
        facts={"unit": unit, "old": old, "new": new, "inside_hint": inside},
    )


# --------------------------------------------------------------------------- E


class DocProperty(DocPropertyOperator):
    name = "pptx.eq.doc_property"
    family = FAMILY
    description = "Set the presentation's Title, Subject or Keywords property."


class SubvisibleNudge(Operator):
    name = "pptx.eq.subvisible_nudge"
    family = FAMILY
    label_class = EQUIV
    target = "document"
    aspects = ("exact_geometry",)
    description = "Move a shape by 0.01 mm, far below what a viewer can see."

    def sites(self, ctx, req, binding):
        return [site(path) for path, shape in pptx_shapes(ctx.base)
                if movable(shape) and shape["kind"] in {"sp", "pic", "table"}][:200]

    def build(self, ctx, where, rng):
        shape = get_shape(ctx.base, where.unit)
        return Build(
            steps=[{"op": "pptx.move_shape", **shape_address(where.unit), "dx_emu": NUDGE_EMU,
                    "dy_emu": 0, "expect_sha256": text_sha256(shape.get("text", ""))}],
            expectation=Expectation(
                allow=[f"{where.unit}/off"],
                must_change=[f"{where.unit}/off"],
                deltas=[(f"{where.unit}/off", [NUDGE_EMU, 0])],
            ),
            facts={"unit": where.unit, "name": shape.get("name", "")},
        )

    def judge(self, ctx, where, built):
        return judge_equivalence(
            ctx, self.aspects,
            f"moves shape {built.facts['name']!r} right by 0.01 mm (one LibreOffice unit), "
            "which no viewer can see",
        )


def _box(shape: dict) -> tuple[int, int, int, int] | None:
    if not shape.get("off") or not shape.get("ext"):
        return None
    x, y = shape["off"]
    cx, cy = shape["ext"]
    return x, y, x + cx, y + cy


def _overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


class ZOrderNonOverlap(Operator):
    name = "pptx.eq.zorder_nonoverlap"
    family = FAMILY
    label_class = EQUIV
    target = "document"
    aspects = ("z_order",)
    description = "Swap the stacking order of two shapes that do not overlap."

    def sites(self, ctx, req, binding):
        out = []
        for s, slide in enumerate(ctx.base["slides"]):
            shapes = slide["shapes"]
            for a in range(len(shapes)):
                for b in range(a + 1, len(shapes)):
                    box_a, box_b = _box(shapes[a]), _box(shapes[b])
                    if box_a and box_b and not _overlap(box_a, box_b):
                        out.append(site(f"slides/{s}/shapes", slide=s, a=a, b=b))
        return out[:200]

    def build(self, ctx, where, rng):
        info = where.info
        shapes = ctx.base["slides"][info["slide"]]["shapes"]
        loc = f"slides/{info['slide']}/shapes"
        return Build(
            steps=[{"op": "pptx.swap_z", "slide": info["slide"], "a": info["a"], "b": info["b"],
                    "expect_sha256": [text_sha256(shapes[info["a"]].get("text", "")),
                                       text_sha256(shapes[info["b"]].get("text", ""))]}],
            expectation=Expectation(
                allow=[f"{loc}/*"],
                must_change=[f"{loc}/*"],
                same_items=[loc],
                forbid_kinds=[],
            ),
            facts={"slide": info["slide"], "a": shapes[info["a"]].get("name", ""),
                   "b": shapes[info["b"]].get("name", "")},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_equivalence(
            ctx, self.aspects,
            f"swaps the stacking order of {f['a']!r} and {f['b']!r} on slide {f['slide'] + 1}, "
            "which do not overlap, so the rendered slide is identical",
        )


# --------------------------------------------------------------------------- A


class TextboxForPlaceholder(Operator):
    name = "pptx.alt.textbox_for_placeholder"
    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("text_run", "slide_object")
    aspects = ("style",)
    description = (
        "Replace a bound text placeholder with a plain text box holding the same text at the "
        "same position, size and character formatting."
    )

    def sites(self, ctx, req, binding):
        out = []
        for unit in bound_shapes(ctx, binding, with_text=True):
            shape = get_shape(ctx.base, unit)
            ph = shape.get("placeholder") or {}
            if ph.get("type") in TEXT_PLACEHOLDERS and shape.get("off") and shape.get("ext"):
                out.append(site(unit, req.req_id))
        return out

    def build(self, ctx, where, rng):
        shape = get_shape(ctx.base, where.unit)
        address = shape_address(where.unit)
        slide = address["slide"]
        count = len(ctx.base["slides"][slide]["shapes"])
        new_loc = f"slides/{slide}/shapes/{count - 1}"
        return Build(
            steps=[
                {"op": "pptx.add_textbox", "slide": slide, "x_emu": shape["off"][0],
                 "y_emu": shape["off"][1], "w_emu": shape["ext"][0], "h_emu": shape["ext"][1],
                 "paras": [p["text"] for p in shape["paras"]],
                 "copy_format_from": address["shape"], "expect_sha256": text_sha256(shape["text"])},
                {"op": "pptx.delete_shape", **address, "expect_sha256": text_sha256(shape["text"])},
            ],
            expectation=Expectation(
                allow=[f"slides/{slide}/shapes/*"],
                must_change=[where.unit, f"slides/{slide}/shapes/+*"],
                must_equal=[(f"{new_loc}/text", shape["text"]),
                            (f"{new_loc}/off", shape["off"]),
                            (f"{new_loc}/ext", shape["ext"])],
                int_tolerance=2 * EMU_PER_HMM,
            ),
            facts={"unit": where.unit, "placeholder": shape["placeholder"]["type"],
                   "text": shape["text"][:80]},
        )

    def judge(self, ctx, where, built):
        req = ctx.requirement(where.req_id)
        f = built.facts
        change = (
            f"replaces the {f['placeholder']} placeholder holding {f['text']!r} with a plain "
            "text box with the same text, position and size"
        )
        allowed = _allowed_placeholder(ctx)
        pinned = re.findall(r"placeholder|\blayout\b|outline", req_text(req), re.IGNORECASE)
        if allowed:
            return Judgement(ALT, f"W-A-ALLOWED: {change}; the spec leaves the mechanism open "
                             f"({allowed}).", "W-A-ALLOWED", (req.req_id,))
        if pinned:
            return Judgement(VIOLATION, f"W-A-PINNED: {change}; {req.req_id} mentions "
                             f"{sorted(set(pinned))}.", "W-A-PINNED", (req.req_id,))
        return Judgement(
            AMBIGUOUS,
            f"W-A-STRUCTURE: {change}; the slide looks the same but loses its title/body "
            f"placeholder (outline view, accessibility); {req.req_id} does not say which counts.",
            "W-A-STRUCTURE",
            (req.req_id,),
        )


def _allowed_placeholder(ctx: Context) -> list[str]:
    return [
        f"allowed_variations[{i}] {text!r}"
        for i, text in enumerate(ctx.spec.allowed_variations)
        if re.search(r"text ?box|placeholder", text, re.IGNORECASE)
    ]


_UPPER_SEGMENT = re.compile(r"[A-Z][A-Z ]{3,}[A-Z]")


class CaseViaFormat(Operator):
    name = "pptx.alt.case_via_format"
    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("text_run",)
    aspects = ("case",)
    description = (
        "Retype an upper-case run in lower case and apply the UPPERCASE case effect."
    )

    def sites(self, ctx, req, binding):
        out = []
        for unit in bound_shapes(ctx, binding, with_text=True):
            for p, para in enumerate(get_shape(ctx.base, unit).get("paras", [])):
                for match in _UPPER_SEGMENT.finditer(para["text"]):
                    out.append(site(unit, req.req_id, para=p, start=match.start(),
                                    end=match.end()))
        return out

    def build(self, ctx, where, rng):
        info = where.info
        shape = get_shape(ctx.base, where.unit)
        paras = [p["text"] for p in shape["paras"]]
        old = paras[info["para"]][info["start"]:info["end"]]
        new = old.lower()
        paras[info["para"]] = (
            paras[info["para"]][: info["start"]] + new + paras[info["para"]][info["end"]:]
        )
        new_text = "\n".join(paras)
        address = shape_address(where.unit)
        return Build(
            steps=[
                {"op": "pptx.replace_text", **address, "para": info["para"],
                 "start": info["start"], "end": info["end"], "new": new,
                 "expect_sha256": text_sha256(shape["text"])},
                {"op": "pptx.set_char_props", **address, "para": info["para"],
                 "start": info["start"], "end": info["start"] + len(new),
                 "expect_sha256": text_sha256(new_text), "props": {"case_map": "upper"}},
            ],
            expectation=Expectation(
                allow=[f"{where.unit}/text", f"{where.unit}/paras/*"],
                must_change=[f"{where.unit}/text", f"{where.unit}/paras/*"],
                must_equal=[(f"{where.unit}/text", new_text)],
            ),
            facts={"unit": where.unit, "old": old, "new": new},
        )

    def judge(self, ctx, where, built):
        from harness.q2_mutation.operators.docx import judge_case_via_format

        return judge_case_via_format(ctx, ctx.requirement(where.req_id), built.facts)


# --------------------------------------------------------------------------- R


class TextEdit(Operator):
    name = "pptx.viol.text_edit"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("text_run", "slide_object", "other")
    description = "Change one letter of a word in a bound shape (preferring quoted text)."

    def sites(self, ctx, req, binding):
        return [site(u, req.req_id) for u in bound_shapes(ctx, binding, with_text=True)
                if get_shape(ctx.base, u)["kind"] == "sp"]

    def build(self, ctx, where, rng):
        return shape_text_build(ctx, where.unit, rng,
                                quoted(req_text(ctx.requirement(where.req_id))))

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_text_edit(
            ctx.requirement(where.req_id), ctx.bindings.get(where.req_id),
            f"changes {f['old']!r} to {f['new']!r} in {f['unit']}", f["old"],
        )


class TableCellText(Operator):
    name = "pptx.viol.table_cell_text"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("table_cell", "text_run", "slide_object")
    provenance = "probe_informed"
    description = "Change one letter of a word in a bound table cell."

    def sites(self, ctx, req, binding):
        out = []
        units = list(binding.units) if binding else []
        for unit in units:
            parts = unit.split("/")
            if len(parts) == 8 and parts[4] == "table":
                table = get_shape(ctx.base, unit).get("table") or {}
                cell = table["rows"][int(parts[6])][int(parts[7])]
                if re.search(r"[A-Za-z]{3}", cell["text"]) and not table.get("merged"):
                    out.append(site(unit, req.req_id))
        for unit in bound_shapes(ctx, binding):
            table = get_shape(ctx.base, unit).get("table")
            if not table or table.get("merged"):
                continue
            for r, row in enumerate(table["rows"]):
                for c, cell in enumerate(row):
                    if re.search(r"[A-Za-z]{3}", cell["text"]):
                        out.append(site(f"{unit}/table/rows/{r}/{c}", req.req_id))
        return out

    def build(self, ctx, where, rng):
        parts = where.unit.split("/")
        r, c = int(parts[6]), int(parts[7])
        cell = get_shape(ctx.base, where.unit)["table"]["rows"][r][c]
        lines = cell["text"].split("\n")
        candidates = [i for i, line in enumerate(lines) if re.search(r"[A-Za-z]{3}", line)]
        para = rng.choice(candidates)
        choice = choose_word_edit(lines[para], rng,
                                  quoted(req_text(ctx.requirement(where.req_id))))
        if choice is None:
            raise OperatorError("no editable word")
        start, end, old, new, _inside = choice
        lines[para] = lines[para][:start] + new + lines[para][end:]
        new_text = "\n".join(lines)
        return Build(
            steps=[{"op": "pptx.replace_text", **shape_address(where.unit), "para": para,
                    "start": start, "end": end, "new": new,
                    "expect_sha256": text_sha256(cell["text"])}],
            expectation=Expectation(
                allow=[f"{where.unit}/text", f"{where.unit}/spans"],
                must_change=[f"{where.unit}/text"],
                must_equal=[(f"{where.unit}/text", new_text)],
            ),
            facts={"unit": where.unit, "old": old, "new": new},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_text_edit(
            ctx.requirement(where.req_id), ctx.bindings.get(where.req_id),
            f"changes {f['old']!r} to {f['new']!r} in table cell {f['unit']}", f["old"],
        )


_CHAR_ATTRS = {
    "bold": ("b", lambda v: v is True, {"bold": False}),
    "italic": ("i", lambda v: v is True, {"italic": False}),
    "underline": ("u", lambda v: v not in (None, "none"), {"underline": False}),
    "color": ("color", lambda v: v is not None, {"color": None}),
}


class DropCharFormat(Operator):
    name = "pptx.viol.drop_char_format"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("text_run",)
    description = "Remove direct bold, italic, underline or colour from a bound run."

    def sites(self, ctx, req, binding):
        out = []
        for unit in bound_shapes(ctx, binding, with_text=True):
            for p, para in enumerate(get_shape(ctx.base, unit).get("paras", [])):
                pos = 0
                for text, props in para["spans"]:
                    for attr, (key, on, _props) in _CHAR_ATTRS.items():
                        if on(props.get(key)) and text.strip():
                            out.append(site(unit, req.req_id, attr=attr, para=p, start=pos,
                                            end=pos + len(text)))
                    pos += len(text)
        return out

    def build(self, ctx, where, rng):
        info = where.info
        shape = get_shape(ctx.base, where.unit)
        return Build(
            steps=[{"op": "pptx.set_char_props", **shape_address(where.unit),
                    "para": info["para"], "start": info["start"], "end": info["end"],
                    "expect_sha256": text_sha256(shape["text"]),
                    "props": _CHAR_ATTRS[info["attr"]][2]}],
            expectation=Expectation(
                allow=[f"{where.unit}/paras/*"],
                must_change=[f"{where.unit}/paras/{info['para']}/spans"],
                preserve=[f"{where.unit}/text"],
            ),
            facts={"unit": where.unit, "attr": info["attr"],
                   "text": shape["paras"][info["para"]]["text"][info["start"]:info["end"]]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), (f["attr"],), f"removes {f['attr']} from {f['text']!r}",
            ctx.bindings.get(where.req_id),
        )


class MoveShape(Operator):
    name = "pptx.viol.move_shape"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("slide_object",)
    description = "Move a bound shape by 1.5 cm."

    def sites(self, ctx, req, binding):
        return [site(u, req.req_id) for u in bound_shapes(ctx, binding)
                if movable(get_shape(ctx.base, u))]

    def build(self, ctx, where, rng):
        shape = get_shape(ctx.base, where.unit)
        x, y = shape["off"]
        width = int((ctx.base.get("slide_size") or [9_144_000, 6_858_000])[0])
        dx = MOVE_EMU if x + shape.get("ext", [0, 0])[0] + MOVE_EMU <= width else -MOVE_EMU
        dy = rng.choice([0, MOVE_EMU, -MOVE_EMU]) if y >= MOVE_EMU else rng.choice([0, MOVE_EMU])
        return Build(
            steps=[{"op": "pptx.move_shape", **shape_address(where.unit), "dx_emu": dx,
                    "dy_emu": dy, "expect_sha256": text_sha256(shape.get("text", ""))}],
            expectation=Expectation(
                allow=[f"{where.unit}/off"],
                must_change=[f"{where.unit}/off"],
                deltas=[(f"{where.unit}/off", [dx, dy])],
            ),
            facts={"unit": where.unit, "dx_cm": dx / 360_000, "dy_cm": dy / 360_000},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), ("position",),
            f"moves {f['unit']} by ({f['dx_cm']:+.1f} cm, {f['dy_cm']:+.1f} cm)",
            ctx.bindings.get(where.req_id),
        )


class DeleteBoundShape(Operator):
    name = "pptx.viol.delete_bound_shape"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("slide_object", "text_run")
    description = "Delete a bound shape."

    def sites(self, ctx, req, binding):
        return [site(u, req.req_id) for u in bound_shapes(ctx, binding)]

    def build(self, ctx, where, rng):
        shape = get_shape(ctx.base, where.unit)
        return Build(
            steps=[{"op": "pptx.delete_shape", **shape_address(where.unit),
                    "expect_sha256": text_sha256(shape.get("text", ""))}],
            expectation=Expectation(allow=[where.unit], must_change=[where.unit]),
            facts={"unit": where.unit, "name": shape.get("name", "")},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), (), f"deletes the bound shape {f['name']!r}",
            ctx.bindings.get(where.req_id), implied_by_kind=("slide_object", "text_run"),
        )


# --------------------------------------------------------------------------- F


class EditUnrelatedText(Operator):
    name = "pptx.extra.edit_unrelated_text"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    description = "Change one letter of a word in a shape no requirement reads."

    def sites(self, ctx, req, binding):
        return [site(u) for u in outside_shapes(ctx) if get_shape(ctx.base, u)["kind"] == "sp"]

    def build(self, ctx, where, rng):
        return shape_text_build(ctx, where.unit, rng, [])

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(ctx, (), f"changes {f['old']!r} to {f['new']!r} in the unrelated "
                           f"shape {f['unit']}", harmful=True)


def outside_slides(ctx: Context) -> list[int]:
    out = []
    for s, slide in enumerate(ctx.base["slides"]):
        unit = f"slides/{s}"
        if not ctx.is_outside(unit):
            continue
        if any(re.search(rf"\bslide\s+{s + 1}\b", req_text(r), re.IGNORECASE)
               for r in ctx.spec.requirements):
            continue
        if any((shape.get("text") or "").strip() for shape in slide["shapes"]):
            out.append(s)
    return out


class DeleteUnrelatedSlide(Operator):
    name = "pptx.extra.delete_unrelated_slide"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    aspects = ("slide_set",)
    description = "Delete a slide with content that no requirement reads."

    def sites(self, ctx, req, binding):
        if len(ctx.base["slides"]) < 2:
            return []
        return [site(f"slides/{s}", slide=s) for s in outside_slides(ctx)]

    def build(self, ctx, where, rng):
        s = where.info["slide"]
        return Build(
            steps=[{"op": "pptx.delete_slide", "slide": s,
                    "expect_shapes": len(ctx.base["slides"][s]["shapes"])}],
            expectation=Expectation(allow=[f"slides/{s}"], must_change=[f"slides/{s}"]),
            facts={"slide": s + 1},
        )

    def judge(self, ctx, where, built):
        return judge_extra(ctx, (), f"deletes slide {built.facts['slide']}, which no "
                           "requirement reads", harmful=True)


class AddTextbox(Operator):
    name = "pptx.extra.add_textbox"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    description = "Add a stray text box with unrequested text to a slide."

    def sites(self, ctx, req, binding):
        return [site(f"slides/{s}", slide=s) for s in range(len(ctx.base["slides"]))
                if ctx.is_outside(f"slides/{s}")] or [
            site(f"slides/{s}", slide=s) for s in range(len(ctx.base["slides"]))
        ]

    def build(self, ctx, where, rng):
        s = where.info["slide"]
        text = neutral_phrase(rng, 3).capitalize()
        width, height = (int(v) for v in (ctx.base.get("slide_size") or [9_144_000, 6_858_000]))
        box_w, box_h = 2_880_000, 540_000
        x = rng.randrange(0, max(1, width - box_w), EMU_PER_HMM * 100)
        y = (height - box_h - 180_000) // EMU_PER_HMM * EMU_PER_HMM
        count = len(ctx.base["slides"][s]["shapes"])
        return Build(
            steps=[{"op": "pptx.add_textbox", "slide": s, "x_emu": x, "y_emu": y,
                    "w_emu": box_w, "h_emu": box_h, "paras": [text]}],
            expectation=Expectation(
                allow=[f"slides/{s}/shapes/+*"],
                must_change=[f"slides/{s}/shapes/+*"],
                must_equal=[(f"slides/{s}/shapes/{count}/text", text)],
            ),
            facts={"slide": s + 1, "text": text},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(ctx, (), f"adds an unrequested text box {f['text']!r} to slide "
                           f"{f['slide']}", harmful=True)


class EditNotes(Operator):
    name = "pptx.extra.edit_notes"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    aspects = ("notes",)
    description = "Change or add speaker notes on a slide no requirement reads."

    def sites(self, ctx, req, binding):
        if any(mentions(req_text(r), "notes") for r in ctx.spec.requirements):
            return []
        return [site(f"slides/{s}/notes", slide=s) for s in range(len(ctx.base["slides"]))
                if ctx.is_outside(f"slides/{s}")]

    def build(self, ctx, where, rng):
        s = where.info["slide"]
        notes = ctx.base["slides"][s].get("notes", "")
        words = [m.span() for m in re.finditer(r"[A-Za-z]{3,}", notes)]
        if words:
            start, end = rng.choice(words)
            new = notes[:start] + perturb_word(notes[start:end], rng) + notes[end:]
        else:
            new = neutral_phrase(rng, 3).capitalize()
        loc = f"slides/{s}/notes"
        return Build(
            steps=[{"op": "pptx.set_notes", "slide": s, "text": new,
                    "expect_sha256": text_sha256(notes)}],
            expectation=Expectation(allow=[loc], must_change=[loc], must_equal=[(loc, new)]),
            facts={"slide": s + 1, "had_notes": bool(notes)},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        verb = "edits" if f["had_notes"] else "adds"
        return judge_extra(ctx, self.aspects, f"{verb} the speaker notes of slide {f['slide']}",
                           harmful=False)


OPERATORS: tuple[type[Operator], ...] = (
    DocProperty,
    SubvisibleNudge,
    ZOrderNonOverlap,
    TextboxForPlaceholder,
    CaseViaFormat,
    TextEdit,
    TableCellText,
    DropCharFormat,
    MoveShape,
    DeleteBoundShape,
    EditUnrelatedText,
    DeleteUnrelatedSlide,
    AddTextbox,
    EditNotes,
)
