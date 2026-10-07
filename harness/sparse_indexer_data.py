"""Data objects of the Q3 K1 localization screen (CPU, NumPy; no torch).

The K1 bundle is one JSON file, hash-bound at submission, that holds every
token the GPU job reads: the packed training stream, the evaluation contexts
(haystack plus Belebele needle), the queries and multiple-choice options, the
prompt ledger and the source and licence manifest. This module owns:

* Belebele loading, the join on ``(link, question_number)`` (row order differs
  across languages) and the passage-id split through
  ``harness.translation_supervised_indexer.split_passage_ids``;
* a clean reimplementation of the ParaDocs document filter (the upstream
  ``rewicks/ParaDocs`` tool carries no licence, so it is reimplemented, not
  vendored), including its target-side consecutiveness quirk;
* the held-out-script character filter, exact 50-gram and MinHash
  (128 permutations, token 5-gram shingles, Jaccard >= 0.8) deduplication of
  training and haystack documents against every evaluation text;
* sequence packing, context construction and the bundle codec.

Every ordering is a SHA-256 or seeded-NumPy order, never Python's ``hash()``.
"""

from __future__ import annotations

import base64
import contextlib
import csv
import gzip
import hashlib
import io
import json
import re
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
from numpy.typing import NDArray

from harness.translation_supervised_indexer import (
    IndexerContractError,
    PassageSplit,
    assert_reads_within,
    split_passage_ids,
)

U32 = NDArray[np.uint32]

BUNDLE_SCHEMA = "cotcodec-k1-bundle-v1"
BUNDLE_LICENSE = "LicenseRef-cotcodec-k1-bundle-v1"
SEQUENCE_LENGTH = 8192
CONTEXT_LENGTH = 8192
SINK_TOKEN_ID = 151643
SPLIT_SEED = 42
STREAM_SEED = 42
TRAIN_SEQUENCES = 2441
DEV_SEQUENCES = 64
MONO_ITEM_MAX_TOKENS = 2048
HAYSTACK_DOC_MIN_TOKENS = 32
HAYSTACK_DOC_MAX_TOKENS = 1536
DEPTHS = (0.15, 0.50, 0.85)
HELD_OUT_SCRIPT_MAX_FRACTION = 0.005
NGRAM_EXACT = 50
MINHASH_PERMUTATIONS = 128
MINHASH_SHINGLE = 5
MINHASH_BANDS = 32
MINHASH_THRESHOLD = 0.8

# Revisions opened and recorded in the reviewed plan (2026-10-06).
BELEBELE_REPO = "facebook/belebele"
BELEBELE_REVISION = "7899cdfa4e1e0d733fd77c848e2c273cb1d32be2"
FINEWEB2_REPO = "HuggingFaceFW/fineweb-2"
FINEWEB2_REVISION = "af9c13333eb981300149d5ca60a8e9d659b276b9"
FINEWEB_REPO = "HuggingFaceFW/fineweb"
FINEWEB_REVISION = "9bb295ddab0e05d785b879661af7260fed5140fc"
FINEWEB_EN_SHARD = "data/CC-MAIN-2025-26/004_00046.parquet"
PARADOCS_REPO = "jhu-clsp/paradocs"
PARADOCS_REVISION = "f80095affa44545d18d0d64a574f9b8679017196"
PARADOCS_TOOL_REVISION = "88f4ed95dadc577605e775ad447eefde5229d611"
# en-th/hi/km exist only as all/paracrawl. The en-de/fr/es/pl all/paracrawl
# files open with millions of lines that carry no document positions, so the
# same-script pairs read the authors' strict split (registered asymmetry); the
# reimplemented filter runs on both.
PARADOCS_SOURCE = {
    "en-th": "all/paracrawl", "en-hi": "all/paracrawl", "en-km": "all/paracrawl",
    "en-de": "strict", "en-fr": "strict", "en-es": "strict", "en-pl": "strict",
}


@dataclass(frozen=True, slots=True)
class Language:
    code: str  # ISO 639-1 used in pair names
    belebele: str  # Belebele / FineWeb-2 config
    script: str
    role: str  # english | train-cross | train-same | train-mono | heldout-cross | heldout-same


