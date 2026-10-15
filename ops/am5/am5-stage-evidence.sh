#!/usr/bin/env bash
# AM5: stage the text-free evidence on the host ($R/evidence-stage): lane records, the driver's
# summary and environment, worker records and per-pass metadata, SHA-256 of the raw outputs that
# stay on the host, a judge-item list with each response replaced by its SHA-256, the build,
# selftest, manifest, prepare and hand-check records, and the analysis outputs and logs. Then
# search every staged file for every distinct reply of at least 12 characters and every question,
# answer and memory text of the ablated and the original development artifacts; exit 1 on a hit.
# Usage: am5-stage-evidence.sh <commit short id of the run> <job id> [analysis short id]
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"; JOB="${2:?job id}"; TAG="${3:-$SHORT}"
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests,logs,prepare,hand-check}
src=$R/runs/dev-ablated/$JOB; dst=$E/jobs/$JOB-dev-ablated
mkdir -p "$dst/am5/sessions"
for f in job.env termination.env manifest.json command.json model-verification.txt \
  provenance-verification.txt gpu-prolog.env container-doctor.txt gpu-compute-apps-prolog.csv; do
  [[ -f $src/$f ]] && cp "$src/$f" "$dst/"; done
sha256sum "$src/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"
sha256sum "$src/study-artifact.json" | cut -d" " -f1 > "$dst/study-artifact.sha256"
cp "$R/ops/scontrol-$JOB.txt" "$dst/scontrol.txt" 2>/dev/null || true
gzip -n -c "$R/runs/dev-ablated/slurm-$JOB.out" > "$dst/slurm-$JOB.out.gz" 2>/dev/null || true
cp "$src/am5/summary.json" "$src/am5/environment.json" "$dst/am5/"
gzip -n -c "$src/am5/gpu-samples.csv" > "$dst/am5/gpu-samples.csv.gz" 2>/dev/null || true
for w in "$src"/am5/sessions/*/; do
  wn=$(basename "$w"); mkdir -p "$dst/am5/sessions/$wn"
  cp "$w"/{session.json,done.json,worker-progress.jsonl} "$dst/am5/sessions/$wn/" 2>/dev/null || true
  for m in "$w"/*.json; do
    case "$(basename "$m")" in session.json|done.json) continue;; esac
    gzip -n -c "$m" > "$dst/am5/sessions/$wn/$(basename "$m").gz"; done
  ( cd "$w" && find . -maxdepth 1 -type f \( -name "*.npz" -o -name "*.texts.jsonl.gz" \) -print0 \
    | sort -z | xargs -0 -r sha256sum ) > "$dst/am5/sessions/$wn/raw-sha256.txt"
done
for f in "$src"/am5/worker-*.log; do gzip -n -c "$f" > "$dst/am5/$(basename "$f").gz"; done
if [[ -f "$src/am5/judge-items.json" ]]; then
  ( cd "$src/am5" && sha256sum judge-items.json ) > "$dst/am5/judge-items.sha256.txt"
  python3 - "$src/am5/judge-items.json" "$dst/am5/judge-items-public.json" <<'PY'
import hashlib, json, sys
items = json.load(open(sys.argv[1]))
out = [{k: v for k, v in i.items() if k != "response"} | {
    "response_sha256": hashlib.sha256(i["response"].encode()).hexdigest()} for i in items]
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PY
  gzip -n "$dst/am5/judge-items-public.json"
fi
cp "$R"/manifests/dev-ablated-"$SHORT".{yaml,dry-run.json,test-only.txt,submit.txt} "$E/manifests/" 2>/dev/null || true
s=$R/selftest-$SHORT
[[ -d $s ]] && { mkdir -p "$E/selftests/selftest-$SHORT"; cp "$s"/{exits.txt,am5-selftest.json,am5-plan.json} "$E/selftests/selftest-$SHORT/" 2>/dev/null || true; }
cp "$R"/ops/slurm-selftest-*.out "$E/selftests/" 2>/dev/null || true
b=$R/overlay-build-vllm-$SHORT
if [[ -d $b ]]; then
  cp "$b/build-receipt.json" "$E/builds/vllm-overlay-$SHORT-build-receipt.json"
  for f in source-validation.json provenance-verification.json vllm-overlay-fixups.json image-id.txt; do
    [[ -f $b/$f ]] && cp "$b/$f" "$E/builds/vllm-overlay-$SHORT-$f"; done
fi
cp "$R"/ops/slurm-vllm-overlay-*.out "$E/builds/" 2>/dev/null || true
[[ -f $R/capsule/source-receipt-$SHORT.json ]] && python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d.pop('file_manifest',None);json.dump(d,open(sys.argv[2],'w'),indent=1,sort_keys=True)" \
  "$R/capsule/source-receipt-$SHORT.json" "$E/builds/source-receipt-$SHORT.json"
cp "$R"/ops/jobs.log "$R"/ops/preflight.log "$R"/ops/scontrol-*.txt "$R"/ops/build-*.txt "$E/ops/" 2>/dev/null || true
cp "$R"/prepare/* "$E/prepare/" 2>/dev/null || true
cp "$R"/hand-check/* "$E/hand-check/" 2>/dev/null || true
cp "$R"/extract-*.{log,json} "$R"/hand-sample-*.json "$E/logs/" 2>/dev/null || true
if [[ -d $R/out-$TAG-a ]]; then
  cp "$R"/out-"$TAG"-a/* "$E/"
  cp "$R/analyze-$TAG.log" "$R/pytest-$TAG.log" "$E/logs/" 2>/dev/null || true
fi
grep -rl "$HOME" "$E" | xargs -r sed -i "s#$HOME#~#g"
python3 - "$E" "$R/runs" "$ABL_ART" "$DEV_ART" <<'PY'
import gzip, json, pathlib, sys
stage, runs = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
texts = set()
for f in runs.glob("dev-ablated/*/am5/sessions/rd-*/all.texts.jsonl.gz"):
    with gzip.open(f, "rt") as h:
        for line in h:
            t = json.loads(line)["text"].strip()
            if len(t) >= 12:
                texts.add(t)
for a in sys.argv[3:]:
    art = json.load(open(a))
    for q in art["questions"]:
        for t in (q["question"], str(q["answer"])):
            if len(t.strip()) >= 12:
                texts.add(t.strip())
        for pool in q["pools"].values():
            for m in pool:
                if len(m["text"].strip()) >= 12:
                    texts.add(m["text"].strip())
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
print(f"texts searched: {len(texts)}; staged files containing one: {len(hits)}")
for h in hits[:20]:
    print("HIT", h)
sys.exit(1 if hits else 0)
PY
echo staged: $(find "$E" -type f | wc -l) files, $(du -sh "$E" | cut -f1)
log_job "evidence staged for ${SHORT} job ${JOB}: $(find "$E" -type f | wc -l) files, no text found"
