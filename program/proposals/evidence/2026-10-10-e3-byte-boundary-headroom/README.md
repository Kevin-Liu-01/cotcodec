# Evidence bundle: E3 Stage-0 headroom probe (e3-byte-boundary-headroom-v1) gauntlet, wave 1

Proposal: `program/proposals/2026-10-10-e3-byte-boundary-headroom.md`.
Draft registration: `program/preregistrations/e3-byte-boundary-headroom-v1.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(rebuilt by `compute/build_bundle.py`).

Built on 2026-10-10 by the gauntlet's single synthesis owner (D67) from four
independent discovery cells (frontier, kill-shot, cross-domain, asset and cost)
of workflow `gauntlet-e3-wave1`. Their queries were parsed from the cells' raw
orx outputs in the session scratchpad into `query-log.json`, with each raw
file's SHA-256. No GPU and no host job was used; all CPU work ran on the
development Mac. The host was read once with `squeue` (empty queue).

| Path | Contents |
|---|---|
| `snapshots/` | One record per primary URL the proposal cites (51): HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, CC0; other pages: the HTML title). No page bodies or paper texts. The four OpenReview records are HTTP 200 browser-challenge pages; they verify nothing about content, and those claims rest on abstracts from the OpenReview search API. |
| `query-log.json` | Every retrieval call: 118 counted orx discover calls (frontier 62, kill-shot 24, cross-domain 27, asset 5, synthesis 0; two failed with OpenAlex HTTP 429) with returned ids and raw-output SHA-256; 19 uncounted OpenReview, web and metadata calls; the cells' paper reads and synthesis re-reads. 118 counted against the declared 150 leaves 32, so the triad's reserve of 30 is intact. |
| `doctors/` | Six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | S1 `instrument_sim.py` and its merged output `instrument-sim.json` (the dossier's UOT instrument and projected boundary Dice under the same synthetic boundaries; instrument gates; decision-rule operating characteristics; calibration decomposition; seeds 42/43/44), `merge_sim.py`; S2 `cost_model.py` and `cost-model.json` (caps and arithmetic); `build_query_log.py`; `snapshot_sources.py`; `build_bundle.py`; `attestations-not-run.md`; `blind-roles.json` (role map for the recorder; never give it to the critic). |
| `blind/` | Two anonymized mechanism paragraphs: the proposal's and the closest prior's (arXiv 2502.06468, token alignability). File names carry no role. |

Reproduce from the worktree root (S1 and S2 are seeded and deterministic; S1
ran as 31 processes, one per seed and part and per condition, merged by
`merge_sim.py`; the exact per-process commands are in each output's `argv`):

```bash
PY=.venv/bin/python   # the simulations ran with the main checkout's venv: Python 3.13.14, numpy 2.5.2, scipy 1.18.0
D=program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom/compute
for s in 42 43 44; do
  OMP_NUM_THREADS=1 $PY $D/instrument_sim.py out/gates-$s.json --only gates --seeds $s
  for l in zh pl; do OMP_NUM_THREADS=1 $PY $D/instrument_sim.py out/uot-$s-$l.json --only uot --seeds $s --langs $l; done
  for c in zh-low zh-base pl-base zh-high ko-base ko-high; do OMP_NUM_THREADS=1 $PY $D/instrument_sim.py out/oc2-$s-$c.json --only oc --seeds $s --langs $c; done
done
OMP_NUM_THREADS=1 $PY $D/instrument_sim.py out/calibration.json --only calibration
python3 $D/merge_sim.py out $D/instrument-sim.json
python3 $D/cost_model.py $D/cost-model.json
python3 $D/snapshot_sources.py program/proposals/2026-10-10-e3-byte-boundary-headroom.md program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom/snapshots/
python3 $D/build_bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e3-byte-boundary-headroom.md
```

The merge also reads the superseded first operating-characteristics run
(`oc-<seed>.json`, made with an earlier version of the script before the
registered rule existed); its inputs' hashes are in `instrument-sim.json`.
`build_query_log.py` reads the session scratchpad and reproduces the log only
inside that session; the log records every raw file's digest.

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and both
  reviewers run after synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended to `program/gauntlet/` after the
  reviewers score.
- **Compute attestations.** No overlay image, scorer harness, manifest,
  container smoke, Slurm dry run or provenance check exists for this probe, and
  the H-Net checkpoints and FLORES+ are not on the host
  (`compute/attestations-not-run.md`). There is no executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.
