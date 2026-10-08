"""The anchor's CPU checks: public settings, run window, evaluator diff, prompt check (G0 9)."""

from __future__ import annotations

import json
from pathlib import Path

from harness.q2_stage1 import anchor, plan

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "program/evidence/2026-10-08/q2-stage1-g0/anchor"


def args(model: str, **override) -> dict:
    base = {"sleep_after_execution": 3.0, "max_steps": 15, "temperature": 0, "top_p": 0.9,
            "max_tokens": 2048, "stop_token": None, "cot_level": "l2",
            "history_type": "action_history", "coordinate_type": "qwen25",
            "max_image_history_length": 3, "test_all_meta_path": "x", "provider_name": "aws",
            "screen_width": 1920, "screen_height": 1080, "model": model, "region": "r"}  # fmt: skip
    base.update(override)
    return base


def test_recorded_settings_win_and_unrecorded_take_runner_defaults():
    out = anchor.public_settings({"turn_1": args("a"), "turn_2": args("b"), "turn_3": args("c")})
    assert out["settings"]["sleep_after_execution"] == {"value": 3.0, "source": "archive args.json"}
    assert out["settings"]["use_old_sys_prompt"]["source"].startswith("pinned runner default")
    assert out["disagreements"] == {}
    assert out["served_model_names"] == {"turn_1": "a", "turn_2": "b", "turn_3": "c"}
    assert out["unrecorded_keys_in_archive"] == ["region"]


def test_disagreeing_runs_are_reported():
    out = anchor.public_settings(
        {"turn_1": args("a"), "turn_2": args("b", max_tokens=1024), "turn_3": args("c")}
    )
    assert out["disagreements"] == {"max_tokens": [2048, 1024, 2048]}


def test_run_window_from_step_screenshots():
    names = ["turn_1/x/t/step_1_20250729@094736.png", "turn_1/x/t/step_2_20250729@110334.png",
             "turn_2/x/t/step_1_20250730@034825.png", "turn_2/args.json"]  # fmt: skip
    window = anchor.run_window(names)
    assert window["turn_1"] == {"first": "20250729@094736", "last": "20250729@110334", "steps": 2}
    assert set(window) == {"turn_1", "turn_2"}


METRICS_INIT = "from .slides import (\n    compare_pptx_files,\n)\nfrom .docs import find\n"
SLIDES_V1 = """
from .utils import helper
TOL = 1


def other():
    return 0


def compare_pptx_files(a, b):
    return helper(a) == helper(b) and TOL
"""
UTILS_V1 = "def helper(x):\n    return x\n"
UTILS_V2 = "def helper(x):\n    return x.strip()\n"
GETTERS_INIT = "from .file import get_vm_file\n"
FILE = "def get_vm_file(env, config):\n    return env.controller.get_file(config['path'])\n"


def fake_show(revs: dict[str, dict[str, str]]):
    def show(rev: str, path: str):
        return revs[rev].get(path)

    return show


def tree(utils: str, slides: str = SLIDES_V1, config: dict | None = None) -> dict[str, str]:
    task = config or {"id": "t1", "instruction": "x", "evaluator": {
        "func": "compare_pptx_files", "result": {"type": "vm_file", "path": "/a"},
        "expected": {"type": "vm_file", "path": "/b"}}}  # fmt: skip
    return {
        "desktop_env/evaluators/metrics/__init__.py": METRICS_INIT,
        "desktop_env/evaluators/metrics/slides.py": slides,
        "desktop_env/evaluators/metrics/utils.py": utils,
        "desktop_env/evaluators/getters/__init__.py": GETTERS_INIT,
        "desktop_env/evaluators/getters/file.py": FILE,
        "evaluation_examples/examples/libreoffice_impress/t1.json": json.dumps(task),
        "desktop_env/desktop_env.py": "class D:\n    def evaluate(self):\n        return 1\n",
    }


def test_closure_follows_helpers_and_constants_not_unrelated_code():
    show = fake_show({"r": tree(UTILS_V1)})
    sources = anchor.closure(show, "r", "desktop_env/evaluators/metrics", "slides",
                             "compare_pptx_files")  # fmt: skip
    keys = set(sources)
    assert "desktop_env/evaluators/metrics/slides.py::compare_pptx_files" in keys
    assert "desktop_env/evaluators/metrics/slides.py::TOL" in keys
    assert "desktop_env/evaluators/metrics/utils.py::helper" in keys
    assert not any(k.endswith("::other") for k in keys)


