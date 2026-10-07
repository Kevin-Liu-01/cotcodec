from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from harness.serving_probe.metrics import (
    GpuSample,
    baseline_verdict,
    check_counters,
    counter,
    counter_delta,
    metrics_from_offline,
    orphan_zombies,
    parse_engine_log,
    parse_nvidia_smi_line,
    parse_prometheus,
    point_counter_deltas,
    process_tree,
    read_cpu_ticks,
    summarize_gpu,
    tmp_mapped_files,
)

PROM = """# HELP vllm:prompt_tokens_total Number of prefill tokens processed.
# TYPE vllm:prompt_tokens_total counter
vllm:prompt_tokens_total{engine="0",model_name="m"} 100.0
vllm:prompt_tokens_total{engine="1",model_name="m"} 20.0
vllm:generation_tokens_total{engine="0",model_name="m"} 50.0
vllm:prefix_cache_queries_total{engine="0"} 10.0
vllm:prefix_cache_hits_total{engine="0"} 4.0
vllm:kv_cache_usage_perc{engine="0"} 0.25
vllm:e2e_request_latency_seconds_bucket{le="+Inf"} 3.0
vllm:weird NaN
"""


def test_prometheus_sums_labels_and_accepts_total_suffix() -> None:
    snapshot = parse_prometheus(PROM)
    assert snapshot["vllm:prompt_tokens_total"] == 120.0
    assert counter(snapshot, "vllm:prompt_tokens") == 120.0
    assert counter(snapshot, "vllm:kv_cache_usage_perc") == 0.25
    assert counter(snapshot, "vllm:missing") is None
    assert "vllm:weird" not in snapshot
    later = parse_prometheus(PROM.replace("50.0", "80.0"))
    assert counter_delta(snapshot, later, "vllm:generation_tokens") == 30.0
    deltas = point_counter_deltas(snapshot, later)
    assert deltas["vllm:prefix_cache_queries"] == 0.0
    assert deltas["prefix_cache_hit_rate"] is None


def test_counter_check_is_exact_for_generation_and_tolerant_for_prompts() -> None:
    deltas = {"vllm:generation_tokens": 300.0, "vllm:prompt_tokens": 1005.0}
    ok = check_counters(
        deltas, client_prompt_tokens=1000, client_output_tokens=300, prompt_tolerance=0.01
    )
    assert ok["pass"] and ok["prompt_matched"] == 1000
    off_by_one = check_counters(
        deltas, client_prompt_tokens=1000, client_output_tokens=299, prompt_tolerance=0.01
    )
    assert not off_by_one["pass"]
    prompt_far = check_counters(
        deltas, client_prompt_tokens=900, client_output_tokens=300, prompt_tolerance=0.01
    )
    assert not prompt_far["pass"]
    fan_out = check_counters(
        {"vllm:generation_tokens": 10.0, "vllm:prompt_tokens": 800.0},
        client_prompt_tokens=100,
        client_output_tokens=10,
        prompt_tolerance=0.01,
        alternative_prompt_tokens=[800],
    )
    assert fan_out["pass"] and fan_out["prompt_matched"] == 800
    assert not check_counters(
        {}, client_prompt_tokens=1, client_output_tokens=1, prompt_tolerance=0.01
    )["pass"]


def test_offline_metric_snapshot_is_flattened() -> None:
    snapshot = [
        SimpleNamespace(name="vllm:generation_tokens", value=10),
        SimpleNamespace(name="vllm:generation_tokens", value=5),
        SimpleNamespace(name="vllm:e2e", buckets={}),
    ]
    assert metrics_from_offline(snapshot) == {"vllm:generation_tokens": 15.0}


def test_nvidia_smi_parsing_and_gpu_summaries() -> None:
    sample = parse_nvidia_smi_line("73000, 97, 650.5, 1980\n", 1.0)
    assert sample == GpuSample(1.0, 73000.0, 97.0, 650.5, 1980.0)
    assert parse_nvidia_smi_line("[N/A], 0", 1.0) is None
    partial = parse_nvidia_smi_line("10, 0, [N/A], [N/A]", 2.0)
    assert partial.power_w is None and partial.sm_clock_mhz is None
    summary = summarize_gpu([sample, GpuSample(2.0, 74000.0, 99.0, 660.5, 1900.0)])
    assert summary["peak_memory_used_mib"] == 74000.0
    assert summary["mean_utilization_pct"] == 98.0
    assert summary["min_sm_clock_mhz"] == 1900.0
    assert summarize_gpu([]) == {"samples": 0}


