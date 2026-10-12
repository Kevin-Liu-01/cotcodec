"""The S2 v4 VM probe: one task's post-setup state in one cell image, in a real VM.

Registration ``s2-arabic-cua-locale-v4``: the development smoke of the derived images (section
"Development smoke") and the capture step that Phase 0 proper (P0.7, P0.11) reuses. One process
per slot, inside the GPU-less episode container (the checker-mutation study's metric image,
OSWorld's locked environment) that the S2 VM lane (``vm_lane.py``) starts in a freshly booted VM
container's ``--network none`` namespace, exactly as the S1a and K2 lanes start an episode; the
VM container mounts the slot's cell image (the certified disk for the stock cell S):

1. wait for the cold boot (``driver.Runner.wait_for_boot``, S1a's);
2. image check: the guest's selector file must have the cell's SHA-256 (none in S), so a record
   always names the image it ran on (``guest/s2_guest.py`` ``facts``);
3. ``reset_task``: the task's own setup, offline from the pinned file cache
   (``osworld_live.LiveTask.setup``, S1a's unmodified call of the pinned code);
4. the guard's keyboard warm-up; the pointer warp (``warp_pointer``: one absolute XTest motion
   to ``POINTER_TARGET``, read back; P0.7); OSWorld's 60 s settle (S1a section 7.1 step 4);
5. the post-setup observation: two screenshots 1 s apart (kept on the host, never committed),
   the accessibility tree (kept on the host; its summary is recorded: named showing nodes, the
   share in Arabic script, the menu bar's left-to-right order), the window titles, the keyboard
   map and input methods;
6. (``evaluate``) S1a's 20 s settle, then the pinned ``DesktopEnv.evaluate()`` with ``DONE``:
   the task's own postconfig (strict window activation, Ctrl+S, ...) and its checker on the
   do-nothing state; the guest-server restart check; P0.10's reader (the values the C1
   checkers read from the user profile's ``registrymodifications.xcu``, ``P010_KEYS``); a last
   screenshot and the end facts (fonts, the unmet package dependencies).

Classification (registration, "Infrastructure failures and exclusions"): a failed boot, image
check, setup step, warm-up, pointer warp or guest transport, an undelivered observation, a
guest-server restart, or a postconfig server error (any ``/setup/*`` reply of the postconfig with
no HTTP status or a status of 500 or above: the guest server's own failure; a non-zero
``returncode`` under HTTP 200 is the guest's state and is scored) ends the slot as
``infrastructure``, and the lane re-queues it once; otherwise the slot is ``probed`` with whatever
the observation and the checker returned (a metric that raises is recorded as ``error``, never an
exclusion).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import time
import traceback
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "s2v4-vm-probe-v1"
EXPERIMENT_ID = "s2-arabic-cua-locale-v4"
SELECTOR_PATH = "/etc/libreoffice/registry/zz-s2v4-cell.xcd"
GUEST_SCRIPT = Path(__file__).resolve().parent / "guest" / "s2_guest.py"
ARABIC = re.compile("[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
LATIN = re.compile("[A-Za-z]")
CP = "https://accessibility.ubuntu.example.org/ns/component"
ST = "https://accessibility.ubuntu.example.org/ns/state"
COORD = re.compile(r"\((-?\d+),\s*(-?\d+)\)")
SERVER_ERROR = 500  # harness.q2_stage1.osworld_live.SERVER_ERROR
REGISTRY_XCU = "/home/user/.config/libreoffice/4/user/registrymodifications.xcu"
# P0.10: the (item path, prop name) pairs each C1 checker reads (OSWorld b138d348:
# slides.check_presenter_console_disable, slides.check_auto_saving_time, docs.find_default_font).
P010_KEYS: dict[str, tuple[tuple[str, str], ...]] = {
    "0f84bef9": (("/org.openoffice.Office.Impress/Misc/Start", "EnablePresenterScreen"),),
    "2cd43775": (("/org.openoffice.Office.Common/Save/Document", "AutoSaveTimeIntervall"),),
    "f178a4a9": (("/org.openoffice.Office.Writer/DefaultFont", "Standard"),),
}
# Every other task reads all three (the reader is exercised on every slot, dev tasks included).
P010_ALL = tuple(k for keys in P010_KEYS.values() for k in keys)
# P0.7 and Phase 1: the screen point the pointer is warped to once per boot, after the warm-up and
# before the 60 s settle. Chosen on smoke 1214's dev renders: inside the document region of Calc,
# Writer and Impress in every cell (Impress's slide editing window spans about x 275-1510 and
# y 250-1045 left to right, x 480-1720 mirrored; Calc's grid x 82-1820, y 281-997; Writer's
# document x 70-1849, y 246-1034); on the LibreOffice window's mirror axis (the window spans
# x 70-1919, and the mirrored layout puts at x what the left-to-right one has at 1989 - x, so the
# point and its mirror image are 1 px apart and the pointer rests over the same document element
# in both directions); and away from the point where the boot leaves the pointer (1732, 978) in
# all 177 capture renders of smoke 1214 (the guest server draws the cursor into every screenshot
# at the pointer), so the warp always moves it.
POINTER_TARGET = (995, 540)


def p010_keys(task_id: str) -> tuple[tuple[str, str], ...]:
    return P010_KEYS.get(task_id[:8], P010_ALL)


def server_error(reply: Mapping[str, Any]) -> bool:
    """A ``/setup/*`` reply the guest server itself failed: no HTTP status, or 500 or above
    (the reading of ``harness.q2_stage1.analysis.server_error``)."""
    status = reply.get("status")
    return not isinstance(status, int) or isinstance(status, bool) or status >= SERVER_ERROR


class ProbeFailure(RuntimeError):
    def __init__(self, step: str, detail: str):
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail


def warp_pointer(guest: Any, target: tuple[int, int] = POINTER_TARGET) -> dict[str, Any]:
    """P0.7's pointer warp (also Phase 1's at every episode start): the guest helper's ``pointer``
    mode moves the pointer to ``target`` in one absolute XTest motion and reads it back. A guest
    that cannot do it, or a pointer read back elsewhere, is an infrastructure loss."""
    try:
        out = guest.run_script(GUEST_SCRIPT.read_text(encoding="utf-8"),
                               ["pointer", json.dumps({"x": target[0], "y": target[1]})])
    except Exception as exc:  # noqa: BLE001 - a guest that cannot answer is infrastructure
        raise ProbeFailure("pointer", f"{type(exc).__name__}: {exc}") from exc
    out.pop("_elapsed_s", None)
    if out.get("after") != list(target):
        raise ProbeFailure("pointer", f"the pointer reads {out.get('after')}, not {list(target)}")
    out["moved"] = out.get("before") != out.get("after")
    return out


@dataclass
class ProbeConfig:
    lane: str
    purpose: str
    slot: str
    task_id: str
    cell: str
    block: str
    attempt: int
    image_sha256: str
    selector_sha256: str | None
    out_dir: str = "/out"
    guest_ip: str = "20.20.20.21"
    server_port: int = 5000
    osworld_dir: str = "/inputs/OSWorld"
    file_cache_dir: str = "/inputs/file_cache/files"
    settle_after_reset_s: float = 60.0
    settle_before_eval_s: float = 20.0
    boot_timeout_s: float = 300.0
    evaluate: bool = True
    t_vm_start: float | None = None

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> ProbeConfig:
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        unknown = sorted(set(data) - set(known))
        if unknown:
            raise ValueError(f"unknown probe config keys: {unknown}")
        return cls(**known)


# --------------------------------------------------------------------------- summaries


def _coord(value: str | None) -> tuple[int, int] | None:
    m = COORD.match(value or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


DOCUMENT_ROLES = ("document-spreadsheet", "document-text", "document-presentation",
                  "document-frame", "document-web")
NOT_CHROME = ("application", "frame", "window")


def a11y_summary(xml_text: str, screen_width: int = 1920) -> dict[str, Any]:
    """Interface strings of LibreOffice's application subtree and the menu bar's order.

    Counted: showing nodes with a name, outside any document subtree (the document's own
    English content is held fixed and is not chrome) and other than the application and its
    window frames (whose names are titles). ``arabic_share`` is the share in Arabic script among
    names with Arabic or Latin letters (P0.13's quantity on the accessibility tree)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return {"parse_error": str(exc)[:200]}
    apps = [el for el in root.iter() if el.tag == "application"
            and re.search(r"soffice|libreoffice", el.get("name", ""), re.I)]  # fmt: skip
    scope = apps or [root]
    counts = {"named": 0, "arabic": 0, "latin": 0}

    def walk(el: ET.Element, in_doc: bool) -> None:
        in_doc = in_doc or el.tag in DOCUMENT_ROLES
        name = (el.get("name") or "").strip()
        if (name and not in_doc and el.tag not in NOT_CHROME
                and el.get(f"{{{ST}}}showing") == "true"):  # fmt: skip
            counts["named"] += 1
            if ARABIC.search(name):
                counts["arabic"] += 1
            elif LATIN.search(name):
                counts["latin"] += 1
        for child in el:
            walk(child, in_doc)

    menubar: list[dict[str, Any]] = []
    for app in scope:
        walk(app, False)
        for bar in app.iter("menu-bar"):
            if bar.get(f"{{{ST}}}showing") != "true" or menubar:
                continue
            for child in bar:
                xy = _coord(child.get(f"{{{CP}}}screencoord"))
                size = _coord(child.get(f"{{{CP}}}size"))
                if xy and size and size[0] > 0:
                    menubar.append({"name": child.get("name"), "x": xy[0], "w": size[0]})
    order = None
    if len(menubar) >= 2:
        order = "ltr" if menubar[0]["x"] < menubar[-1]["x"] else "rtl"
    first_right = None
    if menubar:
        first_right = menubar[0]["x"] + menubar[0]["w"] / 2 > screen_width / 2
    ar, la = counts["arabic"], counts["latin"]
    return {
        "applications": len(apps),
        "named_showing": counts["named"],
        "arabic_script": ar,
        "latin_script": la,
        "arabic_share": round(ar / (ar + la), 4) if ar + la else None,
        "menubar_items": len(menubar),
        "menubar_first": menubar[0]["name"] if menubar else None,
        "menubar_order": order,
        "menubar_first_on_right": first_right,
    }


def result_paths(task: Mapping[str, Any]) -> list[str]:
    """The VM files the task's checker reads (``vm_file`` result getters), absolute."""
    import posixpath

    results = (task.get("evaluator") or {}).get("result")
    configs = results if isinstance(results, list) else [results]
    out: list[str] = []
    for cfg in configs:
        if not isinstance(cfg, Mapping) or cfg.get("type") != "vm_file":
            continue
        paths = cfg.get("path")
        for path in paths if isinstance(paths, list) else [paths]:
            if not isinstance(path, str):
                continue
            text = path.replace("${HOME}", "/home/user").replace("$HOME", "/home/user")
            if text == "~" or text.startswith("~/"):
                text = "/home/user" + text[1:]
            if not text.startswith("/"):
                text = posixpath.join("/home/user", text)
            out.append(posixpath.normpath(text))
    return sorted(set(out))


def rewritten(pre: Mapping[str, Any], post: Mapping[str, Any]) -> bool:
    """Whether the postconfig wrote the file: it exists after and its bytes or mtime moved."""
    if not post.get("exists"):
        return False
    return (not pre.get("exists") or pre.get("sha256") != post.get("sha256")
            or pre.get("mtime_ns") != post.get("mtime_ns"))  # fmt: skip


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- probe


class Probe:
    def __init__(self, cfg: ProbeConfig, *, guest: Any, task: Mapping[str, Any],
                 session_factory: Callable[[ProbeConfig, Mapping[str, Any]], Any],
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.time,
                 gpu_glob: Callable[[], list[str]] | None = None):  # fmt: skip
        self.cfg = cfg
        self.guest = guest
        self.task = dict(task)
        self.session_factory = session_factory
        self.sleep = sleep
        self.clock = clock
        self.gpu_glob = gpu_glob
        self.out = Path(cfg.out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.timings: dict[str, float] = {}
        self.record: dict[str, Any] = {
            "schema": SCHEMA, "experiment_id": EXPERIMENT_ID, "lane": cfg.lane,
            "purpose": cfg.purpose, "slot": cfg.slot, "task_id": cfg.task_id, "cell": cfg.cell,
            "block": cfg.block, "attempt": cfg.attempt, "image_sha256": cfg.image_sha256,
            "status": "infrastructure", "infrastructure_type": "runner_crash", "score": None,
        }  # fmt: skip
        self._runner = self._make_runner()

    def _make_runner(self) -> Any:
        from harness.q2_stage1 import driver

        runner = driver.Runner.__new__(driver.Runner)
        runner.cfg = self.cfg
        runner.guest = self.guest
        runner.sleep = self.sleep
        runner.clock = self.clock
        runner.timings = self.timings
        runner.record = self.record
        runner.session = None
        runner.out = self.out
        return runner

    def progress(self, event: str, **data: Any) -> None:
        line = {"s2v4": event, "slot": self.cfg.slot, "t": round(self.clock(), 3), **data}
        print(json.dumps(line, sort_keys=True), flush=True)

    def facts(self, tag: str) -> dict[str, Any]:
        try:
            args = ["facts", json.dumps({"selector": SELECTOR_PATH})]
            out = self.guest.run_script(GUEST_SCRIPT.read_text(encoding="utf-8"), args)
        except Exception as exc:  # noqa: BLE001 - a guest that cannot answer is infrastructure
            raise ProbeFailure(f"facts {tag}", f"{type(exc).__name__}: {exc}") from exc
        out.pop("_elapsed_s", None)
        return out

    def hash_files(self, tag: str, paths: list[str]) -> dict[str, dict[str, Any]]:
        if not paths:
            return {}
        try:
            out = self.guest.run_script(GUEST_SCRIPT.read_text(encoding="utf-8"),
                                        ["hash", json.dumps({"paths": paths})])  # fmt: skip
        except Exception as exc:  # noqa: BLE001 - a guest that cannot answer is infrastructure
            raise ProbeFailure(f"hash {tag}", f"{type(exc).__name__}: {exc}") from exc
        return {row["path"]: row for row in out.get("files", [])}

    def guest_mode(self, mode: str, tag: str, config: Mapping[str, Any]) -> dict[str, Any]:
        try:
            out = self.guest.run_script(GUEST_SCRIPT.read_text(encoding="utf-8"),
                                        [mode, json.dumps(config)])  # fmt: skip
        except Exception as exc:  # noqa: BLE001 - a guest that cannot answer is infrastructure
            raise ProbeFailure(f"{mode} {tag}", f"{type(exc).__name__}: {exc}") from exc
        out.pop("_elapsed_s", None)
        return out

    def screenshot(self, tag: str) -> dict[str, Any]:
        from harness.q2.vm import desktop

        shot, attempts = desktop.get_screenshot(self.guest)
        if shot is None:
            raise ProbeFailure(f"screenshot {tag}", f"undelivered: {attempts[-1:]}")
        path = self.out / "screens" / f"{tag}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(shot)
        return {"sha256": sha256_bytes(shot), "bytes": len(shot), "attempts": len(attempts)}

    def accessibility(self, tag: str) -> dict[str, Any]:
        from harness.q2.vm import desktop

        tree, attempts = desktop.get_accessibility_tree(self.guest)
        if tree is None:
            # D53 (iii): an undelivered observation is infrastructure.
            raise ProbeFailure(f"accessibility {tag}", f"undelivered: {attempts[-1:]}")
        path = self.out / "a11y" / f"{tag}.xml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tree, encoding="utf-8")
        return {"sha256": sha256_bytes(tree.encode("utf-8")), "summary": a11y_summary(tree),
                "attempts": len(attempts)}  # fmt: skip

    def check_no_gpu(self) -> None:
        import glob

        devices = sorted(self.gpu_glob() if self.gpu_glob else glob.glob("/dev/nvidia*"))
        self.record["gpu_devices"] = devices
        if devices:
            raise ProbeFailure("gpu", f"D12: GPU device files visible: {devices}")

    def run(self) -> dict[str, Any]:
        t0 = self.clock()
        self.record["t_start"] = t0
        session = None
        try:
            self.check_no_gpu()
            self.progress("boot_wait")
            self._runner.wait_for_boot()
            boot = self.facts("boot")
            self.record["facts_boot"] = boot
            if boot.get("selector_sha256") != self.cfg.selector_sha256:
                seen, want = boot.get("selector_sha256"), self.cfg.selector_sha256
                raise ProbeFailure("image_check", f"selector {seen} is not the cell's {want}")
            self.progress("reset_task")
            t = self.clock()
            try:
                session = self.session_factory(self.cfg, self.task)
                self._runner.session = session
                setup = session.setup()
            except Exception as exc:  # noqa: BLE001 - any setup failure is a reset failure
                raise ProbeFailure("reset_task", f"{type(exc).__name__}: {exc}") from exc
            from harness.q2_stage1.driver import for_record

            self.record["setup"] = for_record(setup)
            self.timings["setup_s"] = round(self.clock() - t, 3)
            if (setup or {}).get("failures"):
                raise ProbeFailure("reset_task", f"failed in the guest: {setup['failures'][0]}")
            self.progress("warm_up")
            self._runner.warm_up()
            self.progress("pointer")
            self.record["pointer"] = warp_pointer(self.guest)
            t = self.clock()
            self.sleep(self.cfg.settle_after_reset_s)
            self.timings["settle_after_reset_s"] = round(self.clock() - t, 3)
            self.progress("observe")
            obs: dict[str, Any] = {"shot_1": self.screenshot("post_setup-1")}
            self.sleep(1.0)
            obs["shot_2"] = self.screenshot("post_setup-2")
            obs["stable"] = obs["shot_1"]["sha256"] == obs["shot_2"]["sha256"]
            obs["a11y"] = self.accessibility("post_setup")
            obs["facts"] = self.facts("post_setup")
            self.record["post_setup"] = obs
            if self.cfg.evaluate:
                t = self.clock()
                self.sleep(self.cfg.settle_before_eval_s)
                self.timings["settle_before_eval_s"] = round(self.clock() - t, 3)
                paths = result_paths(self.task)
                pre = self.hash_files("pre_postconfig", paths)
                self.progress("evaluate")
                self.evaluate(session)
                failed = [r for r in self.record["postconfig"]["replies"] if server_error(r)]
                if failed:
                    from harness.q2_stage1.osworld_live import describe_reply

                    raise ProbeFailure("postconfig_server_error",
                                       "; ".join(describe_reply(r) for r in failed))  # fmt: skip
                self._runner.check_restarts("server_end")
                post = self.hash_files("post_evaluate", paths)
                self.record["result_files"] = {
                    p: {"pre": pre.get(p), "post": post.get(p),
                        "rewritten": rewritten(pre.get(p) or {}, post.get(p) or {})}
                    for p in paths}  # fmt: skip
                keys = p010_keys(self.cfg.task_id)
                self.record["p010"] = {
                    "keys": [list(k) for k in keys],
                    **self.guest_mode("registry", "post_evaluate",
                                      {"path": REGISTRY_XCU, "keys": [list(k) for k in keys]}),
                }  # fmt: skip
                self.record["post_evaluate"] = {"shot": self.screenshot("post_evaluate"),
                                                "facts": self.facts("post_evaluate")}  # fmt: skip
            self.record["end_facts"] = self.guest_mode("end", "end", {})
            self.record.update(status="probed", infrastructure_type=None)
        except ProbeFailure as exc:
            self.record.update(status="infrastructure", infrastructure_type=f"probe:{exc.step}",
                               infrastructure_detail=exc.detail[:500])  # fmt: skip
        except Exception as exc:  # noqa: BLE001 - S1a's InfraLoss and any crash
            kind = getattr(exc, "kind", None)
            if kind is not None:
                kind = self._runner.restart_behind(exc)
            detail = str(getattr(exc, "detail", exc))[:500]
            self.record.update(status="infrastructure", infrastructure_type=kind or "runner_crash",
                               infrastructure_detail=detail)
            if kind is None:
                self.record["traceback_tail"] = traceback.format_exc()[-1500:]
        finally:
            if session is not None:
                with contextlib.suppress(Exception):
                    session.close()
        return self.finish(t0)

    def evaluate(self, session: Any) -> None:
        from harness.q2_stage1.driver import strip_stdout
        from harness.q2_stage1.osworld_live import describe_reply, setup_reply_failed

        t = self.clock()
        try:
            score = session.evaluate("DONE")
            self.record["score"] = float(score)
            self.record["verdict"] = "pass" if float(score) >= 1.0 else "fail"
        except Exception as exc:  # noqa: BLE001 - transport and observation losses re-raise
            from harness.q2_stage1.osworld_live import is_observation_failure, is_transport_error

            if is_transport_error(exc) or is_observation_failure(exc):
                raise
            self.record["score"] = None
            self.record["verdict"] = "error"
            self.record["metric_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        replies = list(getattr(session, "evaluate_replies", []) or [])
        self.record["postconfig"] = {
            "replies": strip_stdout(replies),
            "failures": [describe_reply(r) for r in replies if setup_reply_failed(r)],
        }
        self.timings["evaluate_s"] = round(self.clock() - t, 3)

    def finish(self, t0: float) -> dict[str, Any]:
        self.progress("end", status=self.record.get("status"),
                      type=self.record.get("infrastructure_type"))  # fmt: skip
        self.record["t_end"] = self.clock()
        self.timings["run_s"] = round(self.record["t_end"] - t0, 3)
        self.record["timings"] = self.timings
        (self.out / "probe.json").write_text(json.dumps(self.record, indent=1, sort_keys=True),
                                             encoding="utf-8")  # fmt: skip
        return self.record


def run_from_config(config_path: Path) -> dict[str, Any]:
    from harness.q2.vm.guest_http import GuestClient
    from harness.q2_stage1.osworld_live import LiveTask, load_task

    cfg = ProbeConfig.from_json(json.loads(config_path.read_text(encoding="utf-8")))
    task = load_task(cfg.osworld_dir, cfg.task_id)

    def session_factory(c: ProbeConfig, t: Mapping[str, Any]) -> LiveTask:
        return LiveTask(t, osworld_dir=c.osworld_dir, file_cache=Path(c.file_cache_dir),
                        guest_ip=c.guest_ip, server_port=c.server_port,
                        cache_root=Path("/tmp/osworld-cache"))  # fmt: skip

    probe = Probe(cfg, guest=GuestClient(cfg.guest_ip, cfg.server_port), task=task,
                  session_factory=session_factory)  # fmt: skip
    return probe.run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    record = run_from_config(args.config)
    print(json.dumps({k: record.get(k) for k in ("slot", "cell", "status", "infrastructure_type",
                                                 "score")}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
