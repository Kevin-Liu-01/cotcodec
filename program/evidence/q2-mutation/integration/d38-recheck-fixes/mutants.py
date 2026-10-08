"""Targeted mutants of the narrow re-check's fixes, each run against its tests.

Usage (from the repository root, on a clean commit):

    uv run python program/evidence/q2-mutation/integration/d38-recheck-fixes/mutants.py \
        <commit> <scratch dir> <out.json>

Each mutant is a one-line (or one-block) replacement applied to a
``git archive`` copy of ``<commit>`` in its own directory under
``<scratch dir>``; the targeted tests of
``tests/test_q2_mutation_rater_runner.py`` then run there. A mutant is
killed when at least one targeted test fails. The baseline (no mutation)
must pass. Nothing in the repository is changed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RUNNER = "harness/q2_mutation/rater_runner.py"
AUDIT = "harness/q2_mutation/audit.py"
TESTS = "tests/test_q2_mutation_rater_runner.py"

MUTANTS = [
    {
        "id": "M7",
        "what": "re-rate filter: relay mismatch among the void reasons, not the only one",
        "file": RUNNER,
        "old": "if reasons == [RELAY_MISMATCH]:",
        "new": "if isinstance(reasons, list) and RELAY_MISMATCH in reasons:",
        "tests": "rerate or relay",
    },
    {
        "id": "M14",
        "what": "read_journal accepts an agent started twice",
        "file": RUNNER,
        "old": (
            "            if agent in started:\n"
            '                raise SystemExit(f"{path}:{number}: agent {agent} started twice")\n'
        ),
        "new": "            pass\n",
        "tests": "journal or collector",
    },
    {
        "id": "R1",
        "what": "audit summarize takes the list's items without recomputing them",
        "file": AUDIT,
        "old": '        wanted = check_rerate_list(listing, own[listing["calls_sha256"]])',
        "new": '        wanted = [str(i) for i in listing["items"]]',
        "tests": "rerate or relay",
    },
    {
        "id": "R2",
        "what": "export-isolated takes the list's items without recomputing them",
        "file": RUNNER,
        "old": '        wanted = check_rerate_list(rerate, args.rerate_list.parent / "calls.jsonl")',
        "new": '        wanted = [str(i) for i in rerate["items"]]',
        "tests": "rerate or relay",
    },
    {
        "id": "R3",
        "what": "the recompute check accepts a list that is a subset of the recomputed items",
        "file": RUNNER,
        "old": "    if listed != expected:",
        "new": "    if set(listed or []) - set(expected):",
        "tests": "rerate or relay",
    },
    {
        "id": "R4",
        "what": "the recompute check skips the calls file's digest",
        "file": RUNNER,
        "old": (
            '    if not calls_path.is_file() or listing.get("calls_sha256") != '
            "sha256_file(calls_path):"
        ),
        "new": "    if not calls_path.is_file():",
        "tests": "rerate or relay",
    },
    {
        "id": "C1",
        "what": "the collector copies straight into the output directory (no staging)",
        "file": RUNNER,
        "old": '            target = staging / row["file"]',
        "new": (
            "            out_dir.mkdir(parents=True, exist_ok=True)\n"
            '            target = out_dir / row["file"]'
        ),
        "tests": "refused_collection or collector",
    },
    {
        "id": "C2",
        "what": "a refused collection keeps its staging directory",
        "file": RUNNER,
        "old": "        shutil.rmtree(staging, ignore_errors=True)\n",
        "new": "        pass\n",
        "tests": "refused_collection",
    },
    {
        "id": "C3",
        "what": "a refused collection keeps the directories it made for the output",
        "file": RUNNER,
        "old": (
            "        for parent in created:  # the directories made above, deepest first\n"
            "            with contextlib.suppress(OSError):\n"
            "                parent.rmdir()\n"
        ),
        "new": "        pass\n",
        "tests": "refused_collection",
    },
]


def run(commit: str, scratch: Path, mutant: dict | None) -> dict:
    name = mutant["id"] if mutant else "baseline"
    tree = scratch / name
    tree.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", commit], check=True, capture_output=True)
    subprocess.run(["tar", "-x", "-C", str(tree)], input=archive.stdout, check=True)
    tests = mutant["tests"] if mutant else "rerate or relay or journal or collector or collection"
    if mutant:
        path = tree / mutant["file"]
        text = path.read_text(encoding="utf-8")
        if text.count(mutant["old"]) != 1:
            raise SystemExit(f"{name}: the mutated text is not found exactly once")
        path.write_text(text.replace(mutant["old"], mutant["new"]), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", TESTS, "-k", tests],
        cwd=tree,
        capture_output=True,
        text=True,
    )
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    row = {"id": name, "tests": tests, "pytest_exit": proc.returncode, "summary": tail}
    if mutant:
        row |= {"what": mutant["what"], "file": mutant["file"], "killed": proc.returncode == 1}
    return row


def main() -> int:
    commit, scratch, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    scratch.mkdir(parents=True, exist_ok=False)
    head = subprocess.run(
        ["git", "rev-parse", commit], check=True, capture_output=True, text=True
    ).stdout.strip()
    baseline = run(head, scratch, None)
    if baseline["pytest_exit"] != 0:
        raise SystemExit(f"the baseline fails: {baseline}")
    rows = [run(head, scratch, m) for m in MUTANTS]
    out.write_text(
        json.dumps(
            {
                "commit": head,
                "baseline": baseline,
                "mutants": rows,
                "killed": sum(r["killed"] for r in rows),
                "total": len(rows),
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"killed": sum(r["killed"] for r in rows), "total": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
