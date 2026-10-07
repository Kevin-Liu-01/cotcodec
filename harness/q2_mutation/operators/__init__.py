"""Q2 evaluator-mutation operator catalog.

Operators are grouped by document family (``xlsx``, ``docx``, ``pptx``,
``text``, ``config``) and by nominal label class: equivalence (E,
``*.eq.*``), alternative valid solution (A, ``*.alt.*``), requirement
violation (R, ``*.viol.*``) and unrequested extra change (F, ``*.extra.*``,
ABC-style). ``catalog()`` returns the frozen description of every operator
with a hash over the descriptions and the operator source files; the
preregistration records that hash.

Inputs per task file: the LibreOffice-saved gold (the base), the
LibreOffice-saved initial file (the task delta is their structural diff) and
the blind author's requirement spec. Operators never read checker code or
verdicts.

Labels come from the spec only. Every witness argument starts with its rule:

* ``W-E-SILENT`` / ``W-E-ALLOWED`` / ``W-E-CONFLICT``: an E change touches an
  aspect no requirement mentions (equiv), the spec lists as unconstrained
  (equiv), or a requirement mentions (ambiguous).
* ``W-A-SILENT`` / ``W-A-ALLOWED`` / ``W-A-PINNED`` / ``W-A-MENTIONED``: an A
  change preserves the bound observable; the requirement is silent on the
  mechanism (alt), the spec frees it (alt), requires the replaced mechanism
  (violation), or mentions it (ambiguous). ``W-A-REPRESENTATION`` and
  ``W-A-STRUCTURE`` mark A changes that render identically but change stored
  text or placeholder structure (ambiguous unless the spec frees them).
* ``W-R-PINNED`` / ``W-R-TEXT`` / ``W-R-WEAK-BINDING`` / ``W-R-UNPINNED``: an R
  change moves a bound observable off gold; a violation needs the requirement
  to pin the attacked aspect (by keyword, quote or check kind) and a binding
  of high or medium confidence, otherwise ambiguous.
* ``W-F-UNREQUESTED`` / ``W-F-COSMETIC`` / ``W-F-ALLOWED``: an F change edits
  a unit outside every binding and outside the task delta; content changes
  are should_fail_extra_change and cosmetic ones ambiguous; if the spec frees
  the aspect, a cosmetic change is equiv and a content change ambiguous.

Purity checks (all must pass for admission), judged against the null mutant
(the base saved once more through the same path, because LibreOffice is not a
load-save fixed point): ``applied``, ``survived_save``, ``edit_landed``,
``no_collateral_change``, and where declared ``forbidden_kinds_absent``,
``observable_preserved``, ``appearance_preserved``, ``same_items``,
``expected_values``, ``expected_deltas``, ``expected_formulas``.

Planning is deterministic: at most three sites per (task, operator), ordered
by a hash of (task, operator), seeded 42, 43, 44. Recipe steps carry SHA-256
digests of the text they expect, but a recipe's purity expectation can hold
document text (``must_equal`` quotes a whole paragraph), so recipes are
released only through ``campaign export``, which replaces long text by its
digest. Mutant documents and full recipes stay on the host and are never
released.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from harness.q2_mutation.operators import config, docx, pptx, text, xlsx
from harness.q2_mutation.operators._base import Operator

CATALOG_VERSION = "q2-mut-operators-v1"
FAMILY_MODULES = {"xlsx": xlsx, "docx": docx, "pptx": pptx, "text": text, "config": config}
SOURCE_FILES = (
    "__init__.py", "_base.py", "_common.py", "_diff.py", "_formula.py", "_jsonspan.py",
    "_ooxml.py", "_purity.py", "_snapshot.py", "_spec.py", "_textops.py", "apply_text.py",
    "config.py", "docx.py", "pipeline.py", "pptx.py", "text.py", "uno_apply.py", "xlsx.py",
)


def all_operators() -> list[type[Operator]]:
    return [op for module in FAMILY_MODULES.values() for op in module.OPERATORS]


def registry() -> dict[str, type[Operator]]:
    found: dict[str, type[Operator]] = {}
    for op in all_operators():
        if op.name in found:
            raise ValueError(f"duplicate operator name {op.name}")
        found[op.name] = op
    return found


def for_family(family: str) -> list[type[Operator]]:
    return list(FAMILY_MODULES[family].OPERATORS)


def source_digests() -> dict[str, str]:
    root = Path(__file__).parent
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in SOURCE_FILES
    }


def catalog() -> dict:
    entries = [op.catalog_entry() for op in all_operators()]
    counts: dict[str, dict[str, int]] = {}
    for entry in entries:
        family = counts.setdefault(entry["family"], {})
        family[entry["label_class"]] = family.get(entry["label_class"], 0) + 1
    sources = source_digests()
    body = {"catalog_version": CATALOG_VERSION, "operators": entries, "sources": sources}
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {**body, "counts": counts, "total": len(entries), "catalog_sha256": digest}
