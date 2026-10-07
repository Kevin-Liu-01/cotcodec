#!/usr/bin/env python3
"""Build the Q3 K1 study bundle in two stages (fetch with network, build offline).

``paradocs-probe``  stream the head of ParaDocs files through the reimplemented
                    filter and report kept tokens per GB of compressed input;
                    nothing is stored except the JSON report.
``fetch-raw``       download pinned Belebele, FineWeb-2 and FineWeb files into a
                    raw directory (sizes and SHA-256 checked against the Hub's LFS
                    ids) and stream ParaDocs through the filter until each pair's
                    token quota is met, keeping only the filtered documents and a
                    consumption record (file, LFS id, compressed bytes, lines).
``build``           read the raw directory read-only, with no network, and write
                    the deterministic bundle (training stream, evaluation
                    contexts, queries, options, prompt ledger, dedup and quota
                    reports, per-source licence manifest).

Exit codes: 0 success, 2 contract or integrity failure.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import time
from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import sparse_indexer_data as sid  # noqa: E402
from harness.sparse_indexer_data import (  # noqa: E402
    BILINGUAL_PAIRS,
    CROSS_SCRIPT_BILINGUAL,
    CROSS_SCRIPT_HELDOUT,
    DEPTHS,
    HELDOUT,
    LANGUAGES,
    MONOLINGUAL_TRAINING,
    SAME_SCRIPT_BILINGUAL,
    SAME_SCRIPT_HELDOUT,
    DataContractError,
    DedupIndex,
    DedupStats,
    ParadocsFilter,
    ParadocsStats,
    Tokenizer,
)

BILINGUAL_SEQUENCES_TRAIN = 1221
MONOLINGUAL_SEQUENCES_TRAIN = 1220
BILINGUAL_SEQUENCES_DEV = 32
MONOLINGUAL_SEQUENCES_DEV = 32
BILINGUAL_SEQUENCES = BILINGUAL_SEQUENCES_TRAIN + BILINGUAL_SEQUENCES_DEV
MONOLINGUAL_SEQUENCES = MONOLINGUAL_SEQUENCES_TRAIN + MONOLINGUAL_SEQUENCES_DEV
PAIR_QUOTA_TOKENS = BILINGUAL_SEQUENCES * (sid.SEQUENCE_LENGTH - 1) // len(BILINGUAL_PAIRS)
MONO_QUOTA_TOKENS = MONOLINGUAL_SEQUENCES * (sid.SEQUENCE_LENGTH - 1) // len(MONOLINGUAL_TRAINING)
# Pools exceed the packed demand because each sequence discards the remainder
# of the item that overflows it (a bilingual pair is never split across
# sequences); with items capped at 2 x 512 tokens the expected loss is about 5%.
COLLECT_MARGIN = 1.2
BILINGUAL_SIDE_MAX_TOKENS = 512
# Same-script pairs over-collect so a cross-script shortfall can be refilled
# from them in equal shares (registered shortfall rule).
SAME_SCRIPT_COLLECT_FACTOR = 1.75
# Registered streaming cap per cross-script pair. The yield probe (2026-10-06)
# measured 279K, 207K and 331K kept tokens per GB for en-th, en-hi and en-km, so
# the 1.2x quota needs about 6.3, 8.5 and 5.3 GB; en-km's files hold 4.10 GB.
CROSS_SCRIPT_CAP_BYTES = 9_000_000_000
SAME_SCRIPT_CAP_BYTES = 2_000_000_000
DEV_FAMILIES_PER_PAIR = 20
ML_PROMPTS_EN = 100
ML_PROMPTS_X = 100
NEEDLE_ABSENT_FAMILIES = 300
LICENSES = {
    "belebele": "CC-BY-SA-4.0",
    "fineweb-2": "ODC-By-1.0 (plus Common Crawl terms of use)",
    "fineweb": "ODC-By-1.0 (plus Common Crawl terms of use)",
    "paradocs": "Apache-2.0 packaging (README); underlying ParaCrawl text is not owned by "
                "the packager; ParaCrawl's CC0 covers its packaging only",
    "qwen3-0.6b-base-tokenizer": "Apache-2.0",
}


def _hf_url(repo: str, revision: str, path: str) -> str:
    return f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{path}"


def _paths_info(repo: str, revision: str, paths: Sequence[str]) -> dict[str, dict[str, Any]]:
    from huggingface_hub import HfApi

    infos = HfApi().get_paths_info(repo, list(paths), repo_type="dataset", revision=revision)
    out: dict[str, dict[str, Any]] = {}
    for info in infos:
        lfs = getattr(info, "lfs", None)
        out[info.path] = {
            "size": int(getattr(info, "size", 0) or 0),
            "lfs_sha256": getattr(lfs, "sha256", None) if lfs else None,
            "blob_id": getattr(info, "blob_id", None),
        }
    return out


def _list_files(repo: str, revision: str, folder: str) -> list[dict[str, Any]]:
    from huggingface_hub import HfApi

    entries = HfApi().list_repo_tree(repo, path_in_repo=folder, repo_type="dataset",
                                     revision=revision)
    files = []
    for entry in entries:
        if getattr(entry, "size", None) is None:
            continue
        lfs = getattr(entry, "lfs", None)
        files.append({"path": entry.path, "size": int(entry.size),
                      "lfs_sha256": getattr(lfs, "sha256", None) if lfs else None})
    return sorted(files, key=lambda item: item["path"])


def _stream_chunks(url: str, max_bytes: int | None) -> Iterator[bytes]:
    """File bytes of ``url`` (any transport Content-Encoding is decoded first)."""

    import httpx

    sent = 0
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes(1 << 20):
            if max_bytes is not None and sent >= max_bytes:
                return
            if max_bytes is not None and sent + len(chunk) > max_bytes:
                chunk = chunk[: max_bytes - sent]
            sent += len(chunk)
            yield chunk


def _download(url: str, destination: Path, expected_sha256: str | None, size: int) -> dict:
    import httpx

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        actual = sid.sha256_file(destination)
        if expected_sha256 and actual != expected_sha256:
            raise DataContractError(f"{destination} exists with a different digest")
        return {"sha256": actual, "bytes": destination.stat().st_size, "reused": True}
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    written = 0
    with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_bytes(1 << 22):
                handle.write(chunk)
                digest.update(chunk)
                written += len(chunk)
    actual = digest.hexdigest()
    if expected_sha256 and actual != expected_sha256:
        temporary.unlink()
        raise DataContractError(f"{url}: sha256 {actual} != LFS {expected_sha256}")
    if size and written != size:
        temporary.unlink()
        raise DataContractError(f"{url}: {written} bytes != Hub size {size}")
    os.replace(temporary, destination)
    return {"sha256": actual, "bytes": written, "reused": False}


# --------------------------------------------------------------------------- #
# ParaDocs streaming
# --------------------------------------------------------------------------- #


def _paradocs_files(pair: str) -> list[dict[str, Any]]:
    folder = f"data/{pair}/{sid.PARADOCS_SOURCE[pair]}"
    return _list_files(sid.PARADOCS_REPO, sid.PARADOCS_REVISION, folder)


def stream_paradocs_pair(
    pair: str,
    tokenizer: Tokenizer,
    *,
    token_quota: int | None,
    max_bytes: int,
    cfg: ParadocsFilter,
    sink: Any | None = None,
    files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Stream the pair's registered ParaDocs folder in file-name order through the filter.

    Stops when ``token_quota`` item tokens are kept or ``max_bytes`` compressed
    bytes are consumed or the files end. ``sink`` (a callable) receives every
    kept document record; the probe passes ``None`` and stores nothing.
    """

    files = files if files is not None else _paradocs_files(pair)
    sep = tokenizer.encode("\n\n")
    record: dict[str, Any] = {"pair": pair, "files": [], "kept_item_tokens": 0,
                              "kept_en_tokens": 0, "kept_x_tokens": 0, "kept_en_chars": 0,
                              "kept_x_chars": 0, "doc_lines": [], "stop_reason": "files-ended"}
    consumed_total = 0
    started = time.time()
    for file in files:
        if consumed_total >= max_bytes:
            record["stop_reason"] = "byte-cap"
            break
        url = _hf_url(sid.PARADOCS_REPO, sid.PARADOCS_REVISION, file["path"])
        reader = sid.CountingReader(_stream_chunks(url, max_bytes - consumed_total))
        stats = ParadocsStats()
        ordinal = 0
        quota_met = False
        try:
            lines = sid.gzip_text_lines(reader)  # type: ignore[arg-type]
            docs = sid.paradocs_documents(sid.paradocs_rows(lines), cfg, stats)
            batch: list[list] = []

            def flush(batch: list[list], file_name: str) -> None:
                nonlocal ordinal
                sides = [sid.document_sides(doc) for doc in batch]
                encoded = tokenizer.encode_batch([s for pair_ in sides for s in pair_])
                for index, doc in enumerate(batch):
                    en_text, x_text = sides[index]
                    en_tok, x_tok = encoded[2 * index], encoded[2 * index + 1]
                    item_tokens = len(en_tok) + len(sep) + len(x_tok)
                    record["kept_item_tokens"] += item_tokens
                    record["kept_en_tokens"] += len(en_tok)
                    record["kept_x_tokens"] += len(x_tok)
                    record["kept_en_chars"] += len(en_text)
                    record["kept_x_chars"] += len(x_text)
                    record["doc_lines"].append(len(doc))
                    if sink is not None:
                        sink({"doc_id": sid.document_id(pair, file_name, ordinal, doc),
                              "en": en_text, "x": x_text, "lines": len(doc)})
                    ordinal += 1

            file_name = file["path"].rsplit("/", 1)[-1]
            for doc in docs:
                batch.append(doc)
                if len(batch) >= 256:
                    flush(batch, file_name)
                    batch = []
                    if token_quota is not None and record["kept_item_tokens"] >= token_quota:
                        quota_met = True
                        break
            if batch:
                flush(batch, file_name)
                if token_quota is not None and record["kept_item_tokens"] >= token_quota:
                    quota_met = True
        except EOFError:
            # A byte cap inside a gzip member ends the stream mid-member.
            pass
        consumed_total += reader.consumed
        record["files"].append({**file, "bytes_consumed": reader.consumed,
                                "filter": stats.as_dict()})
        if quota_met:
            record["stop_reason"] = "quota-met"
            break
    lines = np.asarray(record.pop("doc_lines") or [0])
    record["kept_documents"] = int(sum(f["filter"]["kept_documents"] for f in record["files"]))
    record["doc_lines_percentiles"] = {
        str(q): float(np.percentile(lines, q)) for q in (10, 50, 90, 99)
    }
    record["bytes_consumed"] = consumed_total
    record["kept_item_tokens_per_gb"] = (
        record["kept_item_tokens"] / (consumed_total / 1e9) if consumed_total else 0.0
    )
    record["seconds"] = round(time.time() - started, 1)
    return record


