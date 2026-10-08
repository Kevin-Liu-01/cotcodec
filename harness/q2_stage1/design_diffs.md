# S1a episode runner: every difference from the upstream harnesses (q2-stage1-rescoped-v1)

Registration section 3.1 item 3 asks that every difference between the S1a runner and each
harness's upstream agent and runner be recorded. `harness/q2/action_path/harness_design_diffs.md`
holds the action-path differences (parsers, IR, executor), which S1a inherits unchanged; it
cannot take S1a's (every file under `harness/q2/` is pinned by a frozen action-path table,
design decision 35 of action-path v2), so they are here. Upstream: H-OSW is OSWorld
`bfd62bdc` `mm_agents/qwen35vl_agent.py` with `lib_run_single.run_single_example` and
`scripts/python/run_multienv_qwen35vl.py`; H-GA is gym-anything `aae6f7607`
`agents/agents/qwen35vl.py` (base `qwen3vl.py`, client `agents/shared/llm_clients.py`) with
`agents/evaluation/run_single.py`.

## Reproduced as upstream (checked by tests)

| What | Where |
|---|---|
| System prompt, tool definition, instruction prompt, the 100/20/10 history and fold, `<tool_response>` wrapping, every reply passed back as an assistant turn | `agents.py`; `tests/test_q2_stage1_agents.py` compares with messages recorded from the unmodified upstream code (`tests/fixtures/q2_stage1/upstream_messages.json`, `scripts/q2_stage1_upstream_fixture.py`) |
| Image processing: `smart_resize` (factor 32, `max_pixels` 16x16x4x12800; 1920x1080 becomes 1920x1088), PIL `resize`, PNG, base64 | `agents.process_image` |
| H-GA's instruction suffix from its runner ("Unless explicitly mentioned, you are required to use the UI to complete the task not terminal.") | `agents.GA_INSTRUCTION_SUFFIX` |
| H-GA's context variants `(100,20,10)`, `(60,12,6)`, `(24,8,4)`, `(8,4,2)`, tried in order each turn | `agents.HGa.act` |
| A turn with no action: H-OSW-fixed calls the model again on the same observation (`run_single_example` keeps `obs`); H-GA captures a fresh one (`env.step([])`) | `driver.Runner.loop` |
| Step counting: one model turn is one step for both; `terminate` ends the episode; evaluation follows the 20 s settle | `driver.Runner.loop` |

## Matched for both harnesses (registered runtime, sections 5.2-5.3)

| What | H-OSW upstream | H-GA upstream | S1a |
|---|---|---|---|
| Sampling | temperature 0.0, top_p 0.9 | temperature 1.0, top_p 0.95, top_k 20, repetition_penalty 1.0 | temperature 0.0, top_p 0.9, top_k -1, max_tokens 2,048 sent explicitly; nothing else |
| Settle | 60 s after reset, 20 s before evaluation | none | 60 s and 20 s |
| Step cap | 50 | task-dependent | 15 |
| Model client | `openai` client, non-streaming, 130 s timeout, 5 attempts on connection/timeout/429/5xx errors with `min(5 x attempt, 30)` s sleeps | `openai` client, 10 attempts on any error but a 400 with `2^(attempt+1)` s sleeps | one stdlib client over the bridge socket (`engine.py`): streaming with `return_token_ids` and usage, 600 s per request, up to 5 attempts on transport errors (including a stream that ends before `[DONE]`), 429 and 5xx with OSWorld's sleeps; a 4xx is not retried; a timeout is not retried |
| Transport | PyAutoGUI strings through `DesktopEnv.step` | gym-anything's own action API | the certified IR through L0-fixed and `DesktopEnv.step` with `pause = 0.0` (`harness/q2/vm/desktop.py`), one IR action per step, a screenshot after each (as `DesktopEnv.step`); the last one is the next observation. H-GA upstream observes once after an action group |
| `terminate(failure)` | `DONE` upstream (an own-spec bug, fixed in H-OSW-fixed) | reported in `metadata.status` | `FAIL` in OSWorld's action history for both, so `DesktopEnv.evaluate()` scores it 0, OSWorld's own convention; the checker's verdict on the state is still captured and rescored offline (`raw_state`) |
| Guard warm-up | none | none | once per boot after setup (action-path v2 design decision 31) |
| Date in the system prompt | today (`datetime.today()`) | today | pinned: `plan.PROMPT_DATE` (Thursday, October 08, 2026) for every A0a, A0b, ANC and A1 episode, through the lane manifest's `date` (`lane.validate_manifest` requires it); recorded per episode (`date_line`). The guest's own clock is not pinned |

