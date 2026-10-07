#!/usr/bin/env python3
"""Read LibreOffice build facts and user profiles out of the OSWorld VM disk.

Runs inside the vmprobe container with --network=none. Inputs: a read-only
qcow2. Outputs (under --out): the root partition as a sparse raw file in a
scratch dir (deleted at the end unless --keep-raw), and copies of the files
listed in WANTED plus a facts.json with their SHA-256. No file leaves the host
except facts.json (build ids, package versions, paths, hashes).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

WANTED_DIRS = [
    "/opt",
    "/usr/lib/libreoffice/program",
    "/home/user/.config/libreoffice/4/user",
    "/etc/systemd/system",
    "/usr/share/fonts",
]
WANTED_FILES = [
    "/usr/lib/libreoffice/program/versionrc",
    "/usr/lib/libreoffice/program/bootstraprc",
    "/home/user/.config/libreoffice/4/user/registrymodifications.xcu",
    "/etc/systemd/system/osworld_server.service",
    "/etc/os-release",
    "/var/lib/dpkg/status",
    "/home/user/.config/vlc/vlcrc",
    "/home/user/.config/GIMP/2.10/gimprc",
    "/home/user/.config/Code/User/settings.json",
]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def debugfs(raw: Path, request: str) -> str:
    out = subprocess.run(
        ["debugfs", "-R", request, str(raw)], capture_output=True, text=True, check=False
    )
    return out.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qcow2", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    facts: dict[str, object] = {}
    info = json.loads(run(["qemu-img", "info", "-U", "--output=json", args.qcow2]).stdout)
    facts["qemu_img_info"] = {k: info.get(k) for k in ("virtual-size", "format", "cluster-size")}
    head = scratch / "head.raw"
    run(
        [
            "qemu-img",
            "dd",
            "-U",
            "-f",
            "qcow2",
            "-O",
            "raw",
            "bs=512",
            "count=34",
            f"if={args.qcow2}",
            f"of={head}",
        ]
    )
    # A GPT header lists partitions; extend the stub to the virtual size so sfdisk
    # accepts it without the backup header.
    with head.open("r+b") as handle:
        handle.truncate(int(info["virtual-size"]))
    table = json.loads(run(["sfdisk", "--json", str(head)]).stdout)["partitiontable"]
    facts["partitions"] = table.get("partitions")
    candidates = sorted(table["partitions"], key=lambda p: -int(p["size"]))
    root = candidates[0]
    raw = scratch / "root.raw"
    run(
        [
            "qemu-img",
            "dd",
            "-U",
            "-f",
            "qcow2",
            "-O",
            "raw",
            "bs=512",
            f"skip={root['start']}",
            f"count={root['size']}",
            f"if={args.qcow2}",
            f"of={raw}",
        ]
    )
    facts["root_partition"] = {"start": root["start"], "size": root["size"]}
    listings = {d: debugfs(raw, f"ls -l {d}") for d in WANTED_DIRS}
    (out / "listings.txt").write_text(
        "\n".join(f"== {d}\n{text}" for d, text in listings.items()), encoding="utf-8"
    )
    opt_entries = re.findall(r"\s(libreoffice[^\s]*)\s*$", listings["/opt"], re.M)
    files = list(WANTED_FILES)
    for entry in opt_entries:
        files += [f"/opt/{entry}/program/versionrc", f"/opt/{entry}/program/bootstraprc"]
    copied = {}
    for path in files:
        target = out / "files" / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["debugfs", "-R", f"dump -p {path} {target}", str(raw)],
            capture_output=True,
            text=True,
            check=False,
        )
        if target.is_file() and target.stat().st_size > 0:
            copied[path] = {
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        elif target.exists():
            target.unlink()
    facts["copied"] = copied
    facts["opt_libreoffice_dirs"] = opt_entries
    status = out / "files" / "var/lib/dpkg/status"
    pkgs = {}
    if status.is_file():
        for block in status.read_text(encoding="utf-8", errors="replace").split("\n\n"):
            name = re.search(r"^Package: (.+)$", block, re.M)
            version = re.search(r"^Version: (.+)$", block, re.M)
            state = re.search(r"^Status: (.+)$", block, re.M)
            if (
                name
                and version
                and state
                and "installed" in state.group(1)
                and re.search(r"libreoffice|^ure|uno|fonts-|xvfb|python3$", name.group(1))
            ):
                pkgs[name.group(1)] = version.group(1)
    facts["dpkg_selected"] = pkgs
    (out / "facts.json").write_text(json.dumps(facts, indent=2, sort_keys=True), encoding="utf-8")
    if not args.keep_raw:
        raw.unlink()
    head.unlink()
    print(json.dumps({"copied": len(copied), "opt": opt_entries, "pkgs": len(pkgs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
