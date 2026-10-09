#!/usr/bin/env bash
# Render the q2-action-path-v2 concurrency-ladder manifests (section 9) with the frozen
# renderer, run from the read-only export of the frozen commit on the host (the export the
# validity controls and the N = 1 acceptance stage ran from). The renderer takes the host
# run root as a parameter (decision D40), so no field is moved after rendering.
#   render_ladder.sh [N...]        (default: 8 16 24 32 40)
# Rung N: L0-fixed, the seed-43 order extended to manifest.ladder_reps(N) repetitions, both
# observation settings, N concurrent VMs, manifest.runner_cpus(N) runner CPUs (the
# renderer's default), attempt 1. A rerun under section 6.1 or the ladder's abort rule
# submits the same rendered file again as a new job (a new output path); nothing is
# re-rendered for it. EXPORT, RENDER_DIR and HOST_ROOT override the defaults for the local
# byte-identity rendering (the host root must still be the host's path).
set -euo pipefail
ROOT="${HOST_ROOT:-$HOME/cotcodec-runs/q2-action-path-v2}"
SHA=bf99a645c3782b2c59a75b6f463461b2515d0d97
E="${EXPORT:-$ROOT/src/$SHA}"
R="${RENDER_DIR:-$ROOT/manifests/rendered}"
mkdir -p "$R"
cd "$E"
rungs=("$@")
[[ ${#rungs[@]} -gt 0 ]] || rungs=(8 16 24 32 40)
for n in "${rungs[@]}"; do
  case "$n" in 8 | 16 | 24 | 32 | 40) ;; *) echo "not a rung: $n" >&2; exit 2 ;; esac
  nn="$(printf '%02d' "$n")"
  file="ladder-n$nn-seed43-a1.yaml"
  [[ -e "$R/$file" ]] && { echo "exists: $R/$file" >&2; exit 2; }
  python3 -B scripts/render_q2_action_path_manifest.py ladder --seed 43 --layer L0-fixed \
    --concurrency "$n" --source-dir "$E" --git-sha "$SHA" --host-root "$ROOT" \
    --name q2ap-v2-ladder --campaign-id "q2ap-v2-ladder-n$nn-a1" --out "$R/$file"
done