def cmd_paradocs_probe(args: argparse.Namespace) -> int:
    tokenizer = Tokenizer(args.tokenizer)
    cfg = ParadocsFilter()
    report: dict[str, Any] = {
        "probe": "paradocs-yield",
        "paradocs_revision": sid.PARADOCS_REVISION,
        "filter": cfg.__dict__ if hasattr(cfg, "__dict__") else {
            "minimum_size": cfg.minimum_size, "frequency_cutoff": cfg.frequency_cutoff,
            "lid_cutoff": cfg.lid_cutoff, "min_avg_score": cfg.min_avg_score},
        "tokenizer_sha256": tokenizer.sha256,
        "pair_quota_tokens": PAIR_QUOTA_TOKENS,
        "stored": "nothing but this report",
        "pairs": {},
    }
    for pair in args.pairs:
        cap = args.max_bytes_cross if pair in CROSS_SCRIPT_BILINGUAL else args.max_bytes_same
        result = stream_paradocs_pair(pair, tokenizer, token_quota=None, max_bytes=cap, cfg=cfg)
        per_gb = result["kept_item_tokens_per_gb"]
        result["projected_gb_for_quota"] = PAIR_QUOTA_TOKENS / per_gb if per_gb else None
        report["pairs"][pair] = result
        print(json.dumps({pair: {k: result[k] for k in (
            "bytes_consumed", "kept_documents", "kept_item_tokens", "kept_item_tokens_per_gb",
            "projected_gb_for_quota", "seconds")}}), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


# --------------------------------------------------------------------------- #
# fetch-raw
# --------------------------------------------------------------------------- #


def _fetch_pair(pair: str, raw_dir: str, tokenizer_path: str, cross_cap: int,
                same_cap: int) -> dict[str, Any]:
    """Stream one ParaDocs pair into ``paradocs/<pair>.jsonl.gz`` plus its record (one process)."""

    out_dir = Path(raw_dir) / "paradocs"
    destination = out_dir / f"{pair}.jsonl.gz"
    record_path = out_dir / f"{pair}.record.json"
    if destination.exists() and record_path.exists():
        # A completed pair from an interrupted fetch: reuse it after re-hashing.
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if sid.sha256_file(destination) != record["filtered_file_sha256"]:
            raise DataContractError(f"{destination} differs from its record")
        return record
    if destination.exists():
        raise DataContractError(f"{destination} exists without a record; remove it")
    tokenizer = Tokenizer(Path(tokenizer_path))
    same = pair in SAME_SCRIPT_BILINGUAL
    quota = int(PAIR_QUOTA_TOKENS * COLLECT_MARGIN * (SAME_SCRIPT_COLLECT_FACTOR if same
                                                      else 1.0))
    temporary = destination.with_suffix(".part")
    # A fixed gzip header (no file name, mtime 0) keeps the filtered file's digest a
    # function of its content.
    with temporary.open("wb") as raw_handle, gzip.GzipFile(
        filename="", mode="wb", fileobj=raw_handle, compresslevel=6, mtime=0
    ) as compressed, io.TextIOWrapper(compressed, encoding="utf-8") as handle:

        def sink(row: dict[str, Any], handle: Any = handle) -> None:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

        record = stream_paradocs_pair(pair, tokenizer, token_quota=quota,
                                      max_bytes=same_cap if same else cross_cap,
                                      cfg=ParadocsFilter(), sink=sink)
    os.replace(temporary, destination)
    record["collect_quota_tokens"] = quota
    record["source_folder"] = sid.PARADOCS_SOURCE[pair]
    record["filtered_file_sha256"] = sid.sha256_file(destination)
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def cmd_fetch_raw(args: argparse.Namespace) -> int:
    raw: Path = args.raw_dir
    raw.mkdir(parents=True, exist_ok=True)
    tokenizer = Tokenizer(args.tokenizer)
    manifest: dict[str, Any] = {"schema": "cotcodec-k1-raw-v1", "tokenizer_sha256":
                                tokenizer.sha256, "sources": {}}
    # Belebele.
    paths = [f"data/{LANGUAGES[c].belebele}.jsonl" for c in sid.BELEBELE_LANGUAGES]
    info = _paths_info(sid.BELEBELE_REPO, sid.BELEBELE_REVISION, paths)
    manifest["sources"]["belebele"] = {
        "repo": sid.BELEBELE_REPO, "revision": sid.BELEBELE_REVISION,
        "license": LICENSES["belebele"], "files": {}}
    for path in paths:
        meta = info[path]
        result = _download(_hf_url(sid.BELEBELE_REPO, sid.BELEBELE_REVISION, path),
                           raw / "belebele" / Path(path).name, meta["lfs_sha256"], meta["size"])
        manifest["sources"]["belebele"]["files"][path] = {**meta, **result}
    # FineWeb-2 test splits (training monolingual + every needle language but English).
    configs = sorted({sid.FINEWEB2_CONFIG[c] for c in MONOLINGUAL_TRAINING + HELDOUT})
    paths = [f"data/{config}/test/000_00000.parquet" for config in configs]
    info = _paths_info(sid.FINEWEB2_REPO, sid.FINEWEB2_REVISION, paths)
    manifest["sources"]["fineweb-2"] = {
        "repo": sid.FINEWEB2_REPO, "revision": sid.FINEWEB2_REVISION,
        "license": LICENSES["fineweb-2"], "files": {}}
    for path in paths:
        if path not in info:
            raise DataContractError(f"FineWeb-2 file missing at the pinned revision: {path}")
        meta = info[path]
        result = _download(_hf_url(sid.FINEWEB2_REPO, sid.FINEWEB2_REVISION, path),
                           raw / "fineweb-2" / path.split("/")[1] / "test-000_00000.parquet",
                           meta["lfs_sha256"], meta["size"])
        manifest["sources"]["fineweb-2"]["files"][path] = {**meta, **result}
    # FineWeb English haystack shard.
    info = _paths_info(sid.FINEWEB_REPO, sid.FINEWEB_REVISION, [sid.FINEWEB_EN_SHARD])
    meta = info[sid.FINEWEB_EN_SHARD]
    result = _download(_hf_url(sid.FINEWEB_REPO, sid.FINEWEB_REVISION, sid.FINEWEB_EN_SHARD),
                       raw / "fineweb" / "CC-MAIN-2025-26-004_00046.parquet",
                       meta["lfs_sha256"], meta["size"])
    manifest["sources"]["fineweb"] = {
        "repo": sid.FINEWEB_REPO, "revision": sid.FINEWEB_REVISION,
        "license": LICENSES["fineweb"], "files": {sid.FINEWEB_EN_SHARD: {**meta, **result}}}
    # ParaDocs, streamed and filtered.
    cfg = ParadocsFilter()
    manifest["sources"]["paradocs"] = {
        "repo": sid.PARADOCS_REPO, "revision": sid.PARADOCS_REVISION,
        "filter_tool_reimplemented_from": f"rewicks/ParaDocs@{sid.PARADOCS_TOOL_REVISION}",
        "filter": {"minimum_size": cfg.minimum_size, "frequency_cutoff": cfg.frequency_cutoff,
                   "lid_cutoff": cfg.lid_cutoff, "min_avg_score": cfg.min_avg_score},
        "license": LICENSES["paradocs"], "pairs": {}}
    out_dir = raw / "paradocs"
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(pair, str(raw), str(args.tokenizer), args.cross_script_cap_bytes,
             args.same_script_cap_bytes) for pair in BILINGUAL_PAIRS]
    with ProcessPoolExecutor(max_workers=len(jobs)) as pool:
        records = list(pool.map(_fetch_pair, *zip(*jobs, strict=True)))
    for pair, record in zip(BILINGUAL_PAIRS, records, strict=True):
        manifest["sources"]["paradocs"]["pairs"][pair] = record
        print(json.dumps({pair: {k: record[k] for k in (
            "bytes_consumed", "kept_item_tokens", "stop_reason")}}), flush=True)
    target = raw / "raw-manifest.json"
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"raw_manifest_sha256": sid.sha256_file(target)}))
    return 0


