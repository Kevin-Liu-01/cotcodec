"""Read-only: job 730's chunk durations against their units' context lengths and options."""
import hashlib, json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import numpy as np
from harness import dense_headroom_data as dhd
run = Path(sys.argv[2])
artifact = json.loads((run / "dense-precheck" / "dev-artifact.json").read_text())
view = dhd.DevView(artifact)
units = dhd.plan_units(view.prompts)
stage = [u for u in units if u.stage == "A-main"]
rows = []
for start in range(0, len(stage), 16):
    chunk = stage[start:start + 16]
    name = hashlib.sha256("|".join(u.unit_id for u in chunk).encode()).hexdigest()[:16]
    path = run / "dense-precheck" / "checkpoints" / "eval" / "A-main" / f"chunk-{name}.npz"
    if not path.exists():
        break
    lengths = [int(view.contexts[u.context_index]["length"]) + len(view.query(u.query_index)) for u in chunk]
    opts = [len(view.options(u.query_index)[0][i]) for u in chunk for i in range(4)]
    fwd = [n for n in opts if n > 1]
    one = [n for n in opts if n == 2]
    rows.append((path.stat().st_mtime, start // 16, float(np.mean(lengths)), len(fwd), int(sum(n - 1 for n in fwd)), len(one)))
prev = None
print("chunk seconds mean_len option_forwards option_tokens one_step_options")
for mtime, idx, mean_len, nfwd, ntok, none in rows:
    dur = None if prev is None else mtime - prev
    print(idx, None if dur is None else round(dur, 1), round(mean_len), nfwd, ntok, none)
    prev = mtime
