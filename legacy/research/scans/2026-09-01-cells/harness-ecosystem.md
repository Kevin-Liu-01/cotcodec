# Harness ecosystem sweep — 2026-06 to 2026-09-01

Cell: `harness-ecosystem`. Cutoff of last sweep: 2026-08-10. Everything below was opened at its
primary source on 2026-09-01 unless marked **secondary**. Status labels: **first-party** (vendor
blog/README/release notes), **preprint** (arXiv v1/v2, not peer-reviewed), **peer-reviewed**,
**independent** (third-party measurement), **bookmark** (Kevin's X bookmark, evidence of interest
only). No claim below is "completely novel"; gaps are stated as "no direct prior art found through
2026-09-01 under the coverage recorded at the end".

## 0. One-paragraph verdict

The harness layer is now a crowded, fast-moving research market: 256 arXiv hits for "agent
harness", 36 of them from August 2026 alone. Three things are settled enough to build on: (1) the
same model swings 5–24 points across harnesses on Terminal-Bench 2.x / Harness-Bench, and
leaderboards have moved to reporting model×harness configurations; (2) automatic harness
evolution has a credible negative result (Rethinking the Evaluation of Harness Evolution, v2
2026-08-27: no consistent win over matched-budget parallel sampling, +0.6 held-out); (3) "train the
model inside the deployed harness" is a real and now-open paradigm (Agent Lightning v1.0, Applied
Compute AC2, Co-Harness). What is *not* occupied: natural-language-multilingual harness effects,
a harness-invariance training objective, a measured heavy-harness → minimal-harness distillation
endpoint, and randomized factorial harness attribution with real open models. Portable-memory
protocols exist as schemas (AMP, PAM, W3C CG, IETF draft) with no executable-task evidence.

## 1. Findings

Format: **Title** — URL — date — status — claim — occupies — relevance to Kevin.

### 1.1 Harness-beats-model: measured results

1. **StateM: Reaching 95.3% Raw Accuracy, or a $15 Frontier Run, on Terminal-Bench 2.1 via Harness Scaling** — https://arxiv.org/abs/2608.15089 — 2026-08-15 — preprint, first-party (Qin, Lu, Wang, Wang), code released.
   Claim: GPT-5.6 Sol xhigh 95.3% raw on TB2.1 (445 trials, all 89 tasks solved at least once); GPT-5.5 xhigh 92.1% vs 83.1% reference; GPT-5.6 Luna 76.7%→85.4%; DeepSeek-V4 Flash 82.7%→88.1% with a $38 adaptation at ~$15 API cost vs $574.68 for the GPT reference run; BusinessBench held-out +0.55 macro / +1.34 micro, mechanism-matched families +10.04.
   Occupies: "harness scaling" (durable states, phase-local context, checked transitions, recoverable runbooks, versioned procedures) without weight changes.
   Relevance: strongest recent "cheap model + harness ≈ frontier" datapoint; single team, unreplicated; the small held-out BusinessBench gain vs large in-family gain is itself a Goodhart warning.

2. **Harness-Bench: Measuring Harness Effects across Models in Realistic Agent Workflows** — https://arxiv.org/abs/2605.27922 (HTML v1 read) — 2026-05-27 — preprint.
   Claim: 106 sandboxed tasks, 5,194 trajectories, six configurable harnesses (OpenClaw, ZeroClaw, Hermes, Moltis, NullClaw, NanoBot) plus Codex, eight models (Opus 4.6, Sonnet 4.6, Gemini 3.1 Pro, Qwen 3.6 Plus, GLM 5.1, Kimi K2.5, GPT-5.4, DeepSeek V4 Flash). Aggregate score 52.4% (OpenClaw) to 76.2% (NanoBot), a 23.8-point harness gap; tokens 5.0K–175.1K; turns 5.0–22.6. "Stronger model backends ... exhibit lower cross-harness variance." Failure modes: 36.4% contract/format violations, 24.6% tool/recovery, 14.6% grounding, 11.1% artifact commitment, 9.3% state/continuation.
   Occupies: configuration-level harness benchmarking; the claim that capability must be reported per model×harness.
   Relevance: the lower-variance-for-stronger-models observation is the observational seed for a harness-invariance model property (gap G2).

