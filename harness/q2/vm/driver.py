"""Host-side driver for VM campaigns (runs inside ``vm-campaign.sbatch``).

It is invoked by the batch script after the script has checked its own digest,
the manifest digest and the source tree digest. It re-validates the manifest,
then starts and removes Docker containers for each cycle:

* the VM container: the digest-pinned OSWorld image, no ``--gpus``, no
  published ports, ``--network none`` (default) or the default bridge with
  nothing published (fallback, exposure recorded), ``/dev/kvm`` only,
  the qcow2 bind-mounted read-only, CPUs taken from the Slurm allocation;
* the runner container: a minimal GPU-less image that joins the VM's network
  namespace (``--network container:<vm>``), runs as the host user with all
  capabilities dropped and a read-only root, and measures the cycle.

Every container carries ``cotcodec.slurm_job=<job id>``; the driver and the
batch script's exit trap remove only containers with this job's label.

This file must not import CUDA libraries or anything outside the standard
library: it runs as a bare host process (decision D12).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from harness.q2.action_path.rdev import summarize_capture
from harness.q2.vm.manifest import (
    ManifestError,
    container_labels,
    manifest_sha256,
    parse_cpuset,
    validate_manifest,
)

DOCKER = "docker"
RUNNER_TIMEOUT_SLACK_S = 900
FALLBACK_MARKER = "falling back to usermode"
RDEV_PLAN = "harness/q2/action_path/rdev_plan.json"
SENTINEL_BLINK = "1777"  # harness/q2/vm/guest/sentinel.py writes this gsettings value


class DriverError(RuntimeError):
    """A campaign precondition failed; the job must stop."""


def run(argv: list[str], timeout: float = 120.0, check: bool = True) -> subprocess.CompletedProcess:
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if check and completed.returncode != 0:
        raise DriverError(f"{argv[:3]} failed ({completed.returncode}): {completed.stderr[-500:]}")
    return completed


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 24), b""):
            digest.update(chunk)
    return digest.hexdigest()


def label_args(labels: dict[str, str]) -> list[str]:
    out: list[str] = []
    for key in sorted(labels):
        out += ["--label", f"{key}={labels[key]}"]
    return out


def vm_name(job_id: str, cycle: int) -> str:
    return f"cotcodec-q2vm-{job_id}-c{cycle:02d}"


def runner_name(job_id: str, cycle: int) -> str:
    return f"cotcodec-q2run-{job_id}-c{cycle:02d}"


def vm_run_argv(
    manifest: dict[str, Any], job_id: str, cycle: int, cpuset: str | None, mems: str | None
) -> list[str]:
    """``docker run`` for one VM container. No --gpus, no -p, no --privileged."""
    vm = manifest["vm"]
    argv = [
        DOCKER,
        "run",
        "--detach",
        "--name",
        vm_name(job_id, cycle),
        *label_args(container_labels(manifest, job_id, "vm", cycle)),
        "--runtime",
        "runc",
        "--cap-add",
        "NET_ADMIN",
        "--device",
        "/dev/kvm",
        "--sysctl",
        "net.ipv4.ip_forward=1",
        "--memory",
        f"{vm['memory_gb']}g",
        "--memory-swap",
        f"{vm['memory_gb']}g",
        "--pids-limit",
        "4096",
        "--stop-timeout",
        "10",
        "--env",
        f"RAM_SIZE={vm['ram_size']}",
        "--env",
        f"CPU_CORES={vm['cpu_cores']}",
        "--env",
        f"DISK_SIZE={vm['disk_size']}",
        "--volume",
        f"{vm['qcow2']['host_path']}:/System.qcow2:ro",
    ]
    if vm["network"] == "none-netns":
        # No Docker network at all: the image's NAT uses loopback as its uplink,
        # so the guest is reachable only from inside this namespace.
        argv += ["--network", "none", "--env", "VM_NET_DEV=lo"]
    else:
        argv += ["--network", "bridge"]
    if cpuset:
        argv += ["--cpuset-cpus", cpuset]
    if mems is not None:
        argv += ["--cpuset-mems", mems]
    argv.append(vm["image"])
    return argv


def runner_run_argv(
    manifest: dict[str, Any],
    job_id: str,
    cycle: int,
    *,
    source_dir: str,
    out_dir: str,
    config_in_container: str,
    cpuset: str | None,
    uid: int,
    gid: int,
    subcommand: str = "boot-cycle",
) -> list[str]:
    runner = manifest["runner"]
    argv = [
        DOCKER,
        "run",
        "--rm",
        "--name",
        runner_name(job_id, cycle),
        *label_args(container_labels(manifest, job_id, "runner", cycle)),
        "--runtime",
        "runc",
        "--network",
        f"container:{vm_name(job_id, cycle)}",
        "--user",
        f"{uid}:{gid}",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=64m",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        f"{runner['memory_gb']}g",
        "--pids-limit",
        "256",
        "--env",
        "CUDA_VISIBLE_DEVICES=",
        "--env",
        "NVIDIA_VISIBLE_DEVICES=void",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--volume",
        f"{source_dir}/harness:/src/harness:ro",
        "--volume",
        f"{out_dir}:/out",
        "--workdir",
        "/src",
    ]
    if cpuset:
        argv += ["--cpuset-cpus", cpuset]
    argv += [
        runner["image_id"],
        "python3",
        "-E",
        "-s",
        "-m",
        "harness.q2.vm.runner",
        subcommand,
        "--config",
        config_in_container,
    ]
    return argv


def probe_run_argv(
    manifest: dict[str, Any],
    job_id: str,
    cycle: int,
    *,
    source_dir: str,
    out_dir: str,
    target_ip: str,
    uid: int,
    gid: int,
) -> list[str]:
    """A separate container on the default bridge, to measure the fallback's exposure."""
    labels = container_labels(manifest, job_id, "exposure-probe", cycle)
    return [
        DOCKER,
        "run",
        "--rm",
        "--name",
        f"cotcodec-q2probe-{job_id}-c{cycle:02d}",
        *label_args(labels),
        "--runtime",
        "runc",
        "--network",
        "bridge",
        "--user",
        f"{uid}:{gid}",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "512m",
        "--env",
        "CUDA_VISIBLE_DEVICES=",
        "--volume",
        f"{source_dir}/harness:/src/harness:ro",
        "--volume",
        f"{out_dir}:/out",
        "--workdir",
        "/src",
        manifest["runner"]["image_id"],
        "python3",
        "-E",
        "-s",
        "-m",
        "harness.q2.vm.runner",
        "tcp-probe",
        "--host",
        target_ip,
        "--port",
        str(manifest["vm"]["server_port"]),
        "--out",
        f"/out/exposure-c{cycle:02d}.json",
    ]


