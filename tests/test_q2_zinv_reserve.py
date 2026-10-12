"""q2-zinv-reserve-validation-v1: the rule, the target filter, the rescoring rows, the guard,
the host tool's commands and the registration's text."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from harness.q2_mutation import campaign
from harness.q2_zinv_reserve import guard, rules, run

ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = ROOT / rules.REGISTRATION
sys.path.insert(0, str(ROOT / "scripts"))
import preregister  # noqa: E402

PLACEHOLDER = re.compile(r"\bTBD\b|<[A-Za-z_ -]+>")  # what the freeze guard refuses
STATUS_FORBIDDEN = ("DRAFT", "not frozen", "No ledger row", "no ledger row", "TBD")
FROZEN_STATUS_START = "**Status: frozen in `program/preregistrations/ledger.jsonl`;"
DRAFT_STATUS_START = "**Status: DRAFT, not frozen (TBD: at the freeze this whole paragraph"
CONFIRM_ROWS = ROOT / "program/evidence/2026-10-08/q2-stage1-g0/zinv/zinv-validation-v3.json"
CONFIRM_OUTCOMES = (
    ROOT / "program/evidence/2026-10-08/q2-mutation-confirm/results/released/"
    "confirm-mutants-v1/outcomes.jsonl"
)
RESERVE_SUMMARY = (
    ROOT / "program/evidence/2026-10-08/q2-mutation-confirm/results/released/controls/"
    "reserve-controls-v1.summary.json"
)


def load_host():
    path = ROOT / "infra/q2-zinv-reserve/run/zr_host.py"
    spec = importlib.util.spec_from_file_location("zr_host", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text() -> str:
    return REGISTRATION.read_text(encoding="utf-8")


def flat(body: str) -> str:
    return " ".join(body.split())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- the rule


def row(rid, task="t1", kind="mutant", operator=rules.ZORDER, label=rules.EQUIV, stored=0.0,
        zinv=1.0, raw=None, digest="d", **extra):  # fmt: skip
    out = {"id": rid, "task_id": task, "kind": kind, "operator": operator, "label": label,
           "stored": stored, "raw": stored if raw is None else raw, "zinv": zinv,
           "files_sha256": digest, "files_unchanged": True,
           "raw_infra": False, "zinv_infra": False}  # fmt: skip
    out.update(extra)
    return out


def zrows(n, tasks, accepted=None):
    accepted = n if accepted is None else accepted
    return [row(f"z{i}", task=f"t{i % tasks}", zinv=1.0 if i < accepted else 0.0) for i in range(n)]


def vrow(rid, task="t0", stored=0.0, zinv=0.0):
    return row(rid, task=task, operator="pptx.viol.text_edit", label=rules.VIOLATION,
               stored=stored, zinv=zinv)  # fmt: skip


def test_small_sample_all_accepted_is_a_descriptive_pass():
    out = rules.judge([*zrows(15, 6), vrow("v1")], n_boot=200)
    assert (out["outcome"], out["status"]) == ("PASS", "descriptive")
    assert out["condition_a"]["accepted"] == 15 and out["condition_b"]["held"]
    assert out["license"] == rules.LICENSES["PASS"]["descriptive"]
    assert out["acceptance"]["exact_one_sided_95_lower"] == pytest.approx(0.05 ** (1 / 15))


def test_one_rejection_fails_below_20_and_passes_at_20():
    assert rules.judge([*zrows(15, 6, accepted=14), vrow("v")], n_boot=50)["outcome"] == "FAIL"
    at20 = rules.judge([*zrows(20, 8, accepted=19), vrow("v")], n_boot=50)
    assert (at20["outcome"], at20["status"]) == ("PASS", "registered_rule")
    at20b = rules.judge([*zrows(20, 8, accepted=18), vrow("v")], n_boot=50)
    assert at20b["outcome"] == "FAIL"
    assert at20b["fail_reasons"] == ["acceptance_below_95_percent"]
    assert len(at20b["condition_a"]["not_accepted"]) == 2
    # 24 on 7 tasks: enough mutants, too few tasks
    assert rules.judge([*zrows(24, 7), vrow("v")], n_boot=50)["status"] == "descriptive"


def test_a_violation_newly_accepted_fails_whatever_the_acceptance():
    out = rules.judge([*zrows(24, 8), vrow("v1", zinv=1.0), vrow("v2")], n_boot=50)
    assert out["outcome"] == "FAIL" and out["fail_reasons"] == ["violation_newly_accepted"]
    assert out["condition_b"]["new_accepts"] == ["v1"]
    # a violation the original already passes is not a new accept (a checker false positive)
    kept = rules.judge([*zrows(24, 8), vrow("v1", stored=1.0, zinv=1.0)], n_boot=50)
    assert kept["outcome"] == "PASS" and kept["violation_bounds"]["original_passes"] == ["v1"]


def test_validity_failures_on_decision_rows_make_the_run_incomplete():
    for broken in (
        {"raw": 1.0},  # the fresh original scoring does not reproduce the registered fail
        {"zinv_infra": True},
        {"files_unchanged": False},
        {"files_unchanged": None},
    ):
        rows = [*zrows(15, 6), vrow("v")]
        rows[0].update(broken)
        out = rules.judge(rows, n_boot=50)
        assert out["outcome"] == "INCOMPLETE", broken
        assert out["validity"]["invalid_decision_rows"] == ["z0"]
    # an invalid gold row is reported, not decisive
    gold = row("g1", kind="gold", operator=None, label="gold", stored=1.0, zinv=1.0, raw=0.0)
    out = rules.judge([*zrows(15, 6), vrow("v"), gold], n_boot=50)
    assert out["outcome"] == "PASS" and out["validity"]["invalid_rows"] == {
        "g1": ["raw_differs_from_stored"]
    }


def test_incomplete_takes_precedence_over_fail_and_both_conditions_are_still_reported():
    rows = [*zrows(15, 6, accepted=10), vrow("v1", zinv=1.0)]
    rows[0].update(files_unchanged=False)  # one invalid decision row
    out = rules.judge(rows, n_boot=50)
    assert out["outcome"] == "INCOMPLETE"
    assert out["fail_reasons"] == ["acceptance_below_95_percent", "violation_newly_accepted"]
    assert out["condition_b"]["new_accepts"] == ["v1"]
    assert "precedence over FAIL" in out["license"] and "no rerun" in out["license"]
    body = flat(text())
    assert "INCOMPLETE takes precedence over FAIL" in body
    assert "Invalid rows are final" in body


def test_licenses_match_section_7_and_every_output_carries_the_blind_warning():
    registered = rules.LICENSES["PASS"]["registered_rule"]
    descriptive = rules.LICENSES["PASS"]["descriptive"]
    for license_text in (registered, descriptive):
        assert "generaliz" not in license_text and "observed rate" not in license_text
        assert "not developed on, at this size" in license_text
    assert "at most about 0.88" in registered and "not 95%" in registered
    body = flat(text())
    assert "the population statement is the lower bound (at most about 0.88), not 95%" in body
    assert "held on documents it was not developed on, at this size" in body
    out = rules.judge([*zrows(15, 6), vrow("v")], n_boot=50)
    assert out["warning"] == rules.BLIND_WARNING
    assert "spot check (D9) is still pending" in rules.BLIND_WARNING
    assert "blind warning" in body and "`rules.BLIND_WARNING`" in body


def test_no_zorder_cell_is_probe_touched_on_the_registered_tasks():
    probe = json.loads((ROOT / campaign.PROBE_TOUCHED).read_text())
    cells = campaign.probe_touched_cells(probe)
    for task in rules.RESERVE_PPTX_TASKS:
        assert probe["tasks"][task]["split"] == "reserve"
        assert cells[task], task  # the scoping probe touched every one of the 8 tasks
        assert not campaign.is_probe_touched(cells, task, rules.ZORDER), task
    assert "no `pptx.eq.zorder_nonoverlap` cell is probe-touched on the 8 tasks" in flat(text())


def test_edge_outcomes_and_reported_quantities():
    assert rules.judge([vrow("v")], n_boot=50)["outcome"] == "NOT_TESTABLE"
    assert rules.judge([vrow("v", zinv=1.0)], n_boot=50)["outcome"] == "FAIL"
    assert rules.judge(zrows(15, 6), n_boot=50)["outcome"] == "PASS_A_ONLY"
    errored = zrows(15, 6)
    errored[3].update(zinv=None, zinv_error="ValueError: x")
    out = rules.judge([*errored, vrow("v")], n_boot=50)
    assert out["outcome"] == "FAIL" and out["reported"]["zinv_errors"] == ["z3"]
    extra = row("e1", operator="pptx.extra.add_textbox", label=rules.EXTRA, zinv=1.0)
    gold = row("g1", kind="gold", operator=None, label="gold", stored=1.0, zinv=0.0)
    out = rules.judge([*zrows(15, 6), vrow("v"), extra, gold], n_boot=50)
    reported = out["reported"]
    assert reported["extra_change_new_accepts"] == ["e1"]
    assert reported["regressions_pass_to_not_pass"] == ["g1"]
    assert {c["id"]: c["change"] for c in reported["other_items_changed"]} == {
        "e1": "fail->pass", "g1": "pass->fail"}  # fmt: skip
    assert out["original_on_z"]["fails"] == 15
    with pytest.raises(ValueError, match="duplicate"):
        rules.judge([row("a"), row("a")])


def test_known_answer_on_zinvs_development_rows():
    """The registered rule read on job 1000's committed rows (the confirm development set)."""
    rows = json.loads(CONFIRM_ROWS.read_text())["rows"]
    out = rules.judge(rows, require_file_check=False, n_boot=500)
    assert (out["outcome"], out["status"]) == ("PASS", "registered_rule")
    assert (out["condition_a"]["n"], out["condition_a"]["tasks"]) == (39, 15)
    assert out["condition_a"]["accepted"] == 39
    assert (out["condition_b"]["n"], out["condition_b"]["new_accepts"]) == (67, [])
    assert out["original_on_z"]["fails"] == 35
    assert out["reported"]["other_items_changed"] == []
    assert "39 of 39 z-order mutants on 15 tasks and 0 of 67 violation" in flat(text())


