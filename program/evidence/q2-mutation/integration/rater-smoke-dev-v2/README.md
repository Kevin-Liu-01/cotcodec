# Second rater smoke on development-split packets (exploratory)

Development smoke of the `q2-evaluator-mutation-v1` audit after the third
draft's re-audit (2026-10-07): the same 133 dev items as
`rater-smoke-dev-v1/`, packed with the saved-start baseline (the starting
file saved through the same LibreOffice steps as the end state) at the pinned
code tree. Dev split only; no confirm or reserve item was sampled, packed or
rated. Nothing here is a result of the registration.

| Step | Where | Record |
|---|---|---|
| Audit sample, baseline saves and packets | Slurm 644, CPU only, LO-VM image `sha256:f5b4c40e...`, code `4b9b45d` | `audit/` (sample, spot-check list, the 12 baseline save jobs and their save events, packet manifest: one 409 MB shard, SHA-256 `fa3305cd...`) |
| Source capsule | host clone of `4b9b45d`, `create_source_archive.py --discovery` | `capsule/source-receipt.json` (archive `fea810e5...`, 2,373 files, worktree clean) |
| cu129 vLLM overlay | Slurm 646, one H100, about 43 s (limit 10 min) | `overlay/` (image `sha256:0fe3f452...`, provenance PASS, base `sha256:423783aa...`, vLLM 0.31.0) |
| vLLM args doctor | Slurm 647, CPU only, in the overlay image | `args-doctor-cpu/` (pass) |
| Open-weight rater | Slurm 650, docker-research lane, `container_profile: vllm`, one H100, 4 min 58 s (limit 8 min, cap 0.14 GPU-h) | `manifests/`, `open-weight/` (receipt, 90 call records, args doctor), `open-weight/lane/` |
| Agent-harness export (D25) | `rater_runner export-harness` on the host | `harness-export/dev-export-manifest.json` (digests of the 133 item files, their page images and `index.json`) |
| Summary | `summarize_smoke.py` | `summary.json`, `packet-estimates.json` |

GPU time: 0.0119 GPU-h (overlay) + 0.0828 GPU-h (rater) = 0.0947 GPU-h, inside
the 0.15 GPU-h allowed for this smoke.

The rater stopped at the lane's checkpoint signal (`termination.env`:
`signal_USR1_checkpoint_missing`), which `docker-research.sbatch` sends 180 s
before the job's limit; it had rated 90 of 133 items (each once, every reply
parsed). The other 43 are `unrated`. No rerun was made, to stay inside the
smoke's allowance.

Findings (exploratory, one rater; `summary.json`):

- The saved start removes the save stage's own changes from the packets: the
  save changes a median of 189 snapshot leaves of a starting file, and the
  difference lines fell from 21,842 to 7,705 over the 133 packets.
- It barely changes this rater's answers: on the 90 items rated in both
  smokes, two equivalence rejections became acceptances; the rater disagrees
  with the label on 22 of 90 items (24 of 90 in the first smoke), and the
  same two gold shams are rejected.
- The remaining rejections are task-level. Where the rater rejects a task's
  gold sham it rejects that task's equivalence and alternative mutants too.
  In 01b269ae the gold file carries a zh-CN document language and a CJK
  default font that the saved starting file does not have: an artifact of
  how the gold was made, not of the save stage (the first smoke's reading),
  which the rater calls an unrequested change. Others cite parts of the
  instruction as unmet in the gold end state; at least one is a misreading
  (b5062e3e: an alphabetical author order judged wrong).
- If the Anthropic rater agreed with every label, kappa would be 0.48 on the
  paired 90 items (0.44 for the first smoke's answers on them): below the
  registered 0.6, so P2-P5 would leave the headline.

Not committed (they hold document content): the packets, items, saved
baselines, the exported harness files, raw responses, the engine log and the
lane's copy of the study artifact. They stay on the host under
`~/cotcodec-runs/stage0/q2-evaluator-mutation/` (`audits/dev-audit-smoke-v2/`,
`raters/dev-smoke-v2/650/`, `raters/harness-export-dev-v2/`).
`SHA256SUMS` covers every file here.