def qemu_img_info_argv(manifest: dict[str, Any], job_id: str) -> list[str]:
    vm = manifest["vm"]
    return [
        DOCKER,
        "run",
        "--rm",
        "--name",
        f"cotcodec-q2qimg-{job_id}",
        *label_args(container_labels(manifest, job_id, "qemu-img", -1)),
        "--runtime",
        "runc",
        "--network",
        "none",
        "--read-only",
        "--volume",
        f"{vm['qcow2']['host_path']}:/System.qcow2:ro",
        "--entrypoint",
        "qemu-img",
        vm["image"],
        "info",
        "--output=json",
        "/System.qcow2",
    ]


def slurm_cpu_ids(job_id: str) -> list[int]:
    completed = run(["scontrol", "show", "job", "-d", job_id], timeout=30)
    match = re.search(r"CPU_IDs=([0-9,\-]+)", completed.stdout)
    if not match:
        raise DriverError("cannot read this job's CPU allocation from scontrol")
    return parse_cpuset(match.group(1))


def numa_nodes() -> dict[int, set[int]]:
    nodes: dict[int, set[int]] = {}
    base = Path("/sys/devices/system/node")
    for node_dir in sorted(base.glob("node[0-9]*")):
        cpulist = (node_dir / "cpulist").read_text().strip()
        nodes[int(node_dir.name[4:])] = set(parse_cpuset(cpulist))
    return nodes


