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
| `harness/q2/vm/guest/l0_fixed.py` | `7601b7b2b4231224c2d2b4a9b11815b1bab2c8b18ce67cff13c312fb276e9838` |
| `harness/q2/action_path/executor.py` | `d5c43bbb76926da056c15a39ddcbf05e1c328bd7dddb6a726cde3c46c2f9776a` |
| `harness/q2/action_path/adapters.py` | `3a62eb109d656a717dfe9cbce31fba3bcf02457e9f5690f3e20639e8becbaf40` |
| `harness/q2/action_path/upstream/osworld_bfd62bdc_fixed.py` | `9558b956004f6c971e881f073c42792e3d5d437396dbe6c0b407b250df3d8fdf` |
| `harness/q2/action_path/upstream/gym_anything_aae6f7607.py` | `c624cee586e3b8b8b2ac12102ae1fca91e7de154b494035c4289123f38887aa6` |
| `harness/q2/action_path/corpus.py` | `b4b1f974d481c249fcb22f2b77102579fcb82e504c64375a9183783f63bfbe49` |
| `harness/q2/action_path/build_suite.py` | `c4648f125ff5149ed494684bf66eb48aa2ed789e9e4cec179203a33376182bf9` |
| `harness/q2/action_path/suite_cells.json` | `ca7103bb93a39c4eb55bec9cc46ea53e0f6ee8051adac683746a634f9c5fd61e` |
| `harness/q2/action_path/qwen35_chat_template.jinja` | `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715` |
| `harness/q2/action_path/mutants.py` | `b64cf4c704382fecad0e2ac5a3041847084b05dc19bfcf19287ceebb375316b5` |
| `harness/q2/action_path/harness_design_diffs.md` | `245dcfcf7b9393bd1c7f03a57360d9443c6478fb8c513bf64835196c4e59b61f` |
| `harness/q2/action_path/canary_targets.json` | `6728df75fcf6e0e5d03aea1318bbe43455c0b8b62b4c1810647f45bbd979f844` |
| `harness/q2/vm/guest/canary_targets.py` | `8b7233391b1da78092326c11d394f0385ee42052835a83554c76260e4201aab3` |
| `harness/q2/vm/guest/probe.py` | `6f72a9a87327f5e7a8039f671b5989e28e6eca90232cb66bf979d770416df808` |
| `harness/q2/vm/guest/guard.py` | `129b93d7ab7cccf91469ce56b4f4a3aefc3ed3697b4d169c96219c423cdfa984` |
| `harness/q2/vm/guest/canary.py` | `2c1c063f04f8bc7c158ef147461957112c6fd0c85c2c259f36a8375bf571d3f2` |
| `harness/q2/vm/marker.py` | `b786b347fc5573425f14090bd67621294ac5c84671bf67f47e663d693ab17fb9` |
| `harness/q2/vm/canary_run.py` | `82c19fd62ff54982f425570b7193c39adc77dc02e86ddc1a2128632f934b8b77` |
| `harness/q2/vm/suite.py` | `030690b601ca75bd855ef0d95f99537ef6b4f3801e44cc20695675c5a6b52baf` |
| `harness/q2/vm/desktop.py` | `0076eca035ecd3944e41d999c3c3eafe4bc5b0735d2313864c5a58638797aed4` |
| `harness/q2/vm/runner.py` | `d3826ede838558a7fd43edec047fe9fd75140d88796d2518676f8913cc1fe218` |
| `harness/q2/vm/driver.py` | `416c543afbb93aafc0206a4897148649122b5b5a8591bfdfd82dbf30d0b9910f` |
| `harness/q2/vm/manifest.py` | `182a299873f71986b2fd1b7647647e433581904662438d6b566913f05cc17fe3` |
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
whose mapping has changed back; zero spare keycodes raises. Every action but
`wait` ends with a 0.1 s settle, PyAutoGUI's default `PAUSE` that ends every
upstream PyAutoGUI call.

## 3. Stage-1 harnesses (`adapters.py`, `upstream/`)

- **H-OSW-fixed**: OSWorld `bfd62bdc`'s `parse_response`, emitting IR, with
  four own-spec fixes marked in the source (terminate failure, explicit key
  names, exact text including edge whitespace) and nothing else changed.
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

## 6. Canary targets (`canary_targets.json`)

The two pointer composites' screen targets per app, measured in development
(`guest/canary_targets.py`: character extents from the accessibility tree
for Writer and Chrome; for VS Code, from a screenshot of the opened fixture).

## 7. Development record (seed 42, never evidence)

Listed in `program/evidence/2026-10-07/q2-action-path-stage0b/README.md`
with every job's outcome.
