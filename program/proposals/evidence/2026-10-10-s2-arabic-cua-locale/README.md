# Evidence bundle: S2 first step gauntlet (wave 1 on Relay; D68 repair run on Q2's OSWorld stack)

Proposal: `program/proposals/2026-10-10-s2-arabic-cua-locale.md`.
Draft registration: `program/preregistrations/s2-arabic-cua-locale-v2.md` (DRAFT, not frozen, no
ledger row); it supersedes wave 1's `s2-arabic-cua-locale-v1.md` (Relay), which is left unedited.
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json` (rebuilt for this
run by `compute/repair-d68/build-bundle-v2.py`; wave 1's `compute/build-bundle.py` is left as it was).

Wave 1 (2026-10-10) was built by the gauntlet's synthesis owner from four discovery cells and
scored 49 (`program/gauntlet/2026-10-10-s2-arabic-cua-locale.jsonl`). D68 ordered one CPU repair
by a single owner and a fresh run with new budgets (queries 80 with at least 30 reserved for the
triad, wall 600 min, tokens 8,000,000, dollars 150, one wave, 0.3 GPU-h for the reviewer). The
repair ran on the development Mac's CPU; it made no host contact.

| Path | Contents |
|---|---|
| `compute/repair-d68/power-osworld.py`, `power-osworld.json` | The repair's design evidence. Task screen of S1a's 113-task pool (applications with shipped Arabic interfaces and separable layout switches; coordinate-click setups excluded; config-reading checkers conditional; informative = Qwen3.5-9B solved at least 1 of 8 S1a episodes): 43 candidates, task sets of 26, 31, 36 and 43. A beta-binomial propensity model fitted on S1a's 154 candidate (task, harness) cells and checked against S1a's k-histogram and rerun discordance. A simulation of the registered estimator (paired t on task means, sign flip, TOST, the rare-break bound, a sharp-null randomization test) over 4 task sets x n in {8, 12, 16} x 17 scenarios (two nulls; uniform logit shift, proportional, half-task, quarter-task and complete-break structures at -3, -5 and -8 pp; T = -5 pp throughout), 1,000 replicates per seed x seeds 42, 43, 44. Cost by the Q2 design study's slot rule (central and high slot prices). Exact noncentral-t MDE grid. Inputs hashed |
| `compute/repair-d68/power-osworld-v0-partial.json` | The superseded first run (LibreOffice strict set only, n in {4, 8, 12, 16}, no rare-break bound). Kept: it showed the t interval under-covering when a few tasks break completely (coverage 0.82-0.92), which is why the SMALL rule now carries the bound |
| `compute/repair-d68/power-osworld-v1-break050.json` | The second, superseded run (all four task sets; the rare-break bound counted a break at D_t <= -0.5). Kept: at K = 43 it let an unqualified SMALL through in up to 0.087 of replicates at a true -5 pp made of complete breaks, so a large drop is now D_t <= -0.25 |
| `compute/repair-d68/registered-caps.py`, `registered-caps.json` | Phase 1 cap for every admissible K (26-43) at the registered n |
| `compute/repair-d68/render-oracle/` | `oracle.py` (O1-O5; O6 is a lane check), `fixture.mjs` (a mock office window rendered in Chromium in four cells under seven variants with known properties, plus A/A renders), `validate.py` (A/A tolerance first, then expected against observed verdicts), `oracle-validation.json` (7 of 7 variants as expected; renders are reproducible from the scripts and hashed in the result, not committed) |
| `compute/repair-d68/fetch-mechanism-sources.py`, `mechanism-sources-index.json` | Snapshots of the 13 primary-source files behind each per-application switch and the isolation construction (LibreOffice core at `08f5d410`, GTK 3.24.33 and 2.24.33, Pango 1.50.6, Gecko `LocaleService.cpp`, UAX #9, CSS Writing Modes 3), each with matched line numbers; the records are in `snapshots/` |
| `compute/repair-d68/build-query-log-run2.py`, `query-log-run2.json` | This run's 22 counted retrieval queries (14 orx discover, 4 ACL Anthology over the full bibliography with abstracts, 4 OpenReview API) with exact queries, returned ids and raw-output SHA-256; uncounted reads and fetches; PRISMA counts |
| `snapshots/` | One record per primary URL the proposal cites (HTTP status, fetch time, SHA-256 and size of the full body, a metadata extract or matched source lines). No page bodies or paper texts. The two OpenReview records are HTTP 200 browser-challenge pages and verify nothing about content |
| `query-log.json` | Wave 1's retrieval (113 counted orx queries by the cells and synthesis; the novelty refuter's 10 are in the gauntlet row), failed calls, uncounted searches, the cells' verdicts |
| `doctors/` | Six preflight doctor records for this run (Source, Citation and Safety PASS; Novelty FAIL until this run's blind critic and refuter run; Design as stated in `design.json`; Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. `citation.json` holds the claim registry C01-C56 |
| `blind/` | Anonymized mechanism paragraphs. This run's packet is named in `compute/repair-d68/blind-roles-run2.json` (recorder only; never give it to the critic); wave 1's two paragraphs and `compute/blind-roles.json` stay for the record |
| `compute/attestations-not-run.md` | Why no compute attestation exists for S2 |
| `compute/power-gate.py`, `power-gate.json`, `cells/`, `build-query-log.py` | Wave 1's Relay evidence, kept as history |
| `compute/snapshot-sources.py`; `compute/repair-d68/build-bundle-v2.py` (wave 1: `compute/build-bundle.py`) | Builders for the snapshots and the bundle |

Reproduce the repair's evidence from the worktree root:

```bash
E=program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/repair-d68
OMP_NUM_THREADS=2 .venv/bin/python $E/power-osworld.py program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json $E/power-osworld.json --nrep 1000
.venv/bin/python $E/registered-caps.py $E/power-osworld.json $E/registered-caps.json
PLAYWRIGHT_CORE=/path/to/playwright-core/index.mjs node $E/render-oracle/fixture.mjs <render-dir>   # a local Chromium
.venv/bin/python $E/render-oracle/validate.py <render-dir> $E/render-oracle/oracle-validation.json
python3 $E/fetch-mechanism-sources.py <snapshot-dir>
python3 $E/build-bundle-v2.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-s2-arabic-cua-locale.md
```

`build-query-log-run2.py` reads the session scratchpad and reproduces the log only inside that
session; the log records every raw output's digest.

Not present, by design or because it does not exist yet:

- **Review receipts for this run.** The blind critic, the refute-first triad and both reviewers
  run after the repair. No trusted Ed25519 store exists (D24).
- **This run's hash-chained audit row.** Appended after its reviewers score.
- **Compute attestations.** No derived localized image, delta certification of the action path,
  oracle run on the real applications, Phase 1 manifest, container smoke, Slurm dry run or
  provenance check exists (`compute/attestations-not-run.md`). There is no executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and honest state.
