"""S2 v5 (D96): A6's Writer targets per image in ap_delta's v5 path (no Docker, no VM)."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from harness.s2_locale import ap_delta as D
from harness.s2_locale import ap_delta_v5 as V
from harness.s2_locale import vm_lane as L

ROOT = Path(__file__).resolve().parents[1]
STEP0 = json.loads((ROOT / V.STEP0_RESULT).read_text())


def _chain(lines: list[str], extra: dict) -> list[str]:
    previous = json.loads(lines[-1])["hash"]
    body = dict(extra, previous_hash=previous)
    body["hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return [*lines, json.dumps(body, sort_keys=True)]


def _source(tmp_path: Path, *, v4_frozen: bool = True, prereg: bool = False) -> Path:
    """The tree as an export has it: the harness and the ledger (v4 frozen, v5 not); with
    ``prereg`` every registration file too (harness/q2's ledger check reads them)."""
    src = tmp_path / "src"
    shutil.copytree(ROOT / "harness", src / "harness",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))  # fmt: skip
    if prereg:
        from harness.q2.vm.manifest import ledger_view

        shutil.copytree(ROOT / "program/preregistrations", src / "program/preregistrations")
        q2 = ("q2-action-path-v2", "q2-action-path-v2-inputs", "q2-action-path-v2-executor")
        view = ledger_view(str(ROOT), [f"program/preregistrations/{n}.md" for n in q2])
        for table in view["tables"].values():  # every file q2's frozen tables pin
            for rel in table:
                (src / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, src / rel)
    else:
        (src / "program/preregistrations").mkdir(parents=True)
    lines = []
    for line in (ROOT / L.LEDGER).read_text().splitlines():
        if not v4_frozen and line.strip() and json.loads(line)["experiment_id"] == V.V4_ID:
            break
        if line.strip() and json.loads(line)["experiment_id"] == V.EXPERIMENT_ID:
            break
        lines.append(line)
    (src / L.LEDGER).write_text("\n".join(lines) + "\n")
    return src


def _freeze_v5(src: Path, sha: str = "b" * 40, head: str = "a" * 40) -> dict:
    """A scratch freeze of a stand-in v5 registration in ``src``'s own ledger (the chain kept);
    the export's ``.git_sha`` is the freeze commit."""
    reg = src / V.REGISTRATION
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text("# S2 v5 frozen stand-in\n")
    lines = (src / L.LEDGER).read_text().splitlines()
    lines = _chain(
        lines,
        {
            "experiment_id": V.EXPERIMENT_ID,
            "frozen_at": "2026-10-14T00:00:00Z",
            "git_head_at_freeze": head,
            "path": V.REGISTRATION,
            "sha256": hashlib.sha256(reg.read_bytes()).hexdigest(),
        },
    )
    (src / L.LEDGER).write_text("\n".join(lines) + "\n")
    (src / ".git_sha").write_text(sha + "\n")
    return json.loads(lines[-1])


def _args(src: Path) -> argparse.Namespace:
    return argparse.Namespace(
        source_dir=src, git_sha="f" * 40, host_root=V.CONFIRM_ROOT, images_root=V.IMAGES_ROOT
    )


# --------------------------------------------------------------------------- the targets


def test_writer_targets_are_d96s_numbers_and_step0s_medians():
    assert hashlib.sha256((ROOT / V.STEP0_RESULT).read_bytes()).hexdigest() == (
        V.STEP0_RESULT_SHA256
    )
    assert STEP0["reading"] == "(a)" and STEP0["exit_labels"] == []
    er, ar = V.WRITER_TARGETS["ER"], V.WRITER_TARGETS["AR"]
    assert er["drag_select_word"] == {"duration_ms": 500, "from": [751, 293], "to": [779, 293]}
    assert er["triple_click_line"] == {"x": 789, "y": 293}
    assert ar["drag_select_word"] == {"duration_ms": 500, "from": [751, 294], "to": [779, 294]}
    assert ar["triple_click_line"] == {"x": 789, "y": 294}
    q2 = json.loads((ROOT / V.Q2_TARGETS).read_text())["apps"]
    for cell in V.K1_CELLS:
        assert V.targets(ROOT, cell) == STEP0["v5_targets"][cell], cell
        for app in ("chrome", "vscode"):
            assert V.targets(ROOT, cell)[app] == q2[app]
        if cell not in ("ER", "AR"):
            assert V.targets(ROOT, cell)["writer"] == q2["writer"]


