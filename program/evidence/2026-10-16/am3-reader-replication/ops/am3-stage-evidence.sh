#!/usr/bin/env bash
# AM3 (EXPLORATORY): stage the text-free evidence on the host: lane records, the driver's summary
# and environment, worker records and per-pass metadata, SHA-256 of the raw outputs that stay on
# the host, a text-free copy of the judge items, the build, selftest and manifest records, and the
# analysis outputs and logs. Then check that no reply text reached the staged tree (every distinct
# reply of at least 12 characters is searched for in every staged file).
# Usage: am3-stage-evidence.sh <commit short id> <job id>
set -Eeuo pipefail
SHORT="${1:?commit short id}"; JOB="${2:?job id}"
R=~/cotcodec-runs/stage0/am3-reader-replication
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests,logs,models}
src=$R/runs/main/$JOB; dst=$E/jobs/$JOB-main
mkdir -p "$dst/am3/sessions"
for f in job.env termination.env manifest.json command.json model-verification.txt \
  provenance-verification.txt gpu-prolog.env container-doctor.txt gpu-compute-apps-prolog.csv; do
  [[ -f $src/$f ]] && cp "$src/$f" "$dst/"; done
sha256sum "$src/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"
sha256sum "$src/study-artifact.json" | cut -d" " -f1 > "$dst/study-artifact.sha256"
cp "$R/ops/scontrol-$JOB.txt" "$dst/scontrol.txt" 2>/dev/null || true
gzip -n -c "$R/runs/main/slurm-$JOB.out" > "$dst/slurm-$JOB.out.gz" 2>/dev/null || true
cp "$src/am3/summary.json" "$src/am3/environment.json" "$dst/am3/"
gzip -n -c "$src/am3/gpu-samples.csv" > "$dst/am3/gpu-samples.csv.gz" 2>/dev/null || true
for w in "$src"/am3/sessions/*/; do
  wn=$(basename "$w"); mkdir -p "$dst/am3/sessions/$wn"
  cp "$w"/{session.json,done.json,worker-progress.jsonl} "$dst/am3/sessions/$wn/" 2>/dev/null || true
  for m in "$w"/*.json; do
    case "$(basename "$m")" in session.json|done.json) continue;; esac
    gzip -n -c "$m" > "$dst/am3/sessions/$wn/$(basename "$m").gz"; done
  ( cd "$w" && find . -maxdepth 1 -type f \( -name "*.npz" -o -name "*.texts.jsonl.gz" \) -print0 \
    | sort -z | xargs -0 -r sha256sum ) > "$dst/am3/sessions/$wn/raw-sha256.txt"
done
for f in "$src"/am3/worker-*.log; do gzip -n -c "$f" > "$dst/am3/$(basename "$f").gz"; done
if [[ -f "$src/am3/judge-items.json" ]]; then
  ( cd "$src/am3" && sha256sum judge-items.json ) > "$dst/am3/judge-items.sha256.txt"
  python3 - "$src/am3/judge-items.json" "$dst/am3/judge-items-public.json" <<'PY'
import hashlib, json, sys
items = json.load(open(sys.argv[1]))
out = [{k: v for k, v in i.items() if k != "response"} | {
    "response_sha256": hashlib.sha256(i["response"].encode()).hexdigest()} for i in items]
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PY
  gzip -n "$dst/am3/judge-items-public.json"
fi
b=$R/overlay-build-vllm-$SHORT
cp "$b/build-receipt.json" "$E/builds/vllm-overlay-$SHORT-build-receipt.json"
for f in source-validation.json provenance-verification.json vllm-overlay-fixups.json image-id.txt; do
  [[ -f $b/$f ]] && cp "$b/$f" "$E/builds/vllm-overlay-$SHORT-$f"; done
cp $R/ops/slurm-vllm-overlay-*.out $R/ops/scontrol-1462.txt $E/builds/ 2>/dev/null || true
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d.pop('file_manifest',None);json.dump(d,open(sys.argv[2],'w'),indent=1,sort_keys=True)" \
  "$R/capsule/source-receipt-$SHORT.json" "$E/builds/source-receipt-$SHORT.json"
cp $R/manifests/main-$SHORT.yaml $R/manifests/main-$SHORT.dry-run.json $R/manifests/main-$SHORT.test-only.txt \
  $R/manifests/main-$SHORT.submit.txt $E/manifests/
cp $R/ops/*.sh $R/ops/*.sbatch $R/ops/*.py $R/ops/jobs.log $R/ops/preflight.log $R/ops/pytest-host-*.txt $E/ops/
cp $R/ops/slurm-selftest-*.out $R/ops/scontrol-146[13].txt $E/selftests/ 2>/dev/null || true
for s in selftest-pre-$SHORT selftest-postbuild-$SHORT; do
  mkdir -p $E/selftests/$s; cp $R/$s/{exits.txt,am3-selftest.json,am3-plan.json} $E/selftests/$s/; done
cp ~/cotcodec-runs/model-fetch/cpu-1460/{receipt.json,summary.jsonl} $E/models/ 2>/dev/null || true
cp ~/cotcodec-runs/hf-cache/cotcodec-receipts-cpu-lane/olmo-2-1124-7b-instruct.json \
  $E/models/olmo-2-1124-7b-instruct.receipt.json
cp $R/out-$SHORT-a/{results.json,per-table.json.gz,tables.md} $E/
cp $R/posthoc-$SHORT.json $E/posthoc.json
cp $R/analyze-$SHORT.log $R/extract-$SHORT.json $R/pytest-$SHORT.log $E/logs/
for f in $R/extract-$SHORT.stderr $R/analyze-$SHORT-a.stderr $R/posthoc-$SHORT.stderr; do gzip -n -c $f > $E/logs/$(basename $f).gz; done
# $HOME is written as ~ in records and logs; the ops scripts are kept exactly as they ran.
grep -rl --exclude-dir=ops "$HOME" "$E" | xargs -r sed -i "s#$HOME#~#g"
# No reply text in the staged tree.
python3 - "$src/am3" "$E" <<'PY'
import gzip, json, pathlib, sys
run, stage = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
texts = set()
for f in run.glob("sessions/rd-*/all.texts.jsonl.gz"):
    with gzip.open(f, "rt") as h:
        for line in h:
            t = json.loads(line)["text"].strip()
            if len(t) >= 12:
                texts.add(t)
# The prompt's own phrase and the judge's validation response are config text, not reply content
# (tables.md names the validation item); they are not searched.
texts -= {"I don't know", "I don't know."}
hits = []
for f in stage.rglob("*"):
    if not f.is_file():
        continue
    raw = f.read_bytes()
    if f.suffix == ".gz":
        raw = gzip.decompress(raw)
    blob = raw.decode("utf-8", "replace")
    for t in texts:
        if t in blob:
            hits.append((str(f.relative_to(stage)), len(t)))
            break
print(f"reply texts searched: {len(texts)}; staged files containing one: {len(hits)}")
for h in hits[:20]:
    print("HIT", h)
sys.exit(1 if hits else 0)
PY
echo staged: $(find "$E" -type f | wc -l) files, $(du -sh "$E" | cut -f1)
