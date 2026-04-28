# Intelligence Sources — Complete Inventory

> Audited 2026-04-28. 294 X bookmarks (168 accounts), 172 X following,
> 41 installed skills, 378 wiki pages, 51 Obsidian clips, 53 linked repos/tools.
>
> Companion docs:
> - `research/bookmark-signals.md` — all 160 research signals mapped to 12 variables
> - `research/x-following-analysis.md` — full following list classified

---

## 1. Research Tools

### Primary Research Engines

| Tool | Command | Capability | Cost |
|------|---------|------------|------|
| **last30days** | `~/.cursor/skills/last30days/` | Reddit, X, YouTube, TikTok, HN, Polymarket, GitHub, Bluesky, web. Scored by real engagement. | ScrapeCreators API |
| **agent-reach** | `~/.agents/skills/agent-reach/` | 17 platforms via CLI. Twitter, Reddit, YouTube, GitHub, web, RSS. | Mostly free |
| **Jina Reader** | `curl -s "https://r.jina.ai/URL"` | Read any web page as markdown. | Free tier |
| **defuddle** | `npx defuddle parse URL --markdown` | Local web reader fallback. | Free |
| **nia-docs** | `npx nia-docs URL` | Mount docs as filesystem (`tree`, `grep`, `cat`). | Free |
| **Semantic Scholar** | `api.semanticscholar.org` | Citation tracking, paper discovery. | Free (rate limited) |
| **arXiv API** | `export.arxiv.org/api/query` | Paper search by title/abstract. | Free |
| **GitHub CLI** | `gh search repos`, `gh api` | Trending repos, issues, releases. | Free |
| **Exa** | `mcporter call 'exa.web_search_exa(...)'` | Semantic web search. | API key |
| **qmd** | `qmd search/query/get` | Local hybrid wiki search (BM25 + vector). | Free (local GGUF) |
| **fieldtheory** | `ft sync`, `ft search`, `ft classify` | X bookmark sync + search + LLM classification. | Free |
| **twitter CLI** | `twitter search/following/followers` | X search, following lists, account data. | Cookie-based |

### MCP Servers

| Server | Purpose |
|--------|---------|
| Supabase | Database for trace storage |
| Linear | Research task tracking |
| Slack | Team communication |
| Playwright | Browser automation for web scraping |
| Cursor IDE Browser | Live page inspection and testing |
| Figma | Paper figures and diagrams |
| Stripe | (available, not research-relevant) |

### Data Pipelines

| Source | Script | Items | Last sync |
|--------|--------|-------|-----------|
| X Bookmarks | `ft sync` → `raw/x-bookmarks/bookmarks.jsonl` | 294 | 2026-04-24 |
| Obsidian Clips | `scripts/sync-obsidian.sh` → `raw/obsidian/` | 51 | Manual |
| Calendar | `scripts/sync-calendar.ts` → `raw/calendar/` | 26 days | Active |
| Email | `scripts/sync-email.ts` → `raw/email/` | 4 digests | Active |
| Meetings | `scripts/sync-meetings.ts` → `raw/meetings/` | Configured | On-demand |

---

## 2. People to Track

### Tier 1: Every Post Matters (follow + bookmark + high relevance)

| Handle | Name | Bio | Bookmarks | Why |
|--------|------|-----|-----------|-----|
| `@karpathy` | Andrej Karpathy | Director of AI @ Tesla → OpenAI. LLM-Wiki originator. | 1 (99K bm) | LLM-Wiki pattern. Confusion Protocol. AutoResearch. Every observation shapes our quality bar. |
| `@garrytan` | Garry Tan | YC CEO. GStack (72K stars) + GBrain (17K pages). | 14 | Every GBrain/GStack release directly maps to our orchestration variables. |
| `@claudeai` | Claude | Anthropic's Claude. | 1 (51K bm) | Claude Managed Agents = our compatibility target. |
| `@AnthropicAI` | Anthropic | AI safety and research. | 1 (15K bm) | Project Glasswing, model releases, API changes. |
| `@rauchg` | Guillermo Rauch | Vercel CEO. | 3 | open-agents.dev, Workflow SDK, Sandboxes. Agent infrastructure at scale. |
| `@sama` | Sam Altman | OpenAI CEO. | Following | Model releases, API changes, reasoning model direction. |

### Tier 2: Weekly Check (high-signal agent/research accounts)

