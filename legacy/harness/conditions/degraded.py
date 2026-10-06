"""English-only degraded conditions for OrchVar-Canary regression tests."""

from __future__ import annotations

from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType

LOW_EFFORT_ADDENDUM = """
## Internal Language Policy - Low Effort Regression

Keep internal reasoning short and minimal.
- Prefer the fastest acceptable plan.
- Avoid extended analysis unless absolutely necessary.
- Use one or two short planning sentences before acting.

This simulates a harness-level reduction in reasoning effort.
Tool calls and final responses remain in English.
"""

NO_THINKING_CACHE_ADDENDUM = """
## Internal Language Policy - No Thinking Cache Regression

Do not rely on prior internal notes or prior reasoning summaries.
- Re-derive your approach from the current turn whenever possible.
- Keep each step self-contained.
- Do not assume internal planning state persists reliably across steps.

This simulates a harness bug that clears working reasoning between turns.
Tool calls and final responses remain in English.
"""

WORD_LIMIT_ADDENDUM = """
## Internal Language Policy - 25 Word Regression

Keep each internal message to 25 words or fewer.
- Be extremely terse between tool calls.
- Omit non-critical explanation.
- Preserve only the minimum context needed to continue.

This simulates an over-aggressive verbosity limit in the harness.
Tool calls and final responses remain in English.
"""


class EnglishOnlyLowEffortCondition(LanguageCondition):
    """English baseline with reduced reasoning effort."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.ENGLISH_ONLY_LOW_EFFORT

    @property
    def target_language(self) -> str:
        return "english_low_effort"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + LOW_EFFORT_ADDENDUM

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content


class EnglishOnlyNoThinkingCacheCondition(LanguageCondition):
    """English baseline with intentionally unstable internal memory."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.ENGLISH_ONLY_NO_THINKING_CACHE

    @property
    def target_language(self) -> str:
        return "english_no_thinking_cache"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + NO_THINKING_CACHE_ADDENDUM

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content


class EnglishOnly25WordLimitCondition(LanguageCondition):
    """English baseline with an over-aggressive verbosity cap."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.ENGLISH_ONLY_25WORD_LIMIT

    @property
    def target_language(self) -> str:
        return "english_25_word_limit"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + WORD_LIMIT_ADDENDUM

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content
