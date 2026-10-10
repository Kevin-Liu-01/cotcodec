# Evidence bundle: S2 first step (s2-arabic-cua-locale-v1) gauntlet, wave 1

Proposal: `program/proposals/2026-10-10-s2-arabic-cua-locale.md`.
Draft registration: `program/preregistrations/s2-arabic-cua-locale-v1.md` (DRAFT, not frozen, no ledger row).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`
(rebuilt by `compute/build-bundle.py`).

Built on 2026-10-10 by the gauntlet's single synthesis owner (D67) from four
independent discovery cells (frontier and novelty, kill-shot, cross-domain,
asset and cost). Their queries were parsed from the cells' raw orx outputs in
the session scratchpad into `query-log.json` (each raw file's SHA-256
recorded). No GPU and no host job was used; all CPU work ran on the
development Mac. The host queue was read once (empty at 2026-10-10T21:42:52Z).

| Path | Contents |
|---|---|
| `snapshots/` | One record per primary URL the proposal cites: HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, CC0; other pages: the HTML title). No page bodies or paper texts. The two OpenReview records are HTTP 200 browser-challenge pages and verify nothing about content. The LibreOffice source is cited by its raw.githubusercontent.com URL because the github.com blob page returned HTTP 503 twice; its record carries the cited lines. |
| `query-log.json` | Every retrieval call: 113 counted orx discover queries (frontier 45, kill-shot 33, cross-domain 21, asset 10, synthesis 4) with returned ids and raw-output SHA-256; 9 orx calls that failed with HTTP 429 (not counted); 65 uncounted OpenReview, Semantic Scholar, OpenAlex-API, arXiv, Crossref, web and source-code calls; paper reads; the cells' verdicts. 37 queries remain under the declared 150, so the triad's reserve of 30 is intact. |
| `doctors/` | Six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. `citation.json` holds the claim registry C01-C39. |
| `compute/power-gate.py`, `power-gate.json` | Analytic MDE grid (exact noncentral t) for the dossier's design and the 2x2; TOST power; the cost model from S1a's realized price and serving probe v2; the gate on transported S1a inputs and its pass region; a Monte Carlo of the staged design (pilot, gate, main study) over four assumed base-rate scenarios, three heterogeneity patterns and four true effects, 1,500 replicates per cell over seeds 42/43/44, with the dossier's fixed design simulated on the same draws. Inputs hashed. About 25 minutes on the Mac. |
| `compute/cells/` | The discovery cells' scripts and outputs that support quantitative claims (kill-shot power simulation and Relay mirror and text-share probes; cross-domain MDE grid; asset power estimate and chrome-share measurement). Local test tokens are redacted; `ORIGINAL_SHA256.txt` records the unredacted originals' hashes. |
| `compute/build-query-log.py`, `snapshot-sources.py`, `build-bundle.py` | Builders for the query log, snapshots and bundle. |
| `compute/attestations-not-run.md` | Why the compute attestations do not exist. |
| `compute/blind-roles.json` | Role map for the recorder; never give it to the critic. |
| `blind/` | Two anonymized mechanism paragraphs: the proposal's and the closest prior's (arXiv 2506.04135, macOSWorld). File names carry no role. |

Reproduce from the worktree root:

```bash
OMP_NUM_THREADS=2 .venv/bin/python program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/power-gate.py program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/power-gate.json --nrep 500
python3 program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/snapshot-sources.py program/proposals/2026-10-10-s2-arabic-cua-locale.md program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/snapshots/
python3 program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/build-bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-s2-arabic-cua-locale.md
```

`build-query-log.py` reads the session scratchpad and reproduces the log only
inside that session; the log records every raw file's digest.

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and both
  reviewers run after synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** Appended to `program/gauntlet/` after the
  reviewers score.
- **Compute attestations.** No Relay local-engine transport, agent adapter,
  environment image, manifest, container smoke, Slurm dry run or provenance
  check exists (`compute/attestations-not-run.md`). There is no executable
  pilot.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.
