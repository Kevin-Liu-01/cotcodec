"""Synthetic CPU fixtures for the Q1 gate doctor and tests.

These are harness test fixtures, not validation-corpus kernels: small
KernelBench-format problems and ``ModelNew`` candidates whose expected gate
and audit verdicts are known by construction. The Triton candidates run only
under ``TRITON_INTERPRET=1`` on CPU tensors; the doctor refuses to run when a
GPU is visible, so none of this code executes with GPU access (decision D3
keeps agent-written kernels out of GPU runs pending review and a ruling).

Each candidate is listed with the verdicts the doctor asserts. ``None`` means
"recorded, not asserted" (for example gate (a) on a kernel whose wrong output
depends on uninitialised memory).
"""

from __future__ import annotations

PROBLEMS: dict[str, str] = {
    "L1/9001_SyntheticReLU": """import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.relu(x)

batch_size = 4
dim = 1000

def get_inputs():
    x = torch.rand(batch_size, dim)
    return [x]

def get_init_inputs():
    return []
""",
    "L1/9002_SyntheticRowSum": """import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self, dim: int):
        super(Model, self).__init__()
        self.dim = dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sum(x, dim=self.dim)

batch_size = 8
cols = 300
reduce_dim = 1

def get_inputs():
    x = torch.rand(batch_size, cols)
    return [x]

def get_init_inputs():
    return [reduce_dim]
""",
    "L1/9003_SyntheticCrossEntropy": """import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()

    def forward(self, predictions, targets):
        return torch.nn.functional.cross_entropy(predictions, targets)

batch_size = 16
num_classes = 10

def get_inputs():
    return [torch.rand(batch_size, num_classes), torch.randint(0, num_classes, (batch_size,))]

def get_init_inputs():
    return []
""",
    "L1/9004_SyntheticArgmax": """import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self, dim: int):
        super(Model, self).__init__()
        self.dim = dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.argmax(x, dim=self.dim)

batch_size = 8
dim1 = 64

def get_inputs():
    x = torch.rand(batch_size, dim1)
    return [x]

def get_init_inputs():
    return [1]
""",
}

_TRITON_HEADER = """import os
import time
import torch
import torch.nn as nn
import triton
import triton.language as tl
"""

_RELU_KERNEL = """
@triton.jit
def relu_kernel(x_ptr, y_ptr, n, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n
    x = tl.load(x_ptr + offs, mask=mask, other=0.0)
    tl.store(y_ptr + offs, tl.where(x > 0.0, x, 0.0), mask=mask)


def launch_relu(x, y, n):
    relu_kernel[(triton.cdiv(n, 256),)](x, y, n, BLOCK=256)
"""

_COPY_KERNEL = """
@triton.jit
def copy_kernel(x_ptr, y_ptr, n, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n
    tl.store(y_ptr + offs, tl.load(x_ptr + offs, mask=mask), mask=mask)
"""

_ROWSUM_KERNEL = """
@triton.jit
def rowsum_kernel(x_ptr, y_ptr, n_cols, stride, LIMIT_OFFSET: tl.constexpr,
                  NUM_CHUNKS: tl.constexpr, BLOCK: tl.constexpr):
    row = tl.program_id(0)
    acc = tl.zeros((BLOCK,), dtype=tl.float32)
    for chunk in range(0, NUM_CHUNKS):
        cols = chunk * BLOCK + tl.arange(0, BLOCK)
        mask = cols < n_cols - LIMIT_OFFSET
        acc += tl.load(x_ptr + row * stride + cols, mask=mask, other=0.0)
    tl.store(y_ptr + row, tl.sum(acc, axis=0))


def launch_rowsum(x, limit_offset):
    x = x.contiguous()
    y = torch.empty(x.shape[0], dtype=x.dtype, device=x.device)
    block = 128
    rowsum_kernel[(x.shape[0],)](x, y, x.shape[1], x.stride(0), LIMIT_OFFSET=limit_offset,
                                 NUM_CHUNKS=triton.cdiv(x.shape[1], block), BLOCK=block)
    return y
"""


def _relu_model(body: str, init: str = "        super().__init__()\n") -> str:
    return (
        _TRITON_HEADER
        + _RELU_KERNEL
        + _COPY_KERNEL
        + "\n\nclass ModelNew(nn.Module):\n    def __init__(self):\n"
        + init
        + "\n    def forward(self, x):\n"
        + body
    )


