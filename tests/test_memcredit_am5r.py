"""Tests for am5-ablated-cost-v1 (scripts/memcredit_am5r.py): the config on top of am3g's and its
pins, the gate and the config binding, the pins inside the image, the step budgets, the held-out
artifact with its replay control, the validation and judge items, the gain side against AM4's
committed figures, the cost indicator, the paired test with Holm and the break-even share, the
power computation, the blind hand check (plan, sample, merge, join, confirmation), the replay
control (V3), the rerun rule, and extract, hand check and analyze end to end on toy runs (no GPU,
no vLLM, no LongMemEval text)."""

from __future__ import annotations

import copy
import gzip
import importlib.util
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import memcredit_am3 as am3  # noqa: E402
import memcredit_am3g as g  # noqa: E402
import memcredit_am5 as a5  # noqa: E402
import memcredit_am5r as r  # noqa: E402
import memcredit_keepset_search as ks  # noqa: E402
import memcredit_label_free as lf  # noqa: E402

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

AM5_EVIDENCE = ROOT / "program/evidence/2026-10-16/am5-evidence-ablated"

# --------------------------------------------------------------------------- config and pins


def test_config_loads_with_am3gs_readers_steps_and_models():
    config = r.load_config()
    base = g.load_config()
    assert config["readers"] == base["readers"] and config["models"] == base["models"]
    assert config["reader_sampling"] == base["reader_sampling"]
    by_id = {s["id"]: s for s in base["steps"]}
    assert tuple(s["id"] for s in config["steps"]) == r.STEP_IDS
    assert all(s == by_id[s["id"]] for s in config["steps"])
    assert "judge8" not in [s["id"] for s in config["steps"]]
    dev, held = config["populations"]["development"], config["populations"]["heldout"]
    a5_config = a5.load_config()
    assert dev["artifact_sha256"] == a5_config["population"]["artifact_sha256"]
    assert dev["question_ids_sha256"] == a5_config["population"]["question_ids_sha256"]
    assert held["control"]["artifact_sha256"] == dev["artifact_sha256"]
    assert held["question_ids_sha256"] == base["populations"]["heldout"]["question_ids_sha256"]
    assert held["source_artifact_sha256"] == base["populations"]["heldout"]["artifact_sha256"]
    assert dev["summary_sha256"] == r.sha256_file(AM5_EVIDENCE / "prepare/ablated-summary.json")


def _write_config(tmp_path: Path, mutate) -> Path:
    import yaml

    raw = yaml.safe_load(r.CONFIG_PATH.read_text())
    mutate(raw)
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(raw))
    return path


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.update(claim_level="exploratory"),
        lambda c: c.update(seeds=[1, 2, 3]),
        lambda c: c.update(steps=["rd-qwen3-8b", "rd-olmo2", "rd-qwen35-9b-default", "judge32"]),
        lambda c: c.update(steps=[*c["steps"], "judge8"]),
        lambda c: c["base"].update(config_sha256="0" * 64),
        lambda c: c["populations"]["heldout"].update(arms=["retrieved", "gold"]),
        lambda c: c["populations"]["heldout"].update(split="heldout"),
        lambda c: c["populations"]["development"].update(artifact_sha256="PENDING"),
        lambda c: c["populations"]["heldout"].update(artifact_sha256="PENDING"),
        lambda c: c["populations"]["heldout"].update(summary_sha256="PENDING"),
        lambda c: c["populations"]["heldout"]["control"].update(questions=62),
        lambda c: c["populations"]["heldout"]["reference"].update(name="another"),
        lambda c: c["populations"]["heldout"]["gain"]["expected"].pop("70"),
        lambda c: c["jobs"]["heldout"].update(gpus=2),
        lambda c: c["jobs"]["heldout"]["step_budgets"].update(judge32=[300, 480]),
        lambda c: c["analysis"].update(caps=[8, 16, 70]),
        lambda c: c["analysis"].update(primary_cap=70),
        lambda c: c["analysis"].update(alpha=0.1),
        lambda c: c["hand_check"].update(chunk=100),
        lambda c: c["hand_check"].update(secondary_fraction=0),
    ],
)
def test_config_refuses_changes(tmp_path, mutate):
    with pytest.raises((r.Am5rError, g.Am3gError, am3.Am3Error)):
        r.load_config(_write_config(tmp_path, mutate))


def test_reference_pins_are_am5s_committed_digests_of_job_1487():
    config = r.load_config()
    pins = config["populations"]["heldout"]["reference"]["sha256"]
    job = AM5_EVIDENCE / "jobs/1487-dev-ablated/am5"
    for step in ("rd-qwen3-8b", "rd-olmo2", "rd-qwen35-9b-default", "judge32"):
        lines = (job / "sessions" / step / "raw-sha256.txt").read_text().splitlines()
        raw = dict(line.split()[::-1] for line in lines)
        assert pins[f"sessions/{step}/all.npz"] == raw["./all.npz"]
        assert pins[f"sessions/{step}/all.texts.jsonl.gz"] == raw["./all.texts.jsonl.gz"]
    assert pins["judge-items.json"] == (job / "judge-items.sha256.txt").read_text().split()[0]
    am5 = config["populations"]["development"]["am5"]
    assert am5["results_sha256"] == r.sha256_file(AM5_EVIDENCE / "results.json")
    assert am5["per_table_sha256"] == r.sha256_file(AM5_EVIDENCE / "per-table.json.gz")
    assert am5["hand_labels_sha256"] == (AM5_EVIDENCE / "hand-check/hand-labels.sha256.txt"
                                         ).read_text().split()[0]  # fmt: skip
    assert am5["hand_plan_sha256"] == (AM5_EVIDENCE / "hand-check/hand-plan.sha256.txt"
                                       ).read_text().split()[0]  # fmt: skip


# --------------------------------------------------------------------------- the gain side


def test_the_gain_side_is_am4s_committed_k_curve():
    """The held-out gain indicators read from am3g's committed per-pool records equal AM4's
    committed b at K = 8 and 70 (and c = 0), per reader."""

    config = r.load_config()
    spec = config["populations"]["heldout"]["gain"]
    assert r.sha256_file(ROOT / spec["am4_results"]["path"]) == spec["am4_results"]["sha256"]
    am4 = json.loads((ROOT / spec["am4_results"]["path"]).read_text())
    rows = r.load_gain_rows(config, "heldout")
    ids = [x["question_id"] for x in rows if x["reader"] == "qwen3-8b"]
    assert len(ids) == 347 and r.ids_sha256(ids) == config["populations"]["heldout"][
        "question_ids_sha256"]  # fmt: skip
    gains = r.gains_of(config, "heldout", ids)
    for reader in r.READERS:
        for cap in r.CAPS:
            cell = am4["curve"][reader][str(cap)]["heldout"]["retrieved"]["primary"]
            assert sum(gains[reader][str(cap)].values()) == cell["rule_right_base_wrong"]
            assert cell["rule_wrong_base_right"] == 0
            assert sum(gains[reader][str(cap)].values()) == spec["expected"][str(cap)][reader]
        assert all(gains[reader]["70"][q] >= gains[reader]["8"][q] for q in ids)


def test_the_development_gain_side_is_am5s_original_block():
    config = r.load_config()
    committed = json.loads((AM5_EVIDENCE / "results.json").read_text())
    rows = r.load_gain_rows(config, "development")
    ids = [x["question_id"] for x in rows if x["reader"] == "qwen3-8b"]
    gains = r.gains_of(config, "development", ids)
    for reader in r.READERS:
        for cap in r.CAPS:
            orig = committed["readers"][reader]["original"]["caps"][str(cap)]
            assert sum(gains[reader][str(cap)].values()) == orig["gained_b"]
            assert orig["lost_c"] == 0


