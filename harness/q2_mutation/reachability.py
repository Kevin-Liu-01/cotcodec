"""GUI-faithful LibreOffice save stage ("reachability stage").

In the real OSWorld pipeline every office end state is re-saved by the
LibreOffice instance in the VM before a checker reads it: the task's
postconfig activates the document window (``wmctrl -Fa <title>``) and sends
Ctrl+S through pyautogui. A byte-level edit that LibreOffice normalizes away
on load never reaches the checker. This stage reproduces that path in a
GPU-less, network-less container:

* Xvfb plus a minimal EWMH window manager (openbox), so ``wmctrl -Fa`` works
  as it does under the VM's GNOME session;
* non-headless ``soffice`` from the build that matches the VM, started with a
  fresh copy of the VM's LibreOffice user profile as ``$HOME`` (the default
  profile, so a postconfig ``libreoffice --convert-to`` reaches the running
  instance exactly as in the VM);
* the candidate files placed at their VM paths under a per-worker root, the
  documents opened before any postconfig step (the corrected injection
  protocol: the document is opened from the mutant, never replaced under an
  open instance);
* the task's postconfig replayed step by step (activate window, Ctrl+S via
  XTEST, Enter, sleeps, ``libreoffice --convert-to`` with its exact filter
  string); steps that are not file saves are recorded as unemulated;
* when a task has no postconfig save, every OOXML/ODF candidate gets one
  agent-equivalent save (open, activate, Ctrl+S), because a GUI agent's file
  was written by this LibreOffice.

Every save records whether the file changed, how long the write took (the VM
reads the file 0.5 s after Ctrl+S; a slower save is timing-sensitive), and any
dialog window that appeared. Nothing is retried silently.

This module runs inside the LibreOffice container with its system Python
(3.10); it uses only the standard library.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import posixpath
import re
import shlex
import shutil
import signal
import subprocess
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VM_HOME = "/home/user"
LO_SAVE_EXTENSIONS = frozenset({".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"})
LO_APP_TITLES = {
    ".docx": "LibreOffice Writer",
    ".odt": "LibreOffice Writer",
    ".doc": "LibreOffice Writer",
    ".xlsx": "LibreOffice Calc",
    ".ods": "LibreOffice Calc",
    ".xls": "LibreOffice Calc",
    ".csv": "LibreOffice Calc",
    ".pptx": "LibreOffice Impress",
    ".odp": "LibreOffice Impress",
    ".ppt": "LibreOffice Impress",
}
HOTKEY_RE = re.compile(r"pyautogui\.hotkey\(\s*\[?\s*([^)\]]*)\]?\s*\)")
PRESS_RE = re.compile(r"pyautogui\.press\(\s*\[?\s*['\"]([a-z0-9]+)['\"]\s*\]?\s*\)")
SLEEP_RE = re.compile(r"time\.sleep\(\s*([0-9.]+)\s*\)")
XDOTOOL_KEYS = {"ctrl": "ctrl", "shift": "shift", "alt": "alt", "enter": "Return", "s": "s"}


# --- planning (pure) --------------------------------------------------------


@dataclass(frozen=True)
class Step:
    kind: str  # open | activate | key | sleep | convert | unemulated
    arg: str = ""
    strict: bool = False
    seconds: float = 0.0
    argv: tuple[str, ...] = ()


def resolve_vm_path(path: str) -> str:
    text = path.replace("${HOME}", VM_HOME).replace("$HOME", VM_HOME)
    if text == "~" or text.startswith("~/"):
        text = VM_HOME + text[1:]
    if not text.startswith("/"):
        text = posixpath.join(VM_HOME, text)
    return posixpath.normpath(text)


def _keys_from_hotkey(arg_text: str) -> str:
    keys = [token.strip().strip("'\"") for token in arg_text.split(",") if token.strip()]
    return "+".join(XDOTOOL_KEYS.get(key, key) for key in keys)


def parse_execute(command: Any) -> list[Step]:
    """Translate one postconfig ``execute`` command into steps."""
    argv = (
        [str(part) for part in command] if isinstance(command, list) else shlex.split(str(command))
    )
    if not argv:
        return []
    if argv[0] in ("python", "python3") and len(argv) >= 3 and argv[1] == "-c":
        code = argv[2]
        if "pyautogui.write" in code:
            return [Step("unemulated", f"pyautogui.write: {code[:80]}")]
        steps: list[Step] = []
        pattern = r"time\.sleep\([^)]*\)|pyautogui\.(?:hotkey|press)\([^)]*\)"
        for match in re.finditer(pattern, code):
            text = match.group(0)
            if text.startswith("time.sleep"):
                sleep = SLEEP_RE.search(text)
                steps.append(Step("sleep", seconds=float(sleep.group(1)) if sleep else 0.0))
            elif text.startswith("pyautogui.hotkey"):
                hot = HOTKEY_RE.search(text)
                steps.append(Step("key", _keys_from_hotkey(hot.group(1) if hot else "")))
            else:
                press = PRESS_RE.search(text)
                key = press.group(1) if press else ""
                steps.append(Step("key", XDOTOOL_KEYS.get(key, key)))
        return steps or [Step("unemulated", f"python -c: {code[:80]}")]
    if argv[0] in ("libreoffice", "soffice") and "--convert-to" in argv:
        return [Step("convert", argv=tuple(argv))]
    return [Step("unemulated", " ".join(argv)[:160])]


def plan_postconfig(postconfig: Sequence[Mapping[str, Any]]) -> list[Step]:
    steps: list[Step] = []
    for item in postconfig:
        kind = item.get("type")
        params = item.get("parameters", {})
        if kind == "activate_window":
            steps.append(
                Step("activate", str(params.get("window_name", "")), bool(params.get("strict")))
            )
        elif kind == "sleep":
            steps.append(Step("sleep", seconds=float(params.get("seconds", 0))))
        elif kind in ("execute", "command"):
            steps.extend(parse_execute(params.get("command")))
        elif kind == "open":
            steps.append(Step("open", resolve_vm_path(str(params.get("path", "")))))
        else:
            steps.append(Step("unemulated", f"postconfig {kind}"))
    return steps


def window_title_for(vm_path: str) -> str | None:
    ext = posixpath.splitext(vm_path)[1].lower()
    app = LO_APP_TITLES.get(ext)
    return f"{posixpath.basename(vm_path)} - {app}" if app else None


def documents_to_open(steps: Sequence[Step], candidate_paths: Iterable[str]) -> list[str]:
    """Candidate documents whose window a postconfig step activates."""
    paths = list(candidate_paths)
    wanted: list[str] = []
    for step in steps:
        if step.kind != "activate":
            continue
        for path in paths:
            title = window_title_for(path)
            matches = title and (
                step.arg == title or step.arg.startswith(posixpath.basename(path) + " ")
            )
            if matches and path not in wanted:
                wanted.append(path)
    return wanted


def build_plan(raw_task: Mapping[str, Any], candidate_paths: Sequence[str]) -> dict[str, Any]:
    """Opening order and replay steps for one candidate end state."""
    postconfig = raw_task.get("evaluator", {}).get("postconfig", [])
    steps = plan_postconfig(postconfig)
    saves_in_postconfig = any(step.kind == "key" and step.arg == "ctrl+s" for step in steps)
    office = [p for p in candidate_paths if posixpath.splitext(p)[1].lower() in LO_SAVE_EXTENSIONS]
    opened_by_postconfig = documents_to_open(steps, candidate_paths) if saves_in_postconfig else []
    agent_saves = [p for p in office if p not in opened_by_postconfig]
    return {
        "open_before_postconfig": opened_by_postconfig,
        "agent_saves": agent_saves,
        "postconfig_steps": [asdict(step) for step in steps],
        "saves_in_postconfig": saves_in_postconfig,
        "unemulated": [step.arg for step in steps if step.kind == "unemulated"],
    }


# --- execution (container only) -------------------------------------------------


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class SaveEvent:
    vm_path: str
    reason: str  # postconfig | agent_save
    before_sha256: str | None
    after_sha256: str | None
    written: bool
    seconds_to_write: float | None
    dialogs: list[str] = field(default_factory=list)


class Display:
    """Xvfb + openbox on one display number."""

    def __init__(self, number: int, workdir: Path) -> None:
        self.number = number
        self.name = f":{number}"
        self.workdir = workdir
        self.procs: list[subprocess.Popen[bytes]] = []

    def env(self, home: Path) -> dict[str, str]:
        env = {
            "DISPLAY": self.name,
            "HOME": str(home),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "SAL_USE_VCLPLUGIN": os.environ.get("SAL_USE_VCLPLUGIN", "gen"),
        }
        return env

    def start(self) -> None:
        log = (self.workdir / f"xvfb-{self.number}.log").open("wb")
        self.procs.append(
            subprocess.Popen(
                ["Xvfb", self.name, "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            probe = subprocess.run(["xdpyinfo"], env={"DISPLAY": self.name}, capture_output=True)
            if probe.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError(f"Xvfb {self.name} did not start")
        wm_home = self.workdir / "wm-home"
        wm_home.mkdir(parents=True, exist_ok=True)
        self.procs.append(
            subprocess.Popen(
                ["openbox"],
                env=self.env(wm_home),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        )
        time.sleep(0.5)

    def stop(self) -> None:
        for proc in reversed(self.procs):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def list_windows(env: Mapping[str, str]) -> list[str]:
    out = subprocess.run(["wmctrl", "-l"], env=dict(env), capture_output=True, text=True)
    titles = []
    for line in out.stdout.splitlines():
        parts = line.split(None, 3)
        titles.append(parts[3] if len(parts) == 4 else "")
    return titles


class LoSession:
    """One LibreOffice instance with a fresh copy of the VM profile."""

    def __init__(self, display: Display, root: Path, soffice: str, profile_template: Path | None):
        self.display = display
        self.root = root
        self.vm_root = root / "vm"
        self.home = root / "home"
        self.soffice = soffice
        self.profile_template = profile_template
        self.procs: list[subprocess.Popen[bytes]] = []
        self.log: list[dict[str, Any]] = []

    def reset(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.vm_root.mkdir(parents=True)
        profile_parent = self.home / ".config" / "libreoffice" / "4"
        profile_parent.mkdir(parents=True)
        if self.profile_template is not None:
            shutil.copytree(self.profile_template, profile_parent / "user")

    @property
    def env(self) -> dict[str, str]:
        return self.display.env(self.home)

    def host_path(self, vm_path: str) -> Path:
        return self.vm_root / resolve_vm_path(vm_path).lstrip("/")

    def _event(self, kind: str, **data: Any) -> None:
        self.log.append({"t": round(time.monotonic(), 3), "event": kind, **data})

    def open(self, vm_path: str, timeout: float = 90.0) -> bool:
        target = self.host_path(vm_path)
        proc = subprocess.Popen(
            [self.soffice, str(target)],
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.procs.append(proc)
        name = target.name
        stem = target.stem
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for title in list_windows(self.env):
                if name in title or stem in title:
                    self._event("opened", vm_path=vm_path, title=title)
                    time.sleep(1.0)
                    return True
            time.sleep(0.5)
        self._event("open_timeout", vm_path=vm_path, windows=list_windows(self.env))
        return False

    def activate(self, title: str, strict: bool) -> bool:
        flag = "-Fa" if strict else "-a"
        result = subprocess.run(
            ["wmctrl", flag, title], env=self.env, capture_output=True, text=True
        )
        ok = result.returncode == 0
        self._event("activate", title=title, strict=strict, ok=ok)
        return ok

    def key(self, combo: str) -> None:
        subprocess.run(["xdotool", "key", "--clearmodifiers", combo], env=self.env, check=False)
        self._event("key", combo=combo)

    def wait_written(
        self, path: Path, before: tuple[float, int] | None, timeout: float
    ) -> float | None:
        """Seconds until the file's (mtime, size) changed and stayed stable for 0.3 s."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if path.is_file():
                stat = path.stat()
                if before is None or (stat.st_mtime, stat.st_size) != before:
                    time.sleep(0.3)
                    again = path.stat()
                    if (again.st_mtime, again.st_size) == (stat.st_mtime, stat.st_size):
                        return round(time.monotonic() - start, 3)
            time.sleep(0.1)
        return None

    def save_with_ctrl_s(self, vm_path: str, reason: str, timeout: float = 30.0) -> SaveEvent:
        target = self.host_path(vm_path)
        before_sha = sha256_file(target)
        before_stat = (target.stat().st_mtime, target.stat().st_size) if target.is_file() else None
        windows_before = set(list_windows(self.env))
        self.key("ctrl+s")
        seconds = self.wait_written(target, before_stat, timeout)
        dialogs = sorted(set(list_windows(self.env)) - windows_before)
        after_sha = sha256_file(target)
        event = SaveEvent(
            vm_path=vm_path,
            reason=reason,
            before_sha256=before_sha,
            after_sha256=after_sha,
            written=seconds is not None,
            seconds_to_write=seconds,
            dialogs=dialogs,
        )
        self._event("save", **asdict(event))
        return event

    def convert(self, argv: Sequence[str], timeout: float = 120.0) -> dict[str, Any]:
        mapped = [self.soffice]
        for arg in argv[1:]:
            mapped.append(str(self.host_path(arg)) if arg.startswith("/") else arg)
        started = time.monotonic()
        result = subprocess.run(
            mapped, env=self.env, capture_output=True, text=True, timeout=timeout
        )
        info = {
            "argv": list(argv),
            "returncode": result.returncode,
            "seconds": round(time.monotonic() - started, 3),
            "stdout_tail": result.stdout[-300:],
        }
        self._event("convert", **info)
        return info

    def close(self) -> None:
        for proc in self.procs:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        self.procs.clear()
        # soffice.bin can outlive its launcher's group when the launcher hands
        # the document to an already running instance; kill by session path.
        subprocess.run(["pkill", "-KILL", "-f", str(self.root)], check=False)
        time.sleep(0.3)


