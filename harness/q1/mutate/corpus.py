"""Corpus orchestration: candidate pool, compile filter, capped selection, layout.

Pipeline (``scripts/q1_generate_mutants.py`` exposes each step):

1. ``build_pool``: enumerate every substrate under a root and write each
   distinct CPU-side candidate to ``<pool>/kernels/<substrate>/<mutant_id>.py``
   with one row per candidate in ``<pool>/pool.jsonl``.
2. ``compile_pool`` (GPU-less container): compile the parent and every
   candidate at the parent's recorded specializations; ``<pool>/compile.jsonl``.
3. ``select``: drop compile failures, compile-equivalent and compile-duplicate
   candidates (when compile results exist), apply the family-stratified cap,
   assign the frozen split, and write the mutant layout and manifest.
4. ``build_controls``: hack-emulating controls for each substrate.

Every step refuses to overwrite its output and writes into a temporary
sibling directory that is renamed into place only on success.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from harness.q1.mutate import compiled as compiled_mod
from harness.q1.mutate.engine import enumerate_mutants, mutant_id
from harness.q1.mutate.fixtures import (
    HACK_KINDS,
    FixtureError,
    applicable,
    build_hack_control,
    mutant_control,
)
from harness.q1.mutate.operators import OPERATORS, registry_fingerprint
from harness.q1.mutate.sampling import (
    DEFAULT_CAP,
    DEFAULT_SEED,
    SPLIT_SEED,
    SPLIT_VERSION,
    problem_split_of,
    split_of,
    stratified_cap,
)
from harness.q1.schema import (
    KERNELBENCH_PROBLEMS_REVISION,
    SCHEMA_VERSION,
    canonical_json,
    iter_kernel_dirs,
    problem_relpath,
    sha256_bytes,
    sha256_file,
    validate_mutation,
)

PACKAGE_DIR = Path(__file__).resolve().parent
POOL_SCHEMA = "q1-mutant-pool/1"
CORPUS_SCHEMA = "q1-mutant-corpus/1"
CONTROLS_SCHEMA = "q1-hack-controls/1"


class CorpusError(RuntimeError):
    """Inputs are inconsistent or an output already exists."""


def package_sha256() -> str:
    """SHA-256 over every source file of the mutator package (path and content)."""
    digest = hashlib.sha256()
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        digest.update(path.relative_to(PACKAGE_DIR).as_posix().encode() + b"\0")
        digest.update(sha256_file(path).encode() + b"\n")
    return digest.hexdigest()


def mutator_identity() -> dict[str, Any]:
    return {
        "package_sha256": package_sha256(),
        "registry_fingerprint": registry_fingerprint(),
        "n_operators": len(OPERATORS),
        "schema_version": SCHEMA_VERSION,
    }


@contextlib.contextmanager
def staged_output(final: Path) -> Iterator[Path]:
    """Yield a temporary sibling of ``final``; rename it into place on success."""
    final = Path(final)
    if final.exists():
        raise CorpusError(f"{final} already exists; refusing to overwrite")
    final.parent.mkdir(parents=True, exist_ok=True)
    staging = final.with_name(f".{final.name}.tmp-{os.getpid()}")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    try:
        yield staging
        staging.rename(final)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=1, sort_keys=True, allow_nan=False) + "\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_substrates(root: Path) -> list[Any]:
    dirs = iter_kernel_dirs(Path(root))
    others = [d.kernel_id for d in dirs if d.kind != "substrate"]
    if others:
        raise CorpusError(f"{root} holds non-substrate directories: {others[:5]}")
    if not dirs:
        raise CorpusError(f"{root} holds no substrates")
    return dirs


# --- 1. pool -------------------------------------------------------------------


def build_pool(substrates_root: Path, pool_root: Path) -> dict[str, Any]:
    substrates = load_substrates(substrates_root)
    with staged_output(pool_root) as staging:
        rows: list[dict[str, Any]] = []
        summaries = []
        for sub in substrates:
            text = sub.kernel_path.read_text(encoding="utf-8")
            enumeration = enumerate_mutants(text)
            kernel_dir = staging / "kernels" / sub.kernel_id
            kernel_dir.mkdir(parents=True)
            (kernel_dir / "parent.py").write_text(text, encoding="utf-8")
            taken: set[str] = set()
            for cand in enumeration.distinct:
                ident = mutant_id(sub.kernel_id, cand, taken)
                (kernel_dir / f"{ident}.py").write_text(cand.source, encoding="utf-8")
                rows.append(
                    {
                        "mutant_id": ident,
                        "parent_substrate_id": sub.kernel_id,
                        "problem_id": sub.problem_id,
                        "operator": cand.operator,
                        "family": cand.family,
                        "rule_origin": cand.rule_origin,
                        "kernelbench_m_rule": cand.kbm_rule,
                        "site": cand.site,
                        "scope": cand.scope,
                        "function": cand.function,
                        "dedup_hash": cand.dedup_hash,
                        "detail": cand.detail,
                        "description": cand.description,
                        "kernel_sha256": sha256_bytes(cand.source.encode()),
                    }
                )
            summaries.append(
                {
                    "substrate_id": sub.kernel_id,
                    "problem_id": sub.problem_id,
                    "kernel_sha256": sha256_file(sub.kernel_path),
                    "parent_dedup_hash": enumeration.parent_hash,
                    "enumeration": enumeration.summary(),
                    "rejected": [
                        {
                            "operator": r.operator,
                            "site": f"kernel.py:{r.line}:{r.col}",
                            "reason": r.reason,
                            "duplicate_of": r.duplicate_of,
                        }
                        for r in enumeration.rejected
                    ],
                }
            )
        _write_jsonl(staging / "pool.jsonl", rows)
        manifest = {
            "schema": POOL_SCHEMA,
            "mutator": mutator_identity(),
            "substrates": summaries,
            "pool_sha256": sha256_file(staging / "pool.jsonl"),
            "n_candidates": len(rows),
        }
        _write_json(staging / "pool_manifest.json", manifest)
    return manifest


def _compile_batch(
    python: str, spec: Path, kernel_dir: Path, names: list[str], timeout_s: int
) -> dict[str, dict[str, Any]]:
    """Compile ``names`` in one fresh interpreter; return the results it printed."""
    argv = [python, "-m", "harness.q1.mutate.compiled", "--spec", str(spec), "--kernels"]
    argv += [str(kernel_dir / f"{n}.py") for n in names]
    env = dict(os.environ, TRITON_DISABLE_LINE_INFO="1")
    env.pop("TRITON_INTERPRET", None)  # the compile filter compiles; it never interprets
    try:
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            cwd=str(PACKAGE_DIR.parents[2]),
            check=False,
        )
        stdout = done.stdout
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
    results: dict[str, dict[str, Any]] = {}
    for line in stdout.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and "kernel" in record:
            results[Path(record["kernel"]).stem] = record
    return results


# --- 2. compile ----------------------------------------------------------------


def compile_pool(
    pool_root: Path,
    specializations_root: Path,
    *,
    workers: int = 8,
    timeout_s: int = 3600,
    python: str = sys.executable,
    batch_size: int | None = None,
) -> Path:
    """Compile parents and candidates (run inside a GPU-less container).

    ``batch_size`` splits each substrate's kernels into batches of at most that
    many (the parent in the first), so one substrate whose kernels take minutes
    each in ptxas (the pilot's FlagGems cumsum) uses several workers. Each kernel
    is compiled in a fresh interpreter batch exactly as before; results, the
    isolated retries and the rows written do not depend on the batching.
    """
    pool_root = Path(pool_root)
    out = pool_root / "compile.jsonl"
    if out.exists():
        raise CorpusError(f"{out} already exists; refusing to overwrite")
    rows = _read_jsonl(pool_root / "pool.jsonl")
    by_substrate: dict[str, list[str]] = {}
    for row in rows:
        by_substrate.setdefault(row["parent_substrate_id"], []).append(row["mutant_id"])

    def names_of(substrate_id: str) -> list[str]:
        return ["parent", *by_substrate.get(substrate_id, [])]

    def compile_batch(task: tuple[str, list[str]]) -> tuple[str, dict[str, dict[str, Any]]]:
        substrate_id, names = task
        spec = Path(specializations_root) / substrate_id / "specializations.json"
        if not spec.is_file():
            return substrate_id, {}
        kernel_dir = pool_root / "kernels" / substrate_id
        return substrate_id, _compile_batch(python, spec, kernel_dir, names, timeout_s)

    tasks: list[tuple[str, list[str]]] = []
    for substrate_id in sorted(by_substrate):
        names = names_of(substrate_id)
        size = batch_size or len(names)
        tasks += [(substrate_id, names[i : i + size]) for i in range(0, len(names), size)]
    merged: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in by_substrate}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for substrate_id, results in pool.map(compile_batch, tasks):
            merged[substrate_id].update(results)

    def finish(substrate_id: str) -> list[dict[str, Any]]:
        spec = Path(specializations_root) / substrate_id / "specializations.json"
        if not spec.is_file():
            return [
                {
                    "substrate_id": substrate_id,
                    "candidate": "parent",
                    "error": "no specializations.json",
                }
            ]
        kernel_dir = pool_root / "kernels" / substrate_id
        names = names_of(substrate_id)
        results = merged[substrate_id]
        # A batch that died (compiler crash, timeout) loses its remaining
        # kernels; retry each of them alone, twice, so one crashing mutant is
        # isolated and attributed to itself.
        for name in [n for n in names if n not in results]:
            for _attempt in range(2):
                results.update(_compile_batch(python, spec, kernel_dir, [name], timeout_s))
                if name in results:
                    break
            else:
                results[name] = {"error": "crash: no result after two isolated attempts"}
        out_rows = []
        for name in names:
            record = results[name]
            row = {"substrate_id": substrate_id, "candidate": name}
            if "hashes" in record:
                row["hashes"] = record["hashes"]
            else:
                row["error"] = record.get("error", "unknown")
            out_rows.append(row)
        return out_rows

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(finish, sorted(by_substrate)))
    staging = out.with_name(f".{out.name}.tmp-{os.getpid()}")
    _write_jsonl(staging, [row for chunk in results for row in chunk])
    staging.rename(out)
    return out


def _compile_status(
    pool_root: Path, rows: list[dict[str, Any]]
) -> tuple[dict[str, tuple[str, str | None]], dict[str, dict[str, Any]]]:
    """Per-mutant (status, compiled_key) and per-substrate compile summaries."""
    compiled_rows = _read_jsonl(Path(pool_root) / "compile.jsonl")
    by_key = {(r["substrate_id"], r["candidate"]): r for r in compiled_rows}
    texts = {}
    status: dict[str, tuple[str, str | None]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for substrate_id in sorted({r["parent_substrate_id"] for r in rows}):
        parent = by_key.get((substrate_id, "parent"), {})
        if "hashes" not in parent:
            raise CorpusError(f"{substrate_id}: parent does not compile: {parent.get('error')}")
        kernel_dir = Path(pool_root) / "kernels" / substrate_id
        parent_text = (kernel_dir / "parent.py").read_text()
        parent_key = compiled_mod.compiled_key(
            parent["hashes"], compiled_mod.launch_scope_hash(parent_text)
        )
        seen: dict[str, str] = {}
        counts: Counter[str] = Counter()
        for row in (r for r in rows if r["parent_substrate_id"] == substrate_id):
            ident = row["mutant_id"]
            record = by_key.get((substrate_id, ident), {})
            texts[ident] = (kernel_dir / f"{ident}.py").read_text()
            result = compiled_mod.classify(
                parent_key, texts[ident], record.get("hashes"), seen, ident
            )
            status[ident] = result
            counts[result[0]] += 1
            if result[0] == "compile-fail":
                kind = str(record.get("error", "missing")).split(":", 1)[0]
                counts[f"compile-fail:{kind}"] += 1
        summaries[substrate_id] = {
            "parent_compiled_key": parent_key,
            **dict(sorted(counts.items())),
        }
    return status, summaries


# --- 3. select -----------------------------------------------------------------


def select(
    pool_root: Path,
    substrates_root: Path,
    out_root: Path,
    *,
    seed: int = DEFAULT_SEED,
    cap: int = DEFAULT_CAP,
    require_compile: bool = True,
    controls_root: Path | None = None,
) -> dict[str, Any]:
    pool_root = Path(pool_root)
    pool_manifest = json.loads((pool_root / "pool_manifest.json").read_text())
    if pool_manifest["pool_sha256"] != sha256_file(pool_root / "pool.jsonl"):
        raise CorpusError("pool.jsonl does not match its manifest")
    if pool_manifest["mutator"]["package_sha256"] != package_sha256():
        raise CorpusError("the pool was built by a different mutator revision; rebuild it")
    substrates = {d.kernel_id: d for d in load_substrates(substrates_root)}
    rows = _read_jsonl(pool_root / "pool.jsonl")
    for summary in pool_manifest["substrates"]:
        sub = substrates.get(summary["substrate_id"])
        if sub is None or sha256_file(sub.kernel_path) != summary["kernel_sha256"]:
            raise CorpusError(f"{summary['substrate_id']}: substrate changed since the pool")
    compile_path = pool_root / "compile.jsonl"
    compile_checked = compile_path.exists()
    if require_compile and not compile_checked:
        raise CorpusError(
            "compile.jsonl is missing (run the compile step, or pass "
            "--no-require-compile for a CPU-only preview)"
        )
    status: dict[str, tuple[str, str | None]] = {}
    compile_summaries: dict[str, dict[str, Any]] = {}
    if compile_checked:
        status, compile_summaries = _compile_status(pool_root, rows)
    eligible = [r for r in rows if not compile_checked or status[r["mutant_id"]][0] == "distinct"]

    selected_rows: list[dict[str, Any]] = []
    substrate_summaries = []
    with staged_output(out_root) as staging:
        for summary in pool_manifest["substrates"]:
            substrate_id = summary["substrate_id"]
            sub = substrates[substrate_id]
            pool_rows = [r for r in eligible if r["parent_substrate_id"] == substrate_id]
            chosen = stratified_cap(
                pool_rows,
                family=lambda r: r["family"],
                operator=lambda r: r["operator"],
                content_key=lambda r: r["dedup_hash"],
                substrate_id=substrate_id,
                cap=cap,
                seed=seed,
            )
            for pick in chosen:
                row = pick.item
                mutation = validate_mutation(
                    {
                        "mutant_id": row["mutant_id"],
                        "parent_substrate_id": substrate_id,
                        "operator": row["operator"],
                        "family": row["family"],
                        "site": row["site"],
                        "seed": seed,
                        "triton_disable_line_info": True,
                        "dedup_hash": row["dedup_hash"],
                        "rule_origin": row["rule_origin"],
                        "kernelbench_m_rule": row["kernelbench_m_rule"],
                        "description": row["description"],
                        "schema_version": SCHEMA_VERSION,
                    }
                )
                target = staging / row["mutant_id"]
                shutil.copytree(sub.path, target)
                for leftover in ("mutation.json", "control.json"):
                    (target / leftover).unlink(missing_ok=True)
                source = (
                    pool_root / "kernels" / substrate_id / f"{row['mutant_id']}.py"
                ).read_text()
                if sha256_bytes(source.encode()) != row["kernel_sha256"]:
                    raise CorpusError(f"{row['mutant_id']}: pool kernel was modified")
                (target / "kernel.py").write_text(source, encoding="utf-8")
                _write_json(target / "mutation.json", mutation)
                selected_rows.append(
                    {
                        **{
                            k: row[k]
                            for k in (
                                "mutant_id",
                                "parent_substrate_id",
                                "problem_id",
                                "operator",
                                "family",
                                "rule_origin",
                                "kernelbench_m_rule",
                                "site",
                                "dedup_hash",
                            )
                        },
                        "compiled_key": status.get(row["mutant_id"], (None, None))[1],
                        "split": split_of(substrate_id, row["dedup_hash"], SPLIT_SEED),
                        "problem_split": problem_split_of(row["problem_id"], SPLIT_SEED),
                        "n_operator_stratum": pick.n_operator_stratum,
                        "k_operator_stratum": pick.k_operator_stratum,
                        "inclusion_probability": pick.inclusion_probability,
                        "weight": pick.weight,
                    }
                )
            substrate_summaries.append(
                {
                    "substrate_id": substrate_id,
                    "problem_id": sub.problem_id,
                    "kernel_sha256": summary["kernel_sha256"],
                    "cpu_distinct": summary["enumeration"]["distinct"],
                    "compile": compile_summaries.get(substrate_id),
                    "eligible": len(pool_rows),
                    "selected": len(chosen),
                    "selected_by_family": dict(sorted(Counter(p.family for p in chosen).items())),
                }
            )
        _write_jsonl(staging / "mutants.jsonl", selected_rows)
        manifest = {
            "schema": CORPUS_SCHEMA,
            "mutator": mutator_identity(),
            "seed": seed,
            "cap": cap,
            "split_version": SPLIT_VERSION,
            "split_seed": SPLIT_SEED,
            "compile_checked": compile_checked,
            "triton_disable_line_info": True,
            "pool_sha256": pool_manifest["pool_sha256"],
            "compile_sha256": sha256_file(compile_path) if compile_checked else None,
            "mutants_sha256": sha256_file(staging / "mutants.jsonl"),
            "substrates": substrate_summaries,
            "totals": {
                "selected": len(selected_rows),
                "by_family": dict(sorted(Counter(r["family"] for r in selected_rows).items())),
                "by_origin": dict(sorted(Counter(r["rule_origin"] for r in selected_rows).items())),
                "by_split": dict(sorted(Counter(r["split"] for r in selected_rows).items())),
            },
        }
        _write_json(staging / "manifest.json", manifest)
    if controls_root is not None:
        _mutant_controls(Path(out_root), substrates, selected_rows, Path(controls_root))
    return manifest


def _mutant_controls(
    mutants_root: Path, substrates: dict[str, Any], rows: list[dict[str, Any]], out_root: Path
) -> None:
    with staged_output(out_root) as staging:
        written = []
        for row in rows:
            sub = substrates[row["parent_substrate_id"]]
            mutation = json.loads((mutants_root / row["mutant_id"] / "mutation.json").read_text())
            text = (mutants_root / row["mutant_id"] / "kernel.py").read_text()
            built = mutant_control(mutant=mutation, substrate=sub.substrate, kernel_text=text)
            if built is None:
                continue
            kernel_text, control = built
            target = staging / control["control_id"]
            target.mkdir()
            (target / "kernel.py").write_text(kernel_text, encoding="utf-8")
            _write_json(target / "control.json", control)
            written.append(control["control_id"])
        _write_json(
            staging / "controls_manifest.json",
            {
                "schema": CONTROLS_SCHEMA,
                "mutator": mutator_identity(),
                "kind": "hack-emulating-mutants",
                "controls": written,
            },
        )


# --- 4. hack controls ----------------------------------------------------------


def problem_source_for(problem_id: str, kernelbench_root: Path | None) -> str:
    """Problem text from a KernelBench checkout or problem tree, or the vendored copy.

    ``kernelbench_root`` may be a checkout (``<root>/KernelBench/levelN``) or a
    problem tree (``<root>/levelN``). ``None`` reads the core's vendored,
    hash-checked KernelBench@423217d9 problems (``harness.q1.problems``).
    """
    if kernelbench_root is None:
        from harness.q1.problems import ProblemError, load_problem_source

        try:
            return load_problem_source(problem_id)
        except ProblemError as exc:
            raise CorpusError(str(exc)) from exc
    root = Path(kernelbench_root)
    relative = problem_relpath(problem_id)
    for candidate in (root / "KernelBench" / relative, root / relative):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    raise CorpusError(f"{problem_id}: {relative} not found under {root}")


def build_controls(
    substrates_root: Path,
    kernelbench_root: Path | None,
    out_root: Path,
    *,
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    """Hack-emulating controls for every applicable (substrate, hack kind).

    ``kernelbench_root=None`` uses the vendored, hash-checked problems.
    """
    revision = None
    if kernelbench_root is not None:
        kernelbench_root = Path(kernelbench_root)
        revision = _git_head(kernelbench_root)
        if revision is not None and revision != KERNELBENCH_PROBLEMS_REVISION:
            raise CorpusError(
                f"KernelBench checkout is at {revision}, expected {KERNELBENCH_PROBLEMS_REVISION}"
            )
    wanted = [k for k in HACK_KINDS if kinds is None or k.name in kinds]
    substrates = load_substrates(substrates_root)
    with staged_output(out_root) as staging:
        written, skipped = [], []
        for sub in substrates:
            problem_source = problem_source_for(sub.problem_id, kernelbench_root)
            kernel_text = sub.kernel_path.read_text(encoding="utf-8")
            for kind in wanted:
                if not applicable(kind, sub.problem_id, problem_source):
                    skipped.append(
                        {
                            "substrate_id": sub.kernel_id,
                            "kind": kind.name,
                            "reason": "not applicable",
                        }
                    )
                    continue
                try:
                    text, control = build_hack_control(
                        kind,
                        substrate=sub.substrate,
                        substrate_kernel=kernel_text,
                        problem_source=problem_source,
                    )
                except FixtureError as exc:
                    skipped.append(
                        {"substrate_id": sub.kernel_id, "kind": kind.name, "reason": str(exc)}
                    )
                    continue
                target = staging / control["control_id"]
                target.mkdir()
                (target / "kernel.py").write_text(text, encoding="utf-8")
                _write_json(target / "control.json", control)
                written.append(
                    {
                        "control_id": control["control_id"],
                        "kind": kind.name,
                        "problem_id": sub.problem_id,
                        "kernel_sha256": sha256_bytes(text.encode()),
                    }
                )
        manifest = {
            "schema": CONTROLS_SCHEMA,
            "mutator": mutator_identity(),
            "kind": "hack-emulating-wrappers",
            "kernelbench_revision": KERNELBENCH_PROBLEMS_REVISION,
            "kernelbench_revision_verified": revision is not None or kernelbench_root is None,
            "kernelbench_source": "vendored-hash-checked"
            if kernelbench_root is None
            else ("git-checkout" if revision is not None else "directory"),
            "controls": written,
            "skipped": skipped,
        }
        _write_json(staging / "controls_manifest.json", manifest)
    return manifest


def _git_head(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    done = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return done.stdout.strip() if done.returncode == 0 else None
