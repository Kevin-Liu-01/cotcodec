#!/usr/bin/env python3
"""Exploratory vLLM inference baseline on H100 (experiment inference-baseline-v1).

Not a registered experiment: it records where time and HBM go when vLLM serves the models on
persistent storage, labelled exploratory everywhere. It runs inside the digest-pinned
cotcodec-vllm overlay through the docker-research lane, one Slurm job per ``jobs`` entry of
``experiments/serving/inference-baseline-v1.yaml``.

Subcommands:

* ``plan --job J``: print the resolved plan (engines, argv, cells) as JSON. CPU only.
* ``run --job J --output-dir D --allocation-minutes M``: the job workload. For each engine it
  starts ``vllm serve``, warms it up, runs every serving cell (``vllm bench serve`` code,
  in-process in a long-lived client) twice, resetting the prefix cache before each run, then
  stops the engine and runs the offline cells (``vllm bench throughput`` code) in a separate
  process. NVML (memory, power, energy, clocks, utilization) is sampled for the whole job and
  the engine's Prometheus metrics (KV-cache usage, queue, preemptions, prefix-cache counters)
  for every run.
* ``client``: the benchmark client (JSON lines on stdin, one ``vllm bench serve`` run each).
* ``offline --spec S``: the offline throughput process for one engine.

Every model the job uses besides the lane's primary model is re-verified against its receipt
with ``scripts/fetch_open_model.py verify`` before its engine starts.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import os
import queue
import re
import signal
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "serving" / "inference-baseline-v1.yaml"
MODEL_ROOT = Path("/model-cache/cotcodec-models")
RECEIPT_ROOT = Path("/model-cache/cotcodec-receipts")
HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"
SERVED_NAME = "ib"
SENTINEL = "@@IB@@ "
GIB = 1024**3

#: Cache and runtime directories for vLLM, Triton, Inductor and FlashInfer, under the run dir.
CACHE_DIRS = {
    "HOME": "home",
    "XDG_CACHE_HOME": "xdg-cache",
    "XDG_CONFIG_HOME": "xdg-config",
    "VLLM_CACHE_ROOT": "vllm",
    "VLLM_CONFIG_ROOT": "vllm-config",
    "VLLM_RPC_BASE_PATH": "rpc",
    "TRITON_CACHE_DIR": "triton",
    "TRITON_HOME": "triton-home",
    "TORCHINDUCTOR_CACHE_DIR": "inductor",
    "TORCH_HOME": "torch",
    "CUDA_CACHE_PATH": "cuda",
    "FLASHINFER_WORKSPACE_BASE": "flashinfer",
    "VLLM_FLASHINFER_AUTOTUNE_CACHE_DIR": "flashinfer-autotune",
    "DG_JIT_CACHE_DIR": "deepgemm",
    "TMPDIR": "tmp",
}
FIXED_ENV = {
    "VLLM_NO_USAGE_STATS": "1",
    "DO_NOT_TRACK": "1",
    "VLLM_DO_NOT_TRACK": "1",
    "VLLM_HOST_IP": HOST,
    # Exposes POST /reset_prefix_cache, used before every measured run.
    "VLLM_SERVER_DEV_MODE": "1",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "PYTHONUNBUFFERED": "1",
    "VLLM_LOGGING_LEVEL": "INFO",
}

#: Prometheus series kept per run (summed over label sets).
METRIC_NAMES = (
    "vllm:kv_cache_usage_perc",
    "vllm:num_requests_running",
    "vllm:num_requests_waiting",
    "vllm:num_preemptions_total",
    "vllm:prefix_cache_queries_total",
    "vllm:prefix_cache_hits_total",
    "vllm:prompt_tokens_total",
    "vllm:generation_tokens_total",
)
NVML_FIELDS = (
    "t",
    "gpu",
    "mem_used_mib",
    "power_w",
    "energy_mj",
    "util_gpu_pct",
    "util_mem_pct",
    "sm_clock_mhz",
    "mem_clock_mhz",
    "temp_c",
    "throttle_reasons",
)


# --------------------------------------------------------------------------- config and plan


class PlanError(ValueError):
    """The config or the requested job is invalid."""


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise PlanError("config must be a schema_version 1 mapping")
    if config.get("claim_level") != "exploratory":
        raise PlanError("this driver only runs the exploratory baseline")
    for key in ("shapes", "num_prompts", "grids", "jobs", "models", "engine_defaults"):
        if not isinstance(config.get(key), dict):
            raise PlanError(f"config.{key} must be a mapping")
    return config


def expand_grid(config: dict[str, Any], name: str, _depth: int = 0) -> list[tuple[str, int]]:
    if _depth > 4:
        raise PlanError(f"grid {name} nests too deeply")
    grid = config["grids"].get(name)
    if not isinstance(grid, list) or not grid:
        raise PlanError(f"unknown or empty grid {name}")
    cells: list[tuple[str, int]] = []
    for item in grid:
        if isinstance(item, str):
            cells.extend(expand_grid(config, item, _depth + 1))
        elif isinstance(item, list) and len(item) == 2:
            cells.append((str(item[0]), int(item[1])))
        else:
            raise PlanError(f"grid {name}: bad cell {item!r}")
    if len(set(cells)) != len(cells):
        raise PlanError(f"grid {name} repeats a cell")
    return cells


def cell_spec(config: dict[str, Any], shape: str, concurrency: int) -> dict[str, Any]:
    if shape == "prefix":
        workload = config["prefix_workload"]
        counts = workload["num_prompts"]
        if concurrency not in counts:
            raise PlanError(f"prefix workload has no prompt count for concurrency {concurrency}")
        return {
            "cell_id": f"prefix-c{concurrency}",
            "shape": "prefix",
            "concurrency": concurrency,
            "num_prompts": int(counts[concurrency]),
            "input_len": int(workload["prefix_len"]) + int(workload["suffix_len"]),
            "output_len": int(workload["output_len"]),
            "prefix_len": int(workload["prefix_len"]),
            "suffix_len": int(workload["suffix_len"]),
            "num_prefixes": int(workload["num_prefixes"]),
        }
    if shape not in config["shapes"]:
        raise PlanError(f"unknown shape {shape}")
    counts = config["num_prompts"].get(shape, {})
    if concurrency not in counts:
        raise PlanError(f"no prompt count for {shape} at concurrency {concurrency}")
    dims = config["shapes"][shape]
    return {
        "cell_id": f"{shape}-c{concurrency}",
        "shape": shape,
        "concurrency": concurrency,
        "num_prompts": int(counts[concurrency]),
        "input_len": int(dims["input_len"]),
        "output_len": int(dims["output_len"]),
    }


def resolve_engine(config: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    defaults = config["engine_defaults"]
    model = raw["model"]
    if model not in config["models"]:
        raise PlanError(f"engine {raw.get('id')}: unknown model {model}")
    engine = {
        "id": raw["id"],
        "model": model,
        "family": config["models"][model]["family"],
        "model_dir": str(MODEL_ROOT / model),
        "tp": int(raw.get("tp", 1)),
        "dtype": raw.get("dtype", defaults["dtype"]),
        "gpu_memory_utilization": float(
            raw.get("gpu_memory_utilization", defaults["gpu_memory_utilization"])
        ),
        "max_model_len": int(raw.get("max_model_len", defaults["max_model_len"])),
        "max_num_seqs": int(raw.get("max_num_seqs", defaults["max_num_seqs"])),
        "max_num_batched_tokens": int(
            raw.get("max_num_batched_tokens", defaults["max_num_batched_tokens"])
        ),
        "prefix_caching": bool(raw.get("prefix_caching", defaults["prefix_caching"])),
        "kv_cache_dtype": str(raw.get("kv_cache_dtype", defaults["kv_cache_dtype"])),
        "text_only_flags": list(config["models"][model].get("text_only_flags", [])),
        "grid": raw["grid"],
        "offline": bool(raw.get("offline", False)),
        "offline_scale": float(raw.get("offline_scale", 1.0)),
    }
    cells = [cell_spec(config, shape, conc) for shape, conc in expand_grid(config, raw["grid"])]
    for cell in cells:
        if cell["input_len"] + cell["output_len"] > engine["max_model_len"]:
            raise PlanError(
                f"engine {engine['id']}: cell {cell['cell_id']} exceeds max_model_len "
                f"{engine['max_model_len']}"
            )
    engine["cells"] = cells
    engine["serve_argv"] = serve_argv(engine, int(config["seed"]))
    engine["offline_cells"] = offline_cells(config, engine) if engine["offline"] else []
    return engine


def engine_flags(engine: dict[str, Any], seed: int) -> list[str]:
    """Engine flags shared by ``vllm serve`` and the offline LLM."""
    return [
        "--tensor-parallel-size", str(engine["tp"]),
        "--dtype", engine["dtype"],
        "--seed", str(seed),
        "--max-model-len", str(engine["max_model_len"]),
        "--gpu-memory-utilization", str(engine["gpu_memory_utilization"]),
        "--max-num-seqs", str(engine["max_num_seqs"]),
        "--max-num-batched-tokens", str(engine["max_num_batched_tokens"]),
        "--enable-prefix-caching" if engine["prefix_caching"] else "--no-enable-prefix-caching",
        "--kv-cache-dtype", engine["kv_cache_dtype"],
        "--generation-config", "vllm",
        "--load-format", "auto",
        *engine["text_only_flags"],
    ]  # fmt: skip


def serve_argv(engine: dict[str, Any], seed: int) -> list[str]:
    return [
        "vllm", "serve", engine["model_dir"],
        "--served-model-name", SERVED_NAME,
        "--host", HOST, "--port", str(PORT),
        "--disable-uvicorn-access-log",
        *engine_flags(engine, seed),
    ]  # fmt: skip


def offline_cells(config: dict[str, Any], engine: dict[str, Any]) -> list[dict[str, Any]]:
    cells = []
    for name, dims in config["offline_shapes"].items():
        prompts = max(8, int(round(int(dims["num_prompts"]) * engine["offline_scale"])))
        cells.append(
            {
                "cell_id": f"offline-{name}",
                "shape": name,
                "input_len": int(dims["input_len"]),
                "output_len": int(dims["output_len"]),
                "num_prompts": prompts,
            }
        )
    return cells


def bench_serve_argv(
    engine: dict[str, Any],
    cell: dict[str, Any],
    *,
    seed: int,
    result_dir: Path,
    result_filename: str,
    label: str,
) -> list[str]:
    argv = [
        "--backend", "vllm",
        "--base-url", BASE_URL,
        "--endpoint", "/v1/completions",
        "--model", engine["model_dir"],
        "--tokenizer", engine["model_dir"],
        "--served-model-name", SERVED_NAME,
        "--num-prompts", str(cell["num_prompts"]),
        "--max-concurrency", str(cell["concurrency"]),
        "--request-rate", "inf",
        "--ignore-eos",
        "--temperature", "0",
        "--seed", str(seed),
        "--percentile-metrics", "ttft,tpot,itl,e2el",
        "--metric-percentiles", "50,90,99",
        # The ready check sends the first prompt once before the run, which would seed the
        # prefix cache for request 0; the driver checks health itself instead.
        "--ready-check-timeout-sec", "0",
        "--disable-tqdm",
        "--save-result",
        "--result-dir", str(result_dir),
        "--result-filename", result_filename,
        "--label", label,
    ]  # fmt: skip
    if cell["shape"] == "prefix":
        argv += [
            "--dataset-name", "prefix_repetition",
            "--prefix-repetition-prefix-len", str(cell["prefix_len"]),
            "--prefix-repetition-suffix-len", str(cell["suffix_len"]),
            "--prefix-repetition-num-prefixes", str(cell["num_prefixes"]),
            "--prefix-repetition-output-len", str(cell["output_len"]),
        ]  # fmt: skip
    else:
        argv += [
            "--dataset-name", "random",
            "--random-input-len", str(cell["input_len"]),
            "--random-output-len", str(cell["output_len"]),
            "--random-range-ratio", "0",
        ]  # fmt: skip
    return argv


def offline_argv(engine: dict[str, Any], cell: dict[str, Any], seed: int) -> list[str]:
    """``vllm bench throughput`` argv for one offline cell (random prompts, all at once)."""
    return [
        "--backend", "vllm",
        "--model", engine["model_dir"],
        "--tokenizer", engine["model_dir"],
        *engine_flags(engine, seed),
        "--dataset-name", "random",
        "--random-input-len", str(cell["input_len"]),
        "--random-output-len", str(cell["output_len"]),
        "--random-range-ratio", "0",
        "--num-prompts", str(cell["num_prompts"]),
        "--disable-detokenize",
    ]  # fmt: skip


def resolve_plan(config: dict[str, Any], job: str) -> dict[str, Any]:
    jobs = config["jobs"]
    if job not in jobs:
        raise PlanError(f"unknown job {job}; known: {sorted(jobs)}")
    spec = jobs[job]
    engines = [resolve_engine(config, raw) for raw in spec["engines"]]
    gpus = int(spec["gpus"])
    for engine in engines:
        if engine["tp"] > gpus:
            raise PlanError(f"engine {engine['id']} needs TP {engine['tp']} > {gpus} GPUs")
    if len({engine["id"] for engine in engines}) != len(engines):
        raise PlanError(f"job {job} repeats an engine id")
    models = []
    for engine in engines:
        if engine["model"] not in models:
            models.append(engine["model"])
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": config["claim_level"],
        "job": job,
        "gpus": gpus,
        "primary_model": spec["primary_model"],
        "models": models,
        "seed": int(config["seed"]),
        "repeats": int(config["repeats"]),
        "engines": engines,
    }


# --------------------------------------------------------------------------- parsers


_ENGINE_LOG_PATTERNS: dict[str, re.Pattern[str]] = {
    "weights_gib": re.compile(r"Model loading took ([0-9.]+) GiB memory and ([0-9.]+) seconds"),
    "kv_cache_gib": re.compile(r"Available KV cache memory: ([0-9.]+) GiB"),
    "kv_cache_tokens": re.compile(r"GPU KV cache size: ([0-9,]+) tokens"),
    "max_concurrency": re.compile(
        r"Maximum concurrency for ([0-9,]+) tokens per request: ([0-9.]+)x"
    ),
    "cuda_graph_gib": re.compile(r"Graph capturing finished in ([0-9.]+) secs, took ([0-9.]+) GiB"),
    "actual_usage": re.compile(
        r"Actual usage is ([0-9.]+) GiB for consumed memory \(weights \+ non-torch\), "
        r"([0-9.]+) GiB for peak activation, and ([0-9.]+) GiB for CUDAGraph memory"
    ),
    "init_engine_s": re.compile(
        r"init engine \(profile, create kv cache, warmup model\) took ([0-9.]+) s"
        r"(?: \(compilation: ([0-9.]+) s\))?"
    ),
    "torch_compile_s": re.compile(r"torch\.compile took ([0-9.]+) s in total"),
    "attention_backend": re.compile(r"Using ([A-Z_0-9]+) attention backend"),
    "architecture": re.compile(r"Resolved architecture: (\S+)"),
}


def _number(text: str) -> float:
    return float(text.replace(",", ""))


def parse_engine_log(text: str) -> dict[str, Any]:
    """HBM breakdown and start-up timings from a vLLM engine log (last match per rank)."""
    out: dict[str, Any] = {}
    weights = [
        (_number(a), _number(b)) for a, b in _ENGINE_LOG_PATTERNS["weights_gib"].findall(text)
    ]
    if weights:
        out["weights_gib_per_rank"] = [w for w, _ in weights]
        out["weights_load_s"] = max(s for _, s in weights)
    kv = [_number(x) for x in _ENGINE_LOG_PATTERNS["kv_cache_gib"].findall(text)]
    if kv:
        out["kv_cache_gib_per_rank"] = kv
    tokens = [_number(x) for x in _ENGINE_LOG_PATTERNS["kv_cache_tokens"].findall(text)]
    if tokens:
        out["kv_cache_tokens"] = int(tokens[-1])
    conc = _ENGINE_LOG_PATTERNS["max_concurrency"].findall(text)
    if conc:
        out["max_concurrency_at_len"] = {
            "len": int(_number(conc[-1][0])),
            "x": _number(conc[-1][1]),
        }
    graphs = _ENGINE_LOG_PATTERNS["cuda_graph_gib"].findall(text)
    if graphs:
        out["cuda_graph_capture"] = [{"seconds": _number(s), "gib": _number(g)} for s, g in graphs]
    usage = _ENGINE_LOG_PATTERNS["actual_usage"].findall(text)
    if usage:
        out["actual_usage_gib_per_rank"] = [
            {"weights_plus_non_torch": _number(a), "peak_activation": _number(b),
             "cuda_graph": _number(c)}
            for a, b, c in usage
        ]  # fmt: skip
    init = _ENGINE_LOG_PATTERNS["init_engine_s"].findall(text)
    if init:
        out["init_engine_s"] = _number(init[-1][0])
        if init[-1][1]:
            out["compilation_s"] = _number(init[-1][1])
    compile_s = _ENGINE_LOG_PATTERNS["torch_compile_s"].findall(text)
    if compile_s:
        out["torch_compile_s"] = _number(compile_s[-1])
    backends = sorted(set(_ENGINE_LOG_PATTERNS["attention_backend"].findall(text)))
    if backends:
        out["attention_backends"] = backends
    arch = _ENGINE_LOG_PATTERNS["architecture"].findall(text)
    if arch:
        out["architecture"] = arch[-1]
    return out


_PROM_LINE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(\S+)")
_PROM_LABEL = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"')


def parse_prometheus(text: str) -> tuple[dict[str, float], dict[str, str]]:
    """Selected vLLM series summed over label sets, and the cache_config_info labels."""
    values: dict[str, float] = {}
    cache_info: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        match = _PROM_LINE.match(line)
        if not match:
            continue
        name, labels, raw = match.groups()
        if name == "vllm:cache_config_info" and labels:
            cache_info = dict(_PROM_LABEL.findall(labels))
            continue
        if name in METRIC_NAMES:
            try:
                value = float(raw)
            except ValueError:
                continue
            values[name] = values.get(name, 0.0) + value
    return values, cache_info


# --------------------------------------------------------------------------- safetensors


def safetensors_breakdown(model_dir: Path) -> dict[str, Any]:
    """Bytes per tensor category from the safetensors headers (no tensor data is read)."""
    categories: dict[str, int] = {}
    tensors = 0
    for shard in sorted(model_dir.glob("*.safetensors")):
        with shard.open("rb") as handle:
            (length,) = struct.unpack("<Q", handle.read(8))
            header = json.loads(handle.read(length))
        for name, meta in header.items():
            if name == "__metadata__":
                continue
            start, end = meta["data_offsets"]
            category = tensor_category(name)
            categories[category] = categories.get(category, 0) + int(end) - int(start)
            tensors += 1
    return {
        "bytes_by_category": categories,
        "tensors": tensors,
        "total_bytes": sum(categories.values()),
    }


def tensor_category(name: str) -> str:
    lowered = name.lower()
    if "visual" in lowered or "vision" in lowered:
        return "vision"
    if lowered.startswith("mtp.") or ".mtp." in lowered:
        return "mtp"
    if "embed_tokens" in lowered:
        return "embed_tokens"
    if "lm_head" in lowered:
        return "lm_head"
    if "shared_expert" in lowered:
        return "shared_expert"
    if ".experts." in lowered:
        return "routed_experts"
    if lowered.endswith("mlp.gate.weight"):
        return "router"
    if "linear_attn" in lowered:
        return "linear_attention"
    if "self_attn" in lowered:
        return "full_attention"
    if ".mlp." in lowered:
        return "dense_mlp"
    return "other"


# --------------------------------------------------------------------------- samplers


class NvmlSampler(threading.Thread):
    """Samples every visible GPU through NVML into one CSV for the whole job."""

    def __init__(self, path: Path, interval_s: float) -> None:
        super().__init__(daemon=True)
        self.path = path
        self.interval_s = interval_s
        self.stop_event = threading.Event()
        self.error: str | None = None

    def run(self) -> None:
        try:
            import pynvml

            pynvml.nvmlInit()
            handles = [
                pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(pynvml.nvmlDeviceGetCount())
            ]
        except Exception as exc:  # noqa: BLE001 - recorded, the job continues without NVML
            self.error = f"nvml init failed: {exc!r}"
            return
        reasons = getattr(pynvml, "nvmlDeviceGetCurrentClocksEventReasons", None)
        if reasons is None:
            reasons = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons
        getters = (
            lambda d: pynvml.nvmlDeviceGetMemoryInfo(d).used // (1024 * 1024),
            lambda d: round(pynvml.nvmlDeviceGetPowerUsage(d) / 1000.0, 2),
            pynvml.nvmlDeviceGetTotalEnergyConsumption,
            lambda d: pynvml.nvmlDeviceGetUtilizationRates(d).gpu,
            lambda d: pynvml.nvmlDeviceGetUtilizationRates(d).memory,
            lambda d: pynvml.nvmlDeviceGetClockInfo(d, pynvml.NVML_CLOCK_SM),
            lambda d: pynvml.nvmlDeviceGetClockInfo(d, pynvml.NVML_CLOCK_MEM),
            lambda d: pynvml.nvmlDeviceGetTemperature(d, pynvml.NVML_TEMPERATURE_GPU),
            lambda d: hex(reasons(d)),
        )
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(NVML_FIELDS)
            while not self.stop_event.is_set():
                now = time.time()
                for index, device in enumerate(handles):
                    row: list[Any] = [f"{now:.3f}", index]
                    for getter in getters:
                        try:
                            row.append(getter(device))
                        except Exception:  # noqa: BLE001 - one missing field is not fatal
                            row.append("")
                    writer.writerow(row)
                handle.flush()
                self.stop_event.wait(self.interval_s)


class MetricsPoller(threading.Thread):
    """Polls the engine's /metrics during one run."""

    def __init__(self, path: Path, interval_s: float) -> None:
        super().__init__(daemon=True)
        self.path = path
        self.interval_s = interval_s
        self.stop_event = threading.Event()
        self.rows: list[dict[str, float]] = []

    def run(self) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["t", *METRIC_NAMES])
            while not self.stop_event.is_set():
                snapshot = scrape_metrics()
                if snapshot is not None:
                    values, _ = snapshot
                    row = {"t": time.time(), **values}
                    self.rows.append(row)
                    writer.writerow([f"{row['t']:.3f}", *(values.get(n, "") for n in METRIC_NAMES)])
                    handle.flush()
                self.stop_event.wait(self.interval_s)