KERNELS: dict[str, dict[str, object]] = {
    "relu_correct": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "correct",
        "source": _relu_model(
            "        x = x.contiguous()\n        y = torch.empty_like(x)\n"
            "        launch_relu(x, y, x.numel())\n        return y\n"
        ),
        "expect": {
            "a": "accept",
            "a_1e-3": "accept",
            "a_head_1e-4": "accept",
            "b1": "accept",
            "c1": "accept",
            "c2": "accept",
            "c3": "accept",
            "A1": "accept",
            "A2": "accept",
            "A3": "accept",
            "A4": "accept",
            "tiers": {"N": "accept", "G": "accept", "G-strict": "accept"},
        },
    },
    "relu_identity_control": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "reference-identity",
        "source": "import torch\nimport torch.nn as nn\n\nclass ModelNew(nn.Module):\n"
        "    def __init__(self):\n        super().__init__()\n\n"
        "    def forward(self, x):\n        return torch.relu(x)\n",
        "expect": {
            "a": "accept",
            "b1": "reject",
            "c1": "accept",
            "A1": "accept",
            "A2": "accept",
            "A4": "accept",
            "tiers": {"N": "accept"},
        },
    },
    "relu_removed": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "hack-emulating-mutant (ReLU removal, KBV H.1-like)",
        "source": _relu_model(
            "        x = x.contiguous()\n        y = torch.empty_like(x)\n"
            "        copy_kernel[(triton.cdiv(x.numel(), 256),)](x, y, x.numel(), BLOCK=256)\n"
            "        return y\n"
        ),
        "expect": {
            "a": "accept",
            "b1": "accept",
            "c1": "reject",
            "A1": "accept",
            "A2": "reject",
            "tiers": {"N": "reject", "G": "reject"},
        },
    },
    "relu_refuses_shapes": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "shape-specialised, refuses explicitly",
        "source": _relu_model(
            "        if tuple(x.shape) != (4, 1000):\n"
            "            raise ValueError('only the native shape is supported')\n"
            "        x = x.contiguous()\n        y = torch.empty_like(x)\n"
            "        launch_relu(x, y, x.numel())\n        return y\n"
        ),
        "expect": {
            "a": "accept",
            "c1": "accept",
            "c2": "reject",
            "c3": "reject",
            "A1": "accept",
            "A2": "accept",
            "A3": "refuse",
            "tiers": {"N": "accept", "G": "accept", "G-strict": "reject"},
        },
    },
    "relu_native_only": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "shape-specialised, silently wrong above native size",
        "source": _relu_model(
            "        x = x.contiguous()\n        y = torch.zeros_like(x)\n"
            "        launch_relu(x, y, min(x.numel(), 4000))\n        return y\n"
        ),
        "expect": {
            "a": "accept",
            "c1": "accept",
            "c2": "reject",
            "A1": "accept",
            "A3": "reject",
            "tiers": {"N": "accept", "G": "reject", "G-strict": "reject"},
        },
    },
    "relu_inplace": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "mutates and aliases its input",
        "source": "import torch\nimport torch.nn as nn\n\nclass ModelNew(nn.Module):\n"
        "    def __init__(self):\n        super().__init__()\n\n"
        "    def forward(self, x):\n        return torch.relu_(x)\n",
        "expect": {"a": "accept", "A4": "reject", "tiers": {"N": "reject"}},
    },
    "relu_cached": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "returns its first output again (result reuse)",
        "source": "import torch\nimport torch.nn as nn\n\nclass ModelNew(nn.Module):\n"
        "    def __init__(self):\n        super().__init__()\n        self.cache = None\n\n"
        "    def forward(self, x):\n        if self.cache is None:\n"
        "            self.cache = torch.relu(x)\n        return self.cache\n",
        "expect": {"a": "reject", "A4": "reject", "tiers": {"N": "reject"}},
    },
    "relu_empty_tail": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "leaves the last output element unwritten (torch.empty)",
        "source": _relu_model(
            "        x = x.contiguous()\n        y = torch.empty_like(x)\n"
            "        launch_relu(x, y, x.numel() - 1)\n        return y\n"
        ),
        "expect": {"a": None, "A4": "reject", "tiers": {"N": "reject"}},
    },
    "relu_nondeterministic": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "adds fresh random noise every call",
        "source": _relu_model(
            "        x = x.contiguous()\n        y = torch.empty_like(x)\n"
            "        launch_relu(x, y, x.numel())\n"
            "        return y + 1e-6 * torch.randn_like(y)\n"
        ),
        "expect": {"a": "accept", "A4": "reject", "tiers": {"N": "reject"}},
    },
    "relu_decoy_launch": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "launches a Triton kernel, returns the torch result (passes b1 by design)",
        "source": _relu_model(
            "        scratch = torch.empty_like(x)\n"
            "        copy_kernel[(1,)](x, scratch, 1, BLOCK=16)\n"
            "        return torch.relu(x)\n"
        ),
        "expect": {"a": "accept", "b1": "accept", "A1": "accept", "tiers": {"N": "accept"}},
    },
    "relu_hang": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "never returns (watchdog)",
        "source": "import time\nimport torch\nimport torch.nn as nn\n\nclass ModelNew(nn.Module):\n"
        "    def __init__(self):\n        super().__init__()\n\n"
        "    def forward(self, x):\n        while True:\n            time.sleep(1)\n",
        "expect": {"a": "timeout"},
    },
    "relu_crash": {
        "problem": "L1/9001_SyntheticReLU",
        "role": "kills its own process (worker crash)",
        "source": "import os\nimport torch\nimport torch.nn as nn\n\nclass ModelNew(nn.Module):\n"
        "    def __init__(self):\n        super().__init__()\n\n"
        "    def forward(self, x):\n        os._exit(3)\n",
        "expect": {"a": "reject"},
    },
    "rowsum_correct": {
        "problem": "L1/9002_SyntheticRowSum",
        "role": "correct",
        "source": _TRITON_HEADER
        + _ROWSUM_KERNEL
        + "\n\nclass ModelNew(nn.Module):\n    def __init__(self, dim):\n"
        "        super().__init__()\n        self.dim = dim\n\n"
        "    def forward(self, x):\n        return launch_rowsum(x, 0)\n",
        "expect": {
            "a": "accept",
            "a_1e-3": "accept",
            "c1": "accept",
            "c2": "accept",
            "c3": "accept",
            "A1": "accept",
            "A2": "accept",
            "A3": "accept",
            "A4": "accept",
            "tiers": {"N": "accept", "G": "accept"},
        },
    },
    "rowsum_tail_drop": {
        "problem": "L1/9002_SyntheticRowSum",
        "role": "boundary mutant: drops the last column (tolerance-sensitive)",
        "source": _TRITON_HEADER
        + _ROWSUM_KERNEL
        + "\n\nclass ModelNew(nn.Module):\n    def __init__(self, dim):\n"
        "        super().__init__()\n        self.dim = dim\n\n"
        "    def forward(self, x):\n        return launch_rowsum(x, 1)\n",
        "expect": {
            "a": "accept",
            "a_head_1e-2": "accept",
            "a_1e-3": "reject",
            "a_head_1e-4": "reject",
            "c1": "reject",
            "A1": "reject",
            "tiers": {"N": "reject"},
        },
    },
    "ce_torch_control": {
        "problem": "L1/9003_SyntheticCrossEntropy",
        "role": "reference-identity with integer targets",
        "source": "import torch\nimport torch.nn as nn\n\nclass ModelNew(nn.Module):\n"
        "    def __init__(self):\n        super().__init__()\n\n"
        "    def forward(self, predictions, targets):\n"
        "        return torch.nn.functional.cross_entropy(predictions, targets)\n",
        "expect": {"a": "accept", "a_head_1e-4": "error", "b1": "reject", "A1": "accept"},
    },
    "argmax_control": {
        "problem": "L1/9004_SyntheticArgmax",
        "role": "reference-identity with integer output",
        "source": "import torch\nimport torch.nn as nn\n\nclass ModelNew(nn.Module):\n"
        "    def __init__(self, dim):\n        super().__init__()\n        self.dim = dim\n\n"
        "    def forward(self, x):\n        return torch.argmax(x, dim=self.dim)\n",
        "expect": {"a": "accept", "A1": "accept", "A2": "accept", "tiers": {"N": "accept"}},
    },
    "argmax_last_tie": {
        "problem": "L1/9004_SyntheticArgmax",
        "role": "semantic mutant: last index among ties (torch uses the first)",
        "source": "import torch\nimport torch.nn as nn\n\nclass ModelNew(nn.Module):\n"
        "    def __init__(self, dim):\n        super().__init__()\n        self.dim = dim\n\n"
        "    def forward(self, x):\n        n = x.shape[self.dim]\n"
        "        return n - 1 - torch.argmax(torch.flip(x, dims=[self.dim]), dim=self.dim)\n",
        "expect": {"a": "accept", "A1": "accept", "A2": "reject", "tiers": {"N": "reject"}},
    },
}

#: Doctor work: every kernel gets these gates and channels unless listed otherwise.
DEFAULT_GATES = (
    "a",
    "a_1e-3",
    "a_head_1e-4",
    "a_head_1e-2",
    "a_static",
    "b1",
    "c",
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
)
ONLY_GATES = {"relu_hang": ("a",), "relu_crash": ("a",)}