def format_cpuset(cpus: list[int]) -> str:
    cpus = sorted(cpus)
    parts: list[str] = []
    start = prev = cpus[0]
    for cpu in cpus[1:]:
        if cpu == prev + 1:
            prev = cpu
            continue
        parts.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = cpu
    parts.append(f"{start}-{prev}" if start != prev else str(start))
    return ",".join(parts)


def plan_cpusets(
    manifest: dict[str, Any], allocated: list[int], nodes: dict[int, set[int]]
) -> dict[str, Any]:
    """Split the Slurm allocation into the VM's and the runner's CPU sets."""
    vm = manifest["vm"]
    need_vm = vm["cpu_cores"]
    need_runner = manifest["runner"]["cpus"]
    pool = sorted(allocated)
    if "cpuset_cpus" in vm:
        requested = parse_cpuset(vm["cpuset_cpus"])
        if not set(requested) <= set(pool):
            raise DriverError("vm.cpuset_cpus is not inside this job's Slurm allocation")
        vm_cpus = requested[:need_vm]
    else:
        vm_cpus = pool[:need_vm]
    rest = [cpu for cpu in pool if cpu not in vm_cpus]
    if len(vm_cpus) < need_vm or len(rest) < need_runner:
        raise DriverError("Slurm allocation is too small for the VM and the runner")
    runner_cpus = rest[:need_runner]
    vm_nodes = {node for node, cpus in nodes.items() if set(vm_cpus) & cpus}
    mems = vm.get("cpuset_mems")
    if mems is None and len(vm_nodes) == 1:
        mems = str(next(iter(vm_nodes)))
    return {
        "allocated": format_cpuset(pool),
        "vm": format_cpuset(vm_cpus),
        "runner": format_cpuset(runner_cpus),
        "vm_mems": mems,
        "vm_numa_nodes": sorted(vm_nodes),
    }


def snapshot_host(job_id: str) -> dict[str, Any]:
    """Foreign-load guard inputs: load average, the Slurm queue and Docker's container count."""
    out: dict[str, Any] = {"t": time.time()}
    try:
        out["loadavg"] = Path("/proc/loadavg").read_text().split()[:3]
    except OSError:
        out["loadavg"] = None
    queue = run(["squeue", "-h", "-o", "%i|%u|%T|%C|%b|%j"], timeout=30, check=False)
    rows = [line.split("|") for line in queue.stdout.splitlines() if line.strip()]
    out["squeue_foreign"] = [r for r in rows if r and r[0] != job_id]
    containers = run([DOCKER, "ps", "--format", "{{.ID}}"], timeout=30, check=False)
    ours = run(
        [
            DOCKER,
            "ps",
            "-a",
            "--filter",
            f"label=cotcodec.slurm_job={job_id}",
            "--format",
            "{{.ID}}",
        ],
        timeout=30,
        check=False,
    )
    out["containers_running_total"] = len(containers.stdout.split())
    out["containers_ours"] = len(ours.stdout.split())
    return out


