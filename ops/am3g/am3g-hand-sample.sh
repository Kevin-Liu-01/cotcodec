#!/usr/bin/env bash
# am3-nonabstain-generality-v1: draw the blind hand-check sample (registration section 8). reg:
# every H1 discordant cell of OLMo-2 and Qwen3.5-9B from the held-out job, and, mixed in, every H2
# discordant cell of the three readers from the abstention job (descriptive), each with as many
# seeded concordant distractors, in one seeded order; dev: the development job's H1 cells. The
# sample, the instructions, the chunks of 60 items and their launch prompts go to $R/hand/, a
# directory of their own: the labeller never sees $R/private/, which holds the features and every
# judge label. The files are made read-only; only counts and digests are printed.
# Usage: am3g-hand-sample.sh dev <commit short id> <development job id>
#        am3g-hand-sample.sh reg <commit short id> <held-out job id> [<abstention job id>]
# (the job ids the rerun rule kept; without the abstention job id, when H2 is void, no
# abstention items are drawn).
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; JOB="${3:?job id the rerun rule kept}"; JOB_A="${4:-}"
check_checkout "$SHORT"
POP=heldout; [[ "$AM3G_MODE" == dev ]] && POP=development
ABS=()
if [[ -n "$JOB_A" ]]; then
  [[ "$AM3G_MODE" == reg ]] || { echo "the dry run has no abstention job" >&2; exit 2; }
  ABS=(--abstention-run-dir "$R/runs/abstention/${JOB_A}/am3g" --abstention-evidence "$ABS_ART"
       --abstention-features "$R/private/features-abstention.json.gz")
fi
uv run --locked --offline python scripts/memcredit_am3g.py hand-sample --population "$POP" \
  --run-dir "$R/runs/${POP}/${JOB}/am3g" --evidence "$(artifact_for "$POP")" \
  --features "$R/private/features-${POP}.json.gz" "${ABS[@]}" --hand-dir "$R/hand" \
  > "$R/hand-sample-${SHORT}.json"
chmod a-w "$R"/hand/*
cat "$R/hand-sample-${SHORT}.json"
log_job "hand-check sample at ${SHORT}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['items'],'items in',d['chunks'],'chunks, sample',d['sample_sha256'][:16],'plan',d['plan_sha256'][:16])" "$R/hand-sample-${SHORT}.json")"
