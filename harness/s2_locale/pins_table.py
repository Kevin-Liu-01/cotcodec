"""S2 v4: the registration's "Code and inputs of record" table (SHA-256 of every file of record).

The registration (section "Code and inputs of record", between ``BEGIN`` and ``END``) lists the
SHA-256 of the code and inputs Phase 0 and K1 run from, so the frozen text names them; the
status-fill commit of the freeze procedure re-fills it (``fill``), and
``tests/test_s2v4_registration.py`` keeps it equal to the tree. The files (``files``): the S2 v4
code and inputs (``FILES``); the shared code they import, found by walking the imports of the
entry modules (``ENTRIES``: the lane, the probe, the gold slot, the oracle, the K0 reader and
``ap_delta``; ``import_closure``); the guest scripts the lanes ship into the VM (``GUEST``); and
every file of harness/q2's closed world (``harness.q2.vm.manifest.closed_world``), which K1 runs
through harness/q2's driver.
``python -m harness.s2_locale.pins_table [--check]``.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from pathlib import Path

REGISTRATION = "program/preregistrations/s2-arabic-cua-locale-v4.md"
BEGIN = "<!-- PINS:BEGIN -->"
END = "<!-- PINS:END -->"
FILES = (
    "harness/s2_locale/k0_v4.py",
    "harness/s2_locale/k0_inputs.py",
    "harness/s2_locale/oracle.py",
    "harness/s2_locale/oracle_vm.py",
    "harness/s2_locale/phase0.py",
    "harness/s2_locale/capture.py",
    "harness/s2_locale/catalog.py",
    "harness/s2_locale/vm_lane.py",
    "harness/s2_locale/vm_probe.py",
    "harness/s2_locale/vm_gold.py",
    "harness/s2_locale/guest/s2_guest.py",
    "harness/s2_locale/golds.py",
    "harness/s2_locale/pd_cache.py",
    "harness/s2_locale/ap_delta.py",
    "harness/s2_locale/image_build.py",
    "harness/s2_locale/fetch_langpacks.py",
    "harness/s2_locale/images.json",
    "infra/slurm/host-single-node/s2v4-vm.sbatch",
    "infra/slurm/host-single-node/s2v4-apdelta.sbatch",
    "infra/slurm/host-single-node/s2v4-cpu.sbatch",
    "scripts/render_q2_action_path_manifest.py",
    "experiments/manifests/s2v4/phase0-census.json",
    "experiments/manifests/s2v4/golds-v4.jsonl",
    "experiments/manifests/s2v4/k1-plan.json",
    "program/evidence/2026-10-11/s2v4-image/pd-cache/pd-cache-manifest.json",
    "program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/pool/pool-v3.json",
    "program/evidence/q2-mutation/splits.json",
    "program/evidence/q2-mutation/harness/file-cache-receipts.tsv",
)
ENTRIES = (
    "harness.s2_locale.vm_lane", "harness.s2_locale.vm_probe", "harness.s2_locale.vm_gold",
    "harness.s2_locale.oracle_vm", "harness.s2_locale.k0_inputs", "harness.s2_locale.ap_delta",
    "harness.s2_locale.pd_cache", "harness.s2_locale.image_build",
)
GUEST = (
    "harness/q2/vm/guest/guard.py",  # the keyboard warm-up (S1a's driver)
    "harness/q2_mutation_k2/guest/k2_guest.py",  # the gold slot's injection executor
)
ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$")


def _module_path(root: Path, module: str) -> str | None:
    for rel in (module.replace(".", "/") + ".py", module.replace(".", "/") + "/__init__.py"):
        if (root / rel).is_file():
            return rel
    return None


def import_closure(root: Path, entries: tuple[str, ...] = ENTRIES) -> list[str]:
    """Every repository file the entry modules import, directly or not (module level or inside
    functions; ``harness`` and ``scripts`` packages only), with the packages' ``__init__.py``."""
    seen: dict[str, str] = {}
    stack = list(entries)
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        rel = _module_path(root, module)
        if rel is None:
            continue
        seen[module] = rel
        parts = module.split(".")
        stack += [".".join(parts[:i]) for i in range(1, len(parts))]
        package = module if rel.endswith("__init__.py") else ".".join(parts[:-1])
        for node in ast.walk(ast.parse((root / rel).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                stack += [a.name for a in node.names if a.name.startswith(("harness", "scripts"))]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.rsplit(".", node.level - 1)[0] if node.level > 1 else package
                    name = f"{base}.{node.module}" if node.module else base
                else:
                    name = node.module or ""
                if name.startswith(("harness", "scripts")):
                    stack += [name, *(f"{name}.{a.name}" for a in node.names)]
    return sorted(set(seen.values()))


def files(root: Path) -> list[str]:
    """``FILES`` first, then the shared code, guest scripts and harness/q2's closed world."""
    from harness.q2.vm.manifest import closed_world

    shared = set(import_closure(root)) | set(GUEST) | set(closed_world(str(root)))
    return list(FILES) + sorted(shared - set(FILES))


def digests(root: Path) -> dict[str, str]:
    return {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files(root)}


def table(root: Path) -> str:
    rows = "".join(f"| `{f}` | `{d}` |\n" for f, d in digests(root).items())
    return f"{BEGIN}\n| File | SHA-256 |\n|---|---|\n{rows}{END}"


def read(text: str) -> dict[str, str]:
    body = text.split(BEGIN, 1)[1].split(END, 1)[0]
    return {m.group(1): m.group(2) for line in body.splitlines() if (m := ROW.match(line))}


def fill(root: Path) -> bool:
    """Rewrite the table in the registration; True if it changed."""
    path = root / REGISTRATION
    text = path.read_text(encoding="utf-8")
    start, end = text.index(BEGIN), text.index(END) + len(END)
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
