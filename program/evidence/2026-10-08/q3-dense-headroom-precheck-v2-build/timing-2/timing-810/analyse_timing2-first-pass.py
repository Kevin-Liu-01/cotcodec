"""Summarise the second timing job (D42 (ii)) and set the 4B limit by D36's rule.

Runs inside the research image (CPU, network none) so that the lane's own unit plan and token
lengths come from the harness: python analyse_timing2.py RECEIPT DEV_ARTIFACT JOB_ENV TERMINATION_ENV
SCONTROL. Prints a text report and writes analysis.json next to the receipt (or to $ANALYSIS_OUT).

D36's rule: minutes = ceil((2 x full-lane evaluation + start-up) / 60) + 3 (the SIGUSR1 lead).
- Full-lane evaluation: for every stage, its unit count times the larger of (a) the mean of the
  stage's measured first evaluations (cold: every subset/continue unit) and (b) the mean of a
  per-stage least-squares fit seconds ~ a + b x tokens applied to every unit of the stage (the
  lane's own token lengths from the development artifact); plus a 5 s statistics bound.
- Start-up: everything before the first lane unit, from Slurm's StartTime: StartTime to job.env
  started_at, plus the job's time outside the workload process (job.env to termination.env minus
  the process's own seconds; it also holds the epilogue, so this over-counts), plus the process's
  time to its first unit (start-up checks, derivation, model load and the attention backend check).
"""
import datetime as dt
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, "/workspace/cotcodec")
from harness import dense_headroom_data as dhd  # noqa: E402

LEAD_MIN = 3
STATS_BOUND_S = 5.0
CAP_TOTAL = 1.5


