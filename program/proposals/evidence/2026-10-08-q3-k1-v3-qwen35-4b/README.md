# Evidence bundle: q3-k1-localization-screen-v3 gauntlet

Proposal: `program/proposals/2026-10-08-q3-k1-v3-qwen35-4b.md`.
Draft registration: `program/preregistrations/q3-k1-localization-screen-v3.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`.

Three passes share this bundle. Wave 1 (synthesis, commit d911d21; recorded in
`program/gauntlet/2026-10-08-q3-k1-v3-qwen35-4b.jsonl`, score 51) built it. The
repair under program decision D48 (same branch, before this run's wave) added
the files marked "repair" below and revised the doctor records. The repair under D52 (2026-10-09, before this run's wave) added the files in the "D52 repair" row and revised the doctor records again.

| Path | Contents |
|---|---|
| `snapshots/` | One record per cited primary URL (50; 8 added by the repair). Each holds the HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, which are CC0; other pages: the HTML title). No page bodies or paper full texts. |
| `query-log.json` | Every retrieval call of the wave-1 discovery cells and synthesis (148 counted against wave 1's 150), and the repair block (`repair_run`: 6 counted against this run's 60, 13 uncounted paper reads with digests, and the screening outcomes of 11 ids). |
| `doctors/` | Six preflight doctor records as revised by the repair (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | Supplementary attestations of the dense pre-check v2's 4B lane (Slurm 862) and its image (build 855); a note that v3's own attestations do not exist; the wave-1 synthesis cost and power scripts. Repair: `repair-literal-channel-sim.py` with `.json` and `-weak-target.json` (S1, block-level literal channels), `repair-decision-sim.py` with `.json` (S2, decision rules on the registered K1 statistics code, validated to 7e-15), `repair-h2-predictive.py` with `.json`, `repair-cost-model.py` with `.json`. |
| `blind/` | Anonymized mechanism paragraphs. Wave 1: the proposal (`e942c63a`), the closest prior (`38ab2fa1`, Oracle-Guided) and SpotAttention (`91fa8475`). Repair, for this run's critic: the repaired proposal (`0ccbe84a`), a fresh closest-prior paragraph (`b005cf6a`) and Lost in Compression (`93f4dd72`). File names carry no role; the mapping is in `bundle.json`. |
| D52 repair (2026-10-09) | `compute/repair3-stage0-dev-facts.py` and `.json` (model-free development facts with the real tokenizer: controlled links, mask, LF and PRE evaluability, the pooled PRE coverage, the answer-sentence kappa bound; per-family counts only, links re-indexed), `compute/repair3-host-stoplists.py` (stop-list proxy from K1's haystack sources on the host CPU; its output is not committed, sha256 `2bcebd74...`), `compute/repair3-decision-sim.py` and `.json` (S3: the D52 rules on measured inputs, imports S2), `compute/repair3-cost-model.py` and `.json`, `compute/repair3-decisiveness.py` and `.json`; `blind/paragraph-e4578790.txt` (proposal), `blind/paragraph-52321202.txt` and `blind/paragraph-9606bfd6.txt` (fresh prior packets); three new snapshots; the query log's `repair3_run` block; the six doctor records revised. |

Reproduce the repair's numbers from the worktree root:

D52 repair (from the worktree root; the facts need the Belebele jsonl files, the Qwen3.5-4B-Base tokenizer.json, sha256 `fe000e3e...`, and the stop lists that `repair3-host-stoplists.py` writes from K1's raw directory):

```bash
uv run --no-project --with pyarrow --with tokenizers python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair3-host-stoplists.py <k1-raw-dir> tokenizer.json stoplists.json
PYTHONPATH=. uv run --with tokenizers python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair3-stage0-dev-facts.py <belebele-dir> tokenizer.json stoplists.json facts.json
PYTHONPATH=. .venv/bin/python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair3-decision-sim.py validate
PYTHONPATH=. OMP_NUM_THREADS=1 NPROC=16 .venv/bin/python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair3-decision-sim.py run out-s3.json
python3 program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair3-cost-model.py
python3 program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair3-decisiveness.py
```

S3 seeds every replicate from CRC32 of its scenario key and uses K1's bootstrap generator (seed 42); its design seed is 42. Rows are keyed, so a stopped run resumes to the same output.

D48 repair:

```bash
S1_FAMILIES=1200 S1_TARGET_LITERAL=2.0 uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-literal-channel-sim.py out-strong.json
S1_FAMILIES=1200 S1_TARGET_LITERAL=1.0 uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-literal-channel-sim.py out-weak.json
PYTHONPATH=. OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 S2_REPS=2000 S2_BOOT=1000 uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-decision-sim.py run out-s2.json
PYTHONPATH=. uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-decision-sim.py validate
uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-h2-predictive.py
uv run --locked python program/proposals/evidence/2026-10-08-q3-k1-v3-qwen35-4b/compute/repair-cost-model.py
```

All randomness is seeded (S1: CRC32 of the scenario tag; S2: CRC32 of the
scenario, K1's bootstrap generator with seed 42). Process count does not change
results.

Not present, by design or because it does not exist yet:

- **Review receipts for this run.** Its reviewers have not run (wave 2's reviews are in the gauntlet row). No trusted
  Ed25519 store exists (D24).
- **This run's hash-chained audit row.** It is appended after its reviewers
  score. Wave 1's row is in `program/gauntlet/`.
- **v3's code, images, probe, smoke and manifests.** They need the v3 code, a
  probe under its own id, Kevin's admission and a freeze.

The deterministic doctor therefore reports FAIL. That is the expected and
honest state.