# --------------------------------------------------------------------------- #
# build (offline, deterministic)
# --------------------------------------------------------------------------- #


def _parquet_texts(path: Path) -> list[tuple[str, str]]:
    import pyarrow.parquet as pq

    table = pq.read_table(path, columns=["id", "text"])
    ids = table.column("id").to_pylist()
    texts = table.column("text").to_pylist()
    return [(str(i), str(t)) for i, t in zip(ids, texts, strict=True)]


def _ordered(rows: list[tuple[str, str]], salt: str) -> list[tuple[str, str]]:
    keyed = {row[0]: row for row in rows}
    if len(keyed) != len(rows):
        raise DataContractError(f"{salt}: duplicate document ids")
    return [keyed[k] for k in sid.stable_order(keyed, salt)]


class _Collector:
    """Tokenise documents in a deterministic order and keep clean ones."""

    def __init__(self, tokenizer: Tokenizer, dedup: DedupIndex) -> None:
        self.tokenizer = tokenizer
        self.dedup = dedup

    def take(
        self,
        rows: list[tuple[str, str]],
        *,
        quota_tokens: int | None,
        script_filter: bool,
        stats: DedupStats,
        latin_expected: str | None = None,
        min_tokens: int = 1,
        max_tokens: int | None = None,
        truncate: int | None = None,
        limit_docs: int | None = None,
    ) -> list[tuple[str, list[int]]]:
        kept: list[tuple[str, list[int]]] = []
        total = 0
        for start in range(0, len(rows), 512):
            chunk = rows[start : start + 512]
            texts = [text for _, text in chunk]
            encoded = self.tokenizer.encode_batch(texts)
            for (doc_id, text), tokens in zip(chunk, encoded, strict=True):
                if script_filter and not sid.passes_script_filter(text):
                    stats.checked += 1
                    stats.script += 1
                    continue
                if latin_expected and sid.reads_as_held_out_latin(text, latin_expected):
                    stats.checked += 1
                    stats.latin += 1
                    continue
                too_long = max_tokens is not None and len(tokens) > max_tokens
                if len(tokens) < min_tokens or too_long:
                    continue
                if not self.dedup.check(tokens, stats):
                    continue
                if truncate is not None:
                    tokens = tokens[:truncate]
                kept.append((doc_id, tokens))
                total += len(tokens)
                if quota_tokens is not None and total >= quota_tokens:
                    return kept
                if limit_docs is not None and len(kept) >= limit_docs:
                    return kept
        if quota_tokens is not None:
            raise DataContractError(f"pool exhausted at {total} of {quota_tokens} tokens")
        return kept