def test_a_gain_side_other_than_the_pinned_one_is_void(monkeypatch):
    config = r.load_config()
    rows = r.load_gain_rows(config, "heldout")
    ids = [x["question_id"] for x in rows if x["reader"] == "qwen3-8b"]
    flipped = copy.deepcopy(rows)
    victim = next(x for x in flipped if x["reader"] == "qwen3-8b" and r.gain_of(x, 8)[0])
    victim["u"]["primary"]["nonabstain_bm25"] = 0  # a gain disappears
    monkeypatch.setattr(r, "load_gain_rows", lambda c, p: flipped)
    with pytest.raises(r.Am5rError, match="V1"):
        r.gains_of(config, "heldout", ids)
    with pytest.raises(r.Am5rError, match="V1"):
        r.gains_of(config, "heldout", ids[:-1])


def test_gain_of_reads_the_records_as_am4s_crosscheck():
    row = {"first_answer_position": 5, "nonabstain_mask": 23, "bm25_top4_mask": 15,
           "u": {"primary": {"bm25_top4": 0, "nonabstain_bm25": 1}}}  # fmt: skip
    assert r.gain_of(row, 8) == (1, 0) and r.gain_of(row, 4) == (0, 0)
    row["first_answer_position"] = 1
    row["nonabstain_mask"] = 15
    assert r.gain_of(row, 8) == (0, 0)


# --------------------------------------------------------------------------- budgets and caps


def _simulate(config: dict, path: str) -> dict:
    """Worst case of the held-out job under budget.overhead_model: every step takes its overhead
    plus its full max_s, and the driver's GPU-memory release wait after it (run_step) its full 120
    s. path: "normal"; "fallback" (OLMo-2's batch-invariant engine fails to start, then its
    default-mode step runs); "capped-fallback" (OLMo-2's batch-invariant pass is stopped by its
    max_s, then the fallback runs)."""

    job = config["jobs"]["heldout"]
    over = config["budget"]["overhead_model"]["heldout"]
    deadline = job["minutes"] * 60 - 210
    t = over["job"]
    started, skipped = {}, []
    order = ["rd-qwen3-8b", "rd-olmo2"] + (["rd-olmo2-default"] if path != "normal" else [])
    order += ["rd-qwen35-9b-default", "judge32"]
    for sid in order:
        min_start, max_s = job["step_budgets"][sid]
        if deadline - t < min_start:
            skipped.append(sid)
            continue
        started[sid] = deadline - t
        if sid == "rd-olmo2" and path == "fallback":
            t += over["failed_engine_step"]
        else:
            t += over["judge32" if sid == "judge32" else "reader"] + max_s
        t += over["release"]
    return {"started": started, "skipped": skipped, "end": t, "deadline": deadline}


def test_the_release_wait_is_run_steps():
    import inspect

    source = inspect.getsource(r.run_step)
    assert "release_until = time.time() + 120" in source
    assert r.load_config()["budget"]["overhead_model"]["heldout"]["release"] == 120


@pytest.mark.parametrize("path", ["normal", "fallback", "capped-fallback"])
def test_the_judge_starts_and_fits_on_every_path(path):
    config = r.load_config()
    over = config["budget"]["overhead_model"]["heldout"]
    for sid, (min_start, max_s) in config["jobs"]["heldout"]["step_budgets"].items():
        assert min_start >= over["judge32" if sid == "judge32" else "reader"] + max_s, sid
    run = _simulate(config, path)
    assert run["skipped"] == [] and "judge32" in run["started"]
    assert run["end"] <= run["deadline"]


def test_the_development_job_fits_job_1487s_timeline():
    """The dry run repeats job 1487 under a 13-minute limit: with job 1487's measured step starts
    and durations every step starts with its min_start_s left and the job ends before the
    deadline."""

    config = r.load_config()
    job = config["jobs"]["development"]
    summary = json.loads((AM5_EVIDENCE / "jobs/1487-dev-ablated/am5/summary.json").read_text())
    scontrol = (AM5_EVIDENCE / "jobs/1487-dev-ablated/scontrol.txt").read_text()
    runtime = next(x.split("=")[1] for x in scontrol.split() if x.startswith("RunTime="))
    h, m, s = (int(x) for x in runtime.split(":"))
    finished = g._iso_seconds(summary["finished_at"])
    start = finished - (h * 3600 + m * 60 + s)
    deadline = start + job["minutes"] * 60 - 210
    for sid, rec in summary["steps"].items():
        if rec["status"] == "not-needed":
            continue
        at = g._iso_seconds(rec["started_at"])
        min_start, max_s = job["step_budgets"][sid]
        assert deadline - at >= min_start, sid
        assert rec["wall_s"] < max_s + 60, sid
    assert finished <= deadline


def test_the_caps_are_the_limits():
    config = r.load_config()
    caps, jobs = config["budget"], config["jobs"]
    assert caps["registered_cap_gpu_hours"] == round(
        (jobs["heldout"]["minutes"] + caps["build_minutes"]) / 60, 2
    )
    assert caps["registered_cap_with_reruns_gpu_hours"] == round(
        2 * (jobs["heldout"]["minutes"] + caps["build_minutes"]) / 60, 2
    )
    assert caps["dry_run_cap_gpu_hours"] == round(
        (jobs["development"]["minutes"] + caps["build_minutes"]) / 60, 2
    )
    assert caps["dry_run_cap_gpu_hours"] <= 0.3


# --------------------------------------------------------------------------- the gate


def _scratch(tmp_path: Path, frozen: bool) -> tuple[Path, Path]:
    reg = tmp_path / "registration.md"
    reg.write_bytes((ROOT / r.REGISTRATION).read_bytes())
    ledger = tmp_path / "ledger.jsonl"
    row = {"experiment_id": r.EXPERIMENT, "sha256": r.sha256_file(reg)}
    ledger.write_text(json.dumps(row) + "\n" if frozen else "")
    return reg, ledger


def test_the_heldout_population_is_refused_before_the_freeze(tmp_path, monkeypatch):
    """Every entry point that runs a model on the held-out population or reads its outputs
    refuses at the gate first; Path.read_bytes is made to fail so that a read before the gate
    would be caught."""

    reg, ledger = _scratch(tmp_path, frozen=False)
    monkeypatch.setattr(r, "LEDGER", ledger)
    monkeypatch.setattr(r, "REGISTRATION", reg)
    with pytest.raises(r.Am5rError, match="after the freeze"):
        r.gate("heldout")
    dummy = tmp_path / "artifact.json"
    dummy.write_text("{}")

    def no_read(self):
        raise AssertionError(f"read before the gate: {self}")

    monkeypatch.setattr(Path, "read_bytes", no_read)
    out = tmp_path / "out"
    argvs = [
        ["run", "--population", "heldout", "--seeds", "42", "43", "44", "--output-dir",
         str(out), "--allocation-minutes", "10", "--evidence", str(dummy),
         "--expected-evidence-sha256", "0" * 64],
        ["extract", "--population", "heldout", "--run-dir", str(tmp_path), "--evidence",
         str(dummy), "--summary", str(dummy), "--private-dir", str(tmp_path / "p"),
         "--reference-run-dir", str(tmp_path), "--rerun-decision", str(dummy)],
        ["hand-sample", "--population", "heldout", "--run-dir", str(tmp_path), "--evidence",
         str(dummy), "--features", str(dummy), "--hand-dir", str(tmp_path / "h")],
        ["analyze", "--population", "heldout", "--features", str(dummy), "--output-dir",
         str(out)],
    ]  # fmt: skip
    for argv in argvs:
        assert r.main(argv) == 2
    assert not out.exists() and not (tmp_path / "p").exists() and not (tmp_path / "h").exists()
    assert r.gate("development") == {"population": "development", "frozen_required": False}


