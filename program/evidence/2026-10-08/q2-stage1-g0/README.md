# q2-stage1-rescoped-v1 (S1a): G0 build evidence, 2026-10-08

The G0 items of the S1a draft that D49 (iv) asked to be built and tested on CPU before
any freeze. Branch `stage0/q2-stage1-rescope`; the registration's section 3.1 states each
result and section 22 ("G0 build") what building them changed. **Nothing here ran a model
or a GPU**: every job was a CPU-only Slurm job (no GRES), every container GPU-less. The
draft is not frozen and has had no fresh audit yet.

| Directory | What | Jobs |
|---|---|---|
| `opencua-remote-code/` | OpenCUA-7B's four remote-code files read and hashed (G0 items 2, 9.2; D49 iii) | fetch job 971 |
| `dev-smoke/` | The episode lane end to end with the scripted fake engine on two dev tasks under both harnesses: 3 of 3 scored; offline rescoring matched live on 3 of 3 | 978, 983 |
| `setup-check/` | G0 item 5: every pool (116) and dev (32) task's setup run once offline: 148 of 148 completed | 982 |
| `zinv/` | G0 item 8: the corrected comparator on the stored checker-mutation confirm campaign; gate passed in the third run (v1 0/29 and v2 26/29 kept) | 980, 995, 1000 |
| `anchor/` | G0 item 9: the public runs' settings (9.5), the prompt check, the evaluator diff (9.6: 110 of 116 tasks excluded, so the anchor is UNAVAILABLE), and the development dry run of the vLLM check (9.3) | git reads on the host (997 and others), 998 |
| `glmm/` | G0 item 12: the container build receipt, its package lock, and the acceptance fit on synthetic data | 972, 984 |
| `transport-check/` | Review item C1: on the pinned OSWorld code against a dead and a half-dead guest, 13 pool tasks x 2: the old rule scored 26 of 26 (0 or a metric exception); the fix records 26 of 26 as transport losses | 1010 |

Raw outputs (episode step logs, captured final states, which hold third-party file-cache
documents, and model replies) stay on the host under
`~/cotcodec-runs/stage0/q2-stage1/` (`runs/<job>/`, `g0/`).

Source revisions: `9d4205a` (fetch lane, GLMM image), `dcd3d4a` (dev smoke), `ac6c7cd`
(setup check, GLMM acceptance, rescoring of the smoke), `c3f2f9d` (zinv v1), `6c5948e`
(zinv v2, anchor evidence), `1b18ba3` (zinv v3, the validated comparator), `e43549d`
(transport check after the correctness and readiness review's fixes).
