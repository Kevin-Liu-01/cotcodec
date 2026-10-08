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

**D27. Checker-mutation raters: upgrade the open-weight rater, isolate the
Claude rater per item, keep the kappa rule.** On the development smoke the
Claude rater scored 12 of 12 shams and contradicted labels on 3-8% of items,
while the open-weight Qwen3.5-9B rater scored half its shams, contradicted
23% and was unsure on 37%, giving kappa 0.22-0.46 against a registered 0.6.
The kappa rule is not relaxed to make the design pass. The open-weight rater
becomes Qwen3.6-35B-A3B (cached with a receipt; validated as a gauntlet
reviewer) if it accepts page images, else the strongest cached multimodal
Qwen; the full development set is rerated with every item rated, within 0.5
GPU-h. The Claude rater runs one agent per item, each in a fresh directory
holding only that item's packet, and a transcript audit voids (as unsure) any
rating whose agent read or ran anything outside its directory. The
equivalence operator `pptx.eq.zorder_nonoverlap` is restricted so it cannot
change rendered order. If kappa still falls below 0.6 with the stronger rater,
the design goes back to review rather than having its rule changed.

**D28. Q1 pilot exposure and D14's precondition.** (Numbered D26 on branch `stage0/q1-gates`; Q1 code comments and the branch's fix-pass evidence still say D26.) The Q1 Stage 0 pilot pass
(jobs 474, 518 and 548, branch `stage0/q1-gates`) scored, with the full gate
and audit stack at replicate 42, five evaluation substrates (S1 L1/3, L2/3 and
L2/74, the Liger cross-entropy and the Triton tutorial matmul) and part of a
sixth (FlagGems cumsum), eight mutants of evaluation parents (three in the
test split) and ten controls, before the preregistration and audit v1 were
frozen. D14's "fixed before any mutant is scored" can no longer be met as
written. Decided: (i) the exposed kernels are listed and hash-bound
(`harness/q1/data/pilot_exposed.json`); (ii) exposed mutants never enter a
sampling frame; (iii) exposed units stay in the primary analysis, because the
outcome-blind pilot rule `q1-pilot/1` chose them and Stage 0 rescores them with
the frozen code, and every primary quantity is also reported without them as a
pre-specified sensitivity analysis; (iv) an audit change motivated by a pilot
verdict (the TF32 `tl.dot` threshold, A5's refusal handling, a cap on the
TF32 convolution tolerance) is labelled data-motivated, is designed and
validated only on S1-cal and other non-evaluation kernels, and removes from
the primary analysis of criteria 2 and 3 and of the mutant metrics every unit
whose correctness it would change (the tutorial matmul family for the TF32
threshold). D14's TF32 policy itself stands; changing it is Kevin's call.
Reversal: Kevin prefers to exclude the exposed units from the primary
analysis outright (criterion 3 then cannot reach 72 units within 8 GPU-h).

