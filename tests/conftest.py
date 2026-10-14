"""Test-suite hooks.

S2 v5 step 0 (decision D94): ``tests/test_s2v5_step0.py`` is pinned by
``experiments/manifests/s2v5/step0-rule.json`` (step 0's analysis refuses to run if it changes), and
it renders its development manifest from a copy of the repository's ledger. Once
``s2-arabic-cua-locale-v5`` has a ledger row, step 0's renderer refuses, as every development job
must after a freeze (D56). That one refusal is reported as a skip, with its reason, in that file
only and only while v5's ledger row exists; every other outcome is reported as it is.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STEP0_TESTS = "tests/test_s2v5_step0.py::"
FROZEN_REFUSAL = "s2-arabic-cua-locale-v5 is frozen: development no longer runs (D56)"


def _v5_frozen() -> bool:
    from harness.s2_locale import ap_delta_v5

    return ap_delta_v5.ledger_row(ROOT) is not None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if (
        report.when == "call"
        and report.failed
        and call.excinfo is not None
        and item.nodeid.startswith(STEP0_TESTS)
        and str(call.excinfo.value) == FROZEN_REFUSAL
        and _v5_frozen()
    ):
        report.outcome = "skipped"
        report.longrepr = (str(item.path), item.location[1] or 0,
                           f"Skipped: step 0 is development, refused after v5's freeze: "
                           f"{FROZEN_REFUSAL}")  # fmt: skip