def test_cells_files_are_q2s_with_only_writers_targets_replaced():
    q2 = json.loads((ROOT / V.Q2_CELLS).read_text())
    assert V.check_cells_files(ROOT) == V.CELLS_SHA256
    assert set(V.CELLS_FILES) == {"ER", "AR"}
    for cell, rel in V.CELLS_FILES.items():
        assert rel.startswith("harness/") and not rel.startswith("harness/q2/")  # /src/harness
        data = json.loads((ROOT / rel).read_text())
        assert data["canary"]["apps"]["writer"]["targets"] == V.WRITER_TARGETS[cell]
        data["canary"]["apps"]["writer"]["targets"] = q2["canary"]["apps"]["writer"]["targets"]
        assert data == q2, cell
        assert (ROOT / rel).read_bytes() == V.render_cells(ROOT, cell)


def test_a_changed_cells_file_is_refused(tmp_path):
    src = _source(tmp_path)
    path = src / V.CELLS_FILES["AR"]
    path.write_bytes(path.read_bytes().replace(b"789", b"790", 1))
    with pytest.raises(V.V5Error, match="pinned v5 cells file"):
        V.check_cells_files(src)


def test_only_canary_campaigns_on_er_and_ar_read_a_v5_cells_file():
    for kind in V.CANARY_KINDS:
        assert V.cells_file("ER", kind) == V.CELLS_FILES["ER"]
        assert V.cells_file("AR", kind) == V.CELLS_FILES["AR"]
        for cell in ("E", "A", "PL"):
            assert V.cells_file(cell, kind) is None
    for kind in ("suite-acceptance", "boot-reset-validation", None):
        assert V.cells_file("ER", kind) is None


# --------------------------------------------------------------------------- the override


def _fake_run(q2m: dict):
    def run(argv, timeout=120.0, check=True):
        if argv[1] == "info":
            out = json.dumps({"ServerVersion": "28", "DefaultRuntime": "runc"})
        elif argv[1:3] == ["image", "inspect"] and argv[-1] == q2m["vm"]["image_id"]:
            out = f'{q2m["vm"]["image_id"]} ["{q2m["vm"]["image"]}"]'
        elif argv[1:3] == ["image", "inspect"]:
            out = q2m["runner"]["image_id"]
        elif argv[1] == "run":
            out = json.dumps({"format": "qcow2", "virtual-size": 53687091200})
        else:
            out = ""
        return type("P", (), {"stdout": out, "stderr": "", "returncode": 0})()

    return run


def _stub_driver(monkeypatch, q2m: dict, seen: list) -> None:
    """harness/q2's driver with Docker, the disk and the host stubbed; ``run_cycle`` is the real
    one (it writes each session's runner config)."""
    from harness.q2.vm import driver

    st = type("St", (), {"st_size": q2m["vm"]["qcow2"]["size_bytes"], "st_mode": 0o100444})()
    fake_os = type("Os", (), {"stat": staticmethod(lambda p, follow_symlinks=False: st),
                              "path": type("P", (), {"isfile": staticmethod(lambda p: True),
                                                     "islink": staticmethod(lambda p: False)}),
                              "getuid": staticmethod(lambda: 1000),
                              "getgid": staticmethod(lambda: 1000)})  # fmt: skip
    monkeypatch.setattr(driver, "os", fake_os)
    monkeypatch.setattr(driver, "run", _fake_run(q2m))
    monkeypatch.setattr(driver, "sha256_file", lambda p: q2m["vm"]["qcow2"]["sha256"])
    monkeypatch.setattr(driver, "slurm_cpu_ids", lambda j: list(range(8)))
    monkeypatch.setattr(driver, "numa_nodes", lambda: {0: set(range(8))})
    monkeypatch.setattr(
        driver, "plan_cpusets", lambda m, a, n: {"vm": "0-3", "vm_mems": "0", "runner": "4"}
    )
    monkeypatch.setattr(driver, "snapshot_host", lambda j: {"t": 0})
    monkeypatch.setattr(driver, "inspect_container", lambda name: {})
    monkeypatch.setattr(driver, "vm_measurements", lambda name: {})
    monkeypatch.setattr(driver, "remove_container", lambda name: {"removed": True})
    monkeypatch.setattr(driver, "cycle_verdict", lambda r, t: {"cycle": r["cycle"]})
    monkeypatch.setattr(
        driver,
        "summarize",
        lambda v, r: {
            "boots_ok": len(r),
            "cycles": len(r),
            "sentinel_pristine": 0,
            "sentinel_reset_checks": 0,
            "sentinel_readback_file": len(r),
            "no_gpu_all": True,
            "no_published_ports_all": True,
            "containers_removed_all": True,
            "leaked_volumes": [],
        },
    )
    monkeypatch.setattr(driver, "session_summary", lambda r: {"runner_errors": []})
    inner = driver.run_cycle

    def run_cycle(*a, **k):
        seen.append(driver.CELLS)
        return inner(*a, **k)

    monkeypatch.setattr(driver, "run_cycle", run_cycle)


