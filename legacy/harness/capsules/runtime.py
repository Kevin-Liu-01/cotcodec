"""Compilation and deterministic dispatch for portable orchestration capsules."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol

from harness.capsules.schema import (
    CapabilityManifest,
    CapsuleAction,
    CapsuleEvent,
    CapsuleManifest,
    DispatchResult,
    Effect,
    Verdict,
)


class CapsuleCompatibilityError(ValueError):
    """Raised when a host cannot faithfully realize a capsule contract."""


class CapsuleConflictError(ValueError):
    """Raised when composed capsules request incompatible exclusive effects."""


class CapsuleSequenceError(ValueError):
    """Raised for reordered events or event-id reuse with different content."""


class Capsule(Protocol):
    manifest: CapsuleManifest

    async def handle(self, event: CapsuleEvent) -> Sequence[CapsuleAction]: ...


EXCLUSIVE_EFFECTS = {
    Effect.REWRITE_TOOL_ARGS,
    Effect.RETRY,
    Effect.REQUEST_VERIFICATION,
}


class CapsuleRuntime:
    """A compiled capsule set bound to one host capability manifest."""

    def __init__(
        self,
        host: CapabilityManifest,
        capsules: Sequence[Capsule],
    ) -> None:
        self.host = host
        self.capsules = tuple(
            sorted(capsules, key=lambda item: (-item.manifest.priority, item.manifest.capsule_id))
        )
        self._last_sequence: dict[str, int] = {}
        self._event_cache: dict[str, tuple[str, DispatchResult]] = {}

    async def dispatch(self, event: CapsuleEvent) -> DispatchResult:
        fingerprint = event.model_dump_json()
        cached = self._event_cache.get(event.event_id)
        if cached is not None:
            cached_fingerprint, result = cached
            if cached_fingerprint != fingerprint:
                raise CapsuleSequenceError(
                    f"event id {event.event_id!r} was reused with different content"
                )
            return result

        if event.hook not in self.host.hooks:
            raise CapsuleCompatibilityError(
                f"host {self.host.harness_id} does not expose {event.hook}"
            )
        previous = self._last_sequence.get(event.session_id)
        if previous is not None and event.sequence <= previous:
            raise CapsuleSequenceError(
                f"session {event.session_id!r} sequence {event.sequence} is not after {previous}"
            )

        actions: list[CapsuleAction] = []
        prepared: list[Capsule] = []
        try:
            for capsule in self.capsules:
                manifest = capsule.manifest
                if event.hook not in manifest.required_hooks:
                    continue
                emitted = list(await capsule.handle(event))
                prepared.append(capsule)
                if len(emitted) > manifest.max_actions_per_event:
                    raise CapsuleCompatibilityError(
                        f"{manifest.capsule_id} exceeded max_actions_per_event"
                    )
                allowed_by_capsule = manifest.required_effects.get(event.hook, frozenset())
                allowed_by_host = self.host.effects_by_hook.get(event.hook, frozenset())
                for action in emitted:
                    if action.source_capsule != manifest.capsule_id:
                        raise CapsuleCompatibilityError(
                            f"{manifest.capsule_id} emitted an action for "
                            f"{action.source_capsule}"
                        )
                    if action.effect not in allowed_by_capsule:
                        raise CapsuleCompatibilityError(
                            f"{manifest.capsule_id} did not declare "
                            f"{action.effect} at {event.hook}"
                        )
                    if action.effect not in allowed_by_host:
                        raise CapsuleCompatibilityError(
                            f"host {self.host.harness_id} cannot enforce "
                            f"{action.effect} at {event.hook}"
                        )
                    if action.effect is Effect.INJECT_CONTEXT:
                        payload_bytes = len(
                            json.dumps(
                                action.payload,
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode()
                        )
                        ceiling = min(
                            manifest.max_context_injection_bytes,
                            self.host.max_context_injection_bytes,
                        )
                        if payload_bytes > ceiling:
                            raise CapsuleCompatibilityError(
                                f"{manifest.capsule_id} emitted {payload_bytes} "
                                f"context bytes above ceiling {ceiling}"
                            )
                    actions.append(action)

            self._reject_conflicts(actions)
            ordered = tuple(
                sorted(
                    actions,
                    key=lambda action: (
                        -action.priority,
                        action.source_capsule,
                        action.effect,
                    ),
                )
            )
            verdict = Verdict.BLOCK if any(
                action.effect is Effect.BLOCK for action in ordered
            ) else Verdict.ALLOW
            result = DispatchResult(
                event_id=event.event_id,
                verdict=verdict,
                actions=ordered,
            )
        except Exception:
            for capsule in reversed(prepared):
                rollback = getattr(capsule, "rollback", None)
                if rollback is not None:
                    await rollback(event)
            raise

        for capsule in prepared:
            commit = getattr(capsule, "commit", None)
            if commit is not None:
                await commit(event)
        self._last_sequence[event.session_id] = event.sequence
        self._event_cache[event.event_id] = (fingerprint, result)
        return result

    @staticmethod
    def _reject_conflicts(actions: Sequence[CapsuleAction]) -> None:
        for effect in EXCLUSIVE_EFFECTS:
            candidates = [action for action in actions if action.effect is effect]
            payloads = {
                json.dumps(action.payload, sort_keys=True, separators=(",", ":"))
                for action in candidates
            }
            if len(payloads) > 1:
                sources = sorted(action.source_capsule for action in candidates)
                raise CapsuleConflictError(
                    f"conflicting {effect} actions from capsules {sources}"
                )


def compile_capsules(
    host: CapabilityManifest,
    capsules: Sequence[Capsule],
) -> CapsuleRuntime:
    """Bind capsules to a host, refusing every unsupported semantic requirement."""

    capsule_ids = [capsule.manifest.capsule_id for capsule in capsules]
    duplicates = sorted(
        capsule_id for capsule_id in set(capsule_ids) if capsule_ids.count(capsule_id) > 1
    )
    if duplicates:
        raise CapsuleCompatibilityError(f"duplicate capsule ids: {duplicates}")

    for capsule in capsules:
        manifest = capsule.manifest
        missing_hooks = set(manifest.required_hooks) - set(host.hooks)
        if missing_hooks:
            raise CapsuleCompatibilityError(
                f"{host.harness_id} lacks hooks required by {manifest.capsule_id}: "
                f"{sorted(missing_hooks)}"
            )
        for hook, effects in manifest.required_effects.items():
            missing_effects = set(effects) - set(host.effects_by_hook.get(hook, frozenset()))
            if missing_effects:
                raise CapsuleCompatibilityError(
                    f"{host.harness_id} cannot enforce effects required by "
                    f"{manifest.capsule_id} at {hook}: {sorted(missing_effects)}"
                )
        if (
            manifest.max_context_injection_bytes
            > host.max_context_injection_bytes
        ):
            raise CapsuleCompatibilityError(
                f"{host.harness_id} context ceiling {host.max_context_injection_bytes} "
                f"is below {manifest.capsule_id} requirement "
                f"{manifest.max_context_injection_bytes}"
            )
    return CapsuleRuntime(host, capsules)
