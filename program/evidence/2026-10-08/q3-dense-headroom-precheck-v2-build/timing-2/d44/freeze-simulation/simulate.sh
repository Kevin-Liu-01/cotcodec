#!/usr/bin/env bash
# One freeze simulation of q3-dense-headroom-precheck-v2 after D44 on a fresh scratch clone of a
# commit of the branch (macOS, local). Usage: simulate.sh MODE OUTDIR SHA
# (MODE: full | status-only | wrong-dec | d42-only; see rewrite.py).
# Never touches the real ledger: the clone's ledger is a copy; the real one is hashed before/after.
set -uo pipefail
mode=$1
out=$2
sha=$3
here=$(cd "$(dirname "$0")" && pwd)
real=/Users/kevinliu/repos/cotcodec/program/preregistrations/ledger.jsonl
clone="$out/clone-$mode"
rm -rf "$clone"
echo "real ledger before: $(shasum -a 256 "$real" | cut -c1-16)"
git clone -q --branch stage0/q3-dense-v2 /Users/kevinliu/repos/cotcodec "$clone"
cd "$clone"
git checkout -q -B sim-freeze "$sha"
g() { git -c user.name=freeze-sim -c user.email=freeze-sim@example.invalid "$@"; }
echo "clone of $(git rev-parse HEAD) mode=$mode"
echo "ledger rows before: $(wc -l < program/preregistrations/ledger.jsonl) head $(tail -1 program/preregistrations/ledger.jsonl | python3 -c 'import json,sys; r=json.loads(sys.stdin.read()); print(r["experiment_id"], r["hash"][:16])')"
uv sync --offline --locked --extra dev --quiet
python3 "$here/rewrite.py" "$clone" "$mode"
git diff -U0 program/preregistrations/q3-dense-headroom-precheck-v2.md > "$out/frozen-wording-$mode.diff"
g commit -qam "sim: frozen wording ($mode)"
uv run --offline --quiet python scripts/preregister.py freeze q3-dense-headroom-precheck-v2 \
  program/preregistrations/q3-dense-headroom-precheck-v2.md; echo "freeze exit=$?"
uv run --offline --quiet python scripts/preregister.py verify q3-dense-headroom-precheck-v2 >/dev/null; echo "verify exit=$?"
uv run --offline --quiet python scripts/preregister.py check-chain; echo "check-chain exit=$?"
tail -1 program/preregistrations/ledger.jsonl > "$out/ledger-row-$mode.json"
g add program/preregistrations/ledger.jsonl && g commit -qm "sim: ledger row ($mode)"
echo "simulated freeze commit $(git rev-parse HEAD)"
python3 - <<'PY'
t = " ".join(open("program/preregistrations/q3-dense-headroom-precheck-v2.md").read().split())
for w in ("DRAFT", "wait for the program owner", "still to be done"):
    print(f"frozen file contains {w!r}: {w in t}")
PY
uv run --offline --extra dev --quiet pytest -q -p no:cacheprovider tests/test_dense_headroom_v2_prereg.py \
  tests/test_dense_headroom_prereg.py tests/test_dense_headroom_v2_manifests.py tests/test_preregister.py \
  2>&1 | grep -E "passed|failed|FAILED|AssertionError: " | sed "s#$clone#SCRATCH_CLONE#g"
echo "pytest exit=${PIPESTATUS[0]}"
echo "real ledger after: $(shasum -a 256 "$real" | cut -c1-16)"
