import io
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

from harness.q2_mutation import controls, offline_eval, raters, reachability, stats, vm_injection
from harness.q2_mutation.tasks import FILE_CACHE_REVISION

CACHE = "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main"
TASK = "4188d3a4-077d-46b7-9c86-23e1a036f6c1"
CSV_FILTER = "csv:Text - txt - csv (StarCalc):44,34,UTF-8,,,,false,true,true,false,false,1"
UNZIP = "unzip /home/user/Desktop/z.zip -d /home/user/Desktop/ && rm -rf /home/user/Desktop/z.zip"
EXPORT = 'import time; import pyautogui; time.sleep(1);pyautogui.hotkey(["shift", "ctrl", "e"]);'

CALC_TASK = {
    "id": TASK,
    "config": [
        {
            "type": "download",
            "parameters": {"files": [{"url": f"{CACHE}/calc/a.xlsx", "path": "/home/user/a.xlsx"}]},
        },
        {"type": "open", "parameters": {"path": "/home/user/a.xlsx"}},
    ],
    "evaluator": {
        "postconfig": [
            {
                "type": "activate_window",
                "parameters": {"window_name": "a.xlsx - LibreOffice Calc", "strict": True},
            },
            {"type": "sleep", "parameters": {"seconds": 0.5}},
            {
                "type": "execute",
                "parameters": {
                    "command": ["python", "-c", 'import pyautogui; pyautogui.hotkey("ctrl", "s");']
                },
            },
            {
                "type": "execute",
                "parameters": {
                    "command": [
                        "libreoffice",
                        "--convert-to",
                        CSV_FILTER,
                        "--outdir",
                        "/home/user",
                        "/home/user/a.xlsx",
                    ]
                },
            },
        ],
        "func": ["compare_table", "check_x"],
        "result": [
            {"type": "vm_file", "path": "/home/user/a.xlsx", "dest": "a.xlsx"},
            {"type": "vm_file", "path": "/home/user/a.csv", "dest": "a.csv"},
        ],
        "expected": [
            {"type": "cloud_file", "path": f"{CACHE}/calc/gold.xlsx", "dest": "gold.xlsx"},
            {"type": "rule", "rules": {}},
        ],
    },
}


def _cache(tmp_path: Path) -> Path:
    root = tmp_path / "cache"
    (root / "calc").mkdir(parents=True)
    (root / "calc" / "a.xlsx").write_bytes(b"initial")
    (root / "calc" / "gold.xlsx").write_bytes(b"gold")
    return root


def test_vm_paths_cannot_escape(tmp_path: Path) -> None:
    root = tmp_path / "vm"
    root.mkdir()
    assert offline_eval.vm_to_host(root, "Desktop/x") == (root / "home/user/Desktop/x").resolve()
    assert offline_eval.vm_to_host(root, "/home/user/../../../x") == (root / "x").resolve()
    (root / "home").mkdir()
    (root / "home" / "link").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        offline_eval.vm_to_host(root, "/home/link/outside")


