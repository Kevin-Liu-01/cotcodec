# q2-action-path-v1: action-path suite on the nested-KVM desktop runtime

**Status: DRAFT. Not frozen.** The program owner reviews and freezes it with
`uv run python scripts/preregister.py freeze q2-action-path-v1 program/preregistrations/q2-action-path-v1.md`.
No acceptance trial may run before that ledger entry exists.

- Experiment id: `q2-action-path-v1`
- Question: Q2 (calibrated computer-use instrument), Stage 0b. Program kill
  criterion it implements: "No GPU episodes until the action-path suite passes
  100%" (`program/questions/q2-calibrated-cua-instrument.md`), read here as
  100% of the gating set G defined in section 4.
- Drafted: 2026-10-07, on branch `stage0/q2-action-path`.
- Reviewed plan this follows: the Stage-0 workflow's reviewed plan
  `q2-action-path-and-vm`, corrected order (catalog and expectations before any
  executor; independent device reference; mutation testing of the suite; one
  IR and one executor; per-harness specs; cross-app canary; both observation
  settings; volume certification split from development).

## 1. What this experiment decides

Whether the action path from a Qwen3.5 tool call to the desktop's input events
is correct enough that Stage-1 task outcomes can be attributed to the model,
the harness design and the observation type rather than to dropped, reordered
or wrong input. It does not measure any model. Its outputs are pass or fail
verdicts per layer, the suite's own mutation score, and upper bounds on
residual per-action failure rates.

## 2. Frozen inputs

### 2.1 Runtime

| Input | Pin |
|---|---|
| OSWorld runtime | `xlang-ai/OSWorld` at `b138d348256078fa634fc3b73567a7337c793e6b` (`DesktopEnv.step`, `PythonController`) |
| VM image | `happysixd/osworld-docker@sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9`, local image ID `sha256:fe8d9a5e5ad6c593d059887ea2c790481b3f32dd42fa961f2441cdbbe2c70cf4` |
| Guest disk | `xlangai/ubuntu_osworld` at `a5d9c3eaae98eebf6e3a0beb84e7e47cf72ae133`, `Ubuntu.qcow2.zip` 12,273,896,463 B, SHA-256 `b795b6cd4c69b252c1b4f10150a347795555032501b60fd031751ed09b896712`; member `Ubuntu.qcow2` 24,460,197,888 B, SHA-256 `6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313`, read-only on the host |
| VM settings | `RAM_SIZE=4G`, `CPU_CORES=4`, `DISK_SIZE=32G`, container memory limit 6 GiB, CPUs from the Slurm allocation |
| Guest facts (boot report, job 374) | Ubuntu 22.04.3, Xorg, GNOME Shell 42.9, 1920x1080, xkb evdev / pc105 / us, PyAutoGUI 0.9.54, python-xlib 0.33, RECORD and XTEST present, 19 spare keycodes, guest server `main.py` SHA-256 `41376a5c4f0b68ed7bbbbcc73ece60427f4a58dd8bd4710176f9911de726339e` |
| Network layout | `none-netns`: VM container with `--network none` and no published ports; the runner joins its namespace (decision D13) |
| Step pause | `DesktopEnv.step(action, pause=0.0)`, the Stage-1 value (OSWorld `bfd62bdc` `run_multienv_qwen35vl.py`, `--sleep_after_execution` default 0.0) |
| Observation settings | both `require_a11y_tree=False` (screenshot) and `require_a11y_tree=True` (screenshot plus accessibility tree) |
| Lane | `infra/slurm/host-single-node/vm-campaign.sbatch` through `scripts/submit_vm_campaign.py` (decision D12), GPU-less runner image built from `infra/q2-vm-runner/Dockerfile` |

### 2.2 Suite inputs

These files are frozen by their SHA-256 at the freeze commit. Before the first
acceptance trial, a second ledger entry `q2-action-path-v1-inputs` freezes a
manifest listing each file and its digest; every acceptance receipt verifies
both ledger entries and every listed digest.

| File | Content at drafting time |
|---|---|
| `harness/q2/action_path/catalog.yaml` | 100 entries, status draft; the 35 key, chord and Caps Lock entries wait for their R-dev reference streams (section 4.3) |
| `harness/q2/action_path/gating_set.json` | G = 86 entries, 14 non-gating with reasons |
| `harness/q2/action_path/mutation_operators.yaml` | 28 operators and the equivalence rule |
| `harness/q2/action_path/l0_raw_prediction.yaml` | the predicted L0-raw failing set |
| `harness/q2/action_path/ir.py`, `vocab.py`, `catalog.py` | IR, vocabularies, validator |
| R-dev reference file | produced by the reference capture (section 4.3) |
| Guest probe, guard and marker code | written before the freeze; digests in the inputs manifest |
| Harness adapters, per-harness expressible sets, regression corpus | section 3; digests in the inputs manifest |
| L0-fixed executor | its git SHA is frozen when development ends (section 10); acceptance uses only that SHA |

