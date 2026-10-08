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
# File-only postconfig commands the metric-side scorer emulates after the saves
# (offline_eval.apply_postconfig_file_steps); they are not GUI steps.
METRIC_SIDE_COMMANDS = frozenset({"diff", "ls", "rm", "unzip", "mkdir", "tar", "zip"})
# Keys are kept in pyautogui's names and sent with pyautogui itself, from the
# VM's own installation (PyAutoGUI 0.9.54, python-xlib 0.33, XTEST), exactly
# as the postconfig command does in the VM.


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
    return "+".join(keys)


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
                steps.append(Step("key", key))
        return steps or [Step("unemulated", f"python -c: {code[:80]}")]
    if argv[0] in ("libreoffice", "soffice") and "--convert-to" in argv:
        return [Step("convert", argv=tuple(argv))]
    if argv[0] in METRIC_SIDE_COMMANDS or (argv[:2] == ["/bin/bash", "-c"] and len(argv) == 3):
        return [Step("metric_side", " ".join(argv)[:160])]
    return [Step("unemulated", " ".join(argv)[:160])]


def derived_outputs(argv: Sequence[str]) -> list[tuple[str, str, str]]:
    """(VM out dir, input stem, extension) a ``--convert-to`` command produces.

    LibreOffice 7.3 writes ``stem.ext``, or ``stem-SheetName.ext`` when the CSV
    filter's sheet option selects a sheet; both shapes are matched.
    """
    args = list(argv)
    if "--convert-to" not in args:
        return []
    target = args[args.index("--convert-to") + 1]
    ext = target.split(":", 1)[0]
    outdir = args[args.index("--outdir") + 1] if "--outdir" in args else VM_HOME
    inputs = [a for a in args[1:] if a.startswith("/") and a != outdir]
    return [
        (resolve_vm_path(outdir), posixpath.splitext(posixpath.basename(path))[0], ext)
        for path in inputs
    ]


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
        elif kind == "download":
            steps.append(Step("metric_side", "postconfig download"))
        elif kind in ("close_window", "launch"):
            steps.append(Step("unemulated", f"postconfig {kind}"))
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


def convert_inputs(argv: Sequence[str]) -> list[str]:
    """VM paths a ``--convert-to`` command reads (its source documents)."""
    args = list(argv)
    if "--convert-to" not in args:
        return []
    outdir = args[args.index("--outdir") + 1] if "--outdir" in args else None
    return [resolve_vm_path(a) for a in args[1:] if a.startswith("/") and a != outdir]


def save_failures(files: Mapping[str, str | None], row: Mapping[str, Any] | None) -> list[str]:
    """Why a candidate's GUI-faithful save cannot be trusted; empty when it can.

    ``files`` is the candidate (VM path -> local file, ``None`` for an absent
    file) and ``row`` the save stage's result for it. A candidate passes only
    if the stage ran without an infrastructure error and without an open or
    activation failure, every office file it places (``LO_SAVE_EXTENSIONS``)
    has at least one save event that wrote it and none that timed out, and
    every postconfig conversion of a placed file produced its output. A
    ``script_writer`` job (stage skipped by design) passes. Preregistration
    section 8: such a candidate is an infrastructure exclusion, never scored
    on its pre-save bytes.
    """
    if row is None:
        return ["no save-stage row"]
    if row.get("infra_error"):
        return [f"infra_error: {row['infra_error']}"[:200]]
    if (row.get("plan") or {}).get("skipped"):
        return []
    reasons = [str(failure) for failure in row.get("failures", [])]
    placed = {resolve_vm_path(p) for p, local in files.items() if local is not None}
    saves: dict[str, list[Mapping[str, Any]]] = {}
    for event in row.get("saves", []):
        saves.setdefault(resolve_vm_path(str(event.get("vm_path", ""))), []).append(event)
    for vm_path in sorted(placed):
        if posixpath.splitext(vm_path)[1].lower() not in LO_SAVE_EXTENSIONS:
            continue
        events = saves.get(vm_path, [])
        if not events:
            reasons.append(f"never saved: {vm_path}")
        elif not all(event.get("written") for event in events):
            reasons.append(f"save not written (timeout): {vm_path}")
    for event in row.get("events", []):
        if event.get("event") != "convert" or event.get("produced"):
            continue
        sources = [p for p in convert_inputs(event.get("argv", [])) if p in placed]
        if sources:
            reasons.append(f"conversion produced nothing: {', '.join(sources)}")
    return reasons


# Unemulated steps that cannot write a file a checker reads: closing or
# launching an application window, and keystrokes sent during setup (the agent's
# end state replaces what they act on). Everything else unemulated (typed text
# such as a file name in a save dialog, shell commands, scripts, package
# installs) is assumed to write and excludes the task (preregistration section 8).
NON_WRITING_STEPS = frozenset({"postconfig close_window", "postconfig launch"})


