"""Check the records of successor E's two pre-freeze gates (G-E4 and G-E5) with E's code.

q2-stage1-successor-e-v1 section 4.1. Reads only the files of this directory and the
repository's committed code; runs nothing on the host. Usage, from the repository root::

    python program/evidence/2026-10-11/q2-stage1-successor-e/gates/check_gates.py --out OUT.json

G-E4 (the CPU-only development smoke, VM job 1206, rescoring job 1208) passes when all four
slots end scored with records that E's ``records.validate`` accepts, the lane receipt holds no
error, and offline rescoring (``rescore.py capture``) of the captured states matches the live
score on every episode (the registration's three conditions). The checks around them (the
manifest is the committed one, the job ran the draft commit's export and the registered batch
file without a GPU, S1a's ``validate`` refuses every record, the rescored states are the live
ones) are reported beside them.

G-E5 (the unchanged ``glmm.R`` on E-shaped synthetic rows in the pinned container, CPU job
1210) is reported as ``glmm.R`` wrote it: each fit's convergence and Hessian, the bootstrap
refits, the variance components beside the generating values and the likelihood-ratio test.
The input is regenerated here with E's ``analysis glmm-synthetic`` code and compared byte for
byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

from harness.q2_stage1 import glmm as G  # noqa: E402
from harness.q2_stage1 import lane as L1  # noqa: E402
from harness.q2_stage1 import records as R1  # noqa: E402
from harness.q2_stage1e import records as RE  # noqa: E402

DRAFT_COMMIT = "8a23a483dc39f6e34aa52dca75a9a5e106b18375"
VM_BATCH_SHA256 = "2d27bbe50f6ce6aa9df9e4ba9a015ca2d6d489ccc4259f8b8b0a245c94fc6229"  # section 23
CPU_BATCH_SHA256 = "3880d337ad5bb0dc3c0edfc39f41811028118ef574c75efb08faa023dc6dee33"  # job 984's
DEV_MANIFEST = ROOT / "experiments/manifests/q2-stage1e/dev-smoke-v1.json"
METRIC_IMAGE_ID = L1.EPISODE_IMAGE_ID
GLMM_IMAGE_ID = "sha256:b15584f3954f1c83fc3e5067e29c57c5c55e3b2a50ef28e4e68a394e595aabed"
GLMM_R_SHA256 = "e3ea337c77bf6a8b9289047b62cfc51053a5f666fe51795071a1ae317f36681d"  # S1a sec. 20
R_LOCK_SHA256 = "abb8871de4549732cd396dc60fc1f2aec78bf1fffad788cb841e8bf61668bfc7"  # S1a G0 12
VM_JOB, RESCORE_JOB, GLMM_JOB = "1206", "1208", "1210"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def kv(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        for part in line.split(" ") if line.startswith("lane_exit=") else [line]:
            if "=" in part:
                key, value = part.split("=", 1)
                out[key] = value
    return out


def ge4() -> dict[str, Any]:
    d = HERE / "ge4"
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    preflight = kv(d / "preflight.txt")
    receipt = json.loads((d / "lane-receipt.json").read_text(encoding="utf-8"))
    raw = read_jsonl(d / "episodes.jsonl")
    checks: dict[str, Any] = {}

    digest = hashlib.sha256(L1.canonical(manifest).encode()).hexdigest()
    committed = json.loads(DEV_MANIFEST.read_text(encoding="utf-8"))
    checks["manifest_is_the_committed_dev_smoke"] = (
        digest
        == preflight["manifest_sha256"]
        == hashlib.sha256(L1.canonical(committed).encode()).hexdigest()
    )
    checks["preflight"] = {
        "source_git_sha_is_the_draft_commit": preflight["source_git_sha"] == DRAFT_COMMIT,
        "batch_is_section_23s_q2e_vm_sbatch": preflight["batch_sha256"] == VM_BATCH_SHA256,
        "no_gres": "gres" not in preflight["job_tres"].lower(),
        "docker_runtime_runc": preflight["docker_default_runtime"] == "runc",
        "lane_exit_0": preflight["lane_exit"] == "0",
        "no_labelled_container_left": preflight["labelled_containers_left"] == "0",
        "job_id": preflight["job_id"] == VM_JOB,
    }

    accepted, refused_by_s1a = [], 0
    for rec in raw:
        accepted.append(RE.validate(rec))  # raises on any record E's validate refuses
        try:
            R1.validate(rec)
        except R1.RecordError:
            refused_by_s1a += 1
    slots = {s["slot"]: s for s in manifest["slots"]}
    labels_match = all(
        all(
            rec[k] == slots[rec["slot"]][k]
            for k in ("task_id", "harness", "size", "session", "rerun", "block")
        )  # fmt: skip
        for rec in accepted
        if rec["slot"] in slots
    )
    checks["records"] = {
        "n_records": len(accepted),
        "accepted_by_e_validate": len(accepted),
        "refused_by_s1a_validate": refused_by_s1a,
        "one_record_per_manifest_slot": sorted(r["slot"] for r in accepted) == sorted(slots),
        "labels_are_the_manifest_slots": labels_match,
        "statuses": sorted({r["status"] for r in accepted}),
        "sessions": sorted({r["session"] for r in accepted}),
        "attempts": sorted({r["attempt"] for r in accepted}),
        "infrastructure_types": sorted({str(r["infrastructure_type"]) for r in accepted}),
        "gpu_devices_seen": sum(len(r["gpu_devices"]) for r in accepted),
    }
    checks["receipt"] = {
        "error": receipt.get("error"),
        "statuses": receipt.get("statuses"),
        "records": receipt.get("records"),
        "stopped": receipt.get("stopped"),
        "purpose": receipt.get("purpose"),
        "foreign_slurm_jobs_in_snapshots": sum(
            len(s.get("squeue_foreign") or []) for s in receipt.get("snapshots") or []
        ),  # fmt: skip
    }

    rows = read_jsonl(d / "rescored-1208.jsonl")
    by_key = {(r["slot"], r["attempt"]): r for r in rows}
    scored = [r for r in accepted if r["status"] == "scored"]
    matches = []
    for rec in scored:
        row = by_key.get((rec["slot"], rec["attempt"]))
        matches.append({
            "slot": rec["slot"],
            "row": row is not None,
            "state_sha256_equal": row is not None and row["state_sha256"] == rec["state_sha256"],
            "live_score_equal": row is not None and row["live_score"] == rec["score"],
            "raw_equals_live": row is not None and row["raw"] == rec["score"],
            "live_offline_match": None if row is None else row["live_offline_match"],
            "errors": [] if row is None else sorted(k for k in row if k.endswith("_error")),
        })  # fmt: skip
    rescore_receipt = json.loads((d / "receipt-1208.json").read_text(encoding="utf-8"))
    checks["rescoring"] = {
        "rows": len(rows),
        "per_episode": matches,
        "receipt_exit_status": rescore_receipt["exit_status"],
        "receipt_image_is_the_metric_image": rescore_receipt["image_id"] == METRIC_IMAGE_ID,
        "receipt_gpus_requested": rescore_receipt["gpus_requested"],
        "receipt_container_dev_nvidia": rescore_receipt["container_dev_nvidia"],
        "receipt_batch_is_s1a_cpu_sbatch": rescore_receipt["batch_sha256"] == CPU_BATCH_SHA256,
        "receipt_job_id": rescore_receipt["job_id"],
    }
    criteria = {
        "all_4_slots_scored_records_accepted_by_e_validate": (
            len(accepted) == 4
            and checks["records"]["one_record_per_manifest_slot"]
            and checks["records"]["statuses"] == ["scored"]
        ),
        "lane_receipt_holds_no_error": "error" not in receipt
        and receipt.get("statuses") == {"scored": 4},
        "offline_rescoring_matches_live_on_every_episode": (
            len(matches) == 4
            and all(
                m["row"]
                and m["state_sha256_equal"]
                and m["live_offline_match"] is True
                and not m["errors"]
                for m in matches
            )  # fmt: skip
            and rescore_receipt["exit_status"] == 0
        ),
        "a_scored_record_with_session_E1": any(
            r["session"] == "E1" and r["status"] == "scored" for r in accepted
        ),
    }
    supporting = (
        checks["manifest_is_the_committed_dev_smoke"]
        and all(checks["preflight"].values())
        and refused_by_s1a == len(accepted)
        and labels_match
        and checks["records"]["gpu_devices_seen"] == 0
        and checks["rescoring"]["receipt_image_is_the_metric_image"]
        and checks["rescoring"]["receipt_gpus_requested"] == 0
        and checks["rescoring"]["receipt_batch_is_s1a_cpu_sbatch"]
    )
    return {
        "criteria": criteria,
        "supporting_checks_hold": bool(supporting),
        "passed": all(criteria.values()) and bool(supporting),
        "checks": checks,
        "scores_live": [r["score"] for r in accepted],
    }


def ge5() -> dict[str, Any]:
    d = HERE / "ge5"
    with tempfile.TemporaryDirectory() as tmp:
        regenerated = Path(tmp) / "synthetic-e-k113.csv"
        G.write_csv(RE.glmm_synthetic(113, 42), regenerated)
        same_input = regenerated.read_bytes() == (d / "synthetic-e-k113.csv").read_bytes()
    out = json.loads((d / "glmm-synthetic-e-k113.json").read_text(encoding="utf-8"))
    receipt = json.loads((d / f"receipt-{GLMM_JOB}.json").read_text(encoding="utf-8"))
    truth = G.SYNTHETIC_TRUTH
    generating = {
        "task": truth["sd_task"] ** 2,
        "task:size": truth["sd_task_size"] ** 2,
        "task:harness": truth["sd_task_harness"] ** 2,
        "task:size:harness": truth["sd_task_size_harness"] ** 2,
        "session": truth["sd_session"] ** 2,
        "harness:session": truth["sd_harness_session"] ** 2,
        "task:session": truth["sd_task_session"] ** 2,
        "task:harness:session": truth["sd_task_harness_session"] ** 2,
    }
    lock = d / "r-packages.json"
    lock_line = (d / "r-packages.sha256").read_text(encoding="utf-8").split()
    checks = {
        "input_regenerated_byte_for_byte_by_e_code": same_input,
        "input_sha256": sha(d / "synthetic-e-k113.csv"),
        "glmm_r_is_s1as": sha(ROOT / "harness/q2_stage1/glmm.R") == GLMM_R_SHA256,
        "r_package_lock_is_s1as": sha(lock) == R_LOCK_SHA256 and R_LOCK_SHA256 in lock_line,
        "exit_code_file": (d / "glmm.exit").read_text(encoding="utf-8").strip(),
        "receipt_exit_status": receipt["exit_status"],
        "receipt_image_is_the_pinned_glmm_image": receipt["image_id"] == GLMM_IMAGE_ID,
        "receipt_gpus_requested": receipt["gpus_requested"],
        "receipt_container_dev_nvidia": receipt["container_dev_nvidia"],
        "receipt_network": receipt["network"],
        "receipt_batch_is_s1a_cpu_sbatch": receipt["batch_sha256"] == CPU_BATCH_SHA256,
        "receipt_started_finished": [receipt["started_at"], receipt["finished_at"]],
    }
    shape = {k: out.get(k) for k in ("schema", "n_episodes", "n_tasks", "seed", "n_boot",
                                     "glmmTMB_version", "TMB_version", "R_version")}  # fmt: skip
    ran = (
        same_input
        and checks["glmm_r_is_s1as"]
        and checks["r_package_lock_is_s1as"]
        and checks["exit_code_file"] == "0"
        and receipt["exit_status"] == 0
        and checks["receipt_image_is_the_pinned_glmm_image"]
        and receipt["gpus_requested"] == 0
        and shape["n_episodes"] == 1808
        and shape["n_tasks"] == 113
    )
    return {
        "ran_as_registered": bool(ran),
        "both_fits_converged_with_pd_hessian": bool(out["full"].get("ok"))
        and bool(out["reduced"].get("ok")),
        "shape": shape,
        "full": out["full"],
        "reduced": out["reduced"],
        "fixed_effects": out.get("fixed_effects"),
        "variance_components": out.get("variance_components"),
        "variance_components_generating": generating,
        "latent_shares": out.get("latent_shares"),
        "bootstrap": out.get("bootstrap"),
        "lrt_task_harness": out.get("lrt_task_harness"),
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; outputs are never overwritten")
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=False).stdout.strip()  # fmt: skip
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "harness"],
                           capture_output=True, text=True, check=False).stdout.strip()  # fmt: skip
    files = sorted(p for p in HERE.rglob("*") if p.is_file() and p.suffix != ".pyc"
                   and p.name not in ("gates-check.json", "README.md"))  # fmt: skip
    result = {
        "schema": "q2-stage1e-gates-check-v1",
        "experiment_id": "q2-stage1-successor-e-v1",
        "draft_commit_exported": DRAFT_COMMIT,
        "G-E4": ge4(),
        "G-E5": ge5(),
        "provenance": {
            "checked_at_commit": head,
            "harness_dirty": bool(dirty),
            "python": sys.version.split()[0],
            "inputs_sha256": {str(p.relative_to(HERE)): sha(p) for p in files},
        },
    }
    text = json.dumps(result, indent=1, sort_keys=True) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(json.dumps({"G-E4 passed": result["G-E4"]["passed"],
                      "G-E5 ran as registered": result["G-E5"]["ran_as_registered"],
                      "G-E5 both fits converged":
                          result["G-E5"]["both_fits_converged_with_pd_hessian"]}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
