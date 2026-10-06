#!/usr/bin/env python3
"""Prepare a sealed official-prompt LongMemEval packet from model outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    LongMemEvalTaskSource,
    prepare_longmemeval_judge_cases,
    seal_official_judge_contract,
    task_manifest_sha256,
    write_judge_packet,
)
from scripts.fetch_open_model import load_registry  # noqa: E402
from scripts.freeze_memory_system_outputs import DEFAULT_LONGMEMEVAL_PATH  # noqa: E402
from scripts.validate_memory_experiments import validate_memory_experiment  # noqa: E402
from scripts.validate_memory_sources import load_and_validate  # noqa: E402
from scripts.validate_provider_models import load_provider_registry  # noqa: E402

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage1-longmemeval-screen.yaml"
)


def prepare_packet(
    *,
    config_path: Path,
    dataset_path: Path,
    bundle_root: Path,
    output_dir: Path,
    mode: str,
) -> dict[str, Any]:
    open_models = set(load_registry()["models"])
    memory_sources = set(load_and_validate()["sources"])
    provider_models = set(load_provider_registry()["models"])
    validate_memory_experiment(
        config_path,
        model_ids=open_models,
        source_ids=memory_sources,
        provider_model_ids=provider_models,
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("LongMemEval experiment must be a schema_version: 1 mapping")
    source_config = config.get("source")
    if not isinstance(source_config, dict) or source_config.get("type") != "longmemeval":
        raise ValueError("judge preparation requires a LongMemEval experiment")
    if mode == "transport-panel":
        task_ids = source_config.get("screen_raw_task_ids")
        expected_manifest = source_config.get("screen_task_manifest_sha256")
    elif mode == "full-benchmark":
        task_ids = None
        expected_manifest = source_config.get("full_task_manifest_sha256")
    else:
        raise ValueError("mode must be transport-panel or full-benchmark")
    source = LongMemEvalTaskSource(
        dataset_path,
        expected_sha256=str(source_config["dataset_sha256"]),
        expected_size=int(source_config["dataset_size"]),
        dataset_revision=str(source_config["dataset_revision"]),
        candidate_seed=int(source_config["candidate_seed"]),
        task_ids=task_ids,
        artifact_role=str(source_config["artifact_role"]),
    )
    actual_manifest = task_manifest_sha256(source)
    if actual_manifest != expected_manifest:
        raise ValueError("judge source task manifest differs from the experiment")
    cases = prepare_longmemeval_judge_cases(source, bundle_root)
    contract = seal_official_judge_contract()
    experiment_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
    packet = write_judge_packet(
        output_dir,
        source,
        cases,
        contract,
        experiment_sha256=experiment_sha256,
        preparation_mode=mode,
    )
    return {
        **packet,
        "mode": mode,
        "task_manifest_sha256": actual_manifest,
        "source_bundle": str(bundle_root.resolve()),
        "packet_root": str(output_dir.resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_LONGMEMEVAL_PATH)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=("transport-panel", "full-benchmark"),
        required=True,
    )
    args = parser.parse_args()
    result = prepare_packet(
        config_path=args.config.resolve(),
        dataset_path=args.dataset.resolve(),
        bundle_root=args.bundle_root.resolve(),
        output_dir=args.output_dir.resolve(),
        mode=args.mode,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
