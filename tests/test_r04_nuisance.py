"""r04-checker-nuisance-invariance-v1: levels, profile edits, items, scorer helpers,
the registered analysis, the operating characteristics, the freeze guard and the image
recipes. Nothing here starts LibreOffice or OSWorld; the dev-split smoke runs on the host."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from harness.r04_nuisance import analysis, guard, items, levels, power, score, xcu
from harness.r04_nuisance import resave as rs

ROOT = Path(__file__).resolve().parents[1]

VM_XCU = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
<item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="FirstRun" oor:op="fuse"><value>false</value></prop></item>
<item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooLocale" oor:op="fuse"><value>en-US</value></prop></item>
<item oor:path="/org.openoffice.Setup/Product"><prop oor:name="ooSetupLastVersion" oor:op="fuse"><value>7.3</value></prop></item>
</oor:items>
"""  # noqa: E501


# --- levels ---------------------------------------------------------------------------------


def test_registered_cells_and_roles():
    cells = levels.registered_cells()
    ids = [c.id for c in cells]
    assert len(ids) == len(set(ids)) == 23
    roles = {c.id: c.role for c in cells}
    assert roles[levels.CONTROL_CELL] == "control"
    assert roles[levels.REPLICATE_CELL] == "validity"
    primary = [c for c in cells if c.role == "primary"]
    assert len(primary) == 11
    assert {c.arm for c in primary} == {"route", "build", "locale"}
    # every primary cell differs from the control in exactly one factor
    for c in primary:
        diffs = (c.build != "B0") + (c.route != "ctrl_s") + (c.locale != "L0")
        assert diffs == 1, c.id
    secondary = [c for c in cells if c.role == "secondary"]
    assert len(secondary) == 10 and all(c.build != "B0" and c.route != "ctrl_s" for c in secondary)
    # primary cells run before secondary ones
    order = [c.role for c in cells]
    assert max(i for i, r in enumerate(order) if r == "primary") < min(
        i for i, r in enumerate(order) if r == "secondary"
    )


def test_control_cell_changes_nothing():
    control = levels.get_cell(levels.CONTROL_CELL)
    assert levels.profile_overrides(control) == []
    assert levels.env_overrides(control, "/tmp/x") == {}
    assert levels.BUILD_BY_ID["B0"].soffice == "/usr/bin/soffice"


def test_build_and_locale_overrides():
    b3 = levels.get_cell("B3.ctrl_s.L0")
    assert levels.profile_overrides(b3) == [
        ("/org.openoffice.Setup/Product", "ooSetupLastVersion", "24.8")
    ]
    assert levels.profile_overrides(levels.get_cell("B1.ctrl_s.L0")) == []
    tr = levels.get_cell("B0.ctrl_s.L4")
    assert ("/org.openoffice.Setup/L10N", "ooSetupSystemLocale", "tr-TR") in (
        levels.profile_overrides(tr)
    )
    assert ("/org.openoffice.Setup/L10N", "ooLocale", "en-US") in levels.profile_overrides(tr)
    assert levels.env_overrides(tr, "/tmp/loc") == {
        "LANG": "tr_TR.UTF-8",
        "LC_ALL": "tr_TR.UTF-8",
        "LOCPATH": "/tmp/loc",
    }
    with pytest.raises(KeyError):
        levels.get_cell("B9.ctrl_s.L0")


def test_tdf_builds_are_pinned():
    tdf = [b for b in levels.BUILDS if b.source == "tdf"]
    assert [b.version for b in tdf] == ["7.3.7.2", "7.6.7.2", "24.8.7.2", "25.8.7.3", "26.2.6.2"]
    for b in tdf:
        assert len(b.tarball_sha256 or "") == 64 and (b.tarball_bytes or 0) > 1e8
        assert b.tarball_url and b.tarball_url.startswith(levels.TDF_ARCHIVE + "/" + b.version)
        assert b.soffice == f"/opt/libreoffice{b.series}/program/soffice"
        assert b.uno_python == "/usr/bin/python3"
    assert sum(b.tarball_bytes or 0 for b in tdf) < 1.1e9
    json.dumps(levels.describe())