## 3. Layers under test

One canonical action IR (`harness/q2/action_path/ir.py`: the Table 21
vocabulary of arXiv 2609.40284 plus explicit holds, buttons 8-9 and the
horizontal wheel) feeds one executor. Upstream input strings survive only in
the L0-raw control.

| Layer | Definition |
|---|---|
| L0-fixed | the project's executor: one base64-transported guest script per IR action sent through `DesktopEnv.step`; holds within one process with release in `finally`; XTest buttons 1-9; explicit key-name map, unknown keys raise; zero spare keycodes raises |
| L0-raw (control) | each IR action as its natural PyAutoGUI 0.9.54 call, one `DesktopEnv.step` per IR action, translation fixed in `l0_raw_prediction.yaml` |
| H-OSW-up (control) | OSWorld `bfd62bdc` `Qwen35VLAgent.parse_response`, unmodified; its PyAutoGUI strings are mapped call-for-call to IR by a fixed translator, then run on L0-fixed |
| H-GA-buggy (control) | gym-anything `bf965cde0` `agents/agents/qwen35vl.py` with `agents/shared/qwen_computer_use.py`, unmodified; its action dicts are mapped to IR by a fixed translator |
| H-OSW-fixed (Stage-1 harness) | `bfd62bdc` with its emit boundary patched to IR and only its own-spec bugs fixed: terminate(status=failure) becomes FAIL; key names go through an explicit map and unknown names raise; text goes through the IR `type` action. Changes are marked under Apache-2.0 §4 |
| H-GA (Stage-1 harness) | gym-anything `aae6f7607`, unmodified; an adapter maps its action dicts to IR and `metadata.status == "failure"` to terminate(failure) |

**Per-harness spec.** A harness is judged against its own system-prompt tool
description. Where that description is silent, Table 21 semantics apply. A
deviation the description itself declares (H-OSW: triple_click "simulated as
double-click", hscroll "mapped to regular scroll"; H-GA: scroll magnitude 1 to
10 per call) is a design difference, logged as part of the harness factor in
`harness_design_diffs.md`, never fixed and never counted as a failure. A
parameter an action's description does not mention is outside that action's
spec. Expressible sets computed by `vocab.py`: H-OSW 85 entries, H-GA 80.

**Regression set R (Table 20 call forms).** Each case is a rendered model
response. Expected IR follows Table 21 semantics, except where the harness's
own prompt declares a deviation or does not cover the call form; those cells
are design differences.

| Case | H-OSW-fixed | H-GA |
|---|---|---|
| R01 middle_click at a coordinate | gating | gating |
| R02 left_click with `text="ctrl"` | gating | outside spec |
| R03 left_click with `keys=["ctrl"]` | outside spec | outside spec |
| R04 shift-, alt- and ctrl+shift-click via `text` | gating | outside spec |
| R05 mouse_move then scroll, two calls in one response | gating | gating |
| R06 mouse_move then one-point left_click_drag, two calls | gating | outside spec |
| R07 three calls in one response (click, type, key) | gating | gating |
| R08 triple_click | declared deviation (expects double click) | gating |
| R09 scroll with a coordinate | outside spec | outside spec |
| R10 hscroll | declared deviation (expects vertical scroll) | outside spec |
| R11 terminate(status=failure) gives FAIL | gating | gating |
| R12 type with non-ASCII text (the five Unicode catalog strings) | gating | gating |
| R13 key `kp_enter`, `menu`, `super` (one call each) | gating | gating |
| R14 left_click at (999, 999) lands on (1919, 1079) | gating | gating |

Outside-spec cells still run and are reported with the IR each harness emits.

**Corpus.** Each harness-expressible catalog entry and each R case is rendered
as a model response with the official template of `Qwen/Qwen3.5-9B` at
`c202236235762e1c871ad0ccb60c8ee5ba337b9a` (`chat_template.jinja`, XML tool
calls, list values rendered as JSON), plus three perturbations: an
`Action:` sentence before the calls, a closed think block before the calls,
and (H-GA only, which documents it) the JSON tool-call fallback. Real model
responses enter only in a later preregistration.

