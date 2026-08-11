"""Reference provenance graph capsule over the canonical lifecycle contract."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from harness.capsules.schema import (
    CapsuleAction,
    CapsuleEvent,
    CapsuleManifest,
    Effect,
    Hook,
)

TOKEN_RE = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class MemoryNode:
    node_id: str
    session_id: str
    sequence: int
    tool_name: str
    content: str
    parent_ids: tuple[str, ...]
    provenance: tuple[str, ...]


class MemoryGraphCapsule:
    """Session-scoped graph memory with provenance and data-only injection."""

    manifest = CapsuleManifest(
        capsule_id="memory-graph",
        capsule_version="0.1.0",
        required_hooks=frozenset(
            {Hook.AFTER_TOOL, Hook.BEFORE_MODEL, Hook.SESSION_END}
        ),
        required_effects={
            Hook.AFTER_TOOL: frozenset({Effect.EMIT_MEMORY_DELTA}),
            Hook.BEFORE_MODEL: frozenset({Effect.INJECT_CONTEXT}),
            Hook.SESSION_END: frozenset(),
        },
        state_scope="session",
        priority=20,
        max_actions_per_event=1,
        max_context_injection_bytes=4096,
    )

    def __init__(self, *, max_items: int = 3, max_item_chars: int = 512) -> None:
        if max_items <= 0 or max_item_chars <= 0:
            raise ValueError("memory graph budgets must be positive")
        if max_items * max_item_chars > 2048:
            raise ValueError("memory graph content budget exceeds the 4096-byte action ceiling")
        self.max_items = max_items
        self.max_item_chars = max_item_chars
        self._nodes: dict[str, list[MemoryNode]] = defaultdict(list)
        self._pending_writes: dict[str, MemoryNode] = {}
        self._pending_session_ends: set[str] = set()

    async def handle(self, event: CapsuleEvent) -> Sequence[CapsuleAction]:
        if event.hook is Hook.SESSION_END:
            self._pending_session_ends.add(event.event_id)
            return ()
        if event.hook is Hook.AFTER_TOOL:
            return self._write(event)
        if event.hook is Hook.BEFORE_MODEL:
            return self._recall(event)
        return ()

    async def commit(self, event: CapsuleEvent) -> None:
        node = self._pending_writes.pop(event.event_id, None)
        if node is not None:
            self._nodes[event.session_id].append(node)
        if event.event_id in self._pending_session_ends:
            self._pending_session_ends.remove(event.event_id)
            self._nodes.pop(event.session_id, None)

    async def rollback(self, event: CapsuleEvent) -> None:
        self._pending_writes.pop(event.event_id, None)
        self._pending_session_ends.discard(event.event_id)

    def _write(self, event: CapsuleEvent) -> Sequence[CapsuleAction]:
        content = str(event.payload.get("content", "")).strip()
        if not content:
            return ()
        tool_name = str(event.payload.get("tool_name", "unknown"))
        session_nodes = self._nodes[event.session_id]
        parent_ids = (session_nodes[-1].node_id,) if session_nodes else ()
        material = f"{event.session_id}\0{event.sequence}\0{tool_name}\0{content}".encode()
        node = MemoryNode(
            node_id=hashlib.sha256(material).hexdigest(),
            session_id=event.session_id,
            sequence=event.sequence,
            tool_name=tool_name,
            content=content,
            parent_ids=parent_ids,
            provenance=tuple(event.provenance),
        )
        self._pending_writes[event.event_id] = node
        return (
            CapsuleAction(
                effect=Effect.EMIT_MEMORY_DELTA,
                source_capsule=self.manifest.capsule_id,
                priority=self.manifest.priority,
                payload={
                    "operation": "append",
                    "node": self._serialize_node(node),
                },
            ),
        )

    def _recall(self, event: CapsuleEvent) -> Sequence[CapsuleAction]:
        query_tokens = self._tokens(str(event.payload.get("query", "")))
        if not query_tokens:
            return ()
        ranked: list[tuple[int, int, MemoryNode]] = []
        for node in self._nodes.get(event.session_id, []):
            overlap = len(query_tokens & self._tokens(node.content))
            if overlap:
                ranked.append((overlap, node.sequence, node))
        selected = [item[2] for item in sorted(ranked, reverse=True)[: self.max_items]]
        if not selected:
            return ()
        items = [
            {
                "node_id": node.node_id,
                "content": node.content[: self.max_item_chars],
                "tool_name": node.tool_name,
                "provenance": list(node.provenance),
                "instruction_authority": "none",
                "trust": "untrusted-data",
            }
            for node in selected
        ]
        return (
            CapsuleAction(
                effect=Effect.INJECT_CONTEXT,
                source_capsule=self.manifest.capsule_id,
                priority=self.manifest.priority,
                payload={
                    "framing": "quoted-untrusted-memory-data",
                    "items": items,
                },
            ),
        )

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return set(TOKEN_RE.findall(value.lower()))

    @staticmethod
    def _serialize_node(node: MemoryNode) -> dict[str, object]:
        return {
            "node_id": node.node_id,
            "session_id": node.session_id,
            "sequence": node.sequence,
            "tool_name": node.tool_name,
            "content": node.content,
            "parent_ids": list(node.parent_ids),
            "provenance": list(node.provenance),
            "trust": "untrusted-data",
        }
