"""The K2 addendum names the exact code it will run and leaves the parent's code untouched."""

from __future__ import annotations

import hashlib
import re
import shutil
import sys
from pathlib import Path

import pytest

from harness.q2_mutation import analysis, campaign
from harness.q2_mutation_k2 import lane, report, rules

ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = ROOT / lane.REGISTRATION
sys.path.insert(0, str(ROOT / "scripts"))
import preregister  # noqa: E402
import q2_mutation_k2_code_table as code_table  # noqa: E402

PLACEHOLDER = re.compile(r"\bTBD\b|<[A-Za-z_ -]+>")  # what the freeze guard refuses
# D32 and D39: the freeze replaces the whole status paragraph with the frozen wording that
# section 14 states under "At the freeze", so no draft-only sentence is frozen with it.
STATUS_FORBIDDEN = ("DRAFT", "not frozen", "no ledger row", "open slot", "TBD")
FROZEN_STATUS_START = "**Status: frozen in `program/preregistrations/ledger.jsonl`;"
DRAFT_STATUS_START = "**Status: DRAFT, not frozen (TBD: at the freeze this whole paragraph"


def text() -> str:
    return REGISTRATION.read_text(encoding="utf-8")


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def status_paragraph(body: str) -> str:
    """The status paragraph at the top: from the line that starts with ``**Status:`` (the
    file's third) to the first blank line, its line breaks folded."""
    lines = body.split("\n")
    assert lines[2].startswith("**Status:"), "the status paragraph starts on the third line"
    end = lines.index("", 2)
    return " ".join(" ".join(lines[2:end]).split())


def stated_frozen_status(body: str) -> str:
    """The frozen status paragraph section 14 states under "At the freeze": its one block
    quote, line breaks folded."""
    parts = body.split("\n### At the freeze\n")
    assert len(parts) == 2, "section 14 has one 'At the freeze' subsection"
    lines = parts[1].split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("> "))
    quote = []
    for line in lines[start:]:
        if not line.startswith(">"):
            break
        quote.append(line[1:])
    assert not any(line.startswith(">") for line in lines[start + len(quote) :]), "one quote"
    return " ".join(" ".join(quote).split())


def fill_status(body: str) -> str:
    """The file as the freeze fills it: the whole status paragraph replaced by the stated one."""
    lines = body.split("\n")
    end = lines.index("", 2)
    return "\n".join([*lines[:2], stated_frozen_status(body), *lines[end:]])


def check_frozen_status(body: str) -> None:
    status = status_paragraph(body)
    assert status == stated_frozen_status(body), "the status paragraph must be section 14's"
    assert status.startswith(FROZEN_STATUS_START)
    for phrase in STATUS_FORBIDDEN:
        assert phrase not in status, f"the frozen status paragraph says {phrase!r}"
    assert not PLACEHOLDER.search(body), "the freeze guard would refuse the filled file"


def test_registration_has_its_own_id() -> None:
    body = text()
    assert body.startswith(f"# {lane.EXPERIMENT_ID}: ")
    assert rules.EXPERIMENT_ID == lane.EXPERIMENT_ID


def scratch_tree(tmp_path: Path, body: str) -> Path:
    """A copy of what the lane reads, with ``body`` as the registration and no ledger."""
    src = tmp_path / "src"
    for rel in (lane.SPLITS, lane.FILE_CACHE_RECEIPTS, lane.REGISTERED_SAMPLE, lane.REGISTERED_K2C):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, src / rel)
    (src / lane.REGISTRATION).parent.mkdir(parents=True, exist_ok=True)
    (src / lane.REGISTRATION).write_text(body, encoding="utf-8")
    return src


