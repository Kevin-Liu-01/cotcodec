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
import importlib.util
import json
import random
import subprocess
import sys
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


def test_step_budgets_fit_each_jobs_limit():
    """On the normal path (no fallback) every step's max_s fits in the limit minus the lane's
    210 s margin, and the registered caps are the limits' sum."""

    config = g.load_config()
    for name, job in config["jobs"].items():
        total = sum(v[1] for k, v in job["step_budgets"].items() if k != "rd-olmo2-default")
        assert total <= job["minutes"] * 60 - 210, name
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
    reg, ledger = _scratch(tmp_path, frozen=True)
    record = g.gate("heldout", ledger=ledger, registration=reg)
    assert record["registration_frozen"] and record["code_pins"]["all_match"]
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


def test_development_extract_and_analyze_end_to_end(tmp_path, monkeypatch):
    artifact = _toy_artifact(4)
    _relax_pins(monkeypatch, {"development": {"questions": 4}})
    features = _extract(tmp_path, monkeypatch, "development", artifact, "dev")
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
    results, per_table = g.analyze_registered(copy.deepcopy(held), copy.deepcopy(absf), config)
    again, per_again = g.analyze_registered(copy.deepcopy(held), copy.deepcopy(absf), config)
    assert json.dumps(results, sort_keys=True) == json.dumps(again, sort_keys=True)
    assert per_table == per_again
    assert results["validity"]["v3_anchor_replay"]["pass"] is True
    assert results["h1"]["status"] in ("read", "JUDGE_DEPENDENT: G-J1 failed; no decision follows")
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
    # A failed anchor replay voids both hypotheses' readings.
    broken = copy.deepcopy(held)
    broken["comparisons"]["anchor"]["pass"] = False
    void, _ = g.analyze_registered(broken, copy.deepcopy(absf), config)
    assert void["h1"]["status"].startswith(g.VOID_REPLAY)
    assert {void["h1"]["readers"][r]["reading"] for r in g.H1_READERS} == {"VOID"}
    assert void["h2"]["status"].startswith(g.VOID_REPLAY)
    # The registered H2 void path keeps H1.
    no_abs, _ = g.analyze_registered(copy.deepcopy(held), None, config, "VOID (V2, incomplete): x")
    assert no_abs["h2"]["status"].startswith("VOID") and "natural_mix" not in no_abs["descriptive"]
    # A changed provenance field is the V1 void.
    other = copy.deepcopy(absf)
    other["abstention_template_sha256"] = "0" * 64
    with pytest.raises(g.Am3gError, match="V1"):
        g.analyze_registered(copy.deepcopy(held), other, config)
    incomplete = copy.deepcopy(held)
    incomplete["readers"].pop("qwen3.5-9b")
    with pytest.raises(g.Am3gError, match="V2"):
        g.analyze_registered(incomplete, copy.deepcopy(absf), config)


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
