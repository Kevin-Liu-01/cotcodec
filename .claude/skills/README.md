# Vendored third-party agent skills

Provenance: [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)
at commit `1dd0fccf46fc3c9855c4a0c313a0c57fe4319883` (fetched 2026-09-01; repository license MIT; per-skill licenses as
stated in each `SKILL.md` frontmatter — MIT or Apache-2.0 for every skill vendored here).
Skills are copied verbatim into `.claude/skills/<name>/` (Claude Code project skills) and
symlinked from `.agents/skills/<name>` (open Agent Skills bridge). Do not edit in place;
re-vendor from upstream and record the new commit here.

| Skill | Use in CoTCodec |
|---|---|
| literature-review, paper-lookup, research-lookup, bgpt-paper-search, exa-search, paperzilla, paperclip | frontier scans and novelty refuters: provenance-first retrieval, line-pinned citations |
| citation-management | proposal bibliographies; pairs with the ARS deterministic citation-verification gate |
| peer-review, scholar-evaluation | judge and reviewer stages of the research gauntlet |
| experimental-design, statistical-power, statistical-analysis | Design doctor: DOE, randomization, sample-size and seed-count justification, paired statistics |
| transformers, pytorch-lightning | implementation of from-scratch and retrofit arms on the H100 node |

The CC-BY-NC-4.0 plugin [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills)
is NOT vendored (license incompatible with this MIT repository). Enable it per user via the
plugin marketplace (see `docs/research-operations.md`); its protocols are referenced, not copied,
by `.claude/rules/research-gauntlet-loop.md`.

## OpenResearch (`orx`) agent skills

Provenance: [alphaXiv/OpenResearch](https://github.com/alphaXiv/OpenResearch) tag `v0.2.2`,
commit `72c781311f7c3b5792b8a4d9e5b9e76db804e3a9` (fetched 2026-09-14; MIT). The twelve `orx-*` skills under
`agent-skills/` are copied verbatim into `.claude/skills/orx-*/` and bridged from
`.agents/skills/`. They are vendored project-scoped instead of running
`orx install-skills`, which writes into the user-global skills directory managed by the
wiki bootstrap. The same text is available at runtime via `orx skill <name>`.

| Skill | Use in CoTCodec |
|---|---|
| orx-lit-review, orx-paper | novelty refuters and frontier scans: alphaXiv/OpenAlex retrieval, full-text reads; LaTeX drafting when a result is sealed |
| orx-experiment-tree, orx-create, orx-git, orx-compute, orx-evidence | the experiment-tree ledger over the fixed run command `scripts/orx_run.py`; `local` for CPU doctors, `ssh` for slurm-manifest nodes; never `--backend slurm` |
| orx-reports, orx-figures | durable artifacts and publication figures once a pilot answers |
| orx-agent-delegation, orx-instances, orx-customize | reference only; not used by the gauntlet |
