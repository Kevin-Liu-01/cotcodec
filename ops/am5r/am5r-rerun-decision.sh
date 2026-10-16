#!/usr/bin/env bash
# am5-ablated-cost-v2: the registration's rerun rule (section 8), applied mechanically to
# one ended GPU job before extract reads it (scripts/memcredit_am5r.py rerun-decision on the
# driver's summary.json and the lane's termination.env). Prints and logs "complete", "rerun",
# "no-rerun" or "void". On "rerun" the operator submits `am5r-submit.sh ... rerun` once; extract
# then takes the rerun's job id, and the rerun's own decision is final: for the job named in the
# population's rerun.txt a "rerun" becomes "void" (V2). am5r-submit.sh ... rerun requires this
# record to say "rerun".
# It decides once, only after the job ended (its scontrol record and termination.env exist), and
# writes the record through a temporary file, so a failed run leaves none.
# Usage: am5r-rerun-decision.sh dev|reg <commit short id> <population> <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; POP="${3:?population}"; JOB="${4:?job id}"
allowed_population "$POP"
check_checkout "$SHORT"
D="$R/rerun-decision-${POP}-${JOB}.json"
[[ ! -e "$D" ]] || { echo "job ${JOB} was decided already ($D):" >&2; cat "$D" >&2; exit 2; }
# Only an ended job is decided: its scontrol record (am5r-job-state.sh) and the lane's
# termination record must both exist.
[[ -f "$R/ops/scontrol-${JOB}.txt" && -f "$R/runs/${POP}/${JOB}/termination.env" ]] \
  || { echo "job ${JOB} has not ended (no R/ops/scontrol-${JOB}.txt or termination.env): not decided" >&2; exit 2; }
# Is JOB this population's rerun? Then a "rerun" decision is void (one rerun per population).
RR=()
for f in "$R"/manifests/"${POP}"-*.rerun.txt; do
  [[ -f "$f" && "$(tail -1 "$f")" == "$JOB" ]] && RR=(--is-rerun)
done
rm -f "$D.tmp"
uv run --locked --offline python scripts/memcredit_am5r.py rerun-decision --population "$POP" \
  --job-dir "$R/runs/${POP}/${JOB}" "${RR[@]}" > "$D.tmp"
mv "$D.tmp" "$D"
cat "$D"
log_job "rerun rule ${POP} job ${JOB}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['decision'],'-',d['why'])" "$D")"
