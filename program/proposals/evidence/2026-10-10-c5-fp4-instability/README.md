# Evidence bundle: C5 Phase 0 and Phase 1 design gauntlet (wave 1: c5-fp4-instability-v1; run 2 after the D68 repair: c5-fp4-instability-v2)

Proposal: `program/proposals/2026-10-10-c5-fp4-instability.md`.
Draft registration: `program/preregistrations/c5-fp4-instability-v2.md` (DRAFT, not frozen; supersedes v1, which is left unedited).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(rebuilt by `compute/repair-d68/build-bundle-v2.py` since the repair; wave 1's
`compute/build-bundle.py` is kept as it was).

Built on 2026-10-10 by the gauntlet's single synthesis owner (D67) from four
independent discovery cells (frontier, kill-shot, cross-domain, asset and cost)
of gauntlet wave 1. Their queries were parsed from the cells' raw orx outputs
in the session scratchpad into `query-log.json` (each raw file's SHA-256
recorded). No GPU and no host job was used; all CPU work ran on the development
Mac. The host was read once (`squeue` empty, all eight GPUs at 0 MiB,
2026-10-10T21:21:22Z) and used twice as a read-only Semantic Scholar relay.

| Path | Contents |
|---|---|
| `snapshots/` | One record per primary URL the proposal cites (47): HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, CC0; other pages: the HTML title). No page bodies or paper texts. The six OpenReview records are HTTP 200 browser-challenge pages; they verify nothing about content, and those claims rest on abstracts from the OpenReview search API. |
| `query-log.json` | Every retrieval call: 114 counted orx discover invocations (frontier 38, kill-shot 26, cross-domain 35, asset 8, synthesis 7; 11 rejected by the backend) with returned ids and raw-output SHA-256; uncounted OpenReview, Semantic Scholar, Hugging Face, web and paper-read records. 36 of the declared 150 remain, above the refuters' reserve of 30. |
| `doctors/` | Six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | N1 `numerics.py` / `.json` (exact representability, codebooks, metamorphic identity, storage, the 2505.19115 Table 4 SD, tie handling); N2 `crest_prediction.py` / `crest-prediction.json` (numpy reference quantizer; tensor-level grid effect per scale configuration); D1 `doe.py` / `.json` (estimability, contrast SEs); S1 `power_sim.py` / `power-sim.json` (decision-rule operating characteristics with LR tuning; SR test power; exact Spearman critical values); S2 `cost_model.py` / `cost-model.json` (Phase 0 caps, Phase 1 projections); `build-query-log.py`; `snapshot-sources.py`; `build-bundle.py`; `attestations-not-run.md`; `blind-roles.json` (role map for the recorder; never give it to the critic). |
| `blind/` | Two anonymized mechanism paragraphs: the proposal's and the closest prior's (arXiv 2505.19115). File names carry no role. |

Reproduce from the worktree root (N1, N2, D1, S1 and S2 are seeded and deterministic; numpy and scipy only):

```bash
D=program/proposals/evidence/2026-10-10-c5-fp4-instability/compute
OMP_NUM_THREADS=2 .venv/bin/python $D/numerics.py $D/numerics.json
OMP_NUM_THREADS=2 .venv/bin/python $D/crest_prediction.py $D/crest-prediction.json
.venv/bin/python $D/doe.py $D/doe.json
.venv/bin/python $D/power_sim.py $D/power-sim.json
.venv/bin/python $D/cost_model.py $D/cost-model.json
python3 $D/snapshot-sources.py program/proposals/2026-10-10-c5-fp4-instability.md program/proposals/evidence/2026-10-10-c5-fp4-instability/snapshots/
python3 $D/build-bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-c5-fp4-instability.md
```

`build-query-log.py` reads the session scratchpad and reproduces the log only
inside that session; the log records every raw file's digest.

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and both
  reviewers run after synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended to `program/gauntlet/` after the
  reviewers score.
- **Compute attestations.** No harness, quantizer kernels, data on the host,
  manifest, container smoke, Slurm dry run or provenance check exists
  (`compute/attestations-not-run.md`). There is no executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.

