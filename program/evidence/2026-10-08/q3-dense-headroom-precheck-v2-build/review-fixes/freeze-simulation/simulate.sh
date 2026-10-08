#!/usr/bin/env bash
# One freeze simulation of q3-dense-headroom-precheck-v2 on a fresh scratch clone.
# Usage: simulate.sh MODE   (full | status-only | wrong-dec). Never touches the real ledger.
set -uo pipefail
mode=$1
here=$(cd "$(dirname "$0")" && pwd)
clone="$here/clone-$mode"
rm -rf "$clone"
git clone -q --branch stage0/q3-dense-v2 /Users/kevinliu/repos/cotcodec "$clone"
cd "$clone"
g() { git -c user.name=freeze-sim -c user.email=freeze-sim@example.invalid "$@"; }
echo "clone of $(git rev-parse HEAD) mode=$mode"
echo "ledger rows before: $(wc -l < program/preregistrations/ledger.jsonl)"
uv sync --offline --locked --extra dev --quiet
python3 "$here/rewrite.py" "$clone" "$mode"
g commit -qam "sim: frozen wording ($mode)"
uv run --offline --quiet python scripts/preregister.py freeze q3-dense-headroom-precheck-v2 \
  program/preregistrations/q3-dense-headroom-precheck-v2.md; echo "freeze exit=$?"
uv run --offline --quiet python scripts/preregister.py verify q3-dense-headroom-precheck-v2 >/dev/null; echo "verify exit=$?"
uv run --offline --quiet python scripts/preregister.py check-chain; echo "check-chain exit=$?"
tail -1 program/preregistrations/ledger.jsonl > "$here/ledger-row-$mode.json"
g add program/preregistrations/ledger.jsonl && g commit -qm "sim: ledger row ($mode)"
echo "simulated freeze commit $(git rev-parse HEAD)"
python3 - <<'PY'
import re
t = " ".join(open("program/preregistrations/q3-dense-headroom-precheck-v2.md").read().split())
for w in ("DRAFT", "wait for the program owner"):
    print(f"frozen file contains {w!r}: {w in t}")
PY
uv run --offline --extra dev --quiet pytest -q -p no:cacheprovider tests/test_dense_headroom_v2_prereg.py \
  tests/test_dense_headroom_prereg.py tests/test_dense_headroom_v2_manifests.py tests/test_preregister.py \
  2>&1 | grep -E "passed|failed|FAILED|AssertionError: " | sed "s#$clone#SCRATCH_CLONE#g"
echo "pytest exit=${PIPESTATUS[0]}"
