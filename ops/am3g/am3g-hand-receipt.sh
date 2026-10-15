#!/usr/bin/env bash
# am3-nonabstain-generality-v1: receipt one labelling stage of the blind hand check before the
# join (registration section 8). The receipt (text-free) carries the labeller's model, its launch
# (cli or subagent) and pinned prompt digest, the instructions' and sample's digests, the plan
# digest, every chunk's transcript digest, the merge record (with each transcript's audit), the
# stage's raw labels digest and, when the stage wrote them, the final labels' digest. It goes to
# $R/hand-check/, to be committed to the repository before am3g-analyze.sh joins the labels (the
# commit id is passed to am3g-analyze.sh as RECEIPT_COMMIT). The labels and transcripts stay on
# the host (they may quote LongMemEval text).
# Reads records only; it runs no repository code. Refuses a second receipt of a stage.
# Usage: am3g-hand-receipt.sh dev|reg <commit short id> first|repair
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; STAGE="${3:?first or repair}"
H="$R/hand"; OUT="$R/hand-check/hand-receipt-${STAGE}.json"
mkdir -p "$R/hand-check"
[[ ! -e "$OUT" ]] || { echo "stage $STAGE already receipted" >&2; exit 2; }
[[ -f "$H/hand-labels-${STAGE}-raw.jsonl" && -f "$H/transcripts-${STAGE}.sha256" ]] \
  || { echo "stage $STAGE is not merged, or has no transcript digests" >&2; exit 2; }
python3 - "$H" "$STAGE" "$OUT" "$R/hand-merge-${STAGE}-${SHORT}.json" <<'PY'
import hashlib, json, pathlib, sys
h, stage, out, merged = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((h / "hand-manifest.json").read_text())
transcripts = [line.split() for line in (h / f"transcripts-{stage}.sha256").read_text().splitlines()
               if line.strip()]
final = h / "hand-labels.jsonl"
receipt = {
    "experiment_id": "am3-nonabstain-generality-v1",
    "stage": stage,
    "labeller_model": manifest["labeller_model"],
    "labeller_launch": ((h / f"labeller-{stage}.txt").read_text().strip()
                        if (h / f"labeller-{stage}.txt").is_file() else None),
    "cli_error_sha256": (digest(h / f"labeller-{stage}-cli-error.txt")
                         if (h / f"labeller-{stage}-cli-error.txt").is_file() else None),
    "labeller_prompt_sha256": manifest["labeller_prompt_sha256"],
    "instructions_sha256": manifest["instructions_sha256"],
    "sample_sha256": manifest["sample_sha256"],
    "plan_sha256": manifest["plan_sha256"],
    "chunks": [{"chunk": c["chunk"], "chunk_sha256": c["chunk_sha256"], "output": c["output"],
                "items": len(c["items"])} for c in manifest[stage]],
    "transcripts_sha256": {name: d for d, name in transcripts},
    "raw_labels_sha256": digest(h / f"hand-labels-{stage}-raw.jsonl"),
    "merge": json.loads(pathlib.Path(merged).read_text()),
    "final_labels_sha256": digest(final) if final.is_file() else None,
    "labeller": "an isolated Claude agent per chunk, blind to every judge label, rule identity, "
                "reader and outcome (D9: agent labels, not human)",
    "joined": False,
}
pathlib.Path(out).write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
if receipt["final_labels_sha256"]:
    (pathlib.Path(out).parent / "hand-labels.sha256.txt").write_text(
        f"{receipt['final_labels_sha256']}  hand-labels.jsonl\n")
    (pathlib.Path(out).parent / "hand-plan.sha256.txt").write_text(
        f"{receipt['plan_sha256']}  plan\n")
print(json.dumps({k: receipt[k] for k in ("stage", "raw_labels_sha256", "final_labels_sha256",
                                          "plan_sha256", "labeller_prompt_sha256")}, indent=1))
PY
log_job "hand labels receipted, stage ${STAGE}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('raw',d['raw_labels_sha256'][:16],'final',(d['final_labels_sha256'] or 'none')[:16])" "$OUT")"
