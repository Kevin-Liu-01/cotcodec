#!/usr/bin/env python3
"""S2 v4 P0.2 inputs: fetch the official Arabic language packs that match the guest's build.

Decision D80 (iv) approves this download: "the official LibreOffice Arabic language packs
matching the guest's LibreOffice 7.3.7 are fetched from the distribution archive". The guest
runs Ubuntu 22.04's ``libreoffice-core`` ``1:7.3.7-0ubuntu0.22.04.4`` (the certified image's
``/var/lib/dpkg/status``, read without a mount by ``infra/q2-mutation/vmprobe``). That version
was the one in ``jammy-updates`` from 2023-12-14 to 2024-05-28 (Launchpad publishing history);
the Arabic language packs ``1:22.04+20230801`` were current there from 2023-08-06 to 2024-02-15.
Both are therefore in the archive state that Ubuntu's snapshot service serves for any instant in
the overlap, with the archive's own signature over that state.

Chain of trust, every link checked here (standard library plus the host's ``gpgv``):

1. ``dists/<suite>/InRelease`` of the snapshot is verified with ``gpgv`` against the Ubuntu
   archive keyring (``/usr/share/keyrings/ubuntu-archive-keyring.gpg``, package
   ``ubuntu-keyring``); the signature must be good and valid (GOODSIG and VALIDSIG, no BADSIG,
   ERRSIG, NO_PUBKEY, EXPSIG, EXPKEYSIG or REVKEYSIG status) and made by the pinned signer
   (``EXPECTED_SIGNER``, the Ubuntu Archive Automatic Signing Key (2018), as the VALIDSIG
   fingerprint and its primary key): any other key in the host keyring is refused; the signed
   text is the one ``gpgv --output`` writes, never a parse of the clearsigned file, and its
   ``Suite`` and ``Codename`` must be the requested suite and its release (``check_release``);
2. the ``Packages.xz`` index named in that signed text is fetched and must match its SHA-256 and
   size there;
3. each requested package's stanza (exact name and version) gives the pool path, size and
   SHA-256 of the ``.deb``; the fetched file must match both;
4. optionally (``--launchpad``), the Launchpad API's own record of the published binary file
   (``binaryFileUrls`` with ``include_meta``) must report the same SHA-256 and size.

Writes ``<out>/debs/<file>.deb``, ``<out>/meta/...`` (InRelease, the signed text, Packages.xz)
and ``<out>/provenance.json``: for every fetched file its URL, filename, size and SHA-256, the
gpgv status lines (signing key fingerprint), the keyring's SHA-256 and the stanzas. Nothing is
installed or executed; the archives are only read later by ``image_build.py``.

Usage (on the login host, network on; never inside a lane job):
  python3 -m harness.s2_locale.fetch_langpacks --out DIR [--snapshot 20240110T000000Z]
      [--suite jammy-updates] [--launchpad]
Re-check a fetched directory offline with the same links (no network; writes verify.json):
  python3 -m harness.s2_locale.fetch_langpacks --verify DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "s2v4-langpack-provenance-v1"
SNAPSHOT_BASE = "https://snapshot.ubuntu.com/ubuntu"
LAUNCHPAD_API = "https://api.launchpad.net/devel"  # binaryFileUrls is a devel-API operation
DEFAULT_SNAPSHOT = "20240110T000000Z"
DEFAULT_SUITE = "jammy-updates"
COMPONENT = "main"
ARCH = "amd64"
KEYRING = "/usr/share/keyrings/ubuntu-archive-keyring.gpg"
# The signer of the archive's InRelease files in the snapshot (Ubuntu Archive Automatic Signing
# Key (2018)); a signature by any other key, even one in the keyring, is refused.
EXPECTED_SIGNER = "F6ECB3762474EDA9D21B7022871920D1991BC93C"
BAD_STATUS = re.compile(r"^\[GNUPG:\] (BADSIG|ERRSIG|NO_PUBKEY|EXPSIG|EXPKEYSIG|REVKEYSIG)\b")
# The guest's LibreOffice and the Arabic packs current beside it (P0.2). libreoffice-l10n-ar is
# the official Arabic language pack of the guest's exact build; the two Ubuntu language packs
# carry GTK's and the base system's Arabic message catalogs (GTK's own dialog strings).
PACKAGES: tuple[tuple[str, str], ...] = (
    ("libreoffice-l10n-ar", "1:7.3.7-0ubuntu0.22.04.4"),
    ("language-pack-ar-base", "1:22.04+20230801"),
    ("language-pack-gnome-ar-base", "1:22.04+20230801"),
)
GUEST_LIBREOFFICE = ("libreoffice-core", "1:7.3.7-0ubuntu0.22.04.4")
SNAPSHOT_RE = re.compile(r"^\d{8}T\d{6}Z$")
SUITE_RE = re.compile(r"^[a-z]+(-[a-z]+)?$")
USER_AGENT = "cotcodec-s2v4-fetch/1 (research; one-off archive fetch)"


class FetchError(RuntimeError):
    """A link of the chain of trust failed; nothing fetched may be used."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def http_get(url: str, timeout: float = 120.0, attempts: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - https only
                if resp.status != 200:
                    raise FetchError(f"{url}: HTTP {resp.status}")
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - retried, then raised
            last = exc
            time.sleep(2.0 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def parse_release_hashes(text: str, field: str = "SHA256") -> dict[str, tuple[str, int]]:
    """``{path: (digest, size)}`` from a Release file's hash section (``field:`` lines)."""
    out: dict[str, tuple[str, int]] = {}
    lines = text.splitlines()
    inside = False
    for line in lines:
        if not line.startswith(" "):
            inside = line.rstrip() == f"{field}:"
            continue
        if inside:
            parts = line.split()
            if len(parts) == 3 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
                out[parts[2]] = (parts[0], int(parts[1]))
    return out


def parse_stanzas(text: str) -> list[dict[str, str]]:
    """Deb822 stanzas (continuation lines folded with newlines)."""
    out: list[dict[str, str]] = []
    cur: dict[str, str] = {}
    last: str | None = None
    for line in text.splitlines():
        if not line.strip():
            if cur:
                out.append(cur)
            cur, last = {}, None
            continue
        if line[0] in " \t" and last is not None:
            cur[last] += "\n" + line.strip()
            continue
        key, _, value = line.partition(":")
        last = key.strip()
        cur[last] = value.strip()
    if cur:
        out.append(cur)
    return out


def find_stanza(stanzas: Iterable[Mapping[str, str]], name: str, version: str) -> dict[str, str]:
    hits = [dict(s) for s in stanzas if s.get("Package") == name and s.get("Version") == version]
    if len(hits) != 1:
        raise FetchError(f"{name} {version}: {len(hits)} stanzas in the signed index (need 1)")
    return hits[0]


def parse_gpgv_status(stdout: str, returncode: int, signed_written: bool,
                      expected: str = EXPECTED_SIGNER) -> dict[str, Any]:  # fmt: skip
    """The verdict on ``gpgv --status-fd 1`` output: good, valid, by ``expected`` (the VALIDSIG
    fingerprint and, when listed, its primary key's), no bad status line, and the signed text
    written."""
    status = [ln for ln in stdout.splitlines() if ln.startswith("[GNUPG:]")]
    valid = [ln.split() for ln in status if ln.startswith("[GNUPG:] VALIDSIG ")]
    fingerprints = [f[2] for f in valid]
    primaries = [f[11] if len(f) > 11 else f[2] for f in valid]
    good = any(ln.startswith("[GNUPG:] GOODSIG ") for ln in status)
    bad = [ln for ln in status if BAD_STATUS.match(ln)]
    signer_ok = bool(valid) and set(fingerprints) == {expected} and set(primaries) == {expected}
    ok = returncode == 0 and good and signer_ok and not bad and signed_written
    return {"ok": ok, "returncode": returncode, "status": status, "good": good,
            "validsig_fingerprints": fingerprints, "primary_fingerprints": primaries,
            "expected_signer": expected, "signer_ok": signer_ok, "bad_status": bad}  # fmt: skip


def gpgv_verify(inrelease: Path, keyring: str, signed_out: Path) -> dict[str, Any]:
    """gpgv over the clearsigned InRelease; the signed text goes to ``signed_out``."""
    if signed_out.exists():
        signed_out.unlink()
    proc = subprocess.run(
        ["gpgv", "--status-fd", "1", "--keyring", keyring, "--output", str(signed_out),
         str(inrelease)],
        capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    out = parse_gpgv_status(proc.stdout, proc.returncode, signed_out.is_file())
    out["stderr"] = proc.stderr.strip().splitlines()[-6:]
    return out


def release_fields(text: str) -> dict[str, str]:
    """The top-level ``Field: value`` lines of a signed Release text (hash sections skipped)."""
    out = {}
    for line in text.splitlines():
        if line and not line.startswith(" ") and ":" in line:
            key, _, value = line.partition(":")
            out.setdefault(key.strip(), value.strip())
    return out


def check_release(signed_text: str, suite: str) -> dict[str, Any]:
    """The signed index is for the requested suite: ``Suite`` is ``suite`` and ``Codename`` its
    release (``jammy`` for ``jammy-updates``)."""
    fields = release_fields(signed_text)
    want = {"Suite": suite, "Codename": suite.split("-", 1)[0]}
    got = {k: fields.get(k) for k in want}
    if got != want:
        raise FetchError(f"the signed InRelease is for {got}, not {want}")
    return got


def launchpad_check(name: str, version: str, filename: str) -> dict[str, Any]:
    """The Launchpad API's record of the published file (sha256 and size), any jammy pocket.

    The publication query needs ``distro_arch_series`` for its ``version`` filter to apply."""
    query = urllib.parse.urlencode({
        "ws.op": "getPublishedBinaries", "binary_name": name, "exact_match": "true",
        "version": version, "ws.size": "50",
        "distro_arch_series": f"{LAUNCHPAD_API}/ubuntu/jammy/{ARCH}",
    })  # fmt: skip
    url = f"{LAUNCHPAD_API}/ubuntu/+archive/primary?{query}"
    pubs = json.loads(http_get(url))
    for pub in pubs.get("entries", []):
        if "/jammy/" not in pub.get("distro_arch_series_link", ""):
            continue
        files_url = pub["self_link"] + "?ws.op=binaryFileUrls&include_meta=true"
        for entry in json.loads(http_get(files_url)):
            if isinstance(entry, dict) and entry.get("url", "").endswith("/" + filename):
                return {
                    "publication": pub["self_link"],
                    "pocket": pub.get("pocket"),
                    "date_published": pub.get("date_published"),
                    "date_superseded": pub.get("date_superseded"),
                    "librarian_url": entry.get("url"),
                    "size": entry.get("size"),
                    "sha1": entry.get("sha1"),
                    "sha256": entry.get("sha256"),
                }
    raise FetchError(f"{name} {version}: no jammy publication lists {filename}")


def fetch(
    out: Path,
    snapshot: str = DEFAULT_SNAPSHOT,
    suite: str = DEFAULT_SUITE,
    packages: Sequence[tuple[str, str]] = PACKAGES,
    keyring: str = KEYRING,
    launchpad: bool = False,
    get=http_get,
    verify=gpgv_verify,
) -> dict[str, Any]:
    if not SNAPSHOT_RE.fullmatch(snapshot):
        raise FetchError(f"snapshot must look like {DEFAULT_SNAPSHOT}")
    if not SUITE_RE.fullmatch(suite):
        raise FetchError("unsafe suite name")
    base = f"{SNAPSHOT_BASE}/{snapshot}"
    meta = out / "meta" / suite
    debs = out / "debs"
    meta.mkdir(parents=True, exist_ok=True)
    debs.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "decision": "D80 (iv)",
        "snapshot": snapshot,
        "suite": suite,
        "component": COMPONENT,
        "architecture": ARCH,
        "guest_libreoffice": {"package": GUEST_LIBREOFFICE[0], "version": GUEST_LIBREOFFICE[1]},
        "t_start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "keyring": {"path": keyring},
        "files": [],
        "packages": [],
    }
    key_path = Path(keyring)
    if key_path.is_file():
        record["keyring"]["sha256"] = sha256_bytes(key_path.read_bytes())

    def keep(kind: str, url: str, path: Path, data: bytes) -> dict[str, Any]:
        path.write_bytes(data)
        entry = {"kind": kind, "url": url, "filename": path.name, "size": len(data),
                 "sha256": sha256_bytes(data), "local": str(path.relative_to(out))}  # fmt: skip
        record["files"].append(entry)
        return entry

    url = f"{base}/dists/{suite}/InRelease"
    inrelease = meta / "InRelease"
    keep("InRelease", url, inrelease, get(url))
    signed = meta / "InRelease.signed.txt"
    sig = verify(inrelease, keyring, signed)
    record["signature"] = sig
    if not sig["ok"]:
        raise FetchError(f"InRelease signature did not verify: {sig['status'][-3:]}")
    signed_text = signed.read_text(encoding="utf-8")
    record["release"] = check_release(signed_text, suite)
    record["files"].append({"kind": "InRelease signed text (gpgv --output)",
                            "filename": signed.name, "size": signed.stat().st_size,
                            "sha256": sha256_bytes(signed.read_bytes()),
                            "local": str(signed.relative_to(out))})  # fmt: skip
    date = re.search(r"^Date: (.+)$", signed_text, re.M)
    record["release_date"] = date.group(1) if date else None
    index_rel = f"{COMPONENT}/binary-{ARCH}/Packages.xz"
    hashes = parse_release_hashes(signed_text)
    if index_rel not in hashes:
        raise FetchError(f"{index_rel} is not in the signed InRelease")
    want_sha, want_size = hashes[index_rel]
    url = f"{base}/dists/{suite}/{index_rel}"
    data = get(url)
    entry = keep("Packages.xz", url, meta / "Packages.xz", data)
    if (entry["sha256"], entry["size"]) != (want_sha, want_size):
        raise FetchError(f"{index_rel}: got {entry['sha256']}/{entry['size']}, signed "
                         f"{want_sha}/{want_size}")  # fmt: skip
    entry["signed_sha256_matches"] = True
    stanzas = parse_stanzas(lzma.decompress(data).decode("utf-8", errors="replace"))
    record["index_stanzas"] = len(stanzas)
    guest = [s for s in stanzas if s.get("Package") == GUEST_LIBREOFFICE[0]]
    record["guest_libreoffice"]["in_index"] = any(s.get("Version") == GUEST_LIBREOFFICE[1]
                                                  for s in guest)  # fmt: skip
    for name, version in packages:
        stanza = find_stanza(stanzas, name, version)
        filename = stanza["Filename"]
        if not re.fullmatch(r"pool/[a-z0-9./+_~-]+\.deb", filename) or ".." in filename:
            raise FetchError(f"unsafe pool path {filename!r}")
        url = f"{base}/{filename}"
        data = get(url)
        entry = keep("deb", url, debs / Path(filename).name, data)
        if entry["sha256"] != stanza["SHA256"] or entry["size"] != int(stanza["Size"]):
            raise FetchError(f"{filename}: got {entry['sha256']}/{entry['size']}, index "
                             f"{stanza['SHA256']}/{stanza['Size']}")  # fmt: skip
        entry["index_sha256_matches"] = True
        pkg = {
            "package": name,
            "version": version,
            "filename": Path(filename).name,
            "url": url,
            "size": entry["size"],
            "sha256": entry["sha256"],
            "md5": hashlib.md5(data).hexdigest(),  # noqa: S324 - recorded beside SHA-256
            "sha1": hashlib.sha1(data).hexdigest(),  # noqa: S324 - recorded beside SHA-256
            "stanza": {k: stanza[k] for k in sorted(stanza) if k != "Description-md5"},
        }
        if launchpad:
            lp = launchpad_check(name, version, Path(filename).name)
            pkg["launchpad"] = lp
            pkg["launchpad_matches"] = (lp.get("sha256") == entry["sha256"]
                                        and int(lp.get("size") or -1) == entry["size"])  # fmt: skip
            if not pkg["launchpad_matches"]:
                raise FetchError(f"{filename}: Launchpad reports "
                                 f"{lp.get('sha256')}/{lp.get('size')}")
        record["packages"].append(pkg)
    record["t_end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record["ok"] = True
    return record


def verify_dir(directory: Path, suite: str = DEFAULT_SUITE, keyring: str = KEYRING,
               packages: Sequence[tuple[str, str]] = PACKAGES,
               verify=gpgv_verify) -> dict[str, Any]:  # fmt: skip
    """The chain of trust re-checked offline on a fetched directory (no download): the stored
    InRelease through ``gpgv`` and the pinned signer, the signed suite, ``Packages.xz`` against
    the signed hash, each stored ``.deb`` against its signed stanza."""
    meta = directory / "meta" / suite
    with tempfile.TemporaryDirectory() as tmp:
        signed = Path(tmp) / "signed.txt"
        sig = verify(meta / "InRelease", keyring, signed)
        if not sig["ok"]:
            raise FetchError(f"InRelease signature did not verify: {sig['status'][-3:]}")
        signed_text = signed.read_text(encoding="utf-8")
    out: dict[str, Any] = {"schema": SCHEMA + "-verify", "signature": sig,
                           "release": check_release(signed_text, suite),
                           "signed_text_sha256": sha256_bytes(signed_text.encode())}  # fmt: skip
    stored = (meta / "InRelease.signed.txt")
    out["stored_signed_text_matches"] = (stored.is_file()
                                         and stored.read_text(encoding="utf-8") == signed_text)
    index_rel = f"{COMPONENT}/binary-{ARCH}/Packages.xz"
    want_sha, want_size = parse_release_hashes(signed_text)[index_rel]
    data = (meta / "Packages.xz").read_bytes()
    if (sha256_bytes(data), len(data)) != (want_sha, want_size):
        raise FetchError(f"{index_rel} differs from the signed hash")
    stanzas = parse_stanzas(lzma.decompress(data).decode("utf-8", errors="replace"))
    out["packages"] = []
    for name, version in packages:
        stanza = find_stanza(stanzas, name, version)
        deb = (directory / "debs" / Path(stanza["Filename"]).name).read_bytes()
        if sha256_bytes(deb) != stanza["SHA256"] or len(deb) != int(stanza["Size"]):
            raise FetchError(f"{stanza['Filename']}: differs from the signed index")
        out["packages"].append({"package": name, "version": version,
                                "sha256": stanza["SHA256"], "size": int(stanza["Size"])})
    out["ok"] = True
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", type=Path, default=None,
                        help="re-check a fetched directory offline (no download)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--snapshot", default=DEFAULT_SNAPSHOT)
    parser.add_argument("--suite", default=DEFAULT_SUITE)
    parser.add_argument("--keyring", default=KEYRING)
    parser.add_argument("--launchpad", action="store_true")
    args = parser.parse_args(argv)
    if args.verify is not None:
        try:
            result = verify_dir(args.verify, args.suite, args.keyring)
        except FetchError as exc:
            result = {"schema": SCHEMA + "-verify", "ok": False, "error": str(exc)}
        print(json.dumps(result, indent=1, sort_keys=True))
        return 0 if result.get("ok") else 2
    if args.out is None:
        parser.error("--out is required (or --verify DIR)")
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        record = fetch(args.out, args.snapshot, args.suite, keyring=args.keyring,
                       launchpad=args.launchpad)  # fmt: skip
    except FetchError as exc:
        failed = {"schema": SCHEMA, "ok": False, "error": str(exc)}
        (args.out / "provenance.failed.json").write_text(json.dumps(failed, indent=1))
        print(json.dumps(failed))
        return 2
    git_sha = Path(".git_sha")
    if git_sha.is_file():
        record["executor_commit"] = git_sha.read_text().strip()
    with tempfile.NamedTemporaryFile("w", dir=args.out, delete=False, suffix=".tmp") as handle:
        json.dump(record, handle, indent=1, sort_keys=True)
        tmp = handle.name
    os.replace(tmp, args.out / "provenance.json")
    print(json.dumps({"ok": True, "packages": [(p["filename"], p["size"], p["sha256"])
                                              for p in record["packages"]]}))  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
