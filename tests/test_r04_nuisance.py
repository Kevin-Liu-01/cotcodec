"""r04-checker-nuisance-invariance-v1: levels, profile edits, items, scorer helpers,
the registered analysis, the operating characteristics, the freeze guard and the image
recipes. Nothing here starts LibreOffice or OSWorld; the dev-split smoke runs on the host."""

from __future__ import annotations

import hashlib
import json
import shutil
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
        assert b.uno_python == f"/opt/libreoffice{b.series}/program/python"
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


def test_score_rows_carry_the_save_outcome_and_read_each_cell_where_it_was_saved(tmp_path):
    assert score.cell_prefix("/out", "B4.ctrl_s.L0", "/ro/saves/B4/B4.ctrl_s.L0") == {
        "/out/B4.ctrl_s.L0/": "/ro/saves/B4/B4.ctrl_s.L0/"
    }
    prefix = score.cell_prefix("/out", "B4.ctrl_s.L0", "/ro/saves/B4.a2/B4.ctrl_s.L0")
    assert (
        score.remap_path("/out/B4.ctrl_s.L0/files/g:t/home/user/a.xlsx", prefix)
        == "/ro/saves/B4.a2/B4.ctrl_s.L0/files/g:t/home/user/a.xlsx"
    )
    assert score.remap_path("/cache/a.xlsx", prefix) == "/cache/a.xlsx"
    gold = tmp_path / "a.xlsx"
    gold.write_bytes(b"x")
    item = {"job_id": "g:t", "mutant_id": "g:t", "task_id": "t",
            "files": {"/home/user/a.xlsx": str(gold)}}  # fmt: skip
    assert score.save_status(item, None) == "no_lo_row"
    assert score.save_status(item, {"job_id": "g:t", "infra_error": "boom"}) == "infra_error"


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


def _row(iid, cell, v, status="scored", funcs=("compare_table",), **extra):
    res = {"verdict": v, "nondeterministic": False, "infra_failed": False}
    return {
        "item_id": iid,
        "cell": cell,
        "status": status,
        "pinned": res,
        "zinv": dict(res),
        "checker_funcs": list(funcs),
        "save": {"saves": []},
        "office_sha256": {"/home/user/a.xlsx": f"{cell}:{iid}"},
        **extra,
    }


def _scores(its, cells, flips=None, status=None, funcs=None):
    flips = flips or {}
    status = status or {}
    funcs = funcs or {}
    out = {}
    for cell in cells:
        rows = []
        for it in its:
            v = "pass"
            if it["item_id"] in flips.get(cell, ()):
                v = "fail"
            rows.append(
                _row(
                    it["item_id"],
                    cell,
                    v,
                    status.get(cell, {}).get(it["item_id"], "scored"),
                    funcs.get(it["item_id"], ("compare_table",)),
                )
            )
        out[cell] = rows
    return out


ALL = [levels.RAW, *[c.id for c in levels.registered_cells()]]
REF = {f"tg{i}": "pass" for i in range(10)}


def analyze_fast(its, scores, **kwargs):
    kwargs.setdefault("reference", REF)
    kwargs.setdefault("splits", ("confirm", "reserve"))
    return analysis.analyze(its, scores, n_boot=200, **kwargs)


def _rounds(its, cells, flips):
    return [_scores(its, [levels.CONTROL_CELL, *cells], flips)] * 2


def test_analysis_invariant_minor_drift_and_confirmation():
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0", "g:1", "g:2"}, "B0.ctrl_s.L1": {"s:0:0"}}
    scores = _scores(its, ALL, flips)
    out = analyze_fast(its, scores, rounds=_rounds(its, ["B3.ctrl_s.L0", "B0.ctrl_s.L1"], flips))
    cells = out["pinned"]["cells"]
    assert cells["B3.ctrl_s.L0"]["reading"] == "DRIFT"
    assert cells["B3.ctrl_s.L0"]["gold"]["confirmed"] == 3
    assert cells["B0.ctrl_s.L1"]["reading"] == "MINOR"
    assert cells["B0.store_as.L0"]["reading"] == "INVARIANT"
    assert out["validity"]["V1"]["status"] == "pass"
    assert out["validity"]["V2"]["status"] == "pass"
    assert out["validity"]["control_retained"]["status"] == "pass"
    assert out["pinned"]["arms"]["build"]["reading"] == "DRIFT"
    assert out["pinned"]["arms"]["locale"]["reading"] == "MINOR"
    assert out["pinned"]["arms"]["route"]["reading"] == "INVARIANT"
    assert cells["B3.ctrl_s.L0"]["flips_against_raw"] == ["g:0", "g:1", "g:2"]
    assert out["complete"] and out["vm_fidelity"]["label"] == analysis.K2_UNVERIFIED
    assert "Kevin" in out["warning"] and "R03 (b)" in out["warning"]
    # every discordance carries the control's and the cell's office digests
    disc = cells["B3.ctrl_s.L0"]["gold"]["discordances"][0]
    assert disc["control_office_sha256"] == {"/home/user/a.xlsx": "B0.ctrl_s.L0:g:0"}
    assert disc["cell_office_sha256"] == {"/home/user/a.xlsx": "B3.ctrl_s.L0:g:0"}


def test_unconfirmed_discordance_is_unstable_not_a_finding():
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0", "g:1", "g:2"}}
    scores = _scores(its, ALL, flips)
    # round 2 does not reproduce two of the three
    rounds = [
        _scores(its, [levels.CONTROL_CELL, "B3.ctrl_s.L0"], flips),
        _scores(its, [levels.CONTROL_CELL, "B3.ctrl_s.L0"], {"B3.ctrl_s.L0": {"g:0"}}),
    ]
    out = analyze_fast(its, scores, rounds=rounds)
    gold = out["pinned"]["cells"]["B3.ctrl_s.L0"]["gold"]
    assert gold["confirmed"] == 1 and gold["unstable"] == 2
    assert out["pinned"]["cells"]["B3.ctrl_s.L0"]["reading"] == "MINOR"
    assert not out["pinned"]["cells"]["B3.ctrl_s.L0"]["harness_noise"]


def test_missing_round_rows_stay_pending_never_invariant():
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0"}}
    # both rounds ran, but neither has a row for B3 (its round job ended without output)
    rounds = [_scores(its, [levels.CONTROL_CELL], {})] * 2
    out = analyze_fast(its, _scores(its, ALL, flips), rounds=rounds)
    cell = out["pinned"]["cells"]["B3.ctrl_s.L0"]
    assert cell["gold"]["pending"] == 1 and cell["reading"] == "PENDING"
    assert out["pinned"]["arms"]["build"]["reading"] == "PENDING"
    assert not out["complete"]


