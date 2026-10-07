"""Purity checks: the mutant differs from its base only where the operator says.

An operator states its footprint as an :class:`Expectation`: locator globs it
may change, globs that must change (the edit landed and survived the save),
values the mutant must hold, observables that must equal the base (for
equivalence and alternative-solution operators), and change kinds that must not
appear anywhere. The check runs on canonical snapshots of the saved base and
the saved mutant, both written by the same LibreOffice save path.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from typing import Any

from harness.q2_mutation.operators import _formula as fx
from harness.q2_mutation.operators._diff import (
    Change,
    diff,
    resolve,
    seg,
    unseg,
    values_equal,
)
from harness.q2_mutation.operators._snapshot import merge_spans

MAX_DETAIL = 12


@dataclass
class Expectation:
    """The declared footprint of one mutant."""

    allow: list[str] = field(default_factory=list)
    must_change: list[str] = field(default_factory=list)
    must_equal: list[tuple[str, Any]] = field(default_factory=list)
    preserve: list[str] = field(default_factory=list)
    forbid_kinds: list[str] = field(default_factory=list)
    xlsx_dependents_of: list[str] = field(default_factory=list)
    formulas: list[tuple[str, str]] = field(default_factory=list)
    appearance: list[str] = field(default_factory=list)
    same_items: list[str] = field(default_factory=list)
    numeric_tolerance: float = 1e-9
    int_tolerance: int = 0

    def as_dict(self) -> dict:
        return {
            "allow": list(self.allow),
            "must_change": list(self.must_change),
            "must_equal": [[loc, value] for loc, value in self.must_equal],
            "preserve": list(self.preserve),
            "forbid_kinds": list(self.forbid_kinds),
            "xlsx_dependents_of": list(self.xlsx_dependents_of),
            "formulas": [[loc, formula] for loc, formula in self.formulas],
            "appearance": list(self.appearance),
            "same_items": list(self.same_items),
            "numeric_tolerance": self.numeric_tolerance,
            "int_tolerance": self.int_tolerance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Expectation:
        return cls(
            allow=list(data.get("allow", [])),
            must_change=list(data.get("must_change", [])),
            must_equal=[(loc, value) for loc, value in data.get("must_equal", [])],
            preserve=list(data.get("preserve", [])),
            forbid_kinds=list(data.get("forbid_kinds", [])),
            xlsx_dependents_of=list(data.get("xlsx_dependents_of", [])),
            formulas=[(loc, formula) for loc, formula in data.get("formulas", [])],
            appearance=list(data.get("appearance", [])),
            same_items=list(data.get("same_items", [])),
            numeric_tolerance=float(data.get("numeric_tolerance", 1e-9)),
            int_tolerance=int(data.get("int_tolerance", 0)),
        )


@dataclass(frozen=True)
class PurityCheck:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _matches(loc: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(loc, pattern) for pattern in patterns)


def _describe(changes: list[Change]) -> str:
    shown = [f"{c.op} {c.loc}" for c in changes[:MAX_DETAIL]]
    more = len(changes) - len(shown)
    return "; ".join(shown) + (f"; +{more} more" if more > 0 else "")


def _close(a: Any, b: Any, tolerance: float, int_tolerance: int = 0) -> bool:
    if int_tolerance and isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(
        isinstance(x, int) and isinstance(y, int) for x, y in zip(a, b, strict=True)
    ):
        return all(abs(x - y) <= int_tolerance for x, y in zip(a, b, strict=True))
    if (
        isinstance(a, list) and isinstance(b, list) and len(a) == 2 and len(b) == 2
        and a[0] == b[0] == "n"
    ):
        x, y = float(a[1]), float(b[1])
        return abs(x - y) <= tolerance * max(1.0, abs(x), abs(y))
    return values_equal(a, b)


APPEARANCE_IGNORED = frozenset(
    {"outlineLvl", "keepNext", "keepLines", "widowControl", "lang", "kern", "rStyle"}
)


def _style_chain(styles: dict, name: str, kind: str) -> list[dict]:
    chain: list[dict] = []
    seen: set[str] = set()
    table = styles.get(kind, {})
    while name and name not in seen and name in table:
        seen.add(name)
        chain.append(table[name])
        name = table[name].get("based_on", "")
    return list(reversed(chain))


_FALSE_TOGGLES = frozenset(
    {"b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "vanish", "outline",
     "shadow", "emboss", "imprint"}
)
_RPR_DEFAULTS = {"u": "none", "vertAlign": "baseline", "spacing": "0", "position": "0",
                 "kern": "0", "color": "auto", "highlight": "none"}


def _merge(base: dict, over: dict) -> dict:
    """Overlay ``over`` on ``base``; nested dicts (rFonts, spacing, ind) merge by key."""
    out = dict(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _normal_rpr(props: dict) -> dict:
    out = {}
    for key, value in props.items():
        if key in APPEARANCE_IGNORED:
            continue
        if key in _FALSE_TOGGLES and value is False:
            continue
        if _RPR_DEFAULTS.get(key) == value:
            continue
        out[key] = value
    return out


def _normal_ppr(props: dict) -> dict:
    out = {}
    for key, value in props.items():
        if key in APPEARANCE_IGNORED:
            continue
        attrs = value.get("attrs") if isinstance(value, dict) else None
        if key == "jc" and attrs and attrs.get("val") in {"left", "start"}:
            continue
        if key == "bidi" and attrs and attrs.get("val") in {"0", "false"}:
            continue
        if key in {"ind", "spacing"} and attrs is not None:
            kept = {k: v for k, v in attrs.items() if v not in {"0", 0}}
            single = kept.get("line") == "240" and kept.get("lineRule", "auto") == "auto"
            if key == "spacing" and single:
                kept.pop("line", None)
                kept.pop("lineRule", None)
            if not kept:
                continue
            value = {**value, "attrs": kept}
        out[key] = value
    return out


def docx_effective(snap: dict, block: dict) -> dict:
    """Paragraph appearance after resolving defaults, styles and direct formatting.

    Values equal to the format's defaults (a false toggle, ``u=none``, zero
    indents, single line spacing, left alignment) are dropped, so explicit and
    implicit defaults compare equal.
    """
    styles = snap.get("styles") or {"defaults": {"rpr": {}, "ppr": {}}, "para": {}, "char": {}}
    name = block.get("style") or next(
        (n for n, entry in styles["para"].items() if entry.get("default")), ""
    )
    ppr = dict(styles["defaults"].get("ppr", {}))
    base_rpr = dict(styles["defaults"].get("rpr", {}))
    for entry in _style_chain(styles, name, "para"):
        ppr = _merge(ppr, entry.get("ppr", {}))
        base_rpr = _merge(base_rpr, entry.get("rpr", {}))
    ppr = _merge(ppr, block.get("ppr", {}))
    spans = []
    for text, props in block.get("spans", []):
        effective = dict(base_rpr)
        for entry in _style_chain(styles, props.get("rStyle", ""), "char"):
            effective = _merge(effective, entry.get("rpr", {}))
        effective = _merge(effective, props)
        spans.append((text, _normal_rpr(effective)))
    return {"text": block.get("text"), "ppr": _normal_ppr(ppr), "spans": merge_spans(spans)}


def _item_signatures(value: Any) -> list[str]:
    items = value if isinstance(value, list) else []
    return sorted(json.dumps(item, sort_keys=True) for item in items)


def xlsx_dependents(snap: dict, cell_locs: list[str]) -> set[str]:
    """Locators of formula-cell values that (transitively) read the given cells."""
    targets: set[tuple[str, int, int]] = set()
    for loc in cell_locs:
        parts = [unseg(p) for p in loc.split("/")]
        if len(parts) >= 4 and parts[0] == "sheets" and parts[2] == "cells":
            row, col = fx.split_address(parts[3])
            targets.add((parts[1], row, col))
    graph: dict[tuple[str, int, int], set[tuple[str, int, int]]] = {}
    for sheet, body in snap.get("sheets", {}).items():
        for address, cell in body["cells"].items():
            formula = cell.get("f")
            if not formula:
                continue
            try:
                reads = fx.referenced_cells(formula.lstrip("{").rstrip("}"), sheet)
            except fx.FormulaError:
                continue
            row, col = fx.split_address(address)
            graph[(sheet, row, col)] = reads
    found: set[tuple[str, int, int]] = set()
    frontier = set(targets)
    while frontier:
        new = {cell for cell, reads in graph.items() if reads & frontier and cell not in found}
        found |= new
        frontier = new
    return {
        f"sheets/{seg(sheet)}/cells/{seg(fx.make_address(row, col))}/v"
        for sheet, row, col in found
    }


def check(base: dict, actual: dict, expectation: Expectation) -> list[PurityCheck]:
    """Run every purity check; all must pass for the mutant to be admitted."""
    changes = diff(base, actual)
    results: list[PurityCheck] = []

    results.append(
        PurityCheck(
            "survived_save",
            bool(changes),
            "mutant differs from the saved base"
            if changes
            else "no difference after the save: the edit was normalized away",
        )
    )

    missing = [
        pattern for pattern in expectation.must_change
        if not any(fnmatch.fnmatchcase(c.loc, pattern) for c in changes)
    ]
    results.append(
        PurityCheck(
            "edit_landed",
            not missing,
            "every targeted locator changed" if not missing else f"unchanged: {missing}",
        )
    )

    tolerated: set[str] = set()
    if expectation.xlsx_dependents_of and base.get("family") == "xlsx":
        tolerated = xlsx_dependents(base, expectation.xlsx_dependents_of)
    collateral = [
        c for c in changes
        if not _matches(c.loc, expectation.allow) and c.loc not in tolerated
    ]
    results.append(
        PurityCheck(
            "no_collateral_change",
            not collateral,
            "all changes inside the declared footprint"
            if not collateral
            else _describe(collateral),
        )
    )

    forbidden = [c for c in changes if c.kind in expectation.forbid_kinds]
    if expectation.forbid_kinds:
        results.append(
            PurityCheck(
                "forbidden_kinds_absent",
                not forbidden,
                f"no {'/'.join(expectation.forbid_kinds)} change"
                if not forbidden
                else _describe(forbidden),
            )
        )

    if expectation.preserve:
        broken = []
        for loc in expectation.preserve:
            try:
                before, after = resolve(base, loc), resolve(actual, loc)
            except (KeyError, IndexError, ValueError):
                broken.append(f"{loc}: unresolvable")
                continue
            if not _close(before, after, expectation.numeric_tolerance):
                broken.append(f"{loc}: {before!r} -> {after!r}")
        results.append(
            PurityCheck(
                "observable_preserved",
                not broken,
                "observables equal the base" if not broken else "; ".join(broken[:MAX_DETAIL]),
            )
        )

    if expectation.must_equal:
        wrong = []
        for loc, expected in expectation.must_equal:
            try:
                value = resolve(actual, loc)
            except (KeyError, IndexError, ValueError):
                wrong.append(f"{loc}: unresolvable")
                continue
            if not _close(value, expected, expectation.numeric_tolerance,
                          expectation.int_tolerance):
                wrong.append(f"{loc}: expected {expected!r}, found {value!r}")
        results.append(
            PurityCheck(
                "expected_values",
                not wrong,
                "mutant holds the recipe's values" if not wrong else "; ".join(wrong[:MAX_DETAIL]),
            )
        )
    if expectation.appearance:
        differs = []
        for loc in expectation.appearance:
            try:
                before = docx_effective(base, resolve(base, loc))
                after = docx_effective(actual, resolve(actual, loc))
            except (KeyError, IndexError, ValueError):
                differs.append(f"{loc}: unresolvable")
                continue
            if not values_equal(before, after):
                differs.append(f"{loc}: effective formatting differs")
        results.append(
            PurityCheck(
                "appearance_preserved",
                not differs,
                "resolved paragraph and character formatting unchanged"
                if not differs
                else "; ".join(differs[:MAX_DETAIL]),
            )
        )

    if expectation.same_items:
        moved = []
        for loc in expectation.same_items:
            try:
                if _item_signatures(resolve(base, loc)) != _item_signatures(resolve(actual, loc)):
                    moved.append(f"{loc}: items differ")
            except (KeyError, IndexError, ValueError):
                moved.append(f"{loc}: unresolvable")
        results.append(
            PurityCheck(
                "same_items",
                not moved,
                "only the order of items changed" if not moved else "; ".join(moved),
            )
        )

    if expectation.formulas:
        wrong_f = []
        for loc, expected in expectation.formulas:
            try:
                value = resolve(actual, loc)
            except (KeyError, IndexError, ValueError):
                wrong_f.append(f"{loc}: unresolvable")
                continue
            if normalize_formula(value) != normalize_formula(expected):
                wrong_f.append(f"{loc}: expected {expected!r}, found {value!r}")
        results.append(
            PurityCheck(
                "expected_formulas",
                not wrong_f,
                "formulas match the recipe" if not wrong_f else "; ".join(wrong_f[:MAX_DETAIL]),
            )
        )
    return results


def normalize_formula(formula: str | None) -> str | None:
    """Compare formulas modulo ``$`` anchors, spaces, case and the ``_xlfn.`` prefix."""
    if formula is None:
        return None
    text = formula.strip().lstrip("=").replace("_xlfn.", "")
    out = []
    in_string = False
    for char in text:
        if char == '"':
            in_string = not in_string
        if not in_string and (char == "$" or char.isspace()):
            continue
        out.append(char if in_string else char.upper())
    return "".join(out)


def admitted(results: list[PurityCheck]) -> bool:
    return all(r.passed for r in results)
