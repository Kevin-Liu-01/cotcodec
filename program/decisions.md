# Decision log

Design and policy decisions made while running the program autonomously.
Each records what was decided, why, and what would reverse it. Kevin can
overrule any of them; decisions marked **Kevin** are reserved for him.

## 2026-10-06

**D1. Public research downloads are authorized.** Kevin asked on 2026-10-06
to "do everything you need to do this research rigorously and correctly".
Public, licensed research artifacts (model weights, datasets, container
images, trajectory archives) may be downloaded to the H100 host's persistent
storage, which has about 21 TB free. Each download is recorded with source,
revision, size and SHA-256. Reversal: Kevin asks to cap downloads.

**D2. Outward actions stay reserved.** Contacting third parties (letta-ai,
paper authors, the host administrator), force-pushing, changing host
configuration and accepting the R570 risk for model-generated GPU code are
**Kevin** decisions. Drafts are prepared; nothing is sent.

**D3. No model-written kernels in Q1's validation corpus.** Kernels written
by Claude in this session would arguably be model-generated code under the
R570 rule. Q1 Stage 0 instead uses compiler-generated kernels (TorchInductor)
and human-written kernels from before 2025 (FlagGems v1.0 manual kernels,
Liger-Kernel v0.3.1, Triton tutorials). Their deterministic mutants are
derived by reviewed harness code. Reversal: the R580 upgrade lands.

**D4. TED2020 is dropped from Q3 K1.** Its license is CC BY-NC-ND 4.0, and
Kevin's employer is a translation company. Training an indexer on it is
arguably a derivative use and not clearly non-commercial in context. K1 uses
permissively licensed parallel data only. Reversal: a written license
opinion.

**D5. Dr. Kernel-8B stays out of receipted runs.** Its model card and repo
declare no license, and KernelGYM has no LICENSE file. The receipted lane
requires a publication-eligible license. Qwen3-8B (Apache-2.0, same layer
shapes) stands in for the throughput probe. Choosing Q1's Stage 1 policy, or
asking the authors to add a license, is **Kevin**'s call.

**D6. KernelGYM's hacking check is reimplemented, not vendored.** Without a
LICENSE file its code cannot be copied into this MIT repository. The
reimplementation follows the released code's behavior, which differs from
the paper's description, and both are documented.

**D7. "Model-generated code" means untrusted code under study.** The R570
rule's purpose is to keep code that no one has reviewed, and that an
optimizer may have shaped adversarially, away from an unpatched driver. Harness
code drafted by an engineering agent, reviewed, tested and committed here is
project code and may run on GPUs. Sampled kernels, policy rollouts and programs
an agent writes during an experiment are untrusted. This matches the original
constraint ("no untrusted model-generated code with GPU access"); the earlier
wording in the docs was broader than intended. Reversal: Kevin rules otherwise.

**D8. Serving probe budget is 0.75 GPU-h expected, 1.0 cap, plus an optional
0.5 GPU-h dummy-weight extension.** The program doc said 0.5 GPU-h; the
reviewed design adds a closed-loop episode replay and the missing 27B and
35B-A3B rungs. Both stay far below the 8 GPU-h gauntlet threshold. The
measurement is what every later GPU budget depends on.

**D9. The Q2 checker-mutation audit uses provider-distinct model raters.**
The reviewed plan calls for two blind human raters for about 300 mutants, and
none is assigned. The audit runs with two raters from different model
providers under the same blind protocol, labelled as model raters in every
result. A stratified sample is set aside for a human spot check by Kevin, and
the result states that the human check is pending. Reversal: human raters
become available.

**D10. The Holo3 v1 analysis is recorded as post-hoc.** Its preregistration
was written after the per-task files were on disk, and its deciding test was
nearly fixed by totals already known. It goes in the ledger verbatim with that
label. Confirmatory claims come only from a v2 frozen before the archive
contents it tests are read. The OpenCUA rerun comparison was already inspected
during review and is exploratory.

**D11. The Q2 Stage 1 noise anchor moves from Holo3 to OpenCUA.** Surfer H's
agent configuration is server-side and cannot be rerun, so "Holo3 rerun within
2 SE of the official rows" cannot be met. OpenCUA has open weights, agent code
in the OSWorld repository, and six public three-run sets. The Stage 1
criterion is reworded before the gauntlet. Reversal: Kevin prefers a
self-hosted Holo3 contrast (70 GB weights and GPU time, gauntlet required).

**D12. VM campaigns run as CPU-only Slurm jobs.** The Docker submitter
requires at least one GPU, but desktop VMs need none. VM work runs through a
dedicated CPU-only batch script that requests no GPU, launches pinned
containers without `--gpus`, and asserts in its receipt that no
`/dev/nvidia*` device is visible. The GPU device files are world-writable on
this host, so every runner, harness and executor container must be GPU-less.

**D13. No new Docker networks.** Creating a user-defined Docker network adds
dockerd-managed iptables state, which is close to the host configuration
reserved in D2. VM containers run without published ports. The runner joins
the VM container's network namespace. If that proves infeasible, ports bind
to 127.0.0.1 only, and the remaining exposure to other local containers is
recorded. This host is single-user.

**D14. Q1 Stage 0 TF32 policy and contract tier.** The speed baseline is
TF32, so the primary audit is TF32-admissible, with a strict-fp32 audit
reported as a secondary. The primary contract tier is "never silently wrong
at held-out shapes". A kernel that refuses an unsupported shape is not
counted as silently wrong. Both are fixed in the Stage 0 preregistration
before any mutant is scored.