def test_pending_without_rounds_marks_every_reading_and_replicate_drift_is_invalid():
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0"}, levels.REPLICATE_CELL: {"g:5"}}
    out = analyze_fast(its, _scores(its, ALL, flips))
    assert out["confirmation_rounds"] == 0 and not out["complete"]
    assert out["validity"]["V2"]["status"] == "pending"
    cells = out["pinned"]["cells"]
    assert cells["B3.ctrl_s.L0"]["reading"] == "PENDING (validity gate pending)"
    assert cells["B0.store_as.L0"]["reading"] == "INVARIANT (validity gate pending)"
    assert cells["B0.store_as.L0"]["reading_before_gates"] == "INVARIANT"
    assert out["pinned"]["arms"]["route"]["reading"] == "INVARIANT (validity gate pending)"
    flips = {levels.REPLICATE_CELL: {"g:4"}, "B3.ctrl_s.L0": {"g:1"}}
    rounds = _rounds(its, [levels.REPLICATE_CELL, "B3.ctrl_s.L0"], flips)
    out = analyze_fast(its, _scores(its, ALL, flips), rounds=rounds)
    assert out["validity"]["V2"]["status"] == "fail"
    # a failed gate overwrites the cell readings as well as the arm readings
    assert out["pinned"]["cells"]["B3.ctrl_s.L0"]["reading"] == "INVALID"
    assert out["pinned"]["cells"]["B3.ctrl_s.L0"]["reading_before_gates"] == "MINOR"
    assert out["pinned"]["arms"]["build"]["reading"] == "INVALID"


def test_a_cell_without_scores_is_refused_unless_named_with_its_reason():
    its = _items()
    scores = _scores(its, ALL)
    for cid in ("B4.ctrl_s.L0", "B0.ctrl_s.L1"):
        del scores[cid]
    with pytest.raises(analysis.AnalysisError, match="neither scored nor named"):
        analyze_fast(its, scores)
    errors = {"B4.ctrl_s.L0": "score job failed 3 times", "B0.ctrl_s.L1": "cap"}
    out = analyze_fast(its, scores, cell_errors=errors)
    cell = out["pinned"]["cells"]["B4.ctrl_s.L0"]
    assert (
        cell["reading"] == "NOT_EVALUABLE" and cell["not_scored_reason"] == errors["B4.ctrl_s.L0"]
    )
    assert out["cells_not_scored"] == dict(sorted(errors.items()))
    assert out["pinned"]["arms"]["build"]["cells"]["B4.ctrl_s.L0"] == "NOT_EVALUABLE"
    # a reason may not knock out a cell that was scored
    with pytest.raises(analysis.AnalysisError, match="only cells without scores"):
        analyze_fast(its, _scores(its, ALL), cell_errors={"B3.ctrl_s.L0": "x"})
    with pytest.raises(analysis.AnalysisError, match="unregistered"):
        analyze_fast(its, {**_scores(its, ALL), "B9.ctrl_s.L0": []})


def test_the_audit_case_fails_closed_on_the_committed_smoke(tmp_path):
    """Score files removed from dev-smoke-v3 no longer turn the build and locale arms
    INVARIANT: the analysis refuses."""
    smoke = ROOT / "program/evidence/2026-10-11/r04-nuisance/dev-smoke-v3"
    scores = tmp_path / "scores"
    shutil.copytree(smoke / "scores", scores)
    for cid in ("B4.ctrl_s.L0", "B5.ctrl_s.L0", "B0.ctrl_s.L1", "B0.ctrl_s.L2", "B0.ctrl_s.L4"):
        (scores / f"scores-{cid}.jsonl").unlink()
    argv = ["--items", str(smoke / "items/items.jsonl"), "--scores", str(scores),
            "--round", str(smoke / "round-1/scores"), "--round", str(smoke / "round-2/scores"),
            "--splits", "dev", "--reference", str(ROOT / levels.CONTROL_SUMMARIES["dev"][0]),
            "--n-boot", "50", "--out", str(tmp_path / "a.json")]  # fmt: skip
    with pytest.raises(SystemExit, match="neither scored nor named"):
        analysis.main(argv)


def test_dev_smoke_v3_readings_reproduce_from_committed_records(tmp_path):
    smoke = ROOT / "program/evidence/2026-10-11/r04-nuisance/dev-smoke-v3"
    out = tmp_path / "a.json"
    pending = tmp_path / "p.json"
    analysis.main(
        ["--items", str(smoke / "items/items.jsonl"), "--scores", str(smoke / "scores"),
         "--round", str(smoke / "round-1/scores"), "--round", str(smoke / "round-2/scores"),
         "--splits", "dev", "--reference", str(ROOT / levels.CONTROL_SUMMARIES["dev"][0]),
         "--n-boot", "50", "--out", str(out), "--pending-out", str(pending)]
    )  # fmt: skip
    new = json.loads(out.read_text())
    old = json.loads((smoke / "analysis.json").read_text())
    for checker in analysis.CHECKERS:
        for cid, table in old[checker]["cells"].items():
            assert new[checker]["cells"][cid]["reading"] == table["reading"], cid
            assert new[checker]["cells"][cid]["gold"]["confirmed"] == table["gold"]["confirmed"]
        assert {a: v["reading"] for a, v in new[checker]["arms"].items()} == {
            a: v["reading"] for a, v in old[checker]["arms"].items()
        }
    assert new["validity"]["gate"] == "pass" and new["complete"]
    assert new["inputs"]["scores"][0]["jobs"] == ["1138"]
    assert [r[0]["jobs"] for r in new["inputs"]["rounds"]] == [["1147"], ["1151"]]
    assert json.loads(pending.read_text()) == {"items": [], "cells": []}


def test_exactly_zero_or_two_rounds():
    its = _items()
    scores = _scores(its, ALL)
    one = _scores(its, [levels.CONTROL_CELL])
    for rounds in ([one], [one, one, one]):
        with pytest.raises(analysis.AnalysisError, match="exactly 0 or 2"):
            analyze_fast(its, scores, rounds=rounds)


def test_control_not_retained_or_not_scored_invalidates_every_reading():
    its = _items()
    status = {levels.CONTROL_CELL: {i["item_id"]: "save_failed" for i in its[:3]}}
    out = analyze_fast(its, _scores(its, ALL, status=status))
    assert out["validity"]["control_retained"]["status"] == "fail"
    assert out["validity"]["gate"] == "invalid"
    assert out["pinned"]["cells"]["B5.ctrl_s.L0"]["reading"] == "INVALID"
    assert all(a["reading"] == "INVALID" for a in out["pinned"]["arms"].values())
    scores = _scores(its, ALL)
    del scores[levels.CONTROL_CELL]
    out = analyze_fast(its, scores, cell_errors={levels.CONTROL_CELL: "save job failed 3 times"})
    assert out["validity"]["gate"] == "invalid"
    assert out["pinned"]["cells"]["B3.ctrl_s.L0"]["reading"] == "INVALID"
    assert out["pinned"]["arms"]["route"]["reading"] == "INVALID"


