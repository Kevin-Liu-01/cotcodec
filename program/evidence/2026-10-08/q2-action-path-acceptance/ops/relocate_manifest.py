#!/usr/bin/env python3
"""Point a rendered q2-action-path-v1 manifest at the operator's v1 host root.

The frozen renderer (scripts/render_q2_action_path_manifest.py) hard-codes the
development host root (~/cotcodec-runs/stage0/q2-action-path). This operator step
rewrites exactly two fields, ``source.host_dir`` and ``run_root``, to
~/cotcodec-runs/q2-action-path-v1/{src/<git sha>,runs}, leaves every other field as
rendered, and re-validates the result with the export's own ``validate_manifest`` and
ledger check (the submitter and the job check it again).

    python3 -B relocate_manifest.py EXPORT RENDERED.yaml OUT.yaml
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

V1_ROOT = "/home/kevin/cotcodec-runs/q2-action-path-v1"


def main() -> int:
    export, rendered, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    sys.path.insert(0, str(export))
    import yaml

    from harness.q2.vm.manifest import ledger_paths, ledger_view, validate_manifest

    raw = yaml.safe_load(rendered.read_text(encoding="utf-8"))
    moved = copy.deepcopy(raw)
    moved["source"]["host_dir"] = f"{V1_ROOT}/src/{raw['git_sha']}"
    moved["run_root"] = f"{V1_ROOT}/runs"
    # Exactly the two fields differ.
    for key in raw:
        if key in ("source", "run_root"):
            continue
        assert moved[key] == raw[key], key
    assert moved["source"]["tree_sha256"] == raw["source"]["tree_sha256"]
    ledger = ledger_view(str(export), ledger_paths(moved))
    validate_manifest(moved, ledger)
    header = rendered.read_text(encoding="utf-8").splitlines()[0]
    out.write_text(
        header + "\n# source.host_dir and run_root moved to the q2-action-path-v1 host root by the"
        " operator\n# (every other field as rendered; re-validated with the ledger)\n"
        + yaml.safe_dump(moved, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"VALID {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
