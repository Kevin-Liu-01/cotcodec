"""The S1a analysis runbook (ops/s1a-analysis/RUNBOOK.md) as written: every command it gives is
accepted by the script it calls, and its environment block refuses unfilled placeholders and
writes a usable env.sh. Synthetic paths only; nothing is submitted."""

from __future__ import annotations

import importlib
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops" / "s1a-analysis"
sys.path.insert(0, str(OPS))

RUNBOOK = OPS / "RUNBOOK.md"
HOST_PREFIX = "/home/kevin/cotcodec-runs/stage0"
FREEZE = "d5f57988ab94e0c098feddb744b78b73b5ad88ca"
OPSC = "0123456789abcdef0123456789abcdef01234567"
VMS = ("1045", "1048", "1051", "1053")

OPS_CMD = re.compile(r"python3 -E -s -B \$OPS/(\w+)\.py\s+(.*)")
STEP_CMD = re.compile(r"\bstep (\S+) (\w+)\.py\s+(.*)")
REGISTERED_CMD = re.compile(r"python3 -E -s -B -m harness\.q2_stage1\.(\w+)\s+(.*)")
END = re.compile(r";|\)|>|\||&&")


def bash_blocks() -> list[str]:
    return re.findall(r"```bash\n(.*?)```", RUNBOOK.read_text(encoding="utf-8"), flags=re.S)


def logical_lines() -> list[str]:
    return [line for block in bash_blocks() for line in block.replace("\\\n", " ").splitlines()]


def expand(text: str, root: Path) -> list[str]:
    """The runbook's shell variables as env.sh sets them, on a synthetic layout."""
    r = f"{root}/r"
    a = f"{r}/analysis/s1a-v1"
    x = f"{r}/src/{FREEZE}"
    scalars = {
        "R": r,
        "A": a,
        "X": x,
        "PLAN": f"{x}/program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json",
        "OPSC": OPSC,
        "OPS": f"{r}/ops/{OPSC}/ops/s1a-analysis",
        "INPUTS": f"{root}/inputs",
        "VM": VMS[0],
    }
    arrays = {
        "RUNS": [arg for vm in VMS for arg in ("--run-dir", f"{r}/runs/{vm}")],
        "COSTRUNS": [arg for vm in VMS for arg in ("--run-dir", f"{r}/runs/{vm}")],
        "DR0S": [arg for vm in VMS for arg in ("--dr0", f"{a}/dr0-{vm}.json")],
        "IN": ["--input", f"{a}/a1.jsonl", "--input", f"{a}/costs.json"],
    }
    for name, values in arrays.items():
        text = text.replace(f'"${{{name}[@]}}"', shlex.join(values))
    text = re.sub(r"\$\{?([A-Z][A-Z0-9_]*)\}?", lambda m: scalars[m.group(1)], text)
    assert "$" not in text, text
    return shlex.split(text)


def runbook_commands() -> list[tuple[str, str, str]]:
    """(kind, module, argument text) for every command line of the runbook."""
    out = []
    for line in logical_lines():
        for kind, pattern in (("ops", OPS_CMD), ("step", STEP_CMD), ("registered", REGISTERED_CMD)):
            for match in pattern.finditer(line):
                module, rest = (
                    (match.group(2), match.group(3)) if kind == "step" else match.groups()
                )
                out.append((kind, module, END.split(rest, maxsplit=1)[0].strip()))
    return out


def test_the_runbook_names_every_operator_step():
    commands = runbook_commands()
    ops = {(m, text.split()[0] if m in ("rescore_jobs", "glmm_inputs") else "") for k, m, text in
           commands if k != "registered"}  # fmt: skip
    assert ops >= {
        ("provenance", ""), ("rescore_jobs", "submit"), ("rescore_jobs", "coverage"),
        ("run_report", ""), ("check_identity", ""), ("first_divergence", ""),
        ("glmm_inputs", "write"), ("glmm_inputs", "submit"), ("glmm_inputs", "collect"),
        ("assemble_s15", ""),
    }  # fmt: skip
    registered = {(m, text.split()[0]) for k, m, text in commands if k == "registered"}
    assert registered == {("rules", "dr0"), ("rescore", "merge"), ("analysis", "costs")}


