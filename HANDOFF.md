# Handoff — 2026-10-06

## What happened

The research program restarted. The previous program moved to `legacy/` with
its history intact (`git mv`), and git tag `legacy-2026-10-06` marks the last
pre-restart commit. The new program is in `program/PROGRAM.md`, chosen from 18
verified candidates. It covers kernel correctness-gate strength,
a calibrated computer-use instrument, and cross-script sparse-indexer recall as
backfill.

Codex's uncommitted work on the H100 host was captured before the restart. Its
three 2026-10-06 documents are in `program/evidence/2026-10-06/codex/`. The
host checkout itself was not touched.

## State

- Stage 0 for all three questions. No GPU job has run in the new program.
- All 99 live tests pass in a fresh clone on the H100 host. One doctor test
  asserts wall time and can fail on a heavily loaded laptop.
- The node is on the R570 driver, which blocks Q1's on-policy audit.

## Next actions

1. Q2: build the OSWorld-Verified evaluator mutation kit (CPU only).
2. Q2: port the cua-speedrun action-path suite to the nested-KVM runtime.
3. Q1: implement gates (a), (b), (c) and the independent audit; validate them on
   reference kernels and deterministic mutants.
4. Q3: write `scripts/run_sparse_indexer_phase0a.py`, rebuild the image with
   tilelang and peft, fetch the `qwen3-0.6b-base` receipt, run K1.
5. Run the 0.5 GPU-h vLLM throughput probe before freezing any GPU budget.

## Waiting on Kevin

- Ask the host administrator for the R580 driver upgrade, or give written risk
  acceptance for Q1's audit of model-generated kernels.
- Approve the ~14.9 GB Holo3 trajectory download for Q2.
- Approve disclosing the Letta symlink and deletion-residue findings to
  letta-ai.
- Decide whether to purge the old host address and the internal corpus
  inventory from public git history. That needs a force-push.
- Rotate the Moonshot API key that was pasted into a chat session.

## Sync the host checkout

The host checkout has Codex's uncommitted edits. They are preserved in a
private archive outside this repository. When Codex is no longer using it:

```bash
cd ~/cotcodec
git stash push -u -m "codex-uncommitted-2026-10-06"
git fetch origin main
git merge --ff-only origin/main
```
