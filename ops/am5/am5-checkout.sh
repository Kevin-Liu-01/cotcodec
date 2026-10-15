#!/usr/bin/env bash
# AM5: a clean clone of commit $1 on the host from the bundle the Mac copied
# ($R/bundles/am5-<short>.bundle), detached at that commit; the scripts running this must equal
# the commit's own copies.
# Usage: am5-checkout.sh <full commit id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
G="${1:?full commit id}"; SHORT=${G:0:8}
B="$R/bundles/am5-${SHORT}.bundle"
if [[ -d "$C/.git" ]]; then
  cd "$C"; [[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
  git bundle verify -q "$B"
  git fetch -q "$B" "+refs/heads/*:refs/remotes/bundle/*"
else
  git clone -q --no-checkout "$B" "$C"; cd "$C"
fi
git -c advice.detachedHead=false checkout -q "$G"
[[ "$(git rev-parse HEAD)" == "$G" && -z "$(git status --porcelain)" ]] || { echo "not clean at $G"; exit 2; }
for f in am5-checkout.sh am5-env.sh; do
  cmp -s "$(dirname "$0")/$f" "$C/ops/am5/$f" || { echo "$(dirname "$0")/$f differs from $G's copy" >&2; exit 2; }
done
log_job "clean checkout of $G (tree $(git rev-parse --short=8 "HEAD^{tree}")) from bundle $(sha256sum "$B" | cut -c1-8)"
