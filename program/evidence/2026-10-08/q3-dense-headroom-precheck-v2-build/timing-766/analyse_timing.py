"""Summarise a timing-receipt.json: per stage per-unit and per-chunk times, components, projection."""
import json
import statistics
import sys
from collections import defaultdict

r = json.load(open(sys.argv[1]))
t = r["timing"]
print("status", t["status"], "signals", json.dumps(r["signals"])[:400])
print("eval started after", round(t["evaluation_started_after_s"], 1), "process", round(t.get("process_seconds", 0), 1))
print("timings", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r["timings_s"].items()})
print("artifact matches 730:", t["dev_artifact_matches_v1_job_730"], r["hashes"]["dev_artifact_sha256"])
by_stage = defaultdict(list)
for u in t["units"]:
    by_stage[(u["stage"], u["phase"])].append(u)
for key, units in sorted(by_stage.items()):
    secs = [u["seconds"] for u in units]
    print(key, "n", len(units), "median", round(statistics.median(secs), 3), "mean", round(statistics.mean(secs), 3),
          "max", round(max(secs), 2), "first", round(secs[0], 2))
    parts = defaultdict(lambda: [0.0, 0.0])
    for u in units:
        for name, p in u["parts"].items():
            parts[name][0] += p["wall_s"]
            parts[name][1] += p["cpu_s"]
    print("   parts per unit (wall, cpu):", {k: (round(v[0] / len(units), 3), round(v[1] / len(units), 3)) for k, v in parts.items()})
for c in t["chunks"]:
    print("chunk", c["stage"], c["chunk"], c["phase"], "prof" if c["profiled"] else "", round(c["seconds"], 2),
          "cpu", round(c["cpu_seconds"], 2), [(b["name"], b["ticks"]) for b in c["busiest_threads"][:3]])
print("reference", t["reference"])
print("torch profiles", {k: v["status"] for k, v in t["torch_profiles"].items()})