# --------------------------------------------------------------------------- design numbers


def test_design_numbers_quoted_by_the_registration():
    body = flat(text())
    table = rules.design_table()
    assert table["max_misses"] == {12: 0, 15: 0, 18: 0, 21: 1, 24: 1, 20: 1}
    for n in (12, 15, 18, 21, 24):
        ind = " / ".join(f"{table['p_fail_independent'][n][p]:.3f}" for p in (0.8, 0.85, 0.9, 0.95))
        clu = " / ".join(f"{table['p_fail_tasks_of_3'][n][p]:.3f}" for p in (0.8, 0.85, 0.9, 0.95))
        p80 = f"{table['p80_independent'][n]:.3f} / {table['p80_tasks_of_3'][n]:.3f}"
        lower = f"{table['zero_miss_lower_bound'][n]:.3f}"
        assert f"| {n} | {ind} | {clu} | {p80} | {lower} |" in body, n
    floor = table["floor"]
    assert f"P(at least 20 mutants) {floor['p_at_least_20_mutants']:.3f}" in body
    assert f"P(8 tasks) {floor['p_8_tasks']:.3f}" in body
    assert f"registered-rule status of section 6) {floor['p_registered_rule']:.3f}" in body
    assert f"mean `n_Z` {floor['mean_mutants']:.1f}" in body
    q = table["q80_violation"]
    assert f"{q[15]:.1%} / {q[20]:.1%} / {q[25]:.1%} / {q[30]:.1%}" in body


def test_expected_size_model_comes_from_the_released_confirm_outcomes():
    outcomes = [json.loads(x) for x in CONFIRM_OUTCOMES.read_text().splitlines() if x.strip()]
    evaluable_targets: dict[str, int] = {}
    for o in outcomes:
        if o.get("checker_family") != rules.FAMILY or o["lock_status"] != "evaluable":
            continue
        evaluable_targets.setdefault(o["task_id"], 0)
        if o["operator"] == rules.ZORDER and o["label"] == rules.EQUIV:
            evaluable_targets[o["task_id"]] += 1
    yields = tuple(evaluable_targets[t] for t in sorted(evaluable_targets))
    assert yields == rules.CONFIRM_ZORDER_YIELDS and sum(yields) == 39
    # every reserve pptx gold passes raw and saved, so all 8 targets are expected evaluable
    summary = json.loads(RESERVE_SUMMARY.read_text())
    assert sha(RESERVE_SUMMARY) == rules.RESERVE_CONTROLS_SUMMARY_SHA256
    for task in rules.RESERVE_PPTX_TASKS:
        entry = summary["tasks"][task]
        assert set(entry["checker_funcs"]) == {rules.FAMILY}
        assert entry["gold_raw_lock"]["verdict"] == entry["gold_saved_lock"]["verdict"] == "pass"


