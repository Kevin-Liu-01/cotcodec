#!/usr/bin/env bash
# am5-ablated-cost-v1: shared host paths for the operator scripts. Sourced, not run.
# Usage: source am5r-env.sh dev|reg
#   dev: the pre-freeze development dry run, ~/cotcodec-runs/stage0/am5r-dev-dryrun
#   reg: the registered run (after the freeze), ~/cotcodec-runs/stage0/am5-ablated-cost-v1
# The held-out ablated artifact is built once, before the freeze, under the registration root
# (inputs/); both modes read it from there. Host paths are written with $HOME.
case "${1:-}" in
  dev) R=$HOME/cotcodec-runs/stage0/am5r-dev-dryrun ;;
  reg) R=$HOME/cotcodec-runs/stage0/am5-ablated-cost-v1 ;;
  *) echo "mode is dev or reg" >&2; return 2 2>/dev/null || exit 2 ;;
esac
AM5R_MODE=$1
C=$R/checkout
REG_ROOT=$HOME/cotcodec-runs/stage0/am5-ablated-cost-v1
AM5_ROOT=$HOME/cotcodec-runs/stage0/am5-evidence-ablated
DATASET=$HOME/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json
# AM1's held-out study artifact (the question order and the pool-builder check; prepare only).
AM1_HELD_ART=$HOME/cotcodec-runs/stage0/am1-memory-credit-v1/study-artifact.json
# AM5's ablated development artifact and its text-free summary (the development population and
# the held-out job's replay control), its job 1487 (the replay reference), its features and its
# receipted hand labels (the dry run's comparison).
DEV_ART=$AM5_ROOT/inputs/ablated-artifact.json
DEV_SUM=$AM5_ROOT/prepare/ablated-summary.json
REF_1487=$AM5_ROOT/runs/dev-ablated/1487/am5
AM5_FEATURES=$AM5_ROOT/private/features-dev-ablated.json.gz
AM5_LABELS=$AM5_ROOT/hand/hand-labels.jsonl
HELD_ART=$REG_ROOT/inputs/heldout-ablated-artifact.json
HELD_SUM=$REG_ROOT/inputs/heldout-ablated-summary.json
mkdir -p "$R/ops"

artifact_for() {
  case "$1" in
    development) echo "$DEV_ART" ;;
    heldout) echo "$HELD_ART" ;;
    *) echo "unknown population $1" >&2; return 2 ;;
  esac
}

summary_for() {
  case "$1" in
    development) echo "$DEV_SUM" ;;
    heldout) echo "$HELD_SUM" ;;
    *) echo "unknown population $1" >&2; return 2 ;;
  esac
}

source_id_for() {
  case "$1" in
    development) echo memcredit-study-dev-ablated-pools ;;
    heldout) echo am5-ablated-cost-v1-heldout-ablated-pools ;;
  esac
}

# The GPU populations each mode may run: dev runs only the development population.
allowed_population() {
  case "$AM5R_MODE:$1" in
    dev:development|reg:heldout) return 0 ;;
    *) echo "mode $AM5R_MODE does not run population $1 on a GPU" >&2; return 2 ;;
  esac
}

# The checkout must be clean and at the given short commit.
check_checkout() {
  cd "$C" || exit 2
  [[ -z "$(git status --porcelain)" ]] || { echo "checkout dirty" >&2; exit 2; }
  [[ "$(git rev-parse --short=8 HEAD)" == "$1" ]] || { echo "checkout is not at $1" >&2; exit 2; }
}

# One line to ops/jobs.log and to stderr, never to stdout, so that a script's stdout carries only
# its own result (am5r-image.sh prints exactly the image id).
log_job() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> "$R/ops/jobs.log"; echo "$line" >&2; }

# The only accepted form of an image id.
check_image() {
  [[ "${1:-}" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "not an image id: '${1:-}'" >&2; exit 2; }
}

# The submitted build attempts of a commit (am5r-build.sh records each job id).
build_attempts() {
  if [[ -f "$R/ops/build-attempts-$1.txt" ]]; then grep -c . "$R/ops/build-attempts-$1.txt" || true
  else echo 0; fi
}

# The build root of the latest submitted attempt: the first, or the one allowed rebuild (-r2).
build_root() {
  if [[ "$(build_attempts "$1")" -ge 2 ]]; then echo "$R/overlay-build-vllm-$1-r2"
  else echo "$R/overlay-build-vllm-$1"; fi
}
