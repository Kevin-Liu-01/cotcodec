"""The OpenCUA-7B anchor's CPU checks (registration G0 items 9.1 and 9.3-9.6, section 5.7).

* ``public-settings`` (9.4, 9.5): reads the three public 15-step runs' ``args.json`` and the
  run window from ``xlangai/ubuntu_osworld_verified_trajs`` at the pinned revision by ranged
  reads (``harness.remote_zip``; size, LFS SHA-256 and revision checked), and records every
  setting the archive holds. A setting it does not hold takes the pinned runner's default
  (``RUNNER_DEFAULTS``, OSWorld ``bfd62bdc`` ``scripts/python/run_multienv_opencua.py``).
* ``evaluator-diff`` (9.6): the archive records no OSWorld revision, so the revision on
  ``main`` when the runs started is inferred from the run window (``PUBLIC_REVISION``), and
  for every pool task the task config and the source of every checker function it uses
  (metric and getter functions, with every module-level name they reach inside
  ``desktop_env/evaluators``) are compared between that revision and ``b138d348``. A task
  with any difference leaves the anchor reading. Runs on the host's OSWorld clone (git only).
* ``check-vllm`` (9.1, 9.3): inside a CPU-only container of the serving image, with no
  network: vLLM's model registry lists ``OpenCUAForConditionalGeneration``;
  ``AutoConfig`` and ``AutoTokenizer`` load from the pinned snapshot with
  ``trust_remote_code`` (the configuration and tokenizer remote code, read and hashed first,
  ``REMOTE_CODE_SHA256``); and vLLM's own CLI parser and ``EngineArgs.create_model_config``
  accept the anchor argv (``plan.engine_argv(..., anchor=True)``). The modeling code is not
  imported and no weight is loaded.
"""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

PINNED_REVISION = "b138d348256078fa634fc3b73567a7337c793e6b"
AGENT_REVISION = "bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06"  # the anchor agent and runner pin
# main when the public runs began (2025-07-29 06:48 UTC); no commit touched
# evaluation_examples/ or desktop_env/evaluators/ from 2025-07-27 until dd488c7 at
# 2025-07-30 06:07 UTC, and every later change (dd488c7 included) is inside the compared range.
PUBLIC_REVISION = "00804f811874ea34ddfdd2e6b3a2fe307311f57c"
ARCHIVE_KEY = "opencua-7b-15"
TURNS = ("turn_1", "turn_2", "turn_3")
RUNNER_DEFAULTS = {  # bfd62bdc run_multienv_opencua.py argparse defaults
    "sleep_after_execution": 5.0,
    "max_steps": 100,
    "temperature": 0,
    "top_p": 0.9,
    "max_tokens": 2048,
    "stop_token": None,
    "cot_level": "l2",
    "history_type": "action_history",
    "coordinate_type": "qwen25",
    "max_image_history_length": 3,
    "use_old_sys_prompt": False,
    "test_all_meta_path": "evaluation_examples/test_nogdrive.json",
    "provider_name": "aws",
    "screen_width": 1920,
    "screen_height": 1080,
}
SETTINGS = tuple(RUNNER_DEFAULTS)
REMOTE_CODE_SHA256 = {  # xlangai/OpenCUA-7B at a2efb7d2 (fetch job 971 receipt)
    "configuration_opencua.py": "12892d04cf561ddf85fbb166088cf6ec2c3edbfed86152461a25ed82f14ef560",
    "modeling_opencua.py": "fb8fcf59150cd659d7cb54151f32b49e18bbd2c662fbe93daf78afc33f0a1b53",
    "processing_opencua.py": "58198678600fd5a81aab6838321ab56b663f6f2c29918af1bac03ac2378b1b99",
    "tokenization_opencua.py": "7386c9fb5b45a5e5a63fab059dd3c4650c1a229d7e1ce5e14ead276e6be9f3db",
}
STEP_PNG = re.compile(r"^(turn_\d)/.*step_\d+_(\d{8}@\d{6})\.png$")
EVALUATORS = "desktop_env/evaluators"