def test_the_status_paragraph_is_replaced_whole_at_the_freeze(tmp_path: Path) -> None:
    """Three states, each checked. The draft: the status paragraph holds the one placeholder,
    so the freeze guard refuses the file as it stands; a scratch copy filled as section 14
    says is accepted by the guard, frozen into a copy of the ledger, verified, and read by the
    lane as frozen. The filled file before its row (the commit that becomes
    ``git_head_at_freeze``) and the frozen file: the status paragraph is the stated one, with
    no draft-only wording; once the row exists the lane reads the file as frozen."""
    body = text()
    frozen = stated_frozen_status(body)
    assert frozen.startswith(FROZEN_STATUS_START)
    assert not PLACEHOLDER.search(frozen)
    for phrase in STATUS_FORBIDDEN:
        assert phrase not in frozen, phrase
    row = lane.ledger_row(ROOT)
    if status_paragraph(body).startswith(DRAFT_STATUS_START):
        assert row is None, "the draft wording was frozen"
        assert len(PLACEHOLDER.findall(body)) == 1, "the status placeholder is the only one"
        draft = scratch_tree(tmp_path / "draft", body)
        with pytest.raises(preregister.PreregistrationError, match="TBD"):
            preregister.freeze(
                draft / lane.REGISTRATION,
                lane.EXPERIMENT_ID,
                ledger=draft / lane.LEDGER,
                root=draft,
            )
        filled = fill_status(body)
        check_frozen_status(filled)
        src = scratch_tree(tmp_path / "filled", filled)
        frozen_row = preregister.freeze(
            src / lane.REGISTRATION, lane.EXPERIMENT_ID, ledger=src / lane.LEDGER, root=src
        )
        assert preregister.verify(lane.EXPERIMENT_ID, ledger=src / lane.LEDGER, root=src)
        assert lane.frozen_registration(src)["hash"] == frozen_row["hash"]
        assert lane.registered_k2c_sha256(src) == sha(lane.REGISTERED_K2C)
        # Rewriting only the bold line leaves draft sentences behind: refused.
        bold_only = body.replace(
            body.split("\n")[2], FROZEN_STATUS_START + " see the ledger row.**", 1
        )
        with pytest.raises(AssertionError, match="section 14's"):
            check_frozen_status(bold_only)
        return
    check_frozen_status(body)
    if row is not None:
        assert lane.frozen_registration(ROOT)["sha256"] == sha(lane.REGISTRATION)


def test_code_table_matches_the_tree() -> None:
    assert code_table.declared(text()) == code_table.table(), (
        "refresh: python scripts/q2_mutation_k2_code_table.py --write"
    )
    listed = set(code_table.FILES)
    package = {
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "harness" / "q2_mutation_k2").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.name not in ("README.md", "SKILL.md")
    }
    assert package <= listed, f"unlisted K2 files: {sorted(package - listed)}"


def test_registration_states_the_registered_inputs() -> None:
    body = text()
    k2c = sha(lane.REGISTERED_K2C)
    assert lane.registered_k2c_sha256(ROOT) == k2c
    for digest in (
        lane.REGISTERED_SAMPLE_SHA256,
        lane.REGISTERED_JOBS_SHA256,
        *report.REGISTERED_INPUTS.values(),
        k2c,
    ):
        assert digest in body
    assert sha(lane.REGISTERED_SAMPLE) == lane.REGISTERED_SAMPLE_SHA256
    for key in ("image", "image_id"):
        assert lane.VM_PINS[key].split("@")[-1] in body
    assert lane.QCOW2_SHA256 in body and lane.EPISODE_IMAGE_ID in body
    assert f"V = {lane.REGISTERED_CONCURRENCY}" in body
    slurm = lane.REGISTERED_SLURM
    assert (
        f"Slurm {slurm['cpus']} CPUs, {slurm['memory_gb']} GB, {slurm['minutes']} minutes" in body
    )
    assert f"run timeout {lane.REGISTERED_SETTINGS['episode_timeout_s']} s" in body
    assert f"At most {rules.MAX_EXCLUDED_PAIRS} of the {rules.REGISTERED_PAIRS} K2 pairs" in body
    for name in rules.K2_EXPLANATIONS:
        assert f"`{name}`" in body


