#!/usr/bin/env bash
# Render (frozen renderer, from the export) and relocate the C1 and C3 manifests.
set -euo pipefail
B="$HOME/cotcodec-runs/q2-action-path-v1"
SHA=a9948ee3d5093fed3ed7e948a58cf3492310140d
E="$B/src/$SHA"
R="$B/manifests/rendered"
S="$B/manifests/submitted"
cd "$E"

short() {
  case "$1" in
    L0-fixed) echo l0fixed ;;
    H-OSW-fixed) echo hoswfixed ;;
    H-GA) echo hga ;;
    H-OSW-up) echo hoswup ;;
    H-GA-buggy) echo hgabuggy ;;
  esac
}

render() {  # criterion layer mutant file campaign
  local criterion="$1" layer="$2" mutant="$3" file="$4" campaign="$5"
  local extra=()
  [[ -n "$mutant" ]] && extra=(--mutant "$mutant")
  python3 -B scripts/render_q2_action_path_manifest.py "$criterion" --seed 42 \
    --layer "$layer" "${extra[@]}" --source-dir "$E" --git-sha "$SHA" \
    --name "q2ap-$(tr 'A-Z' 'a-z' <<<"$criterion")" --campaign-id "$campaign" \
    --out "$R/$file" >/dev/null
  python3 -B "$B/ops/relocate_manifest.py" "$E" "$R/$file" "$S/$file" >/dev/null
  echo "$file"
}

for layer in H-OSW-up H-GA-buggy; do
  s="$(short "$layer")"
  render C1 "$layer" "" "c1-$s-seed42-a1.yaml" "q2ap-v1-c1-$s-a1"
done

for layer in L0-fixed H-OSW-fixed H-GA; do
  s="$(short "$layer")"
  render C3 "$layer" none "c3-ref-$s-seed42-a1.yaml" "q2ap-v1-c3-ref-$s-a1"
done

python3 -B - <<'PY' >"$B/ops/c3-pairs.txt"
import yaml
from harness.q2.action_path import mutants as kit
ops = yaml.safe_load(open("harness/q2/action_path/mutation_operators.yaml"))
for op, layer in kit.scored_pairs(ops):
    print(op, layer)
PY
while read -r op layer; do
  s="$(short "$layer")"
  m="$(cut -d- -f1 <<<"$op" | tr 'A-Z' 'a-z')"
  render C3 "$layer" "$op" "c3-$m-$s-seed42-a1.yaml" "q2ap-v1-c3-$m-$s-a1"
done <"$B/ops/c3-pairs.txt"
