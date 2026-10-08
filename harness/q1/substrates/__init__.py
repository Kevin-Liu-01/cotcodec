"""Q1 Stage 0 substrate corpus: compiler-generated (S1) and human-written (S2) Triton kernels.

S1 is TorchInductor output for KernelBench@423217d9 L1/L2 problems, compiled with
dynamic shapes and converted to plain ``@triton.jit`` functions launched as
``kernel[grid](...)``, so that gate (b)'s launch hook can observe them.

S2 is human-written pre-2025 Triton (FlagGems v1.0-manual, Liger-Kernel v0.3.1,
Triton tutorials), each wrapped in a ``ModelNew`` for one KernelBench problem.

Modules
-------

- :mod:`.sources`: pinned upstream sources (revision, licence) and the problem
  exclusion list.
- :mod:`.inductor_codegen`: runs ``torch.compile`` in a GPU-less container (or on
  a GPU) and records the generated wrapper, kernels, configs and guards. Needs
  torch; imported only by the build step.
- :mod:`.inductor_convert`: pure-Python conversion of a codegen record into a
  substrate directory (``kernel.py`` + ``substrate.json`` + ``build.json``).
- :mod:`.s2_catalog`: the S2 kernel-to-problem mapping and its build.
- :mod:`.admission`: static launch-path check, CPU compile and interpreter
  checks, and the GPU hook-visibility check (``admission_hook`` rows).
- :mod:`.split`: the seeded S1 calibration/evaluation split.

Only :mod:`.inductor_codegen` and parts of :mod:`.admission` import torch or
triton, and they do so lazily.
"""