def test_evaluator_diff_excludes_a_task_whose_helper_changed():
    task = json.loads(tree(UTILS_V1)["evaluation_examples/examples/libreoffice_impress/t1.json"])
    same = anchor.evaluator_diff(
        fake_show({"old": tree(UTILS_V1), "new": tree(UTILS_V1)}), {"t1": task},
        {"t1": "libreoffice_impress"}, public="old", pinned="new",
    )  # fmt: skip
    assert same["excluded"] == [] and same["desktop_env_evaluate_equal"]
    changed = anchor.evaluator_diff(
        fake_show({"old": tree(UTILS_V1), "new": tree(UTILS_V2)}), {"t1": task},
        {"t1": "libreoffice_impress"}, public="old", pinned="new",
    )  # fmt: skip
    assert changed["excluded"] == ["t1"]
    assert changed["per_task"]["t1"]["functions_differing"] == ["metrics.compare_pptx_files"]
    other_config = dict(task, instruction="y")
    moved = anchor.evaluator_diff(
        fake_show({"old": tree(UTILS_V1, config=other_config), "new": tree(UTILS_V1)}),
        {"t1": task}, {"t1": "libreoffice_impress"}, public="old", pinned="new",
    )  # fmt: skip
    assert moved["per_task"]["t1"]["config_equal"] is False and moved["excluded"] == ["t1"]


def test_task_functions_name_metrics_and_getters():
    task = {"evaluator": {"func": ["a", "b"], "result": [{"type": "vm_file"}, {"type": "rule"}],
                          "expected": [None, {"type": "cloud_file"}]}}  # fmt: skip
    assert anchor.task_functions(task) == [
        ("getters", "get_cloud_file"), ("getters", "get_rule"), ("getters", "get_vm_file"),
        ("metrics", "a"), ("metrics", "b")]  # fmt: skip


def test_literal_strings_and_prompt_check():
    old_agent = 'AGNET_SYS_PROMPT_L1 = "x".strip()\nAGNET_SYS_PROMPT_L2 = "a\\nb".strip()\n'
    old_agent += 'AGNET_SYS_PROMPT_L3 = "z"\n'
    prompts = 'SYSTEM_PROMPT_V1_L1 = "x"\nSYSTEM_PROMPT_V1_L2 = "old"\nSYSTEM_PROMPT_V1_L3 = "z"\n'
    prompts += 'SYSTEM_PROMPT_V1_L2 = """a\nb plus"""\n'  # redefined later: the last one wins
    assert anchor.literal_strings(prompts)["SYSTEM_PROMPT_V1_L2"] == "a\nb plus"
    show = fake_show({
        anchor.PUBLIC_REVISION: {"mm_agents/opencua_agent.py": old_agent},
        anchor.AGENT_REVISION: {"mm_agents/opencua/prompts.py": prompts,
                                "mm_agents/opencua/opencua_agent.py": "build_sys_prompt("},
    })  # fmt: skip
    out = anchor.prompt_check(show)
    assert out["L1"]["old_option_equal"] and out["L3"]["old_option_equal"]
    assert not out["L2"]["old_option_equal"] and out["L2"]["diff"]
    assert out["default_is_v2_family"]


def test_recorded_public_settings_evidence():
    data = json.loads((EVIDENCE / "public-settings.json").read_text())
    assert data["archive"]["lfs_sha256"] == (
        "b642e1212d3ebb87e88addc0c55525b12d1ce8b9b253306fa7706908778e9688"
    )
    settings = {k: v["value"] for k, v in data["settings"].items()}
    assert settings["max_steps"] == 15 and settings["cot_level"] == "l2"
    assert settings["sleep_after_execution"] == 3.0
    assert data["disagreements"] == {}


def test_check_vllm_refuses_unreviewed_remote_code(tmp_path):
    for name in anchor.REMOTE_CODE_SHA256:
        (tmp_path / name).write_text("# not the reviewed file\n")
    out = anchor.check_vllm(str(tmp_path))
    assert out["ok"] is False and out["remote_code_pinned"] is False
    assert "nothing was imported" in out["error"]


def test_anchor_argv_is_the_registered_variant():
    argv = plan.engine_argv("/m", plan.SERVED_NAME, anchor=True)
    assert argv[argv.index("--max-model-len") + 1] == "32768"
    assert "--trust-remote-code" in argv
