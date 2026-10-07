"""Mutation campaign driver: blind spec -> operator -> mutant -> GUI-faithful save -> verdict.

This module joins the three Q2 branches. Each subcommand runs in one fixed
place, and only reads what that place may read:

``targets`` (metric image, ``/opt/venv-lock``)
    From the harness control jobs of one split (``controls make-jobs``), pick
    every gold file an operator family can mutate. It reads the task config
    only to pair result files with gold files (as ``make-jobs`` does) and to
    skip files a postconfig conversion derives. Blind specs are validated and
    copied to JSON, because the LibreOffice image has no PyYAML.
``build`` (LO-VM image, its Python 3.10 with pyuno)
    Per target: the base (LibreOffice-save of the gold) and the saved initial
    file through ``uno_apply.py``; planning with the blind spec only against
    the base; application of each recipe to the raw gold (``--apply-to gold``,
    the default: mutant and null mutant are each one LibreOffice round trip
    from the gold, and the null mutant is the base) or to the base
    (``--apply-to base``: the null mutant is the base saved once more);
    purity against the null mutant; deduplication. Writes ``mutations.jsonl`` (strict
    ``MutationResult`` rows), ``admission.jsonl``, the mutant files in the
    shared layout ``files/<mutant_id>/<VM path>``, and ``scoring-jobs.jsonl``
    (admitted mutants plus one null job per target). The operators never see
    the task config, a checker or a verdict.
``reach.sh`` (LO-VM image)
    The harness's GUI-faithful save stage on ``scoring-jobs.jsonl``.
``merge`` (metric image)
    ``controls.merge_lo`` keeping mutant ids, with container paths remapped.
``score.sh`` (metric image)
    The pinned ``DesktopEnv.evaluate()`` under both venvs -> ``VerdictRow`` JSONL.
``recheck`` (metric image)
    Operator purity re-run on the saved mutant against the saved null mutant
    (admission rule and S3/K5 of the preregistration).
``k2-sample`` (anywhere)
    The seeded K2 fidelity sample, drawn from ``scoring-jobs.jsonl`` alone
    (no verdict exists or is read), stratified over task domains.
``report`` (anywhere)
    Joins labels, admission, post-save purity and verdicts into one outcome
    per mutant and the exploratory tables of a development run.
``export`` (anywhere)
    The releasable evidence of one run: redacted recipes (long document text
    replaced by its digest), outcomes, verdict rows and summaries. Mutant
    files never leave the host.

Only the development split runs before the preregistration freeze; any other
split needs the frozen ledger row of ``q2-evaluator-mutation-v1`` whose
digest matches the preregistration file in the staged tree.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

EXPERIMENT_ID = "q2-evaluator-mutation-v1"
PREREG_PATH = "program/preregistrations/q2-evaluator-mutation-v1.md"
LEDGER_PATH = "program/preregistrations/ledger.jsonl"
SPLITS_PATH = "program/evidence/q2-mutation/splits.json"
SPECS_DIR = "program/evidence/q2-mutation/specs"
SANITIZED_MANIFEST = "program/evidence/q2-mutation/sanitized-tasks.manifest.json"
PROBE_TOUCHED = "program/evidence/q2-mutation/harness/probe_touched.json"
FILE_CACHE_RECEIPTS = "program/evidence/q2-mutation/harness/file-cache-receipts.tsv"
DEV_SPLIT = "dev"
# Container mounts of the external inputs (q2-mutation-cpu.sbatch, Q2M_INPUTS).
INPUT_OSWORLD = "OSWorld"
INPUT_FILE_CACHE = "file_cache_1e112283/files"
INPUT_VM_BASELINE = "vm-baseline"
# The OSWorld parts a scoring run executes or reads: the pinned evaluate() and
# metric code, and the task configs.
OSWORLD_TREES = ("desktop_env", "evaluation_examples")

OFFICE_SUFFIXES = {".xlsx": "xlsx", ".docx": "docx", ".pptx": "pptx"}
# Files the save stage must write before scoring (reachability.LO_SAVE_EXTENSIONS).
OFFICE_SAVE_SUFFIXES = frozenset({".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"})
# Plain-text end states the text/config operators edit by splicing characters.
TEXT_SUFFIXES = frozenset(
    {
        ".txt",
        ".md",
        ".csv",
        ".json",
        ".jsonc",
        ".ini",
        ".cfg",
        ".conf",
        ".desktop",
        ".toml",
        ".yaml",
        ".yml",
    }
)
# Operators that edit a unit "outside" the task delta (F class). When the task
# starts without the target file, every unit is task output and no outside
# site exists, so these operators are not planned for that target.
OUTSIDE_TARGET = "outside"

# Scoping probes (2026-10-06, before the preregistration) mapped to the
# operators that make the same kind of edit. A (task, operator) cell is
# probe-touched when the task carries the probe and the operator matches one
# of its patterns; such cells are exploratory (preregistration section 12).
# An unrelated-edit probe (a typo in body text or a table, an edited cell) on a
# task predicts how its checker treats every unrequested change, so it touches
# every extra-change operator of the task, not only the one that types the
# same kind of edit; a revert probe touches every violation operator. Probes of
# the byte-level kind (zip repacks, split runs) map to no document_model
# operator; controls and the headless gold round trip map to none either (P1
# handles the latter separately).
_TEXT_VIOLATIONS = (
    "docx.viol.text_edit",
    "pptx.viol.text_edit",
    "xlsx.viol.value_perturb",
    "text.viol.line_edit",
)
_UNRELATED_EDITS = ("*.extra.*",)
PROBE_OPERATOR_MAP: dict[str, tuple[str, ...]] = {
    "controls:gold+do_nothing(raw)": (),
    "lo_rt:gold_headless_save(ubuntu .13)": (),
    "equiv:E-META": ("*.eq.doc_property",),
    "equiv:E-ZIP": (),
    "runsplit:E-RUNSPLIT-TOUCHED": (),
    "runsplit:E-RUNSPLIT-UNTOUCHED": (),
    "mutants:F-TYPO": _TEXT_VIOLATIONS + _UNRELATED_EDITS,
    "mutants_v2:F-TYPO-BODY": _TEXT_VIOLATIONS + _UNRELATED_EDITS,
    "mutants_v2:F-TYPO-TABLE": ("pptx.viol.table_cell_text",) + _UNRELATED_EDITS,
    "mutants_v2:F-CELL": ("xlsx.viol.value_perturb",) + _UNRELATED_EDITS,
    "mutants:R-REVERT": ("*.viol.*",),
    "mutants_v2:R-REVERT": ("*.viol.*",),
}
# Operators designed after a scoping probe showed what they test (catalog
# provenance "probe_informed"). Their cells are exploratory on every task, as
# if a probe had touched them (preregistration section 12); a test keeps this
# set equal to the catalog's.
PROBE_INFORMED_OPERATORS = frozenset(
    {"docx.extra.edit_unrelated_table_cell", "pptx.viol.table_cell_text"}
)

# Code whose bytes the preregistration pins (README and SKILL files excluded so
# a documentation fix does not move the pin).
CODE_TREE_ROOTS = (
    "harness/q2_mutation",
    "infra/q2-mutation",
    "infra/slurm/host-single-node/q2-mutation-cpu.sbatch",
    "scripts/q2_mutation_export_tasks.py",
    "scripts/q2_mutation_operators.py",
)


DOC_FILES = frozenset({"README.md", "SKILL.md"})


class CampaignError(RuntimeError):
    """A campaign input is inconsistent; nothing is written past this point."""


# --- small helpers ------------------------------------------------------------


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> int:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_json(path: str | Path, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def path_key(vm_path: str) -> str:
    return hashlib.sha256(vm_path.encode("utf-8")).hexdigest()[:8]


def target_id(task_id: str, vm_path: str) -> str:
    return f"{task_id}__{path_key(vm_path)}"


def null_id(task_id: str, vm_path: str) -> str:
    """Id of the null mutant (base saved once more, no edit) of one target."""
    return f"{task_id}__null__{path_key(vm_path)}"


def file_family(vm_path: str) -> str | None:
    suffix = posixpath.splitext(vm_path)[1].lower()
    if suffix in OFFICE_SUFFIXES:
        return OFFICE_SUFFIXES[suffix]
    if suffix in TEXT_SUFFIXES:
        from harness.q2_mutation.operators._snapshot import family_of

        return family_of(vm_path)
    return None


def checker_family(funcs: Sequence[str]) -> str:
    """A checker family is a metric function; several distinct ones are joined by '+'."""
    return "+".join(sorted(set(funcs)))


# --- split guard and pins -------------------------------------------------------


LEDGER_GENESIS = "0" * 64


def ledger_rows(ledger: Path) -> list[dict[str, Any]]:
    """Ledger rows after checking the hash chain end to end (``scripts/preregister.py``)."""
    rows: list[dict[str, Any]] = []
    previous = LEDGER_GENESIS
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        body = {key: value for key, value in row.items() if key != "hash"}
        payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        if row.get("previous_hash") != previous:
            raise CampaignError(f"ledger line {number}: broken previous_hash link")
        if row.get("hash") != hashlib.sha256(payload).hexdigest():
            raise CampaignError(f"ledger line {number}: row hash does not match its body")
        rows.append(row)
        previous = str(row["hash"])
    return rows


def frozen_ledger_row(src: Path) -> dict[str, Any] | None:
    """The ledger row of this experiment if the staged preregistration matches it."""
    ledger = src / LEDGER_PATH
    prereg = src / PREREG_PATH
    if not ledger.is_file() or not prereg.is_file():
        return None
    for row in ledger_rows(ledger):
        if row.get("experiment_id") == EXPERIMENT_ID:
            if row.get("path") != PREREG_PATH or row.get("sha256") != sha256_file(prereg):
                raise CampaignError("the staged preregistration differs from its frozen digest")
            return row
    return None


def require_split_allowed(split: str, src: Path) -> dict[str, Any] | None:
    """Refuse every split but dev unless the preregistration is frozen and intact."""
    if split == DEV_SPLIT:
        return None
    row = frozen_ledger_row(src)
    if row is None:
        raise CampaignError(f"split {split!r} runs only after {EXPERIMENT_ID} is frozen")
    if os.environ.get("Q2M_PREREG_FROZEN") != EXPERIMENT_ID:
        raise CampaignError(f"set Q2M_PREREG_FROZEN={EXPERIMENT_ID} to run split {split!r}")
    check_pins(src)
    return row


# Digests the preregistration's machine-readable pins block must match. Image
# IDs in the block are checked by the submit scripts, which know them.
PINNED_KEYS = (
    "code_tree_sha256",
    "operator_catalog_sha256",
    "operator_catalog_version",
    "operators",
    "spec_set_sha256",
    "specs",
    "sanitized_manifest_sha256",
    "splits_sha256",
    "schema_sha256",
    "probe_touched_sha256",
    "file_cache_receipts_sha256",
)
# Digests of the external inputs, checked against the mounted /inputs tree in
# every container stage that reads them (``campaign guard``).
INPUT_PIN_KEYS = ("osworld_tree_sha256", "vm_baseline_tree_sha256")
_JSON_FENCE = re.compile(r"^```json\n(.*?)^```$", re.DOTALL | re.MULTILINE)


def prereg_pins(text: str) -> dict[str, Any]:
    """The one fenced JSON block of the preregistration that carries ``q2m_pins``."""
    blocks = []
    for body in _JSON_FENCE.findall(text):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "q2m_pins" in data:
            blocks.append(data)
    if len(blocks) != 1:
        raise CampaignError(
            f"the preregistration needs exactly one q2m_pins block, found {len(blocks)}"
        )
    return blocks[0]


def check_pins(src: Path) -> dict[str, Any]:
    """Refuse a staged tree whose code, catalog, specs or splits differ from the pins."""
    declared = prereg_pins((src / PREREG_PATH).read_text(encoding="utf-8"))
    actual = pins(src)
    wrong = sorted(key for key in PINNED_KEYS if declared.get(key) != actual[key])
    if wrong:
        raise CampaignError(f"the staged tree differs from the preregistration pins: {wrong}")
    return declared


def _tree_files(root: Path, entry: str) -> list[Path]:
    path = root / entry
    if path.is_file():
        return [path]
    return sorted(
        p
        for p in path.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
        and p.name not in DOC_FILES
    )


def code_tree_sha256(root: Path) -> str:
    """SHA-256 over (relative path, file SHA-256) of every pinned code file."""
    digest = hashlib.sha256()
    for entry in CODE_TREE_ROOTS:
        for path in _tree_files(root, entry):
            digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            digest.update(sha256_file(path).encode("ascii") + b"\n")
    return digest.hexdigest()


def spec_set_sha256(root: Path) -> str:
    """SHA-256 over the sorted lines '<file sha256>  <name>' of every spec YAML."""
    lines = [
        f"{sha256_file(path)}  {path.name}" for path in sorted((root / SPECS_DIR).glob("*.yaml"))
    ]
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def pins(root: Path) -> dict[str, Any]:
    """Every digest the preregistration names, computed from a source tree."""
    from harness.q2_mutation.operators import catalog

    cat = catalog()
    specs = sorted((root / SPECS_DIR).glob("*.yaml"))
    return {
        "experiment_id": EXPERIMENT_ID,
        "code_tree_sha256": code_tree_sha256(root),
        "operator_catalog_sha256": cat["catalog_sha256"],
        "operator_catalog_version": cat["catalog_version"],
        "operators": cat["total"],
        "spec_set_sha256": spec_set_sha256(root),
        "specs": len(specs),
        "sanitized_manifest_sha256": sha256_file(root / SANITIZED_MANIFEST),
        "splits_sha256": sha256_file(root / SPLITS_PATH),
        "schema_sha256": sha256_file(root / "harness/q2_mutation/schema.py"),
        "probe_touched_sha256": sha256_file(root / PROBE_TOUCHED),
        "file_cache_receipts_sha256": sha256_file(root / FILE_CACHE_RECEIPTS),
    }


def tree_sha256(root: Path, entries: Sequence[str] = ("",)) -> str:
    """SHA-256 over (relative path, file SHA-256) of every file under ``entries``.

    ``__pycache__`` directories, ``.pyc`` files and ``.git`` are skipped.
    """
    digest = hashlib.sha256()
    for entry in entries:
        base = root / entry if entry else root
        for path in sorted(base.rglob("*")):
            parts = path.relative_to(root).parts
            if not path.is_file() or "__pycache__" in parts or ".git" in parts:
                continue
            if path.suffix == ".pyc":
                continue
            digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            digest.update(sha256_file(path).encode("ascii") + b"\n")
    return digest.hexdigest()


def input_digests(inputs: Path) -> dict[str, str]:
    """Digests of the mounted OSWorld tree and VM baseline (``INPUT_PIN_KEYS``)."""
    return {
        "osworld_tree_sha256": tree_sha256(inputs / INPUT_OSWORLD, OSWORLD_TREES),
        "vm_baseline_tree_sha256": tree_sha256(inputs / INPUT_VM_BASELINE),
    }


def check_file_cache(src: Path, files: Path) -> int:
    """Re-hash every file-cache file against the committed receipts; return the count."""
    count = 0
    for line in (src / FILE_CACHE_RECEIPTS).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rel, size, digest = line.split("\t")[:3]
        path = files / rel
        if not path.is_file() or path.stat().st_size != int(size) or sha256_file(path) != digest:
            raise CampaignError(f"file cache {rel} differs from its receipt")
        count += 1
    return count


def check_inputs(src: Path, inputs: Path) -> dict[str, Any]:
    """Refuse mounted inputs whose OSWorld tree, VM baseline or file cache differ from the pins."""
    declared = prereg_pins((src / PREREG_PATH).read_text(encoding="utf-8"))
    actual = input_digests(inputs)
    wrong = sorted(key for key in INPUT_PIN_KEYS if declared.get(key) != actual[key])
    if wrong:
        raise CampaignError(f"the mounted inputs differ from the preregistration pins: {wrong}")
    files = check_file_cache(src, inputs / INPUT_FILE_CACHE)
    return {**actual, "file_cache_files_verified": files}


# --- stage 1: targets (metric image) --------------------------------------------


def derived_paths(raw_task: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    """(directory, stem, extension) of every file a postconfig conversion writes."""
    from harness.q2_mutation.reachability import derived_outputs, plan_postconfig

    steps = plan_postconfig(raw_task.get("evaluator", {}).get("postconfig", []))
    out: list[tuple[str, str, str]] = []
    for step in steps:
        if step.kind == "convert":
            out.extend(derived_outputs(step.argv))
    return out


def is_derived(vm_path: str, derived: Sequence[tuple[str, str, str]]) -> bool:
    directory, name = posixpath.split(vm_path)
    for out_dir, stem, ext in derived:
        same_dir = directory == out_dir and name.endswith("." + ext)
        if same_dir and (name == f"{stem}.{ext}" or name.startswith(f"{stem}-")):
            return True
    return False


def select_targets(
    jobs: Sequence[Mapping[str, Any]],
    task_ids: Sequence[str],
    raw_tasks: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mutation targets of one split from the harness control jobs.

    A target is one gold file of a task with a complete gold whose suffix an
    operator family handles and which no postconfig conversion derives. The
    initial file at the same VM path, if any, gives the task delta; the other
    gold files of the task are the target's context (they stay at gold).
    """
    by_task: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for job in jobs:
        by_task[str(job["task_id"])][str(job["kind"])] = job
    targets: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for task_id in sorted(task_ids):
        kinds = by_task.get(task_id, {})
        gold = kinds.get("gold")
        if gold is None:
            skipped.append({"task_id": task_id, "vm_path": None, "reason": "no complete gold"})
            continue
        initial_files = dict((kinds.get("initial") or {}).get("files", {}))
        derived = derived_paths(raw_tasks[task_id])
        context = {str(vm): str(local) for vm, local in sorted(gold["files"].items())}
        for vm_path, local in sorted(gold["files"].items()):
            family = file_family(vm_path)
            reason = None
            if family is None:
                reason = "no operator family for this file type"
            elif is_derived(vm_path, derived):
                reason = "derived by a postconfig conversion (mutate its source instead)"
            if reason:
                skipped.append({"task_id": task_id, "vm_path": vm_path, "reason": reason})
                continue
            initial = initial_files.get(vm_path)
            targets.append(
                {
                    "target_id": target_id(task_id, vm_path),
                    "null_id": null_id(task_id, vm_path),
                    "task_id": task_id,
                    "family": family,
                    "vm_path": vm_path,
                    "gold": str(local),
                    "gold_sha256": sha256_file(local),
                    "initial": str(initial) if initial else None,
                    "initial_sha256": sha256_file(initial) if initial else None,
                    "context_files": context,
                }
            )
    return targets, skipped


