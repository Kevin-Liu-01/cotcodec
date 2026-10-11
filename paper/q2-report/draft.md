# What an open computer-use benchmark comparison measures: a certified action path, a rerun noise floor and checker defects on OSWorld

Technical report, draft of 2026-10-11. CoTCodec research program, question Q2
(`program/questions/q2-calibrated-cua-instrument.md`). Author: Kevin Liu. This draft was
assembled under decision D71 (iii) from the program's frozen registrations and committed
evidence; the author has not yet reviewed it.

> **Status: DRAFT. Not published, not for circulation.**
>
> - Publishing this report is an outward action reserved to Kevin (D71 (iii); `AGENTS.md`
>   hard rule 9).
> - Section 5 reports OSWorld checker defects that have not been disclosed to the OSWorld
>   maintainers. That disclosure waits on Kevin (`program/state.json`, pending decision 3), so
>   it must be settled before any publication.
> - Every S1a number (section 3) carries the label **not externally anchored**.
> - Every checker-mutation number (section 5) is stated **before Kevin's adjudication of the
>   34-item pool and the 25-item human spot check** (decision D9).
> - Section 9 lists every pending sign-off and four discrepancies in the program record found
>   while drafting.

## Summary

Comparisons between computer-use agents on OSWorld are usually read as differences between
agents. A reported difference also passes through three other instruments: the action path
that turns a model's tool call into desktop input, the run-to-run variation between and within
serving sessions, and the benchmark's own file-state checkers. On one host, we measured each of
the three under frozen preregistrations, using open-weight models where a model was needed, and
audited one public rerun pair. The results, positive and negative alike:

1. **The action path can be certified, and its first certification failed on its own oracle.**
   A preregistered suite (100 catalog entries, seven acceptance criteria, four validity
   controls) accepted the project's runtime and two Qwen3.5 harness adapters on its first
   attempt. That includes zero failures in 64,028 volume trials, which bounds the action
   path's loss at about 1.5 pp per 20-action episode at no more than 32 concurrent VMs. The
   suite's first version was invalidated by its own validity control: the oracle recorded a
   delivered Super+d chord without its modifier. The X RECORD extension reports key events
   queued during GNOME Shell's synchronous keyboard grab before their state is computed.
2. **No harness difference was detected, and none was shown absent.** A two-session study
   (Qwen3.5-4B and 9B, two certified harnesses, 32 primary tasks, 1,808 episodes, no
   infrastructure loss) gave δ = −3.1 pp (H-GA minus H-OSW-fixed; 90% interval −8.9 to
   +2.7). That is neither "Present" nor "near-equivalent" at ±7.5 pp. Rerun-pair discordance
   was 11.3% between sessions and 12.5% within. The registered prediction of a positive
   between-session excess is falsified (one-sided upper bound 0.78 pp), but 9B's success
   shifted by +5.5 pp between its two sessions. The harness share of within-task variance was
   0.055 (one-sided 95% bounds 0 to 0.26), so the registered admission rule for a scale ladder
   came out inconclusive and the ladder did not run.
3. **Within 8 GPU-hours, more tasks buy more than more sessions, and more sessions more than
   more reruns.** A CPU-only design study on these records found that no design in that budget
   could have admitted the scale ladder.
4. **Two checker defects stand out.** `compare_pptx_files` fails 35 of 39 equivalent edits
   that only swap the stacking order of shapes that do not overlap; two model raters both
   accept 29 of those 35 end states as correct and split on the other 6. A GUI-faithful
   LibreOffice save flips 3 of 92 reference golds from pass to fail while both raters accept
   the saved gold as still correct. Kevin's adjudication is pending.
5. **The public Holo3-35B-A3B pair is a session shift.** The two same-day maintainer runs
   differ by a shift that checker time-dependence, step-count behaviour and visible environment
   failures do not explain.

None of it is externally anchored. Of the 116 candidate tasks, 110 changed their config or
their checker code between the OSWorld revision we pin and the revision the public reference
runs were scored with, so no public run could serve as an anchor.

## How to read this report

**Labels.** Each result states its standing with one of these labels:

- *registered*: read by a frozen preregistration's decision rule or prediction;
- *registered secondary*: computed as registered, entering no rule;
- *descriptive*: a pre-specified descriptive output (the checker-mutation study after its exit
  under D35);
- *model-based*: from the CPU design study, which is not a registered analysis;
- *operator count*: computed from raw records by an operator script and reported, never judged.

**Scope of S1a numbers.** Every S1a estimand is conditional on the two realized serving sessions
per size, on this host, image and lane, and on the stated decoding settings. Intervals resample
tasks with the sessions held fixed.

**Units.** "pp" is percentage points. Bootstrap intervals are task-cluster percentile intervals
(10,000 resamples, seed 42) unless stated otherwise.

**Evidence keys.** Every number cites its evidence with a key in square brackets, in its own
sentence or in the caption or lead-in of its table or list. Keys map to repository paths:

| Key | Path |
|---|---|
| [AP2] | `program/evidence/2026-10-08/q2-action-path-v2-acceptance/README.md` (with `acceptance/*.json`) |
| [AP2-VA], [AP2-VB] | the same directory, `independent-verification-stage-a.json` and `independent-verification-stage-b.json` |
| [AP2-REG] | `program/preregistrations/q2-action-path-v2.md` (section numbers given) |
| [AP1] | `program/evidence/2026-10-08/q2-action-path-acceptance/README.md` and `independent-verification.json` |
| [S1A] | `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md` |
| [S1A-AN] | `program/evidence/2026-10-10/q2-stage1-analysis/` (`report/report-guarded.json`, `s15.json`, `glmm-summary.json`, `post-review/post-review.json`) |
| [S1A-REG] | `program/preregistrations/q2-stage1-rescoped-v1.md` (section numbers given) |
| [ANCHOR] | `program/evidence/2026-10-08/q2-stage1-g0/anchor/evaluator-diff.json` |
| [D59T] | `program/evidence/2026-10-10/q2-stage1-d59-tooling/README.md` |
| [DS1] | `program/evidence/2026-10-10/q2-design-study/` (`README.md`, `summary.json`, `fit-*.json`) |
| [DS2] | `program/evidence/2026-10-10/q2-next-step-design-study/README.md` (with its `fit-*`, `ppc-*`, `designs-*` files) |
| [MUT] | `program/evidence/2026-10-08/q2-mutation-confirm/results/README.md` (with `analysis.json`, `summary.json`, `released/confirm-mutants-v1/outcomes.jsonl`) |
| [MUT-A1] | `program/evidence/2026-10-08/q2-mutation-confirm/README.md` (stage A1: K1 and the control runs) |
| [MUT-REG] | `program/preregistrations/q2-evaluator-mutation-v1.md` |
| [ZINV] | `harness/q2_stage1/zinv.py` (module docstring) |
| [H3] | `program/evidence/2026-10-07/holo3-v2/RESULTS.md` and its receipts |
| [H3-REG] | `program/preregistrations/q2-holo3-rerun-audit-v2.md` |
| [SP2] | `program/evidence/2026-10-07/serving-throughput-probe-v2/README.md` |
| [DEC] | `program/decisions.md` (decision numbers given) |
| [STATE] | `program/state.json` (`gpu_hours_ledger`, `pending_decisions_for_kevin`) |
| [LEDGER] | `program/preregistrations/ledger.jsonl` (row numbers given) |

## 1. Motivation

