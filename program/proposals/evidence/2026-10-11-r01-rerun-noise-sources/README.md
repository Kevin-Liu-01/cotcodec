# Evidence bundle: R01 first step gauntlet (wave 1, then the D75 repair for a fresh run)

Proposal: `program/proposals/2026-10-11-r01-rerun-noise-sources.md` (repaired under D75).
Draft registration: `program/preregistrations/r01-rerun-noise-sources-v2.md` (DRAFT, new
experiment id, not frozen, no ledger row); v1 (`r01-rerun-noise-sources-v1.md`) is superseded and
left unedited. Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`,
now built by `compute/repair-d75/build_bundle_v2.py` (wave 1's `compute/build_bundle.py` is kept).

Wave 1 (2026-10-11, score 58; record `program/gauntlet/2026-10-11-r01-rerun-noise-sources.jsonl`,
row hash `22639b76...`) ran four discovery cells, a single-owner synthesis, a blind critic, the
refute-first triad and two reviewers. The D75 repair ran on the development Mac's CPU by a single
owner: no GPU, no host job, read-only ssh only for `squeue` and one relay fetch attempt.

| Path | Contents |
|---|---|
| `compute/pilot/orx-run-83ee815a-...log` | The executable pilot: Stage A0 as orx cpu-doctor node `ff110047` (run `83ee815a-426a-4b94-a93f-cc1277972d76`, `ORX_RESULT ... exit=0`); receipt byte-identical to `program/evidence/2026-10-11/r01-stage-a0/census.json` |
| `compute/repair-d75/power_r01_v2.py`, `power-r01-v2.json` | Repair: operating characteristics of every v2 decision rule under the registered estimator (`harness/r01/estimators.py`): DET on 226 pairs, the step-1 and step-2 cell readings, VAL against S1a's own step-1 data, decisiveness under five scenarios, the A1 census, the wave-1 blocks for Stage C, P-K6 and the dropped closed loop, and the two-stage model (S1a validation, D_w sensitivity, removal predictions with paired intervals). Seeds 42, 43, 44; run as four parallel parts joined with `--merge` |
| `compute/repair-d75/caps_r01_v2.py`, `caps-r01-v2.json` | Repair: caps repriced with arithmetic on S1a's realized step-1 and step-2 costs (`harness/r01/caps.py`); loaded passes simulated as the slowest of 20 lanes; overrun probabilities at the caps; the CPU lane from S1a's realized boot overhead |
| `compute/repair-d75/build_query_log_run2.py`, `query-log-run2.json` | Repair: this run's 15 counted orx discover queries with returned ids and raw-output digests, 8 uncounted reads, 2 uncounted fetch attempts, PRISMA counts |
| `compute/repair-d75/snapshot_new_sources.py` | Repair: snapshots of the six newly cited sources (wave-1 snapshots kept as fetched) |
| `compute/repair-d75/write_doctors_v2.py`, `doctors/` | Repair: the six preflight doctor records rewritten for the repaired candidate (Source, Citation, Design and Safety PASS, Design self-assessed; Novelty and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py` |
| `compute/repair-d75/blind-roles-run2.json`, `blind/` | Repair: fresh anonymized paragraphs, the proposal (`paragraph-3fe4da7c.txt`), cELldjX2oq (`paragraph-69e5c3ef.txt`) and Summers and Dinneen 2021 (`paragraph-d8ac91b5.txt`) for a second critic call; wave 1's two paragraphs are kept. The roles file is for the recorder only |
| `compute/repair-d75/pytest-r01.txt` | Repair: the R01 test run on the Mac (`harness/r01/` against fakes) |
| `compute/attestations-not-run.md` | What exists after the repair and which compute attestations still do not |
| `compute/power_r01.py`, `power-r01.json`, `caps_r01.py`, `caps-r01.json`, `build_query_log.py`, `query-log.json`, `write_doctors.py`, `snapshot-sources.py`, `build_bundle.py`, `blind-roles.json` | Wave 1, kept unchanged (v1 design) |
| `snapshots/` | One record per primary URL the proposal cites (HTTP status, fetch time, body SHA-256, an arXiv metadata extract or the HTML title). The OpenReview records are HTTP 200 browser-challenge pages |

Reproduce from the worktree root:

```bash
uv run --locked --extra dev pytest -q tests/test_r01_*.py
python3 scripts/run_r01_stage_a0_doctor.py --output OUT.json   # byte-identical to the committed census
E=program/proposals/evidence/2026-10-11-r01-rerun-noise-sources/compute/repair-d75
PYTHONPATH=. uv run --locked python $E/caps_r01_v2.py --out $E/caps-r01-v2.json
for p in B_det,B_cells VAL,A1_cen DECISIVE PRED,V1; do
  PYTHONPATH=. uv run --locked python $E/power_r01_v2.py --reps 300 --only $p --out part-${p/,/_}.json; done
PYTHONPATH=. uv run --locked python $E/power_r01_v2.py --merge part-*.json --out $E/power-r01-v2.json
python3 $E/write_doctors_v2.py
python3 $E/build_bundle_v2.py
uv run --locked python scripts/research_direction_doctor.py program/proposals/2026-10-11-r01-rerun-noise-sources.md
```

Not present, by design or because it does not exist yet:

- **This run's review receipts.** The blind critic, the triad and both reviewers run after the
  repair. No trusted Ed25519 store exists (D24).
- **This run's hash-chained audit row.** Appended after its reviewers score.
- **Compute attestations** for A1, B and C (`compute/attestations-not-run.md`).

The deterministic doctor therefore reports FAIL. That is the expected and honest state.