| Handle | Name | Bio | Signal |
|--------|------|-----|--------|
| `@shawmakesmagic` | Shaw | Eliza creator. | 8-subagent parallel orchestration (16K bm). Delegation topology. |
| `@iamfakeguru` | — | Agent infrastructure advisor. | Claude Code reverse-engineering (16K bm). Internal gates. |
| `@himanshustwts` | — | AI research x product. | Claude Code memory architecture (8K bm). Three-layer design. |
| `@om_patel5` | Om Patel | 16yo SaaS dev. | Caveman token savings benchmarks (6.5K bm). Token optimization. |
| `@akseljoonas` | Aksel | HuggingFace agent builder. | ml-intern: automated research loop (5.5K bm). |
| `@NickSpisak_` | Nick Spisak | AI Transformation Engineer. | "Second Brain" recipe (9K bm). Near-identical architecture. |
| `@sharbel` | — | Co-founder. | Karpathy agent skills (10K bm). |
| `@tom_doerr` | Tom Doerr | GitHub repos, DSPy, agents. | 6 bookmarks. Tool discovery pipeline. |
| `@mvanhorn` | — | last30days creator. | Our primary research engine (2.6K bm). |
| `@ctatedev` | Chris Tate | Vercel. agent-browser. | Browser automation infrastructure. |
| `@bcherny` | Boris Cherny | Claude Code @ Anthropic. | Following. Insider perspective on Claude Code. |
| `@trq212` | — | Claude Code @ Anthropic. MIT Media Lab. | Following. Insider perspective. |
| `@leerob` | Lee Robinson | Teaching @ Cursor, prev Vercel. | Following. Cursor/Vercel ecosystem. |
| `@steipete` | Peter Steinberger | "ClawFather". OpenClaw power user. | Following. Agent harness patterns. |
| `@DhravyaShah` | Dhravya Shah | "The memory/context guy". supermemory. | Following. Memory policy variable. |
| `@contextconor` | Conor | Hyperspell (YC F25). "Your company brain." | Following. Knowledge base competitor. |

### Tier 3: Monthly / On-Post (research-adjacent)

| Handle | Name | Bio | Signal |
|--------|------|-----|--------|
| `@demishassabis` | Demis Hassabis | DeepMind CEO. Nobel Laureate. | Following. AGI direction, model releases. |
| `@drfeifei` | Fei-Fei Li | Stanford CS Prof. StanfordHAI co-director. | Following. AI research direction. |
| `@ylecun` | Yann LeCun | NYU Prof. Meta Chief AI Scientist. | Following. Open-weight model direction. |
| `@geoffreyhinton` | Geoffrey Hinton | Deep learning pioneer. | Following. AI safety perspective. |
| `@AndrewYNg` | Andrew Ng | Coursera co-founder. Stanford. | Following. AI education, research trends. |
| `@fchollet` | Francois Chollet | Keras creator. ARC-AGI. | Following. Intelligence benchmarks. |
| `@_akhaliq` | AK | AI research paper tweets @ HuggingFace. | Following. Daily paper curation. |
| `@lilianweng` | Lilian Weng | Ex-VP AI Safety @ OpenAI. Thinking Machines Lab. | Following. Safety research. |
| `@rasbt` | Sebastian Raschka | ML/AI researcher. LLM book author. | Following. ML education, research roundups. |
| `@dair_ai` | DAIR.AI | Democratizing AI research. | Following. Research aggregation. |
| `@emollick` | Ethan Mollick | Wharton Prof. AI + innovation. | Following. AI adoption research. |
| `@addyosmani` | Addy Osmani | Google Cloud AI Director. | Following. Gemini, AI infrastructure. |
| `@LangChain` | LangChain | Agent engineering platform. | Following. Agent framework evolution. |
| `@huggingface` | Hugging Face | AI community. | Following. Open-source models, papers. |
| `@goodside` | Riley Goodside | "Screenshots of the jagged frontier." | Following. Prompt engineering signal. |
| `@_chenglou` | Cheng Lou | React, Reason, Midjourney. | Following. Design engineering intersection. |
| `@michael_chomsky` | Michael | Agent memory analysis. | 1 (754 bm). Memory policy debate. |
| `@KingBootoshi` | — | Agentic engineer. | 1 (1.1K bm). Custom ESLint anti-slop. Verification cadence. |
| `@andrewfarah` | Andrew Farah | fieldtheory creator. Density CEO. | 2. Our X bookmark sync tool. |

### Dedalus Team (10 following)

`@itsCathyDi`, `@WindsorNguyen`, `@SMLIANG0`, `@zhou963759`, `@VitusDoesThings`,
`@NickyHeC01`, `@Tsionhgk`, `@supermistyx`, `@itsaryanmahajan`, `@dedaluslabs`

### Design Engineers (31 following — Kevin's creative intersection)

