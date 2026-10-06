from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "infra/research/past-bench/model_transport_doctor.py"
SPEC = importlib.util.spec_from_file_location("past_model_transport_doctor", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _tool_call(name: str = "echo_probe", value: str = MODULE.PROBE_VALUE) -> SimpleNamespace:
    return SimpleNamespace(
        id="call-ignored",
        function=SimpleNamespace(name=name, arguments=json.dumps({"value": value})),
    )


def test_nonstream_probe_requires_native_exact_tool_call() -> None:
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="tool_calls",
                message=SimpleNamespace(content=None, tool_calls=[_tool_call()]),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=7),
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: response),
        )
    )
    report = MODULE._nonstream_probe(client, MODULE._request(MODULE.EXPECTED_MODEL))
    assert report["tool_calls"] == [
        {"name": "echo_probe", "arguments": {"value": MODULE.PROBE_VALUE}}
    ]


def test_nonstream_probe_rejects_text_markup_without_native_call() -> None:
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(
                    content="<tool_call><function=echo_probe></function></tool_call>",
                    tool_calls=None,
                ),
            )
        ],
        usage=None,
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: response),
        )
    )
    with pytest.raises(MODULE.ModelTransportError):
        MODULE._nonstream_probe(client, MODULE._request(MODULE.EXPECTED_MODEL))


def test_stream_probe_reassembles_native_delta() -> None:
    chunks = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason=None,
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                function=SimpleNamespace(
                                    name="echo_probe",
                                    arguments='{"value":"COTCODEC_',
                                ),
                            )
                        ],
                    ),
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                function=SimpleNamespace(
                                    name=None,
                                    arguments='QWEN_NATIVE_TOOL_PROBE_42"}',
                                ),
                            )
                        ],
                    ),
                )
            ]
        ),
    ]
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: iter(chunks)),
        )
    )
    report = MODULE._stream_probe(client, MODULE._request(MODULE.EXPECTED_MODEL))
    assert report["finish_reason"] == "tool_calls"
    assert report["tool_calls"][0]["arguments"]["value"] == MODULE.PROBE_VALUE
