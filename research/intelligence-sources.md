# Intelligence Sources — Full Inventory

> Everything Kevin has at his disposal for research intelligence.
> Audited 2026-04-28 from X bookmarks (294), wiki (378 pages), 41 installed skills,
> 51 Obsidian clips, and all integration tools.

---

## 1. Research Tools (What Agents Can Execute)

### Primary Research Engines

| Tool | Installed at | Capability | Cost |
|------|-------------|------------|------|
| **last30days** | `~/.cursor/skills/last30days/` | Multi-platform search: Reddit, X, YouTube, TikTok, Instagram, HN, Polymarket, GitHub, Bluesky, web. Scored by real engagement. `--agent` mode for automation. | Requires ScrapeCreators API ($) |
| **agent-reach** | `~/.agents/skills/agent-reach/` | 17 platforms via CLI. Twitter, Reddit, YouTube, GitHub, web pages, RSS. Zero config for 8 channels. | Mostly free (Jina, GitHub CLI) |
| **Jina Reader** | `curl -s "https://r.jina.ai/URL"` | Read any web page as markdown | Free tier |
| **defuddle** | `npx defuddle parse URL --markdown` | Local web reader fallback, no API | Free |
| **nia-docs** | `npx nia-docs URL` | Mount any docs site as filesystem. `tree`, `grep`, `cat` on docs. | Free |
| **Semantic Scholar API** | `api.semanticscholar.org` | Citation tracking, paper discovery, forward references | Free (rate limited) |
| **arXiv API** | `export.arxiv.org/api/query` | Paper search by title/abstract/author | Free |
| **GitHub CLI** | `gh search repos`, `gh api` | Trending repos, issues, releases, org repos | Free |
| **Exa** | `mcporter call 'exa.web_search_exa(...)'` | Semantic web search | API key required |
| **qmd** | `qmd search/query/get` | Local hybrid wiki search (BM25 + vector + reranking) | Free (local GGUF) |

### CLI Tools

| Tool | Command | Purpose |
|------|---------|---------|
| `twitter` | `twitter search "query" -n 10` | X/Twitter search (cookie-based) |
| `rdt` | `rdt search "query"` | Reddit search |
| `yt-dlp` | `yt-dlp --dump-json "URL"` | YouTube transcripts and metadata |
| `gh` | `gh search repos "query"` | GitHub repos, PRs, issues |
| `rg` | `rg "pattern"` | Ripgrep text search |
| `feedparser` | Python RSS parsing | RSS feed monitoring |

### MCP Servers Available

| Server | Tools | Purpose |
|--------|-------|---------|
| `plugin-supabase-supabase` | Database ops | Data storage for traces |
| `plugin-linear-linear` | Issue tracking | Research task management |
| `plugin-slack-slack` | Slack integration | Team communication |
| `plugin-vercel-vercel` | Deploy, env vars | If publishing artifacts |
| `plugin-figma-figma` | Figma design | Paper figures, diagrams |
| `user-playwright` | Browser automation | Web scraping, testing |
| `cursor-ide-browser` | In-IDE browser | Live page inspection |

### Data Integrations (my-wiki)

| Integration | Script | Data | Status |
|-------------|--------|------|--------|
| X Bookmarks | `scripts/sync-x-bookmarks.sh` (fieldtheory) | 294 bookmarks in `raw/x-bookmarks/bookmarks.jsonl` | Active, last sync 2026-04-24 |
| Obsidian Clips | `scripts/sync-obsidian.sh` | 51 web clips in `raw/obsidian/` | Active |
| Google Calendar | `scripts/sync-calendar.ts` | 26 day files in `raw/calendar/` | Active |
| Gmail | `scripts/sync-email.ts` | 4 digest files in `raw/email/` | Active |
| Circleback Meetings | `scripts/sync-meetings.ts` | Meeting transcripts | Configured |

---

## 2. Key People to Track (from bookmarks + wiki)

### Agent Harness & Infrastructure Builders