## Classification (section 7.2)

* A reply whose parse raises (an `IRError`, or any exception from the parser or the IR
  validation) is the harness's unparseable reply: no action for H-OSW-fixed, a one-second
  wait for H-GA; counted in `ir_errors`. This includes a `wait` longer than 10 s, which the
  certified IR refuses (`ir.MAX_WAIT_MS`); upstream would wait. It also includes `type`
  text holding a code point the certified L0-fixed executor refuses to type (a C0 control
  other than newline and tab, DEL, or a C1 control: `l0_fixed.char_keysym`), such as the
  `\r` of a reply written with CRLF line ends: the IR accepts any 1-2,000 characters, so
  without this check the guest would exit non-zero and the turn would be recorded as an
  `executor_device` loss, re-queued and, under greedy decoding, usually lost again
  (`agents.check_typeable`). Upstream would pass the text to PyAutoGUI or xdotool.
* H-GA's context fallback is kept only for a context-length rejection; any other failure of
  the call is an infrastructure loss (`engine_context_fallback`). An engine failure under
  H-OSW-fixed is `engine_request`.
* A step is a transport loss when `/execute` never answers 200, or its first attempt fails
  (a retry may have run the action twice), or no screenshot comes back. A first attempt that
  answers 200 after more than 30 s is recorded (`slow_execute`) and is not a loss: the
  action-path suite counts it, but under S1a a long `type` is agent behaviour.
* A checker metric that raises, or returns nothing or a value outside [0, 1], scores 0
  (`metric_exception`); a getter or postconfig step that loses its transport to the guest is
  a loss. The pinned OSWorld code swallows most transport errors (`get_vm_file` catches any
  exception from `get_file` and returns `None`; `_execute_setup` and `_activate_window_setup`
  log a `RequestException` and go on; `setup` re-raises a failed step as a bare `Exception`;
  `DesktopEnv.evaluate` ignores a failed postconfig), so the outcome of a call cannot tell
  transport from agent state. `osworld_live` records every guest-bound `requests` call that
  raises, and task setup, `evaluate()` and the capture sweep each end in a transport loss
  when any of their guest requests raised, or a file read got no answer on any attempt,
  whatever the pinned code returned (upstream would score such an episode, usually 0).
  `is_transport_error` reads the whole exception chain. A transport failure in task setup is
  recorded as `task_setup`.
* A transport loss behind which the guest server restarted (its process id or its unit's
  `NRestarts` changed since the warm-up) is recorded as `guest_server_restart` (D30). The
  restart check runs after the 20 s settle and again after the capture (a restart during
  evaluation voids the episode even when no request failed), and a check that cannot reach
  the guest server, here or at the warm-up, is a transport loss: the episode cannot be
  shown restart-free.

## Runtime (registration section 4)

* The episode runner runs in the checker-mutation study's metric image
  (`sha256:2006c1a9...`, OSWorld `b138d348`'s locked environment, Python 3.12.13), not in the
  stdlib-only runner image the action-path suite used: the harness clients need Pillow for
  the upstream image processing and the checker needs OSWorld's environment. The transport
  code is the certified, standard-library code (`desktop.py`, `executor.py`, `guard.py`,
  `l0_fixed.py`), unchanged, under Python 3.12 instead of 3.10.
* Task setup is `DesktopEnv.reset`'s task part (`_set_task_info`, `setup_controller.setup`)
  on a fresh cold boot, with `requests` routed so that the guest passes, file-cache URLs are
  served from the pinned local cache, and every other URL is refused; the VM namespace has no
  egress. The checker is the pinned `DesktopEnv.evaluate()` against the live guest, with
  `controller.get_file` recording what it read for the capture.
