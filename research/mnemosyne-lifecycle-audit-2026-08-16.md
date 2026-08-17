# Mnemosyne one-way consolidation lifecycle audit

Date: 2026-08-16  
Source: [official repository](https://github.com/mnemosyne-oss/mnemosyne)  
Revision: `a0e14243e04dbe3fc29287e58126ff5dc0e02b35`

Mnemosyne is a useful working-to-episodic consolidation prior, but it is not a
demonstrated bidirectional active/inactive pager. The contained doctor tested
that boundary directly rather than importing the repository's unmatched
benchmark comparisons.

The exact pinned source ran in two fresh SQLite states inside a digest-pinned
ARM64 Docker image with network disabled, a read-only root filesystem, all
capabilities dropped, no-new-privileges, one CPU, 1 GiB RAM, no provider
secret, no model or embedding call, no GPU, and no sudo. Each repetition used
three fresh container processes: prepare, restart verification, and purge.

Both clean states reproduced the same semantic projection:

- duplicate writes were idempotent and the two sessions remained isolated;
- forced sleep marked the working rows consolidated and created a recallable
  episodic summary;
- the consolidated records left active context and survived a fresh process;
- recall did not reactivate either consolidated record into active context;
- documented `forget(source_id)` removed the working row, while the episodic
  summary remained logically recallable;
- `forget(episodic_summary_id)` returned false, one episodic canary row
  remained, and the plaintext canary remained in `mnemosyne.db`;
- no native session-scoped purge operation was available.

The terminal status is
`BLOCKED_CONSOLIDATED_FORGET_AND_NO_REACTIVATION`. This is a bounded lifecycle
negative, not a memory-quality, graph-efficacy, scientific, or publication
result. An H100 actor cell would spend compute after the registered lifecycle
falsifier already failed, so it is forbidden for this revision.

Unblocking requires a newer immutable revision or an explicit patch arm that
implements source-complete forget or cryptographic erasure, proves zero residue
after a fresh process, and supplies a real archive-to-active transition without
cross-session bleed.

Canonical self-contained evidence:
`research/evidence/memory/mnemosyne-one-way-consolidation-negative-v1.json`.