def test_offline_get_serves_only_pinned_cache(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    fetched: list[str] = []
    get = offline_eval.make_offline_get(cache, fetched)
    response = get(f"{CACHE}/calc/gold.xlsx", stream=True)
    assert b"".join(response.iter_content(2)) == b"gold"
    pinned = CACHE.replace("/main", f"/{FILE_CACHE_REVISION}")
    assert get(f"{pinned}/calc/a.xlsx").content == b"initial"
    for url in ("https://example.org/x", CACHE.replace("/main", "/deadbeef") + "/calc/a.xlsx"):
        with pytest.raises(offline_eval.OfflineNetworkRefused):
            get(url)
    with pytest.raises(offline_eval.OfflineNetworkRefused):
        get(f"{CACHE}/calc/../../outside")
    assert len(fetched) == 2


def test_setup_emulation_handles_file_steps_only(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    (cache / "t").mkdir(parents=True)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        data = b"prefs"
        info = tarfile.TarInfo(".thunderbird/prefs.js")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    (cache / "t" / "p.tar.gz").write_bytes(buffer.getvalue())
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("proj/main.py", "print(1)")
    (cache / "t" / "z.zip").write_bytes(zbuf.getvalue())
    raw = {
        "config": [
            {
                "type": "download",
                "parameters": {
                    "files": [
                        {"url": f"{CACHE}/t/p.tar.gz", "path": "/home/user/p.tar.gz"},
                        {"url": f"{CACHE}/t/z.zip", "path": "/home/user/Desktop/z.zip"},
                    ]
                },
            },
            {
                "type": "execute",
                "parameters": {
                    "command": [
                        "tar",
                        "-xzv",
                        "--recursive-unlink",
                        "-f",
                        "/home/user/p.tar.gz",
                        "-C",
                        "/home/user/",
                    ]
                },
            },
            {
                "type": "execute",
                "parameters": {
                    "command": [
                        "/bin/bash",
                        "-c",
                        UNZIP,
                    ]
                },
            },
            {"type": "execute", "parameters": {"command": "mkdir -p /home/user/data1"}},
            {"type": "execute", "parameters": {"command": ["pip", "install", "pygame"]}},
            {"type": "launch", "parameters": {"command": ["thunderbird"]}},
        ]
    }
    vm = tmp_path / "vm"
    vm.mkdir()
    report = offline_eval.build_initial_vm_root(raw, cache, vm)
    assert (vm / "home/user/.thunderbird/prefs.js").read_bytes() == b"prefs"
    assert (vm / "home/user/Desktop/proj/main.py").exists()
    assert not (vm / "home/user/Desktop/z.zip").exists()
    assert (vm / "home/user/data1").is_dir()
    assert report.setup_unemulated == ["pip install pygame"]
    assert report.unemulated_writes is True
    keys = offline_eval.build_initial_vm_root(
        {
            "config": [
                {
                    "type": "execute",
                    "parameters": {
                        "command": ["python", "-c", "import pyautogui; pyautogui.press('f11')"]
                    },
                }
            ]
        },
        cache,
        vm,
    )
    assert keys.setup_unemulated and keys.unemulated_writes is False


def test_score_job_marks_a_timeout_after_retries_as_infrastructure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def timed_out(*_args: object, **_kwargs: object) -> dict:
        calls.append(1)
        return {
            "score": None,
            "error": "Timeout after 1s",
            "infra_timeout": True,
            "notes": {},
            "seconds": 1.0,
        }

    monkeypatch.setattr(offline_eval, "score_once", timed_out)
    monkeypatch.setattr(
        offline_eval,
        "load_task",
        lambda *_: {"evaluator": {"func": "compare_table"}},
    )
    job = offline_eval.ScoreJob(mutant_id="m", task_id=TASK, files={})
    row, notes = offline_eval.score_job(
        job,
        osworld=tmp_path,
        file_cache=tmp_path,
        venv_lock_sha256="0" * 64,
        dep_set="lock",
        repeat=1,
    )
    assert len(calls) == 3  # one attempt and two retries
    assert row.verdict == "error" and notes["infra_failed"] is True and notes["infra_timeouts"] == 3


def test_stub_controller(tmp_path: Path) -> None:
    vm = tmp_path / "vm"
    (vm / "home/user").mkdir(parents=True)
    (vm / "home/user/a.txt").write_text("x")
    controller = offline_eval.StubController(vm)
    assert controller.get_file("/home/user/a.txt") == b"x"
    assert controller.get_file("/home/user/missing") is None
    assert controller.execute_python_command(
        "import os; print(os.path.expanduser('~/Desktop'))"
    ) == {"output": "/home/user/Desktop\n"}
    with pytest.raises(offline_eval.LiveStateRequired):
        controller.get_accessibility_tree()


def test_gold_pairs_and_initial_jobs(tmp_path: Path) -> None:
    pairs, complete = controls.gold_pairs(CALC_TASK)
    assert pairs == [("/home/user/a.xlsx", f"{CACHE}/calc/gold.xlsx")]
    assert complete is False  # a.csv has no gold: needs a constructed positive control
    single = {
        **CALC_TASK,
        "evaluator": {
            **CALC_TASK["evaluator"],
            "func": "compare_table",
            "result": CALC_TASK["evaluator"]["result"][0],
            "expected": CALC_TASK["evaluator"]["expected"][0],
        },
    }
    pairs, complete = controls.gold_pairs(single)
    assert complete is True
    assert controls.result_paths(CALC_TASK) == ["/home/user/a.csv", "/home/user/a.xlsx"]
    assert controls.initial_files(CALC_TASK, _cache(tmp_path))["/home/user/a.xlsx"].endswith(
        "a.xlsx"
    )


def test_merge_lo_excludes_infra_failures() -> None:
    jobs = [
        {"job_id": "t__gold", "mutant_id": "t__gold", "task_id": TASK, "files": {"/a": "/x"}},
        {"job_id": "t__initial", "mutant_id": "t__initial", "task_id": TASK, "files": {"/a": "/y"}},
    ]
    rows = [
        {
            "job_id": "t__gold",
            "outputs": {"/a": "/saved", "/a.csv": "/csv"},
            "lo_build": "7.3.7.2",
            "saves": [{"written": True}],
        },
        {"job_id": "t__initial", "infra_error": "Timeout"},
    ]
    merged, excluded = controls.merge_lo(jobs, rows)
    assert merged[0]["files"] == {"/a": "/saved", "/a.csv": "/csv"}
    assert merged[0]["saved_via"] == "gui_faithful_lo_save"
    assert merged[0]["mutant_id"] == "t__gold__lo"
    assert excluded == [
        {
            "job_id": "t__initial",
            "mutant_id": "t__initial",
            "kind": "infra_error",
            "reason": "Timeout",
        }
    ]


def _office_row(job_id: str, **changes: object) -> dict:
    row = {
        "job_id": job_id,
        "failures": [],
        "saves": [{"vm_path": "/home/user/a.docx", "written": True}],
        "outputs": {"/home/user/a.docx": f"/out/files/{job_id}/home/user/a.docx"},
        "events": [],
        "lo_build": "7.3.7.2",
        "plan": {"unemulated": []},
    }
    row.update(changes)
    return row


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        # What run_job returns when soffice never shows a window: no exception,
        # no save, a failure entry (the reviewer's reproduction).
        ({"failures": ["open failed: /home/user/a.docx"], "saves": [], "outputs": {}}, "open"),
        ({"failures": ["activate failed: a.docx - LibreOffice Writer"]}, "activate"),
        ({"saves": [{"vm_path": "/home/user/a.docx", "written": False}]}, "not written"),
        ({"saves": [], "outputs": {}}, "never saved"),
    ],
)
def test_merge_lo_excludes_office_files_whose_save_failed(changes: dict, reason: str) -> None:
    job = {
        "job_id": "T__op__abc",
        "mutant_id": "T__op__abc",
        "task_id": TASK,
        "files": {"/home/user/a.docx": "/out/files/T__op__abc/home/user/a.docx"},
    }
    merged, excluded = controls.merge_lo(
        [job], [_office_row(job["job_id"], **changes)], suffix=None
    )
    assert merged == []
    assert [(e["mutant_id"], e["kind"]) for e in excluded] == [("T__op__abc", "save_failed")]
    assert reason in excluded[0]["reason"]
    ok, none = controls.merge_lo([job], [_office_row(job["job_id"])], suffix=None)
    assert none == [] and ok[0]["saved_via"] == "gui_faithful_lo_save"


def test_save_failures_cover_conversions_and_skip_script_writers() -> None:
    files = {"/home/user/a.xlsx": "/m.xlsx", "/home/user/a.csv": "/gold.csv"}
    convert = {
        "event": "convert",
        "argv": [
            "libreoffice",
            "--convert-to",
            "csv",
            "--outdir",
            "/home/user",
            "/home/user/a.xlsx",
        ],
        "produced": [],
    }
    row = _office_row(
        "j", saves=[{"vm_path": "/home/user/a.xlsx", "written": True}], events=[convert]
    )
    assert reachability.save_failures(files, row) == [
        "conversion produced nothing: /home/user/a.xlsx"
    ]
    # Do-nothing without the source file: the VM's conversion also makes nothing.
    assert reachability.save_failures({"/home/user/a.csv": None}, {**row, "saves": []}) == []
    skipped = {"job_id": "j", "plan": {"skipped": "script_writer stratum"}, "saves": []}
    assert reachability.save_failures({"/home/user/a.docx": "/m.docx"}, skipped) == []
    assert reachability.save_failures(files, None) == ["no save-stage row"]


def test_step_may_write() -> None:
    assert reachability.step_may_write("pyautogui.write: import pyautogui; pyautogui.write('x')")
    assert reachability.step_may_write("pip install x")
    assert reachability.step_may_write("python3 -c with open('/home/user/t.py', 'w') as f: f")
    assert not reachability.step_may_write("postconfig close_window")
    assert not reachability.step_may_write("python -c import pyautogui; pyautogui.hotkey('f11')")


