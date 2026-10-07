"""Read selected members of a remote ZIP archive through HTTP range requests.

The Holo3 rerun audit needs a few thousand small files out of public archives
that are 5-13 GB each. This module reads only the central directory and the
byte ranges that hold the selected members, and checks every member against
the CRC-32 and size recorded in the central directory. It never writes a
member that failed its check.

Integrity model:

* ``HFRangeSource`` resolves a file at a pinned Hugging Face revision and
  refuses to read unless the hub reports that same revision
  (``X-Repo-Commit``), the pinned LFS SHA-256 (``X-Linked-Etag``) and the
  pinned size (``X-Linked-Size``). The bytes are then served from the
  content-addressed LFS/Xet object.
* Every member is checked against its central-directory CRC-32 and size.
  Callers add a stronger check (``SHA256SUMS``) where the archive ships one.
* A member cache is content-addressed by archive LFS SHA-256, member name,
  CRC-32 and size; a cached entry is re-checked on every read and a corrupted
  entry fails closed.

Network use is bounded: at most ``MAX_CONCURRENCY`` concurrent range requests,
exponential backoff, and a hard failure after ``max_attempts``.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import os
import struct
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

MAX_CONCURRENCY = 6
LOCAL_HEADER_SIGNATURE = b"PK\x03\x04"
LOCAL_HEADER_SIZE = 30
HF_ENDPOINT = "https://huggingface.co"
USER_AGENT = "cotcodec-holo3-rerun-audit/1"


class RemoteZipError(RuntimeError):
    """Base class for every failure this module raises."""


class RemoteFetchError(RemoteZipError):
    """A range request failed after all retries, or returned the wrong bytes."""


class SourceIdentityError(RemoteZipError):
    """The remote object is not the pinned revision, size or LFS object."""


class ZipIntegrityError(RemoteZipError):
    """A member failed its CRC-32 or size check, or the archive is malformed."""


class MissingMemberError(RemoteZipError):
    """A required member is not in the archive."""


class RangeSource(Protocol):
    """Random-access byte source of known size."""

    size: int

    def read_range(self, start: int, length: int) -> bytes: ...

    def identity(self) -> dict[str, Any]: ...


@dataclass
class TransferStats:
    requests: int = 0
    bytes: int = 0
    retries: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, *, requests: int = 0, nbytes: int = 0, retries: int = 0) -> None:
        with self.lock:
            self.requests += requests
            self.bytes += nbytes
            self.retries += retries

    def as_dict(self) -> dict[str, int]:
        return {"requests": self.requests, "bytes": self.bytes, "retries": self.retries}


class BytesSource:
    """In-memory source, used by tests and for already-verified local bytes."""

    def __init__(self, data: bytes, identity: dict[str, Any] | None = None) -> None:
        self._data = bytes(data)
        self.size = len(self._data)
        self._identity = identity or {"kind": "bytes", "sha256": sha256_bytes(self._data)}
        self.stats = TransferStats()

    def read_range(self, start: int, length: int) -> bytes:
        if start < 0 or length < 0 or start + length > self.size:
            raise RemoteFetchError(f"range {start}+{length} outside 0..{self.size}")
        self.stats.add(requests=1, nbytes=length)
        return self._data[start : start + length]

    def identity(self) -> dict[str, Any]:
        return dict(self._identity)


class SubSource:
    """A window of another source, e.g. a STORED zip nested in an outer zip."""

    def __init__(self, base: RangeSource, offset: int, size: int, label: str) -> None:
        if offset < 0 or size < 0 or offset + size > base.size:
            raise ZipIntegrityError(f"nested window {label} lies outside its parent")
        self.base = base
        self.offset = offset
        self.size = size
        self.label = label

    def read_range(self, start: int, length: int) -> bytes:
        if start < 0 or length < 0 or start + length > self.size:
            raise RemoteFetchError(f"range {start}+{length} outside nested 0..{self.size}")
        return self.base.read_range(self.offset + start, length)

    def identity(self) -> dict[str, Any]:
        return {
            "kind": "nested",
            "parent": self.base.identity(),
            "member": self.label,
            "offset": self.offset,
            "size": self.size,
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:  # noqa: D102
        return None


Opener = Callable[[urllib.request.Request, float], Any]


def _default_open(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310


def _default_open_no_redirect(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.build_opener(_NoRedirect).open(request, timeout=timeout)


class HFRangeSource:
    """A file at a pinned Hugging Face revision, read by byte range.

    ``resolve_open`` must not follow redirects; ``range_open`` follows them.
    Both are injectable so that tests never touch the network.
    """

    def __init__(
        self,
        repo: str,
        revision: str,
        path: str,
        *,
        expected_size: int,
        expected_sha256: str,
        repo_type: str = "datasets",
        max_attempts: int = 6,
        backoff_seconds: float = 1.0,
        timeout: float = 120.0,
        resolve_open: Opener | None = None,
        range_open: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        stats: TransferStats | None = None,
        semaphore: threading.Semaphore | None = None,
    ) -> None:
        if len(revision) != 40:
            raise SourceIdentityError("revision must be a full 40-character commit")
        self.repo = repo
        self.revision = revision
        self.path = path
        self.size = expected_size
        self.expected_sha256 = expected_sha256
        self.repo_type = repo_type
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.timeout = timeout
        self._resolve_open = resolve_open or _default_open_no_redirect
        self._range_open = range_open or _default_open
        self._sleep = sleep
        self.stats = stats or TransferStats()
        self._semaphore = semaphore or threading.Semaphore(MAX_CONCURRENCY)
        self._url: str | None = None
        self._lock = threading.Lock()

    @property
    def resolve_url(self) -> str:
        quoted = urllib.request.quote(self.path)
        return f"{HF_ENDPOINT}/{self.repo_type}/{self.repo}/resolve/{self.revision}/{quoted}"

    def identity(self) -> dict[str, Any]:
        return {
            "kind": "huggingface",
            "repo": self.repo,
            "repo_type": self.repo_type,
            "revision": self.revision,
            "path": self.path,
            "size": self.size,
            "lfs_sha256": self.expected_sha256,
        }

    def _check_headers(self, headers: Any) -> str:
        commit = headers.get("X-Repo-Commit")
        size = headers.get("X-Linked-Size")
        etag = (headers.get("X-Linked-Etag") or "").strip('"')
        location = headers.get("Location")
        if commit != self.revision:
            raise SourceIdentityError(
                f"{self.path}: hub served commit {commit}, pinned {self.revision}"
            )
        if size is None or int(size) != self.size:
            raise SourceIdentityError(f"{self.path}: hub size {size}, pinned {self.size}")
        if etag != self.expected_sha256:
            raise SourceIdentityError(
                f"{self.path}: hub LFS oid {etag}, pinned {self.expected_sha256}"
            )
        if not location:
            raise SourceIdentityError(f"{self.path}: hub did not redirect to the LFS object")
        return str(location)

    def resolve(self, force: bool = False) -> str:
        with self._lock:
            if self._url is not None and not force:
                return self._url
            request = urllib.request.Request(
                self.resolve_url, method="HEAD", headers={"User-Agent": USER_AGENT}
            )
            last: Exception | None = None
            for attempt in range(self.max_attempts):
                try:
                    response = self._resolve_open(request, self.timeout)
                    headers = response.headers
                except urllib.error.HTTPError as exc:
                    if exc.code in (301, 302, 303, 307, 308):
                        self._url = self._check_headers(exc.headers)
                        return self._url
                    last = exc
                    if exc.code not in (429, 500, 502, 503, 504):
                        break
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    last = exc
                else:
                    raise SourceIdentityError(
                        f"{self.path}: expected a redirect to the LFS object, got "
                        f"{getattr(response, 'status', '?')} ({headers.get('Content-Type')})"
                    )
                self.stats.add(retries=1)
                self._sleep(self.backoff_seconds * (2**attempt))
            raise RemoteFetchError(f"{self.path}: could not resolve: {last}")

    def read_range(self, start: int, length: int) -> bytes:
        if length == 0:
            return b""
        end = start + length - 1
        if start < 0 or end >= self.size:
            raise RemoteFetchError(f"{self.path}: range {start}-{end} outside 0..{self.size - 1}")
        last: Exception | None = None
        for attempt in range(self.max_attempts):
            url = self.resolve(force=attempt > 0 and isinstance(last, urllib.error.HTTPError))
            request = urllib.request.Request(
                url, headers={"Range": f"bytes={start}-{end}", "User-Agent": USER_AGENT}
            )
            try:
                with self._semaphore:
                    response = self._range_open(request, self.timeout)
                    with contextlib.closing(response):
                        status = getattr(response, "status", None)
                        content_range = response.headers.get("Content-Range", "")
                        data = response.read()
                expected_range = f"bytes {start}-{end}/{self.size}"
                if status != 206 or content_range != expected_range or len(data) != length:
                    raise RemoteFetchError(
                        f"{self.path}: bad range reply status={status} "
                        f"content-range={content_range!r} bytes={len(data)} want {length}"
                    )
                self.stats.add(requests=1, nbytes=len(data))
                return data
            except urllib.error.HTTPError as exc:
                last = exc
                if exc.code not in (401, 403, 408, 410, 429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, OSError, RemoteFetchError) as exc:
                last = exc
            self.stats.add(retries=1)
            self._sleep(self.backoff_seconds * (2**attempt))
        raise RemoteFetchError(f"{self.path}: range {start}-{end} failed: {last}")


class _SeekableReader(io.RawIOBase):
    """Seekable file object over a RangeSource with a single read-ahead block.

    Used only so that :mod:`zipfile` can parse the end-of-central-directory
    records and the central directory (ZIP64 included) in a handful of reads.
    """

    def __init__(self, source: RangeSource, readahead: int = 1 << 16) -> None:
        self.source = source
        self.pos = 0
        self.readahead = readahead
        self._block_start = -1
        self._block = b""

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.source.size + offset
        else:
            raise ValueError(f"bad whence {whence}")
        return self.pos

    def readinto(self, buffer: Any) -> int:
        want = min(len(buffer), max(0, self.source.size - self.pos))
        if want == 0:
            return 0
        start = self._block_start
        if not (start >= 0 and start <= self.pos and self.pos + want <= start + len(self._block)):
            length = min(max(want, self.readahead), self.source.size - self.pos)
            self._block = self.source.read_range(self.pos, length)
            self._block_start = self.pos
        offset = self.pos - self._block_start
        buffer[:want] = self._block[offset : offset + want]
        self.pos += want
        return want


@dataclass(frozen=True)
class ZipMember:
    name: str
    header_offset: int
    compress_size: int
    file_size: int
    crc: int
    compress_type: int
    flag_bits: int

    @property
    def is_dir(self) -> bool:
        return self.name.endswith("/")


def list_members(source: RangeSource) -> list[ZipMember]:
    """Parse the central directory (ZIP64 aware) of a remote archive."""
    try:
        archive = zipfile.ZipFile(_SeekableReader(source))
    except zipfile.BadZipFile as exc:
        raise ZipIntegrityError(f"not a zip archive: {exc}") from exc
    members = [
        ZipMember(
            name=info.filename,
            header_offset=info.header_offset,
            compress_size=info.compress_size,
            file_size=info.file_size,
            crc=info.CRC,
            compress_type=info.compress_type,
            flag_bits=info.flag_bits,
        )
        for info in archive.infolist()
    ]
    names = [m.name for m in members]
    if len(set(names)) != len(names):
        raise ZipIntegrityError("archive has duplicate member names")
    return members


def stored_member_window(source: RangeSource, member: ZipMember) -> SubSource:
    """Return the data window of a STORED member, e.g. a nested zip."""
    if member.compress_type != zipfile.ZIP_STORED:
        raise ZipIntegrityError(f"{member.name} is not STORED; cannot read it by offset")
    header = source.read_range(member.header_offset, LOCAL_HEADER_SIZE)
    start = _data_start(header, member)
    return SubSource(source, start, member.compress_size, member.name)


def _data_start(header: bytes, member: ZipMember) -> int:
    if header[:4] != LOCAL_HEADER_SIGNATURE:
        raise ZipIntegrityError(f"{member.name}: bad local header signature")
    name_len, extra_len = struct.unpack("<HH", header[26:30])
    return member.header_offset + LOCAL_HEADER_SIZE + name_len + extra_len


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_member(member: ZipMember, raw: bytes) -> bytes:
    """Decompress one member's data and check its CRC-32 and size."""
    if member.flag_bits & 0x1:
        raise ZipIntegrityError(f"{member.name}: encrypted members are not supported")
    if member.compress_type == zipfile.ZIP_STORED:
        data = raw
    elif member.compress_type == zipfile.ZIP_DEFLATED:
        try:
            inflater = zlib.decompressobj(-15)
            data = inflater.decompress(raw) + inflater.flush()
        except zlib.error as exc:
            raise ZipIntegrityError(f"{member.name}: inflate failed: {exc}") from exc
    else:
        raise ZipIntegrityError(f"{member.name}: unsupported compression {member.compress_type}")
    if len(data) != member.file_size:
        raise ZipIntegrityError(f"{member.name}: size {len(data)} != {member.file_size}")
    if zlib.crc32(data) & 0xFFFFFFFF != member.crc:
        raise ZipIntegrityError(f"{member.name}: CRC-32 mismatch")
    return data


