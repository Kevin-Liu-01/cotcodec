#!/usr/bin/env bash
# am3-nonabstain-generality-v1: the registered labelling of one stage (first or repair) of the
# blind hand check (registration section 8), run by the operator on the Mac, in the repository at
# the registration's commit. For every chunk of the stage, in order and one at a time:
#   - a fresh, empty working directory W/<stage>-NN receives exactly two files from the host's
#     R/hand/: hand-check-instructions.txt and the chunk;
#   - the labeller is a fresh Claude agent, model claude-opus-5-5, launched there with the pinned
#     prompt (memcredit_am3g.HAND_LABELLER_PROMPT, written per chunk by hand-sample or
#     hand-merge as hand-<stage>-prompt-NN.txt), in restricted mode (file tools confined to the
#     working directory, no command-running tools, no settings or MCP servers loaded) with only
#     the Read and Write tools;
#   - its output file and its transcript go back to the host (R/hand/ and R/hand/transcripts/,
#     host only: a transcript may quote the sample), and the transcript's SHA-256 is appended to
#     R/hand/transcripts-<stage>.sha256 for the receipt.
# Nothing else is labelled: a chunk whose output is missing or malformed is left so, and the
# merge (am3g-hand-merge.sh) decides what the one repair stage covers.
# Usage: ops/am3g/am3g-hand-label-mac.sh dev|reg <commit short id> first|repair <local work dir>
set -Eeuo pipefail
MODE="${1:?mode}"; SHORT="${2:?commit short id}"; STAGE="${3:?first or repair}"; W="${4:?work dir}"
HOST=fal-h100-01
case "$MODE" in
  dev) R='cotcodec-runs/stage0/am3g-dev-dryrun' ;;
  reg) R='cotcodec-runs/stage0/am3-nonabstain-generality-v1' ;;
  *) echo "mode is dev or reg" >&2; exit 2 ;;
esac
[[ "$(git rev-parse --short=8 HEAD)" == "$SHORT" && -z "$(git status --porcelain)" ]] \
  || { echo "the repository is not clean at $SHORT" >&2; exit 2; }
[[ ! -e "$W/$STAGE" ]] || { echo "$W/$STAGE exists: each stage is labelled once" >&2; exit 2; }
mkdir -p "$W/$STAGE"
scp -q "$HOST:$R/hand/hand-manifest.json" "$W/$STAGE/manifest.json"
python3 -c "import json,sys;[print(c['chunk'],c['output']) for c in json.load(open(sys.argv[1]))[sys.argv[2]]]" \
  "$W/$STAGE/manifest.json" "$STAGE" > "$W/$STAGE/chunks.txt"
ssh "$HOST" "mkdir -p $R/hand/transcripts" < /dev/null
n=0
while read -r chunk output; do
  n=$((n + 1)); nn=$(printf '%02d' "$n")
  d="$W/$STAGE/$STAGE-$nn"; mkdir "$d"
  scp -q "$HOST:$R/hand/hand-check-instructions.txt" "$HOST:$R/hand/$chunk" "$d/" < /dev/null
  scp -q "$HOST:$R/hand/hand-$STAGE-prompt-$nn.txt" "$W/$STAGE/prompt-$nn.txt" < /dev/null
  t="$W/$STAGE/transcript-$nn.jsonl"
  (cd "$d" && claude -p --model claude-opus-5-5 --restricted --strict-mcp-config \
     --tools Read,Write --permission-mode acceptEdits --no-session-persistence \
     --output-format stream-json --verbose "$(cat "../prompt-$nn.txt")" < /dev/null > "$t" 2> "$t.stderr") \
     || echo "chunk $nn: the labeller exited non-zero" >&2
  if [[ -f "$d/$output" ]]; then scp -q "$d/$output" "$HOST:$R/hand/$output" < /dev/null; fi
  scp -q "$t" "$HOST:$R/hand/transcripts/$STAGE-$nn.jsonl" < /dev/null
  echo "$(shasum -a 256 "$t" | cut -d" " -f1)  $STAGE-$nn.jsonl" >> "$W/$STAGE/transcripts.sha256"
done < "$W/$STAGE/chunks.txt"
scp -q "$W/$STAGE/transcripts.sha256" "$HOST:$R/hand/transcripts-$STAGE.sha256"
echo "labelled $n chunks of stage $STAGE; next, on the host: am3g-hand-merge.sh $MODE $SHORT $STAGE"
