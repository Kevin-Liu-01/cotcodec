#!/usr/bin/env bash
# am1-memory-credit-v1 (CONFIRMATORY): stage the text-free operations evidence on the host: lane
# records, driver summary and environment, worker records and per-pass metadata, SHA-256 of the raw
# outputs that stay on the host, a text-free copy of the judge items, the build, selftest, manifest
# and prepare records, and the hand-check sample's SHA-256 (the sample itself, with its texts,
# stays on the host). No analysis output. Usage: am1c-stage-evidence.sh <job id>
set -Eeuo pipefail
JOB="${1:?job id}"
SHORT=9ad36b10
R=/home/kevin/cotcodec-runs/stage0/am1-memory-credit-v1
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests,prepare,hand-check}
src=$R/runs/main/$JOB; dst=$E/jobs/$JOB-main
mkdir -p "$dst/am1/sessions"
for f in job.env termination.env manifest.json command.json model-verification.txt \
  provenance-verification.txt gpu-prolog.env container-doctor.txt gpu-compute-apps-prolog.csv; do
  [[ -f $src/$f ]] && cp "$src/$f" "$dst/"; done
sha256sum "$src/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"
sha256sum "$src/study-artifact.json" | cut -d" " -f1 > "$dst/study-artifact.sha256"
cp "$R/ops/scontrol-$JOB.txt" "$dst/scontrol.txt" 2>/dev/null || true
gzip -n -c "$R/runs/main/slurm-$JOB.out" > "$dst/slurm-$JOB.out.gz" 2>/dev/null || true
cp "$src/am1/summary.json" "$src/am1/environment.json" "$dst/am1/"
gzip -n -c "$src/am1/gpu-samples.csv" > "$dst/am1/gpu-samples.csv.gz"
for w in "$src"/am1/sessions/*/; do
  wn=$(basename "$w"); mkdir -p "$dst/am1/sessions/$wn"
  cp "$w"/{session.json,done.json,worker-progress.jsonl,attention.json} "$dst/am1/sessions/$wn/" 2>/dev/null || true
  for m in "$w"/*.json; do
    case "$(basename "$m")" in session.json|done.json|attention.json) continue;; esac
    gzip -n -c "$m" > "$dst/am1/sessions/$wn/$(basename "$m").gz"; done
  ( cd "$w" && find . -maxdepth 1 -type f \( -name "*.npz" -o -name "*.texts.jsonl.gz" \) -print0 \
    | sort -z | xargs -0 -r sha256sum ) > "$dst/am1/sessions/$wn/raw-sha256.txt"
done
for f in "$src"/am1/worker-*.log; do gzip -n -c "$f" > "$dst/am1/$(basename "$f").gz"; done
if [[ -f "$src/am1/judge-items.json" ]]; then
  sha256sum "$src/am1/judge-items.json" | sed "s#$R/##" > "$dst/am1/judge-items.sha256.txt"
  python3 - "$src/am1/judge-items.json" "$dst/am1/judge-items-public.json" <<'PY'
import hashlib, json, sys
items = json.load(open(sys.argv[1]))
out = [{k: v for k, v in i.items() if k != "response"} | {
    "response_sha256": hashlib.sha256(i["response"].encode()).hexdigest()} for i in items]
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PY
  gzip -n "$dst/am1/judge-items-public.json"
fi
b=$R/overlay-build-vllm-$SHORT
cp "$b/build-receipt.json" "$E/builds/vllm-overlay-$SHORT-build-receipt.json"
for f in source-validation.json provenance-verification.json vllm-overlay-fixups.json image-id.txt; do
  cp "$b/$f" "$E/builds/vllm-overlay-$SHORT-$f"; done
cp $R/ops/slurm-vllm-overlay-*.out $R/ops/scontrol-1454.txt $E/builds/ 2>/dev/null || true
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d.pop('file_manifest',None);json.dump(d,open(sys.argv[2],'w'),indent=1,sort_keys=True)" \
  "$R/capsule/source-receipt-$SHORT.json" "$E/builds/source-receipt-$SHORT.json"
cp $R/manifests/main-$SHORT.yaml $R/manifests/main-$SHORT.dry-run.json $R/manifests/main-$SHORT.test-only.txt \
  $R/manifests/main-$SHORT.submit.txt $E/manifests/
cp $R/ops/*.sh $R/ops/*.sbatch $R/ops/jobs.log $R/ops/preflight.log $R/ops/pins.sha256 \
  $R/ops/pytest-host-*.txt $E/ops/
mkdir -p $E/selftests/selftest-postbuild-$SHORT
cp $R/selftest-postbuild-$SHORT/{exits.txt,study-selftest.json,study-plan.json} $E/selftests/selftest-postbuild-$SHORT/
cp $R/ops/slurm-selftest-*.out $R/ops/scontrol-1455.txt $E/selftests/ 2>/dev/null || true
cp $R/prepare/prepare.log $R/prepare/artifact-stdout.json $E/prepare/
cp $R/prepare/rebuild-check/artifact-stdout.json $E/prepare/rebuild-artifact-stdout.json
gzip -n -c $R/pools-summary.json > $E/prepare/pools-summary-$SHORT.json.gz
sed -i "s#$R/##g" $E/prepare/prepare.log
if [[ -f $R/hand-check-sample.jsonl ]]; then
  ( cd $R && sha256sum hand-check-sample.jsonl ) > $E/hand-check/hand-check-sample.sha256.txt
  cp $R/ops/hand-sample-stdout.json $E/hand-check/ 2>/dev/null || true
fi
echo staged: $(find "$E" -type f | wc -l) files, $(du -sh "$E" | cut -f1)
