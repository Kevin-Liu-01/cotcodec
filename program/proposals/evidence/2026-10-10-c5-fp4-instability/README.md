# Evidence bundle: C5 Phase 0 and Phase 1 design (c5-fp4-instability-v1) gauntlet, wave 1

Proposal: `program/proposals/2026-10-10-c5-fp4-instability.md`.
Draft registration: `program/preregistrations/c5-fp4-instability-v1.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(rebuilt by `compute/build-bundle.py`).

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
