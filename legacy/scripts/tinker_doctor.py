#!/usr/bin/env python3
"""Validate a Tinker experiment and optionally attest live service capabilities."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.training.tinker_backend import (  # noqa: E402
    TinkerContractError,
    load_tinker_contract,
)


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    path = args.contract.resolve()
    try:
        contract = load_tinker_contract(path)
        installed_sdk = importlib.metadata.version("tinker")
    except (TinkerContractError, importlib.metadata.PackageNotFoundError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if installed_sdk != contract.execution.sdk_version:
        print(
            f"FAIL: installed tinker {installed_sdk} != contract "
            f"{contract.execution.sdk_version}",
            file=sys.stderr,
        )
        return 2

    receipt: dict[str, Any] = {
        "schema_version": 1,
        "status": "CONTRACT_VALID",
        "contract": str(path),
        "contract_sha256": sha256_file(path),
        "sdk_version": installed_sdk,
        "declared_cost_ceiling_usd": round(contract.cost_ceiling_usd(), 6),
        "budget_usd": contract.budget.max_usd,
        "models": [stage.tinker_id for stage in contract.stages],
        "online_checked": False,
    }

    if args.online:
        if not os.environ.get(contract.execution.secret_env):
            print(
                f"FAIL: {contract.execution.secret_env} is required for --online; "
                "the key was not read or printed",
                file=sys.stderr,
            )
            return 2
        import tinker

        client = tinker.ServiceClient(
            user_metadata={"project": "cotcodec", "contract": contract.name}
        )
        capabilities = client.get_server_capabilities()
        supported = {
            item.model_name: item.max_context_length
            for item in capabilities.supported_models
            if item.model_name is not None
        }
        missing = sorted(set(receipt["models"]) - set(supported))
        if missing:
            print(f"FAIL: Tinker does not advertise configured models: {missing}", file=sys.stderr)
            return 2
        receipt.update(
            {
                "status": "ONLINE_CAPABILITIES_VALID",
                "online_checked": True,
                "supported_models": {
                    model: {"max_context_length": supported[model]}
                    for model in receipt["models"]
                },
            }
        )

    if args.output:
        atomic_json(args.output.resolve(), receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
