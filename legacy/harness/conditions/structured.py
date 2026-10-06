"""Structured English protocol — schema-like intermediate format."""

from __future__ import annotations

from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType

STRUCTURED_ENGLISH_ADDENDUM = """
## Internal Language Policy — Structured English Protocol

For all internal reasoning, use a structured protocol format:

PLAN:
  goal: <one-line goal>
  steps: [<step1>, <step2>, ...]
  constraints: [<c1>, <c2>, ...]
  assumptions: [<a1>, <a2>, ...]

MEMORY:
  key_facts: [<fact1>, <fact2>, ...]
  state: <current state summary>

TOOL_REASONING:
  action: <tool_name>
  why: <one-line justification>
  expected: <expected outcome>

RETRY:
  error: <error description>
  cause: <root cause>
  fix: <proposed fix>

HANDOFF:
  from: <current subtask>
  to: <next subtask>
  context: <what the next step needs to know>

Use this structured format for ALL internal messages. Keep it terse.
Do NOT wrap in markdown code blocks — use the raw format above.
"""


class StructuredEnglishCondition(LanguageCondition):
    """Structured English protocol — formalized intermediate messages."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.STRUCTURED_ENGLISH

    @property
    def target_language(self) -> str:
        return "structured_english"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + STRUCTURED_ENGLISH_ADDENDUM

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content
