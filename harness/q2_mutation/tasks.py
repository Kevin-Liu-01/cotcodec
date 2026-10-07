"""OSWorld-Verified task scope, classification, sanitization and splits.

Reads task configs from a pinned OSWorld checkout (never imports its code) and
decides which tasks are in the Q2 mutation scope: tasks of
``evaluation_examples/test_nogdrive.json`` (OSWorld-Verified, 361 tasks) that
need no web access and whose every metric reads files or application config
files that can be obtained offline.

Classification of one metric instance (result getter, expected getter):

* ``1A``  a result file compared against a downloadable gold (``cloud_file``)
* ``1B``  a result file checked against a rule
* ``1V``  the expected file also lives in the VM
* ``1C``  an application config file whose baseline lives in the VM image
* ``2``   live VM, accessibility or browser state
* ``2W``  an expected value fetched from the web
* ``3``   infeasible

A task takes the worst class of its metric instances. The scope is classes
1A, 1B, 1V and 1C, minus web-dependent tasks.

``sanitize_task`` produces the only view of a task the blind requirement-spec
author may read. Classification is checker-derived and must never be shown to
that author; it lives in the harness-side scope file.
"""

from __future__ import annotations

import json
import posixpath
import random
import urllib.parse
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.q2_mutation.schema import InitialFile, SanitizedTask, SchemaError

OSWORLD_REPO = "https://github.com/xlang-ai/OSWorld"
OSWORLD_COMMIT = "b138d348256078fa634fc3b73567a7337c793e6b"
OSWORLD_EVALUATOR_COMMIT = "0514b9a262c5e49007a5724e3e6c84171566ae66"
VERIFIED_TASK_LIST = "evaluation_examples/test_nogdrive.json"
FILE_CACHE_REPO = "xlangai/ubuntu_osworld_file_cache"
FILE_CACHE_REVISION = "1e112283c4ecb08d6fed8069bca7de74fa2f12aa"
FILE_CACHE_PREFIX = f"https://huggingface.co/datasets/{FILE_CACHE_REPO}/resolve/"

FILE_RESULT_GETTERS = frozenset(
    {
        "vm_file",
        "cache_file",
        "cloud_file",
        "content_from_vm_file",
        "audio_in_slide",
        "background_image_in_slide",
    }
)
APP_CONFIG_RESULT_GETTERS = frozenset({"vlc_config", "gimp_config_file", "vscode_config"})
OFFLINE_EXPECTED_GETTERS = frozenset({"cloud_file", "rule", "rule_relativeTime", "local_file"})
WEB_EXPECTED_GETTERS = frozenset(
    {"pdf_from_url", "info_from_website", "gotoRecreationPage_and_get_html_content"}
)
WEB_CONFIG_TYPES = frozenset(
    {"chrome_open_tabs", "chrome_close_tabs", "update_browse_history", "googledrive", "login"}
)
WEB_APPS = frozenset({"chrome", "google-chrome", "googledrive"})
CLASS_ORDER = {"1A": 0, "1B": 1, "1V": 2, "1C": 3, "2": 4, "2W": 5, "3": 6}
SCOPE_CLASSES = frozenset({"1A", "1B", "1V", "1C"})

# Tasks whose config looks web-free but whose instruction needs the web.
# Decided by reading each flagged instruction at OSWORLD_COMMIT (2026-10-06).
MANUAL_WEB_EXCLUSIONS: Mapping[str, str] = {
    "5ca86c6f-f317-49d8-b6a7-b527541caae8": "asks to download a university logo from the web",
    "3c8f201a-009d-4bbe-8b65-a6f8b35bb57f": "asks to download an image from a URL",
    "bba3381f-b5eb-4439-bd9e-80c22218d5a7": "asks to stream a video from a URL",
    "7882ed6e-bece-4bf0-bada-c32dc1ddae72": "asks to play content purchased from an online store",
    "2c1ebcd7-9c6d-4c9a-afad-900e381ecd5e": "asks to correct publication details, needs lookup",
}
# Flagged by the instruction-text scan and kept after reading the instruction.
MANUAL_WEB_KEEPS: Mapping[str, str] = {
    "b8adbc24-cef2-4b15-99d5-ecbe7ff445eb": "'Online Shopping' is slide title text",
    "7e287123-70ca-47b9-8521-47db09b69b14": "GRF reports are local PDFs",
    "9b7bc335-06b5-4cd3-9119-1a649c478509": "asks for a local Thunderbird filter only",
}


class TaskScopeError(ValueError):
    """Raised when the OSWorld checkout or a task config is not as pinned."""


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]


@dataclass(frozen=True)
class TaskRecord:
    """A raw OSWorld task plus checker-derived classification (harness-only)."""

    task_id: str
    domain: str
    raw: Mapping[str, Any]
    funcs: tuple[str, ...]
    metric_classes: tuple[str, ...]
    task_class: str
    web: bool
    web_reason: str | None

    @property
    def in_scope(self) -> bool:
        return self.task_class in SCOPE_CLASSES and not self.web


