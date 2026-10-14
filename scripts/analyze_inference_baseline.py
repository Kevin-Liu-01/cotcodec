#!/usr/bin/env python3
"""Tables for the exploratory inference baseline (inference-baseline-v1).

Reads the collected job directories (each holding the driver's ``ib/`` output) and writes CSV
tables plus a JSON summary. Standard library only. Every number it writes is exploratory.

The decode-bandwidth column is an analytical estimate, not a hardware counter (DCGM profiling
and NVML GPM are admin-only on this host): bytes a decode step must read (weights a token
touches, the KV cache of every running sequence, and for the gated-DeltaNet hybrids the
recurrent state read and written) divided by the measured median inter-token latency.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import statistics
from bisect import bisect_left
from pathlib import Path
from typing import Any

H100_HBM_TB_S = 3.35
GDN_STATE_BYTES = 2  # vLLM 0.31.0 keeps the GDN state in the model dtype (bf16) by default


# --------------------------------------------------------------------------- loading


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def job_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "ib" / "summary.json").is_file())


def load_nvml(path: Path) -> dict[int, list[dict[str, float]]]:
    series: dict[int, list[dict[str, float]]] = {}
    if not path.is_file():
        return series
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                gpu = int(row["gpu"])
                sample = {"t": float(row["t"])}
            except (KeyError, ValueError):
                continue
            for key in (
                "mem_used_mib", "power_w", "energy_mj", "util_gpu_pct", "util_mem_pct",
                "sm_clock_mhz", "mem_clock_mhz",
            ):  # fmt: skip
                with contextlib.suppress(KeyError, ValueError):
                    sample[key] = float(row[key])
            with contextlib.suppress(KeyError, ValueError, TypeError):
                # NVML clocks-event reasons: 0x4 is the software power cap.
                sample["power_capped"] = float(bool(int(row["throttle_reasons"], 16) & 0x4))
            series.setdefault(gpu, []).append(sample)
    return series


def window_stats(series: dict[int, list[dict[str, float]]], start: float, end: float) -> dict:
    out: dict[str, Any] = {}
    if not series or end <= start:
        return out
    peak_mem, powers, energy, sm, util_gpu, util_mem, mem_clock = [], [], 0.0, [], [], [], []
    capped: list[float] = []
    for samples in series.values():
        times = [s["t"] for s in samples]
        lo, hi = bisect_left(times, start), bisect_left(times, end)
        window = samples[lo:hi]
        if not window:
            continue
        peak_mem.append(max(s.get("mem_used_mib", 0.0) for s in window))
        powers.append(statistics.fmean(s["power_w"] for s in window if "power_w" in s))
        if "energy_mj" in window[0] and "energy_mj" in window[-1]:
            energy += (window[-1]["energy_mj"] - window[0]["energy_mj"]) / 1000.0
        sm.append(statistics.fmean(s["sm_clock_mhz"] for s in window if "sm_clock_mhz" in s))
        mem_clock.append(
            statistics.fmean(s["mem_clock_mhz"] for s in window if "mem_clock_mhz" in s)
        )
        util_gpu.append(statistics.fmean(s["util_gpu_pct"] for s in window if "util_gpu_pct" in s))
        util_mem.append(statistics.fmean(s["util_mem_pct"] for s in window if "util_mem_pct" in s))
        capped += [s["power_capped"] for s in window if "power_capped" in s]
    if not peak_mem:
        return out
    out["peak_hbm_used_gib_max_gpu"] = round(max(peak_mem) / 1024, 2)
    out["mean_power_w_per_gpu"] = round(statistics.fmean(powers), 1)
    out["energy_j_all_gpus"] = round(energy, 1)
    out["mean_sm_clock_mhz"] = round(statistics.fmean(sm), 0)
    out["mean_mem_clock_mhz"] = round(statistics.fmean(mem_clock), 0)
    out["mean_util_gpu_pct"] = round(statistics.fmean(util_gpu), 1)
    out["mean_util_mem_pct"] = round(statistics.fmean(util_mem), 1)
    if capped:
        out["power_capped_frac"] = round(statistics.fmean(capped), 3)
    return out


# --------------------------------------------------------------------------- model geometry


def text_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("text_config", config)


def geometry(model_record: dict[str, Any]) -> dict[str, Any]:
    """Per-token KV bytes, recurrent-state bytes and weight bytes a decode step reads."""
    cfg = text_config(model_record["config"])
    layers = int(cfg["num_hidden_layers"])
    types = cfg.get("layer_types")
    if types:
        full = sum(1 for t in types if t == "full_attention")
        linear = sum(1 for t in types if t == "linear_attention")
    elif cfg.get("full_attention_interval"):
        full = layers // int(cfg["full_attention_interval"])
        linear = layers - full
    else:
        full, linear = layers, 0
    head_dim = int(
        cfg.get("head_dim") or int(cfg["hidden_size"]) // int(cfg["num_attention_heads"])
    )
    kv_heads = int(cfg["num_key_value_heads"])
    kv_elems_per_token = full * 2 * kv_heads * head_dim
    state_elems = 0
    if linear:
        nk, nv = int(cfg["linear_num_key_heads"]), int(cfg["linear_num_value_heads"])
        dk, dv = int(cfg["linear_key_head_dim"]), int(cfg["linear_value_head_dim"])
        kernel = int(cfg.get("linear_conv_kernel_dim", 4))
        conv_dim = 2 * nk * dk + nv * dv
        state_elems = linear * (nv * dk * dv + conv_dim * (kernel - 1))
    cats = model_record.get("safetensors", {}).get("bytes_by_category", {})
    always = sum(
        cats.get(k, 0)
        for k in (
            "full_attention",
            "linear_attention",
            "dense_mlp",
            "shared_expert",
            "router",
            "other",
        )
    )
    lm_head = cats.get("lm_head") or cats.get("embed_tokens", 0)  # tied: the embedding is the head
    return {
        "layers": layers,
        "full_attention_layers": full,
        "linear_attention_layers": linear,
        "kv_elems_per_token": kv_elems_per_token,
        "state_elems_per_seq": state_elems,
        "weights_always_bytes": always + lm_head,
        "routed_expert_bytes": cats.get("routed_experts", 0),
        "num_experts": int(cfg.get("num_experts") or 0),
        "experts_per_token": int(cfg.get("num_experts_per_tok") or 0),
        "text_weight_bytes": always + lm_head + cats.get("routed_experts", 0),
        "excluded_bytes": {k: cats.get(k, 0) for k in ("vision", "mtp", "embed_tokens")},
    }


def decode_bytes_per_step(geo: dict[str, Any], batch: float, context: float, kv_dtype: str) -> dict:
    """Bytes one decode step reads over all GPUs (weights + KV + GDN state)."""
    weights = geo["weights_always_bytes"]
    if geo["num_experts"] and geo["experts_per_token"]:
        touched = 1.0 - (1.0 - geo["experts_per_token"] / geo["num_experts"]) ** max(batch, 1.0)
        weights += geo["routed_expert_bytes"] * touched
    else:
        weights += geo["routed_expert_bytes"]
    kv_bytes = 1 if kv_dtype.startswith("fp8") else 2
    kv = batch * context * geo["kv_elems_per_token"] * kv_bytes
    state = batch * geo["state_elems_per_seq"] * GDN_STATE_BYTES * 2  # read and write
    return {"weights": weights, "kv": kv, "state": state, "total": weights + kv + state}


# --------------------------------------------------------------------------- tables


SERVE_KEYS = (
    "duration", "completed", "failed", "total_input_tokens", "total_output_tokens",
    "request_throughput", "output_throughput", "total_token_throughput",
    "mean_ttft_ms", "median_ttft_ms", "p99_ttft_ms", "mean_tpot_ms", "median_tpot_ms",
    "p99_tpot_ms", "mean_itl_ms", "median_itl_ms", "p90_itl_ms", "p99_itl_ms",
    "mean_e2el_ms", "median_e2el_ms", "max_concurrent_requests",
)  # fmt: skip


def serve_rows(job: Path, nvml: dict, models: dict, engines: dict) -> list[dict[str, Any]]:
    rows = []
    for meta_path in sorted((job / "ib" / "engines").glob("*/runs/*.meta.json")):
        meta = load_json(meta_path)
        if meta.get("warmup"):
            continue
        row: dict[str, Any] = {
            "job": job.name,
            **{k: meta.get(k) for k in (
                "engine_id", "model", "tp", "kv_cache_dtype", "prefix_caching", "cell_id",
                "shape", "concurrency", "num_prompts", "input_len", "output_len", "repeat",
                "status", "wall_s", "output_tokens_ok",
            )},
        }  # fmt: skip
        result_path = meta_path.with_name(meta_path.name.replace(".meta.json", ".json"))
        if result_path.is_file():
            result = load_json(result_path)
            row.update({k: result.get(k) for k in SERVE_KEYS})
        metrics = meta.get("metrics", {})
        for key in (
            "peak_kv_cache_usage_perc", "mean_kv_cache_usage_perc", "peak_num_requests_running",
            "mean_num_requests_running", "peak_num_requests_waiting",
            "delta_num_preemptions_total", "prefix_cache_hit_rate",
        ):  # fmt: skip
            row[key] = metrics.get(key)
        engine = engines.get(meta.get("engine_id"), {})
        kv_tokens = engine.get("log_parse", {}).get("kv_cache_tokens")
        if kv_tokens and row["peak_kv_cache_usage_perc"] is not None:
            row["peak_kv_tokens_used"] = round(row["peak_kv_cache_usage_perc"] * kv_tokens)
        if meta.get("start_t") and meta.get("end_t"):
            row.update(window_stats(nvml, float(meta["start_t"]), float(meta["end_t"])))
        if row.get("energy_j_all_gpus") and row.get("total_output_tokens"):
            row["joules_per_output_token"] = round(
                row["energy_j_all_gpus"] / row["total_output_tokens"], 4
            )
        record = models.get(meta.get("model"))
        if record and row.get("median_itl_ms") and row["shape"] != "prefix":
            geo = geometry(record)
            batch = row.get("mean_num_requests_running") or row["concurrency"]
            batch = min(float(batch), float(row["concurrency"]))
            if row["concurrency"] == 1:
                batch = 1.0
            context = row["input_len"] + row["output_len"] / 2
            moved = decode_bytes_per_step(geo, batch, context, row["kv_cache_dtype"] or "auto")
            step_s = row["median_itl_ms"] / 1000.0
            per_gpu = moved["total"] / max(1, int(row["tp"])) / step_s
            row["est_decode_batch"] = round(batch, 1)
            row["est_bytes_per_step_gb"] = round(moved["total"] / 1e9, 3)
            row["est_weight_gb"] = round(moved["weights"] / 1e9, 3)
            row["est_kv_gb"] = round(moved["kv"] / 1e9, 3)
            row["est_state_gb"] = round(moved["state"] / 1e9, 3)
            row["est_hbm_tb_s_per_gpu"] = round(per_gpu / 1e12, 3)
            row["est_frac_of_3_35_tb_s"] = round(per_gpu / 1e12 / H100_HBM_TB_S, 3)
        rows.append(row)
    return rows


def offline_rows(job: Path, nvml: dict) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((job / "ib" / "engines").glob("*/offline/offline-*-r*.json")):
        result = load_json(path)
        row = {
            "job": job.name,
            **{k: v for k, v in result.items() if k not in ("tool", "sampling")},
        }
        row.update(window_stats(nvml, float(result["start_t"]), float(result["end_t"])))
        if row.get("energy_j_all_gpus") and row.get("total_output_tokens"):
            row["joules_per_output_token"] = round(
                row["energy_j_all_gpus"] / row["total_output_tokens"], 4
            )
        rows.append(row)
    return rows


def engine_rows(job: Path, models: dict) -> tuple[list[dict[str, Any]], dict[str, dict]]:
    rows, by_id = [], {}
    for path in sorted((job / "ib" / "engines").glob("*/engine.json")):
        engine = load_json(path)
        by_id[engine["engine_id"]] = engine
        parse = engine.get("log_parse", {})
        usage = (parse.get("actual_usage_gib_per_rank") or [{}])[0]
        weights = (parse.get("weights_gib_per_rank") or [None])[0]
        cache = engine.get("cache_config_info", {})
        model = path.parent.name
        row = {
            "job": job.name,
            "engine_id": engine["engine_id"],
            "status": engine.get("status"),
            "ready_s": engine.get("ready_s"),
            "ranks": len(parse.get("weights_gib_per_rank") or []),
            "weights_gib_per_rank": weights,
            "non_torch_gib_per_rank": (
                round(usage["weights_plus_non_torch"] - weights, 2)
                if usage and weights is not None
                else None
            ),
            "peak_activation_gib_per_rank": usage.get("peak_activation"),
            "cuda_graph_gib_per_rank": usage.get("cuda_graph"),
            "kv_cache_gib_per_rank": (parse.get("kv_cache_gib_per_rank") or [None])[0],
            "kv_cache_tokens": parse.get("kv_cache_tokens"),
            "max_concurrency_at_len": json.dumps(parse.get("max_concurrency_at_len")),
            "num_gpu_blocks": cache.get("num_gpu_blocks"),
            "block_size": cache.get("block_size"),
            "cache_dtype": cache.get("cache_dtype"),
            "gpu_memory_ready_mib": json.dumps(engine.get("gpu_memory_ready_mib")),
            "init_engine_s": parse.get("init_engine_s"),
            "torch_compile_s": parse.get("torch_compile_s"),
            "weights_load_s": parse.get("weights_load_s"),
            "attention_backends": " ".join(parse.get("attention_backends", [])),
            "architecture": parse.get("architecture"),
        }
        del model
        rows.append(row)
    return rows, by_id


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("status") != "ok":
            continue
        groups.setdefault((row["job"], row["engine_id"], row["cell_id"]), []).append(row)
    out = []
    for (job, engine_id, cell_id), items in groups.items():
        first = items[0]
        agg: dict[str, Any] = {
            "job": job, "engine_id": engine_id, "model": first["model"], "tp": first["tp"],
            "kv_cache_dtype": first["kv_cache_dtype"], "prefix_caching": first["prefix_caching"],
            "cell_id": cell_id, "shape": first["shape"], "concurrency": first["concurrency"],
            "input_len": first["input_len"], "output_len": first["output_len"],
            "repeats": len(items),
        }  # fmt: skip
        for key in (
            "output_throughput", "total_token_throughput", "request_throughput",
            "median_ttft_ms", "p99_ttft_ms", "median_tpot_ms", "median_itl_ms", "p99_itl_ms",
            "peak_kv_cache_usage_perc", "peak_num_requests_running",
            "delta_num_preemptions_total", "prefix_cache_hit_rate", "peak_hbm_used_gib_max_gpu",
            "mean_power_w_per_gpu", "joules_per_output_token", "mean_sm_clock_mhz",
            "power_capped_frac",
            "est_hbm_tb_s_per_gpu", "est_frac_of_3_35_tb_s", "est_bytes_per_step_gb",
            "est_kv_gb", "est_state_gb", "est_weight_gb",
        ):  # fmt: skip
            values = [float(r[key]) for r in items if r.get(key) is not None]
            if not values:
                continue
            mean = statistics.fmean(values)
            agg[key] = round(mean, 4)
            if len(values) > 1 and key in (
                "output_throughput", "median_ttft_ms", "median_tpot_ms", "median_itl_ms",
                "joules_per_output_token",
            ):  # fmt: skip
                spread = (max(values) - min(values)) / mean if mean else None
                agg[f"{key}_rel_range"] = round(spread, 4) if spread is not None else None
        out.append(agg)
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------------------------------- markdown


def fmt(value: Any, digits: int = 1) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        if value == 0:
            return "0"
        if abs(value) >= 100:
            return f"{value:,.0f}"
        if abs(value) >= 10:
            return f"{value:.{digits}f}"
        if abs(value) >= 1:
            return f"{value:.2f}"
        return f"{value:.3f}"
    return str(value)


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += [
        "| " + " | ".join(fmt(c) if not isinstance(c, str) else c for c in row) + " |"
        for row in rows
    ]
    return "\n".join(lines) + "\n"


def pct(value: Any) -> str:
    return "-" if value is None else f"{100 * float(value):.0f}%"


def markdown(cells: list[dict], engines: list[dict], offline: list[dict], serve: list[dict]) -> str:
    out = ["<!-- generated by scripts/analyze_inference_baseline.py; exploratory -->\n"]
    by = {(c["engine_id"], c["cell_id"]): c for c in cells}
    engine_ids: list[str] = []
    for eid in [e["engine_id"] for e in engines] + [c["engine_id"] for c in cells]:
        if eid not in engine_ids:
            engine_ids.append(eid)

    out.append("### HBM per engine (vLLM start-up accounting, per GPU)\n")
    out.append(
        md_table(
            [
                "engine",
                "ranks",
                "weights GiB",
                "non-torch GiB",
                "peak activation GiB",
                "CUDA graphs GiB",
                "KV cache GiB",
                "KV capacity (tokens)",
                "ready s",
                "compile s",
            ],
            [
                [
                    e["engine_id"],
                    e["ranks"],
                    e["weights_gib_per_rank"],
                    e["non_torch_gib_per_rank"],
                    e["peak_activation_gib_per_rank"],
                    e["cuda_graph_gib_per_rank"],
                    e["kv_cache_gib_per_rank"],
                    e["kv_cache_tokens"],
                    e["ready_s"],
                    e["torch_compile_s"],
                ]
                for e in engines
            ],
        )
    )

    out.append("\n### Single-stream decode (concurrency 1; mean of repeats)\n")
    rows = []
    for eid in engine_ids:
        for shape in ("chat", "in8k", "in32k", "longout"):
            c = by.get((eid, f"{shape}-c1"))
            if not c:
                continue
            rows.append(
                [
                    eid,
                    shape,
                    c.get("median_ttft_ms"),
                    c.get("median_tpot_ms"),
                    c.get("median_tpot_ms_rel_range"),
                    c.get("output_throughput"),
                    c.get("est_bytes_per_step_gb"),
                    c.get("est_hbm_tb_s_per_gpu"),
                    pct(c.get("est_frac_of_3_35_tb_s")),
                    c.get("mean_power_w_per_gpu"),
                    c.get("joules_per_output_token"),
                ]
            )
    out.append(
        md_table(
            [
                "engine",
                "shape",
                "TTFT ms",
                "TPOT ms",
                "TPOT range",
                "out tok/s",
                "est GB/step",
                "est TB/s/GPU",
                "est % of 3.35",
                "W/GPU",
                "J/out tok",
            ],
            rows,
        )
    )

    out.append("\n### Concurrency sweep (closed loop; mean of repeats)\n")
    rows = []
    for eid in engine_ids:
        for shape in ("chat", "in8k", "in32k", "longout"):
            for conc in (1, 8, 32, 128):
                c = by.get((eid, f"{shape}-c{conc}"))
                if not c:
                    continue
                rows.append(
                    [
                        eid,
                        shape,
                        conc,
                        c.get("output_throughput"),
                        c.get("output_throughput_rel_range"),
                        c.get("total_token_throughput"),
                        c.get("median_ttft_ms"),
                        c.get("p99_ttft_ms"),
                        c.get("median_tpot_ms"),
                        c.get("p99_itl_ms"),
                        pct(c.get("peak_kv_cache_usage_perc")),
                        c.get("delta_num_preemptions_total"),
                        pct(c.get("est_frac_of_3_35_tb_s")),
                        c.get("mean_power_w_per_gpu"),
                        c.get("mean_sm_clock_mhz"),
                        pct(c.get("power_capped_frac")),
                        c.get("joules_per_output_token"),
                    ]
                )
    out.append(
        md_table(
            [
                "engine",
                "shape",
                "conc",
                "out tok/s",
                "range",
                "total tok/s",
                "TTFT p50 ms",
                "TTFT p99 ms",
                "TPOT p50 ms",
                "ITL p99 ms",
                "peak KV",
                "preempt",
                "est % BW",
                "W/GPU",
                "SM MHz",
                "power-capped",
                "J/out tok",
            ],
            rows,
        )
    )

    out.append("\n### Qwen3-32B across tensor parallelism (same cells; mean of repeats)\n")
    tp_engines = ["qwen3-32b-tp1", "qwen3-32b-tp1-kvfp8", "qwen3-32b-tp2", "qwen3-32b-tp4",
                  "qwen3-32b-tp4-rerun"]  # fmt: skip
    rows = []
    for cid in ("chat-c1", "chat-c8", "chat-c32", "chat-c128", "in8k-c1", "in8k-c8", "in8k-c128",
                "in32k-c1", "in32k-c32", "longout-c1", "longout-c8", "longout-c128"):  # fmt: skip
        for eid in tp_engines:
            c = by.get((eid, cid))
            if c:
                gpus = int(c["tp"])
                rows.append([cid, eid, gpus, c.get("output_throughput"),
                             c["output_throughput"] / gpus if c.get("output_throughput") else None,
                             c.get("median_ttft_ms"), c.get("median_tpot_ms"),
                             pct(c.get("peak_kv_cache_usage_perc")),
                             c.get("delta_num_preemptions_total"),
                             c.get("joules_per_output_token"), c.get("repeats")])  # fmt: skip
    out.append(
        md_table(
            [
                "cell",
                "engine",
                "GPUs",
                "out tok/s",
                "out tok/s per GPU",
                "TTFT p50 ms",
                "TPOT p50 ms",
                "peak KV",
                "preempt",
                "J/out tok",
                "repeats",
            ],
            rows,
        )
    )

    out.append("\n### FP8 KV cache against BF16 KV cache (same model, same cells)\n")
    rows = []
    for base, fp8 in (("qwen3.5-9b-tp1", "qwen3.5-9b-tp1-kvfp8"),
                      ("qwen3-32b-tp1", "qwen3-32b-tp1-kvfp8")):  # fmt: skip
        for (eid, cid), c in sorted(by.items()):
            if eid != fp8:
                continue
            b = by.get((base, cid))
            ratio = (c["output_throughput"] / b["output_throughput"]
                     if b and b.get("output_throughput") else None)  # fmt: skip
            rows.append([cid, base, b.get("output_throughput") if b else None,
                         b.get("median_tpot_ms") if b else None,
                         pct(b.get("peak_kv_cache_usage_perc")) if b else "-",
                         b.get("delta_num_preemptions_total") if b else None,
                         c.get("output_throughput"), c.get("median_tpot_ms"),
                         pct(c.get("peak_kv_cache_usage_perc")),
                         c.get("delta_num_preemptions_total"), ratio])  # fmt: skip
    out.append(md_table(["cell", "model", "BF16 out tok/s", "BF16 TPOT ms", "BF16 peak KV",
                         "BF16 preempt", "FP8 out tok/s", "FP8 TPOT ms", "FP8 peak KV",
                         "FP8 preempt", "FP8/BF16 tok/s"], rows))  # fmt: skip

    out.append("\n### Prefix caching on and off (shared 4,096-token prefixes; mean of repeats)\n")
    rows = []
    for eid in engine_ids:
        for conc in (8, 32):
            c = by.get((eid, f"prefix-c{conc}"))
            if c:
                rows.append(
                    [
                        eid,
                        conc,
                        "on" if c.get("prefix_caching") in (True, "True") else "off",
                        pct(c.get("prefix_cache_hit_rate")),
                        c.get("median_ttft_ms"),
                        c.get("p99_ttft_ms"),
                        c.get("total_token_throughput"),
                        c.get("output_throughput"),
                        c.get("median_tpot_ms"),
                    ]
                )
    out.append(
        md_table(
            [
                "engine",
                "conc",
                "prefix cache",
                "hit rate",
                "TTFT p50 ms",
                "TTFT p99 ms",
                "total tok/s",
                "out tok/s",
                "TPOT p50 ms",
            ],
            rows,
        )
    )

    out.append("\n### Offline throughput (all prompts at once; vllm bench throughput code)\n")
    groups: dict[tuple, list[dict]] = {}
    for r in offline:
        groups.setdefault((r["engine_id"], r["cell_id"]), []).append(r)
    rows = []
    for (eid, cid), items in sorted(groups.items()):
        outs = [float(i["output_tokens_per_s"]) for i in items]
        tots = [float(i["total_tokens_per_s"]) for i in items]
        mean = statistics.fmean(outs)
        rows.append(
            [
                eid,
                cid.replace("offline-", ""),
                items[0]["num_prompts"],
                f"{items[0]['input_len']}/{items[0]['output_len']}",
                mean,
                (max(outs) - min(outs)) / mean if len(outs) > 1 else None,
                statistics.fmean(tots),
                statistics.fmean(
                    float(i["joules_per_output_token"])
                    for i in items
                    if i.get("joules_per_output_token")
                )
                if any(i.get("joules_per_output_token") for i in items)
                else None,
                len(items),
            ]
        )
    out.append(
        md_table(
            [
                "engine",
                "shape",
                "prompts",
                "in/out",
                "out tok/s",
                "range",
                "total tok/s",
                "J/out tok",
                "repeats",
            ],
            rows,
        )
    )

    home = ["qwen3-0.6b-tp1", "qwen3-1.7b-tp1", "qwen3.5-4b-tp1", "qwen3.5-9b-tp1",
            "qwen3.6-35b-a3b-tp1-seqs128", "qwen3.6-35b-a3b-tp2", "qwen3-32b-tp1",
            "qwen3-32b-tp2", "qwen3-32b-tp4"]  # fmt: skip
    out.append("\n### Pivot: long output (512 in, 4,096 out) by concurrency\n")
    rows = []
    for eid in home:
        cs = {k: by.get((eid, f"longout-c{k}")) for k in (1, 8, 32, 128)}
        if not any(cs.values()):
            continue

        def get(k: int, key: str, cs: dict = cs) -> Any:
            return cs[k].get(key) if cs[k] else None

        top = cs[128]
        rows.append(
            [eid]
            + [get(k, "output_throughput") for k in (1, 8, 32, 128)]
            + [get(k, "median_tpot_ms") for k in (1, 128)]
            + [pct(top.get("peak_kv_cache_usage_perc")) if top else "-"]
            + [get(128, "delta_num_preemptions_total")]
            + [get(k, "joules_per_output_token") for k in (1, 128)]
        )
    out.append(md_table(["engine", "tok/s c1", "tok/s c8", "tok/s c32", "tok/s c128", "TPOT c1 ms",
                         "TPOT c128 ms", "peak KV c128", "preempt c128", "J/tok c1",
                         "J/tok c128"], rows))  # fmt: skip
    out.append("\n### Pivot: 8k-token prompts (8,192 in, 256 out) by concurrency\n")
    rows = []
    for eid in home:
        cs = {k: by.get((eid, f"in8k-c{k}")) for k in (1, 8, 32, 128)}
        if not any(cs.values()):
            continue
        peaks = [float(c.get("peak_kv_cache_usage_perc") or 0) for c in cs.values() if c]

        def get8(k: int, key: str, cs: dict = cs) -> Any:
            return cs[k].get(key) if cs[k] else None

        rows.append(
            [eid]
            + [get8(k, "median_ttft_ms") for k in (1, 8, 32, 128)]
            + [get8(k, "total_token_throughput") for k in (1, 128)]
            + [get8(k, "median_tpot_ms") for k in (1, 32)]
            + [pct(max(peaks)) if peaks else "-"]
        )
    out.append(md_table(["engine", "TTFT c1 ms", "TTFT c8 ms", "TTFT c32 ms", "TTFT c128 ms",
                         "total tok/s c1", "total tok/s c128", "TPOT c1 ms", "TPOT c32 ms",
                         "max peak KV"], rows))  # fmt: skip

    spreads = [
        c[k] for c in cells for k in ("output_throughput_rel_range",) if c.get(k) is not None
    ]
    tpots = [
        c["median_tpot_ms_rel_range"]
        for c in cells
        if c.get("median_tpot_ms_rel_range") is not None
    ]
    ttfts = [
        c["median_ttft_ms_rel_range"]
        for c in cells
        if c.get("median_ttft_ms_rel_range") is not None
    ]
    out.append("\n### Run-to-run spread ((max-min)/mean over the two repeats, all serving cells)\n")
    rows = []
    for name, values in (("output tok/s", spreads), ("median TPOT", tpots), ("median TTFT", ttfts)):
        if values:
            ordered = sorted(values)
            rows.append(
                [
                    name,
                    len(values),
                    pct(statistics.median(ordered)),
                    pct(ordered[int(0.9 * (len(ordered) - 1))]),
                    pct(ordered[-1]),
                ]
            )
    out.append(md_table(["metric", "cells", "median", "p90", "max"], rows))
    not_ok = [r for r in serve if r.get("status") != "ok"]
    out.append(f"\nServing runs: {len(serve)}, not ok: {len(not_ok)}.\n")
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jobs_root", type=Path, help="directory of collected job directories")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    serve, offline, engines_table, models_out = [], [], [], {}
    for job in job_dirs(args.jobs_root):
        models = (
            load_json(job / "ib" / "models.json") if (job / "ib" / "models.json").is_file() else {}
        )
        nvml = load_nvml(job / "ib" / "nvml.csv")
        rows, by_id = engine_rows(job, models)
        engines_table += rows
        serve += serve_rows(job, nvml, models, by_id)
        offline += offline_rows(job, nvml)
        for model_id, record in models.items():
            if "config" in record:
                geo = geometry(record)
                models_out[model_id] = {
                    "revision": record.get("revision"),
                    "receipt_sha256": record.get("receipt_sha256"),
                    "artifact_root_sha256": record.get("artifact_root_sha256"),
                    "total_bytes": record.get("total_bytes"),
                    "verified_by": record.get("verified_by"),
                    "verify_exit": record.get("verify_exit", 0),
                    **{k: v for k, v in geo.items() if k != "excluded_bytes"},
                    "excluded_bytes": geo["excluded_bytes"],
                }
    cells = aggregate(serve)
    write_csv(args.out / "serve_runs.csv", serve)
    write_csv(args.out / "serve_cells.csv", cells)
    write_csv(args.out / "offline_runs.csv", offline)
    write_csv(args.out / "engines.csv", engines_table)
    (args.out / "tables.md").write_text(markdown(cells, engines_table, offline, serve))
    summary = {
        "claim_level": "exploratory",
        "serve_runs": len(serve),
        "serve_runs_ok": sum(1 for r in serve if r.get("status") == "ok"),
        "serve_runs_not_ok": [
            {k: r.get(k) for k in ("job", "engine_id", "cell_id", "repeat", "status")}
            for r in serve
            if r.get("status") != "ok"
        ],
        "offline_runs": len(offline),
        "engines": len(engines_table),
        "models": models_out,
        "bandwidth_model": (
            "bytes per decode step = weights a token touches (all text tensors except the "
            "input embedding; MoE routed experts scaled by 1-(1-k/E)^B for B running sequences) "
            "+ B x (input + output/2) x KV bytes per token + B x GDN state x 2 (read+write), "
            "divided by TP and by the median ITL; compared with 3.35 TB/s per H100"
        ),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "models"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