def test_replicate_not_scored_or_not_retained_makes_v2_not_evaluable():
    its = _items()
    scores = _scores(its, ALL)
    del scores[levels.REPLICATE_CELL]
    out = analyze_fast(its, scores, cell_errors={levels.REPLICATE_CELL: "cap"})
    assert out["validity"]["V2"]["status"] == "not_evaluable"
    assert out["pinned"]["arms"]["build"]["reading"] == "INVALID"
    status = {levels.REPLICATE_CELL: {i["item_id"]: "infra_error" for i in its[:3]}}
    out = analyze_fast(its, _scores(its, ALL, status=status))
    assert out["validity"]["V2"]["status"] == "not_evaluable"
    assert out["validity"]["gate"] == "invalid"


def test_retention_drops_builds_and_build_arm_needs_two():
    its = _items()
    status = {}
    for b in ("B1", "B2", "B3", "B4"):
        status[f"{b}.ctrl_s.L0"] = {it["item_id"]: "save_failed" for it in its[:3]}
    out = analyze_fast(its, _scores(its, ALL, status=status))
    cells = out["pinned"]["cells"]
    assert cells["B1.ctrl_s.L0"]["reading"] == "NOT_EVALUABLE"
    assert cells["B5.ctrl_s.L0"]["reading"] == "INVARIANT"
    assert out["builds_retained"]["B5"] and not out["builds_retained"]["B1"]
    assert out["pinned"]["arms"]["build"]["reading"] == "NOT_EVALUABLE"
    assert out["validity"]["V1"]["status"] == "pass"
    assert {f["item_id"] for f in cells["B1.ctrl_s.L0"]["save_failures"]} == {"g:0", "g:1", "g:2"}


def test_retention_counts_save_failures_not_scorer_failures():
    its = _items()
    scores = _scores(its, ALL)
    rows = scores["B2.ctrl_s.L0"]
    for row in rows[:3]:  # the scorer crashed on three items whose save succeeded
        row["status"] = "harness_error"
        row["save_status"] = "saved"
    out = analyze_fast(its, scores)
    cell = out["pinned"]["cells"]["B2.ctrl_s.L0"]
    assert out["retention"]["B2.ctrl_s.L0"]["gold"]["saved"] == 10
    assert cell["retained"] and cell["reading"] == "INVARIANT"
    assert cell["scoring_failures_by_status"] == {"harness_error": 3}
    assert cell["save_failures"] == []
    for row in rows[:3]:
        row["save_status"] = "save_failed"
    out = analyze_fast(its, scores)
    assert out["retention"]["B2.ctrl_s.L0"]["gold"]["saved"] == 7
    assert out["pinned"]["cells"]["B2.ctrl_s.L0"]["reading"] == "NOT_EVALUABLE"


def test_harness_noise_flag_changes_no_reading():
    its = _items()
    flips = {"B0.store_as.L0": {"g:0", "g:1", "s:0:0"}, levels.REPLICATE_CELL: {"g:7"}}
    rounds = [_scores(its, [levels.CONTROL_CELL, "B0.store_as.L0", levels.REPLICATE_CELL], {})] * 2
    out = analyze_fast(its, _scores(its, ALL, flips), rounds=rounds)
    cell = out["pinned"]["cells"]["B0.store_as.L0"]
    assert cell["harness_noise"] and cell["reading"] == "INVARIANT"
    assert out["validity"]["V2"]["status"] == "pass" and out["validity"]["V2"]["harness_noise"]


def test_task_level_s1a_count_and_v1_difference_limit():
    its = _items(s1a_tasks=4)
    flips = {"B0.headless_convert.L0": {"s:0:0", "s:0:1", "s:1:0", "s:2:1"}}
    rounds = _rounds(its, ["B0.headless_convert.L0"], flips)
    ref = dict(REF)
    ref["tg0"] = ref["tg1"] = "fail"
    out = analyze_fast(its, _scores(its, ALL, flips), rounds=rounds, reference=ref)
    table = out["pinned"]["cells"]["B0.headless_convert.L0"]
    s1a = table["s1a"]["s1a_pass"]
    assert s1a["confirmed"] == 4 and s1a["confirmed_tasks"] == ["ts0", "ts1", "ts2"]
    assert table["reading_before_gates"] == "DRIFT" and table["reading"] == "INVALID"
    assert out["validity"]["V1"]["status"] == "fail"  # two differences > 1
    assert out["pinned"]["arms"]["route"]["reading"] == "INVALID"
    # a gold not valid in the control is listed, not compared
    out = analyze_fast(
        its, _scores(its, ALL, status={levels.CONTROL_CELL: {"g:3": "infra_failed"}})
    )
    assert (
        out["validity"]["V1"]["not_compared"] == ["tg3"] and out["validity"]["V1"]["compared"] == 9
    )
    out = analyze_fast(its, _scores(its, ALL), reference={})
    assert out["validity"]["V1"]["status"] == "fail" and out["validity"]["V1"]["compared"] == 0


def test_analysis_scope_is_a_registered_split_set():
    its = _items()
    for it in its[:5]:
        it["split"] = "dev"
    out = analyze_fast(its, _scores(its, ALL))
    assert out["items"] == len(its) - 5
    dev = analyze_fast(its, _scores(its, ALL), splits=("dev",))
    assert dev["items"] == 5
    for splits in (("confirm",), ("dev", "confirm"), ("reserve",), ("test",)):
        with pytest.raises(ValueError):
            analyze_fast(its, _scores(its, ALL), splits=splits)
    assert levels.check_split_set(["reserve", "confirm"]) == ("confirm", "reserve")


def test_k2_report_drops_a_family_and_reports_it_as_exploratory():
    its = _items()
    funcs = {"g:0": ("compare_pptx_files",), "g:1": ("compare_pptx_files",),
             "g:2": ("compare_pptx_files",)}  # fmt: skip
    flips = {"B4.ctrl_s.L0": {"g:0", "g:1", "g:2"}}
    scores = _scores(its, ALL, flips, funcs=funcs)
    rounds = [_scores(its, [levels.CONTROL_CELL, "B4.ctrl_s.L0"], flips, funcs=funcs)] * 2
    k2 = {
        "executor_commit": "abc",
        "pairs": 80,
        "outcome": "FAMILIES_DROPPED",
        "disagreements": [
            {"checker_family": "compare_pptx_files", "explanation": "unexplained"},
            {"checker_family": "compare_table", "explanation": "nondeterministic"},
        ],
    }
    out = analyze_fast(its, scores, rounds=rounds, k2=k2)
    assert out["vm_fidelity"]["label"] == analysis.K2_VERIFIED
    assert out["vm_fidelity"]["families_dropped"] == ["compare_pptx_files"]
    assert out["pinned"]["cells"]["B4.ctrl_s.L0"]["reading"] == "INVARIANT"
    full = out["k2_exploratory"]["including_dropped_families"]
    assert full["pinned"]["cells"]["B4.ctrl_s.L0"]["reading"] == "DRIFT"
    assert out["k2_exploratory"]["items_left_out"] == 3
    clean = analyze_fast(its, scores, rounds=rounds, k2={**k2, "disagreements": []})
    assert clean["pinned"]["cells"]["B4.ctrl_s.L0"]["reading"] == "DRIFT"
    assert "k2_exploratory" not in clean
    from harness.q2_mutation.campaign import checker_family

    for f in (["b", "a", "b"], ["x"], []):
        assert analysis.checker_family(f) == checker_family(f)