def test_registered_targets_are_the_reserve_pptx_targets_counted_before_the_draft():
    counts = json.loads(
        (ROOT / "program/evidence/q2-mutation/integration/prefreeze-counts-v2/counts.json")
        .read_text()
    )["reserve"]  # fmt: skip
    assert counts["targets_by_doc_family"]["pptx"] == 8
    pptx = sorted(t for t, r in counts["tasks"].items() if r["doc_families"] == ["pptx"])
    assert tuple(pptx) == rules.RESERVE_PPTX_TASKS
    assert all(counts["tasks"][t]["checker_family"] == rules.FAMILY for t in pptx)
    splits = json.loads((ROOT / campaign.SPLITS_PATH).read_text())
    assert set(rules.RESERVE_PPTX_TASKS) <= set(splits["reserve"])


# --------------------------------------------------------------------------- select-targets


def targets(*pairs):
    return [{"target_id": f"{t}__x", "task_id": t, "family": f} for t, f in pairs]


def test_select_targets_keeps_the_registered_reserve_pptx_targets_only():
    reserve = targets(*[(t, "pptx") for t in rules.RESERVE_PPTX_TASKS], ("aaaa", "xlsx"))
    kept, summary = run.select_targets(reserve, "pptx", "reserve")
    assert [t["task_id"] for t in kept] == list(rules.RESERVE_PPTX_TASKS)
    assert summary["dropped_by_family"] == {"xlsx": 1}
    with pytest.raises(run.RunError, match="differ from the registered"):
        run.select_targets(reserve[1:], "pptx", "reserve")
    with pytest.raises(run.RunError, match="differ from the registered"):
        run.select_targets([*reserve, *targets(("bbbb", "pptx"))], "pptx", "reserve")
    with pytest.raises(run.RunError, match="pptx family only"):
        run.select_targets(reserve, "xlsx", "reserve")
    kept, _ = run.select_targets(targets(("d1", "pptx"), ("d2", "docx")), "pptx", "dev")
    assert [t["task_id"] for t in kept] == ["d1"]


def test_select_targets_command_keeps_the_full_list_and_refuses_a_second_run(tmp_path):
    rows = targets(("d1", "pptx"), ("d2", "docx"), ("d3", "pptx"))
    run.write_jsonl(tmp_path / "targets.jsonl", rows)
    assert run.main(["select-targets", "--prep", str(tmp_path), "--family", "pptx",
                     "--split", "dev"]) == 0  # fmt: skip
    assert run.read_jsonl(tmp_path / "targets-all.jsonl") == rows
    assert [t["task_id"] for t in run.read_jsonl(tmp_path / "targets.jsonl")] == ["d1", "d3"]
    summary = json.loads((tmp_path / "targets-selection.json").read_text())
    assert summary["targets_kept"] == 2 and summary["targets_all"] == 3
    assert run.main(["select-targets", "--prep", str(tmp_path), "--family", "pptx",
                     "--split", "dev"]) == 2  # fmt: skip


# --------------------------------------------------------------------------- rescore


def fixture_inputs():
    jobs = [{"mutant_id": m, "task_id": "t", "files": {"/home/user/a.pptx": f"/ro/build/{m}"}}
            for m in ("m1", "m2", "m3")]  # fmt: skip
    verdicts = [
        {"mutant_id": "m1", "checker_funcs": [rules.FAMILY], "score": 0.0, "scored_sha256": "s1"},
        {"mutant_id": "m2", "checker_funcs": [rules.FAMILY], "score": 0.0, "scored_sha256": "s2"},
        {"mutant_id": "m3", "checker_funcs": ["compare_table"], "score": 1.0},
    ]
    outcomes = [
        {"mutant_id": "m1", "lock_status": "evaluable", "operator": rules.ZORDER,
         "label": rules.EQUIV, "probe_touched": False, "target_id": "t__a"},
        {"mutant_id": "m2", "lock_status": "evaluable", "operator": "pptx.viol.text_edit",
         "label": rules.VIOLATION, "probe_touched": True, "target_id": "t__a"},
        {"mutant_id": "m3", "lock_status": "evaluable", "operator": "x", "label": rules.EQUIV},
    ]  # fmt: skip
    golds = [{"mutant_id": "g1", "task_id": "t", "kind": "gold", "files": {}},
             {"mutant_id": "i1", "task_id": "t", "kind": "initial", "files": {}}]  # fmt: skip
    gold_verdicts = [
        {
            "mutant_id": "g1",
            "checker_funcs": [rules.FAMILY] * 2,
            "score": 1.0,
            "scored_sha256": "sg",
        },
        {"mutant_id": "i1", "checker_funcs": [rules.FAMILY], "score": 0.0, "scored_sha256": "si"},
    ]
    return jobs, verdicts, outcomes, golds, gold_verdicts


def test_items_and_rows_carry_the_registered_verdict_and_digests():
    items = run.items_for(*fixture_inputs())
    assert [(i["kind"], i["job"]["mutant_id"]) for i in items] == [
        ("mutant", "m1"), ("mutant", "m2"), ("gold", "g1"), ("initial", "i1")]  # fmt: skip
    assert [i["stored_scored_sha256"] for i in items] == ["s1", "s2", "sg", "si"]
    assert items[1]["probe_touched"] is True and items[0]["target_id"] == "t__a"
    calls = []

    def fake(payload, limit):
        calls.append(payload["corrected"])
        score = 1.0 if payload["corrected"] else 0.0
        return {"score": score, "error": None, "scored_sha256": "s1", "seconds": 0.1}

    out = run.score_item(items[0], osworld="/o", file_cache="/c", vm_baseline=None, timeout=5,
                         run=fake)  # fmt: skip
    assert calls == [False, True]
    assert (out["raw"], out["zinv"], out["stored"]) == (0.0, 1.0, 0.0)
    # the fixture's files do not exist: the file check fails and the row is invalid
    assert out["files_sha256"] is None and out["files_unchanged"] is False
    assert rules.validity_problems(out) == ["files_changed_or_missing"] and rules.in_z(out)


