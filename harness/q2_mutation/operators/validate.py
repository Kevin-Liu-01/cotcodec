"""Operator validation doctor on synthetic documents (harness validation only).

Runs every operator end to end on the small documents in ``_synth`` (written
from scratch, no OSWorld content) inside the LibreOffice container:

1. LibreOffice-save the synthetic gold and initial files (``uno_apply`` rows
   with no steps), and save the saved gold once more to check that the base
   is a fixed point of load-and-save at snapshot level;
2. plan every operator against the synthetic specs;
3. apply office recipes through ``uno_apply.py`` (document model edits plus
   ``.uno:Save``) and text recipes in Python;
4. run the purity checks and validate every record against the schema.

It never runs an OSWorld checker. The summary reports, per operator, how many
mutants were planned, applied, and admitted, and which purity checks failed.

Usage (inside the LO-VM image)::

    python3 -m harness.q2_mutation.operators.validate --out /out/validate \
        --profile-template /home/user/.config/libreoffice/4/user
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from harness.q2_mutation.operators import _synth as synth
from harness.q2_mutation.operators import catalog
from harness.q2_mutation.operators._diff import diff
from harness.q2_mutation.operators._snapshot import snapshot
from harness.q2_mutation.operators.pipeline import (
    apply_manifest,
    apply_text_records,
    is_admitted,
    make_context,
    plan_task,
    resave_row,
    verify,
    write_jsonl,
)
from harness.q2_mutation.schema import RequirementSpec

UNO_APPLY = Path(__file__).with_name("uno_apply.py")
OFFICE = {"xlsx": "workbook.xlsx", "docx": "report.docx", "pptx": "deck.pptx"}
TEXTS = {"config": "settings.json", "ini": "app.conf", "text": "notes.txt"}


def build_inputs(root: Path) -> None:
    gold = root / "inputs" / "gold"
    initial = root / "inputs" / "initial"
    synth.build_xlsx(gold / OFFICE["xlsx"])
    synth.build_xlsx(initial / OFFICE["xlsx"], drop=("Data!D5", "Data!B6", "Data!B7"))
    synth.build_docx(gold / OFFICE["docx"])
    synth.build_docx(initial / OFFICE["docx"], blocks=synth.DEFAULT_DOCX[1:])
    synth.build_pptx(gold / OFFICE["pptx"])
    first = [dict(s) for s in synth.DEFAULT_SLIDES[0]]
    first[0] = {**first[0], "paras": [[("Results", {})]]}
    synth.build_pptx(initial / OFFICE["pptx"], slides=[first, synth.DEFAULT_SLIDES[1]])
    synth.build_json(gold / TEXTS["config"])
    synth.build_json(initial / TEXTS["config"], {**synth.SETTINGS_JSON, "editor.fontSize": 12})
    synth.build_text(gold / TEXTS["ini"], synth.APP_INI)
    synth.build_text(initial / TEXTS["ini"], synth.APP_INI.replace("threads = 4", "threads = 1"))
    synth.build_text(gold / TEXTS["text"], synth.NOTES_TXT)
    synth.build_text(initial / TEXTS["text"],
                     synth.NOTES_TXT.replace("Deploy at noon on Friday\n", ""))


def run_uno(root: Path, rows: list[dict], name: str, args: argparse.Namespace) -> dict[str, dict]:
    manifest = root / f"{name}-manifest.jsonl"
    log = root / f"{name}-log.jsonl"
    write_jsonl(manifest, rows)
    if log.exists():
        log.unlink()
    cmd = [sys.executable, str(UNO_APPLY), "--manifest", str(manifest), "--root", str(root),
           "--log", str(log), "--soffice", args.soffice, "--display", args.display,
           "--timeout", str(args.timeout)]
    if args.profile_template:
        cmd += ["--profile-template", args.profile_template]
    started = time.time()
    subprocess.run(cmd, check=True)
    print(f"{name}: {len(rows)} rows in {time.time() - started:.1f}s", flush=True)
    entries = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    return {e["mutant_id"]: e for e in entries}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--soffice", default="/usr/bin/soffice")
    parser.add_argument("--display", default=":99")
    parser.add_argument("--profile-template", default=None)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    build_inputs(root)

    resave = []
    for family, name in OFFICE.items():
        resave.append(resave_row(f"base-{family}", family, f"inputs/gold/{name}",
                                 f"saved/base/{name}"))
        resave.append(resave_row(f"initial-{family}", family, f"inputs/initial/{name}",
                                 f"saved/initial/{name}"))
    saved = run_uno(root, resave, "resave", args)
    fixed = [
        resave_row(f"fixed-{family}", family, f"saved/base/{name}", f"saved/fixed/{name}")
        for family, name in OFFICE.items()
        if saved.get(f"base-{family}", {}).get("status") == "ok"
    ]
    fixed_log = run_uno(root, fixed, "fixed", args)
    again_rows = [
        resave_row(f"fixed2-{family}", family, f"saved/fixed/{name}", f"saved/fixed2/{name}")
        for family, name in OFFICE.items()
        if fixed_log.get(f"fixed-{family}", {}).get("status") == "ok"
    ]
    again_log = run_uno(root, again_rows, "fixed2", args)

    summary: dict = {
        "catalog_sha256": catalog()["catalog_sha256"],
        "resave": {k: {"status": v["status"], "error": v.get("error")} for k, v in saved.items()},
        "lo_build": next((v.get("lo_build") for v in saved.values()), None),
        "fixed_point": {},
        "fixed_point_second": {},
        "operators": {},
    }
    for family, name in OFFICE.items():
        base = root / "saved" / "base" / name
        again = root / "saved" / "fixed" / name
        if fixed_log.get(f"fixed-{family}", {}).get("status") == "ok":
            changes = diff(snapshot(base, family), snapshot(again, family))
            summary["fixed_point"][family] = [c.as_dict() for c in changes][:20]
        third = root / "saved" / "fixed2" / name
        if again_log.get(f"fixed2-{family}", {}).get("status") == "ok":
            changes = diff(snapshot(again, family), snapshot(third, family))
            summary["fixed_point_second"][family] = [c.as_dict() for c in changes][:20]

    records_all: list[dict] = []
    plans: list[tuple[str, Path, list[dict]]] = []
    for kind in ("xlsx", "docx", "pptx", "config", "ini", "text"):
        spec = RequirementSpec.from_dict(synth.synthetic_spec(kind))
        if kind in OFFICE:
            base = root / "saved" / "base" / OFFICE[kind]
            initial = root / "saved" / "initial" / OFFICE[kind]
            if not base.exists() or not initial.exists():
                continue
        else:
            base = root / "inputs" / "gold" / TEXTS[kind]
            initial = root / "inputs" / "initial" / TEXTS[kind]
        ctx = make_context(spec.task_id, spec, base, initial)
        records, skipped = plan_task(ctx)
        write_jsonl(root / "plans" / f"{kind}.jsonl", records)
        write_jsonl(root / "plans" / f"{kind}-skipped.jsonl", skipped)
        plans.append((kind, base, records))

    office_rows = []
    for kind, _base, records in plans:
        if kind in OFFICE:
            office_rows += apply_manifest(records, f"saved/base/{OFFICE[kind]}", "mutants")
    applied = run_uno(root, office_rows, "apply", args) if office_rows else {}
    for kind, base, records in plans:
        if kind not in OFFICE:
            for entry in apply_text_records(records, base, root / "mutants"):
                applied[entry["mutant_id"]] = entry

    per_op: dict[str, Counter] = defaultdict(Counter)
    failures: dict[str, Counter] = defaultdict(Counter)
    errors: dict[str, list[str]] = defaultdict(list)
    for kind, base, records in plans:
        # Office mutants are compared with the null mutant (base saved once more).
        reference = root / "saved" / "fixed" / OFFICE[kind] if kind in OFFICE else base
        for record in records:
            mutant = root / "mutants" / record["mutant_id"] / base.name
            log = applied.get(record["mutant_id"])
            done = verify(record, reference, mutant if mutant.exists() else None, log)
            records_all.append(done)
            op = record["operator"]
            per_op[op]["planned"] += 1
            per_op[op][f"label:{record['label']}"] += 1
            if log and log.get("status") == "ok":
                per_op[op]["applied"] += 1
            elif log:
                errors[op].append(str(log.get("error"))[:300])
            if is_admitted(done):
                per_op[op]["admitted"] += 1
            for check in done["purity_checks"]:
                if not check["passed"]:
                    failures[op][check["name"]] += 1
                    if check["name"] != "applied":
                        errors[op].append(f"{check['name']}: {check['detail'][:300]}")
    write_jsonl(root / "results.jsonl", records_all)
    for op in sorted(per_op):
        summary["operators"][op] = {
            **dict(per_op[op]),
            "failed_checks": dict(failures[op]),
            "examples": errors[op][:4],
        }
    totals = Counter()
    for counts in per_op.values():
        totals.update({k: v for k, v in counts.items() if k in {"planned", "applied", "admitted"}})
    summary["totals"] = dict(totals)
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps({"totals": summary["totals"], "fixed_point": summary["fixed_point"],
                      "fixed_point_second": summary["fixed_point_second"]}, indent=1)[:4000])
    for op, info in sorted(summary["operators"].items()):
        print(f"{op:45s} planned={info.get('planned', 0)} applied={info.get('applied', 0)} "
              f"admitted={info.get('admitted', 0)} failed={info['failed_checks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
