# Evidence bundle: R01 first step gauntlet (wave 1 synthesis)

Proposal: `program/proposals/2026-10-11-r01-rerun-noise-sources.md`.
Draft registration: `program/preregistrations/r01-rerun-noise-sources-v1.md` (DRAFT, new
experiment id, not frozen, no ledger row). Schema: `program/proposals/evidence/_schema.json`.
Index and hashes: `bundle.json`, built by `compute/build_bundle.py`.

The synthesis ran on 2026-10-11 on the development Mac's CPU, from four independent discovery
cells (frontier, kill-shot, cross-domain, asset). It ran no search of its own and made no host
contact: it worked from the asset cell's read-only copy of S1a's step and reply logs, after
checking all 3,616 files against the committed per-job host listings.

| Path | Contents |
|---|---|
| `compute/pilot/orx-run-83ee815a-...log` | The executable pilot: Stage A0 as orx cpu-doctor node `ff110047` (branch `orx/r01-stage-a0-records-census`, commit `ca3cdbf`), run `83ee815a-426a-4b94-a93f-cc1277972d76` on the local backend with the project's fixed run command; `ORX_RESULT ... exit=0`. Its receipt is byte-identical to `program/evidence/2026-10-11/r01-stage-a0/census.json` |
| `compute/power_r01.py`, `power-r01.json` | Operating characteristics of every registered threshold: the DET gate (exact and beta-binomial), the Stage B readings (episode-cluster bootstrap, text and IR level), the A1 census, Stage C's environment readings (task-cluster bootstrap, homogeneous and concentrated), the K6 prediction (frozen against live rerun noise on a K = 113 contrast), the slate's dropped closed loop (CL) and the step-kick predictions (PRED). Seeds 42, 43, 44 |
| `compute/caps_r01.py`, `caps-r01.json` | Per-request prices from S1a's per-step records and per-job caps under the design study's realized-cost rule |
| `compute/build_query_log.py`, `query-log.json` | The cells' queries with returned ids (103 counted orx discover queries; 18 other searches; 2 failed calls), reads by cell, PRISMA counts, raw-output digests of the frontier, kill-shot and asset cells |
| `snapshots/` | One record per primary URL the proposal cites (HTTP status, fetch time, SHA-256 and size of the body, an arXiv metadata extract or the HTML title). No page bodies. The four OpenReview records are HTTP 200 browser-challenge pages and verify nothing about content |
| `doctors/` | Six preflight doctor records (Source, Citation, Design and Safety PASS; Novelty and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. `citation.json` holds the claim registry C01-C30 and R1-R4 |
| `blind/` | Two anonymized mechanism paragraphs for the blind critic. Their roles are in `compute/blind-roles.json` (recorder only; never give it to the critic) |
| `compute/attestations-not-run.md` | Which compute attestations do not exist yet and why |
| `compute/snapshot-sources.py`, `compute/write_doctors.py`, `compute/build_bundle.py` | Builders |

Reproduce from the worktree root:

```bash
python3 scripts/run_r01_stage_a0_doctor.py --output OUT.json   # byte-identical to the committed census
E=program/proposals/evidence/2026-10-11-r01-rerun-noise-sources/compute
OMP_NUM_THREADS=4 .venv/bin/python $E/power_r01.py --a1 program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl \
    --census program/evidence/2026-10-11/r01-stage-a0/census.json --out $E/power-r01.json
python3 $E/caps_r01.py --out $E/caps-r01.json
python3 $E/build_query_log.py --out program/proposals/evidence/2026-10-11-r01-rerun-noise-sources/query-log.json
python3 $E/snapshot-sources.py program/proposals/2026-10-11-r01-rerun-noise-sources.md program/proposals/evidence/2026-10-11-r01-rerun-noise-sources/snapshots
python3 $E/write_doctors.py
python3 $E/build_bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-11-r01-rerun-noise-sources.md
```

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and both reviewers run after
  the synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended to
  `program/gauntlet/2026-10-11-r01-rerun-noise-sources.jsonl` after the reviewers score.
- **Compute attestations for Stages A1, B and C** (`compute/attestations-not-run.md`).

The deterministic doctor therefore reports FAIL. That is the expected and honest state.