def test_reachability_plan_replays_postconfig() -> None:
    plan = reachability.build_plan(CALC_TASK, ["/home/user/a.xlsx"])
    kinds = [step["kind"] for step in plan["postconfig_steps"]]
    assert kinds == ["activate", "sleep", "key", "convert"]
    assert plan["postconfig_steps"][2]["arg"] == "ctrl+s"
    assert plan["open_before_postconfig"] == ["/home/user/a.xlsx"]
    assert plan["agent_saves"] == []
    convert = plan["postconfig_steps"][3]["argv"]
    assert CSV_FILTER in convert


def test_reachability_agent_save_when_no_postconfig() -> None:
    raw = {"evaluator": {"postconfig": []}}
    plan = reachability.build_plan(raw, ["/home/user/r.docx", "/home/user/out.png"])
    assert plan["agent_saves"] == ["/home/user/r.docx"]
    assert plan["saves_in_postconfig"] is False


def test_parse_execute_variants() -> None:
    steps = reachability.parse_execute(
        [
            "python3",
            "-c",
            EXPORT,
        ]
    )
    assert [(s.kind, s.arg, s.seconds) for s in steps] == [
        ("sleep", "", 1.0),
        ("key", "shift+ctrl+e", 0.0),
    ]
    enter = reachability.parse_execute(
        ["python3", "-c", 'import pyautogui; pyautogui.press(["enter"]);']
    )
    assert enter[0].arg == "enter"
    typed = reachability.parse_execute(["python3", "-c", 'import pyautogui; pyautogui.write("x")'])
    assert typed[0].kind == "unemulated"
    assert reachability.parse_execute(["rm", "-rf", "/x"])[0].kind == "metric_side"
    assert reachability.parse_execute(["pip", "install", "x"])[0].kind == "unemulated"
    assert reachability.window_title_for("/home/user/a.pptx") == "a.pptx - LibreOffice Impress"


def test_audit_sample_strata_probabilities_and_shams() -> None:
    cands = [
        raters.Candidate(f"m{i}", f"t{i % 5}", "should_pass_equiv", "pass") for i in range(300)
    ]
    cands += [
        raters.Candidate(f"d{i}", f"t{i % 5}", "should_pass_equiv", "fail") for i in range(10)
    ]
    cands += [raters.Candidate(f"a{i}", "t1", "should_pass_alt_solution", "pass") for i in range(3)]
    cands += [raters.Candidate("e0", "t1", "should_pass_equiv", "error")]
    # Violations are a census whatever the verdict, up to the cap of 200.
    cands += [
        raters.Candidate(f"v{i}", f"t{i % 7}", "should_fail_violation", "pass" if i % 4 else "fail")
        for i in range(250)
    ]
    sample = raters.draw_audit_sample(cands, seed=42)
    by = {}
    for item in sample:
        by.setdefault(item.stratum, []).append(item)
    assert len(by["alt_solution"]) == 3 and by["alt_solution"][0].inclusion_probability == 1.0
    assert len(by["violation"]) == 200
    assert by["violation"][0].inclusion_probability == pytest.approx(200 / 250)
    assert len(by["disagreement"]) == 10
    assert len(by["agreement"]) == 100
    assert by["agreement"][0].inclusion_probability == pytest.approx(100 / 300)
    assert len(by["sham"]) == 14  # ceil(10% of 313) = 32, capped at 2 per task (7 tasks)
    assert all(item.mutant_id != "e0" for item in sample)
    assert raters.draw_audit_sample(cands, seed=42) == sample


def test_violation_census_weights_every_violation_once() -> None:
    """At the expected confirm size every violation is audited at weight 1."""
    verdicts = ["pass"] * 9 + ["fail"] * 79
    cands = [
        raters.Candidate(f"v{i}", f"t{i % 17}", "should_fail_violation", verdict)
        for i, verdict in enumerate(verdicts)
    ]
    cands += [
        raters.Candidate(f"e{i}", f"u{i % 59}", "should_pass_equiv", "pass") for i in range(236)
    ]
    sample = raters.draw_audit_sample(cands, seed=42)
    violations = [s for s in sample if s.stratum == "violation"]
    assert len(violations) == 88 and {s.inclusion_probability for s in violations} == {1.0}
    assert not any(s.mutant_id.startswith("v") and s.stratum != "violation" for s in sample)


def test_packets_are_blind() -> None:
    item = raters.Sampled("m1", TASK, "agreement", 0.5)
    packet = raters.make_packet(
        item,
        instruction="Do X",
        initial_files=[{"path_in_vm": "/a", "sha256": "0"}],
        candidate_artifacts={"render_png": "r.png"},
        seed=42,
    )
    assert "m1" not in str(packet)
    with pytest.raises(ValueError, match="leaks"):
        raters.make_packet(
            item,
            instruction="Do X",
            initial_files=[],
            candidate_artifacts={"verdict": "pass"},
            seed=42,
        )
    assert sorted(raters.rater_order(["a", "b", "c"], "r1")) == ["a", "b", "c"]
    assert raters.RATERS[0]["provider"] != raters.RATERS[1]["provider"]
    assert raters.RATERS[1]["role"] == "independent"


def test_consensus_and_summary() -> None:
    assert raters.consensus("accept", "accept") == "accept"
    assert raters.consensus("accept", "reject") == "unresolved"
    assert raters.consensus("unsure", "unsure") == "unresolved"
    assert raters.label_is_wrong("should_fail_violation", "accept") is True
    assert raters.label_is_wrong("should_pass_equiv", "accept") is False
    sample = [raters.Sampled(f"m{i}", f"t{i}", "agreement", 0.5) for i in range(6)]
    sample.append(raters.Sampled("s1", "t0", "sham", 1.0, sham="gold"))
    labels = {f"m{i}": "should_fail_violation" for i in range(6)}
    ratings = {f"m{i}": ("reject", "reject") for i in range(5)}
    ratings["m5"] = ("accept", "reject")
    ratings["s1"] = ("accept", "reject")
    summary = raters.summarize(sample, labels, ratings, n_boot=200)
    assert summary.n_unresolved == 1
    # The unresolved item counts as a label error until Kevin adjudicates it;
    # dropping it is only the sensitivity estimate.
    group = "should_fail_violation"
    assert summary.label_error[group].estimate == pytest.approx(1 / 6)
    assert summary.label_error_resolved_only[group].estimate == 0.0
    assert summary.label_error_unresolved_as_wrong[group] == pytest.approx(1 / 6)
    assert summary.sham_accuracy == {"model-rater-anthropic": 1.0, "model-rater-open-weight": 0.0}
    # Each rater on its own: the dissent of one rater stays visible.
    assert summary.per_rater["model-rater-anthropic"][group]["contradicts_label"] == (
        pytest.approx(1 / 6)
    )
    assert summary.per_rater["model-rater-open-weight"][group]["contradicts_label"] == 0.0
    # Six items on six tasks are too few to audit a group: K3 fires; the
    # equivalence group has no item at all and fires as well.
    assert summary.k3[group].sufficient is False
    assert summary.k3_fires == {"should_pass_equiv": True, "should_fail_violation": True}
    assert summary.k3["should_pass_equiv"] is None
    assert summary.decisions["m5"] == "unresolved"
    adjudicated = raters.summarize(
        sample, labels, ratings, adjudicated={"m5": "reject"}, n_boot=200
    )
    assert adjudicated.n_adjudicated == 1
    assert adjudicated.label_error[group].estimate == 0.0
    assert adjudicated.decisions["m5"] == "reject"
    with pytest.raises(ValueError, match="accept or reject"):
        raters.summarize(sample, labels, ratings, adjudicated={"m5": "unsure"}, n_boot=200)