## Run 2: the D68 repair (2026-10-10)

Wave 1 scored 54 (`program/gauntlet/2026-10-10-c5-fp4-instability.jsonl`,
row 1). D68 ordered one CPU-only repair by a single owner and a fresh run with
new budgets (queries 80 with at least 30 reserved for the refuters, wall 600
minutes, tokens 8M, dollars 150, waves 1, GPU 0.3 for reviewer inference).
The repair added, without editing any wave-1 file except this README, the
doctor records (re-evaluated for v2), `compute/attestations-not-run.md`
(appended) and `bundle.json` (rebuilt):

| Path | Contents |
|---|---|
| `query-log-run2.json` | Run 2's 16 counted retrieval queries (orx keyword 10, embedding 2, OpenAlex 2 rejected with HTTP 429, OpenReview search 2) with raw-output SHA-256 and returned ids; the three uncounted full-text reads (2510.25602, 2302.08007, the ARITH 2025 study from its NSF PAR copy) with text hashes; PRISMA counts. 64 queries remain, 30 of them reserved for the triad. |
| `compute/repair-d68/numerics_v2.py`, `numerics-v2.json` | N2v2 and N3: the registered quantizer on the ten v2 cells; whole-tensor and per-row QSNR; UE4M3 subnormal and clamp shares; every v2 contrast; the identification table under exact-scale and wide-UE4M3 toggles. |
| `compute/repair-d68/doe_v2.py`, `doe-v2.json` | D1v2: rank 10 of 10; contrast SEs and MDEs at n = 3 to 6; the seed-count thresholds. |
| `compute/repair-d68/power_sim_v2.py`, `power-sim-v2.json` | S1v2: the registered v2 decision path end to end (probe, G1, seed count, sweeps, RCBD, P2, range flag, secondary verdicts) over nine truths, three effect sizes, three sigmas, two seed correlations and two LR curvatures, with v1's gate reuse replayed on the same data; the exact Spearman critical value for 10 cells. |
| `compute/repair-d68/cost_model_v2.py`, `cost-model-v2.json` | S2v2: J0 to J3 caps from their workloads, the J4 formula and when it fits under 8 GPU-h, Part B caps with every factor applied, wave 1's caps recomputed. |
| `compute/repair-d68/build-query-log-run2.py`, `snapshot-new-sources.py`, `build-bundle-v2.py` | Builders for the run-2 query log, the four new snapshots and this bundle. |
| `compute/repair-d68/blind-roles-run2.json` | Role map for run 2's blind packets (recorder only; never give it to the critic). |
| `blind/paragraph-65332d00.txt`, `blind/paragraph-ad76d839.txt` | Run 2's anonymized mechanism paragraphs: the proposal's and the mechanism prior's (2510.25602 Theorems 1-2 with the ARITH 2025 study's Insights 3 and 5). Wave 1's design-prior paragraph (`paragraph-201f330b.txt`) is kept as an additional packet; wave 1's proposal paragraph (`paragraph-43655420.txt`) is superseded. |

Reproduce run 2's computations from the worktree root (seeded and
deterministic; numpy and scipy only; on a loaded machine S1v2 takes tens of
minutes):

```bash
D=program/proposals/evidence/2026-10-10-c5-fp4-instability/compute/repair-d68
OMP_NUM_THREADS=2 .venv/bin/python $D/numerics_v2.py $D/numerics-v2.json
.venv/bin/python $D/doe_v2.py $D/doe-v2.json
OMP_NUM_THREADS=2 .venv/bin/python $D/power_sim_v2.py $D/power-sim-v2.json
.venv/bin/python $D/cost_model_v2.py $D/cost-model-v2.json
python3 $D/build-bundle-v2.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-c5-fp4-instability.md
```

Wave 1's five computations reproduce byte for byte (checked on 2026-10-10).
The deterministic doctor still reports FAIL: no reviews of this run yet, no
executable pilot, no trust store (D24).
