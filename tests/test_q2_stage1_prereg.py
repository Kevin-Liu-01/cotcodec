"""The q2-stage1-rescoped-v1 draft names the code it runs and cannot be frozen half-filled."""

from __future__ import annotations

import ast
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


def test_only_the_open_slots_keep_the_draft_from_freezing(tmp_path):
    """With every open slot filled on a scratch copy the guard freezes the file: no prose
    use of the placeholder and no angle-bracket text is left to be edited under pressure at
    the freeze."""
    if _frozen():
        pytest.skip("frozen: the ledger row binds the file")
    filled = re.sub(r"\bTBD\b", "filled", _text())
    copy = tmp_path / "program/preregistrations" / PREREG.name
    copy.parent.mkdir(parents=True)
    copy.write_text(filled, encoding="utf-8")
    row = preregister.freeze(copy, P.EXPERIMENT_ID, ledger=tmp_path / "ledger.jsonl", root=tmp_path)
    assert row["experiment_id"] == P.EXPERIMENT_ID


def test_sign_offs_are_open_slots():
    """Kevin's rulings and the program's sign-off are slots the freeze guard checks."""
    section = _text().split("## 18. Design decisions for sign-off", 1)[1].split("\n## ", 1)[0]
    joined = " ".join(section.split())
    assert "Kevin: item 17" in joined and "without the D11 runtime check" in joined
    assert "Kevin: G0 item 5's decisions" in joined and "`26150609`" in joined
    assert "Program sign-off of items 1-16 and 19-27 (decision id): TBD" in joined
    assert joined.count(": TBD") == 3


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


# Files the S1a code reads as data at run time (not imports): the executor's guest program,
# the guard, the catalog the certified keysyms come from and the IR's keysym table.
LOADED_DATA = (
    "harness/q2/vm/guest/l0_fixed.py",
    "harness/q2/vm/guest/guard.py",
    "harness/q2/action_path/catalog.yaml",
    "harness/q2/action_path/keysyms.json",
)


def _module_file(name: str) -> Path | None:
    path = ROOT.joinpath(*name.split("."))
    if path.with_suffix(".py").is_file():
        return path.with_suffix(".py")
    if (path / "__init__.py").is_file():
        return path / "__init__.py"
    return None


def _imports(path: Path) -> set[Path]:
    """In-repo modules a file imports anywhere (lazy imports included), with their packages."""
    out: set[Path] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
        for name in names:
            parts = name.split(".")
            if parts[0] not in ("harness", "scripts"):
                continue
            for i in range(1, len(parts) + 1):
                found = _module_file(".".join(parts[:i]))
                if found is not None:
                    out.add(found)
    return out


def test_code_of_record_lists_everything_the_s1a_code_runs():
    """Section 20 names every in-repo module the S1a code imports, transitively, and every
    file it loads as code or data, so no file the episodes run is left unpinned."""
    rows = _code_table()
    start = [ROOT / p for p in rows if p.endswith(".py") and p.startswith(("harness/", "scripts/"))]
    seen: set[Path] = set()
    stack = list(start)
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        stack += list(_imports(path))
    needed = {p.relative_to(ROOT).as_posix() for p in seen} | set(LOADED_DATA)
    missing = sorted(needed - set(rows))
    assert not missing, f"section 20 lacks {missing}"


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
    assert f"If K_base < {P.K_MAX}" in text and f"K_base < {P.K_FLOOR} goes back" in text
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