# --------------------------------------------------------------------------- 9.4 / 9.5


def run_window(names: Iterable[str]) -> dict[str, dict[str, str]]:
    """First and last step timestamps per public run (the runner's local clock, no zone)."""
    stamps: dict[str, list[str]] = {}
    for name in names:
        match = STEP_PNG.match(name)
        if match:
            stamps.setdefault(match.group(1), []).append(match.group(2))
    return {
        turn: {"first": min(v), "last": max(v), "steps": len(v)}
        for turn, v in sorted(stamps.items())
    }


def public_settings(args_by_turn: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """The anchor's settings: what the three runs recorded (they must agree), else defaults."""
    recorded: dict[str, Any] = {}
    disagreements: dict[str, list[Any]] = {}
    for key in SETTINGS:
        values = [args.get(key, "<absent>") for args in args_by_turn.values()]
        present = [v for v in values if v != "<absent>"]
        if present and len(present) != len(values):
            disagreements[key] = values
        elif present:
            if any(v != present[0] for v in present):
                disagreements[key] = values
            recorded[key] = present[0]
    settings = {
        key: {"value": recorded[key], "source": "archive args.json"}
        if key in recorded
        else {"value": RUNNER_DEFAULTS[key], "source": "pinned runner default (not recorded)"}
        for key in SETTINGS
    }
    return {
        "settings": settings,
        "disagreements": disagreements,
        "served_model_names": {turn: args.get("model") for turn, args in args_by_turn.items()},
        "unrecorded_keys_in_archive": sorted(
            {k for args in args_by_turn.values() for k in args} - set(SETTINGS) - {"model"}
        ),
    }


def read_public(cache_dir: Path | None = None) -> dict[str, Any]:
    """Ranged reads of the args files and the member listing (network; pinned source)."""
    from harness import remote_zip
    from harness.holo3_rerun_audit import DATASET_REPO, DATASET_REVISION, OPENCUA_ARCHIVES

    spec = OPENCUA_ARCHIVES[ARCHIVE_KEY]
    source = remote_zip.HFRangeSource(
        DATASET_REPO, DATASET_REVISION, spec.path,
        expected_size=spec.size, expected_sha256=spec.lfs_sha256,
    )  # fmt: skip
    members = remote_zip.list_members(source)
    names = [m.name for m in members]
    wanted = [f"{turn}/args.json" for turn in TURNS]
    data = remote_zip.extract_members(source, remote_zip.select(members, wanted))
    args = {name.split("/")[0]: json.loads(data[name]) for name in wanted}
    result_txt = sum(1 for n in names if n.endswith("/result.txt"))
    return {
        "archive": {
            "repo": DATASET_REPO,
            "revision": DATASET_REVISION,
            "path": spec.path,
            "size": spec.size,
            "lfs_sha256": spec.lfs_sha256,
        },  # fmt: skip
        "members": len(names),
        "result_txt_members": result_txt,
        "args_sha256": {n: hashlib.sha256(data[n]).hexdigest() for n in wanted},
        "args": args,
        "run_window": run_window(names),
        **public_settings(args),
    }


# --------------------------------------------------------------------------- 9.6

Show = Callable[[str, str], str | None]  # (revision, path) -> text or None


def git_show(repo: Path) -> Show:
    def show(rev: str, path: str) -> str | None:
        done = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"],
                              capture_output=True, text=True)  # fmt: skip
        return done.stdout if done.returncode == 0 else None

    return show


def exported_names(init_source: str) -> dict[str, str]:
    """``name -> module`` from an ``__init__.py`` of relative imports."""
    out = {}
    for node in ast.parse(init_source).body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                out[alias.asname or alias.name] = node.module
    return out


