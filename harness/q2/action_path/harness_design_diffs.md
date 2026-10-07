# Harness design differences (q2-action-path-v1)

The two Stage-1 harnesses differ in design, and the differences are part of
the *harness factor* Stage 1 measures. They are recorded here, never fixed,
and never counted as action-path failures (preregistration section 3,
"Per-harness spec"). A harness is judged against its own system-prompt tool
description; where that is silent, Table 21 of arXiv 2609.40284 applies.

Sources: H-OSW is OSWorld `bfd62bdc` `mm_agents/qwen35vl_agent.py`
(`Qwen35VLAgent.parse_response`, vendored in
`upstream/osworld_bfd62bdc.py`; the Stage-1 harness H-OSW-fixed is the marked
copy `upstream/osworld_bfd62bdc_fixed.py`). H-GA is gym-anything `aae6f7607`
`agents/agents/qwen35vl.py` (`_parse_response` and `step`, vendored in
`upstream/gym_anything_aae6f7607.py`) with the adapter
`controls.translate_ga_dicts`.

## Declared by the harness's own prompt (design differences)

| Harness | Difference | Effect on the suite |
|---|---|---|
| H-OSW | `triple_click` is "simulated as double-click" | `click_triple_left` is outside its expressible set; R08 is judged against a double click |
| H-OSW | `hscroll` is "mapped to regular scroll" | horizontal scroll entries are outside its set; R10 is judged against a vertical scroll (`pixels` -3 is three notches down) |
| H-GA | scroll magnitude "must be between 1 and 10"; the parser clamps to `SCROLL_STEP_LIMIT = 10` | `scroll_down_25` is outside its set |

## Not in the harness's prompt (outside its spec; reported, never gating)

| Harness | Behaviour |
|---|---|
| H-OSW | `scroll` takes no coordinate in its prompt and scrolls at the current pointer; a positioned scroll is rendered as `mouse_move` then `scroll` (two turns); a coordinate given to `scroll` is ignored (R09) |
| H-OSW | `keys` on a click is not in its prompt and is ignored (R03) |
| H-GA | its prompt has no modifier parameter for mouse actions; the parser holds `keys` given on a mouse action (R03), and ignores `text` on a click (R02, R04) |
| H-GA | `left_click_drag` needs `coordinate` and `coordinate2`; a one-point drag becomes a drag from that point to itself (R06) |
| H-GA | no horizontal scroll action: an `hscroll` call yields no device action (R10) |

## Harness mechanics that are the same in development and Stage 1

| Harness | Mechanic | Where it matters |
|---|---|---|
| both | the 0-999 grid is scaled by the screenshot's size / 999 and truncated (`int`); the IR boundary then clamps to the screen (`ir.clamp_point`), so 999 lands on the last pixel as it does upstream (R14) | every pointer cell |
| both | every `<tool_call>` block of a response is executed, in order (R05-R07) | multi-call turns |
| H-OSW | `left_click_drag` drags from the current pointer to `coordinate` (duration 0.5 s unless `duration` is given); a two-point catalog drag is rendered as `mouse_move` then `left_click_drag` | drag cells |
| H-OSW | `wait` becomes `WAIT`, which `DesktopEnv.step` turns into `time.sleep(pause)` with Stage 1's `pause = 0.0`; the model's `time` is not used | `click_double_slow` (the two clicks are separate steps with a screenshot between them, so their gap still exceeds 500 ms) |
| H-OSW | a click without a coordinate clicks at the current pointer; `mouse_move` without one moves to (0, 0) | none in the corpus |
| H-GA | `wait` sets the step's wait time and the step returns only the wait, dropping the response's other actions; a parse with no action and no `Action:` line becomes a one-second wait | `click_double_slow` uses one call per turn, so nothing is dropped; R10's `hscroll` turn yields a one-second wait without an `Action:` line and nothing with one (outside spec) |
| H-GA | `terminate` reports its status in `metadata.status`; the adapter maps `failure` to `terminate(failure)` (R11) | R11 |
| H-GA | a `<tool_call>` block holding JSON (`{"name": "computer_use", "arguments": ...}`) is parsed as a call (its documented fallback) | the `json` perturbation |

## Fixes in H-OSW-fixed (own-spec bugs only; marked in the source)

1. Emit boundary: canonical IR instead of PyAutoGUI strings, call for call.
2. `terminate(status=failure)` is a failure (upstream emitted `DONE`).
3. Key names go through an explicit map; an unknown name raises (upstream
   passed names to PyAutoGUI, which drops `kp_enter`, `menu` and `super`).
4. Text reaches the IR `type` action exactly: the `text` parameter keeps its
   whitespace (only the one wrapping newline the chat template adds is
   trimmed); upstream stripped all edge whitespace, so `type_spaces` could
   never pass.

H-GA is unmodified; its adapter only maps action dicts to the IR.