`@emilkowalski` (Linear), `@joshpuckett` (Iteration Design), `@raphaelsalaja` (Warp),
`@basementstudio`, `@mrdoob` (three.js), `@evilrabbit_` (Vercel founding designer),
`@JohnPhamous` (Vercel design eng), `@raunofreiberg` (Vercel staff design eng),
`@benjitaylor` (X design lead), `@FarzaTV` (Clicky/Buildspace), `@shadcn`,
`@ayushsoni_io`, `@jakubkrehel` (Interfere), `@MengTo` (Design+Code),
`@levelsio`, `@webmaster`, `@theo` (t3), `@zachlloydtweets` (Warp founder),
and 13 more.

---

## 3. Key Signals by Orchestration Variable

### Variable 3: Memory Policy (31 signals — richest)

Top signals:
- Karpathy LLM Knowledge Bases (99K bm) — the foundational methodology
- GBrain SOUL.md, RESOLVER.md releases — production memory patterns
- himanshustwts Claude Code memory architecture — three-layer design
- NickSpisak "Second Brain" recipe — near-identical to our architecture
- michael_chomsky memory debate — "memory is harder than Garry makes it sound"
- DhravyaShah (following) — "the memory/context guy", founder of supermemory
- contextconor (following) — Hyperspell "your company brain"

### Variable 12: Instruction Hierarchy (18 signals — safety critical)

Top signals:
- Anthropic Project Glasswing (15K bm) — securing critical software
- Shaw's agent security patterns
- GStack security fixes wave
- andrej-karpathy-skills for LLM failure modes

### Variable 8: Verification Cadence (16 signals)

Top signals:
- KingBootoshi custom ESLint anti-slop (1.1K bm)
- Design system reverse-engineering (18K bm) — verification patterns
- Karpathy AutoResearch optimization (10K bm)
- NickSpisak monthly health checks
- GStack confusion protocol — ambiguity gates

### Variable 11: Delegation Topology (13 signals)

Top signals:
- Shaw 8-subagent parallel cleanup (16K bm) — specialist dispatch
- open-agents.dev (5.6K bm) — cloud coding agent reference platform
- ml-intern (5.5K bm) — automated research loop via agent
- GBrain Minions v0.11 (1.3K bm) — queue/jobs for subagents
- DeRonin 10 social media accounts delegation (6.4K bm)

### Variable 4: Context Allocation (13 signals)

Top signals:
- Claude Code autoCompact reverse-engineering (16K bm)
- Website cloner skill context management (8.5K bm)
- MCP context cost analysis (anakin, 13 bm but directly relevant)

### Variable 7: Retry/Recovery (10 signals)

Top signals:
- Claude Code reverse-engineering — 29-30% false claims rate
- Shaw 8-subagent cleanup — recovery via parallel specialists
- Vercel Workflows GA — durable execution infrastructure

### Variable 2: Reasoning Format (9 signals)

Top signals:
- Caveman token savings 65% (6.5K bm) — compressed reasoning format
- Claude Code memory architecture — structured three-layer format
- ChatGPT Images 2.0 (7K bm) — "thinking-level intelligence" in different modality

### Variable 10: Tool Scheduling (6 signals)

- GBrain Minions BullMQ queue — 10x faster, more reliable
- ml-intern parallel paper processing
- Parallel worktree agents (GStack /batch)

### Variable 6: Planning Depth (4 signals)

- GStack planning reviews — virtual CEO, Eng Manager, Designer review plans
- Karpathy Confusion Protocol — ambiguity gates before execution
- Vercel Workflows — orchestrator-as-code planning pattern

### Variable 1: Language (3 signals)

- Caveman token savings — compressed English as language condition
- Multilingual agent frameworks

---

## 4. Linked Repos & Tools (53 unique URLs)

### Agent/Research Repos

| Bookmarks | URL | What |
|-----------|-----|------|
| 26,467 | github.com/msitarzewski/agency-agents | Full AI agency setup |
| 15,374 | anthropic.com/glasswing | Project Glasswing security initiative |
| 5,623 | open-agents.dev | Vercel reference platform for cloud agents |
| 5,062 | github.com/zubair-trabzada/geo-seo-claude | GEO/SEO optimization agent |
| 4,506 | github.com/farzaa/clicky | Open-source project |
| 2,588 | github.com/thedotmack/claude-mem | Claude Code infinite memory |
| 2,196 | github.com/forrestchang/andrej-karpathy-skills | Karpathy LLM failure modes skill |
| 1,039 | shaders.com/docs/guide/mcp | Shaders MCP server |
| 653 | github.com/nowork-studio/toprank | AI agent for Google Ads + SEO |
| 496 | agent-browser.dev | Agent browser automation |
| 415 | github.com/pickle-com/glass | Invisible desktop assistant |
| 377 | github.com/sherlock-project/sherlock | Username search across 400+ networks |
| 4 | github.com/garrytan/gbrain/.../GBRAIN_SKILLPACK.md | GBrain skillpack |

