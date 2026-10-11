"""Nuisance save stage: the checker-mutation study's GUI-faithful save under one cell.

Runs inside a LibreOffice container (the LO-VM image for build ``B0``, a derived image for
the TDF builds) with the system Python 3.10 and the standard library only. Every cell
reuses ``harness.q2_mutation.reachability`` unchanged: the same placement of the candidate
files at their VM paths, the same opening order, the same postconfig replay (window
activation, keys through the VM's pyautogui, sleeps, ``--convert-to`` with the task's own
filter string), the same save-event record and the same collection of changed files. A
cell changes only what its factor names:

* build: the ``soffice`` the session starts, and the profile's ``ooSetupLastVersion``;
* locale: ``LANG``/``LC_ALL`` of the LibreOffice and pyautogui processes (glibc data
  compiled at start-up from the image's own ``/usr/share/i18n`` sources into a
  ``LOCPATH`` under ``$TMPDIR``, offline) and the profile's ``ooSetupSystemLocale``, with
  ``ooLocale`` (the interface language) kept en-US;
* route ``store_as``: the instance is started with a UNO pipe and every save event that
  the registered stage makes with Ctrl+S is made by ``uno_store_as`` instead (``storeAsURL``
  on the document's own URL with the filter it was loaded with);
* route ``headless_convert``: no GUI instance; each office file is converted to its own
  format by ``soffice --headless --convert-to <ext>:<filter>`` into a scratch directory and
  copied back, then the task's own postconfig conversions run (headless as well).

The control cell (``B0.ctrl_s.L0``) is the registered stage itself: no profile override,
no environment override, ``reachability.run_job`` with an unmodified session.

Output per cell: ``<out>/<cell>/reachability-<worker>.jsonl`` (one row per job, the
registered row plus the cell, the build identity, what was set in the profile and the
environment) and the changed files under ``<out>/<cell>/files/<job_id>/``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import time
import traceback
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from harness.q2_mutation import reachability as R
from harness.r04_nuisance import levels, xcu

STORE_AS_SCRIPT = Path(__file__).with_name("uno_store_as.py")
# OSWorld's postconfig names windows "<file> - LibreOffice <App>"; newer LibreOffice builds
# title them "<file> \u2014 LibreOffice <App>" (an em dash).
TITLE_SEPARATOR = " - LibreOffice "
ADAPTED_SEPARATOR = " \u2014 LibreOffice "
# The OOXML and ODF filters of a same-format round trip (LibreOffice's filter names).
SAME_FORMAT_FILTERS = {
    ".xlsx": "Calc MS Excel 2007 XML",
    ".docx": "MS Word 2007 XML",
    ".pptx": "Impress MS PowerPoint 2007 XML",
    ".ods": "calc8",
    ".odt": "writer8",
    ".odp": "impress8",
}


class CellError(RuntimeError):
    """The cell cannot run in this container (wrong build, missing locale data)."""


# --- build and locale checks ---------------------------------------------------------


def build_identity(build: levels.Build) -> dict[str, Any]:
    """The soffice version line, and for the VM's build the Ubuntu package version."""
    if not Path(build.soffice).exists():
        raise CellError(f"{build.id}: {build.soffice} does not exist in this image")
    out = subprocess.run(
        [build.soffice, "--version"],
        capture_output=True,
        text=True,
        timeout=180,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/tmp/r04-version-home"},
    )
    line = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
    ident: dict[str, Any] = {"build": build.id, "label": build.label, "version_line": line}
    if f"LibreOffice {build.version}" not in line:
        raise CellError(f"{build.id}: soffice reports {line!r}, not {build.version}")
    ident["uno_python"] = build.uno_python if Path(build.uno_python).exists() else None
    if build.source == "lo-vm":
        ident["package"] = R.lo_version(build.soffice).split("; ", 1)[-1]
        if ident["package"] != "libreoffice-core 1:7.3.7-0ubuntu0.22.04.4":
            raise CellError(f"B0: {ident['package']} is not the VM's package")
    else:
        version_file = Path(build.install_dir or "") / "program" / "versionrc"
        ident["install_dir"] = build.install_dir
        if version_file.is_file():
            ident["versionrc_sha256"] = R.sha256_file(version_file)
    return ident