def load_verified_tasks(osworld_root: Path) -> list[Mapping[str, Any]]:
    """Load every task listed in test_nogdrive.json, in file order."""
    listing = osworld_root / VERIFIED_TASK_LIST
    if not listing.is_file():
        raise TaskScopeError(f"{listing} is missing; is this an OSWorld checkout?")
    index = json.loads(listing.read_text(encoding="utf-8"))
    tasks: list[Mapping[str, Any]] = []
    for domain, ids in index.items():
        for task_id in ids:
            path = osworld_root / "evaluation_examples" / "examples" / domain / f"{task_id}.json"
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("id") != task_id:
                raise TaskScopeError(f"{path}: id field {raw.get('id')!r} != file name")
            tasks.append({"__domain__": domain, **raw})
    return tasks


def metric_class(result_type: str | None, expected_type: str | None) -> str:
    """Class of one (result getter, expected getter) metric instance."""
    if result_type in FILE_RESULT_GETTERS:
        if expected_type == "cloud_file":
            return "1A"
        if expected_type in OFFLINE_EXPECTED_GETTERS or expected_type is None:
            return "1A" if expected_type == "local_file" else "1B"
        if expected_type == "vm_file":
            return "1V"
    if result_type in APP_CONFIG_RESULT_GETTERS and (
        expected_type in OFFLINE_EXPECTED_GETTERS or expected_type is None
    ):
        return "1C"
    if expected_type in WEB_EXPECTED_GETTERS:
        return "2W"
    return "2"


def _metric_pairs(evaluator: Mapping[str, Any]) -> list[tuple[str, str | None, str | None]]:
    funcs = [str(f) for f in _as_list(evaluator.get("func"))]
    results = _as_list(evaluator.get("result"))
    expected = evaluator.get("expected")
    if isinstance(expected, list):
        expected_list = list(expected)
    else:
        expected_list = [expected] * len(funcs) if expected else [None] * len(funcs)
    results += [None] * (len(funcs) - len(results))
    expected_list += [None] * (len(funcs) - len(expected_list))
    pairs = []
    for func, res, exp in zip(funcs, results, expected_list, strict=False):
        res_type = res.get("type") if isinstance(res, Mapping) else None
        exp_type = exp.get("type") if isinstance(exp, Mapping) else None
        pairs.append((func, res_type, exp_type))
    return pairs


def web_reason(raw: Mapping[str, Any]) -> str | None:
    """Why a task needs the web, or None. Config criteria plus manual review."""
    task_id = str(raw["id"])
    if task_id in MANUAL_WEB_EXCLUSIONS:
        return f"manual: {MANUAL_WEB_EXCLUSIONS[task_id]}"
    if raw["__domain__"] == "chrome":
        return "chrome domain"
    if raw.get("proxy"):
        return "proxy"
    config_types = {step.get("type") for step in raw.get("config", [])}
    if config_types & WEB_CONFIG_TYPES:
        return f"config step {sorted(config_types & WEB_CONFIG_TYPES)}"
    apps = set(raw.get("related_apps", []))
    if apps & WEB_APPS:
        return f"related app {sorted(apps & WEB_APPS)}"
    evaluator = raw.get("evaluator", {})
    for getter in _as_list(evaluator.get("result")) + _as_list(evaluator.get("expected")):
        if isinstance(getter, Mapping) and getter.get("type") in (
            WEB_EXPECTED_GETTERS | {"googledrive_file"}
        ):
            return f"web getter {getter.get('type')}"
    return None


def classify(raw: Mapping[str, Any]) -> TaskRecord:
    evaluator = raw.get("evaluator")
    if not isinstance(evaluator, Mapping):
        raise TaskScopeError(f"task {raw.get('id')}: no evaluator")
    pairs = _metric_pairs(evaluator)
    funcs = tuple(func for func, _, _ in pairs)
    if any(func == "infeasible" for func in funcs):
        classes: tuple[str, ...] = ("3",) * len(funcs)
        task_class = "3"
    else:
        classes = tuple(metric_class(res, exp) for _, res, exp in pairs)
        task_class = max(classes, key=lambda c: CLASS_ORDER[c])
    reason = web_reason(raw)
    return TaskRecord(
        task_id=str(raw["id"]),
        domain=str(raw["__domain__"]),
        raw=raw,
        funcs=funcs,
        metric_classes=classes,
        task_class=task_class,
        web=reason is not None,
        web_reason=reason,
    )


def pin_file_cache_url(url: str) -> str:
    """Rewrite a ``/resolve/main/`` file-cache URL to the pinned revision."""
    if not url.startswith(FILE_CACHE_PREFIX):
        raise TaskScopeError(f"initial file outside the pinned HF file cache: {url}")
    rest = url[len(FILE_CACHE_PREFIX) :]
    revision, _, path = rest.partition("/")
    if revision not in ("main", FILE_CACHE_REVISION) or not path:
        raise TaskScopeError(f"unexpected file-cache revision in {url}")
    return f"{FILE_CACHE_PREFIX}{FILE_CACHE_REVISION}/{path}"


