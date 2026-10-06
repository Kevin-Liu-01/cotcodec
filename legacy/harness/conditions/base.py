"""Abstract base class for language conditions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from harness.config import ConditionID, MessageType


class LanguageCondition(ABC):
    """A language condition defines how intermediate agent messages are transformed.

    The contract:
    - FIXED message types (tool_call, tool_result, user_response) are NEVER modified
    - VARIABLE message types may be transformed according to the condition's policy
    - The condition must be stateless across messages (no side effects between calls)
    - The condition must report its target language for logging
    """

    @property
    @abstractmethod
    def condition_id(self) -> ConditionID: ...

    @property
    @abstractmethod
    def target_language(self) -> str: ...

    @abstractmethod
    def transform_system_prompt(self, prompt: str) -> str:
        """Inject language instructions into the system prompt.

        This is where the condition tells the model to use a specific language
        for its internal reasoning and planning messages.
        """
        ...

    def transform_message(self, content: str, message_type: MessageType) -> str:
        """Transform an intermediate message according to this condition.

        Default: pass through FIXED types unchanged, delegate VARIABLE types
        to _transform_variable.
        """
        if not message_type.is_variable:
            return content
        return self._transform_variable(content, message_type)

    @abstractmethod
    def _transform_variable(self, content: str, message_type: MessageType) -> str:
        """Transform a variable-type message. Subclasses implement this."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.condition_id.value})"
