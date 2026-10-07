#!/usr/bin/env python3
"""Command-line entry for the Q2 mutation operators (catalog, plan, apply, verify).

Office files are applied by ``harness/q2_mutation/operators/uno_apply.py``
inside the LO-VM image; this script prepares its manifest and verifies its
output. Text and config files are applied here.

    uv run python scripts/q2_mutation_operators.py catalog --out catalog.json
    uv run python scripts/q2_mutation_operators.py plan --spec specs/<task>.yaml \
        --base saved/base/<file> --initial saved/initial/<file> --out plans.jsonl
    uv run python scripts/q2_mutation_operators.py manifest --plans plans.jsonl \
        --input-rel saved/base/<file> --out apply.jsonl --null-rel saved/null/<file>
    uv run python scripts/q2_mutation_operators.py apply-text --plans plans.jsonl \
        --base <file> --out-dir mutants --log apply-log.jsonl
    uv run python scripts/q2_mutation_operators.py verify --plans plans.jsonl \
        --reference saved/null/<file> --mutants-dir mutants --apply-log apply-log.jsonl \
        --out results.jsonl

``plan`` must run before any checker verdict exists for the mutants it plans,
and the confirmatory campaign waits for the preregistration freeze.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.q2_mutation.operators import catalog  # noqa: E402
from harness.q2_mutation.operators._spec import load_spec  # noqa: E402
from harness.q2_mutation.operators.pipeline import (  # noqa: E402
    apply_manifest,
    apply_text_records,
    is_admitted,
    make_context,
    plan_task,
    read_jsonl,
    resave_row,
    verify,
)


class OutputExists(SystemExit):
    pass


def write_jsonl(path: str | Path, rows: list[dict]) -> None:
    """Refuse to overwrite; write a temporary file and atomically replace."""
    target = Path(path)
    if target.exists():
        raise OutputExists(f"refusing to overwrite {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(tmp, target)


def cmd_catalog(args: argparse.Namespace) -> int:
    data = catalog()
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.out:
        if Path(args.out).exists():
            raise OutputExists(f"refusing to overwrite {args.out}")
        Path(args.out).write_text(text, encoding="utf-8")
    print(f"{data['total']} operators, catalog_sha256 {data['catalog_sha256']}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    ctx = make_context(spec.task_id, spec, args.base, args.initial, args.family,
                       args.target_path_in_vm)
    records, skipped = plan_task(ctx, operators=args.operator or None)
    write_jsonl(args.out, records)
    if args.skips:
        write_jsonl(args.skips, skipped)
    labels = Counter(r["label"] for r in records)
    print(f"{len(records)} mutants for {spec.task_id} ({ctx.family}): {dict(labels)}")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    records = read_jsonl(args.plans)
    rows = apply_manifest(records, args.input_rel, args.output_dir_rel)
    if args.null_rel and records:
        rows.insert(0, resave_row(f"{records[0]['task_id']}__null", records[0]["family"],
                                  args.input_rel, args.null_rel))
    write_jsonl(args.out, rows)
    print(f"{len(rows)} rows")
    return 0


def cmd_apply_text(args: argparse.Namespace) -> int:
    log = apply_text_records(read_jsonl(args.plans), args.base, args.out_dir)
    write_jsonl(args.log, log)
    print(dict(Counter(entry["status"] for entry in log)))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    logs = {row["mutant_id"]: row for row in read_jsonl(args.apply_log)}
    results = []
    for record in read_jsonl(args.plans):
        name = Path(args.reference).name
        mutant = Path(args.mutants_dir) / record["mutant_id"] / name
        results.append(
            verify(record, args.reference, mutant if mutant.exists() else None,
                   logs.get(record["mutant_id"]))
        )
    write_jsonl(args.out, results)
    summary: dict[str, Counter] = defaultdict(Counter)
    for record in results:
        summary[record["operator"]]["planned"] += 1
        summary[record["operator"]]["admitted"] += int(is_admitted(record))
    for op, counts in sorted(summary.items()):
        print(f"{op:45s} {dict(counts)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("catalog")
    p.add_argument("--out")
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser("plan")
    p.add_argument("--spec", required=True)
    p.add_argument("--base", required=True, help="the LibreOffice-saved gold file")
    p.add_argument("--initial", help="the LibreOffice-saved initial file")
    p.add_argument("--family", choices=["xlsx", "docx", "pptx", "text", "config"])
    p.add_argument("--target-path-in-vm")
    p.add_argument("--operator", action="append", help="limit to these operators")
    p.add_argument("--out", required=True)
    p.add_argument("--skips")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("manifest")
    p.add_argument("--plans", required=True)
    p.add_argument("--input-rel", required=True)
    p.add_argument("--output-dir-rel", default="mutants")
    p.add_argument("--null-rel", help="also save the base once more here (null mutant)")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_manifest)

    p = sub.add_parser("apply-text")
    p.add_argument("--plans", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--log", required=True)
    p.set_defaults(func=cmd_apply_text)

    p = sub.add_parser("verify")
    p.add_argument("--plans", required=True)
    p.add_argument("--reference", required=True, help="the null mutant (or the text base)")
    p.add_argument("--mutants-dir", required=True)
    p.add_argument("--apply-log", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