@pytest.mark.parametrize(
    "kind, module, text", runbook_commands(), ids=lambda v: v if len(v) < 40 else v[:40]
)
def test_every_runbook_command_is_accepted_as_written(kind, module, text, tmp_path, capsys):
    """Each operator command parses with its script's own parse_args (and its post-parse
    checks); each registered command gets past its CLI's argparse (it then fails only on the
    synthetic paths, which do not exist)."""
    argv = expand(text, tmp_path)
    if kind in ("ops", "step"):
        mod = importlib.import_module(module)
        try:
            mod.parse_args(argv)
        except SystemExit as exc:
            pytest.fail(f"{module} {text!r} is refused: {capsys.readouterr().err} ({exc})")
        return
    mod = importlib.import_module(f"harness.q2_stage1.{module}")
    try:
        mod.main(argv)
    except SystemExit as exc:
        assert exc.code != 2, f"{module} {text!r} is refused: {capsys.readouterr().err}"
    except Exception:  # noqa: BLE001 - past argparse: the synthetic inputs do not exist
        pass
    assert not list(tmp_path.rglob("*")), "a registered CLI wrote a file"


def test_every_host_block_sources_env_sh_first():
    """Each host step works from a fresh ssh command: every bash block after the environment
    block starts by sourcing env.sh (the Mac block and the environment block excepted)."""
    source = ". /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh"
    blocks = bash_blocks()
    host = [b for b in blocks if "git archive" not in b and "s1a_env_ok" not in b]
    assert len(host) == len(blocks) - 2 and host
    for block in host:
        assert block.splitlines()[0] == source, block


def test_glmm_collect_is_its_own_block_after_the_fits():
    """sbatch returns at once, so collect never shares a block with the GLMM submit."""
    for block in bash_blocks():
        if "glmm_inputs.py collect" in block:
            assert "glmm_inputs.py submit" not in block and "sbatch" not in block


def test_rescore_submit_dry_run_needs_no_out_and_submit_needs_one(capsys):
    import rescore_jobs as RJ

    base = ["submit", "--export", "/x", "--analysis-dir", "/a", "--inputs", "/i",
            "--run-dir", "/r/1045"]  # fmt: skip
    assert RJ.parse_args([*base, "--dry-run"]).out is None
    with pytest.raises(SystemExit) as exc:
        RJ.parse_args(base)
    assert exc.value.code == 2 and "--out is required unless --dry-run" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        RJ.parse_args(["coverage", "--export", "/x", "--analysis-dir", "/a", "--run-dir", "/r",
                       "--records", "/a1.jsonl", "--plan", "/p", "--out", "/o"])  # fmt: skip


# --------------------------------------------------------------------------- env.sh


def env_block() -> str:
    blocks = [b for b in bash_blocks() if "s1a_env_ok" in b]
    assert len(blocks) == 1
    return blocks[0]


def run_bash(
    script: str, cwd: Path, path_prefix: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BASH_FUNC")}
    if path_prefix is not None:
        env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", "-c", script], cwd=cwd, env=env, capture_output=True, text=True, timeout=60
    )


def layout(tmp_path: Path) -> Path:
    stage0 = tmp_path / "stage0"
    r = stage0 / "q2-stage1"
    (r / "ops" / OPSC / "ops" / "s1a-analysis").mkdir(parents=True)
    for vm in VMS:
        (r / "runs" / vm).mkdir(parents=True)
        (r / "runs" / vm / "manifest.json").write_text("{}")
    return stage0


