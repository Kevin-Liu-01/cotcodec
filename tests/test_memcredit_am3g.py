"""Tests for am3-nonabstain-generality-v1 (scripts/memcredit_am3g.py): the config and its pins,
the gate, the abstention population's pools and judge prompt, the request and judge-item tables,
Holm's procedure and H1's readings, H2's cost estimand, the natural-mix summary, and extract plus
analyze end to end on toy run directories (no GPU, no vLLM, no held-out or abstention data).

No test decodes AM1's held-out tables or opens a held-out or abstention input; one test hashes the
committed held-out tables' gz file to check its pin. The gate is tested against scratch copies of
the ledger and the registration, so the tests pass before and after the freeze."""

from __future__ import annotations

import ast
import copy
import gzip
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import memcredit_am3 as am3  # noqa: E402
import memcredit_am3g as g  # noqa: E402
import memcredit_keepset_search as ks  # noqa: E402
import memcredit_label_free as lf  # noqa: E402

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

# --------------------------------------------------------------------------- config and pins


def test_config_loads_with_its_pins():
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    am3_config = g.load_am3_config(config)
    assert config["claim_level"] == "confirmatory"
    assert config["readers"] == am3_config["readers"]
    assert [r["id"] for r in config["readers"]] == list(g.H2_READERS)
    anchor = g.reader_spec(config, g.ANCHOR)
    assert anchor["engine"] == pilot["reader"]["engine"] and anchor["role"] == "anchor"
    assert config["reader_sampling"] == {"temperature": 0.0, "max_tokens": 64, "logprobs": 0}
    assert 'say "I don\'t know"' in pilot["prompt"]["user"]
    steps = {s["id"]: s for s in config["steps"]}
    assert steps["rd-qwen3-8b"]["batch_invariant"] and steps["rd-olmo2"]["batch_invariant"]
    assert not steps["rd-qwen35-9b-default"]["batch_invariant"]
    assert all(s["enforce_eager"] for s in config["steps"])
    assert steps["rd-olmo2-default"]["only_if_incomplete"] == "rd-olmo2"
    assert g.population_arms(config, "abstention") == ("retrieved",)
    assert g.population_arms(config, "heldout") == ("retrieved", "gold")


def test_the_prompt_and_judges_are_am1s_registration_config():
    """The pilot config supplies the prompt and judges; AM1's registration used the same."""

    pilot = g.load_pilot_config(g.load_config())
    reg = yaml.safe_load(ms.REGISTRATION_CONFIG_PATH.read_text())
    for key in ("prompt", "reader", "judge", "pools", "retriever", "source"):
        assert pilot[key] == reg[key], key


def test_heldout_pins_equal_am1_keepset_searchs():
    config = g.load_config()
    held = config["populations"]["heldout"]
    spec = ks.SPLITS["heldout"]
    assert held["artifact_sha256"] == spec["artifact_sha256"]
    assert held["question_ids_sha256"] == spec["question_ids_sha256"]
    assert held["questions"] == spec["questions"] == 347
    assert held["tables"]["sha256"] == spec["tables_sha256"]
    assert held["tables"]["json_sha256"] == spec["tables_json_sha256"]
    assert held["tables"]["path"] == str(spec["tables"])
    pinned = {k: v for k, v in spec["pass"]["sha256"].items() if "worker-progress" not in k}
    assert held["reference"]["sha256"] == pinned
    # The committed gz is hashed, never decoded.
    assert g.sha256_file(ROOT / held["tables"]["path"]) == held["tables"]["sha256"]


def test_development_pins_are_am3s():
    config = g.load_config()
    dev = config["populations"]["development"]
    assert dev["artifact_sha256"] == lf.ARTIFACT_SHA256
    split = json.loads((ROOT / "experiments/am1/memcredit-split-v1.json").read_text())
    assert dev["question_ids_sha256"] == split["development_sha256"]
    assert (
        g.sha256_file(ROOT / "experiments/am1/memcredit-split-v1.json")
        == config["split_file_sha256"]
    )
    raw = {}
    for step in ("rd-qwen3-8b", "rd-olmo2", "rd-qwen35-9b-default", "judge32", "judge8"):
        text = (ROOT / g.AM3_DIR / f"jobs/1466-main/am3/sessions/{step}/raw-sha256.txt").read_text()
        for line in text.splitlines():
            digest, name = line.split()
            raw[f"sessions/{step}/{name[2:]}"] = digest
    for path, digest in dev["reference"]["sha256"].items():
        if path.endswith((".npz", ".texts.jsonl.gz")):
            assert raw[path] == digest, path
    assert (
        dev["reference"]["sha256"]["judge-items.json"]
        == ((ROOT / g.AM3_DIR / "jobs/1466-main/am3/judge-items.sha256.txt").read_text().split()[0])
    )


def test_model_pins_are_am3s_verified_receipts():
    config = g.load_config()
    summary = json.loads((ROOT / g.AM3_DIR / "jobs/1466-main/am3/summary.json").read_text())
    for model_id, pin in config["models"].items():
        got = summary["model_verification"][model_id]
        for key in ("revision", "receipt_sha256", "artifact_root_sha256"):
            assert got[key] == pin[key], (model_id, key)


def _write_config(tmp_path: Path, mutate) -> Path:
    config = yaml.safe_load(g.CONFIG_PATH.read_text())
    mutate(config)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    return path


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.update(claim_level="exploratory"),
        lambda c: c["readers"][1]["engine"].update(max_num_seqs=128),
        lambda c: c["readers"].reverse(),
        lambda c: c["models"]["qwen3-32b"].update(receipt_sha256="not a digest"),
        lambda c: c["models"]["olmo-2-1124-7b-instruct"].update(revision="0" * 40),
        lambda c: c["abstention_judge"].update(template_sha256="0" * 64),
        lambda c: c["abstention_judge"].update(decoy_seed=7),
        lambda c: c["populations"]["abstention"].update(arms=["retrieved", "gold"]),
        lambda c: c["steps"][0].update(batch_invariant=False),
        lambda c: c["steps"][4].update(batch_invariant=False),
        lambda c: c["steps"][3].update(enforce_eager=False),
        lambda c: c["steps"][2].update(only_if_incomplete="rd-qwen3-8b"),
        lambda c: c["jobs"]["heldout"].update(gpus=2),
        lambda c: c["jobs"]["heldout"]["step_budgets"].update({"judge8": [300, 400]}),
        lambda c: c["pilot"].update(config_sha256="0" * 64),
        lambda c: c["am3"].update(config_sha256="0" * 64),
    ],
)
def test_config_refuses_changes(tmp_path, mutate):
    with pytest.raises((g.Am3gError, am3.Am3Error)):
        g.load_config(_write_config(tmp_path, mutate))


def test_verify_models_refuses_a_receipt_other_than_the_pin(monkeypatch):
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    calls = []

    def fake(model_id, receipt_root):
        calls.append(model_id)
        return dict(config["models"][model_id], model_id=model_id)

    monkeypatch.setattr(g.lane, "verify_model", fake)
    verified = g.verify_models(config, pilot)
    assert set(verified) == set(config["models"]) and calls[0] == "qwen3-32b"
    bad = copy.deepcopy(config)
    bad["models"]["qwen3.5-9b"]["artifact_root_sha256"] = "0" * 64
    with pytest.raises(g.Am3gError, match="V1"):
        g.verify_models(bad, pilot)


def _simulate(config: dict, population: str, path: str) -> dict:
    """Worst case of one registered job under budget.overhead_model: every step takes its
    overhead plus its full max_s. path: "normal"; "fallback" (OLMo-2's batch-invariant engine
    fails to start, then its default-mode step runs); "capped-fallback" (OLMo-2's batch-invariant
    pass is stopped by its max_s, then the fallback runs: the residual path of section 11)."""

    job = config["jobs"][population]
    over = config["budget"]["overhead_model"][population]
    budgets = job["step_budgets"]
    deadline = job["minutes"] * 60 - 210
    t = over["job"]
    started, skipped = {}, []
    order = ["rd-qwen3-8b", "rd-olmo2"] + (["rd-olmo2-default"] if path != "normal" else [])
    order += ["rd-qwen35-9b-default", "judge32", "judge8"]
    for sid in order:
        min_start, max_s = budgets[sid]
        if deadline - t < min_start:
            skipped.append(sid)
            continue
        started[sid] = deadline - t
        kind = "judge32" if sid == "judge32" else "judge8" if sid == "judge8" else "reader"
        if sid == "rd-olmo2" and path == "fallback":
            t += over["failed_engine_step"]
        else:
            t += over[kind] + max_s
    return {"started": started, "skipped": skipped, "end": t, "deadline": deadline}


@pytest.mark.parametrize("population", ["heldout", "abstention"])
@pytest.mark.parametrize("path", ["normal", "fallback"])
def test_judges_start_and_fit_in_the_worst_case(population, path):
    """M1 of check 1: with every reader at its cap and the overheads measured in job 1471, both
    judges still start and finish before the deadline, on the normal and the fallback paths; and
    every step's min_start_s covers its own overhead plus its max_s."""

    config = g.load_config()
    over = config["budget"]["overhead_model"][population]
    for sid, (min_start, max_s) in config["jobs"][population]["step_budgets"].items():
        kind = sid if sid.startswith("judge") else "reader"
        assert min_start >= over[kind] + max_s, sid
    run = _simulate(config, population, path)
    assert run["skipped"] == [] and {"judge32", "judge8"} <= set(run["started"])
    assert run["end"] <= run["deadline"]


def test_the_residual_path_is_the_one_section_11_discloses():
    """If OLMo-2's batch-invariant pass is time-capped and its fallback then runs, the held-out job
    cannot reach judge32: a time-budget void with no rerun (section 11 says so)."""

    run = _simulate(g.load_config(), "heldout", "capped-fallback")
    assert "judge32" in run["skipped"]


def test_registered_caps_are_the_limits():
    config = g.load_config()
    caps = config["budget"]
    jobs = config["jobs"]
    assert caps["registered_cap_gpu_hours"] == round(
        (jobs["heldout"]["minutes"] + jobs["abstention"]["minutes"] + caps["build_minutes"]) / 60,
        2,
    )
    assert caps["dry_run_cap_gpu_hours"] == round(
        (jobs["development"]["minutes"] + caps["build_minutes"]) / 60, 2
    )


# --------------------------------------------------------------------------- the judge prompt


def _legacy_prompt_function():
    source = (ROOT / "legacy/harness/memory_trials/longmemeval_judge.py").read_text()
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "official_answer_check_prompt")  # fmt: skip
    namespace: dict = {"LongMemEvalJudgeError": ValueError}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "legacy", "exec"), namespace)  # noqa: S102
    return namespace["official_answer_check_prompt"]


def test_abstention_template_is_the_archived_official_port():
    legacy = _legacy_prompt_function()
    args = ("Q? {x}", "Explanation {0}", "R }")
    for qtype in ("multi-session", "temporal-reasoning", "knowledge-update", "single-session-user"):
        assert g.ABSTENTION_TEMPLATE.format(*args) == legacy(qtype, *args, abstention=True)
    assert g.abstention_template_sha256() == g.ABSTENTION_TEMPLATE_SHA256
    assert g.answer_templates_sha256() == g.ANSWER_TEMPLATES_SHA256


def test_the_archived_port_has_its_section_4_digest():
    """Host and Mac checkouts only: legacy/ is not in the image."""

    port = ROOT / "legacy/harness/memory_trials/longmemeval_judge.py"
    if not port.is_file():
        pytest.skip("legacy/ is not in this tree (the image)")
    assert g.sha256_file(port) == (
        "77aed59acdf42f0848f59f73cc3f61f0d625300b16a18b35797bae139b8dfee1"
    )
    assert "77aed59acdf42f0848f59f73cc3f61f0d625300b16a18b35797bae139b8dfee1" in (
        (ROOT / g.REGISTRATION).read_text()
    )