def _module_symbols(source: str) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """Top-level definitions (name -> source) and relative imports (name -> (module, name))."""
    tree = ast.parse(source)
    defs: dict[str, str] = {}
    imports: dict[str, tuple[str, str]] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            defs[node.name] = ast.get_source_segment(source, node) or ""
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defs[target.id] = ast.get_source_segment(source, node) or ""
        elif isinstance(node, ast.ImportFrom) and node.module:
            module = node.module
            if node.level == 1 or module.startswith("desktop_env.evaluators"):
                for alias in node.names:
                    imports[alias.asname or alias.name] = (module, alias.name)
    return defs, imports


def closure(show: Show, rev: str, package: str, module: str, name: str) -> dict[str, str]:
    """Source of ``name`` and of every module-level name it reaches inside the evaluators."""
    seen: dict[str, str] = {}
    stack = [(package, module, name)]
    while stack:
        pkg, mod, sym = stack.pop()
        if mod.startswith("desktop_env.evaluators."):
            parts = mod.split(".")
            pkg, mod = "/".join(parts[:-1]), parts[-1]
        path = f"{pkg}/{mod}.py"
        key = f"{path}::{sym}"
        if key in seen:
            continue
        text = show(rev, path)
        if text is None:
            seen[key] = "<missing module>"
            continue
        defs, imports = _module_symbols(text)
        if sym in imports:
            target_mod, target_name = imports[sym]
            seen[key] = f"<import {target_mod}.{target_name}>"
            stack.append((pkg, target_mod, target_name))
            continue
        segment = defs.get(sym)
        if segment is None:
            seen[key] = "<undefined>"
            continue
        seen[key] = segment
        used = {n.id for n in ast.walk(ast.parse(segment)) if isinstance(n, ast.Name)}
        used |= {n.attr for n in ast.walk(ast.parse(segment)) if isinstance(n, ast.Attribute)}
        for other in sorted(used - {sym}):
            if other in defs or other in imports:
                stack.append((pkg, mod, other))
    return seen


def normalized(segment: str) -> str:
    """The AST of a definition without docstrings, comments or layout (what can run)."""
    if segment.startswith("<"):
        return segment
    try:
        tree = ast.parse(segment)
    except SyntaxError:
        return segment
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Module)
                and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):  # fmt: skip
            node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def task_functions(task: Mapping[str, Any]) -> list[tuple[str, str]]:
    """``(kind, name)`` of every metric and getter function a task's evaluator names."""
    evaluator = task["evaluator"]
    funcs = evaluator["func"] if isinstance(evaluator["func"], list) else [evaluator["func"]]
    out = [("metrics", f) for f in funcs if f != "infeasible"]
    for key in ("result", "expected"):
        value = evaluator.get(key)
        for getter in value if isinstance(value, list) else [value]:
            if isinstance(getter, Mapping) and getter.get("type"):
                out.append(("getters", f"get_{getter['type']}"))
    return sorted(set(out))


def function_sources(show: Show, rev: str, kind: str, name: str) -> dict[str, str]:
    package = f"{EVALUATORS}/{kind}"
    init = show(rev, f"{package}/__init__.py")
    if init is None:
        return {f"{package}::{name}": "<missing package>"}
    module = exported_names(init).get(name)
    if module is None:
        return {f"{package}::{name}": "<not exported>"}
    return closure(show, rev, package, module, name)


def config_path(show: Show, rev: str, task_id: str, domain: str) -> str:
    return f"evaluation_examples/examples/{domain}/{task_id}.json"


