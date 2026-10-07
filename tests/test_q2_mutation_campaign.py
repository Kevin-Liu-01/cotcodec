"""Tests for the Q2 mutation campaign driver (spec -> operator -> mutant -> save -> verdict).

The end-to-end test runs every stage of the campaign on a synthetic config
task with the real code: ``controls.make_jobs``, ``campaign targets`` (blind
spec YAML -> JSON), ``campaign build`` (planning from the spec, application,
purity against the null mutant), the reachability stage's ``run_job`` (a
fake office session; a JSON candidate is never opened by LibreOffice),
``campaign merge``, the ``offline_eval`` CLI (fresh processes, the offline
file-cache shim) against a stand-in ``desktop_env`` package, ``campaign
recheck`` and ``campaign report``. The office path needs the LO-VM image; it
is exercised on the development split on the host (see
``program/evidence/q2-mutation/integration/``).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from harness.q2_mutation import campaign, controls, offline_eval, reachability
from harness.q2_mutation.operators import _synth as synth
from harness.q2_mutation.operators import registry
from harness.q2_mutation.schema import (
    MutationResult,
    RequirementSpec,
    make_mutant_id,
    read_verdict_rows,
)
from harness.q2_mutation.tasks import FILE_CACHE_PREFIX, FILE_CACHE_REVISION

ROOT = Path(__file__).resolve().parents[1]
CACHE_URL = f"{FILE_CACHE_PREFIX}{FILE_CACHE_REVISION}"
SETTINGS = "/home/user/.config/Code/User/settings.json"

# A stand-in for OSWorld's DesktopEnv with one key-subset JSON checker. Like
# several real OSWorld config checkers it reads only the keys it was told to
# check, so unrequested edits elsewhere in the file pass.
FAKE_DESKTOP_ENV = """
import json
import os


class DesktopEnv:
    def _set_task_info(self, task_config):
        self.task_id = task_config["id"]
        self.cache_dir = os.path.join(self.cache_dir_base, self.task_id)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.evaluator = task_config["evaluator"]

    def evaluate(self):
        import requests

        ev = self.evaluator
        result = self.controller.get_file(ev["result"]["path"])
        if result is None:
            return 0.0
        gold = json.loads(requests.get(ev["expected"]["path"]).content)
        keys = ev["options"]["keys"]
        got = json.loads(result)
        return 1.0 if all(got.get(k) == gold.get(k) for k in keys) else 0.0
"""


# --------------------------------------------------------------------------- fixtures


def _config_task(task_id: str) -> dict[str, Any]:
    return {
        "id": task_id,
        "instruction": "Set the editor font size to 14.",
        "config": [
            {
                "type": "download",
                "parameters": {
                    "files": [{"url": f"{CACHE_URL}/vs_code/initial.json", "path": SETTINGS}]
                },
            }
        ],
        "evaluator": {
            "func": "check_json_settings_subset",
            "result": {"type": "vm_file", "path": SETTINGS, "dest": "settings.json"},
            "expected": {
                "type": "cloud_file",
                "path": f"{CACHE_URL}/vs_code/gold.json",
                "dest": "gold.json",
            },
            "options": {"keys": ["editor.fontSize"]},
        },
    }


class FakeLoSession:
    """The parts of ``reachability.LoSession`` that ``run_job`` uses for non-office files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.vm_root = root / "vm"
        self.log: list[dict[str, Any]] = []

    def reset(self) -> None:
        import shutil

        if self.root.exists():
            shutil.rmtree(self.root)
        self.vm_root.mkdir(parents=True)

    def host_path(self, vm_path: str) -> Path:
        return self.vm_root / reachability.resolve_vm_path(vm_path).lstrip("/")

    def open(self, vm_path: str) -> bool:  # pragma: no cover - must not be reached
        raise AssertionError(f"a JSON candidate was opened in LibreOffice: {vm_path}")

    def close(self) -> None:
        pass


@pytest.fixture
def config_world(tmp_path: Path) -> dict[str, Path | str]:
    task_id = synth.SYNTH_TASK_IDS["config"]
    osworld = tmp_path / "osworld"
    (osworld / "evaluation_examples" / "examples" / "vs_code").mkdir(parents=True)
    (osworld / "evaluation_examples" / "examples" / "vs_code" / f"{task_id}.json").write_text(
        json.dumps(_config_task(task_id)), encoding="utf-8"
    )
    (osworld / "desktop_env").mkdir()
    (osworld / "desktop_env" / "__init__.py").write_text("", encoding="utf-8")
    (osworld / "desktop_env" / "desktop_env.py").write_text(FAKE_DESKTOP_ENV, encoding="utf-8")
    cache = tmp_path / "file_cache"
    synth.build_json(cache / "vs_code" / "gold.json")
    synth.build_json(
        cache / "vs_code" / "initial.json", {**synth.SETTINGS_JSON, "editor.fontSize": 12}
    )
    src = tmp_path / "src"
    (src / campaign.SPECS_DIR).mkdir(parents=True)
    (src / campaign.SPLITS_PATH).write_text(json.dumps({"dev": [task_id]}), encoding="utf-8")
    (src / campaign.SPECS_DIR / f"{task_id}.yaml").write_text(
        yaml.safe_dump(synth.synthetic_spec("config"), sort_keys=False), encoding="utf-8"
    )
    return {"task_id": task_id, "osworld": osworld, "cache": cache, "src": src, "tmp": tmp_path}