def _toy_memory(i: int, rank: int, gold: bool = False) -> dict:
    return {"text": f"memory {i}", "date": "2023/05/01", "bm25_rank": rank, "is_gold": gold}


def _toy_artifact(questions: int = 4, abstention: bool = False) -> dict:
    qs = []
    for q in range(questions):
        qid = f"q{q}_abs" if abstention else f"q{q}"
        entry = {
            "question_id": qid,
            "question_type": "multi-session" if q % 2 else "temporal-reasoning",
            "question": f"question {q}?",
            "question_date": "2023/06/01",
            "answer": f"not mentioned {q}" if abstention else f"blue {q}",
            "pools": {"retrieved": [_toy_memory(i, (i * 3 + q) % 8, i == 0) for i in range(8)]},
        }
        if abstention:
            entry["abstention"] = True
            entry["validation_decoy"] = {"question_id": f"d{q}", "answer": f"green {q}"}
        else:
            entry["pools"]["gold"] = [_toy_memory(i, 10 * i + q, i == 0) for i in range(8)]
            entry["placebos"] = {
                arm: {"swaps": [[{"text": f"swap {i}"}] for i in range(8)],
                      "reorders": [list(range(8))[::-1]]}
                for arm in g.ARMS
            }  # fmt: skip
        qs.append(entry)
    return {"experiment_id": "toy", "split": "toy", "questions": qs}


def test_judge_message_uses_the_abstention_template_only_for_abstention_questions():
    artifact = _toy_artifact(2, abstention=True)
    item = {"question_index": 1, "response": "I don't know."}
    text = g.judge_message(artifact, item)
    assert text == g.ABSTENTION_TEMPLATE.format("question 1?", "not mentioned 1", "I don't know.")
    answerable = _toy_artifact(2)
    assert g.judge_message(answerable, item) == ms.judge_message(answerable, item)
    calibration = dict(item, template="abstention", explanation="generic")
    assert "Explanation: generic" in g.judge_message(answerable, calibration)
    broken = copy.deepcopy(artifact)
    broken["questions"][1].pop("abstention")
    with pytest.raises(g.Am3gError):
        g.judge_message(broken, item)
    flagged = copy.deepcopy(answerable)
    flagged["questions"][1]["abstention"] = True
    with pytest.raises(g.Am3gError):
        g.judge_message(flagged, item)


def test_validation_items_by_population():
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    abs_items = g.validation_items(_toy_artifact(3, True), pilot, config, "abstention")
    assert [i["source"] for i in abs_items[:3]] == [
        "validation:abs-explanation", "validation:abs-idk", "validation:abs-decoy",
    ]  # fmt: skip
    assert [i["expected"] for i in abs_items[:3]] == [1, 1, 0]
    assert abs_items[1]["response"] == "I don't know." and abs_items[2]["response"] == "green 0"
    answerable = _toy_artifact(3)
    held = g.validation_items(answerable, pilot, config, "heldout")
    assert held == ms.validation_items(answerable, pilot["judge"]["validation"])
    dev = g.validation_items(answerable, pilot, config, "development")
    assert dev[: len(held)] == held
    extra = dev[len(held) :]
    assert len(extra) == 6 and all(i["template"] == "abstention" for i in extra)


def test_judge_items_are_the_union_of_distinct_replies():
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    artifact = _toy_artifact(2, abstention=True)
    passes = {"rd-a": {0: "Green.", 1: " Green. ", 71: "I don't know."},
              "rd-b": {0: "Green.", 2: "Red."}}  # fmt: skip
    items = g.judge_items(artifact, pilot, config, "abstention", passes)
    reader = [(i["question_index"], i["response"]) for i in items if i["source"] == "reader"]
    assert reader == [(0, "Green."), (0, "Red."), (1, "I don't know.")]
    assert [i["index"] for i in items] == list(range(len(items)))
    assert sum(i["source"] != "reader" for i in items) == 6


# --------------------------------------------------------------------------- requests


def test_request_table_is_am3s_for_both_arms_and_retrieved_only_for_abstention():
    artifact = _toy_artifact(3)
    assert g.request_table(artifact, g.ARMS) == am3.request_table(artifact)
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    assert g.reader_messages(pilot, artifact, g.ARMS) == am3.reader_messages(pilot, artifact)
    abs_table = g.request_table(_toy_artifact(3, True), ("retrieved",))
    assert len(abs_table) == 3 * 71 and {r["arm"] for r in abs_table} == {"retrieved"}
    assert [r["mask"] for r in abs_table[:71]] == sorted(lf.FOUR_SETS) + [255]


# --------------------------------------------------------------------------- paths and gate


@pytest.mark.parametrize(
    "path",
    [
        "program/evidence/2026-10-16/am1-confirmatory/analysis/tables.json.gz",
        "/h/cotcodec-runs/stage0/am1-memory-credit-v1/study-artifact.json",
        "/h/cotcodec-runs/stage0/am3-nonabstain-generality-v1/inputs/abstention-artifact.json",
        "/h/x/abstention-artifact.json",
        "/h/cotcodec-runs/stage0/am1-keepset-search-v1/private/features.json.gz",
    ],
)
def test_development_refuses_heldout_and_abstention_paths(path):
    with pytest.raises(g.Am3gError):
        g.check_dev_path(path)


def test_development_refuses_a_symlink_to_heldout(tmp_path):
    target = tmp_path / "am1-confirmatory"
    target.mkdir()
    link = tmp_path / "innocent"
    link.symlink_to(target)
    with pytest.raises(g.Am3gError):
        g.check_dev_path(link)


def test_private_outputs_stay_outside_the_repository(tmp_path):
    g.refuse_inside_repo(tmp_path / "private")
    with pytest.raises(g.Am3gError):
        g.refuse_inside_repo(ROOT / "private")


def _scratch(tmp_path: Path, frozen: bool) -> tuple[Path, Path]:
    reg = tmp_path / "registration.md"
    reg.write_bytes((ROOT / g.REGISTRATION).read_bytes())
    ledger = tmp_path / "ledger.jsonl"
    row = {"experiment_id": g.EXPERIMENT, "sha256": g.sha256_file(reg)}
    ledger.write_text(json.dumps(row) + "\n" if frozen else "")
    return reg, ledger


@pytest.mark.parametrize("population", ["heldout", "abstention"])
def test_gated_populations_are_refused_before_the_freeze(tmp_path, monkeypatch, population):
    """Every entry point that opens a held-out or abstention input refuses at the gate first;
    Path.read_bytes is made to fail so that a read before the gate would be caught."""

    reg, ledger = _scratch(tmp_path, frozen=False)
    monkeypatch.setattr(g, "LEDGER", ledger)
    monkeypatch.setattr(g, "REGISTRATION", reg)
    with pytest.raises(g.Am3gError, match="after the freeze"):
        g.gate(population)
    dummy = tmp_path / "artifact.json"
    dummy.write_text("{}")

    def no_read(self):
        raise AssertionError(f"read before the gate: {self}")

    monkeypatch.setattr(Path, "read_bytes", no_read)
    out = tmp_path / "out"
    argvs = [
        ["run", "--population", population, "--seeds", "42", "43", "44", "--output-dir",
         str(out), "--allocation-minutes", "10", "--evidence", str(dummy),
         "--expected-evidence-sha256", "0" * 64],
        ["extract", "--population", population, "--run-dir", str(tmp_path), "--evidence",
         str(dummy), "--private-dir", str(tmp_path / "p")],
        ["analyze", "--heldout-features", str(dummy), "--abstention-void", "x", "--output-dir",
         str(out)],
    ]  # fmt: skip
    for argv in argvs:
        assert g.main(argv) == 2
    assert not out.exists() and not (tmp_path / "p").exists()
    assert g.gate("development") == {"population": "development", "frozen_required": False}


def test_gate_opens_with_a_scratch_ledger_row_and_matching_pins(tmp_path):
    """Before the freeze, the gate opens on a scratch ledger row when the working tree matches
    section 16. Once the real ledger holds this registration's row (the run is complete), the
    working tree legitimately moves on (D122 changed models/registry.yaml), so section 16's pins
    are checked against the files at the freeze commit (the row's git_head_at_freeze), never
    against today's tree; the registration file must still be the frozen one. Either way a
    tampered pin is refused."""

    reg, ledger = _scratch(tmp_path, frozen=True)
    rows = [json.loads(line) for line in (ROOT / g.LEDGER).read_text().splitlines() if line.strip()]
    row = next((x for x in rows if x.get("experiment_id") == g.EXPERIMENT), None)
    if row is None:
        record = g.gate("heldout", ledger=ledger, registration=reg)
        assert record["registration_frozen"] and record["code_pins"]["all_match"]
    else:
        assert row["sha256"] == g.sha256_file(ROOT / g.REGISTRATION)
        commit = row["git_head_at_freeze"]
        pins = ks.code_pins(ROOT / g.REGISTRATION)
        assert pins and str(g.REGISTRATION) not in pins

        def at_freeze(path: str) -> str:
            blob = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
                                  capture_output=True, check=True).stdout  # fmt: skip
            return hashlib.sha256(blob).hexdigest()

        assert [path for path, digest in sorted(pins.items()) if at_freeze(path) != digest] == []
        assert at_freeze(str(g.REGISTRATION)) == row["sha256"]
    tampered = tmp_path / "tampered.md"
    good = ks.code_pins(reg)["scripts/memcredit_am3g.py"]
    tampered.write_text(reg.read_text().replace(good, "0" * 64))
    ledger.write_text(json.dumps({"experiment_id": g.EXPERIMENT,
                                  "sha256": g.sha256_file(tampered)}) + "\n")  # fmt: skip
    with pytest.raises(g.Am3gError, match="pins"):
        g.gate("abstention", ledger=ledger, registration=tampered)


def test_the_feature_code_is_the_whole_import_closure_and_pinned():
    code = (
        "import sys, pathlib; root = pathlib.Path(sys.argv[1]).resolve(); "
        "sys.path[:0] = [str(root), str(root / 'scripts')]; "
        "import memcredit_am3g, memcredit_study; "
        "print('\\n'.join(sorted(str(pathlib.Path(m.__file__).resolve().relative_to(root)) "
        "for m in list(sys.modules.values()) if getattr(m, '__file__', None) "
        "and pathlib.Path(m.__file__).resolve().is_relative_to(root) "
        "and 'site-packages' not in pathlib.Path(m.__file__).resolve().parts)))"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT)], capture_output=True,
                         text=True, check=True, cwd=ROOT)  # fmt: skip
    assert sorted(g.FEATURE_CODE) == out.stdout.split()
    pins = ks.code_pins(ROOT / g.REGISTRATION)
    assert all(path in pins for path in g.FEATURE_CODE)
    assert "experiments/am3/am3-nonabstain-generality-v1.yaml" in pins


def test_every_code_pin_is_in_the_image():
    """The GPU job's gate checks every pin inside the image, which the overlay build makes from
    the capsule minus .dockerignore's entries (legacy/ among them): no pin may sit under one."""

    ignored = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text().splitlines()
        if line.strip() and not line.startswith(("#", "!")) and not set(line) & set("*?[")
    }
    pins = ks.code_pins(ROOT / g.REGISTRATION)
    assert "legacy" in ignored
    for path in pins:
        parts = Path(path).parts
        assert not any("/".join(parts[: i + 1]) in ignored for i in range(len(parts))), path


def test_registration_freezes_on_a_scratch_ledger(tmp_path):
    spec = importlib.util.spec_from_file_location("preregister", ROOT / "scripts/preregister.py")
    prereg = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(prereg)
    ledger = tmp_path / "ledger.jsonl"
    row = prereg.freeze(ROOT / g.REGISTRATION, g.EXPERIMENT, ledger=ledger, root=ROOT)
    assert row["experiment_id"] == g.EXPERIMENT