def _confirm_item(tmp_path: Path, cell: str) -> tuple[Path, dict]:
    src = _source(tmp_path)
    m = {i["cells"][0]: i for part in V.render_confirm(_args(src)) for i in part["campaigns"]}
    return src, m[cell]


def test_q2_driver_runs_driver_main_on_the_v5_cells_file(tmp_path, monkeypatch):
    """The override: driver.main, unedited, checks the v5 file's digest against the manifest,
    plans from it, and names it in every session's runner config (``/src/<file>``)."""
    from harness.q2.vm import driver

    src, item = _confirm_item(tmp_path, "ER")
    q2m = item["manifest"]
    rel = item["cells_file"]
    assert rel == V.CELLS_FILES["ER"]
    assert q2m["workload"]["cells_sha256"] == V.CELLS_SHA256["ER"]
    seen: list = []
    _stub_driver(monkeypatch, q2m, seen)
    run_dir = tmp_path / "run"
    (run_dir / "cycles").mkdir(parents=True)
    (run_dir / "manifest.json").write_text(json.dumps(q2m))
    monkeypatch.setattr(driver, "CELLS", driver.CELLS)  # restored after the test
    argv = [
        "--cells",
        rel,
        "--",
        "--manifest",
        str(run_dir / "manifest.json"),
        "--run-dir",
        str(run_dir),
        "--source-dir",
        str(src),
        "--job-id",
        "91",
    ]
    assert V.q2_driver(argv) == 0
    assert seen == [rel] * 5  # five cold boots, each reading the v5 file
    for cycle in range(5):
        config = json.loads((run_dir / "cycles" / f"config-{cycle:02d}.json").read_text())
        assert config["cells_path"] == f"/src/{rel}"
        assert config["measure_targets"] is False and len(config["trials"]) == 60
    record = json.loads((run_dir / V.OVERRIDE_RECORD).read_text())
    assert record == {
        "cell": "ER",
        "cells": rel,
        "sha256": V.CELLS_SHA256["ER"],
        "replaces": V.Q2_CELLS,
    }
    assert json.loads((run_dir / "receipt.json").read_text())["summary"]["infra_gates_pass"]


def test_q2_driver_refuses_what_is_not_the_pinned_v5_file(tmp_path, monkeypatch):
    from harness.q2.vm import driver

    src, item = _confirm_item(tmp_path, "AR")
    q2m = item["manifest"]
    monkeypatch.setattr(driver, "CELLS", driver.CELLS)
    run_dir = tmp_path / "run"
    rest = [
        "--manifest",
        str(run_dir / "manifest.json"),
        "--run-dir",
        str(run_dir),
        "--source-dir",
        str(src),
        "--job-id",
        "92",
    ]
    with pytest.raises(V.V5Error, match="must be one of"):
        V.q2_driver(["--cells", V.Q2_CELLS, "--", *rest])
    with pytest.raises(V.V5Error, match="DRIVER-ARGS"):
        V.q2_driver(["--cells", V.CELLS_FILES["AR"], *rest])
    path = src / V.CELLS_FILES["AR"]
    path.write_bytes(path.read_bytes().replace(b"789", b"790", 1))
    with pytest.raises(V.V5Error, match="pinned v5 cells file"):
        V.q2_driver(["--cells", V.CELLS_FILES["AR"], "--", *rest])
    assert driver.CELLS == V.Q2_CELLS
    # a manifest naming q2's cells digest is refused inside driver.main under the override
    shutil.copy(ROOT / V.CELLS_FILES["AR"], path)
    seen: list = []
    _stub_driver(monkeypatch, q2m, seen)
    (run_dir / "cycles").mkdir(parents=True)
    bad = json.loads(json.dumps(q2m))
    bad["workload"]["cells_sha256"] = V.cells_sha256(src, None)
    (run_dir / "manifest.json").write_text(json.dumps(bad))
    with pytest.raises(driver.DriverError, match="digest does not match"):
        V.q2_driver(["--cells", V.CELLS_FILES["AR"], "--", *rest])
    assert not seen


