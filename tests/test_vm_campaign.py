"""VM campaign lane (decision D12/D13): manifest validation, docker argv, sbatch parity."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from harness.q2.vm import driver
from harness.q2.vm.hmp import clean_reply, strip_telnet
from harness.q2.vm.manifest import (
    ManifestError,
    container_labels,
    manifest_sha256,
    parse_cpuset,
    source_tree_sha256,
    validate_manifest,
)
from scripts import submit_vm_campaign

ROOT = Path(__file__).resolve().parents[1]
SBATCH = ROOT / "infra/slurm/host-single-node/vm-campaign.sbatch"
GIT = "a" * 40


def base_manifest() -> dict:
    return {
        "schema": "cotcodec-vm-campaign-v1",
        "name": "q2ap-boot-reset",
        "campaign_id": "q2ap-boot-reset-v1",
        "experiment_id": "q2-action-path-v1",
        "purpose": "infrastructure-validation",
        "preregistration": {
            "path": "program/preregistrations/q2-action-path-v1.md",
            "status": "draft",
            "sha256": "b" * 64,
        },
        "git_sha": GIT,
        "source": {
            "host_dir": f"/home/kevin/cotcodec-runs/stage0/q2-action-path/src/{GIT}",
            "tree_sha256": "c" * 64,
        },
        "run_root": "/home/kevin/cotcodec-runs/stage0/q2-action-path/runs",
        "slurm": {"cpus": 8, "memory_gb": 16, "minutes": 240},
        "container_profile": "default",
        "model": {"kind": "none", "reason": "boot and reset validation runs no model"},
        "randomness": {"contract": "deterministic", "seeds": []},
        "vm": {
            "image": "happysixd/osworld-docker@sha256:" + "d" * 64,
            "image_id": "sha256:" + "e" * 64,
            "qcow2": {
                "host_path": "/home/kevin/cotcodec-runs/stage0/q2-action-path/vm/Ubuntu.qcow2",
                "sha256": "f" * 64,
                "size_bytes": 24460197888,
                "source_url": "https://huggingface.co/datasets/xlangai/ubuntu_osworld/resolve/"
                + "1" * 40
                + "/Ubuntu.qcow2.zip",
                "archive_sha256": "2" * 64,
                "revision": "1" * 40,
                "license": "apache-2.0",
            },
            "ram_size": "4G",
            "cpu_cores": 4,
            "disk_size": "32G",
            "memory_gb": 6,
            "network": "none-netns",
            "guest_ip": "20.20.20.21",
            "server_port": 5000,
            "hmp_port": 7100,
            "concurrency": 1,
        },
        "runner": {"image_id": "sha256:" + "3" * 64, "memory_gb": 1, "cpus": 1},
        "workload": {
            "kind": "boot-reset-validation",
            "cycles": 22,
            "boot_timeout_s": 300,
            "settle_timeout_s": 60,
            "hmp_input_check": True,
            "latency_reps": 3,
            "exposure_probe": False,
        },
    }


def test_valid_manifest_passes():
    manifest = base_manifest()
    assert validate_manifest(manifest) is manifest


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda m: m["slurm"].update(gpus=1), "may not request GPUs"),
        (lambda m: m.update(gres="gpu:h100:1"), "may not request GPUs"),
        (lambda m: m["vm"].update(nvidia_devices=["/dev/nvidia0"]), "may not request GPUs"),
        (lambda m: m["vm"].update(image="happysixd/osworld-docker:latest"), "vm.image"),
        (lambda m: m["vm"].update(network="host"), "vm.network"),
        (lambda m: m["vm"].update(guest_ip="10.0.0.5"), "NAT net"),
        (lambda m: m["vm"].update(server_port=8080), "fixed"),
        (lambda m: m.update(run_root="/home/kevin/cotcodec/runs"), "run_root"),
        (lambda m: m.update(run_root="/tmp/runs"), "run_root"),
        (lambda m: m["source"].update(host_dir="/home/kevin/cotcodec-runs/x/../y"), "traversal"),
        (lambda m: m["source"].update(host_dir="/home/kevin/cotcodec-runs/src/other"), "git_sha"),
        (lambda m: m["vm"]["qcow2"].update(source_url="https://huggingface.co/x/y.zip"), "pinned"),
        (lambda m: m["model"].update(kind="vllm"), "model.kind"),
        (lambda m: m.update(container_profile="vllm"), "container_profile"),
        (lambda m: m["vm"].update(memory_gb=4), "1 GiB above"),
        (lambda m: m["slurm"].update(cpus=4), "slurm.cpus"),
        (lambda m: m["slurm"].update(memory_gb=6), "slurm.memory_gb"),
        (lambda m: m["slurm"].update(minutes=30), "cycle budget"),
        (lambda m: m["workload"].update(exposure_probe=True), "exposure probe"),
        (lambda m: m["vm"].update(concurrency=41), "vm.concurrency"),
        (lambda m: m["vm"].update(cpuset_cpus="0-2"), "smaller than"),
        (lambda m: m["vm"].update(cpuset_cpus="300"), "cpuset"),
        (lambda m: m.update(extra=1), "unknown keys"),
        (lambda m: m["randomness"].update(seeds=[42]), "declare no seeds"),
        (lambda m: m.update(purpose="acceptance"), "frozen preregistration"),
        (lambda m: m["preregistration"].update(path="docs/x.md"), "program/preregistrations"),
    ],
)
def test_tampered_manifest_fails(mutate, message):
    manifest = copy.deepcopy(base_manifest())
    mutate(manifest)
    with pytest.raises(ManifestError, match=message):
        validate_manifest(manifest)


def test_acceptance_is_refused_even_when_frozen():
    manifest = base_manifest()
    manifest["purpose"] = "acceptance"
    manifest["preregistration"]["status"] = "frozen"
    with pytest.raises(ManifestError, match="before the freeze"):
        validate_manifest(manifest)


def test_absent_preregistration_only_for_infrastructure_validation():
    manifest = base_manifest()
    manifest["preregistration"].update(status="absent", sha256=None)
    validate_manifest(manifest)
    manifest["purpose"] = "development"
    with pytest.raises(ManifestError, match="only infrastructure validation"):
        validate_manifest(manifest)


def test_seeded_contract_needs_binding():
    manifest = base_manifest()
    manifest["randomness"] = {"contract": "seeded", "seeds": [42, 43, 44]}
    with pytest.raises(ManifestError, match="seed_binding"):
        validate_manifest(manifest)


def test_parse_cpuset():
    assert parse_cpuset("0-3,8,10-11") == [0, 1, 2, 3, 8, 10, 11]
    with pytest.raises(ManifestError):
        parse_cpuset("3-1")
    with pytest.raises(ManifestError):
        parse_cpuset("1,1")


def _flag_values(argv: list[str], flag: str) -> list[str]:
    return [argv[i + 1] for i, arg in enumerate(argv) if arg == flag]


def test_vm_argv_is_gpu_less_unpublished_and_labelled():
    manifest = base_manifest()
    argv = driver.vm_run_argv(manifest, "123", 4, "8-11", "0")
    joined = " ".join(argv)
    assert "--gpus" not in joined and "nvidia" not in joined and "--privileged" not in joined
    assert "-p" not in argv and "--publish" not in joined and "-P" not in argv
    assert _flag_values(argv, "--network") == ["none"]
    assert _flag_values(argv, "--device") == ["/dev/kvm"]
    assert _flag_values(argv, "--runtime") == ["runc"]
    assert "VM_NET_DEV=lo" in _flag_values(argv, "--env")
    labels = _flag_values(argv, "--label")
    assert "cotcodec.slurm_job=123" in labels and "cotcodec.q2=1" in labels
    assert any(v.endswith(":/System.qcow2:ro") for v in _flag_values(argv, "--volume"))
    assert argv[-1] == manifest["vm"]["image"]
    assert _flag_values(argv, "--cpuset-cpus") == ["8-11"]


def test_bridge_fallback_publishes_nothing():
    manifest = base_manifest()
    manifest["vm"]["network"] = "bridge-unpublished"
    argv = driver.vm_run_argv(manifest, "123", 0, None, None)
    assert _flag_values(argv, "--network") == ["bridge"]
    assert not any(a in ("-p", "-P", "--publish", "--publish-all") for a in argv)
    assert not any(a.startswith("VM_NET_DEV") for a in _flag_values(argv, "--env"))


def test_runner_argv_shares_vm_netns_and_drops_privileges():
    manifest = base_manifest()
    argv = driver.runner_run_argv(
        manifest,
        "123",
        2,
        source_dir="/home/kevin/cotcodec-runs/s/src/x",
        out_dir="/o",
        config_in_container="/out/c.json",
        cpuset="12",
        uid=1004,
        gid=1004,
    )
    assert _flag_values(argv, "--network") == ["container:" + driver.vm_name("123", 2)]
    assert "--read-only" in argv and _flag_values(argv, "--cap-drop") == ["ALL"]
    assert _flag_values(argv, "--user") == ["1004:1004"]
    assert "CUDA_VISIBLE_DEVICES=" in _flag_values(argv, "--env")
    assert any(v.endswith("/harness:/src/harness:ro") for v in _flag_values(argv, "--volume"))
    assert "--gpus" not in argv and "--privileged" not in argv


def test_plan_cpusets_uses_the_slurm_allocation():
    manifest = base_manifest()
    nodes = {0: set(range(0, 104)), 1: set(range(104, 208))}
    plan = driver.plan_cpusets(manifest, [8, 9, 10, 11, 112, 113, 114, 115], nodes)
    assert plan["vm"] == "8-11" and plan["runner"] == "112" and plan["vm_mems"] == "0"
    manifest["vm"]["cpuset_cpus"] = "200-203"
    with pytest.raises(driver.DriverError, match="allocation"):
        driver.plan_cpusets(manifest, [8, 9, 10, 11, 12], nodes)


def test_percentile_is_nearest_rank():
    values = [float(v) for v in range(1, 21)]
    assert driver.percentile(values, 50) == 10.0
    assert driver.percentile(values, 95) == 19.0
    assert driver.percentile([], 95) is None


def test_cycle_verdict_flags_leftover_sentinel():
    record = {
        "cycle": 1,
        "token": "q2ap-9-c01",
        "runner_result": {
            "runner": {"ok": True},
            "boot": {"t_screenshot_200": 40.0},
            "facts": {"boot_id": "x"},
            "sentinel_before": {"state": {"file": "q2ap-9-c00", "dconf": "", "gsettings": "10"}},
            "sentinel_after": {
                "state": {"file": "q2ap-9-c01", "dconf": "'q2ap-9-c01'", "gsettings": "1777"}
            },
        },
        "vm_measurements": {"nvidia": 0},
        "vm_inspect": {"device_requests": None, "devices": ["/dev/kvm"], "port_bindings": {}},
        "teardown": {"container_gone": True, "leaked_volumes": []},
        "nat_mode": "nat",
    }
    verdict = driver.cycle_verdict(record, ["q2ap-9-c00"])
    assert verdict["sentinel_pristine"] is False
    assert verdict["sentinel_readback_file"] and verdict["sentinel_readback_gsettings"]
    assert verdict["no_gpu"] and verdict["no_published_ports"]
    record["runner_result"]["sentinel_before"]["state"]["file"] = None
    assert driver.cycle_verdict(record, ["q2ap-9-c00"])["sentinel_pristine"] is True
    record["vm_measurements"]["nvidia"] = 1
    assert driver.cycle_verdict(record, [])["no_gpu"] is False


def test_labels_are_scoped_to_the_job():
    labels = container_labels(base_manifest(), "77", "vm", 3)
    assert labels["cotcodec.slurm_job"] == "77" and labels["cotcodec.cycle"] == "3"


def test_sbatch_requests_no_gpu_and_cleans_only_its_label():
    text = SBATCH.read_text(encoding="utf-8")
    directives = [line for line in text.splitlines() if line.startswith("#SBATCH")]
    assert not any("gres" in d or "gpu" in d.lower() for d in directives)
    assert "label=cotcodec.slurm_job=${SLURM_JOB_ID}" in text
    assert "docker rm --force --volumes" in text
    assert "--gpus" not in text
    assert "trap cleanup EXIT" in text and "trap on_signal USR1 TERM INT" in text


def test_sbatch_tree_hash_matches_python(tmp_path):
    source = tmp_path / ("a" * 40)
    (source / "harness" / "q2" / "__pycache__").mkdir(parents=True)
    (source / "harness" / "__init__.py").write_text("x\n")
    (source / "harness" / "q2" / "mod.py").write_text("print('é')\n", encoding="utf-8")
    (source / "harness" / "q2" / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"\0")
    text = SBATCH.read_text(encoding="utf-8")
    match = re.search(
        r'actual_tree_sha256="\$\(python3 -E -s - "\$\{source_dir\}" <<\'PY\'\n(.*?)\nPY\n',
        text,
        re.S,
    )
    assert match, "tree-hash heredoc not found in the batch script"
    completed = subprocess.run(
        [sys.executable, "-E", "-s", "-", str(source)],
        input=match.group(1),
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout == source_tree_sha256(str(source))


def test_submitter_renders_cpu_only_sbatch():
    manifest = base_manifest()
    argv = submit_vm_campaign.sbatch_argv(manifest, test_only=True)
    assert not any(a.startswith(("--gres", "--gpus", "--gpu")) for a in argv)
    assert "--cpus-per-task=8" in argv and "--mem=16G" in argv and "--time=04:00:00" in argv
    export = next(a for a in argv if a.startswith("--export="))
    values = dict(item.split("=", 1) for item in export[len("--export=") :].split(","))
    decoded = json.loads(bytes.fromhex(values["COTCODEC_VM_MANIFEST_JSON_HEX"]))
    assert decoded == manifest
    assert values["COTCODEC_VM_MANIFEST_SHA256"] == manifest_sha256(manifest)
    assert values["COTCODEC_BATCH_SHA256"] == hashlib.sha256(SBATCH.read_bytes()).hexdigest()
    assert argv[-2:] == ["--test-only", str(SBATCH)]


def test_hmp_telnet_stripping_and_reply_cleanup():
    raw = bytes([255, 251, 1, 255, 251, 3]) + b"info kvm\r\nkvm support: enabled\r\n(qemu) "
    assert strip_telnet(raw).startswith(b"info kvm")
    assert clean_reply(raw, "info kvm") == "kvm support: enabled"
    assert strip_telnet(bytes([255, 255])) == bytes([255])