def test_the_gate_opens_with_a_scratch_ledger_row_and_matching_pins(tmp_path):
    reg, ledger = _scratch(tmp_path, frozen=True)
    record = r.gate("heldout", ledger=ledger, registration=reg)
    assert record["registration_frozen"] and record["code_pins"]["all_match"]
    tampered = tmp_path / "tampered.md"
    good = ks.code_pins(reg)["scripts/memcredit_am5r.py"]
    tampered.write_text(reg.read_text().replace(good, "0" * 64))
    ledger.write_text(json.dumps({"experiment_id": r.EXPERIMENT,
                                  "sha256": r.sha256_file(tampered)}) + "\n")  # fmt: skip
    with pytest.raises(r.Am5rError, match="pins"):
        r.gate("heldout", ledger=ledger, registration=tampered)


def test_the_feature_code_is_the_whole_import_closure_and_pinned():
    code = (
        "import sys, pathlib; root = pathlib.Path(sys.argv[1]).resolve(); "
        "sys.path[:0] = [str(root), str(root / 'scripts')]; "
        "import memcredit_am5r, memcredit_study; "
        "print('\\n'.join(sorted(str(pathlib.Path(m.__file__).resolve().relative_to(root)) "
        "for m in list(sys.modules.values()) if getattr(m, '__file__', None) "
        "and pathlib.Path(m.__file__).resolve().is_relative_to(root) "
        "and 'site-packages' not in pathlib.Path(m.__file__).resolve().parts)))"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT)], capture_output=True,
                         text=True, check=True, cwd=ROOT)  # fmt: skip
    assert sorted(r.FEATURE_CODE) == out.stdout.split()
    pins = ks.code_pins(ROOT / r.REGISTRATION)
    assert all(path in pins for path in r.FEATURE_CODE)
    assert "experiments/am5/am5-ablated-cost-v1.yaml" in pins


def test_every_code_pin_is_in_the_image():
    """The GPU job's gate checks every pin inside the image, which the overlay build makes from
    the capsule minus .dockerignore's entries: no pin may sit under one."""

    ignored = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text().splitlines()
        if line.strip() and not line.startswith(("#", "!")) and not set(line) & set("*?[")
    }
    pins = ks.code_pins(ROOT / r.REGISTRATION)
    assert "legacy" in ignored
    for path in pins:
        parts = Path(path).parts
        assert not any("/".join(parts[: i + 1]) in ignored for i in range(len(parts))), path
        assert (ROOT / path).is_file(), path


def test_registration_freezes_on_a_scratch_ledger(tmp_path):
    spec = importlib.util.spec_from_file_location("preregister", ROOT / "scripts/preregister.py")
    prereg = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(prereg)
    ledger = tmp_path / "ledger.jsonl"
    row = prereg.freeze(ROOT / r.REGISTRATION, r.EXPERIMENT, ledger=ledger, root=ROOT)
    assert row["experiment_id"] == r.EXPERIMENT


def test_heldout_commands_refuse_another_config(tmp_path, capsys):
    other = tmp_path / "config.yaml"
    other.write_text(r.CONFIG_PATH.read_text())
    for argv in (["extract", "--population", "heldout", "--run-dir", "x", "--evidence", "x",
                  "--summary", "x", "--private-dir", str(tmp_path / "p"), "--rerun-decision", "x"],
                 ["analyze", "--population", "heldout", "--features", "x", "--output-dir",
                  str(tmp_path / "o")],
                 ["selftest", "--population", "heldout", "--evidence", "x"],
                 ["hand-sample", "--population", "heldout", "--run-dir", "x", "--evidence", "x",
                  "--features", "x", "--hand-dir", str(tmp_path / "h")]):  # fmt: skip
        assert r.main([*argv, "--config", str(other)]) == 2
        assert "pinned config" in capsys.readouterr().err


@pytest.mark.parametrize(
    "path",
    [
        "/x/am5-ablated-cost-v1/inputs/heldout-ablated-artifact.json",
        "/x/am1-memory-credit-v1/study-artifact.json",
        "/x/am3-nonabstain-generality-v1/per-table.json.gz",
    ],
)
def test_the_development_population_refuses_heldout_paths(path):
    with pytest.raises(r.Am5rError):
        r.check_dev_path(path)


def test_private_outputs_stay_outside_the_repository(tmp_path):
    r.refuse_inside_repo(tmp_path / "private")
    with pytest.raises(r.Am5rError):
        r.refuse_inside_repo(ROOT / "private")


# --------------------------------------------------------------------------- the held-out artifact


def _turn(text: str, role: str = "user", has_answer: bool = False) -> dict:
    t = {"role": role, "content": text}
    if has_answer:
        t["has_answer"] = True
    return t


def _toy_record(qid: str, qtype: str = "multi-session") -> dict:
    sessions, ids, dates = [], [], []
    for s in range(12):
        sid = f"{qid}-s{s}" if s not in (3, 7) else f"{qid}-ans{s}"
        turns = [_turn(f"session {s} about apples {s} and pears {qid}"),
                 _turn(f"assistant reply {s}", role="assistant"),
                 _turn(f"more apples {s} weather chat {qid}")]  # fmt: skip
        if s in (3, 7):
            turns.append(_turn(f"my favourite colour is blue, session {s}", has_answer=True))
        sessions.append(turns)
        ids.append(sid)
        dates.append(f"2023/05/{s + 1:02d} (Mon) 10:00")
    return {"question_id": qid, "question_type": qtype,
            "question": f"What is my favourite colour, apples {qid}?", "answer": "blue",
            "question_date": "2023/06/01 (Thu) 10:00",
            "answer_session_ids": [f"{qid}-ans3", f"{qid}-ans7"], "haystack_sessions": sessions,
            "haystack_session_ids": ids, "haystack_dates": dates}  # fmt: skip


def test_the_heldout_artifact_ablates_in_am1s_order_and_appends_the_control_unchanged():
    pilot = g.load_pilot_config(g.load_config())
    records = [_toy_record(f"q{i}") for i in range(4)]
    control_artifact, _ = a5.build_artifact(records, pilot, {"development": ["q3", "q2"]})
    control = {**control_artifact, "question_ids_sha256": r.ids_sha256(["q3", "q2"])}
    artifact, facts = r.build_heldout_artifact(records, pilot, ["q1", "q0"], control)
    assert [q["question_id"] for q in artifact["questions"]] == ["q1", "q0", "q3", "q2"]
    assert artifact["parts"] == {"main": [0, 2], "control": [2, 4]}
    assert artifact["questions"][2:] == control_artifact["questions"]
    for q, f in zip(artifact["questions"][:2], facts, strict=True):
        assert all("-ans" not in m["session_id"] for m in q["pools"]["retrieved"])
        assert f["has_answer_turns_after"] == 0 and f["sessions_removed"] == 2
        assert q["pools"]["retrieved"] == g.retrieved_pool(
            a5.ablate(records[int(q["question_id"][1])])[0], ms.pool_config(pilot)
        )
    summary = r.heldout_summary(artifact, "0" * 64, facts, pilot)
    assert summary["questions"] == 2 and summary["parts"] == artifact["parts"]
    assert summary["leakage"]["has_answer_turns_left_in_the_haystack"] == 0
    blob = json.dumps(summary)
    for text in ("favourite colour", "apples", "weather chat"):
        assert text not in blob


# --------------------------------------------------------------------------- toy runs


TYPES = ("multi-session", "temporal-reasoning", "single-session-preference")


def _toy_question(qid: str, k: int) -> dict:
    pool = [{"session_id": f"s{i}", "session_index": i, "turn_index": 0,
             "date": f"2023/05/{i + 1:02d} (Mon) 10:00", "is_gold": False,
             "bm25_rank": (i * 3 + k) % 8, "bm25_score": 1.0, "chars": 10, "truncated": False,
             "text": f"memory {i} of {qid}", "text_sha256": "x"} for i in range(8)]  # fmt: skip
    return {"question_id": qid, "question_type": TYPES[k % 3], "question": f"question {qid}?",
            "question_date": "2023/06/01", "answer": f"blue {qid}", "abstention": False,
            "pools": {"retrieved": pool}}  # fmt: skip