# --------------------------------------------------------------------------- abstention pools


def _record(qid: str, qtype: str, turns: list[tuple[str, str, bool]], question: str) -> dict:
    sessions = []
    for i in range(0, len(turns), 4):
        sessions.append([{"role": role, "content": text, **({"has_answer": True} if gold else {})}
                         for role, text, gold in turns[i : i + 4]])  # fmt: skip
    return {
        "question_id": qid,
        "question_type": qtype,
        "question": question,
        "answer": f"answer of {qid}",
        "question_date": "2023/06/01 (Thu) 10:00",
        "haystack_sessions": sessions,
        "haystack_dates": [f"2023/05/{d + 1:02d} (Mon) 10:00" for d in range(len(sessions))],
        "haystack_session_ids": [f"{qid}-s{d}" for d in range(len(sessions))],
    }


def _toy_dataset() -> list[dict]:
    words = ["apple", "river", "guitar", "summer", "train", "garden", "coffee", "museum", "bike"]
    records = []
    for n, qtype in enumerate(("multi-session", "temporal-reasoning", "multi-session")):
        turns = []
        for t in range(24):
            role = "user" if t % 2 == 0 else "assistant"
            text = f"I talked about {words[(t + n) % 9]} and {words[(t * 5 + n) % 9]} " * (
                1 + t % 3
            )
            turns.append((role, text, t == 4))
        qid = f"{n:04d}abcd"
        records.append(_record(qid, qtype, turns, f"What about the {words[n]} and coffee?"))
        records.append(_record(qid + "_abs", qtype, turns[:20], f"What about the {words[n + 3]}?"))
    return records


def test_retrieved_pool_is_build_pools_retrieved_arm():
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    for record in _toy_dataset()[::2]:
        pools = mc.build_pools(record, ms.pool_config(pilot))
        assert g.retrieved_pool(record, ms.pool_config(pilot)) == pools["retrieved"]


def test_build_abstention_artifact_takes_every_abs_question_with_a_seeded_decoy():
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    records = _toy_dataset()
    split = {"development": ["0000abcd", "0001abcd"], "heldout": ["0002abcd"]}
    artifact, facts = g.build_abstention_artifact(records, pilot, split, config)
    ids = [q["question_id"] for q in artifact["questions"]]
    assert ids == sorted(r["question_id"] for r in records if r["question_id"].endswith("_abs"))
    assert artifact["question_ids_sha256"] == g.ids_sha256(ids)
    assert artifact["arms"] == ["retrieved"] and artifact["split"] == "abstention"
    for q in artifact["questions"]:
        assert q["abstention"] is True and list(q["pools"]) == ["retrieved"]
        assert len(q["pools"]["retrieved"]) == 8
        decoy = q["validation_decoy"]["question_id"]
        candidates = sorted(i for i in split["development"]
                            if next(r for r in records if r["question_id"] == i)["question_type"]
                            == q["question_type"])  # fmt: skip
        assert decoy == random.Random(f"44:{q['question_id']}").choice(candidates)
    membership = {f["question_id"]: f["twin_membership"] for f in facts["twins"]}
    assert membership == {"0000abcd_abs": "development", "0001abcd_abs": "development",
                          "0002abcd_abs": "heldout-confirmatory"}  # fmt: skip
    again, _ = g.build_abstention_artifact(records, pilot, split, config)
    assert mc.canonical_json(again) == mc.canonical_json(artifact)
    summary = g.abstention_summary(artifact, "0" * 64, facts, pilot)
    blob = json.dumps(summary)
    assert "I talked about" not in blob and "answer of" not in blob and "What about" not in blob


# --------------------------------------------------------------------------- statistics


def test_holm_step_down():
    out = g.holm({"a": 0.01, "b": 0.04})
    assert out["a"]["p_holm"] == pytest.approx(0.02) and out["a"]["reject"]
    assert out["b"]["p_holm"] == pytest.approx(0.04) and out["b"]["reject"]
    out = g.holm({"a": 0.03, "b": 0.04})
    assert out["a"]["p_holm"] == pytest.approx(0.06) and not out["a"]["reject"]
    assert out["b"]["p_holm"] == pytest.approx(0.06) and not out["b"]["reject"]
    out = g.holm({"a": 0.001, "b": 0.02, "c": 0.04})
    assert [out[k]["reject"] for k in "abc"] == [True, True, True]
    assert out["c"]["step_threshold"] == pytest.approx(0.05)
    assert out["a"]["step_threshold"] == pytest.approx(0.05 / 3)
    out = g.holm({"a": 0.5, "b": 0.5})
    assert not any(v["reject"] for v in out.values())


def test_mcnemar_rejection_counts_under_holm():
    """With c = 0: Holm's first step at 0.05/2 needs b >= 7 (p = 0.0156), b = 6 gives 0.031; at
    0.05/3, b >= 7 as well; at 0.05, b >= 6."""

    assert ks.mcnemar_exact(7, 0) <= 0.025 < ks.mcnemar_exact(6, 0)
    assert ks.mcnemar_exact(7, 0) <= 0.05 / 3
    assert ks.mcnemar_exact(6, 0) <= 0.05 < ks.mcnemar_exact(5, 0)


def _rec(qid: str, arm: str, top: int, rule: int, top8: int | None = None, qtype="x") -> dict:
    u = {"bm25_top4": top, "nonabstain_bm25": rule, "all_8": top if top8 is None else top8,
         "oracle_best4": max(top, rule), "four_subset_correct": top + rule,
         "four_subset_abstain_correct": 0, "four_subset_nonabstain_correct": 0,
         "all_8_abstain_correct": 0}  # fmt: skip
    return {"question_id": qid, "question_type": qtype, "arm": arm, "bm25_top4_mask": 15,
            "nonabstain_mask": 15 if top == rule else 23, "first_answer_position": 1, "reads": 1,
            "four_subset_abstain": 0, "bm25_top4_abstains": top != rule, "all_8_abstains": False,
            "u": {"primary": dict(u), "secondary": dict(u)}}  # fmt: skip


def _records(gains: dict[str, tuple[int, int]], n: int = 40) -> dict[str, list[dict]]:
    out = {}
    for reader, (b, c) in gains.items():
        rows = []
        for i in range(n):
            if i < b:
                top, rule = 0, 1
            elif i < b + c:
                top, rule = 1, 0
            else:
                top, rule = i % 2, i % 2
            for arm in g.ARMS:
                rows.append(_rec(f"q{i}", arm, top, rule))
        out[reader] = rows
    return out


def test_h1_reads_with_holm_across_the_two_readers():
    records = _records({"qwen3-8b": (39, 0), "olmo-2-1124-7b-instruct": (7, 0),
                        "qwen3.5-9b": (6, 0)})  # fmt: skip
    h1 = g.h1_block(records, 200, 42)
    olmo, qwen = h1["readers"]["olmo-2-1124-7b-instruct"], h1["readers"]["qwen3.5-9b"]
    # 7 against 0: p = 0.0156 <= 0.025; then 6 against 0: p = 0.031 <= 0.05. Both rejected.
    assert olmo["reading"] == "NONABSTAIN_HELPS" and qwen["reading"] == "NONABSTAIN_HELPS"
    records = _records({"qwen3-8b": (0, 0), "olmo-2-1124-7b-instruct": (6, 0),
                        "qwen3.5-9b": (6, 0)})  # fmt: skip
    h1 = g.h1_block(records, 200, 42)
    # Both p = 0.031 > 0.025: Holm rejects neither, though each would pass alone at 0.05.
    assert {e["reading"] for e in h1["readers"].values()} == {"NO_DETECTED_DIFFERENCE"}
    assert {e["unadjusted_label"] for e in h1["readers"].values()} == {"NONABSTAIN_HELPS"}
    records = _records({"qwen3-8b": (0, 0), "olmo-2-1124-7b-instruct": (0, 9),
                        "qwen3.5-9b": (1, 1)})  # fmt: skip
    h1 = g.h1_block(records, 200, 42)
    assert h1["readers"]["olmo-2-1124-7b-instruct"]["reading"] == "NONABSTAIN_HURTS"
    assert h1["readers"]["qwen3.5-9b"]["reading"] == "NO_DETECTED_DIFFERENCE"


def test_h2_counts_the_cost_with_an_exact_interval():
    records = _records({"qwen3-8b": (0, 8), "olmo-2-1124-7b-instruct": (1, 3),
                        "qwen3.5-9b": (0, 0)}, n=30)  # fmt: skip
    h2 = g.h2_block(records, 200, 42)
    assert h2["decides"] is False
    anchor = h2["readers"]["qwen3-8b"]
    assert anchor["b2_top4_right_rule_wrong"] == 8 and anchor["c2_rule_right_top4_wrong"] == 0
    assert anchor["cost_rate"] == pytest.approx(8 / 30)
    lo, hi = anchor["cost_rate_ci95_exact"]
    assert lo < 8 / 30 < hi and (lo, hi) == pytest.approx(mc.clopper_pearson(8, 30))
    # 8 against 0: p = 0.0078 <= 0.05/3, a COSTS description (it decides nothing).
    assert anchor["description"] == "NONABSTAIN_COSTS"
    assert anchor["unadjusted_description"] == "NONABSTAIN_COSTS"
    olmo = h2["readers"]["olmo-2-1124-7b-instruct"]
    assert (olmo["b2_top4_right_rule_wrong"], olmo["c2_rule_right_top4_wrong"]) == (3, 1)
    assert olmo["description"] == "NO_DETECTED_DIFFERENCE"
    assert olmo["net_loss_rate"] == pytest.approx(2 / 30)
    records = _records({"qwen3-8b": (9, 0), "olmo-2-1124-7b-instruct": (0, 0),
                        "qwen3.5-9b": (0, 0)}, n=30)  # fmt: skip
    assert g.h2_block(records, 200, 42)["readers"]["qwen3-8b"]["description"] == "NONABSTAIN_SAFE"


def test_break_even_and_natural_mix():
    assert g.break_even(0.1, 0.3) == pytest.approx(0.25)
    assert g.break_even(0.1, 0.0) == 1.0 and g.break_even(0.1, -0.1) == 1.0
    assert g.break_even(0.0, 0.2) == 0.0 and g.break_even(-0.1, 0.2) == 0.0
    assert g.break_even(-0.1, -0.1) is None
    answerable = _records({"x": (39, 0)}, n=347)["x"]
    unanswerable = _records({"x": (0, 6)}, n=30)["x"]
    mix = g.natural_mix(answerable, unanswerable, {"answerable": 470, "abstention": 30}, 500, 42)
    assert mix["questions"] == {"answerable": 347, "unanswerable": 30}
    assert mix["net_count"] == 39 - 6
    assert mix["gain_per_answerable"] == pytest.approx(39 / 347)
    assert mix["loss_per_unanswerable"] == pytest.approx(6 / 30)
    assert mix["mix_rate"] == pytest.approx(0.94 * 39 / 347 - 0.06 * 6 / 30)
    gain, loss = 39 / 347, 6 / 30
    assert mix["break_even_unanswerable_share"] == pytest.approx(gain / (gain + loss))
    lo, hi = mix["mix_rate_ci95"]
    assert lo <= mix["mix_rate"] <= hi
    again = g.natural_mix(answerable, unanswerable, {"answerable": 470, "abstention": 30}, 500, 42)
    assert again == mix