def test_run_campaign_routes_only_v5_cells_campaigns_through_the_override(tmp_path, monkeypatch):
    src, er = _confirm_item(tmp_path, "ER")
    _, pl = _confirm_item(tmp_path / "pl", "PL")
    calls: dict = {}

    class Proc:
        def __init__(self, argv, cwd):
            calls["argv"], calls["cwd"] = argv, cwd

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(V.subprocess, "Popen", Proc)
    monkeypatch.setattr(D, "docker", lambda *a, **k: type("P", (), {"stdout": ""})())
    monkeypatch.setattr(D, "labelled_left", lambda j: 0)
    assert V.run_campaign(er, tmp_path / "er", src, "93", 60.0, [False]) == 0
    argv = calls["argv"]
    assert argv[3:9] == [
        "-m",
        "harness.s2_locale.ap_delta_v5",
        "q2-driver",
        "--cells",
        V.CELLS_FILES["ER"],
        "--",
    ]
    assert argv[argv.index("--manifest") + 1] == str(tmp_path / "er" / "manifest.json")
    pre = (tmp_path / "er" / "preflight.txt").read_text().splitlines()
    assert pre[0] == "job_id=93" and f"cells={V.CELLS_FILES['ER']}" in pre
    assert pre[-1] == "driver_exit=0 labelled_containers_left=0"
    seen = []
    monkeypatch.setattr(D, "run_campaign", lambda *a: seen.append(a) or 0)
    assert V.run_campaign(pl, tmp_path / "pl-run", src, "94", 60.0, [False]) == 0
    assert len(seen) == 1 and seen[0][0] == pl["manifest"]  # ap_delta.run_campaign itself


# --------------------------------------------------------------------------- the confirmation


def test_confirmation_manifests(tmp_path):
    src = _source(tmp_path)
    parts = V.render_confirm(_args(src))
    assert [[i["cells"][0] for i in m["campaigns"]] for m in parts] == [
        ["ER", "AR"],
        ["PL", "E", "A"],
    ]
    pins = L.load_pins(src)
    q2_cells = V.cells_sha256(src, None)
    for k, m in enumerate(parts, 1):
        assert m["purpose"] == "development" and m["check"] == V.CONFIRM
        assert m["part"] == {"index": k, "of": 2}
        assert m["run_root"].startswith(V.CONFIRM_ROOT)
        for item in m["campaigns"]:
            cell, q2m = item["cells"][0], item["manifest"]
            w = q2m["workload"]
            assert q2m["randomness"]["seeds"] == [42] and q2m["vm"]["concurrency"] == 1
            assert q2m["vm"]["qcow2"]["sha256"] == pins[cell]["sha256"]
            assert w["kind"] == "canary-development" and w["measure_targets"] is False
            assert (w["reps"], w["sessions"], w["max_trial_s"]) == (5, 5, 30)
            if cell in ("ER", "AR", "PL"):  # the full A6: 60 entries x 5, one repetition a boot
                assert w["apps"] == ["writer", "chrome", "vscode", "terminal"]
                assert (w["entries"], w["session_trials"], w["trials"]) == ("all", 60, 300)
            else:  # the two Writer composites at q2's targets
                assert w["apps"] == ["writer"] and w["entries"] == list(V.COMPOSITES)
                assert (w["session_trials"], w["trials"]) == (2, 10)
            if cell in ("ER", "AR"):
                assert item["cells_file"] == V.CELLS_FILES[cell]
                assert w["cells_sha256"] == V.CELLS_SHA256[cell]
            else:
                assert "cells_file" not in item and w["cells_sha256"] == q2_cells
            plan = V.plan_of(q2m, src, item.get("cells_file"))
            assert len({c for _, c in plan[0]["trials"]}) == (60 if cell in V.CONFIRM_FULL else 2)
            D.q2_validate(q2m, src)
    assert [V.check_slurm(m)["minutes"] for m in parts] == [10 + 2 * 212, 10 + 212 + 2 * 72]
    assert all(m["slurm"]["minutes"] <= 12 * 60 for m in parts)  # each fits an E gap


