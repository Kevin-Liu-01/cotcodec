"""Candidate artifacts for blind rater packets: structure, difference, render.

A rater sees the instruction, the initial files and the candidate (decision D9,
``raters.py``). This module turns files into what the rater reads:

* ``structure_lines``: a plain-text listing of a document. Office files are
  listed from the operators' own snapshot (``operators/_snapshot.py``, the
  model the purity checks use), one ``location = value`` line per leaf, so
  every attribute an operator can edit is shown: run formatting (highlight,
  colour, font, size, shading), paragraph properties (alignment, spacing,
  indents), styles, headers and footers, notes, cell values, formulas and
  resolved cell styles, slide shapes with geometry, fills, lines, text-body
  properties and slide backgrounds. The listing is not built from
  python-docx, python-pptx or openpyxl, the libraries the checkers read with,
  so the raters do not share the checkers' blind spots. It is a display aid,
  not a checker: no rule, no comparison with gold;
* ``diff_lines``: the alignment-aware structural difference of the
  candidate against the initial file (``operators/_diff.py``, never against
  gold); if it reports nothing while the snapshots differ, a unified
  difference of the two listings is shown instead, so no change is hidden;
* ``render_command``: the LibreOffice headless PDF conversion and
  ``pdftoppm`` page images (100 dpi, up to 20 pages) run in the LO-VM image
  (the VM's own renderer).

Listings are capped so a packet stays readable; a cap is stated in the
listing.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

MAX_STRUCTURE_LINES = 1500
MAX_DIFF_LINES = 600
MAX_VALUE_CHARS = 600
RENDER_DPI = 100
RENDER_PAGES = 20
OFFICE_SUFFIXES = frozenset({".xlsx", ".docx", ".pptx"})
TEXT_SUFFIXES = frozenset({".txt", ".csv", ".json", ".py", ".md", ".html", ".css", ".js", ".xml"})
_SKIP_KEYS = frozenset({"snapshot_version", "family"})


def _cap(lines: list[str], limit: int) -> list[str]:
    if len(lines) <= limit:
        return lines
    return lines[:limit] + [f"... {len(lines) - limit} more lines (listing capped)"]


def _value(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= MAX_VALUE_CHARS:
        return text
    return text[:MAX_VALUE_CHARS] + f"... ({len(text)} chars)"


def flatten(value: Any, location: str = "") -> list[str]:
    """One ``location = json value`` line per leaf; ``/key`` for keys, ``[i]`` for items.

    Empty containers are leaves (``{}``, ``[]``), so for keys without ``/``
    or ``[`` the listing determines the snapshot (the tests invert it).
    """
    if isinstance(value, Mapping) and value:
        lines: list[str] = []
        for key in sorted(value, key=str):
            if not location and key in _SKIP_KEYS:
                continue
            lines += flatten(value[key], f"{location}/{key}")
        return lines
    if isinstance(value, list) and value:
        return [line for i, item in enumerate(value) for line in flatten(item, f"{location}[{i}]")]
    return [f"{location or '/'} = {json.dumps(value, ensure_ascii=False, sort_keys=True)}"]


def office_snapshot(path: Path) -> dict[str, Any]:
    from harness.q2_mutation.operators._snapshot import snapshot

    return snapshot(path)


def structure_lines(path: Path) -> list[str]:
    """Plain-text listing of one file; unknown types get size and hash."""
    suffix = path.suffix.lower()
    try:
        if suffix in OFFICE_SUFFIXES:
            return _cap(flatten(office_snapshot(path)), MAX_STRUCTURE_LINES)
        if suffix in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            return _cap(text.splitlines(), MAX_STRUCTURE_LINES)
    except Exception as exc:  # noqa: BLE001 - an unreadable file is shown as such
        return [f"unreadable {suffix} file: {type(exc).__name__}: {str(exc)[:200]}"]
    data = path.read_bytes()
    return [
        f"binary {suffix or 'file'}: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}"
    ]


def diff_lines(initial: Sequence[str], candidate: Sequence[str]) -> list[str]:
    """Unified difference of the candidate listing against the initial listing."""
    return _cap(
        list(
            difflib.unified_diff(
                list(initial), list(candidate), "initial", "candidate", lineterm="", n=1
            )
        ),
        MAX_DIFF_LINES,
    )


def office_diff_lines(initial: Path, candidate: Path) -> list[str]:
    """Structural changes from the initial file to the candidate (snapshot model)."""
    from harness.q2_mutation.operators._diff import diff

    before = office_snapshot(initial)
    after = office_snapshot(candidate)
    if before == after:
        return []
    changes = diff(before, after)
    lines = [f"{c.op} {c.loc} [{c.kind}]: {_value(c.before)} -> {_value(c.after)}" for c in changes]
    if not lines:
        # The snapshots differ but the structural differ reported nothing:
        # show the listings' difference so the change is never hidden.
        lines = diff_lines(flatten(before), flatten(after))
    return _cap(lines, MAX_DIFF_LINES)


def _difference(initial: Path, candidate: Path, lines: list[str]) -> list[str]:
    same_family = initial.suffix.lower() == candidate.suffix.lower()
    if candidate.suffix.lower() in OFFICE_SUFFIXES and same_family:
        try:
            return office_diff_lines(initial, candidate)
        except Exception as exc:  # noqa: BLE001 - shown, and the listings are compared
            return [f"structural difference unavailable: {type(exc).__name__}"] + diff_lines(
                structure_lines(initial), lines
            )
    return diff_lines(structure_lines(initial), lines)


def artifacts(
    initial: Mapping[str, str], candidate: Mapping[str, str | None]
) -> dict[str, dict[str, Any]]:
    """Per VM path: candidate structure and its difference against the initial file."""
    out: dict[str, dict[str, Any]] = {}
    for vm_path in sorted(candidate):
        local = candidate[vm_path]
        if local is None:
            out[vm_path] = {"structure": ["file absent in the end state"], "diff_vs_initial": []}
            continue
        lines = structure_lines(Path(local))
        out[vm_path] = {
            "structure": lines,
            "diff_vs_initial": (
                _difference(Path(initial[vm_path]), Path(local), lines)
                if vm_path in initial
                else ["new file"]
            ),
        }
    return out


def render_command(document: str, outdir: str, profile_home: str) -> list[list[str]]:
    """Commands (LO-VM image) that render a document to PNG pages."""
    stem = Path(document).stem
    return [
        [
            "env",
            f"HOME={profile_home}",
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            outdir,
            document,
        ],
        [
            "pdftoppm",
            "-r",
            str(RENDER_DPI),
            "-l",
            str(RENDER_PAGES),
            "-png",
            f"{outdir}/{stem}.pdf",
            f"{outdir}/{stem}",
        ],
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--items", type=Path, required=True, help="JSONL: item_id, initial, candidate"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    rows = []
    for line in args.items.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        rows.append(
            {"item_id": item["item_id"], "candidate": artifacts(item["initial"], item["candidate"])}
        )
    args.out.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8"
    )
    print(json.dumps({"items": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
