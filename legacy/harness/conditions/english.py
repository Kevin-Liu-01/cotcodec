"""English-only baseline condition — no transformation."""

from __future__ import annotations

from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType


class EnglishOnlyCondition(LanguageCondition):
    """Baseline: all messages remain in English. No transformation applied."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.ENGLISH_ONLY

    @property
    def target_language(self) -> str:
        return "english"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content
