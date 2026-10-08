# Audit design: operating characteristics of the sampler and K3 (pre-freeze)

Answers the third-draft re-audit's finding that the `should_fail_violation`
K3 group was under-audited at the registered sample size. No real mutant,
verdict or rater answer is read here: the pools are synthetic, sized to the
expected evaluable counts of section 6 of the preregistration.

- `sim_audit_oc.py`: synthetic confirm-scale pools through the registered
  sampler (`raters.draw_audit_sample`, seed 42) and summary
  (`raters.summarize`: Hajek label error, `stats.label_error_bound`, kappa,
  K3, K4), 200 replicates per scenario, bootstrap 1,000 resamples (the exact
  part of the K3 bound does not depend on it). Code at commit `4b9b45d`
  (the sampler and summary of the fourth draft).
- `audit-oc.json`: every scenario (violation tasks 8, 13, 17, 24, 40; true
  label error 0-15%; perfect raters, raters right 90% / wrong 5% / unsure 5%
  with and without Kevin adjudicating every split item; and the third
  draft's sampler for comparison).

Main rows (P(K3 fires for the group), kappa rule excluded, perfect raters):

| Group, size | n audited (Kish) | 0% | 1% | 2% | 5% | 10% |
|---|---|---:|---:|---:|---:|---:|
| equivalence, 59 tasks | 115 (107) | 0.00 | 0.015 | 0.055 | 0.52 | 0.97 |
| violation census, 17 tasks | 89 (89) | 0.00 | 0.00 | 0.065 | 0.55 | 0.95 |
| violation census, 13 tasks | 68 (68) | 0.00 | 0.04 | 0.135 | 0.67 | 0.985 |
| violation census, 24 tasks | 124 (124) | 0.00 | 0.00 | 0.015 | 0.39 | 0.96 |
| violation census, 8 tasks | 42 (42) | 0.01 | 0.295 | 0.475 | 0.82 | 0.97 |
| violation, third-draft sampler, 17 tasks | 34 (30) | 0.42 | 0.595 | 0.715 | 0.91 | |

With noisy raters (each right 90%, about 61 split items per audit), kappa
falls below 0.6 in 0.11-0.27 of replicates (which removes P2-P5 whatever
the labels); with every split item adjudicated correctly K3 behaves as with
perfect raters, and without adjudication K4 fires in 0.99-1.00 of
replicates. Expected audit size at the section 6 counts: about 365 real and
sham items plus the P1 flips.

Run: `python program/evidence/q2-mutation/integration/audit-design-v1/sim_audit_oc.py audit-oc.json 200 1000 16`
(about 25 minutes on 16 cores).
