"""D59 (iii): the S1a operator steps (ops/s1a-analysis), on synthetic records only."""

from __future__ import annotations

import json
import shlex
import shutil
import sys
from pathlib import Path

import pytest

from harness.q2_stage1 import analysis as A
from harness.q2_stage1 import glmm as G
from harness.q2_stage1 import records as R

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "s1a-analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _s1a_ops_synth as SY  # noqa: E402
import assemble_s15 as AS  # noqa: E402
import first_divergence as FD  # noqa: E402
import glmm_inputs as GI  # noqa: E402
import provenance as PV  # noqa: E402
import rescore_jobs as RJ  # noqa: E402
import run_report as RR  # noqa: E402
import s1a_ops as O  # noqa: E402

N = 100
REAL_PLAN = ROOT / O.PLAN_PATH


@pytest.fixture(autouse=True)
def _small(monkeypatch):
    monkeypatch.setattr(A, "N_BOOT", N)
    monkeypatch.setattr(A, "N_RANDOMIZATION", N)
    O.use_export(ROOT)


@pytest.fixture(scope="module")
def sc(tmp_path_factory):
    return SY.write_scenario(
        tmp_path_factory.mktemp("steps") / "session", SY.make_records(**SY.SCENARIOS["session"])
    )


@pytest.fixture(scope="module")
def late(tmp_path_factory):
    return SY.write_scenario(
        tmp_path_factory.mktemp("steps") / "dr0late", SY.make_records(**SY.SCENARIOS["dr0late"])
    )


def run_dirs(scenario) -> list[str]:
    out = []
    for path in scenario["runs"].values():
        out += ["--run-dir", str(path)]
    return out


def dr0s(scenario) -> list[str]:
    out = []
    for path in scenario["dr0"]:
        out += ["--dr0", str(path)]
    return out


def write_guard(path: Path, incomplete: bool = False) -> Path:
    """A guard.json labels block as run_report.py writes it after a successful report."""
    labels = {
        "incomplete": RR.INCOMPLETE if incomplete else None,
        "incomplete_reasons": ["no records from A1-4B-S2"] if incomplete else [],
        "external_anchor": A.NOT_ANCHORED,
    }
    guarded = {"path": "report-guarded.json", "kind": "registered report with the guard's readings"}
    path.write_text(json.dumps({"labels": labels, "guarded_report": guarded}))
    return path


def test_labels_are_refused_until_the_report_step_has_finished(tmp_path):
    with pytest.raises(SystemExit, match="has not finished"):
        O.labels_from_guard(tmp_path / "guard.json")
    failed = tmp_path / "failed.json"  # run_report.py's guard.json when the report failed
    failed.write_text(json.dumps({"labels": {"incomplete": None}, "readings": []}))
    with pytest.raises(SystemExit, match="the report step failed"):
        O.labels_from_guard(failed)
    labels = O.labels_from_guard(write_guard(tmp_path / "ok.json", incomplete=True))
    assert labels["incomplete"] == RR.INCOMPLETE


# --------------------------------------------------------------------------- first divergence