For verifiable machine work, the checker decides what an agent learns and what a leaderboard
says (`program/PROGRAM.md`, thesis). A comparison of two computer-use agents on OSWorld
([OSWorld](https://arxiv.org/abs/2404.07972), 2024-04-11) is the output of a chain:

model → harness (prompt, parser, history layout) → action path → virtual desktop → end state →
checker → verdict

The verdicts are then averaged over a task sample and one or more serving sessions. A
comparison usually means to measure the first two links. The others can each change the number:

- **The action path** can add a difference that belongs to neither agent. cua-speedrun's
  action-path suite found harness parsers that drop multi-call replies, release modifiers
  before the click, or turn a middle click into nothing
  ([cua-speedrun](https://arxiv.org/abs/2609.40284), 2026-09-30, Table 20).
- **Reruns and sessions** add noise. Rerunning the same observation mode on the same web tasks
  changes 12-14% of outcomes ([2608.06171](https://arxiv.org/abs/2608.06171), 2026-08-06). A
  harness swap and a rerun each flip 13% of SWE-bench Verified tasks
  ([2610.04433](https://arxiv.org/abs/2610.04433), 2026-10-03). About 54% of score variance
  among genuine attempts on four scientific coding tasks is run-to-run noise
  ([2610.01618](https://arxiv.org/abs/2610.01618), 2026-10-01).
- **The checker** adds bias. A hand audit found 15.3% of audited FAIL verdicts on computer-use
  benchmarks wrong, 17.5% on the 57 OSWorld-Verified items it audited
  ([2607.28367](https://arxiv.org/abs/2607.28367), 2026-07-30).
- **Harness effects may depend on the model.** Across two coding harnesses, Qwen3.5-4B scores
  8.3% against 37.2% while a large model is unchanged
  ([2609.07925](https://arxiv.org/abs/2609.07925), 2026-09-07). Harness gains diminish with
  capability on SWE-style repair ([2609.32459](https://arxiv.org/abs/2609.32459), 2026-09-26).
  Desktop evidence on that question does not exist yet.

Q2 asks how large each of these other links is on desktop tasks, and whether each can be
bounded before a comparison is read. This report covers five pieces of work, each under its own
preregistration in a hash-chained ledger [LEDGER]:

1. an action-path certification (section 2);
2. a two-session noise-floor and harness study, S1a (section 3);
3. a CPU-only design study on S1a's records (section 4);
4. a mutation audit of OSWorld's file-state checkers (section 5);
5. an audit of two public Holo3-35B-A3B runs (section 6).

**Closest priors.** cua-speedrun runs harness x model x five seeds on OSWorld with an
action-path error suite, screenshots only, with no between-session floor, no task-by-harness
variance share and no checker testing
([2609.40284](https://arxiv.org/abs/2609.40284), 2026-09-30). A G-theory decomposition over 22
benchmarks has few repeated cells, so it cannot identify rerun variance
([2610.00651](https://arxiv.org/abs/2610.00651), 2026-09-30). The nearest work to the checker
audit is the hand audit of FAIL verdicts above, which covers false negatives only, and mutation
analysis of kernel-benchmark oracles ([2609.22220](https://arxiv.org/abs/2609.22220),
2026-09-02). This report makes no novelty claim. The S1a proposal's own novelty check recorded that the
blind closest-prior discrimination had not run (`program/proposals/2026-10-08-q2-stage1-rescoped.md`,
wave 0), and S1a then ran without a gauntlet (D47).

**What this report does not claim.** It ranks no agent and makes no claim about scale; the scale
ladder (S1b) never ran. It says nothing about the accessibility-tree observation, step caps
above 15, sampled decoding, other hosts or images, or any task outside the offline-runnable,
web-free subset used. Section 7 lists the scope in full.

## 2. The instrument: a certified action path

### 2.1 What is under test

The action path is everything between a model's reply and the X server's input events: the
harness parser that turns the reply into actions, one canonical action IR, an executor, and the
guest's input stack. The suite (`q2-action-path-v2`, ledger rows 13-15) tests the three layers
Stage 1 uses [AP2-REG section 3]:

- **L0-fixed**: the project's executor. It sends one guest script per IR action through
  OSWorld's `DesktopEnv.step`, holds keys inside one process with release in `finally`, and
  raises on unknown keys.
- **H-OSW-fixed**: OSWorld `bfd62bdc` `Qwen35VLAgent`, with its emit boundary patched to IR and
  only its own-spec bugs fixed.
- **H-GA**: gym-anything `aae6f7607` `qwen35vl`, unmodified, through an IR adapter.

Three control layers carry known behaviour:

- **L0-raw**: each action as its natural PyAutoGUI 0.9.54 call;
- **H-OSW-up** and **H-GA-buggy**: unmodified upstream parsers with known defects.

**Runtime.** OSWorld `b138d348`; VM image
`happysixd/osworld-docker@sha256:0e6497a9...`; guest disk `Ubuntu.qcow2` (SHA-256
`6bf667a8...`), with Ubuntu 22.04.3, Xorg, GNOME Shell 42.9, 1920x1080; 4 GB RAM and 4 CPUs per
VM; nested KVM on one 8 x H100 host (`fal-h100-01`), CPU-only Slurm jobs [AP2-REG section 2.1].

**Catalog.** The catalog reimplements the 100 public entry ids of cua-speedrun's App. I.1
suite: clicks 18, drags 11, keys and chords 34, scrolls 12, mixed 8, typing 17. Every action
and expectation was written for this repository [AP2-REG section 4.1]. The gating set G is the
86 entries whose actions at least one Stage-1 harness can express. A regression set R of 14
call forms covers the Table 20 failure modes: middle click, modifiers on clicks, two or three
calls in one reply, triple click, scroll at a coordinate, horizontal scroll, `terminate`
failure, non-ASCII text, unusual keys, and the (999, 999) corner [AP2-REG section 3]. Each
harness is judged against its own system-prompt specification. A deviation its prompt declares
is a design difference, never a failure.

### 2.2 Oracles

- **Key events.** An XRecord tap in the guest records core device events in the X server's
  processing order [AP2-REG section 4.4].
- **Text.** A probe window's text buffer, compared by code point, with no normalization.
- **Key, chord and Caps Lock entries (35).** A reference captured by sending the same chords
  through QEMU's human monitor, an input device independent of the executor (R-dev, job 393;
  every entry stable over 5 repetitions).
- **Pointer and scroll entries.** These are labelled *self-specified oracle* in every report.
  Their expectations were written by the suite's authors; only the button numbering was checked
  against the monitor device [AP2-REG section 4.3].
- **Cross-app canary (A6).** Final text is read back from LibreOffice Writer, Chrome, VS Code
  and GNOME Terminal.

### 2.3 Criteria

If any control fails, the suite is invalid. A1-A6 gate every Stage-1 GPU episode, and A7 gates
the screenshot-plus-accessibility setting [AP2-REG sections 7-8].

| Criterion | What it tests | Pass rule |
|---|---|---|
| C1 detection | the two known-defect parsers | each of 9 known-defect cells fails 5 of 5 |
| C2 L0-raw failing set | the PyAutoGUI layer | fails exactly the 8 predicted entries, passes the other 92 |
| C3 mutation score | 28 mutation operators on the scored layers (44 scored pairs) | every scored, non-equivalent mutant killed |
| C4 R-dev agreement | L0-fixed key streams against the monitor reference | equal on all 35 entries in every A1 trial |
| A1 runtime layer | L0-fixed on all 100 entries | 100% of G, 5 repetitions x 2 order seeds x 2 observation settings at N = 1, and the seed-43 shuffle at N* |
| A2 harness layer | H-OSW-fixed and H-GA | 100% of their expressible entries and gating R cells, own spec, both settings |
| A3 stress | 30 timing- and state-sensitive entries | 60 repetitions per entry and layer, zero failures |
| A4 volume | L0-fixed | 64,028 trials over G in 1,068 cold boots, zero failures; at least 10,148 executed actions in each of 7 action classes |
| A5 reset and hygiene | VM reset | 20 of 20 pristine reset checks; base disk unchanged; nothing left behind |
| A6 cross-app canary | four real applications | 300 of 300 trials |
| A7 observation service | OSWorld's guest server | exact one-sided 95% bound on restarts per `/accessibility` call at most 5 x 10^-4 |
| Ladder (N*) | concurrency | largest N whose rung passes with boot p95 at most 180 s and step p95 at most 2x the N = 1 value |

### 2.4 Verdict: accepted on attempt 1

*Registered.* Every criterion passed on its first attempt, with no rerun and no repair (D53)
[AP2]. Two fresh verifiers, one per stage of the campaign, each recomputed every verdict of their
stage with the frozen code from SHA-256-checked raw records, and both reproduced them. Stage B alone re-judged 107,988 ladder, A4 and A7 trials
with 0 mismatches [AP2-VA, AP2-VB].

| Criterion | Job(s) | Result |
|---|---|---|
| C2 | 864 | PASS: L0-raw failed exactly the 8 predicted entries (non-ASCII text skipped; `KP_Enter`; PyAutoGUI raising on buttons 8 and 9) |
| C1 | 866, 868 | PASS: every known-defect cell failed 5 of 5 |
| C3 | 870-962 (47 campaigns, 4,617 trials) | PASS: 42 of 44 scored mutants killed; the other two (M12, M13 on H-OSW-fixed) are comment-only patches predicted equivalent, and came out equivalent |
| C4 | from A1 | PASS: 700 of 700 trials agree with the monitor reference |
| A1 at N = 1 | 968, 970 | PASS: 2,000 of 2,000 trials |
| A2 | 974, 991 | PASS: H-OSW-fixed 97 of 97 and H-GA 87 of 87 in-spec cells, 10 of 10 each; the only failures are outside-spec cells |
| A3 | 1004, 1008, 1013 | PASS: 4,980 of 4,980 trials |
| A6 | 1015 | PASS: 300 of 300 |
| Ladder | 1017-1025 | N* = 32: rungs 8-32 qualify (9,800 of 9,800 trials); rung 40 did not count |
| A1 at N* = 32 | 1023 | PASS: 1,000 of 1,000 |
| A4 | 1027 | PASS: 64,028 of 64,028 trials; 0 restarts in 36,515 `/accessibility` calls |
| A7 | 1029 | PASS: 0 restarts in 39,036 calls; exact one-sided 95% bound 7.67 x 10^-5 per call |
| A5 | 964 and all 15 acceptance campaigns | PASS: 20 of 20 pristine; base disk unchanged in every receipt |

Source: [AP2], all four stages.

**What the zero-failure counts bound.** A4's eight statements hold together at family-wise 95%
(Bonferroni) [AP2-REG section 9; AP2-VB]:

- each of the seven action classes fails at most 4.97-5.00 x 10^-4 per action (10,148-10,216
  executed actions per class), over the catalog's instances as the plan weights them;
- the per-boot failure rate is at most 0.474% (1,068 boots);
- by the union bound, an episode of up to 20 device actions loses at most about 1.5 pp to the
  action path.

The bound covers the L0-fixed runtime path, which is all A4 runs. The harness adapters' parsing
has only A2 (10 repetitions per cell) and A3 (60 per stress entry). The zero-failure per-entry
bounds are much weaker: about 13.9% for A1's 20 repetitions, 4.9% for A3's 60, and 4.2% for A4's
70-repetition mixed entries [AP2-VA; AP2-REG section 9].

**Concurrency.** Rung 40 did not count: 10 of its 80 cold boots failed. In each, `dnsmasq` could
not create an inotify instance, because the host's `fs.inotify.max_user_instances` is 128 and
the VM containers share it [AP2, third stage]. At N = 40 the boots that did start, and all
4,200 trials that ran, were within the timing limits (step p95 3.17 s, 1.18x the N = 1 value).
N* = 32 therefore reflects a host configuration limit, not a measured runtime limit [AP2-VB].
Under the registration, N* below 40 triggers the program kill criterion: cut the Stage-1 task
count before adding GPUs.

### 2.5 The first version's failure and its cause

*Registered (v1); development evidence and decisions D40, D43 and D45 for the cause.*

`q2-action-path-v1` (ledger rows 8-10) ran its first scored control, C2, once: job 768, 500
trials [AP1]. L0-raw failed every predicted entry and one more. `chord_super_d`
(`pyautogui.hotkey('winleft', 'd')`) failed 5 of 5: in every repetition the tap recorded the
four right key events on the right keycodes, but the `d` press, 0-1 ms after the Super_L press,
had core state 0 rather than Mod4. Under v1's section 8, any deviation from the frozen
prediction invalidates the suite. v1 was declared invalid, no v1 acceptance criterion may be
claimed, and C1, C3 and A1-A7 never ran under v1. An independent verifier reproduced the
verdict byte for byte [AP1, `independent-verification.json`]. D40 first read the loss as a
genuine transport defect [DEC D40].

Seed-42 development (jobs 784-787) showed that reading was wrong [AP2-REG section 26; DEC D43]:

- **Only grabbed chords fail.** Under L0-raw, the four chords GNOME Shell grabs (Super+d,
  Alt+F4, Alt+Tab, Ctrl+Alt+Shift+R) failed 10 of 10. The nine chords it does not grab, sent at
  the same 0-2 ms speed, passed 10 of 10, with every modifier state right.
- **The chord was delivered.** In all 15 L0-raw trials of `chord_super_d` (jobs 768 and 784),
  the probe received no key event and lost focus: the shell acted on Super+d. Had the shell
  received `d` without Mod4, it would have replayed `d` to the probe.
- **The mechanism.** GNOME Shell 42.9 grabs its overlay key and keybindings in
  `XIGrabModeSync`. The X server then freezes the keyboard and queues later key events until
  the shell answers. RECORD reports a device event when it is queued, before the server computes
  its state, and does not report it again when the queue is replayed. So the tap recorded the
  queued `d` press with state 0, and without the locked NumLock bit (Mod2) that every processed
  event carries. The server source was read at the X.Org server mirror
  (<https://github.com/mirror/xserver>, master, read 2026-10-08); the guest's Xorg 21.1 release
  was not read, but its records show the same behaviour.
- **Timing decides it.** L0-fixed sends the next key 10 ms after the previous one and holds
  0.1 s. With the keyboard warmed up, its `d` press came 10-14 ms after Super_L, after the
  shell's answer, and carried Mod4 in 127 of 127 development trials.

So v1's a-priori prediction was right about delivery and wrong about what the oracle channel
records.

`q2-action-path-v2` kept v1's catalog, oracles, executor and rules, and changed the judge
(D43, narrowed by D45). A key event recorded without the guard-guaranteed Mod2 bit, after a key
press recorded with Mod2 in the same window, is judged on kind, keycode, keysym and order, not
on modifier state. C3's equivalence comparison reads it the same way [AP2-REG sections 24 and
27]. Two consequences follow:

- **v2's C2 is a reproduction test, not an a-priori test.** It ran on a new order seed (45).
  The only a-priori test of the L0-raw prediction is v1's: one unpredicted failure, verified to
  lie in the oracle's record.
- **The acceptance verdicts do not depend on the new rule.** Across 355,620 key events in A1-A3,
  C1 and C3, every recorded key event carried Mod2. No event in those criteria was read without
  its state, and every verdict would be the same under v1's stricter reading [AP2-VA]. All 53
  events read without their state in the whole program are in C2's four L0-raw grabbed chords,
  each 0-2 ms after the grab key's processed press [AP2, C2].

The lesson for instrument builders: an oracle channel needs its own validity controls. A control
predicted from code reading can fail on the oracle, not on the system it is meant to judge.

**[PENDING: Kevin]** Whether a later registration should observe the shell's side of a grabbed
chord directly. The tap records what the shell's grab held back, not what the shell received
(D43; `program/state.json` pending decision 14).

### 2.6 Limits of the certification

The verdict covers the L0-fixed runtime and the two Stage-1 harness adapters (in-spec cells
only), on this host as configured, at no more than 32 concurrent VMs, with 4 pinned CPUs per VM
[DEC D53; AP2-VB]. It does not cover:

- **Concurrency above 32**, or another host, image or kernel setting. The verdict would need a
  registered deviation or a new registration with its own ladder (D53 (ii)). At 32 VMs the host
  runs about 3 containers below the observed inotify failure point; any other root inotify use
  erodes that margin [AP2-VB].
- **Keys outside the 33 certified keysyms.** A1-A6 certify only the keysyms the gating entries
  use [AP2-REG section 4.5]. S1a counted this exposure: 20-24 of 128 base episodes per (size,
  harness) cell contained at least one key, chord or hold action outside the set, on 18 of the
  32 base tasks. As a description, δ was −4.86 pp on tasks with an exposed episode and −0.89 pp
  on the others [S1A].
- **Catalog instances not tested**, and any per-entry claim at A4's level.
- **The guest server under real task applications**, whose accessibility trees are larger.
- **A whole-boot accessibility failure that no criterion bounds.** In A7 session 193, the guest
  server answered every `/accessibility` call with HTTP 500 for a whole boot, without
  restarting. That is 1 of 1,245 accessibility-setting boots in the suite (exact one-sided 95%
  bound 3.8 x 10^-3 per boot; *operator count*). Had it fallen in A4, A4 would have failed; the
  verifier puts the probability that A4 avoided it at about 0.65 [AP2, fourth stage; AP2-VB].
  S1a read screenshots only, and classified any undelivered observation as an infrastructure
  loss (D53 (iii), D56).
- **C3 is a regression check, not an independent sensitivity estimate.** It repeated
  development's seed-42 conditions with mutants development had already seen killed [AP2-REG
  section 8].
- **Pointer expectations are self-specified**, not measured on an independent device.
- **One governance deviation.** A4 and A7 were rendered and submitted about six minutes after
  the ladder stage handed the rung-40 choice to the program owner. D51 ratified it 13 hours
  later. No verdict changes [DEC D53 (i); AP2-VB]. **[PENDING: Kevin]** Review of this deviation
  (pending decision 14).

## 3. The noise floor and the harness screen (S1a)

### 3.1 Design

`q2-stage1-rescoped-v1` (S1a; ledger row 16, frozen 2026-10-09 22:11 UTC; freeze commit
`d5f5798`) is a rescoped first stage. The original Stage 1 (four sizes x two harnesses x two
observations x three reruns) projected to 431.5 GPU-h in the serving probe (job 466) [SP2].
Both certified harnesses also read screenshots only, so the accessibility-tree arm could not run
on them (D47). S1a stays under 8 GPU-h in every branch, so it needed no gauntlet [S1A-REG
sections 2 and 5; DEC D47, D49].

- **Models.** Qwen3.5-4B and Qwen3.5-9B, bf16, one H100 per engine (vLLM v0.31.0).
- **Harnesses.** H-OSW-fixed and H-GA, the two certified in section 2. They share an upstream
  layout: 100 history turns, older screenshots folded, thinking passed back. They differ in
  their prompts and tool descriptions, modifier handling, drag and scroll semantics, `wait`, and
  how they treat an unparseable reply [S1A-REG section 5.2]. They are close relatives, not two
  unrelated agent designs.
- **Matched settings.** Screenshot only; 15 steps; thinking on with 2,048 output tokens; greedy
  decoding for both (imposed on H-GA, whose agent samples at temperature 1.0 upstream); 60 s
  settle after reset and 20 s before evaluation; the system-prompt date pinned.
- **Tasks.** The pool is the checker-mutation study's 120-task confirm split
  (`program/evidence/q2-mutation/splits.json`) minus the four tasks whose checkers fail their
  own gold (116). An outcome-blind offline-setup rule removed 3
  more, leaving 113 eligible tasks (D55 (ii)). The **primary set** is a 32-task base drawn by
  domain-stratified largest remainder and fixed at the freeze. The other 81 tasks, run as
  extension blocks, form the **registered secondary set** (113 tasks), which enters no rule
  [S1A-REG section 5.4].
- **Sessions.** Two serving sessions per size, at least 12 hours apart, each a fresh engine and
  VM pool with two within-session reruns. That gives four episodes per (size, task, harness):
  512 episodes on the base and 1,808 in all. The jobs ran at V = 20 concurrent VMs, within
  N* = 32 [S1A].

### 3.2 Registered estimands, rules and predictions

[S1A-REG sections 9-12; S1A]

- **D_b, D_w.** Mean fraction of discordant rerun pairs across sessions (4 pairs per cell) and
  within sessions (2 pairs). D_b − D_w is the session excess.
- **δ.** Task-weighted H-GA minus H-OSW-fixed success, pooled over sizes and per size.
- **X.** The mean squared per-task harness effect: δ² plus the task-by-harness variance. X_c is
  its task-specific part.
- **π.** The harness share of within-task outcome variance, π_z = (X⁺/4)/(X⁺/4 + D_b/2), with
  each harness used half the time. π_small is the mean over the two sizes.
- **Inference.** Paired t on δ (90% t interval); one-sided sign-flip test on X; per-size
  sign-flip test on the session shift. The secondary model is a crossed logit GLMM.
- **DR2 (harness pair).** *Present* if Holm over p_δ and p_X rejects at family-wise 5%.
  *Near-equivalent* if not Present, δ's 90% interval lies within ±7.5 pp, and π_small's
  one-sided upper bound is below 0.12. *Inconclusive* otherwise. The ±7.5 pp margin is the
  question file's 7-8 pp line, which has no derivation; it is kept as the only pre-existing
  yardstick.
- **DR5 (admission of the scale ladder S1b).** *GO* if π_small's one-sided 95% lower bound
  exceeds M = 0.13; *NO-GO* if its upper bound is below M; *INCONCLUSIVE* otherwise. M is the
  smallest small-rung share the planned ladder could detect with 80% power, maximized over six
  planning cells. Only GO lets S1b go to the gauntlet (D47). Kevin accepted DR1 and DR5 in place
  of the question file's lines on 2026-10-09 (D55 (i)).
- **Predictions.** P1: D_b − D_w > 0, from the Holo3 audit. P2: D_b in 6-20%. P3: the pair is
  not Present. P4: 4B is at least 10% under one harness. P5: realized cost is at most the cost
  card's high price.
- **DR-A (anchor).** An OpenCUA-7B run against its three public runs was registered as a
  runtime check (D11). It was **unavailable before any GPU job**: only 6 of the 116 tasks keep
  the config and checker code the public runs were scored with, against 58 needed. 110 tasks
  differ, by config or by the AST of a checker definition they reach, between the pinned
  `b138d348` and the public revision `00804f81`, which is inferred from the run window and not
  recorded in the archive [ANCHOR; S1A-REG section 5.7]. Every S1a output is therefore labelled
  **not externally anchored**, and nothing replaces the question file's Holo3 kill line (D55
  (i)).

### 3.3 Outcome for the realized sessions

*Registered.* All four A1 jobs ran (9B and 4B, session 1 on 2026-10-09/10; session 2 on
2026-10-10). Each scored 452 of 452 episodes. DR0 never fired, and not one episode was lost to
infrastructure [S1A].

| Rule or prediction | Outcome | Numbers |
|---|---|---|
| DR0 validity | does not fire | 0 of 226 first attempts lost in every (size, harness) cell of every job |
| DR-A anchor | ANCHOR-UNAVAILABLE | label: not externally anchored |
| DR1 4B floor | does not fire | 4B pooled success 28.91% (H-OSW-fixed) and 26.56% (H-GA) |
| **DR2 harness pair** | **Inconclusive** | not Present: p_δ = 0.367, p_X = 0.459; not near-equivalent: δ's 90% interval [−8.91, +2.66] pp crosses −7.5, and π_small's upper bound 0.260 is not below 0.12 |
| DR4 cost | does not fire | highest realized 0.002702 GPU-h per episode, against the high price 0.011274 |
| **DR5 S1b admission** | **INCONCLUSIVE** | π_small = 0.055, one-sided 95% bounds [0.000, 0.260], against M = 0.13 |
| **P1** session excess > 0 | **falsified** | D_b − D_w = −1.17 pp, 95% [−3.52, +1.56]; one-sided upper bound 0.78 pp < 1 pp |
| P2 D_b in 6-20% | not falsified | D_b = 11.33%, 95% [5.86, 17.19] |
| P3 not Present | not falsified | DR2 Inconclusive |
| P4 4B not at floor | not falsified | 28.91% and 26.56% |
| P5 cost at most high price | not falsified | 0.002497-0.002702 GPU-h per episode |

Source: [S1A], decision rules and predictions; [S1A-AN] `report/report-guarded.json`.

Primary estimands (base, 32 tasks, raw verdicts) [S1A]:

| Estimand | Estimate | 95% interval |
|---|---:|---|
| Success, 4B: H-OSW-fixed / H-GA | 28.91% / 26.56% | |
| Success, 9B: H-OSW-fixed / H-GA | 32.81% / 28.91% | |
| δ pooled (H-GA − H-OSW-fixed) | −3.12 pp | [−10.55, +2.73]; 90% t [−8.91, +2.66] |
| δ_4B; δ_9B | −2.34 pp; −3.91 pp | [−10.16, +4.69]; [−12.50, +2.34] |
| D_b pooled (4B; 9B) | 11.33% (14.06%; 8.59%) | [5.86, 17.19] |
| D_w pooled (4B; 9B) | 12.50% (16.41%; 8.59%) | [6.64, 19.14] |
| X pooled (X_4B; X_9B) | 0.0117 (0.0078; 0.0156) | [−0.0312, 0.0703] |
| π_4B; π_9B; π_small | 0.027; 0.083; 0.055 | π_small [0.000, 0.306] |
| Scale screen δ_4B − δ_9B; π_4B − π_9B | +1.56 pp; −0.056 | [−3.91, +7.81]; [−0.322, +0.100] |
| Session shift (S2 − S1): 4B; 9B | +2.34 pp (p 0.563); +5.47 pp (p 0.016) | [−2.34, +7.03]; [+2.34, +9.38] |

**Robustness.** *Registered sensitivities; none changes a decision* [S1A]:

- Checker-corrected verdicts (section 5.6) are identical to the primary: 0 flips.
- Treating the one metric-exception episode as missing changes nothing.
- The D56 postconfig server-error sensitivity drops no episode.
- Excluding the two flagged base tasks (`70bca0cc`, a confirmed false positive, and `358aa0a7`,
  a false-positive candidate pending Kevin; section 5.4) gives δ = −2.50 pp, and DR2 and DR5 read the same.
- Scoring with the fractional score itself gives δ = −3.06 pp.

**Registered secondary set** (113 tasks; *registered secondary*, enters no rule) [S1A]:

- δ = −1.11 pp, 90% t interval [−3.81, +1.60];
- D_b = 10.40%, excess +0.22 pp (one-sided upper bound 1.44);
- π_small = 0.084, one-sided bounds [0.020, 0.162];
- X sign-flip p = 0.157; the label-permutation sensitivity gives 0.035, a test the registration
  notes can be anti-conservative under a session excess;
- at 9B: X_9B = 0.0376, 95% [0.0022, 0.0796], and π_9B = 0.168, one-sided [0.038, 0.304]. At
  4B, π_4B = 0.000.

Read together, the secondary set is non-confirmatory evidence of task-specific harness effects
at 9B, and of none at 4B.

### 3.4 P1: no between-session excess, but a session shift at 9B

The Holo3 audit (section 6) is why the design has two sessions per size, and it is the basis
of P1: it had concluded that a floor measured inside one session would understate the variance
between sessions [H3]. On
this stack, under greedy decoding, the registered test falsifies P1. Three things qualify that
result [S1A]:

- **4B decides it.** Every discordant 9B cell on the base is a 3-to-1 split of its four reruns
  (11 cells). In such a cell, between- and within-session discordance are both 1/2, so 9B's
  excess is exactly 0 in every bootstrap resample. 4B has six 2-to-2 cells; five split within
  each session and one splits by session.
- **Sessions still mattered at 9B.** Success rose by +5.47 pp from session 1 to session 2
  (sign-flip p = 0.016). That is a shift common to the session's tasks, which the discordance
  contrast cannot see. No rule reads it. There are two per-size tests, and on the secondary set
  the 9B shift is +0.89 pp (p = 0.65).
- **δ includes any harness-by-session effect.** With two sessions per size, an effect of this
  kind common to a session's tasks enters δ and cannot be separated from it [S1A-REG sections 9
  and 19]. The change in the harness effect between sessions (δ_S1 − δ_S2) was +4.69 pp
  (SE 6.87) at 4B and +1.56 pp (SE 6.14) at 9B, reported and not tested [S1A, DR3].

**Where reruns diverge** (*registered descriptive*). All 512 between-session pairs, and 255 of
256 within-session pairs, part at step 1 as "environment"; one 9B within-session pair parts at
step 2 as "serving". The guest's top-bar clock is on every screenshot, so screenshots differ
from step 1 in nearly every pair. Under greedy decoding the clock alone is enough to make reruns
diverge, and this decomposition cannot separate environment from serving numerics [S1A,
first divergence].

### 3.5 The variance split

Three layers of evidence describe how outcome variance divides. They differ in standing.

**(a) The registered share.** π is the harness part of within-task variance against the
between-session rerun floor. On the base it is π_4B = 0.027 and π_9B = 0.083 (π_small 0.055,
upper bound 0.26). On the secondary set it is π_small = 0.084, upper bound 0.16 [S1A]. Even at
its upper bound, the harness share is small next to rerun noise.

**(b) The GLMM** (*registered secondary model*) [S1A; S1A-AN `glmm-summary.json`]:

- **The registered fit did not converge.** On the primary set the optimizer reported singular
  convergence with no positive-definite Hessian. The registration says such a fit is reported as
  such, so the GLMM gives no registered evidence.
- **The secondary-set fit converged** (1,808 episodes, 113 tasks). Its latent-scale shares are
  task 0.92 [0.89, 0.98], task:size 0.032, task:harness 0.012 [0, 0.026] and session about 0.
  The (1|task:harness) likelihood-ratio test gives χ² = 4.00, p = 0.045 (boundary-corrected
  0.023). That is non-confirmatory, and 93 of its 200 bootstrap refits did not converge.

**(c) A probability-scale decomposition** (*model-based*; the design study's fitted generative
model, not a registered analysis) [DS1 `fit-base.json`, `fit-pool.json`; DS2
`fit-pool-rhob0.json`, `fit-pool-4b0.json`, field `prob_scale_components.shares`]:

| Fit (calibration) | Extended check (DS2 section 3.2) | Rerun share 4B / 9B | Task share 4B / 9B | Task x harness share 4B / 9B |
|---|---|---|---|---|
| `fit-base` (32 base tasks; N0) | **fails** at 4B | 0.326 / 0.197 | 0.630 / 0.754 | 0.027 / 0.038 |
| `fit-pool` (113 tasks; P0) | passes | 0.265 / 0.208 | 0.717 / 0.751 | 0.008 / 0.041 |
| `fit-pool-rhob0` (PR) | passes | 0.265 / 0.208 | 0.719 / 0.753 | 0.006 / 0.039 |
| `fit-pool-4b0` (P4) | passes | 0.265 / 0.208 | 0.724 / 0.753 | 0.001 / 0.039 |

Under the calibrations that pass the design study's extended posterior-predictive check, the
picture is consistent:

- which task is drawn explains about three quarters of outcome variance;
- the rerun explains about a fifth (9B) to a quarter (4B);
- which harness is used on which task explains about 4% at 9B and at most 1% at 4B;
- the harness main effect and every session term are below 1%.

About 54-56% of pool tasks never succeed and 15-18% always succeed, so only about 30% carry any
contrast at 15 steps [DS2 section 7].

D69 quotes "rerun noise 20-33%, task-by-harness 3-4%"; those are `fit-base`'s values. That
calibration fails the extended check at 4B (section 9, item D2).

### 3.6 Infrastructure, cost and truncation

*Registered.* [S1A]

- **Infrastructure.** Over 1,808 episodes: 0 losses of any type, 0 guest-server restarts, and 0
  observations retried, slower than 30 s or undelivered (24,218 agent screenshots, 5,031 checker
  reads). There were 0 postconfig server errors.
- **Cost card.** 0.002497-0.002702 GPU-h per episode (engine start-up included), 22-24% of the
  card's high price at V = 20 and 28-30% of its central price; 0.048-0.052 VM-h per episode. A1
  used 4.7169 GPU-h physical in all, and about 90.0 VM-h. This replaces the synthetic projection
  of the serving probe (431.5 GPU-h for the original design) with a realized price for this
  profile on this host [SP2; S1A].
- **Steps and tokens.** Mean steps per base episode were 11.77-12.41. Of 128 base episodes per
  cell, 57-75 ended at the 15-step cap without `terminate`. Output tokens were 4,359-4,862 per
  episode.
- **Truncation.** Steps ending at 2,048 tokens without a complete tool call were 0.17-0.44% per
  (size, harness), far below the 20% label line, so neither size's δ is labelled
  truncation-confounded.

### 3.7 Deviations and defects in the frozen analysis code

*Registered process.* [S1A; D59T; DEC D59, D61, D62]

Before any outcome was read, a dry run of the frozen analysis code on synthetic records found
eleven defects. An independent checker reproduced each one. Decisions D59, D61 and D62 fixed,
while blind, how each would be handled. The one that fired:

- **Fractional scores crashed the registered report.** The registered CLI accepts only 0, 1 and
  NaN, and the base held 14 fractional scores, so it raised. As the disclosed deviation of D59
  (i), the report ran through a wrapper that imports the frozen modules unchanged and widens
  that check. An identity check showed that its report differs from the registered code's only
  in the fractional-score fields.

D61 and D62 (incomplete-data rules) were not triggered. No frozen file changed, and no job was
rerun.

**What has been verified, and what has not.** Two review lenses reproduced every re-runnable
output off the host, from SHA-256-checked copies, and re-implemented the estimands, rules and
sensitivities from the raw records. They did not re-fit the GLMM, and their working files are
not committed. The analysis runbook's own step-12 verification record is still open, and the
session-2 jobs' lane checks other than DR0 and provenance were not re-verified by a second
person [S1A, disclosures 4-5]. D66 calls the result "independently verified" (section 9, item
D4).

### 3.8 What S1a licenses, and what it does not

For the two realized sessions per size, this configuration, this host and image, and the 32
base tasks, all not externally anchored [S1A]:

**Licensed.**

- A rerun-noise floor: D_b = 11.3% and D_w = 12.5%.
- No positive between-session excess by the registered test.
- No detectable harness main effect, with DR2 Inconclusive.
- DR5 INCONCLUSIVE, so S1b does not go to the gauntlet.
- A first real cost card.
- An infrastructure record of 0 losses in 1,808 episodes.

**Not licensed.**

- Any claim about the population of sessions.
- A harness effect net of session effects.
- That the two harnesses are equivalent.
- Any confirmatory task-by-harness claim.
- Any claim about scale. The scale screen's MDE is about 17 pp, and S1a makes no shrinkage
  claim.
- Anything about other harnesses, the accessibility-tree observation, longer step caps, sampled
  decoding, larger models, or the online setting.
- Corrected verdicts as primary evidence.
- Any reading of the 9B session shift beyond these two sessions.

## 4. What more data would buy (design study)

*Model-based.* This is a CPU-only study commissioned by D66 [DS1; DS2]. It is not a registered
analysis. Its design and scenarios were chosen after S1a's readings, which it discloses. It
informed D69.

**Method.** The registration's own operating-characteristics model was fitted to S1a's records
by maximum marginal likelihood: a logit model with task, harness, session, task-by-session and
task-by-harness-by-session terms and Bernoulli reruns. It ran in three passes [DS2 sections 1-3]:

1. the fits, a validation at S1a's design, and a cost model that reprices S1a's 1,808 episodes
   to within 0.4%;
2. four independent evaluators, each covering one family of successor designs;
3. an adversarial attack on the study.

The attack found three blocking problems. The main one: every fit put the cross-size
correlation of per-task harness effects at its 0.995 bound. That copied 9B's task-specific
effects into 4B, which 4B's own data do not show (on the 81 extension tasks X_4B = −0.015, and
the 4B-only X test gives p = 0.82). An extended posterior-predictive check, written after the
attack and before any refitted calibration was checked, rejected the base-fitted calibrations.
Four pool-fitted calibrations passed (P0, PR, P4, P4sf), and every design was re-run under all
four. The residual misfit: 4B's per-task harness differences reverse sign between sessions more
often than any calibration produces (mid-rank 0.94-0.98) [DS2 sections 3.1-3.2, 9].

**Results at S1a's estimates**, as ranges over the four passing calibrations. Each design uses
new serving sessions; 450 simulated data sets per cell, each analysed with the registered code
[DS2 section 4.1]:

| Design | Cap-minutes (of 478) | P(DR2 decisive) | P(DR5 NO-GO) | P(DR5 GO) | δ 90% width (pp) |
|---|---:|---|---|---|---|
| A: S1a repeated (32 tasks, S = 2, R = 2) | 136 | 0.18-0.28 | 0.20-0.33 | 0.00 | 8.7-10.4 |
| A6: 32 tasks, 6 sessions, R = 2 | 396 | 0.58-0.76 | 0.28-0.72 | 0.00 | 6.5-8.7 |
| D: 113 tasks, S = 3, R = 1 | 306 | 0.54-0.62 | 0.20-0.46 | 0.00-0.01 | 5.1-5.7 |
| C: 113 tasks, S = 2, R = 2 (S1a's secondary design) | 376 | 0.66-0.75 | 0.18-0.44 | 0.00 | 4.7-5.4 |
| **E: 113 tasks, S = 4, R = 1** | **406 (6.77 GPU-h)** | **0.83-0.87** | **0.23-0.54** | **0.00** | 4.7-5.4 |
| J: 9B only, 113 tasks, S = 4, R = 2 | 390 | 0.97-0.99 | 0.09-0.36 (against M_9B) | 0.00 | 6.7-6.9 |

**What it finds.**

- **No design within 8 GPU-h can admit S1b.** The calibrations that pass put the population
  share DR5 reads at 0.067-0.098 over the 113 tasks, below M = 0.13. P(GO) is at most 0.03 for
  every design and calibration [DS2, "The answer"].
- **Tasks first, then sessions, then reruns.** That ordering held in every source the
  evaluators or the study ran. E beats C, S1a's own secondary design, by 0.08-0.17 on DR2. A
  DR2 decision from E would most likely be Present (0.52-0.73), driven by task-specific effects
  at 9B through the X test; the δ test alone rejects only 3-5% of the time [DS2 sections 4.1,
  4.3, 6].
- **The boundary is well calibrated.** At a true share of M, E's DR5 error rate is 0.06-0.09.
  With no harness effect, E gives Near-equivalent 0.95-0.97 and a false Present of 0.02-0.03.
- **The registered cost rule must change for any of these designs to fit.** Under S1a's
  registered rule (the card's high price), 478 cap-minutes buy about 700 episodes, and no
  113-task design fits. The study's rule is realized cost x 1.2 x 1.05 [DS2 section 5].
- **For a locale study (S2).** A 5 pp gate at S1a-like task heterogeneity needs about 100-115
  distinct tasks at 8 episodes per task-arm. With 18 templates and S1a-like heterogeneity,
  power stays at 0.23-0.49 whatever the reruns. Every arm must be interleaved within each
  serving session, because S1a's 9B session shift (+5.5 pp) is as large as the effect sought
  [DS2 section 7].

**Decision.** D69 closed S1b and Q2's harness-scale question on this study. No successor GPU is
spent on them. **[PENDING: Kevin]** Successor E remains available as a registration with a
pre-freeze audit, no gauntlet, if a decisive harness reading at 4B and 9B is wanted (pending
decision 17).

**Limits** [DS2 section 9]:

- The calibrations are plug-in conditional ML fits, with no hyperparameter uncertainty.
- The pool-fitted calibrations have no held-out test.
- The session terms rest on two degrees of freedom.
- A harness-by-session effect common to a new session's tasks was not simulated, except in one
  evaluator run.
- The evaluators' and the attack's drivers are not committed.

## 5. Checker defects (checker-mutation study)

*Descriptive.* No number in this section is confirmatory. **[PENDING: Kevin]** The adjudication
of 34 items and the human spot check of 25 items (D9; pending decisions 6 and 8).

### 5.1 Design and how it became descriptive

`q2-evaluator-mutation-v1` (ledger row 11) asks how often OSWorld-Verified's file-state checkers
reject end states that satisfy the task instruction (false negatives), and accept end states
that violate it (false positives). Every office end state reaches the checker the way it does in
the real pipeline: re-saved by the VM's own LibreOffice [MUT-REG sections 1 and 3]. The design:

- **Mutants.** 64 operators edit gold end states of the confirm-split tasks. They work through
  LibreOffice's document model, or splice characters in text files.
- **Blind labels.** Each mutant gets its label from a blind requirement spec, never from a
  checker: *should_pass_equiv*, *should_pass_alt_solution*, *should_fail_violation*,
  *should_fail_extra_change* or *ambiguous*.
- **GUI-faithful save.** A save stage replays each task's postconfig in non-headless LibreOffice
  under Xvfb.
- **Scoring.** The unmodified pinned `DesktopEnv.evaluate()` scores each mutant offline, twice in
  fresh processes, under each of two dependency sets.
- **Audit.** Every candidate checker error, every gold flip and a set of shams were audited
  blind by two model raters: Claude (`claude-opus-5-5`, through the agent harness with one
  isolated agent per item, D25) and Qwen3.6-35B-A3B.

The registered rater-agreement gate was κ ≥ 0.6. Development κ came out at 0.066 under the
registered ingest, and 0.575 with a harness relay turn excepted. D34 (i) then fired: no other
rater was tried, and P2-P5 left the confirmatory headline. D35 froze the study as a
pre-specified descriptive protocol, with candidates listed and counted, each with its audit
decision [MUT-REG status block; DEC D34, D35, D38].

### 5.2 `compare_pptx_files` fails equivalent shape reorders

The operator `pptx.eq.zorder_nonoverlap` swaps two shapes on a slide only when every shape
between them has a known frame and the pair cannot paint the same pixel (2 mm clearance). The
edit changes nothing a viewer sees [MUT-REG Appendix A; ZINV]. Results, in the evaluable
population outside probe-touched cells [MUT; ZINV; outcomes in
`released/confirm-mutants-v1/outcomes.jsonl`]:

- **On `compare_pptx_files`, 35 of 39 evaluable reorder mutants fail.** Including
  `compare_pptx_files_tolerant`, it is 36 of 40, on 16 tasks.
- **Audit.** Both raters accept the end state as correct for 30 of the 36: 29 on
  `compare_pptx_files` and 1 on the tolerant variant. The raters split on the other 6, which are
  in Kevin's pool. No label was contradicted.
- **Shares.** As task-equal candidate shares: the operator 91.7% (81.3-100%); the
  `compare_pptx_files` family 40.2% (32.9-46.3%) of its 85 evaluable should-pass mutants.
  Counting only audit-confirmed events, the family share is 33.5% (24.8-41.7%).
- **Other families.** No other family has a false-negative candidate. `compare_table` has 0 in
  218 should-pass mutants on 30 tasks. No alternative solution (0 of 93) fails.
- **Pooled.** Over all 348 evaluable should-pass mutants on 60 tasks, the candidate share is
  12.4% (7.2-18.3%), and 10.6% (5.8-16.2%) audit-confirmed.

**Mechanism.** `compare_pptx_files` pairs the two decks' top-level shapes in document order. A
swap of two shapes that do not overlap changes their order in the shape list, so the comparator
compares the wrong pairs [ZINV]. S1a's checker-corrected outcome replaces it with
`compare_pptx_files_zinv`. That comparator realigns shapes only when the swapped pair is apart,
keeps every other attribute comparison, and still fails a visible stacking change [ZINV;
S1A-REG section 8].

### 5.3 A GUI-faithful save flips reference golds

The gold fixed point (P1 of this study; a pre-specified replication) asks whether a raw gold
that passes its checker still passes after a GUI-faithful LibreOffice save. Of 92 counted golds
[MUT]:

- **4 flip raw** (4.35%; exact 95% 1.20-10.76%).
- **3 flips are audit-confirmed** (3.26%; exact 95% 0.68-9.23%). Both raters accept the saved
  gold of `3a7c8185`, `9ec204e4` and `b8adbc24` as still correct.
- **The fourth is not a checker error.** Both raters reject the saved gold of `30e3e107`: the
  save changed its content.
- **These counts are final.** No P1 flip is in Kevin's pool.
- **A replication.** The headless scoping round trip, a different save path, flipped 7 of 63
  confirm golds and 1 of 26 reserve golds [MUT-REG section 4].

**Raw golds that fail their own checker.** Before any mutant was scored, 4 of 74 confirm-split
raw golds failed their own checkers: one `check_tabstops` and three `compare_pptx_files` (the
harness check K1, 70 of 74, passed its 90% line) [MUT-A1]. S1a removed these four tasks from its
pool [S1A-REG section 5.4].

### 5.4 False positives are few

Five should-fail mutants pass their checker, out of 96 evaluable on 26 tasks (candidate share
5.9%, 0.8-12.3%) [MUT]:

- **2 are confirmed** (both raters reject the end state): `drop_char_format` on
  `compare_pptx_files` (`70bca0cc`), and `text_edit` on `compare_docx_files` (`d53ff5ee`).
- **3 had their violation label contradicted** by both raters, pending Kevin.
- **Confirmed share:** 2.1% (0-5.4%).

In probe-touched cells, which are counted and never audited, there are 28 false-positive events
and no false negatives.

### 5.5 How reliable the audit is

[MUT, "Audit statistics"]

- **Agreement.** Cohen's κ on the 138 real items is 0.343 (raw agreement 82.6%), below 0.6.
  Adjudication cannot change κ.
- **Sham accuracy.** Claude 36 of 40 (0.90); Qwen 39 of 40 (0.975).
- **Unresolved items.** 24 of 138 real items (17.4%).
- **Gold shams.** Claude rejects all four split gold shams. They sit on tasks that also hold 3
  of the 6 split equivalence candidates.

These raters are model raters. The human spot check is pending, and the study claims no rate.

### 5.6 What the defects did to S1a

*Registered secondary.* Offline rescoring of every S1a final state applied the corrected
comparator to 72 episodes per job. It changed no verdict on the base or the secondary set: 0
flips, and 0 live-versus-offline replay mismatches [S1A]. So for Qwen3.5-4B and 9B at 15 steps,
the reorder defect did not move any S1a outcome. Corrected verdicts stay secondary until Kevin
adjudicates (D9).

### 5.7 What Kevin's answers can change

[MUT, "Pending for Kevin"; `summary.json` `pending_ranges`]

| Output | Now | After adjudication |
|---|---|---|
| Confirmed false negatives | 30 | 30-36 |
| Confirmed false positives | 2 | 2-5 |
| Alternative solutions in P2 | 72 | 72-93 (P2's events do not change) |
| Gold-defect tasks | 0 | 0-4 |
| κ, P1, the candidate shares | as above | unchanged |

## 6. The Holo3 rerun audit

*Registered* (`q2-holo3-rerun-audit-v2`, ledger row 3, frozen 2026-10-07, git head `48f6b4e`;
CPU-only job 438). The v1 analysis is recorded as post hoc (D10; ledger row 2) [H3; H3-REG].

**Question.** The OSWorld-Verified leaderboard has two rows for Holo3-35B-A3B: 82.56 and 78.15
(leaderboard data at <https://github.com/OS-World/OS-World.github.io>, commit `62f8466`,
`static/data/osworld_verified_results.xlsx`). They are two maintainer runs of the same agent on
the same day. Per task they are not exchangeable reruns: the post hoc v1 record gives an exact
McNemar 25 against 9, p = 0.009 on 359 tasks. The trajectories come from
<https://huggingface.co/datasets/xlangai/ubuntu_osworld_verified_trajs> at revision `5473c39e`.
Was the shift on the checker side, the agent side, or an environment failure? [H3; H3-REG
section 1]

| Rule | Outcome | Numbers |
|---|---|---|
| (d) checker time-dependence | not attributable | the 16 clean tasks with a time-dependent checker carry 4 of the 14 net flips (share 0.29); stratified exact one-sided p = 0.156 against α = 0.04 |
| (a) agent behaviour (step counts) | no shift | 322 joined task pairs; geometric-mean step ratio 0.977; Wilcoxon p = 0.94 |
| (b) signatures of the 14 run-2-only failures | unexplained | environment 1, agent-side 1, no registered signature 12 |
| (c) coverage | ok | 695 of 718 scored episodes joined (96.8%) |

Source: [H3].

**Reading.** The pair is a real session shift that none of the registered mechanisms explains.
Runs of one agent on the same day by the same operator differed by 4.4 points for reasons the
trajectories do not reveal [H3].

**What followed.** This finding is why S1a registered two sessions per size and the P1
prediction. On this program's stack, with greedy decoding and a fresh engine per session, S1a
found no between-session excess, but one whole-session shift at 9B (section 3.4). The two
results agree that sessions are a factor to register and interleave across. They disagree on
whether that factor shows up as extra rerun discordance. The settings differ: a remotely
served agent in Holo3's case, a local engine with greedy decoding in ours.

**Limits.** The evaluator-class rules were written while configs and outcomes were on disk;
their blinding is self-attested, and the narrow-L sensitivity gives the same verdict. The 5.75
GB tarball was deleted after the run [H3].

## 7. Limitations and scope

1. **One host, one image, one lane.** Every result is for `fal-h100-01` as configured: the
   pinned VM image and guest disk, OSWorld `b138d348`, CPU-only VM jobs, at most 32 concurrent
   VMs (S1a ran 20). The inotify limit that set N* = 32 is a host setting.
2. **Two sizes, two closely related harnesses.** Qwen3.5-4B and 9B only. H-OSW-fixed and H-GA
   share their history layout, thinking pass-back and Qwen3.5 lineage. A null harness contrast
   between them says little about harness pairs that differ more, such as the coding harnesses
   of [2609.07925](https://arxiv.org/abs/2609.07925).
3. **Screenshot only.** Neither certified harness reads an accessibility tree, so the
   observation factor was not measured. A7 certifies the guest server's restart rate, not the
   observation's effect.
4. **Fixed agent settings.** Greedy decoding (imposed on H-GA), 15 steps, a 2,048-token
   thinking budget, offline VMs with `--network none`. 57-75 of 128 base episodes per cell ended
   at the step cap.
5. **Small task sample, two sessions.** The primary set is 32 tasks. Every estimand is
   conditional on two realized sessions per size, and session-common harness effects cannot be
   separated from δ.
6. **Not externally anchored.** No output was compared with a public run. The anchor failed
   because 110 of 116 tasks changed config or checker code since the public runs were scored,
   which is itself a limit on comparing scores across benchmark revisions [ANCHOR].
7. **Certification limits.** See section 2.6: 33 certified keysyms, catalog instances only, an
   unbounded whole-boot accessibility failure mode, self-specified pointer oracles, and C3 as a
   regression check.
8. **Model raters.** The checker audit used two model raters with κ = 0.343. The human spot
   check and the adjudication are pending. The study is descriptive.
9. **Model-based design numbers.** Section 4's probabilities and section 3.5 (c)'s shares are
   conditional on fitted calibrations, are not registered, and were chosen after S1a's data.
10. **Decisions taken on the owner's behalf.** Many program decisions cited here (D1-D70) were
    taken on Kevin's behalf and await his review. D55 records his own rulings.

## 8. Reproducibility

### 8.1 Registrations and ledger rows

The ledger is hash-chained: `uv run python scripts/preregister.py check-chain` checks the chain,
and `verify` checks each id [LEDGER].

| Registration | Ledger row | Row hash (prefix) | Frozen (UTC) | Evidence |
|---|---:|---|---|---|
| `q2-holo3-rerun-audit-v1-posthoc` | 2 | `2b8536f2` | 2026-10-07 11:39 | post hoc (D10) |
| `q2-holo3-rerun-audit-v2` | 3 | `aa32cb0a` | 2026-10-07 11:39 | [H3] |
| `serving-throughput-probe-v1` | 4 | `13c72ac3` | 2026-10-07 11:42 | `program/evidence/2026-10-07/serving-throughput-probe-v1/` |
| `serving-throughput-probe-v2` | 5 | `52cd6a84` | 2026-10-07 15:01 | [SP2] |
| `q2-action-path-v1`, `-inputs`, `-executor` | 8-10 | `ea94915d`, `9ae84918`, `be4fefcb` | 2026-10-08 07:28 | [AP1] |
| `q2-evaluator-mutation-v1` | 11 | `dc39bfa2` | 2026-10-08 08:25 | [MUT], [MUT-A1], `program/evidence/2026-10-08/q2-mutation-confirm/audit/` |
| `q2-action-path-v2`, `-inputs`, `-executor` | 13-15 | `58da1bb6`, `603b2142`, `fde44535` | 2026-10-08 14:23 | [AP2]; campaigns ran from a read-only export of `bf99a64` |
| `q2-stage1-rescoped-v1` (S1a) | 16 | `bc5e88a0` | 2026-10-09 22:11 | [S1A], [S1A-AN]; freeze commit `d5f5798` |

### 8.2 Decisions

[DEC]

- **Action path:** D30, D33, D39, D40, D43, D45, D51, D53.
- **S1a:** D47, D49, D55 (Kevin's rulings), D56, D57, D59, D61, D62, D66.
- **Design study:** D66, D69.
- **Checker study:** D9, D23, D25, D27, D34, D35, D38.
- **Holo3:** D10, D11, D15.
- **This report:** D71 (iii).

### 8.3 Code

- **Action path:** `harness/q2/action_path/`, `harness/q2/vm/`,
  `scripts/render_q2_action_path_manifest.py`, `infra/slurm/host-single-node/vm-campaign.sbatch`.
- **S1a:** `harness/q2_stage1/` (estimators, rules, the zinv comparator), with the analysis
  tooling in `ops/s1a-analysis/` (`RUNBOOK.md`).
- **Design study:** `harness/q2_design/` (tests: `tests/test_q2_design.py`).
- **Checker study:** `harness/q2_mutation/`, `infra/q2-mutation/`.
- **Holo3:** `scripts/run_holo3_rerun_audit_doctor.py`, `harness/holo3_v2.py`.

Each registration pins its code by digest. `git diff d5f5798 -- harness/q2_stage1` is empty
for the design study [DS1].

### 8.4 Compute

GPU-hours are physical, from the ledger in [STATE] (`gpu_hours_ledger`).

| Work | GPU-h | CPU and VM |
|---|---:|---|
| Action-path v1 and v2 (development, controls, acceptance) | 0 | v2 used 109.12 VM-hours, CPU only [AP2]; the verifier notes this total mixes two span definitions [AP2-VB] |
| S1a (O1, A0a, O2, four A1 jobs) | 4.8444 (A1 4.7169) | about 90.0 VM-h for A1 [S1A] |
| Checker study (unregistered rater development and the confirm audit) | 0.939 | the mutant campaign itself was CPU only [MUT] |
| Serving probes v1 and v2 (v1 also priced Q1) | 1.1513 | [SP2] |
| Holo3 audit v2 | 0 | CPU-only job 438 [H3] |
| Design study | 0 | no host job [DS2] |

### 8.5 Not in the repository

- **Raw records.** Raw run outputs stay on the host's persistent run root. Each run directory's
  `raw-sha256sums.txt` lists the SHA-256 of every raw file [AP2].
- **Rater material.** The checker study's transcripts, per-item answers, packets and isolated
  export are hashed, not committed [MUT].
- **Holo3 data.** The trajectory feature file stays on the host [H3].
- **Working files.** The design study's evaluator and attack drivers, and the S1a reviewers'
  working files, are in session scratch space, not committed [DS2; S1A].

## 9. Pending sign-offs and open items

### 9.1 Pending sign-offs

Each item below is the owner's (`program/state.json` `pending_decisions_for_kevin`, index
given).

| Item | Index | What it affects here |
|---|---:|---|
| Publication of this report | (D71 (iii)) | everything; an outward action |
| Disclosure to xlang-ai of the checker defects (and the earlier OSWorld findings) | 3 | section 5; must precede publication |
| Checker-mutation adjudication, 34 items | 8 | section 5.7 ranges; corrected verdicts' standing in S1a |
| Human spot check, 25 items (D9) | 6 | every audit-dependent output in section 5 |
| Release of the checker study's blind specs, published before sign-off | 13 | the public checker-study materials |
| Review of decisions D1-D70 (and D71) taken on his behalf | 12 | D53 (action path accepted), D56 (S1a sign-off), D59-D62 (analysis-code defects), D66, D69 |
| Action path: shell-side observation of grabbed chords; the job 851 guest-server restart; the A4/A7 governance deviation | 14 | sections 2.5-2.6 |
| Host inotify limit (host administrator) | 16 | N* = 32 and the concurrency scope |
| Successor E | 17 | section 4 |
| A valid Anthropic API key (the Claude rater ran through the agent harness, D25) | 9 | section 5 rater path |

Also open, not Kevin's:

- the S1a runbook's step-12 verification record;
- a second check of the session-2 lane checks [S1A, disclosures 4-5].

### 9.2 Discrepancies found while drafting

These are in the program record, not in the evidence. Each should be corrected at its source
before this report is circulated.

- **D1. δ's direction in D66.** D66 calls pooled δ "H-OSW-fixed minus H-GA". The registration
  [S1A-REG section 2] and [S1A] define δ = H-GA − H-OSW-fixed, and the value −3.1 pp follows
  that definition: success 26.56% against 28.91% at 4B, and 28.91% against 32.81% at 9B. This
  report uses the registered definition.
- **D2. D69's variance shares.** D69's "rerun noise is 20-33% of outcome variance and
  task-by-harness variance 3-4%" are the probability-scale shares of `fit-base`. That
  calibration fails the design study's extended check at 4B. Under the passing calibrations,
  task-by-harness is about 4% at 9B and at most 1% at 4B; rerun is 21-27% (section 3.5 (c)).
- **D3. "35 of 36" in `HANDOFF.md` (State table) and `program/state.json` pending decision 3.**
  Both say `compare_pptx_files`
  fails "35 of 36 equivalent edits". The evidence gives 35 of 39 evaluable reorder mutants on
  `compare_pptx_files`, and 36 of 40 with the tolerant variant [S1A-REG section 8; ZINV; MUT].
  36 is the total number of false-negative candidates. The disclosure text should be corrected
  before it is sent.
- **D4. "Independently verified" in D66.** D66 says S1a was independently verified. The
  verification ran as two review lenses whose working files are not committed. The runbook's
  step-12 record is still open, as [S1A] (disclosure 5) and `program/log.md` (2026-10-10) say.

## References

External sources. Dates are publication dates, or fetch dates for repositories.

- OSWorld: <https://arxiv.org/abs/2404.07972> (2024-04-11); repository
  <https://github.com/xlang-ai/OSWorld>, pinned at `b138d348` (fetched 2026-10-08).
- gym-anything: <https://github.com/cmu-l3/gym-anything>, harness at `aae6f7607` (fetched
  2026-10-08).
- vLLM v0.31.0: <https://github.com/vllm-project/vllm/releases/tag/v0.31.0> (fetched
  2026-10-08).
- cua-speedrun (action-path suite, App. I.1; Table 20): <https://arxiv.org/abs/2609.40284>
  (2026-09-30).
- Routing Is Least Learnable Where It Is Most Valuable (12-14% rerun flips, web):
  <https://arxiv.org/abs/2608.06171> (2026-08-06).
- What Does a Harness Buy? (harness swap and rerun each flip 13%, SWE-bench Verified):
  <https://arxiv.org/abs/2610.04433> (2026-10-03).
- How Benchmarks Mis-Score CUAs (15.3% of audited FAIL verdicts wrong):
  <https://arxiv.org/abs/2607.28367> (2026-07-30).
- FrogNano (Qwen3.5-4B 8.3% against 37.2% across two coding harnesses):
  <https://arxiv.org/abs/2609.07925> (2026-09-07).
- Harness gains diminishing with capability (SWE-style repair):
  <https://arxiv.org/abs/2609.32459> (2026-09-26).
- Run-to-run noise in scientific coding agents (about 54% of score variance):
  <https://arxiv.org/abs/2610.01618> (2026-10-01).
- Agent Evaluation Reliability (G-theory; repeated cells rare): <https://arxiv.org/abs/2610.00651>
  (2026-09-30).
- Measuring the Checker (kernel-oracle mutation analysis): <https://arxiv.org/abs/2609.22220>
  (2026-09-02).
- OSWorld-Verified leaderboard data: <https://github.com/OS-World/OS-World.github.io>, commit
  `62f8466`, `static/data/osworld_verified_results.xlsx` (read 2026-10-07).
- OSWorld-Verified trajectories: <https://huggingface.co/datasets/xlangai/ubuntu_osworld_verified_trajs>,
  revision `5473c39e` (read 2026-10-07).
- X.Org server source (RECORD and device-event processing): <https://github.com/mirror/xserver>,
  master (read 2026-10-08).

The citation metadata above is inherited from the program's verified source lists
(`program/proposals/2026-10-08-q2-stage1-rescoped.md`, sources X4-X15;
`program/questions/q2-calibrated-cua-instrument.md`). It was not re-fetched for this draft.