def test_inputs_are_checked_files_from_finished_jobs(tmp_path):
    with pytest.raises(analysis.AnalysisError, match="never reads"):
        analysis.check_input(tmp_path / "audit-summary" / "adjudication-pool.jsonl")
    with pytest.raises(analysis.AnalysisError, match="never reads"):
        analysis.check_input(tmp_path / "x" / "decisions.jsonl")
    a, b = tmp_path / "a", tmp_path / "b"
    for d, job, status in ((a, "11", 0), (b, "12", 0)):
        d.mkdir()
        (d / f"receipt-{job}.json").write_text(json.dumps({"job_id": job, "exit_status": status}))
        (d / "scores-B0.ctrl_s.L0.jsonl").write_text("")
    with pytest.raises(analysis.AnalysisError, match="two directories"):
        analysis.load_scores([a, b])
    (b / "scores-B0.ctrl_s.L0.jsonl").unlink()
    scores, record = analysis.load_scores([a, b])
    assert record[0]["jobs"] == ["11"] and record[0]["cells"] == ["B0.ctrl_s.L0"]
    (b / "receipt-12.json").write_text(json.dumps({"job_id": "12", "exit_status": 1}))
    with pytest.raises(analysis.AnalysisError, match="exit status 0"):
        analysis.load_scores([a, b])
    (b / "receipt-12.json").unlink()
    with pytest.raises(analysis.AnalysisError, match="no lane receipt"):
        analysis.load_scores([a, b])
    dev = ROOT / levels.CONTROL_SUMMARIES["dev"][0]
    ref, rec = analysis.reference_from_control_summaries([dev], ["dev"])
    assert len(ref) > 17 and rec[0]["split"] == "dev"
    with pytest.raises(analysis.AnalysisError, match="not one of the pinned"):
        analysis.reference_from_control_summaries([dev], ["confirm", "reserve"])
    confirm = ROOT / levels.CONTROL_SUMMARIES["confirm"][0]
    with pytest.raises(analysis.AnalysisError, match="were not given"):
        analysis.reference_from_control_summaries([confirm], ["confirm", "reserve"])
    with pytest.raises(analysis.AnalysisError, match="not one of the pinned"):
        analysis.reference_from_control_summaries([confirm, confirm], ["confirm", "reserve"])


def _write_run(tmp_path, its, scores, rounds=None, pending=None, states=None):
    """A run directory as r04_host.py lays it out, with every step finished."""
    root = "/home/kevin/cotcodec-runs/stage0/r04-nuisance/runs/t"
    run = tmp_path / "t"
    (run / "items").mkdir(parents=True)
    (run / "items" / "items.jsonl").write_text("".join(json.dumps(i) + "\n" for i in its))
    steps = [{"name": "items", "kind": "items", "out": "main", "state": "done", "job": "1",
              "run_dir": f"{root}/items", "cells": []}]  # fmt: skip
    outs = [("main", scores, [(g, c) for g, _r, c in levels.score_groups(ALL[1:], raw=True)])]
    for k, rnd in enumerate(rounds or []):
        outs.append((f"round-{k + 1}", rnd, [("round", sorted(rnd))]))
    job = 100
    for out, cell_rows, groups in outs:
        for group, cells in groups:
            job += 1
            state = (states or {}).get(group, "done")
            d = run / out / "scores" / group
            d.mkdir(parents=True)
            (d / f"receipt-{job}.json").write_text(
                json.dumps({"job_id": str(job), "exit_status": 0})
            )
            for cid in cells:
                if cid in cell_rows and state == "done":
                    (d / f"scores-{cid}.jsonl").write_text(
                        "".join(json.dumps(r) + "\n" for r in cell_rows[cid])
                    )
            steps.append({"name": f"{out}-score-{group}", "kind": "score", "out": out,
                          "group": group, "cells": cells, "state": state, "job": str(job),
                          "run_dir": f"{root}/{out}/scores/{group}",
                          "reason": None if state == "done" else "cap"})  # fmt: skip
    plan = {"name": "t", "splits": ["confirm", "reserve"], "run_root": root, "steps": steps,
            "rounds": {"pending": pending} if rounds else None, "src_sha": "x"}  # fmt: skip
    (run / "plan.json").write_text(json.dumps(plan))
    return run


def test_registered_analysis_reads_everything_from_the_run(tmp_path, monkeypatch):
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0"}}
    scores = _scores(its, ALL, flips)
    src = tmp_path
    # the frozen confirm summaries name real tasks, not tg0-tg9: V1 reads REF instead
    monkeypatch.setattr(
        analysis, "reference_from_control_summaries", lambda paths, splits: (REF, [])
    )
    run = _write_run(tmp_path, its, scores)
    out_path, pending_path = tmp_path / "main.json", tmp_path / "pending.json"
    analysis.main(["--run", str(run), "--src", str(src), "--n-boot", "50",
                   "--out", str(out_path), "--pending-out", str(pending_path)])  # fmt: skip
    main = json.loads(out_path.read_text())
    pending = json.loads(pending_path.read_text())
    assert main["inputs"]["mode"] == "run" and not main["complete"]
    assert pending == {"items": ["g:0"], "cells": ["B3.ctrl_s.L0"]}
    rounds = _rounds(its, ["B3.ctrl_s.L0"], flips)
    run2 = _write_run(tmp_path / "r", its, scores, rounds=rounds, pending=pending)
    analysis.main(["--run", str(run2), "--src", str(src), "--n-boot", "50",
                   "--out", str(out_path)])  # fmt: skip
    final = json.loads(out_path.read_text())
    assert final["complete"] and final["confirmation_rounds"] == 2
    assert final["pinned"]["cells"]["B3.ctrl_s.L0"]["reading"] == "MINOR"
    # rounds that re-ran something else are refused
    run3 = _write_run(tmp_path / "s", its, scores, rounds=rounds,
                      pending={"items": ["g:1"], "cells": ["B3.ctrl_s.L0"]})  # fmt: skip
    with pytest.raises(SystemExit, match="pending discordances"):
        analysis.main(["--run", str(run3), "--src", str(src), "--out", str(out_path)])
    # a score job that ended without output names its cells with the plan's reason
    run4 = _write_run(tmp_path / "u", its, scores, states={"secondary-store_as": "dropped"})
    analysis.main(["--run", str(run4), "--src", str(src), "--n-boot", "50",
                   "--out", str(out_path)])  # fmt: skip
    dropped = json.loads(out_path.read_text())
    assert dropped["pinned"]["cells"]["B2.store_as.L0"]["reading"].startswith("NOT_EVALUABLE")
    assert "dropped" in dropped["cells_not_scored"]["B2.store_as.L0"]
    # an unfinished run is refused, and --run takes no other input
    plan = json.loads((run4 / "plan.json").read_text())
    plan["steps"][-1]["state"] = "submitted"
    (run4 / "plan.json").write_text(json.dumps(plan))
    with pytest.raises(SystemExit, match="unfinished"):
        analysis.main(["--run", str(run4), "--src", str(src), "--out", str(out_path)])
    with pytest.raises(SystemExit):
        analysis.main(["--run", str(run), "--splits", "dev", "--out", str(out_path)])


