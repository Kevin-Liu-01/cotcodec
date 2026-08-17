# Hermes ByteRover offline doctor — 2026-08-14

Status: `BLOCKED_OFFLINE_DAEMON_AND_PORTABLE_SESSION_LIFECYCLE_REPRODUCED`.

This is a native provider-integration negative, not a memory-quality result. The
doctor pins ByteRover CLI v3.16.1's annotated tag object, peeled Git commit,
npm package bytes and integrity, the bundled Hermes adapter, and the contained
image. It then repeats prepare and fresh-process restart in two independent
Docker volumes as UID 1000 with a read-only root, no network, no capabilities,
and no new privileges.

All three relevant command paths were unavailable offline:

- native `brv search`, documented as lexical/BM25;
- Hermes' read path, `brv query -- <query>`;
- Hermes' write path, `brv curate -- <content>`.

Each command hit its seven-second ceiling, and every daemon log recorded the
same fatal network startup error. The local canary file survived restart, so
the negative is daemon execution rather than volume loss. Static binding to the
exact Hermes source also confirms that its working directory is profile-global,
the logical session ID does not namespace storage, and the provider has no
native per-session purge method.

The sealed evidence is
`research/evidence/memory/hermes-byterover-offline-v1.json`. The retained result
root is `data/results/hermes-byterover/2026-08-14-offline-doctor-v1`; it contains
the registered experiment, source and image receipts, exact argv, raw outputs,
two stable projections, and a hash-bound manifest.

H100 admission is forbidden at this revision. A future revision or explicit
patch arm must first pass offline daemon startup with a pinned local model or
deterministic search path, session/tenant ownership, scoped purge, restart, and
residue checks. No provider credentials or H100 time should be spent before
those CPU gates pass.
