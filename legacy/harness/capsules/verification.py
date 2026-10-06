"""Reference capsule that prevents unsupported finalization."""

from __future__ import annotations

from collections.abc import Sequence

from harness.capsules.schema import (
    CapsuleAction,
    CapsuleEvent,
    CapsuleManifest,
    Effect,
    Hook,
)


class VerifyBeforeFinalCapsule:
    """Require a structured passed verification artifact before final output."""

    manifest = CapsuleManifest(
        capsule_id="verify-before-final",
        capsule_version="0.1.0",
        required_hooks=frozenset({Hook.BEFORE_FINAL}),
        required_effects={
            Hook.BEFORE_FINAL: frozenset(
                {Effect.REQUEST_VERIFICATION, Effect.BLOCK}
            )
        },
        state_scope="none",
        priority=100,
        max_actions_per_event=2,
    )

    async def handle(self, event: CapsuleEvent) -> Sequence[CapsuleAction]:
        verification = event.payload.get("verification")
        if isinstance(verification, dict) and verification.get("status") == "passed":
            return ()
        common = {
            "source_capsule": self.manifest.capsule_id,
            "priority": self.manifest.priority,
        }
        return (
            CapsuleAction(
                effect=Effect.REQUEST_VERIFICATION,
                payload={
                    "required_status": "passed",
                    "required_evidence": ["check_id", "artifact_hash"],
                },
                **common,
            ),
            CapsuleAction(
                effect=Effect.BLOCK,
                payload={"reason": "final response lacks passed verification evidence"},
                **common,
            ),
        )
