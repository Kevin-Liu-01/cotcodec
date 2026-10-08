"""Inputs of the Q3 dense headroom pre-check (q3-dense-headroom-precheck-v1), torch-free.

Program decision D26 ended `q3-k1-localization-screen-v2` at an honest gauntlet
exit and asked for a dense-only measurement before any K1 v3: does dense block
top-k attention have enough selection headroom over random, on which base, and
how much of the same-language (MN) leg is literal anchoring rather than
non-literal matching? This module builds the pre-check's inputs from the
development partition of the existing K1 bundle (`k1-bundle-v1.json`, schema
`cotcodec-k1-bundle-v1`) and nothing else:

* ``derive_dev_artifact`` keeps the bundle's development prompts (roles
  ``dev``, ``dev-absent`` and ``dev-nohaystack``), fails closed on any context,
  query or cluster outside the development partition, adds development
  literal (ML) prompts built from the development needles with the builder's
  own sentence rule, and, for a base whose tokenizer differs from the bundle's
  (Qwen3.5-4B-Base), decodes every segment to bytes with the bundle's tokenizer
  and re-encodes it with the base's own, keeping the needle span exact.
* Text features computed before any model runs: English entity anchors
  (proper nouns, dates and numbers a question shares with its passage), the
  digit anchors per language, the share of a query's content tokens that occur
  in the needle, the per-language stop ids of the development haystack, and
  token counts for tokenizer fertility.
* ``plan_units``: unique (context, query) evaluation units in the registered
  stage order.

The torch evaluation lives in ``harness/dense_headroom_torch.py`` and the
statistics and decision rules in ``harness/dense_headroom_stats.py``.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from harness import sparse_indexer_data as sid
from harness.translation_supervised_indexer import assert_reads_within

EXPERIMENT_ID = "q3-dense-headroom-precheck-v1"
ARTIFACT_SCHEMA = "cotcodec-dense-precheck-dev-v1"
SOURCE_BUNDLE_SHA256 = "919d016b87ad862f8f156e9537c9a39e2864dab0e6c605307d100d25a199dd2d"
SOURCE_TOKENIZER_SHA256 = "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
SEEDS: tuple[int, ...] = (42, 43, 44)
CONTEXT_LENGTH = sid.CONTEXT_LENGTH
TOKEN_BUDGET = 1024
BLOCK_SIZE = 4
FIXED_BLOCK_BUDGET = TOKEN_BUDGET // BLOCK_SIZE
STOP_IDS_PER_LANGUAGE = 100
DEV_ROLES = ("dev", "dev-absent", "dev-nohaystack")
LITERAL_ROLE = "dev-literal"
REGISTERED_ROLE_COUNTS = {"dev": 560, "dev-absent": 280, "dev-nohaystack": 280}
REGISTERED_DEV_QUESTIONS = 20
STAGES = ("A-main", "B-absent", "C-literal", "D-nohaystack")
STAGE_OF_ROLE = {"dev": "A-main", "dev-absent": "B-absent", LITERAL_ROLE: "C-literal",
                 "dev-nohaystack": "D-nohaystack"}
SMOKE_452_UNITS = 20


class DenseDataError(ValueError):
    """An input violates the pre-check's data contract (exit code 3 at run time)."""


# --------------------------------------------------------------------------- #
# Lanes
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Lane:
    """One base model the pre-check measures. ``attention_layers`` are the layers
    with softmax attention (all of them for Qwen3, every fourth for Qwen3.5)."""

    lane_id: str
    profile: str  # registered | tiny
    model_id: str
    revision: str
    receipt_sha256: str
    artifact_root_sha256: str
    tokenizer_sha256: str
    n_layers: int
    attention_layers: tuple[int, ...]
    retokenize: bool
    gpus: int
    minutes: int
    cap_gpu_hours: float
    container_profile: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