def test_k3_groups_are_the_ungated_label_classes() -> None:
    """Rejected alternative solutions never fire K3; they are S6 and gate P2."""
    sample, labels, ratings = [], {}, {}
    for i in range(40):
        key = f"e{i}"
        sample.append(raters.Sampled(key, f"t{i % 10}", "agreement", 1.0))
        labels[key], ratings[key] = "should_pass_equiv", ("accept", "accept")
    for i in range(40):
        key = f"v{i}"
        sample.append(raters.Sampled(key, f"t{i % 10}", "agreement", 1.0))
        labels[key], ratings[key] = "should_fail_violation", ("reject", "reject")
    for i in range(30):  # every alternative solution rejected by both raters
        key = f"a{i}"
        sample.append(raters.Sampled(key, f"t{i % 10}", "alt_solution", 1.0))
        labels[key], ratings[key] = "should_pass_alt_solution", ("reject", "reject")
    for i in range(4):
        key = f"x{i}"
        sample.append(raters.Sampled(key, f"t{i}", "disagreement", 1.0))
        labels[key] = "should_fail_extra_change"
        ratings[key] = ("reject", "reject") if i < 3 else ("accept", "reject")
    sample.append(raters.Sampled("t1__p1_flip", "t1", "p1_flip", 1.0))
    ratings["t1__p1_flip"] = ("accept", "accept")
    summary = raters.summarize(sample, labels, ratings, n_boot=200)
    assert set(summary.k3) == {"should_pass_equiv", "should_fail_violation"}
    assert summary.k3_fires == {"should_pass_equiv": False, "should_fail_violation": False}
    assert summary.k4_fires is False
    alt = summary.by_label_class["should_pass_alt_solution"]
    assert alt["n"] == 30 and alt["reject"] == 30 and alt["gate_share"] == 0.0
    extra = summary.by_label_class["should_fail_extra_change"]
    assert extra["reject"] == 3 and extra["unresolved"] == 1
    assert extra["gate_share"] == pytest.approx(0.75)
    assert summary.p1_flips == {"t1__p1_flip": "accept"}
    assert summary.decisions["a0"] == "reject" and summary.decisions["x3"] == "unresolved"


def test_kappa_below_threshold_fires_both_groups() -> None:
    sample, labels, ratings = [], {}, {}
    for i in range(60):
        key = f"e{i}"
        sample.append(raters.Sampled(key, f"t{i % 12}", "agreement", 1.0))
        labels[key] = "should_pass_equiv" if i % 2 else "should_fail_violation"
        ratings[key] = ("accept", "reject") if i % 3 == 0 else ("unsure", "accept")
    summary = raters.summarize(sample, labels, ratings, n_boot=100)
    assert summary.kappa is not None and summary.kappa < raters.KAPPA_MIN
    assert summary.kappa_fires and all(summary.k3_fires.values())


@pytest.mark.parametrize(
    ("text", "answer", "status"),
    [
        ("accept. The table matches.", "accept", "ok"),
        ("**Reject** - cell B2 was changed.", "reject", "ok"),
        ("  Unsure: the render is blank", "unsure", "ok"),
        ("- accept", "accept", "ok"),
        ("Answer: accept", "unsure", "unparseable"),
        ("I would accept this.", "unsure", "unparseable"),
        ("acceptable", "unsure", "unparseable"),
        ("", "unsure", "empty"),
        (None, "unsure", "empty"),
        ("123", "unsure", "unparseable"),
    ],
)
def test_first_token_rule(text: str | None, answer: str, status: str) -> None:
    assert raters.parse_first_token(text) == (answer, status)


def test_non_answers_map_to_unsure() -> None:
    for outcome in (
        "refusal",
        "timeout",
        "transport_exhausted",
        "request_rejected",
        "malformed_response",
        "unrated",
    ):
        assert raters.answer_for(outcome, "accept") == ("unsure", outcome)
    assert raters.answer_for("ok", "reject because") == ("reject", "ok")
    with pytest.raises(ValueError, match="unknown call outcome"):
        raters.answer_for("weird", None)


def test_audit_pool_and_sampler_add_p1_flips() -> None:
    outcomes = [
        {"mutant_id": "m1", "task_id": "t1", "label": "should_pass_equiv",
         "lock_status": "evaluable", "lock_verdict": "pass", "probe_touched": False},
        {"mutant_id": "m2", "task_id": "t1", "label": "should_pass_equiv",
         "lock_status": "evaluable", "lock_verdict": "fail", "probe_touched": True},
        {"mutant_id": "m3", "task_id": "t2", "label": "should_fail_violation",
         "lock_status": "null_not_pass", "lock_verdict": "fail", "probe_touched": False},
        {"mutant_id": "m4", "task_id": "t2", "label": "should_fail_violation",
         "lock_status": "evaluable", "lock_verdict": "pass", "probe_touched": False},
    ]
    pool = raters.audit_candidates(outcomes)
    assert [c.mutant_id for c in pool] == ["m1", "m4"]
    sample = raters.draw_audit_sample(pool, p1_flip_tasks=["t9", "t9"])
    strata = {s.mutant_id: s.stratum for s in sample}
    assert strata["m1"] == "agreement" and strata["m4"] == "violation"
    assert strata["t9__p1_flip"] == "p1_flip"
    assert sum(1 for s in sample if s.stratum == "sham") == 1