def _toy_artifact(population: str, n: int, m: int = 3) -> dict:
    main = [_toy_question(f"h{i:02d}", i) for i in range(n)]
    if population == "development":
        return {"experiment_id": "am5-evidence-ablated-dev", "split": "dev-ablated",
                "questions": main}  # fmt: skip
    control = [_toy_question(f"c{i}", i + 1) for i in range(m)]
    return {
        "experiment_id": r.EXPERIMENT,
        "split": "heldout-ablated",
        "parts": {"main": [0, n], "control": [n, n + m]},
        "questions": main + control,
    }


def _reply(reader: str, qid: str, mask: int) -> str:
    """Mostly abstentions; a few answers per pool, some of them the reference, and refusals that
    the four patterns do not catch."""

    h = int(r.sha256_text(f"{reader}:{qid}:{mask}")[:6], 16) % 100
    if mask == g.FULL or h < 80:
        return "I don't know."
    if h < 86:
        return f"It is blue {qid}."
    if h < 92:
        return f"It is green {qid} {reader}."
    return f"Sorry, nothing about that for {qid}."


def _write_run(directory: Path, artifact: dict, population: str, config: dict,
               replies=_reply) -> dict:  # fmt: skip
    from test_memcredit_am3 import _write_pass

    pilot = g.load_pilot_config(config)
    run = directory
    steps = {
        "rd-qwen3-8b": {"kind": "reader", "reader": "qwen3-8b", "status": "complete",
                        "batch_invariant": True, "enforce_eager": True},
        "rd-olmo2": {"kind": "reader", "reader": "olmo-2-1124-7b-instruct",
                     "status": "complete", "batch_invariant": True, "enforce_eager": True},
        "rd-olmo2-default": {"kind": "reader", "status": "not-needed"},
        "rd-qwen35-9b-default": {"kind": "reader", "reader": "qwen3.5-9b", "status": "complete",
                                 "batch_invariant": False, "enforce_eager": True},
        "judge32": {"kind": "judge", "status": "complete"},
    }  # fmt: skip
    run.mkdir(parents=True)
    (run / "summary.json").write_text(json.dumps(
        {"experiment_id": r.EXPERIMENT, "population": population, "steps": steps}))  # fmt: skip
    passes = {}
    for sid, reader in (("rd-qwen3-8b", "a"), ("rd-olmo2", "b"), ("rd-qwen35-9b-default", "c")):
        rows = {}
        for req in r.request_table(artifact):
            text = replies(reader, req["question_id"], req["mask"])
            rows[req["index"]] = ([100 + len(text) % 7, 151645], [-0.1, -0.01], "stop", text)
        _write_pass(run / "sessions" / sid, rows)
        passes[sid] = {i: row[3] for i, row in rows.items()}
    items = r.judge_items(config, population, artifact, pilot, passes)
    (run / "judge-items.json").write_text(json.dumps(items))
    rows = {}
    for item in items:
        q = artifact["questions"][item["question_index"]]
        yes = q["answer"] in item["response"].lower()
        rows[item["index"]] = ([7], [-0.01], "stop", "yes" if yes else "no")
    _write_pass(run / "sessions" / "judge32", rows)
    return passes


def _reference(
    tmp_path: Path, artifact: dict, config: dict, population: str, replies=_reply
) -> tuple[Path, dict]:
    """A toy job 1487: the control part's requests alone, with the same replies, judged."""

    ctrl = r.control_range(config, population)
    view = {"experiment_id": "am5-evidence-ablated-dev", "split": "dev-ablated",
            "questions": artifact["questions"][ctrl.start : ctrl.stop]}  # fmt: skip
    dev_config = copy.deepcopy(config)
    dev_config["populations"]["development"]["questions"] = len(ctrl)
    ref = tmp_path / "ref1487"
    _write_run(ref, view, "development", dev_config, replies)
    names = [
        f"sessions/{s}/{f}"
        for s in ("rd-qwen3-8b", "rd-olmo2", "rd-qwen35-9b-default", "judge32")
        for f in ("all.json", "all.npz", "all.texts.jsonl.gz")
    ] + ["judge-items.json"]
    return ref, {n: r.sha256_file(ref / n) for n in names}


def _toy_gain_rows(artifact: dict, config: dict, population: str) -> tuple[list[dict], dict]:
    rows, expected = [], {"8": {}, "70": {}}
    main = r.parts_of(config, population)["main"]
    for reader in r.READERS:
        for i, q in enumerate(artifact["questions"][main.start : main.stop]):
            gain = i % 4 == 0
            pos = 3 if gain else 1
            if i % 4 == 2:
                gain, pos = True, 20  # a gain only beyond K = 8
            rows.append({"reader": reader, "arm": "retrieved", "question_id": q["question_id"],
                         "population": "heldout", "first_answer_position": pos,
                         "bm25_top4_mask": 15, "nonabstain_mask": 23 if gain else 15,
                         "u": {"primary": {"bm25_top4": 0 if gain else 1,
                                           "nonabstain_bm25": 1}}})  # fmt: skip
        mine = [x for x in rows if x["reader"] == reader]
        for cap in r.CAPS:
            expected[str(cap)][reader] = sum(r.gain_of(x, cap)[0] for x in mine)
    return rows, expected


def _pipeline(tmp_path, monkeypatch, population: str = "heldout", n: int = 12, m: int = 3,
              replies=_reply, ref_replies=None):  # fmt: skip
    config = r.load_config()
    config["analysis"]["bootstrap"]["resamples"] = 200
    spec = config["populations"][population]
    spec["questions"] = n
    if population == "heldout":
        spec["control"]["questions"] = m
    artifact = _toy_artifact(population, n, m)
    main = r.parts_of(config, population)["main"]
    spec["question_ids_sha256"] = r.ids_sha256(
        [q["question_id"] for q in artifact["questions"][main.start : main.stop]])  # fmt: skip
    if population == "heldout":
        ctrl = r.parts_of(config, population)["control"]
        spec["control"]["question_ids_sha256"] = r.ids_sha256(
            [q["question_id"] for q in artifact["questions"][ctrl.start : ctrl.stop]]
        )
    spec["artifact_sha256"] = "a" * 64
    ref, digests = _reference(tmp_path, artifact, config, population, ref_replies or replies)
    for p in config["populations"].values():
        p["reference"]["sha256"] = digests
    gain_rows, expected = _toy_gain_rows(artifact, config, population)
    spec["gain"]["expected"] = expected
    summary = tmp_path / "prepare-summary.json"
    zero = {
        "pool_has_answer_memories": 0,
        "pool_memories_containing_the_answer": 0,
        "remaining_user_turns_containing_the_answer": 0,
        "answer_normalized_tokens": 2,
        "memories_shared_with_the_original_pool": 3,
        "original_pool_has_answer_memories": 1,
    }
    facts = [
        {"facts": {"question_id": q["question_id"], "question_type": q["question_type"], **zero}}
        for q in artifact["questions"][main.start : main.stop]
    ]
    summary.write_text(
        json.dumps(
            {
                "artifact_sha256": "a" * 64,
                "leakage": {"questions": n},
                "per_question": facts,
                "heldout_retrieved_pool_check": {"questions": n},
            }
        )
    )
    spec["summary_sha256"] = r.sha256_file(summary)
    monkeypatch.setattr(r, "load_config", lambda *a, **k: copy.deepcopy(config))
    monkeypatch.setattr(r, "load_artifact", lambda *a, **k: artifact)
    monkeypatch.setattr(r, "gate", lambda *a, **k: {"population": population})
    monkeypatch.setattr(r, "check_dev_path", lambda *a, **k: None)
    monkeypatch.setattr(r, "load_gain_rows", lambda c, p: gain_rows)
    run = tmp_path / "runs" / population / "1600" / r.OUTPUT
    _write_run(run, artifact, population, config, replies)
    decision = tmp_path / f"rerun-decision-{population}-1600.json"
    decision.write_text(json.dumps({"population": population, "job_dir": "1600",
                                    "decision": "complete"}))  # fmt: skip
    private = tmp_path / "private"
    brief = r.cmd_extract(r.argparse.Namespace(
        config=str(r.CONFIG_PATH), population=population, run_dir=str(run), evidence="x",
        summary=str(summary), private_dir=str(private), reference_run_dir=str(ref),
        rerun_decision=str(decision)))  # fmt: skip
    features_path = private / f"features-{population}.json.gz"
    assert brief["features_sha256"] == r.sha256_file(features_path)
    assert brief["job_id"] == "1600"
    return {
        "config": config,
        "artifact": artifact,
        "run": run,
        "features": features_path,
        "ref": ref,
        "summary": summary,
        "brief": brief,
        "decision": decision,
        "population": population,
    }


