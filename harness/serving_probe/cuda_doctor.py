"""Step-0 CUDA doctor for the serving probe (gates G0.2-G0.4), run in a child process.

It records which ``libcuda`` the process actually mapped (host R570 driver or the
image's CUDA forward-compatibility library), checks a bf16 GEMM against an fp32
reference, compiles and runs a Triton kernel from the exec-capable ``/outputs``
cache, and fails if any file under ``/tmp`` is mapped into the process. Torch and
Triton are imported only when :func:`run_cuda_doctor` runs, inside the container.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from harness.serving_probe.metrics import tmp_mapped_files


def _driver_version() -> dict[str, Any]:
    try:
        libcuda = ctypes.CDLL("libcuda.so.1")
    except OSError as exc:
        return {"loaded": False, "error": str(exc)}
    init_rc = int(libcuda.cuInit(0))
    version = ctypes.c_int(0)
    version_rc = int(libcuda.cuDriverGetVersion(ctypes.byref(version)))
    return {
        "loaded": True,
        "cu_init_rc": init_rc,
        "version_rc": version_rc,
        "version": version.value,
    }


def _mapped_libcuda() -> list[dict[str, str]]:
    try:
        text = Path("/proc/self/maps").read_text(encoding="utf-8")
    except OSError:
        return []
    paths = sorted(
        {line.split()[-1] for line in text.splitlines() if "libcuda.so" in line and "/" in line}
    )
    return [{"path": path, "realpath": os.path.realpath(path)} for path in paths]


def _ldconfig_libcuda() -> list[str]:
    try:
        completed = subprocess.run(
            ["ldconfig", "-p"], check=False, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"ldconfig unavailable: {exc}"]
    return [line.strip() for line in completed.stdout.splitlines() if "libcuda.so" in line]


def run_cuda_doctor(
    *,
    output: Path,
    matmul_size: int,
    max_error: float,
    seed: int,
    expected_gpus: int,
    expected_vllm_version: str,
    expected_vllm_commit: str,
    cache_root: Path,
) -> dict[str, Any]:
    import torch
    import triton
    import vllm

    from harness.serving_probe.triton_kernels import vector_add

    report: dict[str, Any] = {"driver": _driver_version()}
    report["vllm_version"] = vllm.__version__
    report["vllm_build_commit"] = os.environ.get("VLLM_BUILD_COMMIT")
    report["torch_version"] = torch.__version__
    report["torch_cuda"] = torch.version.cuda
    report["triton_version"] = triton.__version__
    available = torch.cuda.is_available()
    count = torch.cuda.device_count() if available else 0
    name = torch.cuda.get_device_name(0) if count else None
    report.update({"cuda_available": available, "device_count": count, "device_name": name})
    if count:
        torch.cuda.init()
        torch.zeros(1, device="cuda")
    report["libcuda_mapped"] = _mapped_libcuda()
    report["libcuda_ldconfig"] = _ldconfig_libcuda()
    report["compat_libcuda_active"] = any(
        "/compat/" in entry["realpath"] for entry in report["libcuda_mapped"]
    )
    g02 = (
        report["driver"].get("cu_init_rc") == 0
        and available
        and count == expected_gpus
        and name is not None
        and "H100" in name
        and report["vllm_version"] == expected_vllm_version
        and report["vllm_build_commit"] == expected_vllm_commit
    )
    report["G0.2"] = {"pass": bool(g02)}

    g03: dict[str, Any] = {"pass": False}
    if g02:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        generator = torch.Generator(device="cuda").manual_seed(seed)
        a = torch.randn(matmul_size, matmul_size, device="cuda", generator=generator).to(
            torch.bfloat16
        )
        b = torch.randn(matmul_size, matmul_size, device="cuda", generator=generator).to(
            torch.bfloat16
        )
        product = (a @ b).float()
        reference = a.float() @ b.float()
        torch.cuda.synchronize()
        error = float((product - reference).abs().max() / reference.abs().max())
        finite = bool(torch.isfinite(product).all())
        g03 = {
            "pass": finite and error < max_error,
            "normalized_max_error": error,
            "finite": finite,
        }
    report["G0.3"] = g03

    g04: dict[str, Any] = {"pass": False}
    if g02:
        triton_cache = Path(os.environ.get("TRITON_CACHE_DIR", ""))
        x = torch.arange(1 << 20, device="cuda", dtype=torch.float32)
        y = torch.full_like(x, 2.0)
        out = vector_add(x, y)
        torch.cuda.synchronize()
        correct = bool(torch.equal(out, x + y))
        cached = triton_cache.is_dir() and any(triton_cache.rglob("*"))
        under_outputs = str(triton_cache).startswith(str(cache_root))
        tmp_maps = tmp_mapped_files(os.getpid())
        g04 = {
            "pass": correct and cached and under_outputs and not tmp_maps,
            "correct": correct,
            "triton_cache_dir": str(triton_cache),
            "triton_cache_populated": cached,
            "triton_cache_under_outputs": under_outputs,
            "tmp_mapped_files": tmp_maps,
        }
    report["G0.4"] = g04
    report["pass"] = all(report[gate]["pass"] for gate in ("G0.2", "G0.3", "G0.4"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