def test_k3_bound_fires_without_observed_errors_when_the_sample_is_small() -> None:
    """The reviewer's case: 6 items on 3 tasks, 0 errors gave a [0, 0] interval."""
    small = [stats.AuditItem(f"m{i}", f"t{i % 3}", "agreement", 1.0, False) for i in range(6)]
    assert stats.audit_label_error(small, n_boot=200).high == 0.0
    bound = stats.label_error_bound(small, n_boot=200)
    assert bound.upper == pytest.approx(stats.exact_upper_bound(0, 6)) and bound.upper > 0.3
    assert bound.sufficient is False
    # 40 items, one error, inclusion probability 0.25: the bootstrap said 0.075;
    # the exact one-sided 95% bound is 0.113 (two-sided limit 0.132) and fires K3.
    items = [stats.AuditItem(f"m{i}", f"t{i % 10}", "agreement", 0.25, i == 0) for i in range(40)]
    bound = stats.label_error_bound(items, n_boot=2000)
    assert bound.kish_n == pytest.approx(40.0)
    assert bound.exact_high == pytest.approx(0.1132, abs=1e-3)
    assert stats.clopper_pearson(1, 40)[1] == pytest.approx(0.1316, abs=1e-3)
    assert bound.upper > stats.K3_THRESHOLD and bound.sufficient
    clean = [stats.AuditItem(f"m{i}", f"t{i % 10}", "agreement", 1.0, False) for i in range(40)]
    assert stats.label_error_bound(clean, n_boot=200).upper < stats.K3_THRESHOLD


def test_injection_plan_order_and_tamper() -> None:
    plan = vm_injection.build_injection_plan(
        CALC_TASK, {"/home/user/a.xlsx": {"local": "/m.xlsx", "sha256": "f" * 64}}, "c" * 64
    )
    ops = [step["op"] for step in plan]
    assert (
        ops.index("kill_process")
        < ops.index("upload")
        < ops.index("config_step")
        < ops.index("postconfig")
    )
    # The scoping protocol: inject while the document is open, then postconfig.
    broken = [s for s in plan if s["op"] not in ("kill_process",)]
    broken.insert(len(broken) - 2, {"op": "kill_process", "name": "soffice"})
    with pytest.raises(vm_injection.InjectionPlanError):
        vm_injection.check_plan(broken)
    reordered = list(plan)
    upload = next(i for i, s in enumerate(reordered) if s["op"] == "upload")
    reopen = next(i for i, s in enumerate(reordered) if s["op"] == "config_step")
    reordered[upload], reordered[reopen] = reordered[reopen], reordered[upload]
    with pytest.raises(vm_injection.InjectionPlanError):
        vm_injection.check_plan(reordered)


def test_injection_plan_opens_agent_created_outputs_before_the_postconfig_save() -> None:
    """The reviewer's case: a target absent from the initial state is never opened by a
    config step, so the postconfig's Ctrl+S cannot reach it unless the plan opens it."""
    target = "/home/user/Desktop/report.docx"
    raw = {
        "id": TASK,
        "config": [{"type": "launch", "parameters": {"command": ["libreoffice", "--writer"]}}],
        "evaluator": {
            "postconfig": [
                {
                    "type": "activate_window",
                    "parameters": {
                        "window_name": "report.docx - LibreOffice Writer",
                        "strict": True,
                    },
                },
                {"type": "sleep", "parameters": {"seconds": 0.5}},
                {
                    "type": "execute",
                    "parameters": {
                        "command": [
                            "python",
                            "-c",
                            "import pyautogui; pyautogui.hotkey('ctrl', 's')",
                        ]
                    },
                },
            ]
        },
    }
    plan = vm_injection.build_injection_plan(
        raw, {target: {"local": "/m.docx", "sha256": "f" * 64}}, "c" * 64
    )
    ops = [step["op"] for step in plan]
    assert "config_step" not in ops
    assert ops.index("upload") < ops.index("open_file") < ops.index("postconfig")
    opened = plan[ops.index("open_file")]
    assert opened == {
        "op": "open_file",
        "path": target,
        "window": "report.docx - LibreOffice Writer",
    }
    assert plan[-2]["expect_changed"] == [target]
    assert plan[-1]["save_paths"] == {target: "postconfig_save"}
    # The same plan without the open step is refused.
    with pytest.raises(vm_injection.InjectionPlanError, match="nothing opened"):
        vm_injection.check_plan([step for step in plan if step["op"] != "open_file"])
    # Without a postconfig save, the target gets an agent-equivalent save, as offline.
    unsaved = {**raw, "evaluator": {"postconfig": []}}
    plan = vm_injection.build_injection_plan(
        unsaved, {target: {"local": "/m.docx", "sha256": "f" * 64}}, "c" * 64
    )
    assert [s for s in plan if s["op"] == "agent_save"] == [
        {"op": "agent_save", "path": target, "window": "report.docx - LibreOffice Writer"}
    ]
    assert plan[-1]["save_paths"] == {target: "agent_save"}
    with pytest.raises(vm_injection.InjectionPlanError, match="agent-equivalent"):
        vm_injection.check_plan([step for step in plan if step["op"] != "agent_save"])
    png = vm_injection.build_injection_plan(
        unsaved, {"/home/user/out.png": {"local": "/o.png", "sha256": "f" * 64}}, "c" * 64
    )
    assert png[-1]["save_paths"] == {"/home/user/out.png": "no_save"}