def test_table_record_is_am3s_and_tolerates_a_missing_second_judge():
    ranks = [3, 0, 5, 1, 7, 2, 6, 4]
    masks = {m: {"abstain": m % 3 == 0, "u": {"primary": int(m % 5 == 0),
                                               "secondary": int(m % 7 == 0)},
                 "finish": "stop", "pattern": None, "digest": "d"}
             for m in g.REQUEST_MASKS}  # fmt: skip
    pool = {"question_id": "t", "question_type": "x", "arm": "retrieved", "bm25_rank": ranks,
            "gold_mask": 1, "masks": masks}  # fmt: skip
    assert g.table_record(pool) == am3.table_record(pool)
    partial = copy.deepcopy(pool)
    partial["masks"][255]["u"]["secondary"] = None
    record = g.table_record(partial)
    assert record["u"]["secondary"] is None
    assert record["u"]["primary"] == am3.table_record(pool)["u"]["primary"]
    missing = copy.deepcopy(pool)
    missing["masks"][15]["u"]["primary"] = None
    with pytest.raises(g.Am3gError, match="V2"):
        g.table_record(missing)


# --------------------------------------------------------------------------- toy runs end to end


def _reply(reader: str, q: int, arm: str, mask: int, abstention: bool) -> str:
    if abstention:
        return f"It is green {q}." if mask % 4 == 1 and reader != "a" else "I don't know."
    if mask & 0b11 == 0b11:
        return f"It is blue {q}." if mask & 0b100 else f"Blue {q}."
    if reader == "b" and mask % 2:
        return "The memories do not mention it."
    return "I don't know." if mask % 3 else f"It is red {q}."


def _toy_run(tmp_path: Path, population: str, artifact: dict, name: str) -> Path:
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    arms = g.population_arms(config, population)
    run = tmp_path / name / "am3g"
    steps = {
        "rd-qwen3-8b": {"kind": "reader", "reader": "qwen3-8b", "status": "complete",
                        "batch_invariant": True, "enforce_eager": True},
        "rd-olmo2": {"kind": "reader", "reader": "olmo-2-1124-7b-instruct",
                     "status": "complete", "batch_invariant": True, "enforce_eager": True},
        "rd-qwen35-9b-default": {"kind": "reader", "reader": "qwen3.5-9b", "status": "complete",
                                 "batch_invariant": False, "enforce_eager": True},
        "judge32": {"kind": "judge", "status": "complete"},
        "judge8": {"kind": "judge", "status": "complete"},
    }  # fmt: skip
    run.mkdir(parents=True)
    (run / "summary.json").write_text(json.dumps(
        {"experiment_id": g.EXPERIMENT, "population": population, "steps": steps}))  # fmt: skip
    from test_memcredit_am3 import _write_pass

    passes = {}
    is_abs = population == "abstention"
    for sid, reader in (("rd-qwen3-8b", "a"), ("rd-olmo2", "b"), ("rd-qwen35-9b-default", "c")):
        rows = {}
        for r in g.request_table(artifact, arms):
            text = _reply(reader, r["question_index"], r["arm"], r["mask"], is_abs)
            rows[r["index"]] = ([100 + len(text) % 7, 151645], [-0.1, -0.01], "stop", text)
        _write_pass(run / "sessions" / sid, rows)
        passes[sid] = {i: row[3] for i, row in rows.items()}
    items = g.judge_items(artifact, pilot, config, population, passes)
    (run / "judge-items.json").write_text(json.dumps(items))
    for step, idk_yes in (("judge32", False), ("judge8", True)):
        rows = {}
        for item in items:
            q = artifact["questions"][item["question_index"]]
            if is_abs or item.get("template") == "abstention":
                yes = "don't know" in item["response"] or "not mentioned" in item["response"]
            else:
                right = q["answer"] in item["response"].lower()
                yes = right or (idk_yes and "don't know" in item["response"])
            rows[item["index"]] = ([7], [-0.01], "stop", "yes" if yes else "no")
        _write_pass(run / "sessions" / step, rows)
    return run


def _extract(tmp_path, monkeypatch, population: str, artifact: dict, name: str) -> dict:
    run = _toy_run(tmp_path, population, artifact, name)
    monkeypatch.setattr(g, "gate", lambda *a, **k: {"population": population})
    monkeypatch.setattr(g, "load_artifact", lambda *a, **k: artifact)
    monkeypatch.setattr(g, "check_dev_path", lambda *a, **k: None)
    private = tmp_path / f"private-{name}"
    args = g.argparse.Namespace(config=str(g.CONFIG_PATH), population=population,
                                run_dir=str(run), evidence="x", private_dir=str(private),
                                reference_run_dir=None)  # fmt: skip
    if population == "heldout":
        monkeypatch.setattr(g, "anchor_checks_heldout",
                            lambda *a, **k: {"pass": True, "r1_replies": {"pass": True},
                                             "r2_labels_vs_tables": {"pass": True}})  # fmt: skip
        args.reference_run_dir = str(tmp_path)
    brief = g.cmd_extract(args)
    assert set(brief["readers"]) == set(g.H2_READERS)
    return g.read_gz_json(private / f"features-{population}.json.gz")


def _relax_pins(monkeypatch, population_specs: dict) -> None:
    real = g.population_spec

    def spec(config, population):
        base = dict(real(config, population))
        base.update(population_specs.get(population, {}))
        return base

    monkeypatch.setattr(g, "population_spec", spec)


def _toy_committed_tables(artifact: dict, reader: str = "a") -> list[dict]:
    tables = []
    for q, question in enumerate(artifact["questions"]):
        for arm in g.ARMS:
            values = [1.0 if f"blue {q}" in _reply(reader, q, arm, m, False).lower() else 0.0
                      for m in range(256)]  # fmt: skip
            tables.append({"question_id": question["question_id"], "arm": arm,
                           "values_hex": g.cc.encode_values(values)})  # fmt: skip
    return tables


def test_development_extract_and_analyze_end_to_end(tmp_path, monkeypatch):
    artifact = _toy_artifact(4)
    _relax_pins(monkeypatch, {"development": {"questions": 4}})
    monkeypatch.setattr(g, "load_pinned_tables", lambda spec: _toy_committed_tables(artifact))
    features = _extract(tmp_path, monkeypatch, "development", artifact, "dev")
    check = features["comparisons"]["anchor_vs_pilot_tables"]
    assert check["cells"] == check["cells_same_label"] == 4 * 2 * 71
    config = g.load_config()
    results, per_table = g.analyze_development(copy.deepcopy(features), config)
    again, _ = g.analyze_development(copy.deepcopy(features), config)
    assert json.dumps(results, sort_keys=True) == json.dumps(again, sort_keys=True)
    assert len(per_table) == 3 * 4 * 2
    cells = results["cells"]["qwen3-8b"]["primary"]["retrieved"]
    assert cells["paired"]["nonabstain_bm25_vs_bm25_top4"]["rule_wrong_base_right"] == 0
    v = features["validation"]["judge_validation"]["primary"]
    assert v["calibration:abs-template-idk"]["yes"] == 4
    assert v["calibration:abs-template-reference"]["yes"] == 0
    blob = json.dumps(results) + json.dumps(per_table) + g.render_markdown(results)
    for text in ("blue 0", "red 1", "It is", "do not mention", "memory 3"):
        assert text not in blob


def test_registered_analyze_end_to_end_and_text_free(tmp_path, monkeypatch):
    held_artifact = _toy_artifact(6)
    abs_artifact = _toy_artifact(5, abstention=True)
    _relax_pins(monkeypatch, {"heldout": {"questions": 6}, "abstention": {"questions": 5}})
    held = _extract(tmp_path, monkeypatch, "heldout", held_artifact, "held")
    absf = _extract(tmp_path, monkeypatch, "abstention", abs_artifact, "abs")
    config = g.load_config()
    int_held, int_abs = copy.deepcopy(held), copy.deepcopy(absf)
    g.int_masks(int_held)
    g.int_masks(int_abs)
    plan = g.hand_plan(int_held, int_abs)
    labels = [{"item_id": i["item_id"], "label": int(i["uses"][0]["judge_primary"])}
              for i in plan["items"]]  # fmt: skip

    def run(h=held, a=absf, lab=labels):
        return g.analyze_registered(copy.deepcopy(h), copy.deepcopy(a) if a else None, config,
                                    None if a else "VOID (V2, incomplete): x",
                                    lab, "f" * 64)  # fmt: skip

    results, per_table = run()
    again, per_again = run()
    assert json.dumps(results, sort_keys=True) == json.dumps(again, sort_keys=True)
    assert per_table == per_again
    assert results["validity"]["v3_anchor_replay"]["pass"] is True
    assert "g_j1_replay_of_am1_validation_items" in results["validity"]
    assert results["h1_hand_check"]["status"] == "joined"
    assert results["h1_hand_check"]["agreement"]["kappa"] in (1.0, None)
    for e in results["h1"]["readers"].values():
        assert e["reading"] == e["judge_reading"]  # hand labels equal the judge's: confirmed
        assert e["scope"]
    assert results["h1"]["readers"]["qwen3.5-9b"]["engine_mode"] == "default"
    # Without labels a directional reading waits; with a missing label it is JUDGE_DEPENDENT.
    pending, _ = run(lab=None)
    assert pending["h1_hand_check"]["status"] == "missing"
    assert all(e["reading"] in ("PENDING_HAND_CHECK", "NO_DETECTED_DIFFERENCE")
               for e in pending["h1"]["readers"].values())  # fmt: skip
    if labels:
        short, _ = run(lab=labels[1:])
        assert short["h1_hand_check"]["status"] == "incomplete"
        assert all(e["reading"] in ("JUDGE_DEPENDENT", "NO_DETECTED_DIFFERENCE")
                   for e in short["h1"]["readers"].values())  # fmt: skip
    assert "natural_mix_linked_twins" in results["descriptive"]
    assert set(results["verdicts"]["H1"]) == set(g.H1_READERS) | {"status"}
    h2 = results["h2"]["readers"]
    # Reader a always abstains on the toy abstention questions: no switch, no cost. Readers b and
    # c answer on some 4-subsets, so the rule leaves correct abstentions: b2 > 0, c2 = 0.
    assert h2["qwen3-8b"]["b2_top4_right_rule_wrong"] == 0
    assert h2["olmo-2-1124-7b-instruct"]["b2_top4_right_rule_wrong"] > 0
    assert all(h2[r]["c2_rule_right_top4_wrong"] == 0 for r in g.H2_READERS)
    gj2 = results["validity"]["g_j2_abstention_judge"]
    assert gj2["idk_yes"] == [5, 5] and gj2["decoy_no"] == [5, 5] and gj2["pass"]
    mix = results["descriptive"]["natural_mix"]["primary"]["olmo-2-1124-7b-instruct"]
    assert mix["questions"] == {"answerable": 6, "unanswerable": 5}
    assert {r["population"] for r in per_table} == {"heldout", "abstention"}
    blob = json.dumps(results) + json.dumps(per_table) + g.render_markdown(results)
    for text in ("blue 0", "green 1", "It is", "red 2", "memory 4", "question 1?"):
        assert text not in blob
    # A failed anchor replay voids both hypotheses' readings (VOID before any other state).
    broken = copy.deepcopy(held)
    broken["comparisons"]["anchor"]["pass"] = False
    void, _ = run(h=broken)
    assert void["h1"]["status"].startswith(g.VOID_REPLAY)
    assert {void["h1"]["readers"][r]["reading"] for r in g.H1_READERS} == {"VOID"}
    assert void["h2"]["status"].startswith(g.VOID_REPLAY)
    # The registered H2 void path keeps H1.
    no_abs, _ = run(a=None)
    assert no_abs["h2"]["status"].startswith("VOID") and "natural_mix" not in no_abs["descriptive"]
    # A changed provenance field is the V1 void.
    other = copy.deepcopy(absf)
    other["abstention_template_sha256"] = "0" * 64
    with pytest.raises(g.Am3gError, match="V1"):
        run(a=other)
    incomplete = copy.deepcopy(held)
    incomplete["readers"].pop("qwen3.5-9b")
    with pytest.raises(g.Am3gError, match="V2"):
        run(h=incomplete)