def compile_locale(posix: str, root: Path) -> dict[str, Any]:
    """Compile ``<posix>.UTF-8`` from the image's own locale sources into ``root``."""
    root.mkdir(parents=True, exist_ok=True)
    name = f"{posix}.UTF-8"
    target = root / name
    if not target.is_dir():
        res = subprocess.run(
            ["localedef", "-c", "-i", posix, "-f", "UTF-8", str(target)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if not target.is_dir():
            raise CellError(f"localedef {posix} failed: {res.stderr[-300:]}")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LOCPATH": str(root), "LC_ALL": name}
    probe = subprocess.run(
        ["locale", "-k", "decimal_point", "thousands_sep", "d_fmt"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    if probe.returncode != 0 or "Cannot set" in probe.stderr:
        raise CellError(f"locale {name} does not load: {probe.stderr[-300:]}")
    return {"locale": name, "locpath": str(root), "lc_numeric_time": probe.stdout.strip()}


# --- the session ------------------------------------------------------------------------


class NuisanceSession(R.LoSession):
    """``reachability.LoSession`` with one cell's build, profile, environment and route."""

    def __init__(
        self,
        display: R.Display,
        root: Path,
        cell: levels.Cell,
        profile_template: Path | None,
        *,
        pipe: str,
        locpath: str | None = None,
    ) -> None:
        build = levels.BUILD_BY_ID[cell.build]
        super().__init__(display, root, build.soffice, profile_template)
        self.cell = cell
        self.build = build
        self.overrides = levels.profile_overrides(cell)
        self.extra_env = levels.env_overrides(cell, locpath)
        self.pipe = pipe
        self.started = False
        self.profile_set: list[str] = []
        self.convert_count = 0
        self.activations_adapted: list[str] = []
        self.uno_python = build.uno_python

    def reset(self) -> None:
        super().reset()
        self.started = False
        self.convert_count = 0
        self.activations_adapted = []
        user = self.home / ".config" / "libreoffice" / "4" / "user"
        if self.overrides:
            if not (user / "registrymodifications.xcu").is_file():
                raise CellError("the cell sets profile properties but the profile has no xcu")
            self.profile_set = xcu.apply_to_profile(user, self.overrides)
        else:
            self.profile_set = []

    @property
    def env(self) -> dict[str, str]:
        env = self.display.env(self.home)
        env.update(self.extra_env)
        return env

    def activate(self, title: str, strict: bool) -> bool:
        """The registered activation; if it fails, the same title with the separator newer
        builds put in window titles ("file — LibreOffice Calc" for "file - LibreOffice
        Calc"). The VM's build never shows that title, so the control is unchanged; every
        adapted activation is recorded (a re-hosted VM would fail it as written)."""
        ok = super().activate(title, strict)
        if ok or TITLE_SEPARATOR not in title:
            return ok
        adapted = title.replace(TITLE_SEPARATOR, ADAPTED_SEPARATOR)
        ok = super().activate(adapted, strict)
        self._event("activate_adapted", title=title, adapted=adapted, ok=ok)
        if ok:
            self.activations_adapted.append(title)
        return ok

    # The first launch of a store_as job starts the instance with a UNO pipe; the rest is
    # LoSession.open line for line (wait for the document's window).
    def open(self, vm_path: str, timeout: float = 90.0) -> bool:
        if self.cell.route != "store_as" or self.started:
            ok = super().open(vm_path, timeout)
            self.started = self.started or ok
            return ok
        target = self.host_path(vm_path)
        proc = subprocess.Popen(
            [self.soffice, f"--accept=pipe,name={self.pipe};urp;", str(target)],
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.procs.append(proc)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for title in R.list_windows(self.env):
                if target.name in title or target.stem in title:
                    self._event("opened", vm_path=vm_path, title=title, uno_pipe=self.pipe)
                    time.sleep(1.0)
                    self.started = True
                    return True
            time.sleep(0.5)
        self._event("open_timeout", vm_path=vm_path, windows=R.list_windows(self.env))
        return False

    def save_with_ctrl_s(self, vm_path: str, reason: str, timeout: float = 30.0) -> R.SaveEvent:
        if self.cell.route != "store_as":
            return super().save_with_ctrl_s(vm_path, reason, timeout)
        target = self.host_path(vm_path)
        before_sha = R.sha256_file(target)
        before_stat = (target.stat().st_mtime, target.stat().st_size) if target.is_file() else None
        windows_before = set(R.list_windows(self.env))
        client = subprocess.run(
            [
                self.uno_python,
                str(STORE_AS_SCRIPT),
                "--pipe",
                self.pipe,
                "--path",
                str(target),
                "--timeout",
                str(timeout),
            ],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=timeout + 30,
        )
        try:
            reply = json.loads(client.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            reply = {"ok": False, "error": f"no reply: {client.stderr[-300:]}"}
        self._event("store_as", vm_path=vm_path, returncode=client.returncode, **reply)
        seconds = self.wait_written(target, before_stat, timeout) if reply.get("ok") else None
        dialogs = sorted(set(R.list_windows(self.env)) - windows_before)
        event = R.SaveEvent(
            vm_path=vm_path,
            reason=reason,
            before_sha256=before_sha,
            after_sha256=R.sha256_file(target),
            written=seconds is not None,
            seconds_to_write=seconds,
            dialogs=dialogs,
        )
        self._event("save", **asdict(event))
        return event

    def headless_round_trip(self, vm_path: str, timeout: float = 120.0) -> R.SaveEvent:
        """Convert one office file to its own format headless and copy it back."""
        target = self.host_path(vm_path)
        ext = target.suffix.lower()
        before_sha = R.sha256_file(target)
        self.convert_count += 1
        outdir = self.root / "round-trip" / str(self.convert_count)
        outdir.mkdir(parents=True, exist_ok=True)
        argv = [
            self.soffice,
            "--headless",
            "--norestore",
            "--convert-to",
            f"{ext[1:]}:{SAME_FORMAT_FILTERS[ext]}",
            "--outdir",
            str(outdir),
            str(target),
        ]
        started = time.monotonic()
        try:
            result = subprocess.run(
                argv, env=self.env, capture_output=True, text=True, timeout=timeout
            )
            returncode: int | None = result.returncode
        except subprocess.TimeoutExpired:
            returncode = None
        produced = outdir / target.name
        written = produced.is_file() and produced.stat().st_size > 0
        seconds = round(time.monotonic() - started, 3) if written else None
        if written:
            shutil.copyfile(produced, target)
        self._event(
            "headless_round_trip",
            vm_path=vm_path,
            returncode=returncode,
            produced=written,
            filter=SAME_FORMAT_FILTERS[ext],
        )
        event = R.SaveEvent(
            vm_path=vm_path,
            reason="headless_convert",
            before_sha256=before_sha,
            after_sha256=R.sha256_file(target),
            written=written,
            seconds_to_write=seconds,
            dialogs=[],
        )
        self._event("save", **asdict(event))
        return event


def run_job_headless(
    session: NuisanceSession, job: Mapping[str, Any], raw_task: Mapping[str, Any], out_dir: Path
) -> dict[str, Any]:
    """Route ``headless_convert``: ``reachability.run_job``'s placement, plan and collection,
    with every save made by a headless same-format round trip and the postconfig's
    conversions run headless (keys, window activation and sleeps have no GUI to act on)."""
    session.reset()
    session.log = []
    files: Mapping[str, str | None] = job["files"]
    for vm_path, local in files.items():
        if local is None:
            continue
        target = session.host_path(vm_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, target)
    before = {p: R.sha256_file(session.host_path(p)) for p in files}
    placed = [p for p, local in files.items() if local is not None]
    plan = R.build_plan(raw_task, placed)
    saves: list[R.SaveEvent] = []
    try:
        for vm_path in placed:
            if Path(vm_path).suffix.lower() in R.LO_SAVE_EXTENSIONS:
                saves.append(session.headless_round_trip(vm_path))
        for raw_step in plan["postconfig_steps"]:
            if raw_step["kind"] == "convert":
                session.convert(tuple(raw_step["argv"]))
    finally:
        session.close()
    return _collect(session, job, files, before, plan, saves, [], [], out_dir)


def _collect(
    session: NuisanceSession,
    job: Mapping[str, Any],
    files: Mapping[str, str | None],
    before: Mapping[str, str | None],
    plan: Mapping[str, Any],
    saves: list[R.SaveEvent],
    failures: list[str],
    target_absent: list[str],
    out_dir: Path,
) -> dict[str, Any]:
    """``reachability.run_job``'s output collection, unchanged."""
    outputs: dict[str, str | None] = {}
    job_out = out_dir / job["job_id"]
    if job_out.exists():
        shutil.rmtree(job_out)
    for host_file in sorted(session.vm_root.rglob("*")):
        if not host_file.is_file() or host_file.name.startswith(".~lock."):
            continue
        vm_path = "/" + host_file.relative_to(session.vm_root).as_posix()
        if vm_path in files and before.get(vm_path) == R.sha256_file(host_file):
            continue
        dest = job_out / vm_path.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(host_file, dest)
        outputs[vm_path] = str(dest)
    for vm_path, local in files.items():
        if local is not None and not session.host_path(vm_path).exists():
            outputs[vm_path] = None
    return {
        "job_id": job["job_id"],
        "task_id": job["task_id"],
        "plan": plan,
        "saves": [asdict(event) for event in saves],
        "failures": failures,
        "postconfig_target_absent": target_absent,
        "before_sha256": dict(before),
        "after_sha256": {p: R.sha256_file(session.host_path(p)) for p in files},
        "outputs": outputs,
        "events": session.log,
    }


def run_one(
    session: NuisanceSession, job: Mapping[str, Any], raw: Mapping[str, Any], out_dir: Path
) -> dict[str, Any]:
    if session.cell.route == "headless_convert":
        return run_job_headless(session, job, raw, out_dir)
    return R.run_job(session, job, raw, out_dir)


# --- CLI ----------------------------------------------------------------------------------


def load_task(osworld: Path, task_id: str) -> dict[str, Any]:
    examples = osworld / "evaluation_examples" / "examples"
    matches = list(examples.glob(f"*/{task_id}.json"))
    if len(matches) != 1:
        raise FileNotFoundError(f"task {task_id}: {len(matches)} config files")
    return json.loads(matches[0].read_text(encoding="utf-8"))


def run_cells(args: argparse.Namespace) -> dict[str, Any]:
    jobs = [json.loads(x) for x in args.jobs.read_text(encoding="utf-8").splitlines() if x.strip()]
    if args.only:
        wanted = set(args.only.read_text(encoding="utf-8").split())
        jobs = [job for job in jobs if job["job_id"] in wanted]
    mine = [job for index, job in enumerate(jobs) if index % args.workers == args.worker]
    work = Path(os.environ.get("TMPDIR", "/tmp")) / f"r04lo-{args.worker}"
    work.mkdir(parents=True, exist_ok=True)
    display = R.Display(100 + args.worker, work)
    display.start()
    summary: dict[str, Any] = {"worker": args.worker, "jobs": len(mine), "cells": {}}
    try:
        for cid in args.cells:
            cell = levels.get_cell(cid)
            build = levels.BUILD_BY_ID[cell.build]
            cell_out = args.out / cid
            cell_out.mkdir(parents=True, exist_ok=True)
            results = cell_out / f"reachability-{args.worker}.jsonl"
            cell_info: dict[str, Any] = {"cell": cell.as_dict()}
            try:
                cell_info["build_identity"] = build_identity(build)
                locpath = None
                if cell.locale != "L0":
                    loc = levels.LOCALE_BY_ID[cell.locale]
                    cell_info["locale_data"] = compile_locale(loc.posix, work / "locales")
                    locpath = cell_info["locale_data"]["locpath"]
                if cell.route == "store_as" and not cell_info["build_identity"]["uno_python"]:
                    raise CellError(f"{build.id}: no UNO client Python at {build.uno_python}")
            except CellError as exc:
                cell_info["cell_error"] = str(exc)
                locpath = None
            session = NuisanceSession(
                display,
                work / "session",
                cell,
                args.profile_template,
                pipe=f"r04w{args.worker}",
                locpath=locpath,
            )
            with results.open("w", encoding="utf-8") as handle:
                for job in mine:
                    started = time.monotonic()
                    if "cell_error" in cell_info:
                        row: dict[str, Any] = {
                            "job_id": job["job_id"],
                            "task_id": job["task_id"],
                            "infra_error": f"cell_error: {cell_info['cell_error']}",
                        }
                    else:
                        try:
                            raw = load_task(args.osworld, job["task_id"])
                            row = run_one(session, job, raw, cell_out / "files")
                        except Exception as exc:  # noqa: BLE001 - an infrastructure failure
                            with contextlib.suppress(Exception):
                                session.close()
                            row = {
                                "job_id": job["job_id"],
                                "task_id": job["task_id"],
                                "infra_error": repr(exc),
                                "traceback_tail": traceback.format_exc()[-1200:],
                            }
                    row["cell"] = cid
                    row["lo_build"] = (cell_info.get("build_identity") or {}).get("version_line")
                    row["profile_set"] = list(session.profile_set)
                    row["activations_adapted"] = list(session.activations_adapted)
                    row["env_set"] = dict(session.extra_env)
                    row["seconds"] = round(time.monotonic() - started, 3)
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                    handle.flush()
            (cell_out / f"cell-{args.worker}.json").write_text(
                json.dumps(cell_info, indent=1, sort_keys=True), encoding="utf-8"
            )
            summary["cells"][cid] = {k: v for k, v in cell_info.items() if k != "cell"}
    finally:
        display.stop()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=Path, required=True, help="items JSONL (job form)")
    parser.add_argument("--cells", nargs="+", required=True)
    parser.add_argument("--osworld", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile-template", type=Path, default=None)
    parser.add_argument("--only", type=Path, default=None, help="file of job ids to run")
    parser.add_argument("--worker", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    for cid in args.cells:
        levels.get_cell(cid)
    summary = run_cells(args)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