## 4. Catalog, gating set and oracles

### 4.1 Catalog

`catalog.yaml` is an independent reimplementation that uses the 100 public
entry IDs, their order and group sizes (clicks 18, drags 11, keys and chords
34, scrolls 12, mixed 8, typing 17) from sandweave@99ba1abe as facts. Every
action, coordinate, string and expectation was written for this repository.
The file is pure ASCII; non-ASCII text is escaped, so no editor can normalize
it. Results are never presented as reproducing the paper's 83/11 or 94/94.

### 4.2 Gating set G

G is the set of entries whose every action is expressible by at least one
Stage-1 harness (`vocab.py`). |G| = 86. The 14 non-gating entries are frozen by
name: `click_button_back`, `click_button_forward`, `press_hold_release_left`,
`press_hold_release_right`, `drag_multipoint_l_shape`, `drag_right_button`,
`drag_middle_button`, `drag_shift_held`, `drag_ctrl_held`, `drag_alt_held`,
`scroll_left_3`, `scroll_right_3`, `scroll_diagonal`, `mixed_gesture_state`.
They run in every pass and are reported; they do not gate.

### 4.3 Oracles

- **Pointer and scroll entries:** the catalog's own expectation: X button
  numbers, counts and order; press and release positions within ±2 px; wheel
  buttons 4-7 with their counts; modifier masks on button events; the timing
  bounds `min_gap_ms` and `max_gap_ms` (double and triple clicks: successive
  presses within 300 ms); at least 3 motion events inside drags; the final
  pointer position within ±2 px where given.
- **Text entries:** code-point equality, no normalization, between the
  catalog's `text` and what the probe's text buffer gained, under the
  catalog's buffer rules (printable code points appended; Return and KP_Enter
  append `\n`; Tab appends `\t`; BackSpace deletes the last code point).
- **Key, chord and Caps Lock entries (35):** the R-dev reference. Each entry's
  `rdev_input` chords are sent through the QEMU human monitor (`sendkey`) of a
  fresh VM, 5 repetitions, and the guest's XRecord stream is recorded. The
  reference is the projection (event kind, keysym at index 0 of the keycode,
  modifier mask restricted to Shift, Control, Mod1, Mod4) with timestamps
  removed. An entry gets a reference only if all 5 repetitions give the same
  projection; otherwise it is labelled "self-specified oracle" and its claim is
  downgraded in every report. Caps Lock additionally requires the Caps LED bit
  to toggle on and back off. Infrastructure validation (job 374) measured the
  HMP path: `sendkey` reaches X for letters, Shift chords, KP_Enter (keycode
  104), KP_Add (86), the 102nd key (94, `less`), Caps Lock with LED toggle, and
  qcode `compose` gives Menu (135) while qcode `menu` gives no event; HMP
  `mouse_button` reaches X buttons 1-3 and HMP wheel input gives buttons 4 and
  5. HMP cannot produce buttons 8 and 9, so those entries keep catalog
  expectations.
- The R-dev capture is a reference measurement on the input device, not a
  trial of any system under test. It runs before any L0-fixed code exists, and
  the catalog with its references is frozen in `q2-action-path-v1-inputs`
  before development of L0-fixed starts.

## 5. Unit and verdict

The unit is one catalog entry (or R case) times one repetition. It is PASS
only if all of these hold:

1. The entry guard is clean before and after it (section 6.2).
2. The event channel matches the oracle exactly as in section 4.3, judged on
   the probe's own event log for `observable: app` entries and on the XRecord
   stream for `raw-only` entries (desktop shortcuts).
3. For `observable: app` entries, the screenshot returned by the
   `DesktopEnv.step` of the entry's last action decodes to the probe's final
   marker (sequence number and CRC-16 of the text buffer).
4. `no_action_control` records zero key, button and motion events on every
   channel.
5. For harness layers, the terminal action matches (terminate success or
   failure, or none).

An entry passes a pass at k of k repetitions. Any mixed result is FLAKY and
counts as a failure. An entry that is PASS in one setting and not another is
a failure of that setting.

## 6. Infrastructure failures and the guard

### 6.1 Infrastructure failures

An infrastructure failure is any of: a boot that does not serve a valid
`/screenshot` within 300 s of container start; an `/execute` call that does not
return HTTP 200 within 30 s; a `/screenshot` failure; the probe absent at a
guard; the QEMU monitor unreachable during a reference capture; a campaign
receipt with `infra_gates_pass` false or a Slurm state other than COMPLETED
with exit code 0:0.

