"""English + prompt compression baseline (LLMLingua-style)."""

from __future__ import annotations

from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType

COMPRESSED_SYSTEM_ADDENDUM = """
## Internal Language Policy — Compressed English

For all internal reasoning, use maximally compressed English:
- Remove articles (a, an, the), filler words, and redundant prepositions
- Use abbreviations for common terms (req→request, resp→response, fn→function)
- Use telegraphic style: subject-verb-object, no subordinate clauses
- Keep technical precision: exact variable names, exact error messages
- Preserve logical structure with numbered steps or bullet points

Example:
Planning: check user order history → verify refund eligibility → process if valid
Constraints: refund_window=30d, user_id must match, status!=cancelled
Next: call get_order_history(user_id="abc123")
"""


class CompressedEnglishCondition(LanguageCondition):
    """Compressed English baseline — prompt compression without language switching."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.ENGLISH_COMPRESSED

    @property
    def target_language(self) -> str:
        return "compressed_english"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + COMPRESSED_SYSTEM_ADDENDUM

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        return content