def test_gold_free_proxy_counts():
    ranks = [3, 0, 5, 1, 7, 2, 6, 4]
    order_free = sorted([s for s in lf.FOUR_SETS if not s & 1],
                        key=lambda s: lf.rank_key(s, ranks), reverse=True)  # fmt: skip
    masks = {str(m): {"abstain": m == order_free[0]} for m in g.REQUEST_MASKS}
    pool = {"arm": "retrieved", "bm25_rank": ranks, "gold_mask": 1, "masks": masks}
    gold = dict(pool, arm="gold")
    proxy = g.gold_free_proxy({"readers": {"x": {"pools": [pool, gold]}}})
    cell = proxy["x"]["retrieved"]
    assert cell["eligible"] == 1 and cell["top_gold_free_abstains"] == 1 and cell["switches"] == 1
    assert cell["gold_free_subsets_abstaining"] == [1, 35]
    assert g.binom_tail_at_least(7, 30, 0.3) == pytest.approx(
        sum(__import__("math").comb(30, i) * 0.3**i * 0.7 ** (30 - i) for i in range(7, 31))
    )


def test_outputs_are_gz_without_mtime(tmp_path):
    path = tmp_path / "x.json.gz"
    g.write_gz_json(path, {"b": 1, "a": [1, 2]})
    raw = path.read_bytes()
    assert raw[4:8] == b"\x00\x00\x00\x00"
    assert json.loads(gzip.decompress(raw)) == {"a": [1, 2], "b": 1}


def _anchor_fixture(
    tmp_path: Path, monkeypatch, flip_token: bool = False, flip_table: bool = False
):
    """A toy held-out population with a job-1458-like reference (AM1's 265-request pools: 256
    subsets, 8 swaps, 1 reorder), its judge passes and committed-style tables."""

    from test_memcredit_am3 import _write_pass

    config = g.load_config()
    pilot = g.load_pilot_config(config)
    artifact = _toy_artifact(3)
    new_requests = g.request_table(artifact, g.ARMS)
    texts = {r["index"]: _reply("a", r["question_index"], r["arm"], r["mask"], False)
             for r in new_requests}  # fmt: skip
    anchor_rows = {i: {"tokens": (len(t) % 7, 151645), "bits": b"\x00\x00\x80\xbf",
                       "finish": "stop", "text": t} for i, t in texts.items()}  # fmt: skip
    ref_requests = ms.request_table(artifact, list(g.ARMS))
    ref_rows, ref_texts = {}, {}
    for r in ref_requests:
        mask = r.get("mask", 0) if r["kind"] == "table" else 0
        text = _reply("a", r["question_index"], r["arm"], mask, False)
        if r["kind"] != "table":
            text = "Placebo reply."
        tokens = [len(text) % 7, 151645]
        if flip_token and r["kind"] == "table" and r["question_index"] == 1 and mask == 255:
            tokens = [99, 151645]
        ref_rows[r["index"]] = (tokens, [-0.5, -0.01], "stop", text)
        ref_texts[r["index"]] = text
    ref = tmp_path / "ref"
    _write_pass(ref / "sessions" / "reader-gpu0", ref_rows)
    validation = ms.validation_items(artifact, pilot["judge"]["validation"])
    ref_items = ms.judge_item_table(artifact, ref_texts, ref_requests, validation)
    (ref / "judge-items.json").write_text(json.dumps(ref_items))

    def label(item):
        q = artifact["questions"][item["question_index"]]
        return "yes" if q["answer"] in item["response"].lower() else "no"

    for step in ("judge32-gpu0", "judge8-gpu0"):
        _write_pass(ref / "sessions" / step,
                    {i["index"]: ([7], [-0.01], "stop", label(i)) for i in ref_items})  # fmt: skip
    items = g.judge_items(artifact, pilot, config, "heldout", {"rd-qwen3-8b": texts})
    labels = {j: {i["index"]: int(label(i) == "yes") for i in items} for j in g.JUDGES}
    item_of = am3.item_index(items)
    pools = g.pool_records(artifact, g.ARMS, anchor_rows, item_of, labels)
    tables = []
    for q, question in enumerate(artifact["questions"]):
        for arm in g.ARMS:
            values = [1.0 if f"blue {q}" in _reply("a", q, arm, m, False).lower() else 0.0
                      for m in range(256)]  # fmt: skip
            if flip_table and (q, arm) == (2, "gold"):
                values[sorted(lf.FOUR_SETS)[3]] = 1.0 - values[sorted(lf.FOUR_SETS)[3]]
            tables.append({"question_id": question["question_id"], "arm": arm,
                           "values_hex": g.cc.encode_values(values)})  # fmt: skip
    pinned = {
        p: g.sha256_file(ref / p) for p in config["populations"]["heldout"]["reference"]["sha256"]
    }
    _relax_pins(monkeypatch, {"heldout": {"reference": dict(
        config["populations"]["heldout"]["reference"], sha256=pinned)}})  # fmt: skip
    monkeypatch.setattr(g, "load_heldout_tables", lambda config: tables)
    return config, artifact, anchor_rows, pools, labels, item_of, items, ref


def test_anchor_checks_pass_on_an_exact_replay(tmp_path, monkeypatch):
    config, artifact, rows, pools, labels, item_of, items, ref = _anchor_fixture(
        tmp_path, monkeypatch
    )
    out = g.anchor_checks_heldout(config, artifact, rows, pools, labels, item_of, items, ref)
    cells = 3 * 2 * 71
    assert out["pass"] is True
    assert out["r1_replies"]["identical_tokens"] == out["r1_replies"]["cells"] == cells
    assert out["r1_replies"]["identical_bits"] == 0  # bits are reported, not gated
    assert out["r2_labels_vs_tables"]["cells_same_label"] == cells
    replay = out["judge_item_replay"]["primary"]
    assert replay["compared"] > 0 and replay["same"] == replay["compared"]


@pytest.mark.parametrize("flip", ["token", "table"])
def test_anchor_checks_fail_on_one_difference(tmp_path, monkeypatch, flip):
    config, artifact, rows, pools, labels, item_of, items, ref = _anchor_fixture(
        tmp_path, monkeypatch, flip_token=flip == "token", flip_table=flip == "table"
    )
    out = g.anchor_checks_heldout(config, artifact, rows, pools, labels, item_of, items, ref)
    assert out["pass"] is False
    if flip == "token":
        assert out["r1_replies"]["pass"] is False
        assert out["r1_replies"]["token_differences"] == [
            {"question_id": "q1", "arm": "retrieved", "mask": 255},
            {"question_id": "q1", "arm": "gold", "mask": 255},
        ]
    else:
        assert out["r1_replies"]["pass"] is True and out["r2_labels_vs_tables"]["pass"] is False
        assert len(out["r2_labels_vs_tables"]["differing_cells"]) == 1


def test_anchor_checks_refuse_a_changed_reference_file(tmp_path, monkeypatch):
    config, artifact, rows, pools, labels, item_of, items, ref = _anchor_fixture(
        tmp_path, monkeypatch
    )
    (ref / "judge-items.json").write_text("[]")
    with pytest.raises(g.Am3gError, match="V1"):
        g.anchor_checks_heldout(config, artifact, rows, pools, labels, item_of, items, ref)


# --------------------------------------------------------------------------- H1's blind hand check


def _hand_features(gains: dict[str, int], switched_concordant: int = 3, n: int = 12) -> dict:
    """Toy held-out features: per H1 reader, ``gains[reader]`` questions where BM25 top 4 abstains
    (judged wrong) and the next 4-subset answers right (discordant), ``switched_concordant`` where
    the rule switches but both are wrong, the rest where top 4 answers (no switch)."""

    ranks = [3, 0, 5, 1, 7, 2, 6, 4]
    order = sorted(lf.FOUR_SETS, key=lambda m: lf.rank_key(m, ranks), reverse=True)
    readers = {}
    for reader in g.H2_READERS:
        pools = []
        for q in range(n):
            masks = {}
            for m in g.REQUEST_MASKS:
                masks[str(m)] = {"abstain": False, "u": {"primary": 0, "secondary": 0},
                                 "digest": f"{reader}-{q}-{m}", "finish": "stop"}  # fmt: skip
            if q < gains.get(reader, 0):
                masks[str(order[0])].update(abstain=True, digest="idk")
                masks[str(order[1])]["u"] = {"primary": 1, "secondary": 1}
            elif q < gains.get(reader, 0) + switched_concordant:
                masks[str(order[0])].update(abstain=True, digest="idk")
            else:
                masks[str(order[0])]["u"] = {"primary": q % 2, "secondary": q % 2}
            pools.append({"question_id": f"q{q:02d}", "question_type": "multi-session",
                          "arm": "retrieved", "bm25_rank": ranks, "gold_mask": 1,
                          "masks": masks})  # fmt: skip
        readers[reader] = {"pools": pools, "batch_invariant": reader != "qwen3.5-9b"}
    return {"readers": readers}


def test_hand_plan_takes_every_discordant_pair_and_as_many_distractor_questions():
    features = _hand_features({"olmo-2-1124-7b-instruct": 4, "qwen3.5-9b": 2})
    plan = g.hand_plan(copy.deepcopy(features))
    assert plan == g.hand_plan(copy.deepcopy(features))  # deterministic
    olmo = plan["readers"]["heldout"]["olmo-2-1124-7b-instruct"]
    qwen = plan["readers"]["heldout"]["qwen3.5-9b"]
    assert (olmo["discordant_questions"], olmo["distractor_questions"]) == (4, 4)
    assert (qwen["discordant_questions"], qwen["distractor_questions"]) == (2, 2)
    # Three concordant questions where the rule switched: Qwen3.5-9B's 2 come from them; OLMo-2
    # needs 4, so one comes from the questions where the rule kept top 4 (the shortfall).
    assert olmo["distractors_where_the_rule_switched"] == 3 and olmo["switched_shortfall"] == 1
    assert qwen["switched_shortfall"] == 0
    assert plan["labeller_prompt_sha256"] == g.hand_labeller_prompt_sha256()
    assert {i["check"] for i in plan["items"]} == {"answer"}
    roles = Counter(u["role"] for i in plan["items"] for u in i["uses"])
    assert roles["discordant-rule"] == roles["discordant-top4"] == 6
    assert roles["distractor"] == 12  # two replies per distractor question
    # Distractor questions come first from those where the rule left BM25 top 4.
    uses = [u for i in plan["items"] for u in i["uses"] if u["role"] == "distractor"]
    assert all(u["mask"] for u in uses)
    # The items are deduplicated by (question, reply digest): the shared "idk" top-4 reply of a
    # question is one item, used by its roles.
    keys = [(i["question_id"], i["reply_digest"]) for i in plan["items"]]
    assert len(keys) == len(set(keys))
    assert [i["item_id"] for i in plan["items"]] == [f"h{n:04d}" for n in range(len(keys))]


def _labels(plan: dict, flip: set[str] = frozenset()) -> list[dict]:
    out = []
    for item in plan["items"]:
        label = int(item["uses"][0]["judge_primary"])
        if item["item_id"] in flip:
            label = 1 - label
        out.append({"item_id": item["item_id"], "label": label})
    return out


