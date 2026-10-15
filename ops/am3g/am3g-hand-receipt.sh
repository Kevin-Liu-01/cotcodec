#!/usr/bin/env bash
# am3-nonabstain-generality-v1: receipt the blind hand labels before the join (registration
# section 8): the labels file's SHA-256 and a text-free receipt go to $R/hand-check/, to be
# committed to the repository before am3g-analyze.sh joins the labels to the judge. The labels
# file itself stays on the host (its notes may quote LongMemEval text). Refuses a second receipt.
# Usage: am3g-hand-receipt.sh dev|reg <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
L="$R/private/hand-labels.jsonl"; S="$R/private/hand-check-sample.jsonl"
mkdir -p "$R/hand-check"
[[ ! -e "$R/hand-check/hand-labels.sha256.txt" ]] || { echo "already receipted" >&2; exit 2; }
[[ -f "$L" && -f "$S" ]] || { echo "no labels or sample" >&2; exit 2; }
chmod a-w "$L"
(cd "$R/private" && sha256sum hand-labels.jsonl) > "$R/hand-check/hand-labels.sha256.txt"
python3 - "$L" "$S" "$R/hand-check/hand-labels-receipt.json" "$R/hand-sample-${SHORT}.json" <<'PY'
import hashlib, json, sys
labels, sample, out, drawn = sys.argv[1:]
rows = [json.loads(x) for x in open(labels, encoding="utf-8") if x.strip()]
items = [json.loads(x)["item_id"] for x in open(sample, encoding="utf-8") if x.strip()]
receipt = {
    "experiment_id": "am3-nonabstain-generality-v1",
    "file": "hand-labels.jsonl",
    "sha256": hashlib.sha256(open(labels, "rb").read()).hexdigest(),
    "rows": len(rows),
    "fields": sorted({k for r in rows for k in r}),
    "label_counts": {str(v): sum(1 for r in rows if r.get("label") == v) for v in (0, 1)},
    "same_item_order_as_sample": [r.get("item_id") for r in rows] == items,
    "sample": {"file": "hand-check-sample.jsonl",
               "sha256": hashlib.sha256(open(sample, "rb").read()).hexdigest(),
               "rows": len(items)},
    "hand_sample_record": json.load(open(drawn)),
    "labeller": "an isolated agent, blind to every judge label, rule identity, reader and outcome "
                "(D9: agent labels, not human)",
    "joined": False,
    "receipted_before_join": "this receipt and hand-labels.sha256.txt are committed before "
                             "am3g-analyze.sh joins the labels",
}
json.dump(receipt, open(out, "w"), indent=1, sort_keys=True)
PY
cat "$R/hand-check/hand-labels.sha256.txt"
log_job "hand labels receipted at ${SHORT}: $(cut -c1-16 "$R/hand-check/hand-labels.sha256.txt")"
