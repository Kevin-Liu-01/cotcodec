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


## Run 2: the D68 repair (2026-10-10)

The fresh gauntlet run after wave 1 (score 52) adds, without editing any wave-1
file except the doctor records (their wave-1 versions are in git history) and this
README:

| Path | Contents |
|---|---|
| `query-log-run2.json` | This run's 20 counted orx discover calls (R01-R20) with returned ids and raw-output SHA-256; 5 uncounted paper reads; metadata reads. Built by `compute/repair-run2/build_query_log_run2.py` from the repair's raw log (session scratchpad). |
| `blind/paragraph-fc068b40.txt`, `blind/paragraph-389fcff8.txt`, `blind/paragraph-5b22801e.txt` | Fresh anonymized mechanism paragraphs (role map `compute/repair-run2/blind-roles-run2.json`, recorder only). Wave 1's two packets are kept unchanged. |
| `compute/repair-run2/e3_estimator_v2.py` | The registered v2 estimator as code (target, matching, budget, floor, statistic, band and gold paths, decision rule). |
| `compute/repair-run2/instrument_sim_v2.py` | S1v2: synthetic EN-ZH-like pairs with a synchronous tree (straight and inverted nodes), an aligner error model calibrated to link AER with an error-correlation parameter, and the parts below; imports the estimator unchanged. |
| `calib.json` | Error-model calibration ((d, s) per target AER and split; seed 2042, 300 pairs per profile). |
| `atten-single-aligner.json`, `atten-consensus.json` | Attenuation maps (seed 42, 500 pairs per cell): per-aligner targets, then the consensus target over AER 0.05-0.25, correlation 0-1 and three splits. |
| `explore-targets.json`, `explore_targets.py` | Recorded design exploration (not decision-bearing) comparing ways to build the target from two aligners; it led to the consensus target. |
| `band_envelope.py`, `band-registered.json` | Band-path constants derived from the attenuation maps. `band.json` holds the provisional constants used inside the OC processes; their in-run verdicts are superseded by `oc_decide.py`. |
| `gates-v2.json`, `ident-v2.json`, `linem-v2.json` | Gates I1-I3 and budget diagnostics, wave 1's density and word-end scenario under v2, and the synthetic line M reference (seeds 42, 43, 44). `superseded/` holds the same three parts run before the consensus target was added (budget capped by the two aligners only), kept for the record. |
| `oc-merged.json`, `oc_decide.py`, `oc-decisions.json`, `oc_summary.py`, `oc-summary.json`, `oc-summary.md` | Operating characteristics: 24 condition-seed runs with per-replicate statistics; verdicts recomputed with the registered constants; summary tables. |
| `cost_model_v2.py`, `cost-model-v2.json` | S2v2: caps smoke 0.2 plus probe 0.7 = 0.9 GPU-h; central 0.26, high 0.63. |
| `merge_v2.py`, `build_bundle_v2.py` | Merging per-process outputs (each input's SHA-256 recorded) and rebuilding `bundle.json`. |

Reproduce S1v2 (Python 3.13.14, numpy 2.5.2, the main checkout's venv; each
process's argv is in the merged files' `inputs`):

```bash
PY=.venv/bin/python; R=program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom/compute/repair-run2
cd $R
for c in zh:balanced zh:precision_heavy zh:recall_heavy pl:balanced ko:balanced; do $PY instrument_sim_v2.py out/calib-${c/:/-}.json --part calib --seeds 2042 --cells $c; done
python3 merge_v2.py calib calib.json out/calib-*.json
# attenuation: --part atten --seeds 42 --pool 500 --cells profile:split:c:aerA:aerB ... (cells as listed in atten-*.json inputs)
python3 merge_v2.py part atten atten-consensus.json out/attenC-*.json out/attenC2-*.json
python3 band_envelope.py atten-consensus.json atten-single-aligner.json band-registered.json
for s in 42 43 44; do $PY instrument_sim_v2.py out/gatesC-$s.json --part gates --seeds $s --pool 1000; \
  $PY instrument_sim_v2.py out/identC-$s.json --part ident --seeds $s --pool 800; \
  $PY instrument_sim_v2.py out/linemC-$s.json --part linem --seeds $s --pool 800; done
# OC: --part oc --seeds S --profile zh --aer A B --c C [--split X] --pool 800 --reps 100 --boot 600 --gold-pool 400 --floor-draws 32 --gold-shifts ...
python3 merge_v2.py part oc oc-merged.json out/oc-*.json
python3 oc_decide.py oc-merged.json band-registered.json oc-decisions.json
python3 oc_summary.py oc-decisions.json oc-summary.json oc-summary.md
python3 cost_model_v2.py cost-model-v2.json
```

Process notes, recorded rather than hidden: the first calibration ran at zsh's
background nice level and was restarted at normal priority; the first OC launch
(populations of 1,200) was stopped for time before writing any output; six
seed-42 OC runs with gold shifts first failed (AER values between calibrated
rows; the lookup now interpolates) and were rerun; the OC processes ran with the
estimator before its decision-only additions (the gold-path margin and validity
gate), whose statistic code is unchanged, and their verdicts were recomputed with
the final file; `compute/repair-run2/repro-check.json` reruns one condition (seed
43, AER 0.085/0.05, c 0, three replicates) with the final files and finds all 108
replicate statistics, every S_true and the agreements identical. The Mac was shared by other workloads (load average 110-180), so
populations were sized to finish within the run's wall budget.
