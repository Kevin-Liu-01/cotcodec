# Evidence bundle: q3-k1-localization-screen-v3 gauntlet

Proposal: `program/proposals/2026-10-08-q3-k1-v3-qwen35-4b.md`.
Draft registration: `program/preregistrations/q3-k1-localization-screen-v3.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`.

Two passes share this bundle. Wave 1 (synthesis, commit d911d21; recorded in
`program/gauntlet/2026-10-08-q3-k1-v3-qwen35-4b.jsonl`, score 51) built it. The
repair under program decision D48 (same branch, before this run's wave) added
the files marked "repair" below and revised the doctor records.

| Path | Contents |
|---|---|
| `snapshots/` | One record per cited primary URL (50; 8 added by the repair). Each holds the HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, which are CC0; other pages: the HTML title). No page bodies or paper full texts. |
| `query-log.json` | Every retrieval call of the wave-1 discovery cells and synthesis (148 counted against wave 1's 150), and the repair block (`repair_run`: 6 counted against this run's 60, 13 uncounted paper reads with digests, and the screening outcomes of 11 ids). |
| `doctors/` | Six preflight doctor records as revised by the repair (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | Supplementary attestations of the dense pre-check v2's 4B lane (Slurm 862) and its image (build 855); a note that v3's own attestations do not exist; the wave-1 synthesis cost and power scripts. Repair: `repair-literal-channel-sim.py` with `.json` and `-weak-target.json` (S1, block-level literal channels), `repair-decision-sim.py` with `.json` (S2, decision rules on the registered K1 statistics code, validated to 7e-15), `repair-h2-predictive.py` with `.json`, `repair-cost-model.py` with `.json`. |
| `blind/` | Anonymized mechanism paragraphs. Wave 1: the proposal (`e942c63a`), the closest prior (`38ab2fa1`, Oracle-Guided) and SpotAttention (`91fa8475`). Repair, for this run's critic: the repaired proposal (`0ccbe84a`), a fresh closest-prior paragraph (`b005cf6a`) and Lost in Compression (`93f4dd72`). File names carry no role; the mapping is in `bundle.json`. |

Reproduce the repair's numbers from the worktree root:

```bash
S1_FAMILIES=1200 S1_TARGET_LITERAL=2.0 uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-literal-channel-sim.py out-strong.json
S1_FAMILIES=1200 S1_TARGET_LITERAL=1.0 uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-literal-channel-sim.py out-weak.json
PYTHONPATH=. OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 S2_REPS=2000 S2_BOOT=1000 uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-decision-sim.py run out-s2.json
PYTHONPATH=. uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-decision-sim.py validate
uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-h2-predictive.py
uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-cost-model.py
```

All randomness is seeded (S1: CRC32 of the scenario tag; S2: CRC32 of the
scenario, K1's bootstrap generator with seed 42). Process count does not change
results.

Not present, by design or because it does not exist yet:

- **Review receipts for this run.** Its reviewers have not run. No trusted
  Ed25519 store exists (D24).
- **This run's hash-chained audit row.** It is appended after its reviewers
  score. Wave 1's row is in `program/gauntlet/`.
- **v3's code, images, probe, smoke and manifests.** They need the v3 code, a
  probe under its own id, Kevin's admission and a freeze.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.
