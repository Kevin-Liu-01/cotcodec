# q2-action-path-v2-executor: executor addendum to q2-action-path-v2

**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger
row for the freeze time and `git_head_at_freeze`.** The three registrations
are frozen in this order, each with its own row: `q2-action-path-v2`, then
`q2-action-path-v2-inputs`, then `q2-action-path-v2-executor` (this
addendum; `uv run python scripts/preregister.py freeze` with each id and its
path). No acceptance trial (A1-A7, the concurrency ladder) and no C1 or C3
run may run before this row exists; C2 needs only the inputs addendum.

- Experiment id: `q2-action-path-v2-executor`, an addendum to
  `q2-action-path-v2` (section 2.2). It changes no rule of that file; it pins
  what that file says is frozen when development ends. It is v1's executor
  addendum (`q2-action-path-v1-executor`, ledger row 10) with the changes
  decisions D40 and D43 make (section 10).
- Drafted: 2026-10-08, on branch `stage0/q2-action-path-v2`, from v1's frozen
  text. v1's addendum was drafted on 2026-10-07 on branch
  `stage0/q2-action-path`, with decisions D30, D33 and D39 applied before its
  freeze on branch `stage0/q2-action-path-d30` (sections 7 and 9). The
  ledger row's `git_head_at_freeze` is the executor SHA every scored campaign
  must run from (its receipt records the exported tree's digest).

## 1. Frozen files

Frozen with this file (SHA-256 of the committed bytes):

| File | SHA-256 |
|---|---|
| `harness/q2/vm/guest/l0_fixed.py` | `7f8bed98ad22eee662d92d5422ee564d80459645d2e0c58bb6f3df74a94425f1` |
| `harness/q2/action_path/executor.py` | `d5c43bbb76926da056c15a39ddcbf05e1c328bd7dddb6a726cde3c46c2f9776a` |
| `harness/q2/action_path/adapters.py` | `3a62eb109d656a717dfe9cbce31fba3bcf02457e9f5690f3e20639e8becbaf40` |
| `harness/q2/action_path/upstream/osworld_bfd62bdc_fixed.py` | `9558b956004f6c971e881f073c42792e3d5d437396dbe6c0b407b250df3d8fdf` |
| `harness/q2/action_path/upstream/gym_anything_aae6f7607.py` | `c624cee586e3b8b8b2ac12102ae1fca91e7de154b494035c4289123f38887aa6` |
| `harness/q2/action_path/corpus.py` | `b4b1f974d481c249fcb22f2b77102579fcb82e504c64375a9183783f63bfbe49` |
| `harness/q2/action_path/build_suite.py` | `1980d245c8bd4a7175124a74f2131d513facc127abfc5c10ec0db25fd1cfbc3a` |
| `harness/q2/action_path/suite_cells.json` | `a79073a2f5e6e7d7e109b14d50fb4c1e2791f856504c32cd855911e726a95c95` |
| `harness/q2/action_path/qwen35_chat_template.jinja` | `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715` |
| `harness/q2/action_path/mutants.py` | `1791311503e0b57808b0f378ce2cd4c93167c76a99c80f8b6666f559a1a90beb` |
| `harness/q2/action_path/harness_design_diffs.md` | `245dcfcf7b9393bd1c7f03a57360d9443c6478fb8c513bf64835196c4e59b61f` |
| `harness/q2/action_path/canary_targets.json` | `a49782274cf7c3dec0b6ceca64564207824220b2dc1572387f98339b0d4805f6` |
| `harness/q2/vm/guest/canary_targets.py` | `8b7233391b1da78092326c11d394f0385ee42052835a83554c76260e4201aab3` |
| `harness/q2/action_path/vm_hours.py` | `58b7379377ae87a72c85076ee87441fbb2da12042a15e9ae4aa62f67365074b1` |
| `harness/q2/action_path/trial_times.json` | `a33ca2e024d6f24a31a60ff62053be1fb197af48c996ae99fb75aff4d20217e5` |
| `harness/q2/action_path/vm_hours.json` | `5fc0617303a2782c02e67888be4584261239e5f90268e4e39d7524aff625636e` |
| `harness/q2/action_path/acceptance.py` | `06bc089e9e96e1dbbeebcfd465b0e8e16300610bc72f9c3dea9f59f81b775715` |
| `scripts/render_q2_action_path_manifest.py` | `0d547c7af6c440f108526a4306870091da09e7b99419334d76a4bdd116b90845` |
| `experiments/manifests/q2-action-path/dev-l0-fixed-v10.yaml` | `0a4f908e67631483687740cfba3266b829f3c5d2577b08b676a5fa022186ad92` |
| `harness/q2/vm/guest/probe.py` | `ba5c0f1d364c80d5f8190f3c357b915cd504d754891285c3772ba959a804efeb` |
| `harness/q2/vm/guest/guard.py` | `19fe2da1c97c88e07062e9113a8df1b8958b583f6f3bf0e1a763f52eb10a5748` |
| `harness/q2/vm/guest/canary.py` | `32742019db56b4f09905c50c71159c2ef3fe024a044d07f4bffb31cd41fcea1e` |
| `harness/q2/vm/marker.py` | `b786b347fc5573425f14090bd67621294ac5c84671bf67f47e663d693ab17fb9` |
| `harness/q2/vm/canary_run.py` | `295bdd0916869adf79015bc6da6cba4aff2a0ab9f0dab089e4ed3a3565abb119` |
| `harness/q2/vm/suite.py` | `6485ddb977d8adaf42ecc8c97f6520d3467633c54aeefba0cec877986805797a` |
| `harness/q2/vm/desktop.py` | `67030d6b5d79753e2db65b33bc12af2b5faaee2eacbaa5e49b4eb2de0a31c188` |
| `harness/q2/vm/runner.py` | `bc944df5db3712322e6f01fc54fa6214aa6d9b6ce727282f33ae1043df303f4e` |
| `harness/q2/vm/driver.py` | `06f3a29f39ad3a5de55efafd23fdfdfe121914f0f7f5dba281f4aabb68f74f7c` |
| `harness/q2/vm/manifest.py` | `f238f12bdb8470919c8892eff46fe8b721e1e0c83ad08a60c0293ed8da3b9e2e` |
| `infra/slurm/host-single-node/vm-campaign.sbatch` | `3d86820d176e3a9f0699814a19f62154cde00f88da1777a33c804e884288ac8a` |
| `scripts/submit_vm_campaign.py` | `f08aafc8bc693cd6eb6850ff972a3401f3bddc99f3c14e03187b4d313fcc5917` |

The lane and judging files listed here are also pinned by the inputs
addendum; pinning them again fixes the code every acceptance campaign runs.
A test (`tests/test_q2_prereg_inputs.py`) recomputes every digest.

## 2. L0-fixed (`guest/l0_fixed.py`, `executor.py`)

One IR action is one `DesktopEnv.step` (OSWorld `b138d348`, `pause=0.0`): a
command that base64-decodes the executor's source with the action appended, so
no typed text is ever quoted. In the guest, every device event is an XTest
request followed by a round trip. Pointer actions move first and hold their
modifiers across the action (released in `finally`); clicks are 20 ms press
and release, 60 ms between the clicks of a double or triple click; drags press
at the first point, move along every path vertex in 16 ms steps over
`duration_ms` and release at the last point; scrolls send one press and
release of button 5/4 per vertical notch, then 7/6 per horizontal notch; keys
are pressed in order, held 0.1 s and released in reverse order. Text: a code
point whose keysym is at index 0 of a layout keycode is that key, at index 1
that key with Shift_L; any other code point is typed through an executor-owned
spare keycode remapped to `[keysym, keysym]` (Latin-1 value or `0x01000000 +
cp`), left mapped after use (least recently used first when one is reused,
never within 0.3 s of its last press), so no client sees a key whose mapping
has changed back; zero spare keycodes raises. A `type` action that changes the
keymap remaps every code point it needs in one burst, then waits until GNOME
Shell (the compositor) answers a D-Bus property read twice within 50 ms, since
it repaints nothing while it rebuilds its keymap. Every action but `wait` then
ends in four steps: the same D-Bus round trip (the shell has processed the
action's events); an XDamage `DamageAdd` of each viewable InputOutput
top-level window's full area, so the compositor repaints every window from its
current contents (InputOnly windows have no contents, and `DamageAdd` on one
is a `BadMatch` error that the X server reported on almost every action of
runs 545-632 until they were skipped; the XFixes region requests and
`DamageAdd` are encoded from the protocol specifications, and a nudge that
cannot be sent fails the action); a wait until the root window's image (read
every 50 ms, as `/screenshot` reads it) has been unchanged for 0.25 s; at
least 0.1 s (PyAutoGUI's default `PAUSE`, which ends every upstream PyAutoGUI
call) and at most 2 s after the action's device events. Development runs
486-499 showed screenshots one compositor frame behind without the quiet wait,
runs 486-493 the screen frozen during keymap rebuilds without the shell wait,
and runs 504-541 the last drawing of 31 of 941 typing trials never painted
without the repaint request (runs 537-541 ran with a nudge that raised and was
skipped, a control: their typing trials failed the same way); from run 545 on,
with the repaint request working, none of 2,114 typing trials did (the reason
for each step is in the executor's source).

Before a session's first trial the runner runs the guard's keyboard warm-up
(inputs addendum; main preregistration design decision 31). It is not part of
L0-fixed, but Stage 1 must run it once per boot after `DesktopEnv.reset`, with
the same `guard.py warmup` the suite uses, before the agent's first action.

## 3. Stage-1 harnesses (`adapters.py`, `upstream/`)

- **H-OSW-fixed**: OSWorld `bfd62bdc`'s `parse_response` with its emit
  boundary changed to IR and the own-spec fixes of the main preregistration's
  design decisions 4 and 23, each marked in the source: terminate(failure) is
  a failure, key names go through an explicit map (unknown names raise),
  non-ASCII text reaches the IR `type` action (part of the emit-boundary
  change), `type` keeps its edge whitespace, and `wait` waits its `time`.
  Nothing else is changed.
- **H-GA**: gym-anything `aae6f7607`'s `_parse_response`, vendored byte for
  byte, with the adapter `controls.translate_ga_dicts` (frozen in the inputs
  addendum).
- Both clamp coordinates at the IR boundary (`ir.clamp_point`).
- `harness_design_diffs.md` lists every design difference of each harness.

## 4. The regression corpus (`corpus.py`, `build_suite.py`, `suite_cells.json`)

Every harness-expressible catalog entry and every R case rendered in the
Qwen3.5-9B chat template's tool-call format (`qwen35_chat_template.jinja`,
`c202236`, SHA-256 checked; a test renders through the template itself with
jinja2 and compares), one tool call per turn except R05-R07, with the
`action`, `think` and (H-GA) `json` perturbations. A2 runs the plain
renderings; each perturbation must parse to exactly the plain rendering's IR
on every gating and declared cell (checked offline by
`tests/test_q2_suite.py`; the same IR then runs on the same executor, so a
VM run would add nothing). The R cases' expectations follow Table 21, or the
declared deviation for H-OSW's R08 and R10; R13 is judged on the XRecord
channel with the overview the Super key opens restored like the hot corner.

## 5. The mutation kit (`mutants.py`)

The 44 scored (operator, layer) pairs of `mutation_operators.yaml` as
anchored source patches; each anchor must match exactly, so a mutant cannot
silently equal the frozen code. C3 runs one mutant per cold-booted session
at the executor SHA, seed-42 order, N = 1, screenshot setting, one repetition
per cell, plus the unmutated reference run for the equivalence rule.
Offline, every parser mutant changes the IR of at least one of its predicted
kill cells, and the two pairs predicted equivalent (M12 and M13 on
H-OSW-fixed) change none (`tests/test_q2_mutants.py`). Those two patches only
mark a line: H-OSW's own prompt declares triple-click as double-click and
hscroll as vertical scroll, so the unmutated parser already does what the
operators would introduce. They stay scored and predicted equivalent as
negative controls of the equivalence rule, with that reason in
`mutation_operators.yaml`. A kill counts only as a clean kill against the
unmutated reference run (main preregistration, section 8 and design
decision 36).

Development (informative only, jobs 553-602 at `b603347`, one session per
mutant on its predicted kill cells, screenshot setting; `b603347` predates
the warm-up and the final repaint request, so these runs are not the frozen
executor): all 42 mutants not
predicted equivalent failed at least one predicted kill cell; M12 and M13 on
H-OSW-fixed passed their declared cells (R08, R10) and the control cell run
with them. Three predicted killers did not kill: `scroll_ctrl_down_3` for M01
on H-OSW-fixed (its scroll takes no modifier from `text`), `mixed_gesture_state`
for M21 (it holds its key with `key_down`, which M21 does not touch) and
`seq_long_mixed` for M26 (its newline is a key action, not typed text). The
predictions stay as frozen; C3's report lists predicted next to observed
killers.

## 6. Canary targets (`canary_targets.json`)

The two pointer composites' screen targets per app, measured in development
(`guest/canary_targets.py`: character extents from the accessibility tree
for Writer and Chrome; for VS Code, from a screenshot of the opened fixture).

## 7. Acceptance analysis (`acceptance.py`)

The decision rules of the main preregistration's sections 5-9 as code
(design decision 32): which campaigns count (COMPLETED 0:0 from the batch
script's own record or Slurm, infrastructure gates, `System.qcow2`
unchanged, nothing leaked), the rerun rules, that each criterion ran exactly
its realized order from one source tree, A1-A7 (A1-A4 and the ladder not
counting a trial whose only failure is a guest-server restart, during the
entry or across the session's reset observation, decisions D30 and D33;
A1-A3 judging an entry on its counted repetitions and failing it on a second
excused trial, and a rung not qualifying with more than two; A7's restarts
of every attempt per accessibility call of the counting attempts, capped at
the plan's 39,036, on the exact one-sided 95% Poisson bound, under attempt 1
only), C1-C4 with C2's reading of L0-raw trials (including the judge's
reading of key events the tap recorded without the guard's lock bit, decision
D43) and C3's clean-kill and
equivalence rules (a mutant is equivalent only if the counting attempt's
streams match the reference's on every cell and each earlier attempt's on
the cells it ran without an infrastructure failure, decision D39), each control reading an earlier attempt by its own
rule (main design decision 45), and the ladder's N* with the foreign-load
abort and its rerun cap, a rung attempt without host snapshots not
qualifying but counting its trials. It reads an attempt killed before its
driver wrote a receipt from its manifest, batch record and finished sessions
(main design decision 46), reads a receipt, cycle or record file that does
not parse as missing, the attempt not counting (decision D39), and reports
without judging every A1-A3 entry with two or more excused trials, A4's
excused trials over every rerun, A4's restarts per accessibility call
against A7's bound under a repair attempt, and each earlier attempt's
receipt beside A5 (main sections 11, 12 and 22). Its verdicts are the ones
reported; `tests/test_q2_acceptance_analysis.py` drives every rule on
synthetic campaigns. It is frozen in the inputs addendum (before C2 is
scored) and pinned again here.

