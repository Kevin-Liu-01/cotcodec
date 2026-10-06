"""Language condition implementations for CoTCodec."""

from harness.conditions.base import LanguageCondition
from harness.conditions.chinese import InternalChineseCondition
from harness.conditions.compressed import CompressedEnglishCondition
from harness.conditions.controlled import ControlledChineseCondition
from harness.conditions.degraded import (
    EnglishOnly25WordLimitCondition,
    EnglishOnlyLowEffortCondition,
    EnglishOnlyNoThinkingCacheCondition,
)
from harness.conditions.english import EnglishOnlyCondition
from harness.conditions.polish import PolishStressCondition
from harness.conditions.router import DynamicRouterCondition
from harness.conditions.structured import StructuredEnglishCondition
from harness.config import ConditionID

CONDITION_REGISTRY: dict[ConditionID, type[LanguageCondition]] = {
    ConditionID.ENGLISH_ONLY: EnglishOnlyCondition,
    ConditionID.ENGLISH_ONLY_LOW_EFFORT: EnglishOnlyLowEffortCondition,
    ConditionID.ENGLISH_ONLY_NO_THINKING_CACHE: EnglishOnlyNoThinkingCacheCondition,
    ConditionID.ENGLISH_ONLY_25WORD_LIMIT: EnglishOnly25WordLimitCondition,
    ConditionID.INTERNAL_CHINESE: InternalChineseCondition,
    ConditionID.CONTROLLED_CHINESE: ControlledChineseCondition,
    ConditionID.ENGLISH_COMPRESSED: CompressedEnglishCondition,
    ConditionID.STRUCTURED_ENGLISH: StructuredEnglishCondition,
    ConditionID.DYNAMIC_ROUTER: DynamicRouterCondition,
    ConditionID.POLISH_STRESS: PolishStressCondition,
}


def get_condition(condition_id: ConditionID, **kwargs) -> LanguageCondition:
    cls = CONDITION_REGISTRY[condition_id]
    return cls(**kwargs)
