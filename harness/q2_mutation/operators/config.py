"""Configuration-file operators (family ``config``: JSON/JSONC and INI-style files).

Implementations live in ``_textops`` with the plain-text operators, because both
families are edited by splicing characters rather than through a document model.
"""

from __future__ import annotations

from harness.q2_mutation.operators._base import Operator
from harness.q2_mutation.operators._textops import (
    ConfigKeyDelete,
    ConfigTrailingNewline,
    ConfigUnrelatedKeyDelete,
    ConfigUnrelatedValue,
    ConfigValueChange,
    IniKeyValueSpacing,
    JsonKeyReorder,
    JsonNumberRepr,
    JsonReformat,
)

FAMILY = "config"

OPERATORS: tuple[type[Operator], ...] = (
    ConfigTrailingNewline,
    JsonReformat,
    JsonKeyReorder,
    IniKeyValueSpacing,
    JsonNumberRepr,
    ConfigValueChange,
    ConfigKeyDelete,
    ConfigUnrelatedValue,
    ConfigUnrelatedKeyDelete,
)
