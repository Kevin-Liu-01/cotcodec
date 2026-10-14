#!/usr/bin/env bash
# collect.sh JOB: headroom check, collect_k1.sh, campaign summary, print the check's key fields.
set -u
J="$1"
S=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/s2v5-ops
EV=/Users/kevinliu/repos/cotcodec-wt-ops-s2v5/program/evidence/2026-10-14/s2v5-phase0-run
until headroom can-start --gb 3 --label s2v5-phase0 >/dev/null; do echo "headroom hold"; sleep 30; done
bash $EV/ops/collect_k1.sh "$J" 2>&1 | tail -2 || exit 1
(cd $S/export-7c963f51 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. perl -e 'alarm shift; exec @ARGV' 200 /Users/kevinliu/repos/cotcodec/.venv/bin/python $EV/campaign_summary.py $S/jobs/$J/[0-9][0-9]-*/) > $EV/k1-jobs/$J/summary-$J.jsonl
python3 - "$EV/k1-jobs/$J/check-$J.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print("CHECK", d["check"], "part", d["part"], "cells", d["cells"], "exec", d["executor_commit"][:8])
print("OWN", json.dumps(d["own_check_on_this_job"], sort_keys=True)[:700])
cs=d["campaigns"]
print("NCAMP", len(cs), "TRIALS", sum(c["trials"] for c in cs), "PASSED", sum(c["trials_passed"] for c in cs), "COUNT_OK", all(not c["counting_problems"] and not c["foreign_abort"] and not c["snapshot_problems"] and c["infra_gates_pass"] and c["qcow2_unchanged"] and c["batch_end"].get("driver_exit")==0 and c["batch_end"].get("labelled_containers_left")==0 and not c["labelled_containers_left"] for c in cs), "BOOTMAX", max(c["boot_s_max"] or 0 for c in cs), "STEPP95", [c["step_p95_s"] for c in cs][:20])
for c in (cs if len(cs) <= 4 else []):
    print({k:c[k] for k in ["dir","sessions","trials","trials_passed","boot_s_max","step_p95_s","infra_gates_pass","qcow2_unchanged","labelled_containers_left","batch_end","counting_problems","foreign_abort","snapshot_problems"]})
print("RECEIPT_EXITS", sorted({c.get("driver_exit") for c in d["receipt_campaigns"]}), len(d["receipt_campaigns"]))
print("PREFLIGHT_END", d["job_preflight"][-1])
PY
grep -E 'JobState|ExitCode|RunTime|StartTime' $EV/k1-jobs/$J/scontrol-$J.last.txt
echo SUMMARY; python3 -c "import json,sys
for l in open(sys.argv[1]):
    d=json.loads(l); d.pop('entries_per_app',None); print(json.dumps(d)[:600])" $EV/k1-jobs/$J/summary-$J.jsonl
