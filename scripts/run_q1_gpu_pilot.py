#!/usr/bin/env python3
"""Q1 Stage 0 GPU pilot driver: one lane job per ``--job``, every phase time-boxed.

``--job smoke`` (no study artifact):

1. **admission** for the pilot: device-mode TorchInductor codegen of the head
   candidates of every S1 pilot stratum (``harness.q1.pilot``), conversion, the
   S2 build, the static check, the pilot selection rule, gate (b)'s launch-hook
   GPU admission of the picks (an inadmissible pick is replaced by the next in
   its stratum), and the corpus manifest;
2. **specializations** of the admitted evaluation picks (one native forward
   pass each; no mutant runs on a GPU here);
3. **controls** (CPU): hack-emulating wrappers around the evaluation picks, and
   the core reference-identity and KernelBench adversarial controls;
4. **smoke**: reference-identity controls of three KernelBench problems through
   every scoring gate and audit channel (A4's poison allocator and
   compute-sanitizer included), gate (a) at replicates 43 and 44, b1 and b2 on
   every hack control of the S1 activation pick,
   gate (a) through unmodified KernelBench at both pinned revisions, and the
   timing harness.

``--job pilot`` (study artifact holding the corpus the smoke job built and the
CPU steps derived from it, plus the unmodified KernelGYM and KBV clones):

1. **fidelity**: unmodified KernelBench (both revisions), KernelGYM
   (``b_native``) and KBV (``c1_kbv_native``) next to ours (``c1_kbv_compat``
   and the scoring rows) on the pilot substrates, the adversarial controls and
   one mutant of each of the first substrates;
2. **calibration**: A1 at M = 16, replicate 42, on the S1-cal picks, then the
   calibration driver (CPU);
3. **timing** of the first pilot substrates against their references (before
   scoring since this pass: in job 518 scoring's in-flight items used up the
   timing reserve);
4. **scoring**: ``pilot.schedule`` (every gate and channel, P0..P4), cut by the
   time box at a deterministic point; ``--scoring-prefix N`` and
   ``--scoring-shared-only`` restrict it to a registered prefix of that order
   (a paired re-measurement, for example at another ``--slots-per-gpu``).

``--phases`` selects which of these run (the unpack always runs).

Every phase writes its wall seconds to ``phases.json`` (the GPU is held for the
whole job, so phase wall time is GPU allocation time). Runs only as a one-GPU
Slurm job through the lane, on trusted code only (decisions D3, D7): KernelBench
reference code, compiler-generated and pre-2025 human-written substrates, and
harness-derived mutants and controls of them.

    python scripts/run_q1_gpu_pilot.py --job smoke --output /outputs/q1 --seeds 42 43 44
    python scripts/run_q1_gpu_pilot.py --job pilot --output /outputs/q1 \\
        --evidence /inputs/study-artifact.json --expected-evidence-sha256 SHA --seeds 42 43 44
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import sys
import time
import traceback
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import pilot  # noqa: E402
from harness.q1.runner import Runner, RunnerConfig, WorkItem, install_signal_handlers  # noqa: E402
from harness.q1.schema import iter_kernel_dirs  # noqa: E402

SMOKE_PROBLEMS = ("L1/19_ReLU", "L1/95_CrossEntropyLoss", "L2/12_Gemm_Multiply_LeakyReLU")
#: Phases of ``--job pilot`` in run order (unpack always runs first).
PILOT_PHASES = ("smoke", "fidelity", "calibration", "timing", "scoring")
#: Head candidates per S1 stratum that get device codegen (fallbacks included).
HEADS_PER_PICK = 3
#: Set by --size-scaled-watchdog (pilot job): per-item limits from pilot.watchdog_limits.
SIZE_SCALED_WATCHDOG = False


class Driver:
    def __init__(
        self,
        out: Path,
        *,
        job: str,
        budget_minutes: float,
        slots: list[str],
        dry_run: bool = False,
    ) -> None:
        self.out = out
        self.dry_run = dry_run
        self.job = job
        self.slots = slots
        self.started = time.monotonic()
        self.end = self.started + budget_minutes * 60.0
        self.phases: list[dict[str, Any]] = []
        self.failed = False
        self.current: Runner | None = None
        self.interrupted = False
        self.trigger: str | None = None
        self.signal_target: Any = None

    def arm_signals(self, record: dict[str, Any]) -> None:
        """(Re)install the SIGUSR1/SIGTERM handlers before every phase and record
        whether something replaced them (job 474 ended its time box without its
        handler running; the cause is recorded here, not assumed)."""
        import signal

        if self.signal_target is None:
            return
        current = signal.getsignal(signal.SIGUSR1)
        record["sigusr1_handler_before"] = getattr(current, "__qualname__", repr(current))
        install_signal_handlers(self.signal_target)

    def remaining(self) -> float:
        return self.end - time.monotonic()

    def write_phases(self) -> None:
        record = {
            "job": self.job,
            "slots": self.slots,
            "slots_per_gpu": len(self.slots),
            "phases": self.phases,
            "elapsed_seconds": round(time.monotonic() - self.started, 3),
        }
        tmp = self.out / ".phases.json.tmp"
        tmp.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.out / "phases.json")

    @contextlib.contextmanager
    def phase(self, name: str) -> Iterator[dict[str, Any]]:
        record: dict[str, Any] = {"phase": name, "status": "running"}
        start = time.monotonic()
        record["start_offset_seconds"] = round(start - self.started, 3)
        self.phases.append(record)
        self.arm_signals(record)
        self.write_phases()
        print(json.dumps({"phase": name, "status": "start"}), flush=True)
        try:
            yield record
            record["status"] = "ok" if record.get("status") == "running" else record["status"]
        except Exception as exc:  # recorded; the next phase still runs
            self.failed = True
            record["status"] = "failed"
            record["error"] = f"{type(exc).__name__}: {exc}"[:2000]
            record["traceback"] = traceback.format_exc()[-4000:]
        finally:
            record["seconds"] = round(time.monotonic() - start, 3)
            self.write_phases()
            print(
                json.dumps({"phase": name, "status": record["status"], "s": record["seconds"]}),
                flush=True,
            )

    def run_items(
        self,
        name: str,
        items: Sequence[WorkItem],
        *,
        budget_seconds: float,
        timing: bool = False,
        record: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run items with a soft time box (no new item after it) and a hard one."""
        budget = max(0.0, min(budget_seconds, self.remaining() - 30.0))
        now = time.monotonic()
        workdir = self.out / name / "items"
        workdir.mkdir(parents=True, exist_ok=True)
        config = RunnerConfig(
            journal_path=self.out / name / "journal.jsonl",
            slots=[] if timing else list(self.slots),
            timing_slots=[self.slots[0]] if timing else [],
            workdir=workdir,
            progress_path=self.out / name / "progress.json",
            soft_deadline=now + budget,
            # Never past the driver's own end: the job must finish before the lane's
            # SIGUSR1 window (job 474 overran its budget by the old fixed margin).
            hard_deadline=max(now + budget, min(now + budget + 330.0, self.end - 15.0)),
        )
        (self.out / name / "items.jsonl").write_text(
            "".join(json.dumps(item.__dict__, sort_keys=True) + "\n" for item in items),
            encoding="utf-8",
        )
        if self.dry_run:  # plumbing check in a GPU-less container: plan, never run
            summary = {"planned": len(items), "dry_run": True}
            if record is not None:
                record.setdefault("runs", []).append({"name": name, **summary})
            return summary
        runner = Runner(config)
        self.current = runner
        if self.signal_target is not None:
            install_signal_handlers(self.signal_target)
        try:
            summary = runner.run(items)
        finally:
            self.current = None
        if runner.trigger is not None:
            self.interrupted = True
            self.trigger = self.trigger or runner.trigger
        summary.update({"planned": len(items), "budget_seconds": round(budget, 1)})
        (self.out / name / "summary.json").write_text(
            json.dumps(summary, indent=1, sort_keys=True, default=str), encoding="utf-8"
        )
        if record is not None:
            record.setdefault("runs", []).append({"name": name, **summary})
        return summary


