"""Canonical, deliberately small contract for portable orchestration capsules."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Hook(StrEnum):
    SESSION_START = "session_start"
    BEFORE_MODEL = "before_model"
    AFTER_MODEL = "after_model"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_FINAL = "before_final"
    SESSION_END = "session_end"


class Effect(StrEnum):
    ANNOTATE = "annotate"
    INJECT_CONTEXT = "inject_context"
    EMIT_MEMORY_DELTA = "emit_memory_delta"
    REWRITE_TOOL_ARGS = "rewrite_tool_args"
    REQUEST_VERIFICATION = "request_verification"
    RETRY = "retry"
    BLOCK = "block"
    CHECKPOINT = "checkpoint"


class Verdict(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"


class CapsuleEvent(BaseModel):
    """One framework-visible lifecycle event, never hidden chain-of-thought."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    event_id: str = Field(min_length=1, max_length=256)
    session_id: str = Field(min_length=1, max_length=256)
    sequence: int = Field(ge=0)
    hook: Hook
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance: list[str] = Field(default_factory=list)
    contains_untrusted_data: bool = False


class CapabilityManifest(BaseModel):
    """What one host adapter can faithfully observe and enforce."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    harness_id: str = Field(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
    adapter_version: str = Field(min_length=1)
    native_protocol: str = Field(min_length=1)
    hooks: frozenset[Hook]
    effects_by_hook: dict[Hook, frozenset[Effect]]
    max_context_injection_bytes: int = Field(default=0, ge=0)
    supports_blocking: bool = False

    @model_validator(mode="after")
    def validate_effect_hooks(self) -> CapabilityManifest:
        undeclared = set(self.effects_by_hook) - set(self.hooks)
        if undeclared:
            raise ValueError(f"effects declared for unsupported hooks: {sorted(undeclared)}")
        blocking_effects = {
            Effect.BLOCK,
            Effect.RETRY,
            Effect.REWRITE_TOOL_ARGS,
            Effect.REQUEST_VERIFICATION,
        }
        if not self.supports_blocking and any(
            blocking_effects & set(effects) for effects in self.effects_by_hook.values()
        ):
            raise ValueError("blocking effects require supports_blocking=true")
        if any(
            Effect.INJECT_CONTEXT in effects for effects in self.effects_by_hook.values()
        ) and self.max_context_injection_bytes <= 0:
            raise ValueError("context injection requires a positive host byte ceiling")
        return self


class CapsuleManifest(BaseModel):
    """The hooks, effects, state boundary, and budget a capsule requires."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    capsule_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    capsule_version: str = Field(min_length=1)
    required_hooks: frozenset[Hook]
    required_effects: dict[Hook, frozenset[Effect]]
    state_scope: Literal["none", "session"]
    priority: int = Field(default=0, ge=-1000, le=1000)
    max_actions_per_event: int = Field(default=4, ge=1, le=32)
    max_context_injection_bytes: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_required_effects(self) -> CapsuleManifest:
        undeclared = set(self.required_effects) - set(self.required_hooks)
        if undeclared:
            raise ValueError(
                f"effects declared outside capsule required_hooks: {sorted(undeclared)}"
            )
        injects_context = any(
            Effect.INJECT_CONTEXT in effects for effects in self.required_effects.values()
        )
        if injects_context and self.max_context_injection_bytes <= 0:
            raise ValueError("context-injecting capsules must declare a positive byte ceiling")
        return self


class CapsuleAction(BaseModel):
    """A bounded request that the host adapter must either enforce or reject."""

    model_config = ConfigDict(frozen=True)

    effect: Effect
    payload: dict[str, Any] = Field(default_factory=dict)
    source_capsule: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    priority: int = Field(default=0, ge=-1000, le=1000)


class DispatchResult(BaseModel):
    """Normalized result used for cross-adapter replay parity checks."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    verdict: Verdict
    actions: tuple[CapsuleAction, ...]