LANGUAGES: dict[str, Language] = {
    "en": Language("en", "eng_Latn", "Latn", "english"),
    "ja": Language("ja", "jpn_Jpan", "Jpan", "heldout-cross"),
    "ko": Language("ko", "kor_Hang", "Hang", "heldout-cross"),
    "bn": Language("bn", "ben_Beng", "Beng", "heldout-cross"),
    "ta": Language("ta", "tam_Taml", "Taml", "heldout-cross"),
    "el": Language("el", "ell_Grek", "Grek", "heldout-cross"),
    "he": Language("he", "heb_Hebr", "Hebr", "heldout-cross"),
    "ka": Language("ka", "kat_Geor", "Geor", "heldout-cross"),
    "id": Language("id", "ind_Latn", "Latn", "heldout-same"),
    "tr": Language("tr", "tur_Latn", "Latn", "heldout-same"),
    "sw": Language("sw", "swh_Latn", "Latn", "heldout-same"),
    "nl": Language("nl", "nld_Latn", "Latn", "heldout-same"),
    "it": Language("it", "ita_Latn", "Latn", "heldout-same"),
    "th": Language("th", "tha_Thai", "Thai", "train-cross"),
    "hi": Language("hi", "hin_Deva", "Deva", "train-cross"),
    "km": Language("km", "khm_Khmr", "Khmr", "train-cross"),
    "zh": Language("zh", "zho_Hans", "Hans", "train-mono"),
    "ar": Language("ar", "arb_Arab", "Arab", "train-mono"),
    "de": Language("de", "deu_Latn", "Latn", "train-same"),
    "fr": Language("fr", "fra_Latn", "Latn", "train-same"),
    "es": Language("es", "spa_Latn", "Latn", "train-same"),
    "pl": Language("pl", "pol_Latn", "Latn", "train-same"),
    "ru": Language("ru", "rus_Cyrl", "Cyrl", "train-mono"),
}
# FineWeb-2 uses cmn_Hani for Mandarin; Belebele uses zho_Hans.
FINEWEB2_CONFIG = {
    code: ("cmn_Hani" if code == "zh" else lang.belebele) for code, lang in LANGUAGES.items()
}
BELEBELE_LANGUAGES = (
    "en", "ja", "ko", "bn", "ta", "el", "he", "ka", "id", "tr", "sw", "nl", "it",
    "th", "hi", "km", "zh", "ar",
)
CROSS_SCRIPT_HELDOUT = ("ja", "ko", "bn", "ta", "el", "he", "ka")
SAME_SCRIPT_HELDOUT = ("id", "tr", "sw", "nl", "it")
HELDOUT = CROSS_SCRIPT_HELDOUT + SAME_SCRIPT_HELDOUT
BILINGUAL_PAIRS = ("en-de", "en-fr", "en-es", "en-pl", "en-th", "en-hi", "en-km")
CROSS_SCRIPT_BILINGUAL = ("en-th", "en-hi", "en-km")
SAME_SCRIPT_BILINGUAL = ("en-de", "en-fr", "en-es", "en-pl")
MONOLINGUAL_TRAINING = ("de", "fr", "es", "pl", "th", "hi", "km", "zh", "ar", "ru")
NEEDLE_LANGUAGES = ("en",) + HELDOUT

# Unicode blocks of the seven held-out cross-script scripts. Han is excluded on
# purpose: Japanese kanji overlap Mandarin training text (claim boundary).
HELD_OUT_SCRIPT_RANGES: tuple[tuple[int, int], ...] = (
    (0x3040, 0x30FF),  # Hiragana, Katakana
    (0x31F0, 0x31FF),  # Katakana phonetic extensions
    (0xFF66, 0xFF9D),  # Halfwidth Katakana
    (0x1100, 0x11FF),  # Hangul Jamo
    (0x3130, 0x318F),  # Hangul compatibility Jamo
    (0xAC00, 0xD7AF),  # Hangul syllables
    (0x0980, 0x09FF),  # Bengali
    (0x0B80, 0x0BFF),  # Tamil
    (0x0370, 0x03FF),  # Greek and Coptic
    (0x1F00, 0x1FFF),  # Greek extended
    (0x0590, 0x05FF),  # Hebrew
    (0x10A0, 0x10FF),  # Georgian
    (0x1C90, 0x1CBF),  # Georgian extended
    (0x2D00, 0x2D2F),  # Georgian supplement
)


class DataContractError(ValueError):
    """Raised when a data input violates the registered K1 bundle contract."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_order(keys: Iterable[str], salt: str) -> list[str]:
    """Deterministic SHA-256 order (independent of Python's string hashing)."""

    return sorted(keys, key=lambda key: hashlib.sha256(f"{salt}|{key}".encode()).hexdigest())


def seeded_rng(*parts: object) -> np.random.Generator:
    payload = "|".join(str(part) for part in parts).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(payload).digest()[:8], "big"))


# --------------------------------------------------------------------------- #
# Script filter
# --------------------------------------------------------------------------- #

