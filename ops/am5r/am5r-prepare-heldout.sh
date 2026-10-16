#!/usr/bin/env bash
# am5-ablated-cost-v2: build the held-out ablated artifact (host CPU, no model) once, before the
# freeze, so that its digest can be pinned in the config and the registration: AM1's 347 held-out
# questions, in AM1's held-out artifact's order, each with its evidence sessions removed and the
# BM25 top-8 user-turn pool built from the rest; then AM5's 63 development ablated pools,
# unchanged, as the replay control. The artifact (pool texts) stays on the host under
# $REG_ROOT/inputs/, read-only; its text-free summary (ids, digests, pool coordinates, leakage
# facts, the builder checks) goes beside it and into the dry-run evidence. No model sees it.
# Usage: am5r-prepare-heldout.sh dev <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
[[ "$AM5R_MODE" == dev ]] || { echo "the artifact is built before the freeze, in dev mode" >&2; exit 2; }
check_checkout "$SHORT"
mkdir -p "$REG_ROOT/inputs" "$R/prepare"
[[ ! -e "$HELD_ART" && ! -e "$HELD_SUM" ]] || { echo "the held-out artifact exists; it is built once" >&2; exit 2; }
uv run --locked --offline python scripts/memcredit_am5r.py prepare-heldout \
  --source "$DATASET" --split-file experiments/am1/memcredit-split-v1.json \
  --heldout-source-artifact "$AM1_HELD_ART" --control-artifact "$DEV_ART" \
  --artifact "$HELD_ART" --summary "$HELD_SUM" \
  > "$R/prepare/prepare-heldout-${SHORT}.json" 2> "$R/prepare/prepare-heldout-${SHORT}.stderr"
chmod a-w "$HELD_ART" "$HELD_SUM"
cp "$HELD_SUM" "$R/prepare/heldout-ablated-summary.json"
sed -i "s#$HOME#~#g" "$R/prepare/prepare-heldout-${SHORT}.json"
cat "$R/prepare/prepare-heldout-${SHORT}.json"
log_job "held-out ablated artifact $(sha256sum "$HELD_ART" | cut -c1-16), summary $(sha256sum "$HELD_SUM" | cut -c1-16), built at ${SHORT} (CPU)"