def env(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out.setdefault(k, v)
    return out


def ts(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


receipt_path, artifact_path, job_env_path, term_env_path, scontrol_path = map(Path, sys.argv[1:6])
r = json.loads(receipt_path.read_text())
t = r["timing"]
job_env, term_env = env(job_env_path), env(term_env_path)
scontrol = scontrol_path.read_text() if scontrol_path.is_file() else ""
slurm_start = None
for tok in scontrol.split():
    if tok.startswith("StartTime="):
        slurm_start = tok.split("=", 1)[1]
    if tok.startswith("EndTime="):
        slurm_end = tok.split("=", 1)[1]
    if tok.startswith("RunTime="):
        slurm_runtime = tok.split("=", 1)[1]
out = {"status": t["status"], "slurm_job_id": r.get("slurm_job_id"),
       "slurm_job_id_source": r.get("slurm_job_id_source"), "signals": r.get("signals")}
print("status", t["status"], "job", r.get("slurm_job_id"), r.get("slurm_job_id_source"))
print("signals", json.dumps(r.get("signals"))[:600])
print("code git", r["hashes"].get("git_sha"), "source", r["hashes"].get("source_sha256"))
print("timings_s", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r["timings_s"].items()})
print("attention_backends", t.get("attention_backends"), "after check", t.get("attention_backends_after_check"))
print("attention_backend_check", json.dumps(t.get("attention_backend_check")))
print("dev artifact equals job 730's:", t["dev_artifact_matches_v1_job_730"], r["hashes"]["dev_artifact_sha256"])
print("versions", t.get("versions"))
for key in ("model_loaded_after_s", "backend_check_started_after_s", "evaluation_started_after_s",
            "subset_finished_after_s", "process_seconds"):
    print(f"{key}: {t.get(key)}")

# ------------------------------------------------------------------ wall clock
started = ts(job_env["started_at"])
finished = ts(term_env["finished_at"])
job_wall = (finished - started).total_seconds()
outside = job_wall - float(t["process_seconds"])
prolog = 0.0
if slurm_start:
    prolog = (started - dt.datetime.fromisoformat(slurm_start).replace(tzinfo=dt.timezone.utc)).total_seconds()
start_up = prolog + outside + float(t["evaluation_started_after_s"])
out["wall"] = {"slurm_start": slurm_start, "slurm_end": globals().get("slurm_end"),
               "slurm_runtime": globals().get("slurm_runtime"),
               "job_env_started_at": job_env["started_at"], "termination_finished_at": term_env["finished_at"],
               "termination_reason": term_env.get("reason"), "exit_code": term_env.get("exit_code"),
               "job_wall_s": job_wall, "process_s": t["process_seconds"],
               "outside_process_s": outside, "slurm_start_to_job_env_s": prolog,
               "gpu_hours_physical_job_env": job_wall / 3600.0}
print("wall", json.dumps(out["wall"]))
check = t.get("attention_backend_check") or {}
out["start_up"] = {"slurm_start_to_job_env_s": prolog, "outside_process_s": outside,
                   "process_to_first_unit_s": t["evaluation_started_after_s"],
                   "of_which_backend_check_s": check.get("seconds"),
                   "model_loaded_after_s": t.get("model_loaded_after_s"),
                   "start_up_s": start_up}
print("start-up", json.dumps(out["start_up"]))

# ------------------------------------------------------------------ units
check_unit = check.get("unit")
cold = defaultdict(list)          # first evaluations of a unit
warm = defaultdict(list)          # re-evaluations (shapes and kernels seen before)
for u in t["units"]:
    (warm if u["unit"] == check_unit else cold)[u["stage"]].append(u)
ref = {x["unit"]: x for x in t["reference"]}
for x in t["reference"]:
    warm[x["stage"]].append({"unit": x["unit"], "seconds": x["v1_seconds"], "v1_reference": True})
per_stage = {}
for stage in dhd.STAGES:
    units = cold.get(stage, [])
    secs = [u["seconds"] for u in units]
    parts = defaultdict(lambda: [0.0, 0.0])
    for u in units:
        for name, p in u["parts"].items():
            parts[name][0] += p["wall_s"]
            parts[name][1] += p["cpu_s"]
    per_stage[stage] = {
        "cold_n": len(secs),
        "cold_mean_s": statistics.mean(secs) if secs else None,
        "cold_median_s": statistics.median(secs) if secs else None,
        "cold_max_s": max(secs) if secs else None,
        "cold_first_s": secs[0] if secs else None,
        "cold_tokens_mean": statistics.mean(u["context_tokens"] for u in units) if units else None,
        "parts_per_unit_wall_cpu_s": {k: (v[0] / len(units), v[1] / len(units)) for k, v in parts.items()} if units else {},
        "warm": [{"unit": w["unit"], "seconds": w["seconds"], "v1_reference": bool(w.get("v1_reference"))} for w in warm.get(stage, [])],
        "chunks": [(c["chunk"], c["phase"], c["profiled"], round(c["seconds"], 2), round(c["cpu_seconds"], 2))
                   for c in t["chunks"] if c["stage"] == stage],
    }
for c in t["chunks"]:
    print("chunk", c["stage"], c["chunk"], c["phase"], "prof" if c["profiled"] else "", round(c["seconds"], 2),
          "cpu", round(c["cpu_seconds"], 2), [(b["name"], b["ticks"]) for b in c["busiest_threads"][:3]])
print("reference", json.dumps(t["reference"]))
print("torch profiles", {k: v.get("status") for k, v in t["torch_profiles"].items()})

# ------------------------------------------------------------------ the lane's units
artifact = json.loads(Path(artifact_path).read_text())
view = dhd.DevView(artifact)
lane_units = dhd.plan_units(view.prompts)
lane_tokens = defaultdict(list)
for u in lane_units:
    tokens, *_ = view.unit_tokens(u.context_index, u.query_index)
    lane_tokens[u.stage].append(len(tokens))
evaluation = 0.0
for stage in dhd.STAGES:
    s = per_stage[stage]
    n = len(lane_tokens[stage])
    s["lane_units"] = n
    s["lane_tokens_mean"] = statistics.mean(lane_tokens[stage])
    s["lane_tokens_max"] = max(lane_tokens[stage])
    units = cold.get(stage, [])
    fit_mean = None
    if len(units) >= 3:
        x = np.asarray([u["context_tokens"] for u in units], dtype=float)
        y = np.asarray([u["seconds"] for u in units], dtype=float)
        if np.ptp(x) > 0:
            b, a = np.polyfit(x, y, 1)
            b = max(b, 0.0)
            a = float(np.mean(y) - b * np.mean(x))
            fit_mean = float(np.mean(a + b * np.asarray(lane_tokens[stage], dtype=float)))
            s["fit_seconds_per_token"] = float(b)
            s["fit_intercept_s"] = a
    s["fit_lane_mean_s"] = fit_mean
    if s["cold_mean_s"] is None:
        s["per_unit_s_entering_rule"] = None
        s["stage_estimate_s"] = None
        continue
    use = max(s["cold_mean_s"], fit_mean or 0.0)
    s["per_unit_s_entering_rule"] = use
    s["stage_estimate_s"] = use * n
    evaluation += use * n
measured_all = all(per_stage[s]["cold_mean_s"] is not None for s in dhd.STAGES)
evaluation_and_stats = evaluation + STATS_BOUND_S
minutes = math.ceil((2.0 * evaluation_and_stats + start_up) / 60.0) + LEAD_MIN
out["per_stage"] = per_stage
out["rule"] = {"every_stage_measured": measured_all, "evaluation_s": evaluation,
               "statistics_bound_s": STATS_BOUND_S, "evaluation_and_statistics_s": evaluation_and_stats,
               "start_up_s": start_up, "minutes": minutes, "cap_gpu_hours": round(minutes / 60.0, 4),
               "useful_window_s": (minutes - LEAD_MIN) * 60.0,
               "lane_units": sum(len(v) for v in lane_tokens.values()),
               "break_even_unit_s": ((minutes - LEAD_MIN) * 60.0 - start_up - STATS_BOUND_S) / sum(len(v) for v in lane_tokens.values()),
               "caps_total_gpu_hours": round(0.10 + 0.10 + 0.20 + minutes / 60.0, 4),
               "cap": CAP_TOTAL}
for stage in dhd.STAGES:
    s = per_stage[stage]
    print(stage, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()
                             if k not in ("chunks", "parts_per_unit_wall_cpu_s", "warm")}))
    print("   parts per cold unit (wall, cpu):", {k: (round(v[0], 3), round(v[1], 3)) for k, v in s["parts_per_unit_wall_cpu_s"].items()})
    print("   warm:", [(w["unit"], round(w["seconds"], 3), "v1" if w["v1_reference"] else "v2") for w in s["warm"]])
print("rule", json.dumps(out["rule"]))
Path(os.environ.get("ANALYSIS_OUT", str(receipt_path.with_name("analysis.json")))).write_text(
    json.dumps(out, indent=1, default=str) + "\n")
