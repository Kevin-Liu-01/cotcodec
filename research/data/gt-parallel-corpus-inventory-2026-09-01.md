# General Translation parallel-corpus inventory — 2026-09-01

Requested as the blocking input for directions 18 and 20–22. Compiled from the
`generaltranslation` GitHub organization (member read access), the public legal
documents, and the public site. No customer content was accessed and none is
quoted here.

## Governance verdict: customer translation memory is not a research input

| Source | Provision | Consequence |
|---|---|---|
| Terms of Service §3.1 (`legal/en-US/terms.md`) | Customers grant GT a right to process "Your Data" only "to: (a) provide Services to you; and (b) Process and generate artificial intelligence outputs"; §3.4 reserves all other rights to the customer | No contractual basis for research use of customer source text or translations, de-identified or not |
| Privacy policy (`legal/en-US/privacy-policy.md`) | "Research and development" and "aggregated, de-identified and/or anonymized data" appear under legitimate interests | Applies to personal data, not to the IP license over Customer Content; does not widen §3.1 |
| Internal privacy policy (`company/compliance/policies/privacy-and-data-subject-rights.md`) | "Personal data collected for translation services shall not be repurposed without additional lawful basis and notification" | A research use would need a recorded lawful basis, a DPIA, and customer notification |
| Records of Processing Activities (`company/compliance/schedules/data-processing-activities.md`) | Activity 1 purpose: "Contract performance — delivering translation services"; no research activity recorded | Research is not a registered processing purpose |
| Data classification (`company/compliance/policies/data-classification-and-handling.md`) | "Translation memory databases and linguistic assets in PlanetScale" are covered assets; customer code is Restricted | Export to a research cluster requires management approval and audit logging even if a basis existed |
| Retention schedule | Translation memories retained for agreement + 1 year in PlanetScale Postgres | Any research copy would need its own retention and purge contract |

Decision: the production translation memory (PlanetScale; `packages/db/prisma/schema/translations.prisma`
models `SourceFile`, `TranslatedFile`, `FileRevision`, `Branch`, per-project
`FileFormat`/`DataFormat` — file-level with per-entry annotations) is **excluded**
from every CoTCodec pilot. The proposals for directions 19–22 already run on
public, license-cleared corpora (NTREX-128, FLORES+, ParaDocs/ParaCrawl,
TED2020, Function Vectors); "GT data" appears only as an optional upgrade arm,
and that arm is now conditional on a company decision (RoPA entry, DPIA,
customer notice) that this repository cannot make.

## GT-owned assets that are usable

| Asset | Where | Shape | Use |
|---|---|---|---|
| GT's own site and docs, translated by GT's product | `https://generaltranslation.com/sitemap.xml`: 792 URLs = 99 pages × 8 locales (`en-US`, `en-GB`, `es`, `fr`, `zh`, `ja`, `it`, `ru`) | Marketing, pricing, legal, and documentation pages; segment-aligned by construction (same source page per locale) | A small, GT-owned, redistributable-by-GT evaluation set (thousands of segments) for translation-paired probes; not training scale |
| Documentation source | `generaltranslation/content` (public repo, no license file): `docs/en-US/` 473 MDX files, `devlog/en-US/` 54 files | English source of the translated docs; translations are rendered by GT's pipeline, not stored in the repo | Source side of the pairs above; pulling target sides requires the live site or GT's own project in `gt-cloud` (company content, not customer content) |
| Translation quality benchmark harness | `generaltranslation/benchmarks` (private): reasoning-tier reports across locales for GPT-5.5, Claude Sonnet 4.6 / Opus 4.7, Grok 4.3 effort tiers; aggregate, binary, and YiSi scores; token and latency costs | Evaluation methodology and locale set GT already trusts | Reuse the locale set and scoring for the cross-lingual recall/indexer probes' language grid |
| Supported-locale list | `generaltranslation/supported-locales` (archived → `General-Translation/gt-libraries`) | Locale codes GT serves | Language-grid enumeration for fertility/resourcedness decorrelation (direction 20) |

## What remains unknown

- Segment counts and byte volume per locale for the GT-owned docs pairs (needs a
  crawl of the 8-locale site or an export from GT's own project; both are
  company-owned content and can be done without touching customer data).
- Whether GT will record a research processing activity for de-identified
  customer translation memory. Until it does, no pilot may assume it.

## Effect on the program

Every phase-0 kill screen in directions 19–22 is unaffected. Stage 1's "General
Translation parallel data is the defining input" framing is revised: the
defining input is *parallel translation data GT can lawfully use*, which today
means public corpora plus GT-owned content, not customer translation memory.