`scripts/render_q2_action_path_manifest.py` writes each scored campaign's
manifest from a local export of the frozen commit: the ledger's digests, the
source tree digest, the realized order's session and trial counts and a Slurm
limit from the lane's worst-case budget (an A4 that would exceed 24 hours is
split into session ranges). The operator names the host run root ROOT with
`--host-root` (decision D40): the export is named at `ROOT/src/` followed by
the git SHA, and the run directories go under `ROOT/runs`; a rendering without
it is refused, and so is the development root v1's renderer hard-coded. It
validates the manifest with the ledger and refuses before the freeze. A7, like
A4, runs at N* and is split into session ranges when one job's budget would
exceed 24 hours; its N* is attempt 1's, from attempt 1's A1 campaigns and full
ladder (main section 11). The VM and runner pins come from the last
development manifest at the candidate executor (`dev-l0-fixed-v10.yaml`),
which carries the main preregistration's section 2.1 pins. The runner CPUs are
`manifest.runner_cpus(N)` (main section 9), and a repair attempt k's manifest
pins `q2-action-path-v2-executor-a2` (or `-a3`); C2's manifest can be rendered
as soon as the inputs addendum is frozen. It pins every addendum the ledger
then holds (v1's C2 manifest pinned the executor addendum too, which v1's
evidence discloses); C2 needs only the inputs addendum, and
`manifest.check_ledger` checks only what each campaign needs.

