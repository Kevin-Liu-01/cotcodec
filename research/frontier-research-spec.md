# Frontier Research Intelligence — Operational Spec

> How CoTCodec stays at the frontier. Danqi said the world is changing fast.
> This spec ensures we know about every relevant development within 48 hours
> of it appearing anywhere.

## Why This Exists

The field moves weekly. Between March 2026 (when the proposal was written)
and fall 2026 (when experiments run), entire research threads will emerge,
models will ship, benchmarks will update, and the competitive landscape will
shift. If we're not tracking this systematically, we show up in September
with a stale proposal.

This spec defines what to track, where to look, how to evaluate signals,
and how findings flow back into the project.

---

## Source Taxonomy

### Tier 1: Lab Research (highest signal, lowest noise)

These are the organizations most likely to publish work that directly
invalidates, supports, or supersedes our research questions.

| Source | URL | What to track | Cadence |
|--------|-----|---------------|---------|
| **Anthropic** | `anthropic.com/research`, `docs.anthropic.com` | Token counting changes, tool use overhead, context window updates, multilingual behavior, agent architecture | Daily |
| **OpenAI** | `openai.com/research`, `platform.openai.com/docs` | Reasoning model updates (o-series), structured outputs, function calling changes, token pricing | Daily |
| **DeepSeek** | `github.com/deepseek-ai`, `arxiv.org (deepseek)` | R1 follow-ups, language mixing behavior, RL reasoning, open-weight multilingual models | Weekly |
| **Google DeepMind** | `deepmind.google/research`, Gemini docs | Gemini reasoning, agent frameworks, multilingual capabilities, context caching | Weekly |
| **Meta FAIR** | `ai.meta.com/research`, `github.com/meta-llama` | Llama reasoning, open-weight agent capabilities, multilingual tokenizers | Weekly |
| **Alibaba (Qwen)** | `github.com/QwenLM`, `qwenlm.github.io` | Qwen multilingual, agent tool use, Chinese-English reasoning | Weekly |
| **Mistral** | `mistral.ai/news`, `github.com/mistralai` | European multilingual, function calling, agent features | Bi-weekly |
| **xAI** | `x.ai/blog` | Grok reasoning, agent capabilities | Bi-weekly |
| **Cohere** | `cohere.com/research` | Command-R, tool use, multilingual | Bi-weekly |

### Tier 2: Academic (highest rigor, delayed signal)

| Source | URL | What to track | Cadence |
|--------|-----|---------------|---------|
| **arXiv cs.CL** | `arxiv.org/list/cs.CL/recent` | Multilingual reasoning, tokenization, CoT, language mixing | Daily |
| **arXiv cs.AI** | `arxiv.org/list/cs.AI/recent` | Agent architectures, tool use, planning, memory | Daily |
| **arXiv cs.MA** | `arxiv.org/list/cs.MA/recent` | Multi-agent systems, delegation, coordination | Weekly |
| **arXiv cs.SE** | `arxiv.org/list/cs.SE/recent` | Code agents, SWE-bench results, coding benchmarks | Weekly |
| **ACL Anthology** | `aclanthology.org` | Published papers (higher signal than preprints) | Monthly |
| **Semantic Scholar** | `semanticscholar.org` | Citation tracking, related paper discovery | Weekly |
| **Hugging Face Papers** | `huggingface.co/papers` | Community-curated daily papers, trending | Daily |
| **Papers With Code** | `paperswithcode.com` | Benchmark leaderboards, SOTA tracking | Weekly |
| **Princeton NLP** | `princeton-nlp.github.io` | Danqi's group output, SWE-bench updates, tau-bench | Weekly |
| **Stanford NLP** | `nlp.stanford.edu` | HELM, agent benchmarks | Bi-weekly |
| **CMU LTI** | `lti.cs.cmu.edu` | Agent systems, multilingual NLP | Bi-weekly |
| **UW NLP** | `nlp.washington.edu` | Retrieval, context, long-form reasoning | Bi-weekly |

### Tier 3: Community & Real-Time Signal (highest speed, highest noise)

