from __future__ import annotations

import copy
import hashlib
import json

import pytest
import yaml

from harness.memory_trials.mnemon_actor import (
    ARM_IDS,
    analyze_rows,
    expected_case_keys,
    load_panel,
    render_prompt,
)
from harness.memory_trials.models import CompletionResult, JsonCompletionMemoryActor
from scripts.run_mnemon_actor_screen import run_screen
from scripts.validate_mnemon_actor_experiment import (
    DEFAULT_EXPERIMENT,
    MnemonActorExperimentError,
    validate_experiment_contract,
)

PANEL = (
    DEFAULT_EXPERIMENT.parents[2]
    / "data/results/mnemon-static-space-panel/2026-08-16-local-docker-v1/panel.json"
)
PANEL_SHA256 = "43a416c62be619de641aa60ecefc83ad0efdd605f7f13fd8821936704acacee5"
MODEL_REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
MODEL_ROOT = "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_live_mnemon_actor_contract_and_panel_pass() -> None:
    config = validate_experiment_contract()
    panel = load_panel(PANEL, expected_sha256=PANEL_SHA256)
    assert config["panel"]["tasks"] == 32
    assert len(expected_case_keys(panel)) == 128
    item = panel["items"][0]
    assert render_prompt(item, arm="lexical_router") == render_prompt(
        item, arm="oracle_space"
    )
    assert item["answer"] in render_prompt(item, arm="lexical_router")
    assert item["answer"] not in render_prompt(item, arm="no_memory")


def test_mnemon_actor_panel_rejects_inactive_space_leak(tmp_path) -> None:
    payload = json.loads(PANEL.read_text(encoding="utf-8"))
    slot = payload["items"][0]["arms"]["lexical_router"][0]
    slot["source_space"] = "DELTA" if payload["items"][0]["target_space"] != "DELTA" else "ALPHA"
    payload["items"][0]["arms"]["oracle_space"] = copy.deepcopy(
        payload["items"][0]["arms"]["lexical_router"]
    )
    path = tmp_path / "panel.json"
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(data)
    with pytest.raises(ValueError, match="inactive-space evidence"):
        load_panel(path, expected_sha256=_sha(data))


def test_mnemon_actor_analysis_applies_registered_kill_screen() -> None:
    panel = load_panel(PANEL, expected_sha256=PANEL_SHA256)
    rows = []
    for task_index, (task_id, arm) in enumerate(expected_case_keys(panel)):
        item_index = task_index // len(ARM_IDS)
        success = arm in {"lexical_router", "oracle_space"}
        rows.append(
            {
                "task_id": task_id,
                "arm": arm,
                "prediction": "answer" if success else "wrong",
                "exact_match": float(success),
                "token_f1": float(success),
                "receipt": {"prompt_tokens": 100 if arm == "no_memory" else 200},
                "aa_checked": arm == "lexical_router" and item_index < 8,
                "aa_text_exact": (
                    True if arm == "lexical_router" and item_index < 8 else None
                ),
            }
        )
    report = analyze_rows(rows, panel=panel)
    assert report["status"] == "MNEMON_STATIC_ROUTING_PASS"
    assert all(report["gates"].values())


def test_mnemon_actor_experiment_rejects_panel_digest_drift(tmp_path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["input"]["panel_sha256"] = "0" * 64
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MnemonActorExperimentError, match="input contract drifted"):
        validate_experiment_contract(path)


def test_mnemon_actor_experiment_accepts_only_hash_bound_external_panel(
    tmp_path,
) -> None:
    external = tmp_path / "panel.json"
    external.write_bytes(PANEL.read_bytes())
    assert (
        validate_experiment_contract(panel_artifact_path=external)["input"][
            "panel_sha256"
        ]
        == PANEL_SHA256
    )
    external.write_text("{}\n", encoding="utf-8")
    with pytest.raises(MnemonActorExperimentError, match="input artifact drifted"):
        validate_experiment_contract(panel_artifact_path=external)


def _fake_actor(panel, calls: list[str]) -> JsonCompletionMemoryActor:
    answer_by_question = {
        item["question"]: item["answer"] for item in panel["items"]
    }
    identity = f"hf:qwen3.5-4b@{MODEL_REVISION}#{MODEL_ROOT}"

    def complete(prompt: str) -> CompletionResult:
        calls.append(prompt)
        matches = [
            (question, answer)
            for question, answer in answer_by_question.items()
            if f"Question: {question}\nAccess-code:" in prompt
        ]
        if len(matches) != 1:
            raise AssertionError("fake Mnemon actor could not identify one task")
        _question, answer = matches[0]
        code_count = prompt.count("states access-code")
        text = answer if code_count == 1 else "UNKNOWN"
        return CompletionResult(
            text=text,
            receipt={
                "backend": "fake-transformers",
                "model_id": "qwen3.5-4b",
                "revision": MODEL_REVISION,
                "artifact_root_sha256": MODEL_ROOT,
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(text.split()),
                "do_sample": False,
                "deterministic_algorithms": True,
                "attention_implementation": "eager",
                "prompt_token_ids_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "completion_token_ids_sha256": hashlib.sha256(text.encode()).hexdigest(),
            },
        )

    return JsonCompletionMemoryActor(
        identity=identity,
        complete=complete,
        contract={
            "schema_version": 1,
            "identity": identity,
            "backend": "fake-transformers",
            "model_id": "qwen3.5-4b",
            "revision": MODEL_REVISION,
            "artifact_root_sha256": MODEL_ROOT,
            "max_new_tokens": 32,
            "dtype": "bfloat16",
            "use_chat_template": True,
            "do_sample": False,
            "deterministic_algorithms": True,
            "attention_implementation": "eager",
        },
    )


def test_mnemon_actor_screen_checkpoints_resumes_and_seals(tmp_path) -> None:
    panel = load_panel(PANEL, expected_sha256=PANEL_SHA256)
    calls: list[str] = []
    actor = _fake_actor(panel, calls)
    output = tmp_path / "run"
    partial = run_screen(
        config_path=DEFAULT_EXPERIMENT,
        panel_path=PANEL,
        expected_panel_sha256=PANEL_SHA256,
        output_dir=output,
        actor=actor,
        stop_requested=lambda: len(calls) >= 1,
    )
    assert partial["status"] == "CHECKPOINTED"
    assert partial["completed_cases"] == 1
    report = run_screen(
        config_path=DEFAULT_EXPERIMENT,
        panel_path=PANEL,
        expected_panel_sha256=PANEL_SHA256,
        output_dir=output,
        actor=actor,
    )
    assert report["status"] == "MNEMON_STATIC_ROUTING_PASS"
    assert report["completed_cases"] == 128
    assert all(report["gates"].values())
    assert run_screen(
        config_path=DEFAULT_EXPERIMENT,
        panel_path=PANEL,
        expected_panel_sha256=PANEL_SHA256,
        output_dir=output,
        actor=actor,
    ) == report