def _edit_confirm(tmp_path, edit):
    src = _source(tmp_path)
    m = V.render_confirm(_args(src))[0]
    edit(m, src)
    return m, src


@pytest.mark.parametrize("edit, match", [
    (lambda m, s: m["campaigns"][0].pop("cells_file"), "cells file on ER"),
    (lambda m, s: m["campaigns"][1].update(cells_file=V.CELLS_FILES["ER"]), "cells file on AR"),
    (lambda m, s: m["campaigns"][0]["manifest"]["workload"].update(
        cells_sha256=V.cells_sha256(s, None)), "cells_sha256"),
    (lambda m, s: m["campaigns"][0]["manifest"]["workload"].update(measure_targets=True),
     "workload"),
    (lambda m, s: m["campaigns"][0]["manifest"]["workload"].update(reps=4), "workload"),
    (lambda m, s: m["campaigns"][1]["manifest"]["randomness"].update(seeds=[43]),
     "reserved for scored"),
    (lambda m, s: m["campaigns"].reverse(), "parts"),
    (lambda m, s: m["campaigns"].pop(), "parts"),
    (lambda m, s: m.update(part={"index": 2, "of": 2}), "part must be"),
    (lambda m, s: m.update(check="A6"), "only the confirmation"),
    (lambda m, s: m.update(purpose="k1"), "only after the freeze"),
    (lambda m, s: m.update(experiment_id=V.V4_ID), "experiment_id"),
    (lambda m, s: m.update(run_root=f"{V.K1_ROOT}/runs"), "run_root"),
    (lambda m, s: m["slurm"].update(gres="gpu:1"), "slurm: cpus, memory_gb, minutes"),
    (lambda m, s: m["slurm"].update(minutes=60), "cover every campaign"),
    (lambda m, s: m["campaigns"][0]["manifest"]["vm"]["qcow2"].update(sha256="0" * 64),
     "pinned"),
])  # fmt: skip
def test_confirmation_refusals(tmp_path, edit, match):
    m, src = _edit_confirm(tmp_path, edit)
    with pytest.raises(V.V5Error, match=match):
        V.validate_manifest(m, src)


def test_confirmation_runs_only_between_v4s_freeze_and_v5s(tmp_path):
    m = V.render_confirm(_args(_source(tmp_path)))[0]
    frozen = _source(tmp_path / "frozen")
    _freeze_v5(frozen)
    with pytest.raises(V.V5Error, match="is frozen: development no longer runs"):
        V.validate_manifest(m, frozen)
    before_v4 = _source(tmp_path / "before", v4_frozen=False)
    with pytest.raises(V.V5Error, match="follows the frozen"):
        V.validate_manifest(m, before_v4)


