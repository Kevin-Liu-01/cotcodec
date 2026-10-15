#!/usr/bin/env python3
"""Kimi-K2.6 fetch, runtime support (read only): SHA-256 of every source file the runtime-support
table cites, as copied out of the pinned vLLM image (docker create + docker cp; nothing in the
image runs) or checked out from each project's release tag (sparse, blobless clones).
Usage: kimi-runtime-sources.py <runtime-src dir> <output json>"""
import hashlib
import json
import pathlib
import subprocess
import sys

root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
V = "vllm-image-423783aa"
cited = {
    "vllm 0.31.0+cu129 in image sha256:423783aa (vllm/vllm-openai@sha256:b18abb2d)": (V, None, [
        "_version.py", "model_executor/models/registry.py", "model_executor/models/kimi_k25.py",
        "model_executor/models/kimi_k25_vit.py", "top/models/kimi_k3/__init__.py",
        "top/models/kimi_k3/nvidia/model.py", "top/models/kimi_k3/nvidia/kda.py",
        "transformers_utils/config.py", "tokenizers/registry.py"]),
    "vllm v0.31.0 tag (GitHub raw)": (".", None, [
        "vllm-v0.31.0-registry.py", "vllm-v0.31.0-supported_models.md"]),
    "sglang v0.5.21": ("sglang-v0.5.21", "python/sglang/srt/models", [
        "kimi_k25.py", "kimi_k3.py", "kimi_linear.py"]),
    "llama.cpp b11669": ("llama.cpp-src", "conversion", [
        "__init__.py", "base.py", "deepseek.py", "kimi_k3.py", "kimi_linear.py", "kimivl.py"]),
    "llama.cpp b11669 runtime (GitHub raw)": ("llama.cpp-b11669", None, [
        "convert_hf_to_gguf.py", "gguf-py_gguf_constants.py", "src_llama-arch.cpp",
        "tools_mtmd_clip.cpp"]),
    "ktransformers v0.7.2": ("ktransformers-src", None, [
        "doc/en/Kimi-K2.5.md", "doc/en/Kimi-K2-Thinking.md",
        "kt-kernel/python/cli/utils/model_registry.py", "kt-kernel/python/sft/config.py"]),
    "mlx-lm v0.32.0": ("mlx-lm-src", "mlx_lm/models", [
        "kimi_k25.py", "kimi_k3.py", "deepseek_v3.py"]),
    "mlx-vlm v0.7.8": ("mlx-vlm-src", "mlx_vlm/models", [
        "kimi_k25/kimi_k25.py", "kimi_k25/vision.py", "kimi_k3/kimi_k3.py", "kimi_k3/vision.py"]),
}
report = {}
for label, (base, sub, files) in cited.items():
    d = root / base / (sub or "")
    commit = None
    if (root / base / ".git").is_dir():
        commit = subprocess.run(["git", "-C", str(root / base), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
    report[label] = {"commit": commit, "files": {
        f: hashlib.sha256((d / f).read_bytes()).hexdigest() for f in files}}
out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
print(json.dumps({k: v["commit"] for k, v in report.items()}, indent=1))
