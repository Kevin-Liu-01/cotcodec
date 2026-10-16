#!/usr/bin/env bash
# G3b (EXPLORATORY): a clean clone of commit $1 on the host at $R/checkout-<short>, detached at
# that commit, from a git bundle copied from the operator's Mac (AM3's ops/am3-checkout.sh, with
# G3's checkout-<short> layout). With a base short sha ($2), the bundle is incremental: the clone
# starts from $R/checkout-<base> and fetches the bundle. Prints the SHA-256 of
# `git archive --format=tar <commit>` so it can be compared with the Mac's.
# Usage: g3b-checkout.sh <full commit id> [<base short sha>]
set -Eeuo pipefail
G="${1:?full commit id}"; SHORT=${G:0:8}; BASE="${2:-}"
R=/home/kevin/cotcodec-runs/stage0/g3b-long-budget
C="$R/checkout-$SHORT"
mkdir -p "$R/ops"
[[ ! -e "$C" ]] || { echo "$C exists"; exit 2; }
if [[ -z "$BASE" ]]; then
  B="$R/bundles/g3b-${SHORT}.bundle"
  git clone -q --no-checkout "$B" "$C"; cd "$C"
  git bundle verify -q "$B"
else
  B="$R/bundles/g3b-${SHORT}-incr.bundle"
  git clone -q --no-checkout "$R/checkout-$BASE" "$C"; cd "$C"
  git bundle verify -q "$B"
  git fetch -q "$B" "+refs/heads/*:refs/remotes/bundle/*"
fi
git -c advice.detachedHead=false checkout -q "$G"
[[ "$(git rev-parse HEAD)" == "$G" && -z "$(git status --porcelain)" ]] || { echo "not clean at $G"; exit 2; }
A=$(git archive --format=tar "$G" | sha256sum | cut -d" " -f1)
echo "$(date -u +%FT%TZ) clean checkout of $G (tree $(git rev-parse --short=8 "HEAD^{tree}")) from bundle $(sha256sum "$B" | cut -c1-8); git archive sha256 $A" | tee -a "$R/ops/jobs.log"
