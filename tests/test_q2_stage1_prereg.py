"""The q2-stage1-rescoped-v1 draft names the code it runs and cannot be frozen half-filled."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from harness.q2_stage1 import lane, rules
from harness.q2_stage1 import plan as P

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "program/preregistrations/q2-stage1-rescoped-v1.md"
LEDGER = ROOT / "program/preregistrations/ledger.jsonl"
SIM = ROOT / "program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis/sim_s1a_v2.json"
ROW = re.compile(r"^\| `([^`]+)` \| (`([0-9a-f]{64})`|TBD) \|$")
sys.path.insert(0, str(ROOT / "scripts"))
import preregister  # noqa: E402
import render_q2_stage1_manifest as builder  # noqa: E402


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


def test_sign_off_slots():
    """Kevin's rulings and the program's sign-off are slots the freeze guard checks. Kevin's
    two are filled from his rulings (D55); the program's stays open until its decision, and
    the lead-in names the same items as its slot."""
    section = _text().split("## 18. Design decisions for sign-off", 1)[1].split("\n## ", 1)[0]
    joined = " ".join(section.split())
    assert "The program may sign off items 1-16 and 19-27;" in joined
    kevin_17 = joined.split("- Kevin: item 17", 1)[1].split("- Kevin: G0 item 5", 1)[0]
    assert "without the D11 runtime check" in kevin_17
    assert kevin_17.rstrip().endswith(
        ": accepted, including the unanchored read (Kevin's ruling of 2026-10-09, D55 (i))"
    )
    kevin_g0 = joined.split("- Kevin: G0 item 5's decisions", 1)[1].split("- Program", 1)[0]
    assert "`26150609`" in kevin_g0
    assert kevin_g0.rstrip().endswith(": accepted (Kevin's ruling of 2026-10-09, D55 (ii))")
    program = "- Program sign-off of items 1-16 and 19-27 (decision id): "
    assert program in joined
    if not _frozen():
        assert program + "TBD" in joined and joined.count(": TBD") == 1


# G0 item 10's slot, which ``lane.load_frozen_plan`` reads: the frozen plan file's
# ``plan_sha256`` field in backticks, on one unbroken run of text.
FROZEN_PLAN_SLOT = re.compile(r"Frozen plan SHA-256: (TBD|`([0-9a-f]{64})`)\.")
PLAN_NAMED = re.compile(r"--purpose a1 --plan (\S+\.json)`")
RUNS = "/home/kevin/cotcodec-runs/stage0/q2-stage1"
HOST = {
    "run_root": f"{RUNS}/runs",
    "vm": {**lane.VM_PINS, "guest_ip": "20.20.20.21",
           "qcow2": {"host_path": f"{RUNS}/../q2-action-path/vm/Ubuntu.qcow2",
                     "sha256": lane.QCOW2_SHA256, "size_bytes": lane.QCOW2_BYTES}},
    "osworld": {"host_dir": f"{RUNS}/inputs/OSWorld", "commit": lane.OSWORLD_COMMIT},
    "file_cache": {"host_dir": f"{RUNS}/inputs/files"},
    "engine": {"bridge_dir": f"{RUNS}/gpu/{{gpu_job_id}}/bridge",
               "gpu_job_id_file": f"{RUNS}/pairs/a1/gpu_job_id"},
}  # fmt: skip


def _named_plan() -> tuple[str, dict]:
    """The plan file G0 item 10 tells the A1 manifests to name, checked as the lane does."""
    paths = set(PLAN_NAMED.findall(" ".join(_text().split())))
    assert len(paths) == 1, f"G0 item 10 must name one plan file for A1, got {paths}"
    rel = paths.pop()
    plan = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    body = {k: v for k, v in plan.items() if k != "plan_sha256"}
    assert plan["plan_sha256"] == P.digest(body), f"{rel} does not match its plan_sha256"
    assert plan["status"] == "frozen-constants", f"{rel} is not a frozen-constants plan"
    return rel, plan


def _source_tree(root: Path, registration: str, plan_rel: str) -> Path:
    """A source tree as an A1 export would hold it: the splits, the plan file, this
    registration (as given) frozen into a copy of the real ledger."""
    for rel in (lane.SPLITS, plan_rel):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, root / rel)
    prereg = root / lane.REGISTRATION
    prereg.parent.mkdir(parents=True, exist_ok=True)
    prereg.write_text(registration, encoding="utf-8")
    ledger = root / lane.LEDGER
    shutil.copy(LEDGER, ledger)
    before = preregister.read_ledger(ledger)
    row = preregister.freeze(prereg, P.EXPERIMENT_ID, ledger=ledger, root=root)
    rows = preregister.read_ledger(ledger)  # the chain holds with the new row
    assert len(rows) == len(before) + 1 and row["previous_hash"] == before[-1]["hash"]
    return root


def _a1_9b_s1(root: Path, plan_rel: str) -> dict:
    return builder.vm_manifest(purpose="a1", host=HOST, source_dir=root, plan_path=plan_rel,
                               size="9B", session="S1")  # fmt: skip


def test_frozen_plan_slot_takes_the_plan_sha256_the_lane_reads(tmp_path):
    """G0 item 10's slot must hold the frozen plan file's ``plan_sha256`` in backticks:
    ``lane.load_frozen_plan`` refuses every A1 manifest otherwise, and only a new experiment
    id would repair a frozen file that states the file's SHA-256 or drops the backticks."""
    text = _text()
    slots = FROZEN_PLAN_SLOT.findall(text)
    assert len(slots) == 1 and text.count("Frozen plan SHA-256:") == 1
    rel, plan = _named_plan()
    sha = plan["plan_sha256"]
    filled = slots[0][1]
    if filled:  # frozen: the slot is the named plan file's plan_sha256, and the lane takes it
        assert filled == sha, "the slot must be the plan file's plan_sha256 field"
        assert f"Frozen plan SHA-256: `{sha}`" in text
        lane.validate_manifest(_a1_9b_s1(ROOT, rel), ROOT)
        return
    assert not _frozen()
    assert f"`{sha}`" in text, "G0 item 10 states the value the slot takes"
    slot = "Frozen plan SHA-256: TBD."
    good = re.sub(r"\bTBD\b", "filled", text.replace(slot, f"Frozen plan SHA-256: `{sha}`."))
    root = _source_tree(tmp_path / "good", good, rel)
    m = _a1_9b_s1(root, rel)
    assert m["plan"] == {"path": rel, "sha256": sha}
    assert lane.validate_manifest(m, root)["slots"] == m["slots"]
    edited = root / lane.REGISTRATION  # an edit after the freeze: the ledger row binds the file
    edited.write_text(good + "\nAn edit after the freeze.\n", encoding="utf-8")
    with pytest.raises(lane.LaneError, match="changed after the freeze"):
        lane.validate_manifest(m, root)
    file_sha = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert file_sha != sha
    for name, wrong in (("file-digest", f"`{file_sha}`"), ("unquoted", sha)):
        bad = re.sub(r"\bTBD\b", "filled", text.replace(slot, f"Frozen plan SHA-256: {wrong}."))
        bad_root = _source_tree(tmp_path / name, bad, rel)
        with pytest.raises(lane.LaneError, match="does not name this plan"):
            lane.validate_manifest(_a1_9b_s1(bad_root, rel), bad_root)