Infrastructure failures are **not excluded** from any gating verdict: an entry
that hits one fails that repetition. They are counted and reported separately.
A whole campaign that ends with a non-COMPLETED Slurm state is rerun as a new
attempt with a new output path, and both attempts are reported.

### 6.2 Entry guard

Before and after every entry: (a) `XQueryKeymap` shows no pressed key and the
pointer shows no pressed button; (b) the LED mask equals the session baseline;
(c) the probe window is mapped, focused and covers 1920x1080 at (0, 0); (d) no
GNOME screen recording is running (no file in `~/Videos/Screencasts` is
growing). After an entry with a declared side effect the guard first runs
that effect's restoration (screencast: the chord again, until no file grows;
closes_window: relaunch the probe; shows_desktop and switches_window:
re-activate the probe; hot_corner: Escape; lock_state: none, the entry must
leave the LED at baseline) and then requires a clean state. Any violation is
charged as a failure to the preceding entry, and the guard restores state
(releases every key and button, relaunches the probe).

## 7. Acceptance criteria (gate Stage-1 GPU episodes)

- **A1 (runtime layer).** L0-fixed passes 100% of G at 5 repetitions in the
  seed-43 and seed-44 shuffles, each under both observation settings, at N = 1
  VM; and passes the seed-43 shuffle under both observation settings at the
  operating concurrency N* (section 9). Trials at N = 1: 86 x 5 x 2 x 2 =
  3,440.
- **A2 (harness layer).** H-OSW-fixed and H-GA each pass 100% of their
  expressible entries (85 and 80) and of their gating R cells, 5 repetitions,
  judged against their own spec, under both observation settings.
- **A3 (stress).** 30 timing- and state-sensitive entries, 60 repetitions
  each, zero failures, on L0-fixed and on each Stage-1 harness where the entry
  is expressible: `click_double_left`, `click_triple_left`, `click_ctrl_left`,
  `click_shift_left`, `click_alt_left`, `click_ctrl_shift_right`,
  `click_burst_5`, `click_double_slow`, `drag_short`, `drag_slow_small`,
  `drag_long_diagonal`, `chord_ctrl_c`, `chord_ctrl_shift_t`,
  `chord_ctrl_shift_arrow`, `chord_shift_tab`, `chord_shift_alone`,
  `chord_ctrl_alone`, `key_kp_enter`, `key_menu`, `caps_lock_roundtrip`,
  `scroll_ctrl_down_3`, `scroll_shift_down_3`, `scroll_down_then_up_net_zero`,
  `type_symbols_shifted`, `type_unicode_bmp`, `type_emoji_zwj`,
  `type_combining`, `type_long_500`, `type_with_correction`, `seq_long_mixed`.
  Repetitions are split evenly between the two observation settings.
- **A4 (volume).** 6,020 pooled L0-fixed trials, zero failures: each G entry 70
  times (35 per observation setting), order shuffled with
  `random.Random(43)`, spread over the N* VMs.
- **A5 (reset and hygiene).** A boot-reset campaign at the frozen source SHA
  shows 20 of 20 pristine reset-sentinel checks; every acceptance campaign's
  receipt shows `System.qcow2` unchanged and zero leaked labelled containers
  or volumes.
- **A6 (cross-app canary).** L0-fixed passes 100% of the canary in each app
  present in the image (boot report): LibreOffice Writer, Google Chrome on a
  local `file://` page with a textarea, Visual Studio Code, GNOME Terminal; 5
  repetitions per app and entry. Canary entries (the strings are those of the
  named catalog entries): `type_plain`, `type_symbols_shifted`,
  `type_unicode_bmp`, `type_emoji`, `type_combining`, `type_rtl`,
  `type_multiline_tabs`, `type_with_correction`, `type_long_200`,
  `key_kp_enter` (must insert one newline), select-all then copy then End then
  paste (text doubled), triple-click a line then type `X` (line replaced),
  drag-select a word then type `Y` (word replaced), `chord_ctrl_home` then type
  `Z` (inserted at the start), `type_spaces`, `type_digits`. GNOME Terminal
  runs the text entries and `key_kp_enter` only (its editing chords mean
  something else), into `cat > file`. State is read back from the saved file
  (Writer: plain-text export; Chrome: the textarea value through the
  accessibility tree; VS Code and Terminal: the saved file) with code-point
  equality.

