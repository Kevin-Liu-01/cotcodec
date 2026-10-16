#!/usr/bin/env bash
# Stage the g3-state-precision-accuracy-v1 evidence on the host: lane receipts, text-free worker
# records, summaries, stats and progress logs, and the SHA-256 of the raw outputs that stay on the
# host (texts.jsonl.gz, tokens.npz, the judge input and the judge's replies). G2c's
# ops/stage-evidence.sh, adapted.
# Usage: stage-evidence.sh  (writes $R/evidence-stage)
set -Eeuo pipefail
R=/home/kevin/cotcodec-runs/stage0/g3-state-precision-accuracy
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests,probe}
lane=(job.env termination.env manifest.json command.json model-verification.txt provenance-verification.txt gpu-prolog.env container-doctor.txt)
copyjob() {  # <run dir> <dest>
  local src=$1 dst=$2 id; id=$(basename "$src"); mkdir -p "$dst"
  for f in "${lane[@]}"; do [[ -f $src/$f ]] && cp "$src/$f" "$dst/"; done
  [[ -f $src/docker-research.sbatch ]] && sha256sum "$src/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"
  if grep -q "^JobId=$id " "$R/ops/scontrol-$id.txt" 2>/dev/null; then cp "$R/ops/scontrol-$id.txt" "$dst/scontrol.txt"
  else scontrol show job "$id" > "$dst/scontrol.txt" 2>/dev/null || echo "scontrol record for $id expired before collection (Slurm accounting is off)" > "$dst/scontrol.txt"; fi
  [[ -f $src/container.log ]] && gzip -c "$src/container.log" > "$dst/container.log.gz"
}
for d in $R/runs/*/[0-9]*; do
  kind=$(basename "$(dirname "$d")"); id=$(basename "$d"); dst=$E/jobs/$id-$kind
  copyjob "$d" "$dst"
  for o in g3 g3judge; do
    [[ -d $d/$o ]] || continue
    mkdir -p "$dst/$o"
    find "$d/$o" -maxdepth 1 -type f \( -name "summary.json" -o -name "environment.json" -o -name "labels.json" \) -exec cp {} "$dst/$o/" \;
    find "$d/$o" -maxdepth 1 -type f -name "*.log" -exec sh -c 'gzip -c "$1" > "$2/$(basename "$1").gz"' _ {} "$dst/$o" \;
    for w in "$d/$o"/*/; do
      [[ -f $w/records.json || -f $w/engine.json ]] || continue
      wn=$(basename "$w"); mkdir -p "$dst/$o/$wn"
      cp "$w"/{engine.json,summary.json,worker-progress.jsonl,records.json,done.json} "$dst/$o/$wn/" 2>/dev/null || true
      cp "$w"/phase-stats.npz "$w"/phase-stats.metrics.jsonl "$dst/$o/$wn/" 2>/dev/null || true
    done
    ( cd "$d/$o" && find . -type f \( -name "*.npz" ! -name "phase-stats.npz" -o -name "texts.jsonl.gz" -o -name "judge-texts.jsonl.gz" \) ! -path "./cache/*" -print0 | sort -z | xargs -0 -r sha256sum ) > "$dst/$o/raw-sha256.txt"
  done
done
for S in $(ls $R | sed -n 's/^overlay-build-vllm-//p'); do
  cp $R/overlay-build-vllm-$S/build-receipt.json $E/builds/vllm-overlay-$S-build-receipt.json 2>/dev/null || true
done
python3 - "$R" "$E" <<'PY'
import hashlib, json, pathlib, sys
R, E = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out = {}
for rec in sorted((R / "capsule").glob("source-receipt-*.json")):
    tag = rec.stem.split("-")[-1]
    d = json.loads(rec.read_text())
    out[tag] = {k: v for k, v in d.items() if not isinstance(v, (list, dict))}
    out[tag]["receipt_sha256"] = hashlib.sha256(rec.read_bytes()).hexdigest()
    out[tag]["archive_sha256_recomputed"] = hashlib.sha256((R / "capsule" / f"source-{tag}.tar.gz").read_bytes()).hexdigest()
(E / "builds" / "source-capsules.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
PY
for s in $R/ops/slurm-vllm-overlay-*.out; do [[ -f $s ]] && tail -n 5 "$s" > "$E/builds/$(basename $s).tail.txt"; done
cp $R/ops/scontrol-build-*.txt $E/builds/ 2>/dev/null || true
for d in $R/selftest-*; do [[ -d $d ]] || continue; n=$(basename $d); mkdir -p $E/selftests/$n; cp $d/*.json $d/*.txt $E/selftests/$n/ 2>/dev/null || true; done
cp $R/probe/lme-lengths/stdout.json $E/probe/lme-lengths-stdout.json 2>/dev/null || true
cp $R/probe/lme-lengths/lme-lengths.json $E/probe/lme-lengths.json 2>/dev/null || true
cp $R/manifests/* $E/manifests/ 2>/dev/null || true
cp $R/ops/jobs.log $R/ops/preflight.log $E/ops/ 2>/dev/null || true
for f in $R/judge-input/*.json; do [[ -f $f ]] && sha256sum "$f" >> $E/ops/judge-input-sha256.txt; done
grep -rlE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" $E --include=*.json --include=*.txt --include=*.env --include=*.jsonl --include=*.yaml | while read f; do echo "IPCHECK $f: $(grep -oE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" $f | sort -u | tr "\n" " ")"; done || true
du -sh $E; find $E -type f | wc -l
