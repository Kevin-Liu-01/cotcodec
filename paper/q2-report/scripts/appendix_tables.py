"""Print the Q2 report's appendix tables from committed files only (CPU, no network).

    PYTHONPATH=. python paper/q2-report/scripts/appendix_tables.py > /tmp/appendix.md

Reads the action-path catalog, gating set, L0-raw prediction and the certified-keysym rule
(`harness/q2/action_path/`), and the frozen S1a plan (base, extension blocks, task domains).
Nothing here computes a result; it only lists the objects the report names.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import yaml

from harness.q2.action_path import catalog as CAT

AP = Path("harness/q2/action_path")
GROUP_NAMES = {"keys_chords": "keys and chords"}
PLAN = Path("program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json")


def short(task_id: str) -> str:
    return task_id[:8]


def main() -> None:
    data = yaml.safe_load((AP / "catalog.yaml").read_text())
    gating = json.loads((AP / "gating_set.json").read_text())
    gating_ids = set(gating["gating"])
    prediction = yaml.safe_load((AP / "l0_raw_prediction_v2.yaml").read_text())
    predicted_fail = set(prediction["predicted_fail"])

    by_group: dict[str, list[str]] = defaultdict(list)
    for entry in data["entries"]:
        by_group[entry["group"]].append(entry["id"])

    print("### A.1 Catalog entries by class\n")
    print(
        "Non-gating entries are in italics; entries in the predicted L0-raw failing set are "
        "marked (+).\n"
    )
    print("| Class | Entries | Entry ids |")
    print("|---|---:|---|")
    for group, ids in by_group.items():
        cells = []
        for i in ids:
            name = f"`{i}`"
            if i not in gating_ids:
                name = f"*{name}*"
            if i in predicted_fail:
                name += " (+)"
            cells.append(name)
        print(f"| {GROUP_NAMES.get(group, group)} | {len(ids)} | {', '.join(cells)} |")
    print(
        f"\nGating set G: {len(gating_ids)} entries; non-gating: {len(gating['non_gating'])} "
        "(each with its reason in `gating_set.json`)."
    )
    print(
        f"Predicted L0-raw failing set ({len(predicted_fail)}): "
        + ", ".join(f"`{i}`" for i in prediction["predicted_fail"])
        + "."
    )

    keysyms = CAT.certified_keysyms(data, sorted(gating_ids))
    print(
        f"\nCertified keysyms ({len(keysyms)}; `catalog.certified_keysyms` over G): "
        + ", ".join(f"`{k}`" for k in keysyms)
        + ".\n"
    )

    plan = json.loads(PLAN.read_text())
    domains = plan["task_domains"]
    base = plan["base"]
    blocks = plan["extension_blocks"]
    ext = [t for k in sorted(blocks, key=int) for t in blocks[k]]
    print("### B.2 Task ids by domain\n")
    print("| Domain | Base (32) | Extension (81) | All 113 |")
    print("|---|---|---|---:|")
    names = sorted({domains[t] for t in base + ext})
    for d in names:
        b = sorted(short(t) for t in base if domains[t] == d)
        e = sorted(short(t) for t in ext if domains[t] == d)
        print(f"| {d} | {len(b)}: {' '.join(b)} | {len(e)}: {' '.join(e)} | {len(b) + len(e)} |")
    print(f"\nBase {len(base)}, extension {len(ext)}, total {len(base) + len(ext)}.")


if __name__ == "__main__":
    main()