def inspect_container(name: str) -> dict[str, Any]:
    completed = run([DOCKER, "inspect", name], timeout=60)
    data = json.loads(completed.stdout)[0]
    host = data.get("HostConfig", {})
    networks = data.get("NetworkSettings", {}).get("Networks") or {}
    return {
        "image": data.get("Image"),
        "runtime": host.get("Runtime"),
        "privileged": host.get("Privileged"),
        "device_requests": host.get("DeviceRequests"),
        "devices": [d.get("PathOnHost") for d in host.get("Devices") or []],
        "port_bindings": host.get("PortBindings"),
        "publish_all_ports": host.get("PublishAllPorts"),
        "network_mode": host.get("NetworkMode"),
        "networks": sorted(networks),
        "has_bridge_address": any(n.get("IPAddress") for n in networks.values()),
        "cap_add": host.get("CapAdd"),
        "cpuset_cpus": host.get("CpusetCpus"),
        "cpuset_mems": host.get("CpusetMems"),
        "memory": host.get("Memory"),
        "mounts": [
            {
                "type": m.get("Type"),
                "destination": m.get("Destination"),
                "rw": m.get("RW"),
                "name": m.get("Name"),
            }
            for m in data.get("Mounts") or []
        ],
        "labels": {
            k: v
            for k, v in (data.get("Config", {}).get("Labels") or {}).items()
            if k.startswith("cotcodec.")
        },
        "started_at": data.get("State", {}).get("StartedAt"),
    }


def bridge_ip(name: str) -> str | None:
    completed = run(
        [
            DOCKER,
            "inspect",
            "--format",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            name,
        ],
        timeout=60,
        check=False,
    )
    value = completed.stdout.strip()
    return value or None


def vm_measurements(name: str) -> dict[str, Any]:
    script = (
        "set -u; "
        "echo nvidia=$(ls -1 /dev 2>/dev/null | grep -c '^nvidia' || true); "
        "echo overlay_bytes=$(stat -c %s /boot.qcow2 2>/dev/null || echo NA); "
        "echo overlay_alloc=$(du -sB1 /boot.qcow2 2>/dev/null | cut -f1 || echo NA); "
        "echo storage_alloc=$(du -sB1 /storage 2>/dev/null | cut -f1 || echo NA); "
        "echo nat_rules=$(iptables -t nat -S 2>/dev/null | grep -c DNAT || true)"
    )
    completed = run([DOCKER, "exec", name, "sh", "-c", script], timeout=60, check=False)
    values: dict[str, Any] = {"rc": completed.returncode}
    for line in completed.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = int(value) if value.strip().isdigit() else value.strip()
    return values


def remove_container(name: str) -> dict[str, Any]:
    volumes = []
    try:
        info = json.loads(run([DOCKER, "inspect", name], timeout=60).stdout)[0]
        volumes = [m["Name"] for m in info.get("Mounts") or [] if m.get("Type") == "volume"]
    except (DriverError, json.JSONDecodeError, IndexError, KeyError):
        pass
    # Upstream reset is stop then remove (OSWorld DockerProvider.revert_to_snapshot).
    stopped = run([DOCKER, "stop", "--time", "10", name], timeout=120, check=False)
    removed = run([DOCKER, "rm", "--force", "--volumes", name], timeout=120, check=False)
    leaked = []
    for volume in volumes:
        if run([DOCKER, "volume", "inspect", volume], timeout=60, check=False).returncode == 0:
            leaked.append(volume)
    gone = run([DOCKER, "inspect", name], timeout=60, check=False).returncode != 0
    return {
        "stop_rc": stopped.returncode,
        "rm_rc": removed.returncode,
        "anonymous_volumes": len(volumes),
        "leaked_volumes": leaked,
        "container_gone": gone,
    }


def percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile (no interpolation)."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100.0 * len(ordered)))
    return ordered[rank - 1]


