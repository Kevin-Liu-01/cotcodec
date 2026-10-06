---
name: update-memory
version: 0.1.0
triggers: ["update memory", "update state", "new finding", "landscape change"]
tools: [read, write]
mutating: true
---

# Update Memory

Update memory.json with new findings, landscape changes, or state transitions.

## Contract

When a session produces new information relevant to the project, this skill:
1. Reads current `memory.json`
2. Identifies which sections need updating
3. Makes targeted updates (never rewrite the whole file)
4. Validates the resulting JSON
5. Appends to `wiki/log.md`

## Sections to Update

| Trigger | Section |
|---------|---------|
| New experiment results | `state.next_actions`, `benchmarking.*.status` |
| New paper found | `landscape_tracking.key_papers_since_proposal` |
| New model released | `landscape_tracking.models_to_track` |
| API pricing change | `landscape_tracking.provider_changes` |
| Benchmark update | `landscape_tracking.benchmark_updates` |
| Phase transition | `state.phase`, `state.next_actions` |
| Meeting with Danqi | `advisor.action_items` |

## Anti-Patterns

- Do NOT overwrite existing entries — append or update
- Do NOT remove items from `key_papers_since_proposal` or `provider_changes`
- Do NOT change `advisor.confirmation` (that's a historical record)
- Do NOT update `state.last_updated` without also updating `state.next_actions`
