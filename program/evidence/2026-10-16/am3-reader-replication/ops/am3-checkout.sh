#!/usr/bin/env bash
# AM3 (EXPLORATORY): a clean clone of commit $1 on the host from a git bundle copied from the
# operator's Mac ($R/bundles/am3-<short>.bundle), detached at that commit; prints the SHA-256 of
# `git archive --format=tar <commit>` so it can be compared with the Mac's.
# Usage: am3-checkout.sh <full commit id>
set -Eeuo pipefail
G="${1:?full commit id}"; SHORT=${G:0:8}
R=/home/kevin/cotcodec-runs/stage0/am3-reader-replication
B="$R/bundles/am3-${SHORT}.bundle"
if [[ -d "$R/checkout/.git" ]]; then
  cd "$R/checkout"; [[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
  git bundle verify -q "$B"
  git fetch -q "$B" "+refs/heads/*:refs/remotes/bundle/*"
else
  git clone -q --no-checkout "$B" "$R/checkout"; cd "$R/checkout"
fi
git -c advice.detachedHead=false checkout -q "$G"
[[ "$(git rev-parse HEAD)" == "$G" && -z "$(git status --porcelain)" ]] || { echo "not clean at $G"; exit 2; }
A=$(git archive --format=tar "$G" | sha256sum | cut -d" " -f1)
echo "$(date -u +%FT%TZ) clean checkout of $G (tree $(git rev-parse --short=8 "HEAD^{tree}")) from bundle $(sha256sum "$B" | cut -c1-8); git archive sha256 $A" | tee -a "$R/ops/jobs.log"
