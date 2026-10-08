"""A small A1-formula tokenizer for reference shifting, rewriting and dependency closure.

It handles the spreadsheet formulas that appear in office tasks: cell and range
references with optional sheet qualifiers and ``$`` anchors, string literals,
function calls and operators. It is not a full Excel grammar; callers treat a
formula it cannot tokenize as not applicable rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_ROW = 1_048_576
MAX_COL = 16_384

_SHEET = r"(?:'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_.]*)"
_CELL = r"\$?[A-Za-z]{1,3}\$?[0-9]{1,7}"
_TOKEN = re.compile(
    rf"""
    (?P<string>"(?:[^"]|"")*")
  | (?P<ref>(?:(?P<sheet>{_SHEET})!)?(?P<a>{_CELL})(?::(?P<b>{_CELL}))?)(?![A-Za-z0-9_(])
  | (?P<func>[A-Za-z_][A-Za-z0-9_.]*)(?=\()
  | (?P<name>[A-Za-z_][A-Za-z0-9_.]*)
  | (?P<number>(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?)
  | (?P<space>\s+)
  | (?P<op>[-+*/^&=<>(),;:%!{{}}]|<>|<=|>=)
    """,
    re.VERBOSE,
)
_CELL_PARTS = re.compile(r"(\$?)([A-Za-z]{1,3})(\$?)([0-9]{1,7})")


class FormulaError(ValueError):
    """The formula is outside the supported subset."""


def col_to_index(letters: str) -> int:
    value = 0
    for char in letters.upper():
        value = value * 26 + (ord(char) - 64)
    return value


def index_to_col(index: int) -> str:
    if index < 1:
        raise FormulaError(f"column index {index} is out of range")
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def split_address(address: str) -> tuple[int, int]:
    """Return (row, col), 1-based, for an address such as ``B5`` or ``$B$5``."""
    match = _CELL_PARTS.fullmatch(address)
    if match is None:
        raise FormulaError(f"not a cell address: {address!r}")
    return int(match.group(4)), col_to_index(match.group(2))


def make_address(row: int, col: int) -> str:
    return f"{index_to_col(col)}{row}"


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    sheet: str | None = None
    first: str | None = None
    last: str | None = None


def tokenize(formula: str) -> list[Token]:
    """Tokenize a formula body (with or without the leading ``=``)."""
    text = formula[1:] if formula.startswith("=") else formula
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None or match.end() == pos:
            raise FormulaError(f"cannot tokenize formula at {pos}: {formula!r}")
        kind = match.lastgroup or "op"
        if match.group("ref") is not None:
            sheet = match.group("sheet")
            if sheet is not None and sheet.startswith("'"):
                sheet = sheet[1:-1].replace("''", "'")
            tokens.append(
                Token("ref", match.group(0), sheet, match.group("a"), match.group("b"))
            )
        else:
            for group in ("string", "func", "name", "number", "space", "op"):
                if match.group(group) is not None:
                    kind = group
                    break
            tokens.append(Token(kind, match.group(0)))
        pos = match.end()
    return tokens


def render(tokens: list[Token]) -> str:
    return "=" + "".join(token.text for token in tokens)


def _quote_sheet(sheet: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", sheet):
        return sheet
    return "'" + sheet.replace("'", "''") + "'"


def _shift_cell(cell: str, drow: int, dcol: int) -> str:
    match = _CELL_PARTS.fullmatch(cell)
    if match is None:
        raise FormulaError(f"not a cell: {cell!r}")
    col_abs, letters, row_abs, digits = match.groups()
    col = col_to_index(letters) + (0 if col_abs else dcol)
    row = int(digits) + (0 if row_abs else drow)
    if not (1 <= row <= MAX_ROW and 1 <= col <= MAX_COL):
        raise FormulaError("shifted reference leaves the sheet")
    return f"{col_abs}{index_to_col(col)}{row_abs}{row}"


def sheet_prefix(sheet: str) -> str:
    return f"{_quote_sheet(sheet)}!"


def ref_text(sheet: str | None, first: str, last: str | None) -> str:
    prefix = f"{_quote_sheet(sheet)}!" if sheet is not None else ""
    return prefix + first + (f":{last}" if last else "")


def shift_formula(formula: str, drow: int, dcol: int) -> str:
    """Shift the relative parts of every reference, as a copied formula would."""
    out = []
    for token in tokenize(formula):
        if token.kind == "ref":
            first = _shift_cell(token.first or "", drow, dcol)
            last = _shift_cell(token.last, drow, dcol) if token.last else None
            out.append(Token("ref", ref_text(token.sheet, first, last), token.sheet, first, last))
        else:
            out.append(token)
    return render(out)


def absolutize(formula: str) -> str:
    """Anchor every reference with ``$``; the value does not change."""
    out = []
    for token in tokenize(formula):
        if token.kind == "ref":
            first = _absolute(token.first or "")
            last = _absolute(token.last) if token.last else None
            out.append(Token("ref", ref_text(token.sheet, first, last), token.sheet, first, last))
        else:
            out.append(token)
    return render(out)


def _absolute(cell: str) -> str:
    match = _CELL_PARTS.fullmatch(cell)
    if match is None:
        raise FormulaError(f"not a cell: {cell!r}")
    return f"${match.group(2).upper()}${match.group(4)}"


def cells_in_ref(first: str, last: str | None, cap: int = 4096) -> list[tuple[int, int]]:
    r1, c1 = split_address(first.replace("$", ""))
    if last is None:
        return [(r1, c1)]
    r2, c2 = split_address(last.replace("$", ""))
    rows = range(min(r1, r2), max(r1, r2) + 1)
    cols = range(min(c1, c2), max(c1, c2) + 1)
    if len(rows) * len(cols) > cap:
        raise FormulaError("range too large to expand")
    return [(r, c) for r in rows for c in cols]


def referenced_cells(formula: str, default_sheet: str) -> set[tuple[str, int, int]]:
    """Every (sheet, row, col) a formula reads, ranges expanded (bounded)."""
    result: set[tuple[str, int, int]] = set()
    for token in tokenize(formula):
        if token.kind != "ref":
            continue
        sheet = token.sheet or default_sheet
        for row, col in cells_in_ref(token.first or "", token.last):
            result.add((sheet, row, col))
    return result


def to_api_grammar(formula: str) -> str:
    """Convert Excel separators to the UNO API grammar (``;`` between arguments).

    ``XCell.setFormula`` parses English function names with ``;`` as the
    parameter separator and ``$Sheet.A1`` sheet references. Commas inside
    string literals are preserved.
    """
    out = []
    for token in tokenize(formula):
        if token.kind == "op" and token.text == ",":
            out.append(";")
        elif token.kind == "ref" and token.sheet is not None:
            # The API grammar writes sheet references as $Sheet.A1 (PODF), not Sheet!A1.
            name = _quote_sheet(token.sheet)
            out.append(f"${name}.{token.first}" + (f":{token.last}" if token.last else ""))
        else:
            out.append(token.text)
    return "=" + "".join(out)


def single_call(formula: str, function: str) -> list[Token] | None:
    """If the formula is exactly ``=FUNCTION(args)``, return the argument tokens."""
    tokens = [t for t in tokenize(formula) if t.kind != "space"]
    if len(tokens) < 3 or tokens[0].kind != "func" or tokens[0].text.upper() != function:
        return None
    if tokens[1].text != "(" or tokens[-1].text != ")":
        return None
    depth = 0
    for index, token in enumerate(tokens[1:], start=1):
        if token.text == "(":
            depth += 1
        elif token.text == ")":
            depth -= 1
            if depth == 0 and index != len(tokens) - 1:
                return None
    return tokens[2:-1]


def split_args(tokens: list[Token]) -> list[list[Token]]:
    """Split call arguments on top-level commas or semicolons."""
    args: list[list[Token]] = [[]]
    depth = 0
    for token in tokens:
        if token.text == "(":
            depth += 1
        elif token.text == ")":
            depth -= 1
        if depth == 0 and token.kind == "op" and token.text in {",", ";"}:
            args.append([])
            continue
        args[-1].append(token)
    return args
