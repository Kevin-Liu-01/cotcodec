"""Offline scorer: the real OSWorld ``DesktopEnv.evaluate()`` with a stubbed VM.

Runs inside the metric container (``infra/q2-mutation/metric``) under the venv
being measured. For each scoring job it

1. builds a VM root directory from the task's initial state: every config
   ``download`` (served from the pinned, hash-verified file cache) plus the
   small set of config shell steps that only create, unpack or remove files
   (``mkdir -p``, ``tar -x``, ``unzip``, ``rm``); any other setup step is
   recorded in ``setup_unemulated``;
2. overlays the candidate end-state files (gold, mutant, do-nothing) at their
   VM paths; office candidates arrive here already saved by the GUI-faithful
   LibreOffice stage (``reachability.py``), and derived artifacts such as the
   postconfig CSV conversion arrive regenerated from the saved file;
3. creates ``DesktopEnv.__new__`` and calls the unmodified pinned
   ``_set_task_info`` and ``evaluate``. The controller reads files from the VM
   root; live getters raise ``LiveStateRequired``; ``requests.get`` is
   replaced by a shim that serves file-cache URLs from local bytes and refuses
   every other URL, so ``get_cloud_file`` keeps its own skip-if-exists cache
   logic; ``action_history`` holds one non-FAIL action; postconfig is not
   replayed here because the reachability stage already applied it.

Each job is scored in a fresh worker process with a timeout, optionally twice
(determinism check). A raised exception is verdict ``error`` and never counts
as a reject: OSWorld's ``run.py`` logs and skips such a task.

The module imports OSWorld only inside the worker, so it can be imported and
unit-tested without the OSWorld checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import multiprocessing as mp
import os
import posixpath
import re
import shlex
import shutil
import sys
import tarfile
import tempfile
import time
import traceback
import urllib.parse
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness.q2_mutation.schema import VerdictRow, verdict_for_score
from harness.q2_mutation.tasks import (
    FILE_CACHE_PREFIX,
    FILE_CACHE_REVISION,
    VM_HOME,
    resolve_vm_path,
)

NON_FAIL_ACTION = "DONE"
LIVE_GETTERS = frozenset(
    {
        "vm_command_line",
        "vm_command_error",
        "vm_terminal_output",
        "accessibility_tree",
        "vm_screen_size",
        "vm_window_size",
        "vm_wallpaper",
        "list_directory",
        "vlc_playing_info",
        "default_video_player",
        "googledrive_file",
        "pdf_from_url",
        "info_from_website",
    }
)


class LiveStateRequired(RuntimeError):
    """The checker asked for live VM state that an offline harness cannot give."""


class OfflineNetworkRefused(RuntimeError):
    """The checker tried to fetch a URL that is not a pinned file-cache file."""


# --- VM root ---------------------------------------------------------------


def vm_to_host(vm_root: Path, vm_path: str) -> Path:
    """Host path of an absolute VM path inside ``vm_root`` (no escape)."""
    resolved = resolve_vm_path(vm_path)
    target = (vm_root / resolved.lstrip("/")).resolve()
    root = vm_root.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"VM path escapes the VM root: {vm_path}")
    return target


def file_cache_local(file_cache: Path, url: str) -> Path:
    """Local bytes for a file-cache URL at ``main`` or the pinned revision."""
    if not url.startswith(FILE_CACHE_PREFIX):
        raise OfflineNetworkRefused(url)
    revision, _, rest = url[len(FILE_CACHE_PREFIX) :].partition("/")
    if revision not in ("main", FILE_CACHE_REVISION):
        raise OfflineNetworkRefused(url)
    path = (file_cache / urllib.parse.unquote(rest)).resolve()
    if file_cache.resolve() not in path.parents or not path.is_file():
        raise OfflineNetworkRefused(url)
    return path


def _safe_extract_tar(archive: Path, dest: Path) -> None:
    with tarfile.open(archive) as handle:
        handle.extractall(dest, filter="data")


def _safe_extract_zip(archive: Path, dest: Path) -> None:
    root = dest.resolve()
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            target = (dest / member.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"zip member escapes destination: {member.filename}")
        handle.extractall(dest)


def _split_shell(command: Any) -> list[list[str]]:
    """Split a config command into simple argv lists (``&&`` and ``;``)."""
    if isinstance(command, list):
        argv = [str(part) for part in command]
        if argv[:2] == ["/bin/bash", "-c"] and len(argv) == 3:
            return _split_shell(argv[2])
        return [argv]
    text = str(command)
    pieces = re.split(r"\s*(?:&&|;)\s*", text)
    return [shlex.split(piece) for piece in pieces if piece.strip()]


def emulate_setup_step(vm_root: Path, argv: list[str], cwd: str) -> tuple[bool, str]:
    """Apply one file-only shell step to the VM root. Returns (handled, cwd)."""
    if not argv:
        return True, cwd
    head, args = argv[0], argv[1:]
    if head == "cd" and len(args) == 1:
        return True, resolve_vm_path(posixpath.join(cwd, args[0]))
    if head == "mkdir":
        for arg in args:
            if not arg.startswith("-"):
                vm_to_host(vm_root, posixpath.join(cwd, arg)).mkdir(parents=True, exist_ok=True)
        return True, cwd
    if head == "rm":
        for arg in args:
            if arg.startswith("-"):
                continue
            target = vm_to_host(vm_root, posixpath.join(cwd, arg))
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        return True, cwd
    if head == "unzip":
        flags = [a for a in args if a.startswith("-") and a != "-d"]
        if set(flags) - {"-q", "-o"}:
            return False, cwd
        rest = [a for a in args if not a.startswith("-") or a == "-d"]
        if "-d" in rest:
            index = rest.index("-d")
            dest_vm = rest[index + 1]
            rest = rest[:index] + rest[index + 2 :]
        else:
            dest_vm = cwd
        if len(rest) != 1:
            return False, cwd
        dest = vm_to_host(vm_root, posixpath.join(cwd, dest_vm))
        dest.mkdir(parents=True, exist_ok=True)
        _safe_extract_zip(vm_to_host(vm_root, posixpath.join(cwd, rest[0])), dest)
        return True, cwd
    if head == "tar":
        archive = None
        dest_vm = cwd
        tokens = list(args)
        for i, token in enumerate(tokens):
            if token == "-f" or (
                token.startswith("-") and not token.startswith("--") and token.endswith("f")
            ):
                archive = tokens[i + 1] if i + 1 < len(tokens) else None
            if token == "-C" and i + 1 < len(tokens):
                dest_vm = tokens[i + 1]
        flags = "".join(
            t.lstrip("-") for t in tokens if t.startswith("-") and not t.startswith("--")
        )
        if "x" not in flags or archive is None:
            return False, cwd
        dest = vm_to_host(vm_root, posixpath.join(cwd, dest_vm))
        dest.mkdir(parents=True, exist_ok=True)
        _safe_extract_tar(vm_to_host(vm_root, posixpath.join(cwd, archive)), dest)
        return True, cwd
    return False, cwd


@dataclass
class VmRootReport:
    downloaded: list[str] = field(default_factory=list)
    emulated: list[str] = field(default_factory=list)
    setup_unemulated: list[str] = field(default_factory=list)


def build_initial_vm_root(raw: Mapping[str, Any], file_cache: Path, vm_root: Path) -> VmRootReport:
    """Initial VM file state of a task: downloads plus file-only shell steps."""
    report = VmRootReport()
    for step in raw.get("config", []):
        kind = step.get("type")
        params = step.get("parameters", {})
        if kind == "download":
            for item in params.get("files", []):
                target = vm_to_host(vm_root, str(item["path"]))
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file_cache_local(file_cache, str(item["url"])), target)
                report.downloaded.append(resolve_vm_path(str(item["path"])))
        elif kind in ("execute", "command"):
            command = params.get("command")
            cwd = VM_HOME
            for argv in _split_shell(command):
                text = " ".join(argv)[:160]
                try:
                    handled, cwd = emulate_setup_step(vm_root, argv, cwd)
                except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
                    report.setup_unemulated.append(f"{text} [failed: {exc}]")
                    continue
                (report.emulated if handled else report.setup_unemulated).append(text)
        elif kind not in ("launch", "open", "activate_window", "sleep", "close_window"):
            report.setup_unemulated.append(f"config step {kind}")
    return report


# Postconfig steps handled by the LibreOffice reachability stage (GUI and
# LibreOffice conversions); everything else that only touches files is
# emulated here, after the saved files are in place.
GUI_POSTCONFIG = frozenset({"activate_window", "sleep", "close_window", "launch", "open"})
STDOUT_COMMANDS = frozenset({"diff", "ls"})


def _is_gui_execute(argv: list[str]) -> bool:
    head = argv[0] if argv else ""
    if head in ("python", "python3") and len(argv) >= 3 and "pyautogui" in argv[2]:
        return True
    return head in ("libreoffice", "soffice") and "--convert-to" in argv


def apply_postconfig_file_steps(
    raw: Mapping[str, Any], file_cache: Path, vm_root: Path, cache_dir: Path
) -> list[str]:
    """Download, file-only shell and ``stdout``-capturing diff/ls postconfig steps.

    OSWorld's setup controller writes an ``execute`` step's stdout to
    ``cache_dir/<stdout>``, where a ``cache_file`` getter reads it. Commands run
    on the VM root with paths mapped in and the VM root prefix mapped back out.
    Returns the steps that were not emulated.
    """
    unemulated: list[str] = []
    for step in raw.get("evaluator", {}).get("postconfig", []):
        kind = step.get("type")
        params = step.get("parameters", {})
        if kind in GUI_POSTCONFIG:
            continue
        if kind == "download":
            for item in params.get("files", []):
                target = vm_to_host(vm_root, str(item["path"]))
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file_cache_local(file_cache, str(item["url"])), target)
            continue
        if kind not in ("execute", "command"):
            unemulated.append(f"postconfig {kind}")
            continue
        argvs = _split_shell(params.get("command"))
        if all(_is_gui_execute(argv) for argv in argvs):
            continue
        stdout_name = params.get("stdout")
        if stdout_name and len(argvs) == 1 and argvs[0] and argvs[0][0] in STDOUT_COMMANDS:
            output = _run_mapped(vm_root, argvs[0])
            (cache_dir / str(stdout_name)).write_text(output, encoding="utf-8")
            continue
        cwd = VM_HOME
        for argv in argvs:
            try:
                handled, cwd = emulate_setup_step(vm_root, argv, cwd)
            except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
                unemulated.append(f"{' '.join(argv)[:160]} [failed: {exc}]")
                continue
            if not handled:
                unemulated.append(" ".join(argv)[:160])
    return unemulated


def _run_mapped(vm_root: Path, argv: list[str]) -> str:
    """Run diff/ls on the VM root as if inside the VM (cwd /home/user)."""
    import subprocess

    root = str(vm_root.resolve())
    mapped = [argv[0]]
    for arg in argv[1:]:
        if arg.startswith("-"):
            mapped.append(arg)
        else:
            mapped.append(str(vm_to_host(vm_root, posixpath.join(VM_HOME, arg))))
    home = vm_to_host(vm_root, VM_HOME)
    home.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(mapped, cwd=home, capture_output=True, text=True, timeout=120)
    return result.stdout.replace(root, "")


def overlay_tree(source: Path, vm_root: Path) -> int:
    """Copy a VM-shaped tree (e.g. home/user/.config/vlc/vlcrc) into the VM root.

    Top-level files of ``source`` (receipts, hash lists) are not VM content.
    """
    count = 0
    for path in sorted(source.rglob("*")):
        if path.parent == source:
            continue
        if path.is_file() and not path.is_symlink():
            target = vm_root / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            count += 1
    return count


# --- stubs -----------------------------------------------------------------


class StubController:
    """Reads VM files from a local directory; refuses live-state requests."""

    def __init__(self, vm_root: Path) -> None:
        self.vm_root = vm_root

    def get_file(self, path: str) -> bytes | None:
        target = vm_to_host(self.vm_root, path)
        return target.read_bytes() if target.is_file() else None

    def get_vm_platform(self) -> str:
        return "Linux"

    def execute_python_command(self, command: str) -> dict[str, str]:
        match = re.search(r"expanduser\(\s*['\"]([^'\"]+)['\"]", command)
        if match:
            return {"output": match.group(1).replace("~", VM_HOME, 1) + "\n"}
        raise LiveStateRequired(f"execute_python_command: {command[:80]}")

    def __getattr__(self, name: str) -> Any:
        def refuse(*_args: Any, **_kwargs: Any) -> Any:
            raise LiveStateRequired(f"controller.{name}")

        return refuse


class StubSetupController:
    """Postconfig is applied by the reachability stage, never replayed here."""

    def __init__(self) -> None:
        self.postconfig_seen: list[Any] = []

    def setup(self, config: Any, use_proxy: bool = False) -> bool:
        self.postconfig_seen.append(config)
        return True

    def __getattr__(self, name: str) -> Any:
        def refuse(*_args: Any, **_kwargs: Any) -> Any:
            raise LiveStateRequired(f"setup_controller.{name}")

        return refuse


class _OfflineResponse:
    def __init__(self, data: bytes, url: str) -> None:
        self._data = data
        self.url = url
        self.status_code = 200
        self.content = data
        self.headers = {"content-length": str(len(data))}

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 8192) -> Iterable[bytes]:
        stream = io.BytesIO(self._data)
        while chunk := stream.read(chunk_size):
            yield chunk

    @property
    def text(self) -> str:
        return self._data.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self._data)


def make_offline_get(file_cache: Path, fetched: list[str]) -> Any:
    def offline_get(url: str, *_args: Any, **_kwargs: Any) -> _OfflineResponse:
        local = file_cache_local(file_cache, str(url))
        fetched.append(str(url))
        return _OfflineResponse(local.read_bytes(), str(url))

    return offline_get


# --- scoring ---------------------------------------------------------------


@dataclass(frozen=True)
class ScoreJob:
    """One candidate end state to score. ``files`` maps VM path -> local path
    (``None`` deletes that VM path). Paths are inside the container."""

    mutant_id: str
    task_id: str
    files: Mapping[str, str | None]
    saved_via: str = "none"
    lo_build: str | None = None
    include_initial: bool = True
    candidate_sha256: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScoreJob:
        return cls(
            mutant_id=str(data["mutant_id"]),
            task_id=str(data["task_id"]),
            files=dict(data.get("files", {})),
            saved_via=str(data.get("saved_via", "none")),
            lo_build=data.get("lo_build"),
            include_initial=bool(data.get("include_initial", True)),
            candidate_sha256=data.get("candidate_sha256"),
        )


def task_path(osworld: Path, task_id: str) -> Path:
    matches = list((osworld / "evaluation_examples" / "examples").glob(f"*/{task_id}.json"))
    if len(matches) != 1:
        raise FileNotFoundError(f"task {task_id}: {len(matches)} config files")
    return matches[0]


def load_task(osworld: Path, task_id: str) -> dict[str, Any]:
    return json.loads(task_path(osworld, task_id).read_text(encoding="utf-8"))


def checker_funcs(raw: Mapping[str, Any]) -> list[str]:
    func = raw["evaluator"]["func"]
    return [str(f) for f in func] if isinstance(func, list) else [str(func)]


def _sha256_tree(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.is_file() else b"-")
    return digest.hexdigest()


def _score_in_worker(payload: dict[str, Any], queue: Any) -> None:
    """Worker body: build the VM root, call the pinned evaluate()."""
    import logging

    logging.disable(logging.CRITICAL)
    osworld = Path(payload["osworld"])
    file_cache = Path(payload["file_cache"])
    job = ScoreJob.from_dict(payload["job"])
    out: dict[str, Any] = {"score": None, "error": None, "notes": {}}
    with tempfile.TemporaryDirectory(prefix="q2m-") as tmp:
        tmp_path = Path(tmp)
        vm_root = tmp_path / "vm"
        vm_root.mkdir()
        try:
            raw = load_task(osworld, job.task_id)
            report = VmRootReport()
            baseline = payload.get("vm_baseline")
            if baseline:
                out["notes"]["vm_baseline_files"] = overlay_tree(Path(baseline), vm_root)
            if job.include_initial:
                report = build_initial_vm_root(raw, file_cache, vm_root)
            scored: list[Path] = []
            for vm_path, local in job.files.items():
                target = vm_to_host(vm_root, vm_path)
                if local is None:
                    if target.is_dir():
                        shutil.rmtree(target)
                    elif target.exists():
                        target.unlink()
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local, target)
                scored.append(target)
            out["notes"]["setup_unemulated"] = report.setup_unemulated
            out["scored_sha256"] = _sha256_tree(scored) if scored else None
            evaluator = raw["evaluator"]
            for getter in _as_list(evaluator.get("result")) + _as_list(evaluator.get("expected")):
                if isinstance(getter, Mapping) and getter.get("type") in LIVE_GETTERS:
                    raise LiveStateRequired(f"getter {getter.get('type')}")
            if str(osworld) not in sys.path:
                sys.path.insert(0, str(osworld))
            import requests

            fetched: list[str] = []
            requests.get = make_offline_get(file_cache, fetched)
            from desktop_env.desktop_env import DesktopEnv

            env = DesktopEnv.__new__(DesktopEnv)
            env.cache_dir_base = str(tmp_path / "cache")
            env.enable_proxy = False
            env.is_environment_used = False
            env.action_history = [NON_FAIL_ACTION]
            env.controller = StubController(vm_root)
            env.setup_controller = StubSetupController()
            env.vm_ip = "127.0.0.1"
            env.server_port = 0
            env._set_task_info(raw)
            out["notes"]["postconfig_unemulated"] = apply_postconfig_file_steps(
                raw, file_cache, vm_root, Path(env.cache_dir)
            )
            result = env.evaluate()
            out["score"] = None if result is None else float(result)
            if result is None:
                out["error"] = "evaluate() returned None"
            out["notes"]["cloud_fetches"] = len(fetched)
        except LiveStateRequired as exc:
            out["error"] = f"LiveStateRequired: {exc}"
        except OfflineNetworkRefused as exc:
            out["error"] = f"OfflineNetworkRefused: {exc}"
        except BaseException as exc:  # noqa: BLE001 - every checker exception is a verdict
            out["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
            out["notes"]["traceback_tail"] = traceback.format_exc()[-800:]
    queue.put(out)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]


# One BLAS/OpenMP thread per scoring process: many processes run side by side
# and the default (all 208 cores each) oversubscribes the node and timed out a
# scikit-image checker on the dev split. Recorded in every notes row.
THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}


def score_once(
    job: ScoreJob,
    osworld: Path,
    file_cache: Path,
    timeout: float,
    vm_baseline: Path | None = None,
) -> dict[str, Any]:
    os.environ.update(THREAD_ENV)
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    payload = {
        "osworld": str(osworld),
        "file_cache": str(file_cache),
        "job": job.__dict__,
        "vm_baseline": str(vm_baseline) if vm_baseline else None,
    }
    process = ctx.Process(target=_score_in_worker, args=(payload, queue))
    started = time.monotonic()
    process.start()
    # Read the result before joining: a child whose queue feeder still holds
    # data cannot exit, so join-then-get can stall until the timeout.
    try:
        out = queue.get(timeout=timeout)
    except Exception:  # noqa: BLE001 - empty queue at the deadline
        out = None
    process.join(10)
    if process.is_alive():
        process.kill()
        process.join()
    if out is None:
        timed_out = time.monotonic() - started >= timeout
        return {
            "score": None,
            "error": (
                f"Timeout after {timeout}s"
                if timed_out
                else f"worker exit {process.exitcode} without result"
            ),
            "infra_timeout": timed_out,
            "notes": {},
            "seconds": round(time.monotonic() - started, 3),
        }
    out["seconds"] = round(time.monotonic() - started, 3)
    return out


def score_job(
    job: ScoreJob,
    *,
    osworld: Path,
    file_cache: Path,
    venv_lock_sha256: str,
    dep_set: str,
    timeout: float = 300.0,
    repeat: int = 2,
    harness_revision: str | None = None,
    vm_baseline: Path | None = None,
) -> tuple[VerdictRow, dict[str, Any]]:
    """Score one job ``repeat`` times in fresh processes; return the row and notes."""
    raw = load_task(osworld, job.task_id)
    runs = []
    infra_timeouts = 0
    for _ in range(max(1, repeat)):
        # A timeout is an infrastructure failure, not a checker verdict: retry
        # it up to twice and count it; a checker exception is never retried.
        for _attempt in range(3):
            run = score_once(job, osworld, file_cache, timeout, vm_baseline)
            if not run.get("infra_timeout"):
                break
            infra_timeouts += 1
        runs.append(run)
    first = runs[0]
    nondeterministic = any(
        (run["score"], run["error"] is None) != (first["score"], first["error"] is None)
        for run in runs[1:]
    )
    score = first["score"] if first["error"] is None else None
    row: dict[str, Any] = {
        "mutant_id": job.mutant_id,
        "task_id": job.task_id,
        "checker_funcs": checker_funcs(raw),
        "score": score,
        "verdict": verdict_for_score(score),
        "saved_via": job.saved_via,
        "lo_build": job.lo_build,
        "venv_lock_sha256": venv_lock_sha256,
        "seconds": round(sum(run["seconds"] for run in runs), 3),
        "dep_set": dep_set,
        "conj": str(raw["evaluator"].get("conj", "and")),
    }
    if score is None:
        row["error"] = first["error"] or "unknown"
    if job.candidate_sha256:
        row["candidate_sha256"] = job.candidate_sha256
    if first.get("scored_sha256"):
        row["scored_sha256"] = first["scored_sha256"]
    if harness_revision:
        row["harness_revision"] = harness_revision
    notes = {
        "mutant_id": job.mutant_id,
        "thread_env": THREAD_ENV,
        "infra_timeouts": infra_timeouts,
        "nondeterministic": nondeterministic,
        "repeat_scores": [run["score"] for run in runs],
        "repeat_errors": [run["error"] for run in runs],
        **first.get("notes", {}),
    }
    return VerdictRow.from_dict(row), notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=Path, required=True, help="JSONL of ScoreJob objects")
    parser.add_argument("--out", type=Path, required=True, help="verdict JSONL to write")
    parser.add_argument("--notes", type=Path, required=True, help="per-job notes JSONL")
    parser.add_argument("--osworld", type=Path, required=True)
    parser.add_argument("--file-cache", type=Path, required=True)
    parser.add_argument(
        "--requirements",
        type=Path,
        required=True,
        help="the requirements file this venv was built from",
    )
    parser.add_argument("--dep-set", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--harness-revision", default=None)
    parser.add_argument(
        "--vm-baseline", type=Path, default=None, help="VM-shaped tree of baseline config files"
    )
    args = parser.parse_args(argv)
    lock_sha = hashlib.sha256(args.requirements.read_bytes()).hexdigest()
    jobs = [
        ScoreJob.from_dict(json.loads(line))
        for line in args.jobs.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    from concurrent.futures import ThreadPoolExecutor

    def one(job: ScoreJob) -> tuple[VerdictRow, dict[str, Any]]:
        return score_job(
            job,
            osworld=args.osworld,
            file_cache=args.file_cache,
            venv_lock_sha256=lock_sha,
            dep_set=args.dep_set,
            timeout=args.timeout,
            repeat=args.repeat,
            harness_revision=args.harness_revision,
            vm_baseline=args.vm_baseline,
        )

    with (
        ThreadPoolExecutor(max_workers=args.workers) as pool,
        args.out.open("w", encoding="utf-8") as out,
        args.notes.open("w", encoding="utf-8") as notes,
    ):
        for row, note in pool.map(one, jobs):
            out.write(row.to_jsonl() + "\n")
            notes.write(json.dumps(note, sort_keys=True) + "\n")
            out.flush()
            notes.flush()
    print(json.dumps({"jobs": len(jobs), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONHASHSEED", "0")
    raise SystemExit(main())
