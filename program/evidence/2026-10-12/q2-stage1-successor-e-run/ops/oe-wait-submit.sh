#!/usr/bin/env bash
# Operator script: submit OE (q2-stage1-successor-e-v1 section 7.2; S1a's O2) only when the
# whole Slurm queue is empty, polling every 2 s for at most about 200 s per invocation (rerun
# it until it submits). OE is the cu129 vLLM overlay build from E's freeze commit: S1a's
# builder and extractor (section 23 digests) from a clean clone of the freeze commit, the
# discovery source archive made there with selected_ref HEAD and pre-validated on CPU with the
# pinned extractor. One H100, 8 CPUs, 32 GB, --time=00:03:00 (the 3-minute cap), no requeue.
# Usage: oe-wait-submit.sh TAG   (TAG = oe or oe-retry; the retry runs only if OE failed)
set -u
TAG="$1"
case "$TAG" in oe|oe-retry) ;; *) echo "TAG must be oe or oe-retry"; exit 2;; esac
F=f6144d6bf745d944cb016cfc2b9894e1dbf7eb66
R=/home/kevin/cotcodec-runs/stage0/q2-stage1e
O=$R/oe
C=$O/checkout-${F:0:12}
A=/home/kevin/cotcodec-runs/source-archives/q2e-oe-${F:0:12}-head
BU=$C/scripts/build_vllm_overlay_on_h100.sh
EX=$C/scripts/extract_discovery_source_archive.py
BROOT=$O/build-${F:0:12}
[ "$TAG" = oe-retry ] && BROOT=$O/build-${F:0:12}-r2
L=$O/ops.log
OUT=$O/$TAG-job-id
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$L"; }
if [ -e "$OUT" ]; then echo "already submitted: $(cat "$OUT")"; squeue -a -h -o '%i|%u|%j|%T|%M|%C|%b'; exit 0; fi
test -d "$C" && test -f "$A.tar.gz" && test -f "$A.receipt.json" && test ! -e "$BROOT" || {
  echo "inputs missing or build root exists"; exit 3; }
[ "$(cd "$C" && git rev-parse HEAD)" = "$F" ] && [ -z "$(cd "$C" && git status --porcelain)" ] || {
  echo "the clone is not clean at $F"; exit 3; }
[ "$(sha256sum "$BU" | cut -d' ' -f1)" = aa43283e757695384e0548d060a18b98f07a3af06f583efdb2d709f677e1a96d ] &&
[ "$(sha256sum "$EX" | cut -d' ' -f1)" = 9b4d21a83beac8913dc06a946cf43ea31d77326e65d04957fad66d7b97d8c3cb ] || {
  echo "builder or extractor digest differs from section 23"; exit 3; }
SRC=$(sha256sum "$A.tar.gz" | cut -d' ' -f1)
TREE=$(cd "$C" && git rev-parse 'HEAD^{tree}')
for i in $(seq 1 100); do
  q=$(squeue -a -h -o '%i')
  if [ -z "$q" ]; then
    log "squeue-before-$TAG: []"
    nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader >>"$L"
    cd "$C"
    J=$(sbatch --parsable --job-name="q2e-$TAG" --partition=research --nodes=1 --ntasks=1 \
      --gres=gpu:h100:1 --cpus-per-task=8 --mem=32G --time=00:03:00 --no-requeue \
      --output="$O/slurm-$TAG-%j.out" \
      --export=ALL,COTCODEC_SOURCE_ARCHIVE=$A.tar.gz,COTCODEC_SOURCE_RECEIPT=$A.receipt.json,COTCODEC_SOURCE_EXTRACTOR=$EX,COTCODEC_SOURCE_EXTRACTOR_SHA256=9b4d21a83beac8913dc06a946cf43ea31d77326e65d04957fad66d7b97d8c3cb,COTCODEC_SOURCE_BUILDER_SHA256=aa43283e757695384e0548d060a18b98f07a3af06f583efdb2d709f677e1a96d,COTCODEC_SOURCE_SHA256=$SRC,COTCODEC_GIT_SHA=$F,COTCODEC_GIT_TREE=$TREE,COTCODEC_BUILD_ROOT=$BROOT,COTCODEC_VLLM_VARIANT=cu129 \
      "$BU")
    rc=$?
    printf '%s\n' "$J" >"$OUT"
    log "$TAG submitted job $J rc=$rc git=${F:0:12} archive=${SRC:0:8} tree=${TREE:0:8} build_root=$BROOT"
    mkdir -p "$O/slurm-state"
    nohup timeout 1800 "$C/scripts/record_slurm_end_states.sh" "$O/slurm-state" "$J" \
      >>"$O/end-states.log" 2>&1 </dev/null &
    nohup timeout 1800 bash -c '
      O="$1"; J="$2"
      while :; do
        echo "$(date -u +%FT%TZ) $(squeue -a -h -o "%i|%u|%j|%T|%M|%C|%b" | tr "\n" ";")" >>"$O/squeue-watch.log"
        s="$(scontrol show job -o "$J" 2>/dev/null)" && [ -n "$s" ] && printf "%s\n" "$s" >"$O/scontrol-$J.last.txt"
        squeue -a -h -o "%i" 2>/dev/null | grep -qE "^$J\$" || break
        sleep 5
      done' _ "$O" "$J" >/dev/null 2>&1 </dev/null &
    sleep 2
    squeue -a -h -o '%i|%u|%j|%T|%M|%C|%b'
    exit 0
  fi
  sleep 2
done
echo "$(date -u +%T) still busy: $(squeue -a -h -o '%i|%j|%T|%M|%C' | tr '\n' ';')"
exit 1