_HELD_OUT_PATTERN = re.compile(
    "[" + "".join(f"\\u{lo:04x}-\\u{hi:04x}" for lo, hi in HELD_OUT_SCRIPT_RANGES) + "]"
)


def held_out_script_fraction(text: str) -> float:
    """Share of non-space characters that belong to a held-out cross-script block."""

    visible = sum(1 for ch in text if not ch.isspace())
    if visible == 0:
        return 0.0
    return len(_HELD_OUT_PATTERN.findall(text)) / visible


def passes_script_filter(text: str) -> bool:
    return held_out_script_fraction(text) <= HELD_OUT_SCRIPT_MAX_FRACTION


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


# Frequent function words, chosen to be specific to one language each. Used to
# drop Latin-script training text that reads as a held-out Latin-script
# language (misaligned lines exist: an en-pl strict line carries Italian).
FUNCTION_WORDS: dict[str, frozenset[str]] = {
    "it": _words(
        "il della delle degli gli questo questa sono anche nella alla "
        "perché essere stato molto"
    ),
    "nl": _words(
        "het een niet zijn voor ook worden wordt deze naar maar bij "
        "wij hebben onze"
    ),
    "tr": _words(
        "ve bir bu için ile olarak daha çok olan gibi ama kadar değil "
        "sonra veya"
    ),
    "id": _words(
        "yang dan dengan untuk dari ini itu tidak dalam akan pada "
        "juga adalah kami mereka"
    ),
    "sw": _words(
        "ya wa kwa katika ni za kuwa hii cha hiyo lakini pia sana "
        "watu kwamba"
    ),
    "de": _words(
        "der die und das ist nicht mit sich auch auf für eine dem den "
        "werden"
    ),
    "fr": _words(
        "le les des et est une pour dans pas qui que sur avec sont "
        "nous"
    ),
    "es": _words(
        "el los las del por para con como más pero sus este está son "
        "también"
    ),
    "pl": _words(
        "się nie jest że jak oraz dla przez jako są które tym może "
        "także"
    ),
    "en": _words(
        "the and of to is that for with are this was from have not "
        "which"
    ),
}
HELD_OUT_LATIN = ("it", "nl", "tr", "id", "sw")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def function_word_scores(text: str) -> dict[str, int]:
    words = [w.lower() for w in _WORD.findall(text)]
    return {lang: sum(1 for w in words if w in vocab) for lang, vocab in FUNCTION_WORDS.items()}


def reads_as_held_out_latin(text: str, expected: str, minimum: int = 3) -> bool:
    """True when a held-out Latin-script language out-scores the expected language."""

    scores = function_word_scores(text)
    best = max(HELD_OUT_LATIN, key=lambda lang: (scores[lang], lang))
    return scores[best] >= minimum and scores[best] > scores.get(expected, 0)


# --------------------------------------------------------------------------- #
# Belebele
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class BelebeleRow:
    link: str
    question_number: int
    passage: str
    question: str
    options: tuple[str, str, str, str]
    correct: int  # 1-based, as released

    @property
    def key(self) -> tuple[str, int]:
        return (self.link, self.question_number)


