#!/usr/bin/env bash
# Stage the g3b-long-budget-v1 evidence on the host: lane receipts, text-free worker records,
# summaries, stats and progress logs, and the SHA-256 of the raw outputs that stay on the host
# (texts.jsonl.gz, tokens.npz). G3's ops/stage-evidence.sh, adapted.
# Usage: stage-evidence.sh  (writes $R/evidence-stage)
set -Eeuo pipefail
R=/home/kevin/cotcodec-runs/stage0/g3b-long-budget
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests}
lane=(job.env termination.env manifest.json command.json model-verification.txt provenance-verification.txt gpu-prolog.env container-doctor.txt)
for d in $R/runs/*/[0-9]*; do
  kind=$(basename "$(dirname "$d")"); id=$(basename "$d"); dst=$E/jobs/$id-$kind
  mkdir -p "$dst"
  for f in "${lane[@]}"; do [[ -f $d/$f ]] && cp "$d/$f" "$dst/"; done
  [[ -f $d/docker-research.sbatch ]] && sha256sum "$d/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"
  if [[ -f $R/ops/scontrol-$id.txt ]]; then cp "$R/ops/scontrol-$id.txt" "$dst/scontrol.txt"; fi
  [[ -f $d/container.log ]] && gzip -n -c "$d/container.log" > "$dst/container.log.gz"
  o=$d/g3b
  [[ -d $o ]] || continue
  mkdir -p "$dst/g3b"
  find "$o" -maxdepth 1 -type f \( -name "summary.json" -o -name "environment.json" \) -exec cp {} "$dst/g3b/" \;
  find "$o" -maxdepth 1 -type f -name "*.log" -exec sh -c 'gzip -n -c "$1" > "$2/$(basename "$1").gz"' _ {} "$dst/g3b" \;
  for w in "$o"/*/; do
    [[ -f $w/records.json || -f $w/engine.json ]] || continue
    wn=$(basename "$w"); mkdir -p "$dst/g3b/$wn"
    cp "$w"/{engine.json,summary.json,worker-progress.jsonl,records.json,done.json} "$dst/g3b/$wn/" 2>/dev/null || true
    cp "$w"/phase-stats.npz "$w"/phase-stats.metrics.jsonl "$dst/g3b/$wn/" 2>/dev/null || true
  done
  ( cd "$o" && find . -type f \( -name "tokens.npz" -o -name "texts.jsonl.gz" \) ! -path "./cache/*" -print0 | sort -z | xargs -0 -r sha256sum ) > "$dst/g3b/raw-sha256.txt"
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
cp $R/manifests/* $E/manifests/ 2>/dev/null || true
cp $R/ops/jobs.log $R/ops/preflight.log $R/ops/guard*.log $E/ops/ 2>/dev/null || true
grep -rlE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" $E --include=*.json --include=*.txt --include=*.env --include=*.jsonl --include=*.yaml --include=*.log | while read f; do echo "IPCHECK $f: $(grep -oE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" $f | sort -u | tr "\n" " ")"; done || true
du -sh $E; find $E -type f | wc -l