def test_first_divergence_reads_each_final_attempt_in_its_own_job(sc, tmp_path):
    finals = R.final_records(R.read_jsonl(sc["records"]))
    runs = O.run_dirs_by_job(sc["runs"].values())
    # a decoy: the same file name in another job's run directory must never be read
    key, rec = next(
        (k, r)
        for k, r in sorted(finals.items())
        if r["status"] == "scored" and k[2] in SY.BASE and r["job"] == "A1-9B-S1"
    )
    decoy = O.episode_dir(runs["A1-4B-S1"], rec)
    decoy.mkdir(parents=True)
    (decoy / "steps.jsonl").write_text('{"step": 1, "ir_sha256": "decoy"}\n')
    try:
        logs, missing = FD.step_logs(finals, SY.BASE, runs)
    finally:
        shutil.rmtree(decoy)
    expected = {k for k, r in finals.items() if r["status"] == "scored" and k[2] in SY.BASE}
    assert set(logs) == expected and missing == []
    assert logs[key][0]["ir_sha256"] != "decoy"
    assert all(r["extension_block"] is None for k, r in finals.items() if k in logs)
    out_path = tmp_path / "fd.json"
    argv = [
        "--export",
        str(ROOT),
        "--plan",
        str(sc["plan"]),
        "--records",
        str(sc["records"]),
        *run_dirs(sc),
        "--guard",
        str(write_guard(tmp_path / "guard.json", incomplete=True)),
        "--out",
        str(out_path),
    ]
    assert FD.main(argv) == 0
    out = json.loads(out_path.read_text())
    assert out["labels"]["incomplete"] == RR.INCOMPLETE
    assert out["labels"]["external_anchor"] == A.NOT_ANCHORED
    assert out["labels"]["source"].startswith("guard.json (sha256 ")
    assert out["first_divergence"] == A.divergence_summary(logs)
    assert out["step_logs_read"] == len(logs)
    assert set(out["first_divergence_by_size"]) == {"4B", "9B"}
    assert "base tasks" in out["set"] and "final attempt" in out["set"]
    assert sum(out["first_divergence"]["between"].values()) > 0


def test_first_divergence_counts_a_missing_log(sc):
    finals = R.final_records(R.read_jsonl(sc["records"]))
    runs = O.run_dirs_by_job(sc["runs"].values())
    _, rec = next(
        (k, r)
        for k, r in sorted(finals.items())
        if r["status"] == "scored" and k[2] in SY.BASE and r["job"] == "A1-9B-S2"
    )
    path = O.episode_dir(runs["A1-9B-S2"], rec) / "steps.jsonl"
    saved = path.read_text()
    path.unlink()
    try:
        _, missing = FD.step_logs(finals, SY.BASE, runs)
        assert f"{rec['slot']}.a{rec['attempt']}" in missing
    finally:
        path.write_text(saved)


# --------------------------------------------------------------------------- rescoring


def test_rescore_submit_dry_run_uses_eight_hours_and_the_metric_image(sc, tmp_path, capsys):
    argv = [
        "submit",
        "--dry-run",
        "--export",
        str(ROOT),
        "--analysis-dir",
        "/runs/A",
        "--inputs",
        "/runs/inputs",
        *run_dirs(sc),
        "--out",
        str(tmp_path / "jobs.json"),
    ]
    assert RJ.main(argv) == 0
    lines = [shlex.split(x) for x in capsys.readouterr().out.splitlines() if x.strip()]
    assert len(lines) == len(sc["runs"])
    for cmd in lines:
        assert cmd[:3] == ["sbatch", "--parsable", "--time=08:00:00"]
        env = dict(item.split("=", 1) for item in cmd[4].removeprefix("--export=").split(",")[1:])
        assert env["Q2M_IMAGE_ID"] == O.METRIC_IMAGE_ID
        assert json.loads(bytes.fromhex(env["Q2M_ARGV_JSON_HEX"])) == RJ.capture_argv()
        assert env["Q2M_EXTRA_RO"].endswith(":/ro/run")
        vm = Path(env["Q2M_EXTRA_RO"].split(":")[0]).name
        assert env["Q2M_RUN_DIR"] == f"/runs/A/rescore-{vm}"
        assert cmd[-1].endswith("infra/slurm/host-single-node/s1a-cpu.sbatch")
    assert not (tmp_path / "jobs.json").exists()
    # the runbook's first line of step 3 with --out left out: the same preview, nothing written
    assert RJ.main([a for a in argv if a not in ("--out", str(tmp_path / "jobs.json"))]) == 0
    again = capsys.readouterr()
    assert [shlex.split(x) for x in again.out.splitlines() if x.strip()] == lines
    assert "nothing submitted" in again.err


