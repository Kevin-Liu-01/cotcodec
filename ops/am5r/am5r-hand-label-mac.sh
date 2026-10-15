#!/usr/bin/env bash
# am5-ablated-cost-v2: the registered labelling of one stage (first or repair) of the
# blind hand check (registration section 8), run by the operator on the Mac, in the repository at
# the registration's commit.
#   prepare: claims the stage on the host, atomically and once (mkdir R/hand/claim-<stage>, with a
#     line in R/ops/jobs.log; a claimed stage is refused). Then, for every chunk of the stage, a
#     fresh, empty working directory W/<stage>/<stage>-NN receives exactly two files from the
#     host's R/hand/: hand-check-instructions.txt and the chunk. The pinned launch prompt
#     (memcredit_am3g.HAND_LABELLER_PROMPT, written per chunk by hand-sample or hand-merge as
#     hand-<stage>-prompt-NN.txt) goes beside the directories as prompt-NN.txt, and as
#     prompt-NN-abs.txt with its three file names made absolute paths into that chunk's directory.
#   cli (the first launch, the default): prepare; then, for every chunk in order and one at a
#     time, a fresh Claude agent, model claude-opus-5-5, launched in the chunk's directory with
#     prompt-NN.txt, in restricted mode (file tools confined to the working directory, no
#     command-running tools, no settings or MCP servers loaded) with only the Read and Write
#     tools, its stream-json transcript saved as W/<stage>/transcript-NN.jsonl; then the push. If
#     the CLI cannot start a session on chunk 01 (no tool call and no non-error result), nothing
#     else is launched, its output and the time are kept (cli-error-01.*, cli-failed-at.txt), and
#     it exits 3. A CLI push happens only inside this action.
#   push subagent <dir>: the fallback, only after that CLI failure. The operator's Claude Code
#     session has launched, per chunk and in order, a fresh subagent with model claude-opus-5-5
#     and prompt-NN-abs.txt as its whole prompt; <dir> is that session's subagents/ directory. The
#     script reads the first user message of every agent-<id>.jsonl there and counts, per chunk,
#     the transcripts whose message is the chunk's prompt (SHA-256 of the stripped text). A chunk
#     with exactly one gets that file, copied unmodified, as its transcript; the counts, the
#     agent ids and the number of files scanned go to the launch record. More than one for any
#     chunk voids the hand check (hand-merge); none leaves the chunk to the repair stage.
#   The push sends to the host (R/hand/; transcripts in R/hand/transcripts/, host only: they may
#   quote the sample) the outputs, the transcripts, their SHA-256 (transcripts-<stage>.sha256),
#   the CLI's error (labeller-<stage>-cli-error.txt) and the launch record
#   (labeller-<stage>.json: the launch, each chunk's directory, the CLI's failure time, the
#   attempts per chunk). A stage is pushed once. hand-merge audits every transcript against the
#   launch record; nothing else is labelled.
# Usage: ops/am5r/am5r-hand-label-mac.sh dev|reg <commit short id> first|repair <local work dir>
#          [cli | prepare | push subagent <session subagents dir>]
set -Eeuo pipefail
MODE="${1:?mode}"; SHORT="${2:?commit short id}"; STAGE="${3:?first or repair}"; W="${4:?work dir}"
ACT="${5:-cli}"; LAUNCH="${6:-}"; SUBAGENTS="${7:-}"
HOST=fal-h100-01
case "$MODE" in
  dev) R='cotcodec-runs/stage0/am5r-dev-dryrun' ;;
  reg) R='cotcodec-runs/stage0/am5-ablated-cost-v2' ;;
  *) echo "mode is dev or reg" >&2; exit 2 ;;
esac
[[ "$STAGE" == first || "$STAGE" == repair ]] || { echo "stage is first or repair" >&2; exit 2; }
[[ "$(git rev-parse --short=8 HEAD)" == "$SHORT" && -z "$(git status --porcelain)" ]] \
  || { echo "the repository is not clean at $SHORT" >&2; exit 2; }
S="$W/$STAGE"

