from __future__ import annotations

from types import SimpleNamespace

from scripts.run_openai_daybreak_blue_doctor import (
    ACCESS_PROGRAM,
    MODEL_ID,
    build_request,
    run_doctor,
)


class FakeDaybreakClient:
    def __init__(self, *, selected_program: str = ACCESS_PROGRAM) -> None:
        self.models = self
        self.responses = self
        self.selected_program = selected_program
        self.request = None

    def list(self):
        return SimpleNamespace(data=[SimpleNamespace(id=MODEL_ID)])

    def create(self, **request):
        self.request = request
        return SimpleNamespace(
            id="resp-daybreak-doctor",
            model=MODEL_ID,
            access_programs=SimpleNamespace(cyber=self.selected_program),
            output_text=(
                '{"status":"defensive_scope_acknowledged",'
                '"action_boundary":"authorized_test_environment_only"}'
            ),
            usage=SimpleNamespace(
                input_tokens=20,
                output_tokens=8,
                total_tokens=28,
                input_tokens_details=SimpleNamespace(cached_tokens=0),
            ),
        )


class FakeAccessError(Exception):
    status_code = 403
    code = "access_program_not_enabled"
    body = {"error": {"code": code}}


class FailingClient(FakeDaybreakClient):
    def create(self, **request):
        raise FakeAccessError


def test_request_explicitly_selects_blue_and_has_no_tools() -> None:
    request = build_request()
    assert request["model"] == MODEL_ID
    assert request["access_programs"] == {"cyber": ACCESS_PROGRAM}
    assert request["store"] is False
    assert "tools" not in request
    assert len(request["safety_identifier"]) <= 64


def test_doctor_passes_only_when_response_binds_selected_program() -> None:
    client = FakeDaybreakClient()
    receipt, exit_code = run_doctor(client=client, sdk_version="test")
    assert exit_code == 0
    assert receipt["status"] == "DAYBREAK_BLUE_CAPABILITY_PASS"
    assert receipt["selected_access_program"] == ACCESS_PROGRAM
    assert all(receipt["gates"].values())
    assert client.request["access_programs"] == {"cyber": ACCESS_PROGRAM}
    assert "output_text" not in receipt


def test_doctor_fails_on_silent_standard_fallback() -> None:
    receipt, exit_code = run_doctor(
        client=FakeDaybreakClient(selected_program="standard"), sdk_version="test"
    )
    assert exit_code == 2
    assert receipt["status"] == "DAYBREAK_BLUE_CAPABILITY_FAIL"
    assert receipt["gates"]["selected_program_exact"] is False


def test_access_denial_is_a_sanitized_decision_result() -> None:
    receipt, exit_code = run_doctor(client=FailingClient(), sdk_version="test")
    assert exit_code == 2
    assert receipt["status"] == "DAYBREAK_BLUE_CAPABILITY_FAIL"
    assert receipt["error"] == {
        "http_status": 403,
        "code": "access_program_not_enabled",
        "type": "FakeAccessError",
    }
    assert "message" not in receipt["error"]
