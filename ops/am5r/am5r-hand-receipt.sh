#!/usr/bin/env bash
# am5-ablated-cost-v1: receipt one labelling stage of the blind hand check before the
# join (registration section 8). It refuses a stage without a launch record, a subagent launch
# without the CLI's recorded failure, and a transcript whose digest on the Mac differs from the
# merge audit's. The receipt (text-free) carries the labeller's model, its launch (cli or
# subagent), the labelling attempts per chunk, the agent ids, models, first-prompt digests and
# times the audit found, the context's instruction-file names, the pinned prompt digest, the
# instructions', sample's and plan's digests, every chunk's transcript digest, the merge record
# (with each transcript's audit), the stage's raw labels digest and, when the stage wrote them,
# the final labels' digest. It goes to $R/hand-check/ with the sample's and merge's records, the
# manifest and the plan, all text-free; R/hand-check/ is committed, as the run's evidence directory's
# hand-check/, before am5r-analyze.sh joins the labels (that commit's id is passed to
# am5r-analyze.sh as RECEIPT_COMMIT). The labels and transcripts stay on the host (they may quote
# LongMemEval text).
# Reads records only; it runs no repository code. Refuses a second receipt of a stage.
# Usage: am5r-hand-receipt.sh dev|reg <commit short id> first|repair
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; STAGE="${3:?first or repair}"
H="$R/hand"; OUT="$R/hand-check/hand-receipt-${STAGE}.json"
mkdir -p "$R/hand-check"
[[ ! -e "$OUT" ]] || { echo "stage $STAGE already receipted" >&2; exit 2; }
[[ -f "$H/hand-labels-${STAGE}-raw.jsonl" && -f "$H/transcripts-${STAGE}.sha256" ]] \
  || { echo "stage $STAGE is not merged, or has no transcript digests" >&2; exit 2; }
[[ -f "$H/labeller-${STAGE}.json" ]] || { echo "stage $STAGE has no launch record" >&2; exit 2; }
python3 - "$H" "$STAGE" "$OUT" "$R/hand-merge-${STAGE}-${SHORT}.json" <<'PY'
import hashlib, json, pathlib, sys
h, stage, out, merged = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((h / "hand-manifest.json").read_text())
launch = json.loads((h / f"labeller-{stage}.json").read_text())
cli_error = h / f"labeller-{stage}-cli-error.txt"
if launch.get("launch") not in ("cli", "subagent"):
    sys.exit(f"the launch record names no launch: {launch.get('launch')!r}")
if launch["launch"] == "subagent" and not (cli_error.is_file() and launch.get("cli_failed_at")):
    sys.exit("a subagent launch without the CLI's recorded failure")
merge = json.loads(pathlib.Path(merged).read_text())
transcripts = {name: d for d, name in (line.split() for line in
               (h / f"transcripts-{stage}.sha256").read_text().splitlines() if line.strip())}
audits = merge["transcript_audit"]
for n, chunk in enumerate(manifest[stage], start=1):
    name, audit = f"{stage}-{n:02d}.jsonl", audits[chunk["output"]]
    if transcripts.get(name) != audit.get("transcript_sha256"):
        sys.exit(f"{name}: the Mac's transcript digest differs from the merge audit's")
final = h / "hand-labels.jsonl"
receipt = {
    "experiment_id": "am5-ablated-cost-v1",
    "stage": stage,
    "labeller_model": manifest["labeller_model"],
    "labeller_launch": launch["launch"],
    "cli_error_sha256": digest(cli_error) if cli_error.is_file() else None,
    "cli_failed_at": launch.get("cli_failed_at"),
    "labelling_attempts": launch.get("attempts"),
    "matching_subagent_transcripts": launch.get("matching_total"),
    "subagent_transcripts_scanned": launch.get("subagent_transcripts_scanned"),
    "labeller_prompt_sha256": manifest["labeller_prompt_sha256"],
    "instructions_sha256": manifest["instructions_sha256"],
    "sample_sha256": manifest["sample_sha256"],
    "plan_sha256": manifest["plan_sha256"],
    "chunks": [{"chunk": c["chunk"], "chunk_sha256": c["chunk_sha256"], "output": c["output"],
                "items": len(c["items"]),
                "agent_ids": audits[c["output"]].get("agent_ids"),
                "models": audits[c["output"]].get("models"),
                "first_prompt_sha256": audits[c["output"]].get("first_prompt_sha256"),
                "first_timestamp": audits[c["output"]].get("first_timestamp"),
                "audit_pass": audits[c["output"]]["pass"]} for c in manifest[stage]],
    "context_instruction_files": sorted({tuple(f) for a in audits.values()
                                         for f in a.get("instruction_files") or []}),
    "transcripts_sha256": transcripts,
    "raw_labels_sha256": digest(h / f"hand-labels-{stage}-raw.jsonl"),
    "merge": merge,
    "void": merge.get("void"),
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
print(json.dumps({k: receipt[k] for k in ("stage", "labeller_launch", "labelling_attempts",
                                          "raw_labels_sha256", "final_labels_sha256",
                                          "plan_sha256", "void")}, indent=1))
PY
# The text-free records that go with the receipt: committed with it (R/hand-check/ is committed
# as the run's evidence directory's hand-check/, which am5r-stage-evidence.sh later copies to the
# same path unchanged).
cp -f "$R/hand-sample-${SHORT}.json" "$R/hand-merge-${STAGE}-${SHORT}.json" "$R/hand-check/"
cp -f "$H/hand-manifest.json" "$R/hand-check/hand-manifest.json"
cp -f "$H/hand-plan.json" "$R/hand-check/hand-plan.json"
chmod a-w "$R"/hand-check/*
log_job "hand labels receipted, stage ${STAGE}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('raw',d['raw_labels_sha256'][:16],'final',(d['final_labels_sha256'] or 'none')[:16])" "$OUT")"
