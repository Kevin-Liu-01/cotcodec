"""Re-derive step 0's reading from the committed files alone (no host, no full screenshots).

The committed rule (``harness/s2_locale/canary_targets_v5.py``, pinned by
``experiments/manifests/s2v5/step0-rule.json``) ran on the host over job 1271's full screenshots
and wrote ``step0-result.json``. The screenshots stay on the host; ``crops/`` holds, for each of
them, the region ``ROI[app]`` the rule reads (RGB, cut by ``tools/crop_rois.py``, which checked on
the host that the rule's luminance of every crop equals its luminance of that region in the full
screenshot). This script:

1. checks every crop's SHA-256 against ``crops/crops-index.json``;
2. rebuilds the observations exactly as ``canary_targets_v5.collect`` builds them, from the
   committed cycle records (``1271/*/cycles/record-NN.json``) and the rule's ``segment`` on each
   before-action crop (the full screenshot's SHA-256 from the index), and checks that they equal
   ``step0-result.json``'s observations;
3. runs the rule's ``decide`` on them with q2's frozen targets and checks that its output equals
   ``step0-result.json`` (every key but ``observations`` and ``rule_files``).

Usage (repository root, standard library only):
  python3 -B program/evidence/2026-10-13/s2v5-step0/rederive.py
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from harness.s2_locale import canary_targets_v5 as R  # noqa: E402

JOB = HERE / "1271"
result = json.loads((HERE / "step0-result.json").read_text(encoding="utf-8"))
index = json.loads((HERE / "crops" / "crops-index.json").read_text(encoding="utf-8"))
by_shot = {i["screenshot"]: i for i in index}
problems = []

for item in index:
    data = (HERE / "crops" / item["crop"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != item["crop_sha256"] or not item["luminance_equal"]:
        problems.append(f"crop {item['crop']}")

observations = []
for sub in sorted(JOB.iterdir()):
    meta = sub / "apdelta.json"
    if not meta.is_file():
        continue
    cells = json.loads(meta.read_text(encoding="utf-8"))["cells"]
    for path in sorted((sub / "cycles").glob("record-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        boot = int(record["cycle"])
        for trial in ((record.get("runner_result") or {}).get("trials")) or []:
            app, entry = str(trial.get("cell", ":")).split(":", 1)
            if app not in R.APPS or entry not in R.ENTRIES:
                continue
            name = f"canary-{int(trial['seq']):03d}-{app}-{entry}.png"
            shot = f"{sub.name}/cycles/shots-{boot:02d}/{name}"
            crop = by_shot.get(shot)
            if crop is None:
                seg = {"ok": False, "error": "no screenshot"}
            else:
                rows = R.read_luminance((HERE / "crops" / crop["crop"]).read_bytes())[2]
                seg = R.segment(rows, app, entry)
                seg["sha256"] = crop["screenshot_sha256"]
            observations.append(
                {
                    "cell": cells[0],
                    "boot": boot,
                    "app": app,
                    "entry": entry,
                    "seq": trial.get("seq"),
                    "screenshot": shot,
                    "infra": trial.get("infra") or [],
                    "text": trial.get("text"),
                    "expect": trial.get("expect"),
                    "pass": trial.get("pass"),
                    "measurement": {k: v for k, v in seg.items() if k != "bands"},
                    "atspi": ((trial.get("measured") or {}).get("extents")),
                }
            )

if observations != result["observations"]:
    problems.append("observations differ from step0-result.json")
q2 = json.loads((ROOT / R.Q2_TARGETS).read_text(encoding="utf-8"))["apps"]
again = json.loads(json.dumps(R.decide(observations, q2)))
committed = {k: v for k, v in result.items() if k not in ("observations", "rule_files")}
if again != committed:
    problems.append("decide() on the re-derived observations differs from step0-result.json")
print(
    json.dumps(
        {
            "crops": len(index),
            "observations": len(observations),
            "reading": again["reading"],
            "decision": again["decision"],
            "exit_labels": again["exit_labels"],
            "problems": problems,
        }
    )
)
sys.exit(1 if problems else 0)
