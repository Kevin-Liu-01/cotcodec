# Evidence bundle: E5 first step (e5-gate-fertility-decomposition-v1) gauntlet, wave 1

Proposal: `program/proposals/2026-10-10-e5-gate-fertility-decomposition.md`.
Draft registration: `program/preregistrations/e5-gate-fertility-decomposition-v1.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(rebuilt by `compute/build-bundle.py`).

Built on 2026-10-10 by the gauntlet's single synthesis owner (D67) from four
independent discovery cells (frontier, kill-shot, cross-domain, asset and cost)
of workflow `gauntlet-e5-wave1`. Their queries were parsed from the cells' raw
orx outputs in the session scratchpad into `query-log.json` (each raw file's
SHA-256 recorded; the frontier and kill-shot query strings are transcribed from
the cells' structured results because their raw files hold only the output).
No GPU and no host job was used; all CPU work ran on the development Mac. The
host was read once with `squeue` (empty at 21:41 UTC).

| Path | Contents |
|---|---|
| `snapshots/` | One record per primary URL the proposal cites (32): HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, CC0; other pages: the HTML title). No page bodies or paper texts. |
| `query-log.json` | 120 counted orx discover queries (frontier 47, kill-shot 24, cross-domain 43, asset 6, synthesis 0) with all returned ids; 18 uncounted OpenReview, web and Anthology searches; 2 failures; 57 cell paper reads (40 distinct); the cells' verdicts in one line each. Exactly the triad's reserve of 30 queries remains. |
| `doctors/` | Six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL; the citation record carries the 42-claim registry parsed from the proposal) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | `estimator.py` (the registered estimator and decision rules as code); S1 `mech-sim.py` and `.json` (identification: per-token decay clamp against r = 2 in six worlds); S2 `power-sim.py` and `.json` (operating characteristics of every threshold); S3 `cost-model.py` and `.json` (tokens, GPU-hours, caps, ladder); S4 `resegment.py` and `.json` (the splitting rules on both real tokenizers); `build-query-log.py`; `build-doctors.py`; `snapshot-sources.py`; `build-bundle.py`; `attestations-not-run.md`; `blind-roles.json` (role map for the recorder; never give it to the critic). |
| `blind/` | Two anonymized mechanism paragraphs: the proposal's and the closest prior's (arXiv 2609.33093). File names carry no role. |

Reproduce from the worktree root (S1 to S3 are seeded and deterministic; S4 is
deterministic given the two tokenizer files, which are in the session
scratchpad and pinned by SHA-256 in `bundle.json`):

```bash
B=program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition
OMP_NUM_THREADS=2 .venv/bin/python $B/compute/mech-sim.py $B/compute/mech-sim.json      # about 10 minutes
OMP_NUM_THREADS=2 .venv/bin/python $B/compute/power-sim.py $B/compute/power-sim.json
.venv/bin/python $B/compute/cost-model.py $B/compute/cost-model.json
.venv/bin/python $B/compute/resegment.py <m-a-p tokenizer.json> <rwkv_vocab_v20230424.txt> $B/snapshots $B/compute/resegment.json
python3 $B/compute/snapshot-sources.py program/proposals/2026-10-10-e5-gate-fertility-decomposition.md $B/snapshots
python3 $B/compute/build-doctors.py
python3 $B/compute/build-bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e5-gate-fertility-decomposition.md
```

`build-query-log.py` reads the session scratchpad and reproduces the log only
inside that session; the log records every raw file's digest.

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and both
  reviewers run after synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended to `program/gauntlet/` after the
  reviewers score.
- **Compute attestations.** No harness, adapter, manifest, container smoke,
  Slurm dry run or provenance check exists for this step; subject G's weights
  are not on the host and its licence is unresolved
  (`compute/attestations-not-run.md`). There is no executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.

## Fresh run under D68: the repair (2026-10-10)

Wave 1 scored 54 (all three refuters refuted; honest exit on the query
budget). D68 ordered one CPU repair by a single owner and a fresh gauntlet run
with new budgets (queries 80 with at least 30 reserved for the triad, wall
600 minutes, tokens 8,000,000, dollars 150, one wave, 0.3 GPU-h for reviewer
inference). The draft registration is now
`program/preregistrations/e5-gate-fertility-decomposition-v2.md` (v1 is kept
unedited). Wave 1's files above are kept as they were; this run adds:

| Path | Contents |
|---|---|
| `compute/repair-d68/estimator_v2.py` | The v2 registered estimator: held-out operating-point rule (K ladder 4, 8, 16 with a ceiling of 90; f ladder 2.7, 2.0 with a native floor of 30), the 2 x 2 factorial contrasts (TNIE, PNIE, INT, PNDE), the guessing-corrected scale, the cluster-robust normal interval, the reading rules and the overall rule |
| `compute/repair-d68/power-sim-v2.py`, `merge-power-v2.py`, `power-sim-v2.json` | S2v2: the whole v2 decision path through the registered estimator (six parts merged) |
| `compute/repair-d68/mech-sim-v2.py`, `merge-mech-v2.py`, `mech-sim-v2.json` | S1v2: identification in a two-layer toy with state-dependent writes, through the registered path (one process per world, merged) |
| `compute/repair-d68/int-sign-probe.py`, `.json` | Direct probe of where the decay-by-write interaction changes sign and whether that region is admissible |
| `compute/repair-d68/superseded-floor40/` | The S2v2 and S1v2 outputs under the native floor of 40 that the repair tried first and dropped, kept unedited |
| `compute/repair-d68/cost-model-v2.py`, `.json` | S3v2: tokens, GPU-hours, caps and ladder per (K_p, f_p) branch |
| `compute/repair-d68/build-query-log-run2.py`, `query-log-run2.json` | This run's 12 counted orx queries, 2 failed OpenAlex calls, 8 full-text reads and 6 citation-graph lookups |
| `compute/repair-d68/build-doctors-v2.py`, `doctors/*.json` | The six doctor records rewritten for this run |
| `compute/repair-d68/build-bundle-v2.py`, `bundle.json` | The bundle rebuilt for this run |
| `compute/repair-d68/blind-roles-run2.json`, `blind/paragraph-bab395c3.txt`, `paragraph-e2ac6471.txt`, `paragraph-3f647ca8.txt` | Fresh anonymized packets: the proposal and the two closest priors (role map for the recorder only) |

Reproduce from the worktree root (seeded; the development Mac was saturated
by other work while these ran, so wall times inside the outputs are not
representative):

```bash
C=program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/compute/repair-d68
OUT=$(mktemp -d)
for p in misc grid0 grid1 tau prof0 prof1; do .venv/bin/python $C/power-sim-v2.py $OUT/power-$p.json $p; done
python3 $C/merge-power-v2.py $OUT $C/power-sim-v2.json
for w in W1_per_token_clock W2_self_normalised_interference W3_clock_and_interference W4_null W5_legacy_duplicates W6_partial W7_decay_inert W8_line W9_erase_dominated; do .venv/bin/python $C/mech-sim-v2.py $OUT/mech-${w:0:2}.json $w; done
python3 $C/merge-mech-v2.py $OUT $C/mech-sim-v2.json
.venv/bin/python $C/int-sign-probe.py $C/int-sign-probe.json
.venv/bin/python $C/cost-model-v2.py $C/cost-model-v2.json
python3 program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/compute/snapshot-sources.py program/proposals/2026-10-10-e5-gate-fertility-decomposition.md program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/snapshots
python3 $C/build-doctors-v2.py && python3 $C/build-bundle-v2.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e5-gate-fertility-decomposition.md
```

The doctor still reports FAIL: no executable pilot, no compute attestation,
no reviews for this run yet and no trusted signing store (D24). That is the
expected and honest state.
