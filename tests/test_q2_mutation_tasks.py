import json
from pathlib import Path

import pytest

from harness.q2_mutation import schema, tasks

CACHE = "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main"


def _write_task(root: Path, domain: str, task_id: str, evaluator: dict, **extra: object) -> None:
    raw = {
        "id": task_id,
        "snapshot": domain,
        "instruction": f"do {task_id[:4]}",
        "source": "https://example.org",
        "trajectory": "t",
        "related_apps": [domain],
        "proxy": False,
        "config": [
            {
                "type": "download",
                "parameters": {
                    "files": [
                        {"url": f"{CACHE}/{domain}/{task_id}/in.xlsx", "path": "Desktop/in.xlsx"}
                    ]
                },
            }
        ],
        "evaluator": evaluator,
    }
    raw.update(extra)
    path = root / "evaluation_examples" / "examples" / domain / f"{task_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw))


def _tid(n: int) -> str:
    return f"{n:08x}-0000-4000-8000-000000000000"


GOLD = {
    "func": "compare_table",
    "result": {"type": "vm_file", "path": "/home/user/Desktop/in.xlsx", "dest": "in.xlsx"},
    "expected": {"type": "cloud_file", "path": f"{CACHE}/x/gold.xlsx", "dest": "gold.xlsx"},
    "postconfig": [{"type": "execute", "parameters": {"command": ["true"]}}],
    "options": {"rules": []},
}
RULE = {
    "func": "check_x",
    "result": {"type": "vm_file", "path": "/home/user/a"},
    "expected": {"type": "rule", "rules": {}},
}
LIVE = {"func": "exact_match", "result": {"type": "vm_command_line"}, "expected": {"type": "rule"}}


def _osworld(root: Path) -> Path:
    _write_task(root, "libreoffice_calc", _tid(1), GOLD, hint="secret")
    _write_task(root, "libreoffice_calc", _tid(2), RULE)
    _write_task(root, "os", _tid(3), LIVE)
    _write_task(root, "multi_apps", _tid(4), GOLD, proxy=True)
    _write_task(root, "vlc", _tid(5), {"func": "infeasible"})
    index = {
        "libreoffice_calc": [_tid(1), _tid(2)],
        "os": [_tid(3)],
        "multi_apps": [_tid(4)],
        "vlc": [_tid(5)],
    }
    (root / "evaluation_examples" / "test_nogdrive.json").write_text(json.dumps(index))
    return root


def test_classification_and_scope(tmp_path: Path) -> None:
    records = {r.task_id: r for r in tasks.scope_records(_osworld(tmp_path))}
    assert records[_tid(1)].task_class == "1A" and records[_tid(1)].in_scope
    assert records[_tid(2)].task_class == "1B" and records[_tid(2)].in_scope
    assert records[_tid(3)].task_class == "2" and not records[_tid(3)].in_scope
    assert records[_tid(4)].web_reason == "proxy" and not records[_tid(4)].in_scope
    assert records[_tid(5)].task_class == "3"


def test_metric_class_table() -> None:
    assert tasks.metric_class("vm_file", "cloud_file") == "1A"
    assert tasks.metric_class("vm_file", "rule") == "1B"
    assert tasks.metric_class("vm_file", "vm_file") == "1V"
    assert tasks.metric_class("vlc_config", "rule") == "1C"
    assert tasks.metric_class("vm_command_line", "info_from_website") == "2W"
    assert tasks.metric_class("accessibility_tree", "rule") == "2"


def test_sanitize_strips_evaluator_and_pins_urls(tmp_path: Path) -> None:
    records = {r.task_id: r for r in tasks.scope_records(_osworld(tmp_path))}
    raw = records[_tid(1)].raw
    rel = f"libreoffice_calc/{_tid(1)}/in.xlsx"
    sanitized = tasks.sanitize_task(raw, {rel: "b" * 64}).to_dict()
    assert set(sanitized) == set(schema.SANITIZED_TASK_KEYS)
    assert not schema.find_forbidden_keys(sanitized)
    text = json.dumps(sanitized)
    for leaked in ("gold.xlsx", "compare_table", "secret", "postconfig", "example.org"):
        assert leaked not in text
    item = sanitized["initial_files"][0]
    assert f"/resolve/{tasks.FILE_CACHE_REVISION}/" in item["url"]
    assert item["path_in_vm"] == "/home/user/Desktop/in.xlsx"
    with pytest.raises(tasks.TaskScopeError, match="no verified sha256"):
        tasks.sanitize_task(raw, {})


def test_pin_url_refuses_foreign_hosts_and_revisions() -> None:
    with pytest.raises(tasks.TaskScopeError, match="outside"):
        tasks.pin_file_cache_url("https://drive.google.com/x")
    with pytest.raises(tasks.TaskScopeError, match="revision"):
        tasks.pin_file_cache_url(CACHE.replace("/main", "/deadbeef") + "/a/b")
    assert tasks.file_cache_path(f"{CACHE}/a/b%20c.xlsx") == "a/b c.xlsx"


def test_resolve_vm_path() -> None:
    assert tasks.resolve_vm_path("Downloads/a.pptx") == "/home/user/Downloads/a.pptx"
    assert tasks.resolve_vm_path("~/Desktop/a") == "/home/user/Desktop/a"
    assert tasks.resolve_vm_path("$HOME/a") == "/home/user/a"
    assert tasks.resolve_vm_path("/tmp/../etc/x") == "/etc/x"


def test_stratified_split_is_deterministic_and_disjoint(tmp_path: Path) -> None:
    records = []
    for n in range(40):
        domain = "libreoffice_calc" if n % 2 else "libreoffice_impress"
        records.append(
            tasks.TaskRecord(_tid(100 + n), domain, {}, ("f",), ("1A",), "1A", False, None)
        )
    first = tasks.stratified_split(records, seed=42, dev_fraction=0.15, confirm_size=20)
    second = tasks.stratified_split(
        list(reversed(records)), seed=42, dev_fraction=0.15, confirm_size=20
    )
    assert first == second
    other = tasks.stratified_split(records, seed=43, dev_fraction=0.15, confirm_size=20)
    assert other != first
    ids = first["dev"] + first["confirm"] + first["reserve"]
    assert len(ids) == len(set(ids)) == 40
    assert len(first["confirm"]) == 20 and len(first["dev"]) == 6
    with pytest.raises(ValueError, match="exceeds"):
        tasks.stratified_split(records, seed=42, dev_fraction=0.15, confirm_size=39)


def test_manual_lists_are_disjoint() -> None:
    assert not set(tasks.MANUAL_WEB_EXCLUSIONS) & set(tasks.MANUAL_WEB_KEEPS)
