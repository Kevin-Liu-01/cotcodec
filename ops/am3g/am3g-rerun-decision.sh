#!/usr/bin/env bash
# am3-nonabstain-generality-v1: the registration's rerun rule (section 8), applied mechanically to
# one ended GPU job before extract reads it (scripts/memcredit_am3g.py rerun-decision on the
# driver's summary.json and the lane's termination.env). Prints and logs "complete", "rerun",
# "no-rerun" or "void". On "rerun" the operator submits `am3g-submit.sh ... rerun` once; extract
# then takes the rerun's job id, and the rerun's own decision is final ("rerun" again is VOID,
# V2). A held-out rerun runs before the abstention job is submitted.
# Usage: am3g-rerun-decision.sh dev|reg <commit short id> <population> <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; POP="${3:?population}"; JOB="${4:?job id}"
allowed_population "$POP"
check_checkout "$SHORT"
D="$R/rerun-decision-${POP}-${JOB}.json"
[[ ! -e "$D" ]] || { cat "$D"; exit 0; }
uv run --locked --offline python scripts/memcredit_am3g.py rerun-decision --population "$POP" \
  --job-dir "$R/runs/${POP}/${JOB}" > "$D"
cat "$D"
log_job "rerun rule ${POP} job ${JOB}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['decision'],'-',d['why'])" "$D")"