def test_extract_splits_the_control_off_and_replays_it(tmp_path, monkeypatch):
    ctx = _pipeline(tmp_path, monkeypatch)
    features = r.read_gz_json(ctx["features"])
    for reader in r.READERS:
        assert len(features["readers"][reader]["pools"]) == 12
        assert len(features["readers"][reader]["control_pools"]) == 3
        assert features["readers"][reader]["pools"][0]["question_id"] == "h00"
        assert features["readers"][reader]["control_pools"][0]["question_id"] == "c0"
    replay = features["replay"]
    assert replay["pass"] and replay["anchor_r1"] and replay["anchor_r2"]
    assert replay["control_cells"] == 3 * 71
    for d in replay["readers"].values():
        assert d["r1"] and d["r2"] and d["identical_bits"] == 3 * 71
    j = replay["judge_item_replay"]["primary"]
    assert j["compared"] > 0 and j["compared"] == j["same"]
    v = features["validation"]
    assert v["judge_validation"]["validation:reference"]["items"] == 8  # preference left out
    assert v["judge_validation_control"]["validation:idk"]["items"] == 3
    r.check_features(features, ctx["config"], "heldout")


def test_a_replay_difference_fails_v3(tmp_path, monkeypatch):
    def changed(reader, qid, mask):
        if reader == "a" and qid == "c1" and mask == 15:
            return "Something else entirely."
        return _reply(reader, qid, mask)

    ctx = _pipeline(tmp_path, monkeypatch, replies=changed, ref_replies=_reply)
    features = r.read_gz_json(ctx["features"])
    assert not features["replay"]["pass"] and not features["replay"]["anchor_r1"]
    assert features["replay"]["readers"]["olmo-2-1124-7b-instruct"]["r1"]
    results, _ = r.analyze_population(features, ctx["config"], "heldout", None, None)
    assert results["primary"]["status"].startswith("VOID (V3")
    assert set(results["verdicts"]["primary_k8"].values()) >= {"VOID"}


def test_the_replay_reference_files_are_checked(tmp_path, monkeypatch):
    ctx = _pipeline(tmp_path, monkeypatch)
    (ctx["ref"] / "judge-items.json").write_text("[]")
    with pytest.raises(g.Am3gError, match="V1"):
        r.cmd_extract(r.argparse.Namespace(
            config="x", population="heldout", run_dir=str(ctx["run"]), evidence="x",
            summary=str(ctx["summary"]), private_dir=str(tmp_path / "p2"),
            reference_run_dir=str(ctx["ref"]), rerun_decision=str(ctx["decision"])))  # fmt: skip


def test_validation_items_are_am1s_per_part():
    config = r.load_config()
    pilot = g.load_pilot_config(config)
    artifact = _toy_artifact("heldout", 6, 4)
    config["populations"]["heldout"]["questions"] = 6
    config["populations"]["heldout"]["control"]["questions"] = 4
    items = r.validation_items(config, "heldout", artifact, pilot)
    spec = pilot["judge"]["validation"]
    main = ms.validation_items({"questions": artifact["questions"][:6]}, spec)
    ctrl = ms.validation_items({"questions": artifact["questions"][6:]}, spec)
    assert items == main + [dict(i, question_index=i["question_index"] + 6) for i in ctrl]
    assert all(artifact["questions"][i["question_index"]]["question_id"].startswith("c")
               for i in items[len(main):])  # fmt: skip


def test_development_judge_items_are_am5s(tmp_path):
    config = r.load_config()
    pilot = g.load_pilot_config(config)
    artifact = _toy_artifact("development", 5)
    config["populations"]["development"]["questions"] = 5
    passes = {sid: {req["index"]: _reply(x, req["question_id"], req["mask"])
                    for req in r.request_table(artifact)}
              for sid, x in (("rd-qwen3-8b", "a"), ("rd-olmo2", "b"))}  # fmt: skip
    assert r.judge_items(config, "development", artifact, pilot, passes) == a5.judge_items(
        artifact, pilot, passes
    )
    assert r.request_table(artifact) == g.request_table(artifact, ("retrieved",))


def test_judge_message_is_the_answer_check_template_only():
    artifact = {
        "questions": [
            {
                "question_id": "q1",
                "question_type": "multi-session",
                "question": "How many?",
                "answer": "3",
                "abstention": False,
            }
        ]
    }
    item = {"question_index": 0, "response": "Three."}
    assert r.judge_message(artifact, item) == ms.judge_prompt("multi-session", "How many?", "3",
                                                              "Three.")  # fmt: skip
    with pytest.raises(r.Am5rError):
        r.judge_message(artifact, {**item, "template": "abstention"})


# --------------------------------------------------------------------------- cost and readings


def _record(qid: str, switched8: bool, switched70: bool, u: int, top4_abstains: bool = True):
    caps = {}
    for cap, sw in (("8", switched8), ("70", switched70)):
        caps[cap] = {"mask": 23 if sw else 15, "reads": 3, "switched": sw,
                     "kept_abstains": not sw and top4_abstains, "u": u if sw else 0,
                     "digest": f"d-{qid}" if sw else f"t-{qid}"}  # fmt: skip
    return {"question_id": qid, "question_type": "multi-session", "bm25_top4_mask": 15,
            "bm25_top4_abstains": top4_abstains, "first_answer_position": 3, "caps": caps,
            "digest": {"bm25_top4": f"t-{qid}", "all_8": f"a-{qid}"},
            "u": {"bm25_top4": 0, "all_8": 0}}  # fmt: skip


def test_the_cost_indicator_is_a_switch_the_judge_rejects():
    assert r.cost_indicator(_record("q", True, True, 0), 8) == 1
    assert r.cost_indicator(_record("q", True, True, 1), 8) == 0
    assert r.cost_indicator(_record("q", False, True, 0), 8) == 0
    assert r.cost_indicator(_record("q", False, True, 0), 70) == 1
    with pytest.raises(r.Am5rError):
        r.cost_indicator(_record("q", True, True, 0, top4_abstains=False), 8)


def test_the_paired_reading_labels_the_direction():
    n = 200
    gain = {f"q{i}": int(i < 30) for i in range(n)}
    below = {f"q{i}": int(100 <= i < 105) for i in range(n)}
    above = {f"q{i}": int(100 <= i < 160) for i in range(n)}
    e = r.paired(below, gain, 500, 42)
    assert (e["cost_only"], e["gain_only"], e["both"]) == (5, 30, 0)
    assert e["unadjusted_label"] == r.COST_BELOW and e["one_sided_97_5"]["upper"] < 0
    assert e["difference"] == pytest.approx((5 - 30) / n)
    e = r.paired(above, gain, 500, 42)
    assert e["unadjusted_label"] == r.COST_ABOVE and e["one_sided_97_5"]["lower"] > 0
    both = {f"q{i}": int(i < 30) for i in range(n)}
    e = r.paired(both, gain, 500, 42)
    assert e["both"] == 30 and e["cost_only"] == e["gain_only"] == 0
    assert e["unadjusted_label"] == r.NOT_SEPARATED and e["p_exact_mcnemar"] == 1.0