# --------------------------------------------------------------------------- end to end


def test_campaign_end_to_end_on_a_config_task(config_world: dict[str, Any]) -> None:
    task_id = config_world["task_id"]
    tmp: Path = config_world["tmp"]
    osworld: Path = config_world["osworld"]
    cache: Path = config_world["cache"]

    # 1. Harness control jobs, then mutation targets with the blind spec.
    jobs, report = controls.make_jobs(osworld, cache, [task_id])
    assert report == {"no_gold": [], "gold_equals_initial": []}
    controls._write_jsonl(tmp / "control-jobs.jsonl", jobs)
    run = tmp / "run"
    prep = run / "prep"
    assert (
        campaign.main(
            [
                "targets",
                "--src",
                str(config_world["src"]),
                "--osworld",
                str(osworld),
                "--jobs",
                str(tmp / "control-jobs.jsonl"),
                "--split",
                "dev",
                "--out",
                str(prep),
            ]
        )
        == 0
    )
    targets = campaign.read_jsonl(prep / "targets.jsonl")
    assert [(t["task_id"], t["vm_path"], t["family"]) for t in targets] == [
        (task_id, SETTINGS, "config")
    ]
    assert targets[0]["initial"] is not None

    # 2. Build: plan from the spec only, apply, check purity, dedupe.
    build = run / "build"
    assert (
        campaign.main(["build", "--targets", str(prep / "targets.jsonl"), "--out", str(build)]) == 0
    )
    summary = json.loads((build / "build-summary.json").read_text())
    assert summary["targets_planned"] == 1
    assert summary["admitted"] > 0
    spec = RequirementSpec.from_dict(synth.synthetic_spec("config"))
    mutations = campaign.read_jsonl(build / "mutations.jsonl")
    for row in mutations:
        result = MutationResult.from_dict(row)
        result.check_against_spec(spec)
        assert result.mutant_id == make_mutant_id(task_id, result.operator, result.recipe)
        assert result.target_path_in_vm == SETTINGS
    labels = {r["label"] for r in mutations}
    assert {"should_fail_violation", "should_fail_extra_change", "should_pass_equiv"} <= labels
    scoring = campaign.read_jsonl(build / "scoring-jobs.jsonl")
    assert [j["kind"] for j in scoring].count("null") == 1
    admitted = {
        a["mutant_id"] for a in campaign.read_jsonl(build / "admission.jsonl") if a["admitted"]
    }
    assert {j["mutant_id"] for j in scoring if j["kind"] == "mutant"} == admitted

    # 3. Reachability stage (real run_job; a JSON file is never opened or saved).
    lo = build / "lo"
    raw = offline_eval.load_task(osworld, task_id)
    rows = []
    for job in scoring:
        row = reachability.run_job(FakeLoSession(tmp / "session"), job, raw, lo / "files")
        row["lo_build"] = "fake-office"
        rows.append(row)
        assert row["plan"]["agent_saves"] == [] and row["outputs"] == {}
    campaign.write_jsonl(lo / "reachability-0.jsonl", rows)

    # 4. Merge keeps MutationResult ids; nothing was saved.
    score = run / "score"
    saved = score / "jobs-saved.jsonl"
    assert (
        campaign.main(
            [
                "merge",
                "--jobs",
                str(build / "scoring-jobs.jsonl"),
                "--lo-rows",
                str(lo / "reachability-0.jsonl"),
                "--out",
                str(saved),
            ]
        )
        == 0
    )
    merged = campaign.read_jsonl(saved)
    assert {j["mutant_id"] for j in merged} == {j["mutant_id"] for j in scoring}
    assert {j["saved_via"] for j in merged} == {"none"}

    # 5. Score with the offline evaluator in fresh processes -> VerdictRow JSONL.
    requirements = tmp / "requirements.txt"
    requirements.write_text("fake==1\n", encoding="utf-8")
    assert (
        offline_eval.main(
            [
                "--jobs",
                str(saved),
                "--out",
                str(score / "mut-verdicts-lock.jsonl"),
                "--notes",
                str(score / "mut-notes-lock.jsonl"),
                "--osworld",
                str(osworld),
                "--file-cache",
                str(cache),
                "--requirements",
                str(requirements),
                "--dep-set",
                "lock",
                "--workers",
                "8",
                "--repeat",
                "1",
                "--timeout",
                "120",
            ]
        )
        == 0
    )
    verdicts = read_verdict_rows(
        (score / "mut-verdicts-lock.jsonl").read_text(encoding="utf-8").splitlines()
    )
    assert len(verdicts) == len(merged)
    lock_sha = hashlib.sha256(requirements.read_bytes()).hexdigest()
    assert all(v.venv_lock_sha256 == lock_sha and v.verdict != "error" for v in verdicts), [
        v.to_dict() for v in verdicts if v.verdict == "error"
    ]
    by_id = {v.mutant_id: v for v in verdicts}
    assert by_id[targets[0]["null_id"]].verdict == "pass"

    # 6. Purity re-check on the saved files, then the joined report.
    assert (
        campaign.main(
            [
                "recheck",
                "--mutations",
                str(build / "mutations.jsonl"),
                "--admission",
                str(build / "admission.jsonl"),
                "--saved-jobs",
                str(saved),
                "--out",
                str(score / "recheck.jsonl"),
            ]
        )
        == 0
    )
    probe = tmp / "probe.json"
    probe.write_text(json.dumps({"tasks": {}}), encoding="utf-8")
    assert (
        campaign.main(
            [
                "report",
                "--run",
                str(score),
                "--mutations",
                str(build / "mutations.jsonl"),
                "--admission",
                str(build / "admission.jsonl"),
                "--probe-touched",
                str(probe),
                "--n-boot",
                "200",
            ]
        )
        == 0
    )
    outcomes = campaign.read_jsonl(score / "outcomes.jsonl")
    assert len(outcomes) == len(mutations)
    for row in outcomes:
        if not row["admitted"]:
            assert row["lock_status"] == "not_admitted"
            continue
        assert row["post_save_admitted"] is True
        if row["label"] == "ambiguous":
            assert row["lock_status"] == "ambiguous"
            continue
        assert row["lock_status"] == "evaluable"
        expected = {
            "should_pass_equiv": "ok",
            "should_pass_alt_solution": "ok",
            # The checker reads only editor.fontSize: a violation of the bound
            # key fails, an unrequested edit elsewhere slips through.
            "should_fail_violation": "ok",
            "should_fail_extra_change": "FP_F",
        }[row["label"]]
        assert row["lock_event"] == expected, row
    summary = json.loads((score / "report.json").read_text())
    assert summary["rates_exploratory"]["FP_F"]["pooled"]["rate"] == 1.0
    assert summary["rates_exploratory"]["FP_R"]["pooled"]["rate"] == 0.0
    assert summary["task_escape"] == {"tasks": 1, "with_escape": 0}

    # 7. Release view: no mutant file, no long document text, ids still check.
    campaign.write_json(
        run / "submitted.json",
        {"run": "e2e", "split": "dev", "git_sha": "0" * 40, "jobs": [1, 2, 3]},
    )
    export = tmp / "export"
    assert campaign.main(["export", "--run", str(run), "--out", str(export)]) == 0
    manifest = json.loads((export / "manifest.json").read_text())
    assert manifest["confirmatory"] is False and manifest["split"] == "dev"
    assert set(manifest["exported_sha256"]) >= {
        "mutations.release.jsonl",
        "outcomes.jsonl",
        "verdicts-lock.jsonl",
        "report.json",
    }
    released = campaign.read_jsonl(export / "mutations.release.jsonl")
    assert [r["mutant_id"] for r in released] == [r["mutant_id"] for r in mutations]
    for row in released:
        assert row["mutant_id"].endswith(row["recipe_sha256"][:12])
        assert not _free_text_leaves(row["recipe_release"])
    assert all(p.is_file() for p in export.iterdir())


