"""Helpers shared by the office operator families."""

from __future__ import annotations

import hashlib
import random

from harness.q2_mutation.operators._base import (
    EQUIV,
    Build,
    Context,
    Judgement,
    Operator,
    Site,
    judge_equivalence,
    site,
)
from harness.q2_mutation.operators._diff import CONTENT, FORMAT, LAYOUT, STRUCTURE
from harness.q2_mutation.operators._purity import Expectation

NON_VIEW_KINDS = [CONTENT, FORMAT, LAYOUT, STRUCTURE]


def text_sha256(text: str) -> str:
    """Steps carry a digest of the text they expect, never the third-party text itself."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# Document property name in the UNO DocumentProperties API -> core.xml local name.
DOC_PROPERTIES = {"Title": "title", "Subject": "subject", "Keywords": "keywords"}
NEUTRAL_WORDS = ("archive", "draft", "quarterly", "review", "working", "notes", "copy", "final")
LETTERS = "abcdefghijklmnopqrstuvwxyz"


def neutral_phrase(rng: random.Random, words: int = 2) -> str:
    return " ".join(rng.sample(NEUTRAL_WORDS, words))


def perturb_word(word: str, rng: random.Random) -> str:
    """Change one letter of ``word`` (keeping case); append a letter if it has none."""
    positions = [i for i, ch in enumerate(word) if ch.isalpha()]
    if not positions:
        return word + rng.choice(LETTERS)
    index = rng.choice(positions)
    old = word[index]
    choices = [c for c in LETTERS if c != old.lower()]
    new = rng.choice(choices)
    new = new.upper() if old.isupper() else new
    return word[:index] + new + word[index + 1 :]


def word_spans(text: str) -> list[tuple[int, int]]:
    """Spans of alphabetic words of length >= 3."""
    spans = []
    start = None
    for i, ch in enumerate(text + " "):
        if ch.isalpha():
            if start is None:
                start = i
        elif start is not None:
            if i - start >= 3:
                spans.append((start, i))
            start = None
    return spans


class DocPropertyOperator(Operator):
    """E: set a document property (Title, Subject or Keywords) in File > Properties."""

    label_class = EQUIV
    target = "document"
    aspects = ("metadata",)

    def sites(self, ctx: Context, req, binding) -> list[Site]:
        return [site(f"meta/{local}", field=name) for name, local in DOC_PROPERTIES.items()]

    def build(self, ctx: Context, where: Site, rng: random.Random) -> Build:
        name = where.info["field"]
        local = DOC_PROPERTIES[name]
        current = ctx.base.get("meta", {}).get(local, "")
        value = neutral_phrase(rng)
        while value == current:
            value = neutral_phrase(rng)
        loc = f"meta/{local}"
        return Build(
            steps=[{"op": "doc.set_property", "field": name, "value": value}],
            expectation=Expectation(
                allow=[loc],
                must_change=[loc],
                must_equal=[(loc, value)],
                forbid_kinds=NON_VIEW_KINDS,
            ),
            facts={"field": name, "before": current, "after": value},
        )

    def judge(self, ctx: Context, where: Site, built: Build) -> Judgement:
        facts = built.facts
        return judge_equivalence(
            ctx,
            self.aspects,
            f"sets the document {facts['field']} property from {facts['before']!r} to "
            f"{facts['after']!r} (File > Properties), which is not shown in the document body",
        )


TEXT_CONTENT_PATTERNS = (
    r"\btext\b", r"\bwords?\b", r"\breads?\b", r"\bspell", r"\btyped?\b", r"\breplac",
    r"\binsert", r"\bcontains?\b", r"\bsays?\b", r"\bwritten\b", r"\bwrite\b", r"\btitled?\b",
    r"\bnamed?\b", r"\blabel",
)


def choose_word_edit(
    text: str, rng: random.Random, prefer: list[str] | None = None
) -> tuple[int, int, str, str, bool] | None:
    """Pick a word to perturb; prefer words inside the quoted hint strings.

    Returns (start, end, old_word, new_word, inside_hint) or None.
    """
    spans = word_spans(text)
    if not spans:
        return None
    hinted = []
    for hint in prefer or []:
        hint = hint.strip()
        if not hint:
            continue
        pos = text.find(hint)
        while pos != -1:
            hinted.extend(s for s in spans if s[0] >= pos and s[1] <= pos + len(hint))
            pos = text.find(hint, pos + 1)
    pool = sorted(set(hinted)) or spans
    start, end = rng.choice(pool)
    old = text[start:end]
    new = perturb_word(old, rng)
    return start, end, old, new, bool(hinted)


def text_violation_reason(req_text_value: str, quoted_hits: list[str], old_word: str) -> str | None:
    """Why editing ``old_word`` violates a requirement, or None if it may not."""
    import re

    for hint in quoted_hits:
        if old_word in hint:
            return f"the requirement quotes {hint!r}, which no longer appears"
    hits = sorted(
        {m.group(0) for p in TEXT_CONTENT_PATTERNS for m in re.finditer(p, req_text_value, re.I)}
    )
    if hits:
        return f"the requirement constrains the text ({hits})"
    return None


def judge_text_edit(req, binding, change: str, old_word: str):
    """R rule for text edits: the requirement quotes or otherwise pins the edited text."""
    from harness.q2_mutation.operators._base import AMBIGUOUS, VIOLATION, Judgement
    from harness.q2_mutation.operators._spec import is_flagged, quoted, req_text

    reason = text_violation_reason(req_text(req), quoted(req_text(req)), old_word)
    confidence = binding.confidence if binding else "none"
    method = binding.method if binding else "none"
    if is_flagged(req.statement):
        return Judgement(
            AMBIGUOUS,
            f"W-R-FLAGGED: {change}; the spec flags {req.req_id} itself as ambiguous.",
            "W-R-FLAGGED",
            (req.req_id,),
        )
    if reason and confidence in {"high", "medium"}:
        return Judgement(
            VIOLATION,
            f"W-R-TEXT: {change}; {req.req_id}: {reason}; the site is bound by {method} "
            f"({confidence}) and gold satisfies {req.req_id}.",
            "W-R-TEXT",
            (req.req_id,),
        )
    if reason:
        return Judgement(
            AMBIGUOUS,
            f"W-R-WEAK-BINDING: {change}; {req.req_id}: {reason}; but the site is bound only by "
            f"{method} ({confidence}).",
            "W-R-WEAK-BINDING",
            (req.req_id,),
        )
    return Judgement(
        AMBIGUOUS,
        f"W-R-UNPINNED: {change}; {req.req_id} does not quote or describe this text.",
        "W-R-UNPINNED",
        (req.req_id,),
    )