def test_the_exact_interval_and_the_test_agree():
    """The exact conditional 95% interval excludes 0 exactly when the two-sided p <= 0.05."""

    n = 100
    for b in range(0, 11, 2):
        for c in range(0, 11):
            cost = {f"q{i}": int(i < b) for i in range(n)}
            gain = {f"q{i}": int(50 <= i < 50 + c) for i in range(n)}
            e = r.paired(cost, gain, 50, 1)
            lo, hi = e["ci95_exact_conditional"]
            if b + c == 0:
                continue
            assert (e["p_exact_mcnemar"] <= 0.05) == (lo > 0 or hi < 0), (b, c)


def test_holm_across_the_three_readers():
    n = 300
    gain = {f"q{i}": int(i < 31) for i in range(n)}
    costs = {
        "qwen3-8b": {f"q{i}": int(200 <= i < 202) for i in range(n)},
        "olmo-2-1124-7b-instruct": {f"q{i}": int(200 <= i < 227) for i in range(n)},
        "qwen3.5-9b": {f"q{i}": int(200 <= i < 212) for i in range(n)},
    }
    fam = r.family_readings(costs, {k: gain for k in costs}, 300, 42)
    labels = {k: v["label"] for k, v in fam["readers"].items()}
    assert labels["qwen3-8b"] == r.COST_BELOW
    assert labels["olmo-2-1124-7b-instruct"] == r.NOT_SEPARATED
    p = {k: v["p_exact_mcnemar"] for k, v in fam["readers"].items()}
    holm = g.holm(p)
    assert all(fam["readers"][k]["holm"] == holm[k] for k in p)
    assert labels["qwen3.5-9b"] == (r.COST_BELOW if holm["qwen3.5-9b"]["reject"]
                                    else r.NOT_SEPARATED)  # fmt: skip


def test_the_break_even_share():
    gain = {f"q{i}": int(i < 30) for i in range(300)}
    cost = {f"q{i}": int(100 <= i < 110) for i in range(300)}
    be = r.break_even_share(cost, gain, 400, 42)
    assert be["break_even_share"] == pytest.approx(30 / 40)
    assert be["ci95"][0] <= be["break_even_share"] <= be["ci95"][1]
    assert be["undefined_resamples"] == 0
    assert r.break_even_share({k: 0 for k in gain}, gain, 50, 1)["break_even_share"] == 1.0
    assert r.break_even_share(cost, {k: 0 for k in gain}, 50, 1)["break_even_share"] == 0.0
    assert be == r.break_even_share(cost, gain, 400, 42)


def test_the_power_computation():
    for alpha in (0.05, 0.05 / 3):
        assert all(r.mcnemar_threshold(nd, alpha) == ks.mcnemar_threshold(nd, alpha)
                   for nd in range(0, 90))  # fmt: skip
    assert r.power_cost_gain(347, 31, 0.0, 0.05)["below"] == pytest.approx(1.0)
    # Brute force on a small case.
    n, gains, q, alpha = 14, 5, 0.3, 0.05
    want = {"below": 0.0, "above": 0.0}
    for n10 in range(n - gains + 1):
        for nb in range(gains + 1):
            w = ks._pmf(n10, n - gains, q) * ks._pmf(nb, gains, q)
            b, c = n10, gains - nb
            if ks.mcnemar_exact(b, c) <= alpha and b != c:
                want["above" if b > c else "below"] += w
    got = r.power_cost_gain(n, gains, q, alpha)
    assert got["below"] == pytest.approx(want["below"]) and got["above"] == pytest.approx(
        want["above"]
    )
    # The hand check can only remove power from a COST_ABOVE_GAIN reading.
    full = r.power_cost_gain(60, 3, 0.4, 0.05)["above"]
    assert r.power_cost_gain(60, 3, 0.4, 0.05, confirm=0.8)["above"] <= full + 1e-12


# --------------------------------------------------------------------------- the hand check


def test_the_hand_plan_covers_the_registered_roles(tmp_path, monkeypatch):
    ctx = _pipeline(tmp_path, monkeypatch, n=30)
    features = r.read_gz_json(ctx["features"])
    config = ctx["config"]
    plan = r.hand_plan(features, config)
    assert plan == r.hand_plan(copy.deepcopy(features), config)
    keys = {(i["question_id"], i["reply_digest"]) for i in plan["items"]}
    assert len(keys) == len(plan["items"])
    r.int_masks(features)
    recs = r.cost_records(features)
    for reader in r.READERS:
        right = wrong8 = beyond = top4 = 0
        for rec in recs[reader]:
            e70, e8 = rec["caps"]["70"], rec["caps"]["8"]
            key = (rec["question_id"], e70["digest"])
            if e70["switched"] and (e70["u"] == 1 or e8["switched"]):
                assert key in keys  # every judged-correct switch, every K = 8 switch
                right += e70["u"] == 1
                wrong8 += e70["u"] == 0 and e8["switched"]
            elif e70["switched"]:
                beyond += 1
            if not rec["bm25_top4_abstains"]:
                assert (rec["question_id"], rec["digest"]["bm25_top4"]) in keys
                top4 += 1
        p = plan["readers"][reader]
        assert (p["switched_judged_correct"], p["switched_judged_wrong_within_primary_cap"],
                p["switched_judged_wrong_beyond_primary_cap"], p["top4_answers"]) == (
            right, wrong8, beyond, top4)  # fmt: skip
        assert p["switched_judged_wrong_beyond_sampled"] == math.ceil(0.5 * beyond)
        assert p["distractor_items"] + p["distractor_shortfall"] == p["target_items"]
    targets = {(i["question_id"], i["reply_digest"]) for i in plan["items"]
               if any(u["role"] != r.ROLE_DISTRACTOR for u in i["uses"])}  # fmt: skip
    for i in plan["items"]:
        if all(u["role"] == r.ROLE_DISTRACTOR for u in i["uses"]):
            assert (i["question_id"], i["reply_digest"]) not in targets
    pools = {(x, p["question_id"]): p for x in r.READERS for p in features["readers"][x]["pools"]}
    for i in plan["items"]:
        for u in i["uses"]:
            cell = pools[(u["reader"], i["question_id"])]["masks"][int(u["mask"])]
            assert not cell["abstain"] and cell["digest"] == i["reply_digest"]
    assert plan["labeller_prompt_sha256"] == g.hand_labeller_prompt_sha256()
    assert plan["instructions_sha256"] == r.sha256_text(r.HAND_INSTRUCTIONS)


def _label(row: dict) -> int:
    """The toy labeller: the reference in the reply, or a refusal, is 1."""

    reply = row["reply"].lower()
    return int(row["reference"] in reply or reply.startswith("sorry"))


def _note(row: dict, label: int) -> str:
    """The toy labeller's note: "decline: ..." for a 1 given to a refusal."""

    return "decline: says it has nothing" if label and row["reply"].startswith("Sorry") else ""


