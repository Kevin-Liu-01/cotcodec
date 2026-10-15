#!/usr/bin/env bash
# AM5: on the operator's Mac. "prepare W": copy the chunk and the instructions from the host's
# $R/hand to a new work directory W outside the repository and write the pinned labeller prompt
# with W's absolute paths (prompt-01-abs.txt; am3g's HAND_LABELLER_PROMPT). The operator's Claude
# Code session then launches one fresh subagent whose whole prompt is that file, and records the
# launch time (epoch seconds) before it in W/launch-epoch.txt. "push W TRANSCRIPT AGENT_ID": audit
# the subagent's transcript (memcredit_am5.py hand-audit; text-free), copy the labels and the
# transcript to the host's $R/hand, and the audit to $R/hand-check. W and the transcript are
# deleted from the Mac after the evidence commit.
# Usage: am5-hand-label-mac.sh prepare W | push W TRANSCRIPT AGENT_ID
set -Eeuo pipefail
HOST=fal-h100-01; RR='cotcodec-runs/stage0/am5-evidence-ablated'
ACT="${1:?prepare or push}"; W="${2:?work directory}"
PY=${PY:-python3}
case "$ACT" in
  prepare)
    [[ ! -e "$W" ]] || { echo "$W exists" >&2; exit 2; }
    case "$(cd "$(dirname "$W")" && pwd)/" in "$(git rev-parse --show-toplevel)"/*) echo "W is inside the repository" >&2; exit 2;; esac
    mkdir -p "$W"
    scp -q "$HOST:$RR/hand/hand-check-instructions.txt" "$HOST:$RR/hand/hand-first-chunk-01.jsonl" \
      "$HOST:$RR/hand/hand-manifest.json" "$W/"
    "$PY" -c "import sys; sys.path.insert(0, 'scripts'); import memcredit_am3g as g; w = sys.argv[1]
print(g.hand_labeller_prompt(f'{w}/hand-first-chunk-01.jsonl', f'{w}/hand-labels-first-01.jsonl', f'{w}/hand-check-instructions.txt'), end='')" "$W" > "$W/prompt-01-abs.txt"
    shasum -a 256 "$W/hand-check-instructions.txt" "$W/hand-first-chunk-01.jsonl" | sed "s#$W/##"
    echo "prompt at $W/prompt-01-abs.txt" ;;
  push)
    T="${3:?transcript}"; A="${4:?agent id}"
    [[ -f "$W/hand-labels-first-01.jsonl" ]] || { echo "no labels in $W" >&2; exit 2; }
    "$PY" scripts/memcredit_am5.py hand-audit --manifest "$W/hand-manifest.json" \
      --chunk hand-first-chunk-01.jsonl --chunk-dir "$W" --transcript "$T" --agent-id "$A" \
      --not-before "$(cat "$W/launch-epoch.txt")" | sed "s#$HOME#~#g" > "$W/hand-audit-01.json"
    cat "$W/hand-audit-01.json"
    ssh "$HOST" "test ! -e $RR/hand/hand-labels-first-01.jsonl" || { echo "labels already pushed" >&2; exit 2; }
    scp -q "$W/hand-labels-first-01.jsonl" "$HOST:$RR/hand/"
    scp -q "$T" "$HOST:$RR/hand/transcript-first-01.jsonl"
    scp -q "$W/hand-audit-01.json" "$HOST:$RR/hand-check/" ;;
  *) echo "action is prepare or push" >&2; exit 2 ;;
esac