def http_get(path: str, timeout: float = 5.0) -> tuple[int, str]:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=timeout) as response:  # noqa: S310
        return response.status, response.read().decode("utf-8", "replace")


def http_post(path: str, timeout: float = 30.0) -> tuple[int, str]:
    request = urllib.request.Request(f"{BASE_URL}{path}", data=b"", method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.status, response.read().decode("utf-8", "replace")


def scrape_metrics() -> tuple[dict[str, float], dict[str, str]] | None:
    try:
        status, body = http_get("/metrics")
    except (OSError, urllib.error.URLError):
        return None
    if status != 200:
        return None
    return parse_prometheus(body)


def summarize_metrics(
    rows: list[dict[str, float]], before: dict[str, float] | None, after: dict[str, float] | None
) -> dict[str, Any]:
    out: dict[str, Any] = {"samples": len(rows)}
    for name in (
        "vllm:kv_cache_usage_perc",
        "vllm:num_requests_running",
        "vllm:num_requests_waiting",
    ):
        values = [row[name] for row in rows if name in row]
        if values:
            out[f"peak_{name.split(':', 1)[1]}"] = max(values)
            out[f"mean_{name.split(':', 1)[1]}"] = sum(values) / len(values)
    if before and after:
        for name in METRIC_NAMES:
            if name.endswith("_total") and name in before and name in after:
                out[f"delta_{name.split(':', 1)[1]}"] = after[name] - before[name]
        queries = out.get("delta_prefix_cache_queries_total")
        hits = out.get("delta_prefix_cache_hits_total")
        if queries:
            out["prefix_cache_hit_rate"] = (hits or 0.0) / queries
    return out


# --------------------------------------------------------------------------- driver


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def allocation_start(job_env: Path) -> tuple[float, str]:
    """The lane's started_at (written before the container), else now."""
    try:
        for line in job_env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key == "started_at":
                started = datetime.strptime(value.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
                return started.timestamp(), "job.env started_at"
    except (OSError, ValueError):
        pass
    return time.time(), "driver start"


class Driver:
    def __init__(
        self,
        plan: dict[str, Any],
        config: dict[str, Any],
        output_dir: Path,
        allocation_minutes: float,
    ) -> None:
        self.plan = plan
        self.config = config
        self.out = output_dir
        self.out.mkdir(parents=True, exist_ok=True)
        start, source = allocation_start(
            Path(os.environ.get("COTCODEC_OUTPUT_DIR", "/outputs")) / "job.env"
        )
        self.allocation_start = start
        self.allocation_source = source
        # Stop starting work 200 s before the limit (the lane signals USR1 at limit - 180 s).
        self.deadline = start + allocation_minutes * 60.0 - 200.0
        self.stop = threading.Event()
        self.stop_reason: str | None = None
        self.server: subprocess.Popen[bytes] | None = None
        self.client: subprocess.Popen[str] | None = None
        self.client_lines: queue.Queue[str] = queue.Queue()
        self.children: list[subprocess.Popen[Any]] = []
        self.summary: dict[str, Any] = {
            "experiment_id": plan["experiment_id"],
            "claim_level": "exploratory",
            "job": plan["job"],
            "started_at": utc_now(),
            "allocation_minutes": allocation_minutes,
            "allocation_start_source": source,
            "engines": [],
            "runs": [],
            "offline": [],
        }
        self.env = self.engine_env()
        self.durations: dict[tuple[str, str], float] = {}

    # ---------------------------------------------------------------- helpers

    def log(self, event: str, **fields: Any) -> None:
        record = {"t": round(time.time(), 3), "utc": utc_now(), "event": event, **fields}
        with (self.out / "progress.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    def remaining(self) -> float:
        return self.deadline - time.time()

    def engine_env(self) -> dict[str, str]:
        cache = self.out / "cache"
        env = dict(os.environ)
        for key, sub in CACHE_DIRS.items():
            path = cache / sub
            path.mkdir(parents=True, exist_ok=True)
            env[key] = str(path)
        env.update(FIXED_ENV)
        env.update({k: str(v) for k, v in self.config["vllm"].get("env", {}).items()})
        return env

    def handle_signal(self, signum: int, _frame: Any) -> None:
        self.stop_reason = signal.Signals(signum).name
        self.stop.set()
        # Unblock a waiting client read; the main loop then tears everything down.
        self.client_lines.put(SENTINEL + json.dumps({"signal": self.stop_reason}))

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_summary(self) -> None:
        self.summary["updated_at"] = utc_now()
        self.write_json(self.out / "summary.json", self.summary)

    # ---------------------------------------------------------------- environment and models

    def record_environment(self) -> None:
        info: dict[str, Any] = {"utc": utc_now(), "python": sys.version}
        try:
            import torch
            import vllm

            info.update(
                vllm=vllm.__version__,
                torch=torch.__version__,
                torch_cuda=torch.version.cuda,
            )
        except Exception as exc:  # noqa: BLE001
            info["import_error"] = repr(exc)
        try:
            import pynvml

            pynvml.nvmlInit()
            info["driver"] = pynvml.nvmlSystemGetDriverVersion()
            info["nvml"] = pynvml.nvmlSystemGetNVMLVersion()
            gpus = []
            for i in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                gpu = {
                    "index": i,
                    "name": pynvml.nvmlDeviceGetName(handle),
                    "uuid": pynvml.nvmlDeviceGetUUID(handle),
                    "memory_total_mib": pynvml.nvmlDeviceGetMemoryInfo(handle).total
                    // (1024 * 1024),
                    "power_limit_w": pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0,
                    "max_sm_clock_mhz": pynvml.nvmlDeviceGetMaxClockInfo(
                        handle, pynvml.NVML_CLOCK_SM
                    ),
                    "max_mem_clock_mhz": pynvml.nvmlDeviceGetMaxClockInfo(
                        handle, pynvml.NVML_CLOCK_MEM
                    ),
                }
                try:
                    support = pynvml.nvmlGpmQueryDeviceSupport(handle)
                    gpu["gpm_supported"] = bool(getattr(support, "isSupportedDevice", support))
                except Exception as exc:  # noqa: BLE001 - recorded: GPM is admin-only here
                    gpu["gpm_supported"] = f"error: {exc!r}"
                gpus.append(gpu)
            info["gpus"] = gpus
        except Exception as exc:  # noqa: BLE001
            info["nvml_error"] = repr(exc)
        try:
            info["nvidia_smi_q"] = subprocess.run(
                ["nvidia-smi", "-q", "-d", "CLOCK,POWER,PERFORMANCE"],
                capture_output=True, text=True, timeout=60, check=False,
            ).stdout  # fmt: skip
        except (OSError, subprocess.SubprocessError) as exc:
            info["nvidia_smi_error"] = repr(exc)
        info["visible"] = {
            k: os.environ.get(k) for k in ("CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES")
        }
        info["lane"] = {
            k: os.environ.get(k)
            for k in ("COTCODEC_GIT_SHA", "COTCODEC_SOURCE_SHA256", "COTCODEC_MODEL_ID",
                      "COTCODEC_EXPECTED_GPUS")
        }  # fmt: skip
        self.write_json(self.out / "environment.json", info)

    def verify_models(self) -> None:
        records = {}
        primary = os.environ.get("COTCODEC_MODEL_ID")
        for model in self.plan["models"]:
            record: dict[str, Any] = {"model_id": model, "model_dir": str(MODEL_ROOT / model)}
            receipt = RECEIPT_ROOT / f"{model}.json"
            if receipt.is_file():
                record["receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
                data = json.loads(receipt.read_text(encoding="utf-8"))
                for key in ("revision", "repo_id", "total_bytes", "artifact_root_sha256", "mode"):
                    record[key] = data.get(key)
            if model == primary:
                record["verified_by"] = "lane (model-verification.txt)"
            else:
                started = time.time()
                result = subprocess.run(
                    [sys.executable, str(PROJECT_ROOT / "scripts" / "fetch_open_model.py"),
                     "--model-root", str(MODEL_ROOT), "--receipt-root", str(RECEIPT_ROOT),
                     "verify", model],
                    capture_output=True, text=True, check=False,
                )  # fmt: skip
                record["verified_by"] = "driver: fetch_open_model.py verify"
                record["verify_exit"] = result.returncode
                record["verify_stdout"] = result.stdout[-2000:]
                record["verify_stderr"] = result.stderr[-2000:]
                record["verify_s"] = round(time.time() - started, 1)
            try:
                record["safetensors"] = safetensors_breakdown(MODEL_ROOT / model)
            except Exception as exc:  # noqa: BLE001
                record["safetensors_error"] = repr(exc)
            try:
                record["config"] = json.loads((MODEL_ROOT / model / "config.json").read_text())
            except Exception as exc:  # noqa: BLE001
                record["config_error"] = repr(exc)
            records[model] = record
            self.log(
                "model-verified",
                model=model,
                verified_by=record["verified_by"],
                exit=record.get("verify_exit", 0),
            )
        self.write_json(self.out / "models.json", records)
        self.model_records = records

    # ---------------------------------------------------------------- engine lifecycle

    def gpu_memory_used_mib(self) -> list[int]:
        try:
            import pynvml

            pynvml.nvmlInit()
            return [
                pynvml.nvmlDeviceGetMemoryInfo(pynvml.nvmlDeviceGetHandleByIndex(i)).used
                // (1024 * 1024)
                for i in range(pynvml.nvmlDeviceGetCount())
            ]
        except Exception:  # noqa: BLE001
            return []

    def wait_gpu_release(self, timeout_s: float = 120.0) -> list[int]:
        end = time.time() + timeout_s
        used = self.gpu_memory_used_mib()
        while used and max(used) > 1024 and time.time() < end:
            time.sleep(2)
            used = self.gpu_memory_used_mib()
        return used

    def start_server(self, engine: dict[str, Any], engine_dir: Path) -> dict[str, Any]:
        engine_dir.mkdir(parents=True, exist_ok=True)
        log_path = engine_dir / "engine.log"
        record: dict[str, Any] = {
            "engine_id": engine["id"],
            "argv": engine["serve_argv"],
            "gpu_memory_before_mib": self.gpu_memory_used_mib(),
            "start_t": time.time(),
        }
        log = log_path.open("ab")
        self.server = subprocess.Popen(  # noqa: S603 - fixed argv from the config
            engine["serve_argv"], env=self.env, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )  # fmt: skip
        log.close()
        timeout = min(900.0, max(60.0, self.remaining()))
        end = time.time() + timeout
        ready = False
        while time.time() < end and not self.stop.is_set():
            if self.server.poll() is not None:
                break
            try:
                status, _ = http_get("/health", timeout=2.0)
                if status == 200:
                    status_models, body = http_get("/v1/models", timeout=5.0)
                    ready = status_models == 200 and f'"id":"{SERVED_NAME}"' in body.replace(
                        " ", ""
                    )
                    if ready:
                        break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(2)
        record["ready"] = ready
        record["ready_t"] = time.time()
        record["ready_s"] = round(record["ready_t"] - record["start_t"], 1)
        record["exit_code_at_ready"] = self.server.poll()
        snapshot = scrape_metrics() if ready else None
        if snapshot:
            record["cache_config_info"] = snapshot[1]
        record["gpu_memory_ready_mib"] = self.gpu_memory_used_mib()
        record["log_parse"] = parse_engine_log(
            log_path.read_text(encoding="utf-8", errors="replace")
        )
        return record

    def stop_process(
        self, process: subprocess.Popen[Any] | None, grace_s: float = 60.0
    ) -> int | None:
        if process is None:
            return None
        if process.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=grace_s)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=30)
        else:
            # The leader exited; make sure no worker of its group survives.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        return process.returncode

    # ---------------------------------------------------------------- client

    def start_client(self) -> None:
        log = (self.out / "client.log").open("a", encoding="utf-8")
        self.client = subprocess.Popen(  # noqa: S603
            [sys.executable, str(Path(__file__).resolve()), "client"],
            env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
            text=True, bufsize=1, start_new_session=True,
        )  # fmt: skip
        self.client_lines = queue.Queue()

        def pump(stream: Any, sink: queue.Queue[str], logfile: Any) -> None:
            for line in stream:
                logfile.write(line)
                logfile.flush()
                if line.startswith(SENTINEL):
                    sink.put(line)
            sink.put(SENTINEL + json.dumps({"eof": True}))

        threading.Thread(
            target=pump, args=(self.client.stdout, self.client_lines, log), daemon=True
        ).start()

    def client_run(self, argv: list[str], timeout_s: float) -> dict[str, Any]:
        if self.client is None or self.client.poll() is not None:
            self.start_client()
        assert self.client is not None and self.client.stdin is not None
        self.client.stdin.write(json.dumps({"argv": argv}) + "\n")
        self.client.stdin.flush()
        try:
            line = self.client_lines.get(timeout=max(1.0, timeout_s))
        except queue.Empty:
            self.stop_process(self.client, grace_s=5)
            self.client = None
            return {"ok": False, "error": f"timeout after {timeout_s:.0f} s"}
        payload = json.loads(line[len(SENTINEL) :])
        if "signal" in payload or "eof" in payload:
            self.stop_process(self.client, grace_s=5)
            self.client = None
            return {"ok": False, "error": f"interrupted: {payload}"}
        return payload

    # ---------------------------------------------------------------- runs

    def reset_prefix_cache(self) -> dict[str, Any]:
        """POST /reset_prefix_cache until the engine reports success (it refuses while busy)."""
        last = "no attempt"
        for attempt in range(5):
            try:
                status, body = http_post("/reset_prefix_cache")
            except (OSError, urllib.error.URLError) as exc:
                last = repr(exc)
            else:
                try:
                    success = json.loads(body).get("success", True) if body.strip() else True
                except (ValueError, AttributeError):
                    success = True
                if status == 200 and success:
                    return {"ok": True, "status": status, "body": body[:200], "attempt": attempt}
                last = f"status {status}: {body[:200]}"
            time.sleep(1)
        return {"ok": False, "error": last}

    def estimate_s(self, engine_id: str, cell: dict[str, Any]) -> float:
        measured = self.durations.get((engine_id, cell["cell_id"]))
        if measured is not None:
            return measured * 1.15 + 15
        return 60.0

    def run_cell(
        self,
        engine: dict[str, Any],
        cell: dict[str, Any],
        repeat: int,
        runs_dir: Path,
        *,
        warmup: bool = False,
    ) -> dict[str, Any]:
        seed = self.plan["seed"] + (1000 if warmup else 0)
        name = f"{cell['cell_id']}-r{repeat}" if not warmup else f"warmup-{cell['cell_id']}"
        record: dict[str, Any] = {
            "engine_id": engine["id"], "model": engine["model"], "tp": engine["tp"],
            "kv_cache_dtype": engine["kv_cache_dtype"], "prefix_caching": engine["prefix_caching"],
            "cell_id": cell["cell_id"], "shape": cell["shape"], "concurrency": cell["concurrency"],
            "num_prompts": cell["num_prompts"], "input_len": cell["input_len"],
            "output_len": cell["output_len"], "repeat": repeat, "warmup": warmup, "name": name,
        }  # fmt: skip
        remaining = self.remaining()
        estimate = self.estimate_s(engine["id"], cell)
        if not warmup and remaining < estimate:
            record.update(
                status="skipped", reason=f"deadline: {remaining:.0f} s left < {estimate:.0f} s"
            )
            self.log("run-skipped", engine=engine["id"], run=name, reason=record["reason"])
            return record
        record["prefix_reset"] = (
            self.reset_prefix_cache() if engine["prefix_caching"] else {"ok": None}
        )
        time.sleep(float(self.config["sampling"]["settle_s"]))
        argv = bench_serve_argv(
            engine, cell, seed=seed, result_dir=runs_dir, result_filename=f"{name}.json",
            label=f"{engine['id']}/{name}",
        )  # fmt: skip
        record["bench_argv"] = argv
        before = scrape_metrics()
        poller = MetricsPoller(
            runs_dir / "metrics" / f"{name}.csv",
            float(self.config["sampling"]["metrics_interval_s"]),
        )
        (runs_dir / "metrics").mkdir(parents=True, exist_ok=True)
        poller.start()
        record["start_t"] = time.time()
        timeout = max(30.0, self.remaining() + 150.0) if not warmup else 600.0
        outcome = self.client_run(argv, timeout)
        record["end_t"] = time.time()
        poller.stop_event.set()
        poller.join(timeout=10)
        after = scrape_metrics()
        record["wall_s"] = round(record["end_t"] - record["start_t"], 3)
        record["client"] = outcome
        record["metrics"] = summarize_metrics(
            poller.rows, before[0] if before else None, after[0] if after else None
        )
        record["server_alive"] = self.server is not None and self.server.poll() is None
        result_path = runs_dir / f"{name}.json"
        if outcome.get("ok") and result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            expected = cell["num_prompts"] * cell["output_len"]
            record["completed"] = result.get("completed")
            record["failed"] = result.get("failed")
            record["total_output_tokens"] = result.get("total_output_tokens")
            record["output_tokens_ok"] = result.get("total_output_tokens") == expected
            record["status"] = "ok" if result.get("completed") == cell["num_prompts"] else "partial"
            if not warmup:
                self.durations[(engine["id"], cell["cell_id"])] = record["wall_s"]
        else:
            record["status"] = "failed"
        self.write_json(runs_dir / f"{name}.meta.json", record)
        self.log(
            "run-done",
            engine=engine["id"],
            run=name,
            status=record["status"],
            wall_s=record["wall_s"],
            hit_rate=record["metrics"].get("prefix_cache_hit_rate"),
        )
        return record

    def run_offline(self, engine: dict[str, Any], engine_dir: Path) -> dict[str, Any]:
        offline_dir = engine_dir / "offline"
        offline_dir.mkdir(parents=True, exist_ok=True)
        spec = {
            "engine": engine,
            "seed": self.plan["seed"],
            "repeats": self.plan["repeats"],
            "warmup_prompts": int(self.config["offline_warmup_prompts"]),
            "output_dir": str(offline_dir),
            "deadline": self.deadline,
        }
        spec_path = offline_dir / "spec.json"
        self.write_json(spec_path, spec)
        record: dict[str, Any] = {"engine_id": engine["id"], "start_t": time.time()}
        log = (offline_dir / "engine.log").open("ab")
        process = subprocess.Popen(  # noqa: S603
            [sys.executable, str(Path(__file__).resolve()), "offline", "--spec", str(spec_path)],
            env=self.env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )  # fmt: skip
        log.close()
        self.children.append(process)
        while process.poll() is None:
            if self.stop.is_set() or time.time() > self.deadline + 120:
                record["stopped"] = self.stop_reason or "deadline"
                break
            time.sleep(2)
        record["exit_code"] = self.stop_process(process, grace_s=60)
        record["end_t"] = time.time()
        record["wall_s"] = round(record["end_t"] - record["start_t"], 1)
        record["log_parse"] = parse_engine_log(
            (offline_dir / "engine.log").read_text(encoding="utf-8", errors="replace")
        )
        results = sorted(offline_dir.glob("offline-*-r*.json"))
        record["results"] = [p.name for p in results]
        record["gpu_memory_after_mib"] = self.wait_gpu_release()
        self.log(
            "offline-done",
            engine=engine["id"],
            exit=record["exit_code"],
            results=len(results),
            wall_s=record["wall_s"],
        )
        return record

    def run_engine(self, engine: dict[str, Any]) -> None:
        engine_dir = self.out / "engines" / engine["id"]
        runs_dir = engine_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        if self.remaining() < 300:
            self.summary["engines"].append(
                {"engine_id": engine["id"], "status": "skipped", "reason": "deadline before start"}
            )
            self.log("engine-skipped", engine=engine["id"], remaining=round(self.remaining()))
            return
        model_record = self.model_records.get(engine["model"], {})
        if model_record.get("verify_exit", 0) != 0:
            self.summary["engines"].append(
                {
                    "engine_id": engine["id"],
                    "status": "skipped",
                    "reason": "model verification failed",
                }
            )
            self.log("engine-skipped", engine=engine["id"], reason="model verification failed")
            return
        self.log("engine-start", engine=engine["id"], argv=engine["serve_argv"])
        record = self.start_server(engine, engine_dir)
        record["status"] = "ready" if record["ready"] else "failed-to-start"
        self.log(
            "engine-ready" if record["ready"] else "engine-failed",
            engine=engine["id"],
            ready_s=record["ready_s"],
            parse=record["log_parse"],
        )
        if record["ready"]:
            for index, raw in enumerate(self.config["warmup"]):
                warm = {
                    "cell_id": f"w{index}",
                    "shape": "random",
                    "concurrency": int(raw["concurrency"]),
                    "num_prompts": int(raw["num_prompts"]),
                    "input_len": int(raw["input_len"]),
                    "output_len": int(raw["output_len"]),
                }
                if warm["input_len"] + warm["output_len"] > engine["max_model_len"]:
                    continue
                self.summary["runs"].append(self.run_cell(engine, warm, 0, runs_dir, warmup=True))
                if self.stop.is_set():
                    break
            for repeat in range(1, self.plan["repeats"] + 1):
                for cell in engine["cells"]:
                    if self.stop.is_set():
                        break
                    if self.server is None or self.server.poll() is not None:
                        self.summary["runs"].append({
                            "engine_id": engine["id"], "cell_id": cell["cell_id"],
                            "repeat": repeat, "status": "skipped", "reason": "engine exited",
                        })  # fmt: skip
                        continue
                    self.summary["runs"].append(self.run_cell(engine, cell, repeat, runs_dir))
                    self.write_summary()
        if self.client is not None:
            self.stop_process(self.client, grace_s=5)
            self.client = None
        record["final_metrics"] = scrape_metrics()
        record["exit_code"] = self.stop_process(self.server)
        self.server = None
        record["stop_t"] = time.time()
        record["log_parse"] = parse_engine_log(
            (engine_dir / "engine.log").read_text(encoding="utf-8", errors="replace")
        )
        record["gpu_memory_after_mib"] = self.wait_gpu_release()
        self.write_json(engine_dir / "engine.json", record)
        self.summary["engines"].append(
            {k: v for k, v in record.items() if k not in ("final_metrics",)}
        )
        self.write_summary()
        if engine["offline"] and not self.stop.is_set():
            if not record["ready"]:
                self.summary["offline"].append(
                    {
                        "engine_id": engine["id"],
                        "status": "skipped",
                        "reason": "engine did not start",
                    }
                )
            elif self.remaining() < 240:
                self.summary["offline"].append(
                    {"engine_id": engine["id"], "status": "skipped", "reason": "deadline"}
                )
                self.log("offline-skipped", engine=engine["id"], remaining=round(self.remaining()))
            else:
                self.summary["offline"].append(self.run_offline(engine, engine_dir))
            self.write_summary()

    def run(self) -> int:
        for signum in (signal.SIGTERM, signal.SIGUSR1, signal.SIGINT):
            signal.signal(signum, self.handle_signal)
        self.write_json(self.out / "plan.json", self.plan)
        self.log(
            "job-start",
            job=self.plan["job"],
            deadline_in_s=round(self.remaining()),
            allocation_start_source=self.allocation_source,
        )
        sampler = NvmlSampler(
            self.out / "nvml.csv", float(self.config["sampling"]["nvml_interval_s"])
        )
        sampler.start()
        try:
            self.record_environment()
            self.verify_models()
            for engine in self.plan["engines"]:
                if self.stop.is_set():
                    self.summary["engines"].append(
                        {"engine_id": engine["id"], "status": "skipped", "reason": self.stop_reason}
                    )
                    continue
                self.run_engine(engine)
        finally:
            for process in (self.client, self.server, *self.children):
                self.stop_process(process, grace_s=20)
            sampler.stop_event.set()
            sampler.join(timeout=5)
            self.summary["nvml_error"] = sampler.error
            self.summary["stop_reason"] = self.stop_reason
            self.summary["finished_at"] = utc_now()
            self.write_summary()
            self.log("job-end", stop_reason=self.stop_reason)
        return 0


# --------------------------------------------------------------------------- client and offline


def client_main() -> int:
    """Long-lived benchmark client: one ``vllm bench serve`` run per stdin JSON line."""
    from vllm.benchmarks.serve import add_cli_args
    from vllm.benchmarks.serve import main as serve_main
    from vllm.utils.argparse_utils import FlexibleArgumentParser

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        parser = FlexibleArgumentParser()
        add_cli_args(parser)
        try:
            args = parser.parse_args(request["argv"])
            started = time.time()
            result = serve_main(args)
            payload = {
                "ok": True,
                "elapsed_s": round(time.time() - started, 3),
                "completed": result.get("completed") if isinstance(result, dict) else None,
            }
        except BaseException as exc:  # noqa: BLE001 - reported to the driver, client survives
            if isinstance(exc, KeyboardInterrupt):
                raise
            payload = {"ok": False, "error": repr(exc)[:2000]}
        sys.stdout.write(SENTINEL + json.dumps(payload) + "\n")
        sys.stdout.flush()
    return 0


def offline_main(spec_path: Path) -> int:
    """Offline throughput for one engine with vLLM's own ``bench throughput`` functions."""
    from vllm import LLM
    from vllm.benchmarks.throughput import (
        _run_vllm_requests,
        add_cli_args,
        get_requests,
        validate_args,
    )
    from vllm.engine.arg_utils import EngineArgs
    from vllm.outputs import RequestOutput
    from vllm.tokenizers import get_tokenizer
    from vllm.utils.argparse_utils import FlexibleArgumentParser

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    engine = spec["engine"]
    out = Path(spec["output_dir"])

    def parse(cell: dict[str, Any], seed: int) -> argparse.Namespace:
        parser = FlexibleArgumentParser()
        add_cli_args(parser)
        args = parser.parse_args(offline_argv(engine, cell, spec["seed"]))
        args.seed = seed
        validate_args(args)
        return args

    base = parse(engine["offline_cells"][0], spec["seed"])
    started = time.time()
    llm = LLM.from_engine_args(EngineArgs.from_cli_args(base))
    print(SENTINEL + json.dumps({"llm_ready_s": round(time.time() - started, 1)}), flush=True)
    tokenizer = get_tokenizer(engine["model_dir"])

    warm_cell = dict(engine["offline_cells"][0], num_prompts=spec["warmup_prompts"])
    warm_args = parse(warm_cell, spec["seed"] + 1000)
    _run_vllm_requests(llm, get_requests(warm_args, tokenizer), 1, True, False, False, False)

    for repeat in range(1, int(spec["repeats"]) + 1):
        for cell in engine["offline_cells"]:
            if time.time() > float(spec["deadline"]):
                print(
                    SENTINEL + json.dumps({"skipped": cell["cell_id"], "repeat": repeat}),
                    flush=True,
                )
                continue
            args = parse(cell, spec["seed"])
            requests = get_requests(args, tokenizer)
            llm.reset_prefix_cache()
            start_t = time.time()
            elapsed, outputs = _run_vllm_requests(llm, requests, 1, True, False, False, False)
            end_t = time.time()
            prompt_tokens = 0
            output_tokens = 0
            for item in outputs or []:
                if not isinstance(item, RequestOutput):
                    continue
                prompt_tokens += len(item.prompt_token_ids or [])
                output_tokens += sum(len(o.token_ids or []) for o in item.outputs if o is not None)
            result = {
                "engine_id": engine["id"], "model": engine["model"], "tp": engine["tp"],
                "cell_id": cell["cell_id"], "shape": cell["shape"], "repeat": repeat,
                "num_prompts": len(requests), "input_len": cell["input_len"],
                "output_len": cell["output_len"], "elapsed_s": elapsed,
                "start_t": start_t, "end_t": end_t,
                "total_prompt_tokens": prompt_tokens, "total_output_tokens": output_tokens,
                "requests_per_s": len(requests) / elapsed,
                "output_tokens_per_s": output_tokens / elapsed,
                "total_tokens_per_s": (prompt_tokens + output_tokens) / elapsed,
                "sampling": "vllm bench throughput default: temperature 1.0, top_p 1.0, ignore_eos",
                "tool": "vllm.benchmarks.throughput._run_vllm_requests (vLLM 0.31.0)",
            }  # fmt: skip
            (out / f"{cell['cell_id']}-r{repeat}.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(SENTINEL + json.dumps({"done": cell["cell_id"], "repeat": repeat,
                                         "output_tokens_per_s": result["output_tokens_per_s"]}),
                  flush=True)  # fmt: skip
    return 0