def test_the_file_digest_is_path_independent_and_sees_a_change(tmp_path):
    one, two = tmp_path / "a" / "x.pptx", tmp_path / "b" / "x.pptx"
    for path in (one, two):
        path.parent.mkdir()
        path.write_bytes(b"deck")
    files = {"/home/user/x.pptx": str(one), "/gone": None}
    assert run.files_digest(files) == run.files_digest({**files, "/home/user/x.pptx": str(two)})
    item = {"kind": "gold", "job": {"mutant_id": "g", "task_id": "t", "files": files},
            "stored": 1.0}  # fmt: skip

    def editing(payload, limit):  # a file changes between the two scorings
        one.write_bytes(b"other")
        return {"score": 1.0, "error": None}

    out = run.score_item(item, osworld="/o", file_cache="/c", vm_baseline=None, timeout=5,
                         run=editing)  # fmt: skip
    assert out["files_unchanged"] is False
    one.write_bytes(b"deck")
    out = run.score_item(item, osworld="/o", file_cache="/c", vm_baseline=None, timeout=5,
                         run=lambda payload, limit: {"score": 1.0})  # fmt: skip
    assert out["files_unchanged"] is True and rules.validity_problems(out) == []


def test_the_parents_scored_digest_is_path_dependent():
    """Why the rows never compare ``scored_sha256``: on the confirm run it differs between the
    lock-exact and the scoping scoring of every one of the 1,300 jobs."""
    base = ROOT / "program/evidence/2026-10-08/q2-mutation-confirm/results/released/"
    rows = {}
    for arm in ("lock", "scout"):
        path = base / f"confirm-mutants-v1/verdicts-{arm}.jsonl"
        rows[arm] = {
            json.loads(x)["mutant_id"]: json.loads(x) for x in path.read_text().splitlines()
        }
    equal = sum(rows["lock"][m]["scored_sha256"] == rows["scout"][m]["scored_sha256"]
                for m in rows["lock"])  # fmt: skip
    assert len(rows["lock"]) == 1300 and equal == 0
    assert "0 of 1,300" in flat(text())


def test_rescore_refuses_unregistered_reserve_controls(tmp_path):
    args = type("A", (), {})()
    args.split = "reserve"
    args.gold_jobs = tmp_path / "jobs-saved-mounted.jsonl"
    args.gold_verdicts = tmp_path / "saved-verdicts-lock.jsonl"
    args.gold_jobs.write_text("{}\n")
    args.gold_verdicts.write_text("{}\n")
    with pytest.raises(run.RunError, match="not the registered reserve-controls-v1"):
        run.check_registered_inputs(args)
    args.split = "dev"
    run.check_registered_inputs(args)  # the dev rehearsal reads any control run


def test_judge_command_reads_a_rows_file(tmp_path):
    rows = {"schema": run.ROWS_SCHEMA, "split": "dev", "comparator_sha256": rules.ZINV_SHA256,
            "rows": [*zrows(15, 6), vrow("v")]}  # fmt: skip
    (tmp_path / "rows.json").write_text(json.dumps(rows))
    assert run.main(["judge", "--rows", str(tmp_path / "rows.json"),
                     "--out", str(tmp_path / "j.json")]) == 0  # fmt: skip
    judgement = json.loads((tmp_path / "j.json").read_text())
    assert judgement["outcome"] == "PASS" and judgement["rows_sha256"] == sha(
        tmp_path / "rows.json"
    )
    rows["split"], rows["comparator_sha256"] = "reserve", "0" * 64
    (tmp_path / "rows.json").write_text(json.dumps(rows))
    assert run.main(["judge", "--rows", str(tmp_path / "rows.json"),
                     "--out", str(tmp_path / "j.json")]) == 2  # fmt: skip


def test_rescore_command_writes_rows_with_the_blind_warning(tmp_path, monkeypatch):
    names = ("mutant_jobs", "mutant_verdicts", "outcomes", "gold_jobs", "gold_verdicts")
    for name, rows in zip(names, fixture_inputs(), strict=True):
        run.write_jsonl(tmp_path / f"{name}.jsonl", rows)

    def fake(item, **_kwargs):
        return {"id": item["job"]["mutant_id"], "kind": item["kind"]}

    monkeypatch.setattr(run, "score_item", fake)
    argv = ["rescore", "--split", "dev", "--osworld", "/o", "--file-cache", "/c",
            "--out", str(tmp_path / "rows.json")]  # fmt: skip
    for name in names:
        argv += [f"--{name.replace('_', '-')}", str(tmp_path / f"{name}.jsonl")]
    assert run.main(argv) == 0
    data = json.loads((tmp_path / "rows.json").read_text())
    assert data["warning"] == rules.BLIND_WARNING and len(data["rows"]) == 4


# --------------------------------------------------------------------------- guard


def status_paragraph(body: str) -> str:
    lines = body.split("\n")
    assert lines[2].startswith("**Status:"), "the status paragraph starts on the third line"
    end = lines.index("", 2)
    return " ".join(" ".join(lines[2:end]).split())


def stated_frozen_status(body: str) -> str:
    parts = body.split("\n### At the freeze\n")
    assert len(parts) == 2
    lines = parts[1].split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("> "))
    quote = []
    for line in lines[start:]:
        if not line.startswith(">"):
            break
        quote.append(line[1:])
    return " ".join(" ".join(quote).split())


def fill_status(body: str) -> str:
    lines = body.split("\n")
    end = lines.index("", 2)
    return "\n".join([*lines[:2], stated_frozen_status(body), *lines[end:]])


def scratch_tree(tmp_path: Path, body: str) -> Path:
    """What the guard reads, copied, with ``body`` as the registration and a ledger copy."""
    src = tmp_path / "src"
    entries = [*guard.CODE_FILES, *guard.REUSED, *campaign.CODE_TREE_ROOTS, campaign.PREREG_PATH,
               guard.LEDGER, "harness/__init__.py"]  # fmt: skip
    for rel in entries:
        source, target = ROOT / rel, src / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"),
                            dirs_exist_ok=True)  # fmt: skip
        else:
            shutil.copy2(source, target)
    (src / guard.REGISTRATION).write_text(body, encoding="utf-8")
    (src / ".git_sha").write_text("f" * 40 + "\n")
    return src


