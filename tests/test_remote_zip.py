from __future__ import annotations

import io
import random
import threading
import time
import urllib.error
import zipfile
from email.message import Message
from pathlib import Path

import pytest

from harness import remote_zip
from harness.remote_zip import BytesSource, HFRangeSource, MemberCache

REV = "5473c39e42a538a187a9b2c2b499db59d560fd8c"
OID = "0" * 63 + "1"


def make_zip(
    entries: dict[str, bytes], stored: set[str] = frozenset(), zip64: bool = False
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            method = zipfile.ZIP_STORED if name in stored else zipfile.ZIP_DEFLATED
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = method
            with archive.open(info, "w", force_zip64=zip64) as handle:
                handle.write(data)
    return buffer.getvalue()


ENTRIES = {
    "root/a/status.json": b'{"score": "1"}',
    "root/a/result.txt": b"1\n",
    "root/b/big.bin": bytes(range(256)) * 400,
    "root/b/status.json": b'{"score": "0"}',
}


def test_list_and_extract_round_trip_with_zip64() -> None:
    for zip64 in (False, True):
        source = BytesSource(make_zip(ENTRIES, stored={"root/a/result.txt"}, zip64=zip64))
        members = remote_zip.list_members(source)
        assert {m.name for m in members} == set(ENTRIES)
        out = remote_zip.extract_members(source, members, max_workers=2)
        assert out == ENTRIES


def test_crc_tamper_fails_closed() -> None:
    data = bytearray(make_zip({"x.txt": b"hello world"}, stored={"x.txt"}))
    data[data.index(b"hello world")] ^= 0x01
    source = BytesSource(bytes(data))
    (member,) = remote_zip.list_members(source)
    with pytest.raises(remote_zip.ZipIntegrityError, match="CRC"):
        remote_zip.extract_members(source, [member])


def test_missing_member_fails_closed() -> None:
    source = BytesSource(make_zip(ENTRIES))
    members = remote_zip.list_members(source)
    with pytest.raises(remote_zip.MissingMemberError):
        remote_zip.select(members, ["root/a/status.json", "root/c/status.json"])


def test_not_a_zip_fails() -> None:
    with pytest.raises(remote_zip.ZipIntegrityError):
        remote_zip.list_members(BytesSource(b"PK not really" * 10))


def test_cache_round_trip_uncached_members_and_corruption(tmp_path: Path) -> None:
    source = BytesSource(make_zip(ENTRIES))
    members = remote_zip.list_members(source)
    cache = MemberCache(tmp_path)
    keep_out = "root/b/big.bin"
    first = remote_zip.extract_members(
        source, members, cache=cache, namespace=OID, uncached=lambda m: m.name == keep_out
    )
    assert first == ENTRIES
    cached_files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert len(cached_files) == len(ENTRIES) - 1  # the uncached member never hits disk
    assert all(ENTRIES[keep_out] != p.read_bytes() for p in cached_files)

    requests_before = source.stats.requests
    small = [m for m in members if m.name != keep_out]
    assert remote_zip.extract_members(source, small, cache=cache, namespace=OID) == {
        m.name: ENTRIES[m.name] for m in small
    }
    assert source.stats.requests == requests_before  # served from cache

    victim = cache._path(cache.key(OID, small[0]))
    victim.write_bytes(b"tampered")
    with pytest.raises(remote_zip.ZipIntegrityError, match="corrupt"):
        remote_zip.extract_members(source, small, cache=cache, namespace=OID)


def test_nested_stored_zip_is_read_by_window() -> None:
    inner = make_zip(
        {"t/x/task_summary.json": b'{"reward": 1.0}', "t/x/images/0.png": b"\x89" * 5000}
    )
    outer = make_zip(
        {"pkg/README.md": b"r", "pkg/runs/inner.zip": inner}, stored={"pkg/runs/inner.zip"}
    )
    source = BytesSource(outer)
    (member,) = remote_zip.select(remote_zip.list_members(source), ["pkg/runs/inner.zip"])
    window = remote_zip.stored_member_window(source, member)
    assert window.size == len(inner)
    inner_members = remote_zip.list_members(window)
    wanted = [m for m in inner_members if m.name.endswith("task_summary.json")]
    assert remote_zip.extract_members(window, wanted) == {
        "t/x/task_summary.json": b'{"reward": 1.0}'
    }
    deflated = remote_zip.select(remote_zip.list_members(source), ["pkg/README.md"])[0]
    if deflated.compress_type != zipfile.ZIP_STORED:
        with pytest.raises(remote_zip.ZipIntegrityError):
            remote_zip.stored_member_window(source, deflated)


def test_plan_spans_coalesces_nearby_members_only() -> None:
    def member(offset: int, size: int) -> remote_zip.ZipMember:
        return remote_zip.ZipMember(f"m{offset}", offset, size, size, 0, 0, 0)

    spans = remote_zip.plan_spans(
        [member(0, 100), member(2_000, 100), member(10_000_000, 100)], max_gap=1 << 20
    )
    assert [len(s.members) for s in spans] == [2, 1]
    capped = remote_zip.plan_spans([member(0, 100), member(2_000, 100)], max_span=1500)
    assert [len(s.members) for s in capped] == [1, 1]


class TrackingSource(BytesSource):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.active = 0
        self.peak = 0
        self._guard = threading.Lock()

    def read_range(self, start: int, length: int) -> bytes:
        with self._guard:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.01)
        try:
            return super().read_range(start, length)
        finally:
            with self._guard:
                self.active -= 1


