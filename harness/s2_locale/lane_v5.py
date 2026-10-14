"""S2 v5: Phase 0's census lane under v5's id (``vm_lane``'s own code, bound to v5).

Registration ``s2-arabic-cua-locale-v5``, sections "Identity" and P0.7. v5 keeps v4's census,
probe, gold slot, oracle and K0 byte-identical (D94, D96): ``vm_lane.py``, ``vm_probe.py``,
``vm_gold.py``, ``oracle_vm.py``, ``k0_inputs.py`` and ``k0_v4.py`` are not edited, and the census
is v4's committed file (``vm_lane.CENSUS``, pinned by ``vm_lane.CENSUS_SHA256``). What v4's code
fixes to v4, and a v5 registered job must not inherit, is four module constants of ``vm_lane``:
the experiment id, the registration file (its ledger row and frozen-file check), the Phase 0 run
root and the batch file. ``bound`` sets them to v5's and restores them on exit; ``main`` is
``vm_lane.main`` run inside it. So a v5 census job is admitted only from v5's freeze export
(``vm_lane.check_export`` against v5's row; ``render-census --freeze-commit`` checks v5's freeze
commit with git), into v5's run root, at most once and resumed at most once there
(``vm_lane.check_once``), through ``s2v5-vm.sbatch``; the lane's own records and receipt carry
v5's id. Everything else ``vm_lane`` does is unchanged.

What stays v4's, and is disclosed in the registration: the probe and the gold slot run in the
episode container as ``vm_probe`` and ``vm_gold`` (separate interpreters, not bound), so a probed
slot's record and a gold slot's record carry their code's constant ``experiment_id`` (v4's) and
the ``s2v4-*`` schema names; ``vm_lane.submit`` hands the manifest to the batch file in
``COTCODEC_S2V4_*`` variables, which ``s2v5-vm.sbatch`` reads under those names. No reader
decides anything on those fields (``k0_inputs``, ``oracle_vm``).

``python -m harness.s2_locale.lane_v5 {run,validate,submit,render,render-census} ...``: the
commands of ``vm_lane``; ``render-census`` names the job ``s2v5-phase0`` unless told otherwise.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType

from harness.s2_locale import vm_lane as L

EXPERIMENT_ID = "s2-arabic-cua-locale-v5"
REGISTRATION = "program/preregistrations/s2-arabic-cua-locale-v5.md"
PHASE0_RUN_ROOT = f"{L.RUN_ROOT}stage0/s2v5/phase0-runs"
BATCH = "infra/slurm/host-single-node/s2v5-vm.sbatch"
NAME = "s2v5-phase0"
BINDING = {
    "EXPERIMENT_ID": EXPERIMENT_ID,
    "REGISTRATION": REGISTRATION,
    "PHASE0_RUN_ROOT": PHASE0_RUN_ROOT,
    "BATCH": BATCH,
}


@contextmanager
def bound() -> Iterator[ModuleType]:
    """``vm_lane`` with v5's id, registration, Phase 0 run root and batch file (restored on
    exit). Every ``vm_lane`` function reads these four names when it runs."""
    saved = {name: getattr(L, name) for name in BINDING}
    for name, value in BINDING.items():
        setattr(L, name, value)
    try:
        yield L
    finally:
        for name, value in saved.items():
            setattr(L, name, value)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["render-census"] and "--name" not in args:
        args += ["--name", NAME]
    with bound():
        return L.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
