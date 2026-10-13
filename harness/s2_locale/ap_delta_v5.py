"""S2 v5 (decisions D94, D96): K1 through ap_delta, with A6's Writer targets per image.

Registration ``s2-arabic-cua-locale-v5``, section "K1". v5 is v4's registration with one change
(D96): the targets of A6's two pointer composites (``triple_click_line``, ``drag_select_word``) in
LibreOffice Writer on the mirrored images, where Writer draws its document 71 px to the right of
where q2 measured it on the certified disk (D93, D94; step 0, Slurm 1271):

* ER: a drag from (751, 293) to (779, 293) in 500 ms and a triple-click at (789, 293);
* AR: a drag from (751, 294) to (779, 294) in 500 ms and a triple-click at (789, 294);
* every other (image, application) keeps q2's frozen targets (``canary_targets.json``).

These are step 0's medians (``step0-result.json``'s ``v5_targets``, pinned by its SHA-256 in
``STEP0_RESULT_SHA256``); no target was chosen by hand.

How they reach harness/q2's runner without editing harness/q2. The runner reads the canary's
targets from the suite-cells file the driver names in each session's config (``driver.CELLS``,
``"/src/" + CELLS``), and the driver checks that file's SHA-256 against the manifest's
``workload.cells_sha256`` before any session. For ER and AR, v5 has its own cells file
(``CELLS_FILES``, under ``harness/s2_locale/canary_v5/``, the only part of the source tree the
runner sees besides harness/q2 being ``harness/``): q2's ``suite_cells.json`` byte for byte except
``canary.apps.writer.targets`` (``render_cells``; pinned in ``CELLS_SHA256``). An A6 campaign on
ER or AR runs ``q2-driver``: harness/q2's ``driver.main``, unedited, with the module constant
``driver.CELLS`` set to that file before it starts, so the driver's digest check, its session plan
and every session's runner read the v5 file. Every other campaign (every other check, and A6 on E,
A and PL) runs exactly as v4 runs it, through ``ap_delta.run_campaign`` and ``ap_delta.run_rung``,
on q2's own cells file. ``harness/q2`` and ``ap_delta.py`` stay byte-identical (v4's frozen pins).

Purposes:

* ``development`` (check ``confirm``), before the freeze only: the development confirmation that
  D96 makes a pre-freeze gate. The full A6 (60 entries, 5 repetitions, seed 42) on ER, AR and PL,
  and the two Writer pointer composites (5 repetitions, seed 42) on E and A at q2's targets: q2
  ``canary-development`` campaigns, one per image, one VM at a time, with A6's own session shape
  (one repetition per cold boot, 30 s per trial) and no target measurement. Its reading
  (``confirm_read``): every entry 5 of 5 on every image, one attempt; any failure is an honest exit
  for S2.
* ``k1``, after the freeze only, from the freeze commit's export: v4's K1 plan
  (``experiments/manifests/s2v4/k1-plan.json``, ``ap_delta.K1_PLAN_SHA256``), every check and rule
  unchanged, run under v5's id and run root (``K1_ROOT``).

Commands: ``render-cells`` (writes the two cells files), ``render-confirm`` and ``render`` (Mac;
PyYAML), ``validate``, ``submit`` (host; ``--dry-run`` writes nothing), ``run`` (inside the job),
``q2-driver`` (inside the job), ``confirm-read`` and ``verdict`` (host or Mac). Standard library
only on the host (Python 3.10).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.s2_locale import ap_delta as D
from harness.s2_locale import vm_lane as L

SCHEMA = "s2v5-apdelta-v1"
EXPERIMENT_ID = "s2-arabic-cua-locale-v5"
V4_ID = L.EXPERIMENT_ID
REGISTRATION = "program/preregistrations/s2-arabic-cua-locale-v5.md"
PURPOSES = ("development", "k1")
CONFIRM = "confirm"
CHECKS = D.CHECKS
K1_CELLS = D.K1_CELLS
RUN_ROOT = L.RUN_ROOT
K1_ROOT = f"{RUN_ROOT}stage0/s2v5/k1"
CONFIRM_ROOT = f"{RUN_ROOT}stage0/s2v5/confirm"
IMAGES_ROOT = f"{RUN_ROOT}stage0/s2v4/image-build-v5/a"  # build 1207's pinned images (v4's)
BATCH = "infra/slurm/host-single-node/s2v5-apdelta.sbatch"
TEMPLATE = "experiments/manifests/q2-action-path/dev-l0-fixed-v10.yaml"
Q2_CELLS = D.CELLS_FILE
Q2_TARGETS = "harness/q2/action_path/canary_targets.json"
STEP0_RESULT = "program/evidence/2026-10-13/s2v5-step0/step0-result.json"
STEP0_RESULT_SHA256 = "18d8b910175ffe084a20f6a3e6963e71e205cfd170d4fcd24d16c0633f85e5d6"
# D96: A6's Writer targets on the mirrored images, step 0's medians (Slurm 1271). Every other
# (image, application) keeps q2's frozen targets.
WRITER_TARGETS: dict[str, dict[str, Any]] = {
    "ER": {"drag_select_word": {"duration_ms": 500, "from": [751, 293], "to": [779, 293]},
           "triple_click_line": {"x": 789, "y": 293}},
    "AR": {"drag_select_word": {"duration_ms": 500, "from": [751, 294], "to": [779, 294]},
           "triple_click_line": {"x": 789, "y": 294}},
}  # fmt: skip
CELLS_DIR = "harness/s2_locale/canary_v5"
CELLS_FILES = {cell: f"{CELLS_DIR}/suite_cells-{cell}.json" for cell in WRITER_TARGETS}
CELLS_SHA256 = {
    "ER": "464c9ab2aecf11c5e6405afac3a3f5ef8d5fa6f33b286bfcbd960624f049f070",
    "AR": "b81b63c6973fd21598965c1fd06247401c63e8c6bf979c2fc15e74ac3dfa4726",
}
OVERRIDE_RECORD = "cells_override.json"
CANARY_KINDS = ("canary-acceptance", "canary-development")
# The development confirmation (D96): two jobs (each fits a gap between successor E sessions);
# the full A6 on these images, the two Writer composites on the others.
CONFIRM_PARTS = (("ER", "AR"), ("PL", "E", "A"))
CONFIRM_FULL = ("ER", "AR", "PL")
COMPOSITES = ("triple_click_line", "drag_select_word")
CONFIRM_REPS = 5
CONFIRM_MAX_TRIAL_S = 30  # A6's own (ap_delta.render_campaign renders it at 30 s per trial)
SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")


class V5Error(ValueError):
    """The manifest is outside v5's registration; nothing may start."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise V5Error(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- targets and cells