def test_concurrency_is_bounded() -> None:
    entries = {f"d{i}/f.bin": random.Random(i).randbytes(3000) for i in range(40)}
    source = TrackingSource(make_zip(entries))
    members = remote_zip.list_members(source)
    remote_zip.extract_members(source, members, max_workers=3, max_gap=0, max_span=4000)
    assert 1 < source.peak <= 3
    with pytest.raises(ValueError):
        remote_zip.extract_members(source, members, max_workers=remote_zip.MAX_CONCURRENCY + 1)


# --------------------------------------------------------------------------- #
# HFRangeSource with fake transports
# --------------------------------------------------------------------------- #


def _headers(**values: str) -> Message:
    message = Message()
    for key, value in values.items():
        message[key.replace("_", "-")] = value
    return message


class FakeResponse:
    def __init__(self, status: int, data: bytes, headers: Message) -> None:
        self.status = status
        self._data = data
        self.headers = headers

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        pass


def resolver(commit: str = REV, size: int = 1000, etag: str = OID, calls: list | None = None):
    def open_(request, timeout):
        if calls is not None:
            calls.append(request.full_url)
        headers = _headers(
            X_Repo_Commit=commit,
            X_Linked_Size=str(size),
            X_Linked_Etag=f'"{etag}"',
            Location="https://cdn/x",
        )
        raise urllib.error.HTTPError(request.full_url, 302, "Found", headers, None)

    return open_


def ranger(blob: bytes, failures: int = 0, bad_range: bool = False):
    state = {"calls": 0}

    def open_(request, timeout):
        state["calls"] += 1
        if state["calls"] <= failures:
            raise urllib.error.HTTPError(request.full_url, 503, "busy", _headers(), None)
        spec = request.headers["Range"].split("=")[1]
        start, end = (int(x) for x in spec.split("-"))
        content_range = f"bytes {start}-{end}/{len(blob)}"
        if bad_range:
            content_range = f"bytes 0-{end - start}/{len(blob)}"
        return FakeResponse(206, blob[start : end + 1], _headers(Content_Range=content_range))

    return open_, state


def hf_source(blob: bytes, **kwargs) -> HFRangeSource:
    sleeps: list[float] = []
    source = HFRangeSource(
        "org/data",
        REV,
        "a.zip",
        expected_size=len(blob),
        expected_sha256=OID,
        sleep=sleeps.append,
        backoff_seconds=0.5,
        max_attempts=4,
        **kwargs,
    )
    source.sleeps = sleeps  # type: ignore[attr-defined]
    return source


def test_hf_source_checks_revision_size_and_lfs_oid() -> None:
    blob = bytes(1000)
    range_open, _ = ranger(blob)
    ok = hf_source(blob, resolve_open=resolver(), range_open=range_open)
    assert ok.read_range(10, 5) == bytes(5)
    for bad in (resolver(commit="f" * 40), resolver(size=999), resolver(etag="e" * 64)):
        source = hf_source(blob, resolve_open=bad, range_open=range_open)
        with pytest.raises(remote_zip.SourceIdentityError):
            source.read_range(0, 1)
    with pytest.raises(remote_zip.SourceIdentityError):
        HFRangeSource("org/data", "main", "a.zip", expected_size=1, expected_sha256=OID)


def test_hf_source_retries_with_backoff_then_fails_closed() -> None:
    blob = bytes(range(256)) * 4
    range_open, state = ranger(blob, failures=2)
    calls: list[str] = []
    source = hf_source(
        blob, resolve_open=resolver(size=len(blob), calls=calls), range_open=range_open
    )
    assert source.read_range(3, 4) == blob[3:7]
    assert source.sleeps == [0.5, 1.0]  # exponential backoff
    assert len(calls) == 3  # re-resolves the signed URL after an HTTP error
    assert source.stats.retries == 2

    always, _ = ranger(blob, failures=99)
    failing = hf_source(blob, resolve_open=resolver(size=len(blob)), range_open=always)
    with pytest.raises(remote_zip.RemoteFetchError):
        failing.read_range(0, 10)
    assert failing.sleeps == [0.5, 1.0, 2.0, 4.0]

    wrong, _ = ranger(blob, bad_range=True)
    mislabeled = hf_source(blob, resolve_open=resolver(size=len(blob)), range_open=wrong)
    with pytest.raises(remote_zip.RemoteFetchError):
        mislabeled.read_range(100, 10)