def run_cycle(
    manifest: dict[str, Any],
    job_id: str,
    cycle: int,
    prev_token: str | None,
    run_dir: Path,
    source_dir: str,
    cpus: dict[str, Any],
) -> dict[str, Any]:
    workload = manifest["workload"]
    vm = manifest["vm"]
    cycles_dir = run_dir / "cycles"
    token = f"q2ap-{job_id}-c{cycle:02d}"
    name = vm_name(job_id, cycle)
    record: dict[str, Any] = {
        "cycle": cycle,
        "token": token,
        "prev_token": prev_token,
        "host_before": snapshot_host(job_id),
    }
    t0 = time.time()
    run(vm_run_argv(manifest, job_id, cycle, cpus["vm"], cpus["vm_mems"]), timeout=120)
    record["t0"] = t0
    try:
        record["vm_inspect"] = inspect_container(name)
        config = {
            "cycle": cycle,
            "token": token,
            "prev_token": prev_token,
            "t0": t0,
            "guest_ip": vm["guest_ip"],
            "server_port": vm["server_port"],
            "hmp_port": vm["hmp_port"],
            "boot_timeout_s": workload["boot_timeout_s"],
            "settle_timeout_s": workload["settle_timeout_s"],
            "out": f"/out/cycle-{cycle:02d}.json",
        }
        if workload["kind"] == "boot-reset-validation":
            subcommand = "boot-cycle"
            config.update(
                latency_reps=workload["latency_reps"],
                hmp_input_check=workload["hmp_input_check"],
                full_facts=cycle == 0,
            )
        else:
            subcommand = "rdev-capture"
            config.update(
                plan_path="/src/" + RDEV_PLAN,
                plan_sha256=workload["plan_sha256"],
                reps=workload["reps"],
            )
        config_path = cycles_dir / f"config-{cycle:02d}.json"
        config_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
        runner_argv = runner_run_argv(
            manifest,
            job_id,
            cycle,
            source_dir=source_dir,
            out_dir=str(cycles_dir),
            config_in_container=f"/out/config-{cycle:02d}.json",
            cpuset=cpus["runner"],
            uid=os.getuid(),
            gid=os.getgid(),
            subcommand=subcommand,
        )
        budget = workload["boot_timeout_s"] + workload["settle_timeout_s"] + RUNNER_TIMEOUT_SLACK_S
        if subcommand == "rdev-capture":
            budget += workload["reps"] * 60 * 6
        try:
            completed = run(runner_argv, timeout=budget, check=False)
            record["runner_rc"] = completed.returncode
            record["runner_stderr_tail"] = completed.stderr[-1500:]
        except subprocess.TimeoutExpired:
            record["runner_rc"] = None
            record["runner_error"] = f"runner exceeded {budget}s"
            run([DOCKER, "rm", "--force", runner_name(job_id, cycle)], timeout=60, check=False)
        result_path = cycles_dir / f"cycle-{cycle:02d}.json"
        if result_path.exists():
            record["runner_result"] = json.loads(result_path.read_text(encoding="utf-8"))
        if workload.get("exposure_probe"):
            target = bridge_ip(name)
            record["exposure_target_is_bridge_ip"] = bool(target)
            if target:
                probe = probe_run_argv(
                    manifest,
                    job_id,
                    cycle,
                    source_dir=source_dir,
                    out_dir=str(cycles_dir),
                    target_ip=target,
                    uid=os.getuid(),
                    gid=os.getgid(),
                )
                run(probe, timeout=120, check=False)
                probe_path = cycles_dir / f"exposure-c{cycle:02d}.json"
                if probe_path.exists():
                    probe_result = json.loads(probe_path.read_text(encoding="utf-8"))
                    probe_result.pop("host", None)  # never record the bridge address
                    record["exposure_probe"] = probe_result
        record["vm_measurements"] = vm_measurements(name)
        logs = run([DOCKER, "logs", name], timeout=60, check=False)
        log_text = logs.stdout + logs.stderr
        (cycles_dir / f"vm-{cycle:02d}.log").write_text(log_text, encoding="utf-8")
        record["nat_mode"] = "usermode-fallback" if FALLBACK_MARKER in log_text else "nat"
        record["qemu_kvm_in_log"] = "-enable-kvm" in log_text or "accel=kvm" in log_text
    finally:
        record["teardown"] = remove_container(name)
    record["host_after"] = snapshot_host(job_id)
    return record


