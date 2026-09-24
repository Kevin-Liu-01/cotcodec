# Daybreak Blue capability boundary

Snapshot: 2026-09-23

Daybreak Blue is a separately approved OpenAI API access program for defensive
cybersecurity work. It is not a general research credit, a model snapshot, a
tool authorization, or an H100 entitlement.

## CoTCodec policy

- Use the pinned underlying model `gpt-5.6-sol`, not the mutable
  `gpt-daybreak-blue-latest` alias, for decision-bearing runs.
- Select `access_programs.cyber=daybreak_blue` explicitly and require the
  response receipt to echo the same program. Never infer Blue from a successful
  model call.
- Use only synthetic or explicitly authorized defensive-security tasks in an
  isolated environment. Ordinary language, memory-quality, and architecture
  experiments remain on their standard provider profiles.
- Include a stable privacy-preserving `safety_identifier`; never store an API
  key, approval email, raw credential, or account token in this repository.
- Daybreak Blue does not imply Daybreak Red, Zero Data Retention, permission to
  act on external targets, or permission to bypass the repository's tool and
  human-review boundaries.

## Capability doctor

The doctor makes one bounded Responses API call with no tools or side effects.
It records the requested and returned model, requested and selected access
program, SDK and runtime versions, token counts, request/output hashes, source
commit, and four pass/fail gates. Raw response text and credentials are omitted.

```bash
uv run --locked python scripts/run_openai_daybreak_blue_doctor.py \
  --output data/results/openai-daybreak-blue/capability-v1.json
```

`DAYBREAK_BLUE_CAPABILITY_PASS` establishes only that the current API key's
project accepted this exact Blue request. A `403 access_program_not_enabled`,
an incompatible model/program error, a silent fallback to `standard`, a model
mismatch, or malformed structured output fails the capability gate.

## Research admission after a pass

A pass permits a new preregistered defensive-safety experiment contract. That
contract must freeze the authorized task set, target scope, standard-vs-Blue
comparison, provider price ceiling, tool policy, safety identifier policy,
retention assumptions, and kill rules. It must not reuse the Blue profile as an
unlabeled replacement for the standard OpenAI condition.

Official references:

- <https://developers.openai.com/api/docs/guides/daybreak>
- <https://developers.openai.com/api/docs/guides/safety-checks/cybersecurity>
- <https://developers.openai.com/api/docs/guides/safety-checks>