class MemberCache:
    """Content-addressed cache of verified member bytes."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @staticmethod
    def key(namespace: str, member: ZipMember) -> str:
        token = f"{namespace}\0{member.name}\0{member.crc:08x}\0{member.file_size}"
        return hashlib.sha256(token.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / key

    def get(self, namespace: str, member: ZipMember) -> bytes | None:
        path = self._path(self.key(namespace, member))
        if not path.is_file():
            return None
        data = path.read_bytes()
        if len(data) != member.file_size or zlib.crc32(data) & 0xFFFFFFFF != member.crc:
            raise ZipIntegrityError(f"cache entry for {member.name} is corrupt: {path.name}")
        return data

    def put(self, namespace: str, member: ZipMember, data: bytes) -> None:
        path = self._path(self.key(namespace, member))
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(handle, "wb") as out:
                out.write(data)
            os.replace(temp, path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temp)
            raise


@dataclass(frozen=True)
class Span:
    start: int
    end: int  # exclusive
    members: tuple[ZipMember, ...]


def plan_spans(
    members: Iterable[ZipMember],
    *,
    slack: int = 1024,
    max_gap: int = 1 << 20,
    max_span: int = 32 << 20,
    archive_size: int | None = None,
) -> list[Span]:
    """Group members into contiguous byte ranges to keep request counts low.

    ``slack`` bounds the local-header extra field; a member whose local header
    is longer is re-read on its own.
    """
    ordered = sorted(members, key=lambda m: m.header_offset)
    spans: list[Span] = []
    current: list[ZipMember] = []
    start = end = 0
    for member in ordered:
        name_len = len(member.name.encode("utf-8"))
        m_start = member.header_offset
        m_end = m_start + LOCAL_HEADER_SIZE + name_len + member.compress_size + slack
        if archive_size is not None:
            m_end = min(m_end, archive_size)
        if current and m_start - end <= max_gap and m_end - start <= max_span:
            current.append(member)
            end = max(end, m_end)
            continue
        if current:
            spans.append(Span(start, end, tuple(current)))
        current, start, end = [member], m_start, m_end
    if current:
        spans.append(Span(start, end, tuple(current)))
    return spans


def _extract_span(source: RangeSource, span: Span) -> dict[str, bytes]:
    blob = source.read_range(span.start, span.end - span.start)
    out: dict[str, bytes] = {}
    for member in span.members:
        rel = member.header_offset - span.start
        header = blob[rel : rel + LOCAL_HEADER_SIZE]
        data_start = _data_start(header, member) - span.start
        data_end = data_start + member.compress_size
        if data_end <= len(blob):
            raw = blob[data_start:data_end]
        else:
            absolute = data_start + span.start
            raw = source.read_range(absolute, member.compress_size)
        out[member.name] = decode_member(member, raw)
    return out


def extract_members(
    source: RangeSource,
    members: Iterable[ZipMember],
    *,
    cache: MemberCache | None = None,
    namespace: str = "",
    uncached: Callable[[ZipMember], bool] = lambda member: False,
    max_workers: int = MAX_CONCURRENCY,
    max_gap: int = 1 << 20,
    max_span: int = 32 << 20,
) -> dict[str, bytes]:
    """Fetch, decompress and CRC-check the given members.

    Members for which ``uncached(member)`` is true are held in memory only and
    never written to the cache (used for logs that carry infrastructure
    identifiers).
    """
    if not 1 <= max_workers <= MAX_CONCURRENCY:
        raise ValueError(f"max_workers must be 1..{MAX_CONCURRENCY}")
    wanted = [m for m in members if not m.is_dir]
    out: dict[str, bytes] = {}
    pending: list[ZipMember] = []
    for member in wanted:
        hit = cache.get(namespace, member) if cache and not uncached(member) else None
        if hit is None:
            pending.append(member)
        else:
            out[member.name] = hit
    spans = plan_spans(pending, max_gap=max_gap, max_span=max_span, archive_size=source.size)
    if spans:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(spans))) as pool:
            for chunk in pool.map(lambda span: _extract_span(source, span), spans):
                out.update(chunk)
    if cache:
        for member in pending:
            if not uncached(member):
                cache.put(namespace, member, out[member.name])
    missing = [m.name for m in wanted if m.name not in out]
    if missing:
        raise MissingMemberError(f"{len(missing)} members not extracted, e.g. {missing[0]}")
    return out


def select(members: Iterable[ZipMember], names: Iterable[str]) -> list[ZipMember]:
    """Return the members with exactly these names, failing closed if any is absent."""
    by_name = {m.name: m for m in members}
    chosen: list[ZipMember] = []
    absent: list[str] = []
    for name in names:
        member = by_name.get(name)
        if member is None:
            absent.append(name)
        else:
            chosen.append(member)
    if absent:
        raise MissingMemberError(f"{len(absent)} required members absent, e.g. {absent[0]}")
    return chosen
