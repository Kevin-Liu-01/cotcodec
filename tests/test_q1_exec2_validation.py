"""Rule ``q1-exec2-validation/1`` (decision D37 iii): items, order, exposure (pure Python)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from harness.q1 import cost_card as cc
from harness.q1 import exec2_validation as rule
from harness.q1 import refstore, trim
from harness.q1.journal import item_key
from harness.q1.runner import Runner, RunnerConfig, WorkItem
from harness.q1.schema import make_verdict_row

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "program/evidence/2026-10-07/q1-engineering-d31/cost-card-d31.json"
SELECTION = ROOT / "program/evidence/2026-10-07/q1-engineering-d31/repilot_selection.json"


def _repilot() -> list[dict[str, str]]:
    selection = json.loads(SELECTION.read_text())
    return [
        {"kernel_id": k, "kernel_path": f"/x/{k}/kernel.py", "problem_id": e["problem_id"]}
        for e in selection["order"]
        for k in e["kernels"]
    ]


def _adversarial() -> list[dict[str, str]]:
    return [
        {
            "kernel_id": f"ctl-kernelbench-{n.replace('_', '-')}-L1-1",
            "kernel_path": f"/c/{n}/kernel.py",
            "problem_id": rule.ADVERSARIAL_PROBLEM,
        }
        for n in rule.ADVERSARIAL
    ]


def _plan() -> list[dict]:
    return rule.items(
        _repilot(), _adversarial(), store_root="/store", journal="/j/references.jsonl"
    )


def test_problem_order_is_ascending_exec2_model_cost() -> None:
    card = json.loads(CARD.read_text())
    fits, factors = card["size_model"], card["paired_concurrency"]["factors"]

    def cost(problem: str) -> float:
        return cc.kernel_replicate_seconds(
            fits, problem, factors=factors, units_of=lambda p, g: trim.item_units(p, g)[0]
        )

    problems = {k["problem_id"] for k in _repilot()}
    assert tuple(rule.problem_order(cost, problems)) == rule.PROBLEM_ORDER


def test_adversarial_items_are_consumer_gates_with_adjacent_inline_twins() -> None:
    plan = _plan()
    adversarial = [e for e in plan if e["kernel_id"].startswith("ctl-kernelbench-")]
    assert len(adversarial) == 3 * len(rule.ADVERSARIAL_GATES) * 2
    assert set(rule.ADVERSARIAL_GATES) == {"c", "A1", "A2", "A3", "A5"}
    for store, inline in zip(adversarial[::2], adversarial[1::2], strict=True):
        assert inline["kernel_id"] == store["kernel_id"] + rule.INLINE_SUFFIX
        assert inline["gate"] == store["gate"]
        assert refstore.OPTION in store["options"]
        assert refstore.OPTION not in inline["options"]
        assert not any(r.startswith("reference.") for r in inline["requires"])
    # nothing else of the plan precedes them except their reference items
    first_repilot = next(i for i, e in enumerate(plan) if e["kernel_id"].startswith("s1-"))
    assert all(
        e["kernel_id"].startswith(("ctl-kernelbench-", "reference.L1-1"))
        for e in plan[:first_repilot]
    )


def test_adversarial_kernels_are_chained() -> None:
    plan = _plan()
    by_kernel: dict[str, list[dict]] = {}
    for e in plan:
        if e["kernel_id"].startswith("ctl-kernelbench-"):
            base, _ = rule.arm_of(e["kernel_id"])
            by_kernel.setdefault(base, []).append(e)
    ids = [k["kernel_id"] for k in _adversarial()]
    assert list(by_kernel) == ids
    for previous, current in zip(ids, ids[1:], strict=False):
        keys = {item_key(e["kernel_id"], e["gate"], e["seed"]) for e in by_kernel[previous]}
        for e in by_kernel[current]:
            assert keys <= set(e["requires"])
    assert all(not any(r.startswith("ctl-") for r in e["requires"]) for e in by_kernel[ids[0]])


def test_repilot_items_round_robin_with_every_gate_and_exec2_units() -> None:
    plan = _plan()
    scoring = [e for e in plan if e["kernel_id"].startswith(("s1-", "ctl-identity-"))]
    assert len(scoring) == 24 * len(trim.SCORING_GATES)
    kernels = list(dict.fromkeys(e["kernel_id"] for e in scoring))
    roles = [rule.kernel_role(k) for k in kernels]
    assert roles == ["substrate"] * 8 + ["identity-control"] * 8 + ["mutant"] * 8
    problems = list(dict.fromkeys(e["problem_id"] for e in scoring))
    assert tuple(problems) == rule.PROBLEM_ORDER
    for e in scoring:
        units, peak = trim.item_units(e["problem_id"], e["gate"])
        assert (e["units"], e["memory_bytes"]) == (units, peak)
        assert e["seed"] == rule.REPLICATE
        assert (refstore.OPTION in e["options"]) == (e["gate"] in rule.ADVERSARIAL_GATES) or (
            e["gate"] == "c"
            and e["problem_id"]
            in {
                "L2/100_ConvTranspose3d_Clamp_Min_Divide",
                "L2/87_Conv2d_Subtract_Subtract_Mish",
            }
        )
    # reference items precede their first consumer, and none is for gate (a)
    seen: set[str] = set()
    for e in plan:
        for ref in e.get("requires") or []:
            if ref.startswith("reference."):
                assert ref in seen
        seen.add(item_key(e["kernel_id"], e["gate"], e["seed"]))
    assert not any(e["gate"] in {"ref_a", "ref_a_head"} for e in plan)


def test_exposure_refuses_evaluation_units() -> None:
    repilot, adversarial = _repilot(), _adversarial()
    exposed = trim.load_exposed()
    ok = rule.exposure(
        repilot,
        adversarial,
        calibration={k["problem_id"] for k in repilot},
        evaluation=set(),
        s2_problems=set(),
        exposed=exposed,
    )
    assert ok["ok"]
    bad = rule.exposure(
        repilot,
        adversarial,
        calibration=set(),
        evaluation={repilot[0]["problem_id"]},
        s2_problems=set(),
        exposed=exposed,
    )
    assert not bad["ok"] and bad["violations"]


class _FakeRunner(Runner):
    def __init__(self, config: RunnerConfig) -> None:
        super().__init__(config)
        self.spans: list[tuple[str, float, float]] = []
        self._spans_lock = threading.Lock()

    def execute(self, item: WorkItem, attempt: int, slot: str) -> tuple[list[dict], bool]:
        start = time.time()
        time.sleep(0.002)
        end = time.time()
        with self._spans_lock:
            self.spans.append((item.kernel_id, start, end))
        row = make_verdict_row(
            kernel_id=item.kernel_id,
            gate=item.gate,
            config_id=f"item/seed-{item.seed}",
            verdict="accept",
            tf32_policy="not-applicable",
            gpu_seconds=end - start,
            wall_seconds=end - start,
            details={"item_key": item.key, "item_final": True, "slot": slot},
            seed=item.seed,
            run_id=self.config.run_id,
            attempt=attempt,
            code_sha256="0" * 64,
        )
        return [row], False


def test_plan_runs_to_the_end_and_adversarial_kernels_never_overlap(tmp_path: Path) -> None:
    entries = _plan()
    items = [WorkItem(**{**e, "journal": None}) for e in entries]
    runner = _FakeRunner(
        RunnerConfig(
            journal_path=tmp_path / "journal.jsonl", slots=["cuda:0"] * 12, workdir=tmp_path
        )
    )
    summary = runner.run(items)
    assert summary["run"] == len(items) and summary["left_in_queue"] == 0
    windows = {}
    for kernel_id, start, end in runner.spans:
        if kernel_id.startswith("ctl-kernelbench-"):
            base, _ = rule.arm_of(kernel_id)
            lo, hi = windows.get(base, (start, end))
            windows[base] = (min(lo, start), max(hi, end))
    ordered = [windows[k["kernel_id"]] for k in _adversarial()]
    for (_, end), (start, _) in zip(ordered, ordered[1:], strict=False):
        assert end <= start


def test_items_hash_ignores_paths() -> None:
    a = _plan()
    b = rule.items(_repilot(), _adversarial(), store_root="/elsewhere", journal="/k/r.jsonl")
    assert rule.items_sha256(a) == rule.items_sha256(b)


def test_manifest_template_fails_closed_until_filled_and_fits_the_cap() -> None:
    import pytest

    yaml = pytest.importorskip("yaml")
    from scripts import submit_docker_research_job as submitter

    raw = yaml.safe_load(
        (ROOT / "experiments/manifests/q1-core/q1-exec2-validation.template.yaml").read_text()
    )
    with pytest.raises(ValueError):
        submitter.validate_manifest(dict(raw), verify_claim_files=False)
    filled = {
        **raw,
        "image_id": "sha256:" + "c" * 64,
        "git_sha": "a" * 40,
        "source_sha256": "b" * 64,
    }
    manifest = submitter.validate_manifest(filled, verify_claim_files=False)
    assert manifest["model"]["kind"] == "none"
    assert manifest["gpus"] * manifest["minutes"] / 60 <= 0.17 + 1e-9
    assert manifest["max_gpu_hours"] <= 0.17
    command = manifest["command"]
    assert (
        command[command.index("--expected-evidence-sha256") + 1] == raw["study_artifact"]["sha256"]
    )
    budget = float(command[command.index("--budget-minutes") + 1])
    assert budget <= manifest["minutes"]
    # the driver's hard deadline ends every item before the lane's SIGUSR1 (180 s early)
    from scripts import run_q1_exec2_validation as driver

    assert budget * 60 - driver.END_MARGIN_SECONDS <= manifest["minutes"] * 60 - 180 - 20