def _write_run(
    job_dir: Path,
    item: dict,
    k: int,
    src: Path,
    *,
    fail: str | None = None,
    override: bool = True,
    job: str = "1300",
) -> Path:
    """A campaign run directory as ap_delta_v5.run and harness/q2's driver write it."""
    q2m = item["manifest"]
    cell = item["cells"][0]
    sub = job_dir / f"{k:02d}-{q2m['campaign_id']}"
    (sub / "cycles").mkdir(parents=True)
    (sub / "manifest.json").write_text(json.dumps(q2m))
    meta = {"check": V.CONFIRM, "cells": [cell]}
    if item.get("cells_file"):
        meta["cells_file"] = item["cells_file"]
        if override:
            (sub / V.OVERRIDE_RECORD).write_text(json.dumps(
                {"cell": cell, "cells": item["cells_file"], "sha256": V.CELLS_SHA256[cell],
                 "replaces": V.Q2_CELLS}))  # fmt: skip
    (sub / "apdelta.json").write_text(json.dumps(meta))
    (sub / "preflight.txt").write_text(f"job_id={job}\ndriver_exit=0 labelled_containers_left=0\n")
    (sub / "receipt.json").write_text(
        json.dumps(
            {
                "job_id": job,
                "qcow2_unchanged": True,
                "summary": {"infra_gates_pass": True},
                "labelled_containers_left": [],
            }
        )
    )
    for session in V.plan_of(q2m, src, item.get("cells_file")):
        trials = [{"seq": seq, "cell": pair, "pass": pair != fail, "infra": []}
                  for seq, pair in session["trials"]]  # fmt: skip
        (sub / "cycles" / f"cycle-{session['index']:02d}.json").write_text(json.dumps(
            {"cycle": session["index"], "setting": "screenshot", "trials": trials,
             "boot": {"t_screenshot_200": 17.0}}))  # fmt: skip
    return sub


def _confirm_runs(tmp_path: Path, src: Path, **kw) -> list[Path]:
    jobs = []
    for n, m in enumerate(V.render_confirm(_args(src))):
        job_dir = tmp_path / "runs" / str(1300 + n)
        for k, item in enumerate(m["campaigns"]):
            opts = kw.get(item["cells"][0], {})
            _write_run(job_dir, item, k, src, job=str(1300 + n), **opts)
        jobs.append(job_dir)
    return jobs


def test_confirm_read_passes_every_entry_5_of_5(tmp_path):
    src = _source(tmp_path)
    out = V.confirm_read(_confirm_runs(tmp_path, src), src)
    assert out["pass"] and out["problems"] == [] and out["decision"].startswith("PROCEED")
    assert {c: (v["entries"], v["trials"], v["passed"]) for c, v in out["per_cell"].items()} == {
        "ER": (60, 300, 300),
        "AR": (60, 300, 300),
        "PL": (60, 300, 300),
        "E": (2, 10, 10),
        "A": (2, 10, 10),
    }
    assert out["per_cell"]["ER"]["cells_file"] == V.CELLS_FILES["ER"]
    assert out["per_cell"]["E"]["cells_file"] == V.Q2_CELLS


@pytest.mark.parametrize("kw, match", [
    ({"AR": {"fail": "writer:drag_select_word"}}, "AR: writer:drag_select_word 0 of 5"),
    ({"E": {"fail": "writer:triple_click_line"}}, "E: writer:triple_click_line 0 of 5"),
    ({"PL": {"fail": "terminal:type_plain"}}, "PL: terminal:type_plain 0 of 5"),
    ({"ER": {"override": False}}, "no override record"),
])  # fmt: skip
def test_confirm_read_any_failure_is_an_honest_exit(tmp_path, kw, match):
    src = _source(tmp_path)
    out = V.confirm_read(_confirm_runs(tmp_path, src, **kw), src)
    assert not out["pass"] and out["decision"].startswith("HONEST EXIT")
    assert any(match in p for p in out["problems"]), out["problems"]


def test_confirm_read_one_attempt_and_every_image(tmp_path):
    src = _source(tmp_path)
    jobs = _confirm_runs(tmp_path, src)
    m = V.render_confirm(_args(src))[0]
    again = tmp_path / "runs" / "1310"
    _write_run(again, m["campaigns"][0], 0, src, job="1310")  # ER a second time
    out = V.confirm_read([*jobs, again], src)
    assert not out["pass"] and "ER: 2 campaigns (one attempt, exactly one)" in out["problems"]
    out = V.confirm_read(jobs[:1], src)  # the second part never ran
    assert not out["pass"]
    assert {
        "PL: 0 campaigns (one attempt, exactly one)",
        "A: 0 campaigns (one attempt, exactly one)",
    } <= set(out["problems"])
    # a campaign that does not count (the driver did not exit 0) is a failure, not a rerun
    pre = next(jobs[0].iterdir()) / "preflight.txt"
    pre.write_text("job_id=1300\ndriver_exit=3 labelled_containers_left=0\n")
    assert not V.confirm_read(jobs, src)["pass"]


# --------------------------------------------------------------------------- K1 after the freeze