def evaluator_diff(
    show: Show,
    tasks: Mapping[str, Mapping[str, Any]],
    domains: Mapping[str, str],
    *,
    public: str = PUBLIC_REVISION,
    pinned: str = PINNED_REVISION,
) -> dict[str, Any]:
    """Per task: config equality and the checker functions whose closure differs."""
    cache: dict[tuple[str, str, str], dict[str, str]] = {}

    def sources(rev: str, kind: str, name: str) -> dict[str, str]:
        key = (rev, kind, name)
        if key not in cache:
            raw = function_sources(show, rev, kind, name)
            cache[key] = {k: normalized(v) for k, v in raw.items()}
        return cache[key]

    def differing_parts(kind: str, name: str) -> list[str]:
        a, b = sources(public, kind, name), sources(pinned, kind, name)
        return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))

    per_task: dict[str, Any] = {}
    for task_id in sorted(tasks):
        path = config_path(show, pinned, task_id, domains[task_id])
        old_text = show(public, path)
        old = json.loads(old_text) if old_text is not None else None
        config_equal = old == tasks[task_id]
        differing = []
        parts: dict[str, list[str]] = {}
        for kind, name in task_functions(tasks[task_id]):
            changed = differing_parts(kind, name)
            if changed:
                differing.append(f"{kind}.{name}")
                parts[f"{kind}.{name}"] = changed
        per_task[task_id] = {
            "config_present_at_public": old is not None,
            "config_equal": config_equal,
            "functions": [f"{k}.{n}" for k, n in task_functions(tasks[task_id])],
            "functions_differing": differing,
            "definitions_differing": parts,
            "config_keys_differing": sorted(
                k
                for k in set(old or {}) | set(tasks[task_id])
                if (old or {}).get(k) != tasks[task_id].get(k)
            ),
            "excluded": (not config_equal) or bool(differing),
        }
    desktop = {rev: (show(rev, "desktop_env/desktop_env.py") or "") for rev in (public, pinned)}
    evaluate_src = {}
    for rev, text in desktop.items():
        tree = ast.parse(text) if text else None
        segment = ""
        for node in ast.walk(tree) if tree else []:
            if isinstance(node, ast.FunctionDef) and node.name == "evaluate":
                segment = ast.get_source_segment(text, node) or ""
        evaluate_src[rev] = normalized(segment) if segment else ""
    excluded = sorted(t for t, row in per_task.items() if row["excluded"])
    config_only = sorted(t for t, row in per_task.items() if not row["config_equal"])
    metrics_or_config = sorted(
        t for t, row in per_task.items()
        if not row["config_equal"]
        or any(f.startswith("metrics.") for f in row["functions_differing"])
    )  # fmt: skip
    counts = collections.Counter(f for row in per_task.values() for f in row["functions_differing"])
    return {
        "schema": "q2-stage1a-anchor-evaluator-diff-v1",
        "public_revision": public,
        "public_revision_basis": "not recorded in the archive; inferred from the run window",
        "pinned_revision": pinned,
        "tasks": len(per_task),
        "rule": "a task leaves the anchor reading when its config or the AST (docstrings, "
        "comments and layout removed) of any checker definition it reaches differs",
        "excluded": excluded,
        "excluded_count": len(excluded),
        "config_differs": config_only,
        "config_or_metric_differs": metrics_or_config,
        "function_difference_counts": dict(counts.most_common()),
        "desktop_env_evaluate_equal": evaluate_src[public] == evaluate_src[pinned],
        "per_task": per_task,
    }


def literal_strings(source: str) -> dict[str, str]:
    """Module-level string constants (``"..."`` or ``"...".strip()``); the last one wins."""
    out: dict[str, str] = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target, value = node.targets[0], node.value
        if not isinstance(target, ast.Name):
            continue
        strip = False
        if (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
                and value.func.attr == "strip" and not value.args):  # fmt: skip
            value, strip = value.func.value, True
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            out[target.id] = value.value.strip() if strip else value.value
    return out


