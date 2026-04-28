---
name: frontier-research
version: 0.1.0
triggers: ["research scan", "frontier scan", "what's new", "latest papers", "new models", "landscape", "track research", "any new papers"]
tools: [shell, read, write]
mutating: true
---

# Frontier Research Scan

Execute a frontier research scan across labs, arxiv, and community sources.

## Contract

When invoked, this skill:
1. Reads `research/frontier-research-spec.md` for the full operational protocol
2. Reads `memory.json` → `landscape_tracking` for last scan date
3. Executes the scan protocol from `automations/frontier-research.md`
4. Writes report to `research/scans/YYYY-MM-DD.md`
5. Updates `memory.json` with new signals
6. Updates relevant `directions/*.md` files
7. Appends to `wiki/log.md`

## Quick Execution

For a quick daily check (15 min):
1. HF Papers trending
2. arXiv cs.CL + cs.AI last 24h
3. X key accounts for announcements
4. Any new model releases

For a full weekly scan (60 min):
1. All Tier 1 lab blogs
2. Full arXiv search across all queries
3. Community sweep (HN, Reddit, X)
4. Citation tracking on seed papers
5. Benchmark leaderboard check
6. Provider API/pricing check

## Anti-Patterns

- Do NOT just read paper titles — read abstracts and check for real data
- Do NOT promote blog posts without measurements
- Do NOT ignore papers that invalidate our hypotheses — those are the most important
- Do NOT skip the competitive intelligence check
- Do NOT forget to update memory.json after the scan

## Output Format

Full report in `research/scans/YYYY-MM-DD.md`.
Brief summary for Kevin: "X signals found, Y high-priority. Key: [1-2 sentence summary]."
