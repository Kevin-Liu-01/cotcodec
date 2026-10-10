# Evidence bundle: E4 gate (e4-icl-write-rule-gate-v1) gauntlet, wave 1

Proposal: `program/proposals/2026-10-10-e4-icl-write-rule-gate.md`.
Draft registration: `program/preregistrations/e4-icl-write-rule-gate-v1.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(rebuilt by `compute/build-bundle.py`).

Built on 2026-10-10 by the gauntlet's single synthesis owner (D58) from four
independent discovery cells (frontier, kill-shot, cross-domain, asset-cost) of
workflow `wf_9f15e9e8-487`, whose structured results are copied into
`query-log.json`. No GPU and no host job was used; all CPU work ran on the
development Mac.

| Path | Contents |
|---|---|
| `snapshots/` | One record per primary URL the proposal cites (36): HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, which are CC0; other pages: the HTML title). No page bodies or paper texts. |
| `query-log.json` | Every retrieval call: the cells' 144 counted discover queries and 63 paper reads with returned ids, and synthesis queries SQ1 to SQ6 with returned ids, raw-output digests and screening counts; 10 synthesis paper reads with text digests. 150 counted against the declared 150. |
| `doctors/` | Six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | S1 `oracle-class-semantics.py` and `.json` (linear surrogate: replicates KILL A at the legacy rank-8 port and checks that the nested state classes separate key-span teachers from retrieval and value-directed teachers at a full-rank port); S2 `decision-sim.py` and `.json` (operating characteristics of the registered decision rules under assumed noise); S3 `cost-model.py` and `.json` (GPU-hour estimate and caps); `snapshot-sources.py`; `build-bundle.py`; `attestations-not-run.md`; `blind-roles.json` (role map for the recorder; never give it to the critic). |
| `blind/` | Two anonymized mechanism paragraphs: the proposal's and the closest prior's (arXiv 2608.13385). File names carry no role. |

Reproduce from the worktree root (all randomness seeded from scenario keys;
process count does not change results):

```bash
OMP_NUM_THREADS=1 .venv/bin/python program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/compute/oracle-class-semantics.py s1.json 8
OMP_NUM_THREADS=2 .venv/bin/python program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/compute/decision-sim.py s2.json
python3 program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/compute/cost-model.py
python3 program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/compute/snapshot-sources.py program/proposals/2026-10-10-e4-icl-write-rule-gate.md snapshots/
python3 program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/compute/build-bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e4-icl-write-rule-gate.md
```

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and both
  reviewers run after synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended to `program/gauntlet/` after the
  reviewers score.
- **Compute attestations.** No harness, adapter, manifest, container smoke,
  Slurm dry run or provenance check exists for this gate
  (`compute/attestations-not-run.md`). There is no executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.
