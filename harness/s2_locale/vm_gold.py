"""The S2 v4 gold slot: the task's gold, saved through its own postconfig in one cell image.

Registration ``s2-arabic-cua-locale-v4`` P0.9 (ii), the passing-side control of K0's A4(ii). One
process per slot, in the episode container the S2 VM lane (``vm_lane.py``) starts in a freshly
booted VM on the slot's cell image. The injection is the K2 executor's (``harness/q2_mutation_k2/
executor.py``, used unedited): S1a's boot wait, the task's own setup, the warm-up and settle, then
the frozen injection plan (LibreOffice's own Quit, the gold uploaded through the pinned
``SetupController`` upload step and checked by SHA-256, the task's own open step, the agent-save
or postconfig save), the pinned ``DesktopEnv.evaluate()`` and the restart checks. After it, the
guest's selector is checked against the cell's (the image check), and ``probe.json`` is written
in the S2 lane's record shape with the K2 run record inside.

Infrastructure (the registration's one rule, as ``vm_probe.py``): a K2 run that is not scored,
a failed image check, or a scored run with a postconfig server error (a postconfig ``/setup/*``
reply with no HTTP status or a status of 500 or above) ends the gold slot as
``infrastructure``, and the lane re-queues it once.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "s2v4-vm-gold-v1"
EXPERIMENT_ID = "s2-arabic-cua-locale-v4"
K2_KEEP = ("status", "exclusion", "infrastructure_type", "infrastructure_detail", "score",
           "verdict", "plan_ops", "save_paths", "post_postconfig", "unsaved_at_read",
           "late_write", "derived_not_uploaded", "timings", "warmup", "postconfig_replies",
           "postconfig_failures")  # fmt: skip


def k2_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """The K2 executor's run config for this gold slot (every file from the pinned cache)."""
    gold = cfg["gold"]
    root = cfg.get("file_cache_dir", "/inputs/file_cache/files")
    return {
        "lane": cfg["lane"], "purpose": cfg["purpose"], "slot": cfg["slot"], "set": "k2",
        "pair": 0, "run": int(cfg.get("rep", 1)), "attempt": int(cfg["attempt"]),
        "block": cfg["block"], "job_id": gold["job_id"], "mutant_id": gold["job_id"],
        "task_id": cfg["task_id"], "kind": "null", "candidate_sha256": gold["candidate_sha256"],
        "files": {vm: {"local": f"{root}/{e['rel']}", "sha256": e["sha256"]}
                  for vm, e in gold["files"].items()},
        "out_dir": cfg.get("out_dir", "/out"), "guest_ip": cfg["guest_ip"],
        "server_port": cfg["server_port"], "osworld_dir": cfg["osworld_dir"],
        "file_cache_dir": root, "settle_after_reset_s": cfg["settle_after_reset_s"],
        "settle_before_eval_s": cfg["settle_before_eval_s"], "t_vm_start": cfg.get("t_vm_start"),
    }  # fmt: skip


def gold_record(cfg: dict[str, Any], k2: dict[str, Any],
                selector: str | None, facts_error: str | None) -> dict[str, Any]:  # fmt: skip
    rec: dict[str, Any] = {
        "schema": SCHEMA, "experiment_id": EXPERIMENT_ID, "lane": cfg["lane"],
        "purpose": cfg["purpose"], "slot": cfg["slot"], "task_id": cfg["task_id"],
        "cell": cfg["cell"], "kind": "gold", "block": cfg["block"], "attempt": cfg["attempt"],
        "image_sha256": cfg["image_sha256"], "gold_job_id": cfg["gold"]["job_id"],
        "k2": {k: k2.get(k) for k in K2_KEEP if k in k2}, "selector_in_guest": selector,
    }  # fmt: skip
    from harness.s2_locale.vm_probe import server_error

    server_errors = [r for r in k2.get("postconfig_replies") or () if server_error(r)]
    if k2.get("status") != "scored":
        rec.update(status="infrastructure", infrastructure_type=k2.get("infrastructure_type"),
                   infrastructure_detail=k2.get("infrastructure_detail"), score=None,
                   verdict=None)  # fmt: skip
    elif server_errors:
        rec.update(status="infrastructure", infrastructure_type="probe:postconfig_server_error",
                   infrastructure_detail=f"{len(server_errors)} postconfig replies: "
                   f"{[r.get('status') for r in server_errors]}", score=None,
                   verdict=None)  # fmt: skip
    elif facts_error is not None or selector != cfg["selector_sha256"]:
        rec.update(status="infrastructure", infrastructure_type="probe:image_check",
                   infrastructure_detail=facts_error or f"selector {selector}", score=None,
                   verdict=None)  # fmt: skip
    else:
        rec.update(status="probed", infrastructure_type=None, score=k2.get("score"),
                   verdict=k2.get("verdict"))  # fmt: skip
    return rec


def run(config_path: Path) -> dict[str, Any]:
    from harness.q2.vm.guest_http import GuestClient
    from harness.q2_mutation_k2 import executor as k2x
    from harness.s2_locale import vm_probe

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    k2_path = Path("/tmp/k2-config.json")
    k2_path.write_text(json.dumps(k2_config(cfg)), encoding="utf-8")
    k2 = k2x.run_from_config(k2_path)
    selector, error = None, None
    try:
        facts = GuestClient(cfg["guest_ip"], cfg["server_port"]).run_script(
            vm_probe.GUEST_SCRIPT.read_text(encoding="utf-8"),
            ["facts", json.dumps({"selector": vm_probe.SELECTOR_PATH})])
        selector = facts.get("selector_sha256")
    except Exception as exc:  # noqa: BLE001 - a guest that cannot answer fails the image check
        error = f"{type(exc).__name__}: {str(exc)[:200]}"
    rec = gold_record(cfg, k2, selector, error)
    out = Path(cfg.get("out_dir", "/out"))
    (out / "probe.json").write_text(json.dumps(rec, indent=1, sort_keys=True), encoding="utf-8")
    return rec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    rec = run(args.config)
    print(json.dumps({k: rec.get(k) for k in ("slot", "cell", "status", "verdict")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