def targets(source_dir: Path, cell: str) -> dict[str, Any]:
    """Every application's A6 targets on ``cell``'s image: q2's frozen targets, with Writer's
    replaced on ER and AR (D96)."""
    out = json.loads((source_dir / Q2_TARGETS).read_text(encoding="utf-8"))["apps"]
    if cell in WRITER_TARGETS:
        out["writer"] = copy.deepcopy(WRITER_TARGETS[cell])
    return out


def render_cells(source_dir: Path, cell: str) -> bytes:
    """``cell``'s v5 cells file: q2's ``suite_cells.json`` with Writer's targets replaced, in
    ``build_suite.render``'s format (q2's file round-trips through it byte for byte)."""
    data = json.loads((source_dir / Q2_CELLS).read_text(encoding="utf-8"))
    data["canary"]["apps"]["writer"]["targets"] = copy.deepcopy(WRITER_TARGETS[cell])
    return (json.dumps(data, indent=1, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def check_cells_files(source_dir: Path) -> dict[str, str]:
    """The v5 cells files in ``source_dir`` are the pinned ones and are q2's file with only
    Writer's targets replaced (raises)."""
    out = {}
    for cell, rel in CELLS_FILES.items():
        path = source_dir / rel
        _require(path.is_file() and not path.is_symlink(), f"{rel} is missing")
        data = path.read_bytes()
        out[cell] = _sha256(data)
        _require(out[cell] == CELLS_SHA256[cell], f"{rel} is not the pinned v5 cells file")
        _require(
            data == render_cells(source_dir, cell),
            f"{rel} is not q2's suite_cells.json with only Writer's targets replaced",
        )
    return out


def cells_file(cell: str, kind: str | None) -> str | None:
    """The v5 cells file a campaign of workload ``kind`` on ``cell`` runs with, or None (q2's)."""
    return CELLS_FILES.get(cell) if kind in CANARY_KINDS else None


def cells_sha256(source_dir: Path, rel: str | None) -> str:
    return _sha256((source_dir / (rel or Q2_CELLS)).read_bytes())


# --------------------------------------------------------------------------- ledger


def ledger_row(source_dir: Path, experiment_id: str = EXPERIMENT_ID) -> dict[str, Any] | None:
    """``experiment_id``'s ledger row after checking the hash chain end to end (None when it has
    none; ``vm_lane.ledger_row`` with the id as a parameter)."""
    ledger = source_dir / L.LEDGER
    if not ledger.is_file():
        return None
    previous, row = "0" * 64, None
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        entry = json.loads(line)
        body = {k: v for k, v in entry.items() if k != "hash"}
        digest = _sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
        _require(entry.get("previous_hash") == previous and entry.get("hash") == digest,
                 f"ledger line {number}: the hash chain does not hold")  # fmt: skip
        previous = digest
        if row is None and entry.get("experiment_id") == experiment_id:
            row = entry
    return row


def frozen_registration(source_dir: Path) -> dict[str, Any]:
    """v5's ledger row, once the source tree's registration is the frozen file (raises)."""
    row = ledger_row(source_dir)
    _require(row is not None, f"no ledger row for {EXPERIMENT_ID}: it is not frozen")
    assert row is not None
    _require(row.get("path") == REGISTRATION, f"the ledger row names {row.get('path')!r}")
    path = source_dir / REGISTRATION
    _require(path.is_file() and not path.is_symlink(), f"{REGISTRATION} is missing")
    actual = _sha256(path.read_bytes())
    _require(
        actual == row.get("sha256"),
        f"{REGISTRATION} changed after the freeze ({actual} != {row.get('sha256')})",
    )
    return row


# --------------------------------------------------------------------------- validation


def confirm_workload(cell: str) -> dict[str, Any]:
    """The q2 workload of the confirmation's campaign on ``cell`` (without its counts)."""
    from harness.q2.vm.manifest import CANARY_APPS

    full = cell in CONFIRM_FULL
    return {"kind": "canary-development", "apps": list(CANARY_APPS) if full else ["writer"],
            "entries": "all" if full else list(COMPOSITES), "reps": CONFIRM_REPS,
            "session_trials": 60 if full else len(COMPOSITES), "measure_targets": False,
            "boot_timeout_s": 300, "settle_timeout_s": 60,
            "max_trial_s": CONFIRM_MAX_TRIAL_S}  # fmt: skip


def plan_of(q2m: Mapping[str, Any], source_dir: Path, rel: str | None) -> list[dict[str, Any]]:
    """The sessions harness/q2's driver runs for a canary-development campaign, from the cells
    file it will read."""
    from harness.q2.vm import driver

    cells = json.loads((source_dir / (rel or Q2_CELLS)).read_text(encoding="utf-8"))
    return driver.session_plan(json.loads(json.dumps(q2m)), cells)


def check_confirm(m: Mapping[str, Any], source_dir: Path) -> None:
    """A confirmation manifest is one of ``CONFIRM_PARTS`` exactly: per image one q2
    canary-development campaign with ``confirm_workload``, seed 42, no model, one VM, the plan's
    counts (one repetition per cold boot)."""
    cells = [item["cells"] for item in m["campaigns"]]
    parts = [[[c] for c in part] for part in CONFIRM_PARTS]
    _require(cells in parts, f"the confirmation runs the parts {list(CONFIRM_PARTS)}")
    index = parts.index(cells) + 1
    _require(
        m.get("part") == {"index": index, "of": len(CONFIRM_PARTS)},
        f"part must be {{index: {index}, of: {len(CONFIRM_PARTS)}}}",
    )
    for item in m["campaigns"]:
        q2m, cell = item["manifest"], item["cells"][0]
        cid = q2m.get("campaign_id")
        _require(
            q2m.get("experiment_id") == "q2-action-path-v2" and q2m.get("purpose") == "development",
            f"{cid}: a q2-action-path-v2 development campaign",
        )
        _require((q2m.get("model") or {}).get("kind") == "none", f"{cid}: no model")
        _require((q2m.get("randomness") or {}).get("seeds") == [42], f"{cid}: seed 42")
        w = q2m.get("workload") or {}
        want = confirm_workload(cell)
        _require({k: w.get(k) for k in want} == want, f"{cid}: the workload is not the "
                                                      f"confirmation's ({want})")  # fmt: skip
        plan = plan_of(q2m, source_dir, item.get("cells_file"))
        trials = sum(len(s["trials"]) for s in plan)
        _require(
            (w.get("sessions"), w.get("trials")) == (len(plan), trials) == (CONFIRM_REPS, trials),
            f"{cid}: one repetition per cold boot ({CONFIRM_REPS} boots)",
        )
        pairs = {c for s in plan for _, c in s["trials"]}
        _require(all({c for _, c in s["trials"]} == pairs and len(s["trials"]) == len(pairs)
                     for s in plan), f"{cid}: every boot runs every entry once")  # fmt: skip


def check_registered(m: Mapping[str, Any], source_dir: Path) -> None:
    """A k1 manifest runs the K1 plan's campaigns for its check and cell (``ap_delta``'s rule,
    under v5's run root): all of them, or one numbered part of a check too long for one job."""
    plan = D.load_k1_plan(source_dir)
    cells = "+".join(m["campaigns"][0]["cells"])
    for item in m["campaigns"]:
        _require(
            "+".join(item["cells"]) == cells,
            f"every campaign of a k1 job runs on {cells}, the first campaign's image",
        )
        _require(item["manifest"]["vm"]["qcow2"]["host_path"]
                 == m["campaigns"][0]["manifest"]["vm"]["qcow2"]["host_path"],
                 "every campaign of a k1 job mounts the first campaign's image")  # fmt: skip
    want = [
        {k: v for k, v in e.items() if k not in ("check", "cell")}
        for e in plan
        if e["check"] == m["check"] and e["cell"] == cells
    ]
    got = [D.campaign_key(item["manifest"]) for item in m["campaigns"]]
    _require(bool(want), f"the K1 plan has no {m['check']} campaigns on {cells}")
    part = m.get("part")
    if part is None:
        _require(D._canon(got) == D._canon(want),
                 f"{m['check']} on {cells}: the campaigns are not the K1 plan's")  # fmt: skip
    else:
        _require(isinstance(part, dict) and 1 <= int(part.get("index", 0)) <= int(
            part.get("of", 0)), "part: index of count")  # fmt: skip
        keys = [json.dumps(dict(w), sort_keys=True) for w in want]
        mine = [json.dumps(dict(g), sort_keys=True) for g in got]
        _require(
            len(set(mine)) == len(mine) and set(mine) <= set(keys),
            f"{m['check']} on {cells}: a part runs distinct campaigns of the K1 plan",
        )
        positions = [keys.index(k) for k in mine]
        _require(positions == sorted(positions), "a part keeps the plan's order")
    for item in m["campaigns"]:
        q2m = item["manifest"]
        _require(q2m.get("purpose") in ("acceptance", "infrastructure-validation"),
                 "a K1 campaign is a scored campaign")  # fmt: skip
        _require(str(q2m.get("run_root", "")).startswith(K1_ROOT),
                 f"a K1 campaign runs under {K1_ROOT}")  # fmt: skip


def check_slurm(m: Mapping[str, Any]) -> dict[str, int]:
    """CPUs, memory and minutes only (no other key, so no GPU can be requested); the minutes
    cover every campaign's q2 budget and its two image checks (``ap_delta.check_slurm``)."""
    slurm = m.get("slurm") or {}
    _require(set(slurm) == {"cpus", "memory_gb", "minutes"}, "slurm: cpus, memory_gb, minutes")
    try:
        return D.check_slurm(m)
    except D.DeltaError as exc:
        raise V5Error(str(exc)) from exc


def validate_manifest(raw: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    m = json.loads(json.dumps(raw))
    _require(m.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    _require(m.get("experiment_id") == EXPERIMENT_ID, f"experiment_id must be {EXPERIMENT_ID}")
    purpose = m.get("purpose")
    _require(purpose in PURPOSES, f"purpose must be one of {PURPOSES}")
    row = ledger_row(source_dir)
    check = m.get("check")
    if purpose == "development":
        _require(row is None, f"{EXPERIMENT_ID} is frozen: development no longer runs (D56)")
        _require(ledger_row(source_dir, V4_ID) is not None, f"v5 follows the frozen {V4_ID} (D94)")
        _require(check == CONFIRM, f"development runs only the confirmation ({CONFIRM})")
        root = CONFIRM_ROOT
    else:
        _require(row is not None, f"k1 runs only after the freeze (no ledger row for "
                                  f"{EXPERIMENT_ID})")  # fmt: skip
        try:
            L.check_export(m, source_dir, frozen_registration(source_dir))
        except L.LaneError as exc:
            raise V5Error(str(exc)) from exc
        _require(check in CHECKS, f"check must be one of {CHECKS}")
        root = K1_ROOT
    _require(isinstance(m.get("name"), str) and bool(SAFE.fullmatch(m["name"])), "unsafe name")
    _require(str(m.get("run_root", "")).startswith(root), f"run_root outside {root}")
    check_cells_files(source_dir)
    pins = L.load_pins(source_dir)
    campaigns = m.get("campaigns") or []
    _require(bool(campaigns), "no campaigns")
    sha_file = source_dir / ".git_sha"
    export_sha = sha_file.read_text(encoding="utf-8").strip() if sha_file.is_file() else None
    seen: set[str] = set()
    for item in campaigns:
        q2m = item.get("manifest") or {}
        cid = str(q2m.get("campaign_id"))
        _require(cid not in seen, f"campaign {cid} twice")
        seen.add(cid)
        cells = item.get("cells") or []
        _require(bool(cells) and all(c in K1_CELLS for c in cells), f"{cid}: cells")
        _require(set(item) <= {"cells", "manifest", "qcow2", "cells_file"}, f"{cid}: fields")
        _require(str(q2m.get("run_root", "")).startswith(root), f"{cid}: run_root outside {root}")
        w = q2m.get("workload") or {}
        rel = cells_file(cells[0], w.get("kind"))
        _require(
            item.get("cells_file") == rel,
            f"{cid}: the cells file on {cells[0]} is {rel or Q2_CELLS} (D96)",
        )
        if "cells_sha256" in w:
            _require(w["cells_sha256"] == cells_sha256(source_dir, rel),
                     f"{cid}: workload.cells_sha256 is not {rel or Q2_CELLS}'s")  # fmt: skip
        multi = D.is_rung(item)
        try:
            if multi:
                _require(purpose == "k1" and check == "rung" and len(campaigns) == 1,
                         "only the rung check runs a rung, as one campaign")  # fmt: skip
                _require(tuple(cells) == D.RUNG_CELLS,
                         f"the rung interleaves the five images {D.RUNG_CELLS}")  # fmt: skip
                _require(set(item.get("qcow2") or {}) == set(cells), f"{cid}: qcow2 per cell")
                for cell in cells:
                    D.check_image_entry(dict(q2m, vm=dict(q2m["vm"], qcow2=item["qcow2"][cell])),
                                        cell, pins)  # fmt: skip
                D.check_image_entry(q2m, cells[0], pins)
                D.check_rung(q2m, source_dir, purpose)
            else:
                _require(purpose == "development" or check != "rung",
                         "the rung check runs the rung")  # fmt: skip
                _require(len(cells) == 1, f"{cid}: a single-image campaign names one cell")
                D.check_image_entry(q2m, cells[0], pins)
                D.q2_validate(q2m, source_dir)
                _require(q2m["vm"]["concurrency"] == 1, f"{cid}: one VM at a time (section 7)")
        except D.DeltaError as exc:
            raise V5Error(str(exc)) from exc
        if export_sha is not None or purpose == "k1":
            _require(q2m.get("git_sha") == export_sha,
                     f"{cid}: git_sha is not the export's .git_sha")  # fmt: skip
    if purpose == "development":
        check_confirm(m, source_dir)
    else:
        check_registered(m, source_dir)
    check_slurm(m)
    return m


# --------------------------------------------------------------------------- run (in the job)


def q2_driver(argv: Sequence[str]) -> int:
    """harness/q2's ``driver.main``, unedited, reading ``--cells`` (a pinned v5 cells file) in
    place of q2's ``suite_cells.json``: its digest check, its session plan and every session's
    runner config (``"/src/" + driver.CELLS``) then name that file. The override is recorded in
    the run directory (``OVERRIDE_RECORD``) before the driver starts."""
    argv = list(argv)
    _require("--" in argv, "q2-driver --cells FILE -- DRIVER-ARGS")
    split = argv.index("--")
    own, rest = argv[:split], argv[split + 1 :]
    _require(len(own) == 2 and own[0] == "--cells", "q2-driver --cells FILE -- DRIVER-ARGS")
    rel = own[1]
    inner = argparse.ArgumentParser(add_help=False)
    inner.add_argument("--source-dir", required=True)
    inner.add_argument("--run-dir", type=Path, required=True)
    known, _ = inner.parse_known_args(rest)
    cell = next((c for c, path in CELLS_FILES.items() if path == rel), None)
    _require(cell is not None, f"--cells must be one of {sorted(CELLS_FILES.values())}")
    assert cell is not None
    digest = cells_sha256(Path(known.source_dir), rel)
    _require(digest == CELLS_SHA256[cell], f"{rel} is not the pinned v5 cells file")
    from harness.q2.vm import driver

    known.run_dir.mkdir(parents=True, exist_ok=True)
    (known.run_dir / OVERRIDE_RECORD).write_text(json.dumps(
        {"cell": cell, "cells": rel, "sha256": digest, "replaces": driver.CELLS},
        indent=1, sort_keys=True) + "\n", encoding="utf-8")  # fmt: skip
    driver.CELLS = rel
    return int(driver.main(rest) or 0)


def run_campaign(item: Mapping[str, Any], run_dir: Path, source_dir: Path, job_id: str,
                 timeout_s: float, stop: list[bool]) -> int:  # fmt: skip
    """One single-image campaign. With q2's cells file: ``ap_delta.run_campaign`` itself. With a
    v5 cells file: the same steps, with the driver started through ``q2-driver``."""
    rel = item.get("cells_file")
    q2m = item["manifest"]
    if rel is None:
        return D.run_campaign(q2m, run_dir, source_dir, job_id, timeout_s, stop)
    from harness.q2.vm.manifest import manifest_sha256

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(q2m, indent=2, sort_keys=True))
    D.write_preflight(run_dir, job_id, {"manifest_sha256": manifest_sha256(dict(q2m)),
                                        "ap_delta": "1", "cells": rel})  # fmt: skip
    argv = [sys.executable, "-E", "-s", "-m", "harness.s2_locale.ap_delta_v5", "q2-driver",
            "--cells", rel, "--", "--manifest", str(run_dir / "manifest.json"), "--run-dir",
            str(run_dir), "--source-dir", str(source_dir), "--job-id", job_id]  # fmt: skip
    proc = subprocess.Popen(argv, cwd=source_dir)
    try:
        rc = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGTERM)
        rc = proc.wait(timeout=120)
    if stop and stop[0] and rc == 0:
        rc = 143
    ids = D.docker("ps", "-aq", "--filter", f"label=cotcodec.slurm_job={job_id}").stdout.split()
    if ids:
        D.docker("rm", "--force", "--volumes", *ids, timeout=120)
    with (run_dir / "preflight.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"driver_exit={rc} labelled_containers_left={D.labelled_left(job_id)}\n")
    return rc


def run(m: Mapping[str, Any], run_dir: Path, source_dir: Path, job_id: str) -> dict[str, Any]:
    """Every campaign of the manifest, in order (``ap_delta.run``); a stop signal ends the job
    after the current campaign."""
    from harness.q2.vm.manifest import source_tree_sha256

    tree = source_tree_sha256(str(source_dir))
    for item in m["campaigns"]:
        source = item["manifest"]["source"]
        _require(source["host_dir"] == str(source_dir.resolve()) and source["tree_sha256"] == tree,
                 f"{item['manifest']['campaign_id']}: source is not this export")  # fmt: skip
    stop = [False]
    signal.signal(signal.SIGUSR1, lambda *_: stop.__setitem__(0, True))
    out: dict[str, Any] = {"schema": "s2v5-apdelta-receipt-v1", "job_id": job_id,
                           "experiment_id": EXPERIMENT_ID, "check": m["check"],
                           "purpose": m["purpose"], "part": m.get("part"), "campaigns": [],
                           "t_start": time.time()}  # fmt: skip
    for k, item in enumerate(m["campaigns"]):
        cid = item["manifest"]["campaign_id"]
        if stop[0]:
            out["campaigns"].append({"campaign_id": cid, "status": "not_started"})
            continue
        sub = run_dir / f"{k:02d}-{cid}"
        if D.is_rung(item):
            rc = D.run_rung(item, sub, source_dir, job_id)
        else:
            rc = run_campaign(item, sub, source_dir, job_id, 60.0 * D.campaign_minutes(
                item["manifest"], D.image_bytes({"campaigns": [item]})), stop)  # fmt: skip
        meta = {"check": m["check"], "cells": item["cells"]}
        if item.get("cells_file"):
            meta["cells_file"] = item["cells_file"]
        (sub / "apdelta.json").write_text(json.dumps(meta))
        out["campaigns"].append(
            {
                "campaign_id": cid,
                "dir": sub.name,
                "cells": item["cells"],
                "cells_file": item.get("cells_file"),
                "driver_exit": rc,
            }
        )
    out["t_end"] = time.time()
    sha = source_dir / ".git_sha"
    out["executor_commit"] = sha.read_text().strip() if sha.is_file() else None
    (run_dir / "apdelta-receipt.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    return out


# --------------------------------------------------------------------------- readings


def campaign_dirs(job_dirs: Sequence[Path]) -> list[tuple[Path, dict[str, Any]]]:
    """Every campaign run directory of the given job directories (``apdelta.json`` and
    ``manifest.json`` present), in job order, with its ``apdelta.json``."""
    out = []
    for job_dir in job_dirs:
        for sub in sorted(Path(job_dir).iterdir()):
            meta, man = sub / "apdelta.json", sub / "manifest.json"
            if meta.is_file() and man.is_file():
                out.append((sub, json.loads(meta.read_text(encoding="utf-8"))))
    return out


def cells_problems(sub: Path, meta: Mapping[str, Any], source_dir: Path) -> list[str]:
    """Whether a canary campaign ran with its image's cells file: the manifest's
    ``cells_sha256``, ``apdelta.json``'s ``cells_file`` and, for a v5 file, the override record
    the driver's wrapper wrote before the driver started."""
    q2m = json.loads((sub / "manifest.json").read_text(encoding="utf-8"))
    w = q2m.get("workload") or {}
    cell = meta["cells"][0]
    rel = cells_file(cell, w.get("kind"))
    out = []
    if meta.get("cells_file") != rel:
        out.append(f"{sub.name}: ran with {meta.get('cells_file') or Q2_CELLS}, not "
                   f"{rel or Q2_CELLS}")  # fmt: skip
    want = CELLS_SHA256[cell] if rel else cells_sha256(source_dir, None)
    if w.get("cells_sha256") != want:
        out.append(f"{sub.name}: workload.cells_sha256 is not {rel or Q2_CELLS}'s")
    record = sub / OVERRIDE_RECORD
    if rel:
        got = json.loads(record.read_text(encoding="utf-8")) if record.is_file() else {}
        if (got.get("cells"), got.get("sha256")) != (rel, want):
            out.append(f"{sub.name}: no override record naming {rel}")
    elif record.is_file():
        out.append(f"{sub.name}: an override record on a campaign that reads q2's cells")
    return out


def confirm_read(job_dirs: Sequence[Path], source_dir: Path) -> dict[str, Any]:
    """The development confirmation's reading (D96): every image of ``CONFIRM_PARTS`` ran once
    (one attempt), its campaign counts (harness/q2's ``counting_problems``), ran its plan, read
    its image's cells file, and passed every entry 5 of 5. Anything else is an honest exit."""
    from harness.q2.action_path import acceptance as A

    problems: list[str] = []
    by_cell: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for sub, meta in campaign_dirs(job_dirs):
        if meta.get("check") != CONFIRM:
            problems.append(f"{sub.name}: not a confirmation campaign ({meta.get('check')})")
            continue
        by_cell.setdefault(meta["cells"][0], []).append((sub, meta))
    per_cell: dict[str, Any] = {}
    for cell in [c for part in CONFIRM_PARTS for c in part]:
        runs = by_cell.get(cell) or []
        if len(runs) != 1:
            problems.append(f"{cell}: {len(runs)} campaigns (one attempt, exactly one)")
        if not runs:
            per_cell[cell] = {"pass": False, "ran": False}
            continue
        sub, meta = runs[-1]
        c = A.load(str(sub))
        mine = list(A.counting_problems(c)) + cells_problems(sub, meta, source_dir)
        q2m = c["manifest"]
        want_w = confirm_workload(cell)
        if {k: (q2m.get("workload") or {}).get(k) for k in want_w} != want_w:
            mine.append(f"{cell}: the workload is not the confirmation's")
        plan = plan_of(q2m, source_dir, cells_file(cell, want_w["kind"]))
        if A.realized(c) != A.expected(plan):
            mine.append(f"{cell}: the trials run ({len(A.realized(c))}) are not the plan "
                        f"({len(A.expected(plan))})")  # fmt: skip
        pairs = sorted({cell_id for s in plan for _, cell_id in s["trials"]})
        flags = A.outcomes([c])
        entries = {}
        for pair in pairs:
            values = [f for v in (flags.get(pair) or {}).values() for f in v]
            entries[pair] = {"passed": sum(values), "trials": len(values),
                             "status": A.entry_status(flags.get(pair) or {})}  # fmt: skip
            if entries[pair]["status"] != "PASS" or len(values) != CONFIRM_REPS:
                mine.append(f"{cell}: {pair} {sum(values)} of {len(values)} "
                            f"({entries[pair]['status']})")  # fmt: skip
        problems += mine
        per_cell[cell] = {"pass": not mine and len(runs) == 1, "ran": True, "job": c["job"],
                          "dir": sub.name, "cells_file": meta.get("cells_file") or Q2_CELLS,
                          "entries": len(entries),
                          "trials": sum(e["trials"] for e in entries.values()),
                          "passed": sum(e["passed"] for e in entries.values()),
                          "not_pass": {k: v for k, v in entries.items() if v["status"] != "PASS"
                                       or v["trials"] != CONFIRM_REPS},
                          "problems": mine}  # fmt: skip
    ok = not problems
    return {"schema": "s2v5-confirm-reading-v1", "experiment_id": EXPERIMENT_ID, "pass": ok,
            "decision": ("PROCEED to the pre-freeze audit (D96)" if ok
                         else "HONEST EXIT for S2 (D94, D96: v5 is S2's last registration)"),
            "per_cell": per_cell, "problems": problems}  # fmt: skip


def verdict(job_dirs: Sequence[Path], freeze_sha: str, source_dir: Path) -> dict[str, Any]:
    """K1 under v5: ``ap_delta.verdict`` (acceptance's own functions, the rung's step p95 per
    image), and, from each A6 run directory, that ER's and AR's campaigns read their v5 cells file
    and every other one q2's; a campaign that read another file did not run as registered, and K1
    is not read as passing."""
    out = D.verdict(job_dirs, freeze_sha)
    problems = [
        p
        for sub, meta in campaign_dirs(job_dirs)
        if meta.get("check") == "A6"
        for p in cells_problems(sub, meta, source_dir)
    ]
    out["schema"] = "s2v5-k1-verdict-v1"
    out["experiment_id"] = EXPERIMENT_ID
    out["a6_cells"] = {"pass": not problems, "problems": problems,
                       "files": {c: CELLS_FILES.get(c, Q2_CELLS) for c in K1_CELLS}}  # fmt: skip
    if problems:
        out["K1"] = "FAIL"
    return out


# --------------------------------------------------------------------------- render (Mac)


def confirm_campaign(args: argparse.Namespace, pins: Mapping[str, Any], cell: str
                     ) -> dict[str, Any]:  # fmt: skip
    """The confirmation's q2 canary-development campaign on ``cell`` (the shape of
    ``ap_delta_step0.canary_campaign``: the template's VM and runner pins)."""
    import yaml

    from harness.q2.vm.manifest import ledger_view, source_tree_sha256

    root = Path(__file__).resolve().parents[2]
    template = yaml.safe_load((root / TEMPLATE).read_text())
    source = Path(args.source_dir)
    rows = ledger_view(str(source), [])["rows"]
    rel = cells_file(cell, "canary-development")
    q2m: dict[str, Any] = {
        "schema": template["schema"], "name": "s2v5-confirm",
        "campaign_id": f"s2v5-confirm-{cell.lower()}", "experiment_id": "q2-action-path-v2",
        "purpose": "development",
        "preregistration": {"path": "program/preregistrations/q2-action-path-v2.md",
                            "status": "frozen", "sha256": rows["q2-action-path-v2"]["sha256"]},
        "git_sha": args.git_sha,
        "source": {"host_dir": f"{args.host_root}/src/{args.git_sha}",
                   "tree_sha256": source_tree_sha256(str(source))},
        "run_root": f"{args.host_root}/runs", "slurm": {},
        "container_profile": template["container_profile"],
        "model": {"kind": "none", "reason": "S2 v5's development confirmation of A6's targets "
                                            "per image; the action-path executor loads no model"},
        "randomness": {"contract": "seeded", "seeds": [42], "seed_binding": {"flag": "--seed"}},
        "vm": dict(copy.deepcopy(template["vm"]), concurrency=1),
        "runner": dict(template["runner"], cpus=1),
        "workload": dict(confirm_workload(cell), cells_sha256=cells_sha256(source, rel),
                         sessions=0, trials=0),
    }  # fmt: skip
    plan = plan_of(q2m, source, rel)
    w = q2m["workload"]
    w.update(sessions=len(plan), trials=sum(len(s["trials"]) for s in plan))
    budget = 600 + w["sessions"] * (w["boot_timeout_s"] + w["settle_timeout_s"] + 240)
    budget += w["trials"] * w["max_trial_s"]
    q2m["slurm"] = {"cpus": q2m["vm"]["cpu_cores"] + q2m["runner"]["cpus"],
                    "memory_gb": q2m["vm"]["memory_gb"] + 3,
                    "minutes": int(math.ceil(budget / 600) * 10)}  # fmt: skip
    item: dict[str, Any] = {
        "cells": [cell],
        "manifest": D.swap_disk(q2m, cell, pins, args.images_root),
    }
    if rel:
        item["cells_file"] = rel
    return item


def _job_slurm(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {"cpus": max(int(i["manifest"]["slurm"]["cpus"]) for i in items),
            "memory_gb": max(int(i["manifest"]["slurm"]["memory_gb"]) for i in items),
            "minutes": 10 + sum(D.campaign_minutes(i["manifest"], D.image_bytes(
                {"campaigns": [i]})) for i in items)}  # fmt: skip


def render_confirm(args: argparse.Namespace) -> list[dict[str, Any]]:
    """The confirmation's manifests, one per part of ``CONFIRM_PARTS``."""
    source = Path(args.source_dir)
    pins = L.load_pins(source)
    out = []
    for k, part in enumerate(CONFIRM_PARTS, 1):
        items = [confirm_campaign(args, pins, cell) for cell in part]
        m: dict[str, Any] = {"schema": SCHEMA, "experiment_id": EXPERIMENT_ID,
                             "purpose": "development", "check": CONFIRM,
                             "name": f"confirm-a6-v1-p{k}", "run_root": f"{args.host_root}/runs",
                             "part": {"index": k, "of": len(CONFIRM_PARTS)}, "campaigns": items,
                             "slurm": _job_slurm(items)}  # fmt: skip
        validate_manifest(m, source)
        out.append(m)
    return out


def render_k1(args: argparse.Namespace) -> list[dict[str, Any]]:
    """The ``k1`` manifests of one check on one cell (or the rung), from v5's freeze export, as
    ``ap_delta.render_k1`` renders v4's: the freeze commit checked with git, q2's renderer per
    campaign, numbered parts past one job's limit; A6 on ER and AR names its v5 cells file."""
    source = Path(args.source_dir)
    row = frozen_registration(source)
    try:
        L.check_freeze_commit(args.repo, args.git_sha, row)
    except L.LaneError as exc:
        raise V5Error(str(exc)) from exc
    pins = L.load_pins(source)
    plan = D.load_k1_plan(source)
    cells = list(D.RUNG_CELLS) if args.check == "rung" else [args.cell]
    key = "+".join(cells)
    entries = [e for e in plan if e["check"] == args.check and e["cell"] == key]
    _require(bool(entries), f"the K1 plan has no {args.check} campaigns on {key}")
    items = []
    for entry in entries:
        q2m = D.render_campaign(entry, cells[0], args, pins)
        q2m["name"] = "s2v5-k1"
        q2m["campaign_id"] = re.sub(r"^s2v4-k1-", "s2v5-k1-", q2m["campaign_id"])
        item: dict[str, Any] = {"cells": cells, "manifest": q2m}
        rel = cells_file(cells[0], q2m["workload"]["kind"])
        if rel:
            q2m["workload"]["cells_sha256"] = cells_sha256(source, rel)
            item["cells_file"] = rel
        if args.check == "rung":
            item["manifest"] = D.swap_disk(q2m, cells[0], pins, args.images_root)
            item["qcow2"] = {c: D.swap_disk(q2m, c, pins, args.images_root)["vm"]["qcow2"]
                             for c in cells}  # fmt: skip
        items.append(item)
    parts: list[list[dict[str, Any]]] = [[]]
    used = 10
    for item in items:
        need = D.campaign_minutes(item["manifest"], D.image_bytes({"campaigns": [item]}))
        if parts[-1] and used + need > D.MAX_JOB_MINUTES:
            parts.append([])
            used = 10
        parts[-1].append(item)
        used += need
    out = []
    for k, chunk in enumerate(parts, 1):
        name = f"k1-{args.check.lower()}-{key.replace('+', '').lower()}"
        m: dict[str, Any] = {
            "schema": SCHEMA, "experiment_id": EXPERIMENT_ID, "purpose": "k1",
            "name": (name if len(parts) == 1 else f"{name}-p{k}")[:60], "check": args.check,
            "run_root": f"{args.host_root}/runs", "campaigns": chunk,
            "freeze": {"commit": args.git_sha, "ledger_row_hash": row["hash"],
                       "git_head_at_freeze": row["git_head_at_freeze"]}}  # fmt: skip
        if len(parts) > 1:
            m["part"] = {"index": k, "of": len(parts)}
        if args.check == "rung":
            q2m = chunk[0]["manifest"]
            m["slurm"] = {"cpus": D.RUNG_N * q2m["vm"]["cpu_cores"] + q2m["runner"]["cpus"],
                          "memory_gb": D.RUNG_N * (q2m["vm"]["memory_gb"] + 1) + 2,
                          "minutes": _job_slurm(chunk)["minutes"]}  # fmt: skip
        else:
            m["slurm"] = _job_slurm(chunk)
        validate_manifest(m, source)
        out.append(m)
    return out


# --------------------------------------------------------------------------- submit (host)


def sbatch_argv(m: Mapping[str, Any], env: Mapping[str, str], batch: Path) -> list[str]:
    request = check_slurm(m)
    hours, mins = divmod(request["minutes"], 60)
    return ["sbatch", "--parsable", f"--cpus-per-task={request['cpus']}",
            f"--mem={request['memory_gb']}G", f"--time={hours:02d}:{mins:02d}:00",
            f"--job-name=s2v5-apd-{m['name']}"[:60],
            "--export=ALL," + ",".join(f"{k}={v}" for k, v in env.items()),
            str(batch)]  # fmt: skip


def check_cpu_only(argv: Sequence[str], batch_text: str) -> None:
    """The request names no GPU, and the batch file asks for none and refuses one."""
    joined = " ".join(argv).lower()
    _require(not any(w in joined for w in ("--gres", "--gpus", "gpu:")), "sbatch asks for a GPU")
    directives = [x for x in batch_text.splitlines() if x.startswith("#SBATCH")]
    _require(not any(("gres" in x.lower() or "gpu" in x.lower()) for x in directives),
             "the batch file asks for a GPU")  # fmt: skip
    _require("refusing to start VMs" in batch_text, "the batch file lacks the GPU refusal")


def submit(manifest_path: Path, source_dir: Path, dry_run: bool, must_end_before: str | None,
           no_e_deadline: bool = False) -> dict[str, Any]:  # fmt: skip
    """Validate, then (unless ``dry_run``) refuse a non-empty queue and a limit that ends after
    the next successor E session's earliest start (``must_end_before``; ``no_e_deadline`` only
    once no E session remains), write the manifest under the run root and ``sbatch`` it."""
    from harness.q2_stage1 import lane as s1a

    m = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), source_dir)
    request = check_slurm(m)
    text = L.canonical(m)
    digest = _sha256(text.encode())
    run_root = Path(m["run_root"])
    stored = run_root / "manifests" / f"{digest}.json"
    batch = source_dir / BATCH
    env = {
        "COTCODEC_S2V5_MANIFEST_PATH_HEX": str(stored).encode().hex(),
        "COTCODEC_S2V5_MANIFEST_SHA256": digest,
        "COTCODEC_BATCH_SHA256": s1a.sha256_file(batch),
        "COTCODEC_SOURCE_HOST_HEX": str(source_dir.resolve()).encode().hex(),
        "COTCODEC_SOURCE_TREE_SHA256": s1a.tree_sha256(source_dir),
        "COTCODEC_RUN_ROOT_HEX": str(run_root).encode().hex(),
    }
    argv = sbatch_argv(m, env, batch)
    check_cpu_only(argv, batch.read_text(encoding="utf-8"))
    out: dict[str, Any] = {"manifest_sha256": digest, "manifest": str(stored), "argv": argv}
    out.update(request)
    if dry_run:
        return out
    _require((must_end_before is not None) != bool(no_e_deadline),
             "pass exactly one of --must-end-before (the next E session's earliest start) and "
             "--no-e-deadline (no E session remains)")  # fmt: skip
    if must_end_before is not None:
        deadline = datetime.fromisoformat(str(must_end_before).replace("Z", "+00:00"))
        # timezone.utc, not datetime.UTC: the host's python3 is 3.10
        ends = datetime.now(timezone.utc).timestamp() + 60 * request["minutes"]  # noqa: UP017
        _require(ends < deadline.timestamp(), f"the job's limit would end after {must_end_before}")
    out["must_end_before"] = must_end_before
    queue = subprocess.run(["squeue", "-h", "-o", "%i"], capture_output=True, text=True,
                           timeout=60, check=True).stdout.split()  # fmt: skip
    _require(not queue, f"the queue is not empty ({len(queue)} jobs)")
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_text(text, encoding="utf-8")
    done = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=True)
    out["job_id"] = done.stdout.strip()
    return out


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["q2-driver"]:
        return q2_driver(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rc = sub.add_parser("render-cells", help="write the v5 cells files (CELLS_FILES)")
    rc.add_argument("--source-dir", type=Path, default=Path("."))
    rf = sub.add_parser("render-confirm", help="the confirmation's manifests (Mac; PyYAML)")
    rf.add_argument("--source-dir", type=Path, required=True, help="export of the code commit")
    rf.add_argument("--git-sha", required=True)
    rf.add_argument("--host-root", default=CONFIRM_ROOT)
    rf.add_argument("--images-root", default=IMAGES_ROOT)
    rf.add_argument("--out-dir", type=Path, required=True)
    rk = sub.add_parser("render", help="a K1 manifest for one check and cell (Mac; PyYAML)")
    rk.add_argument("check", choices=CHECKS)
    rk.add_argument("--cell", default=None, help="the cell image (not for the rung)")
    rk.add_argument("--source-dir", type=Path, required=True, help="export of the freeze commit")
    rk.add_argument("--git-sha", required=True)
    rk.add_argument("--repo", type=Path, default=Path("."))
    rk.add_argument("--host-root", default=K1_ROOT)
    rk.add_argument("--images-root", default=IMAGES_ROOT)
    rk.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("validate")
    v.add_argument("manifest", type=Path)
    v.add_argument("--source-dir", type=Path, default=Path("."))
    s = sub.add_parser("submit")
    s.add_argument("manifest", type=Path)
    s.add_argument("--source-dir", type=Path, default=Path("."))
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--must-end-before", help="the next successor E session's earliest start, UTC")
    s.add_argument("--no-e-deadline", action="store_true", help="no successor E session remains")
    r = sub.add_parser("run")
    r.add_argument("--manifest", type=Path, required=True)
    r.add_argument("--run-dir", type=Path, required=True)
    r.add_argument("--source-dir", type=Path, required=True)
    r.add_argument("--job-id", required=True)
    cr = sub.add_parser("confirm-read", help="the confirmation's reading from its job directories")
    cr.add_argument("jobs", type=Path, nargs="+")
    cr.add_argument("--source-dir", type=Path, default=Path("."))
    cr.add_argument("--out", type=Path, required=True)
    vd = sub.add_parser("verdict", help="K1 from the v5 ap_delta job directories")
    vd.add_argument("jobs", type=Path, nargs="+")
    vd.add_argument("--freeze-commit", required=True)
    vd.add_argument("--source-dir", type=Path, default=Path("."))
    vd.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "render-cells":
        for cell, rel in CELLS_FILES.items():
            path = args.source_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(render_cells(args.source_dir, cell))
            print(json.dumps({"cell": cell, "file": rel, "sha256": _sha256(path.read_bytes())}))
        return 0
    if args.command == "render-confirm":
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for m in render_confirm(args):
            out = args.out_dir / f"{m['name']}.json"
            out.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
            print(json.dumps({"out": out.name, "campaigns": len(m["campaigns"]),
                              **check_slurm(m)}))  # fmt: skip
        return 0
    if args.command == "render":
        manifests = render_k1(args)
        for m in manifests:
            out = (
                args.out
                if len(manifests) == 1
                else args.out.with_name(f"{args.out.stem}-p{m['part']['index']}{args.out.suffix}")
            )
            out.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
            print(json.dumps({"check": m["check"], "part": m.get("part"), "out": out.name,
                              "campaigns": len(m["campaigns"]), **check_slurm(m)}))  # fmt: skip
        return 0
    if args.command == "validate":
        m = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
        print(json.dumps({"ok": True, "check": m["check"], "campaigns": len(m["campaigns"]),
                          **check_slurm(m)}))  # fmt: skip
        return 0
    if args.command == "submit":
        out = submit(args.manifest, args.source_dir, args.dry_run, args.must_end_before,
                     args.no_e_deadline)  # fmt: skip
        print(json.dumps(out, indent=1))
        return 0
    if args.command == "confirm-read":
        out = confirm_read(args.jobs, args.source_dir)
        args.out.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
        print(json.dumps({"pass": out["pass"], "decision": out["decision"]}))
        return 0
    if args.command == "verdict":
        out = verdict(args.jobs, args.freeze_commit, args.source_dir)
        args.out.write_text(json.dumps(out, indent=1, sort_keys=True, default=str))
        print(json.dumps({"K1": out["K1"], "rung_qualifies": out["rung"]["qualifies"],
                          "a6_cells": out["a6_cells"]["pass"]}))  # fmt: skip
        return 0
    if not re.fullmatch(r"[1-9][0-9]{0,19}", args.job_id):
        raise SystemExit("job id must be numeric")
    m = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
    out = run(m, args.run_dir, args.source_dir, args.job_id)
    print(json.dumps({"campaigns": [(c["campaign_id"], c.get("driver_exit"))
                                    for c in out["campaigns"]]}))  # fmt: skip
    return 0 if all(c.get("driver_exit") == 0 for c in out["campaigns"]) else 3


if __name__ == "__main__":
    raise SystemExit(main())