def test_pending_confirmations_lists_items_and_cells():
    its = _items()
    flips = {"B3.ctrl_s.L0": {"g:0"}, levels.REPLICATE_CELL: {"s:1:1"}}
    out = analyze_fast(its, _scores(its, ALL, flips))
    pending = analysis.pending_confirmations(out)
    assert pending == {"items": ["g:0", "s:1:1"], "cells": [levels.REPLICATE_CELL, "B3.ctrl_s.L0"]}


# --- items: the registered split set and P1's golds -------------------------------------------


def test_item_builder_golds_must_be_p1_counted_golds():
    smoke = ROOT / "program/evidence/2026-10-11/r04-nuisance/dev-smoke-v3/items/items.jsonl"
    golds = [
        g for g in map(json.loads, smoke.read_text().splitlines()) if g["population"] == "gold"
    ]
    assert items.check_p1_golds(golds, ROOT, "dev") == {
        "split": "dev", "golds": 17, "equals_p1_counted": True,
    }  # fmt: skip
    with pytest.raises(items.GoldSetMismatch, match="missing"):
        items.check_p1_golds(golds[1:], ROOT, "dev")
    with pytest.raises(items.GoldSetMismatch, match="extra"):
        items.check_p1_golds([*golds, {**golds[0], "task_id": "x"}], ROOT, "dev")
    assert len(items.p1_counted_golds(ROOT, "confirm")) == 67
    assert len(items.p1_counted_golds(ROOT, "reserve")) == 25
    assert items.SPLIT_RUNS == levels.S1A_SPLIT_RUNS
    assert set(levels.REGISTERED_RUN["s1a_runs"]) == set(items.SPLIT_RUNS["confirm"])
    with pytest.raises(SystemExit):  # dev and a registered split never share a run
        items.main(["--splits", str(ROOT / "program/evidence/q2-mutation/splits.json"),
                    "--split", "dev", "confirm", "--out", "/nonexistent/x.jsonl"])  # fmt: skip


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


# --- freeze guard, code of record and the registration ----------------------------------------


def _fake_tree(root: Path, monkeypatch) -> None:
    (root / "code").mkdir(parents=True)
    (root / "code" / "a.py").write_text("x = 1\n")
    (root / "code" / "README.md").write_text("docs\n")
    monkeypatch.setattr(guard, "CODE_TREE_ROOTS", ("code",))


def _freeze_copy(tmp_path: Path, text: str) -> Path:
    prereg = tmp_path / levels.PREREG_PATH
    prereg.parent.mkdir(parents=True, exist_ok=True)
    prereg.write_text(text)
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
    return prereg


def test_guard_allows_dev_and_refuses_unfrozen_splits(tmp_path, monkeypatch):
    assert guard.require_split_allowed("dev", tmp_path) is None
    assert guard.require_splits_allowed(["dev"], tmp_path) is None
    (tmp_path / "program" / "preregistrations").mkdir(parents=True)
    (tmp_path / guard.LEDGER_PATH).write_text("")
    with pytest.raises(guard.GuardError):
        guard.require_split_allowed("confirm", tmp_path)
    for splits in (["confirm"], ["dev", "confirm"], ["reserve"]):
        with pytest.raises(guard.GuardError):
            guard.require_splits_allowed(splits, tmp_path)
    _fake_tree(tmp_path, monkeypatch)
    digest = guard.code_tree_sha256(tmp_path)
    pins = '{{\n "r04_pins": 1,\n "code_tree_sha256": {},\n "images": {{"B0": "sha256:a"}}\n}}'
    prereg = _freeze_copy(tmp_path, f"x\n```json\n{pins.format(json.dumps(digest))}\n```\n")
    with pytest.raises(guard.GuardError, match="R04_PREREG_FROZEN"):
        guard.require_split_allowed("confirm", tmp_path)
    monkeypatch.setenv("R04_PREREG_FROZEN", levels.EXPERIMENT_ID)
    assert guard.require_split_allowed("confirm", tmp_path, {"B0": "sha256:a"})["hash"]
    assert guard.require_splits_allowed(["reserve", "confirm"], tmp_path, {"B0": "sha256:a"})
    with pytest.raises(guard.GuardError, match="pins"):
        guard.require_split_allowed("confirm", tmp_path, {"B0": "sha256:b"})
    # a staged code tree other than the frozen one is refused
    (tmp_path / "code" / "a.py").write_text("x = 2\n")
    with pytest.raises(guard.GuardError, match="code of record"):
        guard.require_split_allowed("confirm", tmp_path)
    (tmp_path / "code" / "a.py").write_text("x = 1\n")
    (tmp_path / "code" / "README.md").write_text("other docs\n")  # docs are not code
    assert guard.require_split_allowed("confirm", tmp_path)
    # a frozen file whose pins block never got its code-tree digest refuses everything
    _freeze_copy(tmp_path, f"x\n```json\n{pins.format('null')}\n```\n")
    with pytest.raises(guard.GuardError, match="code of record"):
        guard.require_split_allowed("confirm", tmp_path)
    prereg.write_text("changed")
    with pytest.raises(guard.GuardError, match="differs"):
        guard.require_split_allowed("confirm", tmp_path)


def test_reused_code_is_the_frozen_code():
    """R04 reuses the checker-mutation study's code (its frozen code-tree digest) and S1a's
    rescorer, comparator and task loader (the digests R04's smoke tests ran) unchanged."""
    from harness.q2_mutation.campaign import code_tree_sha256, prereg_pins

    parent = (ROOT / "program/preregistrations/q2-evaluator-mutation-v1.md").read_text()
    assert code_tree_sha256(ROOT) == prereg_pins(parent)["code_tree_sha256"]
    s1a = {
        "harness/q2_stage1/__init__.py": "0e2190149cf640fac07dab26332a26f6"
        "96374ff4400c23aab82e8cf766f3b334",
        "harness/q2_stage1/rescore.py": "d240db03e969c8aa5bb97403c5005cd4"
        "c9e96016599a78f70e97850415893737",
        "harness/q2_stage1/zinv.py": "64899d5056f4791008c2a10c38a7b0fb"
        "b94fbe912d20a702ec74851a0ca7f655",
        "harness/q2_stage1/osworld_live.py": "38b017c04f67b59e08bc1d764702a2ff"
        "91c80ebde8054c8e80bc277746334313",
    }
    for rel, digest in s1a.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel
    assert set(s1a) <= set(guard.CODE_TREE_ROOTS)


def _status_line(text: str) -> str:
    return next(line for line in text.splitlines() if line.startswith("**Status: "))


