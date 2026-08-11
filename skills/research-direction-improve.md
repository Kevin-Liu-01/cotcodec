---
name: research-direction-improve
version: 0.1.0
triggers: ["novel direction", "new architecture", "new mechanism", "improve research direction", "gauntlet 100"]
tools: [shell, read, write]
mutating: true
---

# Research Gauntlet 100

Turn a promising idea into a falsifiable, reproducible, pilot-ready research
proposal. This workflow borrows the useful mechanics from Claude-of-Duty:
external evaluation, fresh critics, artifact inspection, deterministic gates,
and repeated correction. It rejects the fiction that rhetoric or an unbounded
loop creates perfection.

## Contract

1. Copy `research/proposals/_template.md` to a dated proposal.
2. Declare finite budgets: queries, wall time, tokens, dollars, waves, and GPU-hours.
3. Run every preflight doctor. Each emits `PASS` or `FAIL`, evidence, and remediation.
4. Fan out only independent discovery cells:
   - frontier scout: strongest recent and classical prior work;
   - kill-shot scout: tries to prove the proposal known, invalid, or confounded;
   - cross-domain scout: systems, control, coding theory, neuroscience, and optimization;
   - experimentalist: cheapest decisive experiment and leakage checks.
5. Merge by mechanism, not wording. Give synthesis and causal design one owner.
6. Write the candidate contract and novelty ledger.
7. Send randomized candidate IDs and the evidence packet—not advocate prose—to
   two fresh reviewers. Use different model families when available.
8. Record both reviews as immutable artifacts with provider/model, run ID,
   prompt hash, candidate hash, timestamp, verdict, and output SHA-256.
9. Build the evidence bundle defined by
   `research/proposals/evidence/_schema.json`. Hash every source snapshot,
   query log, doctor output, review, compute attestation, and audit log.
10. Run `uv run python scripts/research_direction_doctor.py <proposal.md>`.
11. If below 100, fix the single highest-impact defect and repeat.

## Preflight Doctors

| Doctor | Pass condition |
|---|---|
| Source | Required backends reachable; cutoff and degraded coverage recorded |
| Citation | URLs, dates, authors, and quantitative claims verified in primary sources |
| Novelty | Synonyms, component pairs, citation graph, code, and adjacent fields searched |
| Design | Intervention, controls, falsifier, metrics, leakage, and statistics specified |
| Compute | Image digest, Slurm dry-run, seeds, quota, checkpoint, and cost plan specified |
| Safety | Safety, monitorability, data rights, and project red lines addressed |

A failed doctor blocks promotion regardless of score.

The Markdown table is a human summary, not evidence. The deterministic doctor
requires hashed doctor artifacts in the evidence bundle. Compute may only pass
after a real model loop, non-stub benchmark adapter, container smoke run, and
successful Slurm dry-run are attested. On the current repo/host, Compute remains
FAIL until those prerequisites are actually fixed.

Promotion metadata must state `Novelty verdict: NO_DIRECT_PRIOR_FOUND` and
`Safety verdict: PASS`; any direct-prior match or safety red line forces reject.
All six budgets must be positive. A 100 additionally requires two Ed25519-signed
review receipts whose public keys come from the external read-only path supplied
by trusted CI as `COTCODEC_TRUSTED_ATTESTORS_PATH`. CI must also set
`COTCODEC_PROTECTED_CI=1` and pin the file in
`COTCODEC_TRUSTED_ATTESTORS_SHA256`; the file must be outside the repository and
not group/world writable. Proposal bundles and the repository cannot introduce
their own accepted trust roots. The signed receipts
bind the proposal and evidence-root hashes, so rewriting snapshots, doctor
claims, compute claims, or audit history invalidates review. The repo-local
`trusted-attestors.json` documents the schema but is intentionally rejected for
promotion until independent review services and protected CI are configured.

## Candidate Contract

Every proposal states:

- research question and variable;
- hypothesized mechanism;
- closest three works and precise novelty delta;
- falsifiable predictions;
- cheapest decisive experiment;
- controls, strong baselines, and ablations;
- success, failure, safety, and wall-clock metrics;
- negative-result value;
- compute, Docker, Slurm, and artifact plan.

Use: "No direct prior art found through YYYY-MM-DD under <coverage>." Never
claim "completely novel."

## Scoring

Two independent reviewers score each dimension from 0 to 10. The lower total
is authoritative.

| Dimension | Max |
|---|---:|
| Question and strategic fit | 10 |
| Primary-source evidence | 10 |
| Defensible novelty delta | 10 |
| Mechanism and falsifiability | 10 |
| Controls and causal identification | 10 |
| Evaluation and statistics | 10 |
| Feasibility and information per GPU-hour | 10 |
| Reproducibility and artifact contract | 10 |
| Safety, data rights, and monitorability | 10 |
| Independent adversarial review quality | 10 |

Hard caps:

- missing falsifier: 59;
- incomplete novelty coverage: 74;
- missing executable pilot: 79;
- missing independent review: 89;
- direct-prior match, fatal leakage, or safety red line: reject.

## Eight Exits

1. all doctors pass and both reviewers score 100;
2. wave cap;
3. token or dollar cap;
4. wall-clock cap;
5. under two points of gain across three waves;
6. human interrupt;
7. the same fatal defect survives three waves;
8. novelty invalidation, external completion, or safety failure.

Scores may fall after better evidence. Track current and best scores; never
optimize prose to hide a scientific defect.

## Audit Trail

Append one JSONL row per wave under `data/research-gauntlet/` with the run ID,
git SHA, source cutoff, exact queries, source hashes, prompts, model IDs, seeds,
reviewer outputs, doctor results, costs, image digest, Slurm job IDs, current
and best score, rejected candidates, and termination reason.

Append with:

```bash
uv run python scripts/research_gauntlet_record.py <audit.jsonl> <record.json>
```

Rows are hash-chained. The final evidence bundle records the audit artifact hash
and final row hash. Hashes make later mutation detectable; they do not prove
reviewer independence by themselves. Different providers are required for 100.
Every row carries sequential `wave`, `score`, `best_score`, `run_id`, proposal
hash, cumulative query/wall/token/dollar/GPU counters, and a final structured
termination state. The doctor rejects counter decreases, budget overruns, or a
non-success termination in a proposal claiming 100.