def test_env_block_refuses_unfilled_placeholders(tmp_path):
    stage0 = layout(tmp_path)
    script = env_block().replace(HOST_PREFIX, str(stage0))
    done = run_bash(script, tmp_path)
    assert done.returncode != 0
    assert "OPSC: not a shipped full sha: FILL-IN" in done.stderr
    assert not (stage0 / "q2-stage1" / "analysis" / "s1a-v1").exists()
    only_vm = script.replace("OPSC=FILL-IN", f"OPSC={OPSC}")
    done = run_bash(only_vm, tmp_path)
    assert done.returncode != 0 and "VMS: no run directory for FILL-IN" in done.stderr
    assert not (stage0 / "q2-stage1" / "analysis" / "s1a-v1").exists()
    outside = only_vm.replace("1051 FILL-IN", "1051 1053").replace(
        'COSTVMS="$VMS"', 'COSTVMS="1045 9999"'
    )
    done = run_bash(outside, tmp_path)
    assert done.returncode != 0 and "COSTVMS: 9999 is not in VMS" in done.stderr


def test_env_block_writes_a_usable_env_sh(tmp_path):
    stage0 = layout(tmp_path)
    script = (
        env_block()
        .replace(HOST_PREFIX, str(stage0))
        .replace("OPSC=FILL-IN", f"OPSC={OPSC}")
        .replace("1051 FILL-IN", "1051 1053")
    )
    done = run_bash(script, tmp_path)
    assert done.returncode == 0, done.stderr
    a = stage0 / "q2-stage1" / "analysis" / "s1a-v1"
    env_sh = (a / "env.sh").read_text()
    assert "FILL-IN" not in env_sh and f"OPSC={OPSC}" in env_sh and (a / "logs").is_dir()
    again = run_bash(script.replace("1051 1053", "1051"), tmp_path)  # write once
    assert "File exists" in again.stderr and (a / "env.sh").read_text() == env_sh
    fake = tmp_path / "bin"
    fake.mkdir()
    sbatch = fake / "sbatch"
    sbatch.write_text('#!/bin/sh\nfor a in "$@"; do echo "arg=$a"; done\n')
    sbatch.chmod(sbatch.stat().st_mode | stat.S_IEXEC)
    probe = (
        f". {a}/env.sh\n"
        'echo "runs=${RUNS[*]}"\necho "dr0s=${DR0S[*]}"\necho "costruns=${COSTRUNS[*]}"\n'
        "step report run_report.py --export $X --out-dir $A/report\n"
        "set -o | grep noclobber\n"
    )
    done = run_bash(probe, tmp_path, fake)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    r = stage0 / "q2-stage1"
    assert f"runs={' '.join(f'--run-dir {r}/runs/{vm}' for vm in VMS)}" in lines
    assert f"dr0s={' '.join(f'--dr0 {a}/dr0-{vm}.json' for vm in VMS)}" in lines
    assert f"costruns={' '.join(f'--run-dir {r}/runs/{vm}' for vm in VMS)}" in lines
    args = [line.removeprefix("arg=") for line in lines if line.startswith("arg=")]
    ops = r / "ops" / OPSC / "ops" / "s1a-analysis"
    assert args == [
        "--parsable", "--job-name=s1a-report", f"--output={a}/logs/%x-%j.out",
        f"{ops}/cpu-step.sbatch", f"{ops}/run_report.py",
        "--export", f"{r}/src/{FREEZE}", "--out-dir", f"{a}/report",
    ]  # fmt: skip
    assert any(line.split() == ["noclobber", "on"] for line in lines)


def test_mac_block_ships_nothing_until_the_commit_is_filled_in(tmp_path):
    blocks = [b for b in bash_blocks() if "git archive" in b]
    assert len(blocks) == 1
    script = blocks[0].replace("ssh -o BatchMode=yes fal-h100-01", "false")
    done = run_bash(script, ROOT)
    assert done.returncode != 0