# --------------------------------------------------------------------------- CLI


def selftest_main(config_path: Path) -> int:
    """CPU-only check that vLLM's own parsers accept every argv this driver will run.

    Pins vLLM's CPU platform so parsing needs no GPU; no model is loaded and nothing runs on a
    device. Also checks the vLLM benchmark entry points and NVML calls the driver imports.
    """
    import vllm.platforms
    from vllm.platforms.cpu import CpuPlatform

    vllm.platforms._current_platform = CpuPlatform()  # parse-only; see docstring
    from vllm.benchmarks import serve as bench_serve
    from vllm.benchmarks import throughput as bench_throughput
    from vllm.entrypoints.launchers.cli_args import make_arg_parser, validate_parsed_serve_args
    from vllm.utils.argparse_utils import FlexibleArgumentParser

    config = load_config(config_path)
    report: dict[str, Any] = {"jobs": {}, "problems": []}
    problems: list[str] = report["problems"]
    for name in ("add_cli_args", "main"):
        if not hasattr(bench_serve, name):
            problems.append(f"vllm.benchmarks.serve.{name} missing")
    for name in ("add_cli_args", "get_requests", "validate_args", "_run_vllm_requests"):
        if not hasattr(bench_throughput, name):
            problems.append(f"vllm.benchmarks.throughput.{name} missing")
    try:
        import pynvml

        for name in ("nvmlDeviceGetTotalEnergyConsumption", "nvmlDeviceGetPowerUsage"):
            if not hasattr(pynvml, name):
                problems.append(f"pynvml.{name} missing")
    except ImportError as exc:
        problems.append(f"pynvml import failed: {exc!r}")
    for job in config["jobs"]:
        plan = resolve_plan(config, job)
        checked = 0
        for engine in plan["engines"]:
            parsed = make_arg_parser(FlexibleArgumentParser()).parse_args(engine["serve_argv"][2:])
            validate_parsed_serve_args(parsed)
            expect = {
                "tensor_parallel_size": engine["tp"],
                "enable_prefix_caching": engine["prefix_caching"],
                "kv_cache_dtype": engine["kv_cache_dtype"],
                "max_model_len": engine["max_model_len"],
                "gpu_memory_utilization": engine["gpu_memory_utilization"],
                "seed": plan["seed"],
            }
            for key, value in expect.items():
                if getattr(parsed, key, None) != value:
                    problems.append(
                        f"{engine['id']}: serve {key}={getattr(parsed, key, None)!r} != {value!r}"
                    )
            for cell in engine["cells"]:
                parser = FlexibleArgumentParser()
                bench_serve.add_cli_args(parser)
                args = parser.parse_args(
                    bench_serve_argv(
                        engine, cell, seed=plan["seed"], result_dir=Path("/tmp"),
                        result_filename="x.json", label="selftest",
                    )
                )  # fmt: skip
                want = {
                    "num_prompts": cell["num_prompts"],
                    "max_concurrency": cell["concurrency"],
                    "ready_check_timeout_sec": 0,
                    "ignore_eos": True,
                    "dataset_name": "prefix_repetition" if cell["shape"] == "prefix" else "random",
                }
                for key, value in want.items():
                    if getattr(args, key, None) != value:
                        problems.append(f"{engine['id']}/{cell['cell_id']}: bench {key} mismatch")
                checked += 1
            for cell in engine["offline_cells"]:
                parser = FlexibleArgumentParser()
                bench_throughput.add_cli_args(parser)
                args = parser.parse_args(offline_argv(engine, cell, plan["seed"]))
                bench_throughput.validate_args(args)
                if args.num_prompts != cell["num_prompts"] or args.dataset_name != "random":
                    problems.append(f"{engine['id']}/{cell['cell_id']}: offline argv mismatch")
                checked += 1
        report["jobs"][job] = {"engines": len(plan["engines"]), "argv_checked": checked}
    report["pass"] = not problems
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--job", required=True)
    plan.add_argument("--config", type=Path, default=CONFIG_PATH)
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--job", required=True)
    run.add_argument("--config", type=Path, default=CONFIG_PATH)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    sub.add_parser("client", allow_abbrev=False)
    offline = sub.add_parser("offline", allow_abbrev=False)
    offline.add_argument("--spec", type=Path, required=True)
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()

    if args.command == "plan":
        print(
            json.dumps(resolve_plan(load_config(args.config), args.job), indent=2, sort_keys=True)
        )
        return 0
    if args.command == "client":
        return client_main()
    if args.command == "offline":
        return offline_main(args.spec)
    if args.command == "selftest":
        return selftest_main(args.config)
    config = load_config(args.config)
    plan = resolve_plan(config, args.job)
    if plan["primary_model"] != os.environ.get("COTCODEC_MODEL_ID", plan["primary_model"]):
        raise SystemExit("the lane's model differs from this job's primary model")
    expected = os.environ.get("COTCODEC_EXPECTED_GPUS")
    if expected is not None and int(expected) != plan["gpus"]:
        raise SystemExit(f"the lane allocated {expected} GPUs; job {args.job} needs {plan['gpus']}")
    return Driver(plan, config, args.output_dir, args.allocation_minutes).run()


if __name__ == "__main__":
    sys.exit(main())