def test_hand_check_confirms_rejects_and_reports_agreement():
    features = _hand_features({"olmo-2-1124-7b-instruct": 8, "qwen3.5-9b": 7})
    plan = g.hand_plan(copy.deepcopy(features))
    hand = g.hand_check(features, plan, _labels(plan), "a" * 64)
    assert hand["status"] == "joined"
    olmo, qwen = hand["readers"]["olmo-2-1124-7b-instruct"], hand["readers"]["qwen3.5-9b"]
    assert (olmo["b_hand"], olmo["c_hand"], qwen["b_hand"], qwen["c_hand"]) == (8, 0, 7, 0)
    assert olmo["hand_label"] == qwen["hand_label"] == "NONABSTAIN_HELPS"
    assert hand["agreement"]["agree"] == hand["agreement"]["items"]
    for reader in g.H1_READERS:
        assert g.confirm_reading("NONABSTAIN_HELPS", hand, reader) == "NONABSTAIN_HELPS"
        assert g.confirm_reading("NO_DETECTED_DIFFERENCE", hand, reader) == (
            "NO_DETECTED_DIFFERENCE"
        )
        assert g.confirm_reading("NONABSTAIN_HURTS", hand, reader) == "JUDGE_DEPENDENT"
    # The hand labeller calls two of Qwen3.5-9B's rule replies wrong: 5 against 0 cannot reject
    # at Holm's step, so its reading becomes JUDGE_DEPENDENT; OLMo-2's stands.
    flip = {i["item_id"] for i in plan["items"]
            if any(u["reader"] == "qwen3.5-9b" and u["role"] == "discordant-rule"
                   for u in i["uses"])}  # fmt: skip
    hand2 = g.hand_check(features, plan, _labels(plan, set(sorted(flip)[:2])), "a" * 64)
    assert hand2["readers"]["qwen3.5-9b"]["b_hand"] == 5
    assert g.confirm_reading("NONABSTAIN_HELPS", hand2, "qwen3.5-9b") == "JUDGE_DEPENDENT"
    assert g.confirm_reading("NONABSTAIN_HELPS", hand2, "olmo-2-1124-7b-instruct") == (
        "NONABSTAIN_HELPS"
    )
    assert hand2["agreement"]["agree"] == hand2["agreement"]["items"] - 2


def test_hand_check_status_without_or_with_bad_labels():
    features = _hand_features({"olmo-2-1124-7b-instruct": 8, "qwen3.5-9b": 7})
    plan = g.hand_plan(copy.deepcopy(features))
    assert g.hand_check(features, plan, None, None)["status"] == "missing"
    assert g.confirm_reading("NONABSTAIN_HELPS", {"status": "missing"}, "x") == (
        "PENDING_HAND_CHECK"
    )
    labels = _labels(plan)
    for bad in (labels[1:], labels + [labels[0]], labels + [{"item_id": "zzz", "label": 1}],
                [dict(labels[0], label=2)] + labels[1:]):  # fmt: skip
        hand = g.hand_check(features, plan, bad, "a" * 64)
        assert hand["status"] == "incomplete"
        assert g.confirm_reading("NONABSTAIN_HELPS", hand, "qwen3.5-9b") == "JUDGE_DEPENDENT"


def test_hand_labels_must_match_the_committed_digest(tmp_path):
    path = tmp_path / "hand-labels.jsonl"
    path.write_text('{"item_id": "h0000", "label": 1}\n')
    rows, digest = g.read_hand_labels(path, g.sha256_file(path))
    assert rows == [{"item_id": "h0000", "label": 1}]
    with pytest.raises(g.Am3gError, match="committed"):
        g.read_hand_labels(path, "0" * 64)
    with pytest.raises(g.Am3gError, match="committed"):
        g.read_hand_labels(path, None)


