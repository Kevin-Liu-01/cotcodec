"""Polish stress condition — deliberately high-fragmentation contrast."""

from __future__ import annotations

from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType

POLISH_SYSTEM_ADDENDUM = """
## Internal Language Policy

For all internal reasoning, planning, memory summaries, retry analysis, and
coordination messages, use Polish (polski). This applies to:
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

This is a stress test condition. Polish typically has high token fragmentation
under most tokenizers, making it a deliberate contrast to Chinese.
"""


class PolishStressCondition(LanguageCondition):
    """Polish stress condition — deliberately high-fragmentation for contrast."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.POLISH_STRESS

    @property
    def target_language(self) -> str:
        return "polish"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + POLISH_SYSTEM_ADDENDUM

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content
