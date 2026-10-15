#!/usr/bin/env bash
# AM5: on the operator's Mac, in the repository: bundle the branch that holds commit $1, copy the
# bundle and the bootstrap scripts (am5-env.sh, am5-checkout.sh, from that commit) to the host.
# Usage: ops/am5/am5-mac-bundle.sh <full commit id> [branch, default the current one]
set -Eeuo pipefail
G="${1:?full commit id}"; BR="${2:-$(git rev-parse --abbrev-ref HEAD)}"
SHORT=${G:0:8}; HOST=fal-h100-01; R='cotcodec-runs/stage0/am5-evidence-ablated'
git merge-base --is-ancestor "$G" "$BR" || { echo "$G is not on $BR" >&2; exit 2; }
T=$(mktemp -d)
git bundle create "$T/am5-${SHORT}.bundle" "$BR"
git show "$G:ops/am5/am5-env.sh" > "$T/am5-env.sh"
git show "$G:ops/am5/am5-checkout.sh" > "$T/am5-checkout.sh"
ssh "$HOST" "mkdir -p $R/bundles $R/bootstrap $R/ops"
scp -q "$T/am5-${SHORT}.bundle" "$HOST:$R/bundles/"
scp -q "$T/am5-env.sh" "$T/am5-checkout.sh" "$HOST:$R/bootstrap/"
rm -rf "$T"
echo "next, on the host: bash ~/$R/bootstrap/am5-checkout.sh $G"
