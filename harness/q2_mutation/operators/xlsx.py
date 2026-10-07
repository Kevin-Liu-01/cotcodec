"""Spreadsheet (xlsx, LibreOffice Calc) mutation operators.

Every recipe is a list of document-model edits that ``uno_apply.py`` performs
through LibreOffice's API on the saved gold, followed by the GUI save path.
Cell units are ``sheets/<sheet>/cells/<A1>`` locators of the base snapshot.
"""

from __future__ import annotations

import random
import re

from harness.q2_mutation.operators import _formula as fx
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
from harness.q2_mutation.operators._common import (
    NON_VIEW_KINDS,
    DocPropertyOperator,
    perturb_word,
)
from harness.q2_mutation.operators._diff import seg, unseg
from harness.q2_mutation.operators._purity import Expectation, xlsx_dependents
from harness.q2_mutation.operators._spec import Binding, Requirement, req_text

FAMILY = "xlsx"


# --------------------------------------------------------------------------- helpers


def cell_unit(sheet: str, address: str) -> str:
    return f"sheets/{seg(sheet)}/cells/{seg(address)}"


def parse_unit(unit: str) -> tuple[str, str]:
    parts = unit.split("/")
    if len(parts) != 4 or parts[0] != "sheets" or parts[2] != "cells":
        raise OperatorError(f"not a cell unit: {unit}")
    return unseg(parts[1]), unseg(parts[3])


def get_cell(snap: dict, unit: str) -> dict:
    sheet, address = parse_unit(unit)
    cell = snap["sheets"].get(sheet, {}).get("cells", {}).get(address)
    if cell is None:
        return {"v": None, "f": None, "style": snap.get("default_style", {})}
    return cell


def bound_cells(binding: Binding | None) -> list[str]:
    if binding is None:
        return []
    return [u for u in binding.units if u.count("/") == 3 and u.startswith("sheets/")]


def all_cells(snap: dict) -> list[str]:
    return [
        cell_unit(sheet, address)
        for sheet, body in snap["sheets"].items()
        for address in sorted(body["cells"], key=lambda a: fx.split_address(a))
    ]


def is_literal(cell: dict) -> bool:
    value = cell.get("v")
    return cell.get("f") is None and value is not None and value[0] in {"n", "s"}


def decimals_shown(cell: dict) -> int:
    """Decimals a user sees for a numeric cell under its number format (approximate)."""
    code = (cell.get("style") or {}).get("numfmt", "General")
    if code in {"General", "@"}:
        value = cell["v"][1]
        if float(value).is_integer():
            return 0
        text = repr(float(value))
        return min(len(text.split(".")[1]), 2) if "." in text and "e" not in text else 2
    section = code.split(";")[0]
    match = re.search(r"0\.(0+)", section)
    decimals = len(match.group(1)) if match else 0
    if "%" in section:
        decimals += 2
    return decimals


def perturbed_value(cell: dict, rng: random.Random) -> list:
    kind, value = cell["v"]
    if kind == "n":
        step = 10.0 ** (-decimals_shown(cell))
        delta = step * rng.choice([1, 2, 3]) * rng.choice([1, -1])
        new = round(float(value) + delta, 10)
        if new == float(value):
            new = float(value) + 1.0
        return ["n", new]
    text = str(value)
    words = [m.span() for m in re.finditer(r"[A-Za-z]{2,}", text)]
    if words:
        start, end = rng.choice(words)
        return ["s", text[:start] + perturb_word(text[start:end], rng) + text[end:]]
    return ["s", text + rng.choice("xyz")]


def set_value_step(sheet: str, address: str, value: list) -> dict:
    return {"op": "xlsx.set_value", "sheet": sheet, "cell": address, "value": value}


def set_formula_step(sheet: str, address: str, formula: str) -> dict:
    return {
        "op": "xlsx.set_formula",
        "sheet": sheet,
        "cell": address,
        "formula": formula,
        "formula_api": fx.to_api_grammar(formula),
    }


def content_expectation(unit: str, **extra) -> Expectation:
    return Expectation(
        allow=[f"{unit}/v", f"{unit}/f"],
        xlsx_dependents_of=[unit],
        **extra,
    )


def feeds_protected(ctx: Context, unit: str) -> bool:
    """True when a formula in the task delta or a requirement binding reads ``unit``."""
    protected = set(ctx.delta) | ctx.bound
    return any(dep.rsplit("/", 1)[0] in protected for dep in xlsx_dependents(ctx.base, [unit]))


def sheet_referenced_elsewhere(snap: dict, sheet: str) -> bool:
    for other, body in snap["sheets"].items():
        if other == sheet:
            continue
        for cell in body["cells"].values():
            formula = cell.get("f") or ""
            if sheet in formula:
                return True
    return any(sheet in name for name in snap["workbook"]["defined_names"])


