"""Synthetic stand-ins for the Holo3 and OpenCUA archives (no network).

The synthetic verified package reproduces the real leaderboard cells exactly,
so the doctor's positive controls pass on it and tamper tests can break them.
It deliberately carries fake infrastructure identifiers (a private IPv4 in a
log line and an error string, a CDP websocket URL) that must never reach a
receipt.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, field

from harness import holo3_rerun_audit as audit
from harness.remote_zip import BytesSource, RangeSource

DOMAIN_COUNTS = {
    "chrome": 46,
    "gimp": 26,
    "libreoffice_calc": 47,
    "libreoffice_impress": 47,
    "libreoffice_writer": 23,
    "multi_apps": 93,
    "os": 24,
    "thunderbird": 15,
    "vlc": 17,
    "vs_code": 23,
}
FAKE_PRIVATE_IP = "192.0.2.10"  # RFC 5737 documentation address


def task_id(i: int) -> str:
    return f"{i:08x}-0000-4000-8000-{i:012x}"


def make_universe() -> dict[str, list[str]]:
    universe: dict[str, list[str]] = {}
    i = 1
    for domain, count in DOMAIN_COUNTS.items():
        universe[domain] = [task_id(i + k) for k in range(count)]
        i += count
    return universe


def fill(total: float, n: int) -> list[float]:
    """n scores in [0, 1] summing to ``total`` (ones, one fraction, zeros)."""
    whole = int(total)
    frac = round(total - whole, 6)
    scores = [1.0] * whole
    if frac > 0:
        scores.append(frac)
    scores += [0.0] * (n - len(scores))
    assert len(scores) == n
    return scores


def zip_bytes(entries: dict[str, bytes], stored: set[str] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            method = zipfile.ZIP_STORED if stored and name in stored else zipfile.ZIP_DEFLATED
            archive.writestr(
                zipfile.ZipInfo(name, (2026, 4, 20, 0, 0, 0)), data, compress_type=method
            )
    return buffer.getvalue()


@dataclass
class World:
    universe: dict[str, list[str]]
    run1: dict[str, float | None]
    run2: dict[str, float | None]
    repaired: list[str]
    errors: list[str]
    env_prep: dict[str, list[str]]
    h: dict[str, dict[str, float | None]]
    opencua: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    drop: set[str] = field(default_factory=set)
    corrupt_sha256sums: bool = False
    tarball: bytes | None = None  # bytes of the trajectory tarball member
    config_manifest: str = ""  # what the stubbed config loader reports

    @property
    def tasks(self) -> list[str]:
        return [t for ts in self.universe.values() for t in ts]

    @property
    def domain_of(self) -> dict[str, str]:
        return {t: d for d, ts in self.universe.items() for t in ts}


def build_world() -> World:
    universe = make_universe()
    chrome = universe["chrome"]
    errors = [chrome[0], chrome[1]]  # setup failure, evaluator crash
    repaired = [universe["gimp"][-1], universe["libreoffice_impress"][-1]]
    runs: dict[str, dict[str, float | None]] = {}
    for run in ("run1", "run2"):
        cells = audit.HOLO3_LEADERBOARD[run]["cells"]
        scores: dict[str, float | None] = {}
        for domain, tasks in universe.items():
            total, n = cells[domain].split("/")
            usable = [t for t in tasks if t not in errors]
            assert len(usable) == int(n)
            # repaired tasks get 0 in gimp and 1 in impress, as in the real data
            values = fill(float(total), int(n))
            if domain == "gimp":
                values = sorted(values, reverse=True)
            for t, v in zip(usable, values, strict=True):
                scores[t] = v
        for t in errors:
            scores[t] = None
        # Rounded domain cells need not add up to the rounded total (run2's
        # cells sum to 280.56, its total is 280.55); nudge fractional scores
        # down by 0.004 each until the total rounds right too.
        target = audit.HOLO3_LEADERBOARD[run]["total"]
        fractional = [t for t, v in scores.items() if v is not None and 0 < v < 1]
        while audit.cell(sum(v for v in scores.values() if v is not None), 359) != target:
            scores[fractional.pop()] -= 0.004  # type: ignore[operator]
        runs[run] = scores
    env_prep = {
        "run1": [universe["os"][0][:8], universe["vlc"][0][:8]],
        "repair": [],
        "run2": [universe["thunderbird"][0][:8]],
    }
    h = {}
    for k, tag in enumerate(audit.H_RUN_TAGS):
        rewards: dict[str, float | None] = {t: runs["run1"][t] for t in runs["run1"]}
        rewards[errors[1]] = None
        rewards[universe["vlc"][-1]] = None
        if k == 1:
            rewards.pop(errors[0])
        for t in universe["libreoffice_calc"][k * 3 : k * 3 + 3]:  # small rerun noise
            rewards[t] = 1.0 - (rewards[t] or 0.0)
        h[tag] = rewards
    world = World(universe, runs["run1"], runs["run2"], repaired, errors, env_prep, h)
    world.opencua = build_opencua(universe)
    return world


def build_opencua(universe: dict[str, list[str]]) -> dict[str, dict[str, dict[str, float]]]:
    tasks = [t for ts in universe.values() for t in ts]
    out: dict[str, dict[str, dict[str, float]]] = {}
    for key, rows in audit.OPENCUA_LEADERBOARD.items():
        turns: dict[str, dict[str, float]] = {}
        for k, text in enumerate(rows.values(), 1):
            total, n = text.split("/")
            chosen = tasks[: int(n)]
            turns[f"turn_{k}"] = dict(zip(chosen, fill(float(total), int(n)), strict=True))
        out[key] = turns
    return out


TRAJECTORY_TAGS = {"run1": "1111-4111", "repair": "3333-4333", "run2": "2222-4222"}


def trajectory_id(task: str, run: str) -> str:
    """Synthetic trajectory id of one run's episode of a task (distinct per run)."""
    return task.replace("0000-4000", TRAJECTORY_TAGS[run])


