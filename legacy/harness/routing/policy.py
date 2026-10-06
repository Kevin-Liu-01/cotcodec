"""Routing policy implementation.

Implements the routing decision tree from the proposal:
1. Code or JSON-adjacent? → English or structured English
2. Safety-critical? → English
3. Planning, memory, or summary? → Chinese or controlled protocol
4. Otherwise → English
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from harness.config import MessageType
from harness.routing.features import MessageFeatures, extract_features


class LanguageDirective(StrEnum):
    ENGLISH = "english"
    CHINESE = "chinese"
    STRUCTURED_ENGLISH = "structured_english"
    COMPRESSED_ENGLISH = "compressed_english"


@dataclass
class RoutingDecision:
    """A routing decision with justification."""

    directive: LanguageDirective
    reason: str
    features: MessageFeatures


class RoutingPolicy:
    """Determines the optimal language for each intermediate message.

    The policy is a simple decision tree that can be extended or replaced
    with a learned policy based on experiment results.
    """

    def __init__(
        self,
        code_threshold: float = 0.3,
        schema_threshold: float = 0.5,
    ):
        self.code_threshold = code_threshold
        self.schema_threshold = schema_threshold

    def route(self, content: str, message_type: MessageType) -> RoutingDecision:
        features = extract_features(content, message_type)

        if not message_type.is_variable:
            return RoutingDecision(
                directive=LanguageDirective.ENGLISH,
                reason="fixed message type",
                features=features,
            )

        if features.is_code_heavy:
            return RoutingDecision(
                directive=LanguageDirective.STRUCTURED_ENGLISH,
                reason=f"code density {features.code_density:.2f} > {self.code_threshold}",
                features=features,
            )

        if features.is_schema_adjacent:
            return RoutingDecision(
                directive=LanguageDirective.ENGLISH,
                reason=(
                    f"schema proximity {features.schema_proximity:.2f} "
                    f"> {self.schema_threshold}"
                ),
                features=features,
            )

        if message_type in {MessageType.PLANNER_NOTE, MessageType.MEMORY_UPDATE}:
            return RoutingDecision(
                directive=LanguageDirective.CHINESE,
                reason="planning/memory message — highest compression benefit",
                features=features,
            )

        if message_type == MessageType.RETRY_DIAGNOSIS:
            return RoutingDecision(
                directive=LanguageDirective.COMPRESSED_ENGLISH,
                reason="retry diagnosis — compress but preserve error context",
                features=features,
            )

        if message_type in {MessageType.SUBTASK_HANDOFF, MessageType.COORDINATOR_MSG}:
            return RoutingDecision(
                directive=LanguageDirective.CHINESE,
                reason="coordination message — good compression target",
                features=features,
            )

        return RoutingDecision(
            directive=LanguageDirective.ENGLISH,
            reason="default fallback",
            features=features,
        )
