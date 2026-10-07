import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from harness.q2_mutation import controls, offline_eval, raters, reachability, vm_injection
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
        {"job_id": "t__gold", "outputs": {"/a": "/saved", "/a.csv": "/csv"}, "lo_build": "7.3.7.2"},
        {"job_id": "t__initial", "infra_error": "Timeout"},
    ]
    merged, excluded = controls.merge_lo(jobs, rows)
    assert merged[0]["files"] == {"/a": "/saved", "/a.csv": "/csv"}
    assert merged[0]["saved_via"] == "gui_faithful_lo_save"
    assert merged[0]["mutant_id"] == "t__gold__lo"
    assert excluded == [{"job_id": "t__initial", "reason": "Timeout"}]


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
    assert reachability.parse_execute(["rm", "-rf", "/x"])[0].kind == "unemulated"
    assert reachability.window_title_for("/home/user/a.pptx") == "a.pptx - LibreOffice Impress"


def test_audit_sample_strata_probabilities_and_shams() -> None:
    cands = [
        raters.Candidate(f"m{i}", f"t{i % 5}", "should_fail_violation", "fail") for i in range(300)
    ]
    cands += [
        raters.Candidate(f"d{i}", f"t{i % 5}", "should_pass_equiv", "fail") for i in range(10)
    ]
    cands += [raters.Candidate(f"a{i}", "t1", "should_pass_alt_solution", "pass") for i in range(3)]
    cands += [raters.Candidate("e0", "t1", "should_pass_equiv", "error")]
    sample = raters.draw_audit_sample(cands, seed=42)
    by = {}
    for item in sample:
        by.setdefault(item.stratum, []).append(item)
    assert len(by["alt_solution"]) == 3 and by["alt_solution"][0].inclusion_probability == 1.0
    assert len(by["disagreement"]) == 10
    assert len(by["agreement"]) == 100
    assert by["agreement"][0].inclusion_probability == pytest.approx(100 / 300)
    assert len(by["sham"]) == 10  # ceil(10% of 113) = 12, capped at 2 per task
    assert all(item.mutant_id != "e0" for item in sample)
    assert raters.draw_audit_sample(cands, seed=42) == sample


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
    assert summary.label_error["should_fail"].estimate == 0.0
    assert summary.label_error_unresolved_as_wrong["should_fail"] == pytest.approx(1 / 6)
    assert summary.sham_accuracy == {"model-rater-anthropic": 1.0, "model-rater-openai": 0.0}


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