def test_rescore_coverage_counts_rows_errors_and_fallbacks(sc, tmp_path):
    analysis = tmp_path / "A"
    shutil.copytree(sc["analysis"], analysis)
    job = "A1-9B-S1"
    rows_path = analysis / f"rescore-{SY.VM[job]}" / "rescored.jsonl"
    rows = O.read_jsonl(rows_path)
    rows[0]["corrected_error"] = "TimeoutError"
    rows[0]["corrected"] = None
    dropped = rows.pop()
    rows_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    out_path = tmp_path / "cov.json"
    argv = [
        "coverage",
        "--export",
        str(ROOT),
        "--analysis-dir",
        str(analysis),
        *run_dirs(sc),
        "--records",
        str(sc["records"]),
        "--plan",
        str(sc["plan"]),
        *dr0s(sc),
        "--out",
        str(out_path),
    ]
    assert RJ.main(argv) == 0
    out = json.loads(out_path.read_text())
    assert out["labels"]["incomplete"] is None and out["labels"]["incomplete_reasons"] == []
    assert out["labels"]["external_anchor"] == A.NOT_ANCHORED
    cov = out["jobs"][job]
    assert cov["rows"] == cov["scored_attempts"] - 1
    assert cov["scored_attempts_without_row"] == 1
    assert cov["rows_with_error"] == 1 and cov["errors_by_field"] == {"corrected_error": 1}
    assert cov["scored_attempts_with_capture"] == cov["scored_attempts"]
    assert dropped["slot"].startswith(job)
    vs = out["verdict_sources"]["primary"]
    assert (
        vs["scored_final_records"]
        == vs["corrected_from_offline_rescoring"] + vs["fell_back_to_live_score"]
    )


def test_rescore_coverage_labels_incomplete_data(late, tmp_path):
    out_path = tmp_path / "cov.json"
    argv = [
        "coverage", "--export", str(ROOT), "--analysis-dir", str(late["analysis"]),
        *run_dirs(late), "--records", str(late["records"]), "--plan", str(late["plan"]),
        *dr0s(late), "--out", str(out_path),
    ]  # fmt: skip
    assert RJ.main(argv) == 0
    labels = json.loads(out_path.read_text())["labels"]
    assert labels["incomplete"] == RR.INCOMPLETE
    assert "no records from A1-4B-S2" in labels["incomplete_reasons"]


def test_verdict_sources_split_checker_corrections_from_replay_mismatches():
    finals = {
        ("4B", "S1", "t1", "H-GA", 1): {
            "status": "scored",
            "score": 0.0,
            "corrected_score": 1.0,
            "slot": "a",
            "attempt": 1,
        },
        ("4B", "S1", "t2", "H-GA", 1): {
            "status": "scored",
            "score": 1.0,
            "corrected_score": 0.0,
            "slot": "b",
            "attempt": 1,
        },
        ("4B", "S1", "t3", "H-GA", 1): {
            "status": "scored",
            "score": 1.0,
            "corrected_score": None,
            "slot": "c",
            "attempt": 1,
        },
        ("4B", "S1", "t4", "H-GA", 1): {
            "status": "scored",
            "score": 1.0,
            "slot": "d",
            "attempt": 1,
        },
        ("4B", "S1", "t5", "H-GA", 1): {
            "status": "infrastructure",
            "score": None,
            "slot": "e",
            "attempt": 1,
        },
        ("4B", "S1", "t6", "H-GA", 1): {
            "status": "scored",
            "score": 0.0,
            "corrected_score": 1.0,
            "slot": "f",
            "attempt": 1,
        },
    }
    rows = RJ.rows_by_attempt(
        [
            {"slot": "a", "attempt": 1, "corrected_applies": True, "live_offline_match": True},
            {"slot": "b", "attempt": 1, "corrected_applies": False},
            {"slot": "f", "attempt": 1, "corrected_applies": True, "live_offline_match": False},
        ]
    )
    out = RJ.verdict_sources(finals, ["t1", "t2", "t3", "t4", "t5", "t6"], rows)
    assert out["fell_back_to_live_score"] == 2 and out["corrected_from_offline_rescoring"] == 3
    assert out["flips_by_task"] == {
        "t1": {"checker_correction": 1},
        "t2": {"replay_mismatch": 1},
        "t6": {"checker_correction": 1, RJ.RAW_REPLAY_ALSO_DIFFERS: 1},
    }
    assert out["flips_total"] == {
        "checker_correction": 2,
        RJ.RAW_REPLAY_ALSO_DIFFERS: 1,
        "replay_mismatch": 1,
    }


