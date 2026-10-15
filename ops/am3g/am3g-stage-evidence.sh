#!/usr/bin/env bash
# am3-nonabstain-generality-v1: stage the text-free evidence on the host: lane records, the
# driver's summary and environment, worker records and per-pass metadata, SHA-256 of the raw
# outputs that stay on the host, a text-free copy of the judge items, the build, selftest,
# manifest and prepare records, and the analysis outputs and logs. Then check that no reply
# text, question, explanation or decoy answer reached the staged tree (every distinct reply of
# at least 12 characters, and every study-artifact question and answer text, is searched for in
# every staged file).
# The commit is the one whose analysis outputs ($R/out-<short>-a) are staged; the checkout may be
# at a later commit of the same branch.
# Usage: am3g-stage-evidence.sh dev|reg <commit short id> <population>:<job id> [...]
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; shift 2
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests,logs,prepare}
ARTS=()
for spec in "$@"; do
  POP=${spec%%:*}; JOB=${spec##*:}
  ARTS+=("$(artifact_for "$POP")")
  src=$R/runs/$POP/$JOB; dst=$E/jobs/$JOB-$POP
  mkdir -p "$dst/am3g/sessions"
  for f in job.env termination.env manifest.json command.json model-verification.txt \
    provenance-verification.txt gpu-prolog.env container-doctor.txt gpu-compute-apps-prolog.csv; do
    [[ -f $src/$f ]] && cp "$src/$f" "$dst/"; done
  sha256sum "$src/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"
  sha256sum "$src/study-artifact.json" | cut -d" " -f1 > "$dst/study-artifact.sha256"
  scontrol show job "$JOB" 2>/dev/null | grep -E "JobState|RunTime" > "$dst/scontrol.txt" || \
    cp "$R/ops/scontrol-$JOB.txt" "$dst/scontrol.txt" 2>/dev/null || true
  gzip -n -c "$R/runs/$POP/slurm-$JOB.out" > "$dst/slurm-$JOB.out.gz" 2>/dev/null || true
  cp "$src/am3g/summary.json" "$src/am3g/environment.json" "$dst/am3g/"
  gzip -n -c "$src/am3g/gpu-samples.csv" > "$dst/am3g/gpu-samples.csv.gz" 2>/dev/null || true
  for w in "$src"/am3g/sessions/*/; do
    wn=$(basename "$w"); mkdir -p "$dst/am3g/sessions/$wn"
    cp "$w"/{session.json,done.json,worker-progress.jsonl} "$dst/am3g/sessions/$wn/" 2>/dev/null || true
    for m in "$w"/*.json; do
      case "$(basename "$m")" in session.json|done.json) continue;; esac
      gzip -n -c "$m" > "$dst/am3g/sessions/$wn/$(basename "$m").gz"; done
    ( cd "$w" && find . -maxdepth 1 -type f \( -name "*.npz" -o -name "*.texts.jsonl.gz" \) -print0 \
      | sort -z | xargs -0 -r sha256sum ) > "$dst/am3g/sessions/$wn/raw-sha256.txt"
  done
  for f in "$src"/am3g/worker-*.log; do gzip -n -c "$f" > "$dst/am3g/$(basename "$f").gz"; done
  if [[ -f "$src/am3g/judge-items.json" ]]; then
    ( cd "$src/am3g" && sha256sum judge-items.json ) > "$dst/am3g/judge-items.sha256.txt"
    python3 - "$src/am3g/judge-items.json" "$dst/am3g/judge-items-public.json" <<'PY'
import hashlib, json, sys
items = json.load(open(sys.argv[1]))
drop = {"response", "explanation"}
out = [{k: v for k, v in i.items() if k not in drop} | {
    "response_sha256": hashlib.sha256(i["response"].encode()).hexdigest()} for i in items]
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PY
    gzip -n "$dst/am3g/judge-items-public.json"
  fi
  cp "$R/manifests/$POP-$SHORT".{yaml,dry-run.json,test-only.txt} "$E/manifests/" 2>/dev/null || true
  cp "$R/manifests/$POP-$SHORT".submit.txt "$R/manifests/$POP-$SHORT".rerun.txt "$E/manifests/" 2>/dev/null || true
  mkdir -p "$E/selftests/$POP-$SHORT"
  cp "$R/selftest-$POP-$SHORT"/{exits.txt,am3g-selftest.json,am3g-plan.json} "$E/selftests/$POP-$SHORT/" 2>/dev/null || true
  cp "$R/extract-$POP-$SHORT".{log,json} "$E/logs/" 2>/dev/null || true
  gzip -n -c "$R/extract-$POP-$SHORT.stderr" > "$E/logs/extract-$POP-$SHORT.stderr.gz" 2>/dev/null || true
done
for s in "$R"/selftest-abstention-"$SHORT" "$R"/selftest-heldout-"$SHORT" "$R"/selftest-development-"$SHORT"; do
  [[ -d $s ]] || continue
  mkdir -p "$E/selftests/$(basename "$s")"
  cp "$s"/{exits.txt,am3g-selftest.json,am3g-plan.json} "$E/selftests/$(basename "$s")/" 2>/dev/null || true
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
cp "$R"/ops/jobs.log "$R"/ops/preflight.log "$E/ops/" 2>/dev/null || true
cp "$R"/ops/slurm-selftest-*.out "$E/selftests/" 2>/dev/null || true
cp "$R"/prepare/* "$E/prepare/" 2>/dev/null || true
if [[ -d $R/out-$SHORT-a ]]; then
  cp "$R"/out-"$SHORT"-a/* "$E/"
  cp "$R/analyze-$SHORT.log" "$R/pytest-$SHORT.log" "$E/logs/" 2>/dev/null || true
  for f in "$R"/analyze-"$SHORT"-a.stderr "$R"/dryrun-compare-"$SHORT".stderr "$R"/power-"$SHORT".stderr; do
    [[ -f $f ]] && gzip -n -c "$f" > "$E/logs/$(basename "$f").gz"; done
fi
# The abstention artifact's summary is staged in both modes, so its texts are searched too.
[[ -r $ABS_ART ]] && ARTS+=("$ABS_ART")
# $HOME is written as ~ in records and logs.
grep -rl "$HOME" "$E" | xargs -r sed -i "s#$HOME#~#g"
# No reply text, question, explanation, decoy answer or memory text in the staged tree.
python3 - "$E" "$R/runs" "${ARTS[@]}" <<'PY'
import gzip, json, pathlib, sys
stage, runs = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
texts = set()
for f in runs.glob("*/*/am3g/sessions/rd-*/all.texts.jsonl.gz"):
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
