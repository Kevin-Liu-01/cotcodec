"""S2 v4 P0.2 inputs: the language-pack fetch's chain of trust (no network)."""

from __future__ import annotations

import hashlib
import lzma
from pathlib import Path

import pytest

from harness.s2_locale import fetch_langpacks as F

DEB = b"!<arch>\nfake deb bytes\n"


def _stanza(name: str, version: str, data: bytes, filename: str) -> str:
    return (
        f"Package: {name}\nVersion: {version}\nArchitecture: all\nFilename: {filename}\n"
        f"Size: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}\n"
        "Description: x\n continuation\n\n"
    )


def _archive(tamper: str | None = None):
    pkgs = [("libreoffice-l10n-ar", "1:7.3.7-0ubuntu0.22.04.4",
             "pool/main/libr/libreoffice/libreoffice-l10n-ar_7.3.7-0ubuntu0.22.04.4_all.deb")]
    index = "".join(_stanza(n, v, DEB, f) for n, v, f in pkgs)
    index += _stanza("libreoffice-core", "1:7.3.7-0ubuntu0.22.04.4", b"core", "pool/x/core.deb")
    xz = lzma.compress(index.encode())
    signed = (
        "Origin: Ubuntu\nDate: Wed, 10 Jan 2024 00:00:00 UTC\nSHA256:\n"
        f" {hashlib.sha256(xz).hexdigest()} {len(xz)} main/binary-amd64/Packages.xz\n"
        f" {'0' * 64} 12 main/binary-amd64/Packages\n"
    )
    files = {
        "dists/jammy-updates/InRelease": b"-----BEGIN PGP SIGNED MESSAGE-----\n" + signed.encode(),
        "dists/jammy-updates/main/binary-amd64/Packages.xz": xz,
        pkgs[0][2]: DEB if tamper != "deb" else DEB + b"x",
    }

    def get(url: str) -> bytes:
        rel = url.split(f"{F.DEFAULT_SNAPSHOT}/", 1)[1]
        return files[rel]

    def verify(inrelease: Path, keyring: str, signed_out: Path) -> dict:
        signed_out.write_text(signed)
        ok = tamper != "sig"
        return {"ok": ok, "status": ["[GNUPG:] GOODSIG"], "validsig_fingerprints": ["F" * 40]}

    return get, verify, pkgs


def test_parse_release_hashes_reads_only_the_named_section():
    text = "MD5Sum:\n abc 1 x\nSHA256:\n" + f" {'a' * 64} 10 main/x\n" + "Other: y\n"
    assert F.parse_release_hashes(text) == {"main/x": ("a" * 64, 10)}


def test_fetch_records_every_link(tmp_path):
    get, verify, pkgs = _archive()
    rec = F.fetch(tmp_path, packages=[p[:2] for p in pkgs], get=get, verify=verify)
    assert rec["ok"] and rec["guest_libreoffice"]["in_index"]
    kinds = [f["kind"] for f in rec["files"]]
    assert kinds[:3] == ["InRelease", "InRelease signed text (gpgv --output)", "Packages.xz"]
    pkg = rec["packages"][0]
    assert pkg["sha256"] == hashlib.sha256(DEB).hexdigest() and pkg["size"] == len(DEB)
    assert (tmp_path / "debs" / pkg["filename"]).read_bytes() == DEB
    assert pkg["url"].startswith(f"{F.SNAPSHOT_BASE}/{F.DEFAULT_SNAPSHOT}/pool/main/")


def test_fetch_refuses_a_bad_signature(tmp_path):
    get, verify, pkgs = _archive("sig")
    with pytest.raises(F.FetchError, match="signature"):
        F.fetch(tmp_path, packages=[p[:2] for p in pkgs], get=get, verify=verify)


def test_fetch_refuses_a_deb_that_differs_from_the_signed_index(tmp_path):
    get, verify, pkgs = _archive("deb")
    with pytest.raises(F.FetchError, match="index"):
        F.fetch(tmp_path, packages=[p[:2] for p in pkgs], get=get, verify=verify)


def test_fetch_refuses_a_missing_version(tmp_path):
    get, verify, _ = _archive()
    with pytest.raises(F.FetchError, match="0 stanzas"):
        F.fetch(tmp_path, packages=[("libreoffice-l10n-ar", "1:7.3.7-0ubuntu0.22.04.5")],
                get=get, verify=verify)  # fmt: skip


def test_registered_packages_are_the_guest_build():
    names = dict(F.PACKAGES)
    assert names["libreoffice-l10n-ar"] == F.GUEST_LIBREOFFICE[1]
    assert set(names) == {"libreoffice-l10n-ar", "language-pack-ar-base",
                          "language-pack-gnome-ar-base"}  # fmt: skip
