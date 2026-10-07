"""CPU tests for scripts/run_open_weight_review.py (fake engine, fake vLLM modules)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import signal
import sys
import types
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import run_open_weight_review as owr
from scripts.submit_docker_research_job import validate_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEWER = PROJECT_ROOT / "experiments" / "reviewer"
SMOKE_SCHEMA = json.loads((REVIEWER / "smoke-schema.json").read_text(encoding="utf-8"))
GOOD = {
    "falsifiability_score": 7,
    "has_falsifier": True,
    "largest_defect": "Sorting is idempotent.",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeEngine:
    """Scripted replies, one list per generate call; records what it was asked."""

    def __init__(self, replies: list[list[str]], *, on_generate: Any = None) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []
        self.on_generate = on_generate

    def render(self, message: str, *, thinking: bool) -> owr.RenderedPrompt:
        text = f"<|im_start|>user\n{message}<|im_end|>\n<|im_start|>assistant\n"
        text += "<think>\n" if thinking else "<think>\n\n</think>\n\n"
        return owr.RenderedPrompt(text=text, token_ids=tuple(range(len(text.split()))))

    def generate(
        self, prompt: owr.RenderedPrompt, *, seeds: Any, max_tokens: int
    ) -> list[owr.Completion]:
        self.calls.append({"prompt": prompt, "seeds": list(seeds), "max_tokens": max_tokens})
        if self.on_generate is not None:
            self.on_generate()
        texts = self.replies.pop(0)
        return [
            owr.Completion(
                text=text,
                token_ids=tuple(ord(c) for c in text),
                finish_reason="length" if text.endswith("...") else "stop",
            )
            for text in texts
        ]

    def facts(self) -> dict[str, Any]:
        return {"vllm_version": "0.31.0", "chat_template_sha256": "c" * 64}


@pytest.fixture
def model(tmp_path: Path) -> dict[str, Path | str]:
    model_dir = tmp_path / "models" / "qwen3.6-35b-a3b"
    model_dir.mkdir(parents=True)
    files = {"config.json": b'{"model_type": "qwen3_5_moe"}', "tokenizer_config.json": b"{}"}
    for name, data in files.items():
        (model_dir / name).write_bytes(data)
    receipt = {
        "model_id": "qwen3.6-35b-a3b",
        "repo_id": "Qwen/Qwen3.6-35B-A3B",
        "backend": "huggingface",
        "mode": "full",
        "revision": "9" * 40,
        "artifact_root_sha256": "a" * 64,
        "publication_eligible": True,
        "total_bytes": 1,
        "files": [
            {"path": name, "bytes": len(data), "sha256": sha(data)} for name, data in files.items()
        ],
    }
    receipt_path = tmp_path / "receipts" / "qwen3.6-35b-a3b.json"
    receipt_path.parent.mkdir()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return {
        "dir": model_dir,
        "receipt": receipt_path,
        "receipt_sha256": sha(receipt_path.read_bytes()),
    }


@pytest.fixture
def bundle(tmp_path: Path) -> tuple[Path, str]:
    output = tmp_path / "request.json"
    code = owr.main(
        [
            "pack",
            "--prompt-file",
            str(REVIEWER / "smoke-prompt.txt"),
            "--schema-file",
            str(REVIEWER / "smoke-schema.json"),
            "--label",
            "smoke",
            "--output",
            str(output),
        ]
    )
    assert code == 0
    return output, sha(output.read_bytes())


@pytest.fixture(autouse=True)
def lane_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("COTCODEC_EXPECTED_GPUS", "COTCODEC_MODEL_ID", "COTCODEC_CHECKPOINT_MARKER"):
        monkeypatch.delenv(key, raising=False)


def run_args(model: dict[str, Any], bundle: tuple[Path, str], out: Path, *extra: str) -> list[str]:
    return [
        "run",
        "--evidence",
        str(bundle[0]),
        "--expected-evidence-sha256",
        bundle[1],
        "--model-dir",
        str(model["dir"]),
        "--model-receipt",
        str(model["receipt"]),
        "--expected-model-receipt-sha256",
        model["receipt_sha256"],
        "--output-dir",
        str(out),
        *extra,
    ]


def thought(answer: str) -> str:
    return f"Let me check the proposal.\n</think>\n\n{answer}"


# ---------------------------------------------------------------------------
# Schema subset
# ---------------------------------------------------------------------------


def test_reference_schemas_are_inside_the_supported_subset() -> None:
    for name in ("smoke-schema.json", "gauntlet-review-v1.schema.json"):
        owr.check_schema(json.loads((REVIEWER / name).read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        ({"type": "array"}, '"type": "object"'),
        ({"type": "object", "properties": {"a": {"format": "date"}}}, "unsupported"),
        ({"type": "object", "patternProperties": {}}, "unsupported"),
        ({"type": "object", "properties": {"a": {"$ref": "#/$defs/x"}}}, "names no $defs"),
        ({"type": "object", "properties": {"a": {"$ref": "other.json#/x"}}}, "local"),
        ({"type": "object", "properties": {"a": {"pattern": "("}}}, "does not compile"),
        ({"type": "object", "required": ["a", "a"]}, "distinct"),
        ({"type": "object", "properties": {"a": {"type": "decimal"}}}, "JSON types"),
        ({"type": "object", "properties": {"a": {"minimum": "1"}}}, "finite number"),
    ],
)
def test_schema_outside_the_subset_fails_closed(schema: dict[str, Any], message: str) -> None:
    with pytest.raises(owr.InputError, match=message.replace("$", r"\$")):
        owr.check_schema(schema)


def test_validator_reports_each_violation_with_a_path() -> None:
    assert owr.validate_instance(GOOD, SMOKE_SCHEMA) == []
    errors = owr.validate_instance(
        {"falsifiability_score": 11, "has_falsifier": 1, "extra": None}, SMOKE_SCHEMA
    )
    assert "$: missing required property 'largest_defect'" in errors
    assert "$: property 'extra' is not allowed" in errors
    assert "$.falsifiability_score: 11 is above the maximum 10" in errors
    assert "$.has_falsifier: expected boolean, got integer" in errors


def test_validator_keeps_json_semantics_for_booleans_and_integers() -> None:
    schema = {"type": "object", "properties": {"n": {"type": "integer"}, "e": {"enum": [1]}}}
    assert owr.validate_instance({"n": 3.0, "e": 1.0}, schema) == []
    assert owr.validate_instance({"n": True}, schema) == ["$.n: expected integer, got boolean"]
    assert owr.validate_instance({"e": True}, schema) == ["$.e: must be one of [1]"]
    unique = {"type": "object", "properties": {"u": {"uniqueItems": True}}}
    assert owr.validate_instance({"u": [1, True]}, unique) == []
    assert owr.validate_instance({"u": [1, 1.0]}, unique) == ["$.u: items are not unique"]


def test_validator_handles_refs_and_combinators() -> None:
    schema = json.loads((REVIEWER / "gauntlet-review-v1.schema.json").read_text(encoding="utf-8"))
    dimension = {"score": 8, "criterion": "MEETS", "evidence_anchor": "s2", "rationale": "ok"}
    review = {
        "candidate_id": "c-1",
        "dimensions": {
            name: dict(dimension) for name in schema["properties"]["dimensions"]["required"]
        },
        "uncapped_total": 80,
        "caps_applied": ["missing-independent-provider-distinct-review-89"],
        "total": 80,
        "verdict": "REVISE",
        "largest_defect": "No executable pilot.",
        "defects": [],
        "calibration_state": "NOT_CALIBRATED",
    }
    assert owr.validate_instance(review, schema) == []
    review["dimensions"]["evaluation_and_statistics"]["score"] = 12
    review["calibration_state"] = "CALIBRATED"
    errors = owr.validate_instance(review, schema)
    assert "$.dimensions.evaluation_and_statistics.score: 12 is above the maximum 10" in errors
    assert '$.calibration_state: must equal "NOT_CALIBRATED"' in errors
    choice = {
        "type": "object",
        "properties": {
            "a": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "o": {"oneOf": [{"type": "integer"}, {"type": "number"}]},
        },
    }
    assert owr.validate_instance({"a": None}, choice) == []
    assert owr.validate_instance({"a": 1}, choice) == ["$.a: matches none of the anyOf branches"]
    assert owr.validate_instance({"o": 1}, choice) == [
        "$.o: matches 2 oneOf branches, not exactly one"
    ]


# ---------------------------------------------------------------------------
# Reply parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "extraction"),
    [
        (json.dumps(GOOD), "bare"),
        ("Here it is:\n```json\n" + json.dumps(GOOD, indent=1) + "\n```\nDone.", "fenced"),
        ("My review: " + json.dumps(GOOD) + " -- end", "embedded"),
    ],
)
def test_parse_reply_accepts_bare_fenced_and_embedded_json(answer: str, extraction: str) -> None:
    value, how = owr.parse_reply(thought(answer), SMOKE_SCHEMA, thinking=True, finish_reason="stop")
    assert value == GOOD and how == extraction


@pytest.mark.parametrize(
    ("text", "thinking", "message"),
    [
        ("still thinking about it ...", True, "inside its reasoning block"),
        (thought(""), True, "no answer text"),
        (thought("no braces here"), True, "no JSON object"),
        (
            thought('{"falsifiability_score": 7, "falsifiability_score": 8}'),
            True,
            "repeats the key",
        ),
        (thought('{"falsifiability_score": NaN}'), True, "non-standard constant"),
        (thought('{"falsifiability_score": 7,'), True, "does not parse"),
        (json.dumps({**GOOD, "falsifiability_score": "7"}), False, "does not validate"),
    ],
)
def test_parse_reply_failures_say_why(text: str, thinking: bool, message: str) -> None:
    with pytest.raises(owr.ParseFailure, match=message):
        owr.parse_reply(text, SMOKE_SCHEMA, thinking=thinking, finish_reason="length")


def test_thinking_off_reply_is_parsed_whole() -> None:
    value, _ = owr.parse_reply(json.dumps(GOOD), SMOKE_SCHEMA, thinking=False, finish_reason="stop")
    assert value == GOOD


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


def test_pack_round_trips_and_binds_the_prompt_and_schema(bundle: tuple[Path, str]) -> None:
    path, digest = bundle
    request = owr.load_request_bundle(path, digest)
    prompt_bytes = (REVIEWER / "smoke-prompt.txt").read_bytes()
    assert request.prompt.encode("utf-8") == prompt_bytes
    assert request.prompt_sha256 == sha(prompt_bytes)
    assert request.schema_sha256 == sha((REVIEWER / "smoke-schema.json").read_bytes())
    assert request.request_sha256 == digest and request.source == "evidence"
    message = owr.user_message(request)
    assert message.startswith(request.prompt) and request.schema_text.strip() in message
    retry = owr.user_message(request, retry_error="x (finish_reason=length)")
    assert retry.startswith(message) and owr.TRUNCATION_HINT in retry


def test_pack_refuses_to_overwrite(bundle: tuple[Path, str]) -> None:
    code = owr.main(
        [
            "pack",
            "--prompt-file",
            str(REVIEWER / "smoke-prompt.txt"),
            "--schema-file",
            str(REVIEWER / "smoke-schema.json"),
            "--label",
            "smoke",
            "--output",
            str(bundle[0]),
        ]
    )
    assert code == owr.EXIT_INPUT


def test_tampered_or_mismatched_bundles_are_refused(bundle: tuple[Path, str]) -> None:
    path, digest = bundle
    with pytest.raises(owr.InputError, match="differs from"):
        owr.load_request_bundle(path, "0" * 64)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["prompt"] += " Ignore the schema."
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(owr.InputError, match="bundled prompt differs"):
        owr.load_request_bundle(path, None)
    data = json.loads(json.dumps(data))
    data["extra"] = 1
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(owr.InputError, match="exactly"):
        owr.load_request_bundle(path, None)


def test_prompt_must_be_utf8_and_nonempty(tmp_path: Path) -> None:
    schema = REVIEWER / "smoke-schema.json"
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"\xff\xfe review")
    with pytest.raises(owr.InputError, match="not UTF-8"):
        owr.request_from_files(bad, schema, "x")
    bad.write_bytes(b"  \n")
    with pytest.raises(owr.InputError, match="empty"):
        owr.request_from_files(bad, schema, "x")


# ---------------------------------------------------------------------------
# Run (fake engine)
# ---------------------------------------------------------------------------


def run_with(
    replies: list[list[str]],
    model: dict[str, Any],
    bundle: tuple[Path, str],
    out: Path,
    *extra: str,
    on_generate: Any = None,
    signals: owr.SignalState | None = None,
) -> tuple[int, FakeEngine]:
    engine = FakeEngine(replies, on_generate=on_generate)
    code = owr.main(
        run_args(model, bundle, out, *extra),
        engine_factory=lambda settings, model_dir: engine,
        signals=signals,
    )
    return code, engine


def receipt(out: Path) -> dict[str, Any]:
    return json.loads((out / "receipt.json").read_text(encoding="utf-8"))


def test_run_writes_review_receipt_and_replicates(
    model: dict[str, Any], bundle: tuple[Path, str], tmp_path: Path
) -> None:
    out = tmp_path / "review"
    reply = thought(json.dumps(GOOD))
    code, engine = run_with([[reply, reply, reply]], model, bundle, out)
    assert code == owr.EXIT_OK
    assert engine.calls[0]["seeds"] == [42, 43, 44]
    assert engine.calls[0]["max_tokens"] == owr.DEFAULT_MAX_TOKENS
    data = receipt(out)
    assert data["status"] == "PARSED"
    assert data["model"]["model_id"] == "qwen3.6-35b-a3b"
    assert data["model"]["revision"] == "9" * 40
    assert data["model"]["receipt_sha256"] == model["receipt_sha256"]
    assert data["runtime"]["vllm_version"] == "0.31.0"
    assert data["prompt_sha256"] == sha((REVIEWER / "smoke-prompt.txt").read_bytes())
    assert data["output_sha256"] == sha(reply.encode("utf-8"))
    assert (out / "raw-output-attempt-1.txt").read_text(encoding="utf-8") == reply
    assert json.loads((out / "parsed.json").read_text(encoding="utf-8")) == GOOD
    assert data["parsed_sha256"] == sha((out / "parsed.json").read_bytes())
    assert data["engine"]["temperature"] == 0.0 and data["engine"]["seeds"] == [42, 43, 44]
    assert data["llm_kwargs"]["language_model_only"] is True
    assert data["llm_kwargs"]["seed"] == 42
    assert data["replicates_identical"] is True
    assert [row["seed"] for row in data["replicates"]] == [43, 44]
    assert data["attempts"][0]["parse"] == {"ok": True, "extraction": "bare"}
    assert (out / "prompt.txt").read_bytes() == (REVIEWER / "smoke-prompt.txt").read_bytes()
    report = owr.verify_output(out)
    assert report["ok"] and report["status"] == "PARSED"
    assert report["receipt_sha256"] == sha((out / "receipt.json").read_bytes())


def test_bad_primary_reply_gets_one_retry_with_the_error_appended(
    model: dict[str, Any], bundle: tuple[Path, str], tmp_path: Path
) -> None:
    out = tmp_path / "review"
    bad = thought('{"falsifiability_score": "seven"}')
    good = thought(json.dumps(GOOD))
    code, engine = run_with([[bad, bad, good], [good]], model, bundle, out)
    assert code == owr.EXIT_OK
    assert engine.calls[1]["seeds"] == [42]
    data = receipt(out)
    assert len(data["attempts"]) == 2
    assert data["attempts"][0]["parse"]["ok"] is False
    retry_message = (out / "user-message-attempt-2.txt").read_text(encoding="utf-8")
    assert "could not be used: the JSON does not validate" in retry_message
    assert "$.falsifiability_score: expected integer, got string" in retry_message
    assert data["output_sha256"] == sha(good.encode("utf-8"))
    assert data["replicates_identical"] is False


def test_two_failures_end_parse_failed_without_parsed_json(
    model: dict[str, Any], bundle: tuple[Path, str], tmp_path: Path
) -> None:
    out = tmp_path / "review"
    truncated = "I keep reasoning ..."
    code, engine = run_with([[truncated] * 3, [truncated]], model, bundle, out)
    assert code == owr.EXIT_PARSE
    assert len(engine.calls) == 2
    data = receipt(out)
    assert data["status"] == "PARSE_FAILED"
    assert "finish_reason=length" in data["error"]
    assert not (out / "parsed.json").exists()
    assert owr.TRUNCATION_HINT in (out / "user-message-attempt-2.txt").read_text(encoding="utf-8")
    assert owr.verify_output(out)["ok"]


def test_signal_while_generating_writes_receipt_then_marker(
    model: dict[str, Any],
    bundle: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "checkpoint.ready"
    monkeypatch.setenv("COTCODEC_CHECKPOINT_MARKER", str(marker))
    out = tmp_path / "review"
    signals = owr.SignalState()
    before = signal.getsignal(signal.SIGUSR1)
    code, _ = run_with(
        [[thought(json.dumps(GOOD))] * 3],
        model,
        bundle,
        out,
        on_generate=lambda: signals.handle(signal.SIGUSR1, None),
        signals=signals,
    )
    assert code == owr.EXIT_SIGNAL
    assert signal.getsignal(signal.SIGUSR1) is before
    data = receipt(out)
    assert data["status"] == "INTERRUPTED" and data["signals_received"] == ["SIGUSR1"]
    lines = marker.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "trigger=SIGUSR1"
    assert f"receipt_sha256={sha((out / 'receipt.json').read_bytes())}" in lines


def test_engine_failure_is_recorded(
    model: dict[str, Any], bundle: tuple[Path, str], tmp_path: Path
) -> None:
    out = tmp_path / "review"

    def explode(settings: Any, model_dir: Any) -> Any:
        raise RuntimeError("CUDA out of memory")

    code = owr.main(run_args(model, bundle, out), engine_factory=explode)
    assert code == owr.EXIT_ENGINE
    assert receipt(out)["status"] == "ENGINE_FAILED"
    assert "CUDA out of memory" in receipt(out)["error"]


def test_prompt_longer_than_the_context_is_refused_before_generating(
    model: dict[str, Any], bundle: tuple[Path, str], tmp_path: Path
) -> None:
    out = tmp_path / "review"
    code, engine = run_with([], model, bundle, out, "--max-model-len", "120", "--max-tokens", "100")
    assert code == owr.EXIT_INPUT and engine.calls == []
    assert receipt(out)["status"] == "INPUT_ERROR"


def test_model_receipt_and_lane_bindings_are_checked(
    model: dict[str, Any],
    bundle: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    good = model["receipt_sha256"]
    model["receipt_sha256"] = "0" * 64
    code, _ = run_with([], model, bundle, tmp_path / "a")
    assert code == owr.EXIT_INPUT and not (tmp_path / "a").exists()
    model["receipt_sha256"] = good
    (model["dir"] / "config.json").write_text("{}", encoding="utf-8")
    code, _ = run_with([], model, bundle, tmp_path / "b")
    assert code == owr.EXIT_INPUT and not (tmp_path / "b").exists()
    (model["dir"] / "config.json").write_bytes(b'{"model_type": "qwen3_5_moe"}')
    monkeypatch.setenv("COTCODEC_EXPECTED_GPUS", "2")
    code, _ = run_with([], model, bundle, tmp_path / "c")
    assert code == owr.EXIT_INPUT
    monkeypatch.setenv("COTCODEC_EXPECTED_GPUS", "1")
    monkeypatch.setenv("COTCODEC_MODEL_ID", "qwen3.5-9b")
    code, _ = run_with([], model, bundle, tmp_path / "d")
    assert code == owr.EXIT_INPUT


def test_existing_output_dir_is_never_reused(
    model: dict[str, Any], bundle: tuple[Path, str], tmp_path: Path
) -> None:
    out = tmp_path / "review"
    out.mkdir()
    code, engine = run_with([], model, bundle, out)
    assert code == owr.EXIT_INPUT and engine.calls == []


def test_verify_detects_tampering(
    model: dict[str, Any], bundle: tuple[Path, str], tmp_path: Path
) -> None:
    out = tmp_path / "review"
    reply = thought(json.dumps(GOOD))
    run_with([[reply] * 3], model, bundle, out)
    (out / "parsed.json").write_text("{}\n", encoding="utf-8")
    report = owr.verify_output(out)
    assert not report["ok"]
    assert "parsed.json is missing or differs from its SHA-256" in report["problems"]


def test_direct_prompt_and_schema_files(model: dict[str, Any], tmp_path: Path) -> None:
    out = tmp_path / "review"
    engine = FakeEngine([[json.dumps(GOOD)]])
    code = owr.main(
        [
            "run",
            "--prompt-file",
            str(REVIEWER / "smoke-prompt.txt"),
            "--schema-file",
            str(REVIEWER / "smoke-schema.json"),
            "--model-dir",
            str(model["dir"]),
            "--model-receipt",
            str(model["receipt"]),
            "--expected-model-receipt-sha256",
            model["receipt_sha256"],
            "--output-dir",
            str(out),
            "--thinking",
            "off",
            "--seeds",
            "42",
        ],
        engine_factory=lambda settings, model_dir: engine,
    )
    assert code == owr.EXIT_OK
    data = receipt(out)
    assert data["request"]["source"] == "files" and data["replicates"] == []
    assert "</think>" in engine.calls[0]["prompt"].text


# ---------------------------------------------------------------------------
# vLLM adapter and doctor (fake modules)
# ---------------------------------------------------------------------------


def doctor_llm_class(params: set[str]) -> type:
    """An LLM class whose public signature names exactly ``params`` (plus **kwargs)."""

    namespace: dict[str, Any] = {}
    arguments = ", ".join(f"{name}=None" for name in sorted(params))
    exec(f"def __init__(self, model, *, {arguments}, **kwargs):\n    pass\n", namespace)  # noqa: S102
    return type("LLM", (), {"__init__": namespace["__init__"]})


def install_fake_vllm(monkeypatch: pytest.MonkeyPatch, *, llm_params: set[str]) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    class SamplingParams:
        def __init__(self, *, temperature: float, max_tokens: int, seed: int, n: int) -> None:
            self.temperature, self.max_tokens, self.seed, self.n = temperature, max_tokens, seed, n

    @dataclasses.dataclass
    class EngineArgs:
        language_model_only: bool = False
        max_num_seqs: int = 256
        max_model_len: int | None = None

    class RecordingLLM:
        def __init__(self, **kwargs: Any) -> None:
            seen["llm_kwargs"] = kwargs

        def generate(self, prompts: Any, params: Any, use_tqdm: bool) -> Any:
            seen["generate"] = (prompts, params, use_tqdm)
            return [
                types.SimpleNamespace(
                    outputs=[
                        types.SimpleNamespace(
                            text=f"reply {p.seed}", token_ids=[1, 2], finish_reason="stop"
                        )
                    ]
                )
                for p in params
            ]

    class Tokenizer:
        chat_template = "{{ messages }}"

        def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
            seen["template_kwargs"] = kwargs
            return f"<user>{messages[0]['content']}</user><think>\n"

        def encode(self, text: str, add_special_tokens: bool) -> list[int]:
            seen["add_special_tokens"] = add_special_tokens
            return [len(word) for word in text.split()]

    vllm = types.ModuleType("vllm")
    vllm.__version__ = "0.31.0"
    vllm.LLM = doctor_llm_class(llm_params)
    vllm.SamplingParams = SamplingParams
    inputs = types.ModuleType("vllm.inputs")
    inputs.TokensPrompt = dict
    arg_utils = types.ModuleType("vllm.engine.arg_utils")
    arg_utils.EngineArgs = EngineArgs
    transformers = types.ModuleType("transformers")
    transformers.__version__ = "4.57.1"
    transformers.AutoTokenizer = types.SimpleNamespace(
        from_pretrained=lambda path, trust_remote_code: Tokenizer()
    )
    torch = types.ModuleType("torch")
    torch.__version__ = "2.13.0"
    for name, module in {
        "vllm": vllm,
        "vllm.inputs": inputs,
        "vllm.engine": types.ModuleType("vllm.engine"),
        "vllm.engine.arg_utils": arg_utils,
        "transformers": transformers,
        "torch": torch,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    seen["recording_llm"] = RecordingLLM
    return seen


EXPLICIT_LLM_PARAMS = {
    "tokenizer",
    "trust_remote_code",
    "dtype",
    "tensor_parallel_size",
    "gpu_memory_utilization",
    "enforce_eager",
    "seed",
    "disable_log_stats",
}


def test_doctor_passes_when_vllm_accepts_every_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_vllm(monkeypatch, llm_params=EXPLICIT_LLM_PARAMS)
    report = owr.doctor(owr.EngineSettings())
    assert report["pass"] is True and report["missing_llm_arguments"] == []


def test_doctor_fails_on_an_unknown_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_vllm(monkeypatch, llm_params=EXPLICIT_LLM_PARAMS - {"enforce_eager"})
    report = owr.doctor(owr.EngineSettings())
    assert report["pass"] is False and report["missing_llm_arguments"] == ["enforce_eager"]


def test_vllm_adapter_renders_with_the_chat_template_and_maps_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = install_fake_vllm(monkeypatch, llm_params=EXPLICIT_LLM_PARAMS)
    monkeypatch.setattr(sys.modules["vllm"], "LLM", seen["recording_llm"])
    settings = owr.EngineSettings(seeds=(42, 43), max_tokens=64, max_model_len=4096)
    engine = owr.VllmReviewEngine(settings, tmp_path / "qwen3.5-9b")
    assert seen["llm_kwargs"]["seed"] == 42 and seen["llm_kwargs"]["language_model_only"]
    rendered = engine.render("Review this.", thinking=True)
    assert seen["template_kwargs"] == {
        "tokenize": False,
        "add_generation_prompt": True,
        "enable_thinking": True,
    }
    assert seen["add_special_tokens"] is False
    completions = engine.generate(rendered, seeds=[42, 43], max_tokens=64)
    prompts, params, use_tqdm = seen["generate"]
    assert [p.seed for p in params] == [42, 43] and use_tqdm is False
    assert all(p.temperature == 0.0 and p.max_tokens == 64 for p in params)
    assert prompts[0]["prompt_token_ids"] == list(rendered.token_ids)
    assert [c.text for c in completions] == ["reply 42", "reply 43"]
    monkeypatch.setattr(owr, "gpu_names", lambda: ["NVIDIA H100 80GB HBM3"])
    facts = engine.facts()
    assert facts["vllm_version"] == "0.31.0" and facts["gpu_names"] == ["NVIDIA H100 80GB HBM3"]


# ---------------------------------------------------------------------------
# Lane manifest
# ---------------------------------------------------------------------------

BUILD = {
    "image_id": "sha256:" + "b" * 64,
    "git_sha": "1" * 40,
    "source_sha256": "c" * 64,
    "variant": "cu129",
    "vllm_version": "0.31.0",
}
MODEL_BINDING = {
    "cache_host_path": "/home/kevin/cotcodec-runs/hf-cache",
    "model_id": "qwen3.6-35b-a3b",
    "revision": "995ad96eacd98c81ed38be0c5b274b04031597b0",
    "receipt_sha256": "18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9",
    "artifact_root_sha256": "8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b",
}


def manifest_for(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "name": "owr-k1v2-wave1",
        "build": BUILD,
        "request_host_path": "/home/kevin/cotcodec-runs/stage0/open-weight-reviewer/inputs/r.json",
        "request_sha256": "d" * 64,
        "request_size": 1234,
        "request_revision": "1" * 40,
        "request_license": owr.DEFAULT_REQUEST_LICENSE,
        "model": MODEL_BINDING,
        "run_root": "/home/kevin/cotcodec-runs/stage0/open-weight-reviewer/runs/k1v2-wave1",
        "minutes": 20,
        "cpus": 16,
        "memory_gb": None,
        "settings": owr.EngineSettings(),
    }
    arguments.update(overrides)
    return owr.render_manifest(**arguments)


def test_rendered_manifest_passes_the_lane_validator() -> None:
    manifest = manifest_for()
    validated = validate_manifest(dict(manifest), verify_claim_files=False)
    assert validated["gpus"] == 1 and validated["memory_gb"] == 160
    assert validated["seed_binding"] == {"flag": "--seeds"}
    assert validated["container_profile"] == "vllm"
    assert validated["study_artifact"]["container_path"] == owr.LANE_EVIDENCE_PATH
    command = manifest["command"]
    assert command[:3] == ["python", "scripts/run_open_weight_review.py", "run"]
    assert command[-4:] == ["--seeds", "42", "43", "44"]
    assert manifest["budget"]["max_gpu_hours"] == pytest.approx(20 / 60, abs=2e-6)
    parsed = owr.build_parser().parse_args(command[2:])
    assert parsed.expected_model_receipt_sha256 == MODEL_BINDING["receipt_sha256"]
    assert parsed.model_dir == Path("/model-cache/cotcodec-models/qwen3.6-35b-a3b")


def test_manifest_gpus_follow_tensor_parallel_size_and_eager_flag() -> None:
    settings = owr.EngineSettings(tensor_parallel_size=2, enforce_eager=True, thinking=False)
    manifest = manifest_for(settings=settings, minutes=7)
    validated = validate_manifest(dict(manifest), verify_claim_files=False)
    assert validated["gpus"] == 2
    assert validated["max_gpu_hours"] >= 2 * 7 / 60
    assert "--enforce-eager" in manifest["command"]
    assert manifest["command"][manifest["command"].index("--thinking") + 1] == "off"
    yaml.safe_dump(manifest)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"name": "Bad_Name"}, "kebab-case"),
        ({"request_revision": "main"}, "40-hex"),
        ({"request_license": "has space"}, "license"),
    ],
)
def test_manifest_rejects_unsafe_fields(override: dict[str, Any], message: str) -> None:
    with pytest.raises(owr.InputError, match=message):
        manifest_for(**override)


def test_settings_bounds() -> None:
    with pytest.raises(owr.InputError):
        owr.EngineSettings(seeds=(42, 42))
    with pytest.raises(owr.InputError):
        owr.EngineSettings(max_tokens=70000, max_model_len=65536)
    with pytest.raises(owr.InputError):
        owr.EngineSettings(tensor_parallel_size=9)
    assert owr.EngineSettings().primary_seed == 42


def test_plan_prints_settings(bundle: tuple[Path, str], capsys: pytest.CaptureFixture[str]) -> None:
    code = owr.main(["plan", "--evidence", str(bundle[0]), "--expected-evidence-sha256", bundle[1]])
    assert code == owr.EXIT_OK
    plan = json.loads(capsys.readouterr().out)
    assert plan["sampling"][0] == {"temperature": 0.0, "max_tokens": 16384, "seed": 42, "n": 1}
    assert plan["llm_kwargs"]["max_num_seqs"] == owr.MAX_NUM_SEQS
