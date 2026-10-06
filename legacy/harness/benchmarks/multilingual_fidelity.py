"""Multilingual-Agent-Fidelity — custom benchmark for Paper 1.

Tests semantic fidelity under language switching on terminology-heavy
agent tasks. Verifies that switching internal language doesn't cause
meaningful drift on domain-specific reasoning.

This is a NOVEL contribution specific to the language orchestration paper.
"""

from __future__ import annotations

from typing import Any

from harness.benchmarks.base import BenchmarkAdapter, BenchmarkTask, TaskResult


class MultilingualFidelityAdapter(BenchmarkAdapter):
    """Custom benchmark testing semantic fidelity under language switching.

    Task categories:
    - Medical terminology: drug interactions, dosage reasoning
    - Legal reasoning: contract clause interpretation
    - Financial calculations: multi-step numeric reasoning with domain terms
    - Technical support: error code interpretation with product-specific vocabulary
    - API integration: endpoint names, parameter types, response schemas

    For each task:
    1. Run in English-only (baseline)
    2. Run in each language condition
    3. Compare outputs via entailment scoring
    4. Flag tasks where language switching changes the answer

    TODO: Build the actual task set with parallel gold annotations.
    """

    def __init__(self, data_dir: str = "raw/baselines/multilingual-fidelity"):
        self.data_dir = data_dir

    @property
    def name(self) -> str:
        return "multilingual_fidelity"

    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        raise NotImplementedError(
            "Multilingual-Agent-Fidelity tasks not yet built. "
            "Requires parallel gold annotations across terminology domains."
        )

    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        raise NotImplementedError("Multilingual fidelity evaluation not yet implemented.")

    def get_system_prompt(self) -> str:
        return (
            "You are an AI assistant completing a domain-specific task. "
            "Use precise terminology. Accuracy of technical terms, numbers, "
            "and domain-specific identifiers is critical."
        )
