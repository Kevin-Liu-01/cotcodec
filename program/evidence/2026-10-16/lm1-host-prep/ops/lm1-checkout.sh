#!/usr/bin/env bash
# LM1 host prep: a clean clone of commit $1 on the host from a git bundle copied from the
# operator's Mac ($R/bundles/lm1-<short>.bundle), detached at that commit; logs the SHA-256 of
# `git archive --format=tar <commit>` so it can be compared with the Mac's (am3g-checkout.sh).
# Usage: lm1-checkout.sh <full commit id>
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
G="${1:?full commit id}"; SHORT=${G:0:8}
B="$R/bundles/lm1-${SHORT}.bundle"
C="$R/checkout"
if [[ -d "$C/.git" ]]; then
  cd "$C"; [[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
  git bundle verify -q "$B"
  git fetch -q "$B" "+refs/heads/*:refs/remotes/bundle/*"
else
  git clone -q --no-checkout "$B" "$C"; cd "$C"
fi
git -c advice.detachedHead=false checkout -q "$G"
[[ "$(git rev-parse HEAD)" == "$G" && -z "$(git status --porcelain)" ]] || { echo "not clean at $G"; exit 2; }
A=$(git archive --format=tar "$G" | sha256sum | cut -d" " -f1)
log_job "clean checkout of $G (tree $(git rev-parse --short=8 "HEAD^{tree}")) from bundle $(sha256sum "$B" | cut -c1-8); git archive sha256 $A"
