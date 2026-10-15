#!/usr/bin/env bash
# am3-nonabstain-generality-v1: draw H1's blind hand-check sample (registration section 8) from the
# held-out job's features and replies (reg) or the development job's (dev): every discordant cell
# of OLMo-2 and Qwen3.5-9B with as many seeded concordant distractors, in one seeded order. The
# sample (question, type, reference answer, reply; nothing else) and the labeller's instructions
# stay on the host in $R/private, read-only; only counts and digests are printed. The isolated
# labeller then writes $R/private/hand-labels.jsonl (agent labels under D9).
# Usage: am3g-hand-sample.sh dev|reg <commit short id> <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; JOB="${3:?job id the rerun rule kept}"
check_checkout "$SHORT"
POP=heldout; [[ "$AM3G_MODE" == dev ]] && POP=development
uv run --locked --offline python scripts/memcredit_am3g.py hand-sample --population "$POP" \
  --run-dir "$R/runs/${POP}/${JOB}/am3g" --evidence "$(artifact_for "$POP")" \
  --features "$R/private/features-${POP}.json.gz" --private-dir "$R/private" \
  > "$R/hand-sample-${SHORT}.json"
chmod a-w "$R/private/hand-check-sample.jsonl" "$R/private/hand-check-instructions.txt"
cat "$R/hand-sample-${SHORT}.json"
log_job "hand-check sample at ${SHORT}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['items'],'items, sample',d['sample_sha256'][:16],'plan',d['plan_sha256'][:16])" "$R/hand-sample-${SHORT}.json")"