def test_code_table_and_reused_pins_match_the_tree():
    body = text()
    assert guard.declared_code_table(body) == guard.code_table(ROOT), (
        "refresh: uv run python -m harness.q2_zinv_reserve.guard code-table --write"
    )
    package = {
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "harness" / "q2_zinv_reserve").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.name not in ("README.md", "SKILL.md")
    }
    assert package <= set(guard.CODE_FILES)
    for rel, digest in guard.REUSED.items():
        assert sha(ROOT / rel) == digest
        assert f"| `{rel}` | `{digest}` |" in body
    s1a = (ROOT / "program/preregistrations/q2-stage1-rescoped-v1.md").read_text()
    for rel, digest in guard.REUSED.items():
        assert f"| `{rel}` | `{digest}` |" in s1a, rel
    assert guard.REUSED["harness/q2_stage1/zinv.py"] == rules.ZINV_SHA256
    assert guard.REUSED["harness/q2_stage1/rescore.py"] == rules.RESCORE_SHA256
    assert guard.REUSED["harness/q2_stage1/__init__.py"] == rules.STAGE1_INIT_SHA256
    parent = campaign.prereg_pins((ROOT / campaign.PREREG_PATH).read_text())
    assert campaign.pins(ROOT)["code_tree_sha256"] == parent["code_tree_sha256"]
    assert guard.PARENT_CODE_TREE_SHA256 == rules.PARENT_CODE_TREE_SHA256
    assert parent["code_tree_sha256"] == guard.PARENT_CODE_TREE_SHA256
    assert guard.check_code(ROOT)["code_table"] == "ok"


def is_draft(body: str) -> bool:
    return status_paragraph(body).startswith(DRAFT_STATUS_START)


def check_frozen_status(body: str) -> None:
    status = status_paragraph(body)
    assert status == stated_frozen_status(body), "the status paragraph must be section 13's"
    assert status.startswith(FROZEN_STATUS_START)
    for phrase in STATUS_FORBIDDEN:
        assert phrase not in status, f"the frozen status paragraph says {phrase!r}"
    assert not PLACEHOLDER.search(body), "the freeze guard would refuse the filled file"


def test_the_status_paragraph_is_replaced_whole_at_the_freeze():
    """Two states. The draft: the status paragraph holds the one placeholder and the real
    ledger has no row. The filled file (the commit that becomes ``git_head_at_freeze``) and
    the frozen one: the status paragraph is section 13's, with no draft-only wording."""
    body = text()
    frozen = stated_frozen_status(body)
    assert frozen.startswith(FROZEN_STATUS_START)
    for phrase in STATUS_FORBIDDEN:
        assert phrase not in frozen, phrase
    row = guard.frozen_row(ROOT)
    if is_draft(body):
        assert row is None, "the draft wording was frozen"
        assert len(PLACEHOLDER.findall(body)) == 1, "the status placeholder is the only one"
        check_frozen_status(fill_status(body))
        bold_only = body.replace(body.split("\n")[2], FROZEN_STATUS_START + " see the row.**", 1)
        with pytest.raises(AssertionError, match="section 13's"):
            check_frozen_status(bold_only)
        return
    check_frozen_status(body)
    if row is not None:
        assert row["sha256"] == sha(REGISTRATION)


def frozen_scratch(tmp_path: Path) -> tuple[Path, str, dict]:
    """A scratch tree whose ledger copy holds this experiment's row: before the real freeze
    (the draft or the fill commit) the filled file is frozen into the copy; after it, the
    frozen tree itself (the real ledger is never written)."""
    body = text()
    if guard.frozen_row(ROOT) is not None:
        return scratch_tree(tmp_path / "frozen", body), body, guard.frozen_row(ROOT)
    filled = fill_status(body) if is_draft(body) else body
    src = scratch_tree(tmp_path / "filled", filled)
    rows_before = len(preregister.read_ledger(src / guard.LEDGER))
    row = preregister.freeze(src / guard.REGISTRATION, guard.EXPERIMENT_ID,
                             ledger=src / guard.LEDGER, root=src)  # fmt: skip
    assert len(preregister.read_ledger(src / guard.LEDGER)) == rows_before + 1
    return src, filled, row


def test_scratch_ledger_rehearsal_of_the_freeze_and_the_reserve_guard(tmp_path, monkeypatch):
    """On a scratch tree with its own copy of the ledger: the draft is refused by the freeze
    guard, and a tree without the row by the reserve guard; the filled file freezes into the
    copy, and the reserve split is then admitted only with the environment variable; an edit
    after the freeze, of the registration or of the code, is refused. The branch is chosen by
    the real ledger, so the suite holds at the draft, at the fill commit (filled, no row) and
    at the freeze commit (the real ledger is never written)."""
    body = text()
    monkeypatch.delenv(guard.FROZEN_ENV, raising=False)
    if guard.frozen_row(ROOT) is None:
        unfrozen = scratch_tree(tmp_path / "unfrozen", body)
        if is_draft(body):
            with pytest.raises(preregister.PreregistrationError, match="TBD"):
                preregister.freeze(unfrozen / guard.REGISTRATION, guard.EXPERIMENT_ID,
                                   ledger=unfrozen / guard.LEDGER, root=unfrozen)  # fmt: skip
        assert guard.require_split_allowed("dev", unfrozen) is None
        with pytest.raises(guard.GuardError, match="only after"):
            guard.require_split_allowed("reserve", unfrozen)
    src, filled, row = frozen_scratch(tmp_path)
    assert preregister.verify(guard.EXPERIMENT_ID, ledger=src / guard.LEDGER, root=src)
    with pytest.raises(guard.GuardError, match="reserve split only"):
        guard.require_split_allowed("confirm", src)
    with pytest.raises(guard.GuardError, match=guard.FROZEN_ENV):
        guard.require_split_allowed("reserve", src)
    monkeypatch.setenv(guard.FROZEN_ENV, guard.EXPERIMENT_ID)
    assert guard.require_split_allowed("reserve", src)["hash"] == row["hash"]
    (src / guard.REGISTRATION).write_text(filled + "\nedited\n", encoding="utf-8")
    with pytest.raises(guard.GuardError, match="frozen digest"):
        guard.require_split_allowed("reserve", src)
    (src / guard.REGISTRATION).write_text(filled, encoding="utf-8")
    (src / "harness/q2_zinv_reserve/rules.py").write_text("# edited\n")
    with pytest.raises(guard.GuardError, match="code table"):
        guard.require_split_allowed("reserve", src)