# D32 and D39: the freeze rewrites the whole status paragraph to the frozen wording, which
# section 22 states under "At the freeze", so no draft-only sentence is frozen with it.
STATUS_FORBIDDEN = ("DRAFT", "not frozen", "no ledger row", "open slot")
FROZEN_STATUS_START = "**Status: frozen in `program/preregistrations/ledger.jsonl`;"


def _status_paragraph(text: str) -> str:
    """The status paragraph at the top: from the line that starts with ``**Status:`` (the
    file's third) to the first blank line, its line breaks folded."""
    lines = text.split("\n")
    assert lines[2].startswith("**Status:"), "the status paragraph starts on the third line"
    end = lines.index("", 2)
    return " ".join(" ".join(lines[2:end]).split())


def _stated_frozen_status(text: str) -> str:
    """The frozen status paragraph section 22 states under "At the freeze": its one block
    quote, line breaks folded."""
    parts = text.split("\n### At the freeze\n")
    assert len(parts) == 2, "section 22 has one 'At the freeze' subsection"
    lines = parts[1].split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("> "))
    quote = []
    for line in lines[start:]:
        if not line.startswith(">"):
            break
        quote.append(line[1:])
    assert not any(line.startswith(">") for line in lines[start + len(quote) :]), "one quote"
    return " ".join(" ".join(quote).split())