| Source | URL | What to track | Cadence |
|--------|-----|---------------|---------|
| **X / Twitter** | Search queries below | Real-time lab announcements, paper drops, hot takes, practitioner signal | Daily |
| **Hacker News** | `news.ycombinator.com` | Community reaction to new models/papers, practitioner experiences | Daily |
| **Reddit r/MachineLearning** | `reddit.com/r/MachineLearning` | Paper discussions, benchmark drama, reproducibility | Daily |
| **Reddit r/LocalLLaMA** | `reddit.com/r/LocalLLaMA` | Open-weight model experiences, multilingual observations | Weekly |
| **Reddit r/LanguageTechnology** | `reddit.com/r/LanguageTechnology` | NLP-specific discussions | Weekly |
| **GitHub Trending** | `github.com/trending` | New agent frameworks, benchmark repos, tool libraries | Weekly |
| **Alignment Forum** | `alignmentforum.org` | Safety-relevant work, instruction following | Bi-weekly |
| **LessWrong** | `lesswrong.com` | Reasoning model analysis, agent safety | Bi-weekly |
| **Interconnects (Nathan Lambert)** | `interconnects.ai` | RLHF/reasoning training analysis | Weekly |
| **The Gradient** | `thegradient.pub` | Long-form ML analysis | Bi-weekly |
| **Ahead of AI (Sebastian Raschka)** | `magazine.sebastianraschka.com` | Monthly ML roundups | Monthly |

---

## Search Queries

### X / Twitter Accounts to Monitor

**Lab accounts:**
`@AnthropicAI`, `@OpenAI`, `@deepaborin` (DeepSeek), `@GoogleDeepMind`,
`@AIatMeta`, `@MistralAI`, `@xaboratory`

**Key researchers:**
`@DanqiChen` (advisor), `@kaborpathy` (agents/wikis), `@garrytan` (agent harness),
`@hwchase17` (LangChain/agents), `@jaborim_togelius` (agent evals),
`@swaboryx` (agent benchmarks), `@SebaborRaschka` (ML education),
`@NaborLambert` (RLHF), `@AbaborMustafa` (agent harness),
`@yizhaborgyao` (ReAct, WebArena)

**Topic searches (run via last30days or agent-reach):**
```
agent orchestration language reasoning 2026
multilingual chain of thought tokens
tool use agent benchmark results 2026
agent memory context window management
LLM reasoning language mixing
prompt compression agent
agent retry recovery strategy
tokenizer fertility multilingual
```

### arXiv Search Queries

```
# Primary (run daily)
ti:"agent" AND (ti:"orchestration" OR ti:"tool use" OR ti:"language")
ti:"reasoning" AND (ti:"language" OR ti:"multilingual" OR ti:"token")
ti:"chain of thought" AND (ti:"compression" OR ti:"language" OR ti:"efficiency")

# Secondary (run weekly)
ti:"agent" AND (ti:"memory" OR ti:"context" OR ti:"planning")
ti:"tokenizer" AND (ti:"multilingual" OR ti:"efficiency" OR ti:"fairness")
ti:"agent" AND (ti:"benchmark" OR ti:"evaluation" OR ti:"safety")
ti:"agent" AND (ti:"retry" OR ti:"recovery" OR ti:"error")
ti:"prompt compression" OR ti:"context compression"
ti:"multi-agent" AND (ti:"delegation" OR ti:"coordination" OR ti:"topology")
ti:"instruction" AND (ti:"hierarchy" OR ti:"following" OR ti:"priority")
```

### Semantic Scholar / Connected Papers

For each of our 34 bibliography entries, track:
- New papers that cite them (forward references)
- Papers they share authors with (research group tracking)
- Papers with high Semantic Scholar "influential citation" score

Key seed papers for connected-papers tracking:
- DeepSeek-R1 (language mixing in reasoning)
- Li et al. 2025 (RLVR language mixing)
- EfficientXLang (cross-lingual reasoning efficiency)
- tau-bench (agent benchmark)
- Cuadron et al. 2025 (overthinking in agents)
- MemGPT (memory management)
- LLMCompiler (tool scheduling)

