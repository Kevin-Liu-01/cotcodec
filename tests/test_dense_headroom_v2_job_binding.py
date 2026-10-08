"""Every v2 receipt records its Slurm job, and the summariser accepts it.

v1's receipts carried ``slurm_job_id: null`` (the entry point read
``SLURM_JOB_ID`` inside the container, where the batch script never sets it),
so v1's summariser refused every receipt its jobs could write (job 727). v2's
entry point reads ``job_id`` from the job's ``job.env``, which the batch script
writes into the job's run directory (the container's ``/outputs``) before it
creates the container. The end-to-end test runs the real
``infra/slurm/host-single-node/docker-research.sbatch`` against stub host tools
(Linux only, as the lane's own runtime tests): the stub container runs the
entry point's receipt-writing code in the environment the batch script passed
to ``docker create``, and the receipt goes to the summariser's job check.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import textwrap
from pathlib import Path

import pytest

from harness import dense_headroom_v2 as dv2
from harness import dense_headroom_v2_lanes as lanes
from scripts import fill_dense_headroom_precheck_manifests as v1f
from scripts import summarise_dense_headroom_precheck_v2 as summariser
from tests.test_research_container import RUNTIME_SKIP, StubbedRun, _deterministic_raw

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_job_id_comes_from_job_env(tmp_path: Path) -> None:
    (tmp_path / "job.env").write_text("job_id=727\npredecessor_job_id=none\n")
    assert dv2.batch_job_id(tmp_path, {}) == {"slurm_job_id": "727", "source": "job.env"}
    assert dv2.batch_job_id(tmp_path, {"SLURM_JOB_ID": "727"})["slurm_job_id"] == "727"
    with pytest.raises(dv2.JobBindingError):
        dv2.batch_job_id(tmp_path, {"SLURM_JOB_ID": "728"})
    (tmp_path / "job.env").write_text("job_id=none\n")
    with pytest.raises(dv2.JobBindingError):
        dv2.batch_job_id(tmp_path, {})
    with pytest.raises(dv2.JobBindingError):
        dv2.batch_job_id(tmp_path / "absent", {})
    assert dv2.batch_job_id(None, {}) == {"slurm_job_id": None, "source": "none"}
    assert dv2.batch_job_id(None, {"SLURM_JOB_ID": "9"})["source"] == "SLURM_JOB_ID"


def test_the_batch_script_writes_job_env_before_the_container_and_passes_no_slurm_id() -> None:
    text = (PROJECT_ROOT / "infra/slurm/host-single-node/docker-research.sbatch").read_text()
    assert text.index('} > "${run_dir}/job.env"') < text.index("docker create \\")
    create = text[text.index("docker create \\"):text.index('> "${run_dir}/container-id.txt"')]
    assert "SLURM_JOB_ID" not in create
    assert '--volume "${run_dir}:/outputs:rw"' in create
    assert "--env COTCODEC_OUTPUT_DIR=/outputs" in create


# The stub container: the entry point's receipt-writing code (v2's and v1's) in the
# container's environment, rebuilt from the batch script's `docker create` call.
RECEIPT_CODE = '''\
import os, sys
from pathlib import Path
from harness import dense_headroom_v2 as dv2
from harness import dense_headroom_v2_lanes as lanes
from harness import dense_headroom_data as dhd
from scripts import run_dense_headroom_precheck_v2 as entry
from scripts import run_dense_headroom_precheck as entry_v1
out = Path(os.environ["COTCODEC_OUTPUT_DIR"])
argv = ["--lane", "qwen3-0.6b-base", "--output-dir", str(out / "dense-precheck"),
        "--evidence", "x", "--expected-evidence-sha256", "x", "--model-dir", "x",
        "--receipt", "x", "--expected-receipt-sha256", "x", "--seeds", "42", "43", "44"]
job = entry.Job(entry.parse_args(argv))
binding = dv2.batch_job_id(out, os.environ)
job.lane = lanes.LANES["qwen3-0.6b-base"]
job.hashes = {"git_sha": os.environ["COTCODEC_GIT_SHA"],
              "source_sha256": os.environ["COTCODEC_SOURCE_SHA256"],
              "job": {"kind": "fresh", "predecessor_job_id": None, "minutes": 30,
                      "slurm_job_id": binding["slurm_job_id"],
                      "slurm_job_id_source": binding["source"]}}
job.receipt("receipt.json", {"status": "PRECHECK_COMPLETE"})
old = entry_v1.Job(entry_v1.parse_args(argv + ["--preregistration", "x",
                                               "--expected-preregistration-sha256", "x"]))
old.out = out / "v1"
old.lane = dhd.LANES["qwen3-0.6b-base"]
old.hashes = dict(job.hashes, job={"kind": "fresh", "predecessor_job_id": None,
                                   "minutes": 30})
old.receipt("receipt.json", {"status": "PRECHECK_COMPLETE"})
'''

WORKLOAD_PROGRAM = textwrap.dedent('''\
    import json, os, subprocess, sys
    from pathlib import Path

    state = Path(os.environ["FAKE_DOCKER_STATE"])
    run_dir = Path(os.environ["FAKE_RUN_DIR"])
    calls = [json.loads(line) for line in (state / "calls.jsonl").read_text().splitlines()]
    (create,) = [c for c in calls if c and c[0] == "create"]
    env = {}
    for flag, value in zip(create, create[1:]):
        if flag == "--env":
            key, _, val = value.partition("=")
            env[key] = val.replace("/outputs", str(run_dir))
        if flag == "--volume" and value.endswith(":/outputs:rw"):
            assert value == f"{run_dir}:/outputs:rw", value
    env["PATH"] = os.environ["PATH"]
    env["PYTHONPATH"] = os.environ["BINDING_PROJECT_ROOT"]
    result = subprocess.run([sys.executable, os.environ["BINDING_RECEIPT_CODE"]], env=env,
                            capture_output=True, text=True)
    sys.stderr.write(result.stderr)
    sys.exit(result.returncode)
''')

WORKLOAD = textwrap.dedent("""\
    #!/usr/bin/env bash
    set -u
    state="${FAKE_DOCKER_STATE:?}"
    echo running > "${state}/status"
    echo "$$" > "${state}/workload.pid.tmp"
    mv "${state}/workload.pid.tmp" "${state}/workload.pid"
    "${BINDING_PYTHON}" "${BINDING_PROGRAM}"
    code=$?
    echo "${code}" > "${state}/exit_code"
    echo exited > "${state}/status"
    exit "${code}"