def _status(
    task: str,
    score: float | None,
    *,
    error: str | None,
    elapsed: float = 100.0,
    run: str = "run1",
) -> bytes:
    if score is None:
        record = {
            "task_id": task,
            "status": "error",
            "error": error,
            "timestamp": "2026-04-20T13:00:00",
        }
    else:
        record = {
            "task_id": task,
            "instruction": "synthetic",
            "status": "completed",
            "started_at": "2026-04-20T13:00:00",
            "trajectory_id": trajectory_id(task, run),
            "score": str(score),
            "elapsed_s": str(elapsed),
            "agp_message": f"Completed (trajectory={task})",
            "agp_actions": "['DONE']",
        }
    return json.dumps(record).encode()


def verified_zip(world: World) -> bytes:
    root = audit.VERIFIED_ROOT
    agent = audit.HOLO3_PREFIX
    files: dict[str, bytes] = {
        "evaluation_examples/test_nogdrive.json": json.dumps(world.universe).encode(),
        "evaluation_examples/test_hcompany_run1_repair.json": json.dumps(
            {
                "chrome": world.errors,
                "gimp": world.repaired[:1],
                "libreoffice_impress": world.repaired[1:],
            }
        ).encode(),
        audit.TARBALL_RELPATH: world.tarball or b"not really a tarball",
    }
    cdp_error = (
        "Setup step 3 failed: _chrome_open_tabs_setup - BrowserType.connect_over_cdp: Timeout "
        f"180000ms exceeded. ws://{FAKE_PRIVATE_IP}:9222/devtools/browser/abc"
    )
    error_text = {world.errors[0]: cdp_error, world.errors[1]: "month must be in 1..12"}
    for run, scores in (("run1", world.run1), ("run2", world.run2)):
        run_dir = audit.RUN_DIRS[run]
        for domain, tasks in world.universe.items():
            for t in tasks:
                if run == "run1" and t in world.repaired:
                    continue
                score = scores[t]
                base = f"{run_dir}/pyautogui/screenshot/{agent}/{domain}/{t}"
                elapsed = 50.0 + (int(t[:8], 16) * (7 if run == "run1" else 11)) % 100
                files[f"{base}/status.json"] = _status(
                    t, score, error=error_text.get(t), elapsed=elapsed, run=run
                )
                if score is not None:
                    files[f"{base}/result.txt"] = f"{score}\n".encode()
    repair_dir = audit.RUN_DIRS["repair"]
    for t in world.repaired + world.errors:
        domain = world.domain_of[t]
        base = f"{repair_dir}/pyautogui/screenshot/{agent}/{domain}/{t}"
        score = world.run1[t] if t in world.repaired else None
        files[f"{base}/status.json"] = _status(t, score, error=error_text.get(t), run="repair")
        if score is not None:
            files[f"{base}/result.txt"] = f"{score}\n".encode()
    for run, prefixes in world.env_prep.items():
        lines = [
            f"2026-04-20 13:00:00,000 surferH.benchmark_retry ERROR [VM-1][{p}] Env prep failed "
            f"(env 1/2, freshen 1/3): Flask not available after 300s at http://{FAKE_PRIVATE_IP}:5000"
            for p in prefixes
        ]
        lines.append("2026-04-20 13:00:01,000 other.logger INFO account 123456789012 ignored")
        files[f"{audit.RUN_DIRS[run]}/benchmark.log"] = ("\n".join(lines) + "\n").encode()
    for run, name in (("run1", "merged_summary_with_repair.json"), ("run2", "final_summary.json")):
        scores = world.run1 if run == "run1" else world.run2
        scored = [v for v in scores.values() if v is not None]
        summary = {
            "total_tasks": len(scores),
            "scored": len(scored),
            "passed": sum(1 for v in scored if v > 0),
            "errors": sum(1 for v in scores.values() if v is None),
            "score": sum(scored) / len(scored),
            "error_tasks": [{"task_id": world.errors[0], "error": cdp_error}],
        }
        files[f"{audit.RUN_DIRS[run]}/{name}"] = json.dumps(summary).encode()
    sums = "".join(
        f"{hashlib.sha256(data).hexdigest()}  ./{rel}\n" for rel, data in sorted(files.items())
    )
    if world.corrupt_sha256sums:
        sums = sums.replace(sums[:8], "0" * 8, 1)
    files["SHA256SUMS"] = sums.encode()
    entries = {root + rel: data for rel, data in files.items() if rel not in world.drop}
    return zip_bytes(entries, stored={root + audit.TARBALL_RELPATH})