def test_postconfig_file_steps_write_stdout_to_cache(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    (cache / "t").mkdir(parents=True)
    (cache / "t" / "inv.pdf").write_bytes(b"same")
    vm = tmp_path / "vm"
    (vm / "home/user/r").mkdir(parents=True)
    (vm / "home/user/r/inv.pdf").write_bytes(b"same")
    raw = {
        "evaluator": {
            "postconfig": [
                {"type": "activate_window", "parameters": {"window_name": "x"}},
                {
                    "type": "execute",
                    "parameters": {
                        "command": [
                            "python",
                            "-c",
                            "import pyautogui; pyautogui.hotkey('ctrl', 's')",
                        ]
                    },
                },
                {
                    "type": "download",
                    "parameters": {
                        "files": [{"path": "/home/user/.inv.pdf", "url": f"{CACHE}/t/inv.pdf"}]
                    },
                },
                {
                    "type": "execute",
                    "parameters": {
                        "command": ["diff", ".inv.pdf", "/home/user/r/inv.pdf"],
                        "stdout": "diff.out",
                    },
                },
                {
                    "type": "execute",
                    "parameters": {"command": ["ls", "-R", "/home/user/r"], "stdout": "ls.out"},
                },
                {"type": "execute", "parameters": {"command": ["pip", "install", "x.whl"]}},
            ]
        }
    }
    out = tmp_path / "taskcache"
    out.mkdir()
    unemulated = offline_eval.apply_postconfig_file_steps(raw, cache, vm, out)
    assert (out / "diff.out").read_text() == ""
    listing = (out / "ls.out").read_text()
    # GNU ls -R prints a "/home/user/r:" header (the VM and the container use
    # GNU ls); BSD ls does not. Either way the host prefix never leaks.
    assert "inv.pdf" in listing
    assert str(tmp_path.resolve()) not in listing and str(tmp_path) not in listing
    assert unemulated == ["pip install x.whl"]
    (vm / "home/user/r/inv.pdf").write_bytes(b"changed")
    offline_eval.apply_postconfig_file_steps(raw, cache, vm, out)
    assert (out / "diff.out").read_text() != ""


def test_relational_expected_is_not_a_gold() -> None:
    raw = {
        "config": [
            {
                "type": "download",
                "parameters": {
                    "files": [{"url": f"{CACHE}/g/berry.jpeg", "path": "/home/user/b.png"}]
                },
            }
        ],
        "evaluator": {
            "func": "check_image_mirror",
            "expected": {"type": "cloud_file", "path": f"{CACHE}/g/berry.jpeg", "dest": "b.png"},
            "result": {"type": "vm_file", "path": "/home/user/b_mirror.png", "dest": "m.png"},
        },
    }
    assert controls.gold_pairs(raw) == ([], False)


def test_overlay_skips_top_level_files(tmp_path: Path) -> None:
    source = tmp_path / "baseline"
    (source / "home/user/.config/vlc").mkdir(parents=True)
    (source / "home/user/.config/vlc/vlcrc").write_text("x")
    (source / "baseline.sha256").write_text("y")
    vm = tmp_path / "vm"
    assert offline_eval.overlay_tree(source, vm) == 1
    assert (vm / "home/user/.config/vlc/vlcrc").exists() and not (vm / "baseline.sha256").exists()


def test_report_aggregate_counts_fixed_point_and_flips() -> None:
    from harness.q2_mutation import report

    def v(verdict: str, score: float | None) -> dict:
        return {"verdict": verdict, "score": score, "error": None}

    tasks = {
        "t1": {
            "gold_raw_lock": v("pass", 1.0),
            "initial_raw_lock": v("fail", 0.0),
            "gold_saved_lock": v("fail", 0.0),
            "gold_raw_scout": v("pass", 1.0),
            "initial_raw_scout": v("pass", 1.0),
            "gold_save": {
                "placed_office": ["/home/user/a.docx"],
                "saves": [
                    {"written": True, "changed": True, "seconds_to_write": 0.8, "dialogs": []}
                ],
            },
        },
        "t2": {
            "gold_raw_lock": v("pass", 1.0),
            "initial_raw_lock": v("fail", 0.0),
            "gold_saved_lock": v("pass", 1.0),
            "gold_save": {"placed_office": ["/home/user/b.xlsx"], "saves": [], "save_failures": []},
        },
        # The gold's save never happened: its "saved" verdict is on pre-save
        # bytes and must not count as a fixed-point outcome.
        "t3": {
            "gold_raw_lock": v("pass", 1.0),
            "initial_raw_lock": v("fail", 0.0),
            "gold_saved_lock": v("fail", 0.0),
            "gold_save": {
                "placed_office": ["/home/user/a.docx"],
                "saves": [],
                "save_failures": ["open failed: /home/user/a.docx"],
            },
        },
        # A text gold: the save stage cannot change it, so it is not exposed
        # and never a P1 outcome (it still counts for K1).
        "t6": {
            "gold_raw_lock": v("pass", 1.0),
            "initial_raw_lock": v("fail", 0.0),
            "gold_saved_lock": v("pass", 1.0),
            "gold_save": {"placed_office": [], "saves": [], "save_failures": []},
        },
        # A postconfig types a file name the harness cannot replay: excluded.
        "t4": {
            "gold_raw_lock": v("fail", 0.0),
            "initial_raw_lock": v("fail", 0.0),
            "gold_saved_lock": v("fail", 0.0),
            "gold_save": {"saves": [], "save_failures": [], "unemulated_writes": True},
        },
        # The do-nothing scoring timed out after its retries: not a K1 outcome.
        "t5": {
            "gold_raw_lock": v("pass", 1.0),
            "initial_raw_lock": {**v("error", None), "infra_failed": True},
        },
    }
    out = report.aggregate(tasks)
    assert out["excluded_unemulated"] == ["t4"]
    assert out["lock"]["k1_gold_pass_and_do_nothing_fail"] == "4/4"
    assert out["lock"]["k1_infra_excluded"] == 1
    assert out["lock"]["gold_fixed_point_flips"] == 1 and out["lock"]["gold_fixed_point_n"] == 2
    assert out["lock"]["gold_save_failed"] == ["t3"]
    assert out["lock"]["gold_fixed_point_not_exposed"] == ["t5", "t6"]
    assert out["lock"]["gold_fixed_point_not_counted"] == ["t3"]
    assert report.p1_flip_tasks(tasks) == ["t1"]
    low, high = out["lock"]["gold_fixed_point_flip_clopper_pearson95"]
    assert low == pytest.approx(0.0126, abs=1e-3) and high == pytest.approx(0.9874, abs=1e-3)
    assert [f["candidate"] for f in out["dependency_flips"]] == ["initial_raw"]
    tasks["t1"]["initial_raw_scout"] = {**v("pass", 1.0), "nondeterministic": True}
    again = report.aggregate(tasks)
    assert again["dependency_flips"] == []
    assert again["venv_differences_from_nondeterministic_checkers"] == [
        {"task_id": "t1", "candidate": "initial_raw"}
    ]
    assert out["saves"] == {
        "n": 1,
        "written": 1,
        "changed_bytes": 1,
        "slower_than_0_5s": 1,
        "with_dialog": 0,
    }


def test_merge_lo_marks_untouched_jobs_unsaved() -> None:
    jobs = [
        {"job_id": "t__gold", "mutant_id": "t__gold", "task_id": TASK, "files": {"/a.png": "/x"}}
    ]
    rows = [{"job_id": "t__gold", "outputs": {}, "lo_build": "7.3.7.2", "saves": [], "events": []}]
    merged, _ = controls.merge_lo(jobs, rows)
    assert merged[0]["saved_via"] == "none" and merged[0]["lo_build"] is None


def test_derived_outputs_of_convert() -> None:
    argv = [
        "libreoffice",
        "--convert-to",
        CSV_FILTER,
        "--outdir",
        "/home/user",
        "/home/user/a.xlsx",
    ]
    assert reachability.derived_outputs(argv) == [("/home/user", "a", "csv")]
    assert reachability.derived_outputs(["libreoffice", "--headless"]) == []


def test_file_only_postconfig_is_metric_side() -> None:
    plan = reachability.build_plan(
        {
            "evaluator": {
                "postconfig": [
                    {"type": "download", "parameters": {"files": []}},
                    {
                        "type": "execute",
                        "parameters": {"command": ["diff", "a", "b"], "stdout": "d"},
                    },
                    {"type": "close_window", "parameters": {"window_name": "x"}},
                ]
            }
        },
        [],
    )
    assert plan["metric_side"] == ["postconfig download", "diff a b"]
    assert plan["unemulated"] == ["postconfig close_window"]


def test_packet_artifacts_for_text_and_binary(tmp_path: Path) -> None:
    from harness.q2_mutation import packets

    before = tmp_path / "a.json"
    before.write_text('{"x": 1}\n')
    after = tmp_path / "b.json"
    after.write_text('{"x": 2}\n')
    blob = tmp_path / "c.png"
    blob.write_bytes(b"\x89PNG")
    out = packets.artifacts(
        {"/home/user/a.json": str(before)},
        {"/home/user/a.json": str(after), "/home/user/c.png": str(blob), "/home/user/gone": None},
    )
    assert '-{"x": 1}' in out["/home/user/a.json"]["diff_vs_initial"]
    assert out["/home/user/c.png"]["diff_vs_initial"] == ["new file"]
    assert out["/home/user/c.png"]["structure"][0].startswith("binary .png: 4 bytes")
    assert out["/home/user/gone"]["structure"] == ["file absent in the end state"]
    assert "gold" not in json.dumps(out)
    cmds = packets.render_command("/w/x.docx", "/w/r", "/w/h")
    assert cmds[0][-1] == "/w/x.docx" and cmds[1][0] == "pdftoppm"


def test_make_jobs_skips_gold_identical_to_initial(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    (cache / "x").mkdir(parents=True)
    (cache / "x" / "in.pptx").write_bytes(b"same")
    (cache / "x" / "gold.pptx").write_bytes(b"same")
    (cache / "x" / "real_gold.pptx").write_bytes(b"answer")
    osworld = tmp_path / "osw"
    tasks_dir = osworld / "evaluation_examples" / "examples" / "libreoffice_impress"
    tasks_dir.mkdir(parents=True)
    ids = [f"{n:08x}-0000-4000-8000-000000000000" for n in (1, 2)]
    for task_id, gold in zip(ids, ("gold.pptx", "real_gold.pptx"), strict=True):
        raw = {
            "id": task_id,
            "config": [
                {
                    "type": "download",
                    "parameters": {
                        "files": [{"url": f"{CACHE}/x/in.pptx", "path": "/home/user/a.pptx"}]
                    },
                }
            ],
            "evaluator": {
                "func": "compare_pptx_files",
                "result": {"type": "vm_file", "path": "/home/user/a.pptx", "dest": "a.pptx"},
                "expected": {"type": "cloud_file", "path": f"{CACHE}/x/{gold}", "dest": "g.pptx"},
            },
        }
        (tasks_dir / f"{task_id}.json").write_text(json.dumps(raw))
    jobs, report = controls.make_jobs(osworld, cache, ids)
    assert report["gold_equals_initial"] == [ids[0]]
    assert [job["job_id"] for job in jobs] == [
        f"{ids[0]}__initial",
        f"{ids[1]}__gold",
        f"{ids[1]}__initial",
    ]


def test_mutation_jobs_follow_the_shared_file_convention(tmp_path: Path) -> None:
    import hashlib

    from harness.q2_mutation import schema

    data = b"mutant bytes"
    recipe = {"seed": 42, "input_sha256": "a" * 64, "params": {"cell": "B2"}}
    mutant_id = schema.make_mutant_id(TASK, "S-R1", recipe)
    target = "/home/user/a.xlsx"
    path = tmp_path / mutant_id / "home/user/a.xlsx"
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    row = {
        "mutant_id": mutant_id,
        "task_id": TASK,
        "operator": "S-R1",
        "family": "spreadsheet",
        "label": "should_fail_violation",
        "witness": {"req_ids": ["R1"], "argument": "x"},
        "purity_checks": [],
        "recipe": recipe,
        "target_path_in_vm": target,
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "stratum": "script_writer",
    }
    jobs = controls.mutation_jobs([row], tmp_path)
    assert jobs[0]["files"] == {target: str(path)}
    assert jobs[0]["skip_reachability"] is True
    row["output_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="output_sha256"):
        controls.mutation_jobs([row], tmp_path)


# --------------------------------------------------------------------------- rater packets


def _patched(src: Path, dst: Path, member: str, old: str, new: str, extra=None) -> Path:
    """Copy an OOXML package, replacing ``old`` by ``new`` in one member."""
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == member:
                text = data.decode("utf-8")
                assert old in text, (member, old)
                data = text.replace(old, new, 1).encode("utf-8")
            zout.writestr(info, data)
        for name, body in (extra or {}).items():
            zout.writestr(name, body)
    return dst


def _docx_with_header(path: Path, text: str) -> Path:
    from harness.q2_mutation.operators import _synth as synth

    base = synth.build_docx(path.with_suffix(".base.docx"))
    header = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="{synth.W}">'
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:hdr>"
    )
    rel = (
        '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/header" Target="header1.xml"/></Relationships>'
    )
    return _patched(
        base,
        path,
        "word/_rels/document.xml.rels",
        "</Relationships>",
        rel,
        {"word/header1.xml": header},
    )


def _office_pair(tmp_path: Path, case: str) -> tuple[Path, Path]:
    from harness.q2_mutation.operators import _synth as synth

    a, b = tmp_path / f"{case}-a", tmp_path / f"{case}-b"
    if case == "docx_highlight":
        blocks = [dict(block) for block in synth.DEFAULT_DOCX]
        blocks[3] = {"runs": [("Highlights include ", {}), ("new markets", {}), (".", {})]}
        return synth.build_docx(a.with_suffix(".docx")), synth.build_docx(
            b.with_suffix(".docx"), blocks=blocks
        )
    if case == "docx_font_colour":
        blocks = [dict(block) for block in synth.DEFAULT_DOCX]
        blocks[5] = {"runs": [("Prepared by the finance team.", {"color": "FF0000"})]}
        return synth.build_docx(a.with_suffix(".docx")), synth.build_docx(
            b.with_suffix(".docx"), blocks=blocks
        )
    if case == "docx_line_spacing":
        base = synth.build_docx(a.with_suffix(".docx"))
        jc = '<w:jc w:val="center"/>'
        spaced = jc + '<w:spacing w:line="480" w:lineRule="auto"/>'
        return base, _patched(base, b.with_suffix(".docx"), "word/document.xml", jc, spaced)
    if case == "docx_header":
        return (
            _docx_with_header(a.with_suffix(".docx"), "Confidential"),
            _docx_with_header(b.with_suffix(".docx"), "Draft"),
        )
    pptx = synth.build_pptx(a.with_suffix(".pptx"))
    slide = "ppt/slides/slide1.xml"
    if case == "pptx_run_colour":
        old = '<a:rPr lang="en-US"/><a:t>Outlook'
        new = (
            '<a:rPr lang="en-US"><a:solidFill><a:srgbClr val="FF0000"/></a:solidFill></a:rPr>'
            "<a:t>Outlook"
        )
        return pptx, _patched(pptx, b.with_suffix(".pptx"), slide, old, new)
    if case == "pptx_background":
        bg = (
            '<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>'
            "<a:effectLst/></p:bgPr></p:bg>"
        )
        return pptx, _patched(pptx, b.with_suffix(".pptx"), slide, "<p:cSld>", bg)
    if case == "pptx_outline":
        fill = '<a:solidFill><a:srgbClr val="4F81BD"/></a:solidFill>'
        line = fill + '<a:ln w="38100"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:ln>'
        return pptx, _patched(pptx, b.with_suffix(".pptx"), "ppt/slides/slide2.xml", fill, line)
    if case == "pptx_text_body":
        old = '<a:bodyPr wrap="square"/>'
        return pptx, _patched(
            pptx, b.with_suffix(".pptx"), slide, old, '<a:bodyPr wrap="square" anchor="ctr"/>'
        )
    if case == "xlsx_fill":
        return synth.build_xlsx(a.with_suffix(".xlsx")), synth.build_xlsx(
            b.with_suffix(".xlsx"), cells={"Data": {"A8": ("s", "Target", 3)}}
        )
    if case == "xlsx_number_format":
        return synth.build_xlsx(a.with_suffix(".xlsx")), synth.build_xlsx(
            b.with_suffix(".xlsx"), cells={"Data": {"B8": ("n", 12, 2)}}
        )
    raise ValueError(case)


@pytest.mark.parametrize(
    ("case", "shown"),
    [
        # The reviewer's reproduction: python-docx's listing showed no highlight.
        ("docx_highlight", "highlight"),
        ("docx_font_colour", "color"),
        ("docx_line_spacing", "spacing"),
        ("docx_header", "headers"),
        ("pptx_run_colour", "FF0000"),
        ("pptx_background", "background"),
        ("pptx_outline", "line"),
        ("pptx_text_body", "anchor"),
        ("xlsx_fill", "fill"),
        ("xlsx_number_format", "0.00"),
    ],
)
def test_packet_diff_shows_formatting_the_checker_libraries_hide(
    tmp_path: Path, case: str, shown: str
) -> None:
    from harness.q2_mutation import packets

    initial, candidate = _office_pair(tmp_path, case)
    out = packets.artifacts({"/f": str(initial)}, {"/f": str(candidate)})["/f"]
    assert out["diff_vs_initial"], case
    assert any(shown in line for line in out["diff_vs_initial"]), out["diff_vs_initial"]
    assert packets.structure_lines(initial) != packets.structure_lines(candidate)
    same = packets.artifacts({"/f": str(initial)}, {"/f": str(initial)})["/f"]
    assert same["diff_vs_initial"] == []


def _unflatten(lines: list[str]) -> dict:
    import re

    root: dict = {}
    for line in lines:
        location, _, value = line.partition(" = ")
        tokens = re.findall(r"/([^/\[]+)|\[(\d+)\]", location)
        node: Any = root
        for i, (key, index) in enumerate(tokens):
            last = i == len(tokens) - 1
            nxt = tokens[i + 1] if not last else None
            fresh: Any = json.loads(value) if last else ([] if nxt and nxt[1] else {})
            if key:
                node = node.setdefault(key, fresh) if not last else node.__setitem__(key, fresh)
            else:
                position = int(index)
                while len(node) <= position:
                    node.append(None)
                if last:
                    node[position] = fresh
                else:
                    if node[position] is None:
                        node[position] = fresh
                    node = node[position]
    return root


def test_packet_listing_determines_the_snapshot(tmp_path: Path) -> None:
    """Every snapshot leaf is listed, so every edit an operator can make is visible."""
    from harness.q2_mutation import packets
    from harness.q2_mutation.operators import _synth as synth
    from harness.q2_mutation.operators._snapshot import snapshot
    from harness.q2_mutation.operators.pipeline import make_context, plan_task
    from harness.q2_mutation.schema import RequirementSpec

    builders = {
        "xlsx": synth.build_xlsx,
        "docx": synth.build_docx,
        "pptx": synth.build_pptx,
    }
    for family, build in builders.items():
        path = build(tmp_path / f"gold.{family}")
        snap = snapshot(path)
        lines = packets.flatten(snap)
        expected = {k: v for k, v in snap.items() if k not in ("snapshot_version", "family")}
        assert _unflatten(lines) == json.loads(json.dumps(expected)), family
        # Every operator of the family edits inside a listed top-level part.
        spec = RequirementSpec.from_dict(synth.synthetic_spec(family))
        ctx = make_context(spec.task_id, spec, path, None)
        records, _ = plan_task(ctx)
        roots = {line.split(" = ")[0].split("/")[1].split("[")[0] for line in lines}
        for record in records:
            for pattern in record["recipe"]["params"]["expectation"]["allow"]:
                assert pattern.split("/")[0] in roots, (record["operator"], pattern)


def test_render_resolution_is_raised() -> None:
    from harness.q2_mutation import packets

    render = packets.render_command("/w/x.docx", "/w/r", "/w/h")[1]
    assert render[render.index("-r") + 1] == "100" and render[render.index("-l") + 1] == "20"
