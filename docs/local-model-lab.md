# Local model lab: open models, harness bakeoffs, Tinker/Kimi ladder

Verified live state: 2026-09-01 (host `fal-h100-01`, 8 × H100 80GB, Slurm
21.08.5 `research` partition, Docker 28.3.1, tmux session `cotcodec` alive since
2026-08-11). This page is the operator path for three kinds of work Kevin asked
for: importing the newest open-weight models, running harness and memory-provider
bakeoffs against local models on the H100 host, and the Tinker/Kimi post-training
ladder. None of it is a research contribution by itself; it is instrumentation
for the directions in `directions/` and `research/proposals/`.

## 1. Model import ladder

| Route | Use it for | Evidence grade | Rule |
|---|---|---|---|
| Hugging Face snapshot pinned to a 40-hex revision via `scripts/fetch_open_model.py` | Every publication-capable input | publication-capable | receipt (artifact-root SHA-256) required before any job |
| Ollama tag (`ollama-*` registry aliases) | Mac-side agent-loop smoke only | non-publication | tags move; a positive result must be rerun from an immutable snapshot |
| Hugging Face custom-code checkpoints (`trust_remote_code: true`, e.g. Kimi Linear 48B-A3B, Kimi-K2.6) | Scale and architecture-diversity cells | blocked until code review | vendor and review `modeling_*.py`; prove tensor-parallel load and checkpoint-resume on the cluster first |
| Diffusers image models (`sdxl-base-1.0`) | Container/vision pipeline smoke | publication-capable input | not a language-plan baseline |

```bash
export COTCODEC_MODEL_ROOT=/home/kevin/cotcodec-models      # persistent, never /tmp
uv run python scripts/fetch_open_model.py list
uv run python scripts/fetch_open_model.py fetch <registry-id> --metadata-only   # inspect first
uv run python scripts/fetch_open_model.py fetch <registry-id>
uv run python scripts/fetch_open_model.py verify <registry-id>
uv run python scripts/smoke_open_model.py <registry-id>                          # offline, trust_remote_code=False
```

Registering a new model means adding an entry to `models/registry.yaml` with
`repo_id`, the exact `revision`, `runtime`, `architecture_family`, `license`,
`trust_remote_code`, `publication_eligible`, `roles`, `metadata_files`,
`required_files`, and a `blocker` line when it is not yet admissible. Verified
2026-09-01 via the Hugging Face API: `moonshotai/Kimi-K2.6` is public,
`custom_code`, license `other`, tagged `kimi_k25` in Transformers, and cites
arXiv 2602.02276; it is a Tinker training target, not a local training target
(about 1T total parameters).

Candidate registry additions verified against the Hugging Face API on
2026-09-01 (revisions are the 40-hex commits observed that day; re-resolve with
`fetch_open_model.py fetch <id> --metadata-only` before pinning). Serving stacks
that day: transformers v5.16.1, vLLM v0.28.0, SGLang v0.5.18, Ollama v0.33.2.
Memory arithmetic assumes full fine-tuning ≈ 16 B/parameter before activations
and LoRA ≈ 1.1 × frozen bf16 weights.

