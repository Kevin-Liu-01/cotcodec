"""GPU (TF32) equivalence of the K1 successor's bank; runs only where CUDA is visible.

Run it inside the research image on one H100 that Slurm allocated, with
``COTCODEC_GPU_TESTS=1 pytest -q tests/test_sparse_indexer_bank_gpu.py``; the
variable keeps a shell that merely sees the node's GPUs from using one outside
the lane (docs/operations.md). It needs no model weights: the
registered-shape bank check uses random bf16-valued activations, and the
device gates of ``harness/sparse_indexer_k1_equivalence_v2.py`` run on a tiny
random Qwen3 model. The throughput probe runs the same gates on the real
teacher before it times anything.
"""

from __future__ import annotations

import os

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

if os.environ.get("COTCODEC_GPU_TESTS") != "1" or not torch.cuda.is_available():
    pytest.skip("needs COTCODEC_GPU_TESTS=1 and an allocated CUDA device",
                allow_module_level=True)

from harness import sparse_indexer_bank as skb  # noqa: E402
from harness import sparse_indexer_k1_equivalence_v2 as eq  # noqa: E402
from harness import sparse_indexer_k1_runtime as rt  # noqa: E402
from harness import sparse_indexer_torch as sit  # noqa: E402

DEVICE = torch.device("cuda:0")


def test_registered_shape_bank_matches_v1_under_tf32() -> None:
    sit.set_determinism(allow_tf32=True)
    generator = torch.Generator().manual_seed(42)
    length = 8192
    hidden = torch.randn(length, 1024, generator=generator).bfloat16().to(DEVICE)
    q = torch.randn(16, length, 128, generator=generator).bfloat16().to(DEVICE)
    k = torch.randn(8, length, 128, generator=generator).bfloat16().to(DEVICE)
    targets = rt.sequence_targets(q, k, 128 ** -0.5)
    report = skb.compare_with_v1(sit.IndexerSpec(), 15, eq.registered_keys(), hidden, targets,
                                 device=DEVICE, dtype=torch.float32)
    tolerance = eq.TOLERANCES
    assert report["loss_max_rel"] <= tolerance["loss_max_rel"], report
    assert report["clip_norm_max_rel"] <= tolerance["clip_norm_max_rel"], report
    assert max(report["grad_max_rel_fro"].values()) <= tolerance["grad_max_rel_fro"], report
    adam = eq.adam_check(sit.IndexerSpec(), 15, eq.registered_keys(), DEVICE)
    assert adam["adam_step_max_rel"] <= tolerance["adam_step_max_rel"], adam


def test_device_gates_on_a_tiny_model(tmp_path) -> None:
    from scripts.run_sparse_indexer_k1_doctor import make_tiny_model

    teacher = sit.load_teacher(make_tiny_model(tmp_path / "model"), DEVICE)
    report = eq.device_check(teacher, DEVICE, profile=rt.Profile.tiny(), length=256, layer=2,
                             unit_rows=5, unit_context=120)
    assert report["passed"], report["gates"]


def test_selection_on_the_device_is_the_registered_rule() -> None:
    assert eq.selection_check(DEVICE)["selection_exact"]
