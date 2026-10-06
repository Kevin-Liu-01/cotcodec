# Palimpsest bitemporal lifecycle audit — 2026-08-16

## Decision

Palimpsest `0f83e166b0512a5ca9f38c2559f68749b35e994d` is a useful
pre-restart bitemporal stale-state control, but it is not restart-safe
bitemporal memory and has no native scoped purge. The exact revision is blocked
from H100 actor work.

Terminal status:
`BLOCKED_BITEMPORAL_RESTART_AND_NO_NATIVE_PURGE`.
`scientific_result=false` and `publication_ready=false`.

## Immutable source and runtime

- Official repository: <https://github.com/joe51111jwd/palimpsest>
- Revision: `0f83e166b0512a5ca9f38c2559f68749b35e994d`
- Tree: `fd25cbc074172ad0291f8a46faccaedd5deb2b48`
- Package version: `0.1.0`
- License: Apache-2.0
- Git archive SHA-256:
  `752c3fb16c9beae152c833cb0cd5e8ed67a80eba3c5fe544283f6642f9cc2be6`
- Container image ID:
  `sha256:afb752691fad10b3048b46772f56a92c54c467e3982e6bfed5f6295d45ff8781`
- Runtime: local ARM64 Docker, network disabled, non-root UID 65532, read-only
  root, all capabilities dropped, no-new-privileges, no GPU, no model, and no
  provider secret.

The lifecycle ran twice in independent Docker volumes. The stable projection
was byte-identical and hashes to
`f490afe9402622abe1ce3ffe2d738df55e979758381dde4faed777b830d76047`.

## What reproduced

Before restart, both repetitions reproduced:

- ordinary valid-time current-value behavior;
- a transaction-time knowledge cutoff;
- mixed single/multi cardinality voting;
- row-count idempotency for replayed native saves.

After restart, ordinary current-value and valid-time behavior still passed.

## Blocking falsifications

The native SQLite persistence layer did not preserve enough ledger state to
continue the bitemporal computation exactly:

- transaction closure state was lost, so the previously valid historical
  `known_at` cutoff returned no claim after restart;
- per-key cardinality state was lost, so the uninterrupted continuation
  produced `['delta']` while the restored continuation produced
  `['gamma', 'delta']`;
- native correction hid the canary from current logical facts, but the plaintext
  canary remained in retained SQLite bytes;
- the public surface exposed no native delete, forget, erase, or scoped purge
  operation.

These are lifecycle defects, not retrieval-quality measurements. They prohibit
using this revision as a durable bitemporal substrate or as an H100 actor arm.

## Upstream-suite boundary

The exact source was installed from its unpinned dependency declaration in the
contained image. The resulting upstream suite ended at 274 passed, 11 failed,
and 35 skipped. Failures included an absent LoCoMo fixture, token-budget drift,
BM25 recency/truncation behavior, and stale superseded excerpts reaching
rendered context. This is useful compatibility evidence, not a locked upstream
release guarantee.

## Evidence

- Machine receipt:
  `research/evidence/memory/palimpsest-bitemporal-negative-v1.json`
- Receipt SHA-256:
  `c0fa0f9830e9155b092fa410682eae08110b2d53c593d9c16b5d8147f9da1a20`
- Report:
  `data/results/palimpsest-bitemporal/2026-08-16-local-docker-v1/report.json`
- Report SHA-256:
  `cd3cf86d4fbe69bdac7558394f231e545280764a66af8c969cc32d4d035a7d84`
- Manifest SHA-256:
  `2a168ddf82fc28cb00bfd5f5b6563f917796d902122f5e12efa02baa8d4013c3`
- Upstream-suite output SHA-256:
  `722bb04153f386019ffa980a8a61e5eddef477045789ea0122d7b8e0e3f9a526`

## Readmission rule

Readmit only a newer immutable revision or an explicitly labeled repair arm
that preserves transaction closures and cardinality state over two fresh
restarts, supplies native scoped physical purge or cryptographic erasure, and
passes the same historical-cutoff, continuation, residue, and idempotency
falsifiers. Memory quality remains a separate matched experiment.