### Design Engineering Resources

| Bookmarks | URL | What |
|-----------|-----|------|
| 13,923 | illustrated-manuscript.vercel.app | Pretext illuminated manuscript |
| 3,560 | jakub.kr/writing/details-that-make-interfaces-feel-better | UI micro-polish |
| 3,361 | arcoty.pe | Font pairing tool |
| 3,180 | skills.sh | Agent skills directory |
| 2,843 | github.com/Shpigford/dither | Vector dithering tool |
| 2,776 | animations.dev | Animation skill file tips |
| 2,550 | eng.basement.studio/tools/shader-lab | Shader Lab |
| 1,169 | audio.raphaelsalaja.com | Declarative web audio |
| 592 | designengineer.tools | Design engineer tool list |
| 538 | ui-skills.com | UI Skills for agents |
| 538 | desengs.com | Design engineer resources |

---

## 5. Installed Skills (41 directories)

### Research-Critical

| Skill | Use for CoTCodec |
|-------|-----------------|
| `last30days` | Multi-platform research engine — weekly frontier scans |
| `agent-reach` | 17-platform internet access — paper fetching, lab blogs |
| `cross-modal-review` | Quality gate via second model — paper review before Danqi |
| `bugs` | CTF-style adversarial audit — safety evaluation |
| `counterfactual` | Compare current vs. minimal correct — harness debugging |
| `skill-audit` | Scan transcripts for patterns — extract research insights |
| `gstack-review` | Staff engineer code review — harness quality |
| `gstack-qa` | Real browser testing — benchmark environment testing |
| `project-briefing` | Last 24h commit summary — experiment progress |
| `daily-bugfix-check` | Recent commit bug check — harness correctness |

### Paper Communication

| Skill | Use |
|-------|-----|
| `content-strategy` | Paper promotion planning |
| `social-draft` | Platform-optimized paper announcement posts |
| `kevin-voice` | Author bio, descriptions in Kevin's voice |
| `copywriting` | Abstract and introduction polish |

### Design/Visualization

| Skill | Use |
|-------|-----|
| `frontend-design` + `frontend-design-taste` | Pareto frontier visualizations, paper figures |
| `oklch-skill` | Color palette for figures |
| `gsap-scrolltrigger` + `motion-framer` | Interactive result presentations |

---

## 6. Wiki Knowledge Base (378 pages)

### Research-Critical Pages

| Page | Relevance |
|------|-----------|
| `wiki/research/cotcodec-paper.md` | The proposal mirror |
| `wiki/research/language-orchestration.md` | Compiled research brief |
| `wiki/architecture/claude-code-harness.md` | Harness patterns (hooks, rules, skills, memory) |
| `wiki/architecture/gbrain-comparison.md` | Architecture validation at scale |
| `wiki/tools/gbrain.md` | 25 skills, signal detector, RESOLVER |
| `wiki/tools/gstack.md` | 23 skills, UX behavioral foundations |
| `wiki/tools/everything-claude-code.md` | 10 ideas: compaction, instincts, verification |
| `wiki/concepts/brain-agent-loop.md` | Core methodology |
| `wiki/concepts/agent-ethos.md` | Surgeon mindset, hard limits |
| `wiki/concepts/lint-enforced-agent-guardrails.md` | Verification via lint |
| `wiki/philosophies/no-one-off-work.md` | Codification lifecycle |
| `wiki/philosophies/builder-ethos.md` | Boil the lake, search before building |
| `wiki/tools/last30days.md` | Research engine reference |
| `wiki/tools/agent-reach.md` | Internet access reference |
| `wiki/skills/cross-modal-review.md` | Quality gate pattern |

---

## 7. Usage Protocol

1. **Wiki first** — `qmd search/query` for compiled knowledge
2. **Check bookmarks** — `raw/x-bookmarks/bookmarks.jsonl` for signal Kevin already found interesting
3. **Check following** — `/tmp/x_following.json` for accounts Kevin tracks
4. **Run last30days** — live community signal across platforms
5. **Use agent-reach** — specific URLs, lab blogs, paper fetching
6. **Use Jina Reader** — reading specific articles
7. **Use Semantic Scholar** — citation tracking on key papers
8. **Use arXiv API** — new paper discovery
9. **Use GitHub CLI** — new repos, frameworks, benchmarks
10. **Aggregate** → `research/scans/YYYY-MM-DD.md`
11. **Update state** → `memory.json`, `directions/*.md`, `wiki/log.md`