| Person | Handle | Why they matter | Bookmark count |
|--------|--------|-----------------|----------------|
| **Garry Tan** | `@garrytan` | GBrain (17K+ page brain), GStack (72K stars). The reference implementation for agent brain + skills architecture. Every release is directly relevant. | 14 |
| **Andrej Karpathy** | `@karpathy` | LLM-Wiki pattern (our architecture). Confusion Protocol, AutoResearch. His observations about LLM failure modes are our quality spec. | 7 (incl. derivatives) |
| **Guillermo Rauch** | `@rauchg` | Vercel CEO. Open-agents.dev, Workflow SDK, Vercel Sandboxes. Agent infrastructure at scale. | 3 |
| **Shaw (Eliza)** | `@shawmakesmagic` | Subagent orchestration patterns, code quality via parallel agents. | 1 (16K bookmarks on his post) |
| **Chris Tate** | `@ctatedev` | Vercel. agent-browser creator. CLI-to-server patterns. | 2 |
| **Harrison Chase** | `@hwchase17` | LangChain creator. "Memory is markdown" quote. Agent memory architecture. | Referenced in wiki |
| **Affaan Mustafa** | `@affaanmustafa` | Everything Claude Code (140K stars). Token optimization, hooks, continuous learning. | Via wiki |
| **Nick Spisak** | `@NickSpisak_` | "Second Brain" recipe: raw/ + wiki/ + outputs/. qmd for search. Monthly health checks. | 3 |

### Research-Adjacent Accounts

| Person | Handle | Relevance |
|--------|--------|-----------|
| **Aksel (HuggingFace)** | `@akseljoonas` | ml-intern: automated research loop agent. Papers → citations → GPU experiments. | 
| **Om Patel** | `@om_patel5` | Claude Code deep-dives, token optimization benchmarks (caveman: 65% savings), ECC coverage. |
| **iamfakeguru** | `@iamfakeguru` | Reverse-engineered Claude Code source. Internal gates, autoCompact, truncation. 1.6M views. |
| **himanshustwts** | `@himanshustwts` | Claude Code memory architecture reverse-engineering. Three-layer design. |
| **Arlan (nia-docs)** | `@arlanr` | Vault: self-improving knowledge base. 50+ integrations. nia-docs docs-as-filesystem. |
| **Michael** | `@michael_chomsky` | Agent memory analysis. Garry Tan / Harrison Chase memory debate. |
| **mvanhorn** | `@mvanhorn` | last30days v3 creator. 20K+ GitHub stars. Agent-led search engine. |
| **KingBootoshi** | `@KingBootoshi` | Custom ESLint rules for anti-slop. Lint-enforced agent guardrails. |
| **andrewfarah** | `@andrewfarah` | fieldtheory creator (our X bookmark sync tool). |

### Frontier Design Engineers (Kevin's intersection)

| Person | Handle | Relevance |
|--------|--------|-----------|
| **Emil Kowalski** | `@emilkowalski` | Linear. Animation decisions, motion design patterns. |
| **Josh Puckett** | `@joshpuckett` | Type design, interaction design. Iteration Design. |
| **basement.studio** | `@basementstudio` | Shader Lab, 3D web, creative engineering. |
| **Raphael Salaja** | `@raphaelsalaja` | Declarative web audio. Warp design engineer. |
| **Zeno Rocha** | `@zenorocha` | React Email, Resend. Open source launches. |

---

## 3. Key Signals from Bookmarks (Research-Relevant)

### Agent Architecture Signals