# --------------------------------------------------------------------------- units


def test_select_targets_skips_derived_and_unknown_files(monkeypatch: pytest.MonkeyPatch) -> None:
    task_id = "11111111-1111-4111-8111-111111111111"
    raw = {
        "evaluator": {
            "postconfig": [
                {
                    "type": "execute",
                    "parameters": {
                        "command": [
                            "libreoffice",
                            "--convert-to",
                            "csv:Text - txt - csv (StarCalc):44,34,UTF-8",
                            "--outdir",
                            "/home/user",
                            "/home/user/a.xlsx",
                        ]
                    },
                }
            ]
        }
    }
    jobs = [
        {
            "task_id": task_id,
            "kind": "gold",
            "files": {
                "/home/user/a.xlsx": "/cache/gold.xlsx",
                "/home/user/a.csv": "/cache/gold.csv",
                "/home/user/movie.mp4": "/cache/movie.mp4",
            },
        },
        {"task_id": task_id, "kind": "initial", "files": {"/home/user/a.xlsx": "/cache/i.xlsx"}},
    ]
    shas = {}

    def fake_sha(path: str) -> str:
        return shas.setdefault(path, hashlib.sha256(path.encode()).hexdigest())

    monkeypatch.setattr(campaign, "sha256_file", fake_sha)
    targets, skipped = campaign.select_targets(
        jobs, [task_id, "22222222-2222-4222-8222-222222222222"], {task_id: raw}
    )
    assert [t["vm_path"] for t in targets] == ["/home/user/a.xlsx"]
    assert targets[0]["initial"] == "/cache/i.xlsx"
    assert set(targets[0]["context_files"]) == {
        "/home/user/a.xlsx",
        "/home/user/a.csv",
        "/home/user/movie.mp4",
    }
    reasons = {(s["vm_path"], s["reason"].split(" ")[0]) for s in skipped}
    assert reasons == {
        ("/home/user/a.csv", "derived"),
        ("/home/user/movie.mp4", "no"),
        (None, "no"),
    }


FAKE_PINS = {key: f"pin-{key}" for key in campaign.PINNED_KEYS}


def _frozen_tree(tmp_path: Path, digest: str | None = None, pins: dict | None = None) -> Path:
    src = tmp_path / "src"
    prereg = src / campaign.PREREG_PATH
    prereg.parent.mkdir(parents=True)
    block = json.dumps({"q2m_pins": 1, **(pins or FAKE_PINS)}, indent=1)
    prereg.write_text(f"# frozen\n\n```json\n{block}\n```\n", encoding="utf-8")
    row = {
        "experiment_id": campaign.EXPERIMENT_ID,
        "path": campaign.PREREG_PATH,
        "sha256": digest or campaign.sha256_file(prereg),
        "previous_hash": campaign.LEDGER_GENESIS,
    }
    payload = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    row["hash"] = hashlib.sha256(payload).hexdigest()
    (src / campaign.LEDGER_PATH).write_text(json.dumps(row) + "\n", encoding="utf-8")
    return src


