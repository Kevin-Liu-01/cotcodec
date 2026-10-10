"""D59 (i)'s claim, checked on the data at hand: the wrapper's ``report.json`` against the
registered CLI. An operator script, not code of record.

Usage (host, after ``run_report.py`` has finished; one more registered report, about 20 s)::

    python3 -E -s -B check_identity.py --export X --records A/a1.jsonl --plan PLAN \
        --costs A/costs.json --wrapper-report A/report/report.json \
        --guard A/report/guard.json --out-dir A/identity

``identity.json`` carries the labels of ``guard.json`` (D61: every output of an incomplete
case is labelled). The check refuses, writing nothing, until ``run_report.py`` has written a
complete ``guard.json``, so it cannot run early against a report still being written.

* The registered CLI (``python3 -E -s -B -m harness.q2_stage1.analysis``, run in the export) on
  the same inputs. If it writes a report, the wrapper's must be byte-identical (``identical``).
* If it fails on a fractional base score (bug B1, "outcomes must be 0, 1 or NaN"), it is run
  again on the same records "scored 0": every fractional live score set to 0.0, and the
  offline replay score set so that each live-versus-offline mismatch flag is unchanged
  (``offline_raw_score`` 0.0 where it equalled the live score, else kept, or the old live
  score where it was 0.0). The two reports must then differ only in ``fractional_score`` and
  the ``fractional_scores`` counts.
* If both fail (bug B2: no size holds two sessions, or a DR5 share has no finite bound), the
  errors are recorded. The guarded report is then the delta-only report, or the report
  recomputed with that ``rules.dr5`` call tolerated (``run_report.py``, D62).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1a_ops as O  # noqa: E402

FRACTIONAL_ERROR = "outcomes must be 0, 1 or NaN"
ALLOWED_LEAVES = ("fractional_score", "fractional_scores")

Runner = Callable[[Path, Path, Path | None, Path], tuple[int, str]]


def _fractional(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0 < float(x) < 1


def scored_zero(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The records with every fractional live score set to 0.0, keeping each record's
    live-versus-offline mismatch flag (``analysis.checker_noise``) unchanged."""
    out = []
    for record in records:
        rec = dict(record)
        if rec.get("status") == "scored" and _fractional(rec.get("score")):
            live = float(rec["score"])
            rec["score"] = 0.0
            for key in ("offline_raw_score", "offline_score"):
                off = rec.get(key)
                if off is None:
                    continue
                if float(off) == live:
                    rec[key] = 0.0
                elif float(off) == 0.0:
                    rec[key] = live
        out.append(rec)
    return out


def differing_paths(a: Any, b: Any, prefix: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for key in sorted(set(a) | set(b), key=str):
            path = f"{prefix}/{key}"
            if key not in a or key not in b:
                out.append(path)
            else:
                out += differing_paths(a[key], b[key], path)
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out += differing_paths(x, y, f"{prefix}/{i}")
        return out
    return [] if a == b else [prefix or "/"]


def subprocess_runner(export: Path) -> Runner:
    def run(records: Path, plan: Path, costs: Path | None, out: Path) -> tuple[int, str]:
        argv = [sys.executable, "-E", "-s", "-B", "-m", "harness.q2_stage1.analysis",
                "--records", str(records), "--plan", str(plan)]  # fmt: skip
        if costs:
            argv += ["--costs", str(costs)]
        argv += ["--out", str(out)]
        done = subprocess.run(argv, cwd=export, capture_output=True, text=True, check=False)
        return done.returncode, done.stderr[-2000:]

    return run


def check(
    records: Path,
    plan: Path,
    costs: Path | None,
    wrapper_report: Path,
    out_dir: Path,
    runner: Runner,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    registered = out_dir / "report-registered.json"
    code, stderr = runner(records, plan, costs, registered)
    result: dict[str, Any] = {
        "wrapper_report": str(wrapper_report),
        "wrapper_report_sha256": O.sha256_file(wrapper_report)
        if wrapper_report.is_file()
        else None,
        "registered": {"exit": code, "stderr_tail": stderr[-600:] if code else ""},
    }
    if code == 0:
        result["registered"]["sha256"] = O.sha256_file(registered)
        result["mode"] = "byte identity"
        result["identical"] = (
            wrapper_report.is_file() and wrapper_report.read_bytes() == registered.read_bytes()
        )
        result["pass"] = result["identical"]
        return result
    if FRACTIONAL_ERROR in stderr:
        zeroed = out_dir / "records-scored-zero.jsonl"
        rows = scored_zero(O.read_jsonl(records))
        O.write_new(zeroed, "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        registered_zero = out_dir / "report-registered-scored-zero.json"
        code0, stderr0 = runner(zeroed, plan, costs, registered_zero)
        result["mode"] = "fractional: only fractional_score and fractional_scores may differ"
        result["registered_scored_zero"] = {
            "exit": code0,
            "stderr_tail": stderr0[-600:] if code0 else "",
        }
        if code0 != 0 or not wrapper_report.is_file():
            result["pass"] = False
            return result
        result["registered_scored_zero"]["sha256"] = O.sha256_file(registered_zero)
        paths = differing_paths(O.read_json(wrapper_report), O.read_json(registered_zero))
        result["differing_paths"] = paths
        result["pass"] = bool(paths) and all(p.rsplit("/", 1)[-1] in ALLOWED_LEAVES for p in paths)
        return result
    result["mode"] = "registered report failed (not on a fractional score)"
    result["wrapper_report_written"] = wrapper_report.is_file()
    result["pass"] = not wrapper_report.is_file()
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--costs", type=Path)
    parser.add_argument("--wrapper-report", type=Path, required=True)
    parser.add_argument(
        "--guard", type=Path, required=True,
        help="run_report.py's guard.json: the labels identity.json carries",
    )  # fmt: skip
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    export = O.use_export(args.export)
    if (args.out_dir / "identity.json").exists():
        raise O.OpsError(f"{args.out_dir}/identity.json exists")
    labels = O.labels_from_guard(args.guard)  # refuses before run_report.py has finished
    result = check(
        args.records.resolve(), args.plan.resolve(), args.costs.resolve() if args.costs else None,
        args.wrapper_report.resolve(), args.out_dir.resolve(), subprocess_runner(export),
    )  # fmt: skip
    result = {"labels": labels, **result, "inputs": {"guard": O.sha256_file(args.guard)}}
    O.write_new(args.out_dir / "identity.json", O.dumps(result))
    print(json.dumps({k: result.get(k) for k in ("mode", "pass", "identical", "differing_paths")}))
    return 0 if result["pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
