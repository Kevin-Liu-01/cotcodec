#!/usr/bin/env bash
# AM5 (exploratory, development split only): shared host paths for the operator scripts. Sourced,
# not run. Host paths are written with $HOME; every record goes under $R.
R=$HOME/cotcodec-runs/stage0/am5-evidence-ablated
C=$R/checkout
DATASET=$HOME/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json
DEV_ART=$HOME/cotcodec-runs/stage0/am1-study/runs/main/1411/study-artifact.json
ABL_ART=$R/inputs/ablated-artifact.json
ABL_SUM=$R/prepare/ablated-summary.json
mkdir -p "$R/ops"

# The checkout must be clean and at the given short commit.
check_checkout() {
  cd "$C" || exit 2
  [[ -z "$(git status --porcelain)" ]] || { echo "checkout dirty" >&2; exit 2; }
  [[ "$(git rev-parse --short=8 HEAD)" == "$1" ]] || { echo "checkout is not at $1" >&2; exit 2; }
}

# One line to ops/jobs.log and to stderr, never to stdout (scripts print only their result there).
log_job() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> "$R/ops/jobs.log"; echo "$line" >&2; }

check_image() {
  [[ "${1:-}" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "not an image id: '${1:-}'" >&2; exit 2; }
}
