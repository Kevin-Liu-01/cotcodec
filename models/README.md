# Open-model inputs

`registry.yaml` is the source of truth for model identities used by research
contracts. A Hugging Face model is publication-eligible only when its immutable
40-character commit, license, access mode, runtime, and remote-code policy are
recorded. An Ollama tag is intentionally limited to local smoke tests.

## Acquire a model

Inspect without downloading weights:

```bash
uv run python scripts/fetch_open_model.py list
uv run python scripts/fetch_open_model.py fetch smollm2-135m --metadata-only
```

Download and hash the complete snapshot:

```bash
uv run python scripts/fetch_open_model.py fetch smollm2-135m
uv run python scripts/fetch_open_model.py verify smollm2-135m
```

The default model root is `data/models/`; receipts go to
`data/model-receipts/`. Both are untracked. Publication artifacts must copy the
receipt into the experiment evidence bundle. Set `COTCODEC_MODEL_ROOT` to
persistent cluster storage rather than node-local `/tmp`.

The fetcher downloads custom-code files but never imports or executes them.
`trust_remote_code: true` is a blocker until that exact revision has been
reviewed and vendored or allowlisted in the digest-pinned container.

## Two claims that must stay separate

- A frozen-checkpoint retrofit asks whether an attachment can add value to an
  already trained model. It is fast and useful, but pretraining may confound the
  mechanism.
- A matched from-scratch comparison asks whether the architecture itself causes
  an improvement under identical data, tokenizer, optimizer, parameters,
  FLOPs, wall-time views, and seeds.

A retrofit result must never be written up as architecture superiority. The
architecture experiment validator enforces this distinction.
