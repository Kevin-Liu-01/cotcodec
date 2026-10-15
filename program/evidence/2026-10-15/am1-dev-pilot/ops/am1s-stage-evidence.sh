#!/usr/bin/env bash
# AM1 development pilot: stage the text-free evidence on the host (lane records, worker records,
# pass metadata, hashes of the raw outputs that stay on the host, text-free copies of the judge
# items). Usage: am1s-stage-evidence.sh <analysis dir> <kind:job> ...  (writes $R/evidence-stage)
set -Eeuo pipefail
AN="${1:?analysis dir}"; shift
R=/home/kevin/cotcodec-runs/stage0/am1-study
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests,prepare,analysis}
for spec in "$@"; do
KIND=${spec%%:*}; JOB=${spec##*:}
src=$R/runs/$KIND/$JOB; dst=$E/jobs/$JOB-$KIND
mkdir -p "$dst/am1/sessions"
for f in job.env termination.env manifest.json command.json model-verification.txt \
  provenance-verification.txt gpu-prolog.env container-doctor.txt; do
  [[ -f $src/$f ]] && cp "$src/$f" "$dst/"; done
sha256sum "$src/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"
cp "$R/ops/scontrol-$JOB.txt" "$dst/scontrol.txt" 2>/dev/null || true
cp "$src/am1/summary.json" "$src/am1/environment.json" "$dst/am1/"
gzip -c "$src/am1/gpu-samples.csv" > "$dst/am1/gpu-samples.csv.gz"
for w in "$src"/am1/sessions/*/; do
  wn=$(basename "$w"); mkdir -p "$dst/am1/sessions/$wn"
  cp "$w"/{session.json,done.json,worker-progress.jsonl,attention.json} "$dst/am1/sessions/$wn/" 2>/dev/null || true
  for m in "$w"/*.json; do
    case "$(basename "$m")" in session.json|done.json|attention.json) continue;; esac
    cp "$m" "$dst/am1/sessions/$wn/"; done
  ( cd "$w" && find . -maxdepth 1 -type f \( -name "*.npz" -o -name "*.texts.jsonl.gz" \) -print0 \
    | sort -z | xargs -0 -r sha256sum ) > "$dst/am1/sessions/$wn/raw-sha256.txt"
done
for f in "$src"/am1/worker-*.log; do gzip -c "$f" > "$dst/am1/$(basename "$f").gz"; done
sha256sum "$src/am1/judge-items.json" > "$dst/am1/judge-items.sha256.txt"
python3 - "$src/am1/judge-items.json" "$dst/am1/judge-items-public.json" <<'PY'
import hashlib, json, sys
items = json.load(open(sys.argv[1]))
out = [{k: v for k, v in i.items() if k != "response"} | {
    "response_sha256": hashlib.sha256(i["response"].encode()).hexdigest()} for i in items]
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PY
done
cp $R/overlay-build-vllm-*/build-receipt.json $E/builds/ 2>/dev/null || true
for b in $R/overlay-build-vllm-*; do s=${b##*-}; [[ -f $b/build-receipt.json ]] && cp $b/build-receipt.json $E/builds/vllm-overlay-$s-build-receipt.json; done
rm -f $E/builds/build-receipt.json
cp $R/ops/slurm-vllm-overlay-*.out $R/ops/scontrol-*.txt $E/builds/ 2>/dev/null || true
for c in $R/capsule/source-receipt-*.json; do
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d.pop('file_manifest',None);json.dump(d,open(sys.argv[2],'w'),indent=1,sort_keys=True)" "$c" "$E/builds/$(basename "$c")"; done
cp $R/manifests/*.yaml $R/manifests/*.dry-run.json $R/manifests/*.submit.txt $E/manifests/ 2>/dev/null || true
cp $R/ops/*.sh $R/ops/*.sbatch $R/ops/jobs.log $R/ops/preflight.log $E/ops/
cp $R/ops/slurm-selftest-*.out $E/selftests/ 2>/dev/null || true
for s in $R/selftest-*; do n=$(basename "$s"); mkdir -p $E/selftests/$n; cp $s/exits.txt $s/study-selftest.json $s/study-plan.json $E/selftests/$n/ 2>/dev/null || true; done
cp $R/prepare/pools-summary-*.json $R/prepare/prepare.log $R/prepare/artifact-stdout.json $R/prepare/split-stdout.json $E/prepare/
cp $R/private/hand-labels.jsonl $R/private/hand-labels-transcription-error.jsonl $E/analysis/
sha256sum $R/private/hand-check-sample.jsonl > $E/analysis/hand-check-sample.sha256.txt
cp -r "$AN"/. $E/analysis/
echo staged: $(find "$E" -type f | wc -l) files, $(du -sh "$E" | cut -f1)
