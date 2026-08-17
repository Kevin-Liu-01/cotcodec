# PAST-Bench Intake and Longitudinal Memory Methodology

Date: 2026-08-14  
Status: source-admitted; no model result  
Primary source: [PAST-Bench paper](https://arxiv.org/abs/2608.04003)  
Code: [Gen-Verse/PAST-Bench at `f8223517`](https://github.com/Gen-Verse/PAST-Bench/tree/f8223517ae7491e776b69793d9f11e9d074ab42e)

## Outcome

PAST-Bench is the next external benchmark for cross-session pathway claims, but
not the next GPU job. The flat 500-task LongMemEval quality matrix remains
first. PAST-Bench follows only after clean source/image provenance because it
tests a different question: whether persistent state causes later fresh-session
improvement and whether the intended save, retrieve, reuse, or update pathway
actually occurred.

The current admission receipt proves the source surface only. It does not prove
that any agent, model, container, grader, or persistence condition works.

## Source contract

`scripts/validate_past_bench_source.py` reads declarative YAML and file content
without importing upstream Python. The registered contract binds:

- Git commit `f8223517ae7491e776b69793d9f11e9d074ab42e`;
- tree `da949dede2557704126e74db0927e6240882f2d8`;
- deterministic Git archive SHA-256
  `be99fad4156bf030f8d3ac9385842099e4d295ec0845d4a46ab5ad5c2bcb88f4`;
- Apache-2.0 license and required runtime/configuration files;
- 26 family manifests and their exact reference configurations;
- 204 declared ordered episodes: Memory 41, Procedure 64, Proactive 48,
  Update 51;
- every task YAML, fixture, grader input, task ID, family order, fresh-session
  bit, persistence-control bit, history mode, and mechanism label;
- seven additional update-family task directories present in the checkout but
  excluded from `episode_order` and the runnable reference manifests.

The seven excluded directories are a useful guard, not an error to hide. A
future checkout that adds an old directory to `episode_order`, or silently
removes one, changes the benchmark and must fail admission.

## Exact scientific question

For one frozen model and agent runtime, does enabled cross-session persistence
improve later fresh-session executable task score relative to the same runtime
with persistence disabled, and is the improvement accompanied by the expected
memory pathway?

This is a bundle-level longitudinal treatment. It is not item-level causal
credit, learned eviction, active/inactive paging, or a proof that the stored
artifact was necessary. CMHT remains a separate prospective item-service
estimand.

## Pilot ladder

### Stage A — source and dependency doctor (CPU, no model)

1. Validate the clean exact checkout with the registered source doctor.
2. Build an offline wheel/npm manifest from exact versions; reject the current
   open-ended `>=` requirements as a publication dependency set.
3. Replace mutable Python base tags and `latest` OpenClaw/Codex/Claude CLI build
   arguments with immutable image/package artifacts.
4. Run the upstream source tests inside the candidate image with network off.
5. Emit image digest, source archive, lock manifest, SBOM, test roster/output,
   and container runtime receipt.

Stage A uses CPU. An H100 would add no validity to source parsing or unit tests.

#### Stage A implementation state

CoTCodec now supplies a candidate runtime overlay without pretending that the
upstream repository itself is locked:

- `research/source-contracts/past-bench-runtime.yaml` binds Python 3.11.15,
  `uv 0.11.30`, an `exclude-newer` cutoff, 106 exact packages, and a
  hash-complete requirements export;
- every one of the 31 direct requirements declared by PAST-Bench core,
  PAST-Bench's mock extra, and Hermes+ resolves to a compatible locked version;
- a Linux/amd64 `manylinux_2_28` binary-wheel dry run resolves all 103 installed
  distributions without an sdist build;
- the base is the exact amd64 manifest
  `docker.io/library/python@sha256:77923445c077d8eb971b14b2b114a1d9cd4a87edb4c75654820ca4832ee8cb15`,
  not a mutable Python tag;
- `scripts/prepare_past_bench_runtime.py` materializes all 2,159 regular Git
  files, reconstructs the pinned Git tree from those bytes, and admits only a
  context whose overlay still matches every host file hash registered by the
  runtime contract;
- the exact 36 test files declared in upstream `pyproject.toml` pass in the
  locked environment: 376 passed and two skipped.

The registered source-doctor receipt is
`5e686206db8d1447d1b18d27bfffdd792f45c9d3418aedc7c15a5d134d6a6a5c`;
the registered runtime-doctor receipt is
`119890c1806e51752bb4e4449b724795c6b248bcba0c5920c6134b3952117652`.
The in-image `--self-contained` verifier is an integrity recheck only; only the
host verifier compares overlay bytes with the registered CoTCodec files and may
emit Docker build argv. An adversarial review found and motivated this host
binding, then reported no remaining actionable P0/P1/P2 finding after repair.

The checkout contains 62 `test_*.py` files in total, but only 36 are in the
maintained upstream roster. A broader sweep is not silently promoted: one
unregistered test still references the removed `self-evolve-tasks/` tree, and
single-process collection of the broad set can collide across vendored agents'
top-level Python package names. The registered roster is therefore the sealed
source-test contract; the other 26 files are diagnostic debt, not evidence.

The runtime uses `whole-process-local-inside-docker`: PAST-Bench and Hermes+ run
locally relative to each other, while the entire process is contained by the
outer Docker-under-Slurm job. This is required because upstream explicitly
rejects `--runtime container` for self-evolve episode sequences. Discovery job
217 built candidate image
`sha256:6184c9561c3381193a85a895f8dfd1cf670d44eb4090874745faad0d1162c1dc`
in 81 seconds on one Slurm-owned H100. The in-image roster passed 376 tests with
two skips; the network-disabled, read-only, UID 65534, no-capabilities import
doctor passed. The retained Docker archive SHA-256 is `5f7f3fcb…`, the build
receipt SHA-256 is `492d1b90…`, and the image retains
`publication-ready=false`. Slurm job 221 then scanned the retained Docker
archive with Syft 1.51.0 in a socket-free, network-disabled container and bound
the result to immutable local repository digest
`127.0.0.1:5000/cotcodec-past@sha256:93cc065fcba069edd4c3e057a17e9aee6139e5117cb8f7d26207eccf6a21b276`.
The sealed SPDX document contains 277 packages and 3,854 files at SHA-256
`c4a7797712aa5d7b8af0d758b4a4c1cdbd46b38e3e4884461d2efbdd5b46b0c5`;
job receipt SHA-256 is `96a9d921…`. The receipt is explicitly
`SELF_ATTESTED_DISCOVERY_PAST_BENCH_SBOM_JOB`, `scientific_result=false`, and
`external_attestation=false`: it closes the discovery SBOM gate, not the
publication trust-root gate. The image deliberately does not contain the Qwen model server. A model cell
must add a reviewed same-job, no-external-egress transport and bind its own
model/image receipt; an arbitrary host endpoint is not an admissible shortcut.
The complete CoTCodec regression suite now passes 410 tests.

Failed jobs 214–216 and 218–220 are preserved. The first group exposed macOS AppleDouble
metadata in the first tar, rejection of the legitimate archive root directory,
and the login host's Python 3.10 boundary. The SBOM group exposed a non-writable
scanner tmpfs, an overescaped loopback-registry regex, and an undersized scanner
PID ceiling. Each failed closed without sealing a receipt. The
final launcher uses only a stdlib receipt precheck on the host and performs the
full Git-tree/runtime verification inside the exact Python 3.11 build image.

### Stage B — one-family interface and recovery smoke

Family: `memory_ability/SM01_preference_adoption` (8 episodes).  
Agent: Hermes+ at the exact source-vendored revision.  
Model: Qwen3.6-35B-A3B, exact existing model receipt, deterministic decoding.  
Conditions: persistence enabled and disabled.  
Compute: two H100s, maximum two wall-clock hours, four H100-hours total.

Required checks:

- every evaluation/control episode starts a fresh agent session;
- persistence-on and persistence-off receive identical prompts, services,
  fixtures, tool schemas, model receipt, decoding, and turn ceilings;
- the only permitted condition difference is the registered persistence path;
- task order and history anchor/load behavior match the sealed reference
  manifest;
- artifacts and traces are checkpointed after every episode;
- a forced interruption after episode three resumes without rerunning completed
  episodes or changing final hashes;
- no tool or model call occurs before the exact task/condition receipt is
  durably committed.

Kill the lane on malformed tool calls, session-state bleed, task/order drift,
non-repeatable deterministic decoding, failed resume equivalence, missing
pathway evidence, or projected Stage C cost above eight H100-hours.

**Executed 2026-08-14 — killed.** Jobs 246/248/250/252 proved controlled stop,
atomic episode checkpoint, fresh-job resume, and completion. The resumed run
showed a descriptive `+0.60` mean evaluation-score delta for persistence, but
the independently uninterrupted job 254 diverged inside the shared prefix.
CPU audit 256 sealed two score mismatches, two pass mismatches, and seven trace
mismatches at report SHA-256 `da6f5966e928787b40e63bff662add5bb06e56a4c0551ce826c17cf1aeb326b8`.
Status is `PAST_SM01_RESTART_EQUIVALENCE_FALSIFIED`; Stage C is blocked. See
`research/past-sm01-qwen36-discovery-2026-08-14.md`.

### Stage C — four-family bounded mechanism screen

Use one canonical family per ability:

| Ability | Family | Episodes |
| --- | --- | ---: |
| Memory | `SM01_preference_adoption` | 8 |
| Procedural reuse | `PC01_sop_bootstrap_01` | 8 |
| Proactive lookup | `PG01_release_decision_followup` | 8 |
| Update | `EP03_recall_then_modify` | 7 |

There are 31 episodes per condition and 62 total episode executions for one
model/agent repeat. Run only if Stage B's measured token and latency ledger
projects the full screen below eight H100-hours. Keep the remaining 173 declared
episodes sealed and unopened until the pilot passes.

Primary outcome: family-balanced later evaluation score difference,
`persistence_on - persistence_off`. Report each family separately and do not
pool controls, learning episodes, and evaluation episodes into one success rate.

Co-primary validity outcome: fraction of successful evaluation episodes with
the preregistered pathway evidence, such as a memory write followed by later
memory use, skill reuse, session search before action, or recovery of the
updated rather than stale state.

Secondary metrics:

- executable tool/task score and grader subcomponents;
- shortcut, wrong-mechanism, and no-persistence control scores;
- memory writes, reads, searches, retrieved bytes, injected tokens, and memory
  administration model calls;
- input/output tokens, time-to-first-action, p50/p95 episode latency, GPU time,
  and dollar-equivalent cost;
- stale-state use, unnecessary proactive lookup, malformed tool arguments,
  prompt-injection behavior, and cross-session residue;
- pathway precision: successful tasks with valid pathway evidence divided by
  all successful tasks;
- pathway recall: successful persistence-dependent tasks with valid pathway
  evidence divided by all such successes.

Inference is descriptive in the 31-episode screen. Do not treat episodes inside
one family as independent replicates. A confirmatory run needs repeated model
seeds or independent runs and family-clustered uncertainty with the complete
preregistered family roster.

### Stage D — model and harness transport, only after Stage C

The intervention and task roster stay fixed. Expansion order:

1. GPT-OSS 120B open checkpoint as the larger local-model confirmation, after
   its complete immutable artifact receipt and four-task interface doctor;
2. Kimi K2.6 hosted frontier confirmation through the contained provider path;
3. one second agent runtime, Nanobot or ZeroClaw, to test whether the result is
   an agent-specific memory affordance rather than a benchmark universal;
4. GPT-5.4 or another exact frontier-provider checkpoint only after provider
   origin, secret-file, response, usage, and price receipts are sealed.

Kimi Linear 48B is not part of this benchmark lane. It remains a separate
architecture/custom-code diagnostic. Tinker is relevant only if a later stage
trains an external memory controller from frozen targets.

## Matched active/inactive controls

PAST-Bench cannot by itself distinguish all active/inactive mechanisms. Later
mechanism cells must keep these controls separate:

| Mechanism | Open control | What it actually tests |
| --- | --- | --- |
| Self-managed core/archive paging | Letta | Agent spends calls editing visible core and querying external stores. |
| Context eviction and recovery | LightMem2 | Completed task/tool output moves to an archived stub and can be faulted back. |
| Monotonic tier promotion | Shodh | Working→Session→LongTerm promotion with decay/reinforcement; no demotion. |
| Named active query spaces | Mnemon | Host chooses which graph spaces participate in recall. |
| Background multi-level consolidation | JiuwenMemory | Raw→summary→structured→profile transformations; graph is a separate path. |
| Simple flat retrieval | BM25, dense BGE, raw-log RRF, Fidelis | Tests whether structure or paging beats a zero-write-LLM floor. |

A pager claim requires promotion and demotion under a fixed active budget and
must beat recency/LRU at `K={2,4,8}` after charging administration calls. A
terminal long-term tier, an archived tool-output stub, or an active namespace
filter is not automatically a pager.

## Containment and checkpoint contract

All model-bearing work runs in Docker under Slurm. The operator may use tmux on
the login host, but tmux is not recovery. The Slurm job owns the workload.

Checkpoint atomically at episode boundaries to persistent storage and on USR1:

- exact source/image/SBOM/model/agent/experiment roots;
- condition and family/task cursor;
- completed task IDs and result/trace roots;
- persistent agent home/state snapshot and hash;
- model decoding and RNG state where supported;
- mock-service fixture and mutation state;
- usage/cost ledger and predecessor Slurm job ID.

Keep two validated generations. A fresh job must reproduce the uninterrupted
suffix byte-for-byte for deterministic cells. Never run provider keys in logged
environment exports, never enable unreviewed remote model code, and never use
sudo to make the lane work.

## Promotion and kill rules

Promote from Stage C only if:

- all source, containment, task-order, session, checkpoint, and pathway doctors
  pass;
- the persistence-on condition improves at least two of four abilities without
  a material regression in another;
- successful later episodes show the intended pathway rather than prompt
  shortcuts or generic model competence;
- safety failures do not rise by more than five points and tool-argument
  correctness does not fall by more than ten points;
- memory-administration cost does not erase the task improvement.

Kill or narrow the claim if persistence-off ties persistence-on, pathway
evidence is absent, a flat retrieval floor ties the memory runtime at lower
cost, results reverse across agent runtimes, or any session bleed/source drift
appears. A well-instrumented null is a valid outcome.
