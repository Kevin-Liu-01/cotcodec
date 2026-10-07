"""The K1 successor's and the throughput probe's draft registrations against the code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from harness import sparse_indexer_k1_budget_v2 as budget
from scripts import derive_sparse_indexer_k1_v2_limits as derive
from scripts import fill_sparse_indexer_k1_probe_manifest as probe_filler
from scripts import fill_sparse_indexer_k1_v2_manifests as filler
from scripts import preregister

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREREGS = PROJECT_ROOT / "program" / "preregistrations"
V1 = (PREREGS / "q3-k1-localization-screen-v1.md").read_text(encoding="utf-8")
V2_PATH = PREREGS / "q3-k1-localization-screen-v2.md"
V2 = V2_PATH.read_text(encoding="utf-8")
PROBE_PATH = PREREGS / "q3-k1-throughput-probe-v1.md"
PROBE = PROBE_PATH.read_text(encoding="utf-8")
CONTRACT = yaml.safe_load((PROJECT_ROOT / filler.CONTRACT_PATH).read_text(encoding="utf-8"))
PLACEHOLDER = re.compile(r"\bTBD\b|<[A-Za-z_ -]+>")  # scripts/preregister.py refuses these


def section(text: str, name: str) -> str:
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^## (.+)$", text, re.M)]
    for index, (start, head) in enumerate(heads):
        if head == name:
            end = heads[index + 1][0] if index + 1 < len(heads) else len(text)
            return text[start:end].strip("\n")
    raise KeyError(name)


def _frozen(experiment_id: str) -> bool:
    try:
        preregister.verify(experiment_id)
    except preregister.PreregistrationError:
        return False
    return True


VERBATIM = ("Arms", "Training stream", "Learning-rate freeze", "Evaluation (audit partition only)",
            "Metrics", "Validity gates (evaluated before any verdict)", "Decision rules",
            "Seeds, sample sizes and sensitivity")


@pytest.mark.parametrize("name", VERBATIM)
def test_v2_copies_v1s_science_verbatim(name) -> None:
    assert section(V1, name) in section(V2, name)


def test_v2_copies_the_question_model_sources_bundle_and_decisions() -> None:
    question = section(V1, "Question").replace(
        "`experiments/architectures/translation-supervised-sparse-indexer-k1-screen.yaml`.",
        "`experiments/architectures/translation-supervised-sparse-indexer-k1-screen-v2.yaml`\n"
        "(v1's, `translation-supervised-sparse-indexer-k1-screen.yaml`, is unchanged).")
    assert question == section(V2, "Question")
    identity = section(V1, "Identity")
    assert identity[identity.index("Model. Qwen/Qwen3-0.6B-Base"):] in V2
    decisions = section(V1, "Design decisions").split("\n", 1)[1].strip("\n")
    assert decisions in section(V2, "Design decisions carried from v1")
    bundle = section(V1, "Bundle digest").split("\n", 1)[1].strip("\n")
    for paragraph in bundle.split("\n\n"):
        assert paragraph in V2 or paragraph.startswith("| Item"), paragraph[:60]
    for clause in ("HOLD is terminal for this experiment id", "it is not discretionary",
                   "the final verdict is INCONCLUSIVE and no second extension runs",
                   "Budget amendments are declined by default",
                   "could change only minutes and GPU-hours, never rules",
                   "A second continuation is declined by default", "PROCEED_TO_K1"):
        assert clause in " ".join(V2.split()), clause


def test_v2_decisions_continue_v1s_numbering_and_name_the_replaced_ones() -> None:
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", section(V2, "Design decisions of v2"),
                                          re.M)]
    assert numbers == list(range(32, 47))
    lead = " ".join(section(V2, "Design decisions carried from v1").split())
    assert "Decisions 18 and 23" in lead and "30" in lead and "31" in lead
    assert "decisions 32 to 46" in " ".join(V2.split())


def _table(text: str) -> dict[str, str]:
    return dict(filler.IDENTITY_ROW_RE.findall(text))


def test_v2_code_table_covers_every_bound_file() -> None:
    pytest.importorskip("torch")
    from scripts import probe_sparse_indexer_k1_throughput as probe

    table = _table(V2)
    v1_table = _table(V1)
    for path in (*filler.SELF_PATHS, filler.CONTRACT_PATH, *probe.CODE_FILES):
        assert path in table, path
    for path, digest in v1_table.items():
        if path in table:
            assert table[path] == digest, f"{path} must be v1's file, unchanged"
    probe_table = _table(PROBE)
    for path, digest in probe_table.items():
        if path in table:
            assert table[path] == digest, f"{path}: the probe must measure the v2 code"
    assert v1_table.keys() - table.keys() == {
        "scripts/fill_sparse_indexer_k1_manifests.py",
        "experiments/architectures/translation-supervised-sparse-indexer-k1-screen.yaml"}


def test_v2_entry_points_code_files_are_tabled() -> None:
    pytest.importorskip("torch")
    from scripts import run_sparse_indexer_phase0a_v2 as entry

    assert set(entry.CODE_FILES) <= set(_table(V2))


@pytest.mark.skipif(_frozen(filler.EXPERIMENT_ID),
                    reason="once frozen, receipts and the filler bind the digests")
def test_v2_code_table_matches_the_working_tree() -> None:
    for path, digest in _table(V2).items():
        assert preregister.sha256_file(PROJECT_ROOT / path) == digest, path


@pytest.mark.skipif(_frozen(probe_filler.EXPERIMENT_ID),
                    reason="once frozen, the probe filler binds the digests")
def test_probe_code_table_matches_the_working_tree() -> None:
    table = _table(PROBE)
    assert probe_filler.SELF_PATH in table
    for path, digest in table.items():
        assert preregister.sha256_file(PROJECT_ROOT / path) == digest, path


def test_v2_bundle_and_probe_rows_are_what_the_filler_reads() -> None:
    assert filler.BUNDLE_ROW_RE.findall(V2) == [
        "919d016b87ad862f8f156e9537c9a39e2864dab0e6c605307d100d25a199dd2d"]
    assert filler.BUNDLE_COMMIT_ROW_RE.findall(V2) == ["ec81fe3292d8559251adb273cb4e6ec5b070c162"]
    # v1's commit A, the bundle's building commit, is v1's ledger row's git_head_at_freeze.
    row = preregister.verify("q3-k1-localization-screen-v1")
    assert row["git_head_at_freeze"] == "ec81fe3292d8559251adb273cb4e6ec5b070c162"


def test_v2_limits_await_the_probe_and_block_the_freeze() -> None:
    compute = section(V2, "Compute")
    if CONTRACT["execution"]["job_limits"] is None:
        assert "<from the probe>" in compute and "<probe receipt digest>" in V2
        assert filler.PROBE_ROW_RE.findall(V2) == []
        assert PLACEHOLDER.search(V2)  # preregister.py freeze refuses this text
    else:  # filled from the probe: the table is the formula's, row for row
        limits = budget.check_limits(CONTRACT["execution"]["job_limits"])
        assert not PLACEHOLDER.search(V2)
        receipt = filler.PROBE_ROW_RE.findall(V2)
        assert receipt == [CONTRACT["throughput_probe"]["receipt_sha256"]]
        rows = [line for line in compute.splitlines() if line.startswith("| ")]
        assert all(row.split(" | ")[3].strip() == str(limits[row_job]["minutes"])
                   for row in rows for row_job in limits if row.startswith(f"| {row_job} "))


def test_v2_formula_constants_match_the_code() -> None:
    flat = " ".join(V2.split())
    assert (f"max({budget.MIN_LIMIT_MINUTES}, ceil({budget.PROJECTION_MARGIN} x "
            f"{1 + budget.HEADROOM:.2f} x P + {budget.SIGNAL_LEAD_MINUTES:.0f}))") in flat
    assert f"a {budget.MAIN_ALLOWANCE_S:.0f} s allowance (v1's)" in flat
    assert f"smoke (1 GPU): {budget.LEG_ALLOWANCE_S:.0f} s" in flat
    for number in ("3,650 selection-only", "5,060", "300 multiple-choice-only", "289,330",
                   "160 selection-only", "280 selection plus multiple-choice",
                   "560 multiple-choice-only", "16,968"):
        assert number in flat, number
    assert budget.AUDIT_MIX.selection_rows_total == 289330
    assert budget.DEV_MIX.selection_rows_total == 16968


def test_v2_scenario_table_is_the_formulas() -> None:
    compute = section(V2, "Compute")
    for name in budget.SCENARIO_INPUTS:
        derived = budget.derive_limits(budget.scenario_rates(name))
        main, ext = derived["jobs"]["main"], derived["jobs"]["extension"]
        row = (f"| {name} |")
        line = next(line for line in compute.splitlines() if line.startswith(row))
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert cells[2] == f"{main['projected_minutes']:.1f} / {main['minutes']}", name
        assert cells[3] == f"{ext['projected_minutes']:.1f} / {ext['minutes']}", name
        assert cells[4] == f"{derived['total_gpu_hours_with_probe']:.2f}", name
    assert budget.derive_limits(budget.scenario_rates("conservative"))["gauntlet_required"]
    assert "the gauntlet would apply" in " ".join(compute.split())


def test_derive_rows_match_the_registered_table_layout() -> None:
    rows = derive.markdown_rows(budget.derive_limits(budget.scenario_rates("central")))
    compute = section(V2, "Compute")
    labels = [line.split(" | ")[0] for line in compute.splitlines()
              if line.startswith("| ") and ("<from the probe>" in line or "0.15 |" in line)]
    assert [row.split(" | ")[0] for row in rows] == labels
    assert derive.PROBE_ROW in compute


def test_probe_registration_states_the_registered_shapes_and_gates() -> None:
    torch = pytest.importorskip("torch")
    from harness import sparse_indexer_k1_equivalence_v2 as eq
    from scripts import probe_sparse_indexer_k1_throughput as probe

    del torch
    shapes = probe.Shapes.registered()
    flat = " ".join(PROBE.split())
    assert f"{shapes.train_steps} steps of the 18-indexer bank" in flat
    assert f"{shapes.extension_steps} steps with the V1 extension's 6 trainable" in flat
    assert f"{shapes.units_per_kind} selection-only" in flat
    assert f"{shapes.unit_rows} query rows" in flat and f"{shapes.long_rows} query rows" in flat
    assert f"{shapes.concurrent_steps} steps each" in flat
    for arm, seconds in shapes.timeouts_s.items():
        assert f"**{arm}** ({seconds:.0f} s)" in flat, arm
    assert eq.TOLERANCES["loss_max_rel"] == 1e-3 and eq.TOLERANCES["adam_step_max_rel"] == 1e-6
    for value in ("1e-3", "1e-2", "1e-6", "1e-4"):
        assert value in flat
    assert probe.EXPERIMENT_ID == "q3-k1-throughput-probe-v1"


def test_probe_registration_reads_as_frozen_text() -> None:
    status = PROBE.split("\n\n", 2)[1]
    assert status.startswith("Status: frozen in program/preregistrations/ledger.jsonl")
    assert not PLACEHOLDER.search(PROBE)
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", section(PROBE, "Design decisions"),
                                          re.M)]
    assert numbers == list(range(1, len(numbers) + 1))
