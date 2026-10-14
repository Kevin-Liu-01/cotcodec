#!/usr/bin/env python3
"""Numbers behind the 2026-10-14 README corrections (inference-baseline-v1, exploratory).

Reads the committed raw job records and the regenerated analysis (and, for before/after
comparisons, the analysis committed at 1c9e1153). Standard library only. Prints one JSON object.

usage: derive_corrections.py <evidence dir> <new analysis dir> <old analysis dir>
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HYBRIDS = ("qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b")
ATTN_BYTES_PER_TOKEN_LAYER = {"qwen3.5-4b": 2 * 4 * 256 * 2, "qwen3.5-9b": 2 * 4 * 256 * 2,
                              "qwen3.6-35b-a3b": 2 * 2 * 256 * 2}  # K+V x KV heads x dim x bf16
FA_BLOCK_ALIGN = 16  # FlashAttention's smallest kernel block size (vLLM 0.31.0 default backend)


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def num(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def utc(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%H:%M:%S")


def main() -> int:
    ev, new_dir, old_dir = (Path(a) for a in sys.argv[1:4])
    out: dict = {}
    summary = json.loads((new_dir / "summary.json").read_text())
    models = summary["models"]
    new_cells = {(c["engine_id"], c["cell_id"]): c for c in rows(new_dir / "serve_cells.csv")}
    old_cells = {(c["engine_id"], c["cell_id"]): c for c in rows(old_dir / "serve_cells.csv")}
    serve = rows(new_dir / "serve_runs.csv")
    engines = {e["engine_id"]: e for e in rows(new_dir / "engines.csv")}

    # 1. GDN state per sequence, and its effect on the bandwidth estimate.
    out["state_per_seq"] = {
        m: {
            "ssm_dtype": models[m]["state_ssm_dtype"],
            "bytes": models[m]["state_bytes_per_seq"],
            "mib": round(models[m]["state_bytes_per_seq"] / 2**20, 2),
            "bf16_ssm_mib_for_comparison": round(
                (models[m]["state_ssm_elems_per_seq"] * 2 + models[m]["state_conv_elems_per_seq"] * 2)
                / 2**20, 2),
            "per_layer_bytes": models[m]["state_bytes_per_seq"] // models[m]["linear_attention_layers"],
        }
        for m in HYBRIDS
    }  # fmt: skip
    changed = []
    for key, c in sorted(new_cells.items()):
        if c["model"] not in HYBRIDS or not c.get("est_frac_of_3_35_tb_s"):
            continue
        o = old_cells[key]
        total, state = num(c["est_bytes_per_step_gb"]), num(c["est_state_gb"])
        o_total, o_state = num(o["est_bytes_per_step_gb"]), num(o["est_state_gb"])
        changed.append({
            "engine": key[0], "cell": key[1],
            "est_pct_bw_old": round(100 * num(o["est_frac_of_3_35_tb_s"]), 1),
            "est_pct_bw_new": round(100 * num(c["est_frac_of_3_35_tb_s"]), 1),
            "est_gb_step_old": o_total, "est_gb_step_new": total,
            "state_gb_old": o_state, "state_gb_new": state,
            "kv_gb": num(c["est_kv_gb"]), "weight_gb": num(c["est_weight_gb"]),
            "state_share_old_pct": round(100 * o_state / o_total, 1) if o_total else None,
            "state_share_new_pct": round(100 * state / total, 1) if total else None,
        })  # fmt: skip
    out["hybrid_bandwidth_cells"] = changed
    out["non_hybrid_cells_changed"] = sum(
        1
        for key, c in new_cells.items()
        if c["model"] not in HYBRIDS
        and (c.get("est_frac_of_3_35_tb_s"), c.get("est_bytes_per_step_gb"))
        != (old_cells[key].get("est_frac_of_3_35_tb_s"), old_cells[key].get("est_bytes_per_step_gb"))
    )

    # 2. Hybrid block pool: blocks per running sequence, and the sequence cap it implies.
    pool = {}
    for eid, e in engines.items():
        model = next((m for m in HYBRIDS if eid.startswith(m)), None)
        if not model or not e.get("num_gpu_blocks"):
            continue
        geo = models[model]
        full, linear = geo["full_attention_layers"], geo["linear_attention_layers"]
        tp = 2 if "tp2" in eid else 1
        kv_bytes = 1 if "kvfp8" in eid else 2
        block, blocks = int(e["block_size"]), int(e["num_gpu_blocks"])
        attn_tok = ATTN_BYTES_PER_TOKEN_LAYER[model] // 2 * kv_bytes // tp
        state_layer = geo["state_bytes_per_seq"] // linear // tp
        gdn_groups = linear // full
        bf16_layer = (geo["state_ssm_elems_per_seq"] * 2 + geo["state_conv_elems_per_seq"] * 2) // linear // tp
        bf16_block = FA_BLOCK_ALIGN * math.ceil(bf16_layer / (FA_BLOCK_ALIGN * attn_tok))
        bf16_blocks = int(blocks * block / bf16_block)
        per_shape = {}
        for shape, tokens in (("chat", 768), ("in8k", 8448), ("in32k", 32256), ("longout", 4608),
                              ("prefix", 4480)):  # fmt: skip
            per_seq = math.ceil(tokens / block) + gdn_groups
            per_seq_bf16 = math.ceil(tokens / bf16_block) + gdn_groups
            per_shape[shape] = {
                "blocks_per_seq": per_seq,
                "gdn_share_of_seq_blocks_pct": round(100 * gdn_groups / per_seq, 1),
                "max_running_seqs": (blocks - 1) // per_seq,
                "bf16_state_counterfactual_max_running_seqs": (bf16_blocks - 1) // per_seq_bf16,
            }
        pool[eid] = {
            "num_gpu_blocks": blocks, "block_size": block, "groups": f"1 attention + {gdn_groups} GDN",
            "layers_per_group": full, "attn_page_bytes_per_layer": block * attn_tok,
            "gdn_state_bytes_per_layer": state_layer,
            "padding_pct": round(100 * (block * attn_tok - state_layer) / state_layer, 2),
            "pool_gib": round(blocks * full * block * attn_tok / 2**30, 3),
            "kv_cache_gib_logged": num(e["kv_cache_gib_per_rank"]),
            "bf16_state_counterfactual_block_size": bf16_block,
            "per_shape": per_shape,
        }  # fmt: skip
    out["hybrid_block_pool"] = pool
    checks = []
    for (eid, cid), c in sorted(new_cells.items()):
        if eid in pool and c.get("peak_kv_cache_usage_perc"):
            shape, conc = c["shape"], int(c["concurrency"])
            per_seq = pool[eid]["per_shape"][shape]["blocks_per_seq"]
            running = num(c["peak_num_requests_running"]) or conc
            predicted = min(running, conc) * per_seq / (pool[eid]["num_gpu_blocks"] - 1)
            checks.append({"engine": eid, "cell": cid, "peak_running": running,
                           "peak_waiting": num(c.get("peak_num_requests_waiting")),
                           "peak_kv_pct": round(100 * num(c["peak_kv_cache_usage_perc"]), 1),
                           "block_model_pct": round(100 * predicted, 1)})  # fmt: skip
    out["hybrid_peak_kv_vs_block_model"] = checks
    out["moe_tp1_runs"] = [
        {k: r.get(k) for k in ("cell_id", "repeat", "peak_num_requests_running",
                               "mean_num_requests_running", "peak_num_requests_waiting",
                               "peak_kv_cache_usage_perc", "median_ttft_ms", "output_throughput",
                               "delta_num_preemptions_total")}
        for r in serve if r["engine_id"] == "qwen3.6-35b-a3b-tp1-seqs128"
    ]  # fmt: skip
    e_log = (ev / "jobs/e-1323/ib/engines/qwen3.6-35b-a3b-tp1/engine.log").read_text(errors="replace")
    out["moe_tp1_refusal"] = [ln.strip()[-200:] for ln in e_log.splitlines()
                              if "Mamba cache blocks" in ln or "Available KV cache memory" in ln][:4]

    # 3. Qwen3-32B TP 1: vLLM's own memory figures.
    log = (ev / "jobs/e-1323/ib/engines/qwen3-32b-tp1/engine.log").read_text(errors="replace")
    out["qwen3_32b_tp1_log"] = [
        re.sub(r"^\(EngineCore[^)]*\) ", "", ln.strip())
        for ln in log.splitlines()
        if re.search(r"Free memory on device|kv-cache-memory|Available KV cache memory|GPU KV cache size", ln)
    ]  # fmt: skip
    # vLLM's "fully utilize" --kv-cache-memory figure, in tokens (32B) and chat sequences (MoE TP 1).
    full = int(re.search(r"--kv-cache-memory=(\d+)`[^`]*to fully utilize", log).group(1))
    out["qwen3_32b_tp1_full_kv"] = {"bytes": full, "tokens_at_256_kib": full // (256 * 1024)}
    h_log = next(ev.glob("jobs/h-1330/ib/engines/*/engine.log")).read_text(errors="replace")
    h_full = int(re.search(r"--kv-cache-memory=(\d+)`[^`]*to fully utilize", h_log).group(1))
    h_pool = pool["qwen3.6-35b-a3b-tp1-seqs128"]
    h_block_bytes = h_pool["layers_per_group"] * h_pool["attn_page_bytes_per_layer"]
    h_blocks = h_full // h_block_bytes
    out["moe_tp1_full_kv"] = {
        "bytes": h_full, "blocks": h_blocks,
        "chat_seqs": (h_blocks - 1) // h_pool["per_shape"]["chat"]["blocks_per_seq"],
        "e_engine_blocks_at_3_65_gib": int(3.65 * 2**30 // h_block_bytes),
    }  # fmt: skip

    # 4. TP 4 in32k-c32 on two engine instances, and prefix-cache hit rates against block alignment.
    out["tp4_in32k_c32_runs"] = [
        {k: r.get(k) for k in ("job", "engine_id", "repeat", "output_throughput", "median_ttft_ms",
                               "median_tpot_ms", "median_itl_ms", "p99_itl_ms")}
        for r in serve
        if r["engine_id"].startswith("qwen3-32b-tp4") and r["cell_id"] in ("in32k-c32", "longout-c128")
    ]  # fmt: skip
    out["p99_itl_32b_in32k"] = [
        {k: c.get(k) for k in ("engine_id", "cell_id", "p99_itl_ms", "repeats")}
        for (eid, cid), c in sorted(new_cells.items())
        if eid.startswith("qwen3-32b") and cid.startswith("in32k") and int(c["concurrency"]) > 1
    ]
    prefix = []
    for (eid, cid), c in sorted(new_cells.items()):
        if c["shape"] != "prefix" or c.get("prefix_caching") not in ("True", True):
            continue
        prompts = 64 if cid == "prefix-c8" else 128
        block = int(engines[eid]["block_size"])
        cacheable = (4096 // block) * block
        prefix.append({
            "engine": eid, "cell": cid, "block_size": block, "cacheable_prefix_tokens": cacheable,
            "observed_pct": round(100 * num(c["prefix_cache_hit_rate"]), 1),
            "observed_runs_pct": [round(100 * num(r["prefix_cache_hit_rate"]), 1) for r in serve
                                  if r["engine_id"] == eid and r["cell_id"] == cid],
            "block_alignment_prediction_pct": round(100 * (prompts - 8) * cacheable / (prompts * 4352), 1),
            "no_alignment_max_pct": round(100 * (prompts - 8) * 4096 / (prompts * 4352), 1),
        })  # fmt: skip
    out["prefix_hit_rates"] = prefix

    # 5. Smaller mismatches.
    spread = [
        {"engine": eid, "cell": cid, "out_tok_s_spread_pct": round(100 * num(c["output_throughput_rel_range"]), 1),
         "est_pct_bw": round(100 * num(c["est_frac_of_3_35_tb_s"]), 1) if c.get("est_frac_of_3_35_tb_s") else None}
        for (eid, cid), c in sorted(new_cells.items())
        if num(c.get("output_throughput_rel_range")) is not None and num(c["output_throughput_rel_range"]) > 0.04
    ]  # fmt: skip
    out["throughput_spread_above_4pct"] = spread
    c1 = [(num(c["mean_power_w_per_gpu"]), eid, cid) for (eid, cid), c in new_cells.items()
          if int(c["concurrency"]) == 1 and c.get("mean_power_w_per_gpu")]  # fmt: skip
    chat1 = [p for p in c1 if p[2] == "chat-c1"]
    c1_runs = [(num(r["mean_power_w_per_gpu"]), r["engine_id"], r["cell_id"], r["repeat"])
               for r in serve if r["concurrency"] == "1" and r.get("mean_power_w_per_gpu")]  # fmt: skip
    out["c1_power_w"] = {"all_shapes": [min(c1), max(c1)], "chat_only": [min(chat1), max(chat1)],
                         "above_470": sorted(p for p in c1 if p[0] > 470),
                         "single_runs": [min(c1_runs), max(c1_runs)]}  # fmt: skip
    cells = list(new_cells.values())
    out["serve_cells"] = {"rows": len(cells), "two_repeats": sum(c["repeats"] == "2" for c in cells),
                          "one_repeat": [f'{c["engine_id"]} {c["cell_id"]}' for c in cells if c["repeats"] == "1"]}  # fmt: skip
    hbm_s = [num(r["peak_hbm_used_gib_max_gpu"]) for r in serve if r.get("peak_hbm_used_gib_max_gpu")]
    off = rows(new_dir / "offline_runs.csv")
    hbm_o = [num(r["peak_hbm_used_gib_max_gpu"]) for r in off if r.get("peak_hbm_used_gib_max_gpu")]
    out["peak_hbm_gib"] = {"serving": [min(hbm_s), max(hbm_s)], "offline": [min(hbm_o), max(hbm_o)]}
    loads = []
    for path in sorted(ev.glob("jobs/*/ib/engines/*/engine.json")):
        e = json.loads(path.read_text())
        if e.get("start_t") and e.get("ready_t"):
            loads.append((float(e["start_t"]), float(e["ready_t"]), path.parts[-5], e["engine_id"]))
    starts = []
    for s, r, job, eid in sorted(loads):
        others = sorted({f"{j}:{x}" for s2, r2, j, x in loads if (j, x) != (job, eid) and s2 < r and r2 > s})
        peak = max(sum(1 for s2, r2, *_ in loads if s2 <= t < r2) for t in (s, *(x[0] for x in loads if s <= x[0] < r)))
        starts.append({"job": job, "engine": eid, "start": utc(s), "ready": utc(r), "ready_s": round(r - s),
                       "overlapping_loads": others, "max_concurrent_loads_during": peak})  # fmt: skip
    out["engine_startups"] = starts

    # 6. Thin records.
    rec = {}
    for rel in ("fetch/scontrol-1310.txt", "selftest/scontrol-1312.txt", "selftest-2/scontrol-1326.txt"):
        p = ev / rel
        rec[rel] = p.stat().st_size if p.exists() else "missing"
    for rel in ("selftest/selftest.json", "selftest-2/selftest.json"):
        text = (ev / rel).read_text(errors="replace")
        try:
            json.loads(text)
            ok = True
        except ValueError:
            ok = False
        lines = text.splitlines()
        first = next((i for i, ln in enumerate(lines) if ln.startswith("{")), len(lines))
        rec[rel] = {"valid_json": ok, "lines": len(lines), "non_json_lines_before_json": first,
                    "distinct_non_json_lines": sorted(set(lines[:first]))}  # fmt: skip
    for rel in ("selftest/pytest.txt", "selftest-2/pytest.txt"):
        rec[rel] = (ev / rel).read_text(errors="replace").strip()[:200]
    listed = committed = 0
    uncommitted: dict[str, int] = {}
    for sha in sorted(ev.glob("jobs/*/host-run-dir.sha256")):
        job = sha.parent
        for line in sha.read_text().splitlines():
            rel = line.split("  ", 1)[1] if "  " in line else line.split()[-1]
            rel = rel[2:] if rel.startswith("./") else rel
            listed += 1
            if (job / rel).is_file():
                committed += 1
            else:
                name = Path(rel).name
                uncommitted[name] = uncommitted.get(name, 0) + 1
    rec["host_run_dir_sha256"] = {"listed": listed, "committed": committed,
                                  "not_committed_by_name": dict(sorted(uncommitted.items()))}  # fmt: skip
    out["records"] = rec
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