| Signal | Source | Impact on CoTCodec |
|--------|--------|--------------------|
| **"Memory is markdown. Skills are markdown. Brain is a git repo."** | Harrison Chase / Garry Tan | Our architecture is validated. The entire ecosystem converges on this pattern. |
| **Karpathy's Confusion Protocol** | Garry Tan implementing in GStack | Ambiguity in agent decisions = orchestration variable (planning depth, verification cadence) |
| **GBrain v0.11 Minions (queue/jobs system)** | Garry Tan | Subagent timeout problem → delegation topology variable. BullMQ-based, 10x faster. |
| **Claude Managed Agents** | @claudeai (57K likes, 50K bookmarks) | Anthropic's official agent harness. Our harness must be compatible/comparable. |
| **Open-agents.dev (Vercel)** | Guillermo Rauch | Reference platform for cloud coding agents. Stripe Minions, Ramp, Spotify. |
| **Vercel Workflows GA** | @vercel | Durable execution for agents. Retry/recovery as infrastructure. |
| **ml-intern (HuggingFace)** | @akseljoonas | Automated research loop: papers → citations → GPU experiments. Research agent pattern. |
| **Claude Code reverse-engineering** | @iamfakeguru, @himanshustwts | autoCompact at 167K tokens, 29-30% false claims, 2K-line blind spot. Internal gates revealed. |
| **Caveman token optimization: 65% savings** | @om_patel5 | Direct evidence for our reasoning format variable. Compressed English condition baseline. |
| **Shaw's 8-subagent cleanup prompt** | @shawmakesmagic (16K bookmarks) | Delegation topology: parallel specialist subagents for quality. |
| **Custom ESLint for anti-slop** | @KingBootoshi | Lint-enforced orchestration constraints. Verification cadence via tooling. |

### Methodology Signals (LLM Wiki pattern validation)

| Signal | Source | Implication |
|--------|--------|-------------|
| **Karpathy's LLM Knowledge Bases tweet** (54K likes, 99K bookmarks) | @karpathy | The foundational tweet. Our entire architecture. 99K bookmarks = massive adoption. |
| **NousResearch Hermes Agent + LLM-Wiki** | @Teknium | Packages Karpathy's pattern for Obsidian research vaults. Community validation. |
| **Nick Spisak's "Second Brain" recipe** | @NickSpisak_ (9K bookmarks) | raw/ + wiki/ + outputs/, qmd for search. Near-identical to our architecture. |
| **GBrain 17,888 pages production** | @garrytan | Scale validation. Our architecture works at 100x our current size. |
| **Michael's agent memory analysis** | @michael_chomsky | "Memory is harder than Garry makes it sound." Important counterpoint. |
| **Vault: self-improving knowledge base** | @arlanr | 50+ integrations, updates while you sleep. Competitor/inspiration. |
| **fieldtheory v3** | @andrewfarah | Our X bookmark sync tool. 294 bookmarks flowing into the research pipeline. |
| **last30days v3** | @mvanhorn (20K stars) | Our primary research engine. Agent-led search scored by real engagement. |

---

## 4. Obsidian Clips (51 sources in raw/obsidian/)

Research-relevant clips:

| Clip | Research relevance |
|------|--------------------|
| `Brin — The Universal Allowlist for Agents.md` | Agent security, supply chain |
| `Code review for the age of AI.md` | Verification cadence variable |
| `The Agent Skills Directory.md` | Skills ecosystem mapping |
| `find-skills by vercel-labsskills.md` | Skills discovery infrastructure |
| `Zero-Config Linting for Biome, ESLint, and Oxlint.md` | Lint-enforced orchestration |
| `UI Skills - A set of skills to polish interfaces built by agents.md` | Agent skill architecture |
| `Self-Promotion+Content Strategy.md` | Paper promotion when ready |
| `AI-Native Observability.md` | Agent monitoring/tracing |

---

## 5. Installed Skills (41 directories at ~/.cursor/skills/)

### Research-Relevant Skills

| Skill | Path | Use for CoTCodec |
|-------|------|-----------------|
| `last30days` | Full multi-platform research engine | Weekly frontier scans |
| `agent-reach` | 17-platform internet access | Paper fetching, API docs, lab blogs |
| `cross-modal-review` | Quality gate via second model | Paper review before Danqi |
| `skill-audit` | Scan transcripts for patterns | Extract research insights from sessions |
| `counterfactual` | Compare current vs. minimal correct | Harness debugging |
| `bugs` | CTF-style adversarial audit | Safety evaluation, injection testing |
| `gstack-review` | Staff engineer code review | Harness code quality |
| `gstack-qa` | Real browser testing | Benchmark environment testing |
| `project-briefing` | Last 24h commit summary | Daily experiment progress |
| `daily-bugfix-check` | Recent commit bug check | Harness correctness |
| `content-strategy` | Content planning | Paper promotion, X/LinkedIn posts |
| `social-draft` | Platform-optimized drafting | Paper announcement posts |
| `kevin-voice` | Write in Kevin's voice | Paper author bio, descriptions |