| Candidate | Revision (2026-09-01) | License | Native transformers 5.16.1 | 8 × H100 verdict | Role |
|---|---|---|---|---|---|
| `Qwen/Qwen3.5-0.8B` / `2B` bases | see cell note (`dc7cdfe2…`, `b1485b2f…`) | Apache-2.0 | yes | full FT easy | smallest open GDN:attention hybrids (18 GDN + 6 attention at 0.8B); copy exact layouts for from-scratch arms |
| `Qwen/Qwen3.8-27B` | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | Apache-2.0 | yes | full FT tight, LoRA easy | dense 48 linear + 16 full attention; also on Tinker |
| `Qwen/Qwen3.8-Flash-Next` | `de4b8e4d43b917e7706784d8bb445c9af86a3540` | Qwen Community 1.0 | yes (`qwen4_exp`, ≥ 5.16.0) | inference FP8 only; training undocumented; vLLM needs 0.29+ | reference for GDN + Qwen Sparse Attention + Gated Residual ablations |
| `zai-org/GLM-5.3-Flash` | `03eb5366286afd40d2221b1d9c63a6dd1ba4832e` | MIT | yes (`glm5_next`) | inference only (~306 GiB FP8); KDA fallback reported NaN; vLLM 0.29+ | KDA + DSA 3:1 production hybrid; behavioural probes only |
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Base-BF16` | `434456c9a6753f29d24e23c95d622aaf17111b3b` | OpenMDW-1.1 | yes (`nemotron_h`) | full FT borderline, LoRA easy | only open 2026 Mamba-2 hybrid BASE; card intends SFT/RL/distillation |
| `google/gemma-4-E2B` / `E4B` / `12B` bases | see cell note | Apache-2.0 | yes | full FT easy | SWA/global family control; E2B is a PorTAL target |
| `allenai/Olmo-Hybrid-7B` | `4f1cc566f9fdf3ce68da2ab6a788a83d89896dcf` | Apache-2.0 | yes | full FT easy | fully open-data hybrid; contamination by construction |
| `HuggingFaceTB/SmolLM3-3B-Base` | `d78a42f79198603e614095753484a04c10c2b940` | Apache-2.0 | yes | full FT easy | small transformer control above SmolLM2-135M |
| `deepseek-ai/DeepSeek-V4-Flash-Base` | `8855555deef230a27a21a8d6f294b7b7497759b6` | none stated in card | yes | inference only (304 GB) | CSA/HCA sparse-attention base; license must be resolved first |
| `moonshotai/Kimi-K2.6` | `7eb5002f6aadc958aed6a9177b7ed26bb94011bb` | modified-MIT | yes (`kimi_k25`) | not viable locally (595.2 GB INT4 safetensors; vLLM recipe requires ~640 GB aggregate VRAM, 8 × H200) | Tinker LoRA only |
| `moonshotai/Kimi-K3` | `a590ce090cb049c93a33dfe8c208ec652aa20503` | Kimi K3 License | no (PR draft) | impossible (1.56 TB MXFP4) | read the report; do not register for execution |

Fifteen of these pilot checkpoints were registered on 2026-09-01 (`models/registry.yaml`, keys such as `qwen3.5-4b-base`, `transformer-1.3b-100b`, `gla-1.3b-100b`, `gdn-1.3b-isp-hybrid-3to1-50b`, `olmo-hybrid-7b`, `e2-ttt-mlp-1.3b-15b`, `rwkv7-1.5b-world`); each carries a `blocker` until its receipt exists.

No sub-10B open KDA base with native transformers support exists, and no 2026
KDA/QSA hybrid ships a public base checkpoint (`Kimi-K3-Base`,
`GLM-5.3-Flash-Base`, `Qwen3.8-*-Base` all return 401). Kimi-Linear-48B-A3B-Base
(already registered, custom code) remains the only KDA base and needs the
reviewed-code and tensor-parallel load proof recorded in its registry blocker.

## 2. Harness and memory-provider bakeoffs on local models

The admitted template is the PAST-Bench SM01 lane
(`research/past-sm01-qwen36-discovery-2026-08-14.md`): a digest-pinned vLLM
image serves a pinned open checkpoint on Slurm-owned H100s, the harness under
test runs in its own pinned container against that OpenAI-compatible endpoint,
runtime networking is disabled after staging, and a fresh Slurm job must resume
from an atomic checkpoint and match an uninterrupted continuation before any
treatment comparison counts. That lane killed itself honestly on
non-repeatable decoding (`PAST_SM01_RESTART_EQUIVALENCE_FALSIFIED`); the
restart-equivalence gate stays mandatory.

Verified images on the host (2026-09-01):

| Image | Identity | Contents that matter |
|---|---|---|
| `cotcodec-research:*-architecture-overlay` | built from `infra/research/Dockerfile`, CUDA 12.8.1 base pinned by digest | torch 2.11.0+cu128, transformers 5.15.0, accelerate, triton; **no** vllm, peft, flash-attn, fla, diffusers, datasets |
| `vllm/vllm-openai` (dangling tag) | label `ai.vllm.image.tag=vllm/vllm-openai:v0.25.1`, commit `752a3a504485790a2e8491cacbb35c137339ad34` | OpenAI-compatible server for the actor endpoint; re-pull by `docker.io/vllm/vllm-openai@sha256:<digest>` and record the digest in the manifest. Do not serve GDN/Mamba hybrids from v0.28.0 with prefix caching plus MTP: outputs are corrupted by a host/device race ([vllm #53912](https://github.com/vllm-project/vllm/issues/53912)); pin a release containing fix #50729 and run the A/A repeat gate |

Bakeoff contract shape (one YAML per harness × model × task family; validator
and tamper tests follow the `experiments/memory/stage3-*-h100-*.yaml` pattern):

1. **Actor**: registry model id, revision, artifact-root SHA-256, vLLM image
   digest, sampling fixed (`temperature 0`, seeds), `--max-model-len` pinned.
2. **Harness under test**: exact source revision and tree hash; container
   digest; provider/memory configuration frozen; secrets absent unless the
   harness is the treatment.
3. **Task family**: frozen episode manifest with SHA-256 and deterministic
   oracles (PAST-Bench, τ²-bench, Terminal-Bench 2 subsets, or the OrchVar
   canaries); pilot on 3–5 tasks before any full run.
4. **Controls**: same model through the plain two-stage OrchVar loop; same
   harness with persistence/memory disabled; matched token and wall budgets.
5. **Gates**: restart equivalence, A/A repeat drift, zero provider calls,
   one visible GPU per requested GPU, checkpoint every completed episode.
6. **Claim boundary**: a bakeoff measures harness × model interaction on a
   frozen task family; it is not evidence about model quality or memory
   semantics.

Harness roster verified on 2026-09-01 (all first-party release pages; pin the
exact tag or commit in each contract, never `latest`):

| Harness | Pin seen 2026-09-01 | Local-model route | Notes |
|---|---|---|---|
| Hermes Agent (NousResearch) | v0.21.0 "Pantheon", tag `v2026.8.31` | OpenAI-compatible base URL to the vLLM step | nine memory providers already conformance-tested in `research/hermes-memory-provider-conformance-2026-08-14.md`; PAST-Bench lane is the template |
| Claude Code | 2.1.257 (CHANGELOG 2026-09-01) | Anthropic-compatible proxy only; treat as frontier-API control unless a verified local shim exists | harness internals are first-party and unmeasured publicly |
| Codex CLI | `rust-v0.152.0` (2026-09-01) | OSS provider config to a local endpoint | pin the release tag; record the config file hash |
| Vercel AI SDK `HarnessAgent` / `@ai-sdk/harness-acp` | experimental ("expect breaking changes"), AI SDK 7 | runs Claude Code, Codex, Pi, Deep Agents, OpenCode, Cline, Cursor, Grok Build, fx through one API | useful as the uniform driver for a factorial harness × model design; not itself a treatment |
| Vercel Labs `fx` | repo 2026-08-11, "Experimental" Zig harness, Apache-2.0 | model-agnostic via gateway | small binary; candidate minimal-harness control |
| agent-browser (Vercel Labs) | v0.36.0 (2026-09-01) | n/a (browser tool surface) | tool surface for browser tasks; pin the release |
| UHP conformance suite | spec + suite run over Codex, Claude Code, Hermes, Pi, dsh | n/a | reports 475× cost spread across eight harness-model configurations; reuse its result schema for paired token/dollar ledgers |

Bakeoff claims must follow the 2026 evaluation mandates surfaced in the sweep:
paired passes with token and dollar ledgers, all-k-of-k reliability rather than
best-of-k, explicit false-completion rates, and environment noise floors
measured before any harness effect is reported.

## 3. Tinker / Kimi ladder

Tinker is a managed LoRA and RL backend (`tinker==0.23.3` pinned;
`harness/training/tinker_backend.py`; `infra/tinker/README.md`). Verified on
2026-09-01 from the product page, it advertises Kimi-K2.6, Qwen3.5-4B/9B/9B-Base,
Qwen3.5-35B-A3B-Base, Qwen3.8-27B, Qwen3.6-35B-A3B, GLM-5.3,
Nemotron-3.5-Lightning-30B-A3B, Nemotron-3 Nano/Super/Ultra, DeepSeek-V3.1,
GPT-OSS-20B/120B, and Inkling; Qwen3.6-27B retires 2026-09-02. Prices and
context limits must be re-frozen in the experiment YAML at submission time, never
read after the result is known.

Ladder (each rung is its own contract; a rung may only be entered after the
previous rung's gates pass):

| Rung | Model | Purpose | Gate |
|---|---|---|---|
| 0 | local `qwen3-0.6b-base` / `smollm2-135m` | renderer, JSONL schema, trace-split determinism | CPU doctors pass twice |
| 1 | Tinker `Qwen/Qwen3.5-4B` | interface smoke, cost calibration, checkpoint export/resume | `tinker_doctor.py --online` receipt; resume matches |
| 2 | Tinker `Qwen/Qwen3.5-9B-Base` or `Qwen3.8-27B` | first treatment/control LoRA pair | preregistered effect size, three seeds |
| 3 | Tinker `moonshotai/Kimi-K2.6` (32K training context) | cross-family transport of the same contract | rung 2 passed; budget frozen |

Constraints verified from Tinker's docs and SDK source on 2026-09-01: the
LoRA surface is five fields with no per-module targeting and no documented rank
cap; MoE adapters use a shared-outer scheme (Kimi-K2.6 rank-1 ≈ 146.7M
parameters, rank-32 ≈ 4.69B); custom losses see only target-token log-probs and
`forward_backward_custom` costs about 1.5× FLOPs; no hidden states, activations,
or gradients are exposed (only MoE expert-balance metrics); AdamW is the only
optimizer; external adapters cannot be imported; a merged Kimi-K2.6 export means
INT4 dequantize → merge → requantize over roughly 595 GB–1 TB. Thinking Machines'
own Kimi-K2.6 SFT sweep stopped at rank 4 (best rank 2), and Tinker has no
rollout routing replay, which R3 identifies as a MoE-RL collapse risk. Adversarial
literature to cite before any LoRA-only claim: "Procedural Knowledge Is Not
Low-Rank" (arXiv 2607.21612), Hybrid-LoRA (2605.18822), and "How Many Bits Can
an Adapter Write?" (2607.21351).

Two repo-facing corrections from the 2026-09-01 check: the pinned client
`tinker==0.23.3` is stale (PyPI 0.27.0; the service rejects unsupported SDKs
with HTTP 400 — observed for 0.22.3 in June 2026; whether 0.23.3 is still
accepted is unknown without a key) and needs an SDK-version doctor before any
paid run; and the 32K
training context assumed by the Kimi stages overflows on 60.6% of SWE-Bench
Verified episodes in the first-party Harbor recipe, so contracts must budget
the 128K tier or cap episode length.

LoRA-only access constrains what a Tinker rung can say about architecture:
it can test whether a frozen 1T hybrid accepts a protocol, objective, or
adapter-expressed mechanism; it cannot test a from-scratch architecture claim.
Label every Tinker result `attachment-capability` unless a matched local
from-scratch arm exists.

## 4. Operator durability: tmux, Slurm, checkpoints

`tmux` keeps the operator shell alive across SSH drops (like `caffeinate` for a
terminal); it does not protect a computation from a node reboot or scheduler
cancellation. Only Slurm-owned jobs with atomic checkpoints on persistent
storage survive that.

```bash
ssh kevin@207.241.191.91
bash scripts/tmux-research-session.sh cotcodec          # attach or create the durable session
cd /home/kevin/cotcodec && git fetch origin main && git merge --ff-only origin/main
uv run python scripts/submit_docker_research_job.py experiments/<manifest>.yaml --dry-run
uv run python scripts/submit_docker_research_job.py experiments/<manifest>.yaml --test-only
uv run python scripts/submit_docker_research_job.py experiments/<manifest>.yaml   # prints job id
squeue -j <job-id>; tail -F /home/kevin/cotcodec-runs/<run-root>/slurm-<job-id>.out
```

Checkpoint rules (from `docs/research-operations.md`): `--signal=B:USR1@180`
triggers an atomic checkpoint; keep two validated generations; bind model or
adapter state, optimizer, scheduler, RNG, data cursor, step, config, source and
model hashes, and parent job id; a workload is queue-ready only when a fresh job
restores the checkpoint and matches the uninterrupted continuation. Never write
results to node-local `/tmp`.

Publication-grade runs remain blocked until the scheduler upgrade in
`docs/h100-operator-runbook.md` lands (cgroup-v2 device constraints, NVML GRES,
Enroot + Pyxis, isolation doctors).