def _hand_sample_fixture(tmp_path, monkeypatch):
    """The sample file carries only the item id, the question id and type, the check, the
    question, the reference text and the reply: no judge label, reader, role, mask or rule
    identity. It sits in its own directory with the instructions, the chunks and their prompts,
    never beside the features."""

    artifact = _toy_artifact(6)
    _relax_pins(monkeypatch, {"development": {"questions": 6}})
    monkeypatch.setattr(g, "load_pinned_tables", lambda spec: _toy_committed_tables(artifact))
    monkeypatch.setattr(g, "HAND_CHUNK", 5)
    features = _extract(tmp_path, monkeypatch, "development", artifact, "dev")
    features_path = tmp_path / "features.json.gz"
    g.write_gz_json(features_path, features)
    run = tmp_path / "dev" / "am3g"
    hand_dir = tmp_path / "hand"
    args = g.argparse.Namespace(config=str(g.CONFIG_PATH), population="development",
                                run_dir=str(run), evidence="x", features=str(features_path),
                                abstention_features=None, abstention_run_dir=None,
                                abstention_evidence=None, hand_dir=str(hand_dir))  # fmt: skip
    out = g.cmd_hand_sample(args)
    rows = [json.loads(line) for line in
            (hand_dir / "hand-check-sample.jsonl").read_text().splitlines()]  # fmt: skip
    plan = g.hand_plan(copy.deepcopy(features))
    assert out["items"] == len(rows) == len(plan["items"])
    assert out["plan_sha256"] == plan["plan_sha256"]
    assert [r["item_id"] for r in rows] == [i["item_id"] for i in plan["items"]]
    allowed = {"item_id", "question_id", "question_type", "check", "question", "reference",
               "reply"}  # fmt: skip
    assert all(set(r) == allowed for r in rows)
    blob = json.dumps(rows)
    for leak in ("judge", "discordant", "distractor", "olmo", "qwen", "mask", "rule"):
        assert leak not in blob.lower()
    assert "Blind hand check" in (hand_dir / "hand-check-instructions.txt").read_text()
    manifest = json.loads((hand_dir / "hand-manifest.json").read_text())
    assert manifest["labeller_model"] == "claude-opus-5-5"
    assert len(manifest["first"]) == out["chunks"] == -(-len(rows) // 5)
    first = manifest["first"][0]
    chunk_rows = (hand_dir / first["chunk"]).read_text().splitlines()
    assert [json.loads(x)["item_id"] for x in chunk_rows] == first["items"]
    prompt = (hand_dir / "hand-first-prompt-01.txt").read_text()
    assert prompt == g.hand_labeller_prompt(first["chunk"], first["output"])
    assert sorted(p.name for p in hand_dir.iterdir() if "features" in p.name) == []
    with pytest.raises(g.Am3gError, match="non-empty"):
        g.cmd_hand_sample(args)
    return hand_dir, rows


def test_hand_sample_is_blind_and_matches_the_plan(tmp_path, monkeypatch):
    _hand_sample_fixture(tmp_path, monkeypatch)


CHUNK_DIR = "/mac/work/first/first-01"


def _write_transcript(hand_dir, stage, n, chunk, extra=(), wrote=True, launch="cli",
                      model="claude-opus-5-5", prompt=True, agent="a1",
                      start="2026-10-15T10:00:01Z", block="tool_use"):  # fmt: skip
    """A labeller transcript: in the CLI's stream-json form (bare file names, no prompt line), or
    in a subagent's form (the absolute-path prompt first, absolute paths, the agent id and a
    timestamp on every line). Read the two inputs, any ``extra`` calls, then Write the output."""

    tdir = hand_dir / "transcripts"
    tdir.mkdir(exist_ok=True)
    d = f"/mac/work/{stage}/{stage}-{n:02d}"
    where = (lambda nm: nm) if launch == "cli" else (lambda nm: f"{d}/{nm}")
    calls = [("Read", "hand-check-instructions.txt"), ("Read", chunk["chunk"]), *extra]
    if wrote:
        calls.append(("Write", chunk["output"]))
    common = {"agentId": agent, "timestamp": start} if launch == "subagent" else {}
    lines = []
    if launch == "subagent" and prompt:
        text = g.hand_labeller_prompt(f"{d}/{chunk['chunk']}", f"{d}/{chunk['output']}",
                                      f"{d}/hand-check-instructions.txt")  # fmt: skip
        lines.append(json.dumps({"type": "user", "message": {"role": "user", "content": text},
                                 **common}))  # fmt: skip
        files = [{"path": "/home/x/CLAUDE.md", "type": "User"}]
        attachment = {"type": "instructions", "files": files}
        lines.append(json.dumps({"type": "attachment", **common, "attachment": attachment}))
    else:
        lines.append(json.dumps({"type": "system", "subtype": "init", "session_id": "s1"}))
    for k, (name, target) in enumerate(calls):
        tool_input = {"file_path": where(target)} if target else {"command": "ls"}
        if target and target.startswith("/"):
            tool_input = {"file_path": target}
        payload = {"type": block if name != "Bash" else "tool_use", "id": f"t{k}", "name": name,
                   "input": tool_input}  # fmt: skip
        message = {"role": "assistant", "model": model, "content": [payload]}
        lines.append(json.dumps({"type": "assistant", "message": message, **common}))
        result = {"type": "tool_result", "tool_use_id": f"t{k}", "content": "ok"}
        reply = {"role": "user", "content": [result]}
        lines.append(json.dumps({"type": "user", "message": reply, **common}))
    (tdir / f"{stage}-{n:02d}.jsonl").write_text("\n".join(lines) + "\n")


def _write_launch(hand_dir, stage, manifest, launch="cli", attempts=None):
    """The launch record that ``am3g-hand-label-mac.sh`` pushes."""

    chunks = manifest[stage]
    nns = [f"{n:02d}" for n in range(1, len(chunks) + 1)]
    record = {"launch": launch, "chunk_dirs": {nn: f"/mac/work/{stage}/{stage}-{nn}" for nn in nns},
              "attempts": attempts or {nn: 1 for nn in nns}}  # fmt: skip
    if launch == "subagent":
        record.update(cli_failed_at="2026-10-15T10:00:00Z", agents={nn: "a1" for nn in nns})
    (hand_dir / f"labeller-{stage}.json").write_text(json.dumps(record))


def test_audit_transcript_admits_only_the_two_reads_and_the_write(tmp_path):
    chunk = {"chunk": "hand-first-chunk-01.jsonl", "output": "hand-labels-first-01.jsonl"}

    def audit(launch="cli", agent=None, not_before=None):
        return g.audit_transcript(tmp_path / "transcripts" / "first-01.jsonl", chunk, launch,
                                  CHUNK_DIR, agent, not_before)  # fmt: skip

    assert audit() == {"pass": False, "why": "no transcript", "tool_calls": 0}
    _write_transcript(tmp_path, "first", 1, chunk)
    assert audit()["pass"] and audit()["tool_calls"] == 3
    _write_transcript(tmp_path, "first", 1, chunk, extra=[("Bash", "")])
    assert not audit()["pass"] and audit()["other_calls"] == ["Bash"]
    _write_transcript(tmp_path, "first", 1, chunk, extra=[("Read", "features.json.gz")])
    assert audit()["other_calls"] == ["Read features.json.gz"]
    _write_transcript(tmp_path, "first", 1, chunk, extra=[("Write", "elsewhere.jsonl")])
    assert not audit()["pass"]
    _write_transcript(tmp_path, "first", 1, chunk, wrote=False)
    assert audit()["why"] == "the output was not written"
    path = tmp_path / "transcripts" / "first-01.jsonl"
    _write_transcript(tmp_path, "first", 1, chunk)
    path.write_text(path.read_text() + "{truncated\n")
    assert not audit()["pass"] and audit()["unreadable_lines"] == 1
    # Check 3: the model, the paths, the tool-call block types.
    _write_transcript(tmp_path, "first", 1, chunk, model="claude-sonnet-x")
    assert "an assistant line of another model" in audit()["failures"]
    _write_transcript(tmp_path, "first", 1, chunk,
                      extra=[("Read", "/elsewhere/hand-first-chunk-01.jsonl")])  # fmt: skip
    assert audit()["other_calls"] == ["Read hand-first-chunk-01.jsonl (outside the chunk)"]
    _write_transcript(tmp_path, "first", 1, chunk, block="server_tool_use")
    assert not audit()["pass"] and "server_tool_use hand-check-instructions.txt" in \
        audit()["other_calls"]  # fmt: skip


def test_audit_transcript_checks_a_subagent_against_its_launch_record(tmp_path):
    chunk = {"chunk": "hand-first-chunk-01.jsonl", "output": "hand-labels-first-01.jsonl"}
    failed = g._iso_seconds("2026-10-15T10:00:00Z")

    def audit(agent="a1", not_before=failed):
        return g.audit_transcript(tmp_path / "transcripts" / "first-01.jsonl", chunk,
                                  "subagent", CHUNK_DIR, agent, not_before)  # fmt: skip

    _write_transcript(tmp_path, "first", 1, chunk, launch="subagent")
    out = audit()
    assert out["pass"], out
    assert out["agent_ids"] == ["a1"] and out["instruction_files"] == [["User", "CLAUDE.md"]]
    assert out["first_prompt_sha256"] == g.sha256_text(g.hand_labeller_prompt(
        f"{CHUNK_DIR}/{chunk['chunk']}", f"{CHUNK_DIR}/{chunk['output']}",
        f"{CHUNK_DIR}/hand-check-instructions.txt").strip())  # fmt: skip
    assert "agent id differs from the launch record" in audit(agent="a2")["failures"]
    _write_transcript(tmp_path, "first", 1, chunk, launch="subagent", start="2026-10-15T09:59:00Z")
    assert "a line without a timestamp after the CLI's failure" in audit()["failures"]
    _write_transcript(tmp_path, "first", 1, chunk, launch="subagent", prompt=False)
    assert "no first prompt" in audit()["failures"]
    # Bare names are the CLI's; a subagent must use the chunk directory's absolute paths.
    _write_transcript(tmp_path, "first", 1, chunk, launch="subagent",
                      extra=[("Read", "hand-check-instructions.txt")])  # fmt: skip
    t = tmp_path / "transcripts" / "first-01.jsonl"
    t.write_text(t.read_text().replace(f"{CHUNK_DIR}/hand-check-instructions.txt",
                                       "hand-check-instructions.txt", 1))  # fmt: skip
    assert not audit()["pass"]


def test_hand_merge_drops_a_chunk_whose_transcript_fails_the_audit(tmp_path, monkeypatch):
    hand_dir, rows = _hand_sample_fixture(tmp_path, monkeypatch)
    manifest = json.loads((hand_dir / "hand-manifest.json").read_text())
    _write_launch(hand_dir, "first", manifest)
    for n, chunk in enumerate(manifest["first"], start=1):
        lines = [json.dumps({"item_id": i, "label": 1, "note": ""}) for i in chunk["items"]]
        (hand_dir / chunk["output"]).write_text("\n".join(lines) + "\n")
        _write_transcript(hand_dir, "first", n, chunk, extra=[("Glob", "")] if n == 1 else ())
    first = g.cmd_hand_merge(g.argparse.Namespace(hand_dir=str(hand_dir), stage="first"))
    assert first["chunks_failing_the_transcript_audit"] == [manifest["first"][0]["output"]]
    assert first["items_lacking_a_valid_row"] == len(manifest["first"][0]["items"])
    manifest = json.loads((hand_dir / "hand-manifest.json").read_text())
    assert [i for c in manifest["repair"] for i in c["items"]] == manifest["first"][0]["items"]
    # The raw file keeps whatever every chunk held, the failing chunk's rows included.
    raw = (hand_dir / "hand-labels-first-raw.jsonl").read_text().splitlines()
    assert len(raw) == len(rows)


def test_hand_merge_needs_the_launch_record_and_voids_an_extra_attempt(tmp_path, monkeypatch):
    hand_dir, rows = _hand_sample_fixture(tmp_path, monkeypatch)
    manifest = json.loads((hand_dir / "hand-manifest.json").read_text())
    for n, chunk in enumerate(manifest["first"], start=1):
        lines = [json.dumps({"item_id": i, "label": 1, "note": ""}) for i in chunk["items"]]
        (hand_dir / chunk["output"]).write_text("\n".join(lines) + "\n")
        _write_transcript(hand_dir, "first", n, chunk, launch="subagent")
    args = g.argparse.Namespace(hand_dir=str(hand_dir), stage="first")
    with pytest.raises(g.Am3gError, match="launch record"):
        g.cmd_hand_merge(args)
    (hand_dir / "labeller-first.json").write_text(json.dumps({"launch": "subagent"}))
    with pytest.raises(g.Am3gError, match="CLI's recorded failure"):
        g.cmd_hand_merge(args)
    _write_launch(hand_dir, "first", manifest, "subagent", attempts={"01": 2})
    out = g.cmd_hand_merge(args)
    assert out["void"].startswith("more than one labelling attempt for chunk(s) 01")
    assert (hand_dir / "hand-labels.jsonl").read_text() == ""
    assert out["labelling_attempts"] == 2 and "repair" not in json.loads(
        (hand_dir / "hand-manifest.json").read_text())  # fmt: skip
    # The void labels (none) join as "incomplete", so a directional reading is JUDGE_DEPENDENT.
    assert g.read_hand_labels(hand_dir / "hand-labels.jsonl", out["final_sha256"])[0] == []
    assert g.confirm_reading("NONABSTAIN_HELPS", {"status": "incomplete"}, "x") == "JUDGE_DEPENDENT"


def test_hand_merge_runs_one_stage_and_one_repair(tmp_path, monkeypatch):
    hand_dir, rows = _hand_sample_fixture(tmp_path, monkeypatch)
    manifest = json.loads((hand_dir / "hand-manifest.json").read_text())
    ids = manifest["items"]
    # The first stage: chunk 1 complete, one row of chunk 2 malformed, one repeated, chunk 3
    # missing altogether (no output, no transcript).
    for n, chunk in enumerate(manifest["first"]):
        if n == 2:
            continue
        lines = [json.dumps({"item_id": i, "label": 1, "note": ""}) for i in chunk["items"]]
        if n == 1:
            lines[0] = "not json"
            lines.append(lines[1])
        (hand_dir / chunk["output"]).write_text("\n".join(lines) + "\n")
        _write_transcript(hand_dir, "first", n + 1, chunk)
    _write_launch(hand_dir, "first", manifest)
    first = g.cmd_hand_merge(g.argparse.Namespace(hand_dir=str(hand_dir), stage="first"))
    lacking = first["items_lacking_a_valid_row"]
    assert first["malformed_rows"] == 1 and first["repeated_items"] == 1
    expected = 2 + len(manifest["first"][2]["items"]) if len(manifest["first"]) > 2 else 2
    assert lacking == expected and not (hand_dir / "hand-labels.jsonl").exists()
    manifest = json.loads((hand_dir / "hand-manifest.json").read_text())
    repair_ids = [i for c in manifest["repair"] for i in c["items"]]
    assert len(repair_ids) == lacking
    _write_launch(hand_dir, "repair", manifest)
    for n, chunk in enumerate(manifest["repair"], start=1):
        (hand_dir / chunk["output"]).write_text("".join(
            json.dumps({"item_id": i, "label": 0}) + "\n" for i in chunk["items"]))  # fmt: skip
        _write_transcript(hand_dir, "repair", n, chunk)
    repair = g.cmd_hand_merge(g.argparse.Namespace(hand_dir=str(hand_dir), stage="repair"))
    assert repair["final_complete"] and repair["final_rows"] == len(ids)
    final = [json.loads(x) for x in (hand_dir / "hand-labels.jsonl").read_text().splitlines()]
    assert [r["item_id"] for r in final] == ids
    assert {r["item_id"] for r in final if r["label"] == 0} == set(repair_ids)
    with pytest.raises(g.Am3gError, match="no further"):
        g.cmd_hand_merge(g.argparse.Namespace(hand_dir=str(hand_dir), stage="repair"))


def test_hand_plan_mixes_in_the_abstention_questions_descriptively():
    held = _hand_features({"olmo-2-1124-7b-instruct": 8, "qwen3.5-9b": 7})
    held["population"] = "heldout"
    absent = _hand_features({"qwen3-8b": 3, "olmo-2-1124-7b-instruct": 2, "qwen3.5-9b": 1}, n=8)
    for reader in absent["readers"].values():
        for pool in reader["pools"]:
            pool["question_id"] += "_abs"
    plan = g.hand_plan(copy.deepcopy(held), copy.deepcopy(absent))
    assert set(plan["readers"]) == {"heldout", "abstention"}
    assert {i["check"] for i in plan["items"]} == {"answer", "abstention"}
    assert all(
        i["check"] == "abstention" for i in plan["items"] if i["question_id"].endswith("_abs")
    )
    hand = g.hand_check(held, plan, _labels(plan), "a" * 64)
    assert hand["status"] == "joined"
    h2 = hand["h2_descriptive"]["readers"]
    # In the toy, top 4 abstains (judged wrong) and the rule's reply is judged right, so the
    # hand labels that copy the judge give c2_hand (the rule right, top 4 wrong) = the gains.
    assert (h2["qwen3-8b"]["c2_hand"], h2["qwen3-8b"]["b2_hand"]) == (3, 0)
    assert hand["h2_descriptive"]["decides"] is False
    assert set(hand["agreement_by_population"]) == {"heldout", "abstention"}
    # H1 readings depend only on the held-out items.
    assert hand["readers"]["olmo-2-1124-7b-instruct"]["b_hand"] == 8


def test_combined_power_matches_the_registered_table():
    rate = 4 / 63 / 2
    assert g.combined_power(347, rate, 1.0, 0.025) == pytest.approx(
        ks.mcnemar_power(347, rate, 1.0, 0.025, {}), abs=1e-9
    )
    values = [round(g.combined_power(347, rate, a, al), 2) for a in (1.0, 0.9, 0.8)
              for al in (0.025, 0.05)]  # fmt: skip
    assert values == [0.93, 0.96, 0.87, 0.93, 0.78, 0.88]


def test_hedge_flag_and_gains_that_hedge():
    assert g.HEDGE_RE.search(mc.normalize_answer("It was either Paris or Rome."))
    assert not g.HEDGE_RE.search(mc.normalize_answer("It was Paris."))
    features = _hand_features({"olmo-2-1124-7b-instruct": 3, "qwen3.5-9b": 2})
    ranks = [3, 0, 5, 1, 7, 2, 6, 4]
    order = sorted(lf.FOUR_SETS, key=lambda m: lf.rank_key(m, ranks), reverse=True)
    features["readers"]["olmo-2-1124-7b-instruct"]["pools"][0]["masks"][str(order[1])]["hedge"] = (
        True
    )
    out = g.gains_that_hedge(features, g.H1_READERS)
    assert out["readers"]["olmo-2-1124-7b-instruct"] == {"gains": 3, "gains_whose_reply_hedges": 1}
    assert out["readers"]["qwen3.5-9b"] == {"gains": 2, "gains_whose_reply_hedges": 0}


def test_h2_reports_the_cost_per_correct_abstention_and_by_near_miss_memory():
    records = _records({"qwen3-8b": (0, 8), "olmo-2-1124-7b-instruct": (0, 0),
                        "qwen3.5-9b": (0, 0)}, n=30)  # fmt: skip
    strata = {f"q{i}": i % 2 == 0 for i in range(30)}
    h2 = g.h2_block(records, 200, 42, strata=strata)
    anchor = h2["readers"]["qwen3-8b"]
    # In the toy, top 4 "abstains" exactly where the rule switches (8 questions, all right).
    assert anchor["bm25_top4_correct_abstentions"] == 8
    assert anchor["cost_per_correct_top4_abstention"] == 1.0
    split = anchor["by_near_miss_memory"]
    assert split["pool_holds_a_has_answer_memory"]["questions"] == 15
    assert (split["pool_holds_a_has_answer_memory"]["b2"]
            + split["pool_holds_none"]["b2"]) == 8  # fmt: skip


def test_the_plan_digest_binds_the_labels():
    hand = {"plan_sha256": "a" * 64}
    g.check_hand_plan(hand, "a" * 64)
    for bad in ("b" * 64, None):
        with pytest.raises(g.Am3gError, match="plan"):
            g.check_hand_plan(hand, bad)


def test_gated_commands_refuse_another_config(tmp_path, capsys):
    other = tmp_path / "config.yaml"
    other.write_text(g.CONFIG_PATH.read_text())
    for argv in (["extract", "--population", "heldout", "--run-dir", "x", "--evidence", "x",
                  "--private-dir", str(tmp_path / "p")],
                 ["analyze", "--heldout-features", "x", "--abstention-void", "v",
                  "--output-dir", str(tmp_path / "o")],
                 ["hand-sample", "--population", "heldout", "--run-dir", "x", "--evidence", "x",
                  "--features", "x", "--hand-dir", str(tmp_path / "h")]):  # fmt: skip
        assert g.main([*argv, "--config", str(other)]) == 2
        assert "pinned config" in capsys.readouterr().err


# --------------------------------------------------------------------------- the rerun rule


def _summary(**steps) -> dict:
    base = {sid: {"kind": "reader", "status": "complete"} for sid in
            ("rd-qwen3-8b", "rd-olmo2", "rd-qwen35-9b-default")}  # fmt: skip
    base |= {"rd-olmo2-default": {"status": "not-needed"}, "judge32": {"status": "complete"},
             "judge8": {"status": "complete"}}  # fmt: skip
    for sid, rec in steps.items():
        base[sid] = rec
    return {"steps": base, "model_verification": {}}


@pytest.mark.parametrize(
    ("summary", "termination", "decision"),
    [
        (_summary(), {"reason": "completed"}, "complete"),
        (_summary(judge8={"status": "partial"}), {"reason": "completed"}, "complete"),
        (None, {"reason": "gpu_prolog_unavailable"}, "rerun"),
        (None, {"reason": "workload_failed"}, "rerun"),
        (None, {"reason": "hard_stop"}, "no-rerun"),
        ({"steps": {}, "model_verification": {"error": "x"}}, {"reason": "workload_failed"},
         "void"),
        (_summary(**{"rd-olmo2": {"status": "engine-failed"},
                     "rd-olmo2-default": {"status": "complete"}}), {"reason": "completed"},
         "complete"),
        (_summary(**{"rd-olmo2": {"status": "engine-failed"},
                     "rd-olmo2-default": {"status": "engine-failed"}}), {"reason": "completed"},
         "rerun"),
        (_summary(**{"rd-qwen3-8b": {"status": "smoke-failed"}}), {"reason": "completed"},
         "rerun"),
        (_summary(**{"rd-qwen3-8b": {"status": "failed"}}), {"reason": "completed"}, "rerun"),
        (_summary(**{"rd-qwen3-8b": {"status": "failed", "worker_done": {"exit": 2}}}),
         {"reason": "completed"}, "void"),
        (_summary(**{"rd-qwen35-9b-default": {"status": "partial"}}), {"reason": "completed"},
         "no-rerun"),
        (_summary(judge32={"status": "skipped", "reason": "remaining 650 s"}),
         {"reason": "completed"}, "no-rerun"),
        (_summary(judge32={"status": "failed", "killed": "late"}), {"reason": "completed"},
         "no-rerun"),
        (_summary(judge32={"status": "skipped", "reason": "SIGTERM"}),
         {"reason": "signal_TERM_checkpoint_confirmed", "finished_at": "2026-10-15T11:00:00Z",
          "hard_stop_at": "2026-10-15T11:02:00Z"}, "no-rerun"),
        (_summary(judge32={"status": "skipped", "reason": "SIGTERM"}),
         {"reason": "signal_TERM_checkpoint_confirmed", "finished_at": "2026-10-15T10:00:00Z",
          "hard_stop_at": "2026-10-15T11:02:00Z"}, "rerun"),
    ],
)  # fmt: skip
def test_the_rerun_rule_is_mechanical(summary, termination, decision):
    assert g.rerun_decision(summary, termination)["decision"] == decision


def test_rerun_decision_reads_a_job_directory(tmp_path):
    job = tmp_path / "1500"
    (job / "am3g").mkdir(parents=True)
    (job / "termination.env").write_text("job_id=1500\nreason=completed\n")
    (job / "am3g" / "summary.json").write_text(json.dumps(_summary()))
    out = g.cmd_rerun_decision(g.argparse.Namespace(population="heldout", job_dir=str(job),
                                                    is_rerun=False))  # fmt: skip
    assert out["decision"] == "complete" and out["job_dir"] == "1500"
    (job / "am3g" / "summary.json").write_text("[1, 2]")
    with pytest.raises(g.Am3gError, match="V2.*not a JSON object"):
        g.cmd_rerun_decision(g.argparse.Namespace(population="heldout", job_dir=str(job),
                                                  is_rerun=False))  # fmt: skip


def test_check_2_cases_of_the_rerun_rule():
    """(a) a signal mid-pass leaves a partial pass: a rerun unless the signal came at the limit;
    (b) the lane's hard stop kills the driver mid-step, whose status never reaches the summary:
    no rerun; and a rerun of a rerun is void."""

    partial = _summary(**{"rd-qwen35-9b-default": {"status": "partial"}})
    partial["signal"] = "SIGTERM"
    early = {"reason": "signal_TERM_checkpoint_confirmed", "finished_at": "2026-10-15T10:00:00Z",
             "hard_stop_at": "2026-10-15T11:02:00Z"}  # fmt: skip
    late = early | {"finished_at": "2026-10-15T11:00:30Z"}
    assert g.rerun_decision(partial, early)["decision"] == "rerun"
    assert g.rerun_decision(partial, late)["decision"] == "no-rerun"
    killed = _summary()
    for sid in ("rd-qwen35-9b-default", "judge32", "judge8"):
        killed["steps"].pop(sid)
    assert g.rerun_decision(killed, {"reason": "hard_stop"})["decision"] == "no-rerun"
    assert g.rerun_decision(killed, {"reason": "completed"})["decision"] == "rerun"
    # A completed job stays complete whatever the lane says about its end.
    assert g.rerun_decision(_summary(), {"reason": "hard_stop"})["decision"] == "complete"
    crashed = _summary(**{"rd-qwen3-8b": {"status": "failed"}})
    again = g.rerun_decision(crashed, {"reason": "completed"}, is_rerun=True)
    assert again["decision"] == "void" and again["rule"] == "V2"


# --------------------------------------------------------------------------- twins and tables


def test_twin_membership_takes_the_split_first():
    split = {"development": ["d1", "d2"], "heldout": ["h1", "h2"]}
    by_id = {k: {} for k in ("d1", "d2", "h1", "h2", "x")}
    excluded = {"d2", "h2"}
    assert g.twin_membership("d2", by_id, split, excluded) == "development"
    assert g.twin_membership("h2", by_id, split, excluded) == "heldout-step0-demo-excluded"
    assert g.twin_membership("h1", by_id, split, excluded) == "heldout-confirmatory"
    assert g.twin_membership("x", by_id, split, excluded) == "not-usable"
    assert g.twin_membership("y", by_id, split, excluded) == "absent"


def test_twin_text_overlap_is_counted_without_text():
    config = g.load_config()
    pilot = g.load_pilot_config(config)
    records = _toy_dataset()
    split = {"development": ["0000abcd", "0001abcd"], "heldout": ["0002abcd"]}
    artifact, facts = g.build_abstention_artifact(records, pilot, split, config)
    for f in facts["twins"]:
        # The toy abstention record reuses its twin's first 20 turns, so every pool memory is
        # among the twin's user turns.
        assert f["pool_memories_in_twin_user_turns"] == 8
        assert 0 <= f["pool_memories_in_twin_retrieved_pool"] <= 8
    summary = g.abstention_summary(artifact, "0" * 64, facts, pilot)
    assert summary["twin_text_overlap"]["memories"] == 24
    assert summary["twin_text_overlap"]["memories_in_twin_user_turns"] == 24


def test_natural_mix_can_resample_linked_twins_together():
    answerable = [_rec(f"t{i}", "retrieved", 0, 1 if i < 5 else 0) for i in range(20)]
    unanswerable = [_rec(f"t{i}_abs", "retrieved", 1, 0 if i < 3 else 1) for i in range(6)]
    weights = {"answerable": 470, "abstention": 30}
    plain = g.natural_mix(answerable, unanswerable, weights, 400, 42)
    linked = g.natural_mix(answerable, unanswerable, weights, 400, 42, link_twins=True)
    assert linked["bootstrap"]["linked_pairs"] == 6 and plain["bootstrap"]["linked_pairs"] == 0
    for key in ("net_count", "gain_per_answerable", "loss_per_unanswerable", "mix_rate"):
        assert linked[key] == plain[key]
    assert linked["mix_rate_ci95"][0] <= linked["mix_rate"] <= linked["mix_rate_ci95"][1]
    assert linked == g.natural_mix(answerable, unanswerable, weights, 400, 42, link_twins=True)


def test_pinned_tables_are_checked_before_use(tmp_path):
    tables = [{"question_id": "q0", "arm": "retrieved", "values_hex": "0" * 64}]
    data = json.dumps(tables).encode()
    gz = gzip.compress(data, mtime=0)
    (tmp_path / "t.json.gz").write_bytes(gz)
    spec = {"path": "t.json.gz", "sha256": g.sha256_bytes(gz), "json_sha256": g.sha256_bytes(data)}
    assert g.load_pinned_tables(spec, tmp_path) == tables
    for bad in ({"sha256": "0" * 64}, {"json_sha256": "0" * 64}, {"path": "missing.gz"}):
        with pytest.raises(g.Am3gError, match="V1"):
            g.load_pinned_tables(spec | bad, tmp_path)
    keyless = json.dumps([{"question_id": "q0"}]).encode()
    (tmp_path / "k.json.gz").write_bytes(gzip.compress(keyless, mtime=0))
    with pytest.raises(g.Am3gError, match="not a list of tables"):
        g.load_pinned_tables({"path": "k.json.gz",
                              "sha256": g.sha256_file(tmp_path / "k.json.gz"),
                              "json_sha256": g.sha256_bytes(keyless)}, tmp_path)  # fmt: skip
    pool = {"question_id": "q9", "arm": "gold", "masks": {}}
    with pytest.raises(g.Am3gError, match="lack 1 pools"):
        g.labels_vs_tables([pool], tables)


def test_the_configs_tables_pins_are_the_committed_files():
    """Both tables files are hashed, and the development one is opened (the pilot's, not
    held-out); the held-out one's entries are not decoded here."""

    config = g.load_config()
    held = config["populations"]["heldout"]["tables"]
    assert g.sha256_file(ROOT / held["path"]) == held["sha256"]
    dev = g.load_pinned_tables(config["populations"]["development"]["tables"])
    assert len(dev) == 126


def test_missing_judge_items_is_a_named_void_not_a_traceback(tmp_path, monkeypatch, capsys):
    artifact = _toy_artifact(2)
    _relax_pins(monkeypatch, {"development": {"questions": 2}})
    run = _toy_run(tmp_path, "development", artifact, "dev")
    (run / "judge-items.json").unlink()
    monkeypatch.setattr(g, "gate", lambda *a, **k: {})
    monkeypatch.setattr(g, "load_artifact", lambda *a, **k: artifact)
    monkeypatch.setattr(g, "check_dev_path", lambda *a, **k: None)
    code = g.main(["extract", "--population", "development", "--run-dir", str(run),
                   "--evidence", "x", "--private-dir", str(tmp_path / "p")])  # fmt: skip
    err = capsys.readouterr().err
    assert code == 2 and "VOID (V2, incomplete)" in err and "judge32 was skipped" in err
    code = g.main(["analyze", "--development-features", str(tmp_path / "none.json.gz"),
                   "--output-dir", str(tmp_path / "o")])  # fmt: skip
    err = capsys.readouterr().err
    assert code == 2 and "VOID (V2, incomplete)" in err and "Traceback" not in err