def _frozen() -> bool:
    from scripts import preregister

    try:
        preregister.verify(levels.EXPERIMENT_ID)
    except preregister.PreregistrationError:
        return False
    return True


def test_registration_pins_match_the_code():
    text = (ROOT / levels.PREREG_PATH).read_text()
    status = _status_line(text)
    pins = guard.prereg_pins(text)
    if _frozen() or status.startswith("**Status: frozen"):
        # After the freeze: the status line says so, the ledger row is this file, the pins
        # block carries the code tree of record and the tree here is that tree.
        assert status.startswith("**Status: frozen")
        row = guard.frozen_row(ROOT)
        assert row is not None and row["path"] == levels.PREREG_PATH
        assert pins["code_tree_sha256"] == guard.code_tree_sha256(ROOT)
        assert "DRAFT" not in status
    else:
        assert status.startswith("**Status: DRAFT")
        assert pins["code_tree_sha256"] is None  # filled at the freeze (section 17)
    assert pins["experiment_id"] == levels.EXPERIMENT_ID
    assert pins["images"]["B0"] == levels.LO_VM_IMAGE_ID
    assert sorted(pins["images"]) == [b.id for b in levels.BUILDS]
    assert pins["metric_image_id"] == levels.METRIC_IMAGE_ID
    assert pins["drift_min"] == analysis.DRIFT_MIN == power.DRIFT_MIN
    assert pins["retention_min"] == analysis.RETENTION_MIN
    assert pins["confirm_rounds"] == analysis.CONFIRM_ROUNDS
    assert pins["registered_splits"] == list(levels.REGISTERED_SPLITS)
    assert pins["cap_lane_hours"] == levels.REGISTERED_RUN["cap_lane_hours"]
    assert pins["workers"] == levels.REGISTERED_RUN["workers"]
    splits = ROOT / "program/evidence/q2-mutation/splits.json"
    assert hashlib.sha256(splits.read_bytes()).hexdigest() == pins["splits_sha256"]
    for split, (rel, digest) in levels.CONTROL_SUMMARIES.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, split
        assert digest[:8] in text


def test_registration_freezes_against_a_scratch_ledger(tmp_path):
    """The program owner's freeze command accepts this file (no TBD or angle-bracket
    placeholder): run against an empty scratch ledger; the real ledger is not touched."""
    from scripts import preregister

    ledger = tmp_path / "ledger.jsonl"
    real = (ROOT / guard.LEDGER_PATH).read_bytes()
    row = preregister.freeze(ROOT / levels.PREREG_PATH, levels.EXPERIMENT_ID, ledger=ledger)
    assert row["path"] == levels.PREREG_PATH
    assert row["sha256"] == hashlib.sha256((ROOT / levels.PREREG_PATH).read_bytes()).hexdigest()
    assert (ROOT / guard.LEDGER_PATH).read_bytes() == real
    assert preregister.read_ledger(ledger)[0]["experiment_id"] == levels.EXPERIMENT_ID


def test_registration_states_the_code_tree_and_the_registered_run():
    text = (ROOT / levels.PREREG_PATH).read_text()
    flat = " ".join(text.split())
    for entry in guard.CODE_TREE_ROOTS:
        assert f"`{entry}`" in flat, entry
    # the registered command lines of section 6
    for phrase in (
        "r04_host.py plan --src SRC --name r04-registered-v1 --registered",
        "r04_host.py next --name r04-registered-v1",
        "python -m harness.r04_nuisance.analysis --run RUN --src . --out RUN/analysis-main.json "
        "--pending-out RUN/pending.json",
        "r04_host.py confirm --name r04-registered-v1 --pending RUN/pending.json",
        "python -m harness.r04_nuisance.analysis --run RUN --src . --out RUN/analysis.json",
        "export R04_PREREG_FROZEN=r04-checker-nuisance-invariance-v1",
    ):
        assert phrase in flat, phrase
    # the projections and limits table of section 6 is levels' arithmetic
    cells = [c.id for c in levels.registered_cells()]
    for group, _role, members in levels.score_groups(cells, raw=True):
        proj = levels.projected_minutes(
            levels.REGISTERED_ITEMS, len(members), 16, levels.SCORE_SECONDS_PER_ITEM_CELL
        )
        assert (
            f"| score `{group}` | {len(members)} | {proj:.0f} | {levels.limit_minutes(proj)} |"
            in flat
        )
    for group, members in levels.save_groups(cells):
        proj = levels.projected_minutes(
            levels.REGISTERED_ITEMS, len(members), 16, levels.SAVE_SECONDS_PER_ITEM_CELL
        )
        assert (
            f"| save `{group}` | {len(members)} | {proj:.0f} | {levels.limit_minutes(proj)} |"
            in flat
        )
    assert "offline harness, VM fidelity unverified" in flat
    assert "q2-evaluator-mutation-v1-k2" in flat


def test_code_tree_digest_covers_the_code_of_record(tmp_path):
    digest = guard.code_tree_sha256(ROOT)
    assert digest == guard.code_tree_sha256(ROOT) and len(digest) == 64
    for entry in guard.CODE_TREE_ROOTS:
        assert (ROOT / entry).exists(), entry
    with pytest.raises(guard.GuardError, match="missing"):
        guard.code_tree_sha256(tmp_path)


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


def _host_tool():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "r04_host", ROOT / "infra/r04-nuisance/run/r04_host.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Lane:
    """squeue and sbatch for the host tool's tests: jobs finish when told to."""

    def __init__(self):
        self.queue: list[str] = []
        self.jobs: dict[str, list[str]] = {}
        self.next_id = 2000

    def squeue(self):
        return [f"{j} r04 kevin RUNNING" for j in self.queue]

    def sbatch(self, command):
        self.next_id += 1
        job = str(self.next_id)
        self.jobs[job] = command
        self.queue.append(job)
        return job

    def finish(self, step, status=0, hours=0.1):
        self.queue.remove(step["job"])
        receipt = {
            "job_id": step["job"],
            "exit_status": status,
            "started_at": "2026-10-12T00:00:00Z",
            "finished_at": f"2026-10-12T{int(hours):02d}:{int(hours % 1 * 60):02d}:00Z",
        }
        Path(step["run_dir"]).joinpath(f"receipt-{step['job']}.json").write_text(
            json.dumps(receipt)
        )


def _host_env(tmp_path, monkeypatch):
    host = _host_tool()
    lane = _Lane()
    src = tmp_path / "src"
    src.mkdir()
    (src / ".git_sha").write_text("f" * 40)
    root = tmp_path / "stage0" / "r04-nuisance"
    (root / "images").mkdir(parents=True)
    images = {b.id: f"sha256:{i:064x}" for i, b in enumerate(levels.BUILDS)}
    (root / "images" / "images.json").write_text(json.dumps(images))
    s1a = tmp_path / "s1a"
    (s1a / "1037").mkdir(parents=True)
    (s1a / "1037" / "episodes.jsonl").write_text("")
    monkeypatch.setattr(host, "ROOT", root)
    monkeypatch.setattr(host, "S1A_RUNS", s1a)
    monkeypatch.setattr(host, "queue_jobs", lane.squeue)
    monkeypatch.setattr(host, "sbatch", lane.sbatch)
    return host, lane, src, root, images


