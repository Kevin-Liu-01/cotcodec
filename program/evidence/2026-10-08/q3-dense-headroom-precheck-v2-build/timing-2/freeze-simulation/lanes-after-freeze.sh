#!/usr/bin/env bash
# After the full-mode simulation: the entry point's code-table check against the frozen file, the
# 0.6B fill with a stand-in image receipt, the 4B fill refused without the 0.6B receipt and accepted
# with a stand-in one, and the submitter's dry run on both. Usage: lanes-after-freeze.sh OUTDIR
set -uo pipefail
out=$1
clone="$out/clone-full"
cd "$clone"
head=$(git rev-parse HEAD)
src=$(git archive --format=tar "$head" | shasum -a 256 | cut -d' ' -f1)
printf '{"image_id": "sha256:%s", "git_sha": "%s", "source_tar_sha256": "%s"}\n' \
  "$(printf 'f%.0s' $(seq 64))" "$head" "$src" > "$out/image-receipt-standin.json"
uv run --offline --quiet python - <<'PY'
from pathlib import Path
from scripts import run_dense_headroom_precheck_v2 as e
table = e.tabled_code(Path("program/preregistrations/q3-dense-headroom-precheck-v2.md").read_text())
code = e.code_hashes()
print("entry-point code-table check: differing", sorted(n for n in e.CODE_FILES if table.get(n) != code[n]))
PY
run="$out/sim-run"; rm -rf "$run"; mkdir -p "$run"
uv run --offline --quiet python scripts/fill_dense_headroom_precheck_v2_manifests.py --lane qwen3-0.6b-base \
  --image-receipt "$out/image-receipt-standin.json" --output "$run/filled" --run-root "$run/root-0p6b" \
  2>&1 | sed "s#$out#SCRATCH#g"; echo "fill 0.6B exit=${PIPESTATUS[0]}"
uv run --offline --quiet python scripts/fill_dense_headroom_precheck_v2_manifests.py --lane qwen3.5-4b-base \
  --image-receipt "$out/image-receipt-standin.json" --output "$run/filled" --run-root "$run/root-4b" \
  2>&1 | sed "s#$out#SCRATCH#g"; echo "fill 4B without the 0.6B receipt exit=${PIPESTATUS[0]}"
uv run --offline --quiet python - "$run/standin-0p6b-receipt.json" <<'PY'
import copy, json, sys
from pathlib import Path
from harness import dense_headroom_v2 as dv2
from scripts import preregister
row = preregister.verify(dv2.EXPERIMENT_ID)
receipt = copy.deepcopy(dv2.load_v1_small_lane_receipt(Path(".")))
receipt.update({"experiment_id": dv2.EXPERIMENT_ID, "slurm_job_id": "999",
                "slurm_job_id_source": "job.env"})
receipt["hashes"]["preregistration_sha256"] = row["sha256"]
Path(sys.argv[1]).write_text(json.dumps(receipt))
print("stand-in 0.6B receipt: v1 job 727's statistics, bound to stand-in job 999, frozen digest", row["sha256"][:16])
PY
uv run --offline --quiet python scripts/fill_dense_headroom_precheck_v2_manifests.py --lane qwen3.5-4b-base \
  --image-receipt "$out/image-receipt-standin.json" --output "$run/filled" --run-root "$run/root-4b" \
  --small-lane-receipt "$run/standin-0p6b-receipt.json" 2>&1 | sed "s#$out#SCRATCH#g"
echo "fill 4B with the stand-in 0.6B receipt exit=${PIPESTATUS[0]}"
for m in "$run"/filled/*.yaml; do
  diff <(sed -n '/^runtime:/,$p' "experiments/manifests/q3-dense-headroom-precheck-v2/$(basename "$m")") \
       <(sed -n '/^runtime:/,$p' "$m") | grep '^[<>]' | sed "s#$out#SCRATCH#g" | cut -c1-120
  uv run --offline --quiet python scripts/submit_docker_research_job.py "$m" --dry-run > "$run/dry-run-$(basename "$m" .yaml).json" 2>&1
  echo "dry run $(basename "$m") exit=$? gpu_hours=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['gpu_hours'])" "$run/dry-run-$(basename "$m" .yaml).json" 2>/dev/null)"
  grep -o '"--time=[^"]*"' "$run/dry-run-$(basename "$m" .yaml).json"
done
