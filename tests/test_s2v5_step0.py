"""S2 v5 step 0 (D94): ap_delta's development renderer extended to A6's canary (no Docker)."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from harness.s2_locale import ap_delta as D
from harness.s2_locale import ap_delta_step0 as S
from harness.s2_locale import vm_lane as L

ROOT = Path(__file__).resolve().parents[1]


def _source(tmp_path: Path, ledger_extra: list[dict] | None = None) -> Path:
    """A view of the tree as the step-0 export has it: the harness and the ledger (v4 frozen,
    v5 not), optionally with rows appended (hash chain kept)."""
    src = tmp_path / "src"
    shutil.copytree(ROOT / "harness", src / "harness",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))  # fmt: skip
    (src / "program/preregistrations").mkdir(parents=True)
    lines = (ROOT / L.LEDGER).read_text().splitlines()
    for extra in ledger_extra or []:
        previous = json.loads(lines[-1])["hash"]
        body = dict(extra, previous_hash=previous)
        body["hash"] = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        lines.append(json.dumps(body, sort_keys=True))
    (src / L.LEDGER).write_text("\n".join(lines) + "\n")
    return src


def _args(tmp_path, **kw):
    return argparse.Namespace(source_dir=_source(tmp_path, **kw), git_sha="f" * 40,
                              host_root=S.HOST_ROOT, images_root=S.IMAGES_ROOT)  # fmt: skip


def test_render_one_canary_development_campaign_per_image(tmp_path):
    args = _args(tmp_path)
    m = S.render(args)
    assert m["experiment_id"] == "s2-arabic-cua-locale-v5" and m["purpose"] == "development"
    assert [item["cells"] for item in m["campaigns"]] == [["E"], ["A"], ["ER"], ["AR"], ["PL"]]
    pins = L.load_pins(args.source_dir)
    for item in m["campaigns"]:
        q2m = item["manifest"]
        cell = item["cells"][0]
        w = q2m["workload"]
        assert w["kind"] == "canary-development" and w["measure_targets"] is True
        assert w["apps"] == ["writer", "chrome", "vscode"]
        assert w["entries"] == ["triple_click_line", "drag_select_word"]
        assert (w["reps"], w["session_trials"], w["sessions"], w["trials"]) == (5, 6, 5, 30)
        assert q2m["randomness"]["seeds"] == [42] and q2m["vm"]["concurrency"] == 1
        assert q2m["model"]["kind"] == "none" and q2m["purpose"] == "development"
        assert q2m["vm"]["qcow2"]["sha256"] == pins[cell]["sha256"]
        assert q2m["vm"]["qcow2"]["host_path"] == f"{S.IMAGES_ROOT}/s2v4-cell-{cell}.qcow2"
        assert q2m["run_root"].startswith(S.HOST_ROOT)
        D.q2_validate(q2m, args.source_dir)  # harness/q2's own admission
    from harness.q2.vm import driver

    cells = json.loads((args.source_dir / D.CELLS_FILE).read_text())
    plan = driver.session_plan(m["campaigns"][0]["manifest"], cells)
    pairs = {f"{a}:{e}" for a in S.APPS for e in S.ENTRIES}
    assert len(plan) == 5 and all({c for _, c in s["trials"]} == pairs for s in plan)  # 1 rep/boot
    slurm = S.check_slurm(m)
    assert slurm == {"cpus": 5, "memory_gb": 9, "minutes": 10 + 5 * (110 + 2),
                     "budget_minutes": 570}  # fmt: skip


@pytest.mark.parametrize("edit, match", [
    (lambda m: m.update(experiment_id=L.EXPERIMENT_ID), "experiment_id"),
    (lambda m: m.update(purpose="k1"), "development"),
    (lambda m: m["campaigns"].reverse(), "in the order"),
    (lambda m: m["campaigns"].pop(), "in the order"),
    (lambda m: m["campaigns"][2]["manifest"]["vm"]["qcow2"].update(sha256="0" * 64), "pinned"),
    (lambda m: m["campaigns"][0]["manifest"]["workload"].update(measure_targets=False),
     "workload"),
    (lambda m: m["campaigns"][0]["manifest"]["workload"].update(apps=["writer"]), "workload"),
    (lambda m: m["campaigns"][1]["manifest"]["workload"].update(reps=4), "workload"),
    (lambda m: m["campaigns"][1]["manifest"]["randomness"].update(seeds=[43]), "seed 42"),
    (lambda m: m["campaigns"][3]["manifest"]["vm"].update(concurrency=2), "one VM"),
    (lambda m: m["campaigns"][3]["manifest"]["model"].update(kind="hf"), "no model"),
    (lambda m: m["slurm"].update(gres="gpu:1"), "slurm: cpus, memory_gb, minutes"),
    (lambda m: m["slurm"].update(minutes=60), "cover every campaign"),
    (lambda m: m.update(run_root="/home/kevin/cotcodec-runs/stage0/s2v4/k1/runs"), "run_root"),
])  # fmt: skip
def test_step0_refusals(tmp_path, edit, match):
    args = _args(tmp_path)
    m = S.render(args)
    edit(m)
    with pytest.raises(S.Step0Error, match=match):
        S.validate_manifest(m, args.source_dir)


def test_step0_is_refused_once_v5_is_frozen(tmp_path):
    row = {"experiment_id": S.EXPERIMENT_ID, "path": "program/preregistrations/x.md"}
    args = _args(tmp_path)
    m = S.render(args)
    frozen = _source(tmp_path / "frozen", ledger_extra=[row])
    with pytest.raises(S.Step0Error, match="is frozen"):
        S.validate_manifest(m, frozen)


def test_submit_dry_run_requests_cpu_only_and_writes_nothing(tmp_path):
    args = _args(tmp_path)
    (args.source_dir / "infra/slurm/host-single-node").mkdir(parents=True)
    shutil.copy(ROOT / S.BATCH, args.source_dir / S.BATCH)
    m = S.render(args)
    path = tmp_path / "step0.json"
    path.write_text(json.dumps(m))
    out = S.submit(path, args.source_dir, dry_run=True, must_end_before=None)
    argv = out["argv"]
    assert argv[0] == "sbatch" and argv[-1].endswith("s2v5-step0.sbatch")
    assert "--cpus-per-task=5" in argv and "--mem=9G" in argv and "--time=09:30:00" in argv
    assert not any("gres" in a or "gpu" in a.lower() for a in argv)
    assert not Path(out["manifest"]).exists()
    # a real submission needs E4's earliest start, and a limit that ends before it
    with pytest.raises(S.Step0Error, match="must-end-before"):
        S.submit(path, args.source_dir, dry_run=False, must_end_before=None)
    with pytest.raises(S.Step0Error, match="would end after"):
        S.submit(path, args.source_dir, dry_run=False, must_end_before="2026-10-13T00:00:00Z")


def test_batch_file_holds_no_gpu_and_runs_the_step0_runner():
    text = (ROOT / S.BATCH).read_text()
    S.check_cpu_only(["sbatch", "--cpus-per-task=5"], text)
    assert "python3 -E -s -m harness.s2_locale.ap_delta_step0 run" in text
    assert "gres/gpu" in text and "CUDA_VISIBLE_DEVICES" in text  # the refusals
    with pytest.raises(S.Step0Error, match="GPU"):
        S.check_cpu_only(["sbatch", "--gres=gpu:1"], text)
    with pytest.raises(S.Step0Error, match="batch file asks"):
        S.check_cpu_only(["sbatch"], "#SBATCH --gres=gpu:1\nrefusing to start VMs\n")
    # the v4 batch, with the names and the program changed (the guards are the same lines)
    v4 = (ROOT / "infra/slurm/host-single-node/s2v4-apdelta.sbatch").read_text()
    body = lambda t: t[t.index("set -Eeuo pipefail") :]  # noqa: E731
    mapped = (body(text).replace("COTCODEC_S2V5_", "COTCODEC_S2V4_")
              .replace("ap_delta_step0 run", "ap_delta run"))  # fmt: skip
    differ = [a for a, b in zip(mapped.splitlines(), body(v4).splitlines(), strict=True) if a != b]
    assert all("s2v5" in line.lower() or "S2 v5" in line for line in differ), differ


def test_keep_screenshots_moves_one_boot(tmp_path):
    (tmp_path / "canary-000-writer-drag_select_word.png").write_bytes(b"a")
    (tmp_path / "canary-000-after-drag_select_word.png").write_bytes(b"b")
    (tmp_path / "cycle-00.json").write_text("{}")
    kept = S.keep_screenshots(tmp_path, 0)
    assert kept == {
        "canary-000-after-drag_select_word.png": hashlib.sha256(b"b").hexdigest(),
        "canary-000-writer-drag_select_word.png": hashlib.sha256(b"a").hexdigest(),
    }
    assert sorted(p.name for p in (tmp_path / "shots-00").iterdir()) == sorted(kept)
    assert (tmp_path / "cycle-00.json").exists() and not list(tmp_path.glob("canary-*"))


def _stub_driver(monkeypatch, q2m, seen, written):
    from harness.q2.vm import driver

    monkeypatch.setattr(
        S.os,
        "stat",
        lambda p, follow_symlinks=False: type(
            "St", (), {"st_size": q2m["vm"]["qcow2"]["size_bytes"], "st_mode": 0o100444}
        )(),
    )
    monkeypatch.setattr(S.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(S.os.path, "islink", lambda p: False)
    monkeypatch.setattr(driver, "sha256_file", lambda p: q2m["vm"]["qcow2"]["sha256"])
    monkeypatch.setattr(driver, "slurm_cpu_ids", lambda j: list(range(8)))
    monkeypatch.setattr(driver, "numa_nodes", lambda: {0: set(range(8))})
    monkeypatch.setattr(driver, "snapshot_host", lambda j: {"t": 0})

    def run_cycle(m, job, cycle, prev, run_dir, src, cpus, session=None):
        seen.append((cycle, prev, m["vm"]["qcow2"]["sha256"], cpus["vm"], len(session["trials"])))
        for seq, pair in session["trials"]:  # the runner's measure-mode screenshots
            app, entry = pair.split(":")
            data = f"{cycle}-{seq}".encode()
            (run_dir / "cycles" / f"canary-{seq:03d}-{app}-{entry}.png").write_bytes(data)
            written.setdefault(cycle, set()).add(f"canary-{seq:03d}-{app}-{entry}.png")
        return {"cycle": cycle, "token": f"t{cycle}"}

    monkeypatch.setattr(driver, "run_cycle", run_cycle)
    monkeypatch.setattr(driver, "cycle_verdict", lambda r, t: {"ok": True, "cycle": r["cycle"]})
    monkeypatch.setattr(
        driver,
        "summarize",
        lambda v, r: {
            "boots_ok": len(r),
            "cycles": len(r),
            "no_gpu_all": True,
            "no_published_ports_all": True,
            "containers_removed_all": True,
            "leaked_volumes": [],
        },
    )
    monkeypatch.setattr(driver, "session_summary", lambda r: {"runner_errors": []})
    monkeypatch.setattr(D, "docker", lambda *a, **k: type("P", (), {"stdout": ""})())
    calls: list = []

    def run(argv, timeout=120.0, check=True):
        calls.append(argv)
        if argv[1] == "info":
            out = json.dumps({"ServerVersion": "27", "DefaultRuntime": "runc"})
        elif argv[1:3] == ["image", "inspect"] and argv[-1] == q2m["vm"]["image_id"]:
            out = f'{q2m["vm"]["image_id"]} ["{q2m["vm"]["image"]}"]'
        elif argv[1:3] == ["image", "inspect"]:
            out = q2m["runner"]["image_id"]
        elif argv[1] == "run":
            out = json.dumps({"format": "qcow2", "virtual-size": 53687091200})
        else:
            out = ""
        return type("P", (), {"stdout": out})()

    monkeypatch.setattr(driver, "run", run)
    return calls


def test_run_canary_keeps_every_boots_screenshots(tmp_path, monkeypatch):
    """driver.main's single-VM branch (driver stubbed): the five sessions in order on the cell's
    image, each one's screenshots moved into its own directory (they share names across boots)."""
    args = _args(tmp_path)
    m = S.render(args)
    item = m["campaigns"][2]  # ER
    q2m = item["manifest"]
    seen: list = []
    written: dict = {}
    calls = _stub_driver(monkeypatch, q2m, seen, written)
    run_dir = tmp_path / "run"
    rc = S.run_canary(item, run_dir, Path(args.source_dir), "91", [False])
    assert rc == 0
    assert [s[0] for s in seen] == [0, 1, 2, 3, 4]
    assert [s[1] for s in seen] == [None, "t0", "t1", "t2", "t3"]  # driver.main's prev token
    assert {s[2] for s in seen} == {q2m["vm"]["qcow2"]["sha256"]} and {s[4] for s in seen} == {6}
    assert [c[1] for c in calls[:3]] == ["info", "image", "image"]
    for cycle in range(5):
        record = json.loads((run_dir / "cycles" / f"record-{cycle:02d}.json").read_text())
        kept = record["step0_screenshots"]
        assert set(kept) == written[cycle]
        for name, sha in kept.items():
            data = (run_dir / "cycles" / f"shots-{cycle:02d}" / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == sha and data.startswith(f"{cycle}-".encode())
    receipt = json.loads((run_dir / "receipt.json").read_text())
    assert receipt["summary"]["infra_gates_pass"] and receipt["qcow2_unchanged"]
    assert receipt["ap_delta"] == {"step0": True, "cell": "ER"}
    assert (run_dir / "preflight.txt").read_text().splitlines()[-1] == (
        "driver_exit=0 labelled_containers_left=0"
    )
    # USR1 before the third boot: two sessions, then a stop (not a pass)
    seen.clear()
    stop = [False]
    from harness.q2.vm import driver

    inner = driver.run_cycle

    def stopping(*a, **k):
        out = inner(*a, **k)
        if out["cycle"] == 1:
            stop[0] = True
        return out

    monkeypatch.setattr(driver, "run_cycle", stopping)
    assert S.run_canary(item, tmp_path / "run2", Path(args.source_dir), "92", stop) == 3
    assert [s[0] for s in seen] == [0, 1]
    assert json.loads((tmp_path / "run2" / "receipt.json").read_text())["stopped_before_cycle"] == 2


def test_run_canary_stops_before_any_session_without_the_runner_image(tmp_path, monkeypatch):
    args = _args(tmp_path)
    item = S.render(args)["campaigns"][0]
    q2m = item["manifest"]
    seen: list = []
    _stub_driver(monkeypatch, q2m, seen, {})
    from harness.q2.vm import driver

    real = driver.run
    monkeypatch.setattr(
        driver,
        "run",
        lambda argv, timeout=120.0, check=True: type(
            "P", (), {"stdout": "" if argv[-1] == q2m["runner"]["image_id"] else real(argv).stdout}
        )(),
    )
    assert S.run_canary(item, tmp_path / "run", Path(args.source_dir), "93", [False]) == 3
    assert not seen
    assert (
        "runner image is missing"
        in json.loads((tmp_path / "run" / "receipt.json").read_text())["error"]
    )


def test_ap_delta_and_harness_q2_are_not_edited():
    """Step 0 extends ap_delta without editing it: v4's pinned files are byte-identical."""
    reg = (ROOT / "program/preregistrations/s2-arabic-cua-locale-v4.md").read_text()
    for path in ("harness/s2_locale/ap_delta.py", "harness/s2_locale/vm_lane.py",
                 "harness/q2/vm/canary_run.py", "harness/q2/action_path/suite_cells.json",
                 "harness/q2/action_path/canary_targets.json"):  # fmt: skip
        sha = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert f"| `{path}` | `{sha}` |" in reg, path
