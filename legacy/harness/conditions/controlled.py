"""Controlled Chinese — restricted lexicon with explicit markers."""

from __future__ import annotations

from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType

CONTROLLED_CHINESE_ADDENDUM = """
## Internal Language Policy — Controlled Chinese

For internal reasoning, use Controlled Chinese with these conventions:

1. Use Chinese for natural language reasoning and planning
2. Prefix each section with an explicit marker:
   - [计划] for planning / goals
   - [约束] for constraints and requirements
   - [假设] for assumptions
   - [不确定] for uncertainty or alternatives
   - [工具] for tool-related reasoning
   - [风险] for risks or failure modes
   - [记忆] for memory summaries
   - [重试] for retry diagnosis
3. Keep technical terms, variable names, file paths, and API names in English
4. Keep numbers, dates, and measurements in their original format

MUST remain in English: tool calls, JSON arguments, structured output, final response.

Example:
[计划] 需要查询user的order history，然后检查refund eligibility
[约束] refund_window = 30 days，user_id必须match
[工具] 调用 get_order_history(user_id="abc123")
"""


class ControlledChineseCondition(LanguageCondition):
    """Chinese with restricted lexicon, explicit section markers, English technical terms."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.CONTROLLED_CHINESE

    @property
    def target_language(self) -> str:
        return "controlled_chinese"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + CONTROLLED_CHINESE_ADDENDUM

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content