# --------------------------------------------------------------------------- host tool


def parent_bodies(split: str, workers: int = 16, apply_to: str = "gold") -> list[str]:
    """The ``sh -c`` bodies of the frozen submit_mutants.sh jobs 1-3, expanded by bash."""
    script = (ROOT / "infra/q2-mutation/run/submit_mutants.sh").read_text()
    bodies = []
    for name in ("a1", "a2", "a3"):
        match = re.search(name + r'=\$\(hex (?:"\$\{frozen_env\[@\]\}" )?sh -c "(.*?)"\)\n',
                          script, re.DOTALL)  # fmt: skip
        assert match, name
        program = (
            f"split={split}\npy=/opt/venv-lock/bin/python\nworkers={workers}\n"
            f"apply_to={apply_to}\n"
            'guard="cd /src && ${py} -m harness.q2_mutation.campaign guard --split ${split} '
            '--src /src --inputs /inputs"\n'
            f'printf "%s" "{match.group(1)}"\n'
        )
        out = subprocess.run(["bash", "-c", program], capture_output=True, text=True, check=True)
        bodies.append(" ".join(out.stdout.split()))
    return bodies


def test_steps_1_to_3_are_the_parents_frozen_jobs():
    host = load_host()
    for split in ("dev", "reserve"):
        a1, a2, a3 = parent_bodies(split)
        ours = [" ".join(b.split()) for b in host.parent_commands(split, host.WORKERS, "gold")]
        assert ours == [a1, a2, a3], split
        guard_cmd = (f"cd /src && {host.PY} -m harness.q2_zinv_reserve.guard check "
                     f"--split {split} --src /src")  # fmt: skip
        targets = host.step_argv("targets", split, "gold")
        body = " ".join(targets[-1].split())
        assert body.startswith(f"{guard_cmd} && {a1} && ")
        assert body.endswith(f"select-targets --prep /out --family pptx --split {split}")
        assert host.step_argv("build", split, "gold") == ["sh", "-c", host.parent_commands(
            split, host.WORKERS, "gold")[1]]  # fmt: skip
        score = host.step_argv("score", split, "gold")
        assert " ".join(score[-1].split()) == f"{guard_cmd} && {a3}"
        env = targets[: targets.index("sh")]
        if split == "dev":
            assert env == [] and score[0] == "sh"
        else:
            assert env == ["env", "Q2M_PREREG_FROZEN=q2-evaluator-mutation-v1",
                           "Q2ZR_PREREG_FROZEN=q2-zinv-reserve-validation-v1"]  # fmt: skip
            assert score[:3] == env
    zinv = host.step_argv("zinv", "reserve", "gold")[-1]
    for part in ("harness.q2_zinv_reserve.guard check --split reserve",
                 "harness.q2_mutation.campaign guard --split reserve",
                 "run rescore --split reserve", "--gold-jobs /ro/csaved/jobs-saved-mounted.jsonl",
                 "--workers 7 --timeout 300", "run judge --rows /out/zinv-rows.json"):  # fmt: skip
        assert part in zinv, part


def host_setup(tmp_path, monkeypatch, split="dev"):
    host = load_host()
    q2m = tmp_path / "q2m"
    for sub in ("saved", "lo"):
        (q2m / "runs" / "dev-controls-v9" / sub).mkdir(parents=True)
    monkeypatch.setattr(host, "Q2M", q2m)
    src = scratch_tree(tmp_path / "staged", text())
    root = tmp_path / "root"
    return host, src, root


def test_host_plan_and_next_submit_one_job_at_a_time(tmp_path, monkeypatch):
    host, src, root = host_setup(tmp_path, monkeypatch)
    monkeypatch.delenv(guard.FROZEN_ENV, raising=False)
    refusal = "only after" if guard.frozen_row(ROOT) is None else guard.FROZEN_ENV
    with pytest.raises(guard.GuardError, match=refusal):
        host.make_plan(src, "r", "reserve", None, root)
    with pytest.raises(host.HostError, match="controls-run"):
        host.make_plan(src, "d", "dev", None, root)
    assert host.main(["--root", str(root), "plan", "--src", str(src), "--name", "d",
                      "--split", "dev", "--controls-run", "dev-controls-v9"]) == 0  # fmt: skip
    queue: list[str] = ["900 other kevin RUNNING"]
    submitted: list[list[str]] = []
    monkeypatch.setattr(host, "queue_jobs", lambda: list(queue))

    def fake_sbatch(command):
        submitted.append(command)
        return str(1000 + len(submitted))

    monkeypatch.setattr(host, "sbatch", fake_sbatch)

    def plan():
        return host.read_plan(root, "d")[1]

    def finish(exit_status: int) -> None:
        step = next(s for s in plan()["steps"] if s["state"] == "submitted")
        receipt = {"exit_status": exit_status, "started_at": "2026-10-11T00:00:00Z",
                   "finished_at": "2026-10-11T00:06:00Z"}  # fmt: skip
        Path(step["run_dir"], f"receipt-{step['job']}.json").write_text(json.dumps(receipt))

    host.main(["--root", str(root), "next", "--name", "d"])
    assert submitted == [], "a busy queue holds every submission"
    host.main(["--root", str(root), "next", "--name", "d", "--dry-run"])
    assert submitted == []
    queue.clear()
    host.main(["--root", str(root), "next", "--name", "d"])
    assert len(submitted) == 1 and "--job-name=q2zr-d-targets" in submitted[0]
    # gone from the queue without a receipt: failed; the step reruns once, in a fresh directory
    host.main(["--root", str(root), "next", "--name", "d"])
    assert len(submitted) == 2 and "--job-name=q2zr-d-targets.a2" in submitted[1]
    steps = plan()["steps"]
    assert steps[0]["state"] == "superseded" and steps[1]["name"] == "targets.a2"
    assert steps[1]["run_dir"].endswith("prep.a2") and steps[1]["state"] == "submitted"
    finish(0)
    host.main(["--root", str(root), "next", "--name", "d"])
    build = submitted[-1]
    assert len(submitted) == 3 and "--job-name=q2zr-d-build" in build
    export = next(a for a in build if a.startswith("--export="))
    assert f"Q2M_EXTRA_RO={root}/runs/d/prep.a2:/ro/prep" in export
    assert "Q2M_IMAGE_ID=sha256:f5b4c40e" in export  # the LO-VM image for the build
    finish(1)
    host.main(["--root", str(root), "next", "--name", "d"])  # failed: the rerun is submitted
    assert len(submitted) == 4 and "--job-name=q2zr-d-build.a2" in submitted[3]
    finish(1)
    host.main(["--root", str(root), "next", "--name", "d"])
    assert [s["state"] for s in plan()["steps"]].count("failed_final") == 1
    host.main(["--root", str(root), "next", "--name", "d"])
    assert len(submitted) == 4, "nothing is submitted after a final failure"


