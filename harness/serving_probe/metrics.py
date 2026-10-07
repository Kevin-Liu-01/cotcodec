"""Metric parsing and samplers for the serving probe.

* Prometheus text from vLLM's ``/metrics`` is reduced to per-name sums so a
  point's counter deltas can be checked against the client's own totals (G0.7).
* ``nvidia-smi`` is sampled every 500 ms for device memory, utilisation, power
  and SM clock; the device-level memory reading is the contamination check,
  because ``nvidia-smi`` inside a PID-namespaced container cannot attribute
  other containers' processes.
* ``/proc/<pid>/stat`` gives API-server and client CPU per point.
* Engine log lines give KV-cache capacity, weight memory and startup phases.
"""

from __future__ import annotations

import csv
import math
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SAMPLE_RE = re.compile(
    r"^(?P<name>[A-Za-z_:][A-Za-z0-9_:]*)(?:\{(?P<labels>[^}]*)\})?\s+(?P<value>\S+)"
)


def parse_prometheus(text: str) -> dict[str, float]:
    """Sum every sample by metric name (labels dropped); comments ignored."""
    totals: dict[str, float] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        match = _SAMPLE_RE.match(line.strip())
        if not match:
            continue
        try:
            value = float(match.group("value"))
        except ValueError:
            continue
        if math.isnan(value):
            continue
        name = match.group("name")
        totals[name] = totals.get(name, 0.0) + value
    return totals


def counter(snapshot: Mapping[str, float], name: str) -> float | None:
    """Return a counter by base name, accepting the ``_total`` suffix."""
    for candidate in (name, f"{name}_total"):
        if candidate in snapshot:
            return snapshot[candidate]
    return None


def counter_delta(
    before: Mapping[str, float], after: Mapping[str, float], name: str
) -> float | None:
    start = counter(before, name)
    end = counter(after, name)
    if start is None or end is None:
        return None
    return end - start


#: Counters whose per-point deltas are recorded.
POINT_COUNTERS = (
    "vllm:prompt_tokens",
    "vllm:generation_tokens",
    "vllm:prefix_cache_queries",
    "vllm:prefix_cache_hits",
    "vllm:num_preemptions",
    "vllm:mm_cache_queries",
    "vllm:mm_cache_hits",
    "vllm:request_success",
    "vllm:prompt_tokens_cached",
)


def point_counter_deltas(before: Mapping[str, float], after: Mapping[str, float]) -> dict[str, Any]:
    deltas: dict[str, Any] = {name: counter_delta(before, after, name) for name in POINT_COUNTERS}
    queries = deltas.get("vllm:prefix_cache_queries")
    hits = deltas.get("vllm:prefix_cache_hits")
    deltas["prefix_cache_hit_rate"] = (hits / queries) if queries and hits is not None else None
    return deltas


def metrics_from_offline(snapshot: Iterable[Any]) -> dict[str, float]:
    """Flatten ``vllm.LLM.get_metrics()`` counters and gauges into a name->sum map."""
    totals: dict[str, float] = {}
    for metric in snapshot:
        value = getattr(metric, "value", None)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            name = str(metric.name)
            totals[name] = totals.get(name, 0.0) + float(value)
    return totals


def check_counters(
    deltas: Mapping[str, Any],
    *,
    client_prompt_tokens: int,
    client_output_tokens: int,
    prompt_tolerance: float,
    alternative_prompt_tokens: Sequence[int] = (),
) -> dict[str, Any]:
    """G0.7: generation-token delta equals the client total; prompt delta within tolerance."""
    generated = deltas.get("vllm:generation_tokens")
    prompt = deltas.get("vllm:prompt_tokens")
    generation_ok = generated is not None and int(round(generated)) == int(client_output_tokens)
    candidates = [client_prompt_tokens, *alternative_prompt_tokens]
    prompt_ok = False
    matched = None
    if prompt is not None:
        for candidate in candidates:
            if candidate > 0 and abs(prompt - candidate) <= prompt_tolerance * candidate:
                prompt_ok, matched = True, candidate
                break
            if candidate == 0 and prompt == 0:
                prompt_ok, matched = True, candidate
                break
    return {
        "pass": bool(generation_ok and prompt_ok),
        "generation_delta": generated,
        "client_output_tokens": client_output_tokens,
        "prompt_delta": prompt,
        "client_prompt_tokens": client_prompt_tokens,
        "prompt_matched": matched,
    }