def _check_frozen_status(text: str) -> None:
    status = _status_paragraph(text)
    assert status == _stated_frozen_status(text), "the status paragraph must be section 22's"
    assert status.startswith(FROZEN_STATUS_START)
    for phrase in STATUS_FORBIDDEN:
        assert phrase not in status, f"the frozen status paragraph says {phrase!r}"


def test_the_status_paragraph_is_replaced_whole_at_the_freeze(tmp_path):
    """Before the freeze: the placeholder names the whole paragraph, the stated frozen
    paragraph passes the post-freeze check, and a scratch copy filled as section 22 says the
    freeze fills it is accepted by the guard, frozen into a copy of the ledger, verified and
    passes the check. After the freeze: the status paragraph is the stated one."""
    text = _text()
    frozen = _stated_frozen_status(text)
    assert frozen.startswith(FROZEN_STATUS_START)
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", frozen)
    for phrase in STATUS_FORBIDDEN:
        assert phrase not in frozen, phrase
    if _frozen():
        _check_frozen_status(text)
        return
    status = _status_paragraph(text)
    assert status.startswith("**Status: DRAFT, not frozen (TBD: at the freeze this whole paragraph")
    assert status.count("TBD") == 1
    lines = text.split("\n")
    end = lines.index("", 2)
    filled = "\n".join(lines[:2] + [frozen] + lines[end:])
    rel, plan = _named_plan()
    filled = filled.replace(
        "Frozen plan SHA-256: TBD.", f"Frozen plan SHA-256: `{plan['plan_sha256']}`."
    ).replace("(decision id): TBD", "(decision id): D99")
    _check_frozen_status(filled)
    root = _source_tree(tmp_path / "frozen", filled, rel)  # the guard accepts it; row added
    row = preregister.verify(P.EXPERIMENT_ID, ledger=root / lane.LEDGER, root=root)
    assert row["sha256"] == lane.frozen_registration(root)["sha256"]
    _check_frozen_status((root / lane.REGISTRATION).read_text(encoding="utf-8"))
    # Rewriting only the bold line, as the old slot said, leaves draft sentences: refused.
    bold_only = re.sub(r"\bTBD\b", "filled", text)
    with pytest.raises(AssertionError, match="section 22's"):
        _check_frozen_status(bold_only)


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


def test_registered_base_is_the_draw_on_the_eligible_pool():
    """Section 5.4 states the K = 32 base and the eligible pool the plan draws it from."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import render_q2_stage1_plan as renderer

    inputs = renderer.load_inputs(ROOT)
    pool = P.eligible_pool(inputs["confirm_ids"], P.OFFLINE_EXCLUDED)
    base = P.draw_tasks(pool, inputs["domain"], 32)["base"]
    text = " ".join(_text().split())
    assert "K = 32 base: `" + " ".join(t[:8] for t in base) + "`" in text
    assert f"**Eligible pool ({len(pool)} tasks):**" in text
    for task in P.OFFLINE_EXCLUDED:
        assert f"`{task[:8]}`" in text
    assert f"`{P.SETUP_CHECK_SHA256}`" in text
