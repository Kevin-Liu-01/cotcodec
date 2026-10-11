#!/usr/bin/env python3
"""Snapshot the primary sources behind the S2 fixture's per-application switches (D68 repair).

For each URL it records the HTTP status, fetch time, SHA-256 and size of the full body and the
line numbers and text of the lines matching the given patterns. Bodies are not stored (licences
vary; the hash binds the record to the bytes). Writes one JSON per URL into the snapshot dir.

Usage: python fetch-mechanism-sources.py <snapshot_dir>
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

LO = "https://raw.githubusercontent.com/LibreOffice/core/08f5d410a474badedeaa3fbabaea9b6f564d1b83"
SOURCES = [
    # LibreOffice VCL: paragraph direction of UI text follows the BiDiRtl layout flag (no auto mode)
    (f"{LO}/vcl/source/text/ImplLayoutArgs.cxx", [r"BiDiRtl", r"ubidi_setPara", r"nLevel"], "MPL-2.0"),
    # LibreOffice: where windows and output devices get the RTL text layout mode
    (f"{LO}/vcl/source/outdev/outdev.cxx", [r"GetLayoutRTL", r"BiDiRtl \|", r"ComplexTextLayoutFlags::Default"], "MPL-2.0"),
    # LibreOffice: UI strings come from gettext catalogs under program/resource for every UI language
    # (no en-US special case); the qtz key-id pseudo-locale shows pseudo-locales are supported
    (f"{LO}/unotools/source/i18n/resmgr.cxx", [r"add_messages_path", r"pgettext\(", r"== \"qtz\"", r"bindtextdomain"], "MPL-2.0"),
    # LibreOffice gtk3 plugin: default widget direction from AllSettings::GetLayoutRTL
    (f"{LO}/vcl/unx/gtk3/gtkinst.cxx", [r"gtk_widget_set_default_direction", r"GetLayoutRTL"], "MPL-2.0"),
    # LibreOffice configmgr: finalized nodes in a lower layer cannot be overridden by the user layer
    (f"{LO}/configmgr/source/xcuparser.cxx", [r"finalized"], "MPL-2.0"),
    # LibreOffice Calc: English function names switch
    (f"{LO}/officecfg/registry/schema/org/openoffice/Office/Calc.xcs", [r"EnglishFunctionName"], "MPL-2.0"),
    # LibreOffice: CTL and UIMirroring schema
    (f"{LO}/officecfg/registry/schema/org/openoffice/Office/Common.xcs", [r"UIMirroring", r"CTLFont"], "MPL-2.0"),
    # GTK 3 and GTK 2: default direction comes from the translation of "default:LTR"
    ("https://raw.githubusercontent.com/GNOME/gtk/3.24.33/gtk/gtkmain.c", [r"default:LTR", r"default:RTL", r"gtk_get_locale_direction"], "LGPL-2.1"),
    ("https://raw.githubusercontent.com/GNOME/gtk/2.24.33/gtk/gtkmain.c", [r"default:LTR", r"default:RTL"], "LGPL-2.1"),
    # Pango: auto_dir (paragraph direction from content) is the layout default
    ("https://raw.githubusercontent.com/GNOME/pango/1.50.6/pango/pango-layout.c", [r"auto_dir\s*=", r"pango_layout_set_auto_dir", r"auto-dir"], "LGPL-2.0"),
    # Gecko: UI direction override and the bidi pseudo-locale
    # Gecko: the app UI direction follows the app locale (or the bidi/accented pseudo-locales);
    # no intl.uidirection override remains (a pattern that matches nothing is recorded as such)
    ("https://raw.githubusercontent.com/mozilla/gecko-dev/master/intl/locale/LocaleService.cpp", [r"intl\.uidirection", r"IsAppLocaleRTL\(\) \{", r"EqualsLiteral\(\"bidi\"\)", r"EqualsLiteral\(\"accented\"\)", r"return IsLocaleRTL\(locale\)"], "MPL-2.0"),
    # Unicode Bidirectional Algorithm (UAX #9): isolates FSI/LRI/RLI/PDI
    ("https://www.unicode.org/reports/tr9/", [r"FIRST STRONG ISOLATE", r"POP DIRECTIONAL ISOLATE", r"X5c"], "Unicode terms"),
    # CSS Writing Modes 3: unicode-bidi: plaintext
    ("https://www.w3.org/TR/css-writing-modes-3/", [r"plaintext"], "W3C document licence"),
]


def fetch(url: str) -> tuple[int, bytes, str]:
    out = subprocess.run(
        ["perl", "-e", "alarm shift; exec @ARGV", "90", "curl", "-sS", "-L", "-A", "cotcodec-s2-repair/1", "-w", "\n%{http_code}", url],
        capture_output=True,
    )
    body = out.stdout
    nl = body.rfind(b"\n")
    code = int(body[nl + 1 :].decode() or 0) if nl >= 0 else 0
    return code, body[:nl], out.stderr.decode()[-300:]


def main() -> int:
    snapdir = Path(sys.argv[1])
    snapdir.mkdir(parents=True, exist_ok=True)
    index = []
    for url, pats, lic in SOURCES:
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        code, body, err = fetch(url)
        text = body.decode("utf-8", errors="replace")
        lines = {}
        for i, line in enumerate(text.splitlines(), 1):
            if any(re.search(p, line) for p in pats):
                lines[str(i)] = line.strip()[:240]
                if len(lines) >= 25:
                    break
        rec = {
            "url": url,
            "fetched_at": ts,
            "http_status": code,
            "raw_bytes": len(body),
            "raw_sha256": hashlib.sha256(body).hexdigest(),
            "raw_stored": False,
            "licence": lic,
            "extract": {"patterns": pats, "lines": lines},
            "purpose": "S2 D68 repair: per-application locale and direction switches, text-direction isolation",
        }
        if err.strip():
            rec["curl_stderr_tail"] = err.strip()
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[1])[:150] + ".json"
        (snapdir / name).write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
        index.append({"file": name, "http_status": code, "matched_lines": len(lines)})
        print(code, len(lines), url)
    (snapdir / "_repair-d68-mechanism-index.json").write_text(json.dumps(index, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
