"""G3b post hoc for the independent check's wording fixes (EXPLORATORY; CPU, text-free, from the
committed files only). Uses the analysis's own functions and bootstrap (10,000 draws, seed 42).
- seeds 42-43 pooled at 81,920 (no time-cut rollout at those seeds);
- the G3b-minus-G3 change in the bf16 gap at 32,768 with the 6 unknown pairs counted as
  unsolved or solved;
- the seed-order contrast on the questions G3b's contrast uses (G3 on the same questions, and the
  paired difference), and G3b's contrast with the 6 unknown pairs counted as unsolved or solved;
- tokens per solved problem at 32,768 on the 147 known pairs, and the partial tokens of the 6
  unknown rollouts;
- the rollouts that reached 81,920 and still count as correct in the by-cap row at 81,920.
Usage (repository root): uv run --locked python <this file> > <evidence>/analysis/posthoc-check.json
"""

import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
E = ROOT / "program/evidence/2026-10-16/g3b-long-budget"
G3 = ROOT / "program/evidence/2026-10-16/g3-state-precision-accuracy/data/per-request.jsonl.gz"
spec = importlib.util.spec_from_file_location("a", ROOT / "scripts/analyze_g3b_long_budget.py")
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
REPS, SEED, CAP = 10000, 42, 32768


def ci(b: dict, j: int = 0) -> list[float]:
    return [100 * b["ci95"][0][j], 100 * b["ci95"][1][j]]


def main() -> None:
    from harness import g3b_long_budget as g3b

    rows = [r for r in a.a3.read_jsonl_gz(E / "data/per-request.jsonl.gz") if r["phase"] == "main"]
    for r in rows:
        c = r[f"c{CAP}_correct"]
        r["c_lower"] = 0 if c is None else c
        r["c_upper"] = 1 if c is None else c
    arms = ["fp32", "bf16"]
    out: dict = {}
    # 1. Seeds 42-43 at 81,920.
    s4243 = [r for r in rows if r["seed"] in (42, 43)]
    p = a.paired(s4243, "correct", arms, REPS, SEED)
    out["seeds_42_43_at_81920"] = {
        "pairs": p["pairs"],
        "pairs_dropped": p["pairs_dropped"],
        "time_cut": sum(1 for r in s4243 if r["finish_reason"] == g3b.TIME_CUT),
        "fp32": 100 * p["fp32"]["mean"],
        "bf16": 100 * p["bf16"]["mean"],
        "diff": 100 * p["bf16_minus_fp32"]["diff"],
        "ci95": [100 * x for x in p["bf16_minus_fp32"]["ci95"]],
    }
    # 2. Change in the bf16 gap against G3 at 32,768, with the unknown pairs bounded.
    old = a.g3_rows_on(g3b.read_g3_rows(G3), sorted({r["question_index"] for r in rows}))
    out["gap_change_at_32768"] = {
        k: a.gap_change(rows, key, old, "correct", "bf16", REPS, SEED)["gap_new_minus_gap_old"]
        for k, key in (("known", f"c{CAP}_correct"), ("unknown_unsolved", "c_lower"),
                       ("unknown_solved", "c_upper"))
    }  # fmt: skip
    for v in out["gap_change_at_32768"].values():
        v["diff"] *= 100
        v["ci95"] = [100 * x for x in v["ci95"]]
    # 3. Seed-order contrasts on the same questions.
    seeds = [42, 43, 44]
    known = a.complete_pairs(rows, f"c{CAP}_correct", arms)

    def per_q(rs: list, key: str) -> dict:
        ref = a.a3.per_question_seed_matrix(rs, key, "fp32", seeds)
        arm = a.a3.per_question_seed_matrix(rs, key, "bf16", seeds)
        qs = sorted(set(ref) & set(arm))
        d = np.array([arm[q] for q in qs]) - np.array([ref[q] for q in qs])
        return dict(zip(qs, d[:, 0] - d[:, 1:].mean(axis=1), strict=True))

    new = per_q(known, f"c{CAP}_correct")
    oldc = per_q(old, "correct")
    qs = sorted(set(new) & set(oldc))
    b = a.a3.bootstrap(np.column_stack([[oldc[q] for q in qs], [new[q] - oldc[q] for q in qs]]),
                       REPS, SEED)  # fmt: skip
    out["seed_contrast_same_questions"] = {
        "n_questions": len(qs),
        "g3": {"contrast": 100 * b["point"][0], "ci95": ci(b, 0)},
        "g3b_minus_g3": {"diff": 100 * b["point"][1], "ci95": ci(b, 1)},
        "g3b_unknown_unsolved": 100 * float(np.mean(list(per_q(rows, "c_lower").values()))),
        "g3b_unknown_solved": 100 * float(np.mean(list(per_q(rows, "c_upper").values()))),
    }
    # 4. Tokens per solved problem at 32,768.
    tok = {}
    for arm in arms:
        k = [r for r in known if r["arm"] == arm]
        unk = [r for r in rows if r["arm"] == arm and r[f"c{CAP}_correct"] is None]
        solved = sum(r[f"c{CAP}_correct"] for r in k)
        tok[arm] = {
            "known_pairs_tokens_within_cap": int(sum(min(r["completion_len"], CAP) for r in k)),
            "known_pairs_solved": int(solved),
            "tokens_per_solved_known_pairs": sum(min(r["completion_len"], CAP) for r in k) / solved,
            "unknown_rollouts": len(unk),
            "unknown_partial_tokens": int(sum(r["completion_len"] for r in unk)),
        }
    out["tokens_per_solved_at_32768"] = tok
    # 5. Rollouts at 81,920 that count as correct in the by-cap row at 81,920.
    out["reached_81920_and_correct"] = [
        {"arm": r["arm"], "request_id": r["request_id"], "thinking_closed": r["thinking_closed"]}
        for r in rows
        if r["finish_reason"] == "length" and r["correct"]
    ]
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
