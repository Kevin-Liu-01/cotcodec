#!/usr/bin/env bash
# Render the q2-action-path-v2 volume campaigns A4 and A7 (section 7) at attempt 1's N* with
# the frozen renderer, run from the read-only export of the frozen commit on the host (the
# export the controls, the N = 1 stage and the ladder ran from). The renderer takes the host
# run root as a parameter (decision D40), so no field is moved after rendering.
#   render_volume.sh NSTAR A4|A7 [START END]
# NSTAR is acceptance.n_star over attempt 1's A1 campaigns and attempt 1's ladder
# (acceptance/ladder-n-star.json); manifest.py admits A4 and A7 only at 1 or a ladder rung.
# A4: L0-fixed, volume_plan.json's 1,068 sessions in its seed-43 order, both settings.
# A7: L0-fixed, G in the screenshot-plus-accessibility setting only, 360 repetitions of the
# seed-43 shuffle, 516 sessions. Both at NSTAR VMs with manifest.runner_cpus(NSTAR) runner
# CPUs (the renderer's default), attempt 1 (A7 has no other). The renderer refuses a job
# whose worst-case budget exceeds the lane's 24 h; only then is a campaign split into
# consecutive session ranges [START, END) (section 9), each rendered by its own call. A rerun
# under section 6.1 submits the same rendered file again as a new job; nothing is
# re-rendered for it. EXPORT, RENDER_DIR and HOST_ROOT override the defaults for the local
# byte-identity rendering (the host root must still be the host's path).
set -euo pipefail
ROOT="${HOST_ROOT:-$HOME/cotcodec-runs/q2-action-path-v2}"
SHA=bf99a645c3782b2c59a75b6f463461b2515d0d97
E="${EXPORT:-$ROOT/src/$SHA}"
R="${RENDER_DIR:-$ROOT/manifests/rendered}"
n="${1:?N*}"
criterion="${2:?A4 or A7}"
case "$n" in 1 | 8 | 16 | 24 | 32 | 40) ;; *) echo "not 1 or a ladder rung: $n" >&2; exit 2 ;; esac
case "$criterion" in A4 | A7) ;; *) echo "not A4 or A7: $criterion" >&2; exit 2 ;; esac
lower="$(tr 'A-Z' 'a-z' <<<"$criterion")"
nn="$(printf '%02d' "$n")"
range=()
suffix=""
if [[ $# -ge 4 ]]; then
  range=(--session-range "$3" "$4")
  suffix="-s$3-$4"
fi
file="$lower-l0fixed-seed43-n$nn$suffix-a1.yaml"
campaign="q2ap-v2-$lower-l0fixed-n$nn$suffix-a1"
mkdir -p "$R"
[[ -e "$R/$file" ]] && { echo "exists: $R/$file" >&2; exit 2; }
cd "$E"
python3 -B scripts/render_q2_action_path_manifest.py "$criterion" --seed 43 --layer L0-fixed \
  --concurrency "$n" ${range[@]+"${range[@]}"} --source-dir "$E" --git-sha "$SHA" --host-root "$ROOT" \
  --name "q2ap-v2-$lower" --campaign-id "$campaign" --out "$R/$file"