def test_split_guard_refuses_confirm_before_the_freeze(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("Q2M_PREREG_FROZEN", raising=False)
    monkeypatch.setattr(campaign, "pins", lambda root: dict(FAKE_PINS))
    assert campaign.require_split_allowed("dev", tmp_path) is None
    with pytest.raises(campaign.CampaignError, match="only after"):
        campaign.require_split_allowed("confirm", tmp_path)
    src = _frozen_tree(tmp_path)
    with pytest.raises(campaign.CampaignError, match="Q2M_PREREG_FROZEN"):
        campaign.require_split_allowed("confirm", src)
    monkeypatch.setenv("Q2M_PREREG_FROZEN", campaign.EXPERIMENT_ID)
    assert campaign.require_split_allowed("confirm", src)["experiment_id"] == campaign.EXPERIMENT_ID
    tampered = _frozen_tree(tmp_path / "t", digest="0" * 64)
    with pytest.raises(campaign.CampaignError, match="differs from its frozen digest"):
        campaign.require_split_allowed("reserve", tampered)
    drifted = _frozen_tree(tmp_path / "d", pins={**FAKE_PINS, "spec_set_sha256": "other"})
    with pytest.raises(campaign.CampaignError, match=r"pins: \['spec_set_sha256'\]"):
        campaign.require_split_allowed("confirm", drifted)


def test_prereg_pins_block_is_unique() -> None:
    one = '```json\n{"q2m_pins": 1, "a": 2}\n```\n'
    other = '```json\n{"x": 1}\n```\n'
    assert campaign.prereg_pins(other + one) == {"q2m_pins": 1, "a": 2}
    with pytest.raises(campaign.CampaignError, match="found 2"):
        campaign.prereg_pins(one + one)
    with pytest.raises(campaign.CampaignError, match="found 0"):
        campaign.prereg_pins(other)


def test_repository_split_guard_holds_until_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """The committed tree has no ledger row for this experiment: confirm stays closed."""
    monkeypatch.setenv("Q2M_PREREG_FROZEN", campaign.EXPERIMENT_ID)
    if campaign.frozen_ledger_row(ROOT) is not None:
        pytest.skip("frozen: the guard now checks the ledger digest instead")
    with pytest.raises(campaign.CampaignError):
        campaign.require_split_allowed("confirm", ROOT)


def test_probe_operator_map_covers_every_probe_and_names_real_operators() -> None:
    import fnmatch

    probe = json.loads((ROOT / campaign.PROBE_TOUCHED).read_text(encoding="utf-8"))
    cells = campaign.probe_touched_cells(probe)
    assert set(cells) == set(probe["tasks"])
    names = sorted(registry())
    for op, patterns in campaign.PROBE_OPERATOR_MAP.items():
        for pattern in patterns:
            assert any(fnmatch.fnmatchcase(name, pattern) for name in names), (op, pattern)
    seen = {op for info in probe["tasks"].values() for op in info["probes"]}
    assert seen <= set(campaign.PROBE_OPERATOR_MAP)
    with pytest.raises(campaign.CampaignError, match="no operator mapping"):
        campaign.probe_touched_cells({"tasks": {"t": {"probes": ["new:PROBE"]}}})


@pytest.mark.parametrize("probe", ["mutants:F-TYPO", "mutants_v2:F-TYPO-BODY", "mutants_v2:F-CELL"])
def test_unrelated_edit_probes_touch_every_extra_change_operator(probe: str) -> None:
    """The reviewer's case: an F-TYPO probe on a paragraph-blind checker predicts the
    outcome of deleting or reformatting an unrelated paragraph too."""
    cells = campaign.probe_touched_cells({"tasks": {"t": {"probes": [probe]}}})
    extra = [name for name in registry() if ".extra." in name]
    assert extra and all(campaign.is_probe_touched(cells, "t", name) for name in extra)
    assert not campaign.is_probe_touched(cells, "t", "docx.eq.view_zoom")


@pytest.mark.parametrize(
    ("label", "admitted", "post", "verdict", "null", "unstable", "expected"),
    [
        ("should_pass_equiv", False, None, None, None, False, ("not_admitted", None)),
        ("should_pass_equiv", True, None, "pass", "pass", False, ("not_scored", None)),
        ("should_pass_equiv", True, False, "pass", "pass", False, ("normalized", None)),
        ("should_pass_equiv", True, True, "pass", "fail", False, ("null_not_pass", None)),
        ("should_pass_equiv", True, True, "error", "pass", False, ("error", None)),
        ("should_pass_equiv", True, True, "fail", "pass", True, ("nondeterministic", None)),
        ("ambiguous", True, True, "fail", "pass", False, ("ambiguous", None)),
        ("should_pass_equiv", True, True, "fail", "pass", False, ("evaluable", "FN")),
        ("should_pass_equiv", True, True, "pass", "pass", False, ("evaluable", "ok")),
        ("should_pass_alt_solution", True, True, "fail", "pass", False, ("evaluable", "FN_alt")),
        ("should_fail_violation", True, True, "pass", "pass", False, ("evaluable", "FP_R")),
        ("should_fail_violation", True, True, "fail", "pass", False, ("evaluable", "ok")),
        ("should_fail_extra_change", True, True, "pass", "pass", False, ("evaluable", "FP_F")),
    ],
)
def test_classify(
    label: str,
    admitted: bool,
    post: bool | None,
    verdict: str | None,
    null: str | None,
    unstable: bool,
    expected: tuple[str, str | None],
) -> None:
    post_row = None if post is None else {"status": "checked", "post_save_admitted": post}
    verdict_row = None if verdict is None else {"verdict": verdict}
    null_row = None if null is None else {"verdict": null}
    assert campaign.classify(label, admitted, post_row, verdict_row, null_row, unstable) == expected


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        ({"save_failed": True}, "save_failed"),
        ({"unemulated": True}, "unemulated"),
        ({"infra_failed": True}, "infra_failed"),
        ({"save_failed": True, "infra_failed": True}, "save_failed"),
    ],
)
def test_classify_infrastructure_exclusions(flags: dict[str, bool], expected: str) -> None:
    post = {"status": "checked", "post_save_admitted": True}
    status = campaign.classify(
        "should_pass_equiv", True, post, {"verdict": "error"}, {"verdict": "pass"}, False, **flags
    )
    assert status == (expected, None)
    assert campaign.classify("should_pass_equiv", False, post, None, None, False, **flags) == (
        "not_admitted",
        None,
    )


