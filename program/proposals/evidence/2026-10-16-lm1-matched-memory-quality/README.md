# Evidence bundle: LM1 gauntlet, wave 1 synthesis (2026-10-16)

- **Proposal:** `program/proposals/2026-10-16-lm1-matched-memory-quality.md`.
- **Draft registration (pilot only):** `program/preregistrations/lm1-matched-memory-quality-v1.md`
  (DRAFT, new experiment id, not frozen, no ledger row).
- **Schema:** `program/proposals/evidence/_schema.json`.
- **Index and hashes:** `bundle.json`, built by `compute/build_bundle.py`.

The synthesis owner ran on the development Mac's CPU. It used no GPU and submitted no host job; it
ran one read-only `nvidia-smi`, `squeue` and `free` check on the host. What it ran:
- six counted `orx discover` searches (title phrases of the closest priors and knowledge under
  quantization; `compute/synthesis-queries.json`);
- six `orx paper --full` reads (2509.25689, 2504.02010, 2610.15372, 2604.18556, 2404.05405,
  2508.10925) and five abstract reads;
- Hub API and model-card reads at pinned revisions, two llama.cpp documents at `620d2225`, four
  Artificial Analysis pages, and the source snapshots;
- the decision-rule simulation and the cap arithmetic.

The four discovery cells (frontier, kill-shot, cross-domain, asset and cost) ran before it,
independently and read-only. Their query records are in `query-log.json`. The Mac's load average was
near 300 from other sessions during the simulation, which is why its vectorized run took about 20
minutes of wall time (`runtime_s` 1,168 in `sim-lm1.json`).

| Path | Contents |
|---|---|
| `query-log.json` (`compute/build_query_log.py`) | Every counted search with the ids it returned: frontier 41, kill-shot 8, cross-domain 24, synthesis 6 (itemized), asset cell 13 (counted, not itemized: the cell returned no query strings); 92 in all. PRISMA counts and the synthesis's uncounted reads |
| `snapshots/` (`compute/snapshot_sources.py`) | One record per URL the proposal cites (38): HTTP status, fetch time, body SHA-256 and size, and an arXiv metadata extract or the HTML title. Bodies are not stored. All 38 returned HTTP 200 |
| `compute/sim_lm1.py`, `sim-lm1.json`, `.stdout` | Operating characteristics of the registered decision rule: superpopulation item model, two variance settings, nine true effects, 1,600 and 1,000 primary items, seeds 42-44, 1,000 replicates per cell per seed; coverage of the normal interval |
| `compute/caps_lm1.py`, `caps-lm1.json`, `.stdout` | Pilot guards (6.9 GPU-h unconditional, line 8.0), pessimistic completion per arm, the P2 Mac-time matching, and the full study's GPU-h by branch |
| `compute/blind-roles.json`, `blind/` | The two anonymized mechanism paragraphs for the blind critic (the proposal's and CC-MoE's) and their roles; the roles file is for the recorder only |
| `compute/write_doctors.py`, `doctors/` | The six preflight doctor records (Source, Citation, Design and Safety PASS, Design self-assessed; Novelty and Compute FAIL) and the deterministic doctor's verbatim output (`doctors/direction-doctor-output.json`) |
| `compute/attestations-not-run.md` | The compute attestations that do not exist yet, and what produces each |

Reproduce from the repository root (CPU; numpy from the project environment):

```bash
E=program/proposals/evidence/2026-10-16-lm1-matched-memory-quality
uv run --locked python $E/compute/sim_lm1.py --out $E/compute/sim-lm1.json --reps 1000 --seeds 42 43 44
python3 -I $E/compute/caps_lm1.py --out $E/compute/caps-lm1.json
python3 -I $E/compute/build_query_log.py --out $E/query-log.json
python3 -I $E/compute/snapshot_sources.py program/proposals/2026-10-16-lm1-matched-memory-quality.md $E/snapshots
python3 -I $E/compute/write_doctors.py
python3 -I $E/compute/build_bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-16-lm1-matched-memory-quality.md
```

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and the two reviewers follow this
  synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** The recorder appends it after the reviewers score.
- **LM1 compute attestations** (`compute/attestations-not-run.md`) and an executable pilot.
- **Benchmark text.** The datasets were read in the session scratchpad to check their fields and
  sizes; no item text is committed.

The deterministic doctor therefore reports FAIL. That is the expected and honest state.