def _bilingual_items(
    pair: str, rows: list[dict[str, Any]], tokenizer: Any, dedup: DedupIndex, sep: list[int],
    quota: int, stats: DedupStats, side_max: int = BILINGUAL_SIDE_MAX_TOKENS,
) -> tuple[list[tuple[str, list[int]]], int]:
    items: list[tuple[str, list[int]]] = []
    total = 0
    for start in range(0, len(rows), 512):
        chunk = rows[start : start + 512]
        encoded = tokenizer.encode_batch([s for row in chunk for s in (row["en"], row["x"])])
        for index, row in enumerate(chunk):
            en_tok, x_tok = encoded[2 * index], encoded[2 * index + 1]
            stats.checked += 1
            if not (sid.passes_script_filter(row["en"]) and sid.passes_script_filter(row["x"])):
                stats.script += 1
                continue
            if sid.reads_as_held_out_latin(row["en"], "en") or sid.reads_as_held_out_latin(
                row["x"], pair.split("-")[1]
            ):
                stats.latin += 1
                continue
            local = DedupStats()
            if not (dedup.check(en_tok, local) and dedup.check(x_tok, local)):
                # One removal per document, under the first failing check.
                if local.exact_ngram:
                    stats.exact_ngram += 1
                else:
                    stats.minhash += 1
                continue
            en_tok, x_tok = en_tok[:side_max], x_tok[:side_max]
            coin = hashlib.sha256(f"order|{row['doc_id']}".encode()).digest()[0] & 1
            item = (x_tok + sep + en_tok) if coin else (en_tok + sep + x_tok)
            items.append((row["doc_id"], item))
            total += len(item)
            if total >= quota:
                return items, total
    return items, total


