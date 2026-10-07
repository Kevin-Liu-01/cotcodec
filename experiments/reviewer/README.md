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
6. Writes everything to a fresh directory and `SHA256SUMS` over it, asks the
   engine to shut down (bounded at 30 s, outcome in `engine_close`) and leaves
   with `os._exit`. Smoke job 617 showed why: after a complete review the
   process hung in interpreter shutdown, and because the signal handlers had
   been reset, PID 1 ignored the lane's USR1 and TERM; the job hit its time limit
   and the container outlived it. The handlers now stay installed until exit.

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
`/home/kevin/cotcodec-runs/stage0/open-weight-reviewer` (spell run roots out in
full; the lane refuses `~`); `$C` the clone.

Current build (2026-10-07): commit `37f4f2a`, image
`sha256:eda7249764e263e8b0f8ae20816206bb8279a00f602f8402f4b8fea0cce05293`,
receipt `$R/overlay-37f4f2aaf93e/build-receipt.json`, clone with a test venv
`$C=$R/wt-37f4f2aaf93e`. Its exit fix is CPU-validated as PID 1 but has not run
on a GPU (`program/evidence/2026-10-07/open-weight-reviewer-smoke/`). The
image of `f74084d` (`f760b0fe`) hangs after its review: do not use it.

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
verify`: 72 GB for qwen3.6-35b-a3b, 19 GB for qwen3.5-9b). Measured for
qwen3.5-9b, eager (smoke job 617): 15 s from container start to the workload,
52.5 s engine init, 3.6 s to generate 3 x 62 tokens. Nothing has been measured
for qwen3.6-35b-a3b; `--minutes 20` above is an estimate for a first review
(leave out `--enforce-eager` for long outputs so CUDA graphs speed decoding).

After the job leaves the queue, accept it only with `JobState=COMPLETED`,
`ExitCode=0:0`, `reason=completed` in `termination.env`, and no container left
behind: `docker ps -a --filter name=cotcodec-<job-id>` must list nothing.

`plan` prints the resolved settings without a GPU; `doctor` checks, inside the
image, that the installed vLLM accepts every argument `run` passes:

```bash
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home <overlay-image-id> python scripts/run_open_weight_review.py doctor
```

## Building the overlay for a new commit

The image must contain the reviewer's commit: build it as the serving probes
did, from a fresh clean clone that nothing else touches (a second clone runs
the tests), with one idle H100 for about a minute, accounted separately from
review inference. The commands used for overlay 629:

```bash
C="$R/checkout-<sha12>"; A=/home/kevin/cotcodec-runs/source-archives/owr-<sha12>
cd "$C" && python3 scripts/create_source_archive.py --discovery \
  --output "$A.tar.gz" --receipt "$A.receipt.json"
EX="$C/scripts/extract_discovery_source_archive.py"; BU="$C/scripts/build_vllm_overlay_on_h100.sh"
sbatch --parsable --job-name=owr-overlay --partition=research --nodes=1 --ntasks=1 \
  --gres=gpu:h100:1 --cpus-per-task=8 --mem=32G --time=00:05:00 \
  --output="$R/slurm-overlay-%j.out" \
  --export=ALL,COTCODEC_SOURCE_ARCHIVE=$A.tar.gz,COTCODEC_SOURCE_RECEIPT=$A.receipt.json,\
COTCODEC_SOURCE_EXTRACTOR=$EX,COTCODEC_SOURCE_EXTRACTOR_SHA256=$(sha256sum "$EX" | cut -d' ' -f1),\
COTCODEC_SOURCE_BUILDER_SHA256=$(sha256sum "$BU" | cut -d' ' -f1),\
COTCODEC_SOURCE_SHA256=$(sha256sum "$A.tar.gz" | cut -d' ' -f1),\
COTCODEC_GIT_SHA=$(git rev-parse HEAD),COTCODEC_GIT_TREE=$(git rev-parse 'HEAD^{tree}'),\
COTCODEC_BUILD_ROOT=$R/overlay-<sha12>,COTCODEC_VLLM_VARIANT=cu129 "$BU"
```
