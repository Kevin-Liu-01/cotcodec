# PAST-Bench SM01 Qwen3.6 Discovery Result

Date: 2026-08-14  
Status: `PAST_SM01_RESTART_EQUIVALENCE_FALSIFIED`  
Scientific result: false  
Publication ready: false

## Question

Under a frozen PAST-Bench/Hermes+ runtime and a frozen
Qwen3.6-35B-A3B checkpoint, does cross-session persistence improve the eight
registered `SM01_preference_adoption` episodes relative to the identical agent
with persistence disabled?

This was a bounded discovery cell. Its preregistered validity gate required a
fresh Slurm job resumed after episode three to match an uninterrupted execution.
Non-repeatable deterministic decoding or failed restart equivalence killed the
lane, regardless of the apparent treatment effect.

## Contained execution

All model execution ran inside Docker under Slurm on `fal-h100-01`; no model ran
on the login node. Runtime networking was disabled after the pinned artifacts
were staged. No `sudo` was used.

- PAST-Bench source revision:
  `f8223517ae7491e776b69793d9f11e9d074ab42e`
- PAST source receipt:
  `5e686206db8d1447d1b18d27bfffdd792f45c9d3418aedc7c15a5d134d6a6a5c`
- PAST runtime receipt:
  `27fb11233ecb18bbdc60ca1c7c0100284b93c87b9fb5d07eb461d028bfd4a64d`
- PAST image ID:
  `sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150`
- PAST image archive SHA-256:
  `2f97fa8c18528eff8fd2e335e851255be280a20d2a3a81f74eab7485c0db285b`
- PAST SBOM SHA-256:
  `37f7eb4eab884c7d924e718f9ed8389102a61fe43b36d48e29249996bf857fff`
- vLLM image ID:
  `sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d`
- Qwen3.6-35B-A3B revision:
  `995ad96eacd98c81ed38be0c5b274b04031597b0`
- Qwen model artifact root:
  `8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b`

CPU Slurm job 244 proved the offline Hermes bootstrap. H100 job 246 stopped
after the third primary episode and atomically checkpointed generation four.
CPU job 248 validated that controlled-stop checkpoint. Fresh H100 job 250
resumed it without rerunning episodes one through three and completed the
eight-episode persistence-on/off sequence. CPU job 252 sealed the completed
resume receipt. H100 job 254 began the independently uninterrupted execution;
it was cancelled immediately when the registered mismatch kill became
observable. CPU job 256 sealed the comparison.

The fresh-resume receipt is
`e23615a0186f8d08f1462e2b3d6ecf6d0cf131ebf054bd99d03721f206490e72`.
The final determinism-falsification report is
`da6f5966e928787b40e63bff662add5bb06e56a4c0551ce826c17cf1aeb326b8`.

## Completed resumed run

| Episode | Persistence on | Persistence off |
| --- | ---: | ---: |
| Cold baseline | 0.60, fail | 0.60, fail |
| Learn A | 1.00, pass | 0.56, fail |
| Learn B | 1.00, pass | 0.60, fail |
| Near evaluation | 1.00, pass | 0.40, fail |
| Far evaluation | 1.00, pass | 0.40, fail |
| Control 2 | 0.80, fail | 0.80, fail |
| Control 1 | 0.60, fail | 0.60, fail |
| Control 3 | 0.60, fail | 0.60, fail |

The resumed run's two evaluation episodes show a descriptive mean score delta
of `+0.60` and pass-rate delta of `+1.00` for persistence. The controls are
identical. These values are promising diagnostics only; the validity failure
below prevents promotion as a scientific effect.

## Registered falsifier

The independently uninterrupted job diverged within the shared prefix despite
greedy decoding, seed 42, eager execution, fixed topology, and registered
CUBLAS settings:

| Episode | Uninterrupted | Resumed |
| --- | ---: | ---: |
| Cold baseline | 0.60, fail | 0.60, fail |
| Learn A | 1.00, pass | 1.00, pass |
| Learn B | 0.76, fail | 1.00, pass |
| Near evaluation | 0.704, fail | 1.00, pass |

The sealed audit records two score mismatches, two pass/fail mismatches, seven
trace mismatches, and normalized episode drift in all four comparable primary
episodes. The kill criterion therefore fired. The result cannot establish a
PAST-Bench persistence effect, checkpoint equivalence, or publication-ready
Qwen/Hermes behavior.

## Decision

Do not rerun this exact cell or relax its deterministic gate post hoc. Do not
advance to the four-family PAST screen.

A future methodology must be registered as a different estimand before new GPU
use. Two defensible options are:

1. use a dense model/runtime with a demonstrated repeated cold-load exactness
   doctor before the PAST cell; or
2. explicitly model generation as stochastic, use multiple independent
   uninterrupted and interrupted replicates, compare executable scores/actions
   with a preregistered equivalence margin, and retain byte/trace equality only
   as a diagnostic.

Either option must retain exact task ordering, checkpoint lineage, artifact
identity, persistence isolation, and control parity. The existing negative
result remains part of the evidence record.