def load_spec_yaml(path: Path) -> dict[str, Any]:
    """Validate a blind spec and return its canonical dictionary."""
    import yaml

    from harness.q2_mutation.schema import RequirementSpec

    spec = RequirementSpec.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))
    if spec.task_id != path.stem:
        raise CampaignError(f"{path.name}: task_id {spec.task_id} does not match the file name")
    return spec.to_dict()


def cmd_targets(args: argparse.Namespace) -> int:
    from harness.q2_mutation.offline_eval import load_task

    src = Path(args.src)
    splits = json.loads((src / SPLITS_PATH).read_text(encoding="utf-8"))
    task_ids = list(splits[args.split])
    raw_tasks = {task_id: load_task(Path(args.osworld), task_id) for task_id in task_ids}
    jobs = read_jsonl(args.jobs)
    targets, skipped = select_targets(jobs, task_ids, raw_tasks)
    counts = {
        "split": args.split,
        "tasks": len(task_ids),
        "tasks_with_target": len({t["task_id"] for t in targets}),
        "targets": len(targets),
        "targets_by_family": dict(Counter(t["family"] for t in targets)),
        "targets_without_initial": sum(1 for t in targets if t["initial"] is None),
        "skipped": dict(Counter(s["reason"] for s in skipped)),
    }
    if args.count_only:
        # Design counts only (no files, no specs): allowed for every split.
        print(json.dumps(counts, sort_keys=True))
        if args.out:
            write_json(Path(args.out) / f"target-counts-{args.split}.json", counts)
        return 0
    require_split_allowed(args.split, src)
    out = Path(args.out)
    specs_out = out / "specs"
    for task_id in sorted({t["task_id"] for t in targets}):
        spec = load_spec_yaml(src / SPECS_DIR / f"{task_id}.yaml")
        write_json(specs_out / f"{task_id}.json", spec)
    for target in targets:
        yaml_path = src / SPECS_DIR / f"{target['task_id']}.yaml"
        # Relative to targets.jsonl: the next stage mounts this directory elsewhere.
        target["spec_json"] = f"specs/{target['task_id']}.json"
        target["spec_yaml_sha256"] = sha256_file(yaml_path)
    write_jsonl(out / "targets.jsonl", targets)
    write_json(out / "targets.report.json", {**counts, "skipped_detail": skipped})
    print(json.dumps(counts, sort_keys=True))
    return 0