@dataclass(frozen=True)
class BuildParams:
    """Registered bundle sizes; the CPU doctor builds a tiny bundle with the same code."""

    sequence_length: int = sid.SEQUENCE_LENGTH
    context_length: int = sid.CONTEXT_LENGTH
    sink: int = sid.SINK_TOKEN_ID
    bilingual_train: int = BILINGUAL_SEQUENCES_TRAIN
    mono_train: int = MONOLINGUAL_SEQUENCES_TRAIN
    bilingual_dev: int = BILINGUAL_SEQUENCES_DEV
    mono_dev: int = MONOLINGUAL_SEQUENCES_DEV
    mono_item_max: int = sid.MONO_ITEM_MAX_TOKENS
    mono_min_tokens: int = 16
    haystack_min: int = sid.HAYSTACK_DOC_MIN_TOKENS
    haystack_max: int = sid.HAYSTACK_DOC_MAX_TOKENS
    haystack_docs: int = 4000
    haystack_draw: int = 256
    dev_families_per_pair: int = DEV_FAMILIES_PER_PAIR
    ml_en: int = ML_PROMPTS_EN
    ml_x: int = ML_PROMPTS_X
    absent: int = NEEDLE_ABSENT_FAMILIES
    collect_margin: float = COLLECT_MARGIN
    bilingual_side_max: int = BILINGUAL_SIDE_MAX_TOKENS
    max_bytes: int = 512 * 1024**2

    @property
    def pair_quota(self) -> int:
        sequences = self.bilingual_train + self.bilingual_dev
        return sequences * (self.sequence_length - 1) // len(BILINGUAL_PAIRS)

    @property
    def mono_quota(self) -> int:
        sequences = self.mono_train + self.mono_dev
        return sequences * (self.sequence_length - 1) // len(MONOLINGUAL_TRAINING)


@dataclass
class RawSources:
    belebele: dict[str, list[sid.BelebeleRow]]
    mono: dict[str, list[tuple[str, str]]]
    bilingual: dict[str, list[dict[str, Any]]]
    haystack: dict[str, list[tuple[str, str]]]
    haystack_source: dict[str, str]
    manifest: dict[str, Any]
    manifest_sha256: str


def load_raw_sources(raw: Path, tokenizer: Any) -> RawSources:
    """Read the raw directory, verifying every file against the fetch manifest."""

    manifest_path = raw / "raw-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if tokenizer.sha256 != manifest["tokenizer_sha256"]:
        raise DataContractError("tokenizer differs from the one used by fetch-raw")
    for source in ("belebele", "fineweb-2", "fineweb"):
        for path, meta in manifest["sources"][source]["files"].items():
            local = {
                "belebele": raw / "belebele" / Path(path).name,
                "fineweb-2": raw / "fineweb-2" / path.split("/")[1] / "test-000_00000.parquet",
                "fineweb": raw / "fineweb" / "CC-MAIN-2025-26-004_00046.parquet",
            }[source]
            if sid.sha256_file(local) != meta["sha256"]:
                raise DataContractError(f"raw file changed since fetch: {local}")
    bilingual = {}
    for pair, record in manifest["sources"]["paradocs"]["pairs"].items():
        path = raw / "paradocs" / f"{pair}.jsonl.gz"
        if sid.sha256_file(path) != record["filtered_file_sha256"]:
            raise DataContractError(f"filtered ParaDocs file changed: {pair}")
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            bilingual[pair] = [json.loads(line) for line in handle]
    belebele = {code: sid.load_belebele(raw / "belebele" / f"{LANGUAGES[code].belebele}.jsonl")
                for code in sid.BELEBELE_LANGUAGES}
    mono = {code: _parquet_texts(raw / "fineweb-2" / sid.FINEWEB2_CONFIG[code] /
                                 "test-000_00000.parquet") for code in MONOLINGUAL_TRAINING}
    haystack, haystack_source = {}, {}
    for code in sid.NEEDLE_LANGUAGES:
        if code == "en":
            haystack[code] = _parquet_texts(raw / "fineweb" / "CC-MAIN-2025-26-004_00046.parquet")
            haystack_source[code] = "fineweb:CC-MAIN-2025-26/004_00046"
        else:
            config = sid.FINEWEB2_CONFIG[code]
            haystack[code] = _parquet_texts(raw / "fineweb-2" / config / "test-000_00000.parquet")
            haystack_source[code] = f"fineweb-2:{config}"
    return RawSources(belebele, mono, bilingual, haystack, haystack_source, manifest,
                      sid.sha256_file(manifest_path))


