"""Timing harness: randomized paired order, warm-up, L2 flush, CUDA events.

Protocol (preregistered; plan section 9):

- warm-up: ``warmup`` calls of each side before timing (triggers JIT and
  autotuning, which are excluded from timing);
- ``rounds + 1`` rounds; the first round is discarded; in each round the
  order of {reference, candidate} is shuffled with ``random.Random(seed)``;
- before every timed call the L2 cache is flushed by writing a 256 MiB
  buffer (as KernelBench ``clear_l2_cache``), then the device is synchronized;
- each call is bracketed by CUDA events (``time.perf_counter`` on CPU, for
  the doctor only);
- per round the speedup is ``t_ref / t_cand``; the estimate is the median of
  per-round ratios with a percentile bootstrap CI (B = 10,000, seed 0);
- clocks, throttle reasons, temperature and power are sampled per round when
  ``nvidia-smi`` is available; rounds with an active throttle reason other
  than idle are dropped and counted;
- baselines: the reference is timed with TF32 enabled
  (``set_float32_matmul_precision("high")`` and cuDNN TF32) and with strict
  fp32, and both speedups are reported;
- timing runs only on the dedicated timing GPUs (runner configuration), and
  the uncontended evidence (lane prolog attestation, in-container
  ``nvidia-smi`` view) is recorded with every result.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import statistics
import subprocess
import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from typing import Any

import torch

from harness.q1.gates.common import report_phase, synchronize

L2_FLUSH_BYTES = 256 * 1024 * 1024
UNCONTENDED_ENV = "Q1_UNCONTENDED_ATTESTATION"
#: The lane's GPU prolog result (``docker-research.sbatch`` writes it to the run dir).
PROLOG_ENV_PATH = os.environ.get("Q1_GPU_PROLOG_ENV", "/outputs/gpu-prolog.env")
#: nvidia-smi throttle reasons that do not invalidate a round (bit masks).
BENIGN_THROTTLE = {0x0, 0x1}  # none, GPU idle


def flush_l2(device: torch.device, buffer: torch.Tensor | None = None) -> torch.Tensor | None:
    if device.type != "cuda":
        return None
    if buffer is None:
        buffer = torch.empty(L2_FLUSH_BYTES // 8, dtype=torch.int64, device=device)
    buffer.fill_(42)
    return buffer


class _Clock:
    def __init__(self, device: torch.device) -> None:
        self.device = device

    def time_call(self, fn: Callable[[], Any]) -> float:
        if self.device.type == "cuda":
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record()
            fn()
            end.record()
            torch.cuda.synchronize(self.device)
            return float(start.elapsed_time(end))
        begin = time.perf_counter()
        fn()
        return (time.perf_counter() - begin) * 1000.0


def gpu_sample(index: int | None) -> dict[str, Any] | None:
    """One nvidia-smi sample (clocks, throttle reasons, temperature, power)."""
    if index is None or shutil.which("nvidia-smi") is None:
        return None
    query = "clocks.sm,clocks.mem,clocks_throttle_reasons.active,temperature.gpu,power.draw"
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={query}",
                "--format=csv,noheader,nounits",
                "-i",
                str(index),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    fields = [f.strip() for f in out.split(",")]
    if len(fields) != 5:
        return None
    try:
        throttle = int(fields[2], 16)
    except ValueError:
        throttle = -1
    return {
        "sm_mhz": fields[0],
        "mem_mhz": fields[1],
        "throttle": throttle,
        "temp_c": fields[3],
        "power_w": fields[4],
    }


def _read_env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            key, sep, value = line.strip().partition("=")
            if sep:
                values[key] = value
    return values


def uncontended_evidence() -> dict[str, Any]:
    """Lane GPU-prolog result, any extra attestation, and the in-container view.

    The prolog checks foreign compute processes once, before the container
    starts; it is evidence for that moment, not isolation.
    """
    evidence: dict[str, Any] = {"prolog_env_path": PROLOG_ENV_PATH}
    if os.path.isfile(PROLOG_ENV_PATH):
        try:
            evidence["prolog"] = _read_env_file(PROLOG_ENV_PATH)
        except OSError as exc:
            evidence["prolog_error"] = str(exc)
    path = os.environ.get(UNCONTENDED_ENV)
    if path and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as handle:
                evidence["attestation"] = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            evidence["attestation_error"] = str(exc)
    if shutil.which("nvidia-smi"):
        try:
            evidence["compute_apps_visible"] = (
                subprocess.run(
                    ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                .stdout.strip()
                .splitlines()
            )
        except (OSError, subprocess.SubprocessError) as exc:
            evidence["compute_apps_error"] = str(exc)
    prolog = evidence.get("prolog", {})
    if prolog:
        evidence["uncontended"] = (
            prolog.get("foreign_compute_processes") == "0" and prolog.get("decision") == "exclusive"
        )
    else:
        evidence["uncontended"] = None
    return evidence


def bootstrap_median_ci(
    values: Sequence[float], *, resamples: int = 10_000, seed: int = 0, level: float = 0.95
) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(values)
    medians = sorted(
        statistics.median(values[rng.randrange(n)] for _ in range(n)) for _ in range(resamples)
    )
    lo = medians[int((1 - level) / 2 * resamples)]
    hi = medians[min(resamples - 1, int((1 + level) / 2 * resamples))]
    return lo, hi


def paired_timing(
    reference: Callable[[], Any],
    candidate: Callable[[], Any],
    *,
    device: torch.device,
    rounds: int = 30,
    warmup: int = 10,
    seed: int = 0,
    gpu_index: int | None = None,
    resamples: int = 10_000,
) -> dict[str, Any]:
    """Randomized paired timing of two zero-argument callables."""
    report_phase("timing")
    with torch.no_grad():
        for _ in range(warmup):
            reference()
            candidate()
        synchronize(device)
        rng = random.Random(seed)
        clock = _Clock(device)
        buffer = None
        kept: list[dict[str, Any]] = []
        dropped = 0
        for round_index in range(rounds + 1):
            order = [("reference", reference), ("candidate", candidate)]
            rng.shuffle(order)
            sample = gpu_sample(gpu_index)
            times: dict[str, float] = {}
            for name, fn in order:
                buffer = flush_l2(device, buffer)
                synchronize(device)
                times[name] = clock.time_call(fn)
            if round_index == 0:
                continue
            if sample is not None and sample["throttle"] not in BENIGN_THROTTLE:
                dropped += 1
                continue
            kept.append({"order": [n for n, _ in order], **times, "gpu": sample})
    ratios = [r["reference"] / r["candidate"] for r in kept if r["candidate"] > 0]
    ref_times = [r["reference"] for r in kept]
    cand_times = [r["candidate"] for r in kept]

    def cv(xs: Sequence[float]) -> float | None:
        if len(xs) < 2 or not statistics.mean(xs):
            return None
        return statistics.pstdev(xs) / statistics.mean(xs)

    result: dict[str, Any] = {
        "rounds_requested": rounds,
        "rounds_kept": len(kept),
        "rounds_dropped_throttle": dropped,
        "median_speedup": statistics.median(ratios) if ratios else None,
        "speedup_ci95": (
            list(bootstrap_median_ci(ratios, resamples=resamples)) if len(ratios) > 1 else None
        ),
        "reference_ms_median": statistics.median(ref_times) if ref_times else None,
        "candidate_ms_median": statistics.median(cand_times) if cand_times else None,
        "reference_cv": cv(ref_times),
        "candidate_cv": cv(cand_times),
        "device": str(device),
        "clock": "cuda-events" if device.type == "cuda" else "perf_counter",
    }
    return result


@contextmanager
def tf32_baseline(enabled: bool):  # noqa: ANN201
    old = (
        torch.get_float32_matmul_precision(),
        torch.backends.cudnn.allow_tf32,
    )
    torch.set_float32_matmul_precision("high" if enabled else "highest")
    torch.backends.cudnn.allow_tf32 = enabled
    try:
        yield
    finally:
        torch.set_float32_matmul_precision(old[0])
        torch.backends.cudnn.allow_tf32 = old[1]


def time_against_baselines(
    reference_model: torch.nn.Module,
    candidate_model: torch.nn.Module,
    inputs: Sequence[Any],
    *,
    device: torch.device,
    rounds: int = 30,
    warmup: int = 10,
    seed: int = 0,
    gpu_index: int | None = None,
    resamples: int = 10_000,
) -> dict[str, Any]:
    """Speedup of the candidate over the TF32 and the strict-fp32 reference."""
    out: dict[str, Any] = {"uncontended": uncontended_evidence()}
    for label, enabled in (("tf32", True), ("strict_fp32", False)):
        # The flags are process-wide for the whole paired run, so both sides
        # see the same environment and no flag toggling falls inside a timed call.
        with tf32_baseline(enabled):
            out[label] = paired_timing(
                lambda: reference_model(*inputs),
                lambda: candidate_model(*inputs),
                device=device,
                rounds=rounds,
                warmup=warmup,
                seed=seed,
                gpu_index=gpu_index,
                resamples=resamples,
            )
    return out