def _hand_check(tmp_path, monkeypatch, ctx, label=_label) -> dict:
    from test_memcredit_am3g import _write_launch, _write_transcript

    monkeypatch.setattr(g, "HAND_CHUNK", 7)
    hand = tmp_path / "hand"
    out = r.cmd_hand_sample(r.argparse.Namespace(
        config="x", population="heldout", run_dir=str(ctx["run"]), evidence="x",
        features=str(ctx["features"]), hand_dir=str(hand)))  # fmt: skip
    rows = [json.loads(x) for x in (hand / "hand-check-sample.jsonl").read_text().splitlines()]
    assert out["items"] == len(rows) > 0
    allowed = {"item_id", "question_id", "question_type", "check", "question", "reference",
               "reply"}  # fmt: skip
    assert all(set(x) == allowed and x["check"] == r.HAND_CHECK for x in rows)
    assert all(not lf.abstention(x["reply"])[0] for x in rows)
    blob = json.dumps(rows).lower()
    for leak in ("judge", "switched", "distractor", "olmo", "qwen", "mask", "top4"):
        assert leak not in blob
    assert (hand / "hand-check-instructions.txt").read_text() == r.HAND_INSTRUCTIONS
    manifest = json.loads((hand / "hand-manifest.json").read_text())
    assert manifest["labeller_prompt_sha256"] == g.hand_labeller_prompt_sha256()
    assert (hand / "hand-first-prompt-01.txt").read_text() == g.hand_labeller_prompt(
        manifest["first"][0]["chunk"], manifest["first"][0]["output"]
    )
    with pytest.raises(r.Am5rError, match="non-empty"):
        r.cmd_hand_sample(r.argparse.Namespace(
            config="x", population="heldout", run_dir=str(ctx["run"]), evidence="x",
            features=str(ctx["features"]), hand_dir=str(hand)))  # fmt: skip
    by_id = {x["item_id"]: x for x in rows}
    _write_launch(hand, "first", manifest)
    for n, chunk in enumerate(manifest["first"], start=1):
        lines = [json.dumps({"item_id": i, "label": label(by_id[i]),
                             "note": _note(by_id[i], label(by_id[i]))})
                 for i in chunk["items"]]  # fmt: skip
        (hand / chunk["output"]).write_text("\n".join(lines) + "\n")
        _write_transcript(hand, "first", n, chunk)
    merged = g.cmd_hand_merge(r.argparse.Namespace(hand_dir=str(hand), stage="first"))
    assert merged["final_complete"]
    return {"hand": hand, "manifest": manifest, "merged": merged, "rows": rows}


def _analyze(tmp_path, ctx, hc, name="out") -> dict:
    out = tmp_path / name
    r.cmd_analyze(r.argparse.Namespace(
        config="x", population="heldout", features=str(ctx["features"]),
        hand_labels=str(hc["hand"] / "hand-labels.jsonl"),
        hand_labels_sha256=hc["merged"]["final_sha256"],
        hand_plan_sha256=hc["manifest"]["plan_sha256"], output_dir=str(out)))  # fmt: skip
    return {"dir": out, "results": json.loads((out / "results.json").read_text())}


def test_extract_hand_check_and_analyze_end_to_end_and_text_free(tmp_path, monkeypatch):
    ctx = _pipeline(tmp_path, monkeypatch, n=30)
    hc = _hand_check(tmp_path, monkeypatch, ctx)
    first = _analyze(tmp_path, ctx, hc, "out")
    res = first["results"]
    assert res["hand_check"]["status"] == "joined"
    assert res["validity"]["v3_replay_control"]["pass"]
    for key in ("primary", "secondary"):
        block = res[key]
        assert block["status"] == "read"
        for reader in r.READERS:
            e = block["readers"][reader]
            assert e["reading"] == r.confirm_reading(e["judge_reading"], "joined",
                                                     e["hand_label"])  # fmt: skip
    # The judge-based cost equals AM5's block's cost_judge, and the hand-based one counts the
    # refusals outside the patterns as no cost.
    for reader in r.READERS:
        jb = res["primary"]["judge"]["readers"][reader]
        block = res["descriptive"]["readers"][reader]["ablated"]["caps"]["8"]
        assert jb["cost"] == block["cost_judge"]["count"]
        hand = res["primary"]["hand"]["unlabelled_cost"]["readers"][reader]
        assert hand["switched_replies"]["unlabelled"] == 0
        assert hand["cost"] == jb["cost"] - hand["switched_replies"]["judge_no_hand_yes"]
    assert res["sensitivity_without_preference"]["questions"] == 20
    # Declines are counted from the notes; labelled items carry the leakage facts and both labels.
    declines = [x for x in hc["rows"] if x["reply"].startswith("Sorry")]
    assert res["hand_check"]["decline_notes"]["items"] == len(declines) > 0
    assert res["hand_check"]["decline_notes"]["label_0_with_decline_note"] == 0
    items = res["labelled_items"]
    assert [i["item_id"] for i in items] == hc["manifest"]["items"]
    assert sum(i["decline"] for i in items) == len(declines)
    assert all(set(i["facts"]) == set(a5.ITEM_FACTS) and i["hand"] in (0, 1) for i in items)
    for reader in r.READERS:
        d = res["descriptive"]["readers"][reader]
        for name in r.LEAK_FLAGS:
            parts = d["by_leak_flag"][name]
            assert parts["flag"]["questions"] + parts["no_flag"]["questions"] == 30
            for cap in ("8", "70"):
                total = parts["flag"][cap]["cost"] + parts["no_flag"][cap]["cost"]
                assert total == res["primary" if cap == "8" else "secondary"]["judge"][
                    "readers"][reader]["cost"]  # fmt: skip
        assert d["switched_replies_hand_labelled_declines"]["8"] <= d["ablated"]["caps"]["8"][
            "switch_rate"]["count"]  # fmt: skip
    # Byte-identical on a rerun.
    again = _analyze(tmp_path, ctx, hc, "out2")
    for f in ("results.json", "per-table.json.gz", "tables.md"):
        assert (first["dir"] / f).read_bytes() == (again["dir"] / f).read_bytes()
    blob = (
        (first["dir"] / "results.json").read_text()
        + (first["dir"] / "tables.md").read_text()
        + gzip.decompress((first["dir"] / "per-table.json.gz").read_bytes()).decode()
    )
    for text in ("blue h", "green", "It is", "Sorry", "memory 3", "question h0", "nothing about"):
        assert text not in blob
    # A plan digest other than the receipted one is refused.
    with pytest.raises(r.Am5rError, match="plan"):
        r.cmd_analyze(r.argparse.Namespace(
            config="x", population="heldout", features=str(ctx["features"]),
            hand_labels=str(hc["hand"] / "hand-labels.jsonl"),
            hand_labels_sha256=hc["merged"]["final_sha256"], hand_plan_sha256="0" * 64,
            output_dir=str(tmp_path / "out3")))  # fmt: skip
    with pytest.raises(r.Am5rError, match="exists"):
        _analyze(tmp_path, ctx, hc, "out")


def test_extract_reads_only_a_complete_job_once(tmp_path, monkeypatch):
    ctx = _pipeline(tmp_path, monkeypatch)

    def extract(decision: Path, private: Path) -> dict:
        return r.cmd_extract(r.argparse.Namespace(
            config="x", population="heldout", run_dir=str(ctx["run"]), evidence="x",
            summary=str(ctx["summary"]), private_dir=str(private),
            reference_run_dir=str(ctx["ref"]), rerun_decision=str(decision)))  # fmt: skip

    with pytest.raises(r.Am5rError, match="exists"):
        extract(ctx["decision"], ctx["features"].parent)
    with pytest.raises(g.Am3gError, match="V2"):
        extract(tmp_path / "no-decision.json", tmp_path / "p4")
    for record, why in (({"decision": "no-rerun", "job_dir": "1600", "population": "heldout"},
                         "does not say complete"),
                        ({"decision": "void", "job_dir": "1600", "population": "heldout"},
                         "does not say complete"),
                        ({"decision": "complete", "job_dir": "1599", "population": "heldout"},
                         "names job 1599"),
                        ({"decision": "complete", "job_dir": "1600",
                          "population": "development"}, "names job")):  # fmt: skip
        path = tmp_path / "decision.json"
        path.write_text(json.dumps(record))
        with pytest.raises(r.Am5rError, match=why):
            extract(path, tmp_path / "p5")
    assert not (tmp_path / "p4").exists() and not (tmp_path / "p5").exists()
    assert r.read_gz_json(ctx["features"])["job_id"] == "1600"


def test_hand_sample_refuses_features_of_another_job(tmp_path, monkeypatch):
    ctx = _pipeline(tmp_path, monkeypatch)
    other = tmp_path / "runs" / "heldout" / "1601" / r.OUTPUT
    with pytest.raises(r.Am5rError, match="job 1600's"):
        r.cmd_hand_sample(r.argparse.Namespace(
            config="x", population="heldout", run_dir=str(other), evidence="x",
            features=str(ctx["features"]), hand_dir=str(tmp_path / "hand")))  # fmt: skip
    assert not (tmp_path / "hand").exists()


