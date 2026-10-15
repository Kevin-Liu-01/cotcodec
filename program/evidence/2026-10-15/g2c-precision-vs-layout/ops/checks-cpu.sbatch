#!/usr/bin/env bash
#SBATCH --job-name=g2c-checks-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
# CPU-only (no GRES) checks of g2c-precision-layout-v1 at a clean checkout (G2C_CHECKOUT): ruff on
# the new files, the full test suite, the architecture and provider validators, and the README's
# seed-42 reproduction command checked against the committed analysis.json. G2C_BASE_CHECKOUT (a
# clean checkout of the branch's G2b merge parent) reruns any test file that fails here, to tell
# a pre-existing failure from one this branch introduced.
set -uo pipefail
: "${G2C_CHECKOUT:?}"; : "${G2C_OUT:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
mkdir -p "$G2C_OUT"
cd "$G2C_CHECKOUT"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
echo "git $(git rev-parse HEAD)"
uv sync --locked --extra dev -q
F="harness/g2c_precision_layout.py scripts/run_g2c_rollouts.py scripts/run_g2c_teacher_force.py scripts/analyze_g2c_precision_layout.py tests/test_g2c_precision_layout.py program/evidence/2026-10-15/g2c-precision-vs-layout/ops/render_manifest.py program/evidence/2026-10-15/g2c-precision-vs-layout/ops/subset_per_token.py"
uv run --locked --extra dev ruff check $F; echo "ruff check exit $?"
uv run --locked --extra dev ruff format --check $F; echo "ruff format exit $?"
uv run --locked --extra dev pytest -q tests/test_g2c_precision_layout.py tests/test_g2b_state_dtype.py 2>&1 | tail -3
uv run --locked --extra dev pytest -q -p no:cacheprovider tests > "$G2C_OUT/pytest-full.txt" 2>&1; echo "full pytest exit $?"
tail -8 "$G2C_OUT/pytest-full.txt"
uv run --locked python scripts/validate_architecture_experiments.py > "$G2C_OUT/validate-architecture.txt" 2>&1; echo "architecture validator exit $?"
uv run --locked python scripts/validate_provider_models.py; echo "provider validator exit $?"
E=program/evidence/2026-10-15
uv run --locked python scripts/analyze_g2c_precision_layout.py analyze \
  --per-token $E/g2c-precision-vs-layout/data/per-token-qwen3.5-4b-seed42.npz \
              $E/g2c-precision-vs-layout/data/per-token-qwen3.5-9b-seed42.npz \
  --g2b-per-token $E/g2b-state-dtype/data/per-token-qwen3.5-4b-seed42.npz \
                  $E/g2b-state-dtype/data/per-token-qwen3.5-9b-seed42.npz \
  --output-dir "$G2C_OUT/repro-seed42" > /dev/null; echo "seed-42 reproduction exit $?"
uv run --locked python - "$E/g2c-precision-vs-layout/analysis/analysis.json" "$G2C_OUT/repro-seed42/analysis.json" <<'PY'
import json, sys
full = json.load(open(sys.argv[1]))["mismatch"]
sub = json.load(open(sys.argv[2]))["mismatch"]
keys = ("tokens", "mean_abs", "p99_abs", "k3", "share_ratio_outside_band", "slope_within_sequences_per_1k")
worst = 0.0
for model in full:
    for arm in ("fp32", "bf16", "fp16", "bf16_b528"):
        a = full[model]["subsets"][f"{arm}/seed_42"]["dec_vs_r1"]
        b = sub[model]["subsets"][f"{arm}/seed_42"]["dec_vs_r1"]
        for k in keys:
            worst = max(worst, abs(a[k] - b[k]) / max(abs(a[k]), 1e-12))
print(f"seed-42 rows, committed subsets vs full analysis: largest relative difference {worst:.3g}")
PY
if [[ -n "${G2C_BASE_CHECKOUT:-}" ]]; then
  failed=$(grep -oE "^FAILED tests/[^:]+" "$G2C_OUT/pytest-full.txt" | sed 's/^FAILED //' | sort -u)
  for t in $failed; do
    (cd "$G2C_BASE_CHECKOUT" && [[ -z "$(git status --porcelain)" ]] && uv sync --locked --extra dev -q && \
      echo "base $(git rev-parse --short=8 HEAD) $t: $(uv run --locked --extra dev pytest -q -p no:cacheprovider "$t" 2>&1 | tail -1)")
  done
fi
echo done
