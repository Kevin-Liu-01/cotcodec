# Evidence bundle: E7 G1 floor gate gauntlet (wave 1 and the D68 repair for a fresh run)

Proposal: `program/proposals/2026-10-10-e7-equivariant-writes-g1.md`.
Draft registration: `program/preregistrations/e7-equivariant-writes-g1-v2.md` (DRAFT, not
frozen; supersedes `e7-equivariant-writes-g1-v1.md`, which wave 1 reviewed and which is left
unedited). Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`,
rebuilt for this run by `compute/repair-d68/build-bundle-v2.py` (wave 1's
`compute/build-bundle.py` is kept as it was).

Wave 1 (2026-10-10) was built by the gauntlet's single synthesis owner (D67) from four
independent discovery cells; its record is row 1 of
`program/gauntlet/2026-10-10-e7-equivariant-writes-g1.jsonl` (score 51). The D68 repair was
done by a single owner on the development Mac (CPU only, no GPU, no host contact). Its
artifacts are under `compute/repair-d68/`, its queries in `query-log-run2.json`, and its blind
packets in `blind/` with the role map `compute/repair-d68/blind-roles-run2.json`.

| Path | Contents |
|---|---|
| `snapshots/` | One record per primary URL the proposal cites: HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history and abstract, CC0; other pages: the HTML title). No page bodies or paper texts. OpenReview records are HTTP 200 browser-challenge pages and verify nothing about content. Wave 1's records are unedited; the repair added records for new URLs only (`compute/repair-d68/snapshot-new-sources.py`, field `snapshot_run`). |
| `query-log.json` | Wave 1: 97 counted orx discover queries of the four cells and synthesis, with returned ids and raw-output SHA-256; 63 uncounted entries. |
| `query-log-run2.json` | This run: the repair's 37 counted retrieval queries (orx keyword 16, embedding 6, OpenAlex 5 of which 4 returned HTTP 429; OpenReview 4; ACL Anthology 4 over the cached full bibliography; OpenAlex citing works 2) with returned ids and raw-output SHA-256; 7 uncounted full-text reads; PRISMA counts. 43 of the 80 declared queries remain; at least 30 are reserved for the triad. |
| `cells/cell-verdicts.json` | Wave 1's four discovery cells' verdicts, counts and coverage limits. |
| `doctors/` | Six preflight doctor records, updated for this run (each carries `supersedes_sha256`): Source, Citation and Safety PASS; Novelty, Design and Compute FAIL. The verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | Wave 1's S1 `gate-sim.py`, S2 `cost-model.py`, S3 `reach-doctor.py` with outputs (unedited); the legacy phase-0 doctor rerun; wave 1's builders; `attestations-not-run.md` (updated for v2); `blind-roles.json` (wave 1's role map). |
| `compute/repair-d68/` | The D68 repair's checks, listed below. |
| `blind/` | Anonymized mechanism paragraphs. Wave 1: `paragraph-803016fc.txt` (proposal) and `paragraph-36695b43.txt` (2610.06750). This run: a fresh proposal paragraph, a fresh 2610.06750 paragraph and a SWAX paragraph; roles only in `compute/repair-d68/blind-roles-run2.json`. File names carry no role. |

Contents of `compute/repair-d68/`:
- S3v2 `reach-cut-v2.py` and `.json`: which evaluation intervention removes which path from the
  facts to the answer, by complex step on a NumPy reference of the registered module graph
  (width 16, RoPE SWA-512, fla-style GDN with conv, L2-normalised q and k, gated output norm),
  3 seeds x 7 distances x 12 modes x 2 perturbation sets = 504 rows, each checked against an
  independent symbolic reachability count (`reachable`). PASS: they agree on every row.
- P1 `instrument-pool-v2.py` and `.json`: the measured NTREX-128 pool (1,360 eligible, 699 in
  the registered test half), the v1, v2a (rejected) and v2 builders' cell sizes and surface
  oracle levels for real and decoy queries. Counts, rates and file hashes only.
- S1v2 `gate-sim-v2.py` and `.json`: the registration-v2 decision rule under the registered
  estimator (sentence-cluster percentile bootstrap, B = 2,000, seed 42) on the measured design;
  surface-only and decoy-quality scenarios; the v1 failure modes; decisiveness by world.
- S2v2 `cost-model-v2.py` and `.json`: caps under D22 with every job's arithmetic (466 min =
  7.767 GPU-h).
- `build-query-log-run2.py`, `snapshot-new-sources.py`, `build-bundle-v2.py`,
  `blind-roles-run2.json` (recorder only; never give it to a critic).

Reproduce from the worktree root (all seeded and deterministic; P1 needs a local NTREX-128
copy at commit 468c6b69 whose file hashes are recorded in its output):

```bash
OMP_NUM_THREADS=1 .venv/bin/python program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/reach-cut-v2.py program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/reach-cut-v2.json 12
.venv/bin/python program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/instrument-pool-v2.py <ntrex_dir> program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/instrument-pool-v2.json
OMP_NUM_THREADS=1 .venv/bin/python program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/gate-sim-v2.py program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/instrument-pool-v2.json program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/gate-sim-v2.json 1000 16
python3 program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/cost-model-v2.py program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/cost-model-v2.json
python3 program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/snapshot-new-sources.py program/proposals/2026-10-10-e7-equivariant-writes-g1.md program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/snapshots/
python3 program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/build-bundle-v2.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e7-equivariant-writes-g1.md
```

`build-query-log-run2.py` reads the session scratchpad's raw query log and reproduces the log
only inside that session; the log records every raw output's digest.

Not present, by design or because it does not exist yet:

- **Review receipts for this run.** The blind critic, the refute-first triad and both
  reviewers run after the repair. No trusted Ed25519 store exists (D24).
- **This run's hash-chained audit row.** Appended to `program/gauntlet/` after the reviewers
  score; wave 1's row is already there.
- **Compute attestations.** No harness, adapter, manifest, container smoke, Slurm dry run or
  provenance check exists for this gate, and the data are not on the host
  (`compute/attestations-not-run.md`). There is no executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and honest state.