def step_may_write(text: str) -> bool:
    """Whether one unemulated setup or postconfig step may write a checker-read file."""
    stripped = text.strip()
    if stripped in NON_WRITING_STEPS:
        return False
    keystrokes = stripped.startswith(("python -c ", "python3 -c ")) and "pyautogui" in stripped
    return not (keystrokes and "pyautogui.write" not in stripped and "open(" not in stripped)


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
        "metric_side": [step.arg for step in steps if step.kind == "metric_side"],
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
            # The VM runs LibreOffice under GNOME with the gtk3 VCL plugin.
            "SAL_USE_VCLPLUGIN": os.environ.get("Q2M_VCL_PLUGIN", "gtk3"),
            # pyautogui is in the VM user's site-packages (~/.local), which the
            # postconfig's `python -c` sees because it runs as that user.
            "PYTHONUSERBASE": os.environ.get("Q2M_PYTHONUSERBASE", "/home/user/.local"),
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
        """Send keys through pyautogui (XTEST), as the VM's postconfig does."""
        keys = [key for key in combo.split("+") if key]
        call = (
            f"pyautogui.hotkey({keys!r}[0], *{keys!r}[1:])"
            if len(keys) > 1
            else (f"pyautogui.press({keys[0]!r})")
        )
        result = subprocess.run(
            ["python3", "-c", f"import pyautogui; {call}"],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self._event("key", combo=combo, returncode=result.returncode, stderr=result.stderr[-200:])

    def wait_written(
        self, path: Path, before: tuple[float, int] | None, timeout: float
    ) -> float | None:
        """Seconds until the file's (mtime, size) changed (then held stable for 0.3 s)."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if path.is_file():
                stat = path.stat()
                if before is None or (stat.st_mtime, stat.st_size) != before:
                    detected = time.monotonic() - start
                    time.sleep(0.3)
                    again = path.stat()
                    if (again.st_mtime, again.st_size) == (stat.st_mtime, stat.st_size):
                        # Time until the new file was first visible, not
                        # including the stability check.
                        return round(detected, 3)
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
        """Run a postconfig ``--convert-to`` as the VM does, then wait for its output.

        Any file the conversion would produce is removed first: in the real
        pipeline the agent never writes it, the postconfig derives it, so a
        stale candidate copy must not survive a conversion that silently fails.
        With a LibreOffice instance already running on the same profile the
        command hands the request to that instance and returns at once, so the
        output is awaited (up to 20 s) and its appearance time recorded.
        """
        outputs = derived_outputs(argv)
        removed = []
        for pattern_dir, stem, ext in outputs:
            directory = self.host_path(pattern_dir)
            for candidate in sorted(directory.glob(f"{stem}*.{ext}")) if directory.is_dir() else []:
                if candidate.name == f"{stem}.{ext}" or candidate.name.startswith(f"{stem}-"):
                    removed.append("/" + candidate.relative_to(self.vm_root).as_posix())
                    candidate.unlink()
        mapped = [self.soffice]
        for arg in argv[1:]:
            mapped.append(str(self.host_path(arg)) if arg.startswith("/") else arg)
        started = time.monotonic()
        result = subprocess.run(
            mapped, env=self.env, capture_output=True, text=True, timeout=timeout
        )
        returned = round(time.monotonic() - started, 3)
        produced: list[str] = []
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline and not produced:
            for pattern_dir, stem, ext in outputs:
                directory = self.host_path(pattern_dir)
                if directory.is_dir():
                    produced += [
                        "/" + c.relative_to(self.vm_root).as_posix()
                        for c in sorted(directory.glob(f"{stem}*.{ext}"))
                        if c.name == f"{stem}.{ext}" or c.name.startswith(f"{stem}-")
                    ]
            if not produced:
                time.sleep(0.1)
        if produced:
            time.sleep(0.5)  # let the writer finish before collection
        info = {
            "argv": list(argv),
            "returncode": result.returncode,
            "seconds_to_return": returned,
            "seconds_to_output": round(time.monotonic() - started, 3) if produced else None,
            "removed_before": removed,
            "produced": produced,
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
    """``soffice --version`` plus the libreoffice-core package version.

    Ubuntu's 0ubuntu0.22.04.4 and 0ubuntu0.22.04.13 both report
    "LibreOffice 7.3.7.2 30(Build:2)", so the version line alone does not
    identify the build.
    """
    out = subprocess.run([soffice, "--version"], capture_output=True, text=True, timeout=120)
    line = out.stdout.strip().splitlines()[0] if out.stdout.strip() else "unknown"
    deb = subprocess.run(
        ["dpkg-query", "-W", "-f", "${Version}", "libreoffice-core"],
        capture_output=True,
        text=True,
        check=False,
    )
    package = deb.stdout.strip() if deb.returncode == 0 and deb.stdout.strip() else "unknown"
    return f"{line}; libreoffice-core {package}"


def run_job(
    session: LoSession, job: Mapping[str, Any], raw_task: Mapping[str, Any], out_dir: Path
) -> dict[str, Any]:
    """Place files, open documents, replay postconfig, collect saved files."""
    if job.get("skip_reachability"):
        # script_writer stratum: bytes reach the checker as written, unsaved.
        return {
            "job_id": job["job_id"],
            "task_id": job["task_id"],
            "plan": {"skipped": "script_writer stratum"},
            "saves": [],
            "failures": [],
            "postconfig_target_absent": [],
            "outputs": {},
            "events": [],
        }
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
    target_absent: list[str] = []
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
                mapped = any(
                    window_title_for(p) == step.arg for p in plan["open_before_postconfig"]
                )
                ok = session.activate(step.arg, step.strict)
                if not ok and mapped:
                    failures.append(f"activate failed: {step.arg}")
                elif not ok:
                    # No candidate file has this window (do-nothing without the
                    # result file, or a window name the task never produces).
                    # In the VM wmctrl fails the same way and keys go to the
                    # focused window.
                    target_absent.append(step.arg)
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
    outputs: dict[str, str | None] = {}
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
    for vm_path, local in files.items():
        if local is not None and not session.host_path(vm_path).exists():
            outputs[vm_path] = None  # removed (a derived file the conversion did not remake)
    return {
        "job_id": job["job_id"],
        "task_id": job["task_id"],
        "plan": plan,
        "saves": [asdict(event) for event in saves],
        "failures": failures,
        "postconfig_target_absent": target_absent,
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
                    import traceback

                    result = {
                        "job_id": job["job_id"],
                        "task_id": job["task_id"],
                        "infra_error": repr(exc),
                        "traceback_tail": traceback.format_exc()[-1200:],
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
