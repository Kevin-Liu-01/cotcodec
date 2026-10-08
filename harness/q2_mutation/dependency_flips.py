"""S1 dependency flips: candidates from the repeat-2 scorings, confirmed at repeat 5.

A candidate is a job whose verdict differs between the lock-exact and the
scoping venv while each venv's two fresh-process scorings agree. Two
agreeing scorings do not rule out a nondeterministic checker (on the dev
split, ``check_python_file_by_test_suite`` of 9219480b passes about 3 runs in
10 in both venvs and showed a spurious flip in ``dev-controls-v8``), so every
candidate is rescored five times in fresh processes in each venv
(``score.sh <jobs> <prefix>-s1 <workers> 5``). A candidate is a confirmed
dependency flip only if all five scorings agree within each venv and the two
venvs' verdicts differ; otherwise it is reported as unstable (S5), never as a
flip.

Runs inside the metric image after the scoring step of a mutation run (job 3)
and after each scoring step of a control run (jobs 1 and 3):

    python -m harness.q2_mutation.dependency_flips --jobs <jobs.jsonl> \
        --prefix /out/mut --workers 16

writes ``<prefix>-s1-jobs.jsonl`` (the candidates' jobs), the rescoring's
``<prefix>-s1-verdicts-*.jsonl`` and ``-notes-*.jsonl``, and ``<prefix>-s1.json``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

ARMS = ("lock", "scout")
CONFIRM_REPEAT = 5
SCORE_SH = "/src/infra/q2-mutation/run/score.sh"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _by_id(path: Path) -> dict[str, dict[str, Any]]:
    return {row["mutant_id"]: row for row in _jsonl(path)}


def candidates(prefix: str) -> list[str]:
    """Jobs whose verdicts differ between the venvs while each venv's repeats agree."""
    verdicts = {arm: _by_id(Path(f"{prefix}-verdicts-{arm}.jsonl")) for arm in ARMS}
    notes = {arm: _by_id(Path(f"{prefix}-notes-{arm}.jsonl")) for arm in ARMS}
    out = []
    for mutant_id in sorted(set(verdicts["lock"]) & set(verdicts["scout"])):
        if verdicts["lock"][mutant_id]["verdict"] == verdicts["scout"][mutant_id]["verdict"]:
            continue
        if any(notes[arm].get(mutant_id, {}).get("nondeterministic") for arm in ARMS):
            continue
        out.append(mutant_id)
    return out


def stable_verdict(note: Mapping[str, Any]) -> str | None:
    """The verdict all repeated scorings give, or None if they disagree or failed."""
    scores = list(note.get("repeat_scores") or [])
    errors = list(note.get("repeat_errors") or [])
    if len(scores) < CONFIRM_REPEAT or note.get("infra_failed"):
        return None
    if any(e is not None for e in errors) or len(set(scores)) != 1:
        return None
    return "pass" if scores[0] == 1.0 else "fail"


def confirm(prefix: str, ids: list[str]) -> dict[str, Any]:
    notes = {arm: _by_id(Path(f"{prefix}-s1-notes-{arm}.jsonl")) for arm in ARMS}
    confirmed, unstable = [], []
    for mutant_id in ids:
        verdict = {arm: stable_verdict(notes[arm].get(mutant_id, {})) for arm in ARMS}
        if None not in verdict.values() and verdict["lock"] != verdict["scout"]:
            confirmed.append({"mutant_id": mutant_id, **verdict})
        else:
            unstable.append({"mutant_id": mutant_id, **verdict})
    return {
        "rule": f"verdicts differ between venvs and {CONFIRM_REPEAT} fresh-process scorings "
        "agree within each venv",
        "candidates": ids,
        "confirmed": confirmed,
        "unstable": unstable,
    }


def run(
    jobs: Path,
    prefix: str,
    workers: int,
    *,
    score: Callable[[Path, str, int], None] | None = None,
) -> dict[str, Any]:
    ids = candidates(prefix)
    wanted = set(ids)
    selected = [job for job in _jsonl(jobs) if job["mutant_id"] in wanted]
    s1_jobs = Path(f"{prefix}-s1-jobs.jsonl")
    s1_jobs.write_text(
        "".join(json.dumps(job, sort_keys=True) + "\n" for job in selected), encoding="utf-8"
    )
    if selected:
        (score or _score)(s1_jobs, f"{prefix}-s1", workers)
    result = confirm(prefix, ids)
    Path(f"{prefix}-s1.json").write_text(
        json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _score(jobs: Path, prefix: str, workers: int) -> None:
    subprocess.run(
        ["sh", SCORE_SH, str(jobs), prefix, str(workers), str(CONFIRM_REPEAT)], check=True
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args(argv)
    result = run(args.jobs, args.prefix, args.workers)
    print(json.dumps({k: len(v) for k, v in result.items() if isinstance(v, list)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
