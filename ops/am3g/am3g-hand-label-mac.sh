#!/usr/bin/env bash
# am3-nonabstain-generality-v1: the registered labelling of one stage (first or repair) of the
# blind hand check (registration section 8), run by the operator on the Mac, in the repository at
# the registration's commit.
#   prepare: for every chunk of the stage, a fresh, empty working directory W/<stage>/<stage>-NN
#     receives exactly two files from the host's R/hand/: hand-check-instructions.txt and the
#     chunk. The pinned launch prompt (memcredit_am3g.HAND_LABELLER_PROMPT, written per chunk by
#     hand-sample or hand-merge as hand-<stage>-prompt-NN.txt) goes beside the directories as
#     prompt-NN.txt, and as prompt-NN-abs.txt with its three file names made absolute paths into
#     that chunk's directory.
#   cli (the registered launch, the default): prepare; then, for every chunk in order and one at a
#     time, a fresh Claude agent, model claude-opus-5-5, launched in the chunk's directory with
#     prompt-NN.txt, in restricted mode (file tools confined to the working directory, no
#     command-running tools, no settings or MCP servers loaded) with only the Read and Write
#     tools, its stream-json transcript saved as W/<stage>/transcript-NN.jsonl; then push.
#   push: the outputs and transcripts go back to the host (R/hand/ and R/hand/transcripts/, host
#     only: a transcript may quote the sample), with the transcripts' SHA-256 in
#     R/hand/transcripts-<stage>.sha256 and the launch used ("cli" or "subagent") in
#     R/hand/labeller-<stage>.txt, all for the receipt. A stage is pushed once.
#   The fallback, only when the CLI cannot start a session on chunk 01 (cli then stops with exit
#     3 before any other chunk, and push sends its error to R/hand/labeller-<stage>-cli-error.txt):
#     the operator's Claude Code session launches, per chunk and in order, a fresh subagent with
#     model claude-opus-5-5 and prompt-NN-abs.txt as its whole prompt, saves that subagent's
#     transcript as W/<stage>/transcript-NN.jsonl, and runs push with the launch "subagent".
# Either way, hand-merge audits every chunk's transcript (only Reads of the chunk's two input
# files and the Write of its output) and drops the rows of a chunk that fails or has none.
# Nothing else is labelled: a chunk whose output is missing or malformed is left so, and the merge
# (am3g-hand-merge.sh) decides what the one repair stage covers.
# Usage: ops/am3g/am3g-hand-label-mac.sh dev|reg <commit short id> first|repair <local work dir>
#          [cli | prepare | push cli|subagent]
set -Eeuo pipefail
MODE="${1:?mode}"; SHORT="${2:?commit short id}"; STAGE="${3:?first or repair}"; W="${4:?work dir}"
ACT="${5:-cli}"; LAUNCH="${6:-cli}"
HOST=fal-h100-01
case "$MODE" in
  dev) R='cotcodec-runs/stage0/am3g-dev-dryrun' ;;
  reg) R='cotcodec-runs/stage0/am3-nonabstain-generality-v1' ;;
  *) echo "mode is dev or reg" >&2; exit 2 ;;
esac
[[ "$STAGE" == first || "$STAGE" == repair ]] || { echo "stage is first or repair" >&2; exit 2; }
[[ "$LAUNCH" == cli || "$LAUNCH" == subagent ]] || { echo "the launch is cli or subagent" >&2; exit 2; }
[[ "$(git rev-parse --short=8 HEAD)" == "$SHORT" && -z "$(git status --porcelain)" ]] \
  || { echo "the repository is not clean at $SHORT" >&2; exit 2; }
S="$W/$STAGE"

prepare() {
  [[ ! -e "$S" ]] || { echo "$S exists: each stage is labelled once" >&2; exit 2; }
  mkdir -p "$S"
  scp -q "$HOST:$R/hand/hand-manifest.json" "$S/manifest.json" < /dev/null
  python3 -c "import json,sys;[print(c['chunk'],c['output']) for c in json.load(open(sys.argv[1]))[sys.argv[2]]]" \
    "$S/manifest.json" "$STAGE" > "$S/chunks.txt"
  local n=0 nn d chunk output
  while read -r chunk output; do
    n=$((n + 1)); nn=$(printf '%02d' "$n"); d="$S/$STAGE-$nn"; mkdir "$d"
    scp -q "$HOST:$R/hand/hand-check-instructions.txt" "$HOST:$R/hand/$chunk" "$d/" < /dev/null
    scp -q "$HOST:$R/hand/hand-$STAGE-prompt-$nn.txt" "$S/prompt-$nn.txt" < /dev/null
    python3 - "$S/prompt-$nn.txt" "$(cd "$d" && pwd)" hand-check-instructions.txt "$chunk" "$output" \
      > "$S/prompt-$nn-abs.txt" <<'PY'
import re, sys
text, d, names = open(sys.argv[1]).read(), sys.argv[2], sys.argv[3:]
pattern = re.compile("|".join(re.escape(n) for n in names))
sys.stdout.write(pattern.sub(lambda m: f"{d}/{m.group(0)}", text))
PY
  done < "$S/chunks.txt"
  echo "prepared $n chunks in $S" >&2
}

