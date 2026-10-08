"""The q2-stage1-rescoped-v1 draft names the code it runs and cannot be frozen half-filled."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from harness.q2_stage1 import plan as P
from harness.q2_stage1 import rules

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "program/preregistrations/q2-stage1-rescoped-v1.md"
LEDGER = ROOT / "program/preregistrations/ledger.jsonl"
SIM = ROOT / "program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis/sim_s1a_v2.json"
ROW = re.compile(r"^\| `([^`]+)` \| (`([0-9a-f]{64})`|TBD) \|$")
sys.path.insert(0, str(ROOT / "scripts"))
import preregister  # noqa: E402


def _text() -> str:
    return PREREG.read_text(encoding="utf-8")


def _frozen() -> bool:
    return any(
        json.loads(line)["experiment_id"] == P.EXPERIMENT_ID
        for line in LEDGER.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _code_table() -> dict[str, str | None]:
    section = _text().split("## 20. Code of record", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        m = ROW.match(line.strip())
        if m:
            rows[m.group(1)] = m.group(3)
    return rows


def test_the_draft_cannot_be_frozen_until_every_slot_is_filled(tmp_path):
    if _frozen():
        pytest.skip("frozen: the ledger row binds the file")
    text = _text()
    assert "TBD" in text.split("\n", 3)[2], "the status line must read TBD until the freeze"
    copy = tmp_path / "program/preregistrations" / PREREG.name
    copy.parent.mkdir(parents=True)
    copy.write_text(text, encoding="utf-8")
    with pytest.raises(preregister.PreregistrationError, match="TBD"):
        preregister.freeze(copy, P.EXPERIMENT_ID, ledger=tmp_path / "ledger.jsonl", root=tmp_path)


def test_code_of_record_matches_the_tree():
    rows = _code_table()
    assert len(rows) >= 12
    for path, digest in rows.items():
        if digest is None:
            continue
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert actual == digest, f"{path} changed: refresh section 20 of the registration"
    for module in ("estimators", "records", "rules", "plan", "analysis"):
        assert rows[f"harness/q2_stage1/{module}.py"] is not None


def test_registered_numbers_equal_the_code():
    text = _text()
    assert f"**M = {rules.M_SMALL}**" in text or f"**{rules.M_SMALL}**" in text
    assert f"| **{rules.M_9B}** |" in text
    sim = json.loads(SIM.read_text(encoding="utf-8"))
    assert max(cell["M_small"] for cell in sim["dr5"].values()) == rules.M_SMALL
    assert max(cell["M_9B"] for cell in sim["dr5"].values()) == rules.M_9B
    caps = P.CAP_MINUTES
    for job in ("O1", "A0a", "A0b", "O2", "ANC"):
        assert re.search(rf"\| {job} \| [^|]+ \| [^|]+ \| {caps[job]} \|", text), job
    for v, price in P.PRICE_HIGH.items():
        assert f"{price:.6f}" in text, (v, price)
    for v, price in P.PRICE_CENTRAL.items():
        assert f"{price:.6f}" in text, (v, price)
    assert f"If K_base < {P.K_FLOOR}" in text
    assert "min(p_δ, p_X) <= 0.025" in text and rules.ALPHA / len(rules.DR2_FAMILY) == 0.025
    assert "within ±7.5 pp" in text and rules.EQUIVALENCE_MARGIN == 0.075
    assert "below 0.12" in text and rules.PI_EQUIVALENCE_BOUND == 0.12
    assert "more than 5% of its first-attempt dispatched" in text and rules.DR0_CELL_LOSS == 0.05
    assert "Seeds are [42, 43, 44]" in text and P.SEEDS == (42, 43, 44)
    for task in P.FLAGGED_TASKS:
        assert f"`{task[:8]}`" in text


def test_draft_plan_digest_is_the_renderers(tmp_path):
    out = tmp_path / "plan.json"
    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts/render_q2_stage1_plan.py"), "--out", str(out)],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert f"`{run.stdout.strip()}`" in _text()