def test_report_never_scores_an_unsaved_office_mutant() -> None:
    """The reviewer's reproduction: an office mutant whose save never ran is not evaluable."""
    task = "77777777-7777-4777-8777-777777777777"
    vm = "/home/user/Desktop/a.docx"

    def mutation(op: str, seed: int) -> dict[str, Any]:
        recipe = {"seed": seed, "input_sha256": "a" * 64, "params": {}}
        return {
            "mutant_id": make_mutant_id(task, op, recipe),
            "task_id": task,
            "operator": op,
            "family": "docx",
            "label": "should_pass_equiv",
            "witness": {"req_ids": ["R1"], "argument": "W-E-SILENT: x"},
            "purity_checks": [],
            "recipe": recipe,
            "target_path_in_vm": vm,
        }

    rows = [mutation("docx.eq.view_zoom", s) for s in (42, 43, 44)]
    ids = [r["mutant_id"] for r in rows]
    null = f"{task}__null__x"
    admission = [
        {"mutant_id": i, "target_id": f"{task}__x", "admitted": True, "failed_checks": []}
        for i in ids
    ]
    recheck = [
        {"mutant_id": i, "status": "checked", "post_save_admitted": True, "post_save_failed": []}
        for i in ids
    ]
    scoring = [
        {"mutant_id": i, "target_id": f"{task}__x", "kind": "mutant", "files": {vm: f"/f/{i}"}}
        for i in ids
    ] + [{"mutant_id": null, "target_id": f"{task}__x", "kind": "null", "files": {vm: "/n"}}]
    # ids[0]: merge excluded it (open failed); ids[1]: reached the scorer unsaved
    # (an older merge); ids[2]: saved and scored, but its scoring timed out.
    saved = [
        {**scoring[1], "saved_via": "none"},
        {**scoring[2], "saved_via": "gui_faithful_lo_save"},
        {**scoring[3], "saved_via": "gui_faithful_lo_save"},
    ]
    excluded = [{"mutant_id": ids[0], "kind": "save_failed", "reason": "open failed: x"}]
    verdict = {"checker_funcs": ["compare_docx_files"]}
    lock = {
        ids[1]: {**verdict, "verdict": "fail", "score": 0.0},
        ids[2]: {**verdict, "verdict": "error", "score": None},
        null: {**verdict, "verdict": "pass", "score": 1.0},
    }
    notes = {"lock": {ids[2]: {"mutant_id": ids[2], "infra_failed": True}}}
    outcomes, summary = campaign.build_report(
        rows,
        admission,
        recheck,
        {"lock": lock},
        notes,
        saved,
        {},
        excluded=excluded,
        scoring_jobs=scoring,
        n_boot=100,
    )
    status = {o["mutant_id"]: o["lock_status"] for o in outcomes}
    assert status == {ids[0]: "save_failed", ids[1]: "save_failed", ids[2]: "infra_failed"}
    assert summary["save_stage_exclusions"] == [{"mutant_id": ids[0], "kind": "save_failed"}]
    # The null mutant's save failing excludes every mutant of the target.
    _, summary = campaign.build_report(
        rows,
        admission,
        recheck,
        {"lock": lock},
        {},
        saved[:2],
        {},
        excluded=[{"mutant_id": null, "kind": "save_failed"}],
        scoring_jobs=scoring,
        n_boot=100,
    )
    assert summary["status"]["lock"] == {"save_failed": 3}
    # A task whose postconfig types a file name is excluded as unemulated.
    typed = [{**job, "save_stage_unemulated_writes": True} for job in saved]
    outcomes, summary = campaign.build_report(
        rows, admission, recheck, {"lock": lock}, {}, typed, {}, scoring_jobs=scoring, n_boot=100
    )
    assert {o["lock_status"] for o in outcomes} == {"save_failed", "unemulated"}
    assert summary["unemulated_tasks"] == [task]