All of A1-A6 must hold. If any fails, Stage 1 does not start.

## 8. Validity controls

If any control fails, the suite is invalid and no acceptance may be claimed.

- **C1 (detection).** H-GA-buggy (whose prompt also takes modifiers in
  `text`) fails R01 (middle click gives no action), R02 (Ctrl is pressed and
  released before the click) and each of R05, R06 and R07 (only the first call
  runs) in 5 of 5 repetitions.
  H-OSW-up, judged against Table 21 semantics, fails R08 (triple click), R09
  (scroll at a coordinate), R10 (hscroll) and R11 (terminate failure) in 5 of
  5. These are deterministic parser defects, so 1 to 4 of 5 is itself a defect.
- **C2 (L0-raw prediction).** L0-raw fails exactly the set in
  `l0_raw_prediction.yaml`: `type_unicode_bmp`, `type_emoji`, `type_rtl`,
  `type_combining`, `type_emoji_zwj`, `key_kp_enter`, `click_button_back`,
  `click_button_forward`; everything else passes, notably
  `type_shell_hostile` and `type_symbols_shifted`. Any deviation in either
  direction is reported and explained before acceptance. The prediction is
  never edited.
- **C3 (mutation score).** Every operator in `mutation_operators.yaml` (28),
  applied to L0-fixed and, for parser and both-layer operators, to each of the
  four harness parsers, yields a mutant that is killed (some entry or R case
  fails, or the guard fires) unless it is equivalent under the frozen
  equivalence rule (byte-identical XRecord stream without timestamps, text
  buffer and terminal action on every entry). Required: 100% of non-equivalent
  mutants killed. Mutants run in development sessions at seed 42; they are not
  acceptance trials.
- **C4 (R-dev agreement).** For every key, chord and Caps Lock entry with a
  reference, L0-fixed's projected stream equals the reference. Entries
  without a stable reference are listed as self-specified in every report.

## 9. Sample sizes, power and concurrency

**Zero-failure bounds.** With n trials and no failure, the one-sided 95%
upper bound on the per-trial failure probability is 1 - 0.05^(1/n): n = 5
gives 45.1%; 20 gives 13.9%; 60 gives 4.9%; 3,440 gives 0.087%; 6,020 gives
0.050%.

**Why these sizes.** The Stage-1 paired minimum detectable effect is about
7-8 pp (estimate, `program/questions/q2-calibrated-cua-instrument.md`). An
episode of about 20 actions with independent per-action failure rate p loses
about 20p of its successes, so keeping action-path loss at or below 1 pp needs
p ≤ 5 x 10^-4, which zero failures in 6,020 trials (A4) bounds. Gym-anything
PR #53 reports intermittent entries failing 4-20% of the time that 5
repetitions missed; the 60-repetition stress subset (A3) detects a 5% failure
rate with probability 1 - 0.95^60 = 95.4%, and the 20 A1 repetitions per entry
detect a 10% rate with probability 1 - 0.9^20 = 87.8%.

**Cost.** One entry trial takes about 1-3 s of VM time (measured `/execute`
no-op 15 ms, `/screenshot` 0.56 s, `/accessibility` 1.3 s median in job 374).
A1 + A2 + A3 + A4 total about 21,000 trials, under 20 VM-hours, CPU only.

**Concurrency rule.** N* is the largest N in {1, 8, 16, 24, 32, 40} such that,
at that rung: at least 20 cold boots were measured; boot p95 (container start
to first valid `/screenshot`) ≤ 180 s; step p95 ≤ 2 x the N = 1 value; A1's
seed-43 shuffle passes under both observation settings; and no foreign-load
abort occurred. A rung aborts if a foreign Slurm job starts or foreign load
exceeds 8 CPUs; the snapshots go into the receipt. VMs are pinned to CPUs from
their Slurm allocation; the ladder never exceeds 160 vCPUs. If N* < 40, the
program kill criterion applies: cut the Stage-1 task count before adding GPUs.

## 10. Seeds, order and the development/acceptance split

- **Order.** For shuffle seed s, the run order is built with
  `rng = random.Random(s)`; for each of the 5 repetitions, `ids` = the 100
  catalog IDs in catalog order, `rng.shuffle(ids)`, appended. It is computed
  by Python 3.10.12 in the runner image, and the realized order file's SHA-256
  goes into each receipt.
- **Seed 42: development, never evidence.** Catalog order and the seed-42
  shuffle; L0-fixed, the probe, the guard and the adapters may be iterated
  freely; mutation scoring (C3) and the L0-raw control (C2) run here.