# --- stage 2: build (LO-VM image) -----------------------------------------------


def run_uno(
    root: Path,
    rows: Sequence[Mapping[str, Any]],
    name: str,
    *,
    soffice: str,
    profile_template: str | None,
    timeout: int,
    shards: int = 1,
    display_base: int = 120,
) -> dict[str, dict[str, Any]]:
    """Run ``uno_apply.py`` over ``rows`` in ``shards`` parallel offices; log by mutant id."""
    if not rows:
        return {}
    applier = Path(__file__).resolve().parent / "operators" / "uno_apply.py"
    shards = max(1, min(shards, len(rows)))
    procs = []
    logs = []
    for index in range(shards):
        part = [row for i, row in enumerate(rows) if i % shards == index]
        manifest = root / "uno" / f"{name}-{index}-manifest.jsonl"
        log = root / "uno" / f"{name}-{index}-log.jsonl"
        write_jsonl(manifest, part)
        if log.exists():
            log.unlink()
        cmd = [
            sys.executable,
            str(applier),
            "--manifest",
            str(manifest),
            "--root",
            str(root),
            "--log",
            str(log),
            "--soffice",
            soffice,
            "--display",
            f":{display_base + index}",
            "--timeout",
            str(timeout),
        ]
        if profile_template:
            cmd += ["--profile-template", profile_template]
        procs.append(subprocess.Popen(cmd))
        logs.append(log)
    started = time.time()
    codes = [proc.wait() for proc in procs]
    seconds = time.time() - started
    print(f"uno {name}: {len(rows)} rows, {shards} shards, {seconds:.1f}s", flush=True)
    if any(codes):
        raise CampaignError(f"uno_apply {name} exited {codes}")
    entries: dict[str, dict[str, Any]] = {}
    for log in logs:
        for entry in read_jsonl(log):
            entries[entry["mutant_id"]] = entry
    return entries


def _rel(*parts: str) -> str:
    return posixpath.join(*parts)


def mutant_file_rel(mutant_id: str, vm_path: str) -> str:
    """The shared layout: ``files/<mutant_id>/<VM path without the leading slash>``."""
    return _rel("files", mutant_id, vm_path.lstrip("/"))


def prepare_rows(target: Mapping[str, Any]) -> list[dict[str, Any]]:
    """uno_apply rows that save the gold (base) and the initial file once."""
    key = target["target_id"]
    name = posixpath.basename(target["vm_path"])
    rows = [
        {
            "mutant_id": f"{key}-base",
            "family": target["family"],
            "input": target["gold"],
            "input_sha256": target["gold_sha256"],
            "output": _rel("prep", key, "base", name),
            "steps": [],
        }
    ]
    if target["initial"]:
        rows.append(
            {
                "mutant_id": f"{key}-initial",
                "family": target["family"],
                "input": target["initial"],
                "input_sha256": target["initial_sha256"],
                "output": _rel("prep", key, "initial", name),
                "steps": [],
            }
        )
    return rows


def wanted_operators(family: str, has_initial: bool) -> list[str]:
    from harness.q2_mutation.operators import for_family

    return [op.name for op in for_family(family) if has_initial or op.target != OUTSIDE_TARGET]


