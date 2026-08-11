# Research Direction: <name>

**Status:** draft
**Owner:** <name>
**Source cutoff:** YYYY-MM-DD
**Coverage limits:** <unavailable databases or platforms>
**Budgets:** queries=0; wall_minutes=0; tokens=0; dollars=0; waves=0; gpu_hours=0
**Novelty verdict:** REJECT_PENDING_AUDIT
**Safety verdict:** FAIL
**Evidence bundle:** evidence/<proposal-slug>/bundle.json

## Claim and Research Question

## Strategic Fit and Why Now

## Primary-Source Evidence

## Closest Prior Work

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|

Novelty wording: No direct prior art found through `<date>` under `<coverage>`.

## Mechanism and Falsifiable Predictions

## Cheapest Decisive Pilot

## Controls, Baselines, and Ablations

## Evaluation, Statistics, and Leakage Checks

## Compute and Reproducibility

Include Docker image digest, Slurm command, seeds, checkpoints, artifact paths,
GPU-hour estimate, preemption handling, and cost ceiling.

Required machine fields: immutable image
`registry.example/project@sha256:<64 lowercase hex>`, an `sbatch` command,
`seeds: [42, 43, 44]`, and `gpu_hours: <integer>`.

## Safety, Data Rights, and Monitorability

## Negative-Result Value

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | FAIL | | |
| Citation | FAIL | | |
| Novelty | FAIL | | |
| Design | FAIL | | |
| Compute | FAIL | | |
| Safety | FAIL | | |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=<provider> | model=<model> | run_id=<id> | artifact=<path>

Reviewer B: FAIL | provider=<different-provider> | model=<model> | run_id=<id> | artifact=<path>

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | |
| Primary-source evidence | 0 | 0 | |
| Defensible novelty delta | 0 | 0 | |
| Mechanism and falsifiability | 0 | 0 | |
| Controls and causal identification | 0 | 0 | |
| Evaluation and statistics | 0 | 0 | |
| Feasibility and information per GPU-hour | 0 | 0 | |
| Reproducibility and artifact contract | 0 | 0 | |
| Safety, data rights, and monitorability | 0 | 0 | |
| Independent adversarial review quality | 0 | 0 | |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|

The evidence bundle follows `research/proposals/evidence/_schema.json`. All
source snapshots, query logs, reviewer outputs, doctor outputs, container and
Slurm attestations, and the hash-chained audit JSONL must live below the bundle
directory and match their recorded SHA-256 hashes. A prose PASS without those
artifacts is a deterministic FAIL. Each review receipt must be Ed25519-signed by
a provider-specific key loaded from the external read-only path configured as
`COTCODEC_TRUSTED_ATTESTORS_PATH` in trusted CI. CI also pins its SHA-256 and
sets `COTCODEC_PROTECTED_CI=1`; proposal authors cannot add a trust root inside
the repository or their evidence bundle.
