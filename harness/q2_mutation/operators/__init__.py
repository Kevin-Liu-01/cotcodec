"""Q2 evaluator-mutation operator catalog.

Operators are grouped by document family (``xlsx``, ``docx``, ``pptx``,
``text``, ``config``) and by nominal label class: equivalence (E),
alternative valid solution (A), requirement violation (R) and unrequested
extra change (F, ABC-style). Each operator takes a blind-author requirement
(or an outside site), proposes a deterministic seeded recipe, states its
purity footprint and derives its label from the spec alone.

``catalog()`` returns the frozen description of every operator together with
a hash over the descriptions and the operator source files; the
preregistration records that hash.
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