LANES: dict[str, Lane] = {
    "qwen3-0.6b-base": Lane(
        lane_id="qwen3-0.6b-base", profile="registered", model_id="qwen3-0.6b-base",
        revision="da87bfb608c14b7cf20ba1ce41287e8de496c0cd",
        receipt_sha256="e7f36f05e6c87ec50b3736cf133fda60775abccb38f60fa9d3c134c432cf46df",
        artifact_root_sha256="7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0",
        tokenizer_sha256=SOURCE_TOKENIZER_SHA256, n_layers=28,
        attention_layers=tuple(range(28)), retokenize=False, gpus=1, minutes=9,
        cap_gpu_hours=0.15, container_profile="default"),
    "qwen3.5-4b-base": Lane(
        lane_id="qwen3.5-4b-base", profile="registered", model_id="qwen3.5-4b-base",
        revision="1001bb4d826a52d1f399e183466143f4da7b741b",
        receipt_sha256="253a14185bcff0762b8a43944635a550055d3346fe16c416d6bcfe4460793cfe",
        artifact_root_sha256="c7fbfd6bd1c73b9a0080decf794f5e4333c955f2704591affc61b0a9ac850e42",
        tokenizer_sha256="fe000e3ed39ed12b8d2481d527d44f93c65d37e87645d2dcc80d1bf9d50d2927",
        n_layers=32, attention_layers=tuple(range(3, 32, 4)), retokenize=True, gpus=1,
        minutes=21, cap_gpu_hours=0.35, container_profile="large-cpu-mem"),
}
# Doctor-only stand-ins (CPU, tiny random models, stand-in tokenizers).
TINY_LANES: dict[str, Lane] = {
    "tiny-attention": Lane(
        lane_id="tiny-attention", profile="tiny", model_id="qwen3-0.6b-base",
        revision="da87bfb608c14b7cf20ba1ce41287e8de496c0cd", receipt_sha256="",
        artifact_root_sha256="", tokenizer_sha256="", n_layers=4,
        attention_layers=tuple(range(4)), retokenize=False, gpus=0, minutes=0,
        cap_gpu_hours=0.0, container_profile="default"),
    "tiny-hybrid": Lane(
        lane_id="tiny-hybrid", profile="tiny", model_id="qwen3.5-4b-base",
        revision="1001bb4d826a52d1f399e183466143f4da7b741b", receipt_sha256="",
        artifact_root_sha256="", tokenizer_sha256="", n_layers=4,
        attention_layers=(1, 3), retokenize=True, gpus=0, minutes=0,
        cap_gpu_hours=0.0, container_profile="default"),
}
TOTAL_CAP_GPU_HOURS = 0.5  # program decision D26
REGISTERED_ORDER = ("qwen3-0.6b-base", "qwen3.5-4b-base")
# Jobs of a registered lane. Every job of a lane (its first job, a re-run of a
# void job, its one continuation) counts against that lane's own minutes: the
# filler charges each ended job its elapsed minutes rounded up plus one, and a
# later job gets what is left, at least MIN_JOB_MINUTES. Slurm sends SIGUSR1
# USR1_LEAD_MINUTES before a job's limit and the job ends there, so its useful
# time is its limit minus that lead; MIN_JOB_MINUTES leaves every granted job
# at least MIN_USEFUL_MINUTES of it (D32). A continuation follows a predecessor
# that used at least one minute and was charged one more, so its limit is at
# most the lane's minutes minus CONTINUATION_MIN_CHARGE.
OUTPUT_SUBDIR = "dense-precheck"
RESUME_SUBPATH = f"{OUTPUT_SUBDIR}/checkpoints"
USR1_LEAD_MINUTES = 3
MIN_USEFUL_MINUTES = 2
MIN_JOB_MINUTES = USR1_LEAD_MINUTES + MIN_USEFUL_MINUTES  # 5
CONTINUATION_MIN_CHARGE = 2


def lane_of(lane_id: str) -> Lane:
    lane = LANES.get(lane_id) or TINY_LANES.get(lane_id)
    if lane is None:
        raise DenseDataError(f"unknown lane {lane_id!r}")
    return lane


def registered_caps_total() -> float:
    return round(sum(lane.cap_gpu_hours for lane in LANES.values()), 6)


def budget_blocks(context_length: int) -> int:
    """The matched budget: 12.5 percent of the context in 4-token blocks.

    A registered 8,192-token context gives the K1 budget of 256 blocks (1,024
    tokens); a re-tokenized context keeps the fraction, not the token count.
    """

    if context_length < BLOCK_SIZE:
        raise DenseDataError("context is shorter than one block")
    return max(1, (context_length * TOKEN_BUDGET // CONTEXT_LENGTH) // BLOCK_SIZE)


def fixed_blocks(profile: str) -> int:
    return FIXED_BLOCK_BUDGET if profile == "registered" else 4


# --------------------------------------------------------------------------- #
# Token codecs
# --------------------------------------------------------------------------- #


class TokenCodec(Protocol):
    sha256: str
    sink: int

    def encode(self, text: str) -> list[int]: ...

    def decode_bytes(self, ids: Iterable[int]) -> bytes: ...


def _bytes_to_unicode() -> dict[int, str]:
    """GPT-2's reversible byte-to-character table (the ByteLevel pre-tokenizer)."""

    printable = (list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1))
                 + list(range(ord("®"), ord("ÿ") + 1)))
    codes = printable[:]
    extra = 0
    for byte in range(256):
        if byte not in printable:
            printable.append(byte)
            codes.append(256 + extra)
            extra += 1
    return {byte: chr(code) for byte, code in zip(printable, codes, strict=True)}


_BYTE_DECODER = {char: byte for byte, char in _bytes_to_unicode().items()}


class ByteLevelCodec:
    """A Hugging Face byte-level BPE ``tokenizer.json`` (Qwen3, Qwen3.5).

    ``decode_bytes`` maps every id to its raw bytes through the ByteLevel table,
    so a segment decodes exactly (no replacement characters); special tokens
    are refused inside a segment.
    """

    def __init__(self, path: Path) -> None:
        from tokenizers import Tokenizer

        self.path = path
        self.sha256 = sid.sha256_file(path)
        self._tok = Tokenizer.from_file(str(path))
        sink = self._tok.token_to_id("<|endoftext|>")
        if sink is None:
            raise DenseDataError(f"{path} has no <|endoftext|> token")
        self.sink = int(sink)
        self._special = frozenset(int(i) for i in self._tok.get_added_tokens_decoder())
        self._cache: dict[int, bytes] = {}

    def encode(self, text: str) -> list[int]:
        return list(self._tok.encode(text, add_special_tokens=False).ids)

    def _token_bytes(self, token_id: int) -> bytes:
        cached = self._cache.get(token_id)
        if cached is not None:
            return cached
        if token_id in self._special:
            raise DenseDataError(f"special token {token_id} inside a text segment")
        piece = self._tok.id_to_token(token_id)
        if piece is None:
            raise DenseDataError(f"token id {token_id} is outside the vocabulary")
        try:
            value = bytes(_BYTE_DECODER[char] for char in piece)
        except KeyError as exc:
            raise DenseDataError(f"token {token_id} is not a byte-level token") from exc
        self._cache[token_id] = value
        return value

    def decode_bytes(self, ids: Iterable[int]) -> bytes:
        return b"".join(self._token_bytes(int(i)) for i in ids)


