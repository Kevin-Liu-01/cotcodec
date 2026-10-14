"""S2 v5: the registration's "Code and inputs of record" table (SHA-256 of every file of record).

v4's table (``pins_table``: v4's files of record, the shared code they import, the guest scripts
the lanes ship into the VM, and every file of harness/q2's closed world) with v5's own files after
v4's: the K1 path with A6's Writer targets per image (``ap_delta_v5.py`` and its two cells files),
the census gate (``lane_v5.py``), their batch files and step 0's result, whose ``v5_targets``
the targets are. The import walk adds v5's two entry modules to v4's. The status-fill commit of
v5's freeze procedure re-fills the table (``fill``), and ``tests/test_s2v5_registration.py``
keeps it equal to the tree. ``python -m harness.s2_locale.pins_table_v5 [--check]``.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from harness.s2_locale import pins_table as P

REGISTRATION = "program/preregistrations/s2-arabic-cua-locale-v5.md"
V5_FILES = (
    "harness/s2_locale/ap_delta_v5.py",
    "harness/s2_locale/lane_v5.py",
    "harness/s2_locale/canary_v5/suite_cells-ER.json",
    "harness/s2_locale/canary_v5/suite_cells-AR.json",
    "infra/slurm/host-single-node/s2v5-apdelta.sbatch",
    "infra/slurm/host-single-node/s2v5-vm.sbatch",
    "program/evidence/2026-10-13/s2v5-step0/step0-result.json",
)
ENTRIES = (*P.ENTRIES, "harness.s2_locale.ap_delta_v5", "harness.s2_locale.lane_v5")


def files(root: Path) -> list[str]:
    """v4's ``FILES``, then v5's, then the shared code, guest scripts and harness/q2's closed
    world."""
    from harness.q2.vm.manifest import closed_world

    first = [*P.FILES, *V5_FILES]
    shared = set(P.import_closure(root, ENTRIES)) | set(P.GUEST) | set(closed_world(str(root)))
    return first + sorted(shared - set(first))


def digests(root: Path) -> dict[str, str]:
    return {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files(root)}


def table(root: Path) -> str:
    rows = "".join(f"| `{f}` | `{d}` |\n" for f, d in digests(root).items())
    return f"{P.BEGIN}\n| File | SHA-256 |\n|---|---|\n{rows}{P.END}"


def read(text: str) -> dict[str, str]:
    return P.read(text)


def fill(root: Path) -> bool:
    """Rewrite the table in v5's registration; True if it changed."""
    path = root / REGISTRATION
    text = path.read_text(encoding="utf-8")
    start, end = text.index(P.BEGIN), text.index(P.END) + len(P.END)
    new = text[:start] + table(root) + text[end:]
    if new != text:
        path.write_text(new, encoding="utf-8")
    return new != text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    if args.check:
        ok = read((args.root / REGISTRATION).read_text(encoding="utf-8")) == digests(args.root)
        print("pins table matches the tree" if ok else "pins table differs from the tree")
        return 0 if ok else 1
    print("filled" if fill(args.root) else "unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