# 0 when the CLI ran chunk 01 (its transcript holds an assistant message); 1 when it could not
# start a session there, in which case nothing else is launched and its output is kept as
# cli-error-01.* for push.
run_cli() {
  local n=0 nn d chunk output t
  while read -r chunk output; do
    n=$((n + 1)); nn=$(printf '%02d' "$n"); d="$S/$STAGE-$nn"; t="$S/transcript-$nn.jsonl"
    (cd "$d" && claude -p --model claude-opus-5-5 --restricted --strict-mcp-config \
       --tools Read,Write --permission-mode acceptEdits --no-session-persistence \
       --output-format stream-json --verbose "$(cat "../prompt-$nn.txt")" < /dev/null > "$t" \
       2> "$S/transcript-$nn.stderr") || echo "chunk $nn: the labeller exited non-zero" >&2
    if [[ "$n" == 1 ]] && ! grep -q '"type": *"assistant"' "$t"; then
      mv "$t" "$S/cli-error-01.jsonl"; mv "$S/transcript-01.stderr" "$S/cli-error-01.stderr"
      rm -f "$d/$output"
      echo "the CLI could not start a session on chunk 01 ($S/cli-error-01.*); the fallback" \
        "applies: one fresh subagent per chunk with prompt-NN-abs.txt, its transcript saved as" \
        "$S/transcript-NN.jsonl, then: $0 $MODE $SHORT $STAGE $W push subagent" >&2
      return 1
    fi
  done < "$S/chunks.txt"
}

push() {
  [[ -f "$S/chunks.txt" ]] || { echo "nothing prepared in $S" >&2; exit 2; }
  ssh "$HOST" "test ! -e $R/hand/transcripts-$STAGE.sha256" < /dev/null \
    || { echo "stage $STAGE was pushed already" >&2; exit 2; }
  ssh "$HOST" "mkdir -p $R/hand/transcripts" < /dev/null
  : > "$S/transcripts.sha256"
  local n=0 nn d chunk output t
  while read -r chunk output; do
    n=$((n + 1)); nn=$(printf '%02d' "$n"); d="$S/$STAGE-$nn"; t="$S/transcript-$nn.jsonl"
    if [[ -f "$d/$output" ]]; then scp -q "$d/$output" "$HOST:$R/hand/$output" < /dev/null; fi
    if [[ -f "$t" ]]; then
      scp -q "$t" "$HOST:$R/hand/transcripts/$STAGE-$nn.jsonl" < /dev/null
      echo "$(shasum -a 256 "$t" | cut -d" " -f1)  $STAGE-$nn.jsonl" >> "$S/transcripts.sha256"
    else
      echo "chunk $nn: no transcript (the merge's audit drops its rows)" >&2
    fi
  done < "$S/chunks.txt"
  echo "$LAUNCH" > "$S/labeller.txt"
  if [[ -f "$S/cli-error-01.stderr" ]]; then
    cat "$S/cli-error-01.stderr" "$S/cli-error-01.jsonl" > "$S/cli-error.txt"
    scp -q "$S/cli-error.txt" "$HOST:$R/hand/labeller-$STAGE-cli-error.txt" < /dev/null
  fi
  scp -q "$S/labeller.txt" "$HOST:$R/hand/labeller-$STAGE.txt" < /dev/null
  scp -q "$S/transcripts.sha256" "$HOST:$R/hand/transcripts-$STAGE.sha256" < /dev/null
  echo "pushed $n chunks of stage $STAGE (launch $LAUNCH); next, on the host: am3g-hand-merge.sh $MODE $SHORT $STAGE" >&2
}

case "$ACT" in
  cli) [[ "$LAUNCH" == cli ]] || { echo "the cli action pushes with the launch cli" >&2; exit 2; }
       prepare; run_cli || exit 3; push ;;
  prepare) prepare ;;
  push) push ;;
  *) echo "action is cli, prepare or push" >&2; exit 2 ;;
esac
