# Daybreak Blue capability boundary

Snapshot: 2026-09-23

Daybreak Blue is a separately approved OpenAI API access program for defensive
cybersecurity work. It is not a general research credit, a model snapshot, a
tool authorization, or an H100 entitlement.

## Current access state

Kevin reports that the account has been approved for Daybreak Blue. The exact
API capability is **not yet verified**:

- ORX experiment `4019afe4-94a4-475c-abfd-64dfcdc15e35` used its two-attempt
  cap. Run `c02e9981…` exposed a source-snapshot assumption; repaired run
  `6661f1f5…` reached OpenAI but received HTTP 401 `invalid_api_key`.
- The node is frozen. Do not run it a third time or relabel approval as a
  capability pass.
- As checked on 2026-09-23, `~/.config/cotcodec/secrets.env` exists with mode
  600 but contains no `OPENAI_API_KEY`.

### Kevin's one required setup action

In the OpenAI Platform, select the API project to which Daybreak Blue was
approved and create a new API key for that exact project. Add it locally as:

```text
OPENAI_API_KEY=<new project key>
```

in `~/.config/cotcodec/secrets.env`, keep the file at mode 600, and never paste
the key into chat, shell history, Git, experiment YAML, or an evidence receipt.
After that, create a new versioned ORX capability node rather than reusing the
frozen one. Its single bounded request must return a receipt selecting
`access_programs.cyber=daybreak_blue`; a valid standard API call is not enough.

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

For a new versioned node, first load the local secret into that shell and use a
new output path; never overwrite `capability-v1.json`:

```bash
set -a
source ~/.config/cotcodec/secrets.env
set +a
uv run --locked python scripts/run_openai_daybreak_blue_doctor.py \
  --output data/results/openai-daybreak-blue/capability-v2.json
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