prepare() {
  [[ ! -e "$S" ]] || { echo "$S exists: each stage is labelled once" >&2; exit 2; }
  ssh "$HOST" "mkdir $R/hand/claim-$STAGE && echo '$(date -u +%FT%TZ) hand stage $STAGE claimed for labelling at $SHORT' >> $R/ops/jobs.log" < /dev/null \
    || { echo "stage $STAGE is already claimed (R/hand/claim-$STAGE): it is labelled once" >&2; exit 2; }
  mkdir -p "$S"
  scp -q "$HOST:$R/hand/hand-manifest.json" "$S/manifest.json" < /dev/null
  python3 -c "import json,sys;[print(c['chunk'],c['output']) for c in json.load(open(sys.argv[1]))[sys.argv[2]]]" \
    "$S/manifest.json" "$STAGE" > "$S/chunks.txt"
  local n=0 nn d chunk output
  : > "$S/chunk-dirs.txt"
  while read -r chunk output; do
    n=$((n + 1)); nn=$(printf '%02d' "$n"); d="$S/$STAGE-$nn"; mkdir "$d"; d="$(cd "$d" && pwd)"
    echo "$nn $d" >> "$S/chunk-dirs.txt"
    scp -q "$HOST:$R/hand/hand-check-instructions.txt" "$HOST:$R/hand/$chunk" "$d/" < /dev/null
    scp -q "$HOST:$R/hand/hand-$STAGE-prompt-$nn.txt" "$S/prompt-$nn.txt" < /dev/null
    python3 - "$S/prompt-$nn.txt" "$d" hand-check-instructions.txt "$chunk" "$output" \
      > "$S/prompt-$nn-abs.txt" <<'PY'
import re, sys
text, d, names = open(sys.argv[1]).read(), sys.argv[2], sys.argv[3:]
pattern = re.compile("|".join(re.escape(n) for n in names))
sys.stdout.write(pattern.sub(lambda m: f"{d}/{m.group(0)}", text))
PY
  done < "$S/chunks.txt"
  echo "prepared $n chunks in $S" >&2
}

# 0 when the CLI ran chunk 01 (its transcript holds a tool call or a result that is not an
# error); 1 when it could not start a session there (for instance an authentication error, which
# the CLI reports as an assistant text and an error result), in which case nothing else is
# launched and its output and the time are kept for the push.
run_cli() {
  local n=0 nn d chunk output t
  while read -r chunk output; do
    n=$((n + 1)); nn=$(printf '%02d' "$n"); d="$S/$STAGE-$nn"; t="$S/transcript-$nn.jsonl"
    (cd "$d" && claude -p --model claude-opus-5-5 --restricted --strict-mcp-config \
       --tools Read,Write --permission-mode acceptEdits --no-session-persistence \
       --output-format stream-json --verbose "$(cat "../prompt-$nn.txt")" < /dev/null > "$t" \
       2> "$S/transcript-$nn.stderr") || echo "chunk $nn: the labeller exited non-zero" >&2
    if [[ "$n" == 1 ]] && ! python3 - "$t" <<'PY'
import json, sys
started = False
for line in open(sys.argv[1], errors="replace"):
    try:
        entry = json.loads(line)
    except ValueError:
        continue
    if not isinstance(entry, dict):
        continue
    if entry.get("type") == "result" and entry.get("is_error") is False:
        started = True
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_use" for b in content):
        started = True
sys.exit(0 if started else 1)
PY
    then
      date -u +%FT%TZ > "$S/cli-failed-at.txt"
      mv "$t" "$S/cli-error-01.jsonl"; mv "$S/transcript-01.stderr" "$S/cli-error-01.stderr"
      rm -f "$d/$output"
      echo "the CLI could not start a session on chunk 01 ($S/cli-error-01.*); the fallback" \
        "applies: one fresh subagent per chunk with prompt-NN-abs.txt as its whole prompt, then:" \
        "$0 $MODE $SHORT $STAGE $W push subagent <the session's subagents directory>" >&2
      return 1
    fi
  done < "$S/chunks.txt"
}