def test_host_runs_all_four_steps_and_mounts_the_finished_attempts(tmp_path, monkeypatch):
    host, src, root = host_setup(tmp_path, monkeypatch)
    plan = host.make_plan(src, "d", "dev", "dev-controls-v9", root)
    run_dir = root / "runs" / "d"
    run_dir.mkdir(parents=True)
    host.write_plan(run_dir, plan)
    monkeypatch.setattr(host, "queue_jobs", lambda: [])
    submitted = []
    monkeypatch.setattr(host, "sbatch", lambda c: submitted.append(c) or str(len(submitted)))
    for _ in range(4):
        host.main(["--root", str(root), "next", "--name", "d"])
        step = next(s for s in host.read_plan(root, "d")[1]["steps"] if s["state"] == "submitted")
        Path(step["run_dir"], f"receipt-{step['job']}.json").write_text(json.dumps(
            {"exit_status": 0, "started_at": "2026-10-11T00:00:00Z",
             "finished_at": "2026-10-11T00:30:00Z"}))  # fmt: skip
    host.main(["--root", str(root), "next", "--name", "d"])
    states = [s["state"] for s in host.read_plan(root, "d")[1]["steps"]]
    assert states == ["done"] * 4 and len(submitted) == 4
    export = next(a for a in submitted[3] if a.startswith("--export="))
    controls = tmp_path / "q2m" / "runs" / "dev-controls-v9"
    assert (f"Q2M_EXTRA_RO={run_dir}/build:/ro/build+{run_dir}/score:/ro/score"
            f"+{controls}/saved:/ro/csaved+{controls}/lo:/ro/lo") in export  # fmt: skip
    assert "Q2M_IMAGE_ID=sha256:2006c1a9" in export
    assert [c for c in submitted[0] if c.startswith("--time=")] == ["--time=00:30:00"]
    assert Counter(c.split("=")[0] for c in submitted[0])["--export"] == 1
    # the lane-hour cap: 4 x 0.5 h used, nothing more would be submitted
    assert host.hours_used(host.read_plan(root, "d")[1]) == pytest.approx(2.0)


def test_the_reserve_split_has_one_registered_plan_name(tmp_path, monkeypatch):
    host, _src, root = host_setup(tmp_path, monkeypatch)
    src, _filled, _row = frozen_scratch(tmp_path)
    (src / ".git_sha").write_text("f" * 40 + "\n")
    monkeypatch.setenv(guard.FROZEN_ENV, guard.EXPERIMENT_ID)
    with pytest.raises(host.HostError, match="one registered plan is reserve-v1"):
        host.make_plan(src, "reserve-v2", "reserve", None, root)
    saved = tmp_path / "q2m" / "runs" / rules.RESERVE_CONTROLS_RUN / "saved"
    saved.mkdir(parents=True)
    (saved.parent / "lo").mkdir()
    for name in rules.RESERVE_CONTROLS:
        (saved / name).write_text("{}\n")
    # the registered name passes the name check and meets the control-file digests next
    with pytest.raises(host.HostError, match="differs from its registered digest"):
        host.make_plan(src, rules.RESERVE_PLAN, "reserve", None, root)
    body = flat(text())
    assert f"--name {rules.RESERVE_PLAN} --split reserve" in body
    assert "Only the plan named `reserve-v1` is evidence" in body


def finished_dev_run(tmp_path, monkeypatch):
    """A dev plan whose four steps finished (step 1 after one rerun), with the files the
    parent's ``campaign export`` reads (empty row files) and this addendum's step outputs."""
    host, src, root = host_setup(tmp_path, monkeypatch)
    plan = host.make_plan(src, "d", "dev", "dev-controls-v9", root)
    run_dir = root / "runs" / "d"
    run_dir.mkdir(parents=True)
    host.write_plan(run_dir, plan)
    monkeypatch.setattr(host, "queue_jobs", lambda: [])
    jobs = iter(range(501, 510))
    monkeypatch.setattr(host, "sbatch", lambda c: str(next(jobs)))
    exits = iter([1, 0, 0, 0, 0])  # the first targets attempt fails, its rerun finishes
    while True:
        host.main(["--root", str(root), "next", "--name", "d"])
        steps = host.read_plan(root, "d")[1]["steps"]
        step = next((s for s in steps if s["state"] == "submitted"), None)
        if step is None:
            break
        out = Path(step["run_dir"])
        files = {
            "targets": {"targets.report.json": {"split": "dev", "targets": 1},
                        "targets-selection.json": {"split": "dev", "targets_kept": 1}},
            "build": {"build-summary.json": {"mutants": 0}, "mutations.jsonl": None,
                      "admission.jsonl": None, "targets-built.jsonl": None,
                      "scoring-jobs.jsonl": None},
            "score": {"jobs-saved.jsonl": None, "recheck.jsonl": None, "outcomes.jsonl": None,
                      "report.json": {"rows": 0}, "mut-verdicts-lock.jsonl": None,
                      "mut-notes-lock.jsonl": None},
            "zinv": {"zinv-rows.json": {"schema": run.ROWS_SCHEMA, "rows": [
                         {"id": "m1", "zinv_error": "KeyError: " + "x" * 200, "raw_error": None}]},
                     "judgement.json": {"outcome": "PASS", "status": "descriptive"}},
        }[step["stage"]]  # fmt: skip
        for name, data in files.items():
            (out / name).write_text("" if data is None else json.dumps(data))
        receipt = {"exit_status": next(exits), "started_at": "2026-10-11T00:00:00Z",
                   "finished_at": "2026-10-11T00:05:00Z", "argv_json_hex": ""}  # fmt: skip
        (out / f"receipt-{step['job']}.json").write_text(json.dumps(receipt))
    assert [s["state"] for s in host.read_plan(root, "d")[1]["steps"]] == [
        "superseded", "done", "done", "done", "done"]  # fmt: skip
    return host, root, run_dir