def test_reused_code_is_byte_identical_to_its_frozen_pins() -> None:
    body = text()
    for rel in (
        "harness/q2_mutation/vm_injection.py",
        "harness/q2_mutation/reachability.py",
        "harness/q2_mutation/tasks.py",
        "harness/q2_mutation/schema.py",
        "harness/q2_mutation/analysis.py",
        "harness/q2_stage1/osworld_live.py",
        "harness/q2_stage1/driver.py",
        "harness/q2_stage1/lane.py",
    ):
        assert f"| `{rel}` | `{sha(rel)}` |" in body, rel
    s1a = (ROOT / "program/preregistrations/q2-stage1-rescoped-v1.md").read_text()
    for rel in ("harness/q2_stage1/osworld_live.py", "harness/q2_stage1/driver.py",
                "harness/q2_stage1/lane.py"):  # fmt: skip
        assert f"| `{rel}` | `{sha(rel)}` |" in s1a
    pinned = []
    for name in ("q2-action-path-v2.md", "q2-action-path-v2-inputs.md",
                 "q2-action-path-v2-executor.md"):  # fmt: skip
        doc = (ROOT / "program/preregistrations" / name).read_text()
        pinned += re.findall(r"^\| `(harness/q2/vm/[^`]+)` \| `([0-9a-f]{64})` \|", doc, re.M)
    assert pinned
    for rel, digest in pinned:
        assert sha(rel) == digest, f"{rel} changed since action-path v2 froze it"


def test_the_parents_code_tree_and_explanations_are_unchanged() -> None:
    parent = (ROOT / campaign.PREREG_PATH).read_text()
    assert (
        campaign.prereg_pins(parent)["code_tree_sha256"] == campaign.pins(ROOT)["code_tree_sha256"]
    )
    assert "58bee0190c0c7eb5d44f36e27c0f1e0daab82c1c48716009a9066777c69a0721" in text()
    assert rules.K2_EXPLANATIONS == analysis.K2_EXPLANATIONS


def test_the_k2_job_runs_from_the_freeze_commit_in_every_text() -> None:
    """The lane accepts k2 only from a tree holding the ledger row, so the job runs from the
    freeze commit (the row's commit), never from its parent ``git_head_at_freeze``."""
    body = " ".join(text().split())
    assert "export the freeze commit itself, never its parent" in body
    assert "The freeze commit is the executor commit." in body
    assert "`git_head_at_freeze` is the executor commit" not in body
    base = (ROOT / "experiments/manifests/q2-mutation-k2/k2-confirm-v1.base.json").read_text()
    assert "export of the freeze commit" in base
    assert "from the ledger row's git_head_at_freeze" not in base
    skill = (ROOT / "harness/q2_mutation_k2/SKILL.md").read_text()
    assert "never its parent" in skill
    # The report takes the K2-C digest from the registration, not from an argument.
    assert "--k2c-sha256" not in body


def test_the_reported_quantities_are_produced_by_the_report_code() -> None:
    """Section 8's quantities exist in the report's summary (a test of report.py builds them;
    here the text and the code name the same tables): agreement per set only, the run
    statistics per set and pooled."""
    body = " ".join(text().split())
    for phrase in ("by save path", "checker observations", "host snapshots"):
        assert phrase in body
    assert "Per set (`k2`, `k2c`) only: pairs agreeing, differing and excluded" in body
    assert "Agreement is never pooled over the two sets" in body
    assert "Per set and pooled over every run attempt of the job" in body
    assert "and pooled over both: agreement" not in body
    source = (ROOT / "harness/q2_mutation_k2/report.py").read_text()
    for key in ('"by_save_path"', '"observations"', '"host_overlap"', '"by_offline_verdict"'):
        assert key in source


def test_the_blind_warning_and_the_run_root_are_the_registrations() -> None:
    body = " ".join(text().split())
    assert "`blind_warning` field" in body and "D77" in report.BLIND_WARNING
    assert f"`{lane.REGISTERED_RUN_ROOT}`" in body
    base = (ROOT / "experiments/manifests/q2-mutation-k2/k2-confirm-v1.base.json").read_text()
    assert f'"run_root": "{lane.REGISTERED_RUN_ROOT}"' in base
    summary = "program/evidence/2026-10-08/q2-mutation-confirm/mutants-confirm-v1/score/"
    summary += "k2-sample.summary.json"
    assert f"`{summary}` (SHA-256 `{sha(summary)}`)" in body