def test_report_counts_escapes_flips_and_probe_cells() -> None:
    def mutation(task: str, op: str, label: str, seed: int) -> dict[str, Any]:
        recipe = {"seed": seed, "input_sha256": "a" * 64, "params": {}}
        return {
            "mutant_id": make_mutant_id(task, op, recipe),
            "task_id": task,
            "operator": op,
            "family": "xlsx",
            "label": label,
            "witness": {"req_ids": ["R1"], "argument": "W-R-PINNED: x"},
            "purity_checks": [],
            "recipe": recipe,
            "target_path_in_vm": "/home/user/a.xlsx",
        }

    t1, t2 = "44444444-4444-4444-8444-444444444444", "55555555-5555-4555-8555-555555555555"
    rows = [
        mutation(t1, "xlsx.viol.value_perturb", "should_fail_violation", 42),
        mutation(t1, "xlsx.eq.view_zoom", "should_pass_equiv", 42),
        mutation(t2, "xlsx.viol.value_perturb", "should_fail_violation", 42),
        mutation(t2, "xlsx.extra.edit_unrelated_value", "should_fail_extra_change", 42),
    ]
    admission = [
        {
            "mutant_id": r["mutant_id"],
            "target_id": f"{r['task_id']}__x",
            "admitted": True,
            "failed_checks": [],
        }
        for r in rows
    ]
    recheck = [
        {
            "mutant_id": r["mutant_id"],
            "status": "checked",
            "post_save_admitted": True,
            "post_save_failed": [],
        }
        for r in rows
    ]
    saved = [
        {
            "mutant_id": r["mutant_id"],
            "target_id": f"{r['task_id']}__x",
            "kind": "mutant",
            "saved_via": "gui_faithful_lo_save",
        }
        for r in rows
    ] + [
        {
            "mutant_id": f"{t}__null",
            "target_id": f"{t}__x",
            "kind": "null",
            "saved_via": "gui_faithful_lo_save",
        }
        for t in (t1, t2)
    ]

    def verdicts(passed: dict[str, bool]) -> dict[str, dict[str, Any]]:
        out = {
            k: {
                "verdict": "pass" if v else "fail",
                "score": float(v),
                "checker_funcs": ["compare_table"],
            }
            for k, v in passed.items()
        }
        out.update(
            {
                f"{t}__null": {"verdict": "pass", "score": 1.0, "checker_funcs": ["compare_table"]}
                for t in (t1, t2)
            }
        )
        return out

    lock = verdicts(
        {
            rows[0]["mutant_id"]: True,
            rows[1]["mutant_id"]: True,
            rows[2]["mutant_id"]: False,
            rows[3]["mutant_id"]: True,
        }
    )
    scout = verdicts(
        {
            rows[0]["mutant_id"]: False,
            rows[1]["mutant_id"]: True,
            rows[2]["mutant_id"]: False,
            rows[3]["mutant_id"]: True,
        }
    )
    probe_cells = {t2: ["xlsx.extra.*"]}
    outcomes, summary = campaign.build_report(
        rows,
        admission,
        recheck,
        {"lock": lock, "scout": scout},
        {},
        saved,
        probe_cells,
        n_boot=200,
    )
    events = {o["mutant_id"]: o["lock_event"] for o in outcomes}
    assert events[rows[0]["mutant_id"]] == "FP_R"
    assert events[rows[3]["mutant_id"]] == "FP_F"
    assert [o["probe_touched"] for o in outcomes] == [False, False, False, True]
    # The probe-touched F mutant is kept out of the confirmatory-style tables.
    assert summary["rates_exploratory"]["FP_F"]["pooled"] is None
    assert summary["rates_exploratory"]["FP_R"]["pooled"]["rate"] == 0.5
    assert summary["task_escape"] == {"tasks": 2, "with_escape": 1}
    assert summary["venv_disagreements"] == [rows[0]["mutant_id"]]
    assert summary["s5_unstable_at_repeat_5"] == {"lock": [], "scout": []}

    # S1 candidate rescored five times per venv (dependency_flips.py): the lock
    # venv's five scorings disagree, so it was scored nondeterministically and
    # leaves P2-P5 as S5 (``nondeterministic``), like a repeat-2 disagreement.
    # The null mutant of t2 agrees five times on a verdict other than its first
    # two scorings, so every mutant of that target is nondeterministic too.
    s1 = {
        "lock": {
            rows[0]["mutant_id"]: {"repeat_scores": [1.0, 1.0, 0.0, 1.0, 1.0]},
            f"{t2}__null": {"repeat_scores": [0.0] * 5, "repeat_errors": [None] * 5},
        },
        "scout": {rows[0]["mutant_id"]: {"repeat_scores": [0.0] * 5}},
    }
    outcomes, summary = campaign.build_report(
        rows,
        admission,
        recheck,
        {"lock": lock, "scout": scout},
        {},
        saved,
        probe_cells,
        s1_notes=s1,
        n_boot=200,
    )
    status = {o["mutant_id"]: (o["lock_status"], o["scout_status"]) for o in outcomes}
    assert status[rows[0]["mutant_id"]] == ("nondeterministic", "evaluable")
    assert status[rows[1]["mutant_id"]] == ("evaluable", "evaluable")
    assert status[rows[2]["mutant_id"]][0] == "nondeterministic"
    assert summary["s5_unstable_at_repeat_5"]["lock"] == sorted(
        [rows[0]["mutant_id"], f"{t2}__null"]
    )
    assert summary["s5_unstable_at_repeat_5"]["scout"] == []