def cmd_build(args: argparse.Namespace) -> int:
    from harness.q2_mutation.operators._base import OFFICE_FAMILIES
    from harness.q2_mutation.operators.apply_text import TextApplyError, apply_file
    from harness.q2_mutation.operators.pipeline import (
        dedupe_admitted,
        is_admitted,
        make_context,
        plan_task,
        verify,
    )
    from harness.q2_mutation.schema import MutationResult, RequirementSpec

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    targets = read_jsonl(args.targets)
    for target in targets:
        target["spec_json"] = str(Path(args.targets).parent / target["spec_json"])
    uno = {
        "soffice": args.soffice,
        "profile_template": args.profile_template,
        "timeout": args.timeout,
        "shards": args.shards,
    }
    built: list[dict[str, Any]] = []
    for target in targets:
        if sha256_file(target["gold"]) != target["gold_sha256"]:
            raise CampaignError(f"{target['target_id']}: gold file does not match its digest")
        if target["initial"] and sha256_file(target["initial"]) != target["initial_sha256"]:
            raise CampaignError(f"{target['target_id']}: initial file does not match its digest")

    office = [t for t in targets if t["family"] in OFFICE_FAMILIES]
    text = [t for t in targets if t["family"] not in OFFICE_FAMILIES]
    prep = run_uno(out, [row for t in office for row in prepare_rows(t)], "prepare", **uno)
    null_rows = []
    nulls: dict[str, dict[str, Any]] = {}
    for target in office:
        key = target["target_id"]
        name = posixpath.basename(target["vm_path"])
        if prep.get(f"{key}-base", {}).get("status") != "ok":
            continue
        if args.apply_to == "gold":
            # Recipes are applied to the raw gold, so a mutant is one LibreOffice
            # round trip away from the gold, as the base is: the base is the null.
            null = out / mutant_file_rel(target["null_id"], target["vm_path"])
            null.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out / "prep" / key / "base" / name, null)
            nulls[target["null_id"]] = {"status": "ok", "null": "base"}
            continue
        null_rows.append(
            {
                "mutant_id": target["null_id"],
                "family": target["family"],
                "input": _rel("prep", key, "base", name),
                "output": mutant_file_rel(target["null_id"], target["vm_path"]),
                "steps": [],
            }
        )
    nulls.update(run_uno(out, null_rows, "null", **uno))
    for target in text:
        key = target["target_id"]
        name = posixpath.basename(target["vm_path"])
        base = out / "prep" / key / "base" / name
        base.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target["gold"], base)
        null = out / mutant_file_rel(target["null_id"], target["vm_path"])
        null.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base, null)

    plans: list[tuple[dict[str, Any], Path, Path, list[dict[str, Any]]]] = []
    for target in targets:
        key = target["target_id"]
        name = posixpath.basename(target["vm_path"])
        base = out / "prep" / key / "base" / name
        null = out / mutant_file_rel(target["null_id"], target["vm_path"])
        entry = {k: target[k] for k in ("target_id", "null_id", "task_id", "family", "vm_path")}
        is_office = target["family"] in OFFICE_FAMILIES
        failed = None
        if is_office and prep.get(f"{key}-base", {}).get("status") != "ok":
            failed = f"base save: {prep.get(f'{key}-base', {}).get('error', 'no log')}"
        elif is_office and nulls.get(target["null_id"], {}).get("status") != "ok":
            failed = f"null save: {nulls.get(target['null_id'], {}).get('error', 'no log')}"
        elif (
            is_office and target["initial"] and prep.get(f"{key}-initial", {}).get("status") != "ok"
        ):
            failed = f"initial save: {prep.get(f'{key}-initial', {}).get('error', 'no log')}"
        if failed:
            built.append({**entry, "status": "prepare_failed", "error": str(failed)[:400]})
            continue
        if target["initial"] is None:
            initial = None
        elif is_office:
            initial = out / "prep" / key / "initial" / name
        else:
            initial = Path(target["initial"])
        spec = RequirementSpec.from_dict(json.loads(Path(target["spec_json"]).read_text()))
        try:
            ctx = make_context(
                target["task_id"], spec, base, initial, target["family"], target["vm_path"]
            )
            records, skips = plan_task(
                ctx, operators=wanted_operators(target["family"], initial is not None)
            )
        except Exception as exc:  # noqa: BLE001 - a snapshot failure excludes the target
            built.append({**entry, "status": "plan_failed", "error": repr(exc)[:400]})
            continue
        built.append(
            {
                **entry,
                "status": "planned",
                "base_sha256": sha256_file(base),
                "null_sha256": sha256_file(null),
                "has_initial": initial is not None,
                "planned": len(records),
                "skips": dict(Counter(s["reason"][:60] for s in skips)),
                "bindings": {
                    rid: {"method": b.method, "confidence": b.confidence, "units": len(b.units)}
                    for rid, b in ctx.bindings.items()
                },
            }
        )
        plans.append((target, base, null, records))

    apply_rows = []
    # What each recipe was applied to: the recipe's own input_sha256 names the
    # base it was planned on; under --apply-to gold the steps edit the raw gold.
    applied_input: dict[str, dict[str, str]] = {}
    for target, base, _null, records in plans:
        if target["family"] not in OFFICE_FAMILIES:
            for record in records:
                # Text and config bases are byte copies of the gold.
                applied_input[record["mutant_id"]] = {
                    "applied_to": "gold",
                    "applied_input_sha256": target["gold_sha256"],
                }
            continue
        for record in records:
            to_gold = args.apply_to == "gold"
            input_sha = target["gold_sha256"] if to_gold else record["recipe"]["input_sha256"]
            applied_input[record["mutant_id"]] = {
                "applied_to": args.apply_to,
                "applied_input_sha256": input_sha,
            }
            apply_rows.append(
                {
                    "mutant_id": record["mutant_id"],
                    "family": record["family"],
                    "input": target["gold"] if to_gold else str(base.relative_to(out)),
                    "input_sha256": input_sha,
                    "output": mutant_file_rel(record["mutant_id"], target["vm_path"]),
                    "steps": record["recipe"]["params"]["steps"],
                }
            )
    applied = run_uno(out, apply_rows, "apply", **uno)
    for target, base, _null, records in plans:
        if target["family"] in OFFICE_FAMILIES:
            continue
        for record in records:
            dst = out / mutant_file_rel(record["mutant_id"], target["vm_path"])
            entry = {"mutant_id": record["mutant_id"], "applier": "q2-text-apply-v1"}
            try:
                entry["output_sha256"] = apply_file(
                    base, dst, record["recipe"]["params"]["steps"], record["recipe"]["input_sha256"]
                )
                entry["status"] = "ok"
            except (TextApplyError, ValueError, KeyError) as exc:
                entry["status"] = "error"
                entry["error"] = f"{exc.__class__.__name__}: {exc}"
            applied[record["mutant_id"]] = entry

    verified: list[dict[str, Any]] = []
    target_of: dict[str, str] = {}
    for target, _base, null, records in plans:
        for record in records:
            mutant = out / mutant_file_rel(record["mutant_id"], target["vm_path"])
            done = verify(
                record, null, mutant if mutant.exists() else None, applied.get(record["mutant_id"])
            )
            MutationResult.from_dict(done).check_against_spec(
                RequirementSpec.from_dict(json.loads(Path(target["spec_json"]).read_text()))
            )
            verified.append(done)
            target_of[record["mutant_id"]] = target["target_id"]
    kept, dropped = dedupe_admitted(verified)
    dropped_ids = {r["mutant_id"] for r in dropped}
    admission = []
    for record in verified:
        failed = [c["name"] for c in record["purity_checks"] if not c["passed"]]
        admission.append(
            {
                "mutant_id": record["mutant_id"],
                "target_id": target_of[record["mutant_id"]],
                "admitted": is_admitted(record) and record["mutant_id"] not in dropped_ids,
                "purity_admitted": is_admitted(record),
                "duplicate": record["mutant_id"] in dropped_ids,
                "failed_checks": failed,
                "apply_status": applied.get(record["mutant_id"], {}).get("status", "missing"),
                **applied_input.get(record["mutant_id"], {}),
            }
        )
    write_jsonl(out / "mutations.jsonl", verified)
    write_jsonl(out / "admission.jsonl", admission)
    write_jsonl(out / "targets-built.jsonl", built)
    jobs = scoring_jobs(verified, admission, targets, built, out)
    write_jsonl(out / "scoring-jobs.jsonl", jobs)
    summary = {
        "targets": len(targets),
        "targets_planned": sum(1 for b in built if b["status"] == "planned"),
        "target_status": dict(Counter(b["status"] for b in built)),
        "planned": len(verified),
        "applied": sum(1 for a in admission if a["apply_status"] == "ok"),
        "purity_admitted": sum(1 for a in admission if a["purity_admitted"]),
        "duplicates": len(dropped_ids),
        "admitted": sum(1 for a in admission if a["admitted"]),
        "labels_planned": dict(Counter(r["label"] for r in verified)),
        "labels_admitted": dict(
            Counter(r["label"] for r, a in zip(verified, admission, strict=True) if a["admitted"])
        ),
        "scoring_jobs": len(jobs),
        "lo_build": next((e.get("lo_build") for e in prep.values() if e.get("lo_build")), None),
        "apply_to": args.apply_to,
    }
    write_json(out / "build-summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


def scoring_jobs(
    mutations: Sequence[Mapping[str, Any]],
    admission: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    built: Sequence[Mapping[str, Any]],
    files_root: Path,
) -> list[dict[str, Any]]:
    """Admitted mutants and one null job per planned target, with gold context files."""
    from harness.q2_mutation.controls import mutation_jobs

    by_target = {t["target_id"]: t for t in targets}
    planned = {b["target_id"] for b in built if b["status"] == "planned"}
    admitted = {a["mutant_id"] for a in admission if a["admitted"]}
    context = {t["task_id"]: t["context_files"] for t in targets}
    rows = [m for m in mutations if m["mutant_id"] in admitted]
    jobs = mutation_jobs(rows, files_root / "files", context=context)
    target_by_mutant = {a["mutant_id"]: a["target_id"] for a in admission}
    for job in jobs:
        job["target_id"] = target_by_mutant[job["mutant_id"]]
    for target_key in sorted(planned):
        target = by_target[target_key]
        null = files_root / mutant_file_rel(target["null_id"], target["vm_path"])
        files = {vm: local for vm, local in target["context_files"].items()}
        files[target["vm_path"]] = str(null)
        jobs.append(
            {
                "job_id": target["null_id"],
                "mutant_id": target["null_id"],
                "task_id": target["task_id"],
                "target_id": target_key,
                "kind": "null",
                "label": None,
                "stratum": "document_model",
                "files": files,
                "candidate_sha256": sha256_file(null),
                "skip_reachability": False,
            }
        )
    return jobs


# --- stage 4: merge (metric image) ----------------------------------------------


def remap(path: str | None, mapping: Sequence[tuple[str, str]]) -> str | None:
    if path is None:
        return None
    for old, new in mapping:
        if path.startswith(old):
            return new + path[len(old) :]
    return path


def cmd_merge(args: argparse.Namespace) -> int:
    from harness.q2_mutation.controls import merge_lo

    mapping = [tuple(item.split("=", 1)) for item in args.path_map]
    jobs = read_jsonl(args.jobs)
    lo_rows = [row for path in args.lo_rows for row in read_jsonl(path)]
    merged, excluded = merge_lo(jobs, lo_rows, suffix=None)
    for job in merged:
        job["files"] = {vm: remap(local, mapping) for vm, local in job["files"].items()}
    write_jsonl(args.out, merged)
    write_jsonl(Path(args.out).with_suffix(".excluded.jsonl"), excluded)
    print(json.dumps({"merged": len(merged), "excluded": len(excluded)}))
    return 0


# --- stage 6: recheck (metric image) --------------------------------------------


def recheck_rows(
    mutations: Sequence[Mapping[str, Any]],
    admission: Sequence[Mapping[str, Any]],
    saved_jobs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Operator purity on the saved mutant against the saved null mutant."""
    from harness.q2_mutation.operators.pipeline import is_admitted, verify

    saved = {job["mutant_id"]: job for job in saved_jobs}
    nulls = {job["target_id"]: job for job in saved_jobs if job.get("kind") == "null"}
    target_of = {a["mutant_id"]: a["target_id"] for a in admission if a["admitted"]}
    rows = []
    for record in mutations:
        mutant_id = record["mutant_id"]
        if mutant_id not in target_of:
            continue
        vm_path = record["target_path_in_vm"]
        job = saved.get(mutant_id)
        null_job = nulls.get(target_of[mutant_id])
        if job is None or null_job is None:
            rows.append({"mutant_id": mutant_id, "status": "no_saved_pair"})
            continue
        mutant_file = job["files"].get(vm_path)
        null_file = null_job["files"].get(vm_path)
        if not mutant_file or not null_file:
            rows.append({"mutant_id": mutant_id, "status": "saved_file_missing"})
            continue
        log = {"status": "ok", "lo_build": job.get("lo_build") or "unsaved"}
        done = verify(dict(record), null_file, mutant_file, log)
        rows.append(
            {
                "mutant_id": mutant_id,
                "status": "checked",
                "saved_via": job.get("saved_via"),
                "null_saved_via": null_job.get("saved_via"),
                "saved_sha256": sha256_file(mutant_file),
                "post_save_admitted": is_admitted(done),
                "post_save_failed": [c["name"] for c in done["purity_checks"] if not c["passed"]],
                "post_save_checks": done["purity_checks"],
            }
        )
    return rows


def cmd_recheck(args: argparse.Namespace) -> int:
    rows = recheck_rows(
        read_jsonl(args.mutations), read_jsonl(args.admission), read_jsonl(args.saved_jobs)
    )
    write_jsonl(args.out, rows)
    print(
        json.dumps(
            {
                "rechecked": len(rows),
                "post_save_admitted": sum(1 for r in rows if r.get("post_save_admitted")),
            }
        )
    )
    return 0


# --- stage 7: report ------------------------------------------------------------


EVENT_OF_LABEL = {
    "should_pass_equiv": ("FN", "fail_or_partial"),
    "should_pass_alt_solution": ("FN_alt", "fail_or_partial"),
    "should_fail_violation": ("FP_R", "pass"),
    "should_fail_extra_change": ("FP_F", "pass"),
}


def probe_touched_cells(probe: Mapping[str, Any]) -> dict[str, list[str]]:
    """task id -> operator name patterns touched by a scoping probe."""
    cells: dict[str, list[str]] = {}
    for task_id, info in probe.get("tasks", {}).items():
        patterns: list[str] = []
        for op in info.get("probes", []):
            if op not in PROBE_OPERATOR_MAP:
                raise CampaignError(f"probe op {op!r} has no operator mapping")
            patterns.extend(PROBE_OPERATOR_MAP[op])
        cells[task_id] = sorted(set(patterns))
    return cells


def is_probe_touched(cells: Mapping[str, Sequence[str]], task_id: str, operator: str) -> bool:
    """A probe cell, or a probe-informed operator anywhere: both are exploratory."""
    if operator in PROBE_INFORMED_OPERATORS:
        return True
    return any(fnmatch.fnmatchcase(operator, pattern) for pattern in cells.get(task_id, ()))


def classify(
    label: str,
    admitted: bool,
    post_save: Mapping[str, Any] | None,
    verdict: Mapping[str, Any] | None,
    null_verdict: Mapping[str, Any] | None,
    nondeterministic: bool,
    *,
    save_failed: bool = False,
    unemulated: bool = False,
    infra_failed: bool = False,
) -> tuple[str, str | None]:
    """(status, event) of one mutant under one venv.

    status, first match wins: not_admitted | save_failed (the GUI-faithful
    save of the mutant or of its null mutant did not write every office file,
    or an office candidate reached the scorer unsaved) | unemulated (the task
    has a setup or postconfig step the harness cannot replay and that may write
    a file the checker reads) | not_scored | normalized | infra_failed (the
    mutant's or its null mutant's scoring timed out after its retries, or
    failed for a harness cause: the scoring process died without a result, a
    live getter, a refused network fetch; ``offline_eval.score_job``) |
    null_not_pass | error | nondeterministic | ambiguous | evaluable. The first
    three and infra_failed are infrastructure exclusions (preregistration
    section 8). event is set only for evaluable mutants: FN / FN_alt / FP_R /
    FP_F when the checker disagrees with the label, 'ok' when it agrees.
    """
    if not admitted:
        return "not_admitted", None
    if save_failed:
        return "save_failed", None
    if unemulated:
        return "unemulated", None
    if verdict is None:
        return "not_scored", None
    if post_save is None or post_save.get("status") != "checked":
        return "not_scored", None
    if not post_save.get("post_save_admitted"):
        return "normalized", None
    if infra_failed:
        return "infra_failed", None
    if null_verdict is None or null_verdict["verdict"] != "pass":
        return "null_not_pass", None
    if verdict["verdict"] == "error":
        return "error", None
    if nondeterministic:
        return "nondeterministic", None
    if label == "ambiguous":
        return "ambiguous", None
    event, wrong = EVENT_OF_LABEL[label]
    passed = verdict["verdict"] == "pass"
    disagrees = (not passed) if wrong == "fail_or_partial" else passed
    return "evaluable", (event if disagrees else "ok")


def unsaved_office(job: Mapping[str, Any] | None) -> bool:
    """An office candidate that reached the scorer without its GUI-faithful save."""
    if job is None or job.get("skip_reachability"):
        return False
    office = any(
        posixpath.splitext(vm)[1].lower() in OFFICE_SAVE_SUFFIXES
        for vm, local in (job.get("files") or {}).items()
        if local is not None
    )
    return office and job.get("saved_via") != "gui_faithful_lo_save"


def _verdicts(path: Path) -> dict[str, dict[str, Any]]:
    from harness.q2_mutation.schema import read_verdict_rows

    if not path.is_file():
        return {}
    rows = read_verdict_rows(path.read_text(encoding="utf-8").splitlines())
    return {row.mutant_id: row.to_dict() for row in rows}


def _notes(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    return {row["mutant_id"]: row for row in read_jsonl(path)}


def icc_oneway(groups: Mapping[str, Sequence[bool]]) -> float | None:
    """One-way ANOVA intra-cluster correlation of a binary event; None if undefined."""
    clusters = [list(map(float, g)) for g in groups.values() if g]
    n_total = sum(len(g) for g in clusters)
    k = len(clusters)
    if k < 2 or n_total <= k:
        return None
    grand = sum(sum(g) for g in clusters) / n_total
    ss_between = sum(len(g) * (sum(g) / len(g) - grand) ** 2 for g in clusters)
    ss_within = sum(sum((x - sum(g) / len(g)) ** 2 for x in g) for g in clusters)
    ms_between = ss_between / (k - 1)
    ms_within = ss_within / (n_total - k)
    n0 = (n_total - sum(len(g) ** 2 for g in clusters) / n_total) / (k - 1)
    denominator = ms_between + (n0 - 1) * ms_within
    if denominator <= 0:
        return None
    return (ms_between - ms_within) / denominator


def _interval(units: list[Any], seed: int, n_boot: int) -> dict[str, Any] | None:
    from harness.q2_mutation.stats import cluster_bootstrap_ci

    if not units:
        return None
    ci = cluster_bootstrap_ci(units, n_boot=n_boot, seed=seed)
    return {
        "rate": round(ci.estimate, 4),
        "low": round(ci.low, 4),
        "high": round(ci.high, 4),
        "tasks": ci.n_clusters,
        "mutants": ci.n_units,
    }


def build_report(
    mutations: Sequence[Mapping[str, Any]],
    admission: Sequence[Mapping[str, Any]],
    recheck: Sequence[Mapping[str, Any]],
    verdicts: Mapping[str, Mapping[str, Mapping[str, Any]]],
    notes: Mapping[str, Mapping[str, Mapping[str, Any]]],
    saved_jobs: Sequence[Mapping[str, Any]],
    probe_cells: Mapping[str, Sequence[str]],
    *,
    excluded: Sequence[Mapping[str, Any]] = (),
    scoring_jobs: Sequence[Mapping[str, Any]] = (),
    primary: str = "lock",
    seed: int = 42,
    n_boot: int = 10_000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Outcome rows (one per planned mutant) and the summary tables.

    ``excluded`` are the jobs ``merge`` left out because their save stage
    failed; ``scoring_jobs`` (the build's job list) names the null mutant of
    a target whose own save failed, which ``saved_jobs`` no longer holds.
    """
    from harness.q2_mutation.stats import Unit, minimum_detectable_rate

    adm = {a["mutant_id"]: a for a in admission}
    post = {r["mutant_id"]: r for r in recheck}
    null_of_target = {
        job["target_id"]: job["mutant_id"]
        for job in [*scoring_jobs, *saved_jobs]
        if job.get("kind") == "null"
    }
    saved = {job["mutant_id"]: job for job in saved_jobs}
    saved_via = {job["mutant_id"]: job.get("saved_via") for job in saved_jobs}
    save_failed_ids = {row["mutant_id"] for row in excluded if row.get("mutant_id")}
    arms = sorted(verdicts)

    def save_failed(mutant: str | None) -> bool:
        return bool(mutant) and (mutant in save_failed_ids or unsaved_office(saved.get(mutant)))

    def unemulated_writes(mutant: str | None, arm: str) -> bool:
        if not mutant:
            return False
        note = notes.get(arm, {}).get(mutant, {})
        return bool(
            (saved.get(mutant) or {}).get("save_stage_unemulated_writes")
            or note.get("setup_unemulated_writes")
            or note.get("postconfig_unemulated_writes")
        )

    outcomes = []
    for record in mutations:
        mutant_id = record["mutant_id"]
        a = adm[mutant_id]
        null = null_of_target.get(a["target_id"])
        row: dict[str, Any] = {
            "mutant_id": mutant_id,
            "task_id": record["task_id"],
            "target_id": a["target_id"],
            "operator": record["operator"],
            "doc_family": record["family"],
            "label": record["label"],
            "witness_rule": record["witness"]["argument"].split(":", 1)[0],
            "admitted": a["admitted"],
            "failed_checks": a["failed_checks"],
            "post_save_admitted": post.get(mutant_id, {}).get("post_save_admitted"),
            "post_save_failed": post.get(mutant_id, {}).get("post_save_failed"),
            "saved_via": saved_via.get(mutant_id),
            "probe_informed": record["operator"] in PROBE_INFORMED_OPERATORS,
            "probe_touched": is_probe_touched(probe_cells, record["task_id"], record["operator"]),
        }
        for arm in arms:
            verdict = verdicts[arm].get(mutant_id)
            null_verdict = verdicts[arm].get(null) if null else None
            note = notes.get(arm, {}).get(mutant_id, {})
            null_note = notes.get(arm, {}).get(null, {}) if null else {}
            unstable = bool(note.get("nondeterministic")) or bool(null_note.get("nondeterministic"))
            status, event = classify(
                record["label"],
                a["admitted"],
                post.get(mutant_id),
                verdict,
                null_verdict,
                unstable,
                save_failed=save_failed(mutant_id) or save_failed(null),
                unemulated=unemulated_writes(mutant_id, arm) or unemulated_writes(null, arm),
                infra_failed=bool(note.get("infra_failed") or null_note.get("infra_failed")),
            )
            row[f"{arm}_verdict"] = verdict["verdict"] if verdict else None
            row[f"{arm}_score"] = verdict["score"] if verdict else None
            row[f"{arm}_null_verdict"] = null_verdict["verdict"] if null_verdict else None
            row[f"{arm}_status"] = status
            row[f"{arm}_event"] = event
            if verdict:
                row["checker_family"] = checker_family(verdict["checker_funcs"])
        outcomes.append(row)

    summary: dict[str, Any] = {
        "primary_dep_set": primary,
        "planned": len(outcomes),
        "admitted": sum(1 for r in outcomes if r["admitted"]),
        "save_stage_exclusions": [
            {"mutant_id": row.get("mutant_id"), "kind": row.get("kind")}
            for row in sorted(excluded, key=lambda r: str(r.get("mutant_id")))
        ],
        "unemulated_tasks": sorted(
            {
                r["task_id"]
                for r in outcomes
                if any(r.get(f"{arm}_status") == "unemulated" for arm in arms)
            }
        ),
        "labels_admitted": dict(Counter(r["label"] for r in outcomes if r["admitted"])),
        "status": {arm: dict(Counter(r[f"{arm}_status"] for r in outcomes)) for arm in arms},
        "null_verdicts": {
            arm: {
                target: verdicts[arm].get(null, {}).get("verdict")
                for target, null in sorted(null_of_target.items())
            }
            for arm in arms
        },
    }
    if primary in arms:
        evaluable = [
            r for r in outcomes if r[f"{primary}_status"] == "evaluable" and not r["probe_touched"]
        ]
        tables: dict[str, Any] = {}
        icc: dict[str, Any] = {}
        for event in ("FN", "FN_alt", "FP_R", "FP_F"):
            label = next(k for k, v in EVENT_OF_LABEL.items() if v[0] == event)
            rows = [r for r in evaluable if r["label"] == label]
            units = [Unit(r["task_id"], r[f"{primary}_event"] == event) for r in rows]
            per_family: dict[str, Any] = {}
            for family in sorted({r["checker_family"] for r in rows}):
                fam_units = [
                    Unit(r["task_id"], r[f"{primary}_event"] == event)
                    for r in rows
                    if r["checker_family"] == family
                ]
                per_family[family] = _interval(fam_units, seed, n_boot)
            tables[event] = {"pooled": _interval(units, seed, n_boot), "by_checker": per_family}
            groups: dict[str, list[bool]] = defaultdict(list)
            for unit in units:
                groups[unit.task_id].append(unit.event)
            icc[event] = icc_oneway(groups)
        summary["rates_exploratory"] = tables
        summary["icc_by_event"] = icc
        defined = [v for v in icc.values() if v is not None]
        summary["icc_max_defined"] = max(defined) if defined else None
        flips = []
        if len(arms) == 2:
            other = [arm for arm in arms if arm != primary][0]
            for r in outcomes:
                first, second = r[f"{primary}_verdict"], r[f"{other}_verdict"]
                # S1 counts a flip only when each venv's repeated scorings agree.
                unstable = any(
                    notes.get(arm, {}).get(r["mutant_id"], {}).get("nondeterministic")
                    for arm in arms
                )
                if first and second and first != second and not unstable:
                    flips.append(r["mutant_id"])
        summary["venv_disagreements"] = flips
        task_escape: dict[str, bool] = defaultdict(bool)
        for r in evaluable:
            if r["label"] in ("should_pass_equiv", "should_fail_violation"):
                task_escape[r["task_id"]] |= r[f"{primary}_event"] in ("FN", "FP_R")
        summary["task_escape"] = {
            "tasks": len(task_escape),
            "with_escape": sum(1 for v in task_escape.values() if v),
        }
        per_task = Counter(r["task_id"] for r in evaluable)
        if per_task:
            mean_size = sum(per_task.values()) / len(per_task)
            summary["mean_evaluable_mutants_per_task"] = round(mean_size, 2)
        normalization = defaultdict(Counter)
        for r in outcomes:
            if r["admitted"] and r["post_save_admitted"] is not None:
                normalization[r["operator"]]["checked"] += 1
                normalization[r["operator"]]["normalized"] += int(not r["post_save_admitted"])
        summary["normalization_by_operator"] = {
            k: dict(v) for k, v in sorted(normalization.items())
        }
        summary["by_operator"] = {
            op: dict(
                Counter(
                    f"{r['label']}:{r[f'{primary}_status']}:{r[f'{primary}_event']}"
                    for r in outcomes
                    if r["operator"] == op
                )
            )
            for op in sorted({r["operator"] for r in outcomes})
        }
        # The registered design sizes (preregistration section 6): P5 and P2
        # pooled, the two largest families, and the P3 / P4 pools.
        summary["mdr_reference"] = {
            f"{n}_tasks_icc_{icc_value}": round(minimum_detectable_rate(0.05, n, 3.0, icc_value), 4)
            for n in (59, 31, 21, 13)
            for icc_value in (0.13, 0.5, 1.0)
        }
    return outcomes, summary


K2_PAIRS = 80
K2_MIN_DOMAINS = 3
K2_PER_TASK = 4


def k2_sample(
    jobs: Sequence[Mapping[str, Any]],
    domain_of: Mapping[str, str],
    *,
    n: int = K2_PAIRS,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """The K2 fidelity sample: ``n`` scoring jobs over at least three task domains.

    Drawn from the build's job list only (admitted mutants and null mutants),
    before and without any verdict. Each domain's jobs are shuffled with
    ``random.Random(f"{seed}:k2:{domain}")``; jobs are then taken round-robin
    over the sorted domains, at most ``K2_PER_TASK`` per task, and if the cap
    leaves fewer than ``n`` the remainder is filled round-robin without it.
    """
    import random

    pool: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for job in sorted(jobs, key=lambda j: str(j["job_id"])):
        if job.get("kind") in ("mutant", "null"):
            pool[domain_of[str(job["task_id"])]].append(job)
    if len(pool) < K2_MIN_DOMAINS:
        raise CampaignError(f"K2 needs at least {K2_MIN_DOMAINS} domains, found {len(pool)}")
    queues = {}
    for domain in sorted(pool):
        queue = list(pool[domain])
        random.Random(f"{seed}:k2:{domain}").shuffle(queue)
        queues[domain] = queue
    chosen: list[Mapping[str, Any]] = []
    taken: set[str] = set()
    for capped in (True, False):
        per_task = Counter(str(j["task_id"]) for j in chosen)
        progress = True
        while len(chosen) < n and progress:
            progress = False
            for domain in sorted(queues):
                for job in queues[domain]:
                    job_id = str(job["job_id"])
                    task = str(job["task_id"])
                    if job_id in taken or (capped and per_task[task] >= K2_PER_TASK):
                        continue
                    chosen.append(job)
                    taken.add(job_id)
                    per_task[task] += 1
                    progress = True
                    break
                if len(chosen) >= n:
                    break
    return [
        {
            "job_id": job["job_id"],
            "mutant_id": job["mutant_id"],
            "task_id": job["task_id"],
            "domain": domain_of[str(job["task_id"])],
            "kind": job["kind"],
            "candidate_sha256": job.get("candidate_sha256"),
        }
        for job in chosen
    ]


def cmd_k2_sample(args: argparse.Namespace) -> int:
    jobs = read_jsonl(args.jobs)
    domains = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))["domain"]
        for path in Path(args.sanitized).glob("*.json")
    }
    out = Path(args.out)
    try:
        rows = k2_sample(jobs, domains, n=args.n, seed=args.seed)
        status = "drawn"
    except CampaignError as exc:
        rows, status = [], f"not drawn: {exc}"
    write_jsonl(out, rows)
    summary = {
        "status": status,
        "pairs": len(rows),
        "by_domain": dict(Counter(r["domain"] for r in rows)),
        "tasks": len({r["task_id"] for r in rows}),
        "jobs_sha256": sha256_file(args.jobs),
        "sample_sha256": sha256_file(out),
        "seed": args.seed,
    }
    write_json(out.with_suffix(".summary.json"), summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    run = Path(args.run)
    verdicts = {arm: _verdicts(run / f"mut-verdicts-{arm}.jsonl") for arm in ("lock", "scout")}
    verdicts = {arm: rows for arm, rows in verdicts.items() if rows}
    notes = {arm: _notes(run / f"mut-notes-{arm}.jsonl") for arm in verdicts}
    probe = json.loads(Path(args.probe_touched).read_text(encoding="utf-8"))
    excluded_path = run / "jobs-saved.excluded.jsonl"
    scoring_path = Path(args.admission).parent / "scoring-jobs.jsonl"
    outcomes, summary = build_report(
        read_jsonl(args.mutations),
        read_jsonl(args.admission),
        read_jsonl(run / "recheck.jsonl"),
        verdicts,
        notes,
        read_jsonl(run / "jobs-saved.jsonl"),
        probe_touched_cells(probe),
        excluded=read_jsonl(excluded_path) if excluded_path.is_file() else [],
        scoring_jobs=read_jsonl(scoring_path) if scoring_path.is_file() else [],
        n_boot=args.n_boot,
    )
    s1 = run / "mut-s1.json"
    if s1.is_file():
        # S1 counts only the candidates confirmed at five scorings per venv.
        summary["s1"] = json.loads(s1.read_text(encoding="utf-8"))
    write_jsonl(run / "outcomes.jsonl", outcomes)
    write_json(run / "report.json", summary)
    print(json.dumps({k: summary[k] for k in ("planned", "admitted", "status")}, sort_keys=True))
    return 0


def cmd_pins(args: argparse.Namespace) -> int:
    out = pins(Path(args.root))
    if args.inputs:
        out.update(input_digests(Path(args.inputs)))
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


def cmd_guard(args: argparse.Namespace) -> int:
    """Refuse a stage whose split, staged code or mounted inputs differ from the registration.

    Every split: the mounted OSWorld tree, VM baseline and file cache must
    match the pins. Every split but dev: also the frozen ledger row (hash chain
    and file digest), ``Q2M_PREREG_FROZEN`` and the code, catalog, spec,
    split, probe-map and receipt digests (``require_split_allowed``).
    """
    src = Path(args.src)
    row = require_split_allowed(args.split, src)
    checked = check_inputs(src, Path(args.inputs))
    print(json.dumps({"split": args.split, "frozen": bool(row), **checked}, sort_keys=True))
    return 0


# --- stage 8: release view (anywhere) -------------------------------------------

# Recipes and purity details can carry document text (a ``must_equal`` value
# holds a whole paragraph of the gold). The released view keeps every
# identifier, locator, digest and short value, and replaces longer free text
# (anything with whitespace or non-ASCII characters from REDACT_MIN_CHARS on)
# by its SHA-256 and length. The full recipe and the base file it names
# (``input_sha256``) stay in the host run root; planning is deterministic given
# the base, so a holder of the base files can regenerate each recipe and check
# its digest and mutant id. The mutant file is the recipe's steps applied to the
# file a release row names in ``applied_input_sha256`` (the raw gold under
# ``--apply-to gold``, not the base). (A fresh LibreOffice save of the gold is
# not byte-identical, so it yields new ids with the same sites and labels.)
REDACT_MIN_CHARS = 32
_PLAIN_TOKEN = re.compile(r"[A-Za-z0-9_./\[\]:!$#@=+*,()<>&%^|~;?'\"-]+")
# A quote opens after a non-word character and closes before one, so the
# apostrophe in "R2's" or "don't" neither opens nor closes a span.
_QUOTED = re.compile(r"(?<!\w)'(.*?)'(?!\w)|(?<!\w)\"(.*?)\"(?!\w)", re.DOTALL)
OUTCOME_KEYS = frozenset(
    {
        "mutant_id",
        "task_id",
        "target_id",
        "operator",
        "doc_family",
        "label",
        "witness_rule",
        "admitted",
        "failed_checks",
        "post_save_admitted",
        "post_save_failed",
        "saved_via",
        "probe_touched",
        "probe_informed",
        "checker_family",
    }
)


def needs_redaction(text: str) -> bool:
    return len(text) >= REDACT_MIN_CHARS and not _PLAIN_TOKEN.fullmatch(text)


def _redacted(text: str) -> dict[str, Any]:
    return {"redacted_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "chars": len(text)}


def redact(value: Any) -> Any:
    """Replace long free-text leaves with their digest; keep structure and short values."""
    if isinstance(value, Mapping):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    if isinstance(value, str) and needs_redaction(value):
        return _redacted(value)
    return value


def _marker(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"<redacted sha256 {digest[:16]}, {len(text)} chars>"


def free_text_leaves(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return [leaf for item in value.values() for leaf in free_text_leaves(item)]
    if isinstance(value, list | tuple):
        return [leaf for item in value for leaf in free_text_leaves(item)]
    return [value] if isinstance(value, str) and needs_redaction(value) else []


def redact_quotes(text: str, known: Sequence[str] = ()) -> str:
    """Witness arguments are templates: redact known free text, then long quoted spans."""
    for leaf in sorted(set(known), key=len, reverse=True):
        text = text.replace(leaf, _marker(leaf))

    def swap(match: re.Match[str]) -> str:
        inner = match.group(1) if match.group(1) is not None else match.group(2)
        if len(inner) < REDACT_MIN_CHARS or inner.startswith("<redacted sha256 "):
            return match.group(0)
        return f"'{_marker(inner)}'"

    return _QUOTED.sub(swap, text)


def release_record(
    record: Mapping[str, Any], applied: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """The releasable view of one ``MutationResult``: ids, label, witness, digests.

    ``applied`` (the build's admission row) names what the recipe's steps were
    applied to and that file's SHA-256: under ``--apply-to gold`` the gold, not
    the base that ``recipe.input_sha256`` names (the base is what planning read).
    """
    from harness.q2_mutation.schema import MutationResult, recipe_sha256

    result = MutationResult.from_dict(record)
    digest = recipe_sha256(result.recipe)
    if not result.mutant_id.endswith(digest[:12]):
        raise CampaignError(f"{result.mutant_id}: recipe digest does not match the id")
    return {
        "mutant_id": result.mutant_id,
        "task_id": result.task_id,
        "operator": result.operator,
        "family": result.family,
        "label": result.label,
        "stratum": result.stratum,
        "target_path_in_vm": result.target_path_in_vm,
        "output_sha256": result.output_sha256,
        "witness": {
            "req_ids": list(result.witness.req_ids),
            "argument": redact_quotes(
                result.witness.argument, free_text_leaves(dict(result.recipe))
            ),
        },
        "purity_checks": [
            {"name": check.name, "passed": check.passed} for check in result.purity_checks
        ],
        "recipe_sha256": digest,
        "recipe_release": redact(dict(result.recipe)),
        "applied_to": (applied or {}).get("applied_to"),
        "applied_input_sha256": (applied or {}).get("applied_input_sha256"),
    }


def release_verdict(row: Mapping[str, Any]) -> dict[str, Any]:
    """A verdict row with any checker exception message cut to its type and a short head."""
    from harness.q2_mutation.schema import VerdictRow

    out = VerdictRow.from_dict(row).to_dict()
    if out.get("error"):
        head = str(out["error"])
        out["error"] = head if len(head) <= 80 else head[:80] + "..."
    return out


def _receipts(root: Path) -> list[dict[str, Any]]:
    receipts = []
    for path in sorted(root.glob("*/receipt-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        argv = json.loads(bytes.fromhex(data.pop("argv_json_hex", "")) or b"[]")
        receipts.append({**data, "stage": path.parent.name, "argv": argv})
    return receipts


def notes_summary(notes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "jobs": len(notes),
        "nondeterministic": sorted(n["mutant_id"] for n in notes if n.get("nondeterministic")),
        "infra_timeouts": sum(int(n.get("infra_timeouts", 0)) for n in notes),
        "infra_failed": sorted(n["mutant_id"] for n in notes if n.get("infra_failed")),
        "setup_unemulated_jobs": sum(1 for n in notes if n.get("setup_unemulated")),
        "postconfig_unemulated_jobs": sum(1 for n in notes if n.get("postconfig_unemulated")),
        "unemulated_writing_jobs": sum(
            1
            for n in notes
            if n.get("setup_unemulated_writes") or n.get("postconfig_unemulated_writes")
        ),
    }


def reachability_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    saves = [save for row in rows for save in row.get("saves", [])]
    timings = sorted(s["seconds_to_write"] for s in saves if s.get("seconds_to_write") is not None)
    return {
        "jobs": len(rows),
        "infra_errors": sorted(row["job_id"] for row in rows if row.get("infra_error")),
        "skipped": sum(1 for row in rows if (row.get("plan") or {}).get("skipped")),
        "jobs_with_failures": sorted(row["job_id"] for row in rows if row.get("failures")),
        "jobs_with_unemulated_steps": sorted(
            row["job_id"] for row in rows if (row.get("plan") or {}).get("unemulated")
        ),
        "saves": len(saves),
        "saves_written": sum(1 for s in saves if s.get("written")),
        "saves_with_dialogs": sum(1 for s in saves if s.get("dialogs")),
        "saves_slower_than_0_5s": sum(1 for t in timings if t > 0.5),
        "max_seconds_to_write": timings[-1] if timings else None,
        "lo_builds": sorted({str(row.get("lo_build")) for row in rows}),
    }


def recheck_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_status = Counter(row["status"] for row in rows)
    failed: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for name in row.get("post_save_failed") or []:
            failed[row["mutant_id"].split("__")[1]][name] += 1
    return {
        "rows": len(rows),
        "status": dict(by_status),
        "post_save_admitted": sum(1 for row in rows if row.get("post_save_admitted")),
        "post_save_failed_by_operator": {op: dict(c) for op, c in sorted(failed.items())},
    }


def cmd_export(args: argparse.Namespace) -> int:
    """Write the releasable evidence of one run (no document content, no mutant files)."""
    run = Path(args.run)
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise CampaignError(f"{out} is not empty; version the export directory")
    submitted = json.loads((run / "submitted.json").read_text(encoding="utf-8"))
    if submitted["split"] != DEV_SPLIT:
        require_split_allowed(submitted["split"], Path(args.src))
    sources = {}
    for rel in (
        "submitted.json",
        "prep/targets.report.json",
        "build/build-summary.json",
        "build/mutations.jsonl",
        "build/admission.jsonl",
        "build/targets-built.jsonl",
        "build/scoring-jobs.jsonl",
        "score/jobs-saved.jsonl",
        "score/recheck.jsonl",
        "score/outcomes.jsonl",
        "score/report.json",
    ):
        sources[rel] = sha256_file(run / rel)
    for arm in ("lock", "scout"):
        for kind in ("verdicts", "notes"):
            rel = f"score/mut-{kind}-{arm}.jsonl"
            if (run / rel).is_file():
                sources[rel] = sha256_file(run / rel)
    if (run / "score/jobs-saved.excluded.jsonl").is_file():
        sources["score/jobs-saved.excluded.jsonl"] = sha256_file(
            run / "score/jobs-saved.excluded.jsonl"
        )
    mutations = read_jsonl(run / "build/mutations.jsonl")
    outcomes = read_jsonl(run / "score/outcomes.jsonl")
    for row in outcomes:
        extra = {
            key
            for key in row
            if key not in OUTCOME_KEYS
            and not any(key.startswith(f"{arm}_") for arm in ("lock", "scout"))
        }
        if extra:
            raise CampaignError(f"outcome row carries unexpected keys {sorted(extra)}")
    lo_rows = [
        row
        for path in sorted((run / "build/lo").glob("reachability-*.jsonl"))
        for row in read_jsonl(path)
    ]
    admission = {a["mutant_id"]: a for a in read_jsonl(run / "build/admission.jsonl")}
    write_jsonl(
        out / "mutations.release.jsonl",
        (release_record(r, admission.get(r["mutant_id"])) for r in mutations),
    )
    write_jsonl(out / "outcomes.jsonl", outcomes)
    notes_out: dict[str, Any] = {}
    for arm in ("lock", "scout"):
        path = run / f"score/mut-verdicts-{arm}.jsonl"
        if path.is_file():
            write_jsonl(
                out / f"verdicts-{arm}.jsonl", (release_verdict(r) for r in read_jsonl(path))
            )
            notes_out[arm] = notes_summary(read_jsonl(run / f"score/mut-notes-{arm}.jsonl"))
    write_json(out / "notes-summary.json", notes_out)
    write_json(out / "reachability-summary.json", reachability_summary(lo_rows))
    write_json(
        out / "recheck-summary.json", recheck_summary(read_jsonl(run / "score/recheck.jsonl"))
    )
    write_json(out / "report.json", json.loads((run / "score/report.json").read_text()))
    write_json(
        out / "build-summary.json", json.loads((run / "build/build-summary.json").read_text())
    )
    write_json(out / "targets.json", json.loads((run / "prep/targets.report.json").read_text()))
    write_jsonl(out / "targets-built.jsonl", read_jsonl(run / "build/targets-built.jsonl"))
    write_json(out / "receipts.json", _receipts(run))
    exported = {
        path.name: sha256_file(path)
        for path in sorted(out.iterdir())
        if path.name != "manifest.json"
    }
    write_json(
        out / "manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "run": submitted["run"],
            "split": submitted["split"],
            "git_sha": submitted["git_sha"],
            "slurm_jobs": submitted["jobs"],
            # Runs before the --apply-to option applied recipes to the base.
            "apply_to": submitted.get("apply_to", "base"),
            "confirmatory": False,
            "source_sha256": sources,
            "exported_sha256": exported,
            "redaction": {
                "min_chars": REDACT_MIN_CHARS,
                "rule": "free-text leaves (whitespace or non-ASCII) of at least min_chars in a "
                "recipe become {redacted_sha256, chars}; long quoted spans in witness arguments "
                "likewise; purity-check details and reachability events are dropped",
            },
        },
    )
    print(json.dumps({"exported": sorted(exported), "mutations": len(mutations)}))
    return 0


# --- CLI ------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    tg = sub.add_parser("targets", help="pick mutation targets of one split (metric image)")
    tg.add_argument("--src", default=".", help="staged source tree (repository root)")
    tg.add_argument("--osworld", required=True)
    tg.add_argument("--jobs", required=True, help="controls make-jobs output for the split")
    tg.add_argument("--split", required=True, choices=["dev", "confirm", "reserve"])
    tg.add_argument("--out", default=None)
    tg.add_argument("--count-only", action="store_true")
    tg.set_defaults(func=cmd_targets)

    bd = sub.add_parser("build", help="bases, plans, mutants, purity, scoring jobs (LO-VM)")
    bd.add_argument("--targets", required=True)
    bd.add_argument("--out", required=True)
    bd.add_argument("--soffice", default="/usr/bin/soffice")
    bd.add_argument("--profile-template", default=None)
    bd.add_argument("--timeout", type=int, default=240)
    bd.add_argument("--shards", type=int, default=4)
    bd.add_argument(
        "--apply-to",
        choices=["base", "gold"],
        default="gold",
        help="office recipes edit the raw gold (null mutant = base) or the base "
        "(null mutant = base saved once more)",
    )
    bd.set_defaults(func=cmd_build)

    mg = sub.add_parser("merge", help="saved files into scoring jobs, mutant ids kept")
    mg.add_argument("--jobs", required=True)
    mg.add_argument("--lo-rows", nargs="+", required=True)
    mg.add_argument("--out", required=True)
    mg.add_argument("--path-map", nargs="*", default=[], help="OLD_PREFIX=NEW_PREFIX")
    mg.set_defaults(func=cmd_merge)

    rc = sub.add_parser("recheck", help="purity on saved mutants vs the saved null mutant")
    rc.add_argument("--mutations", required=True)
    rc.add_argument("--admission", required=True)
    rc.add_argument("--saved-jobs", required=True)
    rc.add_argument("--out", required=True)
    rc.set_defaults(func=cmd_recheck)

    k2 = sub.add_parser("k2-sample", help="seeded K2 fidelity sample from the job list")
    k2.add_argument("--jobs", required=True, help="build/scoring-jobs.jsonl")
    k2.add_argument("--sanitized", required=True, help="sanitized task export (domains)")
    k2.add_argument("--out", required=True)
    k2.add_argument("--n", type=int, default=K2_PAIRS)
    k2.add_argument("--seed", type=int, default=42)
    k2.set_defaults(func=cmd_k2_sample)

    rp = sub.add_parser("report", help="outcomes and exploratory tables of one run")
    rp.add_argument("--run", required=True)
    rp.add_argument("--mutations", required=True)
    rp.add_argument("--admission", required=True)
    rp.add_argument("--probe-touched", required=True)
    rp.add_argument("--n-boot", type=int, default=10_000)
    rp.set_defaults(func=cmd_report)

    pn = sub.add_parser("pins", help="digests the preregistration names")
    pn.add_argument("--root", default=".")
    pn.add_argument("--inputs", default=None, help="also digest a mounted inputs tree")
    pn.set_defaults(func=cmd_pins)

    gd = sub.add_parser("guard", help="refuse unregistered splits, code or inputs (containers)")
    gd.add_argument("--split", required=True, choices=["dev", "confirm", "reserve"])
    gd.add_argument("--src", default="/src")
    gd.add_argument("--inputs", default="/inputs")
    gd.set_defaults(func=cmd_guard)

    ex = sub.add_parser("export", help="releasable evidence of one run (no document content)")
    ex.add_argument("--run", required=True, help="run root with prep/, build/, score/")
    ex.add_argument("--out", required=True)
    ex.add_argument("--src", default=".", help="repository root (ledger check for non-dev runs)")
    ex.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CampaignError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
