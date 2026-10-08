# Transport failures in the pinned checker (review item C1), job 1010

What it shows: with the pinned OSWorld `b138d348` code, a guest that does not answer is
scored as the agent's outcome by the old rule, and is a transport loss under the fix
(`harness/q2_stage1/osworld_live.py` at `e43549d`).

- **Job 1010** (2026-10-08, `s1a-cpu.sbatch` run mode, CPU only, no GRES, `--network none`,
  no VM; the checker-mutation metric image `sha256:2006c1a9...`; source `e43549d` exported
  read-only; OSWorld and the file cache from the mutation study's inputs). Receipt:
  `receipt-1010.json`. Script: `transport_check.py` (run from the job's output directory).
- **Tasks:** 13 pool tasks covering every result getter that routes through
  `controller.get_file` or swallows a failed request: `cache_file` after a postconfig
  (`dfac9ee8`, `9bc3cc16`, `d38192b0`), `gimp_config_file` (`7b7617bd`), `vlc_config`
  (`5ac2891a`), `vscode_config` (`53ad5833`), `audio_in_slide` (`c59742c0`),
  `background_image_in_slide` (`47f7c0ce`) and `vm_file` (`035f41ba`, `0a211154`,
  `0bf05a7d`, `185f29bd`, `26150609`).
- **Guests:** `dead` (a closed port: every request refused) and `half` (a stand-in server
  that answers `GET /terminal` and resets every other connection, so the postconfig's
  connectivity probe passes and its steps and the getters fail).
- **Per task and guest:** the pinned `DesktopEnv.evaluate()` as the old runner called it
  (what it returned or raised, and whether the old `is_transport_error`, top-level type
  only, called it transport), then `LiveTask.evaluate()` as the new runner calls it.
  `time.sleep` is skipped in the container (the pinned retries sleep 5 s; only the control
  flow is checked).

| | Rows |
|---|---:|
| Task x guest runs | 26 |
| Pinned `evaluate()` returned 0 (the getter swallowed the failure; old runner: scored 0) | 10 |
| Pinned `evaluate()` raised a non-transport exception (`TypeError` 6, `AssertionError` 4, `AttributeError` 4, a wrapped `Exception` 2; old runner: `metric_exception`, scored 0) | 16 |
| Old runner recorded a transport loss | 0 |
| New runner (`LiveTask.evaluate`) raised `TransportFailure` (a transport loss) | 26 |

`transport-check.json` holds every row (task prefix, getters, postconfig step types, the
two outcomes and the guest request errors counted in each). No file content is recorded.