def internal_zip(world: World) -> bytes:
    outer: dict[str, bytes] = {
        audit.INTERNAL_ROOT + "README.md": b"synthetic",
        audit.INTERNAL_ROOT + "SHA256SUMS": b"",
    }
    nested_names = []
    for tag, rewards in world.h.items():
        root = f"trajectories/results_20260416_{tag}/"
        inner: dict[str, bytes] = {}
        for t, reward in rewards.items():
            domain = world.domain_of[t]
            inner[f"{root}{domain}/{t}/task_summary.json"] = json.dumps(
                {"trajectory_id": t, "reward": reward}
            ).encode()
            inner[f"{root}{domain}/{t}/actions.json"] = json.dumps(
                [{"image": "images/0000.png"}, {"action": {"tool_name": "answer"}}] * 3
            ).encode()
            inner[f"{root}{domain}/{t}/images/0000.png"] = b"\x89PNG" + t.encode()
        if tag == audit.H_RUN_TAGS[2]:
            inner[f"{root}multi_apps/{world.universe['multi_apps'][0]}.err"] = b"trace"
        name = (
            f"{audit.INTERNAL_ROOT}h_company_internal_runs/trajectories_results_20260416_{tag}.zip"
        )
        outer[name] = zip_bytes(inner)
        nested_names.append(name)
    return zip_bytes(outer, stored=set(nested_names))


def opencua_zip(world: World, key: str) -> bytes:
    entries: dict[str, bytes] = {}
    for turn, scores in world.opencua[key].items():
        for t, score in scores.items():
            base = f"{turn}/{world.domain_of[t]}/{t}"
            entries[f"{base}/result.txt"] = f"{score}\n".encode()
            entries[f"{base}/traj.jsonl"] = b"{}\n"
    return zip_bytes(entries)


def opener(world: World):
    """Map ArchiveSpec -> in-memory source, building each archive once."""
    cache: dict[str, bytes] = {}

    def open_archive(spec: audit.ArchiveSpec) -> RangeSource:
        if spec.key not in cache:
            if spec.key == audit.VERIFIED_ARCHIVE.key:
                cache[spec.key] = verified_zip(world)
            elif spec.key == audit.INTERNAL_ARCHIVE.key:
                cache[spec.key] = internal_zip(world)
            else:
                cache[spec.key] = opencua_zip(world, spec.key)
        return BytesSource(cache[spec.key], identity={"kind": "synthetic", "key": spec.key})

    return open_archive


def leaderboard_rows() -> dict[int, dict[str, str]]:
    rows: dict[int, dict[str, str]] = {1: {"A": "Model", "K": "Success rate"}}
    for spec in audit.HOLO3_LEADERBOARD.values():
        row = {"A": "Holo3-35B-A3B", "F": "100", "L": spec["total"]}
        total, n = spec["total"].split("/")
        row["K"] = f"{100 * float(total) / int(n):.2f}"
        for column, domain in audit.LEADERBOARD_DOMAIN_COLUMNS.items():
            row[column] = spec["cells"][domain]
        rows[spec["row"]] = row
    for key, expected in audit.OPENCUA_LEADERBOARD.items():
        _, size, steps = key.split("-")
        for number, total in expected.items():
            rows[number] = {"A": audit.OPENCUA_MODEL_NAMES[size], "F": steps, "L": total, "K": "25"}
    rows[200] = {"A": "Some Agent", "F": "100", "K": "90.0"}
    return rows


def run1_only_tasks(world: World) -> list[str]:
    return [
        t
        for t in world.tasks
        if world.run1[t] is not None
        and world.run2[t] is not None
        and world.run1[t] >= 0.5 > world.run2[t]  # type: ignore[operator]
    ]


def configs(world: World) -> dict[str, dict]:
    """Task configs: mostly offline or web, with some live and clock evaluators.

    Half of the run1-only tasks get a live expected value (class L, plan's
    narrow L too), so rule (d) has something to find; a few other tasks get a
    clock rule or a result-side live getter (class L, not narrow L).
    """
    live = set(run1_only_tasks(world)[::2])
    out = {}
    for i, t in enumerate(world.tasks):
        url = "https://www.example.org/page" if i % 7 == 0 else "http://localhost:8080/x"
        evaluator: dict = {"func": "f"}
        if t in live:
            evaluator = {
                "func": "check",
                "expected": {"type": "info_from_website", "url": "https://www.example.org/live"},
            }
        elif i % 13 == 0:
            evaluator = {
                "func": "check",
                "expected": {"type": "rule", "rules": {"relativeTime": {"from": "today"}}},
            }
        elif i % 17 == 0:
            evaluator = {"func": "check", "result": {"type": "active_tab_info"}}
        out[t] = {"config": [{"type": "open", "parameters": {"url": url}}], "evaluator": evaluator}
    return out