def test_baseline_requires_an_idle_device_for_every_sample() -> None:
    idle = [GpuSample(t, 0.0, 0.0, 70.0, 345.0) for t in range(20)]
    assert baseline_verdict(idle, max_memory_mib=1024, max_utilization_pct=0)["pass"]
    busy = idle + [GpuSample(21.0, 0.0, 3.0, 70.0, 345.0)]
    assert not baseline_verdict(busy, max_memory_mib=1024, max_utilization_pct=0)["pass"]
    foreign = idle + [GpuSample(21.0, 2048.0, 0.0, 70.0, 345.0)]
    assert not baseline_verdict(foreign, max_memory_mib=1024, max_utilization_pct=0)["pass"]
    assert not baseline_verdict([], max_memory_mib=1024, max_utilization_pct=0)["pass"]


def _proc(
    root: Path,
    pid: int,
    *,
    ppid: int,
    state: str = "S",
    utime: int = 0,
    stime: int = 0,
    maps: str = "",
) -> None:
    directory = root / str(pid)
    directory.mkdir(parents=True)
    fields = [state, str(ppid)] + ["0"] * 9 + [str(utime), str(stime)] + ["0"] * 10
    (directory / "stat").write_text(f"{pid} (python (x)) {' '.join(fields)}\n")
    (directory / "maps").write_text(maps)


def test_proc_helpers(tmp_path: Path) -> None:
    maps = (
        "7f0-7f1 r-xp 00000000 00:2e 12 /tmp/torchinductor_x/abc.so\n"
        "7f2-7f3 r-xp 00000000 00:2e 13 /outputs/probe/cache/triton/k.so\n"
        "7f4-7f5 rw-s 00000000 00:05 14 /tmp/shm (deleted)\n"
        "7f6-7f7 rw-p 00000000 00:00 0 \n"
    )
    _proc(tmp_path, 10, ppid=1, utime=150, stime=50, maps=maps)
    _proc(tmp_path, 11, ppid=10)
    _proc(tmp_path, 12, ppid=11)
    _proc(tmp_path, 13, ppid=1, state="Z")
    _proc(tmp_path, 14, ppid=1, state="Z")
    _proc(tmp_path, 15, ppid=10, state="Z")
    (tmp_path / "self").mkdir()
    assert read_cpu_ticks(10, tmp_path) == 200
    assert read_cpu_ticks(99, tmp_path) is None
    assert tmp_mapped_files(10, tmp_path) == ["/tmp/shm", "/tmp/torchinductor_x/abc.so"]
    assert sorted(process_tree(10, tmp_path)) == [10, 11, 12, 15]
    assert orphan_zombies(1, {14}, tmp_path) == [13]


def test_engine_log_facts() -> None:
    log = "\n".join(
        [
            "INFO Model loading took 17.67 GiB memory and 12.3 seconds",
            "INFO Available KV cache memory: 44.10 GiB",
            "INFO GPU KV cache size: 1,234,560 tokens",
            "INFO Maximum concurrency for 65,536 tokens per request: 18.84x",
            "INFO torch.compile takes 45.6 s in total",
            "INFO Graph capturing finished in 21 secs, took 0.62 GiB",
            "INFO Initializing a V1 LLM engine with config: compilation_config={'level': 3}",
        ]
    )
    facts = parse_engine_log(log)
    assert facts["weights_gib"] == 17.67
    assert facts["kv_cache_gib"] == 44.10
    assert facts["kv_cache_tokens"] == 1234560
    assert facts["max_concurrency"] == [65536.0, 18.84]
    assert facts["compile_s"] == 45.6
    assert facts["graph_capture_s"] == 21.0
    assert "level" in facts["compilation_config_line"]
    assert facts["enforce_eager"] is False
    assert parse_engine_log("")["kv_cache_tokens"] is None
