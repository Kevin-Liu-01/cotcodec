"""Author tool that writes ``keysyms.json`` from X.Org's ``keysymdef.h``.

The IR accepts every keysym name that X11 itself defines, so it is never
narrower than the paper's "key or chord" action (review finding: a closed
table of about 80 names would make Stage-1 key actions such as ``plus`` or
``KP_0`` fail at the IR boundary). The table is generated from xorgproto
2024.1 ``include/X11/keysymdef.h`` (MIT/X11 licence, notice reproduced in the
JSON) and committed; its source digest is recorded there.

Run on a machine that has the header::

    python -m harness.q2.action_path.build_keysyms PATH/TO/keysymdef.h \
        > harness/q2/action_path/keysyms.json

The header's SHA-256 must equal ``EXPECTED_SHA256``; a different revision is a
deliberate change to this file, never a silent one.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_SHA256 = "4ba0724695c817a08b4ea3a79c5e8a52e0798cc8d5906281b10f89dc6225208d"
SOURCE = {
    "name": "xorgproto",
    "version": "2024.1",
    "file": "include/X11/keysymdef.h",
    "url": "https://gitlab.freedesktop.org/xorg/proto/xorgproto/-/blob/"
    "xorgproto-2024.1/include/X11/keysymdef.h",
    "obtained_from": "conda package xorg-xorgproto 2024.1 (build h5eee18b_1) on the H100 host",
    "size_bytes": 186634,
    "sha256": EXPECTED_SHA256,
    "license": "MIT (X11 style), see notice",
}
NOTICE = (
    "Copyright 1987, 1994, 1998 The Open Group. Permission to use, copy, modify, "
    "distribute, and sell this software and its documentation for any purpose is "
    "hereby granted without fee, provided that the above copyright notice appear in "
    "all copies and that both that copyright notice and this permission notice appear "
    "in supporting documentation. The above copyright notice and this permission "
    "notice shall be included in all copies or substantial portions of the Software. "
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR '
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS "
    "FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE OPEN GROUP BE "
    "LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF "
    "CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE "
    "SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. Except as contained in "
    "this notice, the name of The Open Group shall not be used in advertising or "
    "otherwise to promote the sale, use or other dealings in this Software without "
    "prior written authorization from The Open Group. "
    "Copyright 1987 by Digital Equipment Corporation, Maynard, Massachusetts. All "
    "Rights Reserved. Permission to use, copy, modify, and distribute this software "
    "and its documentation for any purpose and without fee is hereby granted, provided "
    "that the above copyright notice appear in all copies and that both that copyright "
    "notice and this permission notice appear in supporting documentation, and that "
    "the name of Digital not be used in advertising or publicity pertaining to "
    "distribution of the software without specific, written prior permission. DIGITAL "
    "DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL IMPLIED "
    "WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL DIGITAL BE LIABLE FOR "
    "ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING "
    "FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR "
    "OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE "
    "OF THIS SOFTWARE."
)
DEFINE_RE = re.compile(r"^#define XK_([A-Za-z0-9_]+)\s+0x([0-9a-fA-F]+)\b")
# A name the IR never accepts: pressing "no symbol" is not an action.
EXCLUDED = ("VoidSymbol",)


def parse(text: str) -> list[list[object]]:
    """Every ``#define XK_name 0xVALUE`` in file order, as [name, value]."""
    out: list[list[object]] = []
    for line in text.splitlines():
        match = DEFINE_RE.match(line)
        if match and match.group(1) not in EXCLUDED:
            out.append([match.group(1), int(match.group(2), 16)])
    return out


def render(header: bytes) -> str:
    digest = hashlib.sha256(header).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"keysymdef.h SHA-256 {digest} is not the pinned {EXPECTED_SHA256}")
    table = parse(header.decode("utf-8"))
    head = {
        "schema": "cotcodec-q2-keysyms-v1",
        "source": SOURCE,
        "notice": NOTICE,
        "canonical_rule": "the first name defined for a value, in file order",
    }
    lines = ["{"]
    for key, value in head.items():
        lines.append(f" {json.dumps(key)}: {json.dumps(value, sort_keys=True)},")
    lines.append(' "keysyms": [')
    rows = [f"  {json.dumps(row)}" for row in table]
    lines.append(",\n".join(rows))
    lines.append(" ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.write(render(Path(sys.argv[1]).read_bytes()))
