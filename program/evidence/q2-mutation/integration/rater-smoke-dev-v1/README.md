# Rater smoke on development-split packets (exploratory)

Development smoke of the `q2-evaluator-mutation-v1` rater runner, answering
the second review's blocking defect 2 (2026-10-07). Dev split only; no
confirm or reserve item was sampled, packed or rated. Nothing here is a
result of the registration.

| Step | Where | Record |
|---|---|---|
| Audit sample and packets | Slurm 559, CPU only, LO-VM image `sha256:f5b4c40e...`, code `ba840b4` | `audit/` (sample of 133 items, spot-check list, packet manifest: one 410 MB shard, SHA-256 `a7f1e678...`) |
| Source capsule | host clone of `ba840b4` (bundle of the branch), `create_source_archive.py --discovery` | `capsule/source-receipt.json` (archive `a63bb27e...`, 2,267 files, worktree clean) |
| cu129 vLLM overlay | Slurm 566, one H100, 45 s (cap 10 min) | `overlay/` (image `sha256:6bc53f50...`, provenance PASS, base `sha256:423783aa...`, vLLM 0.31.0) |
| vLLM args doctor | Slurm 573, CPU only, in the overlay image | `args-doctor-cpu/` (pass) |
| Open-weight rater | Slurm 582, docker-research lane, `container_profile: vllm`, one H100, 6 min 37 s (cap 12 min, 0.2 GPU-h) | `manifests/` (manifest, dry run, submission), `open-weight/` (receipt, 133 call records, args doctor), `open-weight/lane/` (lane records: manifest, model receipt and verification, provenance, GPU prolog, termination) |
| Anthropic rater | not run | the API key in the agent environment is rejected (HTTP 401, "API key is invalid") on `GET /v1/models/claude-opus-5-5`; no packet was sent |

GPU time (Slurm `scontrol`, `ops/`): 0.0125 GPU-h (overlay) + 0.1103 GPU-h
(rater) = 0.1228 GPU-h.

The open-weight rater rated all 133 items once (no transport retry, no
refusal, every reply parsed by the first-token rule; `summary.json`). Its
answers on this dev sample are exploratory and come from one rater only:
do-nothing shams 6 of 6 rejected, gold shams 4 of 6 accepted, the P1 flip
(af23762e) accepted, equivalence mutants 35 accepted and 25 rejected,
alternative solutions 25 and 3, violations 8 and 18, extra changes 0 and 6.
Read on the host, its rejections of equivalence mutants and of gold shams
cite the task result or changes the save stage itself makes (the VM profile
writes its default font and the zh-CN language into a saved spreadsheet), not
the mutation, because the packet's difference is against the raw starting
file. The largest prompt was 120,678 tokens of the 131,072-token window.

Not committed (they hold document content): the packets, the items file,
raw responses, the engine log and the lane's copy of the study artifact.
They stay on the host under `~/cotcodec-runs/stage0/q2-evaluator-mutation/`
(`audits/dev-audit-smoke-v1/`, `raters/dev-smoke-v1/582/`).
`SHA256SUMS` covers every file here.
