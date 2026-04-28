# Variable 11: Delegation Topology

**Status:** Unexplored. Connects to Kevin's Dedalus work (multi-agent orchestration). Paper 4+ candidate.

## The Variable

σ = topology ∈ {single_agent, manager_worker, peer_to_peer, hierarchical, swarm, specialist_dispatch}

How should work be distributed across agents?

## Why It Matters

AutoGen, CrewAI, and Kevin's MCP SDK at Dedalus all enable multi-agent
systems. But the choice of topology is usually made once at design time
and never varied. The research question: is there an optimal topology
for different task structures?

From ECC: the subagent orchestration pattern (iterative retrieval) is one
topology. GStack's parallel worktree agents (/batch) is another. These
represent different points in the design space.

## Conditions to Test

| Topology | Description |
|----------|-------------|
| Single agent | One agent does everything |
| Manager-worker | Manager plans, workers execute |
| Specialist dispatch | Route each subtask to a domain-specialist agent |
| Peer-to-peer | Agents negotiate and collaborate |
| Hierarchical | Tree of agents with escalation |
| Swarm | Multiple agents independently attempt, best result wins |

## Key Hypotheses

1. Single agent outperforms multi-agent on short tasks (delegation overhead)
2. Specialist dispatch outperforms generalist on multi-domain tasks
3. Swarm (best-of-N) improves success rate but multiplies cost
4. The crossover point depends on task complexity and domain breadth

## Connections

- **Context allocation** — each sub-agent gets its own context window (or shares one)
- **Language** — different agents could use different internal languages
- **Tool scheduling** — multi-agent enables natural parallelism

## Community Evidence (from Kevin's X bookmarks — 13 signals)

- **Shaw 8-subagent parallel cleanup** (16.5K bm @shawmakesmagic) — "Use this prompt:
  I want to clean up my codebase. Make a sub agent for each of the following: [8 specialists]."
  Specialist dispatch pattern with massive community validation.
- **open-agents.dev** (5.6K bm @rauchg) — Vercel's reference platform for cloud coding agents.
  "Stripe (Minions), Ramp (Inspect), Spotify (Honk), Block (Goose) are building their own
  AI software factories." Enterprise delegation topology evidence.
- **ml-intern** (5.5K bm @akseljoonas) — HuggingFace's automated research loop agent.
  "Researches papers, goes through citations, implements ideas in GPU."
  Manager-worker topology for research automation.
- **GBrain v0.11 Minions** (1.3K bm @garrytan) — "Got sick of OpenClaw's subagents timing out.
  Built a queue/jobs system based on BullMQ. Minions are 10x faster, more reliable."
  Queue-based delegation solves timeout problem.
- **DeRonin 10 social accounts** (6.4K bm) — "I run 10 social media accounts and don't write
  a single post manually." Specialist dispatch for content creation.
- **Claude Managed Agents** (50.7K bm @claudeai) — Anthropic's official multi-agent harness.
  "Everything you need to build and deploy agents at scale." The delegation API we must
  be compatible with.