# --------------------------------------------------------------------------- section 15


def test_assemble_section_15(sc, tmp_path):
    guarded_dir = tmp_path / "report"
    argv = [
        "--export",
        str(ROOT),
        "--records",
        str(sc["records"]),
        "--plan",
        str(sc["plan"]),
        "--costs",
        str(sc["costs"]),
        "--out-dir",
        str(guarded_dir),
    ]
    for path in sc["dr0"]:
        argv += ["--dr0", str(path)]
    assert RR.main(argv) == 0
    out_path = tmp_path / "s15.json"
    argv = [
        "--export",
        str(ROOT),
        "--plan",
        str(sc["plan"]),
        "--records",
        str(sc["records"]),
        *run_dirs(sc),
        "--costs",
        str(sc["costs"]),
        "--analysis-dir",
        str(sc["analysis"]),
        "--report-guarded",
        str(guarded_dir / "report-guarded.json"),
        "--out",
        str(out_path),
    ]
    assert AS.main(argv) == 0
    out = json.loads(out_path.read_text())
    recs = R.read_jsonl(sc["records"])
    finals = R.final_records(recs)
    for item in (
        "dr0_per_job",
        "labels",
        "output_tokens",
        "steps",
        "restarts_per_episode",
        "observations_per_episode",
        "uncertified_exposure_per_episode",
        "losses_by_task",
        "cost_card_prices",
        "offline_setup_exclusions",
        "setup_and_postconfig_failures",
        "host_snapshots",
        "secondary_corrected",
        "per_domain",
        "rescoring",
        "checker_noise_set",
        "truncation",
        "dr3",
    ):
        assert item in out, item
    assert out["labels"] == {
        "incomplete": None,
        "incomplete_reasons": [],
        "external_anchor": A.NOT_ANCHORED,
    }
    assert set(out["dr0_per_job"]) - {"source"} == set(SY.JOBS)
    # tokens: the primary cell's completion total equals the records' sum
    cell = [
        r
        for k, r in finals.items()
        if k[2] in SY.BASE and r["status"] == "scored" and k[0] == "4B" and k[3] == "H-GA"
    ]
    tok = out["output_tokens"]["primary"]["4B/H-GA"]
    assert tok["completion"]["total"] == sum(r["tokens"]["completion"] for r in cell)
    # steps: censoring at 15 and the success distribution
    st = out["steps"]["primary"]["4B/H-GA"]
    assert st["step_of_termination"]["censored_at_15"] == sum(
        1 for r in cell if r["ended"] == "step_cap"
    )
    assert (
        sum(st["step_of_success"].values())
        == st["successes"]
        == sum(1 for r in cell if r["score"] == 1.0)
    )
    assert st["step_of_success"].get("censored_at_15", 0) == sum(
        1 for r in cell if r["score"] == 1.0 and r["ended"] == "step_cap"
    )
    # losses by task: attempts lost add up to the records' infrastructure attempts
    lost = sum(v["attempts_lost"] for v in out["losses_by_task"]["tasks"].values())
    assert lost == sum(1 for r in recs if r["status"] == "infrastructure")
    assert all(t in out["losses_by_task"]["tasks"] for t in SY.BASE)
    # prices
    job = out["cost_card_prices"]["jobs"]["A1-9B-S1"]
    assert job["price_central"] == 0.00902 and job["price_high"] == 0.011274
    assert job["ratio_to_central"] == round(job["gpu_h_per_episode"] / 0.00902, 4)
    assert out["offline_setup_exclusions"]["equals_plan_module_constant"] is True
    # snapshots: the pair is excluded, another user's job name is not copied
    snap = out["host_snapshots"]["A1-9B-S1"]
    jobs = {f["job"]: f for f in snap["summary"]["foreign_jobs"]}
    assert SY.GPU["A1-9B-S1"] not in jobs
    assert jobs["777"]["owner"] == "other user" and "name" not in jobs["777"]
    assert jobs["778"]["owner"] == "same user" and jobs["778"]["name"] == "q2s1a-next"
    assert "private-name" not in out_path.read_text()
    assert snap["summary"]["max_loadavg"] == [2.5, 1.5, 0.9]
    # failures by type
    fail = out["setup_and_postconfig_failures"]["attempts_total"]
    assert fail["infra_task_setup"] == sum(
        1 for r in recs if r.get("infrastructure_type") == "task_setup"
    )
    assert fail["setup_replies_failed"] == fail["infra_task_setup"]
    assert sum(fail["postconfig_failed_by_type"].values()) == fail["postconfig_replies_failed"]
    # the secondary set under corrected verdicts: registered estimands, guarded
    sec = out["secondary_corrected"]
    assert sec["tasks"] == len(SY.BASE) + 4 and "DR2" in sec and "X_4B" in sec["estimates"]
    assert sec["flips_per_task"] == A.corrected_flips(finals, SY.TASKS)
    # rescoring: flips split; impress tasks are the corrected family in the synthetic data
    for task, kinds in out["rescoring"]["secondary"]["flips_by_task"].items():
        assert set(kinds) <= {"checker_correction", "replay_mismatch", RJ.RAW_REPLAY_ALSO_DIFFERS}
        if "checker_correction" in kinds:
            assert SY.DOMAINS[task] == "libreoffice_impress"
    assert "every final record" in out["checker_noise_set"]["set"]
    base_only = out["truncation"]["base_only_description"]
    assert base_only == A.truncation_labels({k: r for k, r in finals.items() if k[2] in SY.BASE})
    assert (
        out["dr3"]["4B"]["D_b"]
        == json.loads((guarded_dir / "report.json").read_text())["primary"]["estimates"]["D_b_4B"]
    )


