# Evidence bundle: G2-stream gauntlet, wave 1 synthesis (2026-10-15)

- **Proposal:** `program/proposals/2026-10-16-g2-kimi-expert-streaming.md`.
- **Draft registration (pilot only):** `program/preregistrations/g2-kimi-expert-streaming-v1.md`
  (DRAFT, new experiment id, not frozen, no ledger row).
- **Schema:** `program/proposals/evidence/_schema.json`.
- **Index and hashes:** `bundle.json`, built by `compute/build_bundle.py`.

The synthesis owner ran on the development Mac's CPU. It used no GPU, submitted no host job and ran
no retrieval search. What it did run:
- five `orx paper --full` reads;
- pinned-commit reads of ds4 (`90aa4b56`) and of the Anemll fork (`a809594f`);
- Hub metadata reads, one web page fetch, and the source snapshots.

The four discovery cells (frontier, kill-shot, cross-domain, asset and cost) ran before it,
independently and read-only. Their query records are in `query-log.json`. The Mac was under a load
average near 500 from other sessions during the simulation, so the synthetic runs use a reduced
configuration (one readout seed, 12 sessions per workload, 2 layers). The unit tests ran on all
three seeds.

| Path | Contents |
|---|---|
| `query-log.json` (`compute/build_query_log.py`) | Every counted search of the four cells, with the ids it returned: 57 orx discover, 3 OpenAlex lookups, 7 web, 8 GitHub, 7 Hugging Face; 82 in all. Also PRISMA counts and the synthesis's uncounted reads. The cells saved no raw outputs, so there are no per-query raw digests |
| `snapshots/` (`compute/snapshot_sources.py`) | One record per URL the proposal cites (38): HTTP status, fetch time, body SHA-256 and size, and an arXiv metadata extract or the HTML title. Bodies are not stored. All 38 returned HTTP 200. The three ACM papers are cited through their OpenAlex records (`api.openalex.org/works/doi:...`), because their DOI pages returned 403 bot challenges on the first pass; those three first-pass records were deleted and replaced |
| `compute/ds4-targets.json` | The pre-registered validation targets from ds4 at `90aa4b56`: values, roles (one calibration row, holdouts, contrasts), noise classes, input-fidelity strata, exclusions and the SHA-256 of every ds4 file read |
| `compute/identification_g2stream.py`, `identification-g2stream.json`, `.stdout` | For each ds4 generation row, the (h, B) pairs that fit it under the dossier's A6. Also: B from the whole-pool append (6.08 GB/s); the dossier null's interval and its frozen central predictions (G = 1.415; ratio 1 for every contrast); and the Kimi sensitivity to B, h and e |
| `compute/sim_g2stream.py`, `sim-g2stream.json`, `.stdout` | Event-atomic simulators (LRU, LFU, ds4 decayed hotness, static, Belady) with unit tests: Che, inclusion, ds4-without-hotness equals LRU, the Belady bound. Also the synthetic readout's spread and cold start, and the validation rule's operating characteristics (seeds 42-44) |
| `compute/caps_g2stream.py`, `caps-g2stream.json`, `.stdout` | Cap arithmetic: pilot caps 7.45 GPU-h (about 4.1 expected); full study 15.3-41.0 GPU-h (cap 50); downloads 707.5 GB |
| `compute/blind-roles.json`, `blind/` | The anonymized mechanism paragraphs for the blind critic, in a seeded order: the proposal's, and the Anemll Flash-MoE workflow's. The roles file is for the recorder only |
| `compute/write_doctors.py`, `doctors/` | The six preflight doctor records (Source, Citation, Design and Safety PASS, with Design self-assessed; Novelty and Compute FAIL) and the deterministic doctor's verbatim output (`doctors/direction-doctor-output.json`) |
| `compute/attestations-not-run.md` | The compute attestations that do not exist yet, and what produces each |

Reproduce from the repository root (CPU; numpy from the project environment):

```bash
E=program/proposals/evidence/2026-10-16-g2-kimi-expert-streaming
python3 -I $E/compute/identification_g2stream.py --out $E/compute/identification-g2stream.json
uv run --locked python $E/compute/sim_g2stream.py --out $E/compute/sim-g2stream.json \
    --sessions 12 --T 512 --layers 2 --readout-seeds 1 --validation-reps 20000
python3 -I $E/compute/caps_g2stream.py --out $E/compute/caps-g2stream.json
python3 -I $E/compute/build_query_log.py --out $E/query-log.json
python3 -I $E/compute/snapshot_sources.py program/proposals/2026-10-16-g2-kimi-expert-streaming.md $E/snapshots
python3 -I $E/compute/write_doctors.py
python3 -I $E/compute/build_bundle.py
uv run python scripts/research_direction_doctor.py program/proposals/2026-10-16-g2-kimi-expert-streaming.md
```

Not present, by design or because it does not exist yet:

- **Review receipts.** The blind critic, the refute-first triad and the two reviewers follow this
  synthesis. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** The recorder appends it after the reviewers score.
- **Compute attestations** (`compute/attestations-not-run.md`) and an executable pilot.

The deterministic doctor therefore reports FAIL. That is the expected and honest state.
