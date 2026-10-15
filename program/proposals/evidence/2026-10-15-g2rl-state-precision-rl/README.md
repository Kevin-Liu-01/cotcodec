# Evidence bundle: G2-RL gauntlet, wave 1 synthesis (2026-10-15)

Proposal: `program/proposals/2026-10-15-g2rl-state-precision-rl.md`.
Draft registration (pilot only): `program/preregistrations/g2rl-state-precision-rl-v1.md` (DRAFT,
new experiment id, not frozen, no ledger row). Schema: `program/proposals/evidence/_schema.json`.
Index and hashes: `bundle.json`, built by `compute/build_bundle.py`.

The synthesis owner ran on the development Mac's CPU: no GPU, no host job, no retrieval search
(one full-text read and the source snapshots). The four discovery cells (frontier, kill-shot,
cross-domain, asset and cost) ran before it, independently and read-only; their query records
are in `query-log.json`.

| Path | Contents |
|---|---|
| `query-log.json` (`compute/build_query_log.py`) | Every orx discover query of the three retrieval cells with the ids it returned (98), the web searches (8), the approximate GitHub search counts (about 51), the uncounted reads, PRISMA counts and the two counting conventions. The cells saved no raw outputs, so there are no per-query raw digests |
| `snapshots/` (`compute/snapshot_sources.py`) | One record per URL the proposal cites (49): HTTP status, fetch time, body SHA-256 and size, an arXiv metadata extract or the HTML title; bodies are not stored. All returned HTTP 200; the OpenReview record is a browser-challenge page and verifies nothing |
| `compute/mismatch_by_cap.py`, `mismatch-by-cap.json`, `.stdout` | The committed G2b/G2c seed-42 per-token data (4B and 9B; fp32, bf16, fp16 state) re-read under 4K, 8K and 16K caps: k3 and mean abs mismatch with ratios to fp32 (bootstrap over prompts), TIS weight shares above 2 and 5 and below 0.5, per-sequence log trajectory ratios, a sequence mask calibrated on fp32, PSIS k-hat, cut shares |
| `compute/power_g2rl.py`, `power-g2rl.json`, `.stdout` | Operating characteristics (seeds 42-44): minimum detectable effects; the pilot's manipulation gate by a prompt-cluster bootstrap of committed data; the gradient-bias readout and the TIS recovery estimator in a Gaussian model at R = 3 and R = 4; the full design's learning rule under effect, SD and collapse scenarios |
| `compute/caps_g2rl.py`, `caps-g2rl.json`, `.stdout` | Cap arithmetic: the pilot's jobs (7.9167 cap-GPU-h, about 6.0 expected) and the full design's stages and paths (central, low, high) |
| `compute/blind-roles.json`, `blind/` | The anonymized mechanism paragraphs (the proposal's and Ring-linear's, arXiv 2510.19338) for the blind critic, in a seeded order; the roles file is for the recorder only |
| `compute/write_doctors.py`, `doctors/` | The six preflight doctor records (Source, Citation, Design and Safety PASS, Design self-assessed; Novelty and Compute FAIL) and the deterministic doctor's verbatim output (`doctors/direction-doctor-output.json`) |
| `compute/attestations-not-run.md` | The compute attestations that do not exist yet, and what produces each |

Reproduce from the repo root (CPU; numpy and scipy from the project environment):

```bash
E=program/proposals/evidence/2026-10-15-g2rl-state-precision-rl
python3 $E/compute/mismatch_by_cap.py --out $E/compute/mismatch-by-cap.json
uv run --locked python $E/compute/power_g2rl.py --out $E/compute/power-g2rl.json --reps 2000 --grad-reps 200
python3 $E/compute/caps_g2rl.py --out $E/compute/caps-g2rl.json
python3 $E/compute/build_query_log.py --out $E/query-log.json
python3 $E/compute/snapshot_sources.py program/proposals/2026-10-15-g2rl-state-precision-rl.md $E/snapshots
python3 $E/compute/write_doctors.py
python3 $E/compute/build_bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-15-g2rl-state-precision-rl.md
```

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and the two reviewers follow this
  synthesis; no trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended by the recorder after the reviewers score.
- **Compute attestations** (`compute/attestations-not-run.md`) and an executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and honest state.