def test_assemble_on_incomplete_data_guards_the_extra_sets(late, tmp_path):
    out = AS.assemble(
        R.read_jsonl(late["records"]),
        json.loads(late["plan"].read_text()),
        O.run_dirs_by_job(late["runs"].values()),
        costs=None,
        analysis_dir=late["analysis"],
        guarded=None,
    )
    assert out["labels"]["incomplete"] == RR.INCOMPLETE
    sec = out["secondary_corrected"]
    assert "not_estimable" in sec["tests"]["session_signflip_p"][0]
    assert sec["DR5"]["outcome"] == RR.DR5_NOT_EVALUABLE
    assert "not_estimable" in out["cost_card_prices"]
    assert "not_estimable" in out["dr3"]
    base_missing = sum(
        v["base_slots_without_record"] for v in out["losses_by_task"]["tasks"].values()
    )
    assert base_missing == 0  # only the jobs present are expected


def test_step_distributions_censoring():
    recs = [
        {"steps": 3, "ended": "terminate_success", "score": 1.0},
        {"steps": 15, "ended": "step_cap", "score": 1.0},
        {"steps": 15, "ended": "step_cap", "score": 0.0},
        {"steps": 15, "ended": "terminate_failure", "score": 0.0},
    ]
    out = AS.step_distributions(recs)
    assert out["step_of_termination"] == {"03": 1, "15": 1, "censored_at_15": 2}
    assert out["step_of_success"] == {"03": 1, "censored_at_15": 1}
    assert out["steps"] == {"03": 1, "15": 3}
    # the sorted serialisation keeps the steps in numeric order
    assert list(json.loads(O.dumps(out))["step_of_termination"]) == ["03", "15", "censored_at_15"]
    assert out["successes"] == 2 and out["not_successful"] == 2


