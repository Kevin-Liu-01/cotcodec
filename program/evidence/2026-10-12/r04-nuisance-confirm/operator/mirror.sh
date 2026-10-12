#!/bin/sh
# usage: mirror.sh DEST  -- copy the host run directory without documents (registration section 13)
set -e
DEST="$1"; mkdir -p "$DEST"
RUN=cotcodec-runs/stage0/r04-nuisance/runs/r04-registered-v1
SRC=cotcodec-runs/stage0/r04-nuisance/src/e312e996fe7d3d032016bc1f6195cc3b7449af68
perl -e 'alarm shift; exec @ARGV' 220 rsync -a --prune-empty-dirs -e 'ssh -o BatchMode=yes' \
  --include='/plan.json' \
  --include='/items/' --include='/items/items.jsonl' --include='/items/items.report.json' --include='/items/receipt-*.json' \
  --include='/rounds/' --include='/rounds/pending.json' --include='/rounds/only.txt' \
  --include='/*/' --include='/*/saves/' --include='/*/saves/*/' --include='/*/saves/*/receipt-*.json' \
  --include='/*/scores/' --include='/*/scores/*/' --include='/*/scores/*/receipt-*.json' --include='/*/scores/*/scores-*.jsonl' \
  --exclude='*' "fal-h100-01:$RUN/" "$DEST/"
for out in main round-1 round-2; do
  if [ -d "$DEST/$out/saves" ]; then
    perl -e 'alarm shift; exec @ARGV' 220 ssh -o BatchMode=yes fal-h100-01 "python3 -B ~/$SRC/infra/r04-nuisance/run/summarize_saves.py ~/$RUN/$out/saves" > "$DEST/$out/saves-summary.json"
  fi
done
echo mirrored
