from __future__ import annotations

import asyncio

import pytest

from harness.agent_loop import ToolCall
from harness.receipted_tool_runtime import ReceiptedSQLiteCanaryToolRuntime


def test_constraint_failure_is_an_observation_and_attempt_receipt() -> None:
    async def run():
        runtime = ReceiptedSQLiteCanaryToolRuntime()
        call = ToolCall("create_handoff_note", {"case_id": "COSMETIC-01"})
        first = await runtime.execute(call)
        second = await runtime.execute(call)
        return first, second, runtime.close_and_receipt()

    first, second, receipt = asyncio.run(run())
    assert first == {"created": True, "case_id": "COSMETIC-01"}
    assert second == {
        "ok": False,
        "error": {
            "code": "sqlite_constraint_violation",
            "tool": "create_handoff_note",
            "message": "tool mutation violated a uniqueness constraint",
            "retryable": False,
        },
    }
    assert receipt["attempt_count"] == 2
    assert receipt["success_count"] == 1
    assert receipt["error_count"] == 1
    assert [attempt["status"] for attempt in receipt["attempts"]] == [
        "success",
        "error",
    ]
    assert receipt["delegate_receipt"]["operation_count"] == 1


def test_unexpected_delegate_exception_propagates() -> None:
    class BrokenDelegate:
        async def execute(self, call):
            del call
            raise RuntimeError("unexpected transport failure")

        def close_and_receipt(self):
            return {"identity": "broken"}

    async def run():
        runtime = ReceiptedSQLiteCanaryToolRuntime(BrokenDelegate())
        with pytest.raises(RuntimeError, match="unexpected transport failure"):
            await runtime.execute(
                ToolCall("create_handoff_note", {"case_id": "COSMETIC-01"})
            )
        return runtime.close_and_receipt()

    receipt = asyncio.run(run())
    assert receipt["attempt_count"] == 0
    assert receipt["error_count"] == 0