**D29. Upstream benchmark test code on GPUs.** (Numbered D27 on branch `stage0/q1-gates`; Q1 code comments and the branch's fix-pass evidence still say D27.) D3 and D7 did not name two
kinds of code that ran with GPU access in Q1 pilot job 518: KernelBench's three
adversarial test kernels (`load_inline` CUDA, upstream commit 29c73cc of
2025-12-27, vendored verbatim and reviewed here) and the unmodified upstream
fidelity code (KernelBench at both pinned revisions, KernelGYM@3a84417f and
kernel_bench_verified@3fdf6fec, unpacked read-only from hash-checked trees).
Both are admitted as trusted inputs under D7: neither is code under study
produced during an experiment, each is pinned by hash, small, and run only as
a control or to check the gates against upstream. They are not part of D3's
validation corpus, which stays TorchInductor output and human-written kernels
from before 2025. Reversal: Kevin rules that post-2025 upstream code waits
for the R580 driver; the three controls and the fidelity runs then move after
the upgrade.

**D30. Action-path A4: observation-service restarts are bounded separately.**
In development the upstream OSWorld guest server crashed once in 8,114
accessibility calls, and its systemd unit then stopped the processes it had
launched. A4 certifies the action path; a guest-server fault belongs to the
upstream observation service, which Stage 1 will run unchanged. Patching the
server would make the runtime differ from the one the leaderboard uses.
Decided before freezing: A4's zero-failure count excludes guest-server
restarts, which are reported; the observation service gets its own registered
bound (at most 5 x 10^-4 restarts per accessibility call, upper 95% bound from
a dedicated campaign); the probe and tap are started in their own systemd
scope so a restart costs at most the entry it hits; and Stage 1 counts
restarts per episode as infrastructure failures. The single-event uncertainty
is reported with A4.

**D31. Q1 Stage 0 budget: engineering first, then re-pilot.** The trimmed
Stage 0 (rule trim/2) fits 8 GPU-h only at the central estimate. As with D20,
the design is not cut: an engineering-only pass computes references once per
problem and draw, then a re-pilot of at most 0.5 GPU-h on S1-cal and other
non-evaluation kernels only (no further exposure of evaluation units) sets the
projection. Stage 0 is admitted only if the high estimate is within 8 GPU-h;
otherwise it waits on the gauntlet (D24). D14's audit policy stays as
registered: the TF32 convolution tolerance above 1 on two pilot problems is
reported as a limitation, and any audit change follows D28's data-motivated
rule.

**D32. Q3 dense pre-check design decisions: accepted, four amended.** The
second fresh pre-freeze audit of `q3-dense-headroom-precheck-v1`
(`program/evidence/2026-10-07/q3-dense-headroom-precheck/prefreeze-audit-2.json`)
found one blocker (the status line would have been frozen as a draft) and
recommended four amendments. Decisions 2-9, 11, 14 and 15 are accepted as
drafted, including decision 5's explicit H2 relaxation: H2 gates a lane only
on FAIL, and any K1 v3 re-tests H2 under K1's bounds whenever the chosen
base's H2 is not PASS. Amended: 1, both lanes run unless the 0.6B smoke
reproduction fails, and the 4B lane never depends on the 0.6B headroom; 10,
the floor's condition (c) passes only on a V1-adequate sigma whose seed-mean
English ML loss is at least 2.5 points, the same reach rule as decision 8;
12, every job, the first included, takes an exclusive filler claim, each
filled manifest is submitted once, the summariser voids a lane with an
unclaimed or over-claim job, the effective window is the limit minus the
3-minute USR1 lead, and the smallest grant leaves 2 useful minutes; 13, only
Triton's cache moves to the run directory. The status line is rewritten
before the freeze.

**D33. Action-path restarts: D30's exclusion extends to A1-A3 and the ladder.**
A1-A3 and the ladder certify the action path, as A4 does. A guest-server
restart during an observation call is an observation-service fault, and A7
now bounds it on its own. Under the strict rule, one such restart (about 87%
likely across A1-A3 and the ladder at the development rate) would fail the
suite for a construct those criteria do not measure. So the narrow
restart-only rule of D30 applies to them too: a trial whose only failures
are a guest-server restart during an observation call and the accessibility
tree that restart left undelivered is excused and reported; any other failure
in that trial counts. A restart during an action (`/execute`) or a guard
still counts, because the same server delivers actions. An A1-A3 entry is
judged on its counted repetitions and needs all but at most one of its
repetitions counted: a second excused trial in one entry counts as a failure.
A ladder rung's "every gating trial passes" reads over its counted gating
trials, and a rung with more than two excused trials does not qualify.
Excused trials' steps stay in the step p95. Also decided before the freeze,
from the review of `13c6790`: A7 sums restarts over every attempt but takes
its call count from the counting attempt only, capped at the plan's 39,036
calls, so cancelling and rerunning cannot raise its pass chance; A7 runs
under attempt 1 at that attempt's N* and is not re-judged when a later
attempt changes N*; a restart during the reset observation is excused the
same way; and the remaining exposure (restarts outside an observation call,
or slower than DesktopEnv's retry window of about 10 s, still count, and a
post-guard restart can cost two entries) is stated with A4 and accepted.

**D34. Checker-mutation audit: D27's consequence fired; one rater retry,
then an honest exit.** With the upgraded open-weight rater (Qwen3.6-35B-A3B,
thinking off, job 702) and the isolated Claude rater (133 items, no voids),
development kappa is 0.27 against the registered 0.6, and the fourth review
(score 57) projects P(kappa >= 0.6) near 0 at confirm scale. The open-weight
rater accepts 19 of 26 violation mutants, often answering one word. As D27
requires, the design went back to review; the kappa rule and its consequence
stay as registered. Decided: (i) the open-weight rater runs once more, with
thinking on (max_tokens at least 4,096), one configuration only; the
development audit is rebuilt and rerated by both raters under the isolated
protocol, within D27's 0.5 GPU-h. If development kappa is still below 0.6, no
other rater is tried: the predictions that need audited labels (P2-P5) leave
the confirmatory headline before the confirm campaign runs, and the campaign
reports P1 and the checker false-negative candidates descriptively. (ii) Gold
defects: every task with an audited K3 item gets a gold sham; when a task's
gold sham is decided reject, its equivalence items leave the equivalence K3
group and are reported as gold defects; labels stay relative to the gold.
(iii) Violation misses: concordant answers that contradict a K3 label join
the blind adjudication pool, mixed with the splits and disclosed; new-file
end states get a text-level difference in the packet; and
`pptx.viol.delete_bound_shape` skips shapes whose frame lies mostly off the
slide. (iv) Audit integrity: the registered transcript audit ties each
transcript to its item (the prompt names it, the answer's item id matches,
the packet was read) and the final-text fallback needs an exact answer
token; opaque ids use a secret per-audit salt, committed as a hash and
revealed after ingest; the rater prompt template is committed and
registered; and the context the agent harness injects is disclosed in
section 9. (v) The rater GPU cap is re-measured with thinking on and
registered so the 807-item maximum fits; the experiment's total stays under
8 GPU-h, or it goes to the gauntlet (D24). Adjudication of the pool stays
Kevin's.

**D35. Checker-mutation study: D34's exit fired; freeze it as a descriptive
protocol.** Development kappa after the thinking-on rerate is 0.066 under
the registered ingest and 0.575 with the workflow harness's relay turn
excepted (a sensitivity: after a session restart the harness put a
byte-identical relay of the session request before every resumed rater's
task, and the registered first-prompt rule voided those 110 otherwise clean
transcripts). Both are below 0.6, so D34 (i) applies: no other rater is
tried, and P2-P5 leave the confirmatory headline; the registered 0.066 stays
as recorded. The fifth review (score 64; scores 55, 62, 56, 57, 64) judged
the study still worth running as a pre-specified descriptive protocol,
because the catalog, blind labels, sampler and analysis can be locked before
any confirm mutant exists. Decided: (i) the analysis code encodes the exit
(P2-P5 always excluded from the confirmatory headline, K6's adequacy claim
retired, K6b and K7 descriptive, K4 reported but no longer a stop); (ii) the
descriptive outputs are pre-specified: P1 (replication only, as before), the
checker false-negative candidates (evaluable should-pass mutants, equivalence
outside probe cells and alternative solutions, that the checker fails) and
false-positive candidates (evaluable should-fail mutants it passes), each
listed with its audit decision, with per-family and per-operator counts and
task-equal shares with intervals, and S1-S7; (iii) the confirm audit covers
every candidate event, every P1 flip, the audit gates and the shams (a census
of what is reported, not a random sample of all mutants), within the
registered 3.0 GPU-h rater cap, and Kevin adjudicates its pool; (iv) the
transcript audit checks every user turn: exactly one equals the rendered
template, and the only other turn allowed is the harness relay frame, which
must precede the task turn, be byte-identical across the run, name no item
and be hashed into the receipt; every transcript of an item, interrupted ones
included, is ingested and audited, and at most one may answer; (v) packets
put the difference section before the file listings, a label-blind format
change disclosed with the dev results it postdates.

**D36. Q3 dense pre-check: v1 ended INCOMPLETE on two code defects; a v2
with the same design.** `q3-dense-headroom-precheck-v1` ran (jobs 727 and
730, 0.42 GPU-h) and gave no combined read. The 0.6B lane's receipt is valid
(K1 smoke 452 reproduced to 1e-6 points), but every receipt the frozen code
can write has a null Slurm job id, which the summariser rejects; and the 4B
lane ran CPU-bound (GPU idle, one core busy, about 61 s per 16-unit chunk
against an 11-minute estimate for the lane) and ignored SIGUSR1, so it was
void. Neither is a design question, and the 4B lane is the informative one:
on 0.6B a NEGATIVE-capable K1 v3 already looks excluded descriptively (H1_CX
12.25, 99% upper bound 15.6) and H2 fails because the model barely answers
cross-script questions. Decided: a successor `q3-dense-headroom-precheck-v2`
keeps v1's data, statistics, decision rules, thresholds and D32's
amendments unchanged. Its code (i) binds each receipt to its Slurm job, with
an end-to-end test that feeds a batch-produced receipt to the summariser;
(ii) honours SIGUSR1 on the 4B path, with a test that loads the 4B
dependencies and runs the entry point as the container's PID 1; and (iii)
removes the CPU bottleneck without changing any computed quantity, shown by
bit-level tests on small inputs and by a registered validity gate: v2's 0.6B
lane must reproduce v1's job-727 statistics (to 1e-6) as well as smoke 452.
Before the freeze, one development timing job of at most 0.1 GPU-h measures
the fixed 4B path; the 4B lane's limit is then at least twice the measured
time plus start-up, with the one continuation kept. Both lanes run under
v2; v1's 0.6B receipt is reported beside v2's. The v2 cap is 1.5 GPU-h,
timing job included, which with v1 stays far below 8 GPU-h. Any K1 v3 still
needs a new id and the gauntlet (D26).

**D37. Q1 Stage 0 after D31: safe execution, one validation job, then the
gauntlet.** The D31 re-pilot (job 713, 0.33 GPU-h) and its review confirm
that Stage 0 is not admitted: through bucket P3 the high estimate is 9.03
GPU-h without the reference store and 9.15-9.66 with it, no registered
execution change brings it under 8, and the pilot cost model under-predicts
the re-pilot's own items by 1.72x, so every projection is biased low. The
re-pilot also showed that the registered 12-items-per-GPU rule (trim/2 item
6) is unsafe: out-of-memory failures on 3 of 8 problems, healthy slots
retired under contention, and silent `na` results in A5. Decided: (i) the
execution policy `q1-stage0-exec/2` (memory-sized items per GPU, a free-memory
guard, a health check that drains and retries before retiring a slot, one
resource-failure marker list) replaces trim/2 item 6; it changes execution
only, never a gate, tolerance, family, tier, sample or rule; (ii) the
reference store serves gate (c) and A1-A5 but not gate (a), whose fidelity to
upstream KernelBench needs the reference in the candidate's process; one
shared realization per problem and draw of a nondeterministic reference is
accepted and disclosed; (iii) one validation job under exec/2, on the
re-pilot's non-evaluation kernels plus the three KernelBench adversarial
controls under the store, within the 0.17 GPU-h left of D31's 0.5, measures
the policy's safety and cost; (iv) D31 stands: Stage 0 waits on the gauntlet
under D24, and a gauntlet wave on the Stage 0 design runs now, so the
admission ruling (Kevin's) has a scored, reviewed package. D14's audit policy
stays as registered (D31).

**D38. Checker-mutation protocol: the eighth draft's choices, and the minor
items fixed before the freeze.** The sixth review scored the D35 protocol 80
(scores 55, 62, 56, 57, 64, 80) and its one blocker, user messages delivered
as harness attachments, is fixed by a registered allow-list of entry and
attachment types that fails closed. Accepted as implemented: the census audit
with its seeded stratified fallback; gold shams for every audited task (wider
than D34's K3 tasks); the relay frame registered under D35's constraints; and
the difference-first packet order. Because a freeze pins this code, the
review's minor items are fixed rather than recorded: the fallback takes the
largest budget that fits; a registered collector maps every transcript of the
rating run to its item and refuses any it cannot map; audit summarize refuses
calls files whose relay frames differ, and the receipt records the relayed
text verbatim; concordant contradictions join the adjudication pool for every
candidate kind, not only the K3 groups; an interrupted attempt counts as
answering only through a structured answer; and stale text is corrected. The
confirm rating runs as one workflow session; if a resume brings a different
relay frame, the items it voids are re-rated once in a fresh, unresumed run,
answer-blind, and both results are reported. Kevin's own items stay his: the
adjudication pool (about 16 items) and the human spot check (about 35 items,
D9).

**D39. Action-path freeze details: D33's limit is per entry, and C3
equivalence fails closed.** D33's A1-A3 limit counts excused trials per
entry, over both observation settings, every rerun and, in A1, both seeds'
shuffles; D33's author confirms that reading here, as the registrations now
state. The final pre-freeze verifier found that C3 could turn a surviving
mutant into an equivalent one by cancelling and rerunning: equivalence was
read from the counting attempt alone. Decided: a mutant is equivalent only if
its counting attempt's stream signature equals the reference's and so does
every earlier attempt's on each cell whose earlier trial had no
infrastructure failure; kills stay read from the counting attempt. The three
status lines are rewritten to the frozen wording before the freeze (as D32
required for Q3), and the analysis treats an unparseable record file like a
missing one, so a write cut short by a kill cannot block a verdict.

**D40. Action-path suite: v1 is invalid on C2; a v2 that reports the miss
and re-tests the prediction honestly.** `q2-action-path-v1`'s first scored
campaign, C2 (job 768, L0-raw, 500 trials, counted), failed: `chord_super_d`
was predicted to pass under raw PyAutoGUI and failed 5 of 5, because the `d`
press reached X without the Super modifier within 1 ms of the Super press.
The other 99 entries matched the prediction. The X event record shows the
loss is real, so the oracle detected a genuine transport defect and the
miss is in the authors' prediction, not in the oracle. Under sections 8 and
11, v1 is invalid: no v1 acceptance criterion may be claimed, and C1, C3
and A1-A7 did not run. This result is reported as it stands. Decided: a
successor `q2-action-path-v2` (with its own `-inputs` and `-executor`)
keeps v1's catalog, oracles, guard, executor, acceptance rules and
development evidence. It changes three things: (i) the L0-raw prediction
lists `chord_super_d` as a failure, with the mechanism (a shell keyboard
grab on a Super chord sent without key holds), and says plainly that this
entry is informed by v1's C2 run; (ii) v2's C2 is therefore read as a
reproduction test of the L0-raw failing set on a new order seed, not as an
a-priori prediction test, and v1's C2 outcome (one unpredicted failure,
verified real) is reported as the a-priori result; (iii) the manifest
renderer takes the run root as a parameter instead of hard-coding the
development host root. Development may characterise the mechanism, and
whether L0-fixed is exposed under Stage-1 conditions, on seed 42 only; A1
then tests L0-fixed on `chord_super_d` as registered. No other rule
changes, and no v1 data enters a v2 verdict.

**D41. Q1 Stage 0 withdrawn after its gauntlet exit; the audit metric is the
blocking problem.** Gauntlet wave 1 on the Stage 0 design ended at an honest
exit (score 45, the lower of 47 and 45; all three refuters refuted; the
declared query budget spent). Both reviewers named the same fatal defect:
under the TF32-admissible policy, the registered audit's A1-A3 metric cannot
separate a correct TF32 matmul or convolution from a destroyed output on most
measured L2 problems (on L2/46 a correct Inductor convolution scores 0.83 and
an all-zeros output 0.999), so it cannot serve as ground truth for Stage 0's
false-accept and false-reject rates, nor for Stage 1. The D37 validation job
(752, 0.11 GPU-h) showed the memory-aware policy is safe (no resource
failures, no retired slots) but that items cost about 2.4 times the model, so
Stage 0 as drafted projects to 20-25 GPU-h at the high point. The refuters
also found its measurement design largely occupied by "Measuring the
Checker" (2609.22220); that matters less for an instrument check than for a
claim, but it removes any case for spending above 8 GPU-h on it. Decided:
(i) `q1-stage0-gate-validation` as drafted is withdrawn; any successor is a
new id with a fresh gauntlet (D24 still applies); (ii) the audit metric is
studied first, on CPU only, from the stored journals of S1-cal and other
non-evaluation units (jobs 474, 518, 548, 713 and 752; D28: no evaluation
unit), to characterise where tolerance-based audits are vacuous and to
design a metric that separates correct reduced-precision outputs from
destroyed ones, or else to restrict the audit to problems and draws where it
can; (iii) the per-item process overhead that dominates cost is designed
for, not yet built; (iv) Q1 Stage 1 still needs the R580 driver upgrade or
written risk acceptance.

**D42. Q3 dense pre-check v2: the 4B attention backend, and a second timing
job.** Building `q3-dense-headroom-precheck-v2` found the 4B lane's real
bottleneck: torch routes Qwen3.5's head-dimension-256 attention to cuDNN,
which builds a new graph for every new sequence shape (about 0.7 s of CPU per
forward, GPU idle). Turning cuDNN attention off on that lane removes it, but
the flash or memory-efficient backend that replaces it is not bit-equal, so it
departs from D36 (iii), and the one timing job D36 allowed (Slurm 766) ran
before the fix, so the 45-minute 4B limit is a projection. The rest of v2 is
bit-equal to v1, shown on CPU and on two real 4B units. Decided: (i) D36 (iii)
is amended for q3-dense-headroom-precheck-v2's 4B lane only: PyTorch's
flash, memory-efficient or math attention replaces cuDNN; the change is
disclosed, its effect is reported by the descriptive `attention_backend_check`,
and no v1 4B number exists for it to depart from; the 0.6B lane stays gated
on reproducing job 727 to 1e-6. (ii) A second timing job of at most 0.1 GPU-h,
in a fresh timing run root and at the code head, times the fixed 4B path,
starting with one `attention_backend_check` so the lane's exact start-up runs
on the GPU; the 4B limit is then set by D36's rule from that measurement,
not from the projection. The v2 cap stays 1.5 GPU-h. (iii) Decisions 16-21 of
the v2 registration are accepted as amended by this decision, after a narrow
re-check of the measured limits; the status line and the decisions' lead-in
name D42 when frozen.

**D43. Action-path v2: D40's stated cause is corrected, and the judge stops
reading a state the tap cannot observe.** The seed-42 development D40 allowed
(jobs 784-787; `q2-action-path-v2.md` section 26, branch
`stage0/q2-action-path-v2`) shows that D40's reading was wrong. GNOME Shell
grabs its overlay key and keybindings synchronously, so the X server queues
later key events until the shell answers, and the RECORD extension reports a
queued event before the server computes its state. The tap therefore records
the `d` press of a Super chord sent within a few milliseconds of Super_L with
state 0, and without the locked NumLock bit that every processed event
carries, while the shell did receive Super+d (15 of 15 L0-raw trials showed
the desktop). v1's C2 failure is in what the oracle channel records, not in
delivery; v1's a-priori prediction was right about delivery. v1 stays invalid
under its own section 8, which judges the record, and that result stands as
reported. The branch's draft decision accepted the remaining exposure (a slow
shell answer would fail L0-fixed trials whose chord was delivered: at the
bound of 2.3% per trial, A4's 276 such trials would almost surely meet one),
which would let the suite fail, after three repair attempts, on an artifact
of the oracle. Decided instead: v2's judge treats the modifier state of a key
event recorded without the guard-guaranteed locked lock bits as unobservable
(such an event was recorded while queued, which requires an active shell
grab, which requires the grab key to have been pressed) and judges it on
kind, keycode, keysym and order only; every other event is judged as before.
The L0-raw prediction for `chord_super_d` follows from the new rule, and
v2's C2 stays a reproduction test, disclosed as informed by v1's C2. The
change is developed on seed 42 (positive and negative cases, including a
dropped modifier on grabbed and ungrabbed chords) and reviewed before v2's
freeze. Whether a later registration should observe the shell's side of a
grabbed chord directly stays with Kevin.

**D44. Q3 dense pre-check v2: the 4B limit is the largest estimate, and v2's
decisions are accepted.** The second timing job (Slurm 810, 0.045 GPU-h)
timed the fixed 4B path: cold and warm units now take the same time (0.16 to
0.43 s per unit by stage), the per-shape cost is gone, and v1's evaluation
path is bit-equal to v2's on five units. Under D36's rule the 4B limit was
set at 30 minutes from an estimator (stage means scaled by length) chosen
after a first pass came out over the cap; the narrow re-check showed that a
per-stage line fit gives 31 minutes and the larger of the two in every stage
32. Decided: the 4B lane's limit is 32 minutes (cap 0.533 GPU-h), the largest
of the estimates computed, so D36's "at least twice the measured time" holds
under each of them; the registered caps total 0.933 GPU-h within D36's 1.5.
Decisions 16-21 of `q3-dense-headroom-precheck-v2` are accepted as amended by
D42 and this decision (D42 (iii)); its status line and decisions' lead-in
name D42 and D44 when it is frozen.

**D45. Action-path v2: D43's rule narrowed, and applied to C3.** The two
adversarial reviews of D43's implementation found that the rule (read a
key event without its modifier state when it lacks the guard-guaranteed
Mod2) rests on a precondition nothing checks: that the event was queued by a
grab its own entry activated. A synchronous grab already active when an
entry's first key arrives would make every event of the entry read without
state, so a raw-only trial in which the server processed nothing could pass;
the guard cannot see such a freeze. They also found that C3's equivalence
comparison still reads the recorded state byte for byte, so one slow shell
answer could make a no-op mutant non-equivalent and fail C3 (up to about
7%), the kind of oracle artifact D43 removed elsewhere. Decided: (i) an event
is read without its state only when a key press recorded with Mod2 comes
before it in the same window; otherwise its state is judged as recorded. None
of the 280 development events changes. (ii) The same narrowed rule applies
inside C3's stream signature and earlier-attempt comparison. (iii) The
reports section 12 promises (each event read without its state, its offset
from the preceding processed press) are produced by the analysis. Because
the judge changes, the seed-42 final development runs are repeated at the
new commit and the executor addendum's byte-identity statement names it.

**D46. Q1 Stage 0 closes on the audit-metric study; Q1 GPU spend stops until
Stage 1 can run.** The CPU-only study D41 ordered (branch
`stage0/q1-audit-metric`, evidence under `program/evidence/2026-10-08/`,
replicated by an independent critic and attacked by an adversarial one, no
evaluation unit touched) found the registered audit's failure analytic: its
metric scores an all-zeros output at 1/(1+kappa) = 0.999 for any reference,
and TF32 noise on cancelling sums pushes the threshold above that on most L2
problems, so no threshold or multiplier repairs it. A noise-relative
normaliser (rule `q1-audit-metric/2`: max-abs and blockwise error over the
largest error of a yardstick of correct references, a floor, and a decoy
determinacy gate) certifies gross destruction cleanly, but under TF32 valid
algorithms already sit up to about 45-50 times the yardstick while a 1%
fault scores a median of about 15, so most 1%-level faults (239 of 272) fall
in an ambiguous band. With the measurement design largely occupied by
"Measuring the Checker", Stage 0 projected at 20-25 GPU-h, and its only
consumer, Stage 1, blocked by the R580 driver and the policy licence, a
successor Stage 0 is not worth funding now. Decided: Q1 Stage 0 is closed
with this study as its outcome (a limiting result: under a TF32-admissible
policy a tolerance audit can certify that a kernel is not grossly wrong, not
that it is correct to 1%); no further Q1 GPU job runs until Stage 1 can. If
Q1 is revived: Kevin rules on D14 (is TF32 truncation admissible), rule /2
is the audit design, an S1-cal-only GPU pilot of about 1.2 GPU-h tests it on
real kernels first, and any reduced Stage 0 takes a new id and a fresh
gauntlet.
