# Open-weight reviewer

`scripts/run_open_weight_review.py` is the provider-distinct gauntlet reviewer
of program decisions D23 and D24: a cached open-weight model served offline by
vLLM v0.31.0 (the cu129 overlay of the serving probes) reads one review prompt
and answers with one JSON object that must validate against a JSON schema. The
reviewer reads proposal text only, never code, so serving it on GPUs is outside
D7's untrusted-code rule.

| File | Role |
|---|---|
| `smoke-prompt.txt`, `smoke-schema.json` | the dummy request of the lane smoke |
| `gauntlet-review-v1.schema.json` | reference schema for one gauntlet review (ten 0-10 dimensions in the criterion-bound form, caps, verdict, defects, `calibration_state: NOT_CALIBRATED`); the total and the caps are checked by the consumer |

## What one job does

1. Reads the request bundle (prompt and schema, each with its SHA-256) from the
   lane's study-artifact mount and checks it against
   `--expected-evidence-sha256`; checks the model receipt against
   `--expected-model-receipt-sha256` and spot-checks `config.json`,
   `tokenizer_config.json` and `chat_template.jinja` against it (the lane has
   already verified every file of the snapshot).
2. Builds one user turn: the prompt, then a fixed block with the schema
   (`owr-user-message-v1`), rendered with the model's own chat template
   (`enable_thinking` from `--thinking`).
3. Generates greedily (temperature 0, `--max-tokens`) one request per seed in
   one batch. Seed 42 (the first) is the review; 43 and 44 are replicates whose
   token-level agreement with it is recorded (`replicates_identical`).
4. Takes the text after the last `</think>`, parses one JSON object (bare, else
   the first fenced block, else from the first `{`; duplicate keys and NaN are
   refused) and validates it with the built-in subset validator
   (`cotcodec-json-schema-subset-v1`: a schema using any other keyword is
   refused at `pack` time, never silently ignored).
5. If that fails, one retry of seed 42 with the error appended to the prompt.
6. Writes everything to a fresh directory and `SHA256SUMS` over it.

| Output | Content |
|---|---|
| `receipt.json` | status, model id, HF revision, model receipt SHA-256, artifact root, vLLM/torch/transformers versions, GPU names, every LLM and sampling argument, prompt SHA-256, per-attempt prompt-token and output SHA-256s, finish reasons, timings, replicates, signals, file digests |
| `parsed.json` | the validated JSON (canonical, sorted keys); only when `status` is `PARSED` |
| `raw-output-attempt-<n>.txt` | the exact decoded text of attempt n (seed 42), reasoning included |
| `replicate-seed-<s>.txt` | the replicates' text |
| `user-message-attempt-<n>.txt`, `prompt.txt`, `schema.json` | what the model was given |
| `SHA256SUMS` | every file above, `receipt.json` included |

Exit codes: 0 `PARSED`, 2 bad input (`INPUT_ERROR`), 3 stopped by USR1/TERM
(`INTERRUPTED`: receipt, then the lane's `checkpoint.ready`; a review has no
resumable state, resubmit with a longer allocation), 4 `PARSE_FAILED`, 5
`ENGINE_FAILED`.

## Running a review on fal-h100-01

Everything below runs on the host from a clean clone of the commit the overlay
image was built from (`manifest` refuses any other checkout). `$R` is
`~/cotcodec-runs/stage0/open-weight-reviewer`; `$C` the clone.

```bash
cd "$C"
# 1. Pack the prompt and schema (refuses to overwrite).
uv run --locked python scripts/run_open_weight_review.py pack \
  --prompt-file <prompt.txt> --schema-file experiments/reviewer/gauntlet-review-v1.schema.json \
  --label <kebab-label> --output "$R/inputs/<kebab-label>.json"
# 2. Render the lane manifest from the overlay build receipt (refuses to overwrite).
uv run --locked python scripts/run_open_weight_review.py manifest \
  --build-receipt "$R/overlay-<sha12>/build-receipt.json" \
  --request "$R/inputs/<kebab-label>.json" \
  --model-id qwen3.6-35b-a3b --name owr-<kebab-label> \
  --run-root "$R/runs/<kebab-label>" --minutes 20 \
  --max-model-len 65536 --max-tokens 12288 --thinking on \
  --output "$R/manifests/<kebab-label>.yaml"
# 3. Submit through the lane.
uv run --locked python scripts/submit_docker_research_job.py "$R/manifests/<kebab-label>.yaml" --dry-run
uv run --locked python scripts/submit_docker_research_job.py "$R/manifests/<kebab-label>.yaml" --test-only
uv run --locked python scripts/submit_docker_research_job.py "$R/manifests/<kebab-label>.yaml"
# 4. Collect: the review is in <run-root>/<job-id>/review/.
cat "$R/runs/<kebab-label>/<job-id>/termination.env"
uv run --locked python scripts/run_open_weight_review.py verify \
  --output-dir "$R/runs/<kebab-label>/<job-id>/review"
```

`--minutes` times `--tensor-parallel-size` sets the GPU-hour cap
(`max_gpu_hours`). Slurm sends USR1 180 s (up to 240 s) before the limit, and
the lane ends the job soon after, so the work must fit in the allocation minus
4 minutes. The lane first hashes the whole snapshot (`fetch_open_model.py
verify`: 72 GB for qwen3.6-35b-a3b, 19 GB for qwen3.5-9b).

`plan` prints the resolved settings without a GPU; `doctor` checks, inside the
image, that the installed vLLM accepts every argument `run` passes:

```bash
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home <overlay-image-id> python scripts/run_open_weight_review.py doctor
```

## Building the overlay for a new commit

The image must contain the reviewer's commit: build it as the serving probes
did (`scripts/build_vllm_overlay_on_h100.sh`, cu129, from a fresh clean clone
and its discovery source archive; one idle H100 for about a minute, accounted
separately from review inference). The exact commands of the smoke build are in
the smoke evidence README.
