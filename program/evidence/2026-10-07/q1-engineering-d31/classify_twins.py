"""Decision D31 evidence: classify every inline/store twin row pair of re-pilot job 713
that is not byte-identical. Recorded analysis script (pure Python).

    python classify_twins.py RUN_DIR OUT.json

Classes, checked in order:

- ``non-consumer-gate``: the row belongs to a gate that reads no reference (b1, b2, A4
  and its probes), so both arms ran identical code; a difference is the inline path's
  own run-to-run variation (for example compute-sanitizer error counts or a probe that
  fails under memory pressure);
- ``inline-reference-nondeterministic``: the problem's inline items computed different
  reference errors (``e_r32_device``) for the same draw, so the inline path does not
  reproduce its own references (the store computes them once);
- ``static-checker-set-order``: only gate ``a_static``'s warning list differs, and as a
  set it is equal (KernelBench's static checker returns a set, whose order follows
  Python's per-process string hashing);
- ``a4-rejected-kernel``: A4 finds the kernel faulty in both arms by its own checks
  (determinism or dual poison fails, the poison allocator changes its output, or it
  raises inside A4, for example an illegal address), so its output depends on bytes it
  never wrote or reads outside its inputs, and its rows depend on allocator history;
  every audit tier rejects it either way;
- ``memory-contention``: either twin item met a CUDA out-of-memory error or a cuDNN
  "unable to find an engine" failure (in any attempt), a watchdog timeout or a retry, or
  the problem's reference item for that channel recorded a resource failure (so the
  store twin computed inline under the same pressure);
- ``unexplained``: anything else.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from harness.q1 import repilot  # noqa: E402
from harness.q1.journal import Journal  # noqa: E402

#: Gates that read no reference: both arms run the same code.
NON_CONSUMER = {"b1", "b2", "A4", "A4_poison", "A4_sanitizer"}
#: Text of a failure caused by other items' memory use (not by the candidate: an illegal
#: memory access, for example, is the candidate's own fault).
CONTENTION = (
    "out of memory",
    "outofmemoryerror",
    "unable to find an engine",
    "cudaerrormemoryallocation",
)


def main() -> int:
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    journal = Journal(run / "q1" / "repilot" / "journal.jsonl")
    rows = journal.final_rows()
    every, _ = journal.read()
    items = [json.loads(line) for line in (run / "q1" / "repilot" / "items.jsonl").open()]
    problem = {i["kernel_id"]: i["problem_id"] for i in items}
    # inline reference nondeterminism per problem
    seen: dict = collections.defaultdict(set)
    for r in rows:
        if r["gate"] in {"A1", "A2", "A3"} and r["config_id"] != "aggregate":
            base, arm = repilot.arm_of(r["kernel_id"])
            if arm == "inline" and r["details"].get("e_r32_device") is not None:
                seen[(problem[r["kernel_id"]], r["config_id"])].add(r["details"]["e_r32_device"])
    nondeterministic = {p for (p, _), v in seen.items() if len(v) > 1}
    # dual poison failures per base kernel and arm
    poisoned: dict = collections.defaultdict(set)
    for r in rows:
        if r["gate"] == "A4" and r["config_id"] == "in-process":
            base, arm = repilot.arm_of(r["kernel_id"])
            subs = r["details"].get("subchecks", {})
            if any(not s.get("dual_poison_factory", {}).get("passed", True) for s in subs.values()):
                poisoned[base].add(arm)
    # A4 verdicts per base kernel and arm (the in-process row, the probes and the
    # runner's item-level rows)
    a4_rejects: dict = collections.defaultdict(set)
    for r in rows:
        if r["gate"] != "A4" or r["verdict"] != "reject":
            continue
        base, arm = repilot.arm_of(r["kernel_id"])
        details = r["details"]
        text = json.dumps(details).lower()
        if any(m in text for m in CONTENTION):
            continue
        own = set(details.get("failed") or []) & {
            "determinism",
            "dual_poison_factory",
        } or details.get("reason") in {"output-depends-on-poison", "candidate-raised"}
        if own:
            a4_rejects[base].add(arm)
    # reference items that met a resource failure, per (problem, channel gate)
    starved: set = set()
    references = run / "q1" / "repilot" / "references.jsonl"
    for line in references.open():
        ref = json.loads(line)
        text = json.dumps(ref["details"]).lower()
        if "resource failure" in text or "outofmemory" in text or "out of memory" in text:
            problem_id = ref["kernel_id"].removeprefix("reference.").replace("-", "/", 1)
            starved.add((problem_id, ref["gate"]))
    channel_of = {
        "a": "ref_a",
        "a_1e-3": "ref_a",
        "a_static": "ref_a",
        "a_head_1e-4": "ref_a_head",
        "a_head_1e-2": "ref_a_head",
        "c1": "ref_c",
        "c2": "ref_c",
        "c3": "ref_c",
        "c_1e-2": "ref_c",
        "c_kbv_raw": "ref_c",
        "A1": "ref_A1",
        "A2": "ref_A2",
        "A3": "ref_A3",
        "A5": "ref_A5",
    }
    # contention: any attempt of the item (or of the kernel's A4 probes) shows it
    troubled: set = set()
    for r in every:
        text = json.dumps(r["details"]).lower()
        attempt = int(r.get("attempt", 1))
        if attempt > 1 or r["verdict"] == "timeout" or any(m in text for m in CONTENTION):
            base, _ = repilot.arm_of(r["kernel_id"])
            troubled.add((base, r["gate"]))
    by_key: dict = collections.defaultdict(lambda: {"inline": [], "store": []})
    for r in rows:
        base, arm = repilot.arm_of(r["kernel_id"])
        key = (base, r["gate"], r["config_id"], r["tf32_policy"], int(r.get("seed", 42)))
        by_key[key][arm].append(r)
    twins = repilot.compare_twins(rows)
    classes = collections.Counter()
    verdict_classes = collections.Counter()
    listed = []
    for d in twins["differing"]:
        base, gate = d["key"][0], d["key"][1]
        p = problem.get(base)
        warnings_only = d["fields"] == [".details.static_warnings"]
        if warnings_only:
            twins_rows = by_key[tuple(d["key"])]
            pair = [
                {json.dumps(sorted(r["details"]["static_warnings"])) for r in twins_rows[arm]}
                for arm in ("inline", "store")
            ]
        if gate in NON_CONSUMER:
            cls = "non-consumer-gate"
        elif p in nondeterministic:
            cls = "inline-reference-nondeterministic"
        elif warnings_only and pair[0] == pair[1]:
            cls = "static-checker-set-order"
        elif poisoned.get(base) == {"inline", "store"} or a4_rejects.get(base) == {
            "inline",
            "store",
        }:
            cls = "a4-rejected-kernel"
        elif (
            (base, gate) in troubled
            or (gate.startswith("A4") and (base, "A4") in troubled)
            or (p, channel_of.get(gate)) in starved
        ):
            cls = "memory-contention"
        else:
            cls = "unexplained"
        classes[cls] += 1
        if not d["verdicts_equal"]:
            verdict_classes[cls] += 1
        listed.append({**d, "class": cls})
    report = {
        "rows_compared": twins["rows_compared"],
        "rows_identical": twins["rows_identical"],
        "verdicts_identical": twins["verdicts_identical"],
        "rows_in_one_arm_only": twins["only_one_arm"],
        "differing_rows_by_class": dict(classes),
        "verdict_differences_by_class": dict(verdict_classes),
        "inline_nondeterministic_problems": sorted(nondeterministic),
        "a4_rejected_kernels": sorted(
            k
            for k in set(poisoned) | set(a4_rejects)
            if {"inline", "store"} in (poisoned.get(k), a4_rejects.get(k))
        ),
        "differing": listed,
    }
    out.write_text(json.dumps(report, indent=1, sort_keys=True))
    print(json.dumps({k: v for k, v in report.items() if k != "differing"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