def _k1_args(src: Path, check: str, cell: str | None) -> argparse.Namespace:
    return argparse.Namespace(
        source_dir=src,
        git_sha="b" * 40,
        host_root=V.K1_ROOT,
        images_root=V.IMAGES_ROOT,
        repo=src,
        check=check,
        cell=cell,
    )


def test_k1_renders_a6_with_the_images_cells_file(tmp_path, monkeypatch):
    src = _source(tmp_path, prereg=True)
    (src / D.K1_PLAN).parent.mkdir(parents=True)
    shutil.copy(ROOT / D.K1_PLAN, src / D.K1_PLAN)
    _freeze_v5(src)
    monkeypatch.setattr(L, "check_freeze_commit", lambda repo, commit, row: {})
    rendered = {}
    for check, cell in (("A6", "ER"), ("A6", "AR"), ("A6", "E"), ("C1", "ER")):
        (m,) = V.render_k1(_k1_args(src, check, cell))
        assert m["experiment_id"] == V.EXPERIMENT_ID and m["purpose"] == "k1"
        assert m["freeze"]["commit"] == "b" * 40
        rendered[(check, cell)] = m
        for item in m["campaigns"]:
            q2m = item["manifest"]
            assert q2m["campaign_id"].startswith("s2v5-k1-")
            assert q2m["run_root"].startswith(V.K1_ROOT)
    for cell in ("ER", "AR"):
        (item,) = rendered[("A6", cell)]["campaigns"]
        assert item["cells_file"] == V.CELLS_FILES[cell]
        assert item["manifest"]["workload"]["cells_sha256"] == V.CELLS_SHA256[cell]
        assert item["manifest"]["workload"]["kind"] == "canary-acceptance"
    (item,) = rendered[("A6", "E")]["campaigns"]
    assert "cells_file" not in item
    assert item["manifest"]["workload"]["cells_sha256"] == V.cells_sha256(src, None)
    assert all("cells_file" not in i for i in rendered[("C1", "ER")]["campaigns"])
    # what a k1 job refuses: the wrong cells, the parent's export, a v4 manifest, no freeze
    m = rendered[("A6", "ER")]
    for edit, match in (
        (lambda x: x["campaigns"][0].pop("cells_file"), "cells file on ER"),
        (
            lambda x: x["campaigns"][0]["manifest"]["workload"].update(
                cells_sha256=V.cells_sha256(src, None)
            ),
            "cells_sha256",
        ),
        (lambda x: x["freeze"].update(commit="c" * 40), "freeze commit"),
        (lambda x: x.update(run_root=f"{D.K1_ROOT}/runs"), "run_root"),
        (lambda x: x.update(experiment_id=V.V4_ID), "experiment_id"),
    ):
        bad = json.loads(json.dumps(m))
        edit(bad)
        with pytest.raises(V.V5Error, match=match):
            V.validate_manifest(bad, src)
    (src / V.REGISTRATION).write_text("# edited after the freeze\n")
    with pytest.raises(V.V5Error, match="changed after the freeze"):
        V.validate_manifest(m, src)
    with pytest.raises(V.V5Error, match="only after the freeze"):
        V.validate_manifest(m, _source(tmp_path / "unfrozen"))


def test_k1_plan_is_v4s():
    """v5 runs v4's registered K1 campaigns: the same plan file and pin."""
    assert hashlib.sha256((ROOT / D.K1_PLAN).read_bytes()).hexdigest() == D.K1_PLAN_SHA256
    assert V.CHECKS == D.CHECKS and V.K1_CELLS == D.K1_CELLS == ("E", "A", "ER", "AR", "PL")


