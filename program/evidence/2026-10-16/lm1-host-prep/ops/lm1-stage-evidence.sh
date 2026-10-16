#!/usr/bin/env bash
# LM1 host prep: collect the text-free records of the fetches, the image builds, the receipt
# verification and the smoke test into $R/evidence-stage/, for copying into
# program/evidence/2026-10-16/lm1-host-prep/. Model output text (completion.txt, chat.txt) and the
# server logs stay on the host; the smoke rows carry their SHA-256 instead.
# Usage: lm1-stage-evidence.sh <base build root> <overlay build root> <verify job> <smoke run dir>
#        <fetch job>...
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
BASE="${1:?base build root}"; OVL="${2:?overlay build root}"; VJ="${3:?verify job}"; SMOKE="${4:?smoke run dir}"; shift 4
E="$R/evidence-stage"
rm -rf "$E"; mkdir -p "$E/image/base" "$E/image/overlay" "$E/models/receipts" "$E/models/fetch" "$E/models/verify" "$E/smoke" "$E/ops"
for f in build-receipt.json versions.txt manifest.txt ldd-missing.txt runtime-env.txt image-id.txt; do cp "$BASE/$f" "$E/image/base/"; done
gzip -9c "$BASE/docker-build.log" > "$E/image/base/docker-build.log.gz"
python3 - "$BASE/image-inspect.json" "$E/image/base/image-config.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))[0]
keep = {k: d[k] for k in ("Id", "RepoTags", "RepoDigests", "Created", "Size", "Architecture", "Os")}
keep["Config"] = {k: d["Config"].get(k) for k in ("Env", "Entrypoint", "Cmd", "Labels", "WorkingDir")}
keep["RootFS_layers"] = len(d.get("RootFS", {}).get("Layers", []))
json.dump(keep, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PY
for f in build-receipt.json image-id.txt provenance-verification.json plan-check.json llama-server-version.txt source-validation.json; do cp "$OVL/$f" "$E/image/overlay/"; done
gzip -9c "$OVL/llamacpp-overlay.log" > "$E/image/overlay/llamacpp-overlay.log.gz"
for id in $LM1_IDS; do cp "$RECEIPTS/$id.json" "$E/models/receipts/"; done
for j in "$@"; do
  mkdir -p "$E/models/fetch/$j"
  cp /home/kevin/cotcodec-runs/model-fetch/cpu-$j/{receipt.json,summary.jsonl} "$E/models/fetch/$j/"
  for log in /home/kevin/cotcodec-runs/model-fetch/cpu-$j/*.log; do
    tr '\r' '\n' < "$log" | grep -av "^\s*$" | tail -n 200 | gzip -9c > "$E/models/fetch/$j/$(basename "$log").tail.gz"
  done
done
cp /home/kevin/cotcodec-runs/model-fetch/verify-$VJ/{receipt.json,summary.jsonl} "$E/models/verify/"
cp "$R"/ops/*.sh "$R"/ops/*.py "$R"/ops/jobs.log "$R"/ops/preflight.log "$R"/ops/progress.log "$E/ops/" 2>/dev/null || true
cp "$R"/ops/scontrol-*-{start,end}.txt "$E/ops/" 2>/dev/null || true
for f in "$R"/ops/slurm-*.out /home/kevin/cotcodec-runs/model-fetch/slurm-*-{"$VJ"}.out; do
  [[ -f "$f" ]] && tail -n 60 "$f" > "$E/ops/$(basename "$f").tail.txt" || true
done
cp "$R"/manifests/smoke-*.{yaml,dry-run.json,test-only.txt,submit.txt} "$E/smoke/" 2>/dev/null || true
# The lane's run directory: text-free records only (as G3 committed its lane jobs).
for f in command.json container-doctor.txt gpu-prolog.env gpu-compute-apps-prolog.csv job.env \
  manifest.json model-verification.txt provenance-verification.txt termination.env; do
  [[ -f "$SMOKE/$f" ]] && cp "$SMOKE/$f" "$E/smoke/" || true
done
[[ -f "$SMOKE/container.log" ]] && gzip -9c "$SMOKE/container.log" > "$E/smoke/container.log.gz"
[[ -f "$SMOKE/docker-research.sbatch" ]] && sha256sum "$SMOKE/docker-research.sbatch" | cut -d' ' -f1 > "$E/smoke/docker-research.sbatch.sha256"
mkdir -p "$E/smoke/lm1smoke"
for f in results.jsonl summary.json; do cp "$SMOKE/lm1smoke/$f" "$E/smoke/lm1smoke/" 2>/dev/null || true; done
find "$E" -type f | sort | xargs sha256sum > "$E/SHA256SUMS.txt"
du -sh "$E"