class StandInByteCodec:
    """Doctor stand-in equal to the K1 doctor's ``ByteTokenizer`` (ids 2 + byte, sink 1)."""

    def __init__(self, vocab: int = 512) -> None:
        self.vocab = vocab
        self.sink = 1
        self.sha256 = hashlib.sha256(f"byte-tokenizer-{vocab}".encode()).hexdigest()

    def encode(self, text: str) -> list[int]:
        return [2 + (b % (self.vocab - 2)) for b in text.encode("utf-8")]

    def decode_bytes(self, ids: Iterable[int]) -> bytes:
        out = bytearray()
        for token in ids:
            value = int(token) - 2
            if not 0 <= value < 256:
                raise DenseDataError(f"stand-in id {token} is not a byte")
            out.append(value)
        return bytes(out)


class StandInPairCodec:
    """Doctor stand-in with a different vocabulary: bytes are ids 3..258 and each
    pair of lowercase ASCII letters is one id from 259, so re-tokenization
    changes every length and position (sink 2)."""

    vocab = 259 + 26 * 26

    def __init__(self) -> None:
        self.sink = 2
        self.sha256 = hashlib.sha256(b"pair-tokenizer-935").hexdigest()

    def encode(self, text: str) -> list[int]:
        data = text.encode("utf-8")
        out: list[int] = []
        index = 0
        while index < len(data):
            a = data[index]
            if (index + 1 < len(data) and 97 <= a <= 122 and 97 <= data[index + 1] <= 122):
                out.append(259 + (a - 97) * 26 + (data[index + 1] - 97))
                index += 2
            else:
                out.append(3 + a)
                index += 1
        return out

    def decode_bytes(self, ids: Iterable[int]) -> bytes:
        out = bytearray()
        for token in ids:
            value = int(token)
            if 3 <= value < 259:
                out.append(value - 3)
            elif 259 <= value < self.vocab:
                pair = value - 259
                out.extend((97 + pair // 26, 97 + pair % 26))
            else:
                raise DenseDataError(f"stand-in pair id {token} is outside the vocabulary")
        return bytes(out)


def decode_text(codec: TokenCodec, ids: Sequence[int], *, tail_tolerant: bool = False
                ) -> tuple[str, int]:
    """Exact UTF-8 text of a token segment and the number of dropped tail bytes.

    Only a segment that ends where the K1 builder cut the haystack
    (``tail_tolerant``) may end inside a character; at most three trailing bytes
    of an incomplete sequence are dropped. Any other invalid byte raises.
    """

    raw = codec.decode_bytes(ids)
    try:
        return raw.decode("utf-8"), 0
    except UnicodeDecodeError as exc:
        incomplete_tail = (exc.reason == "unexpected end of data"
                           and exc.end == len(raw) and len(raw) - exc.start <= 3)
        if not (tail_tolerant and incomplete_tail):
            raise DenseDataError(f"segment is not valid UTF-8: {exc.reason}") from exc
        return raw[: exc.start].decode("utf-8"), len(raw) - exc.start


# --------------------------------------------------------------------------- #
# Text features (no model)
# --------------------------------------------------------------------------- #

_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_POSSESSIVE = re.compile(r"['’]s$")
_DIGIT_RUN = re.compile(r"\d+", re.UNICODE)
NOT_ENTITIES = frozenset({"I"})


def _normalise_digits(run: str) -> str:
    return "".join(str(unicodedata.decimal(ch)) for ch in run)


def digit_runs(text: str) -> set[str]:
    """Maximal decimal-digit runs, any script's digits written as ASCII."""

    return {_normalise_digits(run) for run in _DIGIT_RUN.findall(text)}


def _words(text: str) -> list[str]:
    return [_POSSESSIVE.sub("", word) for word in _WORD.findall(text)]


def english_anchors(question: str, passage: str) -> dict[str, list[str]]:
    """Entity anchors an English question shares with its passage.

    ``capitalised``: a word starting with an uppercase letter that is not the
    question's first word nor the pronoun "I", also present (exact, possessive
    "'s" removed) in the passage (proper nouns, months, named events).
    ``digits``: a digit run present in both (dates, numbers, units' values).
    Belebele's translation rules keep these strings with the passage in every
    translation, so the English flag marks the question in all languages.
    """

    words = _words(question)
    passage_words = set(_words(passage))
    capitalised = sorted({w for i, w in enumerate(words)
                          if i > 0 and w[:1].isupper() and w not in NOT_ENTITIES
                          and w in passage_words})
    digits = sorted(digit_runs(question) & digit_runs(passage))
    return {"capitalised": capitalised, "digits": digits}


def symbol_only(codec: TokenCodec, token_id: int) -> bool:
    """A token whose bytes decode on their own to text without a letter or digit."""

    try:
        text = codec.decode_bytes([token_id]).decode("utf-8")
    except (UnicodeDecodeError, DenseDataError):
        return False  # a fragment of a multi-byte character carries content
    return not any(ch.isalnum() for ch in text)


class ContentFilter:
    """Content tokens of a query: not a stop id of the needle language nor of the
    query's own language, and not symbol-only.

    Both languages' stop ids are removed so that on a cross-script prompt the
    query's function words (English ones on an X>en prompt) do not count as
    content; on a same-language prompt the two sets are the same.
    """

    def __init__(self, codec: TokenCodec, stop_ids: Mapping[str, Sequence[int]]) -> None:
        self.codec = codec
        self.stop = {language: frozenset(int(i) for i in ids)
                     for language, ids in stop_ids.items()}
        self._symbol: dict[int, bool] = {}

    def _stop(self, languages: Sequence[str]) -> frozenset[int]:
        if isinstance(languages, str):
            raise DenseDataError("content tokens need the needle and the query language")
        missing = sorted(set(languages) - set(self.stop))
        if missing:
            raise DenseDataError(f"no stop ids for {missing}")
        return frozenset().union(*(self.stop[language] for language in languages))

    def is_content(self, token_id: int, languages: Sequence[str]) -> bool:
        token_id = int(token_id)
        if token_id in self._stop(languages):
            return False
        flag = self._symbol.get(token_id)
        if flag is None:
            flag = symbol_only(self.codec, token_id)
            self._symbol[token_id] = flag
        return not flag

    def content_ids(self, tokens: Iterable[int], languages: Sequence[str]) -> list[int]:
        stop = self._stop(languages)
        out = []
        for token in tokens:
            token = int(token)
            if token in stop:
                continue
            flag = self._symbol.get(token)
            if flag is None:
                flag = symbol_only(self.codec, token)
                self._symbol[token] = flag
            if not flag:
                out.append(token)
        return out


def stop_ids_by_language(contexts: Sequence[Mapping[str, Any]],
                         tokens_of: Any, limit: int = STOP_IDS_PER_LANGUAGE
                         ) -> dict[str, list[int]]:
    """The ``limit`` most frequent ids of each needle language's development
    haystack (needle and needle-absent contexts, needle span and sink removed);
    ties go to the lower id."""

    counts: dict[str, Counter[int]] = {}
    for index, meta in enumerate(contexts):
        if meta["kind"] not in ("needle", "absent"):
            continue
        tokens = tokens_of(index)
        start, end = int(meta["needle_start"]), int(meta["needle_end"])
        body = np.concatenate([tokens[1:start], tokens[end:]]) if start > 0 else tokens[1:]
        counts.setdefault(meta["needle_language"], Counter()).update(int(t) for t in body)
    return {language: [token for token, _ in sorted(counter.items(),
                                                    key=lambda kv: (-kv[1], kv[0]))[:limit]]
            for language, counter in sorted(counts.items())}


# --------------------------------------------------------------------------- #
# Development artifact
# --------------------------------------------------------------------------- #


def _flat(chunks: Sequence[Sequence[int]]) -> tuple[NDArray[np.uint32], NDArray[np.int64]]:
    offsets = np.zeros(len(chunks) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum([len(c) for c in chunks])
    data = (np.concatenate([np.asarray(c, dtype=np.uint32) for c in chunks]) if chunks
            else np.zeros(0, np.uint32))
    return data.astype(np.uint32), offsets


def split_digest(bundle: Mapping[str, Any]) -> str:
    return hashlib.sha256(sid.canonical_json_bytes(bundle["split"])).hexdigest()


def k1_smoke_units(prompts: Sequence[Mapping[str, Any]], n: int = SMOKE_452_UNITS
                   ) -> list[str]:
    """The development units K1 v1's smoke read (``plan_units`` keys sorted as
    strings, role ``dev``, first ``n``): bundle-index unit keys."""

    keys = sorted({f"c{int(p['context_index'])}-q{int(p['query_index'])}" for p in prompts
                   if p["role"] == "dev"})
    return keys[:n]


def derive_dev_artifact(bundle: Mapping[str, Any], source: TokenCodec, lane_codec: TokenCodec,
                        lane: Lane) -> dict[str, Any]:
    """The pre-check's inputs from the K1 bundle's development partition only.

    Raises ``DenseDataError`` (or the partition guard's ``IndexerContractError``)
    on any input outside the development partition or any token that does not
    round-trip.
    """

    if bundle.get("schema") != sid.BUNDLE_SCHEMA:
        raise DenseDataError("not a K1 bundle")
    if bundle.get("tokenizer_sha256") != source.sha256:
        raise DenseDataError("the source codec is not the bundle's tokenizer")
    if not lane.retokenize and lane_codec.sha256 != source.sha256:
        raise DenseDataError("a lane without re-tokenization must use the bundle's tokenizer")
    split = sid.split_from_bundle(bundle)
    section = bundle["eval"]
    prompts = [p for p in section["prompts"] if p["partition"] == "development"]
    roles = Counter(p["role"] for p in prompts)
    if set(roles) != set(DEV_ROLES):
        raise DenseDataError(f"development roles {sorted(roles)} differ from {DEV_ROLES}")
    if lane.profile == "registered" and dict(roles) != REGISTERED_ROLE_COUNTS:
        raise DenseDataError(f"development role counts {dict(roles)} are not the registered ones")
    assert_reads_within((p["cluster"] for p in prompts), split, "development")
    context_meta = section["context_meta"]
    query_meta = section["query_meta"]
    context_tokens = sid.decode_array(section["context_tokens"])
    context_offsets = sid.decode_array(section["context_offsets"])
    query_tokens = sid.decode_array(section["query_tokens"])
    query_offsets = sid.decode_array(section["query_offsets"])
    option_tokens = sid.decode_array(section["option_tokens"])
    option_offsets = sid.decode_array(section["option_offsets"])
    sink = int(bundle["stream"]["sink_token"])
    if sink != source.sink:
        raise DenseDataError("the bundle's sink is not the source codec's sink")

    def src_context(index: int) -> NDArray[np.uint32]:
        return context_tokens[context_offsets[index] : context_offsets[index + 1]]

    def src_query(index: int) -> NDArray[np.uint32]:
        return query_tokens[query_offsets[index] : query_offsets[index + 1]]

    sep_l, newline_l = lane_codec.encode("\n\n"), lane_codec.encode("\n")
    contexts: list[dict[str, Any]] = []
    context_chunks: list[list[int]] = []
    context_map: dict[int, int] = {}
    needle_text: dict[tuple[str, str, int], str] = {}

    def add_context(src: int) -> int:
        if src in context_map:
            return context_map[src]
        meta = context_meta[src]
        if meta["partition"] != "development" or meta["link"] not in split.development:
            raise DenseDataError(f"context {src} lies outside the development partition")
        tokens = np.asarray(src_context(src))
        if sid.sha256_bytes(np.asarray(tokens, np.uint32).tobytes()) != meta["tokens_sha256"]:
            raise DenseDataError(f"context {src} differs from its bundle digest")
        if int(tokens[0]) != sink:
            raise DenseDataError(f"context {src} does not start with the sink")
        kind = meta["kind"]
        start, end = int(meta["needle_start"]), int(meta["needle_end"])
        dropped = 0
        if kind == "absent":
            body, dropped = decode_text(source, tokens[1:], tail_tolerant=True)
            segments = [("haystack", body)]
        elif kind == "nohaystack":
            if (start, end) != (1, len(tokens)):
                raise DenseDataError(f"no-haystack context {src} has a needle span {start, end}")
            segments = [("needle", decode_text(source, tokens[1:])[0])]
        elif kind == "needle":
            if not 1 <= start < end <= len(tokens):
                raise DenseDataError(f"context {src} has no needle span")
            before = decode_text(source, tokens[1:start])[0]
            passage = decode_text(source, tokens[start:end])[0]
            after, dropped = decode_text(source, tokens[end:], tail_tolerant=True)
            segments = [("haystack", before), ("needle", passage), ("haystack", after)]
        else:
            raise DenseDataError(f"context {src} has unknown kind {kind!r}")
        if lane.retokenize:
            out = [lane_codec.sink]
            n0 = n1 = -1
            for name, text in segments:
                encoded = lane_codec.encode(text)
                if name == "needle":
                    n0, n1 = len(out), len(out) + len(encoded)
                out.extend(encoded)
            if kind == "absent":
                n0 = n1 = -1
        else:
            out = [int(t) for t in tokens]
            n0, n1 = start, end
        if kind != "absent":
            passage_text = next(text for name, text in segments if name == "needle")
            needle_text.setdefault((meta["needle_language"], meta["link"],
                                    int(meta["question_number"])), passage_text)
            if not 0 < n0 < n1 <= len(out):
                raise DenseDataError(f"context {src}: empty needle after re-tokenization")
        context_map[src] = len(contexts)
        contexts.append({
            "kind": kind, "needle_language": meta["needle_language"], "link": meta["link"],
            "question_number": int(meta["question_number"]), "depth": float(meta["depth"]),
            "needle_start": int(n0), "needle_end": int(n1), "length": len(out),
            "source_index": int(src), "source_tokens_sha256": meta["tokens_sha256"],
            "tokens_sha256": sid.sha256_bytes(np.asarray(out, np.uint32).tobytes()),
            "dropped_tail_bytes": int(dropped),
        })
        context_chunks.append(out)
        return context_map[src]

    queries: list[dict[str, Any]] = []
    query_chunks: list[list[int]] = []
    option_chunks: list[list[int]] = []
    query_map: dict[int, int] = {}
    question_text: dict[tuple[str, str, int], str] = {}

    def add_query(src: int) -> int:
        if src in query_map:
            return query_map[src]
        meta = query_meta[src]
        if meta["link"] not in split.development:
            raise DenseDataError(f"query {src} lies outside the development partition")
        tokens = np.asarray(src_query(src))
        r0, r1 = int(meta["row_start"]), int(meta["row_end"])
        text = decode_text(source, tokens[r0:r1])[0]
        question_text.setdefault((meta["language"], meta["link"], int(meta["question_number"])),
                                 text)
        option_ids: list[int] = []
        for option in meta["options"]:
            src_option = option_tokens[option_offsets[option] : option_offsets[option + 1]]
            if lane.retokenize:
                encoded = lane_codec.encode(decode_text(source, src_option)[0])
            else:
                encoded = [int(t) for t in src_option]
            option_ids.append(len(option_chunks))
            option_chunks.append(encoded)
        if lane.retokenize:
            body = lane_codec.encode(text)
            out = sep_l + body + newline_l
            q0, q1 = len(sep_l), len(sep_l) + len(body)
        else:
            out = [int(t) for t in tokens]
            q0, q1 = r0, r1
        query_map[src] = len(queries)
        queries.append({
            "language": meta["language"], "link": meta["link"],
            "question_number": int(meta["question_number"]), "kind": meta["kind"],
            "row_start": q0, "row_end": q1, "options": option_ids,
            "option_bytes": [int(b) for b in meta["option_bytes"]],
            "correct": int(meta["correct"]), "source_index": int(src),
        })
        query_chunks.append(out)
        return query_map[src]

    out_prompts: list[dict[str, Any]] = []
    for prompt in sorted(prompts, key=lambda p: p["prompt_id"]):
        c = add_context(int(prompt["context_index"]))
        q = add_query(int(prompt["query_index"]))
        cmeta, qmeta = contexts[c], queries[q]
        if cmeta["link"] != prompt["cluster"] or qmeta["link"] != prompt["cluster"]:
            raise DenseDataError(f"{prompt['prompt_id']}: context, query and cluster disagree")
        out_prompts.append({
            "prompt_id": prompt["prompt_id"], "role": prompt["role"], "pair": prompt["pair"],
            "condition": prompt["condition"], "family_id": prompt["family_id"],
            "cluster": prompt["cluster"], "question_number": cmeta["question_number"],
            "needle_language": cmeta["needle_language"], "query_language": qmeta["language"],
            "context_index": c, "query_index": q,
            "source_unit": f"c{int(prompt['context_index'])}-q{int(prompt['query_index'])}",
        })

    # Development literal (ML) prompts: one verbatim needle sentence, picked by
    # the K1 builder's rule, in every needle context of a development question.
    needle_contexts = sorted({(c["needle_language"], c["link"], c["question_number"]): i
                              for i, c in enumerate(contexts) if c["kind"] == "needle"}.items())
    for (language, link, qnum), c in needle_contexts:
        passage = needle_text[(language, link, qnum)]
        sentences = [s for s in sid.split_sentences(passage) if s]
        cell = f"{link}|{qnum}"
        pick = int(hashlib.sha256(f"ml-sentence|{language}|{cell}".encode()).hexdigest(), 16)
        sentence = sentences[pick % len(sentences)] if sentences else passage
        if sentence not in passage:
            raise DenseDataError("a literal sentence is not verbatim in its needle")
        body = lane_codec.encode(sentence)
        query_map_key = len(queries)
        queries.append({
            "language": language, "link": link, "question_number": qnum, "kind": "literal",
            "row_start": len(sep_l), "row_end": len(sep_l) + len(body), "options": [],
            "option_bytes": [], "correct": -1, "source_index": -1,
        })
        query_chunks.append(sep_l + body + newline_l)
        family = f"ml|{language}|{link}|{qnum}"
        out_prompts.append({
            "prompt_id": f"{LITERAL_ROLE}|{language}>{language}|{link}|{qnum}|ML",
            "role": LITERAL_ROLE, "pair": f"{language}>{language}", "condition": "ML",
            "family_id": family, "cluster": link, "question_number": qnum,
            "needle_language": language, "query_language": language,
            "context_index": c, "query_index": query_map_key, "source_unit": None,
        })

    flat_c, off_c = _flat(context_chunks)
    flat_q, off_q = _flat(query_chunks)
    flat_o, off_o = _flat(option_chunks)

    def lane_context(index: int) -> NDArray[np.uint32]:
        return flat_c[off_c[index] : off_c[index + 1]]

    stop_ids = stop_ids_by_language(contexts, lane_context)
    features = text_features(contexts, queries, out_prompts, flat_c, off_c, flat_q, off_q,
                             needle_text, question_text, lane_codec, stop_ids)
    dev_questions = sorted({(p["cluster"], p["question_number"]) for p in out_prompts})
    if lane.profile == "registered" and len(dev_questions) != REGISTERED_DEV_QUESTIONS:
        raise DenseDataError(f"{len(dev_questions)} development questions, expected "
                             f"{REGISTERED_DEV_QUESTIONS}")
    counts = Counter(p["role"] for p in out_prompts)
    return {
        "schema": ARTIFACT_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "lane": lane.lane_id,
        "profile": lane.profile,
        "source": {"bundle_schema": bundle["schema"], "tokenizer_sha256": source.sha256,
                   "split_sha256": split_digest(bundle), "split_seed": split.seed,
                   "development_links": sorted(split.development),
                   "k1_smoke_units": k1_smoke_units(prompts)},
        "lane_tokenizer_sha256": lane_codec.sha256,
        "retokenized": bool(lane.retokenize),
        "sink": int(lane_codec.sink),
        "contexts": contexts,
        "queries": queries,
        "prompts": out_prompts,
        "context_tokens": sid.encode_array(flat_c),
        "context_offsets": sid.encode_array(off_c),
        "query_tokens": sid.encode_array(flat_q),
        "query_offsets": sid.encode_array(off_q),
        "option_tokens": sid.encode_array(flat_o),
        "option_offsets": sid.encode_array(off_o),
        "stop_ids": stop_ids,
        "features": features,
        "counts": {"prompts_by_role": dict(sorted(counts.items())),
                   "contexts": len(contexts), "queries": len(queries),
                   "development_questions": len(dev_questions),
                   "dropped_tail_bytes": int(sum(c["dropped_tail_bytes"] for c in contexts)),
                   "context_length": {"min": int(min(c["length"] for c in contexts)),
                                      "max": int(max(c["length"] for c in contexts))}},
    }


def text_features(contexts: Sequence[Mapping[str, Any]], queries: Sequence[Mapping[str, Any]],
                  prompts: Sequence[Mapping[str, Any]], flat_c: NDArray[np.uint32],
                  off_c: NDArray[np.int64], flat_q: NDArray[np.uint32], off_q: NDArray[np.int64],
                  needle_text: Mapping[tuple[str, str, int], str],
                  question_text: Mapping[tuple[str, str, int], str], codec: TokenCodec,
                  stop_ids: Mapping[str, Sequence[int]]) -> dict[str, Any]:
    """Model-free features, all from development text and the lane's tokens."""

    questions: dict[str, Any] = {}
    for link, qnum in sorted({(p["cluster"], p["question_number"]) for p in prompts}):
        en_q = question_text.get(("en", link, qnum))
        en_p = needle_text.get(("en", link, qnum))
        if en_q is None or en_p is None:
            raise DenseDataError(f"{link}|{qnum}: no English question or passage")
        anchors = english_anchors(en_q, en_p)
        per_language_digits = {}
        for (language, l_link, l_q), passage in sorted(needle_text.items()):
            if (l_link, l_q) != (link, qnum):
                continue
            question = question_text.get((language, link, qnum))
            if question is not None:
                per_language_digits[language] = sorted(digit_runs(question)
                                                       & digit_runs(passage))
        questions[f"{link}|{qnum}"] = {
            "anchors": anchors,
            "anchored": bool(anchors["capitalised"] or anchors["digits"]),
            "digit_anchors_by_language": per_language_digits,
        }
    filt = ContentFilter(codec, stop_ids)
    overlap: dict[str, Any] = {}
    for prompt in prompts:
        if prompt["role"] not in ("dev", LITERAL_ROLE):
            continue
        context = contexts[prompt["context_index"]]
        query = queries[prompt["query_index"]]
        c_tokens = flat_c[off_c[prompt["context_index"]] : off_c[prompt["context_index"] + 1]]
        q_tokens = flat_q[off_q[prompt["query_index"]] : off_q[prompt["query_index"] + 1]]
        needle = {int(t) for t in c_tokens[context["needle_start"] : context["needle_end"]]}
        content = filt.content_ids(q_tokens[query["row_start"] : query["row_end"]],
                                   (context["needle_language"], query["language"]))
        shared = sum(1 for t in content if t in needle)
        overlap[prompt["prompt_id"]] = {
            "content_tokens": len(content), "shared_with_needle": shared,
            "share": (shared / len(content)) if content else 0.0}
    tokens: dict[str, Any] = {"passage": {}, "question": {}}
    for context in contexts:
        if context["kind"] == "needle":
            key = f"{context['needle_language']}|{context['link']}|{context['question_number']}"
            tokens["passage"][key] = int(context["needle_end"] - context["needle_start"])
    for query in queries:
        if query["kind"] == "question":
            key = f"{query['language']}|{query['link']}|{query['question_number']}"
            tokens["question"][key] = int(query["row_end"] - query["row_start"])
    return {"questions": questions, "prompt_overlap": overlap, "token_counts": tokens,
            "anchor_rule": "English question words that are capitalised (not the first word, "
                           "not 'I') or digit runs, also present in the English passage"}


def canonical_artifact_bytes(artifact: Mapping[str, Any]) -> bytes:
    return sid.canonical_json_bytes(artifact)


def artifact_sha256(artifact: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_artifact_bytes(artifact)).hexdigest()


# --------------------------------------------------------------------------- #
# Staged view and units
# --------------------------------------------------------------------------- #


class DevView:
    """Decoded arrays of a development artifact."""

    def __init__(self, artifact: Mapping[str, Any]) -> None:
        if artifact.get("schema") != ARTIFACT_SCHEMA:
            raise DenseDataError("not a dense pre-check development artifact")
        self.artifact = artifact
        self.contexts = artifact["contexts"]
        self.queries = artifact["queries"]
        self.prompts = artifact["prompts"]
        self.ctx = sid.decode_array(artifact["context_tokens"])
        self.ctx_off = sid.decode_array(artifact["context_offsets"])
        self.qry = sid.decode_array(artifact["query_tokens"])
        self.qry_off = sid.decode_array(artifact["query_offsets"])
        self.opt = sid.decode_array(artifact["option_tokens"])
        self.opt_off = sid.decode_array(artifact["option_offsets"])
        links = frozenset(artifact["source"]["development_links"])
        bad = sorted({p["cluster"] for p in self.prompts} - links)
        if bad:
            raise DenseDataError(f"{len(bad)} prompt cluster(s) outside the development links")

    def context(self, index: int) -> NDArray[np.uint32]:
        return self.ctx[self.ctx_off[index] : self.ctx_off[index + 1]]

    def query(self, index: int) -> NDArray[np.uint32]:
        return self.qry[self.qry_off[index] : self.qry_off[index + 1]]

    def unit_tokens(self, context_index: int, query_index: int
                    ) -> tuple[NDArray[np.uint32], int, int, int, int]:
        """Tokens, query rows ``[q0, q1)`` and needle span ``[n0, n1)`` (``-1`` if absent)."""

        context = self.context(context_index)
        query = self.query(query_index)
        cmeta, qmeta = self.contexts[context_index], self.queries[query_index]
        tokens = np.concatenate([context, query]).astype(np.uint32)
        q0 = len(context) + int(qmeta["row_start"])
        q1 = len(context) + int(qmeta["row_end"])
        return tokens, q0, q1, int(cmeta["needle_start"]), int(cmeta["needle_end"])

    def options(self, query_index: int) -> tuple[list[NDArray[np.uint32]], list[int], int]:
        qmeta = self.queries[query_index]
        options = [self.opt[self.opt_off[i] : self.opt_off[i + 1]] for i in qmeta["options"]]
        return options, list(qmeta["option_bytes"]), int(qmeta["correct"])


@dataclass(frozen=True)
class Unit:
    unit_id: str
    stage: str
    context_index: int
    query_index: int
    select: bool
    mc: bool


def plan_units(prompts: Sequence[Mapping[str, Any]]) -> list[Unit]:
    """Unique (context, query) units; each belongs to the first stage that needs it.

    Selection (recall) is read on ``dev`` (MN, CX) and ``dev-literal`` (ML)
    prompts; multiple choice on ``dev`` (MN, CX), ``dev-absent`` and
    ``dev-nohaystack`` prompts.
    """

    needs: dict[tuple[int, int], dict[str, Any]] = {}
    for prompt in prompts:
        key = (int(prompt["context_index"]), int(prompt["query_index"]))
        stage = STAGE_OF_ROLE[prompt["role"]]
        entry = needs.setdefault(key, {"stage": stage, "select": False, "mc": False})
        if STAGES.index(stage) < STAGES.index(entry["stage"]):
            entry["stage"] = stage
        entry["select"] |= prompt["role"] in ("dev", LITERAL_ROLE)
        entry["mc"] |= prompt["role"] in ("dev", "dev-absent", "dev-nohaystack")
    units = [Unit(f"c{c}-q{q}", entry["stage"], c, q, bool(entry["select"]), bool(entry["mc"]))
             for (c, q), entry in needs.items()]
    return sorted(units, key=lambda u: (STAGES.index(u.stage), u.context_index, u.query_index))


def unit_of(prompt: Mapping[str, Any]) -> str:
    return f"c{int(prompt['context_index'])}-q{int(prompt['query_index'])}"


def lexical_block_scores(tokens: NDArray[np.uint32], context_length: int, q0: int, q1: int,
                         languages: Sequence[str], content: ContentFilter
                         ) -> NDArray[np.float32]:
    """The literal selector's block scores: per 4-token block of the whole
    sequence, how many context tokens (sink excluded) are content ids of the
    query (``languages``: the needle's and the query's). Query blocks score only
    their context tokens (none). It matches every shared token, entities among
    them; it is a lexical-overlap selector, not an entity detector."""

    wanted = sorted(set(content.content_ids(tokens[q0:q1], languages)))
    match = np.zeros(len(tokens), dtype=np.float32)
    if wanted:
        match[1:context_length] = np.isin(tokens[1:context_length],
                                          np.asarray(wanted, dtype=tokens.dtype))
    n_blocks = len(tokens) // BLOCK_SIZE
    return match[: n_blocks * BLOCK_SIZE].reshape(n_blocks, BLOCK_SIZE).sum(axis=1)


GPU_ONLY_KERNEL_PACKAGES = ("fla", "causal_conv1d")


def block_gpu_only_kernels() -> list[str]:
    """For a CPU run: make the GPU-only kernel packages unimportable before
    ``transformers`` is imported, so its Qwen3.5 gated-delta layers use their
    torch implementation (flash-linear-attention's Triton kernels need a GPU).
    Returns the packages blocked; a package already imported is left alone."""

    import sys

    blocked = []
    for name in GPU_ONLY_KERNEL_PACKAGES:
        if name not in sys.modules:
            sys.modules[name] = None  # type: ignore[assignment]
            blocked.append(name)
    return blocked


def write_json(path: Path, payload: Any) -> str:
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)
    return hashlib.sha256(data).hexdigest()


__all__ = [
    "ARTIFACT_SCHEMA",
    "CONTINUATION_MIN_CHARGE",
    "EXPERIMENT_ID",
    "LANES",
    "MIN_JOB_MINUTES",
    "MIN_USEFUL_MINUTES",
    "OUTPUT_SUBDIR",
    "REGISTERED_ORDER",
    "RESUME_SUBPATH",
    "SEEDS",
    "SOURCE_BUNDLE_SHA256",
    "SOURCE_TOKENIZER_SHA256",
    "STAGES",
    "TINY_LANES",
    "TOTAL_CAP_GPU_HOURS",
    "USR1_LEAD_MINUTES",
    "ByteLevelCodec",
    "ContentFilter",
    "DenseDataError",
    "DevView",
    "Lane",
    "StandInByteCodec",
    "StandInPairCodec",
    "Unit",
    "artifact_sha256",
    "block_gpu_only_kernels",
    "budget_blocks",
    "decode_text",
    "derive_dev_artifact",
    "digit_runs",
    "english_anchors",
    "fixed_blocks",
    "k1_smoke_units",
    "lane_of",
    "lexical_block_scores",
    "plan_units",
    "registered_caps_total",
    "stop_ids_by_language",
    "symbol_only",
    "unit_of",
]
