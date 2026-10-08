"""Nested-KVM desktop runtime: VM campaign manifests, host driver and in-netns runner.

Everything in this package is standard-library only and Python 3.10 compatible,
because the driver runs on the H100 host (Python 3.10, no project venv) and the
runner runs in a minimal GPU-less container.
"""
