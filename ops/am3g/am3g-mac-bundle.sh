#!/usr/bin/env bash
# am3-nonabstain-generality-v1: on the operator's Mac, in the repository: bundle the branch that
# holds commit $2, copy the bundle and the two bootstrap scripts (am3g-env.sh and
# am3g-checkout.sh, taken from that commit with `git show`) to the host, and print their SHA-256
# for comparison with section 16's pins. am3g-checkout.sh then refuses to proceed unless the
# bootstrap copies equal the checked-out ones.
# Usage: ops/am3g/am3g-mac-bundle.sh dev|reg <full commit id> [branch, default the current one]
set -Eeuo pipefail
MODE="${1:?mode}"; G="${2:?full commit id}"; BR="${3:-$(git rev-parse --abbrev-ref HEAD)}"
SHORT=${G:0:8}; HOST=fal-h100-01
case "$MODE" in
  dev) R='cotcodec-runs/stage0/am3g-dev-dryrun' ;;
  reg) R='cotcodec-runs/stage0/am3-nonabstain-generality-v1' ;;
  *) echo "mode is dev or reg" >&2; exit 2 ;;
esac
git merge-base --is-ancestor "$G" "$BR" || { echo "$G is not on $BR" >&2; exit 2; }
T=$(mktemp -d)
git bundle create "$T/am3g-${SHORT}.bundle" "$BR"
git show "$G:ops/am3g/am3g-env.sh" > "$T/am3g-env.sh"
git show "$G:ops/am3g/am3g-checkout.sh" > "$T/am3g-checkout.sh"
ssh "$HOST" "mkdir -p $R/bundles $R/bootstrap $R/ops"
scp -q "$T/am3g-${SHORT}.bundle" "$HOST:$R/bundles/"
scp -q "$T/am3g-env.sh" "$T/am3g-checkout.sh" "$HOST:$R/bootstrap/"
shasum -a 256 "$T/am3g-env.sh" "$T/am3g-checkout.sh" | sed "s#$T/##"
ssh "$HOST" "cd $R/bootstrap && sha256sum am3g-env.sh am3g-checkout.sh"
rm -rf "$T"
echo "next, on the host: bash ~/$R/bootstrap/am3g-checkout.sh $MODE $G"
