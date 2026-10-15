#!/usr/bin/env bash
# Stage the g2c-precision-layout-v1 evidence on the host (records, summaries, stats, hashes of
# the raw outputs that stay on the host), as G2b's ops/stage-evidence.sh did.
# Usage: stage-evidence.sh  (writes $R/evidence-stage)
set -Eeuo pipefail
R=/home/kevin/cotcodec-runs/stage0/g2c-precision-layout
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{jobs,builds,manifests,ops,selftests,source-check}
lane=(job.env termination.env manifest.json command.json model-verification.txt provenance-verification.txt gpu-prolog.env container-doctor.txt)
copyjob() {  # <run dir> <dest>
  local src=$1 dst=$2 id; id=$(basename "$src"); mkdir -p "$dst"
  for f in "${lane[@]}"; do [[ -f $src/$f ]] && cp "$src/$f" "$dst/"; done
  [[ -f $src/docker-research.sbatch ]] && sha256sum "$src/docker-research.sbatch" | cut -d" " -f1 > "$dst/docker-research.sbatch.sha256"
  scontrol show job "$id" > "$dst/scontrol.txt" 2>/dev/null || echo "scontrol record for $id expired before collection (Slurm accounting is off)" > "$dst/scontrol.txt"
  [[ -f $src/container.log ]] && gzip -c "$src/container.log" > "$dst/container.log.gz"
}
for d in $R/runs/*/[0-9]*; do
  kind=$(basename "$(dirname "$d")"); id=$(basename "$d"); dst=$E/jobs/$id-$kind
  copyjob "$d" "$dst"
  for o in g2c g2ctf; do
    [[ -d $d/$o ]] || continue
    mkdir -p "$dst/$o"
    find "$d/$o" -maxdepth 1 -type f \( -name "*.json" -o -name "*.jsonl" \) ! -name "tf-input.json" ! -name "tf-*-sequences.json" -exec cp {} "$dst/$o/" \;
    find "$d/$o" -maxdepth 1 -type f -name "*.log" -exec sh -c 'gzip -c "$1" > "$2/$(basename "$1").gz"' _ {} "$dst/$o" \;
    for w in "$d/$o"/*/; do
      [[ -f $w/engine.json || -f $w/summary.json ]] || continue
      wn=$(basename "$w"); mkdir -p "$dst/$o/$wn"
      cp "$w"/{engine.json,summary.json,worker-progress.jsonl,sequences.json,done.json} "$dst/$o/$wn/" 2>/dev/null || true
      cp "$w"/phase-*-stats.npz "$w"/phase-*-stats.metrics.jsonl "$dst/$o/$wn/" 2>/dev/null || true
    done
    ( cd "$d/$o" && find . -type f \( -name "*.npz" -o -name "tf-input.json" -o -name "tf-*.json" -o -name "texts.jsonl.gz" \) ! -path "./cache/*" -print0 | sort -z | xargs -0 -r sha256sum ) > "$dst/$o/raw-sha256.txt"
  done
done
S=3833d544
cp $R/overlay-build-vllm-$S/build-receipt.json $E/builds/vllm-overlay-$S-build-receipt.json 2>/dev/null || true
d=$R/overlay-build-research-$S
if [[ -d $d ]]; then
  { echo "image_id=$(cat $d/image-id.txt)"; echo "image_inspect_sha256=$(sha256sum $d/image-inspect.json | cut -d" " -f1)"; echo "source_validation_sha256=$(sha256sum $d/source-validation.json | cut -d" " -f1)"; echo "build_log_sha256=$(sha256sum $d/source-overlay.log | cut -d" " -f1)"; } > $E/builds/research-overlay-$S.txt
  cp $d/source-validation.json $E/builds/research-overlay-$S-source-validation.json
fi
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
for s in $R/ops/slurm-vllm-overlay-*.out $R/ops/slurm-research-overlay-*.out; do [[ -f $s ]] && tail -n 5 "$s" > "$E/builds/$(basename $s).tail.txt"; done
for d in $R/selftest-*; do [[ -d $d ]] || continue; n=$(basename $d); mkdir -p $E/selftests/$n; cp $d/*.json $d/*.txt $E/selftests/$n/ 2>/dev/null || true; done
cp $R/source-check/* $E/source-check/ 2>/dev/null || true
cp $R/manifests/* $E/manifests/ 2>/dev/null || true
cp $R/ops/jobs.log $R/ops/preflight.log $E/ops/ 2>/dev/null || true
grep -rlE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" $E --include=*.json --include=*.txt --include=*.env --include=*.jsonl --include=*.yaml | while read f; do echo "IPCHECK $f: $(grep -oE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" $f | sort -u | tr "\n" " ")"; done
du -sh $E; find $E -type f | wc -l
