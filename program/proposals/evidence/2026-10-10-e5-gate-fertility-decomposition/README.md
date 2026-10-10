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
