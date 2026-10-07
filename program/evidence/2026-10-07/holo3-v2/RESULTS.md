# Holo3 rerun audit v2: results

Registration: `q2-holo3-rerun-audit-v2` (ledger row `aa32cb0a...`, frozen
2026-10-07, `git_head_at_freeze` `48f6b4e`). Run as Slurm job 438 (CPU only)
from a fresh clone of `b721739` on the H100 host, 11:39-11:54 UTC. Every
receipt is labelled `v2 CONFIRMATORY`, and every run condition holds: the
repository ledger, code unchanged since the freeze, Python 3.14 with scipy
1.18.0, the feature file traced to a confirmatory tarball scan, and the run
inside the 14-day window.

## Question

The two OSWorld-Verified rows for Holo3-35B-A3B (82.56 and 78.15) are two
maintainer runs of the same agent on the same day. Per task they are not
exchangeable reruns (v1 post-hoc record: exact McNemar 25 vs 9, p = 0.009).
Was the shift on the checker side, the agent side, or an environment failure?

## Registered outcomes

| Rule | Outcome | Key numbers |
|---|---|---|
| (d) checker time-dependence | **not attributable to checker time-dependence** | 16 clean tasks have a time-dependent checker; they carry 4 of the 14 net flips (share 0.29); stratified exact one-sided p = 0.156 (alpha 0.04). Same verdict under the narrow-L sensitivity (p = 0.51) |
| (a) agent behaviour (step counts) | **no agent-behaviour shift** | 322 joined task pairs; geometric-mean step ratio run1/run2 0.977; Wilcoxon p = 0.94 (alpha 0.01). Same verdict on concordant tasks only (p = 0.36) |
| (b) failure signatures of the 14 run2-unique failures | **unexplained** | environment 1 of 14, agent-side (step cap or premature answer) 1 of 14; 12 have no registered signature. Same verdict under every registered sensitivity |
| (c) coverage | **coverage ok** | 695 of 718 scored episodes joined and parsed (96.8%) |

Error rates were fixed before the run: (d) 0.04, (a) 0.01, each (b)
comparison 0.025; nominal family-wise rate 0.10.

## What this means for Q2

- The pair is a real session shift that none of the registered mechanisms
  explains: not checkers that read the clock or the live web, not a change in
  how long the agent works, and not visible environment failures.
- Runs of one agent on the same day by the same operator can differ by 4.4
  points for reasons the trajectories do not reveal. A rerun-noise floor
  measured inside one session would understate the variance between sessions.
- Consequence for the Stage 1 design: the variance model needs a session
  random effect with more than one session per cell, and the noise anchor is
  OpenCUA, whose agent can be rerun (decision D11).

## Limits

- Blinding of the evaluator-class rules to the class-outcome join is
  self-attested; the rule list was written while configs and outcomes were on
  disk. The narrow-L sensitivity gives the same verdict.
- About 232 MB of the tarball was read during scoping; the registered
  probe-region sensitivity is in the receipt.
- The 5.75 GB tarball was deleted after the run; the trajectory feature file
  (SHA-256 `df5abafd...`) stays on the host and is not published.

## Files

`receipt-v2-d.json` (rule d alone), `receipt-v2-tarball.json` (verified
download and scan), `receipt-v2-final.json` (all rules), `slurm-438.out`.