---

## Research Threads

Each thread maps to one or more orchestration variables. A signal is
relevant if it provides new data, mechanisms, benchmarks, or baselines
for any of these threads.

### Thread A: Agent Internal Communication (Variables 1-2)
Language choice, reasoning format, structured protocols, compression.
Key question: how should agents represent their internal state?

### Thread B: Context Management (Variables 3-5, 9)
Memory policy, context allocation, observation granularity, compaction.
Key question: how should agents manage their finite context budget?

### Thread C: Planning & Recovery (Variables 6-8)
Planning depth, retry strategy, verification cadence.
Key question: how should agents balance exploration vs. exploitation?

### Thread D: Coordination & Control (Variables 10-12)
Tool scheduling, delegation topology, instruction hierarchy.
Key question: how should agents coordinate with tools and other agents?

### Thread E: Benchmarks & Evaluation
New agent benchmarks, leaderboard changes, evaluation methodology.
Key question: are our benchmarks still the right ones?

### Thread F: Models & Providers
New model releases, API changes, pricing changes, capability shifts.
Key question: do our experimental assumptions still hold?

### Thread G: Safety & Alignment
Multilingual safety, instruction following, agent safety evaluation.
Key question: do orchestration changes introduce safety regressions?

---

## Signal Evaluation Protocol

Not everything is worth tracking. Every signal goes through this filter:

### Promotion Criteria (must meet at least one)

1. **New measurement** — quantitative data on an orchestration variable
2. **New mechanism** — explains WHY an orchestration choice matters
3. **New benchmark** — evaluation suite relevant to our variables
4. **Direct competitor** — someone studying the same or adjacent questions
5. **Baseline update** — stronger baseline we need to compare against
6. **Provider reality check** — API/pricing/model change affecting our cost model
7. **Invalidation risk** — result that could invalidate our hypothesis or design

### Rejection Criteria

- General multilingual NLP without agent connection
- Survey-only papers without new data
- Blog posts without reproducible claims
- Hype without measurements
- Work on hidden/internal CoT (we only study framework-visible messages)

### Signal Scoring

| Score | Meaning | Action |
|-------|---------|--------|
| 5 | Directly changes our experimental design | Read immediately, update proposal |
| 4 | New baseline or competitor — must cite and compare | Read within 48h, add to bibliography |
| 3 | Relevant evidence for one of our hypotheses | Read within a week, consider citing |
| 2 | Tangentially relevant, good context | File for later, don't prioritize |
| 1 | Interesting but not actionable | Note and move on |

---

## Output Schema

Every research scan produces a structured report:

```markdown
# Frontier Research Scan — YYYY-MM-DD

## Executive Summary
- X new signals found across Y sources
- Z signals scored 4+
- Key landscape changes: [list]

## High-Priority Signals (score 4-5)

### 1. [Title](url)
- **Source:** lab / arxiv / community
- **Thread:** A-G (which research thread)
- **Variable(s):** which orchestration variable(s)
- **Score:** 1-5
- **Published:** YYYY-MM-DD
- **Key finding:** 1-3 sentences
- **Impact on CoTCodec:** how this changes our project
- **Action:** read-now | cite | update-design | add-baseline | monitor
- **Cite key:** authorYYYYkeyword (if citing)

### 2. ...

## Medium-Priority Signals (score 2-3)
[Same format, briefer]

## Rejected / Low-Signal
- [Title](url) — why rejected

## Provider & Model Updates
- API changes, pricing, new models

## Benchmark Updates
- Leaderboard changes, new benchmarks

## Landscape Summary
What changed in the last [period]? What should we update?

## Recommended Updates
- memory.json changes
- directions/ updates
- bibliography additions
- design changes to discuss with Danqi
```

---

## Data Flow