def test_mutation_jobs_place_the_other_gold_files(tmp_path: Path) -> None:
    data = b"mutated"
    recipe = {"seed": 42, "input_sha256": "a" * 64, "params": {}}
    task = "33333333-3333-4333-8333-333333333333"
    mutant_id = make_mutant_id(task, "docx.viol.text_edit", recipe)
    local = tmp_path / mutant_id / "home/user/a.docx"
    local.parent.mkdir(parents=True)
    local.write_bytes(data)
    row = {
        "mutant_id": mutant_id,
        "task_id": task,
        "operator": "docx.viol.text_edit",
        "family": "docx",
        "label": "should_fail_violation",
        "witness": {"req_ids": ["R1"], "argument": "W-R-PINNED: x"},
        "purity_checks": [],
        "recipe": recipe,
        "target_path_in_vm": "/home/user/a.docx",
        "output_sha256": hashlib.sha256(data).hexdigest(),
    }
    context = {task: {"/home/user/a.docx": "/gold/a.docx", "~/b.docx": "/gold/b.docx"}}
    (job,) = controls.mutation_jobs([row], tmp_path, context=context)
    assert job["files"] == {"/home/user/a.docx": str(local), "/home/user/b.docx": "/gold/b.docx"}
    assert job["skip_reachability"] is False


def test_pins_name_the_catalog_specs_and_code_tree() -> None:
    from harness.q2_mutation.operators import catalog

    first = campaign.pins(ROOT)
    assert first == campaign.pins(ROOT)
    assert first["operator_catalog_sha256"] == catalog()["catalog_sha256"]
    assert first["specs"] == 205 and first["operators"] == 64
    assert len(first["code_tree_sha256"]) == 64


def _free_text_leaves(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _free_text_leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _free_text_leaves(item)]
    return [value] if isinstance(value, str) and campaign.needs_redaction(value) else []


def test_release_view_redacts_document_text() -> None:
    paragraph = "The Iliad is the teachers' favourite heroic epic, much like the Odyssey."
    cjk = "\u6587\u6863\u5185\u5bb9" * 10
    recipe = {
        "seed": 42,
        "input_sha256": "a" * 64,
        "params": {
            "expectation": {"must_equal": [["body/10/text", paragraph]], "allow": ["body/10/text"]},
            "facts": {"old": "Iliad", "new": "Iqiad", "text": cjk},
            "steps": [{"op": "docx.replace_text", "expect_sha256": "b" * 64, "new": "Iqiad"}],
        },
    }
    task = "66666666-6666-4666-8666-666666666666"
    record = {
        "mutant_id": make_mutant_id(task, "docx.viol.text_edit", recipe),
        "task_id": task,
        "operator": "docx.viol.text_edit",
        "family": "docx",
        "label": "should_fail_violation",
        "witness": {"req_ids": ["R1"], "argument": f"W-R-TEXT: replaces 'Iliad' in '{paragraph}'"},
        "purity_checks": [{"name": "applied", "passed": True, "detail": paragraph}],
        "recipe": recipe,
    }
    view = campaign.release_record(record)
    text = json.dumps(view, ensure_ascii=False)
    assert paragraph not in text and cjk not in text and "favourite heroic" not in text
    assert "'Iliad'" in view["witness"]["argument"]
    assert view["recipe_release"]["params"]["facts"]["new"] == "Iqiad"
    assert view["recipe_release"]["params"]["expectation"]["allow"] == ["body/10/text"]
    digest = view["recipe_release"]["params"]["expectation"]["must_equal"][0][1]
    assert digest == {
        "redacted_sha256": hashlib.sha256(paragraph.encode()).hexdigest(),
        "chars": len(paragraph),
    }
    assert view["purity_checks"] == [{"name": "applied", "passed": True}]
    record["recipe"] = {**recipe, "seed": 43}
    with pytest.raises(Exception, match="mutant_id|recipe"):
        campaign.release_record(record)


