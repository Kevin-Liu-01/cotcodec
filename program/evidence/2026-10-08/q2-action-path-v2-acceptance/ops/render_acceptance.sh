#!/usr/bin/env bash
# Render the q2-action-path-v2 acceptance manifests of the N = 1 stage with the frozen
# renderer, run from the read-only export of the frozen commit on the host (the same export
# the validity controls ran from). The renderer takes the host run root as a parameter
# (decision D40), so no field is moved after rendering.
#   render_acceptance.sh A5|A1|A2|A3|A6
# A5: the boot-reset campaign (21 cold boots, 20 reset-sentinel checks; infrastructure
#     validation at the frozen SHA). A1: L0-fixed, seeds 43 and 44, both settings.
# A2: H-OSW-fixed and H-GA, seed 43, both settings. A3: the 30 stress entries on L0-fixed,
# H-OSW-fixed and H-GA, seed 43, 30 repetitions per setting. A6: the canary, seed 43.
# Every campaign is attempt 1 and N = 1 (the ladder, A4 and A7 are not in this stage).
set -euo pipefail
ROOT="$HOME/cotcodec-runs/q2-action-path-v2"
SHA=bf99a645c3782b2c59a75b6f463461b2515d0d97
E="$ROOT/src/$SHA"
R="$ROOT/manifests/rendered"
mkdir -p "$R"
cd "$E"

short() {
  case "$1" in
    L0-fixed) echo l0fixed ;;
    H-OSW-fixed) echo hoswfixed ;;
    H-GA) echo hga ;;
  esac
}

render() {  # criterion seed layer file campaign
  local criterion="$1" seed="$2" layer="$3" file="$4" campaign="$5"
  local extra=()
  [[ -n "$layer" ]] && extra=(--layer "$layer")
  [[ -e "$R/$file" ]] && { echo "exists: $R/$file" >&2; exit 2; }
  python3 -B scripts/render_q2_action_path_manifest.py "$criterion" --seed "$seed" \
    "${extra[@]}" --source-dir "$E" --git-sha "$SHA" --host-root "$ROOT" \
    --name "q2ap-v2-$(tr 'A-Z' 'a-z' <<<"$criterion")" --campaign-id "$campaign" \
    --out "$R/$file" >/dev/null
  echo "$file"
}

case "${1:?A5, A1, A2, A3 or A6}" in
  A5)
    # The renderer ignores --seed for A5 (deterministic); its header comment still prints it.
    render A5 43 "" "a5-bootreset-a1.yaml" "q2ap-v2-a5-bootreset-a1"
    ;;
  A1)
    for seed in 43 44; do
      render A1 "$seed" L0-fixed "a1-l0fixed-seed$seed-a1.yaml" "q2ap-v2-a1-l0fixed-s$seed-a1"
    done
    ;;
  A2)
    for layer in H-OSW-fixed H-GA; do
      s="$(short "$layer")"
      render A2 43 "$layer" "a2-$s-seed43-a1.yaml" "q2ap-v2-a2-$s-a1"
    done
    ;;
  A3)
    for layer in L0-fixed H-OSW-fixed H-GA; do
      s="$(short "$layer")"
      render A3 43 "$layer" "a3-$s-seed43-a1.yaml" "q2ap-v2-a3-$s-a1"
    done
    ;;
  A6)
    render A6 43 "" "a6-canary-seed43-a1.yaml" "q2ap-v2-a6-canary-a1"
    ;;
  *)
    echo "unknown criterion $1" >&2
    exit 2
    ;;
esac
