#!/usr/bin/env python3
"""Run the pinned LongMemEval GPT-4o judge over a sealed packet.

The response journal is the checkpoint: every case is written atomically before
the next provider call.  Resume revalidates the packet, contract, and every
completed response and never resubmits a finished case.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.longmemeval_judge import (  # noqa: E402
    LongMemEvalJudgeCase,
    LongMemEvalJudgeContract,
    LongMemEvalJudgeError,
    LongMemEvalJudgment,
    atomic_write,
    official_judge_request_payload,
    seal_judgment,
    summarize_longmemeval_judgments,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LongMemEvalJudgeError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise LongMemEvalJudgeError(f"JSON artifact must be an object: {path}")
    return value


def load_judge_packet(
    packet_root: Path,
) -> tuple[dict[str, Any], tuple[LongMemEvalJudgeCase, ...], LongMemEvalJudgeContract]:
    """Hash-verify and load one immutable packet."""

    packet_root = packet_root.resolve()
    manifest_path = packet_root / "manifest.json"
    manifest = _json_object(manifest_path)
    if manifest.get("status") != "PREPARED_OFFICIAL_PROMPT_PACKET":
        raise LongMemEvalJudgeError("packet is not prepared for official judgment")
    if manifest.get("preparation_mode") not in {"transport-panel", "full-benchmark"}:
        raise LongMemEvalJudgeError("packet omitted its registered preparation mode")
    experiment_sha256 = manifest.get("experiment_sha256")
    if not isinstance(experiment_sha256, str) or len(experiment_sha256) != 64:
        raise LongMemEvalJudgeError("packet omitted its experiment digest")
    expected_cases = manifest.get("files", {}).get("judge-cases.jsonl")
    cases_path = packet_root / "judge-cases.jsonl"
    if not isinstance(expected_cases, str) or _sha256_file(cases_path) != expected_cases:
        raise LongMemEvalJudgeError("judge case file failed hash verification")
    try:
        cases = tuple(
            LongMemEvalJudgeCase.model_validate(json.loads(line))
            for line in cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        contract = LongMemEvalJudgeContract.model_validate(manifest["judge_contract"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise LongMemEvalJudgeError("packet contains an invalid case or contract") from exc
    if len(cases) != manifest.get("case_count") or not cases:
        raise LongMemEvalJudgeError("packet case count is incomplete")
    if [case.sequence for case in cases] != list(range(1, len(cases) + 1)):
        raise LongMemEvalJudgeError("packet case sequence is not contiguous")
    if sha256_text(canonical_json([case.case_sha256 for case in cases])) != manifest.get(
        "case_root_sha256"
    ):
        raise LongMemEvalJudgeError("packet case root differs from its manifest")
    if contract.contract_sha256 != manifest.get("judge_contract_sha256"):
        raise LongMemEvalJudgeError("packet judge contract digest mismatch")
    return manifest, cases, contract


def _response_json(response: Any) -> str:
    if hasattr(response, "model_dump_json"):
        return response.model_dump_json()
    if isinstance(response, dict):
        return canonical_json(response)
    raise LongMemEvalJudgeError("provider response is not serializable")


def _response_fields(response: Any) -> tuple[str, str, str | None, int, int]:
    payload = json.loads(_response_json(response))
    try:
        content = payload["choices"][0]["message"]["content"]
        response_id = payload["id"]
        model = payload["model"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LongMemEvalJudgeError("provider response lacks chat-completion fields") from exc
    if not all(isinstance(value, str) and value for value in (content, response_id, model)):
        raise LongMemEvalJudgeError("provider response has invalid text, ID, or model")
    usage = payload.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    if not all(
        isinstance(value, int) and value >= 0
        for value in (prompt_tokens, completion_tokens)
    ):
        raise LongMemEvalJudgeError("provider response lacks nonnegative token counts")
    fingerprint = payload.get("system_fingerprint")
    if fingerprint is not None and not isinstance(fingerprint, str):
        raise LongMemEvalJudgeError("provider system fingerprint must be text or null")
    return content, response_id, fingerprint, prompt_tokens, completion_tokens


def _preflight(client: Any, requested_model: str) -> dict[str, Any]:
    response = client.models.list()
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    if not isinstance(data, (list, tuple)):
        raise LongMemEvalJudgeError("OpenAI model-list response has no data list")
    model_ids = sorted(
        {
            model_id
            for item in data
            if isinstance(
                (
                    model_id := item.get("id")
                    if isinstance(item, dict)
                    else getattr(item, "id", None)
                ),
                str,
            )
        }
    )
    if requested_model not in model_ids:
        raise LongMemEvalJudgeError("official judge model is absent from provider preflight")
    return {
        "schema_version": "1.0",
        "provider": "openai",
        "endpoint": "/models",
        "requested_model": requested_model,
        "available": True,
        "listed_model_count": len(model_ids),
        "model_ids_sha256": sha256_text(canonical_json(model_ids)),
    }


def run_official_judge(
    packet_root: Path,
    output_root: Path,
    *,
    client: Any,
    resume: bool = False,
) -> dict[str, Any]:
    """Execute or resume the exact official judge contract."""

    manifest, cases, contract = load_judge_packet(packet_root)
    installed_sdk = importlib.metadata.version("openai")
    if installed_sdk != contract.sdk_version:
        raise LongMemEvalJudgeError("installed OpenAI SDK differs from packet contract")
    packet_manifest_sha256 = _sha256_file(packet_root.resolve() / "manifest.json")
    output_root = output_root.resolve()
    run_contract = {
        "schema_version": "1.0",
        "packet_manifest_sha256": packet_manifest_sha256,
        "case_root_sha256": manifest["case_root_sha256"],
        "case_count": len(cases),
        "judge_contract_sha256": contract.contract_sha256,
    }
    contract_path = output_root / "run-contract.json"
    responses_root = output_root / "responses"
    if output_root.exists():
        if not resume:
            raise LongMemEvalJudgeError(f"judge output already exists: {output_root}")
        if _json_object(contract_path) != run_contract:
            raise LongMemEvalJudgeError("judge resume contract changed")
    else:
        output_root.mkdir(parents=True)
        responses_root.mkdir()
        atomic_write(
            contract_path,
            (json.dumps(run_contract, indent=2, sort_keys=True) + "\n").encode(),
        )
    responses_root.mkdir(exist_ok=True)
    completed_manifest_path = output_root / "bundle" / "manifest.json"
    if completed_manifest_path.is_file():
        completed = _json_object(completed_manifest_path)
        if (
            completed.get("packet_manifest_sha256") != packet_manifest_sha256
            or completed.get("judge_contract_sha256") != contract.contract_sha256
            or completed.get("case_count") != len(cases)
        ):
            raise LongMemEvalJudgeError("completed judge bundle changed contract")
        files = completed.get("files")
        if not isinstance(files, dict) or any(
            not isinstance(expected, str)
            or _sha256_file(completed_manifest_path.parent / name) != expected
            for name, expected in files.items()
        ):
            raise LongMemEvalJudgeError("completed judge bundle failed hash verification")
        return completed
    preflight_path = output_root / "preflight.json"
    if not preflight_path.exists():
        preflight = _preflight(client, contract.requested_model)
        atomic_write(
            preflight_path,
            (json.dumps(preflight, indent=2, sort_keys=True) + "\n").encode(),
        )
    elif not _json_object(preflight_path).get("available"):
        raise LongMemEvalJudgeError("stored judge preflight did not pass")

    expected_response_names = [
        f"{case.sequence:08d}-{case.trial_id}.json" for case in cases
    ]
    existing_response_names = sorted(path.name for path in responses_root.glob("*.json"))
    if existing_response_names != expected_response_names[: len(existing_response_names)]:
        raise LongMemEvalJudgeError(
            "judge response journal is not a contiguous case prefix"
        )

    judgments: list[LongMemEvalJudgment] = []
    for case in cases:
        path = responses_root / f"{case.sequence:08d}-{case.trial_id}.json"
        if path.exists():
            judgment = LongMemEvalJudgment.model_validate(_json_object(path))
            if judgment.case_sha256 != case.case_sha256:
                raise LongMemEvalJudgeError("resumed judgment binds a different case")
            judgments.append(judgment)
            continue
        request = official_judge_request_payload(case, contract)
        response = client.chat.completions.create(**request)
        provider_response_json = _response_json(response)
        content, response_id, fingerprint, input_tokens, output_tokens = (
            _response_fields(response)
        )
        if json.loads(provider_response_json).get("model") != contract.requested_model:
            raise LongMemEvalJudgeError("provider returned a different judge model")
        judgment = seal_judgment(
            {
                "schema_version": "1.0",
                "sequence": case.sequence,
                "case_sha256": case.case_sha256,
                "judge_contract_sha256": contract.contract_sha256,
                "judge_model_id": contract.requested_model,
                "openai_sdk_version": contract.sdk_version,
                "provider_api_version": contract.provider_api_version,
                "request_sha256": sha256_text(canonical_json(request)),
                "provider_response_json": provider_response_json,
                "provider_response_id": response_id,
                "system_fingerprint": fingerprint,
                "raw_response": content,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )
        atomic_write(
            path,
            (
                json.dumps(
                    judgment.model_dump(mode="json"), indent=2, sort_keys=True
                )
                + "\n"
            ).encode(),
        )
        judgments.append(judgment)

    report = summarize_longmemeval_judgments(cases, judgments, contract)
    bundle_root = output_root / "bundle"
    if bundle_root.exists():
        raise LongMemEvalJudgeError("final judge bundle already exists")
    bundle_root.mkdir()
    judgment_bytes = "".join(
        canonical_json(item.model_dump(mode="json")) + "\n" for item in judgments
    ).encode()
    judgments_sha256 = atomic_write(bundle_root / "judgments.jsonl", judgment_bytes)
    report_bytes = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    report_sha256 = atomic_write(bundle_root / "score-report.json", report_bytes)
    final_manifest = {
        "schema_version": "1.0",
        "status": report["status"],
        "scientific_result": False,
        "packet_manifest_sha256": packet_manifest_sha256,
        "judge_contract_sha256": contract.contract_sha256,
        "case_count": len(cases),
        "preflight_sha256": _sha256_file(preflight_path),
        "judgment_root_sha256": report["judgment_root_sha256"],
        "files": {
            "judgments.jsonl": judgments_sha256,
            "score-report.json": report_sha256,
        },
    }
    atomic_write(
        bundle_root / "manifest.json",
        (json.dumps(final_manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    return final_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args()
    secret = os.environ.get(args.api_key_env)
    if not secret:
        raise SystemExit(f"{args.api_key_env} is not set")
    from openai import OpenAI

    result = run_official_judge(
        args.packet_root,
        args.output_root,
        client=OpenAI(api_key=secret),
        resume=args.resume,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
