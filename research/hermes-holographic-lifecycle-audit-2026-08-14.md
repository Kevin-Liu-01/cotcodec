# Hermes Holographic lifecycle audit — 2026-08-14

## Decision

The pinned bundled Holographic provider is a useful local single-user SQLite
memory, but it is not admitted as a portable multi-session memory provider.
Two fresh, network-disabled, read-only-root Docker executions reproduced native
restart, duplicate-add idempotence, and persistent update/feedback behavior.
They also reproduced global logical-session visibility and the absence of a
native per-session purge operation.

Status: `BLOCKED_GLOBAL_SESSION_SCOPE_AND_NATIVE_SESSION_PURGE_REPRODUCED`.
This is lifecycle evidence only. It is not a memory-quality result, a secure
erasure claim, or authorization for an H100 experiment.

## Immutable identities

- Repository: `https://github.com/NousResearch/hermes-agent`
- Commit: `a90d5369f76c87c98547d2e283aa26d5cfabf322`
- Tree: `963eb136bfb21fd0b296a40529cbb3575c610874`
- Git archive SHA-256: `2a2934d3c8379816b2e3919f4cf1191f04e93f136da6f2128246d368644a9514`
- License: MIT
- Container image ID: `sha256:e3cdc03e8319a914a8b8978312199d76ee903b482658b67a7e637a8fa3694a95`
- Result manifest root: `bcd33923559acdea33ba3dbbe9af249cb6825b04a0c91cef11b203892faa9aa9`
- Stable projection: `b8c3f64023e6bf54eaa9d6cabb35fb341ed503b4149c4c0356a62cac8adbd3b5`
- Sealed evidence: `research/evidence/memory/hermes-holographic-lifecycle-v1.json`
- Sealed evidence SHA-256: `a532c646f24463a30910959f70c278c816d331a36b79efb1e75980604c31451d`

## Reproduced findings

- Native SQLite/FTS data survived a fresh provider process.
- Repeating the same add was idempotent.
- Update and feedback mutations survived restart.
- A fresh logical session could retrieve facts written by another logical
  session because the provider uses one Hermes-home database.
- The native interface can remove an individual memory but cannot purge all
  state owned by one logical session.
- The retained Linux container had zero plaintext hits after individual
  removal. A separate macOS diagnostic retained plaintext, so physical erasure
  is runtime-dependent and remains unproven.
- Holographic vector scoring was disabled in this exact cell because NumPy was
  not present. This result covers SQLite/FTS lifecycle, not HRR quality.

## Admission rule

Do not run this revision in a portable H100 memory study. Admit only a newer
immutable pin or a separately labeled wrapper/patch arm that provides explicit
session/tenant ownership, scoped purge, restart-stable ownership receipts, and
zero cross-session visibility. A future HRR quality cell must pin NumPy and
compare against the same FTS candidates and token budget.
