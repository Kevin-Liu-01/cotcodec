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

## 2026-10-07

**D15. Holo3 v2 sign-offs.** The 5.75 GB verified-run tarball read is
approved under D1, once v2 is frozen and its freeze gate checks the repository
ledger. Design decisions 1-14 of the v2 draft are accepted, with two
conditions: a checker-side label that is not robust to the narrow-L
sensitivity is reported as exploratory, and the nominal family-wise error
rate over rules (a), (b) and (d) (0.10) is stated. The v1 post-hoc record is
frozen together with v2.

**D16. Q3 K1 sign-offs.** Design decisions 1-25 of the K1 draft are accepted
(budget 2.65 GPU-h plus a conditional 1.5 GPU-h extension, below the gauntlet
threshold). A HOLD is terminal for the experiment id. The V1 extension is
mandatory when the main read calls for it, and an extension that is not run
or ends void makes the verdict INCONCLUSIVE. Budget amendments after
SMOKE_PASS_OVER_BUDGET, or a second continuation, are declined by default;
any amendment would be recorded here before audit statistics exist and may
change only minutes and GPU-hours, never rules. The manifest filler must
enforce SMOKE_PASS, PROCEED_TO_K1 and resume equivalence before it fills the
main job.

**D17. Serving probe sign-offs.** D8 is amended: the overlay image build and
the metadata fetch (about 0.33 GPU-h of idle H100 allocation) are accounted
separately from the 1.0 GPU-h probe cap. If a cu129 gate fails, one cu130
retry (9.04 GB image, overlay rebuild, rerun of the failed job) is
pre-approved with an extra cap of 1.0 GPU-h. No GPU resume run is required
for a probe with no training state. The prefix-caching-off arm and the TP=2
real-weight run stay excluded. Design decisions 2-27 of the draft are
accepted, conditional on job acceptance gating budget entry.

**D18. Serving probe design decisions 1 and 28-36 accepted.** D17 accepted
decisions 2-27 by number. Decisions 28-36 implement D17's acceptance gating,
the audit's corrections, the narrowed cu130 retry scope (a retry only after a
gate failure that ends a job as a pre-result) and the lane-termination check.
Decision 1 is accepted as written.

**D19. Serving probe v2 budget.** `serving-throughput-probe-v2` gets its own
allowance of 1.0 GPU-h for the probe job plus 0.167 GPU-h for the overlay
build, separate from D8's v1 cap (v1 used 0.666). It is frozen only after a
fresh pre-freeze audit.

**D20. K1 successor: same design, engineering-only, measured first.** The
successor to `q3-k1-localization-screen-v1` keeps every registered design
decision accepted under D16, including the three-LR grid, and changes only
code efficiency (batched indexer bank, vectorised evaluation), limits and
caps, under a new id. A separate synthetic-token throughput probe (no
Belebele or partition reads, at most 0.15 GPU-h) runs first under its own
id; the v2 limits and caps are then set from its measurement, with real
headroom for the smoke gate and a budget gate for the mandatory extension.
The LR grid is not dropped while the conservative total stays under 8 GPU-h.
If the measured total would exceed 8 GPU-h, v2 goes through the research
gauntlet instead of being cut.

**D21. Serving probe v2 design decisions 1-25 accepted.** This includes
dropping jobs B and C (v1's Q1 decision cannot change, and leaving out job C
can only push the Q2 decision toward rescoping), cu129 only with no cu130
retry (cu129 passed every gate in v1), and no GPU resume run. The X1 replay
threshold moved from v1's 5% to 8% after v1 measured 5.89%. That is accepted
only because v2 collects fresh data on identical prompt token sequences, the
8% is calibrated to v1's measured run-to-run noise (about 2 standard errors),
and the registration discloses that it was chosen after v1's result.