@pytest.mark.parametrize("apply_to", ["gold", "base"])
def test_build_wires_office_recipes_to_gold_or_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, apply_to: str
) -> None:
    """Office wiring without LibreOffice: a stand-in applier copies input to output."""
    task_id = synth.SYNTH_TASK_IDS["xlsx"]
    gold = synth.build_xlsx(tmp_path / "cache" / "gold.xlsx")
    initial = synth.build_xlsx(tmp_path / "cache" / "initial.xlsx", title="draft")
    spec_dir = tmp_path / "prep" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / f"{task_id}.json").write_text(json.dumps(synth.synthetic_spec("xlsx")))
    vm_path = "/home/user/Desktop/report.xlsx"
    target = {
        "target_id": campaign.target_id(task_id, vm_path),
        "null_id": campaign.null_id(task_id, vm_path),
        "task_id": task_id,
        "family": "xlsx",
        "vm_path": vm_path,
        "gold": str(gold),
        "gold_sha256": campaign.sha256_file(gold),
        "initial": str(initial),
        "initial_sha256": campaign.sha256_file(initial),
        "context_files": {vm_path: str(gold)},
        "spec_json": f"specs/{task_id}.json",
    }
    campaign.write_jsonl(tmp_path / "prep" / "targets.jsonl", [target])
    calls: dict[str, list[dict[str, Any]]] = {}

    def fake_uno(root: Path, rows: list, name: str, **_: Any) -> dict[str, dict[str, Any]]:
        calls[name] = list(rows)
        logs = {}
        for row in rows:
            src = Path(root, row["input"])
            assert campaign.sha256_file(src) == row.get("input_sha256", campaign.sha256_file(src))
            dst = Path(root, row["output"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            logs[row["mutant_id"]] = {"status": "ok", "lo_build": "stand-in"}
        return logs

    monkeypatch.setattr(campaign, "run_uno", fake_uno)
    out = tmp_path / "build"
    argv = ["build", "--targets", str(tmp_path / "prep" / "targets.jsonl"), "--out", str(out)]
    assert campaign.main([*argv, "--apply-to", apply_to]) == 0
    base = out / "prep" / target["target_id"] / "base" / "report.xlsx"
    null = out / campaign.mutant_file_rel(target["null_id"], vm_path)
    assert campaign.sha256_file(null) == campaign.sha256_file(base)
    applied = calls["apply"]
    assert applied, "no office recipe reached the applier"
    if apply_to == "gold":
        assert "null" not in calls or not calls["null"]
        assert {row["input"] for row in applied} == {str(gold)}
        assert {row["input_sha256"] for row in applied} == {target["gold_sha256"]}
    else:
        assert [row["input"] for row in calls["null"]] == [str(base.relative_to(out))]
        assert {row["input"] for row in applied} == {str(base.relative_to(out))}
    summary = json.loads((out / "build-summary.json").read_text())
    assert summary["apply_to"] == apply_to
    # Each admission row says what the steps edited: the gold or the base.
    admission = campaign.read_jsonl(out / "admission.jsonl")
    wanted = target["gold_sha256"] if apply_to == "gold" else campaign.sha256_file(base)
    assert {(a["applied_to"], a["applied_input_sha256"]) for a in admission} == {(apply_to, wanted)}
    mutations = campaign.read_jsonl(out / "mutations.jsonl")
    by_id = {a["mutant_id"]: a for a in admission}
    released = campaign.release_record(mutations[0], by_id[mutations[0]["mutant_id"]])
    assert released["applied_to"] == apply_to and released["applied_input_sha256"] == wanted
    assert released["recipe_release"]["input_sha256"] == campaign.sha256_file(base)
    # The stand-in made no edit, so every mutant fails edit_landed and none is admitted.
    assert summary["admitted"] == 0 and summary["planned"] == len(applied)


def test_ledger_chain_check_matches_preregister_and_refuses_tampering(tmp_path: Path) -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import preregister

    ledger = ROOT / campaign.LEDGER_PATH
    assert campaign.ledger_rows(ledger) == preregister.read_ledger(ledger)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    forged = json.loads(lines[0])
    forged["sha256"] = "0" * 64
    bad = tmp_path / "ledger.jsonl"
    bad.write_text("\n".join([json.dumps(forged), *lines[1:]]) + "\n", encoding="utf-8")
    with pytest.raises(campaign.CampaignError, match="row hash"):
        campaign.ledger_rows(bad)


def _inputs_world(tmp_path: Path) -> tuple[Path, Path]:
    src = tmp_path / "src"
    inputs = tmp_path / "inputs"
    for rel, text in {
        "OSWorld/desktop_env/evaluators/metrics/table.py": "def compare_table(): ...\n",
        "OSWorld/evaluation_examples/examples/calc/t.json": '{"id": "t"}\n',
        "OSWorld/README.md": "not pinned\n",
        "vm-baseline/home/user/.config/vlc/vlcrc": "[core]\n",
        "file_cache_1e112283/files/calc/t/gold.xlsx": "gold bytes",
    }.items():
        path = inputs / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    gold = inputs / "file_cache_1e112283/files/calc/t/gold.xlsx"
    receipts = src / campaign.FILE_CACHE_RECEIPTS
    receipts.parent.mkdir(parents=True)
    receipts.write_text(
        f"calc/t/gold.xlsx\t{gold.stat().st_size}\t{campaign.sha256_file(gold)}\t-\treused\n",
        encoding="utf-8",
    )
    block = json.dumps({"q2m_pins": 1, **campaign.input_digests(inputs)}, indent=1)
    prereg = src / campaign.PREREG_PATH
    prereg.parent.mkdir(parents=True)
    prereg.write_text(f"# draft\n\n```json\n{block}\n```\n", encoding="utf-8")
    return src, inputs


def test_guard_checks_the_mounted_inputs_against_the_pins(tmp_path: Path) -> None:
    src, inputs = _inputs_world(tmp_path)
    checked = campaign.check_inputs(src, inputs)
    assert checked["file_cache_files_verified"] == 1
    assert (
        campaign.main(["guard", "--split", "dev", "--src", str(src), "--inputs", str(inputs)]) == 0
    )
    # A README outside the pinned trees may change; a task config may not.
    (inputs / "OSWorld/README.md").write_text("changed\n", encoding="utf-8")
    campaign.check_inputs(src, inputs)
    (inputs / "OSWorld/evaluation_examples/examples/calc/t.json").write_text("{}\n")
    with pytest.raises(campaign.CampaignError, match="osworld_tree_sha256"):
        campaign.check_inputs(src, inputs)
    src, inputs = _inputs_world(tmp_path / "b")
    (inputs / "file_cache_1e112283/files/calc/t/gold.xlsx").write_text("gold bytez")
    with pytest.raises(campaign.CampaignError, match="file cache calc/t/gold.xlsx"):
        campaign.check_inputs(src, inputs)
    assert (
        campaign.main(["guard", "--split", "dev", "--src", str(src), "--inputs", str(inputs)]) == 2
    )


def test_pins_cover_the_probe_map_and_the_file_cache_receipts() -> None:
    assert {"probe_touched_sha256", "file_cache_receipts_sha256"} <= set(campaign.PINNED_KEYS)
    actual = campaign.pins(ROOT)
    assert actual["probe_touched_sha256"] == campaign.sha256_file(ROOT / campaign.PROBE_TOUCHED)
