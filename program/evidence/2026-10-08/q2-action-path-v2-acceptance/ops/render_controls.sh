#!/usr/bin/env bash
# Render the q2-action-path-v2 validity-control manifests with the frozen renderer, run from
# the read-only export of the frozen commit on the host. The renderer takes the host run
# root as a parameter (decision D40), so no field is moved after rendering.
#   render_controls.sh C2|C1|C3
# C2: L0-raw, seed 45 (C2's own order seed). C1: H-OSW-up and H-GA-buggy, seed 42.
# C3: the three unmutated reference runs and every scored (operator, layer) pair, seed 42.
# Every campaign is attempt 1 (validity controls have no repair attempt), N = 1.
set -euo pipefail
ROOT="$HOME/cotcodec-runs/q2-action-path-v2"
SHA=bf99a645c3782b2c59a75b6f463461b2515d0d97
E="$ROOT/src/$SHA"
R="$ROOT/manifests/rendered"
mkdir -p "$R"
cd "$E"

short() {
  case "$1" in
    L0-raw) echo l0raw ;;
    L0-fixed) echo l0fixed ;;
    H-OSW-fixed) echo hoswfixed ;;
    H-GA) echo hga ;;
    H-OSW-up) echo hoswup ;;
    H-GA-buggy) echo hgabuggy ;;
  esac
}

render() {  # criterion seed layer mutant file campaign
  local criterion="$1" seed="$2" layer="$3" mutant="$4" file="$5" campaign="$6"
  local extra=()
  [[ -n "$mutant" ]] && extra=(--mutant "$mutant")
  [[ -e "$R/$file" ]] && { echo "exists: $R/$file" >&2; exit 2; }
  python3 -B scripts/render_q2_action_path_manifest.py "$criterion" --seed "$seed" \
    --layer "$layer" "${extra[@]}" --source-dir "$E" --git-sha "$SHA" --host-root "$ROOT" \
    --name "q2ap-v2-$(tr 'A-Z' 'a-z' <<<"$criterion")" --campaign-id "$campaign" \
    --out "$R/$file" >/dev/null
  echo "$file"
}

case "${1:?C2, C1 or C3}" in
  C2)
    render C2 45 L0-raw "" "c2-l0raw-seed45-a1.yaml" "q2ap-v2-c2-l0raw-a1"
    ;;
  C1)
    for layer in H-OSW-up H-GA-buggy; do
      s="$(short "$layer")"
      render C1 42 "$layer" "" "c1-$s-seed42-a1.yaml" "q2ap-v2-c1-$s-a1"
    done
    ;;
  C3)
    for layer in L0-fixed H-OSW-fixed H-GA; do
      s="$(short "$layer")"
      render C3 42 "$layer" none "c3-ref-$s-seed42-a1.yaml" "q2ap-v2-c3-ref-$s-a1"
    done
    python3 -B - <<'PY' >"$ROOT/ops/c3-pairs.txt"
import yaml
from harness.q2.action_path import mutants as kit
ops = yaml.safe_load(open("harness/q2/action_path/mutation_operators.yaml"))
for op, layer in kit.scored_pairs(ops):
    print(op, layer)
PY
    while read -r op layer; do
      s="$(short "$layer")"
      m="$(cut -d- -f1 <<<"$op" | tr 'A-Z' 'a-z')"
      render C3 42 "$layer" "$op" "c3-$m-$s-seed42-a1.yaml" "q2ap-v2-c3-$m-$s-a1"
    done <"$ROOT/ops/c3-pairs.txt"
    ;;
  *)
    echo "unknown control $1" >&2
    exit 2
    ;;
esac
