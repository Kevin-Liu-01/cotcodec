#!/usr/bin/env bash
# am5-ablated-cost-v1: stage the text-free evidence on the host: lane records, the
# driver's summary and environment, worker records and per-pass metadata, SHA-256 of the raw
# outputs that stay on the host, a text-free copy of the judge items, the build, selftest,
# manifest and prepare records, and the analysis outputs and logs. Then check that no reply
# text, question, answer or memory text reached the staged tree (every distinct reply of at least
# 12 characters, and every question, answer and memory text of both artifacts, is searched for in
# every staged file).
# The commit is the one whose build, selftests, manifests and extract logs are staged; the
# analysis outputs staged are $R/out-<ANALYSIS_TAG>-a (default: the same commit; set ANALYSIS_TAG
# to stage a later rerun's). The checkout may be at a later commit of the same branch.
# Usage: am5r-stage-evidence.sh dev|reg <commit short id> <population>:<job id> [...]
set -Eeuo pipefail
# A job refused at its prolog (no am5r/ directory) or a worker that died before writing a pass
# leaves globs unmatched and records missing: those are skipped, never an error (round 2).
shopt -s nullglob
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; shift 2
TAG="${ANALYSIS_TAG:-$SHORT}"
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests,logs,prepare}
ARTS=()
for spec in "$@"; do
  POP=${spec%%:*}; JOB=${spec##*:}
  ARTS+=("$(artifact_for "$POP")")
  src=$R/runs/$POP/$JOB; dst=$E/jobs/$JOB-$POP
  mkdir -p "$dst/am5r/sessions"
  for f in job.env termination.env manifest.json command.json model-verification.txt \
    provenance-verification.txt gpu-prolog.env container-doctor.txt gpu-compute-apps-prolog.csv; do
    if [[ -f $src/$f ]]; then cp "$src/$f" "$dst/"; fi; done
  if [[ -f $src/docker-research.sbatch ]]; then
    sha256sum "$src/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"; fi
  if [[ -f $src/study-artifact.json ]]; then
    sha256sum "$src/study-artifact.json" | cut -d" " -f1 > "$dst/study-artifact.sha256"; fi
  scontrol show job "$JOB" 2>/dev/null | grep -E "JobState|RunTime" > "$dst/scontrol.txt" || \
    cp "$R/ops/scontrol-$JOB.txt" "$dst/scontrol.txt" 2>/dev/null || true
  if [[ -f $R/runs/$POP/slurm-$JOB.out ]]; then
    gzip -n -c "$R/runs/$POP/slurm-$JOB.out" > "$dst/slurm-$JOB.out.gz"; fi
  for f in summary.json environment.json; do
    if [[ -f $src/am5r/$f ]]; then cp "$src/am5r/$f" "$dst/am5r/"; fi; done
  if [[ -f $src/am5r/gpu-samples.csv ]]; then
    gzip -n -c "$src/am5r/gpu-samples.csv" > "$dst/am5r/gpu-samples.csv.gz"; fi
  for w in "$src"/am5r/sessions/*/; do
    wn=$(basename "$w"); mkdir -p "$dst/am5r/sessions/$wn"
    cp "$w"/{session.json,done.json,worker-progress.jsonl} "$dst/am5r/sessions/$wn/" 2>/dev/null || true
    for m in "$w"/*.json; do
      case "$(basename "$m")" in session.json|done.json) continue;; esac
      gzip -n -c "$m" > "$dst/am5r/sessions/$wn/$(basename "$m").gz"; done
    ( cd "$w" && find . -maxdepth 1 -type f \( -name "*.npz" -o -name "*.texts.jsonl.gz" \) -print0 \
      | sort -z | xargs -0 -r sha256sum ) > "$dst/am5r/sessions/$wn/raw-sha256.txt"
  done
  for f in "$src"/am5r/worker-*.log; do gzip -n -c "$f" > "$dst/am5r/$(basename "$f").gz"; done
  if [[ -f "$src/am5r/judge-items.json" ]]; then
    ( cd "$src/am5r" && sha256sum judge-items.json ) > "$dst/am5r/judge-items.sha256.txt"
    python3 - "$src/am5r/judge-items.json" "$dst/am5r/judge-items-public.json" <<'PY'
import hashlib, json, sys
items = json.load(open(sys.argv[1]))
drop = {"response", "explanation"}
out = [{k: v for k, v in i.items() if k not in drop} | {
    "response_sha256": hashlib.sha256(i["response"].encode()).hexdigest()} for i in items]
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PY
    gzip -n "$dst/am5r/judge-items-public.json"
  fi
  cp "$R/manifests/$POP-$SHORT".{yaml,dry-run.json,test-only.txt} "$E/manifests/" 2>/dev/null || true
  cp "$R/manifests/$POP-$SHORT".submit.txt "$R/manifests/$POP-$SHORT".rerun.txt "$E/manifests/" 2>/dev/null || true
  cp "$R/extract-$POP-$SHORT".{log,json} "$E/logs/" 2>/dev/null || true
  gzip -n -c "$R/extract-$POP-$SHORT.stderr" > "$E/logs/extract-$POP-$SHORT.stderr.gz" 2>/dev/null || true
done
for s in "$R"/selftest-heldout-"$SHORT" "$R"/selftest-development-"$SHORT"; do
  [[ -d $s ]] || continue
  mkdir -p "$E/selftests/$(basename "$s")"
  cp "$s"/{exits.txt,am5r-selftest.json,am5r-plan.json} "$E/selftests/$(basename "$s")/" 2>/dev/null || true
done
b=$R/overlay-build-vllm-$SHORT
if [[ -d $b ]]; then
  cp "$b/build-receipt.json" "$E/builds/vllm-overlay-$SHORT-build-receipt.json"
  for f in source-validation.json provenance-verification.json vllm-overlay-fixups.json image-id.txt; do
    [[ -f $b/$f ]] && cp "$b/$f" "$E/builds/vllm-overlay-$SHORT-$f"; done
fi
cp "$R"/ops/slurm-vllm-overlay-*.out "$E/builds/" 2>/dev/null || true
[[ -f $R/capsule/source-receipt-$SHORT.json ]] && python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d.pop('file_manifest',None);json.dump(d,open(sys.argv[2],'w'),indent=1,sort_keys=True)" \
  "$R/capsule/source-receipt-$SHORT.json" "$E/builds/source-receipt-$SHORT.json"
cp "$R"/ops/jobs.log "$R"/ops/preflight.log "$R"/ops/scontrol-*.txt "$E/ops/" 2>/dev/null || true
cp "$R"/rerun-decision-*.json "$E/ops/" 2>/dev/null || true
if [[ -d $R/hand-check ]]; then
  # The receipts and their text-free records, exactly as committed before the join
  # (am5r-hand-receipt.sh), so the staged copy shows no difference from that commit.
  mkdir -p "$E/hand-check"; cp "$R"/hand-check/* "$E/hand-check/"
fi
cp "$R"/ops/slurm-selftest-*.out "$E/selftests/" 2>/dev/null || true
cp "$R"/prepare/* "$E/prepare/" 2>/dev/null || true
if [[ -d $R/out-$TAG-a ]]; then
  cp "$R"/out-"$TAG"-a/* "$E/"
  cp "$R/analyze-$TAG.log" "$R/pytest-$TAG.log" "$E/logs/" 2>/dev/null || true
  for f in "$R"/analyze-"$TAG"-a.stderr "$R"/dryrun-compare-"$TAG".stderr "$R"/power-"$TAG".stderr; do
    [[ -f $f ]] && gzip -n -c "$f" > "$E/logs/$(basename "$f").gz"; done
fi
cp "$R"/extract-*.log "$R"/extract-*.json "$E/logs/" 2>/dev/null || true
# The held-out artifact's summary is staged in both modes (it holds the control's pools too), and
# the development artifact rides along in the held-out job: both artifacts' texts are searched.
[[ -r $HELD_ART ]] && ARTS+=("$HELD_ART")
ARTS+=("$DEV_ART")
# $HOME is written as ~ in records and logs, the gzipped ones included (pipefail-safe: a grep that
# finds nothing must not end the script).
{ grep -rl --exclude='*.gz' "$HOME" "$E" || true; } | xargs -r sed -i "s#$HOME#~#g"
while IFS= read -r -d '' f; do
  if gzip -dc "$f" | grep -c "$HOME" > /dev/null; then
    gzip -dc "$f" | sed "s#$HOME#~#g" | gzip -n > "$f.tmp" && mv "$f.tmp" "$f"
  fi
done < <(find "$E" -type f -name '*.gz' -print0)
# No reply text, question, answer or memory text in the staged tree.
python3 - "$E" "$R/runs" "${ARTS[@]}" <<'PY'
import gzip, json, pathlib, sys
stage, runs = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
texts = set()
for f in runs.glob("*/*/am5r/sessions/rd-*/all.texts.jsonl.gz"):
    with gzip.open(f, "rt") as h:
        for line in h:
            t = json.loads(line)["text"].strip()
            if len(t) >= 12:
                texts.add(t)
for a in sys.argv[3:]:
    art = json.load(open(a))
    for q in art["questions"]:
        for t in (q["question"], str(q["answer"]), str(q.get("validation_decoy", {}).get("answer", ""))):
            if len(t.strip()) >= 12:
                texts.add(t.strip())
        for pool in q["pools"].values():
            for m in pool:
                if len(m["text"].strip()) >= 12:
                    texts.add(m["text"].strip())
# The prompt's own phrase and the validation response are config text, not content.
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
log_job "evidence staged for ${SHORT} ($*): $(find "$E" -type f | wc -l) files, no text found"
