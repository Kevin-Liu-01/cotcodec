#!/usr/bin/env bash
# AM5: on the host, merge the labeller's output into the final labels (once) and write the
# text-free receipt to $R/hand-check: the labeller's model and launch, the pinned prompt's,
# instructions', sample's, plan's, chunk's, transcript's and labels' digests, the audit, the counts.
# $R/hand-check is committed to the repository before am5-analyze.sh joins the labels.
# Usage: am5-hand-merge.sh <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"
check_checkout "$SHORT"
H="$R/hand"
[[ -f "$R/hand-check/hand-audit-01.json" && -f "$H/transcript-first-01.jsonl" ]] || { echo "no audit or transcript" >&2; exit 2; }
uv run --locked --offline python scripts/memcredit_am5.py hand-merge --hand-dir "$H" > "$R/hand-check/hand-merge-${SHORT}.json"
sha256sum "$H/hand-labels.jsonl" | cut -d" " -f1 > "$R/hand-check/hand-labels.sha256.txt"
python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['plan_sha256'])" "$H/hand-manifest.json" > "$R/hand-check/hand-plan.sha256.txt"
python3 - "$H" "$R/hand-check" <<'PY'
import hashlib, json, pathlib, sys
h, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((h / "hand-manifest.json").read_text())
audit = json.loads((out / "hand-audit-01.json").read_text())
merge = json.loads(next(out.glob("hand-merge-*.json")).read_text())
if audit["audit"]["transcript_sha256"] != digest(h / "transcript-first-01.jsonl"):
    sys.exit("the host's transcript differs from the audited one")
receipt = {
    "experiment_id": "am5-evidence-ablated-dev",
    "labeller_model": manifest["labeller_model"],
    "labeller_launch": "one Claude Code subagent of the operator session, fresh context, pinned prompt",
    "labeller_prompt_sha256": manifest["labeller_prompt_sha256"],
    "instructions_sha256": manifest["instructions_sha256"],
    "sample_sha256": manifest["sample_sha256"],
    "plan_sha256": manifest["plan_sha256"],
    "chunks": [{k: c[k] for k in ("chunk", "chunk_sha256", "output")} | {"items": len(c["items"])}
               for c in manifest["first"]],
    "transcript_sha256": digest(h / "transcript-first-01.jsonl"),
    "audit": audit,
    "merge": merge,
    "labels_sha256": digest(h / "hand-labels.jsonl"),
}
(out / "hand-receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
print(json.dumps({"pass": audit["audit"]["pass"], "labelled": merge["labelled"],
                  "items": merge["items"], "labels_sha256": receipt["labels_sha256"]}))
PY
chmod a-w "$H"/* "$H"
log_job "hand-merge and receipt at ${SHORT}: labels $(cut -c1-16 "$R/hand-check/hand-labels.sha256.txt")"
