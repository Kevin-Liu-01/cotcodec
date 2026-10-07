# Toy Triton kernels for the Q1 mutator tests

Small kernels written for the mutator's unit tests. The tests parse them as
source text only; they are never imported or launched by the test suite, and
they are not part of the Q1 validation corpus (decision D3). The compiled-dedup
test compiles `relu_where.py` for sm_90 in a GPU-less container without running
it. Each file imitates one upstream style (FlagGems, TorchInductor, the Triton
tutorials) so that every operator family has at least one site.