def cycle_verdict(record: dict[str, Any], seen_tokens: list[str]) -> dict[str, Any]:
    result = record.get("runner_result") or {}
    boot = result.get("boot") or {}
    before = ((result.get("sentinel_before") or {}).get("state")) or {}
    after = ((result.get("sentinel_after") or {}).get("state")) or {}
    token = record["token"]
    leftovers = [t for t in seen_tokens if t and any(t in str(v) for v in before.values())]
    if str(before.get("gsettings")) == SENTINEL_BLINK:
        leftovers.append("gsettings")
    hmp = result.get("hmp_input") or {}
    measurements = record.get("vm_measurements") or {}
    inspect = record.get("vm_inspect") or {}
    no_gpu = (
        (result.get("runner") or {}).get("ok") is True
        and measurements.get("nvidia") == 0
        and not inspect.get("device_requests")
        and all("nvidia" not in str(d) for d in inspect.get("devices") or [])
    )
    return {
        "cycle": record["cycle"],
        "booted": boot.get("t_screenshot_200") is not None,
        "boot_s": boot.get("t_screenshot_200"),
        "settled_s": (result.get("settle") or {}).get("t_settled"),
        "boot_id": (result.get("facts") or {}).get("boot_id"),
        "sentinel_pristine": not leftovers and "sentinel_error" not in result,
        "sentinel_leftovers": leftovers,
        "sentinel_readback_file": after.get("file") == token,
        "sentinel_readback_dconf": token in str(after.get("dconf")),
        "sentinel_readback_gsettings": str(after.get("gsettings")) == SENTINEL_BLINK,
        "hmp_ok": hmp.get("ok"),
        "hmp_steps": {s["id"]: s["ok"] for s in hmp.get("steps") or []},
        "no_gpu": no_gpu,
        "no_published_ports": not inspect.get("port_bindings")
        and not inspect.get("publish_all_ports"),
        "nat_mode": record.get("nat_mode"),
        "container_removed": (record.get("teardown") or {}).get("container_gone"),
        "leaked_volumes": (record.get("teardown") or {}).get("leaked_volumes"),
        "error": result.get("error") or record.get("runner_error"),
    }