# --------------------------------------------------------------------------- GLMM


def test_glmm_inputs_use_the_registered_writer(sc, tmp_path):
    out_dir = tmp_path / "glmm-inputs"
    argv = [
        "write",
        "--export",
        str(ROOT),
        "--plan",
        str(sc["plan"]),
        "--records",
        str(sc["records"]),
        "--guard",
        str(write_guard(tmp_path / "guard.json", incomplete=True)),
        "--out-dir",
        str(out_dir),
    ]
    assert GI.main(argv) == 0
    recs = R.read_jsonl(sc["records"])
    finals = R.final_records(recs)
    expected = tmp_path / "expected.csv"
    G.write_csv(G.rows_from_records(finals, SY.BASE), expected)
    assert (out_dir / "primary.csv").read_bytes() == expected.read_bytes()
    meta = json.loads((out_dir / "inputs.json").read_text())
    assert meta["sets"]["secondary"]["tasks"] == len(SY.TASKS)
    assert meta["sets"]["primary"]["sessions"] == ["4B:S1", "4B:S2", "9B:S1", "9B:S2"]
    assert meta["registered_reading"].startswith("primary")
    assert meta["labels"]["incomplete"] == RR.INCOMPLETE


def test_glmm_container_captures_each_fit_exit_code(tmp_path, capsys):
    script = GI.container_script()
    assert f"for f in {' '.join(GI.SETS)}; do" in script
    assert "/inputs/$f.csv /out/glmm-$f.json 200 42" in script
    assert "echo $? >/out/$f.exit" in script and "exit 91" in script
    (tmp_path / "primary.csv").write_text("y\n")
    (tmp_path / "secondary.csv").write_text("y\n")
    argv = [
        "submit",
        "--dry-run",
        "--export",
        str(ROOT),
        "--inputs-dir",
        str(tmp_path),
        "--out-dir",
        "/runs/A/glmm-out",
        "--guard",
        str(write_guard(tmp_path / "guard.json")),
        "--out",
        str(tmp_path / "job.json"),
    ]
    assert GI.main(argv) == 0
    cmd = shlex.split(capsys.readouterr().out.strip())
    env = dict(item.split("=", 1) for item in cmd[4].removeprefix("--export=").split(",")[1:])
    assert env["Q2M_IMAGE_ID"] == O.GLMM_IMAGE_ID
    assert json.loads(bytes.fromhex(env["Q2M_ARGV_JSON_HEX"])) == ["sh", "-c", script]