def _formula_tokens(formula: str) -> list[fx.Token] | None:
    try:
        return [t for t in fx.tokenize(formula) if t.kind != "space"]
    except fx.FormulaError:
        return None


def _formula_cells(ctx: Context, binding: Binding | None, req: Requirement) -> list[str]:
    return [u for u in bound_cells(binding) if get_cell(ctx.base, u).get("f")]


# --------------------------------------------------------------------------- E operators


class DocTitle(DocPropertyOperator):
    name = "xlsx.eq.doc_property"
    family = FAMILY
    description = "Set the workbook's Title, Subject or Keywords property."


class ViewZoom(Operator):
    name = "xlsx.eq.view_zoom"
    family = FAMILY
    label_class = EQUIV
    target = "document"
    aspects = ("zoom",)
    description = "Change one sheet's zoom level (view state saved in the file)."

    def sites(self, ctx, req, binding):
        states = ctx.base["workbook"]["states"]
        return [
            site(f"sheets/{seg(name)}/view", sheet=name)
            for name in ctx.base["workbook"]["sheets"]
            if states.get(name, "visible") == "visible"
        ]

    def build(self, ctx, where, rng):
        sheet = where.info["sheet"]
        current = ctx.base["sheets"][sheet].get("view", {}).get("zoom", 100)
        zoom = rng.choice([z for z in (75, 90, 120, 150) if z != current])
        loc = f"sheets/{seg(sheet)}/view/zoom"
        return Build(
            steps=[{"op": "xlsx.set_view", "sheet": sheet, "zoom": zoom, "restore_active": True}],
            expectation=Expectation(
                allow=["sheets/*/view/*", "book_view/*"],
                must_change=[loc],
                must_equal=[(loc, zoom)],
                forbid_kinds=NON_VIEW_KINDS,
            ),
            facts={"sheet": sheet, "before": current, "after": zoom},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_equivalence(
            ctx, self.aspects, f"changes the zoom of sheet {f['sheet']!r} from {f['before']}% "
            f"to {f['after']}%"
        )


class ViewSelection(Operator):
    name = "xlsx.eq.view_selection"
    family = FAMILY
    label_class = EQUIV
    target = "document"
    aspects = ("selection",)
    description = "Move the cell cursor to another cell of the active sheet."

    def sites(self, ctx, req, binding):
        names = ctx.base["workbook"]["sheets"]
        active = ctx.base["book_view"].get("active_tab", 0)
        if not names or active >= len(names):
            return []
        sheet = names[active]
        current = ctx.base["sheets"][sheet].get("view", {}).get("active_cell", "A1")
        return [
            site(cell_unit(sheet, address), sheet=sheet, cell=address)
            for address in sorted(ctx.base["sheets"][sheet]["cells"])
            if address != current
        ][:50]

    def build(self, ctx, where, rng):
        sheet, address = where.info["sheet"], where.info["cell"]
        loc = f"sheets/{seg(sheet)}/view/active_cell"
        before = ctx.base["sheets"][sheet].get("view", {}).get("active_cell", "A1")
        return Build(
            steps=[{"op": "xlsx.set_view", "sheet": sheet, "select": address,
                    "restore_active": False}],
            expectation=Expectation(
                allow=["sheets/*/view/*", "book_view/*"],
                must_change=[loc],
                must_equal=[(loc, address)],
                forbid_kinds=NON_VIEW_KINDS,
            ),
            facts={"sheet": sheet, "before": before, "after": address},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_equivalence(
            ctx, self.aspects,
            f"moves the cell cursor on {f['sheet']!r} from {f['before']} to {f['after']}",
        )


class ActiveSheet(Operator):
    name = "xlsx.eq.active_sheet"
    family = FAMILY
    label_class = EQUIV
    target = "document"
    aspects = ("active_sheet",)
    description = "Leave a different sheet tab active when the file is saved."

    def sites(self, ctx, req, binding):
        names = ctx.base["workbook"]["sheets"]
        active = ctx.base["book_view"].get("active_tab", 0)
        states = ctx.base["workbook"]["states"]
        return [
            site(f"book_view/{i}", sheet=name, index=i)
            for i, name in enumerate(names)
            if i != active and states.get(name, "visible") == "visible"
        ]

    def build(self, ctx, where, rng):
        return Build(
            steps=[{"op": "xlsx.set_view", "sheet": where.info["sheet"], "activate": True,
                    "restore_active": False}],
            expectation=Expectation(
                allow=["sheets/*/view/*", "book_view/*"],
                must_change=["book_view/active_tab"],
                must_equal=[("book_view/active_tab", where.info["index"])],
                forbid_kinds=NON_VIEW_KINDS,
            ),
            facts={"sheet": where.info["sheet"]},
        )

    def judge(self, ctx, where, built):
        return judge_equivalence(
            ctx, self.aspects, f"leaves sheet {built.facts['sheet']!r} as the active tab"
        )


# --------------------------------------------------------------------------- A operators


class _FormulaRewrite(Operator):
    """Base for A operators that replace a bound formula with an equivalent one."""

    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("cell_value",)
    pinned_patterns: tuple[str, ...] = ()
    mechanism_aspects: tuple[str, ...] = ("function",)

    def rewrite(self, ctx: Context, sheet: str, formula: str) -> str | None:
        raise NotImplementedError

    def sites(self, ctx, req, binding):
        out = []
        for unit in _formula_cells(ctx, binding, req):
            cell = get_cell(ctx.base, unit)
            if cell["v"] is None or cell["v"][0] == "e" or cell["f"].startswith("{"):
                continue
            sheet, _address = parse_unit(unit)
            if self.rewrite(ctx, sheet, cell["f"]) is not None:
                out.append(site(unit, req.req_id))
        return out

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        cell = get_cell(ctx.base, where.unit)
        new = self.rewrite(ctx, sheet, cell["f"])
        if new is None:
            raise OperatorError("formula not rewritable")
        return Build(
            steps=[set_formula_step(sheet, address, new)],
            expectation=content_expectation(
                where.unit,
                must_change=[f"{where.unit}/f"],
                preserve=[f"{where.unit}/v"],
                formulas=[(f"{where.unit}/f", new)],
            ),
            facts={"cell": f"{sheet}!{address}", "before": cell["f"], "after": new,
                   "value": cell["v"]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        req = ctx.requirement(where.req_id)
        return judge_alternative(
            ctx, req, self.mechanism_aspects,
            f"rewrites {f['cell']} from {f['before']} to the equivalent {f['after']} "
            f"(same value {f['value'][1]!r})",
            self.pinned_patterns,
        )


class LiteralForFormula(_FormulaRewrite):
    name = "xlsx.alt.literal_for_formula"
    mechanism_aspects = ("formula",)
    pinned_patterns = (
        r"\b(use|using|with|enter|insert|write|contain|contains)\b[^.]{0,30}\b(formula|function)",
        r"\bformula\b[^.]{0,20}\b(in|into|for)\b",
    )
    description = "Replace a bound formula with the literal value it computes."

    def rewrite(self, ctx, sheet, formula):
        return None  # value replacement handled in build

    def sites(self, ctx, req, binding):
        out = []
        for unit in _formula_cells(ctx, binding, req):
            cell = get_cell(ctx.base, unit)
            literal_value = cell["v"] is not None and cell["v"][0] in {"n", "s"}
            if literal_value and not cell["f"].startswith("{"):
                out.append(site(unit, req.req_id))
        return out

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        cell = get_cell(ctx.base, where.unit)
        return Build(
            steps=[set_value_step(sheet, address, cell["v"])],
            expectation=content_expectation(
                where.unit,
                must_change=[f"{where.unit}/f"],
                must_equal=[(f"{where.unit}/f", None)],
                preserve=[f"{where.unit}/v"],
            ),
            facts={"cell": f"{sheet}!{address}", "before": cell["f"], "after": cell["v"][1],
                   "value": cell["v"]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        req = ctx.requirement(where.req_id)
        return judge_alternative(
            ctx, req, self.mechanism_aspects,
            f"replaces the formula {f['before']} in {f['cell']} with its value {f['after']!r}",
            self.pinned_patterns,
        )


class ReferenceForLiteral(Operator):
    name = "xlsx.alt.reference_for_literal"
    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("cell_value",)
    aspects = ("literal",)
    description = (
        "Replace a bound typed value with a reference to another cell holding the same value."
    )
    pinned_patterns = (r"hard.?cod", r"\bliteral", r"values? only", r"paste[^.]{0,20}values?",
                       r"\btype\b")

    def _source(self, ctx: Context, unit: str) -> str | None:
        target = get_cell(ctx.base, unit)
        for other in all_cells(ctx.base):
            if other == unit:
                continue
            cell = get_cell(ctx.base, other)
            if is_literal(cell) and cell["v"] == target["v"] and ctx.is_outside(other):
                return other
        return None

    def sites(self, ctx, req, binding):
        return [
            site(u, req.req_id)
            for u in bound_cells(binding)
            if is_literal(get_cell(ctx.base, u)) and self._source(ctx, u)
        ]

    def build(self, ctx, where, rng):
        source = self._source(ctx, where.unit)
        if source is None:
            raise OperatorError("no source cell")
        sheet, address = parse_unit(where.unit)
        src_sheet, src_address = parse_unit(source)
        ref = src_address if src_sheet == sheet else fx.ref_text(src_sheet, src_address, None)
        formula = f"={ref}"
        return Build(
            steps=[set_formula_step(sheet, address, formula)],
            expectation=content_expectation(
                where.unit,
                must_change=[f"{where.unit}/f"],
                preserve=[f"{where.unit}/v"],
                formulas=[(f"{where.unit}/f", formula)],
            ),
            facts={"cell": f"{sheet}!{address}", "formula": formula,
                   "value": get_cell(ctx.base, where.unit)["v"]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_alternative(
            ctx, ctx.requirement(where.req_id), self.aspects,
            f"replaces the typed value {f['value'][1]!r} in {f['cell']} with {f['formula']}, "
            "a reference to a cell holding the same value",
            self.pinned_patterns,
        )


def _range_cells(token: fx.Token) -> list[tuple[int, int]] | None:
    try:
        return fx.cells_in_ref(token.first or "", token.last, cap=64)
    except fx.FormulaError:
        return None


def _numeric_or_empty(ctx: Context, sheet: str, cells: list[tuple[int, int]]) -> bool:
    body = ctx.base["sheets"].get(sheet)
    if body is None:
        return False
    values = [body["cells"].get(fx.make_address(r, c), {}).get("v") for r, c in cells]
    return any(v is not None for v in values) and all(v is None or v[0] == "n" for v in values)


class SumRangeExpand(_FormulaRewrite):
    name = "xlsx.alt.sum_range_expand"
    pinned_patterns = (r"\bSUM\s*\(", r"\bSUM\b function", r"function\s+SUM\b",
                       r"\busing\s+SUM\b")
    description = "Rewrite =SUM(A1:A3) as =A1+A2+A3 over a numeric range."

    def rewrite(self, ctx, sheet, formula):
        args = fx.single_call(formula, "SUM")
        if args is None or len(args) != 1 or args[0].kind != "ref" or args[0].last is None:
            return None
        cells = _range_cells(args[0])
        ref_sheet = args[0].sheet or sheet
        if cells is None or not 2 <= len(cells) <= 30:
            return None
        if not _numeric_or_empty(ctx, ref_sheet, cells):
            return None
        prefix = fx.sheet_prefix(args[0].sheet) if args[0].sheet else ""
        return "=" + "+".join(f"{prefix}{fx.make_address(r, c)}" for r, c in cells)


class PlusChainToSum(_FormulaRewrite):
    name = "xlsx.alt.plus_chain_to_sum"
    pinned_patterns = (r"=\s*\$?[A-Z]{1,3}\$?\d+\s*\+",)
    mechanism_aspects = ()
    description = "Rewrite =A1+A2+A3 (a contiguous row or column) as =SUM(A1:A3)."

    def rewrite(self, ctx, sheet, formula):
        tokens = _formula_tokens(formula)
        if not tokens or len(tokens) < 3 or len(tokens) % 2 == 0:
            return None
        refs = tokens[0::2]
        ops = tokens[1::2]
        if any(t.kind != "ref" or t.last is not None for t in refs):
            return None
        if any(t.text != "+" for t in ops) or len({t.sheet for t in refs}) != 1:
            return None
        cells = [fx.split_address((t.first or "").replace("$", "")) for t in refs]
        rows = {r for r, _ in cells}
        cols = {c for _, c in cells}
        ordered = sorted(cells)
        if len(rows) == 1:
            span = [c for _, c in ordered]
        elif len(cols) == 1:
            span = [r for r, _ in ordered]
        else:
            return None
        if span != list(range(span[0], span[0] + len(span))) or ordered != cells:
            return None
        ref_sheet = refs[0].sheet or sheet
        if not _numeric_or_empty(ctx, ref_sheet, cells):
            return None
        first = fx.make_address(*cells[0])
        last = fx.make_address(*cells[-1])
        return f"=SUM({fx.ref_text(refs[0].sheet, first, last)})"


class AverageToSumCount(_FormulaRewrite):
    name = "xlsx.alt.average_to_sum_count"
    pinned_patterns = (r"\bAVERAGE\s*\(", r"\bAVERAGE\b function", r"function\s+AVERAGE\b",
                       r"\busing\s+AVERAGE\b")
    description = "Rewrite =AVERAGE(r) as =SUM(r)/COUNT(r)."

    def rewrite(self, ctx, sheet, formula):
        args = fx.single_call(formula, "AVERAGE")
        if args is None or len(args) != 1 or args[0].kind != "ref" or args[0].last is None:
            return None
        cells = _range_cells(args[0])
        if cells is None or not _numeric_or_empty(ctx, args[0].sheet or sheet, cells):
            return None
        ref = args[0].text
        return f"=SUM({ref})/COUNT({ref})"


class AbsoluteRefs(_FormulaRewrite):
    name = "xlsx.alt.absolute_refs"
    mechanism_aspects = ("references",)
    description = "Anchor every reference of a bound formula with $ (same value)."

    def rewrite(self, ctx, sheet, formula):
        tokens = _formula_tokens(formula)
        if not tokens:
            return None
        refs = [t for t in tokens if t.kind == "ref"]
        if not refs or all("$" in (t.first or "") and "$" in (t.last or "$") for t in refs):
            return None
        try:
            new = fx.absolutize(formula)
        except fx.FormulaError:
            return None
        return new if new != formula else None


class ConcatToAmpersand(_FormulaRewrite):
    name = "xlsx.alt.concat_to_ampersand"
    pinned_patterns = (r"\bCONCATENATE\b", r"\bCONCAT\b")
    description = "Rewrite =CONCATENATE(a,b,...) as =a&b&..."

    def rewrite(self, ctx, sheet, formula):
        args = fx.single_call(formula, "CONCATENATE")
        if args is None:
            return None
        parts = fx.split_args(args)
        if len(parts) < 2 or any(not p for p in parts):
            return None
        rendered = []
        for part in parts:
            text = "".join(t.text for t in part)
            simple = len(part) == 1 and part[0].kind in {"ref", "string", "number"}
            rendered.append(text if simple else f"({text})")
        return "=" + "&".join(rendered)


class NamedStyleForDirect(Operator):
    name = "xlsx.alt.named_style_for_direct"
    family = FAMILY
    label_class = ALT
    target = "requirement"
    check_kinds = ("cell_format",)
    aspects = ("style",)
    description = (
        "Move a bound cell's direct formatting into a new named cell style with the same "
        "properties."
    )

    def sites(self, ctx, req, binding):
        default = ctx.base.get("default_style", {})
        out = []
        for unit in bound_cells(binding):
            style = get_cell(ctx.base, unit)["style"]
            if style.get("style_name") not in {"", "Normal", "Default"}:
                continue
            visible = {k: style.get(k) for k in ("font", "fill", "numfmt", "border")}
            if visible != {k: default.get(k) for k in visible}:
                out.append(site(unit, req.req_id))
        return out

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        name = f"Q2M Style {rng.randrange(1000, 9999)}"
        keep = [f"{where.unit}/style/{k}" for k in ("font", "fill", "numfmt", "border", "align")]
        return Build(
            steps=[{"op": "xlsx.direct_to_named_style", "sheet": sheet, "cell": address,
                    "style_name": name}],
            expectation=Expectation(
                allow=[f"{where.unit}/style/style_name", f"{where.unit}/style/protection/*"],
                must_change=[f"{where.unit}/style/style_name"],
                preserve=keep + [f"{where.unit}/v", f"{where.unit}/f"],
            ),
            facts={"cell": f"{sheet}!{address}", "style_name": name},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_alternative(
            ctx, ctx.requirement(where.req_id), self.aspects,
            f"applies {f['cell']}'s formatting through a new named cell style "
            f"{f['style_name']!r} instead of direct formatting; the resolved font, fill, number "
            "format, border and alignment are unchanged",
            (r"direct(ly)? format",),
        )


# --------------------------------------------------------------------------- R operators


class ValuePerturb(Operator):
    name = "xlsx.viol.value_perturb"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("cell_value",)
    description = "Change a bound typed value by a visible amount (or one letter of a string)."

    def sites(self, ctx, req, binding):
        return [site(u, req.req_id) for u in bound_cells(binding)
                if is_literal(get_cell(ctx.base, u))]

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        cell = get_cell(ctx.base, where.unit)
        new = perturbed_value(cell, rng)
        return Build(
            steps=[set_value_step(sheet, address, new)],
            expectation=content_expectation(
                where.unit, must_change=[f"{where.unit}/v"],
                must_equal=[(f"{where.unit}/v", new)],
            ),
            facts={"cell": f"{sheet}!{address}", "before": cell["v"][1], "after": new[1]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), (),
            f"changes {f['cell']} from {f['before']!r} to {f['after']!r}",
            ctx.bindings.get(where.req_id), implied_by_kind=("cell_value",),
        )


class FormulaRefShift(Operator):
    name = "xlsx.viol.formula_ref_shift"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("cell_value",)
    description = "Shift one reference of a bound formula by one row (an off-by-one error)."

    def sites(self, ctx, req, binding):
        out = []
        for unit in _formula_cells(ctx, binding, req):
            tokens = _formula_tokens(get_cell(ctx.base, unit)["f"].lstrip("{").rstrip("}"))
            if tokens and any(t.kind == "ref" for t in tokens):
                out.append(site(unit, req.req_id))
        return out

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        formula = get_cell(ctx.base, where.unit)["f"]
        if formula.startswith("{"):
            raise OperatorError("array formula")
        tokens = fx.tokenize(formula)
        ref_positions = [i for i, t in enumerate(tokens) if t.kind == "ref"]
        index = rng.choice(ref_positions)
        token = tokens[index]
        endpoint = "last" if token.last and rng.random() < 0.5 else "first"
        cell = token.last if endpoint == "last" else token.first
        row, _col = fx.split_address((cell or "").replace("$", ""))
        drow = 1 if row == 1 or rng.random() < 0.5 else -1
        match = re.fullmatch(r"(\$?[A-Za-z]{1,3}\$?)(\d+)", cell or "")
        if match is None:
            raise OperatorError("unparsable reference")
        moved = f"{match.group(1)}{int(match.group(2)) + drow}"
        first = moved if endpoint == "first" else token.first
        last = moved if endpoint == "last" else token.last
        new_token = fx.Token("ref", fx.ref_text(token.sheet, first or "", last), token.sheet,
                             first, last)
        tokens[index] = new_token
        new = fx.render(tokens)
        return Build(
            steps=[set_formula_step(sheet, address, new)],
            expectation=content_expectation(
                where.unit,
                must_change=[f"{where.unit}/f", f"{where.unit}/v"],
                formulas=[(f"{where.unit}/f", new)],
            ),
            facts={"cell": f"{sheet}!{address}", "before": formula, "after": new},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), (),
            f"changes the formula in {f['cell']} from {f['before']} to {f['after']}, and the "
            "purity check requires the computed value to change",
            ctx.bindings.get(where.req_id), implied_by_kind=("cell_value",),
        )


class ClearBoundCell(Operator):
    name = "xlsx.viol.clear_bound_cell"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("cell_value",)
    description = "Clear the contents of a bound cell."

    def sites(self, ctx, req, binding):
        return [site(u, req.req_id) for u in bound_cells(binding)
                if get_cell(ctx.base, u)["v"] is not None]

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        cell = get_cell(ctx.base, where.unit)
        return Build(
            steps=[{"op": "xlsx.clear_contents", "sheet": sheet, "range": address}],
            expectation=content_expectation(
                where.unit,
                must_change=[f"{where.unit}/v"],
                must_equal=[(f"{where.unit}/v", None), (f"{where.unit}/f", None)],
            ),
            facts={"cell": f"{sheet}!{address}", "before": cell["v"][1]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), (),
            f"clears {f['cell']} (was {f['before']!r})",
            ctx.bindings.get(where.req_id), implied_by_kind=("cell_value",),
        )


_FORMAT_ATTRS = {
    "bold": ("font", "b", True, {"bold": False}),
    "italic": ("font", "i", True, {"italic": False}),
    "underline": ("font", "u", None, {"underline": False}),
    "color": ("font", "color", None, {"color": None}),
}


class DropCharFormat(Operator):
    name = "xlsx.viol.drop_char_format"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("cell_format",)
    description = "Remove bold, italic, underline, font colour or fill from a bound cell."

    def sites(self, ctx, req, binding):
        out = []
        default_font = ctx.base.get("default_style", {}).get("font", {})
        for unit in bound_cells(binding):
            style = get_cell(ctx.base, unit)["style"]
            font = style.get("font", {})
            for attr, (_group, key, on, _props) in _FORMAT_ATTRS.items():
                value = font.get(key)
                set_flag = on is True and value is True
                set_value = (
                    on is None and value not in (None, "none") and value != default_font.get(key)
                )
                if set_flag or set_value:
                    out.append(site(unit, req.req_id, attr=attr))
            if style.get("fill", {}).get("pattern") not in (None, "none"):
                out.append(site(unit, req.req_id, attr="fill"))
        return out

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        attr = where.info["attr"]
        if attr == "fill":
            step = {"op": "xlsx.set_cell_props", "sheet": sheet, "range": address,
                    "props": {"fill": None}}
            touched = [f"{where.unit}/style/fill", f"{where.unit}/style/fill/*"]
            must = f"{where.unit}/style/fill/*"
        else:
            _group, key, _on, props = _FORMAT_ATTRS[attr]
            step = {"op": "xlsx.set_char_props", "sheet": sheet, "range": address,
                    "props": props}
            touched = [f"{where.unit}/style/font/{key}"]
            must = f"{where.unit}/style/font/{key}"
        return Build(
            steps=[step],
            expectation=Expectation(allow=touched, must_change=[must]),
            facts={"cell": f"{sheet}!{address}", "attr": attr},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        aspect = {"bold": "bold", "italic": "italic", "underline": "underline",
                  "color": "color", "fill": "fill"}[f["attr"]]
        return judge_violation(
            ctx.requirement(where.req_id), (aspect,),
            f"removes {f['attr']} from {f['cell']}", ctx.bindings.get(where.req_id),
        )


class NumberFormatChange(Operator):
    name = "xlsx.viol.number_format_change"
    family = FAMILY
    label_class = VIOLATION
    target = "requirement"
    check_kinds = ("cell_format",)
    description = "Change a bound cell's number format so its displayed value changes."

    def sites(self, ctx, req, binding):
        return [
            site(u, req.req_id) for u in bound_cells(binding)
            if (get_cell(ctx.base, u)["v"] or [None])[0] == "n"
        ]

    @staticmethod
    def new_code(code: str) -> str:
        section = code.split(";")[0]
        if "%" in section:
            return "0.00"
        match = re.search(r"0\.(0+)", section)
        if match:
            return section.replace(match.group(0), match.group(0) + "0", 1)
        if re.search(r"[dmyhs]", section, re.IGNORECASE) and code != "General":
            return "0.00"
        if section in {"General", "0", "#,##0"}:
            return "0.000"
        return "General"

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        code = get_cell(ctx.base, where.unit)["style"].get("numfmt", "General")
        new = self.new_code(code)
        loc = f"{where.unit}/style/numfmt"
        return Build(
            steps=[{"op": "xlsx.set_cell_props", "sheet": sheet, "range": address,
                    "props": {"number_format": new}}],
            expectation=Expectation(allow=[loc], must_change=[loc], must_equal=[(loc, new)]),
            facts={"cell": f"{sheet}!{address}", "before": code, "after": new},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_violation(
            ctx.requirement(where.req_id), ("number_format",),
            f"changes the number format of {f['cell']} from {f['before']!r} to {f['after']!r}",
            ctx.bindings.get(where.req_id),
        )


# --------------------------------------------------------------------------- F operators


def outside_literal_cells(ctx: Context) -> list[str]:
    return [
        u for u in all_cells(ctx.base)
        if is_literal(get_cell(ctx.base, u)) and ctx.is_outside(u) and not feeds_protected(ctx, u)
    ]


class EditUnrelatedValue(Operator):
    name = "xlsx.extra.edit_unrelated_value"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    description = "Change a typed value that no requirement reads and the task did not touch."

    def sites(self, ctx, req, binding):
        return [site(u) for u in outside_literal_cells(ctx)][:200]

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        cell = get_cell(ctx.base, where.unit)
        new = perturbed_value(cell, rng)
        return Build(
            steps=[set_value_step(sheet, address, new)],
            expectation=content_expectation(
                where.unit, must_change=[f"{where.unit}/v"], must_equal=[(f"{where.unit}/v", new)]
            ),
            facts={"cell": f"{sheet}!{address}", "before": cell["v"][1], "after": new[1]},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(
            ctx, (), f"changes the unrelated cell {f['cell']} from {f['before']!r} to "
            f"{f['after']!r}", harmful=True,
        )


class ClearUnrelatedRow(Operator):
    name = "xlsx.extra.clear_unrelated_row"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    description = "Clear every typed value in a data row that no requirement reads."

    def sites(self, ctx, req, binding):
        out = []
        for sheet, body in ctx.base["sheets"].items():
            rows: dict[int, list[str]] = {}
            for address in body["cells"]:
                row, _ = fx.split_address(address)
                rows.setdefault(row, []).append(address)
            for row, addresses in sorted(rows.items()):
                units = [cell_unit(sheet, a) for a in addresses]
                filled = [u for u in units if get_cell(ctx.base, u)["v"] is not None]
                if len(filled) < 2:
                    continue
                if all(
                    is_literal(get_cell(ctx.base, u)) and ctx.is_outside(u)
                    and not feeds_protected(ctx, u)
                    for u in filled
                ):
                    out.append(site(f"sheets/{seg(sheet)}/rows/{row}", sheet=sheet, row=row,
                                    cells=sorted(filled)))
        return out[:200]

    def build(self, ctx, where, rng):
        sheet, row, cells = where.info["sheet"], where.info["row"], where.info["cells"]
        cols = [fx.split_address(parse_unit(u)[1])[1] for u in cells]
        rng_text = f"{fx.make_address(row, min(cols))}:{fx.make_address(row, max(cols))}"
        allow = [f"{u}/{k}" for u in cells for k in ("v", "f")]
        return Build(
            steps=[{"op": "xlsx.clear_contents", "sheet": sheet, "range": rng_text}],
            expectation=Expectation(
                allow=allow,
                must_change=[f"{u}/v" for u in cells],
                must_equal=[(f"{u}/v", None) for u in cells],
                xlsx_dependents_of=list(cells),
            ),
            facts={"sheet": sheet, "row": row, "cells": len(cells)},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(
            ctx, (), f"clears row {f['row']} of {f['sheet']!r} ({f['cells']} values)",
            harmful=True,
        )


def outside_sheets(ctx: Context, require_content: bool) -> list[str]:
    out = []
    for name in ctx.base["workbook"]["sheets"]:
        units = [cell_unit(name, a) for a in ctx.base["sheets"][name]["cells"]]
        if any(not ctx.is_outside(u) for u in units):
            continue
        if any(re.search(rf"\b{re.escape(name)}\b", req_text(r)) for r in ctx.spec.requirements):
            continue
        if sheet_referenced_elsewhere(ctx.base, name):
            continue
        has_content = any(get_cell(ctx.base, u)["v"] is not None for u in units)
        if require_content and not has_content:
            continue
        out.append(name)
    return out


class RenameUnrelatedSheet(Operator):
    name = "xlsx.extra.rename_unrelated_sheet"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    aspects = ("sheet_name",)
    description = "Rename a sheet that no requirement mentions and no formula references."

    def sites(self, ctx, req, binding):
        return [site(f"sheets/{seg(n)}", sheet=n) for n in outside_sheets(ctx, False)]

    def build(self, ctx, where, rng):
        sheet = where.info["sheet"]
        new = f"{sheet[:24]} {rng.choice(['old', 'copy', 'tmp', 'bak'])}"
        loc = f"sheets/{seg(sheet)}/name"
        return Build(
            steps=[{"op": "xlsx.rename_sheet", "sheet": sheet, "new_name": new}],
            expectation=Expectation(allow=[loc], must_change=[loc]),
            facts={"before": sheet, "after": new},
        )

    def judge(self, ctx, where, built):
        f = built.facts
        return judge_extra(
            ctx, self.aspects, f"renames the unrelated sheet {f['before']!r} to {f['after']!r}",
            harmful=True,
        )


class DeleteUnrelatedSheet(Operator):
    name = "xlsx.extra.delete_unrelated_sheet"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    aspects = ("sheet_set",)
    description = "Delete a non-empty sheet that no requirement reads."

    def sites(self, ctx, req, binding):
        if len(ctx.base["workbook"]["sheets"]) < 2:
            return []
        return [site(f"sheets/{seg(n)}", sheet=n) for n in outside_sheets(ctx, True)]

    def build(self, ctx, where, rng):
        sheet = where.info["sheet"]
        loc = f"sheets/{seg(sheet)}"
        return Build(
            steps=[{"op": "xlsx.remove_sheet", "sheet": sheet}],
            expectation=Expectation(
                allow=[loc, "workbook/sheet_order", "book_view/*", "sheets/*/view/*",
                       "workbook/defined_names"],
                must_change=[loc],
            ),
            facts={"sheet": sheet},
        )

    def judge(self, ctx, where, built):
        return judge_extra(
            ctx, (), f"deletes the unrelated, non-empty sheet {built.facts['sheet']!r}",
            harmful=True,
        )


class FormatUnrelatedCell(Operator):
    name = "xlsx.extra.format_unrelated_cell"
    family = FAMILY
    label_class = EXTRA
    target = "outside"
    aspects = ("bold", "color")
    description = "Make an unrelated non-empty cell bold and red."

    def sites(self, ctx, req, binding):
        out = []
        for unit in all_cells(ctx.base):
            cell = get_cell(ctx.base, unit)
            font = cell["style"].get("font", {})
            if cell["v"] is not None and ctx.is_outside(unit) and not font.get("b"):
                out.append(site(unit))
        return out[:200]

    def build(self, ctx, where, rng):
        sheet, address = parse_unit(where.unit)
        return Build(
            steps=[{"op": "xlsx.set_char_props", "sheet": sheet, "range": address,
                    "props": {"bold": True, "color": "FF0000"}}],
            expectation=Expectation(
                allow=[f"{where.unit}/style/font/*"],
                must_change=[f"{where.unit}/style/font/b", f"{where.unit}/style/font/color"],
            ),
            facts={"cell": f"{sheet}!{address}"},
        )

    def judge(self, ctx, where, built):
        return judge_extra(
            ctx, self.aspects, f"makes the unrelated cell {built.facts['cell']} bold and red",
            harmful=False,
        )


_CELL_ALLOW = re.compile(r"^sheets/([^/]+)/cells/([A-Z]{1,3})([0-9]+)/")


def allow_edited_rows(self: Operator, ctx: Context, built: Build) -> Build:
    """LibreOffice recomputes the automatic height of a row whose cell it edits.

    That is a consequence of the edit, so the row attributes of every row that
    holds an edited cell join the footprint. Rows of untouched cells stay out.
    """
    rows = set()
    for pattern in built.expectation.allow + built.expectation.must_change:
        match = _CELL_ALLOW.match(pattern)
        if match:
            rows.add(f"sheets/{match.group(1)}/rows/{match.group(3)}/*")
    built.expectation.allow = list(built.expectation.allow) + sorted(rows)
    return built


OPERATORS: tuple[type[Operator], ...] = (
    DocTitle,
    ViewZoom,
    ViewSelection,
    ActiveSheet,
    LiteralForFormula,
    ReferenceForLiteral,
    SumRangeExpand,
    PlusChainToSum,
    AverageToSumCount,
    AbsoluteRefs,
    ConcatToAmpersand,
    NamedStyleForDirect,
    ValuePerturb,
    FormulaRefShift,
    ClearBoundCell,
    DropCharFormat,
    NumberFormatChange,
    EditUnrelatedValue,
    ClearUnrelatedRow,
    RenameUnrelatedSheet,
    DeleteUnrelatedSheet,
    FormatUnrelatedCell,
)

for _op in OPERATORS:
    _op.finalize = allow_edited_rows  # type: ignore[method-assign]