def assemble_bundle(sources: RawSources, tokenizer: Any, params: BuildParams) -> dict[str, Any]:
    """The deterministic bundle from verified raw sources (no I/O, no network).

    The bundle pins its code by the SHA-256 of the builder and data module, not
    by a commit id, so its digest depends only on the raw directory, the code
    content and the tokenizer; the commit that built it goes in the sidecar
    and in the manifest's study_artifact.revision.
    """

    sep = tokenizer.encode("\n\n")
    newline = tokenizer.encode("\n")
    joined = sid.belebele_join(sources.belebele)
    split = sid.passage_split(joined)
    eval_texts: list[str] = []
    for variants in joined.values():
        for row in variants.values():
            eval_texts.extend([row.passage, row.question, *row.options])
    eval_texts = sorted(set(eval_texts))
    dedup = DedupIndex(tokenizer.encode_batch(eval_texts))
    collector = _Collector(tokenizer, dedup)
    reports: dict[str, Any] = {"dedup": {}, "quota": {}, "eval_texts_indexed": len(eval_texts)}

    mono_items: list[tuple[str, list[int]]] = []
    mono_quota = int(params.mono_quota * params.collect_margin)
    for code in MONOLINGUAL_TRAINING:
        config = sid.FINEWEB2_CONFIG[code]
        docs = _ordered(sources.mono[code], f"mono|{code}")
        stats = DedupStats()
        latin = code if LANGUAGES[code].script == "Latn" else None
        kept = collector.take(docs, quota_tokens=mono_quota, script_filter=True, stats=stats,
                              latin_expected=latin, min_tokens=params.mono_min_tokens,
                              truncate=params.mono_item_max)
        mono_items.extend((f"fineweb-2:{config}:{doc_id}", tokens) for doc_id, tokens in kept)
        reports["dedup"][f"mono-{code}"] = stats.as_dict()
        reports["quota"][f"mono-{code}"] = {"quota": mono_quota,
                                            "tokens": sum(len(t) for _, t in kept)}

    quota = int(params.pair_quota * params.collect_margin)
    bilingual: dict[str, list[tuple[str, list[int]]]] = {}
    realised: dict[str, int] = {}
    for pair in CROSS_SCRIPT_BILINGUAL:
        stats = DedupStats()
        items, total = _bilingual_items(pair, sources.bilingual[pair], tokenizer, dedup, sep,
                                        quota, stats, params.bilingual_side_max)
        bilingual[pair], realised[pair] = items, total
        reports["dedup"][f"bi-{pair}"] = stats.as_dict()
    shortfall = sum(max(0, quota - realised[p]) for p in CROSS_SCRIPT_BILINGUAL)
    same_quota = quota + -(-shortfall // len(SAME_SCRIPT_BILINGUAL))
    for pair in SAME_SCRIPT_BILINGUAL:
        stats = DedupStats()
        items, total = _bilingual_items(pair, sources.bilingual[pair], tokenizer, dedup, sep,
                                        same_quota, stats, params.bilingual_side_max)
        if total < same_quota:
            raise DataContractError(f"{pair}: {total} tokens, below the refill quota")
        bilingual[pair], realised[pair] = items, total
        reports["dedup"][f"bi-{pair}"] = stats.as_dict()
    reports["quota"]["bilingual"] = {
        "pair_quota": quota, "cross_script_shortfall": shortfall,
        "same_script_refill_quota": same_quota, "collected_tokens": realised,
    }

    rng = sid.seeded_rng("k1-stream", sid.STREAM_SEED)
    bi_flat = [item for pair in BILINGUAL_PAIRS for item in bilingual[pair]]
    bi_order = rng.permutation(len(bi_flat))
    n_bi = params.bilingual_train + params.bilingual_dev
    n_mono = params.mono_train + params.mono_dev
    bi_tokens, bi_used = sid.pack_sequences((bi_flat[i][1] for i in bi_order), n_bi,
                                            params.sequence_length, params.sink)
    used_by_pair = {pair: 0 for pair in BILINGUAL_PAIRS}
    for index in bi_order[:bi_used]:
        used_by_pair[bi_flat[index][0].split(":", 1)[0]] += len(bi_flat[index][1])
    used_total = sum(used_by_pair.values())
    reports["quota"]["bilingual"]["packed_tokens_by_pair"] = used_by_pair
    reports["quota"]["bilingual"]["packed_share_by_pair"] = {
        pair: value / used_total for pair, value in used_by_pair.items()}
    mono_order = rng.permutation(len(mono_items))
    mono_tokens, mono_used = sid.pack_sequences((mono_items[i][1] for i in mono_order), n_mono,
                                                params.sequence_length, params.sink)
    train_bi, dev_bi = bi_tokens[: params.bilingual_train], bi_tokens[params.bilingual_train :]
    train_mono, dev_mono = mono_tokens[: params.mono_train], mono_tokens[params.mono_train :]
    train = np.concatenate([train_bi, train_mono])
    kinds = np.asarray([1] * len(train_bi) + [0] * len(train_mono), dtype=np.int32)
    order = rng.permutation(len(train))
    train, kinds = train[order], kinds[order]
    dev = np.concatenate([dev_bi, dev_mono])
    dev_kinds = np.asarray([1] * len(dev_bi) + [0] * len(dev_mono), dtype=np.int32)

    haystacks: dict[str, list[tuple[str, list[int]]]] = {}
    for code in sid.NEEDLE_LANGUAGES:
        docs = _ordered(sources.haystack[code], f"haystack|{code}")
        stats = DedupStats()
        kept = collector.take(docs, quota_tokens=None, script_filter=False, stats=stats,
                              min_tokens=params.haystack_min, max_tokens=params.haystack_max,
                              limit_docs=params.haystack_docs)
        haystacks[code] = [(f"{sources.haystack_source[code]}:{doc_id}", tokens)
                           for doc_id, tokens in kept]
        reports["dedup"][f"haystack-{code}"] = stats.as_dict()

    evaluation = _build_evaluation(joined, split, tokenizer, haystacks, sep, newline, params)
    return {
        "schema": sid.BUNDLE_SCHEMA,
        "license": sid.BUNDLE_LICENSE,
        "license_manifest": {
            "bundle_license_id": sid.BUNDLE_LICENSE,
            "statement": "Mixed-licence research bundle. Each source keeps its own terms; "
                         "the bundle adds no rights. Publish ids and hashes for web text.",
            "sources": LICENSES,
        },
        "sources": sources.manifest.get("sources", {}),
        "raw_manifest_sha256": sources.manifest_sha256,
        "tokenizer_sha256": tokenizer.sha256,
        "builder": {"script": "scripts/build_sparse_indexer_k1_bundle.py",
                    "script_sha256": sid.sha256_file(Path(__file__)),
                    "data_module_sha256": sid.sha256_file(
                        PROJECT_ROOT / "harness" / "sparse_indexer_data.py"),
                    "params": asdict(params)},
        "split": {"seed": split.seed, "development": sorted(split.development),
                  "audit": sorted(split.audit), "primary": sorted(split.primary)},
        "stream": {
            "sequence_length": params.sequence_length,
            "sink_token": params.sink,
            "train_tokens": sid.encode_array(train),
            "train_kinds": sid.encode_array(kinds),
            "dev_tokens": sid.encode_array(dev),
            "dev_kinds": sid.encode_array(dev_kinds),
            "items_used": {"bilingual": int(bi_used), "monolingual": int(mono_used)},
            "extension_rule": "epochs 2 and 3 of the same training sequences, each epoch in a "
                              "fresh permutation seeded 43 and 44",
        },
        "eval": evaluation,
        "reports": reports,
    }


def write_bundle(bundle: dict[str, Any], output: Path, max_bytes: int,
                 git_sha: str | None = None) -> dict[str, Any]:
    payload = sid.canonical_json_bytes(bundle)
    if len(payload) > max_bytes:
        raise DataContractError(f"bundle is {len(payload)} bytes, above {max_bytes}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise DataContractError(f"{output} exists; bundles are versioned, never overwritten")
    temporary = output.with_name(output.name + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, output)
    summary = {"bundle": str(output), "sha256": sid.sha256_bytes(payload),
               "size_bytes": len(payload), "built_from_git_sha": git_sha,
               "license": bundle["license"], "reports": bundle["reports"],
               "eval_counts": bundle["eval"]["counts"]}
    sidecar = output.with_name(output.name + ".manifest.json")
    sidecar.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def cmd_build(args: argparse.Namespace) -> int:
    tokenizer = Tokenizer(args.model_dir / "tokenizer.json")
    sources = load_raw_sources(args.raw_dir, tokenizer)
    params = BuildParams(haystack_docs=args.haystack_docs, max_bytes=args.max_bytes)
    bundle = assemble_bundle(sources, tokenizer, params)
    summary = write_bundle(bundle, args.output, params.max_bytes, args.git_sha)
    print(json.dumps({"sha256": summary["sha256"], "size_bytes": summary["size_bytes"]}))
    return 0


def _build_evaluation(
    joined: dict, split: Any, tokenizer: Any,
    haystacks: dict[str, list[tuple[str, list[int]]]], sep: list[int], newline: list[int],
    params: BuildParams,
) -> dict[str, Any]:
    """Contexts, queries, options and the prompt ledger (crossed item design)."""

    contexts: list[np.ndarray] = []
    context_meta: list[dict[str, Any]] = []
    queries: list[list[int]] = []
    query_meta: list[dict[str, Any]] = []
    options: list[list[int]] = []
    prompts: list[dict[str, Any]] = []
    context_index: dict[tuple, int] = {}
    query_index: dict[tuple, int] = {}

    def haystack_for(code: str, key: str) -> list[tuple[str, list[int]]]:
        pool = haystacks[code]
        rng = sid.seeded_rng("haystack-draw", code, key)
        order = rng.permutation(len(pool))
        return [pool[i] for i in order[: params.haystack_draw]]

    def add_context(code: str, link: str, qnum: int, depth: float, kind: str,
                    partition: str) -> int:
        key = (code, link, qnum, kind)
        if key in context_index:
            return context_index[key]
        row = joined[(link, qnum)][code]
        if kind == "nohaystack":
            tokens = np.asarray([params.sink] + tokenizer.encode(row.passage), dtype=np.uint32)
            start, end, used = 1, len(tokens), ()
        else:
            needle = None if kind == "absent" else tokenizer.encode(row.passage)
            built = sid.build_context(needle, haystack_for(code, f"{link}|{qnum}|{kind}"),
                                      depth, sep, params.context_length, params.sink)
            tokens, start, end, used = (built.tokens, built.needle_start, built.needle_end,
                                        built.haystack_ids)
        context_index[key] = len(contexts)
        contexts.append(tokens)
        context_meta.append({
            "needle_language": code, "link": link, "question_number": qnum, "depth": depth,
            "kind": kind, "partition": partition, "needle_start": int(start),
            "needle_end": int(end), "haystack_ids": list(used),
            "tokens_sha256": sid.sha256_bytes(np.asarray(tokens, np.uint32).tobytes()),
        })
        return context_index[key]

    def add_query(code: str, link: str, qnum: int, kind: str, text: str | None = None) -> int:
        key = (code, link, qnum, kind, text)
        if key in query_index:
            return query_index[key]
        row = joined[(link, qnum)][code]
        body = tokenizer.encode(text if text is not None else row.question)
        tokens = sep + body + newline
        option_ids = []
        for option in row.options:
            option_ids.append(len(options))
            options.append(tokenizer.encode(option))
        query_index[key] = len(queries)
        queries.append(tokens)
        query_meta.append({
            "language": code, "link": link, "question_number": qnum, "kind": kind,
            "row_start": len(sep), "row_end": len(sep) + len(body),
            "options": option_ids,
            "option_bytes": [len(option.encode("utf-8")) for option in row.options],
            "correct": row.correct - 1,
        })
        return query_index[key]

    def depth_of(code: str, link: str, qnum: int, partition: str) -> float:
        ordered = sid.stable_order([f"{link}|{q}" for link, q in partition_keys[partition]],
                                   f"depth|{code}")
        return DEPTHS[ordered.index(f"{link}|{qnum}") % len(DEPTHS)]

    partition_keys = {
        "audit": sid.questions_in(joined, split, "audit"),
        "development": sid.questions_in(joined, split, "development"),
    }

    def add_family(pair_kind: str, x: str, direction: str, link: str, qnum: int,
                   partition: str, role: str) -> None:
        needle, query_lang = (x, "en") if direction == "x-needle" else ("en", x)
        pair = f"{needle}>{query_lang}"
        depth = depth_of(needle, link, qnum, partition)
        c = add_context(needle, link, qnum, depth, "needle", partition)
        family = f"{role}|{pair}|{link}|{qnum}"
        for condition, lang in (("MN", needle), (pair_kind, query_lang)):
            q = add_query(lang, link, qnum, "question")
            prompts.append({"prompt_id": f"{family}|{condition}", "role": role,
                            "partition": partition, "pair": pair, "pair_kind": pair_kind,
                            "condition": condition, "family_id": family, "cluster": link,
                            "context_index": c, "query_index": q})

    # Audit: crossed design, every audit question in every pair.
    for link, qnum in partition_keys["audit"]:
        for x in CROSS_SCRIPT_HELDOUT:
            for direction in ("x-needle", "en-needle"):
                add_family("CX", x, direction, link, qnum, "audit", "main")
        for x in SAME_SCRIPT_HELDOUT:
            for direction in ("x-needle", "en-needle"):
                add_family("CS", x, direction, link, qnum, "audit", "same-script")
    # Literal ceiling (ML): 100 English-needle and 100 X-needle prompts.
    audit_keys = partition_keys["audit"]
    en_cells = sid.stable_order([f"{link}|{q}" for link, q in audit_keys], "ml|en")[: params.ml_en]
    x_cells = sid.stable_order(
        [f"{x}|{link}|{q}" for x in CROSS_SCRIPT_HELDOUT for link, q in audit_keys], "ml|x"
    )[: params.ml_x]
    for code, cell in [("en", c) for c in en_cells] + [
        (c.split("|", 1)[0], c.split("|", 1)[1]) for c in x_cells
    ]:
        link, qnum_s = cell.rsplit("|", 1)
        qnum = int(qnum_s)
        row = joined[(link, qnum)][code]
        sentences = [s for s in sid.split_sentences(row.passage) if s]
        pick = int(hashlib.sha256(f"ml-sentence|{code}|{cell}".encode()).hexdigest(), 16)
        sentence = sentences[pick % len(sentences)] if sentences else row.passage
        depth = depth_of(code, link, qnum, "audit")
        c = add_context(code, link, qnum, depth, "needle", "audit")
        q = add_query(code, link, qnum, "literal", sentence)
        family = f"ml|{code}|{link}|{qnum}"
        prompts.append({"prompt_id": f"{family}|ML", "role": "literal", "partition": "audit",
                        "pair": f"{code}>{code}", "pair_kind": "ML", "condition": "ML",
                        "family_id": family, "cluster": link, "context_index": c,
                        "query_index": q})
    # Needle-absent CX cells (paired with their needle-present family for H2b).
    cx_cells = sid.stable_order(
        [f"{x}|{d}|{link}|{q}" for x in CROSS_SCRIPT_HELDOUT for d in ("x-needle", "en-needle")
         for link, q in audit_keys], "absent")[: params.absent]
    for cell in cx_cells:
        x, direction, link, qnum_s = cell.split("|")
        qnum = int(qnum_s)
        needle, query_lang = (x, "en") if direction == "x-needle" else ("en", x)
        c = add_context(needle, link, qnum, 0.0, "absent", "audit")
        q = add_query(query_lang, link, qnum, "question")
        pair = f"{needle}>{query_lang}"
        prompts.append({"prompt_id": f"absent|{pair}|{link}|{qnum}|CX", "role": "absent",
                        "partition": "audit", "pair": pair, "pair_kind": "CX",
                        "condition": "CX", "family_id": f"main|{pair}|{link}|{qnum}",
                        "cluster": link, "context_index": c, "query_index": q})
    # Development pre-check: 20 dev questions crossed with the 14 CX pairs, their
    # needle-absent twins and a no-haystack passage+question reference.
    dev_keys = [tuple(k.rsplit("|", 1)) for k in sid.stable_order(
        [f"{link}|{q}" for link, q in partition_keys["development"]], "dev-precheck"
    )[: params.dev_families_per_pair]]
    for link, qnum_s in dev_keys:
        qnum = int(qnum_s)
        for x in CROSS_SCRIPT_HELDOUT:
            for direction in ("x-needle", "en-needle"):
                add_family("CX", x, direction, link, qnum, "development", "dev")
                needle, query_lang = (x, "en") if direction == "x-needle" else ("en", x)
                pair = f"{needle}>{query_lang}"
                q = add_query(query_lang, link, qnum, "question")
                for kind, role in (("absent", "dev-absent"), ("nohaystack", "dev-nohaystack")):
                    c = add_context(needle, link, qnum, 0.0, kind, "development")
                    prompts.append({"prompt_id": f"{role}|{pair}|{link}|{qnum}|CX", "role": role,
                                    "partition": "development", "pair": pair,
                                    "pair_kind": "CX", "condition": "CX",
                                    "family_id": f"dev|{pair}|{link}|{qnum}", "cluster": link,
                                    "context_index": c, "query_index": q})

    def flat(chunks: list) -> tuple[np.ndarray, np.ndarray]:
        offsets = np.zeros(len(chunks) + 1, dtype=np.int64)
        offsets[1:] = np.cumsum([len(c) for c in chunks])
        data = np.concatenate([np.asarray(c, dtype=np.uint32) for c in chunks]) if chunks else (
            np.zeros(0, np.uint32))
        return data.astype(np.uint32), offsets

    ctx_data, ctx_off = flat(contexts)
    q_data, q_off = flat(queries)
    o_data, o_off = flat(options)
    return {
        "context_tokens": sid.encode_array(ctx_data),
        "context_offsets": sid.encode_array(ctx_off),
        "context_meta": context_meta,
        "query_tokens": sid.encode_array(q_data),
        "query_offsets": sid.encode_array(q_off),
        "query_meta": query_meta,
        "option_tokens": sid.encode_array(o_data),
        "option_offsets": sid.encode_array(o_off),
        "prompts": prompts,
        "counts": {
            "contexts": len(contexts), "queries": len(queries), "prompts": len(prompts),
            "by_role": {role: sum(1 for p in prompts if p["role"] == role)
                        for role in sorted({p["role"] for p in prompts})},
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    probe = sub.add_parser("paradocs-probe")
    probe.add_argument("--tokenizer", type=Path, required=True)
    probe.add_argument("--pairs", nargs="+", default=list(BILINGUAL_PAIRS))
    probe.add_argument("--max-bytes-cross", type=int, default=1_000_000_000)
    probe.add_argument("--max-bytes-same", type=int, default=200_000_000)
    probe.add_argument("--output", type=Path, required=True)
    fetch = sub.add_parser("fetch-raw")
    fetch.add_argument("--raw-dir", type=Path, required=True)
    fetch.add_argument("--tokenizer", type=Path, required=True)
    fetch.add_argument("--cross-script-cap-bytes", type=int, default=CROSS_SCRIPT_CAP_BYTES)
    fetch.add_argument("--same-script-cap-bytes", type=int, default=SAME_SCRIPT_CAP_BYTES)
    build = sub.add_parser("build")
    build.add_argument("--raw-dir", type=Path, required=True)
    build.add_argument("--model-dir", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--git-sha", required=True)
    build.add_argument("--haystack-docs", type=int, default=4000)
    build.add_argument("--max-bytes", type=int, default=512 * 1024**2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "paradocs-probe":
            return cmd_paradocs_probe(args)
        if args.command == "fetch-raw":
            return cmd_fetch_raw(args)
        return cmd_build(args)
    except DataContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
