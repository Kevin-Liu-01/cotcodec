"""Plain-text file operators (family ``text``); implementations live in ``_textops``."""

from __future__ import annotations

from harness.q2_mutation.operators._base import Operator
from harness.q2_mutation.operators._textops import (
    TextLineEdit,
    TextTrailingNewline,
    TextUnrelatedLineDelete,
    TextUnrelatedLineEdit,
)

FAMILY = "text"

OPERATORS: tuple[type[Operator], ...] = (
    TextTrailingNewline,
    TextLineEdit,
    TextUnrelatedLineEdit,
    TextUnrelatedLineDelete,
)
