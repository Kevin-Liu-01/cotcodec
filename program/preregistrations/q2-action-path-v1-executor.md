# q2-action-path-v1-executor: executor addendum to q2-action-path-v1

**Status: DRAFT. Not frozen.** The program owner freezes it when development
ends, after `q2-action-path-v1` and `q2-action-path-v1-inputs`, with
`uv run python scripts/preregister.py freeze q2-action-path-v1-executor program/preregistrations/q2-action-path-v1-executor.md`.
The scored C1 and C3 runs and every acceptance trial (A1-A6, the concurrency
ladder) wait for this ledger entry.

- Experiment id: `q2-action-path-v1-executor`, an addendum to
  `q2-action-path-v1` (section 2.2). It changes no rule of that file; it pins
  what that file says is frozen when development ends.
- Drafted: 2026-10-07, on branch `stage0/q2-action-path`. The ledger row's
  `git_head_at_freeze` is the executor SHA every scored campaign must run
  from (its receipt records the exported tree's digest).

## 1. Frozen files

Frozen with this file (SHA-256 of the committed bytes):

| File | SHA-256 |
|---|---|
| `harness/q2/vm/guest/l0_fixed.py` | `1af2bd76cefe4e63d55e803fe65a4a0804572e59c328be246074995fa88a7200` |
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
| `harness/q2/action_path/vm_hours.py` | `757981ef219f62f7f423d1ff9d02f75fd042c5c0063669f724337d2a96c270ab` |
| `harness/q2/action_path/acceptance.py` | `9dac21a9c166a866c25e803fd8025a328da43e67320632cdc7d8c553d8a1a632` |
| `harness/q2/vm/guest/probe.py` | `ba5c0f1d364c80d5f8190f3c357b915cd504d754891285c3772ba959a804efeb` |
| `harness/q2/vm/guest/guard.py` | `595fce1fa164c8fce868690b1853706ac6fa4761f0d15f41ac5cc0c3804224c5` |
| `harness/q2/vm/guest/canary.py` | `32742019db56b4f09905c50c71159c2ef3fe024a044d07f4bffb31cd41fcea1e` |
| `harness/q2/vm/marker.py` | `b786b347fc5573425f14090bd67621294ac5c84671bf67f47e663d693ab17fb9` |
| `harness/q2/vm/canary_run.py` | `295bdd0916869adf79015bc6da6cba4aff2a0ab9f0dab089e4ed3a3565abb119` |
| `harness/q2/vm/suite.py` | `ef3b23c6c671d94a460b962aa2924a534bff749ecec4f33ff13d92e0d4e5edf6` |
| `harness/q2/vm/desktop.py` | `67030d6b5d79753e2db65b33bc12af2b5faaee2eacbaa5e49b4eb2de0a31c188` |
| `harness/q2/vm/runner.py` | `14e7ae59e3abe9afd9d4cbd0464811b82cba8710cea034c9fed8c622e07f7c9c` |
| `harness/q2/vm/driver.py` | `5afb36ec8a31f749d0275c5909f2c22a858c05f48d6c289ff1560ed0b0bf7a4e` |
| `harness/q2/vm/manifest.py` | `6271124d660136db1c5921a05628f2e4d96831c2c7cc9568ab349908cda40538` |
| `infra/slurm/host-single-node/vm-campaign.sbatch` | `3d86820d176e3a9f0699814a19f62154cde00f88da1777a33c804e884288ac8a` |
| `scripts/submit_vm_campaign.py` | `f08aafc8bc693cd6eb6850ff972a3401f3bddc99f3c14e03187b4d313fcc5917` |

The lane and judging files listed here are also pinned by the inputs
addendum; pinning them again fixes the code every acceptance campaign runs.
A test (`tests/test_q2_prereg_inputs.py`) recomputes every digest.

## 2. L0-fixed (`guest/l0_fixed.py`, `executor.py`)

One IR action is one `DesktopEnv.step` (OSWorld `b138d348`, `pause=0.0`): a
command that base64-decodes the executor's source with the action appended,
so no typed text is ever quoted. In the guest, every device event is an XTest
request followed by a round trip. Pointer actions move first and hold their
modifiers across the action (released in `finally`); clicks are 20 ms press
and release, 60 ms between the clicks of a double or triple click; drags press
at the first point, move along every path vertex in 16 ms steps over
`duration_ms` and release at the last point; scrolls send one press and
release of button 5/4 per vertical notch, then 7/6 per horizontal notch; keys
are pressed in order, held 0.1 s and released in reverse order. Text: a code
point whose keysym is at index 0 of a layout keycode is that key, at index 1
that key with Shift_L; any other code point is typed through an
executor-owned spare keycode remapped to `[keysym, keysym]` (Latin-1 value or
`0x01000000 + cp`), left mapped after use (least recently used first when one
is reused, never within 0.3 s of its last press), so no client sees a key
whose mapping has changed back; zero spare keycodes raises. A `type` action
that changes the keymap remaps every code point it needs in one burst, then
waits until GNOME Shell (the compositor) answers a D-Bus property read twice
within 50 ms, since it repaints nothing while it rebuilds its keymap. Every
action but `wait` then ends in four steps: the same D-Bus round trip (the
shell has processed the action's events); an XDamage `DamageAdd` of each
viewable top-level window's full area, so the compositor repaints every window
from its current contents (the XFixes region requests and `DamageAdd` are
encoded from the protocol specifications, and a nudge that cannot be sent
fails the action); a wait until the root window's image (read every 50 ms, as
`/screenshot` reads it) has been unchanged for 0.25 s; at least 0.1 s
(PyAutoGUI's default `PAUSE`, which ends every upstream PyAutoGUI call) and at
most 2 s after the action's device events. Development runs 486-499 showed
screenshots one compositor frame behind without the quiet wait, runs 486-493
the screen frozen during keymap rebuilds without the shell wait, and runs
504-541 the last drawing of about 4% of typing trials never painted without
the repaint request (runs 537-541 ran with a nudge that raised and was
skipped, a control: their typing trials failed the same way); from run 545 on,
with the repaint request working, no typing trial did (the reason for each
step is in the executor's source).

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
H-OSW-fixed) change none (`tests/test_q2_mutants.py`).

Development (informative only, jobs 553-602 at `b603347`, one session per
mutant on its predicted kill cells, screenshot setting): all 42 mutants not
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

The decision rules of the main preregistration's sections 5-9 as code (design
decision 32): which campaigns count (Slurm COMPLETED 0:0, infrastructure gates,
`System.qcow2` unchanged, nothing leaked), that each criterion ran exactly its
realized order, A1-A6, C1-C4 with C3's kill and equivalence rules, and the
ladder's N* with the foreign-load abort. Its verdicts are the ones reported;
`tests/test_q2_acceptance_analysis.py` drives every rule on synthetic
campaigns.

## 8. VM time (`vm_hours.py`, `trial_times.json`, `vm_hours.json`)

`trial_times.json` holds the measured per-entry trial times (both settings),
session overheads and canary times of the final development runs at the
candidate executor, with each receipt's SHA-256; `vm_hours.json` is
`vm_hours.py plan` over it (a test checks the file reproduces), and the main
preregistration's section 9 cites its totals.

## 9. Development record (seed 42, never evidence)

Listed in `program/evidence/2026-10-07/q2-action-path-stage0b/README.md`
with every job's outcome, and per job in `development-runs.json` there.