def lo_version(soffice: str) -> str:
    out = subprocess.run([soffice, "--version"], capture_output=True, text=True, timeout=120)
    return out.stdout.strip().splitlines()[0] if out.stdout.strip() else "unknown"


def run_job(
    session: LoSession, job: Mapping[str, Any], raw_task: Mapping[str, Any], out_dir: Path
) -> dict[str, Any]:
    """Place files, open documents, replay postconfig, collect saved files."""
    session.reset()
    session.log = []
    files: Mapping[str, str | None] = job["files"]
    for vm_path, local in files.items():
        if local is None:
            continue
        target = session.host_path(vm_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, target)
    before = {p: sha256_file(session.host_path(p)) for p in files}
    plan = build_plan(raw_task, [p for p, local in files.items() if local is not None])
    saves: list[SaveEvent] = []
    failures: list[str] = []
    try:
        for vm_path in plan["agent_saves"]:
            title = window_title_for(vm_path)
            if not session.open(vm_path):
                failures.append(f"open failed: {vm_path}")
                continue
            if title and not session.activate(title, strict=True):
                failures.append(f"activate failed: {title}")
            saves.append(session.save_with_ctrl_s(vm_path, "agent_save"))
        for vm_path in plan["open_before_postconfig"]:
            if not session.open(vm_path):
                failures.append(f"open failed: {vm_path}")
        last_activated: str | None = None
        for raw_step in plan["postconfig_steps"]:
            step = Step(**{**raw_step, "argv": tuple(raw_step["argv"])})
            if step.kind == "activate":
                if not session.activate(step.arg, step.strict):
                    failures.append(f"activate failed: {step.arg}")
                last_activated = step.arg
            elif step.kind == "sleep":
                time.sleep(step.seconds)
            elif step.kind == "key" and step.arg == "ctrl+s":
                target = next(
                    (
                        p
                        for p in plan["open_before_postconfig"]
                        if last_activated and window_title_for(p) == last_activated
                    ),
                    None,
                )
                if target is None:
                    session.key("ctrl+s")
                    failures.append(f"ctrl+s with no mapped document (window {last_activated})")
                else:
                    saves.append(session.save_with_ctrl_s(target, "postconfig"))
            elif step.kind == "key":
                session.key(step.arg)
            elif step.kind == "convert":
                session.convert(step.argv)
            elif step.kind == "open":
                session.open(step.arg)
    finally:
        session.close()
    outputs: dict[str, str] = {}
    job_out = out_dir / job["job_id"]
    if job_out.exists():
        shutil.rmtree(job_out)
    for host_file in sorted(session.vm_root.rglob("*")):
        if not host_file.is_file() or host_file.name.startswith(".~lock."):
            continue
        vm_path = "/" + host_file.relative_to(session.vm_root).as_posix()
        if vm_path in files and before.get(vm_path) == sha256_file(host_file):
            continue  # unchanged: the scorer keeps its own copy of the candidate
        dest = job_out / vm_path.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(host_file, dest)
        outputs[vm_path] = str(dest)
    return {
        "job_id": job["job_id"],
        "task_id": job["task_id"],
        "plan": plan,
        "saves": [asdict(event) for event in saves],
        "failures": failures,
        "before_sha256": before,
        "after_sha256": {p: sha256_file(session.host_path(p)) for p in files},
        "outputs": outputs,
        "events": session.log,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--osworld", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--soffice", default="soffice")
    parser.add_argument("--profile-template", type=Path, default=None)
    parser.add_argument("--worker", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    jobs = [json.loads(line) for line in args.jobs.read_text().splitlines() if line.strip()]
    mine = [job for index, job in enumerate(jobs) if index % args.workers == args.worker]
    work = Path(os.environ.get("TMPDIR", "/tmp")) / f"q2lo-{args.worker}"
    work.mkdir(parents=True, exist_ok=True)
    display = Display(100 + args.worker, work)
    display.start()
    build = lo_version(args.soffice)
    results_path = args.out / f"reachability-{args.worker}.jsonl"
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        with results_path.open("w", encoding="utf-8") as handle:
            session = LoSession(display, work / "session", args.soffice, args.profile_template)
            for job in mine:
                examples = args.osworld / "evaluation_examples" / "examples"
                task_file = next(examples.glob(f"*/{job['task_id']}.json"))
                raw = json.loads(task_file.read_text(encoding="utf-8"))
                started = time.monotonic()
                try:
                    result = run_job(session, job, raw, args.out / "files")
                except Exception as exc:  # noqa: BLE001 - an infrastructure failure, recorded
                    result = {
                        "job_id": job["job_id"],
                        "task_id": job["task_id"],
                        "infra_error": repr(exc),
                    }
                result["lo_build"] = build
                result["seconds"] = round(time.monotonic() - started, 3)
                handle.write(json.dumps(result, sort_keys=True) + "\n")
                handle.flush()
    finally:
        display.stop()
    print(json.dumps({"worker": args.worker, "jobs": len(mine), "lo_build": build}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