def prompt_check(show: Show) -> dict[str, Any]:
    """Which pinned system prompt, if any, equals the one the public runs' agent sent.

    The public runs (July 2025) used ``mm_agents/opencua_agent.py`` at ``PUBLIC_REVISION``
    (``AGNET_SYS_PROMPT_L1``-``L3``). At ``AGENT_REVISION`` the agent sends
    ``SYSTEM_PROMPT_V1_L*`` with ``--use_old_sys_prompt`` and ``build_sys_prompt`` (the V2
    family) without it.
    """
    old = literal_strings(show(PUBLIC_REVISION, "mm_agents/opencua_agent.py") or "")
    new = literal_strings(show(AGENT_REVISION, "mm_agents/opencua/prompts.py") or "")
    out: dict[str, Any] = {"public_revision": PUBLIC_REVISION, "agent_revision": AGENT_REVISION}
    for level in ("L1", "L2", "L3"):
        a, b = old.get(f"AGNET_SYS_PROMPT_{level}"), new.get(f"SYSTEM_PROMPT_V1_{level}")
        row: dict[str, Any] = {
            "public_sha256": hashlib.sha256(a.encode()).hexdigest() if a else None,
            "old_option_sha256": hashlib.sha256(b.encode()).hexdigest() if b else None,
            "old_option_equal": a is not None and a == b,
        }
        if a and b and a != b:
            import difflib

            row["diff"] = [
                line[:300]
                for line in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
            ][:12]
        out[level] = row
    out["default_is_v2_family"] = "build_sys_prompt" in (
        show(AGENT_REVISION, "mm_agents/opencua/opencua_agent.py") or ""
    )
    return out


# --------------------------------------------------------------------------- 9.1 / 9.3


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _first_attr(modules: Iterable[str], name: str) -> Any:
    """``name`` from the first of ``modules`` that has it (vLLM moves things between releases)."""
    for module in modules:
        try:
            return getattr(__import__(module, fromlist=[name]), name)
        except (ImportError, AttributeError):
            continue
    raise ImportError(f"{name} is in none of {list(modules)}")


