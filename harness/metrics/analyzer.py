"""Trace analysis and Pareto frontier computation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_traces(trace_dir: str | Path) -> pd.DataFrame:
    """Load all JSONL trace files from a directory into a DataFrame."""
    trace_dir = Path(trace_dir)
    rows = []

    for jsonl_file in trace_dir.rglob("*.jsonl"):
        with open(jsonl_file) as f:
            for line in f:
                trace = json.loads(line)
                outcome = trace.get("outcome", {}) or {}
                rows.append({
                    "experiment_id": trace["experiment_id"],
                    "benchmark": trace["benchmark"],
                    "condition": trace["condition"],
                    "model": trace["model"],
                    "task_id": trace["task_id"],
                    "seed": trace["seed"],
                    "success": outcome.get("success", False),
                    "total_tokens": outcome.get("total_tokens", 0),
                    "total_latency_ms": outcome.get("total_latency_ms", 0),
                    "tool_calls_correct": outcome.get("tool_calls_correct", 0),
                    "tool_calls_total": outcome.get("tool_calls_total", 0),
                    "retries": outcome.get("retries", 0),
                    "safety_failures": outcome.get("safety_failures", 0),
                    "cost_usd": outcome.get("cost_usd", 0),
                    "message_count": len(trace.get("messages", [])),
                })

    return pd.DataFrame(rows)


def condition_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare metrics across conditions."""
    return df.groupby("condition").agg({
        "success": "mean",
        "total_tokens": "mean",
        "total_latency_ms": "mean",
        "tool_calls_correct": "sum",
        "tool_calls_total": "sum",
        "retries": "mean",
        "safety_failures": "sum",
        "cost_usd": "mean",
    }).round(4)


def message_type_decomposition(trace_dir: str | Path) -> pd.DataFrame:
    """Decompose token usage by message type across conditions.

    This is the key analysis: which message types benefit from language routing?
    """
    trace_dir = Path(trace_dir)
    rows = []

    for jsonl_file in trace_dir.rglob("*.jsonl"):
        with open(jsonl_file) as f:
            for line in f:
                trace = json.loads(line)
                for msg in trace.get("messages", []):
                    rows.append({
                        "condition": trace["condition"],
                        "message_type": msg["type"],
                        "language": msg["language"],
                        "token_count_input": msg.get("token_count_input", 0),
                        "token_count_output": msg.get("token_count_output", 0),
                        "total_tokens": (
                            msg.get("token_count_input", 0)
                            + msg.get("token_count_output", 0)
                        ),
                        "latency_ms": msg.get("latency_ms", 0),
                    })

    df = pd.DataFrame(rows)
    return df.groupby(["condition", "message_type"]).agg({
        "total_tokens": ["mean", "sum", "count"],
        "latency_ms": ["mean", "sum"],
    }).round(2)


def compute_pareto_frontier(
    df: pd.DataFrame,
    cost_col: str = "total_tokens",
    success_col: str = "success",
) -> list[dict[str, Any]]:
    """Compute Pareto-optimal conditions on the cost-success frontier.

    A condition is Pareto-optimal if no other condition has both lower cost
    and higher success rate.
    """
    agg = df.groupby("condition").agg({
        cost_col: "mean",
        success_col: "mean",
    }).reset_index()

    points = agg.to_dict("records")
    pareto = []

    for p in points:
        dominated = False
        for q in points:
            if q["condition"] == p["condition"]:
                continue
            if q[cost_col] <= p[cost_col] and q[success_col] >= p[success_col]:
                if q[cost_col] < p[cost_col] or q[success_col] > p[success_col]:
                    dominated = True
                    break
        if not dominated:
            pareto.append(p)

    return sorted(pareto, key=lambda x: x[cost_col])