""")


@pytest.fixture
def lane_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # A fresh directory whose path satisfies the submitter's simple-path rule.
    return tmp_path_factory.mktemp("lane")


@RUNTIME_SKIP
def test_a_batch_receipt_is_bound_to_its_job_and_accepted(lane_root: Path) -> None:
    program = lane_root / "binding_program.py"
    program.write_text(WORKLOAD_PROGRAM, encoding="utf-8")
    receipt_code = lane_root / "receipt_writer.py"
    receipt_code.write_text(RECEIPT_CODE, encoding="utf-8")
    run = StubbedRun(lane_root, _deterministic_raw(), BINDING_PROGRAM=str(program),
                     BINDING_RECEIPT_CODE=str(receipt_code),
                     BINDING_PYTHON=sys.executable,
                     BINDING_PROJECT_ROOT=str(PROJECT_ROOT))
    (lane_root / "workload.sh").write_text(WORKLOAD, encoding="utf-8")
    assert run.run() == 0, run.stderr_text()

    job_dir = run.run_dir
    job = run.env_file("job.env")
    receipt_path = job_dir / "dense-precheck" / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["slurm_job_id"] == job["job_id"] == job_dir.name == "4242"
    assert receipt["slurm_job_id_source"] == "job.env"
    v1_receipt = json.loads((job_dir / "v1" / "receipt.json").read_text(encoding="utf-8"))
    assert v1_receipt["slurm_job_id"] is None  # job 727's defect, from v1's own code

    # What the real container and the filler would have left beside the receipt.
    (job_dir / "provenance-verification.txt").write_text(json.dumps(
        {"status": "PASS", "git_sha": job["git_sha"], "source_sha256": job["source_sha256"]}))
    manifest = json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
    lane = dataclasses.replace(lanes.LANES["qwen3-0.6b-base"], minutes=manifest["minutes"])
    text = json.dumps({"name": manifest["name"], "resources": {"minutes": manifest["minutes"]},
                       "image_id": manifest["image_id"]})
    v1f.claim_slot(job_dir.parent, lane, v1f.NextJob("first", manifest["minutes"], 0, None, 0),
                   text, manifest["image_id"])
    log = lane_root / "orx.log"
    log.write_text(f"ORX_RESULT kind=slurm-manifest direction=x job={job_dir.name} exit=0\n")
    orx = summariser.v1s.orx_results([log])

    checked = summariser.v1s.check_job(receipt_path, receipt, lane, orx)
    assert checked["job_id"] == "4242"
    with pytest.raises(summariser.SummaryError, match="Slurm job is not its job directory"):
        summariser.v1s.check_job(receipt_path, v1_receipt, lane, orx)