def test_glmm_collect_checks_the_package_digest_and_reports_convergence(tmp_path):
    out_dir = tmp_path / "glmm-out"
    out_dir.mkdir()
    lock = ROOT / "program/evidence/2026-10-08/q2-stage1-g0/glmm/r-packages.json"
    shutil.copy(lock, out_dir / "r-packages.json")
    (out_dir / "r-packages.sha256").write_text(f"{O.R_PACKAGES_SHA256}  /opt/q2/r-packages.json\n")
    good = {
        "n_episodes": 500,
        "full": {"ok": True, "pdHess": True},
        "reduced": {"ok": True},
        "lrt_task_harness": {"p_value": 0.1, "both_converged": True},
        "bootstrap": {"refits_failed": 0, "refits_not_converged": 3, "refits_used": 200},
    }
    bad = {
        "n_episodes": 500,
        "full": {"ok": False, "pdHess": False},
        "reduced": {"ok": False},
        "lrt_task_harness": {"p_value": None, "both_converged": False},
        "bootstrap": {"refits_failed": 0, "refits_not_converged": 134, "refits_used": 200},
    }
    (out_dir / "glmm-primary.json").write_text(json.dumps(good))
    (out_dir / "glmm-secondary.json").write_text(json.dumps(bad))
    (out_dir / "primary.exit").write_text("0\n")
    (out_dir / "secondary.exit").write_text("1\n")
    out = GI.collect_summary(out_dir)
    assert out["r_packages"]["matches_registered"] and out["r_packages"]["matches_image_file"]
    assert out["fits"]["primary"]["exit_code"] == 0 and out["fits"]["secondary"]["exit_code"] == 1
    assert out["fits"]["primary"]["full"] == good["full"]
    assert "3 refits" in out["fits"]["primary"]["notes"][0]
    assert any("non-converged fit" in n for n in out["fits"]["secondary"]["notes"])
    guard = write_guard(tmp_path / "guard.json")
    argv = ["collect", "--out-dir", str(out_dir), "--guard", str(guard)]
    # before the job's receipt exists (the fits still running) collect writes nothing
    with pytest.raises(SystemExit, match="has not ended"):
        GI.main([*argv, "--out", str(tmp_path / "summary.json")])
    assert not (tmp_path / "summary.json").exists()
    receipt = {"job_id": "991", "image_id": O.GLMM_IMAGE_ID, "exit_status": 91}
    (out_dir / "receipt-991.json").write_text(json.dumps(receipt))
    assert GI.main([*argv, "--out", str(tmp_path / "summary.json")]) == 0
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["labels"]["incomplete"] is None
    assert summary["labels"]["external_anchor"] == A.NOT_ANCHORED
    (out_dir / "r-packages.json").write_text("{}")
    assert GI.collect_summary(out_dir)["r_packages"]["matches_registered"] is False
    # a package lock that differs from the registered one stops the analysis (exit 3)
    assert GI.main([*argv, "--out", str(tmp_path / "summary-bad.json")]) == 3
    bad = json.loads((tmp_path / "summary-bad.json").read_text())
    assert bad["r_packages"]["matches_registered"] is False


# --------------------------------------------------------------------------- provenance


def test_provenance_on_the_frozen_tree_and_plan(sc, tmp_path):
    out_path = tmp_path / "prov.json"
    argv = [
        "--export",
        str(ROOT),
        "--plan",
        str(REAL_PLAN),
        "--input",
        str(sc["records"]),
        "--out",
        str(out_path),
    ]
    assert PV.main(argv) == 0
    out = json.loads(out_path.read_text())
    assert out["registration"]["sha256"] == O.REGISTRATION_SHA256
    assert out["frozen_plan"]["recomputed_plan_sha256"] == O.PLAN_SHA256
    assert out["code_of_record"]["files"] > 60 and out["code_of_record"]["pass"]
    assert out["inputs"][str(sc["records"])]["sha256"] == O.sha256_file(sc["records"])
    assert {"python", "numpy", "scipy"} <= set(out["environment"])
    assert "run_report.py" in out["ops_files"]


def test_provenance_records_a_missing_input_and_the_labels(sc, tmp_path):
    out_path = tmp_path / "prov.json"
    pattern = tmp_path / "glmm-out" / "glmm-*.json"  # an unmatched glob reaches it literally
    argv = [
        "--export", str(ROOT), "--plan", str(REAL_PLAN), "--input", str(sc["records"]),
        "--input", str(pattern), "--guard", str(write_guard(tmp_path / "guard.json", True)),
        "--out", str(out_path),
    ]  # fmt: skip
    assert PV.main(argv) == 0
    out = json.loads(out_path.read_text())
    assert out["inputs_missing"] == [str(pattern)]
    assert out["inputs"][str(pattern)] == {"missing": True}
    assert out["inputs"][str(sc["records"])]["sha256"] == O.sha256_file(sc["records"])
    assert out["labels"]["incomplete"] == RR.INCOMPLETE


def test_provenance_refuses_another_plan(sc, tmp_path):
    out_path = tmp_path / "prov.json"
    argv = ["--export", str(ROOT), "--plan", str(sc["plan"]), "--out", str(out_path)]
    assert PV.main(argv) == 3
    assert json.loads(out_path.read_text())["frozen_plan"]["pass"] is False