### Design/Viz Skills (for paper figures)

| Skill | Use |
|-------|-----|
| `frontend-design` | Pareto frontier visualizations |
| `oklch-skill` | Color palette for figures |
| `gsap-scrolltrigger` | Interactive result presentations |

---

## 6. Wiki Knowledge Base (378 pages across 18 categories)

### Categories Most Relevant to CoTCodec

| Category | Pages | Relevance |
|----------|-------|-----------|
| **Skills** | 117 | Agent orchestration patterns, harness techniques |
| **Tools** | 39 | Research tools, agent infrastructure |
| **Concepts** | 16 | Agent ethos, brain-agent loop, production safety |
| **Architecture** | 10 | Claude Code harness, GBrain comparison, agent system |
| **Philosophies** | 26 | Builder ethos, no-one-off-work, ownership |
| **Research** | 3 | CoTCodec paper, language orchestration brief |
| **People** | 88 | Contact network, collaborators |

### Key Wiki Pages for CoTCodec Research

| Page | Why |
|------|-----|
| `wiki/research/cotcodec-paper.md` | The proposal mirror |
| `wiki/research/language-orchestration.md` | Compiled research brief |
| `wiki/architecture/claude-code-harness.md` | Harness patterns to replicate |
| `wiki/architecture/gbrain-comparison.md` | Architecture validation |
| `wiki/tools/gbrain.md` | 25 skills, signal detector, RESOLVER |
| `wiki/tools/gstack.md` | 23 skills, UX behavioral foundations |
| `wiki/tools/everything-claude-code.md` | 10 ideas worth stealing |
| `wiki/concepts/brain-agent-loop.md` | Core methodology |
| `wiki/concepts/agent-ethos.md` | Surgeon mindset |
| `wiki/philosophies/no-one-off-work.md` | Codification lifecycle |
| `wiki/philosophies/builder-ethos.md` | Boil the lake, search before building |
| `wiki/tools/last30days.md` | Research engine reference |
| `wiki/tools/agent-reach.md` | Internet access reference |
| `wiki/skills/cross-modal-review.md` | Quality gate pattern |

---

## 7. Raw Sources Available

| Source | Path | Count | Status |
|--------|------|-------|--------|
| X Bookmarks | `raw/x-bookmarks/bookmarks.jsonl` | 294 entries | Synced 2026-04-24 |
| Obsidian Clips | `raw/obsidian/*.md` | 51 clips | Manually synced |
| Calendar | `raw/calendar/2026/*.md` | 26 day files | Synced |
| Email | `raw/email/*.md` | 4 digests | Synced |
| Research | `raw/research/*.tex, *.md` | 6 files | Manual |
| Career | `raw/career/resume-kevin-liu.tex` | 1 file | Manual |
| HumanX targets | `raw/humanx-*.csv` | 4 CSV files | Event data |

---

## Usage Protocol

When running frontier research scans:

1. **Search wiki first** — `qmd search/query` for compiled knowledge
2. **Check X bookmarks** — `raw/x-bookmarks/bookmarks.jsonl` for signal Kevin already found interesting
3. **Run last30days** — for the last 30 days of live community signal across platforms
4. **Use agent-reach** — for specific URLs, lab blogs, paper fetching
5. **Use Jina Reader** — for reading specific articles found via search
6. **Use Semantic Scholar** — for citation tracking on key papers
7. **Use arXiv API** — for new paper discovery
8. **Use GitHub CLI** — for new repos, frameworks, benchmarks
9. **Aggregate findings** → `research/scans/YYYY-MM-DD.md`
10. **Update state** → `memory.json`, relevant `directions/*.md`, `wiki/log.md`
