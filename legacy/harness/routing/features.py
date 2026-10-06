"""Message feature extraction for routing decisions.

Features used by the dynamic router to decide which language to use
for a given intermediate message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from harness.config import MessageType


@dataclass
class MessageFeatures:
    """Features extracted from a message for routing decisions."""

    message_type: MessageType
    code_density: float
    named_entity_density: float
    numerical_density: float
    schema_proximity: float
    char_count: int
    word_count: int

    @property
    def is_code_heavy(self) -> bool:
        return self.code_density > 0.3

    @property
    def is_schema_adjacent(self) -> bool:
        return self.schema_proximity > 0.5

    @property
    def is_planning(self) -> bool:
        return self.message_type in {
            MessageType.PLANNER_NOTE,
            MessageType.MEMORY_UPDATE,
            MessageType.COORDINATOR_MSG,
        }


def extract_features(content: str, message_type: MessageType) -> MessageFeatures:
    """Extract routing-relevant features from a message."""
    words = content.split()
    word_count = len(words)

    return MessageFeatures(
        message_type=message_type,
        code_density=_code_density(content, word_count),
        named_entity_density=_named_entity_density(content, word_count),
        numerical_density=_numerical_density(content, word_count),
        schema_proximity=_schema_proximity(content),
        char_count=len(content),
        word_count=word_count,
    )


def _code_density(content: str, word_count: int) -> float:
    """Proportion of content that looks like code."""
    if word_count == 0:
        return 0.0
    code_markers = [
        "{", "}", "(", ")", "[", "]", "=", ";", "//", "/*", "*/",
        "->", "=>", "def ", "class ", "import ", "return ", "if ", "for ",
    ]
    hits = sum(content.count(m) for m in code_markers)
    return min(1.0, hits / max(1, word_count))


def _named_entity_density(content: str, word_count: int) -> float:
    """Rough proportion of capitalized multi-word sequences (named entities)."""
    if word_count == 0:
        return 0.0
    entities = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", content)
    entity_words = sum(len(e.split()) for e in entities)
    return min(1.0, entity_words / max(1, word_count))


def _numerical_density(content: str, word_count: int) -> float:
    """Proportion of tokens that are numbers."""
    if word_count == 0:
        return 0.0
    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", content)
    return min(1.0, len(numbers) / max(1, word_count))


def _schema_proximity(content: str) -> float:
    """How close the content is to JSON/schema structure."""
    schema_indicators = [
        '":', '": ', "null", "true", "false",
        '"type"', '"name"', '"value"', '"id"',
    ]
    hits = sum(1 for ind in schema_indicators if ind in content)
    return min(1.0, hits / max(1, len(schema_indicators)))
