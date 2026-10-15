#!/usr/bin/env bash
# am1-memory-credit-v1 (CONFIRMATORY): build the held-out study artifact, the 347 questions of
# the confirmatory set, with the registered command (registration section 17) from the clean
# clone at the freeze commit (the prepare script refuses the held-out split unless the
# registration is frozen in the ledger with this file). Then a determinism check: the same
# command into a scratch path, digests compared, the copy deleted. Read-only afterwards.
set -Eeuo pipefail
FREEZE=9ad36b10dcbd324647e4a98c3a150f954f7123f6
R=/home/kevin/cotcodec-runs/stage0/am1-memory-credit-v1
SOURCE_JSON=/home/kevin/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json
P="$R/prepare"
cd "$R/checkout"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse HEAD)" == "${FREEZE}" ]] || { echo "checkout is not at the freeze commit"; exit 2; }
echo "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442  ${SOURCE_JSON}" \
  | sha256sum -c - | tee -a "$P/prepare.log"
echo "$(date -u +%FT%TZ) artifact at $(git rev-parse HEAD) (registered command)" | tee -a "$P/prepare.log"
set +e
uv run --locked --offline python scripts/memcredit_study_prepare.py artifact \
  --config experiments/am1/am1-memory-credit-v1.yaml --source "${SOURCE_JSON}" \
  --split-file experiments/am1/memcredit-split-v1.json --split heldout \
  --artifact "$R/study-artifact.json" --summary "$R/pools-summary.json" \
  > "$P/artifact-stdout.json" 2> "$P/artifact-stderr.txt"
rc=$?
set -e
echo "$(date -u +%FT%TZ) artifact exit ${rc}" | tee -a "$P/prepare.log"
(( rc == 0 )) || exit "${rc}"
chmod a-w "$R/study-artifact.json" "$R/pools-summary.json"
sha256sum "$R/study-artifact.json" "$R/pools-summary.json" | tee -a "$P/prepare.log"
stat -c "%s %n" "$R/study-artifact.json" | tee -a "$P/prepare.log"
mkdir -p "$P/rebuild-check"
echo "$(date -u +%FT%TZ) rebuild check (same command, scratch path)" | tee -a "$P/prepare.log"
uv run --locked --offline python scripts/memcredit_study_prepare.py artifact \
  --config experiments/am1/am1-memory-credit-v1.yaml --source "${SOURCE_JSON}" \
  --split-file experiments/am1/memcredit-split-v1.json --split heldout \
  --artifact "$P/rebuild-check/study-artifact.json" --summary "$P/rebuild-check/pools-summary.json" \
  > "$P/rebuild-check/artifact-stdout.json" 2> "$P/rebuild-check/artifact-stderr.txt"
sha256sum "$P/rebuild-check/study-artifact.json" "$P/rebuild-check/pools-summary.json" | tee -a "$P/prepare.log"
if cmp -s "$R/study-artifact.json" "$P/rebuild-check/study-artifact.json" \
  && cmp -s "$R/pools-summary.json" "$P/rebuild-check/pools-summary.json"; then
  echo "rebuild identical; scratch copy removed" | tee -a "$P/prepare.log"
  rm -f "$P/rebuild-check/study-artifact.json"
else
  echo "REBUILD DIFFERS" | tee -a "$P/prepare.log"; exit 5
fi
[[ -z "$(git status --porcelain)" ]] || { echo "checkout dirty after the build" | tee -a "$P/prepare.log"; exit 2; }