def check_vllm(model_dir: str) -> dict[str, Any]:
    """Inside the serving image, CPU only: registry, AutoConfig/AutoTokenizer, ModelConfig."""
    from harness.q2_stage1 import plan

    out: dict[str, Any] = {"model_dir": model_dir}
    root = Path(model_dir)
    hashes = {name: file_sha256(root / name) for name in REMOTE_CODE_SHA256}
    out["remote_code_sha256"] = hashes
    out["remote_code_pinned"] = hashes == REMOTE_CODE_SHA256
    if not out["remote_code_pinned"]:
        out["ok"] = False
        out["error"] = "remote code differs from the reviewed files; nothing was imported"
        return out
    checks: dict[str, Any] = {}
    try:
        from vllm.model_executor.models import ModelRegistry

        archs = set(ModelRegistry.get_supported_archs())
        checks["registry_lists_opencua"] = "OpenCUAForConditionalGeneration" in archs
    except Exception as exc:  # noqa: BLE001 - recorded
        checks["registry_error"] = f"{type(exc).__name__}: {exc}"[:400]
    try:
        from transformers import AutoConfig, AutoTokenizer

        config = AutoConfig.from_pretrained(model_dir, trust_remote_code=True)
        checks["config_class"] = type(config).__name__
        checks["config_architectures"] = list(getattr(config, "architectures", []) or [])
        derived = getattr(config, "max_position_embeddings", None)
        text_config = getattr(config, "text_config", None)
        if text_config is not None:
            derived = getattr(text_config, "max_position_embeddings", derived)
        checks["max_position_embeddings"] = derived
        tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        checks["tokenizer_class"] = type(tokenizer).__name__
        sample = tokenizer.encode("Click the OK button.")
        checks["tokenizer_roundtrip"] = tokenizer.decode(sample) == "Click the OK button."
    except Exception as exc:  # noqa: BLE001 - recorded
        checks["hf_error"] = f"{type(exc).__name__}: {exc}"[:400]
    for module in ("vllm.tokenizers", "vllm.transformers_utils.tokenizer"):
        try:
            get_tokenizer = __import__(module, fromlist=["get_tokenizer"]).get_tokenizer
        except (ImportError, AttributeError):
            continue
        try:
            engine_tokenizer = get_tokenizer(model_dir, trust_remote_code=True)
            checks["vllm_tokenizer_class"] = type(engine_tokenizer).__name__
        except Exception as exc:  # noqa: BLE001 - recorded
            checks["vllm_tokenizer_error"] = f"{type(exc).__name__}: {exc}"[:400]
        checks["vllm_tokenizer_loader"] = module
        break
    try:
        from vllm.engine.arg_utils import EngineArgs

        make_arg_parser = _first_attr(
            ("vllm.entrypoints.openai.cli_args", "vllm.entrypoints.launchers.cli_args"),
            "make_arg_parser",
        )
        FlexibleArgumentParser = _first_attr(  # noqa: N806 - vLLM's class
            ("vllm.utils", "vllm.utils.argparse_utils"), "FlexibleArgumentParser"
        )
        argv = plan.engine_argv(model_dir, plan.SERVED_NAME, anchor=True)
        parser = make_arg_parser(FlexibleArgumentParser())
        args = parser.parse_args(argv[2:])  # drop "vllm serve"; the model is positional
        engine_args = EngineArgs.from_cli_args(args)
        model_config = engine_args.create_model_config()
        checks["argv"] = argv
        checks["model_config_max_model_len"] = model_config.max_model_len
        checks["model_config_trust_remote_code"] = model_config.trust_remote_code
        checks["model_config_architectures"] = list(model_config.architectures or [])
    except Exception as exc:  # noqa: BLE001 - recorded
        checks["vllm_error"] = f"{type(exc).__name__}: {exc}"[:600]
    out["checks"] = checks
    out["ok"] = bool(
        checks.get("registry_lists_opencua")
        and checks.get("tokenizer_roundtrip")
        and "vllm_tokenizer_error" not in checks
        and checks.get("model_config_max_model_len") == plan.ANCHOR_MAX_MODEL_LEN
        and checks.get("model_config_trust_remote_code") is True
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pub = sub.add_parser("public-settings")
    pub.add_argument("--out", type=Path, required=True)
    diff = sub.add_parser("evaluator-diff")
    diff.add_argument("--osworld-git", type=Path, required=True)
    diff.add_argument("--splits", type=Path, required=True)
    diff.add_argument("--out", type=Path, required=True)
    prompt = sub.add_parser("prompt-check")
    prompt.add_argument("--osworld-git", type=Path, required=True)
    prompt.add_argument("--out", type=Path, required=True)
    vllm = sub.add_parser("check-vllm")
    vllm.add_argument("--model-dir", required=True)
    vllm.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "public-settings":
        result = read_public()
    elif args.command == "check-vllm":
        result = check_vllm(args.model_dir)
    elif args.command == "prompt-check":
        result = prompt_check(git_show(args.osworld_git))
    else:
        from harness.q2_stage1.plan import task_pool

        show = git_show(args.osworld_git)
        pool = task_pool(json.loads(args.splits.read_text())["confirm"])
        tasks, domains = {}, {}
        listing = subprocess.run(
            ["git", "-C", str(args.osworld_git), "ls-tree", "-r", "--name-only", PINNED_REVISION,
             "evaluation_examples/examples"], capture_output=True, text=True, check=True,
        ).stdout.split()  # fmt: skip
        by_id = {Path(p).stem: p.split("/")[2] for p in listing if p.endswith(".json")}
        for task_id in pool:
            domains[task_id] = by_id[task_id]
            tasks[task_id] = json.loads(show(PINNED_REVISION, config_path(
                show, PINNED_REVISION, task_id, by_id[task_id])))  # fmt: skip
        result = evaluator_diff(show, tasks, domains)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    summary = {k: v for k, v in result.items() if not isinstance(v, dict | list)}
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
