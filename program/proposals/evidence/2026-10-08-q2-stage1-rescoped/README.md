# Evidence bundle: q2-stage1-rescoped gauntlet, wave 0

Proposal: `program/proposals/2026-10-08-q2-stage1-rescoped.md`. Draft
preregistration: `program/preregistrations/q2-stage1-rescoped-v1.md`. Schema:
`program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(built by `analysis/build_bundle.py`).

| Path | Contents |
|---|---|
| `snapshots/` | One record per cited primary URL (26), fetched on 2026-10-08: HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract. arXiv extracts hold the title, authors, dates and abstract (CC0 metadata); other pages hold only the HTML title. Bodies are not stored. The two raw GitHub files of the pinned harnesses hash-equal `harness/q2/action_path/upstream/PROVENANCE.json` |
| `query-log.json` | The 10 orx 0.2.2 discover queries of this wave with every returned id, and the three full-text reads with their SHA-256 |
| `doctors/` | Six preflight doctor records (Source, Citation, Design and Safety PASS; Novelty and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py` |
| `compute/` | A note that no S1a compute attestation exists yet; the cost basis is `serving-throughput-probe-v2` job 466 |
| `analysis/cost_s1a.py`, `cost_s1a.json` | The cost card recomputed with the frozen `harness/serving_probe/budget.py`: the card's cells, the certified pair's per-episode prices at T = 15, the thinking pass-back bound, S1a caps and jobs, the anchor, VM-hours and the S1b projections. Run: `python cost_s1a.py <repo root>` |
| `analysis/sim_s1a.py`, `sim_s1a.json` | Seeded operating characteristics of S1a (2,000 data sets per point, 200 permutations): δ MDE, D_b and D_b − D_w precision, the X tests under four scenarios including task x harness x session noise, the session-shift test, the anchor kill rule, and the ladder's planning value M |
| `analysis/sim_signflip.py`, `sim_signflip.json` | The sign-flip X test and the share's sampling SD (1,000 data sets, 500 flips) |
| `analysis/task_draw.py`, `task-draw-K32.json`, `-K24.json`, `-K16.json` | The seeded base draw and extension order. The K = 24 and K = 16 bases are nested in K = 32 |
| `analysis/snapshot_sources.py`, `snapshot-index.json` | The snapshot fetcher and its index |

The simulation outputs were produced by the same scripts before `ruff
format` reflowed them. The changes are layout and docstrings only. The cost
output was regenerated from the committed script.

Not present, by design or because it does not exist yet:

- **Review receipts.** No reviewer has run. No trusted Ed25519 store exists
  (D24).
- **The hash-chained audit row.** It is appended after the reviewers score.
- **S1a's image, manifest, smoke, dry-run and orx node.** They come after the
  G0 items (preregistration section 3).

The deterministic doctor therefore reports FAIL, which is the expected and
honest state for wave 0.
