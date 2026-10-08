"""Minimal stand-in for KernelBench@44130946 src/utils.py.

The upstream module imports dotenv, openai, litellm, transformers and tqdm at
import time for inference helpers that src/eval.py never calls during
evaluation. Only the helpers eval.py reaches are provided; their bodies are
copied verbatim from upstream (MIT, see ../LICENSE).
"""

import os


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