# For the subagent launch: per chunk, the transcripts in $SUBAGENTS whose first user message is
# the chunk's prompt; copies the one transcript of a chunk that has exactly one, unmodified.
find_subagents() {
  python3 - "$S" "$SUBAGENTS" <<'PY'
import glob, hashlib, json, os, shutil, sys
s, subagents = sys.argv[1], sys.argv[2]
digest = lambda text: hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
nns = [line.split()[0] for line in open(os.path.join(s, "chunk-dirs.txt")) if line.strip()]
want = {}
for nn in nns:
    for name in (f"prompt-{nn}.txt", f"prompt-{nn}-abs.txt"):
        want[digest(open(os.path.join(s, name), encoding="utf-8").read())] = nn
found = {nn: [] for nn in nns}
files = sorted(glob.glob(os.path.join(subagents, "agent-*.jsonl")))
for path in files:
    first = None
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            message = entry.get("message") if isinstance(entry, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if entry.get("type") != "user":
                continue
            if isinstance(content, list) and content and all(
                    isinstance(b, dict) and b.get("type") == "text" for b in content):
                content = "".join(str(b.get("text", "")) for b in content)
            if isinstance(content, str):
                first = content
                break
    if first is not None and digest(first) in want:
        found[want[digest(first)]].append(os.path.basename(path))
for nn, names in found.items():
    if len(names) == 1:
        src, dst = os.path.join(subagents, names[0]), os.path.join(s, f"transcript-{nn}.jsonl")
        shutil.copyfile(src, dst)
        same = hashlib.sha256(open(src, "rb").read()).digest() == \
            hashlib.sha256(open(dst, "rb").read()).digest()
        if not same:
            sys.exit(f"chunk {nn}: the copy differs from {names[0]}")
json.dump({"scanned": len(files), "found": found}, open(os.path.join(s, "subagents-found.json"), "w"),
          indent=1, sort_keys=True)
for nn, names in found.items():
    print(f"chunk {nn}: {len(names)} matching transcript(s) {' '.join(names)}", file=sys.stderr)
PY
}

push() {
  local launch="$1"
  [[ -f "$S/chunks.txt" ]] || { echo "nothing prepared in $S" >&2; exit 2; }
  if [[ "$launch" == subagent ]]; then
    [[ -f "$S/cli-error-01.stderr" && -f "$S/cli-failed-at.txt" ]] \
      || { echo "the subagent launch applies only after the CLI could not start a session" >&2; exit 2; }
    [[ -d "$SUBAGENTS" ]] || { echo "name the session's subagents/ directory" >&2; exit 2; }
    find_subagents
  fi
  ssh "$HOST" "test ! -e $R/hand/labeller-$STAGE.json" < /dev/null \
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
  python3 - "$S" "$launch" > "$S/labeller.json" <<'PY'
import json, os, sys
s, launch = sys.argv[1], sys.argv[2]
dirs = dict(line.split(None, 1) for line in open(os.path.join(s, "chunk-dirs.txt")) if line.strip())
record = {"launch": launch, "chunk_dirs": {nn: d.strip() for nn, d in dirs.items()}}
failed = os.path.join(s, "cli-failed-at.txt")
record["cli_failed_at"] = open(failed).read().strip() if os.path.exists(failed) else None
if launch == "subagent":
    found = json.load(open(os.path.join(s, "subagents-found.json")))
    record["subagent_transcripts_scanned"] = found["scanned"]
    record["matching_transcripts"] = found["found"]
    record["attempts"] = {nn: len(names) for nn, names in found["found"].items()}
    record["agents"] = {nn: names[0][len("agent-"):-len(".jsonl")]
                        for nn, names in found["found"].items() if len(names) == 1}
    record["matching_total"] = sum(record["attempts"].values())
else:
    record["attempts"] = {nn: int(os.path.exists(os.path.join(s, f"transcript-{nn}.jsonl")))
                          for nn in dirs}
json.dump(record, sys.stdout, indent=1, sort_keys=True)
PY
  if [[ -f "$S/cli-error-01.stderr" ]]; then
    cat "$S/cli-error-01.stderr" "$S/cli-error-01.jsonl" > "$S/cli-error.txt"
    scp -q "$S/cli-error.txt" "$HOST:$R/hand/labeller-$STAGE-cli-error.txt" < /dev/null
  fi
  scp -q "$S/transcripts.sha256" "$HOST:$R/hand/transcripts-$STAGE.sha256" < /dev/null
  scp -q "$S/labeller.json" "$HOST:$R/hand/labeller-$STAGE.json" < /dev/null
  echo "pushed $n chunks of stage $STAGE (launch $launch); next, on the host: am5r-hand-merge.sh $MODE $SHORT $STAGE" >&2
}

case "$ACT" in
  cli) [[ -z "$LAUNCH" ]] || { echo "the cli action takes no launch argument" >&2; exit 2; }
       prepare; run_cli || exit 3; push cli ;;
  prepare) prepare ;;
  push) [[ "$LAUNCH" == subagent ]] \
          || { echo "push is the subagent fallback only (a CLI push happens inside cli)" >&2; exit 2; }
        push subagent ;;
  *) echo "action is cli, prepare or push subagent" >&2; exit 2 ;;
esac