```
Sources (Tier 1-3)
  → Scan (daily/weekly/monthly per source)
  → Filter (promotion/rejection criteria)
  → Score (1-5)
  → Report (structured markdown)
  → Actions:
      ├── memory.json → landscape_tracking (all scored 3+)
      ├── directions/*.md → update relevant variable docs (scored 4+)
      ├── bibliography → add new references (scored 4+ with cite action)
      ├── Danqi briefing → flag design-changing signals (scored 5)
      └── wiki log → append to wiki/log.md
```

---

## Execution

### Tools Available

| Tool | What it does | Best for |
|------|-------------|----------|
| `last30days` | Multi-platform search across Reddit, X, YouTube, HN, GitHub, web | Broad topic sweeps, community sentiment |
| `agent-reach` | Direct access to web pages, Twitter, Reddit, YouTube, GitHub | Specific URLs, lab blogs, API docs |
| Jina Reader | `curl -s "https://r.jina.ai/URL"` | Reading specific articles/papers |
| `defuddle` | `npx defuddle parse URL --markdown` | Fallback web reader |
| Semantic Scholar API | `api.semanticscholar.org` | Citation tracking, paper discovery |
| arXiv API | `export.arxiv.org/api/query` | Paper search by title/abstract |
| GitHub CLI | `gh search repos`, `gh repo view` | Trending repos, new frameworks |

### Execution Schedule

| Cadence | What | How long |
|---------|------|----------|
| **Daily** | arXiv cs.CL + cs.AI new submissions, HF Papers, X key accounts | 15-20 min |
| **Weekly** | Full Tier 1 lab scan, Tier 2 academic scan, HN/Reddit sweep | 45-60 min |
| **Bi-weekly** | Tier 2 secondary labs, Tier 3 community deep-dive | 30-45 min |
| **Monthly** | Full landscape review, bibliography audit, Danqi prep | 90 min |

### Running a Scan

1. Read `memory.json` → `landscape_tracking` for last scan date and known papers
2. Execute searches across sources (see queries above)
3. Filter and score results
4. Write report to `research/scans/YYYY-MM-DD.md`
5. Update `memory.json` with new signals
6. Update relevant `directions/*.md` files
7. Append to `wiki/log.md`

---

## Competitive Intelligence

### Groups Working on Adjacent Problems

Track these groups — if they publish on our topic, we need to know immediately.

| Group | Lead | Adjacent work | Risk level |
|-------|------|---------------|------------|
| Princeton NLP | Danqi Chen | tau-bench, SWE-bench, agent evals | Low (advisor) |
| Yizhong Wang (UW → ?) | WebArena, agent benchmarks | Medium |
| DeepSeek Research | DeepSeek-R1 language mixing | High — closest to our RQ |
| Microsoft Research (Ahuja) | EfficientXLang, cross-lingual reasoning | High — direct precursor |
| Li et al. (UPenn) | RLVR language mixing in bilingual LLMs | High — key evidence |
| Wang et al. (LMU Munich) | Language mixing patterns across 15 languages | Medium |
| Schut / Gal (Oxford) | Do LLMs think in English? | Medium |
| Jiang et al. (Microsoft) | LLMLingua prompt compression | Medium — baseline |
| Google (Cuadron et al.) | Overthinking in agentic tasks | Medium |
| Packer et al. (Berkeley) | MemGPT, agent memory | Medium |

### If Someone Scoops Us

If a paper drops that directly answers our research question:

1. **Don't panic.** Read it carefully. Our framing (routing policy over
   message types, not blanket language switching) is likely different.
2. **Identify the gap.** What didn't they test? Which variables? Which
   benchmarks? What about safety?
3. **Pivot to comparison.** "We replicate and extend X" is a valid paper.
4. **Brief Danqi within 24 hours.**

---

## Integration with my-wiki

The `language-orchestration-radar` automation in my-wiki handles Thread A
(language-specific signals). This spec covers ALL threads across ALL variables.

When this project's radar finds something, update both:
- `research/scans/YYYY-MM-DD.md` (this repo)
- `my-wiki/wiki/research/cotcodec-paper.md` (if it affects the proposal)
- `my-wiki/wiki/research/language-orchestration.md` (if it's language-specific)
