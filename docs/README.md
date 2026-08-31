# Documentation index

CoTCodec documentation is deliberately layered so current truth is not trapped
inside task transcripts or repeated across stale README files.

| Layer | Owner | Purpose |
|---|---|---|
| Human entry point | [`../README.md`](../README.md) | Why the project exists and where to start |
| Current compiled state | [`current-state.md`](current-state.md) | Latest admitted/killed gates and next action |
| Memory continuation | [`memory-handoff.md`](memory-handoff.md) | Exact pins, sealed results, next lifecycle falsifiers, and stop rules |
| H100 operation | [`h100-operator-runbook.md`](h100-operator-runbook.md) | Live host state, admitted submission lane, and publication blockers |
| Scientific semantics | [`evidence-model.md`](evidence-model.md) | What each evidence level can and cannot claim |
| Code ownership | [`repository-map.md`](repository-map.md) | Directory responsibilities and dependency flow |
| Operations | [`research-operations.md`](research-operations.md) | Local, SSH, Slurm, rerun, and writeback procedure |
| Local data | [`data-policy.md`](data-policy.md) | What stays local, what is portable, what enters Git |
| Harness architecture | [`../harness/README.md`](../harness/README.md) | Execution and trace pipeline |
| Compute contract | [`../infra/README.md`](../infra/README.md) | Scheduler/container/checkpoint boundaries |
| Full agent reference | [`../AGENTS.md`](../AGENTS.md) | Complete research operating guide |
| Local agent procedures | `../**/SKILL.md` | Directory-specific work instructions |
| Compiled machine state | [`../memory.json`](../memory.json) | Program state and next actions |
| Append-only history | [`../wiki/log.md`](../wiki/log.md) | Chronological evidence and decisions |

## Documentation ownership rule

- Rewrite compiled pages when truth changes.
- Append observations to `wiki/log.md`; never rewrite its history.
- Keep experiment contracts immutable after observing their treatment.
- Put executable procedure in `SKILL.md`, not in prose-only checklists.
- Put machine-generated topology only inside Agent-Docs auto markers.