def parse_belebele_line(line: str) -> BelebeleRow:
    raw = json.loads(line)
    try:
        options = tuple(str(raw[f"mc_answer{i}"]) for i in range(1, 5))
        row = BelebeleRow(
            link=str(raw["link"]),
            question_number=int(raw["question_number"]),
            passage=str(raw["flores_passage"]),
            question=str(raw["question"]),
            options=options,  # type: ignore[arg-type]
            correct=int(raw["correct_answer_num"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DataContractError(f"malformed Belebele row: {exc}") from exc
    if row.correct not in (1, 2, 3, 4):
        raise DataContractError("correct_answer_num must be 1-4")
    return row


def load_belebele(path: Path) -> list[BelebeleRow]:
    with path.open(encoding="utf-8") as handle:
        return [parse_belebele_line(line) for line in handle if line.strip()]


def belebele_join(rows_by_language: Mapping[str, Sequence[BelebeleRow]]) -> dict[
    tuple[str, int], dict[str, BelebeleRow]
]:
    """Join languages on ``(link, question_number)`` and check the answer key agrees."""

    if "en" not in rows_by_language:
        raise DataContractError("the join is anchored on English")
    joined: dict[tuple[str, int], dict[str, BelebeleRow]] = {}
    for language, rows in rows_by_language.items():
        seen: set[tuple[str, int]] = set()
        for row in rows:
            if row.key in seen:
                raise DataContractError(f"{language}: duplicate key {row.key}")
            seen.add(row.key)
            joined.setdefault(row.key, {})[language] = row
    languages = set(rows_by_language)
    for key, variants in joined.items():
        if set(variants) != languages:
            missing = sorted(languages - set(variants))
            raise DataContractError(f"{key} is missing in {missing}")
        answers = {row.correct for row in variants.values()}
        if len(answers) != 1:
            raise DataContractError(f"{key}: answer key differs across languages")
    return joined


def passage_split(joined: Mapping[tuple[str, int], Mapping[str, BelebeleRow]]) -> PassageSplit:
    links = sorted({link for link, _ in joined})
    return split_passage_ids(links, seed=SPLIT_SEED)


def questions_in(
    joined: Mapping[tuple[str, int], Mapping[str, BelebeleRow]], split: PassageSplit,
    partition: str,
) -> list[tuple[str, int]]:
    allowed = {"development": split.development, "audit": split.audit,
               "primary": split.primary}[partition]
    keys = sorted(key for key in joined if key[0] in allowed)
    assert_reads_within((link for link, _ in keys), split, partition)
    return keys


# --------------------------------------------------------------------------- #
# Tokenizer
# --------------------------------------------------------------------------- #


class Tokenizer:
    """Thin wrapper over ``tokenizers.Tokenizer`` (no special tokens added)."""

    def __init__(self, path: Path) -> None:
        from tokenizers import Tokenizer as _Tokenizer

        self.path = path
        self.sha256 = sha256_file(path)
        self._tok = _Tokenizer.from_file(str(path))

    def encode(self, text: str) -> list[int]:
        return list(self._tok.encode(text, add_special_tokens=False).ids)

    def encode_batch(self, texts: Sequence[str]) -> list[list[int]]:
        return [list(e.ids) for e in self._tok.encode_batch(list(texts), add_special_tokens=False)]


# --------------------------------------------------------------------------- #
# N-gram hashing, MinHash and the dedup index
# --------------------------------------------------------------------------- #

_HASH_BASE = np.uint64(0x9E3779B97F4A7C15)


def window_hashes(tokens: Sequence[int] | NDArray[Any], n: int) -> NDArray[np.uint64]:
    """64-bit polynomial hashes of every length-``n`` token window (wrapping arithmetic)."""

    array = np.asarray(tokens, dtype=np.uint64) + np.uint64(1)
    if array.size < n:
        return np.zeros(0, dtype=np.uint64)
    count = array.size - n + 1
    out = np.zeros(count, dtype=np.uint64)
    power = np.uint64(1)
    with np.errstate(over="ignore"):
        for offset in range(n - 1, -1, -1):
            out = out + array[offset : offset + count] * power
            power = power * _HASH_BASE
    return out


class MinHasher:
    """MinHash over token 5-gram shingles with multiply-shift universal hashing."""

    def __init__(self, permutations: int = MINHASH_PERMUTATIONS, seed: int = 42) -> None:
        rng = np.random.default_rng(seed)
        self.a = rng.integers(1, 2**63, size=permutations, dtype=np.uint64) | np.uint64(1)
        self.b = rng.integers(0, 2**63, size=permutations, dtype=np.uint64)
        self.permutations = permutations

    def signature(self, tokens: Sequence[int] | NDArray[Any]) -> NDArray[np.uint64] | None:
        shingles = np.unique(window_hashes(tokens, MINHASH_SHINGLE))
        if shingles.size == 0:
            return None
        with np.errstate(over="ignore"):
            mixed = (shingles[:, None] * self.a[None, :] + self.b[None, :]) >> np.uint64(32)
        return mixed.min(axis=0)


def _band_keys(signature: NDArray[np.uint64], bands: int) -> list[bytes]:
    rows = signature.size // bands
    return [signature[i * rows : (i + 1) * rows].tobytes() for i in range(bands)]


@dataclass
class DedupStats:
    checked: int = 0
    exact_ngram: int = 0
    minhash: int = 0
    script: int = 0
    latin: int = 0

    def as_dict(self) -> dict[str, int]:
        return {"checked": self.checked, "removed_exact_50gram": self.exact_ngram,
                "removed_minhash": self.minhash, "removed_held_out_script": self.script,
                "removed_held_out_latin_function_words": self.latin}


class DedupIndex:
    """Exact 50-gram and MinHash-LSH index over every evaluation text."""

    def __init__(self, eval_token_lists: Iterable[Sequence[int]], bands: int = MINHASH_BANDS):
        self.hasher = MinHasher()
        self.bands = bands
        windows: list[NDArray[np.uint64]] = []
        self.signatures: list[NDArray[np.uint64]] = []
        self.buckets: dict[bytes, list[int]] = {}
        texts = 0
        for tokens in eval_token_lists:
            texts += 1
            windows.append(window_hashes(tokens, NGRAM_EXACT))
            signature = self.hasher.signature(tokens)
            if signature is None:
                continue
            index = len(self.signatures)
            self.signatures.append(signature)
            for key in _band_keys(signature, bands):
                self.buckets.setdefault(key, []).append(index)
        self.ngrams = np.unique(np.concatenate(windows)) if windows else np.zeros(0, np.uint64)
        self.texts = texts

    def has_exact_ngram(self, tokens: Sequence[int] | NDArray[Any]) -> bool:
        hashes = window_hashes(tokens, NGRAM_EXACT)
        if hashes.size == 0 or self.ngrams.size == 0:
            return False
        return bool(np.isin(hashes, self.ngrams, assume_unique=False).any())

    def max_jaccard(self, tokens: Sequence[int] | NDArray[Any]) -> float:
        signature = self.hasher.signature(tokens)
        if signature is None:
            return 0.0
        candidates: set[int] = set()
        for key in _band_keys(signature, self.bands):
            candidates.update(self.buckets.get(key, ()))
        best = 0.0
        for index in sorted(candidates):
            best = max(best, float(np.mean(self.signatures[index] == signature)))
        return best

    def check(self, tokens: Sequence[int] | NDArray[Any], stats: DedupStats) -> bool:
        """True when the document is clean; counts the first removal reason."""

        stats.checked += 1
        if self.has_exact_ngram(tokens):
            stats.exact_ngram += 1
            return False
        if self.max_jaccard(tokens) >= MINHASH_THRESHOLD:
            stats.minhash += 1
            return False
        return True


# --------------------------------------------------------------------------- #
# ParaDocs filter (reimplementation of rewicks/ParaDocs @ 88f4ed95 semantics)
# --------------------------------------------------------------------------- #

PARADOCS_FIELDS = (
    "src", "tgt", "similarity_one", "similarity_two", "collection",
    "src_paragraph_id", "tgt_paragraph_id", "src_sentence_id", "tgt_sentence_id",
    "src_start_index", "src_end_index", "tgt_start_index", "tgt_end_index",
    "src_language_id", "tgt_language_id", "frequency", "src_docid", "tgt_docid",
)
_POSITION_FIELDS = (
    "src_paragraph_id", "src_sentence_id", "src_start_index", "src_end_index",
    "tgt_paragraph_id", "tgt_sentence_id", "tgt_start_index", "tgt_end_index",
)


@dataclass(frozen=True, slots=True)
class ParadocsFilter:
    """Registered release filter settings (upstream code defaults)."""

    minimum_size: int = 2
    frequency_cutoff: int = 100
    lid_cutoff: float = 0.5
    min_avg_score: float = 0.0


@dataclass
class ParadocsStats:
    lines: int = 0
    breaks_none: int = 0
    breaks_malformed: int = 0
    breaks_frequency: int = 0
    breaks_lid: int = 0
    breaks_empty: int = 0
    documents: int = 0
    kept_documents: int = 0
    kept_lines: int = 0

    def as_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


def _field(row: Mapping[str | None, Any], name: str) -> Any:
    return row.get(name)


def paradocs_breaks(row: Mapping[str | None, Any], cfg: ParadocsFilter,
                    stats: ParadocsStats | None = None) -> bool:
    """Upstream ``breaks_document``: a line that ends any running document."""

    values = [_field(row, name) for name in _POSITION_FIELDS]
    if "None" in values:
        if stats:
            stats.breaks_none += 1
        return True
    try:
        frequency = int(_field(row, "frequency"))
        src_lid = float(_field(row, "src_language_id"))
        tgt_lid = float(_field(row, "tgt_language_id"))
        for name in _POSITION_FIELDS[2:4] + _POSITION_FIELDS[6:8]:
            int(_field(row, name))
    except (TypeError, ValueError):
        # Upstream raises on a malformed line and stops; a streaming reader
        # treats it as a document break instead (registered deviation).
        if stats:
            stats.breaks_malformed += 1
        return True
    if frequency > cfg.frequency_cutoff:
        if stats:
            stats.breaks_frequency += 1
        return True
    if src_lid < cfg.lid_cutoff or tgt_lid < cfg.lid_cutoff:
        if stats:
            stats.breaks_lid += 1
        return True
    if not str(_field(row, "src")).strip() or not str(_field(row, "tgt")).strip():
        if stats:
            stats.breaks_empty += 1
        return True
    return False


def paradocs_is_consecutive(preceding: Mapping[str | None, Any],
                            subsequent: Mapping[str | None, Any]) -> bool:
    """Upstream ``is_consecutive``, quirk included.

    The target-side test compares ``subsequent.tgt_start_index`` with
    ``subsequent.tgt_end_index`` (not with ``preceding.tgt_end_index``), so it
    is true for every well-formed line. It is replicated for fidelity.
    """

    return (
        int(subsequent["src_start_index"]) - int(preceding["src_end_index"]) <= 2
        and int(subsequent["tgt_start_index"]) - int(subsequent["tgt_end_index"]) <= 2
    )


def paradocs_documents(
    rows: Iterable[Mapping[str | None, Any]], cfg: ParadocsFilter,
    stats: ParadocsStats | None = None,
) -> Iterator[list[Mapping[str | None, Any]]]:
    """Upstream ``yield_doc`` followed by ``meets_requirements``; yields kept documents."""

    document: list[Mapping[str | None, Any]] | None = None
    last_id: str | None = None

    def finish(doc: list[Mapping[str | None, Any]] | None) -> list | None:
        if doc is None:
            return None
        if stats:
            stats.documents += 1
        if len(doc) < cfg.minimum_size:
            return None
        total = 0.0
        for line in doc:
            with contextlib.suppress(TypeError, ValueError):
                total += float(line["similarity_two"])
        if total / len(doc) < cfg.min_avg_score:
            return None
        if stats:
            stats.kept_documents += 1
            stats.kept_lines += len(doc)
        return doc

    for row in rows:
        if stats:
            stats.lines += 1
        doc_id = f"{row.get('src_docid')}-{row.get('tgt_docid')}"
        if document is None:
            if not paradocs_breaks(row, cfg, stats):
                document = [row]
            last_id = doc_id
        elif doc_id == last_id:
            if paradocs_breaks(row, cfg, stats):
                kept = finish(document)
                if kept:
                    yield kept
                document = None
            elif paradocs_is_consecutive(document[-1], row):
                document.append(row)
            else:
                kept = finish(document)
                if kept:
                    yield kept
                document = [row]
        else:
            kept = finish(document)
            if kept:
                yield kept
            last_id = doc_id
            document = None if paradocs_breaks(row, cfg, stats) else [row]
    kept = finish(document)
    if kept:
        yield kept


def paradocs_rows(text_lines: Iterable[str]) -> Iterator[dict[str | None, Any]]:
    """Parse TSV lines exactly as upstream (csv.DictReader, tab, QUOTE_NONE)."""

    csv.field_size_limit(sys.maxsize)
    reader = csv.DictReader(
        text_lines, delimiter="\t", fieldnames=list(PARADOCS_FIELDS), quoting=csv.QUOTE_NONE
    )
    yield from reader


class CountingReader(io.RawIOBase):
    """Wrap a byte iterator; count compressed bytes consumed."""

    def __init__(self, chunks: Iterator[bytes]) -> None:
        self._chunks = chunks
        self._buffer = b""
        self.consumed = 0

    def readable(self) -> bool:
        return True

    def readinto(self, target: Any) -> int:
        while not self._buffer:
            try:
                self._buffer = next(self._chunks)
            except StopIteration:
                return 0
        size = min(len(target), len(self._buffer))
        target[:size] = self._buffer[:size]
        self._buffer = self._buffer[size:]
        self.consumed += size
        return size


def gzip_text_lines(raw: BinaryIO) -> Iterator[str]:
    """Universal-newline text lines of a (possibly multi-member) gzip byte stream.

    ``gzip.open(path, 'rt')`` in upstream decodes UTF-8 strictly; invalid
    bytes would crash it. This reader uses ``errors='replace'`` and the
    replacement count is not tracked; ParaCrawl text is UTF-8.
    """

    with gzip.GzipFile(fileobj=raw) as handle:
        text = io.TextIOWrapper(handle, encoding="utf-8", errors="replace", newline=None)
        yield from text


def document_sides(doc: Sequence[Mapping[str | None, Any]]) -> tuple[str, str]:
    """English (src) and X (tgt) sides of a kept document, sentences joined by spaces."""

    src = " ".join(str(line["src"]).strip() for line in doc)
    tgt = " ".join(str(line["tgt"]).strip() for line in doc)
    return src, tgt


def document_id(pair: str, file_name: str, ordinal: int, doc: Sequence[Mapping]) -> str:
    first = doc[0]
    return f"{pair}:{file_name}:{ordinal}:{first.get('src_docid')}-{first.get('tgt_docid')}"


# --------------------------------------------------------------------------- #
# Packing and contexts
# --------------------------------------------------------------------------- #


def pack_sequences(
    items: Iterable[Sequence[int]], n_sequences: int, length: int = SEQUENCE_LENGTH,
    sink: int = SINK_TOKEN_ID,
) -> tuple[U32, int]:
    """Greedy packing: ``[sink] item [sink] item ...``; the item that overflows is cut.

    Returns the ``(n_sequences, length)`` array and the number of items used.
    Raises when the items run out before ``n_sequences`` are full.
    """

    out = np.zeros((n_sequences, length), dtype=np.uint32)
    iterator = iter(items)
    used = 0
    for index in range(n_sequences):
        row: list[int] = [sink]
        while len(row) < length:
            try:
                item = next(iterator)
            except StopIteration as exc:
                raise DataContractError(
                    f"items ran out at sequence {index} of {n_sequences}"
                ) from exc
            used += 1
            if len(row) > 1:
                row.append(sink)
            row.extend(int(t) for t in item)
        out[index] = np.asarray(row[:length], dtype=np.uint32)
    return out, used


@dataclass(frozen=True, slots=True)
class Context:
    tokens: U32
    needle_start: int
    needle_end: int
    haystack_ids: tuple[str, ...]


def build_context(
    needle: Sequence[int] | None,
    haystack: Sequence[tuple[str, Sequence[int]]],
    depth: float,
    sep: Sequence[int],
    length: int = CONTEXT_LENGTH,
    sink: int = SINK_TOKEN_ID,
) -> Context:
    """``[sink] + haystack docs (each followed by sep)`` with the needle at a doc boundary.

    The needle (followed by ``sep``) is inserted at the haystack document
    boundary nearest to ``depth * (length - 1 - |needle| - |sep|)`` (ties go to
    the earlier boundary). The haystack tail is cut so the context is exactly
    ``length`` tokens. With ``needle=None`` the context is haystack only.
    """

    if not 0.0 <= depth <= 1.0:
        raise DataContractError("depth must lie in [0, 1]")
    sep = list(sep)
    stream: list[int] = []
    boundaries: list[int] = []
    used: list[str] = []
    budget = length - 1
    for doc_id, tokens in haystack:
        if len(stream) >= budget:
            break
        boundaries.append(len(stream))
        stream.extend(int(t) for t in tokens)
        stream.extend(sep)
        used.append(doc_id)
    if len(stream) < budget:
        raise DataContractError("haystack is too short for the context")
    if needle is None:
        tokens = np.asarray([sink] + stream[:budget], dtype=np.uint32)
        return Context(tokens, -1, -1, tuple(used))
    block = list(needle) + sep
    latest = budget - len(block)
    eligible = [b for b in boundaries if b <= latest]
    if not eligible:
        raise DataContractError("needle does not fit inside the context")
    target = depth * latest
    insert = min(eligible, key=lambda b: (abs(b - target), b))
    merged = stream[:insert] + block + stream[insert:]
    tokens = np.asarray([sink] + merged[:budget], dtype=np.uint32)
    start = 1 + insert
    return Context(tokens, start, start + len(needle), tuple(used))


SENTENCE_END = re.compile(r"(?<=[.!?。！？।])\s+|(?<=[。！？])")


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_END.split(text) if part and part.strip()]


# --------------------------------------------------------------------------- #
# Bundle codec
# --------------------------------------------------------------------------- #


def encode_array(array: NDArray[Any]) -> dict[str, Any]:
    array = np.ascontiguousarray(array)
    if array.dtype not in (np.uint32, np.int64, np.int32, np.float32):
        raise DataContractError(f"unsupported bundle dtype {array.dtype}")
    little = array.astype(array.dtype.newbyteorder("<"), copy=False)
    return {
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "sha256": sha256_bytes(little.tobytes()),
        "base64": base64.b64encode(little.tobytes()).decode("ascii"),
    }


def decode_array(payload: Mapping[str, Any]) -> NDArray[Any]:
    dtype = np.dtype(str(payload["dtype"])).newbyteorder("<")
    raw = base64.b64decode(payload["base64"], validate=True)
    if sha256_bytes(raw) != payload["sha256"]:
        raise DataContractError("bundle array digest mismatch")
    shape = tuple(int(v) for v in payload["shape"])
    return np.frombuffer(raw, dtype=dtype).reshape(shape).astype(dtype.newbyteorder("="))


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n").encode("ascii")


def load_bundle(path: Path, expected_sha256: str) -> dict[str, Any]:
    """Verify the file digest before parsing; raise on mismatch or wrong schema."""

    raw = path.read_bytes()
    actual = sha256_bytes(raw)
    if actual != expected_sha256:
        raise DataContractError(f"bundle sha256 {actual} != expected {expected_sha256}")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get("schema") != BUNDLE_SCHEMA:
        raise DataContractError("bundle schema is not " + BUNDLE_SCHEMA)
    return payload


@dataclass(frozen=True)
class EvalPrompt:
    prompt_id: str
    role: str
    partition: str
    pair: str
    pair_kind: str
    condition: str
    family_id: str
    cluster: str
    context_index: int
    query_index: int


@dataclass
class EvalView:
    """Decoded evaluation section of a bundle."""

    context_tokens: U32
    context_offsets: NDArray[np.int64]
    context_meta: list[dict[str, Any]]
    query_tokens: U32
    query_offsets: NDArray[np.int64]
    query_meta: list[dict[str, Any]]
    option_tokens: U32
    option_offsets: NDArray[np.int64]
    prompts: list[EvalPrompt] = field(default_factory=list)

    def context(self, index: int) -> U32:
        return self.context_tokens[self.context_offsets[index] : self.context_offsets[index + 1]]

    def query(self, index: int) -> U32:
        return self.query_tokens[self.query_offsets[index] : self.query_offsets[index + 1]]

    def option(self, index: int) -> U32:
        return self.option_tokens[self.option_offsets[index] : self.option_offsets[index + 1]]

    def prompt_tokens(self, prompt: EvalPrompt) -> tuple[U32, int, int, int, int]:
        """Tokens plus absolute query rows ``[q0, q1)`` and needle span ``[n0, n1)``."""

        context = self.context(prompt.context_index)
        query = self.query(prompt.query_index)
        meta_c = self.context_meta[prompt.context_index]
        meta_q = self.query_meta[prompt.query_index]
        tokens = np.concatenate([context, query]).astype(np.uint32)
        q0 = len(context) + int(meta_q["row_start"])
        q1 = len(context) + int(meta_q["row_end"])
        return tokens, q0, q1, int(meta_c["needle_start"]), int(meta_c["needle_end"])


def eval_view(bundle: Mapping[str, Any], partitions: Sequence[str],
              split: PassageSplit | None = None) -> EvalView:
    """Decode the evaluation section, keeping only prompts in ``partitions``.

    When ``split`` is given every kept prompt's cluster must lie in its declared
    partition, or ``IndexerContractError`` is raised (fail-closed read).
    """

    section = bundle["eval"]
    prompts = [EvalPrompt(**row) for row in section["prompts"] if row["partition"] in partitions]
    if split is not None:
        for partition in partitions:
            clusters = [p.cluster for p in prompts if p.partition == partition]
            if clusters:
                assert_reads_within(clusters, split, partition)
    return EvalView(
        context_tokens=decode_array(section["context_tokens"]),
        context_offsets=decode_array(section["context_offsets"]),
        context_meta=list(section["context_meta"]),
        query_tokens=decode_array(section["query_tokens"]),
        query_offsets=decode_array(section["query_offsets"]),
        query_meta=list(section["query_meta"]),
        option_tokens=decode_array(section["option_tokens"]),
        option_offsets=decode_array(section["option_offsets"]),
        prompts=prompts,
    )


def split_from_bundle(bundle: Mapping[str, Any]) -> PassageSplit:
    section = bundle["split"]
    return PassageSplit(
        development=frozenset(section["development"]),
        audit=frozenset(section["audit"]),
        primary=frozenset(section["primary"]),
        seed=int(section["seed"]),
    )


def check_partition_read(bundle: Mapping[str, Any], partition: str,
                         clusters: Iterable[str]) -> None:
    assert_reads_within(clusters, split_from_bundle(bundle), partition)


__all__ = [
    "BELEBELE_LANGUAGES",
    "BILINGUAL_PAIRS",
    "BUNDLE_LICENSE",
    "BUNDLE_SCHEMA",
    "CROSS_SCRIPT_HELDOUT",
    "LANGUAGES",
    "SAME_SCRIPT_HELDOUT",
    "BelebeleRow",
    "Context",
    "CountingReader",
    "DataContractError",
    "DedupIndex",
    "DedupStats",
    "EvalPrompt",
    "EvalView",
    "IndexerContractError",
    "MinHasher",
    "ParadocsFilter",
    "ParadocsStats",
    "Tokenizer",
    "belebele_join",
    "build_context",
    "canonical_json_bytes",
    "decode_array",
    "document_sides",
    "encode_array",
    "eval_view",
    "gzip_text_lines",
    "held_out_script_fraction",
    "load_belebele",
    "load_bundle",
    "pack_sequences",
    "paradocs_breaks",
    "paradocs_documents",
    "paradocs_is_consecutive",
    "paradocs_rows",
    "passage_split",
    "passes_script_filter",
    "reads_as_held_out_latin",
    "questions_in",
    "split_from_bundle",
    "split_sentences",
    "window_hashes",
]
