# Evidence bundle: C3 Stage-0 gate (c3-selection-allocation-gate-v1) gauntlet, wave 1

Proposal: `program/proposals/2026-10-10-c3-selection-allocation-gate.md`.
Draft registration: `program/preregistrations/c3-selection-allocation-gate-v1.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(rebuilt by `compute/build-bundle.py`).

Built on 2026-10-10 by the gauntlet's single synthesis owner (D64) from four
independent discovery cells (frontier, kill-shot, cross-domain, asset and cost)
of workflow `gauntlet-c3-wave1`. Their queries were parsed from the cells' raw
orx outputs in the session scratchpad into `query-log.json` (each raw file's
SHA-256 recorded). No GPU and no host job was used; all CPU work ran on the
development Mac. The host was read once with `squeue` (S1a jobs 1062 and 1064
were running).

| Path | Contents |
|---|---|
| `snapshots/` | One record per primary URL the proposal cites (54): HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, CC0; other pages: the HTML title). No page bodies or paper texts. The five OpenReview records are HTTP 200 browser-challenge pages ("Verifying your browser"); they verify nothing about content, and those claims rest on abstracts from the OpenReview search API. |
| `query-log.json` | Every retrieval call: 127 counted orx discover queries (frontier 45, kill-shot 39, cross-domain 31, asset 12, synthesis 0) with returned ids and raw-output SHA-256; 24 uncounted OpenReview, web and OpenAlex API searches; 3 fetch failures; paper reads; the cells' verdicts in one line each. 127 counted against the declared 150, leaving 23, which is 7 short of the triad's reserve of 30. |
| `doctors/` | Six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | S1 `gate-sim.py` and `.json` (operating characteristics of lines D, F, S and H; identification of the dossier's spread target; assumed distributions; seeds 42/43/44); S2 `cost-model.py` and `.json` (GPU-hour estimate, cap formula and N rule, calibrated on probe v1 job B's dummy-weight Qwen3-8B points); `build-query-log.py`; `snapshot-sources.py`; `build-bundle.py`; `attestations-not-run.md`; `blind-roles.json` (role map for the recorder; never give it to the critic). |
| `blind/` | Two anonymized mechanism paragraphs: the proposal's and the closest prior's (arXiv 2608.17124, CASE). File names carry no role. |

Reproduce from the worktree root (S1 and S2 are seeded and deterministic):

```bash
OMP_NUM_THREADS=2 .venv/bin/python program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/compute/gate-sim.py program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/compute/gate-sim.json
.venv/bin/python program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/compute/cost-model.py program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/compute/cost-model.json
python3 program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/compute/snapshot-sources.py program/proposals/2026-10-10-c3-selection-allocation-gate.md program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/snapshots/
python3 program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/compute/build-bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-c3-selection-allocation-gate.md
```

`build-query-log.py` reads the session scratchpad and reproduces the log only
inside that session; the log records every raw file's digest.

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and both
  reviewers run after synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended to `program/gauntlet/` after the
  reviewers score.
- **Compute attestations.** No harness, adapter, manifest, container smoke,
  Slurm dry run or provenance check exists for this gate, and Qwen3-8B's
  weights are not on the host (`compute/attestations-not-run.md`). There is no
  executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.
