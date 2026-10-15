#!/usr/bin/env bash
# Kimi-K2.6 fetch: stage the text-only evidence on the host: the lane's records and receipt, the
# Hub listing it was checked against (a trimmed model-info, no model-card or licence text), the
# cross-check, the runtime-source digests, the ops scripts and logs. No weights, no Hub text files.
# Usage: kimi-stage-evidence.sh <job id>
set -Eeuo pipefail
J="${1:?job id}"
R=/home/kevin/cotcodec-runs/stage0/kimi-k26-fetch
L=/home/kevin/cotcodec-runs/model-fetch/cpu-$J
E=$R/evidence-stage
rm -rf "$E"; mkdir -p "$E"/{models,hub,runtime,ops}
cp "$L/receipt.json" "$L/summary.jsonl" "$E/models/"
cp /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts-cpu-lane/kimi-k2.6.json "$E/models/kimi-k2.6.receipt.json"
gzip -n -c "$L/kimi-k2.6.log" > "$E/models/kimi-k2.6.log.gz"
gzip -n -c "/home/kevin/cotcodec-runs/model-fetch/slurm-cotcodec-fetch-cpu-$J.out" > "$E/models/slurm-$J.out.gz"
cp "$R"/ops/scontrol-"$J"-*.txt "$E/models/"
cp "$R/crosscheck-$J.json" "$E/models/crosscheck.json"
cp "$R/hub/tree.json" "$E/hub/tree-7eb5002f.json"
python3 -I - "$R/hub/model-info.json" "$E/hub/model-info-7eb5002f.min.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
cfg = d.get("config") or {}
keep = {k: d.get(k) for k in ("id", "sha", "gated", "private", "disabled", "lastModified",
                              "createdAt", "library_name", "pipeline_tag", "safetensors")}
keep["license_tags"] = [t for t in d.get("tags", []) if t.startswith("license") or t == "custom_code"]
keep["card_license"] = {k: (d.get("cardData") or {}).get(k) for k in ("license", "license_name")}
keep["config"] = {k: cfg.get(k) for k in ("architectures", "model_type", "auto_map")}
json.dump(keep, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PY
( cd "$R/hub/text" && sha256sum LICENSE THIRD_PARTY_NOTICES.md README.md config.json \
  docs_deploy_guidance.md generation_config.json ) > "$E/hub/text-files-read.sha256"
cp "$R/runtime-sources.json" "$E/runtime/"
cp "$R"/ops/*.sh "$R"/ops/*.py "$R/ops/jobs.log" "$R/ops/preflight.log" "$R/ops/progress.log" "$E/ops/"
# $HOME is written as ~ in records and logs; the ops scripts are kept exactly as they ran.
grep -rlI --exclude-dir=ops "$HOME" "$E" | xargs -r sed -i "s#$HOME#~#g"
find "$E" -type f | sort | xargs sha256sum | sed "s#$E/##" > "$R/evidence-stage.sha256"
du -sh "$E"; wc -l < "$R/evidence-stage.sha256"