def _plan(host, root, name):
    return json.loads((root / "runs" / name / "plan.json").read_text())


def _drive(host, lane, root, name, *, fail=(), hours=0.1):
    """Run next until complete; fail the named steps' first attempts."""
    for _ in range(200):
        host.main(["next", "--name", name])
        plan = _plan(host, root, name)
        running = [s for s in plan["steps"] if s["state"] == "submitted"]
        if not running:
            return plan
        step = running[0]
        if step["kind"] == "items":
            Path(step["run_dir"]).joinpath("items.jsonl").write_text(
                "".join(json.dumps({"item_id": f"g:{i}"}) + "\n" for i in range(34))
            )
        lane.finish(step, status=1 if step["name"] in fail else 0, hours=hours)
    raise AssertionError("did not complete")


def test_host_tool_plans_runs_and_renders_cpu_only_jobs(tmp_path, monkeypatch):
    host, lane, src, root, images = _host_env(tmp_path, monkeypatch)
    cells = [c.id for c in levels.registered_cells()]
    host.main(["plan", "--src", str(src), "--name", "smoke", "--split", "dev", "--golds",
               "--s1a", "1037", "--cells", *cells, "--workers", "8"])  # fmt: skip
    plan = _plan(host, root, "smoke")
    names = [s["name"] for s in plan["steps"]]
    assert names == [
        "items", "main-save-B0", "main-save-B0.r2", "main-save-B1", "main-save-B2",
        "main-save-B3", "main-save-B4", "main-save-B5", "main-score-control", "main-score-route",
        "main-score-build", "main-score-locale", "main-score-secondary-store_as",
        "main-score-secondary-headless_convert",
    ]  # fmt: skip
    assert plan["splits"] == ["dev"] and plan["cap_lane_hours"] is None
    plan = _drive(host, lane, root, "smoke", fail={"main-save-B4", "main-score-build"})
    states = {s["name"]: s["state"] for s in plan["steps"]}
    assert states["main-save-B4"] == "superseded" and states["main-save-B4.a2"] == "done"
    assert states["main-score-build"] == "superseded" and states["main-score-build.a2"] == "done"
    assert all(v in ("done", "superseded") for v in states.values())
    by_name = {s["name"]: s for s in plan["steps"]}
    for step in plan["steps"]:
        if not step.get("command"):
            continue
        command = " ".join(step["command"])
        assert "--gres" not in command and "--gpus" not in command
        assert "Q2M_MODE=run" in command and command.endswith(host.LANE)
        assert f"--time={step['minutes'] // 60:02d}:{step['minutes'] % 60:02d}:00" in command
        assert step["minutes"] >= levels.LIMIT_FLOOR_MINUTES
    # each attempt has its own directory; scores read the save attempt that finished
    assert by_name["main-save-B4.a2"]["run_dir"].endswith("main/saves/B4.a2")
    argv = json.loads(bytes.fromhex(
        next(e for e in by_name["main-score-build.a2"]["command"][-2].split(",")
             if e.startswith("Q2M_ARGV_JSON_HEX=")).split("=", 1)[1]))  # fmt: skip
    assert "B4.ctrl_s.L0=/ro/saves/B4.a2/B4.ctrl_s.L0" in argv
    assert "B3.ctrl_s.L0=/ro/saves/B3/B3.ctrl_s.L0" in argv
    control = json.loads(bytes.fromhex(
        next(e for e in by_name["main-score-control"]["command"][-2].split(",")
             if e.startswith("Q2M_ARGV_JSON_HEX=")).split("=", 1)[1]))  # fmt: skip
    assert control[control.index("--cell") + 1] == "raw"
    assert by_name["main-score-control"]["image"] == levels.METRIC_IMAGE_ID
    assert by_name["main-save-B4.a2"]["image"] == images["B4"]
    items_argv = json.loads(bytes.fromhex(
        next(e for e in by_name["items"]["command"][-2].split(",")
             if e.startswith("Q2M_ARGV_JSON_HEX=")).split("=", 1)[1]))  # fmt: skip
    assert items_argv[items_argv.index("--split") + 1] == "dev" and "env" not in items_argv
    # rounds: both added at once from the analysis's pending list, and only once
    pending = tmp_path / "pending.json"
    pending.write_text(json.dumps({"items": ["g:3", "g:1"], "cells": ["B4.ctrl_s.L0"]}))
    host.main(["confirm", "--name", "smoke", "--pending", str(pending)])
    with pytest.raises(SystemExit):
        host.main(["confirm", "--name", "smoke", "--pending", str(pending)])
    plan = _drive(host, lane, root, "smoke")
    rounds = [s["name"] for s in plan["steps"] if s["out"] != "main"]
    assert rounds == ["round-1-save-B0", "round-1-save-B4", "round-1-score",
                      "round-2-save-B0", "round-2-save-B4", "round-2-score"]  # fmt: skip
    assert plan["rounds"]["pending"] == {"items": ["g:1", "g:3"], "cells": ["B4.ctrl_s.L0"]}
    assert (root / "runs/smoke/rounds/only.txt").read_text() == "g:1\ng:3\n"
    # a third failure ends the step; its cells reach the analysis as not scored
    host.main(["plan", "--src", str(src), "--name", "fails", "--split", "dev",
               "--cells", levels.CONTROL_CELL, levels.REPLICATE_CELL, "B5.ctrl_s.L0"])  # fmt: skip
    plan = _drive(host, lane, root, "fails",
                  fail={"main-save-B5", "main-save-B5.a2", "main-save-B5.a3"})  # fmt: skip
    by_name = {s["name"]: s for s in plan["steps"]}
    assert by_name["main-save-B5.a3"]["state"] == "failed_final"
    assert by_name["main-score-build"]["state"] == "not_run"
    assert "B5.ctrl_s.L0" in by_name["main-score-build"]["not_scored"]


def test_host_tool_cap_drops_secondary_then_stops(tmp_path, monkeypatch):
    host, lane, src, root, _images = _host_env(tmp_path, monkeypatch)
    cells = [c.id for c in levels.registered_cells()]
    host.main(["plan", "--src", str(src), "--name", "capped", "--split", "dev", "--cells", *cells,
               "--cap-lane-hours", "6.2"])  # fmt: skip
    plan = _drive(host, lane, root, "capped", hours=0.5)
    states = {s["name"]: s["state"] for s in plan["steps"]}
    # 12 jobs of half an hour use 6 h of 6.2: the secondary score jobs are dropped first
    assert states["main-score-secondary-store_as"] == "dropped"
    assert states["main-score-secondary-headless_convert"] == "dropped"
    assert states["main-score-locale"] == "done"
    host.main(["plan", "--src", str(src), "--name", "stopped", "--split", "dev", "--cells", *cells,
               "--cap-lane-hours", "2"])  # fmt: skip
    plan = _drive(host, lane, root, "stopped", hours=0.5)
    states = [s["state"] for s in plan["steps"]]
    assert states.count("done") == 4 and "not_run" in states
    assert all(s["reason"] for s in plan["steps"] if s["state"] in ("not_run", "dropped"))