def _item(kernel: Any, gate: str, seed: int, options: dict | None = None) -> WorkItem:
    return WorkItem(
        kernel_id=kernel.kernel_id,
        kernel_path=str(kernel.kernel_path),
        problem_id=kernel.problem_id,
        gate=gate,
        seed=seed,
        options=dict(options or {}),
        exclusive=pilot.exclusive_problem(kernel.problem_id),
        timeouts=pilot.watchdog_limits(kernel.problem_id) if SIZE_SCALED_WATCHDOG else None,
    )


def _build_main(argv: list[str]) -> int:
    from scripts.q1_build_substrates import main as build_main

    print(json.dumps({"q1_build_substrates": argv[0]}), flush=True)
    return build_main(argv)


def _s1_candidates() -> list[dict[str, Any]]:
    from harness.q1 import problems
    from harness.q1.substrates import split as s1_split

    split = s1_split.calibration_split(problems.list_problem_ids(include_excluded=True), seed=42)
    halves = {pid: "calibration" for pid in split["calibration"]}
    halves.update({pid: "evaluation" for pid in split["evaluation"]})
    return [
        {
            "substrate_id": f"s1-inductor-{pid.replace('/', '-')}",
            "problem_id": pid,
            "source_kind": "inductor",
            "split_half": half,
        }
        for pid, half in sorted(halves.items())
    ]


