"""Check the checker-mutation note's number table (CPU, no network).

    uv run --locked python paper/checker-mutation-note/scripts/check_claims.py

Run from the repository root. `data/claims.json` maps every number in `draft.md` to the
committed file it comes from. For each claim this script checks that:

- its `text` occurs in the draft;
- every evidence item holds: a JSON item (`key`, a list of keys and indexes) resolves in the
  committed file, and its value rendered with `fmt` equals `expect`; a text item (`match`) is a
  substring of the committed file;
- each `expect` (or `shown`, where the text writes the value differently, as "70 of 74" for
  "70/74") occurs in the claim's `text`.

Then it masks every claim's text in the draft, together with the structural phrases listed in
`structural` (section, table and query references, versions), dates, arXiv ids, headings, code
spans, links and identifiers glued to letters (D72, K2, MUT-P1, task ids), and reports every
number left over. Exit status 0 means every claim checks and every number is covered.
"""

from __future__ import annotations

import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

NOTE_DIR = Path("paper/checker-mutation-note")
CLAIMS = NOTE_DIR / "data/claims.json"


def half_up(value: float, places: int) -> str:
    q = Decimal(1).scaleb(-places) if places else Decimal(1)
    return str(Decimal(repr(value)).quantize(q, rounding=ROUND_HALF_UP))


def render(value: object, fmt: str) -> str:
    if fmt == "raw":
        return str(value)
    if fmt == "len":
        return str(len(value))  # type: ignore[arg-type]
    if fmt == "int":
        return str(int(value))  # type: ignore[call-overload]
    if fmt == "comma":
        return f"{int(value):,}"  # type: ignore[call-overload]
    if fmt in ("pct0", "pct1", "pct2"):
        places = int(fmt[-1])
        pct = float(value) * 100  # type: ignore[arg-type]
        return half_up(pct, places)
    if fmt in ("pct1z", "pct2z"):
        v = float(value)  # type: ignore[arg-type]
        if v == 0.0:
            return "0"
        if v == 1.0:
            return "100"
        return half_up(v * 100, int(fmt[3]))
    if fmt in ("round2", "round3", "round1"):
        return half_up(float(value), int(fmt[-1]))  # type: ignore[arg-type]
    raise ValueError(f"unknown fmt {fmt!r}")


def resolve(obj: object, key: list) -> object:
    for k in key:
        if isinstance(obj, list):
            obj = obj[int(k)]
        elif isinstance(obj, dict):
            if k not in obj:
                raise KeyError(k)
            obj = obj[k]
        else:
            raise KeyError(k)
    return obj


def check_claims(spec: dict, draft: str) -> list[str]:
    errors: list[str] = []
    files: dict[str, str] = spec["sources"]
    texts: dict[str, str] = {}
    parsed: dict[str, object] = {}
    seen_ids: set[str] = set()
    for claim in spec["claims"]:
        cid = claim["id"]
        if cid in seen_ids:
            errors.append(f"{cid}: duplicate id")
        seen_ids.add(cid)
        text = claim["text"]
        if text not in draft:
            errors.append(f"{cid}: text not in draft: {text!r}")
        if not claim.get("evidence"):
            errors.append(f"{cid}: no evidence")
        for ev in claim.get("evidence", []):
            path = files.get(ev["file"], ev["file"])
            p = Path(path)
            if not p.is_file():
                errors.append(f"{cid}: missing file {path}")
                continue
            if "match" in ev:
                if path not in texts:
                    texts[path] = p.read_text()
                if ev["match"] not in texts[path]:
                    errors.append(f"{cid}: match not in {path}: {ev['match']!r}")
                if "expect" in ev and ev["expect"] not in ev["match"]:
                    errors.append(f"{cid}: expect {ev['expect']!r} not in its match")
            else:
                if path not in parsed:
                    parsed[path] = json.loads(p.read_text())
                try:
                    value = resolve(parsed[path], ev["key"])
                except (KeyError, IndexError, ValueError) as exc:
                    errors.append(f"{cid}: key {ev['key']} not in {path} ({exc})")
                    continue
                got = render(value, ev.get("fmt", "raw"))
                if got != ev["expect"]:
                    errors.append(
                        f"{cid}: {path} {ev['key']} renders {got!r}, expected {ev['expect']!r}"
                    )
            shown = ev.get("shown", ev.get("expect"))
            if shown is not None and shown not in text:
                errors.append(f"{cid}: {shown!r} not in claim text {text!r}")
    return errors


MASK_PATTERNS = [
    r"```.*?```",  # fenced code
    r"`[^`]*`",  # code spans
    r"<https?://[^>]*>",  # autolinks
    r"\]\([^)]*\)",  # link and image targets
    r"(?m)^#+ [\d.]*",  # heading numbers
    r"\b\d{4}-\d{2}-\d{2}\b",  # ISO dates
    r"\b\d{2}:\d{2}:\d{2}Z?\b",  # times
    r"\b\d{4}\.\d{4,5}\b",  # arXiv ids
    r"[A-Za-z][A-Za-z0-9_.+-]*\d[A-Za-z0-9_.+-]*",  # identifiers glued to letters
    r"\b[0-9a-f]*[a-f][0-9a-f]*\b",  # hex ids that start with a digit
]

NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def uncovered(spec: dict, draft: str) -> list[tuple[int, str, str]]:
    masked = list(draft)

    def blank(start: int, end: int) -> None:
        for i in range(start, end):
            if masked[i] != "\n":
                masked[i] = " "

    phrases = [c["text"] for c in spec["claims"]] + list(spec.get("structural", []))
    for phrase in sorted(set(phrases), key=len, reverse=True):
        for m in re.finditer(re.escape(phrase), draft):
            blank(m.start(), m.end())
    flat = "".join(masked)
    for pat in MASK_PATTERNS:
        for m in re.finditer(pat, flat, flags=re.S):
            blank(m.start(), m.end())
        flat = "".join(masked)
    out = []
    for m in NUMBER.finditer(flat):
        line = flat.count("\n", 0, m.start()) + 1
        src_line = draft.splitlines()[line - 1]
        out.append((line, m.group(0).rstrip(","), src_line.strip()[:110]))
    return out


def main() -> int:
    spec = json.loads(CLAIMS.read_text())
    draft = Path(spec["note"]).read_text()
    errors = check_claims(spec, draft)
    left = uncovered(spec, draft)
    for e in errors:
        print("CLAIM", e)
    for line, tok, ctx in left:
        print(f"UNCOVERED line {line}: {tok!r} in: {ctx}")
    n = len(spec["claims"])
    m = sum(len(c.get("evidence", [])) for c in spec["claims"])
    print(
        f"{n} claims, {m} evidence items, {len(errors)} claim errors, {len(left)} uncovered numbers"
    )
    return 1 if errors or left else 0


if __name__ == "__main__":
    sys.exit(main())
