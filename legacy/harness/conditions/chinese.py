"""Internal Chinese condition — intermediate messages in free-form Chinese."""

from __future__ import annotations

from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType

CHINESE_SYSTEM_ADDENDUM = """
## Internal Language Policy

For all internal reasoning, planning, memory summaries, retry analysis, and
coordination messages, use Chinese (中文). This applies to:
- Planning notes and reasoning traces
- Subtask handoffs between steps
- Memory update summaries
- Retry diagnosis and error analysis
- Coordination messages

IMPORTANT: The following MUST remain in English:
- All tool calls and their JSON arguments
- All structured output (JSON, YAML, code)
- The final user-facing response
- Any text that will be parsed by tools or APIs

This is a communication optimization. Use natural Chinese for your internal
thinking and planning, but keep all structured interfaces in English.
"""


class InternalChineseCondition(LanguageCondition):
    """Internal messages use free-form Chinese. Tool calls and responses stay English."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.INTERNAL_CHINESE

    @property
    def target_language(self) -> str:
        return "chinese"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + CHINESE_SYSTEM_ADDENDUM

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content
