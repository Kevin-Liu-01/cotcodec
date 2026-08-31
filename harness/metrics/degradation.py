"""Degradation detection for orchestration variable changes.

Implements statistical tests to determine whether an orchestration change
caused a real quality regression or just evaluation noise.

Based on:
- "When LLMs get significantly worse" (ICLR 2026) — McNemar's test
- Anthropic April 23, 2026 postmortem — harness-level degradation case study
- Amazon LLM-Accuracy-Stats framework
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SampleOutcome:
    """Per-sample outcome for paired comparison."""

    task_id: str
    baseline_correct: bool
    treatment_correct: bool


@dataclass(frozen=True)
class TraceOutcomeRecord:
    """One strictly keyed terminal trace outcome."""

    pair_key: tuple[str, str, str, str, int, str]
    success: bool
    category: str
    condition: str


@dataclass
class DegradationResult:
    """Result of a degradation test between two conditions."""

    baseline_condition: str
    treatment_condition: str
    model: str
    benchmark: str
    n_samples: int
    baseline_accuracy: float
    treatment_accuracy: float
    accuracy_delta: float
    mcnemar_statistic: float
    p_value: float
    is_degradation: bool
    confidence_level: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline": self.baseline_condition,
            "treatment": self.treatment_condition,
            "model": self.model,
            "benchmark": self.benchmark,
            "n_samples": self.n_samples,
            "baseline_accuracy": round(self.baseline_accuracy, 4),
            "treatment_accuracy": round(self.treatment_accuracy, 4),
            "accuracy_delta": round(self.accuracy_delta, 4),
            "mcnemar_statistic": round(self.mcnemar_statistic, 4),
            "p_value": round(self.p_value, 6),
            "is_degradation": self.is_degradation,
        }


class DegradationDetector:
    """Detects quality degradation between orchestration conditions.

    Uses McNemar's test (ICLR 2026) for per-sample paired comparison.
    Can detect degradations as small as 0.3% with controlled false positives.
    """

    def __init__(self, confidence_level: float = 0.05):
        self.confidence_level = confidence_level
        self._results: list[DegradationResult] = []

    def compare_conditions(
        self,
        outcomes: list[SampleOutcome],
        baseline_condition: str,
        treatment_condition: str,
        model: str = "",
        benchmark: str = "",
    ) -> DegradationResult:
        """Run McNemar's test comparing two conditions on the same samples.

        McNemar's test uses the 2x2 contingency table of discordant pairs:
        - b: baseline correct, treatment wrong (degradation evidence)
        - c: baseline wrong, treatment correct (improvement evidence)

        Test statistic: chi2 = (b - c)^2 / (b + c)
        Under H0 (no difference), follows chi-squared with 1 df.
        """
        n = len(outcomes)
        baseline_correct = sum(1 for o in outcomes if o.baseline_correct)
        treatment_correct = sum(1 for o in outcomes if o.treatment_correct)

        b = sum(1 for o in outcomes if o.baseline_correct and not o.treatment_correct)
        c = sum(1 for o in outcomes if not o.baseline_correct and o.treatment_correct)

        discordant = b + c
        if discordant == 0:
            result = DegradationResult(
                baseline_condition=baseline_condition,
                treatment_condition=treatment_condition,
                model=model,
                benchmark=benchmark,
                n_samples=n,
                baseline_accuracy=baseline_correct / max(1, n),
                treatment_accuracy=treatment_correct / max(1, n),
                accuracy_delta=(treatment_correct - baseline_correct) / max(1, n),
                mcnemar_statistic=0.0,
                p_value=1.0,
                is_degradation=False,
                confidence_level=self.confidence_level,
            )
            self._results.append(result)
            return result

        chi2 = (b - c) ** 2 / discordant

        from scipy import stats
        p_value = 1 - stats.chi2.cdf(chi2, df=1)

        is_degradation = p_value < self.confidence_level and b > c

        result = DegradationResult(
            baseline_condition=baseline_condition,
            treatment_condition=treatment_condition,
            model=model,
            benchmark=benchmark,
            n_samples=n,
            baseline_accuracy=baseline_correct / max(1, n),
            treatment_accuracy=treatment_correct / max(1, n),
            accuracy_delta=(treatment_correct - baseline_correct) / max(1, n),
            mcnemar_statistic=chi2,
            p_value=p_value,
            is_degradation=is_degradation,
            confidence_level=self.confidence_level,
        )
        self._results.append(result)
        return result

    def aggregate_across_benchmarks(
        self,
        results: list[DegradationResult],
        method: str = "fisher",
    ) -> dict[str, Any]:
        """Aggregate degradation detection across multiple benchmarks.

        Methods (from ICLR 2026 paper):
        - bonferroni: Most conservative. Adjust alpha by number of tests.
        - fisher: Combine p-values via Fisher's method. Balanced.
        - simes: Most sensitive, higher false positive risk.
        """
        if not results:
            return {"method": method, "combined_p_value": 1.0, "is_degradation": False}

        p_values = [r.p_value for r in results]
        n_tests = len(p_values)

        if method == "bonferroni":
            adjusted_alpha = self.confidence_level / n_tests
            combined_degradation = any(
                r.p_value < adjusted_alpha and r.accuracy_delta < 0 for r in results
            )
            return {
                "method": "bonferroni",
                "adjusted_alpha": adjusted_alpha,
                "is_degradation": combined_degradation,
                "per_benchmark": [r.to_dict() for r in results],
            }

        elif method == "fisher":
            import math

            from scipy import stats
            stat = -2 * sum(math.log(max(p, 1e-300)) for p in p_values)
            combined_p = 1 - stats.chi2.cdf(stat, df=2 * n_tests)
            return {
                "method": "fisher",
                "combined_p_value": round(combined_p, 6),
                "is_degradation": combined_p < self.confidence_level,
                "per_benchmark": [r.to_dict() for r in results],
            }

        elif method == "simes":
            sorted_p = sorted(p_values)
            simes_reject = any(
                p <= self.confidence_level * (i + 1) / n_tests
                for i, p in enumerate(sorted_p)
            )
            return {
                "method": "simes",
                "is_degradation": simes_reject,
                "per_benchmark": [r.to_dict() for r in results],
            }

        raise ValueError(f"Unknown aggregation method: {method}")

    def run_canary(
        self,
        baseline_traces: str | Path,
        treatment_traces: str | Path,
    ) -> dict[str, Any]:
        """Run the OrchVar-Canary suite comparing two trace directories.

        Loads paired traces from baseline and treatment, requires identical
        experiment/benchmark/model/task/seed/run-group key sets, and rejects
        duplicates or partial intersections.
        """
        baseline_path = Path(baseline_traces)
        treatment_path = Path(treatment_traces)

        baseline_outcomes = self._load_outcomes(baseline_path)
        treatment_outcomes = self._load_outcomes(treatment_path)

        baseline_keys = set(baseline_outcomes)
        treatment_keys = set(treatment_outcomes)
        if baseline_keys != treatment_keys:
            missing_treatment = sorted(baseline_keys - treatment_keys)
            missing_baseline = sorted(treatment_keys - baseline_keys)
            raise ValueError(
                "paired trace key mismatch: "
                f"missing treatment={missing_treatment}, missing baseline={missing_baseline}"
            )
        if not baseline_keys:
            raise ValueError("paired trace sets are empty")

        outcomes = [
            SampleOutcome(
                task_id="|".join(map(str, pair_key)),
                baseline_correct=baseline_outcomes[pair_key].success,
                treatment_correct=treatment_outcomes[pair_key].success,
            )
            for pair_key in sorted(baseline_keys)
        ]

        baseline_conditions = {record.condition for record in baseline_outcomes.values()}
        treatment_conditions = {record.condition for record in treatment_outcomes.values()}
        if len(baseline_conditions) != 1 or len(treatment_conditions) != 1:
            raise ValueError("each paired trace set must contain exactly one condition")
        sample = next(iter(baseline_outcomes.values()))

        result = self.compare_conditions(
            outcomes,
            baseline_condition=next(iter(baseline_conditions)),
            treatment_condition=next(iter(treatment_conditions)),
            model=sample.pair_key[2],
            benchmark=sample.pair_key[1],
        )

        return {
            "canary_result": result.to_dict(),
            "matched_tasks": len(baseline_keys),
            "alert": result.is_degradation,
            "recommendation": (
                "BLOCK: significant degradation detected"
                if result.is_degradation
                else "PASS: no significant degradation"
            ),
        }

    def run_canary_by_category(
        self,
        baseline_traces: str | Path,
        treatment_traces: str | Path,
    ) -> dict[str, Any]:
        """Run exact paired McNemar tests independently for every category."""
        baseline = self._load_outcomes(Path(baseline_traces))
        treatment = self._load_outcomes(Path(treatment_traces))
        if set(baseline) != set(treatment):
            raise ValueError("paired trace key mismatch")
        categories = sorted({record.category for record in baseline.values()})
        if not categories or any(not category for category in categories):
            raise ValueError("canary traces have missing categories")
        per_category: dict[str, Any] = {}
        for category in categories:
            keys = sorted(
                key for key, record in baseline.items() if record.category == category
            )
            if {treatment[key].category for key in keys} != {category}:
                raise ValueError("paired trace category drifted")
            outcomes = [
                SampleOutcome(
                    task_id="|".join(map(str, key)),
                    baseline_correct=baseline[key].success,
                    treatment_correct=treatment[key].success,
                )
                for key in keys
            ]
            sample = baseline[keys[0]]
            result = self.compare_conditions(
                outcomes,
                baseline_condition=sample.condition,
                treatment_condition=treatment[keys[0]].condition,
                model=sample.pair_key[2],
                benchmark=sample.pair_key[1],
            )
            per_category[category] = result.to_dict()
        return {
            "matched_pairs": len(baseline),
            "categories": per_category,
        }

    @staticmethod
    def _load_outcomes(
        trace_dir: Path,
    ) -> dict[tuple[str, str, str, str, int, str], TraceOutcomeRecord]:
        """Load terminal outcomes and reject incomplete or duplicate pair keys."""
        outcomes: dict[
            tuple[str, str, str, str, int, str], TraceOutcomeRecord
        ] = {}
        files = [trace_dir] if trace_dir.is_file() else sorted(trace_dir.rglob("*.jsonl"))
        if not files:
            raise ValueError(f"trace directory has no JSONL files: {trace_dir}")
        for jsonl_file in files:
            with jsonl_file.open(encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    try:
                        trace = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"{jsonl_file}:{line_number}: malformed JSON"
                        ) from exc
                    outcome = trace.get("outcome")
                    metadata = trace.get("task_metadata")
                    fields = (
                        trace.get("experiment_id"),
                        trace.get("benchmark"),
                        trace.get("model"),
                        trace.get("task_id"),
                        trace.get("seed"),
                        trace.get("run_group"),
                    )
                    if (
                        not all(isinstance(value, str) and value for value in fields[:4])
                        or isinstance(fields[4], bool)
                        or not isinstance(fields[4], int)
                        or not isinstance(fields[5], str)
                        or not isinstance(outcome, dict)
                        or not isinstance(outcome.get("success"), bool)
                        or not isinstance(metadata, dict)
                        or not isinstance(metadata.get("category"), str)
                    ):
                        raise ValueError(
                            f"{jsonl_file}:{line_number}: incomplete terminal trace"
                        )
                    pair_key = (
                        str(fields[0]),
                        str(fields[1]),
                        str(fields[2]),
                        str(fields[3]),
                        int(fields[4]),
                        str(fields[5]),
                    )
                    if pair_key in outcomes:
                        raise ValueError(f"duplicate paired trace key: {pair_key}")
                    outcomes[pair_key] = TraceOutcomeRecord(
                        pair_key=pair_key,
                        success=outcome["success"],
                        category=metadata["category"],
                        condition=str(trace.get("condition", "")),
                    )
        return outcomes


# Canary task categories for OrchVar-Canary benchmark
CANARY_CATEGORIES = {
    "reasoning_depth": {
        "description": "Tasks that fail when thinking is too short",
        "catches": "Reasoning effort reductions (high→medium)",
        "anthropic_bug": "March 4 effort change",
    },
    "context_recall": {
        "description": "Tasks that need information from step 2 at step 10",
        "catches": "Memory/thinking cache clearing",
        "anthropic_bug": "March 26 thinking cache bug",
    },
    "verbosity_sensitive": {
        "description": "Tasks where brevity causes critical information loss",
        "catches": "System prompt verbosity limits",
        "anthropic_bug": "April 16 ≤25-word limit",
    },
    "multi_turn_memory": {
        "description": "Tasks that degrade if working memory is cleared between turns",
        "catches": "Compaction policy regressions",
        "anthropic_bug": "March 26 thinking cache bug (compounding)",
    },
    "tool_argument_precision": {
        "description": "Tasks where tool arguments must be exact (IDs, dates, numbers)",
        "catches": "Schema fidelity loss under compression or language switching",
        "anthropic_bug": None,
    },
    "safety_canary": {
        "description": "Tasks that test refusal consistency across conditions",
        "catches": "Instruction hierarchy regression under language mixing",
        "anthropic_bug": None,
    },
}
