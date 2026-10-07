# Program evidence

## 2026-10-06: question selection

| File | What it is |
|---|---|
| `question-dossier.md` / `.json` | All 18 candidates, verified and ranked by three judges: corrected question, what was wrong, closest priors, citable anchors with verification status, first experiment, kill criteria |
| `sources-verified.json` | Per-source primary-text checks behind the dossier |
| `codex-five-directions-source-checks.json` | One verifier per source for Codex's five-direction document: 44 claims, 42 verified, 2 corrected |
| `codex/` | Codex's three documents from 2026-10-06 and their verification records, as written on the H100 host. Their large `sources.json` dumps are not copied |

These are records of a selection process, not experimental results. Codex's
documents are kept verbatim, so their relative links point at the pre-restart
layout; prefix those paths with `legacy/`. Dates in
the dossier are arXiv submission dates unless stated otherwise.

## 2026-10-07: Q3 K1 bundle sources

| File | What it is |
|---|---|
| `2026-10-07/q3-k1-bundle-sources.json` | Every external file behind the K1 study bundle (revision, licence, size, SHA-256, Hub LFS id), the ParaDocs streaming record per pair (files, compressed bytes consumed, kept documents and tokens, stop reason, filter counts, filtered-file digest), the 2026-10-07 ParaDocs yield probe, and the bundle's digest, size, licence id and dedup, filter and quota reports. Identifiers and digests only; no source text |

This is input construction for preregistration q3-k1-localization-screen-v1,
not an experimental result.

## 2026-10-07: Q3 K1 pre-freeze operating characteristics

| File | What it is |
|---|---|
| `2026-10-07/q3-k1-prefreeze-simulations/sim_xi.py`, `sim_xi_4000_10000.json` | GO and NEGATIVE probabilities and 99 percent interval coverage of the registered xi and xi_rel rules: 4,000 synthetic audit reads per cell (two targets each), B = 10,000, five noise scenarios (A the preregistration's worked case, B cluster-dominated, C seed-dominated, D both terms comparable, E small seed SD), nine true effects |
| `2026-10-07/q3-k1-prefreeze-simulations/sim_h2.py`, `sim_h2_2000_10000.json` | Pass probabilities of the H2a and H2b gates on the development pre-check and the audit read: 2,000 replicates per cell, B = 10,000, logit item-difficulty SD 0.8 or 1.5 |
| `2026-10-07/q3-k1-prefreeze-simulations/sim_v12.py`, `sim_v12.log` | HOLD (V2) and V1-failure trigger rates on 100 English ML prompts, two targets by three seeds, 200,000 draws per cell |

The pre-freeze audit of preregistration q3-k1-localization-screen-v1 wrote
these scripts and ran them with the registered statistics code
(`harness/sparse_indexer_k1_stats.py` at SHA-256 `743a4317...`, NumPy 2.5.2):
the two bootstrap studies on the H100 host's CPU, the trigger-rate study on a
workstation CPU. They are kept verbatim (so `program/evidence` is excluded
from lint); a run from the repository root with `harness/` importable
reproduces them. Commit A changes that module only by adding `final_verdict`
and documentation; the interval and gate functions the scripts call are
unchanged. Synthetic numbers only: they describe the decision rules, not the
model or the data.
