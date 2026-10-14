"""Shared helpers for the G2 exploratory pilot (experiments/g2/g2-pilot-v1.yaml).

Pure Python (no torch, no vLLM) so that both images and the CPU analysis can import it:
config and prompt loading, the per-job deadline, the lane's checkpoint marker, model receipt
verification, and the token-level mismatch statistics.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "g2" / "g2-pilot-v1.yaml"
MODEL_ROOT = Path("/model-cache/cotcodec-models")
CACHE_ROOT = Path("/model-cache")
#: The lane stops a container 30 s before the limit and signals USR1 180 s before it; work
#: stops being started this many seconds before the limit.
DEADLINE_MARGIN_S = 210.0


class G2ConfigError(ValueError):
    """The pilot config or its inputs are invalid."""


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("experiment_id") != "g2-pilot-v1":
        raise G2ConfigError("not the g2-pilot-v1 config")
    if config.get("claim_level") != "exploratory":
        raise G2ConfigError("the G2 pilot is exploratory only")
    seeds = config.get("seeds")
    if seeds != [42, 43, 44]:
        raise G2ConfigError("seeds must be [42, 43, 44]")
    for model_id, model in config["models"].items():
        if not set(model["rollout_seeds"]) <= set(seeds):
            raise G2ConfigError(f"{model_id}: rollout seeds outside the declared seeds")
        if not set(config["teacher_force"]["fp32_seeds"]) <= set(model["rollout_seeds"]):
            raise G2ConfigError(f"{model_id}: fp32 seeds must be rollout seeds")
    analysis = config.get("analysis", {})
    analysis["entropy_edges"] = numeric_edges(analysis.get("entropy_edges"), "entropy_edges")
    return config


def numeric_edges(values: Any, name: str = "edges") -> list[float]:
    """Bin edges as floats, strictly increasing; anything that is not a number is refused.

    YAML 1.1 (PyYAML) reads an exponent without a sign, such as ``1.0e9``, as a string, and
    numpy then compares values with the edges as text. The g2-pilot-v1 analysis first ran
    with such an edge and misbinned about a quarter of the hybrid's tokens.
    """

    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise G2ConfigError(f"{name}: need a list of at least two edges, got {values!r}")
    edges: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise G2ConfigError(f"{name}: edge {value!r} is a {type(value).__name__}, not a number")
        if math.isnan(value):
            raise G2ConfigError(f"{name}: edge is NaN")
        edges.append(float(value))
    if any(b <= a for a, b in zip(edges, edges[1:], strict=False)):
        raise G2ConfigError(f"{name}: edges must increase strictly, got {edges}")
    return edges


def load_prompts(config: dict[str, Any]) -> list[dict[str, Any]]:
    spec = config["prompts"]
    path = PROJECT_ROOT / spec["file"]
    raw = path.read_bytes()
    if sha256_bytes(raw) != spec["sha256"]:
        raise G2ConfigError("prompt file digest differs from the config")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != spec["count"] or [r["prompt_index"] for r in rows] != list(range(len(rows))):
        raise G2ConfigError("prompt file must hold prompt_index 0..count-1 in order")
    return rows


def user_message(row: dict[str, Any], config: dict[str, Any]) -> str:
    return row["problem"] + config["prompts"]["user_suffix"]


def sequence_id(model_id: str, prompt_index: int, seed: int) -> str:
    return f"{model_id}/p{prompt_index:03d}/s{seed}"


def prompt_subset(prompts: Sequence[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """The first-seed subset of ``count`` prompts: random.Random(42).sample, in index order."""

    import random

    if count >= len(prompts):
        return list(prompts)
    chosen = sorted(random.Random(42).sample(range(len(prompts)), count))
    return [prompts[i] for i in chosen]


def rollout_plan(config: dict[str, Any], prompts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every (model, seed, prompt) request in submission order: model, then seed, then prompt."""

    plan = []
    for model_id, model in config["models"].items():
        for seed in model["rollout_seeds"]:
            for row in prompts:
                plan.append(
                    {
                        "sequence_id": sequence_id(model_id, row["prompt_index"], seed),
                        "model_id": model_id,
                        "seed": seed,
                        "prompt_index": row["prompt_index"],
                    }
                )
    return plan


# --------------------------------------------------------------------------- lane runtime


def allocation_start(output_root: Path | None = None) -> tuple[float, str]:
    """The lane's started_at from job.env (written before the container starts), else now."""

    root = output_root or Path(os.environ.get("COTCODEC_OUTPUT_DIR", "/outputs"))
    try:
        for line in (root / "job.env").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key == "started_at":
                started = datetime.strptime(value.strip(), "%Y-%m-%dT%H:%M:%SZ")
                return started.replace(tzinfo=UTC).timestamp(), "job.env started_at"
    except (OSError, ValueError):
        pass
    return time.time(), "driver start"


def deadline(allocation_minutes: float, output_root: Path | None = None) -> tuple[float, str]:
    start, source = allocation_start(output_root)
    return start + allocation_minutes * 60.0 - DEADLINE_MARGIN_S, source


def write_checkpoint_marker(trigger: str, note: str) -> None:
    """The lane's signal checkpoint marker: temporary file then rename, with the trigger line."""

    marker = Path(os.environ.get("COTCODEC_CHECKPOINT_MARKER", "/outputs/checkpoint.ready"))
    marker.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=marker.parent, delete=False, encoding="utf-8", prefix=".ckpt-"
    ) as handle:
        handle.write(f"trigger={trigger}\nnote={note}\nutc={utc_now()}\n")
        temporary = Path(handle.name)
    os.replace(temporary, marker)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def verify_model(model_id: str, receipt_root: str) -> dict[str, Any]:
    """Re-verify a model snapshot against its receipt with the committed fetch script."""

    receipt = CACHE_ROOT / receipt_root / f"{model_id}.json"
    record: dict[str, Any] = {
        "model_id": model_id,
        "receipt": str(receipt),
        "receipt_sha256": sha256_file(receipt),
    }
    data = json.loads(receipt.read_text(encoding="utf-8"))
    for key in ("repo_id", "revision", "mode", "total_bytes", "artifact_root_sha256"):
        record[key] = data.get(key)
    if data.get("mode") != "full":
        raise G2ConfigError(f"{model_id}: receipt is not a full snapshot")
    if model_id == os.environ.get("COTCODEC_MODEL_ID") and receipt_root == "cotcodec-receipts":
        # The lane verified every file of its primary model before the workload started.
        record["verified_by"] = "lane (model-verification.txt)"
        return record
    record["verified_by"] = "scripts/fetch_open_model.py verify"
    started = time.time()
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "fetch_open_model.py"),
            "--model-root",
            str(MODEL_ROOT),
            "--receipt-root",
            str(CACHE_ROOT / receipt_root),
            "verify",
            model_id,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    record.update(
        verify_exit=result.returncode,
        verify_stdout=result.stdout[-2000:],
        verify_stderr=result.stderr[-2000:],
        verify_s=round(time.time() - started, 1),
    )
    if result.returncode != 0:
        raise G2ConfigError(f"{model_id}: snapshot verification failed")
    return record


# --------------------------------------------------------------------------- statistics


def k3(log_ratio: float) -> float:
    """Schulman's k3 estimator of KL(p || q) at a sample from p, with log_ratio = log q - log p."""

    return math.expm1(log_ratio) - log_ratio


def position_bin(position: int, width: int) -> int:
    return position // width
