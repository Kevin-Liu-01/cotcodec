#!/usr/bin/env bash
# G3b (EXPLORATORY): a clean clone of commit $1 on the host from a git bundle copied from the
# operator's Mac ($R/bundles/g3b-<short>.bundle), at $R/checkout-<short>, detached at that commit
# (AM3's ops/am3-checkout.sh, with G3's checkout-<short> layout). Prints the SHA-256 of
# `git archive --format=tar <commit>` so it can be compared with the Mac's.
# Usage: g3b-checkout.sh <full commit id>
set -Eeuo pipefail
G="${1:?full commit id}"; SHORT=${G:0:8}
R=/home/kevin/cotcodec-runs/stage0/g3b-long-budget
B="$R/bundles/g3b-${SHORT}.bundle"
C="$R/checkout-$SHORT"
mkdir -p "$R/ops"
[[ ! -e "$C" ]] || { echo "$C exists"; exit 2; }
git bundle verify -q "$B"
git clone -q --no-checkout "$B" "$C"; cd "$C"
git -c advice.detachedHead=false checkout -q "$G"
[[ "$(git rev-parse HEAD)" == "$G" && -z "$(git status --porcelain)" ]] || { echo "not clean at $G"; exit 2; }
A=$(git archive --format=tar "$G" | sha256sum | cut -d" " -f1)
echo "$(date -u +%FT%TZ) clean checkout of $G (tree $(git rev-parse --short=8 "HEAD^{tree}")) from bundle $(sha256sum "$B" | cut -c1-8); git archive sha256 $A" | tee -a "$R/ops/jobs.log"