def test_verdict_confirms_each_a6_campaign_read_its_images_cells(tmp_path, monkeypatch):
    src = _source(tmp_path)
    monkeypatch.setattr(
        D, "verdict", lambda jobs, sha: {"K1": "PASS", "rung": {"qualifies": True}, "per_image": {}}
    )
    job = tmp_path / "1400"
    for k, cell in enumerate(("E", "ER")):
        sub = job / f"{k:02d}-a6-{cell.lower()}"
        sub.mkdir(parents=True)
        rel = V.CELLS_FILES.get(cell)
        q2m = {"workload": {"kind": "canary-acceptance",
                            "cells_sha256": V.CELLS_SHA256[cell] if rel else
                            V.cells_sha256(src, None)}}  # fmt: skip
        (sub / "manifest.json").write_text(json.dumps(q2m))
        meta = {"check": "A6", "cells": [cell], **({"cells_file": rel} if rel else {})}
        (sub / "apdelta.json").write_text(json.dumps(meta))
        if rel:
            (sub / V.OVERRIDE_RECORD).write_text(
                json.dumps({"cells": rel, "sha256": V.CELLS_SHA256[cell]})
            )
    out = V.verdict([job], "b" * 40, src)
    assert out["K1"] == "PASS" and out["a6_cells"]["pass"]
    assert out["schema"] == "s2v5-k1-verdict-v1"
    (job / "01-a6-er" / V.OVERRIDE_RECORD).unlink()
    out = V.verdict([job], "b" * 40, src)
    assert out["K1"] == "FAIL" and not out["a6_cells"]["pass"]


# --------------------------------------------------------------------------- submit and batch


def test_submit_dry_run_and_the_scheduling_rules(tmp_path):
    src = _source(tmp_path)
    (src / "infra/slurm/host-single-node").mkdir(parents=True)
    shutil.copy(ROOT / V.BATCH, src / V.BATCH)
    m = V.render_confirm(_args(src))[0]
    path = tmp_path / "confirm.json"
    path.write_text(json.dumps(m))
    out = V.submit(path, src, dry_run=True, must_end_before=None)
    argv = out["argv"]
    assert argv[0] == "sbatch" and argv[-1].endswith("s2v5-apdelta.sbatch")
    assert "--time=07:14:00" in argv and not any("gres" in a or "gpu" in a.lower() for a in argv)
    assert not Path(out["manifest"]).exists()
    with pytest.raises(V.V5Error, match="exactly one of"):
        V.submit(path, src, dry_run=False, must_end_before=None)
    with pytest.raises(V.V5Error, match="exactly one of"):
        V.submit(
            path, src, dry_run=False, must_end_before="2099-01-01T00:00:00Z", no_e_deadline=True
        )
    with pytest.raises(V.V5Error, match="would end after"):
        V.submit(path, src, dry_run=False, must_end_before="2026-10-13T00:00:00Z")


def test_batch_file_is_v4s_with_the_names_and_the_program_changed():
    text = (ROOT / V.BATCH).read_text()
    V.check_cpu_only(["sbatch", "--cpus-per-task=5"], text)
    assert "python3 -E -s -m harness.s2_locale.ap_delta_v5 run" in text
    with pytest.raises(V.V5Error, match="GPU"):
        V.check_cpu_only(["sbatch", "--gres=gpu:1"], text)
    v4 = (ROOT / D.BATCH).read_text()
    body = lambda t: t[t.index("set -Eeuo pipefail") :]  # noqa: E731
    mapped = (body(text).replace("COTCODEC_S2V5_", "COTCODEC_S2V4_")
              .replace("ap_delta_v5 run", "ap_delta run"))  # fmt: skip
    differ = [(a, b) for a, b in zip(mapped.splitlines(), body(v4).splitlines(), strict=True)
              if a != b]  # fmt: skip
    assert all("s2v5" in a.lower() or "S2 v5" in a for a, _ in differ), differ


def test_v4s_code_and_harness_q2_are_not_edited():
    """v5 extends ap_delta and vm_lane without editing them: v4's pinned files and harness/q2
    are byte-identical to v4's frozen table."""
    reg = (ROOT / "program/preregistrations/s2-arabic-cua-locale-v4.md").read_text()
    for path in ("harness/s2_locale/ap_delta.py", "harness/s2_locale/vm_lane.py",
                 "harness/s2_locale/vm_probe.py", "harness/s2_locale/k0_v4.py",
                 "harness/q2/vm/driver.py", "harness/q2/vm/runner.py",
                 "harness/q2/vm/canary_run.py", "harness/q2/action_path/suite_cells.json",
                 "harness/q2/action_path/canary_targets.json", D.BATCH, L.BATCH,
                 "experiments/manifests/s2v4/k1-plan.json",
                 "experiments/manifests/s2v4/phase0-census.json"):  # fmt: skip
        sha = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert f"| `{path}` | `{sha}` |" in reg, path