def summarize(verdicts: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    boots = [v["boot_s"] for v in verdicts if v["boot_s"] is not None]
    settles = [v["settled_s"] for v in verdicts if v["settled_s"] is not None]
    boot_ids = [v["boot_id"] for v in verdicts if v["boot_id"]]
    sentinel_checks = verdicts[1:]
    hmp_steps: dict[str, list[bool]] = {}
    for verdict in verdicts:
        for step, ok in (verdict["hmp_steps"] or {}).items():
            hmp_steps.setdefault(step, []).append(bool(ok))
    latency: dict[str, list[float]] = {
        "screenshot_s": [],
        "accessibility_s": [],
        "execute_noop_s": [],
    }
    for record in records:
        block = (record.get("runner_result") or {}).get("latency") or {}
        for key in latency:
            latency[key] += block.get(key) or []
    return {
        "cycles": len(verdicts),
        "boots_ok": sum(v["booted"] for v in verdicts),
        "boot_s": {
            "p50": percentile(boots, 50),
            "p95": percentile(boots, 95),
            "max": max(boots) if boots else None,
            "n": len(boots),
        },
        "settled_s": {
            "p50": percentile(settles, 50),
            "p95": percentile(settles, 95),
            "n": len(settles),
        },
        "distinct_boot_ids": len(set(boot_ids)),
        "sentinel_reset_checks": len(sentinel_checks),
        "sentinel_pristine": sum(v["sentinel_pristine"] for v in sentinel_checks),
        "sentinel_readback_file": sum(v["sentinel_readback_file"] for v in verdicts),
        "sentinel_readback_dconf": sum(v["sentinel_readback_dconf"] for v in verdicts),
        "sentinel_readback_gsettings": sum(v["sentinel_readback_gsettings"] for v in verdicts),
        "hmp_cycles_all_ok": sum(1 for v in verdicts if v["hmp_ok"]),
        "hmp_step_pass_counts": {k: f"{sum(v)}/{len(v)}" for k, v in sorted(hmp_steps.items())},
        "no_gpu_all": all(v["no_gpu"] for v in verdicts),
        "no_published_ports_all": all(v["no_published_ports"] for v in verdicts),
        "nat_modes": sorted({str(v["nat_mode"]) for v in verdicts}),
        "containers_removed_all": all(v["container_removed"] for v in verdicts),
        "leaked_volumes": sorted({x for v in verdicts for x in v["leaked_volumes"] or []}),
        "latency_s": {
            key: {"n": len(vals), "p50": percentile(vals, 50), "p95": percentile(vals, 95)}
            for key, vals in latency.items()
        },
        "errors": [
            {"cycle": v["cycle"], "error": str(v["error"])[:300]} for v in verdicts if v["error"]
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[1-9][0-9]{0,19}", args.job_id):
        raise SystemExit("job id must be numeric")
    try:
        manifest = validate_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    except ManifestError as exc:
        raise SystemExit(f"manifest rejected inside the job: {exc}") from exc
    run_dir: Path = args.run_dir
    (run_dir / "cycles").mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "schema": "cotcodec-vm-campaign-receipt-v1",
        "job_id": args.job_id,
        "manifest_sha256": manifest_sha256(manifest),
        "campaign_id": manifest["campaign_id"],
        "git_sha": manifest["git_sha"],
        "source_tree_sha256": manifest["source"]["tree_sha256"],
        "started_at": time.time(),
        "driver_python": sys.version.split()[0],
    }
    docker_info = run([DOCKER, "info", "--format", "{{json .}}"], timeout=60)
    info = json.loads(docker_info.stdout)
    receipt["docker"] = {
        "server_version": info.get("ServerVersion"),
        "default_runtime": info.get("DefaultRuntime"),
        "runtimes": sorted((info.get("Runtimes") or {}).keys()),
        "cgroup_version": info.get("CgroupVersion"),
    }
    vm = manifest["vm"]
    image_check = run(
        [DOCKER, "image", "inspect", "--format", "{{.Id}} {{json .RepoDigests}}", vm["image_id"]],
        timeout=60,
    ).stdout.strip()
    if not image_check.startswith(vm["image_id"]) or vm["image"] not in image_check:
        raise DriverError("VM image ID and digest reference do not agree")
    runner_id = run(
        [DOCKER, "image", "inspect", "--format", "{{.Id}}", manifest["runner"]["image_id"]],
        timeout=60,
    ).stdout.strip()
    if runner_id != manifest["runner"]["image_id"]:
        raise DriverError("runner image is missing")
    qcow2 = vm["qcow2"]
    stat = os.stat(qcow2["host_path"], follow_symlinks=False)
    if not os.path.isfile(qcow2["host_path"]) or os.path.islink(qcow2["host_path"]):
        raise DriverError("qcow2 must be a regular file")
    if stat.st_size != qcow2["size_bytes"]:
        raise DriverError("qcow2 size does not match the manifest")
    if stat.st_mode & 0o222:
        raise DriverError("qcow2 must be read-only on the host")
    receipt["qcow2_sha256_before"] = sha256_file(qcow2["host_path"])
    if receipt["qcow2_sha256_before"] != qcow2["sha256"]:
        raise DriverError("qcow2 digest does not match the manifest")
    qimg = run(qemu_img_info_argv(manifest, args.job_id), timeout=120)
    qinfo = json.loads(qimg.stdout)
    receipt["qcow2_info"] = {k: qinfo.get(k) for k in ("format", "virtual-size", "actual-size")}
    allocated = slurm_cpu_ids(args.job_id)
    cpus = plan_cpusets(manifest, allocated, numa_nodes())
    receipt["cpusets"] = cpus
    receipt["host_start"] = snapshot_host(args.job_id)
    dangling_before = run([DOCKER, "volume", "ls", "-q", "--filter", "dangling=true"], timeout=60)
    receipt["dangling_volumes_before"] = len(dangling_before.stdout.split())

    workload = manifest["workload"]
    if workload["kind"] == "rdev-capture":
        plan_path = Path(args.source_dir) / RDEV_PLAN
        if hashlib.sha256(plan_path.read_bytes()).hexdigest() != workload["plan_sha256"]:
            raise DriverError("R-dev plan digest does not match the manifest")
    cycles = workload.get("cycles", 1)

    records: list[dict[str, Any]] = []
    verdicts: list[dict[str, Any]] = []
    tokens: list[str] = []
    prev = None
    for cycle in range(cycles):
        record = run_cycle(manifest, args.job_id, cycle, prev, run_dir, args.source_dir, cpus)
        verdict = cycle_verdict(record, tokens)
        records.append(record)
        verdicts.append(verdict)
        tokens.append(record["token"])
        prev = record["token"]
        (run_dir / "cycles" / f"record-{cycle:02d}.json").write_text(
            json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(json.dumps({"cycle_verdict": verdict}, sort_keys=True), flush=True)

    receipt["qcow2_sha256_after"] = sha256_file(qcow2["host_path"])
    receipt["qcow2_unchanged"] = receipt["qcow2_sha256_after"] == receipt["qcow2_sha256_before"]
    leftovers = run(
        [
            DOCKER,
            "ps",
            "-a",
            "--filter",
            f"label=cotcodec.slurm_job={args.job_id}",
            "--format",
            "{{.Names}}",
        ],
        timeout=60,
    )
    receipt["labelled_containers_left"] = leftovers.stdout.split()
    dangling_after = run([DOCKER, "volume", "ls", "-q", "--filter", "dangling=true"], timeout=60)
    receipt["dangling_volumes_after"] = len(dangling_after.stdout.split())
    receipt["host_end"] = snapshot_host(args.job_id)
    receipt["finished_at"] = time.time()
    summary = summarize(verdicts, records)
    infra_ok = (
        summary["boots_ok"] == summary["cycles"]
        and summary["sentinel_pristine"] == summary["sentinel_reset_checks"]
        and summary["sentinel_readback_file"] == summary["cycles"]
        and summary["no_gpu_all"]
        and summary["no_published_ports_all"]
        and summary["containers_removed_all"]
        and not summary["leaked_volumes"]
        and receipt["qcow2_unchanged"]
        and not receipt["labelled_containers_left"]
    )
    if workload["kind"] == "rdev-capture":
        # One boot, no reset check; the capture itself is summarized below.
        infra_ok = (
            summary["boots_ok"] == summary["cycles"]
            and summary["no_gpu_all"]
            and summary["no_published_ports_all"]
            and summary["containers_removed_all"]
            and not summary["leaked_volumes"]
            and receipt["qcow2_unchanged"]
            and not receipt["labelled_containers_left"]
        )
        capture = ((records[0].get("runner_result") or {}).get("capture")) or {}
        if capture.get("trials"):
            capture["job_id"] = args.job_id
            reference = summarize_capture(capture)
            (run_dir / "rdev_reference.json").write_text(
                json.dumps(reference, indent=2, sort_keys=True), encoding="utf-8"
            )
            entries = reference["entries"].values()
            summary["rdev"] = {
                "entries": len(reference["entries"]),
                "stable": sum(1 for e in entries if e["stable"]),
                "unstable": sorted(k for k, e in reference["entries"].items() if not e["stable"]),
            }
        else:
            infra_ok = False
            summary["rdev"] = {"error": capture.get("error", "no capture trials")}
    summary["infra_gates_pass"] = infra_ok
    receipt["summary"] = summary
    receipt["verdicts"] = verdicts
    (run_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"summary": summary}, sort_keys=True), flush=True)
    return 0 if infra_ok else 3


if __name__ == "__main__":
    sys.exit(main())
