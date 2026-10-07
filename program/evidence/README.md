# Program evidence

## 2026-10-06: question selection

| File | What it is |
|---|---|
| `question-dossier.md` / `.json` | All 18 candidates, verified and ranked by three judges: corrected question, what was wrong, closest priors, citable anchors with verification status, first experiment, kill criteria |
| `sources-verified.json` | Per-source primary-text checks behind the dossier |
| `codex-five-directions-source-checks.json` | One verifier per source for Codex's five-direction document: 44 claims, 42 verified, 2 corrected |
| `codex/` | Codex's three documents from 2026-10-06 and their verification records, as written on the H100 host. Their large `sources.json` dumps are not copied |

These are records of a selection process, not experimental results. Codex's
documents are kept verbatim, so their relative links point at the pre-restart
layout; prefix those paths with `legacy/`. Dates in
the dossier are arXiv submission dates unless stated otherwise.

## 2026-10-07: Q3 K1 bundle sources

| File | What it is |
|---|---|
| `2026-10-07/q3-k1-bundle-sources.json` | Every external file behind the K1 study bundle (revision, licence, size, SHA-256, Hub LFS id), the ParaDocs streaming record per pair (files, compressed bytes consumed, kept documents and tokens, stop reason, filter counts, filtered-file digest), the 2026-10-07 ParaDocs yield probe, and the bundle's digest, size, licence id and dedup, filter and quota reports. Identifiers and digests only; no source text |

This is input construction for preregistration q3-k1-localization-screen-v1,
not an experimental result.
