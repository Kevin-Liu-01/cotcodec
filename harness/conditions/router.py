"""Dynamic router — selects language per message type based on content features."""

from __future__ import annotations

from harness.conditions.base import LanguageCondition
from harness.config import ConditionID, MessageType

ROUTER_SYSTEM_ADDENDUM = """
## Internal Language Policy — Dynamic Routing

You will receive a language directive at the start of each internal message
based on its type and content features. Follow the directive for that message.

Possible directives:
- [LANG:EN] — use English
- [LANG:ZH] — use Chinese (中文)
- [LANG:STRUCT] — use structured English protocol
- [LANG:COMPRESSED] — use compressed telegraphic English

The routing is determined by the message type:
- Planning and memory summaries → typically [LANG:ZH] (highest compression)
- Code-adjacent or schema-heavy messages → [LANG:EN] or [LANG:STRUCT]
- Safety-critical messages → [LANG:EN] (no language switching)
- Retry diagnosis → [LANG:COMPRESSED]

Always follow the directive. Tool calls and final responses remain in English.
"""


class DynamicRouterCondition(LanguageCondition):
    """Routes each message to the optimal language based on type and content features."""

    @property
    def condition_id(self) -> ConditionID:
        return ConditionID.DYNAMIC_ROUTER

    @property
    def target_language(self) -> str:
        return "dynamic"

    def transform_system_prompt(self, prompt: str) -> str:
        return prompt + ROUTER_SYSTEM_ADDENDUM

    def route_message_type(self, message_type: MessageType, content: str) -> str:
        """Determine the optimal language directive for a message.

        Routing decision tree (from the proposal):
        1. Code or JSON-adjacent? → English or structured English
        2. Safety-critical? → English
        3. Planning, memory, or summary? → Chinese or controlled protocol
        4. Otherwise → English
        """
        if not message_type.is_variable:
            return "[LANG:EN]"

        code_density = self._estimate_code_density(content)
        if code_density > 0.3:
            return "[LANG:STRUCT]"

        if message_type in {MessageType.PLANNER_NOTE, MessageType.MEMORY_UPDATE}:
            return "[LANG:ZH]"

        if message_type == MessageType.RETRY_DIAGNOSIS:
            return "[LANG:COMPRESSED]"

        if message_type in {MessageType.SUBTASK_HANDOFF, MessageType.COORDINATOR_MSG}:
            return "[LANG:ZH]"

        return "[LANG:EN]"

    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        directive = self.route_message_type(message_type, content)
        return f"{directive}\n{content}"

    @staticmethod
    def _estimate_code_density(content: str) -> float:
        """Rough heuristic for code density based on syntax markers."""
        if not content:
            return 0.0
        code_markers = ["{", "}", "(", ")", "=", ";", "//", "/*", "*/", "->", "=>", "def ", "class "]
        marker_count = sum(content.count(m) for m in code_markers)
        return min(1.0, marker_count / max(1, len(content.split())))