def file_cache_path(url: str) -> str:
    """Repository-relative path of a file-cache URL (URL-decoded)."""
    pinned = pin_file_cache_url(url)
    return urllib.parse.unquote(pinned[len(FILE_CACHE_PREFIX) + len(FILE_CACHE_REVISION) + 1 :])


# The VM's OSWorld server runs with WorkingDirectory=/home/user (the VM image's
# /etc/systemd/system/osworld.service; desktop_env/server/osworld_server.service:11)
# and applies expanduser and expandvars to upload paths (server/main.py:1166).
VM_HOME = "/home/user"


def resolve_vm_path(path: str) -> str:
    """Absolute VM path for a download target as the OSWorld server resolves it."""
    text = path.replace("${HOME}", VM_HOME).replace("$HOME", VM_HOME)
    if text == "~" or text.startswith("~/"):
        text = VM_HOME + text[1:]
    if not text.startswith("/"):
        text = posixpath.join(VM_HOME, text)
    return posixpath.normpath(text)


def initial_downloads(raw: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(pinned url, absolute path in VM) for every download step of the config."""
    out: list[tuple[str, str]] = []
    for step in raw.get("config", []):
        if step.get("type") != "download":
            continue
        for item in step.get("parameters", {}).get("files", []):
            url = pin_file_cache_url(str(item["url"]))
            out.append((url, resolve_vm_path(str(item["path"]))))
    return out


def sanitize_task(raw: Mapping[str, Any], sha256_by_path: Mapping[str, str]) -> SanitizedTask:
    """The blind-author view of one task. Never includes evaluator fields."""
    files = []
    for url, path_in_vm in initial_downloads(raw):
        rel = file_cache_path(url)
        if rel not in sha256_by_path:
            raise TaskScopeError(f"no verified sha256 for initial file {rel}")
        files.append(InitialFile(url=url, path_in_vm=path_in_vm, sha256=sha256_by_path[rel]))
    task = SanitizedTask(
        task_id=str(raw["id"]),
        domain=str(raw["__domain__"]),
        instruction=str(raw["instruction"]),
        related_apps=tuple(str(app) for app in raw.get("related_apps", [])),
        initial_files=tuple(files),
        snapshot=str(raw.get("snapshot", "")),
    )
    # Round-trip through the strict validator: refuses forbidden keys.
    try:
        return SanitizedTask.from_dict(task.to_dict())
    except SchemaError as exc:
        raise TaskScopeError(f"task {raw['id']}: {exc}") from exc


def scope_records(osworld_root: Path) -> list[TaskRecord]:
    return [classify(raw) for raw in load_verified_tasks(osworld_root)]


def class_counts(records: Iterable[TaskRecord]) -> dict[str, dict[str, int]]:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        table[record.domain][record.task_class] += 1
    return {domain: dict(sorted(counter.items())) for domain, counter in sorted(table.items())}


# --- splits ---------------------------------------------------------------


def stratum_of(record: TaskRecord) -> str:
    return f"{record.domain}/{record.task_class}"


def stratified_split(
    records: Sequence[TaskRecord],
    *,
    seed: int,
    dev_fraction: float,
    confirm_size: int,
) -> dict[str, list[str]]:
    """Seeded stratified split of in-scope tasks into dev / confirm / reserve.

    Within each stratum (domain x task class) tasks are shuffled with a
    stratum-specific RNG derived from ``seed``. A share ``dev_fraction`` (at
    least one task in strata of three or more) goes to the development split.
    From the remaining tasks, ``confirm_size`` are allocated to the
    confirmatory mutation subset proportionally to stratum size (largest
    remainder, ties broken by stratum name); the rest are the reserve.
    """
    if not 0.0 < dev_fraction < 1.0:
        raise ValueError("dev_fraction must be in (0, 1)")
    by_stratum: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if not record.in_scope:
            raise ValueError(f"{record.task_id} is not in scope")
        by_stratum[stratum_of(record)].append(record.task_id)
    dev: list[str] = []
    pool: dict[str, list[str]] = {}
    for name in sorted(by_stratum):
        ids = sorted(by_stratum[name])
        random.Random(f"{seed}:{name}").shuffle(ids)
        n_dev = int(round(dev_fraction * len(ids)))
        if n_dev == 0 and len(ids) >= 3:
            n_dev = 1
        dev.extend(ids[:n_dev])
        pool[name] = ids[n_dev:]
    total = sum(len(ids) for ids in pool.values())
    if confirm_size > total:
        raise ValueError(f"confirm_size {confirm_size} exceeds the {total} non-dev tasks")
    quotas = {name: confirm_size * len(ids) / total for name, ids in pool.items()}
    alloc = {name: int(quota) for name, quota in quotas.items()}
    remainder = confirm_size - sum(alloc.values())
    order = sorted(quotas, key=lambda name: (-(quotas[name] - alloc[name]), name))
    for name in order[:remainder]:
        alloc[name] += 1
    confirm: list[str] = []
    reserve: list[str] = []
    for name in sorted(pool):
        confirm.extend(pool[name][: alloc[name]])
        reserve.extend(pool[name][alloc[name] :])
    return {"dev": sorted(dev), "confirm": sorted(confirm), "reserve": sorted(reserve)}
