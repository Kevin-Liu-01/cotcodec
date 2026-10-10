# Evidence bundle: E7 G1 floor gate (e7-equivariant-writes-g1-v1) gauntlet, wave 1

Proposal: `program/proposals/2026-10-10-e7-equivariant-writes-g1.md`.
Draft registration: `program/preregistrations/e7-equivariant-writes-g1-v1.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(rebuilt by `compute/build-bundle.py`).

Built on 2026-10-10 by the gauntlet's single synthesis owner (D67) from four
independent discovery cells (frontier, kill-shot, cross-domain, asset and
cost) of the E7 gauntlet workflow.
- The cells' queries were parsed from their raw orx outputs in the session
  scratchpad into `query-log.json`, with each raw file's SHA-256 recorded.
- No GPU and no host job was used. All CPU work ran on the development Mac.
- The host was read once with `squeue` (queue empty at 21:25 UTC).

| Path | Contents |
|---|---|
| `snapshots/` | One record per primary URL the proposal cites (49): HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (for arXiv: title, authors, version history and abstract, which are CC0; for other pages: the HTML title). No page bodies or paper texts are stored. The three OpenReview records are HTTP 200 browser-challenge pages ("Verifying your browser"); they verify nothing about content, and those claims rest on abstracts from the OpenReview search API. |
| `query-log.json` | Every retrieval call: 97 counted orx discover queries (frontier 46, kill-shot 23, cross-domain 24, synthesis 4) with returned ids and raw-output SHA-256; 63 uncounted log entries (OpenReview, web, GitHub, Hugging Face, curl, paper reads). 97 are counted against the declared 150, leaving 53; the triad's reserve of 30 is intact. |
| `cells/cell-verdicts.json` | One-paragraph summaries of the four cells' verdicts, counts and coverage limits. |
| `doctors/` | Six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | The scripts and outputs listed below this table. |
| `blind/` | Two anonymized mechanism paragraphs: the proposal's and the closest prior's (arXiv 2610.06750, Balancing Memory Pathways). File names carry no role. |

Contents of `compute/`:
- S1 `gate-sim.py` and `.json`: operating characteristics of the registered
  decision rule under assumed distributions; 1,000 replicates per scenario;
  seeds 42, 43, 44.
- S2 `cost-model.py` and `.json`: GPU-hour estimate, caps under D22's
  counting rule and the throughput gate. The base is the measured 282,501.4
  tokens/s (Slurm 359).
- S3 `reach-doctor.py` and `.json`: the state-free reach of the A0 layer
  graph by complex-step derivative on a NumPy stand-in. PASS: nonzero at
  1,560 and exactly zero at 1,561 with the state cut, in three seeds. It also
  reports the initial decay-timescale shares under fla 0.5.2's
  initialization.
- `legacy-phase0-doctor-main.json`: the asset cell's rerun of the legacy
  phase-0 object doctor on main (PHASE0_OBJECT_DOCTOR_PASS, 11/11, payload
  SHA-256 equal to the value registered on 2026-09-01; synthetic objects
  only).
- `build-query-log.py`, `snapshot-sources.py`, `build-bundle.py`.
- `attestations-not-run.md`.
- `blind-roles.json`: the role map for the recorder. Never give it to the
  critic.

Reproduce from the worktree root (S1, S2 and S3 are seeded and deterministic):

```bash
OMP_NUM_THREADS=1 .venv/bin/python program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/gate-sim.py program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/gate-sim.json 1000 6
python3 program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/cost-model.py program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/cost-model.json
OMP_NUM_THREADS=1 .venv/bin/python program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/reach-doctor.py program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/reach-doctor.json
python3 program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/snapshot-sources.py program/proposals/2026-10-10-e7-equivariant-writes-g1.md program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/snapshots/
python3 program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/build-bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e7-equivariant-writes-g1.md
```

`build-query-log.py` reads the session scratchpad and reproduces the log only
inside that session; the log records every raw file's digest. One snapshot
(the fla source page on GitHub) returned HTTP 503 on the first pass and was
refetched on its own, with HTTP 200.

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and both
  reviewers run after synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended to `program/gauntlet/` after the
  reviewers score.
- **Compute attestations.** No harness, adapter, manifest, container smoke,
  Slurm dry run or provenance check exists for this gate. The 1.04B-token
  data pool is not on the host (`compute/attestations-not-run.md`). There is
  no executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.