## 8. VM time (`vm_hours.py`, `trial_times.json`, `vm_hours.json`)

`trial_times.json` holds the measured per-entry trial times (both settings),
session overheads and canary times of the final development runs at the
candidate executor, with each receipt's SHA-256; `vm_hours.json` is
`vm_hours.py plan` over it (a test checks the file reproduces), and the main
preregistration's section 9 cites its totals. A7 (decision D30) is sized from
the same measured times as A4's accessibility-setting trials (31.1 VM-hours;
98.4 VM-hours for every campaign). C2 is sized on the seed-42 order, as in
v1; its seed-45 order runs the same 500 trials in the same 9 sessions, so its
0.25 VM-hours are unchanged (decision D40; a test checks it).

## 9. Development record (seed 42, never evidence)

The first paragraph is v1's record, kept; the second states v1's rule; the
rest is v2's rule (decisions D40 and D43).

Listed in `program/evidence/2026-10-07/q2-action-path-stage0b/README.md`
with every job's outcome, and per job in `development-runs.json` there. The
last development runs ran at `7653799`, the commit that applied decision D30
to the files a campaign executes (the probe and the tap in their own systemd
scopes, the server's restart counter, A7's plan and admission): the
guest-server fault injection, inside the tenth trial and after the twentieth
of each session (job 703), L0-fixed on one VM (704) and on 8 VMs (705),
H-OSW-fixed (706), H-GA (707) and the canary (708). Every in-spec cell passed
in every repetition and setting; the only failures were the outside-spec R
cells of each harness and, in job 703, the two trials each session's kills
hit (the one killed inside with `guest_server_restart` alone). Job 694 ran
the fault injection at `34f79e4`, which differs from `7653799` only in
`manifest.py`'s A7 repair refusal and a comment in `suite.py`, with the same
outcome; jobs 695-699, the other five campaigns at `34f79e4`, were cancelled
while booting when that refusal was added. Before D30 the final runs were
662-667 at `30d8c7f` and 633-637 at `82af567`. The executor, adapters,
corpus and guest code are identical at all three commits; among the files a
campaign executes only the session, runner, driver and manifest code
changed (and the wording of `mutation_operators.yaml`'s rules; inputs
addendum, section 5), so the VM-hour sizing measured at `82af567` (section
8) stands. The scopes act only when a session starts; steps ran 6-8% slower
than at `30d8c7f` (p95 2.92 s on one VM against job 663's 2.74 s, 3.02 s on 8
VMs against 664's 2.79 s; mean trial 2.35 s against the sizing's 2.28 s)
while the host ran the other campaigns of this pass and other users'
processes (load average up to 180 on 208 CPUs during 704's last session).

v1's rule: every file a VM campaign executes had to be byte-identical at
v1's freeze commit to `7653799`; the `git diff --stat` below listed only
`harness/q2/README.md` and `harness/q2/action_path/acceptance.py` there (no
campaign executes `acceptance.py`; no file of the lane imports it), so the
development runs at `7653799` stood.

v2's rule (decisions D40 and D43). Every file a VM campaign executes must be byte-identical at v2's freeze commit to `126ff8b`, the commit of v2's
final development runs (jobs 830-839; main section 27). Run at the freeze
commit,

`git diff --stat 126ff8b HEAD -- harness/q2 infra/slurm/host-single-node/vm-campaign.sbatch scripts/submit_vm_campaign.py`

may list only the analysis and sizing files (`acceptance.py`, `vm_hours.py`,
`trial_times.json`, `vm_hours.json`), the prediction files (which only
`acceptance.py` reads) and Markdown files. Anything else needs new
development runs before the freeze. On `stage0/q2-action-path-v2` it lists
exactly `harness/q2/action_path/l0_raw_prediction_v2.yaml` (section 24, item
1 of the main registration: `chord_super_d`'s reason and the basis notes,
written after the runs).

Why the final development runs were repeated. Against `7653799`, the commit
of v1's final development runs (jobs 703-708), the files a campaign executes
that differ at `126ff8b`, each with its reason, are:

- `harness/q2/action_path/order.py` (D40): C2's own order seed, 45, built
  only for criterion C2;
- `harness/q2/vm/manifest.py` (D40, D43): v2's registration ids, C2's seed,
  seed 45 reserved like 43 and 44, L0-raw admitted in development at seed
  42, and the development-only fault `fault_drop_modifier`;
- `harness/q2/vm/driver.py` (D40, D43): the L0-raw development plan (the
  L0-fixed cells), the criterion passed to the order, and the fault passed to
  the runner;
- `harness/q2/action_path/verdict.py` (D43): a key event the XRecord tap
  recorded without Mod2 is judged on kind, keycode, keysym and order, not
  its state (the trial verdict and C4), and each verdict reports those
  events;
- `harness/q2/vm/guest/guard.py` (D43): condition (f), Mod2 in the logical
  modifier state, and the `mods` field of each check;
- `harness/q2/vm/runner.py` (D43): the development-only fault, applied as an
  anchored patch of `l0_fixed.py`'s `key` method in the session's process,
  only when a development manifest names it;
- `harness/q2/vm/suite.py`: a docstring D40 had made untrue (no code).

Against `e66bf16`, where v2's first development runs ran (jobs 784-787), the
same D43 files differ (`verdict.py`, `guard.py`, `runner.py`, `driver.py`,
`manifest.py`, `suite.py`). `verdict.py` and `guard.py` judge every trial
and run before and after every entry, so the runs at `7653799` and
`e66bf16` no longer stand for the code the campaigns will execute. Jobs
834-839 repeat 703-708 at `126ff8b` with their workloads and Slurm resources
unchanged: the guest-server fault injection (834: 52 of 56, the two trials
each session's kills hit, as 703), L0-fixed on one VM and on 8 (835: 400 of
400; 836: 800 of 800), H-OSW-fixed (837: 194 of 198, R03 and R09 outside
spec) and H-GA (838: 178 of 186, R02, R04, R06 and R10 outside spec), and
the canary (839: 60 of 60). Every in-spec cell passed in every repetition
and setting, the only failures are 703-708's, no trial of those layers read
an event without its state, C4 agreed in 140 of 140 and 280 of 280 key,
chord and Caps Lock trials, every guard check read Mod2, and step p95 was
2.71 s on one VM and 2.76 s on 8 (704: 2.92 s, 705: 3.02 s). Jobs 830-833
ran the L0-raw and L0-fixed samples and the negative case D43 asked for
(main section 27). The executor, the adapters, the corpus and the other guest
code are identical at `7653799`, `e66bf16` and `126ff8b`, so the VM-hour
sizing measured at `82af567` (section 8) stands. The renderer
(`scripts/render_q2_action_path_manifest.py`) is run by the operator before
submission, not by a campaign.

## 10. Changes from v1 (D40)

Decision D40 changes three things in the main preregistration (its section
24), and decision D43 changes the judge and the guard (its section 27). In
this addendum:

1. **Ids and paths.** This file is `q2-action-path-v2-executor`, an addendum
   to `q2-action-path-v2`, frozen after `q2-action-path-v2-inputs`; a repair
   attempt runs under `q2-action-path-v2-executor-a2` (then `-a3`).
2. **Frozen rows that differ from v1's** (section 1):
   `harness/q2/action_path/acceptance.py` (C2 reads v2's prediction and seed),
   `scripts/render_q2_action_path_manifest.py` (the host run root as a
   parameter, v2's paths), `harness/q2/vm/driver.py` and
   `harness/q2/vm/manifest.py` (as in the inputs addendum, section 5); for
   D43, `harness/q2/vm/guest/guard.py` (condition f), `harness/q2/vm/runner.py`
   (the development fault) and `harness/q2/vm/suite.py` (a docstring), with
   `driver.py`, `manifest.py` and `acceptance.py` changed again. Every other
   row is v1's digest: L0-fixed, the adapters, the vendored parsers, the
   corpus, the mutation kit, the design differences, the canary targets and
   the VM-hour sizing are unchanged.
3. **The byte-identity rule** (section 9) names every file a campaign
   executes that differs from v1's final development commit (`7653799`) or
   v2's first (`e66bf16`), why, and the commit they must all equal now
   (`126ff8b`), where v2's final development runs (jobs 830-839, repeating
   703-708) ran.
4. **Text.** Section 7 describes the renderer's host-root parameter and
   corrects what v1 said about the addenda C2's manifest pins (the renderer
   pins every addendum the ledger holds, as v1's evidence for job 768
   discloses); section 8 states that C2's sizing does not depend on its order
   seed.
5. **Unchanged.** v1's development record (section 9, first paragraph), the
   mutation kit's development results (section 5) and the frozen L0-fixed
   executor (section 2) carry over: v2 runs the same executor and harnesses.
