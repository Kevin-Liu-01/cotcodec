"""Fetch pinned public source files (OSWorld task configs, the leaderboard sheet).

OSWorld task configs are read at an exact commit. The file list and each
file's git blob SHA-1 come from the GitHub trees API for that commit; every
file fetched from ``raw.githubusercontent.com`` is checked against its blob
SHA-1, so the bytes are bound to the commit. Verified blobs are cached by
blob SHA-1.

The OSWorld-Verified leaderboard sheet has no declared license. It is fetched
at a pinned site commit, checked against a pinned SHA-256, parsed in memory
for the cells this audit cites, and never written into the repository.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

USER_AGENT = "cotcodec-holo3-rerun-audit/1"
GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"

Fetch = Callable[[str], bytes]


class SourceFetchError(RuntimeError):
    """A pinned source could not be fetched or did not match its pin."""


def http_get(url: str, *, attempts: int = 5, backoff: float = 1.0, timeout: float = 60.0) -> bytes:
    """GET with bounded exponential backoff; fails closed."""
    last: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return response.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in (403, 408, 429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        time.sleep(backoff * (2**attempt))
    raise SourceFetchError(f"GET failed for {url}: {last}")


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


class GitHubCommitFiles:
    """Files of one repository at one commit, verified against git blob SHA-1."""

    def __init__(
        self,
        repo: str,
        commit: str,
        *,
        cache_dir: Path | None = None,
        fetch: Fetch = http_get,
    ) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise SourceFetchError("commit must be a full 40-character SHA-1")
        self.repo = repo
        self.commit = commit
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._fetch = fetch
        self._tree: dict[str, str] | None = None
        self.tree_sha256: str | None = None
        self.fetched = 0

    def _cached(self, name: str) -> Path | None:
        return self.cache_dir / name if self.cache_dir else None

    def tree(self) -> dict[str, str]:
        """Map path -> blob SHA-1 for every blob at the commit."""
        if self._tree is not None:
            return self._tree
        cache = self._cached(f"tree-{self.repo.replace('/', '__')}-{self.commit}.json")
        if cache and cache.is_file():
            raw = cache.read_bytes()
        else:
            url = f"{GITHUB_API}/repos/{self.repo}/git/trees/{self.commit}?recursive=1"
            raw = self._fetch(url)
        payload = json.loads(raw)
        # The trees API echoes the root tree SHA, not the commit SHA; each
        # file is bound to the commit through its blob SHA-1 instead.
        if payload.get("truncated"):
            raise SourceFetchError(f"tree listing for {self.repo}@{self.commit} is truncated")
        tree = {
            entry["path"]: entry["sha"]
            for entry in payload.get("tree", [])
            if entry.get("type") == "blob"
        }
        if not tree:
            raise SourceFetchError(f"empty tree for {self.repo}@{self.commit}")
        if cache and not cache.is_file():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(raw)
        self.tree_sha256 = hashlib.sha256(raw).hexdigest()
        self._tree = tree
        return tree

    def read(self, path: str) -> bytes:
        tree = self.tree()
        blob = tree.get(path)
        if blob is None:
            raise SourceFetchError(f"{path} is not in {self.repo}@{self.commit}")
        cache = self._cached(f"blob-{blob}")
        if cache and cache.is_file():
            data = cache.read_bytes()
        else:
            url = f"{GITHUB_RAW}/{self.repo}/{self.commit}/{urllib.request.quote(path)}"
            data = self._fetch(url)
            self.fetched += 1
        if git_blob_sha1(data) != blob:
            raise SourceFetchError(f"{path}: content does not match blob {blob}")
        if cache and not cache.is_file():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(data)
        return data


def fetch_pinned_file(
    url: str, sha256: str, *, cache_dir: Path | None = None, fetch: Fetch = http_get
) -> bytes:
    """Fetch a file and require an exact SHA-256 (cached by that digest)."""
    cache = Path(cache_dir) / f"sha256-{sha256}" if cache_dir else None
    data = cache.read_bytes() if cache and cache.is_file() else fetch(url)
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256:
        raise SourceFetchError(f"{url}: sha256 {actual} != pinned {sha256}")
    if cache and not cache.is_file():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(data)
    return data


_XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_CELL_RE = re.compile(r"([A-Z]+)(\d+)")


def read_xlsx_first_sheet(data: bytes) -> dict[int, dict[str, str]]:
    """Return {row number: {column letter: text}} for the first worksheet.

    Stdlib only: shared strings, inline strings and plain values. Enough for
    the leaderboard sheet; not a general spreadsheet reader.
    """
    try:
        book = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise SourceFetchError(f"not an xlsx file: {exc}") from exc
    tag_t = f"{{{_XLSX_NS['m']}}}t"
    shared: list[str] = []
    if "xl/sharedStrings.xml" in book.namelist():
        root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
        for item in root.findall("m:si", _XLSX_NS):
            shared.append("".join(node.text or "" for node in item.iter(tag_t)))
    sheet = ElementTree.fromstring(book.read("xl/worksheets/sheet1.xml"))
    data_node = sheet.find("m:sheetData", _XLSX_NS)
    rows: dict[int, dict[str, str]] = {}
    if data_node is None:
        return rows
    for row in data_node:
        number = int(row.attrib["r"])
        cells: dict[str, str] = {}
        for cell in row:
            match = _CELL_RE.fullmatch(cell.attrib.get("r", ""))
            if not match:
                continue
            value = cell.find("m:v", _XLSX_NS)
            kind = cell.attrib.get("t")
            if value is not None and value.text is not None:
                text = shared[int(value.text)] if kind == "s" else value.text
            else:
                inline = cell.find("m:is", _XLSX_NS)
                if inline is None:
                    continue
                text = "".join(node.text or "" for node in inline.iter(tag_t))
            cells[match.group(1)] = text
        rows[number] = cells
    return rows


def describe_fetch(obj: Any) -> dict[str, Any]:
    """Small, public-safe description of a GitHubCommitFiles instance."""
    return {
        "repo": obj.repo,
        "commit": obj.commit,
        "tree_listing_sha256": obj.tree_sha256,
        "files_fetched_from_network": obj.fetched,
    }