def _head_problems(candidates: list[dict[str, Any]]) -> list[str]:
    """Problems whose device codegen runs: the first picks of every S1 stratum."""
    ordered = sorted(candidates, key=lambda c: pilot.pilot_key(c["substrate_id"]))
    heads: list[str] = []
    for stratum in pilot.STRATA:
        members = [c for c in ordered if stratum.predicate(c)]
        for candidate in members[: stratum.count * HEADS_PER_PICK]:
            if candidate["problem_id"] not in heads:
                heads.append(candidate["problem_id"])
    return heads


def job_smoke(driver: Driver, args: argparse.Namespace) -> None:
    from harness.q1.substrates import admission

    out = driver.out
    kb = str(PROJECT_ROOT / "harness" / "q1" / "third_party" / "kernelbench" / "problems")
    records, root = out / "records-cuda", out / "substrates-built"
    selection: dict[str, Any] = {}
    with driver.phase("admission") as record:
        s1 = _s1_candidates()
        heads = _head_problems(s1)
        record["codegen_problems"] = heads
        steps = [
            [
                "s1-codegen",
                "--kernelbench-root",
                kb,
                "--records-dir",
                str(records),
                "--mode",
                "mock-h100" if driver.dry_run else "cuda",
                "--jobs",
                "8",
                "--problems",
                *heads,
            ],
            ["s1-convert", "--records-dir", str(records), "--out-root", str(root)],
            ["s2-build", "--kernelbench-root", kb, "--out-root", str(root)],
            ["check-static", "--root", str(root)],
            ["split", "--kernelbench-root", kb, "--out", str(root / "split.json")],
        ]
        for step in steps:
            code = _build_main(step)
            record.setdefault("steps", []).append({"step": step[0], "exit": code})
            if code != 0 and not (step[0] == "s2-build" and code == 1):
                raise RuntimeError(f"{step[0]} exited {code}")
        static = {
            row["substrate_id"]: row["verdict"]
            for row in json.loads((root / "check_static.json").read_text())["rows"]
        }
        built = []
        for kernel in iter_kernel_dirs(root):
            sub = kernel.substrate or {}
            half = next(
                (c["split_half"] for c in s1 if c["substrate_id"] == kernel.kernel_id), "evaluation"
            )
            built.append(
                {
                    "substrate_id": kernel.kernel_id,
                    "problem_id": kernel.problem_id,
                    "source_kind": sub.get("source_kind"),
                    "split_half": half,
                }
            )
        hook_path = root / "admission_hook.jsonl"
        refused: set[str] = set()
        for _attempt in range(4):
            selection = pilot.select_pilot(
                built,
                eligible=lambda c, refused=frozenset(refused): (
                    static.get(c["substrate_id"]) == "pass" and c["substrate_id"] not in refused
                ),
            )
            picks = selection["evaluation"] + selection["calibration"]
            todo = [p for p in picks if not _admitted(hook_path, p, check_only=True)]
            if driver.dry_run:  # no GPU: admission is not decided, picks stand
                break
            if todo:
                admission.admit_gpu_main(root, Path(kb), hook_path, only=todo, seed=42)
            newly = {p for p in picks if not _admitted(hook_path, p)}
            if not newly:
                break
            refused |= newly
        selection["refused_by_admission"] = sorted(refused)
        selection["admission_rows"] = str(hook_path)
        (out / "pilot_selection.json").write_text(json.dumps(selection, indent=1, sort_keys=True))
        record["selection"] = {k: selection[k] for k in ("evaluation", "calibration")}
        _build_main(
            [
                "manifest",
                "--root",
                str(root),
                "--split",
                str(root / "split.json"),
                "--out",
                str(out / "corpus_manifest.json"),
            ]
        )
        for role, folder in (
            ("evaluation", "pilot-substrates"),
            ("calibration", "pilot-calibration"),
        ):
            target = out / folder
            target.mkdir(exist_ok=True)
            for substrate_id in selection[role]:
                shutil.copytree(root / substrate_id, target / substrate_id)

    with driver.phase("specializations") as record:
        from scripts.q1_record_specializations import main as record_main

        code = record_main(
            [
                "--substrates-root",
                str(out / "pilot-substrates"),
                "--out-root",
                str(out / "specializations"),
            ]
            + (["--dry-run"] if driver.dry_run else [])
        )
        record["exit"] = code
        if driver.dry_run:
            (out / "specializations").mkdir(exist_ok=True)
        if code != 0:
            raise RuntimeError(f"specialization recording exited {code}")

    with driver.phase("controls") as record:
        from harness.q1 import controls as core_controls
        from harness.q1.mutate import corpus

        manifest = corpus.build_controls(out / "pilot-substrates", None, out / "controls-hacks")
        problems_needed = sorted(
            {k.problem_id for k in iter_kernel_dirs(out / "pilot-substrates")} | set(SMOKE_PROBLEMS)
        )
        written = core_controls.write_controls(out / "controls-core", identity=problems_needed)
        record.update({"hack_controls": len(manifest["controls"]), "core_controls": len(written)})

    with driver.phase("smoke") as record:
        from harness.q1.controls import identity_control_id

        core = {k.kernel_id: k for k in iter_kernel_dirs(out / "controls-core")}
        identity = [core[identity_control_id(pid)] for pid in SMOKE_PROBLEMS]
        items = [_item(k, gate, 42) for k in identity for gate in pilot.SCORING_GATES]
        items += [_item(k, "a", seed) for k in identity for seed in args.seeds if seed != 42]
        activation = [s for s in selection.get("evaluation", []) if s.startswith("s1-")][:1]
        hacks = [
            k
            for k in iter_kernel_dirs(out / "controls-hacks")
            if activation and k.kernel_id.startswith(activation[0] + ".")
        ]
        items += [_item(k, gate, 42) for k in hacks for gate in ("b1", "b2")]
        items += [
            _item(k, gate, 42)
            for k in identity
            for gate in ("a_upstream_44130946", "a_upstream_423217d9")
        ]
        driver.run_items("smoke", items, budget_seconds=driver.remaining() - 240, record=record)

    with driver.phase("timing") as record:
        core = {k.kernel_id: k for k in iter_kernel_dirs(out / "controls-core")}
        identity = [core[identity_control_id(pid)] for pid in SMOKE_PROBLEMS]
        driver.run_items(
            "timing",
            [_item(k, "timing", 42) for k in identity],
            budget_seconds=driver.remaining() - 60,
            timing=True,
            record=record,
        )


