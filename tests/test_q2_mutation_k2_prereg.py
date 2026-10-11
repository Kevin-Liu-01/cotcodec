"""The K2 addendum names the exact code it will run and leaves the parent's code untouched."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from harness.q2_mutation import analysis, campaign
from harness.q2_mutation_k2 import lane, report, rules

ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = ROOT / lane.REGISTRATION
sys.path.insert(0, str(ROOT / "scripts"))
import q2_mutation_k2_code_table as code_table  # noqa: E402


def text() -> str:
    return REGISTRATION.read_text(encoding="utf-8")


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def test_registration_is_a_draft_with_its_own_id_and_no_ledger_row_yet() -> None:
    body = text()
    assert body.startswith(f"# {lane.EXPERIMENT_ID}: ")
    assert "**Status: DRAFT." in body
    assert lane.ledger_row(ROOT) is None, "freezing is the program owner's step"
    assert rules.EXPERIMENT_ID == lane.EXPERIMENT_ID
    # The freeze command's text check passes (no TBD, no <placeholder>).
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", body)


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
    for digest in (lane.REGISTERED_SAMPLE_SHA256, *report.REGISTERED_INPUTS.values(), k2c):
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
