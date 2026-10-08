"""Minimal stand-in for KernelBench@423217d9 src/kernelbench/utils.py.

The upstream module imports dotenv, openai, litellm and tqdm at import time
for inference helpers that eval.py never calls during evaluation. Only the
helpers eval.py reaches are provided; their bodies are copied verbatim from
upstream (MIT, see ../LICENSE).
"""

import os

import torch


def get_gpu_vendor(device: torch.device | int | None = None) -> str:
    """Returns 'nvidia', 'amd', or 'unknown' for the given device."""
    if not torch.cuda.is_available():
        return "unknown"
    if device is None:
        device = torch.cuda.current_device()
    name = torch.cuda.get_device_name(device).upper()
    if "NVIDIA" in name:
        return "nvidia"
    if "AMD" in name or "MI3" in name:
        return "amd"
    return "unknown"


def read_file(file_path) -> str:
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist")
        return ""
    
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""