def test_predictive_power_is_the_power_averaged_over_the_development_rate():
    n, gains = 60, 6
    d = r.rejection_directions(n - gains, gains, 0.05)
    sharp = r.predictive_power(n, gains, 300, 2000, 0.05, d)
    point = r.power_cost_gain(n, gains, 0.15, 0.05, directions=d)
    assert abs(sharp["above"] - point["above"]) < 0.03
    assert sharp["any"] == pytest.approx(sharp["below"] + sharp["above"])
    vague = r.predictive_power(n, gains, 0, 10, 0.05, d)
    assert 0 <= vague["below"] <= 1 and 0 <= vague["above"] <= 1


def test_the_registered_analysis_needs_the_receipted_labels(tmp_path, monkeypatch):
    ctx = _pipeline(tmp_path, monkeypatch)
    with pytest.raises(r.Am5rError, match="hand-labels"):
        r.cmd_analyze(
            r.argparse.Namespace(
                config="x",
                population="heldout",
                features=str(ctx["features"]),
                hand_labels=None,
                hand_labels_sha256=None,
                hand_plan_sha256=None,
                output_dir=str(tmp_path / "o"),
            )
        )
    results, _ = r.analyze_population(r.read_gz_json(ctx["features"]), ctx["config"], "heldout",
                                      None, None)  # fmt: skip
    for e in results["primary"]["readers"].values():
        assert e["reading"] in ("PENDING_HAND_CHECK", r.NOT_SEPARATED)
        assert e["hand_label"] is None


def test_confirmation_rule():
    for jr in r.DIRECTIONAL:
        assert r.confirm_reading(jr, "joined", jr) == jr
        other = r.COST_ABOVE if jr == r.COST_BELOW else r.COST_BELOW
        assert r.confirm_reading(jr, "joined", other) == "JUDGE_DEPENDENT"
        assert r.confirm_reading(jr, "joined", r.NOT_SEPARATED) == "JUDGE_DEPENDENT"
        assert r.confirm_reading(jr, "missing", None) == "PENDING_HAND_CHECK"
        assert r.confirm_reading(jr, "incomplete", None) == "JUDGE_DEPENDENT"
    assert r.confirm_reading(r.NOT_SEPARATED, "joined", r.COST_BELOW) == r.NOT_SEPARATED


def test_hand_costs_assign_unlabelled_replies_against_the_reading():
    recs = [_record("q1", True, True, 0), _record("q2", False, True, 0),
            _record("q3", False, True, 1), _record("q4", False, False, 0)]  # fmt: skip
    hand_of = {("q1", "d-q1"): 1, ("q3", "d-q3"): 0}
    cost, counts = r.hand_costs(recs, 70, hand_of, "cost")
    assert cost == {"q1": 0, "q2": 1, "q3": 1, "q4": 0}
    assert counts["unlabelled"] == 1 and counts["judge_no_hand_yes"] == 1
    assert counts["judge_yes_hand_no"] == 1
    cost, _ = r.hand_costs(recs, 70, hand_of, "no-cost")
    assert cost["q2"] == 0
    cost, counts = r.hand_costs(recs, 8, hand_of, "cost")
    assert cost == {"q1": 0, "q2": 0, "q3": 0, "q4": 0} and counts["unlabelled"] == 0


def test_hand_labels_that_reverse_the_judge_make_the_reading_judge_dependent(tmp_path, monkeypatch):
    """With labels that call every switched reply correct, a judge-based COST_ABOVE_GAIN cannot
    stand; the toy's judge-based readings are compared with the hand-based ones."""

    def many_costs(reader, qid, mask):
        k = int(qid[1:]) + (1 if qid.startswith("c") else 0)
        top4 = lf.bm25_top_mask([(i * 3 + k) % 8 for i in range(8)])
        h = int(r.sha256_text(f"{reader}:{qid}:{mask}")[:6], 16) % 100
        if mask in (g.FULL, top4) or h < 55:
            return "I don't know."
        return f"It is green {qid}."

    ctx = _pipeline(tmp_path, monkeypatch, n=40, replies=many_costs)
    hc = _hand_check(tmp_path, monkeypatch, ctx, label=lambda row: 1)
    res = _analyze(tmp_path, ctx, hc)["results"]
    for reader in r.READERS:
        e = res["primary"]["readers"][reader]
        assert e["judge_reading"] == r.COST_ABOVE
        assert e["hand_label"] in (r.COST_BELOW, r.NOT_SEPARATED)
        assert e["reading"] == "JUDGE_DEPENDENT"


# --------------------------------------------------------------------------- the rerun rule


def test_rerun_decision_reads_an_am5r_job_directory(tmp_path):
    job = tmp_path / "1600"
    (job / r.OUTPUT).mkdir(parents=True)
    (job / "termination.env").write_text("job_id=1600\nreason=completed\n")
    steps = {sid: {"kind": "reader", "status": "complete"}
             for sid in ("rd-qwen3-8b", "rd-olmo2", "rd-qwen35-9b-default")}  # fmt: skip
    steps |= {"rd-olmo2-default": {"status": "not-needed"}, "judge32": {"status": "complete"}}
    (job / r.OUTPUT / "summary.json").write_text(
        json.dumps({"steps": steps, "model_verification": {}})
    )
    args = r.argparse.Namespace(population="heldout", job_dir=str(job), is_rerun=False)
    out = r.cmd_rerun_decision(args)
    assert out["decision"] == "complete" and out["job_dir"] == "1600"
    steps["judge32"] = {"status": "skipped", "reason": "remaining 300 s"}
    (job / r.OUTPUT / "summary.json").write_text(
        json.dumps({"steps": steps, "model_verification": {}})
    )
    assert r.cmd_rerun_decision(args)["decision"] == "no-rerun"
    (job / r.OUTPUT / "summary.json").write_text("[1]")
    with pytest.raises(r.Am5rError, match="V2.*not a JSON object"):
        r.cmd_rerun_decision(args)
    assert set(g.ESSENTIAL) == {*r.READERS, "judge32"}


def test_missing_judge_items_is_a_named_void_not_a_traceback(tmp_path, monkeypatch, capsys):
    ctx = _pipeline(tmp_path, monkeypatch)
    (ctx["run"] / "judge-items.json").unlink()
    code = r.main(["extract", "--population", "heldout", "--run-dir", str(ctx["run"]),
                   "--evidence", "x", "--summary", str(ctx["summary"]),
                   "--private-dir", str(tmp_path / "p3"), "--reference-run-dir",
                   str(ctx["ref"]), "--rerun-decision", str(ctx["decision"])])  # fmt: skip
    err = capsys.readouterr().err
    assert code == 2 and "VOID (V2, incomplete)" in err and "Traceback" not in err


def test_development_dry_run_mechanics_end_to_end(tmp_path, monkeypatch):
    """The development population: the whole artifact is the replay, every reader's R1 and R2
    pass, and the analysis decides nothing."""

    ctx = _pipeline(tmp_path, monkeypatch, population="development", n=9)
    features = r.read_gz_json(ctx["features"])
    assert features["replay"]["control_cells"] == 9 * 71 and features["replay"]["pass"]
    assert "control_pools" not in features["readers"]["qwen3-8b"]
    results, per_table = r.analyze_population(features, ctx["config"], "development", None, None)
    assert results["claim_level"] == "exploratory" and len(per_table) == 3 * 9
    assert results["secondary"]["decides"] is False


def test_rng_draws_are_seeded_and_stable():
    """The hand plan's draws use string seeds (Python's random), which are stable across
    processes."""

    a = random.Random("44:am5r:hand:wrong:qwen3-8b").sample(range(20), 5)
    b = random.Random("44:am5r:hand:wrong:qwen3-8b").sample(range(20), 5)
    assert a == b
    assert mc.normalize_answer("It is Blue.") == "it is blue"