def test_export_writes_the_parents_release_view_of_the_finished_attempts(tmp_path, monkeypatch):
    host, root, run_dir = finished_dev_run(tmp_path, monkeypatch)
    assert host.main(["--root", str(root), "export", "--name", "d"]) == 0
    view, release = run_dir / "view", run_dir / "release"
    submitted = json.loads((view / "submitted.json").read_text())
    assert {"run", "split", "git_sha", "apply_to", "jobs"} <= set(submitted)
    assert submitted["jobs"] == [502, 503, 504, 505] and submitted["superseded_jobs"] == [501]
    assert (view / "prep").resolve() == (run_dir / "prep.a2").resolve()
    manifest = json.loads((release / "campaign" / "manifest.json").read_text())
    assert (manifest["run"], manifest["split"], manifest["slurm_jobs"]) == (
        "d", "dev", [502, 503, 504, 505])  # fmt: skip
    stages = [r["stage"] for r in json.loads((release / "campaign" / "receipts.json").read_text())]
    assert stages == ["build", "prep", "score", "zinv"]
    rows = json.loads((release / "zinv-rows.json").read_text())["rows"]
    assert rows[0]["zinv_error"] == "KeyError: " + "x" * 70 + "..."
    ours = json.loads((release / "manifest.json").read_text())
    assert ours["warning"] == rules.BLIND_WARNING and ours["outcome"] == "PASS"
    assert (release / "BLIND-WARNING.txt").read_text().strip() == rules.BLIND_WARNING
    assert sorted(p.name for p in (release / "receipts").iterdir()) == [
        "build-receipt-503.json", "score-receipt-504.json", "targets-receipt-501.json",
        "targets.a2-receipt-502.json", "zinv-receipt-505.json"]  # fmt: skip
    for rel, digest in ours["files_sha256"].items():
        assert sha(release / rel) == digest, rel
    assert "campaign/outcomes.jsonl" in ours["files_sha256"]
    assert not (run_dir / "release.partial").exists()
    assert host.main(["--root", str(root), "export", "--name", "d"]) == 2  # written once


def test_export_refuses_an_incomplete_or_reused_plan(tmp_path, monkeypatch):
    host, src, root = host_setup(tmp_path, monkeypatch)
    plan = host.make_plan(src, "d", "dev", "dev-controls-v9", root)
    (root / "runs" / "d").mkdir(parents=True)
    host.write_plan(root / "runs" / "d", plan)
    with pytest.raises(host.HostError, match="not complete"):
        host.export_release(root, "d")
    plan["reuse_parent_run"] = "dev-mutants-v9"
    with pytest.raises(host.HostError, match="reuses a parent run"):
        host.make_view(root / "runs" / "d", plan)
    assert "zr_host.py export --name reserve-v1" in text()


# --------------------------------------------------------------------------- registration


def test_the_registration_states_the_registered_values():
    body = flat(text())
    assert text().startswith(f"# {rules.EXPERIMENT_ID}: ")
    for task in rules.RESERVE_PPTX_TASKS:
        assert f"`{task}`" in body
    for digest in (*rules.RESERVE_CONTROLS.values(), rules.RESERVE_CONTROLS_SUMMARY_SHA256,
                   rules.ZINV_SHA256, rules.PARENT_CODE_TREE_SHA256):  # fmt: skip
        assert digest in body
    host = load_host()
    assert f"`{host.ROOT}`" in body and host.CAP_LANE_HOURS == 4.0
    assert "reach 4.0" in body and "a cap of 4 lane-hours" in body
    for stage, (cpus, memory, _tmpfs, minutes) in host.RESOURCES.items():
        assert (
            f"`{stage}` (" in body and f"{cpus} CPUs, {memory[:-1]} GB, limit {minutes} min" in body
        )
    assert "`accepted * 100 >= 95 * n_Z`" in body
    assert (rules.ACCEPT_NUM, rules.ACCEPT_DEN, rules.MIN_MUTANTS, rules.MIN_TASKS) == (
        95,
        100,
        20,
        8,
    )
    assert "`n_Z` < 20 or `t_Z` < 8" in body
    assert "timeout 300 s" in body and host.TIMEOUT_S == 300 and host.ZINV_WORKERS == 7
    for outcome in rules.OUTCOMES:
        assert outcome in body
    assert "export the freeze commit itself, never its parent" in body


def test_a_dev_rehearsal_of_step_4_alone_reuses_a_parent_dev_run(tmp_path, monkeypatch):
    host, src, root = host_setup(tmp_path, monkeypatch)
    parent = tmp_path / "q2m" / "runs" / "dev-mutants-v9"
    for sub in ("prep", "build", "score"):
        (parent / sub).mkdir(parents=True)
    (parent / "submitted.json").write_text(json.dumps({"split": "dev"}))
    with pytest.raises(host.HostError, match="only a dev rehearsal"):
        host.make_plan(src, "r", "reserve", None, root, "dev-mutants-v9")
    plan = host.make_plan(src, "z", "dev", "dev-controls-v9", root, "dev-mutants-v9")
    assert [s["state"] for s in plan["steps"]] == ["done", "done", "done", "pending"]
    run_dir = root / "runs" / "z"
    run_dir.mkdir(parents=True)
    host.write_plan(run_dir, plan)
    monkeypatch.setattr(host, "queue_jobs", lambda: [])
    submitted = []
    monkeypatch.setattr(host, "sbatch", lambda c: submitted.append(c) or "77")
    host.main(["--root", str(root), "next", "--name", "z"])
    assert len(submitted) == 1 and "--job-name=q2zr-z-zinv" in submitted[0]
    export = next(a for a in submitted[0] if a.startswith("--export="))
    assert f"Q2M_EXTRA_RO={parent}/build:/ro/build+{parent}/score:/ro/score+" in export
    assert f"Q2M_RUN_DIR={run_dir}/zinv" in export
