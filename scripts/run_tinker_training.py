#!/usr/bin/env python3
"""Run bounded Tinker SFT from a registered rendered-prefix dataset."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import signal
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.training.tinker_backend import (  # noqa: E402
    TinkerExperimentContract,
    TinkerStage,
    load_tinker_contract,
)


@dataclass(frozen=True)
class Example:
    example_id: str
    prefix: str
    target: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def load_examples(path: Path) -> list[Example]:
    examples: list[Example] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"line {line_number}: record must be an object")
            if set(payload) != {"example_id", "prefix", "target"}:
                raise ValueError(
                    f"line {line_number}: fields must be example_id, prefix, target"
                )
            values = [payload[key] for key in ("example_id", "prefix", "target")]
            if not all(isinstance(value, str) and value for value in values):
                raise ValueError(f"line {line_number}: all fields must be nonempty strings")
            if payload["example_id"] in seen:
                raise ValueError(f"line {line_number}: duplicate example_id")
            seen.add(payload["example_id"])
            examples.append(Example(*values))
    if not examples:
        raise ValueError("training dataset contains no examples")
    return examples


def epoch_order(size: int, seed: int, epoch: int) -> list[int]:
    order = list(range(size))
    random.Random(f"cotcodec-tinker:{seed}:{epoch}").shuffle(order)
    return order


def select_batch(
    examples: list[Example], seed: int, epoch: int, cursor: int, batch_size: int
) -> tuple[list[Example], int, int]:
    selected: list[Example] = []
    while len(selected) < batch_size:
        order = epoch_order(len(examples), seed, epoch)
        remaining = min(batch_size - len(selected), len(order) - cursor)
        selected.extend(examples[index] for index in order[cursor : cursor + remaining])
        cursor += remaining
        if cursor == len(order):
            epoch += 1
            cursor = 0
    return selected, epoch, cursor


def build_datum(tokenizer: Any, example: Example) -> tuple[Any, int]:
    import tinker

    prefix_tokens = tokenizer.encode(example.prefix, add_special_tokens=False)
    all_tokens = tokenizer.encode(example.prefix + example.target, add_special_tokens=False)
    if len(prefix_tokens) < 1 or len(all_tokens) <= len(prefix_tokens):
        raise ValueError(f"{example.example_id}: empty prefix or target tokenization")
    if all_tokens[: len(prefix_tokens)] != prefix_tokens:
        raise ValueError(
            f"{example.example_id}: target changes prefix tokenization; freeze a renderer "
            "boundary that is token-prefix stable"
        )
    model_tokens = all_tokens[:-1]
    target_tokens = np.asarray(all_tokens[1:], dtype=np.int64)
    weights = np.asarray(
        [0.0] * (len(prefix_tokens) - 1)
        + [1.0] * (len(all_tokens) - len(prefix_tokens)),
        dtype=np.float32,
    )
    datum = tinker.Datum(
        model_input=tinker.ModelInput.from_ints(model_tokens),
        loss_fn_inputs={
            "target_tokens": tinker.TensorData.from_numpy(target_tokens),
            "weights": tinker.TensorData.from_numpy(weights),
        },
    )
    return datum, len(model_tokens)


class StopController:
    def __init__(self) -> None:
        self.requested: str | None = None

    def request(self, signum: int, _: Any) -> None:
        self.requested = signal.Signals(signum).name


async def save_checkpoint(
    training_client: Any,
    contract: TinkerExperimentContract,
    stage: TinkerStage,
    seed: int,
    step: int,
    kind: str,
    ttl_seconds: int | None,
    state: dict[str, Any],
    state_path: Path,
) -> dict[str, Any]:
    stem = f"{contract.name}-{stage.name}-seed-{seed}-step-{step:06d}-{kind}"
    state_future = await training_client.save_state_async(
        f"{stem}-state", ttl_seconds=ttl_seconds
    )
    state_response = await state_future.result_async()
    sampler_future = await training_client.save_weights_for_sampler_async(
        f"{stem}-sampler", ttl_seconds=ttl_seconds
    )
    sampler_response = await sampler_future.result_async()
    updated = {
        **state,
        "step": step,
        "checkpoint_kind": kind,
        "tinker_state_path": state_response.path,
        "tinker_sampler_path": sampler_response.path,
    }
    atomic_json(state_path, updated)
    return updated


def download_checkpoint(service_client: Any, tinker_path: str, output: Path) -> str:
    response = (
        service_client.create_rest_client()
        .get_checkpoint_archive_url_from_tinker_path(tinker_path)
        .result()
    )
    digest = hashlib.sha256()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
        with httpx.stream("GET", response.url, follow_redirects=True, timeout=300) as remote:
            remote.raise_for_status()
            for chunk in remote.iter_bytes():
                handle.write(chunk)
                digest.update(chunk)
    os.replace(temporary, output)
    return digest.hexdigest()


def base_state(
    contract_hash: str,
    stage: TinkerStage,
    seed: int,
    epoch: int,
    cursor: int,
    cumulative_tokens: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract_sha256": contract_hash,
        "stage": stage.name,
        "model": stage.tinker_id,
        "seed": seed,
        "epoch": epoch,
        "cursor": cursor,
        "cumulative_train_tokens": cumulative_tokens,
    }


async def run(args: argparse.Namespace) -> int:
    contract_path = args.contract.resolve()
    contract = load_tinker_contract(contract_path)
    stage = next((item for item in contract.stages if item.name == args.stage), None)
    if stage is None:
        raise ValueError(f"unknown stage {args.stage!r}")
    if args.seed not in contract.seeds:
        raise ValueError(f"seed {args.seed} is not registered")
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN",
                    "contract": str(contract_path),
                    "stage": stage.name,
                    "model": stage.tinker_id,
                    "seed": args.seed,
                    "execution_enabled": contract.execution.enabled,
                    "train_token_ceiling": stage.train_tokens_per_seed,
                    "cost_ceiling_usd": contract.cost_ceiling_usd(),
                },
                indent=2,
            )
        )
        return 0
    if not contract.execution.enabled:
        raise ValueError("contract execution is disabled; resolve every blocker first")
    if not os.environ.get(contract.execution.secret_env):
        raise ValueError(f"{contract.execution.secret_env} is not set")
    train_path = args.train_jsonl.resolve()
    expected_hash = contract.data.train.sha256
    if expected_hash is None or sha256_file(train_path) != expected_hash:
        raise ValueError("training dataset does not match the registered SHA-256")
    examples = load_examples(train_path)

    import tinker

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "resume-state.json"
    contract_hash = sha256_file(contract_path)
    service_client = tinker.ServiceClient(
        user_metadata={
            "project": "cotcodec",
            "contract_sha256": contract_hash,
            "stage": stage.name,
            "seed": str(args.seed),
        }
    )
    if args.resume_state:
        state = json.loads(args.resume_state.resolve().read_text(encoding="utf-8"))
        expected = {
            "contract_sha256": contract_hash,
            "stage": stage.name,
            "seed": args.seed,
        }
        if any(state.get(key) != value for key, value in expected.items()):
            raise ValueError("resume state identity does not match this run")
        training_client = (
            await service_client.create_training_client_from_state_with_optimizer_async(
                state["tinker_state_path"]
            )
        )
        next_step = int(state["step"]) + 1
        epoch = int(state["epoch"])
        cursor = int(state["cursor"])
        cumulative_tokens = int(state["cumulative_train_tokens"])
    else:
        training_client = await service_client.create_lora_training_client_async(
            base_model=stage.tinker_id,
            rank=contract.lora.rank,
            seed=args.seed,
            train_mlp=contract.lora.train_mlp,
            train_attn=contract.lora.train_attn,
            train_unembed=contract.lora.train_unembed,
            user_metadata={"arm": "capsule-aware-lora"},
        )
        next_step, epoch, cursor, cumulative_tokens = 1, 0, 0, 0
        state = {}

    tokenizer = training_client.get_tokenizer()
    metrics_path = output_dir / "training-metrics.jsonl"
    stopper = StopController()
    signal.signal(signal.SIGUSR1, stopper.request)
    signal.signal(signal.SIGTERM, stopper.request)
    last_checkpoint = state
    completed_step = next_step - 1
    stop_reason = "max_steps"

    for step in range(next_step, contract.lora.max_steps + 1):
        batch, next_epoch, next_cursor = select_batch(
            examples, args.seed, epoch, cursor, contract.lora.batch_size
        )
        prepared = [build_datum(tokenizer, example) for example in batch]
        batch_tokens = sum(item[1] for item in prepared)
        if cumulative_tokens + batch_tokens > stage.train_tokens_per_seed:
            stop_reason = "train_token_ceiling"
            break
        future = await training_client.forward_backward_async(
            [item[0] for item in prepared], loss_fn="cross_entropy"
        )
        forward = await future.result_async()
        optim = await training_client.optim_step_async(
            tinker.AdamParams(learning_rate=contract.lora.learning_rate)
        )
        optim_result = await optim.result_async()
        completed_step = step
        cumulative_tokens += batch_tokens
        epoch, cursor = next_epoch, next_cursor
        metric = {
            "step": step,
            "example_ids": [example.example_id for example in batch],
            "batch_tokens": batch_tokens,
            "cumulative_train_tokens": cumulative_tokens,
            "estimated_train_usd": cumulative_tokens
            * stage.prices.train_per_million
            / 1_000_000,
            "forward_metrics": forward.metrics,
            "optimizer_metrics": optim_result.metrics or {},
        }
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(metric, sort_keys=True) + "\n")

        checkpoint_due = (
            step % contract.checkpoints.full_state_every_steps == 0
            or step % contract.checkpoints.sampler_weights_every_steps == 0
        )
        if checkpoint_due or stopper.requested:
            last_checkpoint = await save_checkpoint(
                training_client,
                contract,
                stage,
                args.seed,
                step,
                "interrupt" if stopper.requested else "periodic",
                (
                    contract.checkpoints.durable_ttl_seconds
                    if stopper.requested
                    else contract.checkpoints.periodic_ttl_seconds
                ),
                base_state(
                    contract_hash, stage, args.seed, epoch, cursor, cumulative_tokens
                ),
                state_path,
            )
        if stopper.requested:
            stop_reason = f"signal_{stopper.requested}"
            marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
            if marker:
                Path(marker).write_text(last_checkpoint["tinker_state_path"] + "\n")
            interrupted = {**last_checkpoint, "stop_reason": stop_reason}
            atomic_json(output_dir / "interrupted-receipt.json", interrupted)
            print(json.dumps(interrupted, indent=2, sort_keys=True))
            return 75

    last_checkpoint = await save_checkpoint(
        training_client,
        contract,
        stage,
        args.seed,
        completed_step,
        "final",
        contract.checkpoints.durable_ttl_seconds,
        base_state(contract_hash, stage, args.seed, epoch, cursor, cumulative_tokens),
        state_path,
    )
    archive = output_dir / "final-sampler-checkpoint.tar.gz"
    archive_sha = download_checkpoint(
        service_client, last_checkpoint["tinker_sampler_path"], archive
    )
    final = {
        **last_checkpoint,
        "stop_reason": stop_reason,
        "archive": archive.name,
        "archive_sha256": archive_sha,
    }
    atomic_json(output_dir / "final-receipt.json", final)
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--train-jsonl", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/tinker-runs"))
    parser.add_argument("--resume-state", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and args.train_jsonl is None:
        parser.error("--train-jsonl is required unless --dry-run is used")
    try:
        return asyncio.run(run(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
