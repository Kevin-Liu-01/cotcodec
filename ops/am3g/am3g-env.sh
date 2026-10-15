#!/usr/bin/env bash
# am3-nonabstain-generality-v1: shared host paths for the operator scripts. Sourced, not run.
# Usage: source am3g-env.sh dev|reg
#   dev: the pre-freeze development dry run, ~/cotcodec-runs/stage0/am3g-dev-dryrun
#   reg: the registered run (after the freeze), ~/cotcodec-runs/stage0/am3-nonabstain-generality-v1
# The abstention population's artifact is built once, before the freeze, under the registration
# root (inputs/); both modes read it from there. Host paths are written with $HOME.
case "${1:-}" in
  dev) R=$HOME/cotcodec-runs/stage0/am3g-dev-dryrun ;;
  reg) R=$HOME/cotcodec-runs/stage0/am3-nonabstain-generality-v1 ;;
  *) echo "mode is dev or reg" >&2; return 2 2>/dev/null || exit 2 ;;
esac
AM3G_MODE=$1
C=$R/checkout
REG_ROOT=$HOME/cotcodec-runs/stage0/am3-nonabstain-generality-v1
DATASET=$HOME/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json
DEV_ART=$HOME/cotcodec-runs/stage0/am1-study/runs/main/1411/study-artifact.json
HELD_ART=$HOME/cotcodec-runs/stage0/am1-memory-credit-v1/study-artifact.json
ABS_ART=$REG_ROOT/inputs/abstention-artifact.json
REF_1458=$HOME/cotcodec-runs/stage0/am1-memory-credit-v1/runs/main/1458/am1
REF_1466=$HOME/cotcodec-runs/stage0/am3-reader-replication/runs/main/1466/am3
AM3_FEATURES=$HOME/cotcodec-runs/stage0/am3-reader-replication/private-18e8f125/features.json.gz
mkdir -p "$R/ops"

artifact_for() {
  case "$1" in
    development) echo "$DEV_ART" ;;
    heldout) echo "$HELD_ART" ;;
    abstention) echo "$ABS_ART" ;;
    *) echo "unknown population $1" >&2; return 2 ;;
  esac
}

source_id_for() {
  case "$1" in
    development) echo memcredit-study-dev-pools ;;
    heldout) echo am1-memory-credit-v1-heldout-pools ;;
    abstention) echo longmemeval-s-abstention-pools ;;
  esac
}

# The GPU populations each mode may run: dev runs only the development split.
allowed_population() {
  case "$AM3G_MODE:$1" in
    dev:development|reg:heldout|reg:abstention) return 0 ;;
    *) echo "mode $AM3G_MODE does not run population $1 on a GPU" >&2; return 2 ;;
  esac
}

# The checkout must be clean and at the given short commit.
check_checkout() {
  cd "$C" || exit 2
  [[ -z "$(git status --porcelain)" ]] || { echo "checkout dirty" >&2; exit 2; }
  [[ "$(git rev-parse --short=8 HEAD)" == "$1" ]] || { echo "checkout is not at $1" >&2; exit 2; }
}

# One line to ops/jobs.log and to stderr, never to stdout, so that a script's stdout carries only
# its own result (am3g-image.sh prints exactly the image id).
log_job() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> "$R/ops/jobs.log"; echo "$line" >&2; }

# The only accepted form of an image id.
check_image() {
  [[ "${1:-}" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "not an image id: '${1:-}'" >&2; exit 2; }
}

# The submitted build attempts of a commit (am3g-build.sh records each job id).
build_attempts() {
  if [[ -f "$R/ops/build-attempts-$1.txt" ]]; then grep -c . "$R/ops/build-attempts-$1.txt" || true
  else echo 0; fi
}

# The build root of the latest submitted attempt: the first, or the one allowed rebuild (-r2).
build_root() {
  if [[ "$(build_attempts "$1")" -ge 2 ]]; then echo "$R/overlay-build-vllm-$1-r2"
  else echo "$R/overlay-build-vllm-$1"; fi
}