def _admitted(hook_path: Path, substrate_id: str, *, check_only: bool = False) -> bool:
    """True when both grad modes recorded an ``accept``; with ``check_only``, True
    when any row exists (the substrate was already tried)."""
    if not hook_path.exists():
        return False
    rows = [
        json.loads(line)
        for line in hook_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    mine = [r for r in rows if r["kernel_id"] == substrate_id]
    if check_only:
        return bool(mine)
    return len(mine) >= 2 and all(r["verdict"] == "accept" for r in mine)


def job_pilot(driver: Driver, args: argparse.Namespace) -> None:
    from harness.q1 import study_artifact

    out = driver.out
    inputs = out / "inputs"
    with driver.phase("unpack") as record:
        document = study_artifact.load(args.evidence, args.expected_evidence_sha256)
        record.update(study_artifact.unpack(document, inputs))
    corpus = inputs / "corpus"
    kernelgym, kbv = inputs / "kernelgym", inputs / "kbv"
    selection = json.loads((corpus / "pilot_selection.json").read_text())
    substrates = {k.kernel_id: k for k in iter_kernel_dirs(corpus / "pilot-substrates")}
    ordered = [substrates[s] for s in selection["evaluation"] if s in substrates]
    mutants: dict[str, list[Any]] = {s: [] for s in substrates}
    for kernel in iter_kernel_dirs(corpus / "mutants"):
        mutants.setdefault(kernel.mutation["parent_substrate_id"], []).append(kernel)
    controls: dict[str, list[Any]] = {s: [] for s in substrates}
    for folder in ("controls-hacks", "controls-mutants"):
        if (corpus / folder).is_dir():
            for kernel in iter_kernel_dirs(corpus / folder):
                parent = kernel.kernel_id.split(".", 1)[0]
                controls.setdefault(parent, []).append(kernel)
    core = {k.kernel_id: k for k in iter_kernel_dirs(corpus / "controls-core")}
    for substrate in ordered:
        from harness.q1.controls import identity_control_id

        ident = core.get(identity_control_id(substrate.problem_id))
        if ident is not None:
            controls[substrate.kernel_id].insert(0, ident)
    fidelity_options = {
        "b_native": {"kernelgym_src": str(kernelgym)},
        "c1_kbv_native": {"kbv_src": str(kbv)},
    }
    shared = [s for s in ordered if not pilot.exclusive_problem(s.problem_id)]
    phases = set(args.phases)

    if "smoke" in phases:
        _pilot_smoke(driver, args, core, controls)
    if "fidelity" in phases:
        _pilot_fidelity(driver, args, core, mutants, shared, fidelity_options)
    if "calibration" in phases:
        _pilot_calibration(driver, args, corpus)
    # Timing runs before scoring: in job 518 scoring's in-flight items overran the
    # timing reserve and the timing phase got a zero budget.
    if "timing" in phases:
        with driver.phase("timing") as record:
            driver.run_items(
                "timing",
                [_item(k, "timing", 42) for k in shared[: args.timing_kernels]],
                budget_seconds=min(args.timing_minutes * 60, driver.remaining() - 45),
                timing=True,
                record=record,
            )
    if "scoring" in phases:
        _pilot_scoring(driver, args, out, ordered, controls, mutants)


def _pilot_smoke(driver: Driver, args: argparse.Namespace, core: dict, controls: dict) -> None:
    with driver.phase("smoke") as record:
        # Every scoring gate and audit channel (A4 poison allocator and compute-sanitizer
        # included), unmodified KernelBench gate (a) at both revisions and the timing
        # harness on the reference-identity control of a small problem; b1 and b2 on the
        # cached-output hack control of the S1 activation pick (no launch after the
        # first call). b2 retries only an empty event table; the window's 1024-element
        # self-test always records device rows on a working GPU, so the retry branch is
        # reached only by a profiler failure (CPU unit test); b2 rows record
        # profile_attempts so a retry would be visible.
        from harness.q1.controls import identity_control_id

        identity = core[identity_control_id(args.smoke_problem)]
        items = [_item(identity, gate, 42) for gate in pilot.SCORING_GATES]
        items += [
            _item(identity, gate, 42) for gate in ("a_upstream_44130946", "a_upstream_423217d9")
        ]
        cached = [
            k
            for group in controls.values()
            for k in group
            if k.kernel_id.endswith(".hack.cached-output")
        ][:1]
        items += [_item(k, gate, 42) for k in cached for gate in ("b1", "b2")]
        driver.run_items("smoke", items, budget_seconds=args.smoke_minutes * 60, record=record)
        driver.run_items(
            "smoke-timing",
            [_item(identity, "timing", 42)],
            budget_seconds=120,
            timing=True,
            record=record,
        )


def _pilot_fidelity(
    driver: Driver,
    args: argparse.Namespace,
    core: dict,
    mutants: dict,
    shared: list,
    fidelity_options: dict,
) -> None:
    with driver.phase("fidelity") as record:
        adversarial = [
            k
            for k in core.values()
            if k.control and k.control["control_kind"] == "kernelbench-adversarial"
        ]
        first_mutants = [
            pilot.order_mutants([_kmeta(m) for m in mutants[s.kernel_id]])[0]["kernel"]
            for s in shared[: args.fidelity_mutants]
            if mutants[s.kernel_id]
        ]
        kernels = list(shared) + adversarial + first_mutants
        items = [
            _item(k, gate, 42, fidelity_options.get(gate))
            for k in kernels
            for gate in pilot.FIDELITY_GATES
        ]
        # Ours on the same kernels where scoring will not reach them first.
        items += [
            _item(k, gate, 42)
            for k in adversarial + first_mutants
            for gate in ("a", "a_head_1e-4", "b1", "b2")
        ]
        driver.run_items(
            "fidelity", items, budget_seconds=args.fidelity_minutes * 60, record=record
        )


def _pilot_calibration(driver: Driver, args: argparse.Namespace, corpus: Path) -> None:
    out = driver.out
    with driver.phase("calibration") as record:
        calibration = sorted(
            iter_kernel_dirs(corpus / "pilot-calibration"),
            key=lambda k: pilot.native_input_bytes(k.problem_id) or 0,
        )
        driver.run_items(
            "calibration",
            [_item(k, "A1", 42) for k in calibration],
            budget_seconds=args.calibration_minutes * 60,
            record=record,
        )
        from scripts.q1_calibrate_audit import main as calibrate_main

        record["calibrate_exit"] = calibrate_main(
            [
                "--journal",
                str(out / "calibration" / "journal.jsonl"),
                "--corpus",
                str(corpus / "pilot-calibration"),
                "--output",
                str(out / "audit-calibration.json"),
            ]
        )


def _pilot_scoring(
    driver: Driver,
    args: argparse.Namespace,
    out: Path,
    ordered: list,
    controls: dict,
    mutants: dict,
) -> None:
    with driver.phase("scoring") as record:

        def meta(kernel: Any) -> dict[str, Any]:
            return {
                "kernel_id": kernel.kernel_id,
                "kernel_path": str(kernel.kernel_path),
                "problem_id": kernel.problem_id,
            }

        plan = pilot.schedule(
            [meta(s) for s in ordered],
            {s: [meta(k) for k in v] for s, v in controls.items()},
            {
                s: [{**meta(k), "family": k.mutation["family"]} for k in v]
                for s, v in mutants.items()
            },
        )
        items = [
            WorkItem(
                kernel_id=p.kernel_id,
                kernel_path=p.kernel_path,
                problem_id=p.problem_id,
                gate=p.gate,
                seed=p.seed,
                exclusive=pilot.exclusive_problem(p.problem_id),
                timeouts=pilot.watchdog_limits(p.problem_id) if SIZE_SCALED_WATCHDOG else None,
            )
            for p in plan
        ]
        (out / "scoring-plan.json").write_text(
            json.dumps([p.__dict__ for p in plan], indent=0, sort_keys=True)
        )
        # A measurement job may score only a registered prefix of the schedule (the
        # first N items, in pilot.schedule order), optionally without the exclusive
        # items, so it can be paired item by item with an earlier pilot job.
        if args.scoring_prefix is not None:
            items = items[: args.scoring_prefix]
        if args.scoring_shared_only:
            items = [item for item in items if not item.exclusive]
        record["scoring_selection"] = {
            "prefix": args.scoring_prefix,
            "shared_only": args.scoring_shared_only,
            "items": len(items),
        }
        driver.run_items("scoring", items, budget_seconds=driver.remaining() - 30, record=record)


def _kmeta(kernel: Any) -> dict[str, Any]:
    return {"kernel_id": kernel.kernel_id, "family": kernel.mutation["family"], "kernel": kernel}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--job", choices=("smoke", "pilot"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--budget-minutes", type=float, default=10.0)
    parser.add_argument("--slots-per-gpu", type=int, default=4)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--expected-evidence-sha256")
    parser.add_argument("--smoke-minutes", type=float, default=6.0)
    parser.add_argument("--smoke-problem", default="L2/12_Gemm_Multiply_LeakyReLU")
    parser.add_argument("--fidelity-minutes", type=float, default=8.0)
    parser.add_argument("--fidelity-mutants", type=int, default=4)
    parser.add_argument("--calibration-minutes", type=float, default=3.0)
    parser.add_argument(
        "--timing-reserve-minutes",
        type=float,
        default=2.5,
        help="accepted for the job 518 argv; timing now runs before scoring",
    )
    parser.add_argument("--timing-minutes", type=float, default=2.5)
    parser.add_argument("--timing-kernels", type=int, default=3)
    parser.add_argument(
        "--phases",
        nargs="+",
        choices=PILOT_PHASES,
        default=list(PILOT_PHASES),
        help="pilot job phases to run (unpack always runs)",
    )
    parser.add_argument("--scoring-prefix", type=int, default=None)
    parser.add_argument("--scoring-shared-only", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="GPU-less plumbing check: mock codegen, no admission, items planned not run",
    )
    parser.add_argument(
        "--size-scaled-watchdog",
        action="store_true",
        help="per-item watchdog limits that grow with native input bytes (pilot.watchdog_limits)",
    )
    args = parser.parse_args(argv)
    global SIZE_SCALED_WATCHDOG
    SIZE_SCALED_WATCHDOG = args.size_scaled_watchdog
    if sorted(args.seeds) != [42, 43, 44]:
        parser.error("the pilot declares replicates 42, 43 and 44")
    import torch

    if not torch.cuda.is_available() and not args.dry_run:
        print("FAIL: the Q1 GPU pilot needs one visible GPU", file=sys.stderr)
        return 2
    if torch.cuda.is_available() and args.dry_run:
        print("FAIL: --dry-run is for GPU-less containers only", file=sys.stderr)
        return 2
    args.output.mkdir(parents=True, exist_ok=True)
    driver = Driver(
        args.output,
        job=args.job,
        budget_minutes=args.budget_minutes,
        slots=["cuda:0"] * args.slots_per_gpu,
        dry_run=args.dry_run,
    )

    class _Proxy:  # signals reach whichever runner is active
        def stop(self, trigger: str) -> None:
            driver.interrupted = True
            driver.trigger = driver.trigger or trigger
            driver.end = min(driver.end, time.monotonic())  # no further phase starts
            if driver.current is not None:
                driver.current.stop(trigger)

    driver.signal_target = _Proxy()
    install_signal_handlers(driver.signal_target)
    gpu = torch.cuda.is_available()
    env = {
        "torch": torch.__version__,
        "dry_run": args.dry_run,
        "device": torch.cuda.get_device_name(0) if gpu else None,
        "capability": list(torch.cuda.get_device_capability(0)) if gpu else None,
        "poison_alloc_so": os.environ.get("Q1_POISON_ALLOC_SO_PATH"),
        "compute_sanitizer": shutil.which("compute-sanitizer")
        or (
            "/usr/local/cuda/bin/compute-sanitizer"
            if Path("/usr/local/cuda/bin/compute-sanitizer").exists()
            else None
        ),
    }
    (args.output / "environment.json").write_text(json.dumps(env, indent=1, sort_keys=True))
    if args.job == "smoke":
        job_smoke(driver, args)
    else:
        if args.evidence is None or not args.expected_evidence_sha256:
            parser.error("--job pilot needs --evidence and --expected-evidence-sha256")
        job_pilot(driver, args)
    driver.write_phases()
    if driver.interrupted:
        marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
        if marker:
            tmp = Path(marker).with_name(".checkpoint.ready.tmp")
            tmp.write_text(f"trigger={driver.trigger or 'SIGUSR1'}\nnote=q1-pilot journals final\n")
            os.replace(tmp, marker)
        return 75
    return 1 if driver.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
