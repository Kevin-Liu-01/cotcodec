#!/usr/bin/env bash
# am5-ablated-cost-v2: a clean clone of commit $2 on the host from a git bundle copied
# from the operator's Mac ($R/bundles/am5r-<short>.bundle), detached at that commit; prints the
# SHA-256 of `git archive --format=tar <commit>` so it can be compared with the Mac's. The first
# checkout runs from the bootstrap copies am5r-mac-bundle.sh placed in $R/bootstrap; they must
# equal the commit's own copies (checked below), which section 16 pins.
# Usage: am5r-checkout.sh dev|reg <full commit id>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
G="${2:?full commit id}"; SHORT=${G:0:8}
B="$R/bundles/am5r-${SHORT}.bundle"
if [[ -d "$C/.git" ]]; then
  cd "$C"; [[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
  git bundle verify -q "$B"
  git fetch -q "$B" "+refs/heads/*:refs/remotes/bundle/*"
else
  git clone -q --no-checkout "$B" "$C"; cd "$C"
fi
git -c advice.detachedHead=false checkout -q "$G"
[[ "$(git rev-parse HEAD)" == "$G" && -z "$(git status --porcelain)" ]] || { echo "not clean at $G"; exit 2; }
# The scripts running this (a bootstrap copy, or the checkout's own) must be the commit's.
for f in am5r-checkout.sh am5r-env.sh; do
  cmp -s "$(dirname "$0")/$f" "$C/ops/am5r/$f" || { echo "$(dirname "$0")/$f differs from $G's copy" >&2; exit 2; }
done
A=$(git archive --format=tar "$G" | sha256sum | cut -d" " -f1)
log_job "clean checkout of $G (tree $(git rev-parse --short=8 "HEAD^{tree}")) from bundle $(sha256sum "$B" | cut -c1-8); git archive sha256 $A"
