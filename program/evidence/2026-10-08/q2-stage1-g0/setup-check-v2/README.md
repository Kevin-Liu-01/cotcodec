# G0 item 5, second pass: offline setup with every guest reply recorded (job 1011)

What it shows: which pool and dev tasks of `q2-stage1-rescoped-v1` set up cleanly offline,
step by step, and which the registered offline-setup exclusion (section 5.4, rules (a)-(c))
removes before the draw. The first pass (`../setup-check/`, job 982) recorded only that no
step raised; the pinned OSWorld code goes on after a step that fails inside the guest (HTTP
500, or HTTP 200 with a non-zero `returncode`), so it could not see such a step.

- **Job 1011** (2026-10-08, `s1a-vm.sbatch`, CPU only, 8 CPUs, no GRES, Docker runtime runc,
  one VM at a time, 87 minutes). Source `8b4a874`, exported read-only; that commit holds the
  recording code and the exclusion rule, so the rule was registered before this ran.
  Manifest `experiments/manifests/q2-stage1/setup-check-v2.json` (canonical SHA-256
  `88dd43b2390f31d1e9105d4fa8f780ea5e8aa48ffe8716097aadfc88fc5b0f75`). Receipt:
  `lane-receipt.json`; preflight: `preflight.txt` (no labelled container left).
- **Per task:** a cold boot from the read-only qcow2, the task's setup through the pinned
  `SetupController` with every guest `/setup/*` reply recorded per step (`setup.replies`:
  HTTP status, `returncode`, stderr and stdout tails), the registered diagnostics
  (`plan.SETUP_DIAGNOSTICS`: `code --list-extensions` for `53ad5833` and `e2b5e914`), then
  the task's postconfig steps on the untouched initial state (`postconfig_probe`; no getter
  and no metric runs, so no verdict exists). No model call, no agent action. A failed slot
  was re-queued once.
- **Records:** `setup.jsonl`, SHA-256
  `97e792f72a52ff3a380f74dd52ca57c85ed0e496d0e0faf90d685d9d8a94a4ca` (`plan.SETUP_CHECK_SHA256`).
  This copy drops every reply's stdout tail (`output_tail`, 18 replies): `dfac9ee8`'s
  postconfig decrypts and prints the stored credentials of the Thunderbird test profile in
  OSWorld's file cache, which do not belong in a public repository. The host's original under
  the run root keeps them (SHA-256
  `da37184134df2d06ff19693c4a6f5411972762b6d22d9f25199fd672cb62b0c6`). Statuses, return
  codes, stderr tails, the diagnostics' output and the step argv are unchanged, and the
  exclusion rule reads nothing that was dropped.

| | |
|---|---:|
| Tasks (116 pool, 32 dev) | 148 |
| Slots (3 re-queued after a failure) | 151 |
| Final attempts clean | 145 |
| Setup replies / postconfig replies recorded | 439 / 241 |
| Cold boot / setup / slot, median (s) | 18.3 / 11.4 / 32.3 |

Setup failures (each failed the same way on both attempts) and the exclusion:

| Task | Failing step | Rule | Outcome |
|---|---|---|---|
| `26150609` | `pip install pygame`: HTTP 500, timed out after 120 s | (a), (b) | excluded |
| `982d12a5` | colour-theme step needs `jq`, absent from the guest: returncode 127 | (b) | excluded |
| `e2b5e914` | `code --install-extension ms-python.python`: returncode 1, no network; the extension is not listed | (a), (b) | excluded |

Checked and kept: `53ad5833` (its local `.vsix` installs offline; `undefined_publisher.eval`
is listed) and `d38192b0` (its postconfig `pip install` of the cached wheel succeeds).
Postconfig steps that fail on the initial state because they read what the agent must
produce are reported, not judged: `415ef462` (`diff` of a file the agent saves), `9bc3cc16`
(`ls` of a backup the agent makes) and `d38192b0` (the attachment check). Every dev task is
clean, so A0a's dev tasks are unchanged.

`plan.OFFLINE_EXCLUDED` is `plan.offline_exclusions` on this file over every pool and dev task
(`tests/test_q2_stage1_plan.py` recomputes it). The eligible pool has 113 tasks and the K = 32
base is re-drawn on it (registration section 5.4).

What remains holds OSWorld's public task text and paths only; no host address.