@dataclass(frozen=True)
class GpuSample:
    t: float
    memory_used_mib: float
    utilization_pct: float
    power_w: float | None
    sm_clock_mhz: float | None


def parse_nvidia_smi_line(line: str, t: float) -> GpuSample | None:
    """Parse ``memory.used,utilization.gpu,power.draw,clocks.sm`` (noheader,nounits)."""
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 2:
        return None

    def number(text: str) -> float | None:
        try:
            value = float(text)
        except ValueError:
            return None
        return value if math.isfinite(value) else None

    memory = number(parts[0])
    utilization = number(parts[1])
    if memory is None or utilization is None:
        return None
    power = number(parts[2]) if len(parts) > 2 else None
    clock = number(parts[3]) if len(parts) > 3 else None
    return GpuSample(t, memory, utilization, power, clock)


NVIDIA_SMI_QUERY = "memory.used,utilization.gpu,power.draw,clocks.sm"


def query_gpu_once(runner: Callable[..., Any] = subprocess.run) -> GpuSample | None:
    completed = runner(
        ["nvidia-smi", f"--query-gpu={NVIDIA_SMI_QUERY}", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError(f"expected exactly one visible GPU, nvidia-smi listed {len(lines)}")
    return parse_nvidia_smi_line(lines[0], time.perf_counter())


def summarize_gpu(samples: Sequence[GpuSample]) -> dict[str, Any]:
    if not samples:
        return {"samples": 0}

    def mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    return {
        "samples": len(samples),
        "peak_memory_used_mib": max(sample.memory_used_mib for sample in samples),
        "mean_utilization_pct": mean([sample.utilization_pct for sample in samples]),
        "mean_power_w": mean([s.power_w for s in samples if s.power_w is not None]),
        "mean_sm_clock_mhz": mean([s.sm_clock_mhz for s in samples if s.sm_clock_mhz is not None]),
        "min_sm_clock_mhz": min(
            (s.sm_clock_mhz for s in samples if s.sm_clock_mhz is not None), default=None
        ),
    }


def baseline_verdict(
    samples: Sequence[GpuSample], *, max_memory_mib: float, max_utilization_pct: float
) -> dict[str, Any]:
    """G0.8: the device is idle before the engine starts."""
    passed = bool(samples) and all(
        sample.memory_used_mib < max_memory_mib and sample.utilization_pct <= max_utilization_pct
        for sample in samples
    )
    return {
        "pass": passed,
        "samples": len(samples),
        "max_memory_used_mib": max((s.memory_used_mib for s in samples), default=None),
        "max_utilization_pct": max((s.utilization_pct for s in samples), default=None),
    }


class GpuSampler:
    """Background ``nvidia-smi -lms`` reader that keeps samples and a CSV trace."""

    def __init__(
        self, csv_path: Path, interval_ms: int, popen: Callable[..., Any] = subprocess.Popen
    ):
        self.csv_path = csv_path
        self.interval_ms = interval_ms
        self._popen = popen
        self._samples: list[GpuSample] = []
        self._lock = threading.Lock()
        self._process: Any = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._process = self._popen(
            [
                "nvidia-smi",
                f"--query-gpu={NVIDIA_SMI_QUERY}",
                "--format=csv,noheader,nounits",
                f"-lms={self.interval_ms}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self._thread = threading.Thread(target=self._read, name="gpu-sampler", daemon=True)
        self._thread.start()

    def _read(self) -> None:
        with self.csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            for line in self._process.stdout:
                sample = parse_nvidia_smi_line(line, time.perf_counter())
                if sample is None:
                    continue
                with self._lock:
                    self._samples.append(sample)
                writer.writerow(
                    [
                        f"{sample.t:.3f}",
                        sample.memory_used_mib,
                        sample.utilization_pct,
                        sample.power_w,
                        sample.sm_clock_mhz,
                    ]
                )
                handle.flush()

    def window(self, start: float, end: float) -> list[GpuSample]:
        with self._lock:
            return [sample for sample in self._samples if start <= sample.t <= end]

    def stop(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
        if self._thread is not None:
            self._thread.join(timeout=5)


def read_cpu_ticks(pid: int, proc_root: Path = Path("/proc")) -> int | None:
    """utime + stime of ``pid`` in clock ticks, or None if it is gone."""
    try:
        text = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    fields = text[text.rfind(")") + 2 :].split()
    return int(fields[11]) + int(fields[12])


def cpu_percent(ticks_start: int | None, ticks_end: int | None, wall_s: float) -> float | None:
    """CPU of one process over a window; 100 means one core fully busy."""
    if ticks_start is None or ticks_end is None or wall_s <= 0:
        return None
    hertz = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
    return 100.0 * (ticks_end - ticks_start) / hertz / wall_s


def process_tree(root_pid: int, proc_root: Path = Path("/proc")) -> list[int]:
    """``root_pid`` and all descendants, from ``/proc/*/stat`` parent links."""
    parents: dict[int, int] = {}
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            text = (entry / "stat").read_text(encoding="utf-8")
        except OSError:
            continue
        fields = text[text.rfind(")") + 2 :].split()
        parents[int(entry.name)] = int(fields[1])
    tree = [root_pid]
    frontier = [root_pid]
    while frontier:
        current = frontier.pop()
        children = [pid for pid, parent in parents.items() if parent == current]
        tree.extend(children)
        frontier.extend(children)
    return tree


def tmp_mapped_files(pid: int, proc_root: Path = Path("/proc")) -> list[str]:
    """Files under /tmp mapped into ``pid`` (JIT artefacts escaping the /outputs caches)."""
    try:
        text = (proc_root / str(pid) / "maps").read_text(encoding="utf-8")
    except OSError:
        return []
    paths = set()
    for line in text.splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) == 6 and parts[5].startswith("/tmp/"):
            paths.add(parts[5].replace(" (deleted)", ""))
    return sorted(paths)


def orphan_zombies(my_pid: int, tracked: set[int], proc_root: Path = Path("/proc")) -> list[int]:
    """Zombie children of ``my_pid`` that no Popen object owns (PID-1 reaping)."""
    zombies: list[int] = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in tracked:
            continue
        try:
            text = (entry / "stat").read_text(encoding="utf-8")
        except OSError:
            continue
        fields = text[text.rfind(")") + 2 :].split()
        if fields[0] == "Z" and int(fields[1]) == my_pid:
            zombies.append(pid)
    return zombies


_LOG_PATTERNS: dict[str, re.Pattern[str]] = {
    "kv_cache_tokens": re.compile(r"GPU KV cache size:\s*([\d,]+)\s*tokens"),
    "max_concurrency": re.compile(
        r"Maximum concurrency for\s*([\d,]+)\s*tokens per request:\s*([\d.]+)x"
    ),
    "weights_gib": re.compile(r"Model loading took\s*([\d.]+)\s*GiB"),
    "kv_cache_gib": re.compile(r"Available KV cache memory:\s*([\d.]+)\s*GiB"),
    "compile_s": re.compile(r"torch\.compile takes\s*([\d.]+)\s*s in total"),
    "graph_capture_s": re.compile(r"Graph capturing finished in\s*([\d.]+)\s*sec"),
    "init_engine_s": re.compile(r"init engine .*? took\s*([\d.]+)\s*seconds"),
}


def parse_engine_log(text: str) -> dict[str, Any]:
    """Extract startup facts from a vLLM log; raw lines are kept for audit."""
    facts: dict[str, Any] = {}
    for key, pattern in _LOG_PATTERNS.items():
        matches = list(pattern.finditer(text))
        match = matches[-1] if matches else None
        if match is None:
            facts[key] = None
            continue
        values = [group.replace(",", "") for group in match.groups()]
        numbers = [float(value) for value in values]
        facts[key] = numbers[0] if len(numbers) == 1 else numbers
    config_lines = [line for line in text.splitlines() if "compilation_config" in line]
    facts["compilation_config_line"] = config_lines[-1][-2000:] if config_lines else None
    facts["enforce_eager"] = "enforce_eager=True" in text
    return facts
