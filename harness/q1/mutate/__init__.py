"""Q1 mutator: a Triton/Python AST port of the Measuring the Checker taxonomy.

Public entry points:

- :func:`enumerate_mutants` (engine) - distinct mutants of one ``kernel.py``;
- :data:`OPERATORS` - the operator registry (paper rules and Triton-only
  extensions, tagged);
- :func:`stratified_cap`, :func:`split_of` (sampling) - the per-substrate cap
  and the frozen dev/test split;
- ``corpus`` - pool, compile filter, selection and controls on disk;
- ``compiled`` - the compiled-specialization dedup hook;
- ``fixtures`` - hack-emulating positive controls;
- ``rules`` - the KernelBench-M rule mapping table.

Everything except ``compiled.record_specializations`` and
``compiled.compile_hashes`` is pure Python with no torch or Triton import.
"""

from harness.q1.mutate.engine import Enumeration, MutantCandidate, enumerate_mutants
from harness.q1.mutate.operators import OPERATORS, registry_fingerprint, registry_table
from harness.q1.mutate.sampling import split_of, stratified_cap

__all__ = [
    "OPERATORS",
    "Enumeration",
    "MutantCandidate",
    "enumerate_mutants",
    "registry_fingerprint",
    "registry_table",
    "split_of",
    "stratified_cap",
]