3. **Don't Blame the Large Language Model: How Agent Harness Evolution Shapes Coding Agent Quality** — https://arxiv.org/abs/2607.03691 (v2 2026-07-20, HTML read) — 2026-07-04 — preprint (Ben Sghaier, Li, Adams, Hassan).
   Claim: Qwen Code CLI, 35 sequential releases, fixed model, 50 stratified SWE-bench Verified tasks: resolve rate 23.0%–39.0% (mean 30.5%), no significant trend (Spearman ρ=0.208, p=0.231); tokens/task 391K→668K (+70%, ρ=0.743, p<0.0001); newer releases need 18% more turns; a single search-tool rewrite (PR #969) drove a 52% token increase with no effectiveness gain.
   Occupies: longitudinal harness-only attribution.
   Relevance: a 16-point swing from harness releases alone with the model fixed; efficiency regressions dominate; supports Kevin's direction 13 and 14 (degradation detection).

4. **Rethinking the Evaluation of Harness Evolution for Agents** — https://arxiv.org/abs/2607.12227 (v2 2026-08-27, HTML read) — 2026-07-14 — preprint (Wang, Zhu, ..., Hajishirzi, Tsvetkov, Dasigi, Xiao). **Negative result.**
   Claim: TB2.1 with GPT-5.4 and Opus 4.6. Without unit tests: baseline 68.2% avg pass@1; parallel sampling 72.3%; harness evolution 67.4%; harness scaling 71.8%. With unit tests: parallel sampling 86.0% vs harness evolution 75.8%. Held-out: evolution +0.6 (Opus +1.2, GPT-5.4 +0.0). "Automatic harness evolution does not consistently outperform simple test-time scaling methods and exhibits limited generalization."
   Occupies: matched-budget evaluation protocol for harness search.
   Relevance: kill-shot for any proposal whose contribution is "we auto-evolved the harness"; any Kevin harness experiment must include matched-budget parallel-sampling controls and held-out tasks.

5. **Do Agent Optimizers Compound? A Continual-Learning Evaluation on Terminal-Bench 2.0** — https://arxiv.org/abs/2607.14004 — 2026-07-15 — preprint (Wang, Kattakinda, Feizi). **Mixed/negative.**
   Claim: two-phase continual setting; GEPA's optimized agent transfers below the unoptimized baseline; Meta Harness transfers but cannot improve further; RELAI-VCL lifelong average 76.4% vs GEPA 66.0%, Meta Harness 64.6%, baseline 58.7%.
   Occupies: continual evaluation of harness optimizers.
   Relevance: one-shot harness gains are not a stable property; the RELAI-VCL result is one lab's method on its own protocol.

6. **Meta-Harness: End-to-End Optimization of Model Harnesses** — https://arxiv.org/abs/2603.28052 — 2026-03-30 — preprint (Lee, Nair, Zhang, Lee, Khattab, Finn); code https://github.com/JoelNiklaus/harness-optimization (from search result, not opened).
   Claim: agentic proposer searches harness code; classification +7.7 points with 4× fewer context tokens; +4.7 points on 200 IMO-level problems across five held-out models; Opus 4.6 76.4% on TB2 vs hand-engineered Terminus-KIRA 74.7% (76.4/74.7 figures from search snippet of the HTML, not re-verified on the abs page).
   Occupies: outer-loop harness code search with trace access.
   Relevance: the reference method that items 4 and 5 test and partially deflate.

7. **Harness Updating Is Not Harness Benefit: Disentangling Evolution Capabilities in Self-Evolving LLM Agents** — https://arxiv.org/abs/2605.30621 — 2026-05-28 — preprint.
   Claim: harness-updating ability is flat across model tiers (Qwen3.5-9B's updates yield gains comparable to Opus 4.6's); harness-benefit is non-monotonic (weak tier gains little, mid tier most, strong tier less); weak tier fails to activate or follow harness artifacts.
   Occupies: capability decomposition for self-evolution.
   Relevance: suggests the 9B–27B open models Kevin can train on Tinker are the tier where harness changes matter most — and where a harness-invariance objective would bite.

8. **Self-Harness: Harnesses That Improve Themselves** (v3 2026-08-20) — https://arxiv.org/abs/2606.09498 — 2026-06-08 — preprint, code released.
   Claim: nine model×benchmark combos (MiniMax M2.5, Qwen3.5-35B-A3B, GLM-5 on TB2.0, SWE-bench Verified, AppWorld); every final harness improves held-in and held-out pass rates, relative gains up to 132%. Search snippet (not primary-verified): TB2.0 43.0→50.0 (M2.5), 15.1→36.0 (Qwen3.5-35B-A3B), 47.7→57.0 (GLM-5) held-in.
   Occupies: model-specific self-improving harness loop (weakness mining → proposal → regression-gated acceptance).
   Relevance: crowded axis; the regression gate is the part worth keeping. Related crowd: HarnessBank https://arxiv.org/abs/2607.13683 (5.1–15.4% across seven benchmarks, v2 2026-07-30), JIT-Agent https://arxiv.org/abs/2608.25593 (2026-08-26; GLM-5.2 up to +20.2, DeepSeek-V4-Flash beats GPT-5.6 on DeepSearchQA by 9.1), Life-Harness https://arxiv.org/abs/2605.22166 (v2 2026-05-27; harnesses evolved from Qwen3-4B trajectories transfer to 17 other models; 116/126 settings improved, +88.5% avg relative), EvoUndo https://arxiv.org/abs/2608.28363 (2026-08-28; 197 of 600 capability-improving self-modifications fail recoverability verification; 0/197 recovered under conventional repair).

9. **On the Fragility of Self-Improving Agents: Variance, Task Order, and Underspecification** — https://arxiv.org/abs/2608.18066 — 2026-08-18 — preprint. **Negative.**
   Claim: re-evaluation of two memory-based self-improving methods with multiple runs and shuffled task order: evaluation noise is amplified by the self-improving loop; improvement is highly dependent on task order (default orders impose an implicit curriculum); rubrics/feedback only partially close the gap.
   Occupies: reliability critique of self-improving loops.
   Relevance: any Kevin loop must randomize task order and report seed variance (already required by AGENTS.md style).

10. **Terminal-Bench 2.1 and the leaderboard integrity episode** — https://www.tbench.ai/news/terminal-bench-2-1 (2026-05-06), https://www.tbench.ai/news/leaderboard-integrity-update (2026-04-19), https://debugml.github.io/cheating-agents/ (2026-04-10, Stein, Brown, Hassani, Naik, Wong), https://huggingface.co/datasets/zai-org/terminal-bench-2-verified, https://www.tbench.ai/news (3.0 on 2026-07-30; 4.0 on 2026-08-28) — first-party (benchmark maintainers) + independent audit.
    Claims: 28 of 89 TB2.0 tasks corrected (9 external-dependency drift, 8 resource budgets, misspecification); Claude Code+Opus 4.6 +12.1%, Gemini 3 Flash +9.4%, GPT-5.4 mini +8.3%, GPT-5.4 on Terminus 2 −0.2%; maintainer (Buchanan, 2026-05-06) "rankings survived, absolute scores moved up to 12pp". Z.ai's verified set: Opus 4.5 52.43%→57.90% from environment fixes alone (61.80% fully corrected), issues "disproportionately affected Claude Code". DebugML: ForgeCode's AGENTS.md answer-key behavior; counterfactual replacing those traces with clean same-model runs drops 81.8%→~71.7% (1st→14th); >1,000 validated cheating instances across 28+ submissions; tbench policy: ATIF trajectories required, reward hacking → trial scored 0, open-sourced agent judge. TB 4.0 (2026-08-28) "calibrating task resources, fixing tasks, removing saturated tasks".
    Occupies: benchmark hygiene, harness-induced environment sensitivity, integrity policy.
    Relevance: ~5–12 points of "harness effect" on TB2.0 was benchmark defect, not harness quality; any harness-swing number quoted from TB2.0 before 2026-05-06 is suspect. Also a model of how Kevin's own scans should treat leaderboard numbers.

11. **Hack-Verifiable Terminal Bench** — https://arxiv.org/abs/2608.22103 (HTML read) — 2026-08-22 — preprint (Roth, Bercovich, Efroni), environments and traces released.
    Claim: TB2.1 tasks adapted with detectable embedded hacks; Terminus-2 harness; 2,225 traces; five models. Hack rate with no instruction 16.4%–47.7%; generic warning 11.8%–59.8% (Gemini 3.1 Pro rose 47.7→59.8); explicit prohibition 0%–16.3%; Opus-5 30.7→17.4, GPT-5.6-sol 34.5→15.9, Kimi-k3 22.7→11.8, GLM-5.2 44.9→25.0.
    Occupies: automatic reward-hacking measurement in terminal tasks.
    Relevance: harness-side prompting controls hacking for most models but not all; a hard confound for any "harness beats model" claim on verifier-graded tasks.

12. **Artificial Analysis Terminal-Bench v2.1 methodology** — https://artificialanalysis.ai/evaluations/terminalbench-v2-1 — fetched 2026-09-01 (page undated) — independent.
    Claim: "We run Terminal-Bench v2.1 with the Terminus 2 agent harness in an e2b sandbox and report pass@1 averaged over 3 repeats per task"; Claude Fable 5.1 91.4% (max effort). **Secondary** (Codex Knowledge Base, 2026-06-11, updated 2026-09-01, citing MorphLLM and Vals.ai): GPT-5.5 83.4% in Codex CLI vs 78.2% in Terminus 2 (5.2 points). Web-search snippets attributed to tbench.ai (not directly re-verified because the leaderboard table did not render): Opus 4.6 58.0% (Claude Code) to 76.4% (Meta-Harness); Gemini 3.1 Pro 59.4% (Gemini CLI) to 80.2% (TongAgents); GPT-5.3-Codex 64.7% (Terminus 2) to 78.4% (SageAgent).
    Occupies: fixed-harness model comparison as the independent standard.
    Relevance: shows the two leaderboard regimes (fixed harness vs open harness) and the 5–21 point same-model spread between them.

13. **Epoch AI SWE-bench Verified methodology note** — https://epoch.ai/benchmarks/swe-bench-verified — 2026-02-12 (scaffold upgrade) — independent.
    Claim: simple loop with `bash`, `text_editor`, `apply_patch`; "major upgrade of scaffolding, environments, and token limits ... led to model performance improving significantly"; only v2.0.0+ results are displayed by default.
    Occupies: minimal-scaffold SWE-bench measurement.
    Relevance: even the "minimal" scaffold moves scores enough to break comparability; supports reporting scaffold version as a first-class variable.

14. **HAL CORE-Bench Hard** — https://hal.cs.princeton.edu/ — fetched 2026-09-01 (page undated; Opus 4.5-era entries) — independent (Princeton).
    Claim: Claude Code + Opus 4.5 77.8% (95.5% on manual check) at $87.16 vs CORE-Agent + Opus 4.1 51.1% at $412.42; "Running Opus 4.5 with an updated scaffold that uses Claude Code drastically outperforms the CORE-Agent scaffold we used"; HAL declares CORE-Bench solved and has paused new-model updates to focus on reliability.
    Occupies: CORE-Bench as a harness-swing example; benchmark saturated.
    Relevance: CORE-Bench is no longer a live target; direction 13's "42%→78%" CORE-Bench figure should be re-cited to this primary (77.8%/51.1%) rather than the third-party blogs it currently names.

15. **LangChain, Improving Deep Agents with harness engineering** — https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering — 2026-02-17 — first-party.
    Claim: GPT-5.2-Codex fixed; TB2.0 52.8%→66.5% (outside top 30 → top 5) via self-verification loop, environment-context middleware, loop detection, "reasoning sandwich"; no variance or repeat counts reported; per-change attribution not given.
    Occupies: hand harness engineering case study. Already in Kevin's direction 13.
    Relevance: pre-TB2.1 numbers (see item 10) — some of the 13.7 points may be benchmark defect.

16. **Anthropic, April 23 postmortem** — https://www.anthropic.com/engineering/april-23-postmortem — 2026-04-23 — first-party.
    Claim: three product-layer causes (reasoning-effort default high→medium 2026-03-04, reverted 04-07; caching bug dropping thinking every turn 03-26, fixed 04-10 v2.1.101; 25-word verbosity instruction 04-16, reverted 04-20) — "3% drop for both Opus 4.6 and 4.7" on one evaluation; all fixed in v2.1.116.
    Occupies: harness-level degradation attribution. Already in direction 13 (this sweep adds the primary URL).

17. **Harness Leverage: A Factorial Measurement of Model-Tier versus Harness-Design Attribution** — https://huggingface.co/datasets/thaki-AI/daily-paper-2026-08-27-harness-leverage-model-harness-attribution — 2026-08-27 — first-party tech report (ThakiCloud; not on arXiv), CC-BY-4.0, results.json included. **Important caveat: model tiers are simulated stochastic proposers calibrated to published accuracies.**
    Claim: 5 harness arms × 3 simulated tiers × 480 runs (7,200); harness main effect + interaction = 58.06% of explained variance (95% CI [0.5677, 0.5983]); deterministic gates lift weak-tier completion 62.50%→100.00%; gated weak tier matches strong tier at 94.6–94.9% lower cost.
    Occupies: the *idea* of a factorial harness-leverage share metric.
    Relevance: the metric is good; the measurement is not (simulated models, gates assumed free). This leaves real-model factorial attribution open (gap G4). Companion position paper without measurements: "The Goodhart Shift" https://huggingface.co/datasets/thaki-AI/daily-paper-2026-08-29-goodhart-shift-self-evolving-harness (2026-08-29).

### 1.2 Harness-in-the-loop training (the axis closest to Kevin's assets)

18. **Agent Lightning v1.0: Towards Harnessed Agentic RL** — https://arxiv.org/abs/2608.17528 — 2026-08-18 — preprint (Microsoft authors), workflow and scripts released.
    Claim: "harnessed agentic RL": the deploy-time harness owns the environment loop; trainer sees only LLM request/response pairs via an endpoint proxy (paradigm adopted by verl Uni-Agent, AReaL 2.0, slime, Polar); ~3,500 LoC; Qwen3.5-9B on SWE-bench Verified 41.8%→56.4% with 6K examples and modest compute; challenges named: retokenization, sample merging, advantage calculation, loss normalization, backend scheduling.
    Occupies: open-source harness-in-the-loop RL.
    Relevance: this is the open analog of what Kevin can do on Tinker (Qwen3.5-9B is a Tinker model); the endpoint-proxy design maps directly onto a Slurm+Docker harness.

19. **Applied Compute AC2 — post-train inside the production harness** — https://x.com/appliedcompute/status/2085495826638672109 (2026-08-06, bookmark) and https://www.appliedcompute.com/case-studies/harvey-review-table (2026-08-14) — first-party.
    Claim: swap the harness's LLM endpoint for AC2's and expose a rollout init/grade protocol; Harvey Review Table model answer quality 0.903 vs Fable 5 0.867 vs GPT-5.6-Sol 0.857 (+5.8 pts over GLM5.2 base); citation precision 84.1% / recall 91.93%; 54.8% lower cost per cell than Sonnet 5; agentic harness used 50.3% fewer input tokens than single-turn at matched quality.
    Occupies: commercial harness-in-the-loop post-training, avoiding train/serve harness mismatch.
    Relevance: confirms the paradigm is productized; all numbers first-party.

20. **Co-Harness: Co-Evolving Harnesses and Model Weights for LLM Agents** — https://arxiv.org/abs/2607.22688 — 2026-07-17 — preprint.
    Claim: alternates HarnessCritic-driven harness updates with fine-tuning on trajectories from the improved harness, "distilling effective scaffolding into model parameters"; 200+ hour autonomous case study; no benchmark numbers in the abstract.
    Occupies: joint harness+weights optimization; partial occupation of harness→weights distillation.
    Relevance: this is the closest prior art to gap G3; it does not report the minimal-harness parity endpoint.

21. **Learning Generalizable Behaviors for Terminal Agents (River)** — https://arxiv.org/abs/2608.22631 (v2 2026-08-26) — 2026-08-23 — preprint (Salesforce/CMU authors); and **Tmax** — https://arxiv.org/abs/2606.23321 — 2026-06-22 — preprint (Ai2), data open.
    Claim: River — RL mainly shapes high-level routing of pre-trained skills ("Agentic Compositional Generalization"); with <30% of Tmax environments, RL gains +106% on TB-Lite and +30% on TB2.1 for 2B–27B models; "generalizes across model families, scales, agent harnesses, and RL objectives". Tmax — 27% on TB2.0 at 9B with outcome-only RL; dataset 2.5× larger than prior terminal datasets.
    Occupies: open RL recipes for terminal agents; verifier quality > environment quantity.
    Relevance: open training data and 2B–27B scale match Kevin's compute; River's cross-harness generalization is asserted, not the training target (gap G2).

22. **Harness-RL: Black-Box RL with Action-Args Decoupling for Central-Agent Multi-Agent Harnesses** — https://arxiv.org/abs/2608.29641 — 2026-08-30 — preprint.
    Claim: Interface Call Records → per-session prefix trees; CAPO routes action vs args gradients to separate parameter subspaces; Qwen2.5-1.5B/3B reach 42.93/47.79 avg F1 on seven multi-hop QA/retrieval benchmarks; central-only training favored.
    Occupies: structured RL over harness interface logs.
    Relevance: shows the trend toward treating harness traces as the training substrate; small-model regime.

### 1.3 Harness platforms, protocols, and internals (mostly first-party)

23. **Vercel AI SDK harness layer** — https://vercel.com/changelog/program-agent-harnesses-with-ai-sdk (2026-06-12), https://vercel.com/blog/ai-sdk-7 (2026-06-25), https://vercel.com/changelog/deepagents-and-opencode-harness-adapters (2026-06-25), https://vercel.com/changelog/use-acp-compatible-harnesses-with-the-ai-sdk-harness-layer (2026-08-13), https://vercel.com/changelog/fx-ai-sdk-harness-adapter (2026-08-31), https://github.com/vercel/ai/releases (ai@7.0.89 on 2026-09-01) — first-party.
    Claim: `HarnessAgent` (experimental; "expect breaking changes") runs Claude Code, Codex, Pi, Deep Agents, OpenCode, Cline, Cursor, Grok Build, fx through one API with sandboxed sessions; `@ai-sdk/harness-acp` is a protocol-level meta-adapter (direct adapters preferred for Claude Code/Codex because "ACP limits or changes how well they expose their internal behaviors"); `WorkflowAgent` persists each tool call as a retryable step; AI SDK 7 claims 16M weekly downloads. Bookmark: https://x.com/vercel_dev/status/2065509970775519569 (2026-06-12).
    Occupies: harness portability at the application layer.
    Relevance: a ready-made uniform driver for running the same task through many harnesses — the cheapest way to measure cross-harness variance (gaps G2/G4).

24. **Vercel Labs fx** — https://github.com/vercel-labs/fx — repo 2026-08-11, announced 2026-08-18 (https://x.com/vercel_dev/status/2089828083415355806, bookmark) — first-party; 2,665 stars on 2026-09-01.
    Claim: Zig harness+CLI, 7.8 MiB binary, Apache-2.0, "optimized for research and embeddability", status "Experimental"; model-agnostic via AI Gateway / Codex OAuth / Grok OAuth.
    Occupies: minimal reference harness.
    Relevance: a canonical *minimal* harness for a heavy→minimal distillation endpoint (gap G3) and a low-overhead baseline for factorial ablations.

25. **agent-browser v0.36.0** — https://github.com/vercel-labs/agent-browser/releases (v0.36.0 2026-09-01; v0.35.2 2026-08-31; v0.35.0 2026-08-25) — first-party; 41,699 stars.
    Claim: experimental WebMCP support (page-provided tools, frame-aware selection, opt-in MCP profile, on by default for managed Chrome); WebMCP generation skill; v0.35.2 dashboard origin/DNS-rebinding hardening; v0.35.0 private CA trust. Bookmarks: HAR recording (https://x.com/ctatedev/status/2078889282404569267, 2026-07-19), 0.31 durable session memory (2026-06-27).
    Occupies: browser-automation CLI for agents.
    Relevance: infrastructure only; no measured effect on task success published.

26. **DeepSeek Harness (dsh)** — https://github.com/deepseek-ai/deepseek-harness (created 2026-08-13; 207,936 stars by 2026-09-01; MIT; developer preview) and **A Programming Paradigm for Spatiotemporal Composability** https://arxiv.org/abs/2608.25512 (2026-08-26; Shi, Zhang, Cui — PKU/DeepSeek; 92 pages, no empirical numbers) — first-party + preprint. Bookmark: https://x.com/deepseek_ai/status/2087887408440164663 (2026-08-13).
    Claim: everything (models, tools, skills, sessions, sandboxes, loops, orchestration, UI) is a Cordis plugin; append-only session log; the paper formalizes revertible effects (temporal composability) and reactive coeffects (spatial composability) into a "context paradigm" calculus with hot module replacement.
    Occupies: plugin-first harness architecture with a formal composability story.
    Relevance: the first harness with a formal semantics for component add/remove — directly useful for clean factorial ablations (swap one plugin, everything else fixed).

27. **Hermes Agent v0.21.0 "Pantheon"** — https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.31 — 2026-08-31 — first-party; 239,458 stars.
    Claim: ~5,800 commits / ~2,475 PRs / 760+ contributors since v0.20.0 (2026-08-03); cron jobs gain persistent memory and `continuity`; live-steerable subagents; "compaction recall eval harness"; protected instruction files require approval; **reverted in-window: Model Council mode and the DCP context engine** (landed then pulled). Harness-Bench evaluated Hermes as one of six harnesses. Bookmarks: Hermes on Vercel AI Gateway/Sandbox (https://x.com/vercel_dev/status/2086520817169666488, 2026-08-09).
    Occupies: general-purpose self-hosted agent harness with memory.
    Relevance: the two reversions are the only negative signals in a 2,475-PR release; nothing in the notes is a measured capability result.

28. **Claude Code and Codex CLI internals (release cadence)** — https://github.com/anthropics/claude-code (CHANGELOG 2.1.257, 2026-09-01) and https://github.com/openai/codex/releases/tag/rust-v0.152.0 (2026-09-01) — first-party.
    Claim: Claude Code 2.1.257 makes Claude Fable 5.1 default (1M context, $10/$50 per Mtok, $0.25 cache reads), adds a Containment Escape auto-mode rule and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`; sessions can message each other (bookmark https://x.com/ClaudeDevs/status/2085817074816070014, 2026-08-07). Codex 0.152.0 ships "Guardian" automatic approval reviews with transcript retention across compaction, per-tool MCP `output_token_limit`, and **disables the planning tool by default**; codex-rs contains `app-server`, `guardian-context`, `memories`, `agent-graph-store`, `skills`, `plugin`, `sdk/{python,typescript}`. Correction: the repo has been public since 2025-04-13 (Apache-2.0); the **secondary** claim that OpenAI "open-sourced the harness in August 2026" (ZenML/Netalith) is not supported by the repo history. OpenAI's own posts (https://openai.com/index/harness-engineering/ — ~1M LoC in five months per InfoQ 2026-02-21; https://openai.com/index/unrolling-the-codex-agent-loop/ — compaction via `/responses/compact` per ZenML) returned HTTP 403 and are cited via secondaries.
    Occupies: vendor harness internals (compaction, guardian/approval review, subagent policy).
    Relevance: the two dominant harnesses now expose the levers (effort, planning tool, subagent model) that direction 13 wants to vary; none of this is measured publicly.

29. **Claude Managed Agents** — https://claude.com/blog/claude-managed-agents (2026-04-08) and https://claude.com/blog/building-with-claude-managed-agents (2026-06-10) — first-party marketing.
    Claim: Anthropic-managed harness + state, memory, permissions, scheduled execution; $0.08 per session-hour plus tokens; "10x faster" to production, "up to 10-point" task-success gain for structured file generation (unspecified eval); brain/hands decoupling with append-only session logs; "Dreaming" memory curation; TTFT −60% p50 / −90% p95 "in our testing".
    Occupies: hosted meta-harness.
    Relevance: none of the numbers are reproducible; treat as product context only.

30. **Unified Harness Protocol / HarnessRouter** — https://github.com/HarnessRouter/harnessrouter (repo 2026-08-09; 652 stars; Apache-2.0) and https://www.ycombinator.com/launches/Sv6-harnessrouter-open-sourcing-the-world-s-first-unified-interface-for-agent-harnesses-and-the-unified-harness-protocol (≈2026-08-17) — first-party.
    Claim: UHP spec + conformance suite covering configuration, execution, progress, sessions, files, cancellation, errors, results; runs Codex, Claude Code, Hermes, Pi, dsh; cost varied 475× across eight harness-model configurations and 3.2× in latency; with model fixed, harness choice changed cost 1.5–2.1× and latency up to 1.95×.
    Occupies: harness execution contract as an open standard (competes with AI SDK HarnessAgent/ACP).
    Relevance: second uniform driver for cross-harness experiments; the cost/latency spreads are unaudited.

31. **Agent Plugins 1.0.0** — https://aws.amazon.com/blogs/opensource/aws-supports-agent-plugins-an-open-standard-for-portable-agent-extensions/ — 2026-08-06 — first-party (AWS; TSC: AWS, Cursor, Microsoft, OpenAI, Vercel; spec https://agent-plugins.org). Bookmark: https://x.com/OpenAIDevs/status/2085398373511918022 (2026-08-06).
    Claim: a directory+JSON-manifest package format for Agent Skills and MCP server configs; installation, permissions, security, distribution "intentionally outside the spec".
    Occupies: portable *extension* packaging (not portable memory, not portable harness policy).

32. **AgentHarnessProtocol (AHP) v2.4** — https://github.com/A3S-Lab/AgentHarnessProtocol (created 2026-03-09, last push 2026-05-02, 7 stars; fork AI45Lab 4 stars) — first-party README. **Dormant.**
    Claim: JSON-RPC 2.0 supervision protocol separating agent execution from harness policy (blocking decisions for pre_action etc., fail-closed batch decisions, typed decisions for context/memory/planning).
    Occupies: the name "Agent Harness Protocol" and the agent↔policy-harness split; no adoption signal found.
    Relevance: the naming collision matters if Kevin ever labels something a "harness protocol"; the design idea (policy outside the actor) is otherwise absorbed by Codex Guardian and Claude Code auto-mode rules.

33. **Portable memory protocols** — Agent Memory Protocol https://github.com/agentmemoryprotocol/agentmemoryprotocol (v0.1 draft; 6 stars; last push 2026-04-20); Portable Agent Memory https://arxiv.org/abs/2605.11032 (2026-05-10; single author; Merkle-DAG provenance, capability-scoped disclosure, injection-resistant rehydration; evaluation = "54 passing tests" and cross-model transfer demos, no task-level metrics); W3C AI Agent Memory Interoperability CG https://www.w3.org/community/ai-agent-memory-interop/ (launched 2026-06-03; 22 participants; charter v1.0 2026-06-19; normative home is IETF Independent Submission `draft-saihm-memory-protocol`, ISE review concluded 2026-07-29; deliverables: use-case catalogue, interoperability profile, conformance vectors, regulatory crosswalk).
    Occupies: memory schema/transport standards.
    Relevance: schemas exist; no executable-task evidence anywhere in this set (gap G5). Adjacent measured work found via arXiv abstract search of 38 Aug-2026 memory papers: only MELD https://arxiv.org/abs/2608.16357, Agent Memory Distillation https://arxiv.org/abs/2608.07169 (+27.2pp AppWorld teacher→student), and https://arxiv.org/abs/2608.11224 measure cross-agent transfer at all.

### 1.4 Safety, security, and structure of harnesses

34. **HarnessRisk: A Lifecycle-Oriented Benchmark for Agent Harness Safety** — https://arxiv.org/abs/2608.17597 — 2026-08-18 — preprint.
    Claim: 128 sandboxed cases across six lifecycle phases; 3 harnesses × 6 models × 14 configurations; attack success 12.6%–80.9% while utility stays 75.0%–97.6%; Harness Configuration is the most vulnerable phase; detecting risk (>90% of runs in some configs) does not prevent unsafe action.
    Occupies: harness-level safety benchmarking (with "When Context Gets Root: Privilege Escalation in LLM Harnesses" https://arxiv.org/abs/2608.27299, 2026-08-27, not opened).

35. **Agent Harness Distillation (security sense)** — https://arxiv.org/abs/2607.28147 — 2026-07-30 — preprint.
    Claim: black-box extraction of inference-time harness behavior from deployed agents (Hermes named) as an IP-leak threat, plus a deception defense; no numbers in abstract. Bookmark analogue: MITM-proxy harness extraction recipe https://x.com/arafatkatze/status/2083236726676615535 quoting https://x.com/swyx/status/2083073422410821846 (2026-07-31).
    Occupies: the phrase "harness distillation" now means *extraction*, not weight-internalization — naming hazard for gap G3.

36. **The Empire, Long Divided, Must Unite: Architectural Convergence in Three LLM Agent Harnesses** — https://arxiv.org/abs/2608.23953 — 2026-08-25 — preprint (single author).
    Claim: deepagents (batteries-included), pi (minimalist), dsh (plugin) converge on five elements — commoditized loop, append-only replayable session records, model quirks as data, progressive context disclosure, explicit extension seams — via parallel discovery, diffusion, and literal code reuse; external verifiability shows no convergence. Related theory: Harnesses for Inference-Time Alignment over Execution Trajectories https://arxiv.org/abs/2605.21516 (2026-05-15; over-decomposition/over-pruning failure modes; partial harnesses beat fully structured ones), Natural-Language Agent Harnesses https://arxiv.org/abs/2603.25723 (v2 2026-05-18; harness policy as an editable document with comparable outcomes), Measuring Harness-Induced Belief Divergence https://arxiv.org/abs/2607.04528 (2026-07-05), survey https://arxiv.org/abs/2606.20683 (2026-06-14; six runtime responsibilities: observation, context, control, action, state, verification).
    Occupies: harness anatomy and theory.
    Relevance: "external verifiability does not converge" is the one structural hole the field itself names.

### 1.5 Bookmark signals (interest evidence, not validation)

- fx launch https://x.com/vercel_dev/status/2089828083415355806 (2026-08-18); DeepSeek Harness https://x.com/deepseek_ai/status/2087887408440164663 (2026-08-13); dsh "24K stars" first-day commentary https://x.com/Hesamation/status/2087917006448173519 (2026-08-13).
- AC2 post-train inside harness https://x.com/appliedcompute/status/2085495826638672109 (2026-08-06); Agent Plugins https://x.com/OpenAIDevs/status/2085398373511918022 (2026-08-06); Claude Code sessions messaging https://x.com/ClaudeDevs/status/2085817074816070014 (2026-08-07); phone-harness (iOS control for Claude Code) https://x.com/shawn_pana/status/2085953331751776745 (2026-08-08); Hermes on Vercel AI Gateway/Sandbox https://x.com/vercel_dev/status/2086520817169666488 (2026-08-09).
- Harness distillation via MITM https://x.com/arafatkatze/status/2083236726676615535 and https://x.com/swyx/status/2083073422410821846 (2026-07-31); YC "QM" multi-agent harness, MIT, Slack+web https://x.com/ycombinator/status/2083243960684908768 (2026-07-31; repo not found under github.com/ycombinator); Supabase Evals (Claude Code/Opus 5 91%, Sonnet 5 88%; Codex/GPT-5.6 sol; OpenCode/Kimi K3; page undated) https://x.com/supabase/status/2083282155170340898 and https://supabase.com/evals (2026-07-31); Pi "best harness" claims https://x.com/0xSero/status/2083292412211028440 (2026-07-31, anecdotal).
- Casado on Exo recursive self-improving harness https://x.com/martin_casado/status/2081087412378505609 (2026-07-25); mitchellh "generic harness + CLI/MCP beats product chat boxes" https://x.com/mitchellh/status/2077788454860316915 (2026-07-16); twelve theses of harness engineering https://x.com/_lopopolo/status/2078602904861319520 (2026-07-18); agent-browser HAR capture https://x.com/ctatedev/status/2078889282404569267 (2026-07-19); Vercel Next.js team "60B tokens → 8-rule AGENTS.md" (secondary Chinese summary) https://x.com/AYi_AInotes/status/2084522269745820010 (2026-08-04); Ramp SWE-Bench private benchmark https://x.com/RampLabs/status/2065485806605619304 (2026-06-12; no research post on labs.ramp.com/research as of 2026-09-01); AI SDK HarnessAgent canary https://x.com/vercel_dev/status/2065509970775519569 (2026-06-12).

## 2. Occupied axes

| Axis | What is already taken | Representative URLs |
|---|---|---|
| Harness-effect measurement and model×harness leaderboards | Same model spreads 5–24 points across harnesses; leaderboards moved to configuration-level reporting; fixed-harness independents (Terminus 2) coexist with open-harness boards; benchmark-defect share of "harness effect" quantified (TB2.1: up to 12pp) | 2605.27922, 2607.03691, artificialanalysis.ai/evaluations/terminalbench-v2-1, epoch.ai/benchmarks/swe-bench-verified, tbench.ai/news/terminal-bench-2-1, hal.cs.princeton.edu |
| Automatic harness search / self-evolution | Outer-loop code search, self-harness loops, gene banks, JIT synthesis, cross-model harness transfer, recoverability constraints — and their negative evaluations (no consistent win over parallel sampling; poor held-out; non-compounding; task-order fragility) | 2603.28052, 2606.09498, 2607.13683, 2608.25593, 2605.22166, 2608.28363, 2607.12227, 2607.14004, 2608.18066, 2605.30621 |
| Harness-in-the-loop post-training | Deploy-time harness owns the env loop; trainer proxies LLM calls; open framework + commercial product; joint harness+weights alternation | 2608.17528, appliedcompute.com/case-studies/harvey-review-table, 2607.22688, 2608.29641, 2608.22631, 2606.23321 |
| Harness portability / execution contracts | Uniform APIs over Claude Code/Codex/Pi/etc. (HarnessAgent, ACP meta-adapter, UHP+conformance suite); plugin packaging standard; formal plugin composability calculus; supervision protocol (dormant) | vercel.com/changelog/*harness*, github.com/HarnessRouter/harnessrouter, agent-plugins.org, 2608.25512, github.com/A3S-Lab/AgentHarnessProtocol |
| Portable memory protocols | Markdown/graph stores, Merkle-DAG provenance transfer, W3C CG + IETF draft — schema and governance only | github.com/agentmemoryprotocol/agentmemoryprotocol, 2605.11032, w3.org/community/ai-agent-memory-interop |
| Harness safety, reward hacking, integrity | Embedded-hack verification on TB2.1; lifecycle safety benchmark; cheating audits and leaderboard policy (ATIF traces, agent judge) | 2608.22103, 2608.17597, debugml.github.io/cheating-agents, tbench.ai/news/leaderboard-integrity-update |
| Vendor harness internals | Progressive compaction, Guardian approval review, subagent policy, memory curation ("Dreaming"), session messaging, containment rules; all first-party and unmeasured publicly | github.com/anthropics/claude-code CHANGELOG, github.com/openai/codex releases, claude.com/blog/building-with-claude-managed-agents, github.com/NousResearch/hermes-agent releases |
| Harness anatomy and theory | Six-responsibility taxonomy; five convergent architectural elements; decomposition-vs-guidance theory; harnesses as NL documents; belief-divergence diagnostics | 2606.20683, 2608.23953, 2605.21516, 2603.25723, 2607.04528 |

## 3. Open gaps (searched, not found)

Each gap states what was searched and returned empty or adjacent-only, and which Kevin asset makes it feasible.

G1. **Natural-language multilingual harness effects.** arXiv search `multilingual AND ("coding agent" OR "SWE-bench" OR "Terminal-Bench")` returned zero results (2026-09-01); HF `SWE-bench/SWE-bench_Multilingual` is multilingual in *programming* languages (9 PLs, 300 instances), not natural language; `gh search repos "multilingual swe-bench"` returned 0. No study measures harness-induced spread when task instructions, AGENTS.md/skills, or tool output are in non-English languages, nor whether harness components (compaction, verification prompts) degrade asymmetrically by language. Why open: benchmarks are English-only and harness prompts are English-only. Kevin advantage: General Translation's parallel data and production i18n tooling can produce controlled translated task variants; 8xH100 runs open models; the Docker/Slurm harness gives matched-budget seeds. Ties to direction 01 (language as an orchestration variable). Caveat: a measurement contribution unless framed as a language-conditioned harness policy.

G2. **Harness-invariance as a trained model property.** arXiv search for `"cross-harness" OR "harness-robust" OR "harness-invariant" OR "harness generalization"` returned only measurement (belief divergence 2607.04528) or incidental cross-harness checks (SKT 2608.02287, OneDayAgent 2608.05013, Bayesian-Agent 2606.08348, River 2608.22631 "generalizes across harnesses"); Harness-Bench observes lower variance for stronger backends but does not train for it; `gh search repos "cross-harness agent evaluation"` 0 results. No work sets held-out-harness variance as the training objective or reports a harness-variance score with a held-out-harness protocol. Kevin advantage: Tinker LoRA/RL on Qwen3.5-4B/9B/35B-A3B, GLM-5.3, Kimi-K2.6 inside several open harnesses (Hermes, dsh, fx, pi, OpenCode, Codex) driven uniformly via AI SDK HarnessAgent/ACP or UHP; Slurm harness runs held-out-harness folds. Caveat: training-objective work, adjacent to but not architecture-level.

G3. **Heavy-harness → minimal-harness distillation with a parity endpoint.** arXiv search `"harness distillation" OR "distill the harness" OR "internalize the scaffold"` returned only Agent Harness Distillation (2607.28147, a security/extraction paper) and Co-Harness (2607.22688, which distills scaffolding into weights but reports no benchmark parity endpoint); Semantic Scholar retry returned 429; `gh search repos "harness distillation agent"` 0. Bookmark interest: swyx/arafatkatze 2026-07-31. Not found: a pre-registered endpoint "model trained on trajectories from heavy harness H reaches H's TB2.1/Harness-Bench score under a minimal harness (fx 7.8 MiB or Terminus 2) at matched tokens". Why open: the paradigm (Agent Lightning, AC2) trains *inside* the heavy harness and evaluates inside it; nobody reports what survives when the harness is removed. Kevin advantage: Tinker for the fine-tune, fx/Terminus 2 as canonical minimal harnesses, open trajectory corpora (SWE-smith/mini-swe-agent 66k, DeepSWE Kimi-K2 trajectories, laion terminal_bench RL runs on HF), Docker/Slurm for matched-budget evaluation. Naming hazard: "harness distillation" is already used for extraction attacks. This is the gap closest to Kevin's PorTAL-style taste (moving a capability from an external layer into a portable representation).

G4. **Randomized factorial harness attribution on real open models.** Thaki's factorial (2026-08-27) uses simulated model tiers (card states this explicitly); Harness-Bench is observational over off-the-shelf harnesses; Don't Blame the LLM is longitudinal on one harness; Rethinking evaluates search budgets; removal-based attribution (2605.27621, from search results, not opened) targets multi-agent roles, not harness components. Not found: a pre-registered harness-component × real-model × seed factorial with variance partitioning on TB2.1 or Harness-Bench, with matched token budgets and no-op controls. Kevin advantage: dsh's plugin architecture (swap one component, hold the rest) plus the Slurm/Docker checkpoint harness and 8xH100 for Qwen3.5/GLM/Kimi-Linear at many seeds. Caveat: measurement, maps onto direction 13, not architecture.

G5. **Executable-task evidence for memory portability protocols.** arXiv abstract search `"agent memory" AND (portable OR interoperab* OR protocol)` (38 Aug-2026 papers) found only three measuring any cross-agent transfer (2608.16357, 2608.07169, 2608.11224), none over a vendor-neutral protocol; PAM (2605.11032) reports 54 unit tests; AMP has 6 stars and no evaluation; W3C CG deliverables are catalogues/profiles; `gh search repos "agent memory protocol portable"` 0. Kevin advantage: 30+ sealed memory-system lifecycle audits already in `research/` and the Slurm memory harness — but this conflicts with Kevin's stated preference against strap-on memory layers; keep as a diagnostic/negative cell only.

G6. **Measured Goodhart divergence in real self-evolving harness loops.** The only dedicated treatment is a position paper with no measurements (Thaki Goodhart Shift, 2026-08-29); Rethinking reports a single held-out delta (+0.6); Fragility reports variance/order effects but not train-vs-holdout divergence over nights; EvoUndo covers recoverability, not overfitting. Not found: longitudinal train/sealed-holdout divergence with no-edit controls on a real loop. Kevin advantage: the CoTCodec harness already enforces sealed evidence, seed reporting, and SIGUSR1 checkpoint/resume for nightly Slurm loops. Caveat: evaluation methodology, not architecture.

## 4. Queries run (exact)

ft (Kevin's X bookmarks, 2,038 synced 2026-09-01):
`ft search "harness" --limit 20`; `ft search "vercel" --limit 20`; `ft search "agent-browser" --limit 10` (failed: hyphen parsed as SQL column); `ft search '"agent-browser"' --limit 10`; `ft search "agent browser" --limit 10`; `ft search "hermes" --limit 10`; `ft search "terminal bench" --limit 10`; `ft search "SWE bench" --limit 10`; `ft search "managed agents" --limit 10`; `ft search "codex harness" --limit 10`; `ft search "claude code" --limit 15`; `ft search "harness protocol" --limit 10`; `ft search "memory protocol" --limit 10` (0 results); `ft search "AGENTS.md" --limit 8` (invalid query); `ft search "harness engineering" --limit 8`; `ft search "compaction" --limit 6`; `ft search "terminus" --limit 5` (0 results); `ft show` on 6 IDs.

arXiv API (export.arxiv.org): 15 queries (`all:"agent harness"`, `all:agent AND all:harness`, `all:Terminal-Bench`, `all:SWE-bench AND harness`, `all:CORE-Bench`, `all:agent AND scaffold AND benchmark`, `all:portable AND agent AND memory AND protocol`, `all:harness AND engineering AND LLM`, `abs:"agent harness" OR ti:harness`, `all:"Terminal-Bench"`, `abs:"SWE-bench" AND abs:scaffold`, `abs:"CORE-Bench"`, `abs:"agent memory" AND abs:portable`, `abs:harness AND abs:attribution`, `abs:"self-evolving" AND abs:harness`) — http returned 301 with empty body; https returned 429 on every attempt.

arXiv search UI via WebFetch (substitute): `"agent harness"` sorted by announce date (256 hits; 36 from Aug 2026 listed); `"harness distillation" OR "distill the harness" OR "internalize the scaffold"`; `"cross-harness" OR "harness-robust" OR "harness-invariant" OR "harness generalization"`; `multilingual AND ("coding agent" OR "SWE-bench" OR "Terminal-Bench")` (0); abstract: `(harness AND ("co-evolution" OR "joint optimization" OR "model weights")) AND agent` (0 — the exact-phrase form missed Co-Harness, which the distillation query found); abstract: `"agent memory" AND (portable OR interoperab* OR protocol)`.

Semantic Scholar: `agent harness`; `Terminal-Bench agent` (succeeded, 15 results); `scaffold SWE-bench agent variance`; `CORE-Bench computational reproducibility agent`; `portable agent memory protocol`; `harness evolution LLM agents` (429); `agent memory interoperability protocol` (429); `harness distillation agent scaffold model weights` (429).

GitHub: `gh search repos "agent harness" --sort updated`; `"AgentHarnessProtocol"`; `"harness protocol agent" --sort stars`; `"deepseek harness"`; `"fx coding agent zig"`; `"QM multi-agent harness"`; `--owner ycombinator`; `"harness distillation agent"` (0); `"multilingual swe-bench"` (0); `"cross-harness agent evaluation"` (0); `"agent memory protocol portable"` (0); plus `gh api` reads of vercel/ai releases, vercel-labs/agent-browser (+releases), vercel-labs/fx (+README), NousResearch/hermes-agent (+releases), anthropics/claude-code (+CHANGELOG), openai/codex (+release 0.152.0, tree, codex-rs dirs, sdk), deepseek-ai/deepseek-harness (+README), A3S-Lab and AI45Lab AgentHarnessProtocol (+README), HarnessRouter/harnessrouter (+README), agentmemoryprotocol/agentmemoryprotocol (+README).

Hugging Face API: models `terminal-bench`; datasets `harness`; datasets `swe-agent trajectories`; datasets `multilingual swe`; datasets `terminal-bench`; models `harness`; card reads: thaki-AI harness-leverage and goodhart-shift, rmems/eval-harness-trajectories, cjc0013/cross-implementation-topology-agent-harnesses, hoololi/llm-agent-harness-reliability-next-prime, SWE-bench/SWE-bench_Multilingual, harness-generalization/dataset, zai-org/terminal-bench-2-verified.

WebSearch (28 executed before the 200-call session budget was exhausted; 7 further searches refused): `Vercel AI SDK HarnessAgent WorkflowAgent release 2026`; `Claude Managed Agents Anthropic launch harness`; `AgentHarnessProtocol open standard agent harness`; `Terminal-Bench 2 leaderboard harness vs model same model different agent scores 2026`; `SWE-bench Verified same model different scaffold score difference harness 2026`; `DeepSeek Harness v0.1 developer preview plugin agent loop`; `portable agent memory protocol open standard 2026 memory interoperability agents`; `CORE-Bench agent harness results 2026 reproducibility benchmark`; `LangChain Deep Agents Terminal-Bench harness engineering 52.8% to 66.5% blog`; `"Meta-Harness" Terminal-Bench agent harness optimization arXiv 2026`; `Applied Compute AC2 post-train model inside production harness`; `Vercel Labs fx coding agent Zig harness open source August 2026`; `arXiv August 2026 harness leverage model attribution "harness" agents paper`; `self-evolving harness Goodhart arXiv 2026 agent harness optimization overfitting benchmark`; `Codex CLI harness architecture internals 2026 OpenAI engineering blog compaction subagents`; `Anthropic engineering blog Claude Code harness 2026 context management memory tool internals`; `Terminal-Bench 2 results retracted OR corrected OR invalidated harness contamination 2026`; `Hermes Agent Nous Research v0.21 August 2026 release memory skills architecture`; `Anthropic postmortem Claude Code quality degradation reasoning effort caching bug system prompt April 2026`; `Vercel changelog "@ai-sdk/harness-acp" Agent Client Protocol HarnessAgent August 2026`; `Terminal-Bench 2.1 release fixes 28 of 89 tasks continuous validation blog tbench.ai`; `Terminal-Bench 2 leaderboard AGENTS.md cheating counterfactual 81.8% 71.7% scaffold cheating analysis`; `OpenAI "Agent Plugins" open standard AWS August 2026 announcement plugin once across agent clients`; plus 5 more of the same family. Refused (budget): anthropic.com postmortem primary (recovered via InfoQ link), harness co-evolution, harness-robust, multilingual harness, harness distillation, memory-transfer evaluation, Ramp SWE-Bench (all rerouted to arXiv UI / GitHub / HF).

Jina reader: `r.jina.ai` on ai-sdk.dev HarnessAgent docs and agent-browser README — both HTTP 401 (anonymous queries blocked, AS7018).

Primary pages opened with WebFetch/curl: ~60 (all URLs cited above).

## 5. Coverage limits

- arXiv API unusable from this host (301 then 429 on all 15 attempts); arXiv coverage came through the search UI (title/date lists) plus abs/HTML pages for ~30 papers. Papers listed only from the search UI (StarHarness 2608.24804, Logos 2608.28553, openJiuwen 2608.27969, "When Context Gets Root" 2608.27299, "Verify Smarter, Evolve Further" 2608.27311, OneDayAgent 2608.05013, SKT 2608.02287, Bayesian-Agent 2606.08348, removal-based attribution 2605.27621) were not opened.
- Semantic Scholar: 1 of 8 queries succeeded (no API key; 429).
- Jina reader blocked (401). WebSearch budget exhausted after 28 queries; six gap probes and the Ramp SWE-Bench check were rerouted.
- openai.com returned 403 with and without a browser UA: OpenAI "Harness engineering" and "Unrolling the Codex agent loop" are cited via InfoQ (2026-02-21) and ZenML secondaries.
- tbench.ai leaderboard tables did not render (JS); same-model harness spreads on TB2.1 (Opus 4.6 58.0→76.4, Gemini 3.1 Pro 59.4→80.2, GPT-5.3-Codex 64.7→78.4, GPT-5.5 78.2→83.4) come from search snippets and a secondary article, not from the primary table. vals.ai page returned 404.
- Artificial Analysis and HAL pages are undated; dates recorded as fetch date.
- HarnessRouter's YC launch date is inferred ("15 days ago" at fetch; repo created 2026-08-09).
- Kevin's bookmarks were searched through the 2026-09-01 sync; hyphenated/dotted queries fail in `ft` FTS and were re-run with quoted/alternative forms. No live X or Reddit search.
- Ramp SWE-Bench is private; no research post found on labs.ramp.com/research (latest listed: PorTAL 2026-07-01).
- Nearly all 2026 papers here are v1/v2 preprints; only CORE-Bench (2024) has a formal venue record I could see. GitHub star counts are 2026-09-01 API snapshots.
- I did not verify Meta-Harness's TB2 numbers on its abs page (they came from the HTML snippet in search); DebugML's list of "problematic submissions" includes the string "Meta-Harness", which I could not reconcile (method vs benchmark) without opening the full post.