def test_host_tool_registered_plan_needs_the_freeze(tmp_path, monkeypatch):
    host, _lane, src, root, _images = _host_env(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="fixes"):
        host.main(["plan", "--src", str(src), "--name", "r", "--registered", "--split", "dev"])
    with pytest.raises(guard.GuardError):
        host.main(["plan", "--src", str(src), "--name", "r", "--registered"])
    with pytest.raises(SystemExit, match="only as --registered"):
        host.main(["plan", "--src", str(src), "--name", "r", "--split", "confirm", "reserve",
                   "--cells", levels.CONTROL_CELL])  # fmt: skip
    with pytest.raises(SystemExit, match="control"):
        host.main(["plan", "--src", str(src), "--name", "r", "--split", "dev",
                   "--cells", "B3.ctrl_s.L0"])  # fmt: skip
    assert not (root / "runs" / "r").exists()
    reg = levels.REGISTERED_RUN
    assert reg["splits"] == ["confirm", "reserve"] and reg["workers"] == 16
    assert reg["cells"] == [c.id for c in levels.registered_cells()]


def test_headless_route_collects_like_the_registered_stage(tmp_path, monkeypatch):
    gold = tmp_path / "gold.xlsx"
    gold.write_bytes(b"gold")
    other = tmp_path / "notes.txt"
    other.write_bytes(b"n")
    session = rs.NuisanceSession(
        rs.R.Display(197, tmp_path), tmp_path / "s", levels.get_cell("B0.headless_convert.L0"),
        None, pipe="p",
    )  # fmt: skip
    converted: list[tuple[str, ...]] = []

    def fake_round_trip(self, vm_path, timeout=120.0):
        target = self.host_path(vm_path)
        before = rs.R.sha256_file(target)
        target.write_bytes(b"resaved")
        return rs.R.SaveEvent(vm_path, "headless_convert", before, rs.R.sha256_file(target),
                              True, 0.9, [])  # fmt: skip

    monkeypatch.setattr(rs.NuisanceSession, "headless_round_trip", fake_round_trip)
    monkeypatch.setattr(rs.NuisanceSession, "convert", lambda self, argv: converted.append(argv))
    monkeypatch.setattr(rs.NuisanceSession, "close", lambda self: None)
    job = {
        "job_id": "g:t",
        "task_id": "t",
        "files": {"/home/user/a.xlsx": str(gold), "/home/user/notes.txt": str(other)},
    }
    raw = {"evaluator": {"postconfig": [
        {"type": "activate_window", "parameters": {"window_name": "a.xlsx - LibreOffice Calc"}},
        {"type": "execute", "parameters": {"command": [
            "libreoffice", "--convert-to", "csv:Text - txt - csv (StarCalc):44,34,UTF8",
            "--outdir", "/home/user", "/home/user/a.xlsx"]}}]}}  # fmt: skip
    row = rs.run_job_headless(session, job, raw, tmp_path / "out")
    assert [s["vm_path"] for s in row["saves"]] == ["/home/user/a.xlsx"]
    assert len(converted) == 1 and converted[0][0] == "libreoffice"
    assert set(row["outputs"]) == {"/home/user/a.xlsx"}
    assert (tmp_path / "out" / "g:t" / "home/user/a.xlsx").read_bytes() == b"resaved"
    assert rs.R.save_failures(job["files"], row) == []


def test_store_as_save_event_from_the_uno_client(tmp_path, monkeypatch):
    session = rs.NuisanceSession(
        rs.R.Display(196, tmp_path), tmp_path / "s", levels.get_cell("B3.store_as.L0"), None,
        pipe="r04w0",
    )  # fmt: skip
    session.log = []
    target = session.host_path("/home/user/a.docx")
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before")
    calls = []

    class Done:
        returncode = 0
        stderr = ""
        stdout = '{"ok": true, "filter": "MS Word 2007 XML", "error": null}\n'

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv and argv[0] == session.uno_python:
            target.write_bytes(b"after, longer")
            return Done()
        raise AssertionError(argv)

    monkeypatch.setattr(rs.subprocess, "run", fake_run)
    monkeypatch.setattr(rs.R, "list_windows", lambda env: [])
    event = session.save_with_ctrl_s("/home/user/a.docx", "agent_save", timeout=5.0)
    assert event.written and event.before_sha256 != event.after_sha256
    assert calls[0][0] == "/opt/libreoffice24.8/program/python"
    assert calls[0][calls[0].index("--pipe") + 1] == "r04w0"
    assert any(e["event"] == "store_as" and e["ok"] for e in session.log)


def test_save_summary_reads_both_save_layouts(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "summarize_saves", ROOT / "infra/r04-nuisance/run/summarize_saves.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row = {"job_id": "g:t", "saves": [{"written": True, "dialogs": []}], "seconds": 1.0}
    for cell_dir in (
        tmp_path / "flat" / "B0.ctrl_s.L0",
        tmp_path / "jobs" / "B4.a2" / "B4.ctrl_s.L0",
    ):
        cell_dir.mkdir(parents=True)
        (cell_dir / "reachability-0.jsonl").write_text(json.dumps(row) + "\n")
        (cell_dir / "cell-0.json").write_text(json.dumps({"build_identity": {"build": "B0"}}))
    (tmp_path / "jobs" / "B4.a2" / "logs").mkdir()
    assert list(module.summarize(tmp_path / "flat")) == ["B0.ctrl_s.L0"]
    summary = module.summarize(tmp_path / "jobs")
    assert list(summary) == ["B4.a2/B4.ctrl_s.L0"] and summary["B4.a2/B4.ctrl_s.L0"]["rows"] == 1


def test_no_r04_module_imports_audit_rater_or_packet_code():
    """Registration section 2.1: R04 reads no audit or adjudication file and imports no audit,
    rater or packet code (statically, and at import time with its reused modules)."""
    import ast

    forbidden = {"audit", "raters", "rater_runner", "packets"}
    for path in sorted((ROOT / "harness/r04_nuisance").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module, *(f"{node.module}.{a.name}" for a in node.names)]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for name in names:
                assert not forbidden & set(name.split(".")), (path.name, name)
    code = (
        "import sys\n"
        "import harness.r04_nuisance.analysis, harness.r04_nuisance.items\n"
        "import harness.r04_nuisance.score, harness.r04_nuisance.guard\n"
        "import harness.q2_mutation.controls, harness.q2_mutation.offline_eval\n"
        "import harness.q2_mutation.report, harness.q2_mutation.campaign\n"
        "bad = [m for m in sys.modules if m.split('.')[-1] in "
        f"{sorted(forbidden)!r} and m.startswith('harness')]\n"
        "print(bad)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True
    )
    assert out.stdout.strip() == "[]"