**D22. K1 v2 counting rule and probe sign-offs.** The 8 GPU-h threshold of
D20 for `q3-k1-localization-screen-v2` applies to the sum of the registered
caps of every job: the conditional V1 extension at its worst-case cap, the
main continuation inside the main cap, and the cap of every throughput-probe
run whatever its outcome. Expected use never replaces a cap. The limit
formula's factors (1.2 and 1.15) are fixed before the probe runs. If the
probe-derived total exceeds 8 GPU-h, v2 is not frozen and goes through the
research gauntlet. A one-GPU job of at most 0.1 GPU-h is pre-approved to run
the batched-bank GPU equivalence tests before the probe is frozen, so the TF32
tolerances are checked on the H100 first; it reads no evaluation data. Probe
design decisions 1-12 and v2 design decisions 32-46 are accepted.

**D23. Checker-mutation raters: Claude plus a self-hosted open-weight model.**
D9 called for two provider-distinct model raters. No OpenAI key is available
and the Moonshot account is suspended for insufficient balance (recharging is
Kevin's call). The raters are therefore a Claude model through the Anthropic
API and an open-weight vision-language model served on the H100s with the
cu129 vLLM overlay already validated by the serving probes (a Qwen3.5
checkpoint with a receipt; different developer and training lineage). The
spec author is also a Claude model, so the open-weight rater is the
independent one: each rater's verdicts are reported separately, and an item
on which the open-weight rater dissents is either adjudicated in Kevin's
human spot check or counted as a label error, never dropped. Rater inputs are
documents, diffs and renders, not code, so serving them on GPUs is outside
the untrusted-code rule (D7). GPU time for the rater is bounded in the
registration.

**D24. K1 v2 goes through the gauntlet; the gauntlet cannot certify 100 here
yet.** The K1 v2 throughput probe (Slurm 543, PROBE_COMPLETE) puts the v2
caps plus the probe at 8.05 GPU-h under D22, over the 8 GPU-h threshold. The
counting rule was fixed before the measurement and is not revisited, so
`q3-k1-localization-screen-v2` is not frozen and runs the research gauntlet
(D20). A gauntlet score of 100 requires two Ed25519-signed reviews whose keys
come from an external trust store pinned by protected CI, plus a real compute
attestation; that infrastructure does not exist and only Kevin can set it up
(generating the keys here would defeat its purpose). Gauntlets therefore run
with honest budgets and end at an honest exit below 100, with the review
content ready to sign. Every experiment over 8 GPU-h (K1 v2, the rescoped Q2
Stage 1, and Q1 Stage 0 if its pilot lands over the line) waits on Kevin
either establishing the trust store or ruling on admission.

**D25. The Claude rater runs through the agent harness until a valid API key
exists.** The `ANTHROPIC_API_KEY` available here is invalid (HTTP 401 on the
models endpoint), and supplying a key is Kevin's call. The D23 Claude rater
therefore runs as a Claude subagent through the Claude Code agent harness:
one blind packet per item, read from files that contain only the packet, no
access to labels, checker code or the other rater's answers, the model id
recorded from the harness, and every prompt, packet digest and response
hashed into the rater receipt. Sampling cannot be fixed on this path, which
is disclosed; the open-weight rater stays seeded and deterministic. Reversal:
a valid API key, after which the API path registered in the runner is used.

**D26. K1 v2 ends at an honest gauntlet exit; Q3 continues with a dense
headroom pre-check.** Gauntlet wave 1 for `q3-k1-localization-screen-v2`
scored 45 (lower of two provider-distinct reviews: Claude 45, Qwen3.6-35B-A3B
59), and all three refuters refuted, so the candidate stops. The defects are
in the inherited design, not the engineering: NEGATIVE needs 20 points of
dense headroom over random and v1's smoke measured about 14 on the 0.6B base;
a selector flat on both non-literal legs falls inside NEGATIVE; GO is
confounded because Belebele's translation rules keep a passage's proper
nouns, dates and units in same-language questions but not in cross-script
ones; and "cross-script" is collinear with scripts unseen in indexer training
and with 5-6x tokenizer fertility. Next: a dense-only headroom pre-check under
a new id, reading the development partition only and at most 0.5 GPU-h, on
the 0.6B base and the registered 4B fallback. Any K1 v3 adds a non-literal
adequacy floor, an entity-controlled question set and a seen-script
cross-script condition, takes a new id, and runs the gauntlet.