- **Freeze of the executor.** When development ends, the git SHA of L0-fixed
  and the adapters is recorded in `q2-action-path-v1-inputs`.
- **Seeds 43 and 44: acceptance.** Fresh VMs (every cycle is a cold boot of a
  new container), the frozen executor SHA, both observation settings. Stress
  and volume orders use `random.Random(43)`. There is no unseeded randomness.

## 11. Repairs and kill criteria

- A failed acceptance attempt is repaired only as a new versioned attempt
  (`-a2`, then `-a3`) with a new output path and a new executor SHA recorded in
  an addendum. The catalog, its references, G and the predictions stay frozen.
- If any gating entry still fails at the third attempt, the affected layer is
  not admitted and Stage 1 does not start.
- If the reset sentinel fails, it is debugged before any concurrency work.
- A finding that a harness "bug" is a design difference goes into
  `harness_design_diffs.md` and never relaxes a verdict after the fact.

## 12. Reported regardless of outcome

Per-entry tables for every layer, attempt, shuffle and observation setting,
including development-run counts; FLAKY entries with their pass fractions;
infrastructure failures by type; the mutation score per operator and per
layer, with the observed killers next to the predicted ones; the L0-raw
prediction table against the observed results; the R-dev reference stability
per entry; per-app canary results; the concurrency table (boot p50/p95, step
p50/p95, CPU steal and utilization, overlay growth, pass rate per rung); every
design difference per harness; and every non-gating entry's results.

## 13. Infrastructure validation already done (not evidence for A1-A6)

Allowed before the freeze and reported as infrastructure validation only:

- Job 369 (2 cycles) and job 374 (22 cycles): cold boots in the `none-netns`
  layout with boot time, settle time, guest facts, reset sentinel (file, dconf
  key, gsettings key), latency of `/screenshot`, `/accessibility` and
  `/execute`, and HMP input reachability (section 4.3).
- Job 372 (2 cycles): the bridge-unpublished fallback. A separate container
  on Docker's default bridge reached the guest's `/platform` through the
  image's DNAT (HTTP 200), which is the exposure decision D13 records; the
  fallback is therefore not used.

## 14. Design decisions

Each was open in the reviewed plan and is settled here with its reason.

1. **Lane:** CPU-only Slurm jobs through `vm-campaign.sbatch` (decision D12).
   The shared Docker submitter requires a GPU.
2. **Network:** `--network none` for the VM container with the image's NAT on
   loopback, and the runner in the VM's namespace. Stronger than D13's
   default: the guest is unreachable from every other container (measured in
   job 372 for the bridge alternative) and has no egress, so the suite is
   web-free by construction. No Docker network is created (D13).
3. **H-GA is aae6f7607 unmodified.** Its documented deviations (one-point
   drags degrade to a two-point drag at the target, no hscroll, coordinate-less
   middle, double and triple clicks dropped, terminate failure reported through
   metadata) fall outside its own prompt's spec or are handled by the adapter,
   so they are excluded from its expressible set with a recorded effect rather
   than patched. Patching would turn it into a different harness.
4. **H-OSW-fixed fixes only own-spec bugs.** Terminate failure, key names and
   non-ASCII text are fixed; triple-as-double and hscroll-as-scroll are
   declared in its own prompt and stay as design differences; `keys` on
   clicks and coordinates on scroll are not in its prompt and are not added.
5. **Step pause 0.0 s**, the upstream Stage-1 run-script value, so the
   visual check tests the screenshots Stage 1 will see.
6. **L0-raw uses natural PyAutoGUI calls with PyAutoGUI's own key names**
   (where one exists), so it tests the runtime path rather than a harness's
   name mapping; harness name mapping is tested at the harness layer.
7. **Volume mix is uniform over G.** Weighting by mined Qwen3.5 action
   frequencies needs a range read of a 25.3 GB archive; that can enter a later
   preregistration. Uniform weighting puts the bound on every G entry.
8. **Menu key reference uses QEMU qcode `compose`.** Measured: qcode `menu`
   gives no X event, `compose` gives keysym Menu (keycode 135).
9. **Keymap-dependent predictions use the measured keymap.** C2 predicts
   `type_symbols_shifted` passes because keycode 94 carries `less` at index 0
   in this guest (xmodmap, job 374) and b138d348 excludes `<` from its Linux
   shift set.
10. **Infrastructure failures count as failures** for gating and are
    reported separately, never excluded.
