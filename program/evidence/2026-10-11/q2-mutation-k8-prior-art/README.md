# q2-evaluator-mutation-v1: K8 prior-art check (2026-10-11)

K8 of `program/preregistrations/q2-evaluator-mutation-v1.md` (section 10): "Before drafting,
rerun `orx` and keyword search including citers of AgentRewardBench and ABC. If a mutation
audit of desktop CUA checkers has appeared, pivot the note to the reachability, gold
fixed-point and dependency-drift findings."

**Timing deviation.** K8 was registered for before drafting. It ran on 2026-10-11 (started
21:03Z), after the first draft of the checker-mutation note (`paper/checker-mutation-note/`,
`8899585a`), because a review of that draft found it had not run. It ran before any
publication. The confirm results README had listed it as "not run here (before drafting a
note)".

## What ran

Record: `k8-record.json` (every query, every hit's id, title and date, both citer lists, the
screen and its decisions). Raw outputs and abstracts are third-party text; they stay in the
session scratchpad and are hashed in the record.

- 12 `orx discover` calls (orx 0.2.2, which reports itself outdated against 0.2.18), 15
  results each, no date filter: 6 alphaXiv keyword, 4 alphaXiv embedding and 2 OpenAlex
  queries on mutation testing and audits of OSWorld and desktop checkers. 134 distinct hits.
- Citers from the Semantic Scholar Graph API: 110 of AgentRewardBench (arXiv 2504.08942) and
  114 of ABC (arXiv 2507.02825), 216 distinct. OpenAlex's citation graph lists 0 and 2 citers
  for the two papers, so it was used only as a cross-check.
- Every hit and citer title was read. 28 citer titles match the screen's regex. 15 items were
  shortlisted, and 22 abstracts were read (Semantic Scholar batch and the arXiv export API).
- First-version dates for five arXiv ids, from the arXiv export API: OSWorld 2404.07972
  2024-04-11, 2604.24955 2026-04-27, 2605.12673 2026-05-12, 2609.37315 2026-09-29 and
  2610.07274 2026-10-05.

## Result

**K8 does not fire.** No mutation audit of desktop computer-use-agent checkers was found, so
the note keeps its scope.

One newly found prior touches the desktop: BenchJack, "Do Androids Dream of Breaking the
Game? Systematically Auditing AI Agent Benchmarks with BenchJack" (arXiv 2605.12673,
2026-05-12). Per its abstract it drives coding agents to search 10 agent benchmarks, desktop
computing among them, for reward-hacking exploits, and reports fully patching WebArena and
OSWorld within three iterations. It audits exploitable false accepts of the evaluation
pipeline, not checker verdicts on equivalent or violating end states, and it builds no
mutants of gold end states. The note cites it.

The abstracts of two priors the note had characterized from titles only were read here:
2609.37315 audits the tools of four tool-using agent benchmarks against their advertised
contracts, and 2604.24955 (BenchGuard) audits the artifacts of scientific agent benchmarks.
Neither touches a desktop state checker.

## Coverage limits

- The newest hit in any source is dated 2026-10-08. Later posts are not covered; the
  alphaXiv index and Semantic Scholar both lag new posts.
- Citers come from Semantic Scholar only.
- Not searched in this run: OpenReview, the ACL Anthology, Google Scholar, GitHub and X.
- The shortlist was screened on abstracts, not full texts.
- An absence in these searches is not a claim that no such audit exists.