def test_dockerfiles_are_rendered_from_levels():
    out = subprocess.run(
        [sys.executable, str(ROOT / "infra/r04-nuisance/render_dockerfiles.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    text = (ROOT / "infra/r04-nuisance/lo-tdf/B3/Dockerfile").read_text()
    assert f"FROM {levels.LO_VM_TAG}" in text
    assert "sha256sum -c" in text and "cmp /opt/r04/dpkg-before.tsv" in text
    assert "dpkg -i" not in text and "apt-get" not in text


# --- profile edits --------------------------------------------------------------------------


def test_xcu_set_props_replaces_and_appends():
    new = xcu.set_props(
        VM_XCU,
        [
            ("/org.openoffice.Setup/Product", "ooSetupLastVersion", "24.8"),
            ("/org.openoffice.Setup/L10N", "ooSetupSystemLocale", "de-DE"),
        ],
    )
    props = xcu.read_props(new)
    assert props[("/org.openoffice.Setup/Product", "ooSetupLastVersion")] == "24.8"
    assert props[("/org.openoffice.Setup/L10N", "ooSetupSystemLocale")] == "de-DE"
    assert props[("/org.openoffice.Setup/L10N", "ooLocale")] == "en-US"
    assert props[("/org.openoffice.Office.Common/Misc", "FirstRun")] == "false"
    assert new.count("ooSetupLastVersion") == 1
    assert new.rstrip().endswith("</oor:items>")
    assert xcu.set_props(VM_XCU, []) == VM_XCU


def test_xcu_rejects_non_profile_and_escapes():
    with pytest.raises(ValueError):
        xcu.set_props("<x/>", [("/a", "b", "c")])
    new = xcu.set_props(VM_XCU, [("/a", "b", "x<y&z")])
    assert "<value>x&lt;y&amp;z</value>" in new


def test_session_reset_applies_cell_profile(tmp_path):
    template = tmp_path / "template"
    template.mkdir()
    (template / "registrymodifications.xcu").write_text(VM_XCU)
    display = rs.R.Display(199, tmp_path / "wm")
    control = rs.NuisanceSession(
        display, tmp_path / "s0", levels.get_cell(levels.CONTROL_CELL), template, pipe="p"
    )
    control.reset()
    user = tmp_path / "s0" / "home" / ".config" / "libreoffice" / "4" / "user"
    assert (user / "registrymodifications.xcu").read_text() == VM_XCU
    assert control.env["LC_ALL"] == "en_US.UTF-8" and "LOCPATH" not in control.env
    de = rs.NuisanceSession(
        display,
        tmp_path / "s1",
        levels.get_cell("B0.ctrl_s.L1"),
        template,
        pipe="p",
        locpath="/tmp/loc",
    )
    de.reset()
    user = tmp_path / "s1" / "home" / ".config" / "libreoffice" / "4" / "user"
    props = xcu.read_props((user / "registrymodifications.xcu").read_text())
    assert props[("/org.openoffice.Setup/L10N", "ooSetupSystemLocale")] == "de-DE"
    assert de.env["LC_ALL"] == "de_DE.UTF-8" and de.env["LOCPATH"] == "/tmp/loc"
    assert de.profile_set and de.soffice == "/usr/bin/soffice"
    b5 = rs.NuisanceSession(
        display, tmp_path / "s2", levels.get_cell("B5.headless_convert.L0"), template, pipe="p"
    )
    assert b5.soffice == "/opt/libreoffice26.2/program/soffice"
    no_template = rs.NuisanceSession(
        display, tmp_path / "s3", levels.get_cell("B3.ctrl_s.L0"), None, pipe="p"
    )
    with pytest.raises(rs.CellError):
        no_template.reset()


def test_same_format_filters_cover_save_exposed_types():
    assert set(rs.SAME_FORMAT_FILTERS) == set(rs.R.LO_SAVE_EXTENSIONS)


# --- items ----------------------------------------------------------------------------------


def _write_episode(
    run: Path,
    slot: str,
    attempt: int,
    task: str,
    files: dict[str, bytes],
    score_value: float,
    cache: dict[str, bytes] | None = None,
) -> dict:
    record = {
        "slot": slot,
        "attempt": attempt,
        "task_id": task,
        "status": "scored",
        "score": score_value,
        "job": "A0a",
    }
    ep = items.episode_dir(run, record) / "capture"
    vm = {}
    for path, data in files.items():
        target = ep / "vm" / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        vm[path] = hashlib.sha256(data).hexdigest()
    cache_digests = {}
    for rel, data in (cache or {}).items():
        target = ep / "cache" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        cache_digests[rel] = hashlib.sha256(data).hexdigest()
    state = hashlib.sha256(
        json.dumps({"vm": vm, "cache": cache_digests}, sort_keys=True).encode()
    ).hexdigest()
    manifest = {
        "vm_files": vm,
        "cache_files": cache_digests,
        "state_sha256": state,
        "action_history": ["DONE"],
    }
    (ep / "capture.json").write_text(json.dumps(manifest))
    return record


def test_s1a_states_dedupe_and_populations(tmp_path):
    run = tmp_path / "1037"
    records = [
        _write_episode(run, "A0a:a:000", 1, "t1", {"/home/user/a.xlsx": b"A"}, 1.0),
        _write_episode(run, "A0a:a:001", 1, "t1", {"/home/user/a.xlsx": b"A"}, 1.0),
        _write_episode(run, "A0a:a:002", 1, "t1", {"/home/user/a.xlsx": b"B"}, 0.0),
        _write_episode(run, "A0a:a:003", 1, "t2", {"/home/user/b.docx": b"C"}, 1.0),
        _write_episode(run, "A0a:a:004", 1, "t2", {"/home/user/b.docx": b"C"}, 0.0),
        _write_episode(run, "A0a:a:005", 1, "t3", {"/home/user/c.txt": b"D"}, 1.0),
    ]
    (run / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    splits = {"dev": ["t1", "t2", "t3"], "confirm": [], "reserve": []}
    states = items.s1a_states({"1037": run}, splits)
    assert len(states) == 3  # the .txt-only state is not save-exposed
    pops = sorted(s["population"] for s in states)
    assert pops == ["s1a_fail", "s1a_mixed", "s1a_pass"]
    passed = next(s for s in states if s["population"] == "s1a_pass")
    assert len(passed["episodes"]) == 2 and passed["split"] == "dev"
    assert passed["files"]["/home/user/a.xlsx"].endswith("vm/home/user/a.xlsx")
    built, report = items.s1a_items(states)
    assert report["items"] == 3 and len({i["item_id"] for i in built}) == 3
    assert all(i["item_id"] == i["job_id"] == i["mutant_id"] for i in built)


def test_fail_state_sample_is_seeded_and_capped():
    states = [{"task_id": f"t{i % 2}", "state_sha256": f"{i:064x}"} for i in range(10)]
    first = items.sample_fail_states(states)
    assert first == items.sample_fail_states(list(reversed(states)))
    assert len(first) == 2 * items.FAIL_PER_TASK


def test_population_of():
    assert items.population_of([1.0, 1]) == "s1a_pass"
    assert items.population_of([0.0]) == "s1a_fail"
    assert items.population_of([0.5]) == "s1a_mixed"
    assert items.population_of([1.0, 0.0]) == "s1a_mixed"


# --- scorer helpers -------------------------------------------------------------------------


def test_derived_capture_keeps_cache_and_updates_digests(tmp_path):
    run = tmp_path / "run"
    rec = _write_episode(
        run,
        "A0a:a:000",
        1,
        "t1",
        {"/home/user/a.xlsx": b"A", "/home/user/n.json": b"{}"},
        1.0,
        cache={"a.xlsx": b"A"},
    )
    capture = items.episode_dir(run, rec) / "capture"
    manifest = json.loads((capture / "capture.json").read_text())
    item = {"capture_dir": str(capture), "state_sha256": manifest["state_sha256"]}
    saved = tmp_path / "saved.xlsx"
    saved.write_bytes(b"A-resaved")
    merged = {
        "/home/user/a.xlsx": str(saved),
        "/home/user/n.json": str(capture / "vm/home/user/n.json"),
    }
    dest = score.derived_capture(item, merged, tmp_path / "derived")
    new = json.loads((dest / "capture.json").read_text())
    assert new["vm_files"]["/home/user/a.xlsx"] == hashlib.sha256(b"A-resaved").hexdigest()
    assert new["cache_files"] == manifest["cache_files"]
    assert (dest / "cache" / "a.xlsx").read_bytes() == b"A"
    assert new["action_history"] == ["DONE"] and new["r04_derived_from"] == item["state_sha256"]
    assert new["state_sha256"] != manifest["state_sha256"]


def test_scorer_small_helpers(tmp_path):
    assert score.verdict_of(1.0, None) == "pass"
    assert score.verdict_of(0.5, None) == "fail"
    assert score.verdict_of(None, "boom") == "error"
    assert score.remap_path("/out/B0/files/x", {"/out/": "/ro/saves/"}) == "/ro/saves/B0/files/x"
    assert score.remap_path(None, {}) is None
    cell = tmp_path / "cell"
    cell.mkdir()
    row = {"job_id": "g:t", "task_id": "t", "events": [{"stdout_tail": "secret"}]}
    (cell / "reachability-0.jsonl").write_text(json.dumps(row) + "\n")
    (cell / "reachability-1.jsonl").write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError):
        score.load_cell_rows(cell)
    summary = score.save_summary({**row, "saves": [], "plan": {"unemulated": []}})
    assert "events" not in summary and "secret" not in json.dumps(summary)


# --- analysis -------------------------------------------------------------------------------


def _items(n_gold=10, s1a_tasks=4):
    out = [
        {"item_id": f"g:{i}", "task_id": f"tg{i}", "population": "gold", "split": "confirm"}
        for i in range(n_gold)
    ]
    for t in range(s1a_tasks):
        for k in range(2):
            out.append(
                {
                    "item_id": f"s:{t}:{k}",
                    "task_id": f"ts{t}",
                    "population": "s1a_pass",
                    "split": "confirm",
                }
            )
    return out


def _row(iid, cell, v, status="scored", funcs=("compare_table",)):
    res = {"verdict": v, "nondeterministic": False, "infra_failed": False}
    return {
        "item_id": iid,
        "cell": cell,
        "status": status,
        "pinned": res,
        "zinv": dict(res),
        "checker_funcs": list(funcs),
        "save": {"saves": []},
    }


def _scores(its, cells, flips=None, status=None):
    flips = flips or {}
    status = status or {}
    out = {}
    for cell in cells:
        rows = []
        for it in its:
            v = "pass"
            if it["item_id"] in flips.get(cell, ()):
                v = "fail"
            rows.append(
                _row(it["item_id"], cell, v, status.get(cell, {}).get(it["item_id"], "scored"))
            )
        out[cell] = rows
    return out


PRIMARY = [c.id for c in levels.registered_cells() if c.role in ("control", "validity", "primary")]


def test_analysis_invariant_minor_drift_and_confirmation():
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0", "g:1", "g:2"}, "B0.ctrl_s.L1": {"s:0:0"}}
    scores = _scores(its, ["raw", *PRIMARY], flips)
    rounds = [_scores(its, [levels.CONTROL_CELL, "B3.ctrl_s.L0", "B0.ctrl_s.L1"], flips)] * 2
    ref = {f"tg{i}": "pass" for i in range(10)}
    out = analysis.analyze(its, scores, rounds=rounds, reference=ref)
    cells = out["pinned"]["cells"]
    assert cells["B3.ctrl_s.L0"]["reading"] == "DRIFT"
    assert cells["B3.ctrl_s.L0"]["gold"]["confirmed"] == 3
    assert cells["B0.ctrl_s.L1"]["reading"] == "MINOR"
    assert cells["B0.store_as.L0"]["reading"] == "INVARIANT"
    assert out["validity"]["V1"]["status"] == "pass"
    assert out["validity"]["V2"]["status"] == "pass"
    assert out["pinned"]["arms"]["build"]["reading"] == "DRIFT"
    assert out["pinned"]["arms"]["locale"]["reading"] == "MINOR"
    assert out["pinned"]["arms"]["route"]["reading"] == "INVARIANT"
    assert cells["B3.ctrl_s.L0"]["flips_against_raw"] == ["g:0", "g:1", "g:2"]


def test_unconfirmed_discordance_is_unstable_not_a_finding():
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0", "g:1", "g:2"}}
    scores = _scores(its, [*PRIMARY], flips)
    # round 2 does not reproduce two of the three
    rounds = [
        _scores(its, [levels.CONTROL_CELL, "B3.ctrl_s.L0"], flips),
        _scores(its, [levels.CONTROL_CELL, "B3.ctrl_s.L0"], {"B3.ctrl_s.L0": {"g:0"}}),
    ]
    out = analysis.analyze(its, scores, rounds=rounds, reference={})
    gold = out["pinned"]["cells"]["B3.ctrl_s.L0"]["gold"]
    assert gold["confirmed"] == 1 and gold["unstable"] == 2
    assert out["pinned"]["cells"]["B3.ctrl_s.L0"]["reading"] == "MINOR"


def test_pending_without_rounds_and_invalid_on_replicate_drift():
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0"}}
    out = analysis.analyze(its, _scores(its, PRIMARY, flips), reference=None)
    assert out["pinned"]["cells"]["B3.ctrl_s.L0"]["reading"] == "PENDING"
    assert out["validity"]["V1"]["status"] == "not_checked"
    assert "pending" in out["pinned"]["arms"]["route"]["reading"]
    flips = {levels.REPLICATE_CELL: {"g:4"}}
    rounds = [_scores(its, [levels.CONTROL_CELL, levels.REPLICATE_CELL], flips)] * 2
    out = analysis.analyze(its, _scores(its, PRIMARY, flips), rounds=rounds, reference={})
    assert out["validity"]["V2"]["status"] == "fail"
    assert out["pinned"]["arms"]["build"]["reading"] == "INVALID"


def test_retention_drops_builds_and_build_arm_needs_two():
    its = _items()
    status = {}
    for b in ("B1", "B2", "B3", "B4"):
        status[f"{b}.ctrl_s.L0"] = {it["item_id"]: "save_failed" for it in its[:3]}
    ref = {f"tg{i}": "pass" for i in range(10)}
    out = analysis.analyze(its, _scores(its, PRIMARY, status=status), reference=ref)
    cells = out["pinned"]["cells"]
    assert cells["B1.ctrl_s.L0"]["reading"] == "NOT_EVALUABLE"
    assert cells["B5.ctrl_s.L0"]["reading"] == "INVARIANT"
    assert out["builds_retained"]["B5"] and not out["builds_retained"]["B1"]
    assert out["pinned"]["arms"]["build"]["reading"] == "NOT_EVALUABLE"
    assert out["validity"]["V1"]["status"] == "pass"


def test_task_level_s1a_count_and_v1_difference_limit():
    its = _items(s1a_tasks=4)
    flips = {"B0.headless_convert.L0": {"s:0:0", "s:0:1", "s:1:0", "s:2:1"}}
    rounds = [_scores(its, [levels.CONTROL_CELL, "B0.headless_convert.L0"], flips)] * 2
    ref = {f"tg{i}": "pass" for i in range(10)}
    ref["tg0"] = ref["tg1"] = "fail"
    out = analysis.analyze(its, _scores(its, PRIMARY, flips), rounds=rounds, reference=ref)
    s1a = out["pinned"]["cells"]["B0.headless_convert.L0"]["s1a"]["s1a_pass"]
    assert s1a["confirmed"] == 4 and s1a["confirmed_tasks"] == ["ts0", "ts1", "ts2"]
    assert out["pinned"]["cells"]["B0.headless_convert.L0"]["reading"] == "DRIFT"
    assert out["validity"]["V1"]["status"] == "fail"  # two differences > 1
    assert out["pinned"]["arms"]["route"]["reading"] == "INVALID"


def test_analysis_scope_is_the_registered_splits():
    its = _items()
    for it in its[:5]:
        it["split"] = "dev"
    out = analysis.analyze(its, _scores(its, PRIMARY), reference={})
    assert out["items"] == len(its) - 5
    dev = analysis.analyze(its, _scores(its, PRIMARY), reference={}, splits=("dev",))
    assert dev["items"] == 5


# --- operating characteristics --------------------------------------------------------------


def test_power_exact_gold_probabilities():
    null = power.gold_probs(0.0, 0.0)
    assert null["drift"] == 0.0 and null["zero"] == 1.0
    p5 = power.gold_probs(0.05, 0.0)
    assert 0.83 < p5["drift"] < 0.86
    noisy = power.gold_probs(0.0, 0.05)
    assert noisy["drift"] < 1e-4
    assert 0.03 < power.rate_for_power(0.8) < 0.05
    # exact Poisson-binomial over the 32 S1a tasks
    assert power.task_counts(0.0, 0.5, 0.0) == [1.0, 0.0, 0.0]
    assert abs(sum(power.poisson_binomial([0.1, 0.5, 0.9])) - 1.0) < 1e-12
    oc = power.cell_oc(0.05, 0.10, 0.5, 0.0)
    assert abs(oc["p_invariant"] + oc["p_minor"] + oc["p_drift"] - 1.0) < 1e-12


def test_power_run_is_deterministic_and_committed():
    a = power.run()
    assert a["grid"] == power.run()["grid"]
    committed = ROOT / "program/evidence/2026-10-11/r04-nuisance/power.json"
    assert json.loads(committed.read_text())["grid"] == json.loads(json.dumps(a["grid"]))
    assert sum(power.S1A_PASS_STATES_PER_TASK) == 270 and a["s1a_pass_tasks"] == 32
    assert a["familywise_under_null"]["0.0"]["false_drift_any_of_11"] == 0.0


# --- freeze guard ---------------------------------------------------------------------------


def test_guard_allows_dev_and_refuses_unfrozen_splits(tmp_path, monkeypatch):
    assert guard.require_split_allowed("dev", tmp_path) is None
    (tmp_path / "program" / "preregistrations").mkdir(parents=True)
    (tmp_path / guard.LEDGER_PATH).write_text("")
    with pytest.raises(guard.GuardError):
        guard.require_split_allowed("confirm", tmp_path)
    prereg = tmp_path / levels.PREREG_PATH
    prereg.write_text('x\n```json\n{\n "r04_pins": 1,\n "images": {"B0": "sha256:a"}\n}\n```\n')
    body = {
        "experiment_id": levels.EXPERIMENT_ID,
        "path": levels.PREREG_PATH,
        "sha256": hashlib.sha256(prereg.read_bytes()).hexdigest(),
        "previous_hash": guard.GENESIS,
    }
    body["hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (tmp_path / guard.LEDGER_PATH).write_text(json.dumps(body) + "\n")
    with pytest.raises(guard.GuardError, match="R04_PREREG_FROZEN"):
        guard.require_split_allowed("confirm", tmp_path)
    monkeypatch.setenv("R04_PREREG_FROZEN", levels.EXPERIMENT_ID)
    assert guard.require_split_allowed("confirm", tmp_path, {"B0": "sha256:a"})["hash"]
    with pytest.raises(guard.GuardError, match="pins"):
        guard.require_split_allowed("confirm", tmp_path, {"B0": "sha256:b"})
    prereg.write_text("changed")
    with pytest.raises(guard.GuardError, match="differs"):
        guard.require_split_allowed("confirm", tmp_path)


def test_frozen_mutation_study_code_is_untouched():
    """R04 must not change the checker-mutation study's pinned code tree."""
    changed = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            "--name-only",
            "main",
            "--",
            "harness/q2_mutation",
            "infra/q2-mutation",
            "infra/slurm/host-single-node/q2-mutation-cpu.sbatch",
            "harness/q2_stage1",
        ],
        capture_output=True,
        text=True,
    )
    if changed.returncode != 0:
        pytest.skip("no main branch to compare with")
    assert changed.stdout.strip() == ""


def test_registration_pins_match_the_code():
    text = (ROOT / levels.PREREG_PATH).read_text()
    assert "Status: DRAFT" in text
    pins = guard.prereg_pins(text)
    assert pins["experiment_id"] == levels.EXPERIMENT_ID
    assert pins["images"]["B0"] == levels.LO_VM_IMAGE_ID
    assert sorted(pins["images"]) == [b.id for b in levels.BUILDS]
    assert pins["metric_image_id"] == levels.METRIC_IMAGE_ID
    assert pins["drift_min"] == analysis.DRIFT_MIN == power.DRIFT_MIN
    assert pins["retention_min"] == analysis.RETENTION_MIN
    assert pins["confirm_rounds"] == analysis.CONFIRM_ROUNDS
    splits = ROOT / "program/evidence/q2-mutation/splits.json"
    assert hashlib.sha256(splits.read_bytes()).hexdigest() == pins["splits_sha256"]


def test_activation_falls_back_to_the_em_dash_title(tmp_path, monkeypatch):
    seen = []

    def fake_activate(self, title, strict):
        seen.append(title)
        return "—" in title

    monkeypatch.setattr(rs.R.LoSession, "activate", fake_activate)
    session = rs.NuisanceSession(
        rs.R.Display(198, tmp_path),
        tmp_path / "s",
        levels.get_cell("B3.ctrl_s.L0"),
        None,
        pipe="p",
    )
    session.log = []
    assert session.activate("a.xlsx - LibreOffice Calc", True)
    assert seen == ["a.xlsx - LibreOffice Calc", "a.xlsx — LibreOffice Calc"]
    assert session.activations_adapted == ["a.xlsx - LibreOffice Calc"]
    seen.clear()
    assert not session.activate("Untitled window", True)
    assert seen == ["Untitled window"]

    monkeypatch.setattr(rs.R.LoSession, "activate", lambda self, title, strict: True)
    session.activations_adapted = []
    assert session.activate("a.xlsx - LibreOffice Calc", True)
    assert session.activations_adapted == []


def test_capture_verification_against_committed_digests(tmp_path):
    run = tmp_path / "1037"
    rec = _write_episode(
        run, "A0a:a:000", 1, "t1", {"/home/user/a.xlsx": b"A"}, 1.0, cache={"a.xlsx": b"A"}
    )
    capture = items.episode_dir(run, rec) / "capture"
    lines = []
    for path in sorted(capture.rglob("*")):
        if path.is_file():
            lines.append(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  ./"
                f"{path.relative_to(run).as_posix()}"
            )
    sums_path = tmp_path / "sums.txt"
    sums_path.write_text("\n".join(lines) + "\n")
    sums = items.read_sums(sums_path)
    assert items.verify_capture(run, capture, sums) == 3
    (capture / "vm/home/user/a.xlsx").write_bytes(b"tampered")
    with pytest.raises(items.CaptureMismatch):
        items.verify_capture(run, capture, sums)
    (capture / "vm/home/user/a.xlsx").unlink()
    with pytest.raises(items.CaptureMismatch):
        items.verify_capture(run, capture, sums)
    assert set(items.SPLIT_RUNS["confirm"]) | set(items.SPLIT_RUNS["dev"]) == set(items.S1A_RUNS)
    for _job, _digest, path in items.S1A_RUNS.values():
        assert (ROOT / path).is_file()
