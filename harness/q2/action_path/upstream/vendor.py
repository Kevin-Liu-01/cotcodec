"""Write the vendored upstream parser extracts from pinned upstream files (author tool).

The suite runs four upstream response parsers unmodified (preregistration
section 3): OSWorld ``bfd62bdc`` (H-OSW-up, and the base of H-OSW-fixed),
gym-anything ``aae6f7607`` (H-GA) and gym-anything ``bf965cde0`` (H-GA-buggy).
Their modules import model clients, PIL and agent base classes that the GPU-less
runner image does not have, so only the parsing code is vendored: exact line
ranges of the upstream files, copied byte for byte, placed in a minimal module
whose header states the licence, the source and the change (extraction).

``BLOCKS`` fixes every range. ``PROVENANCE.json`` records each upstream file's
SHA-256 and each block's SHA-256; ``tests/test_q2_upstream_vendor.py`` checks
that every block appears verbatim in its module and hashes to the recorded
digest. To re-create the modules from the upstream files:

    python -m harness.q2.action_path.upstream.vendor --upstream-dir DIR

where ``DIR`` holds the files named in ``SOURCES`` (``git show REV:PATH``).
The file digests must match ``harness/q2/README.md``'s source table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

SOURCES = {
    "osworld_agent": {
        "repo": "https://github.com/xlang-ai/OSWorld",
        "rev": "bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06",
        "path": "mm_agents/qwen35vl_agent.py",
        "file": "osw_qwen35vl_agent_bfd62bdc.py",
        "sha256": "1f39be92cf5461d9671ab9307a69c05691abf0226aa6b53d2af332003a5096fe",
        "license": "Apache-2.0",
    },
    "ga_aae6": {
        "repo": "https://github.com/cmu-l3/gym-anything",
        "rev": "aae6f7607e0f3d9d6306e1fefbad92bda99ca99a",
        "path": "agents/agents/qwen35vl.py",
        "file": "ga_qwen35vl_aae6.py",
        "sha256": "93666f2751d99dfee0034700f65385ca2db1544e3d9a0d194807050d2edea1a5",
        "license": "MIT",
    },
    "ga_bf96": {
        "repo": "https://github.com/cmu-l3/gym-anything",
        "rev": "bf965cde02f498bf7d162e6e44da984cff289912",
        "path": "agents/agents/qwen35vl.py",
        "file": "ga_qwen35vl_bf96.py",
        "sha256": "824ef657345f317bf197b7f6470d82ddbf1779bd556a9a29cd184c5641fa43d8",
        "license": "MIT",
    },
    "ga_bf96_shared": {
        "repo": "https://github.com/cmu-l3/gym-anything",
        "rev": "bf965cde02f498bf7d162e6e44da984cff289912",
        "path": "agents/shared/qwen_computer_use.py",
        "file": "ga_qwen_cu_bf96.py",
        "sha256": "b74793ea329407d0d27fb536c3db0502f5f0dfeb34f279691ca5f836f0c7b815",
        "license": "MIT",
    },
}

APACHE_NOTICE = """\
# Copyright the OSWorld authors (xlang-ai/OSWorld). Licensed under the Apache
# License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law
# or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
"""

MIT_NOTICE = """\
# MIT License
#
# Copyright (c) 2026 cmu-l3
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""

# Each module: a header, then parts in order. A part is literal glue text or a
# block ("source", first_line, last_line), 1-based and inclusive.
MODULES = {
    "osworld_bfd62bdc.py": {
        "notice": APACHE_NOTICE,
        "parts": [
            "import json\nimport re\nfrom typing import Dict, List, Optional, Tuple\n\n\n"
            "class Qwen35VLAgent:\n"
            '    """Stand-in for the upstream class: only what parse_response uses."""\n\n'
            '    def __init__(self, coordinate_type: str = "relative"):\n'
            "        self.coordinate_type = coordinate_type\n\n",
            ("osworld_agent", 104, 106),
            "\n",
            ("osworld_agent", 373, 563),
        ],
    },
    "gym_anything_aae6f7607.py": {
        "notice": MIT_NOTICE,
        "parts": [
            "import json\nimport re\nfrom typing import Any, Dict, List, Optional, Tuple\n\n",
            ("ga_aae6", 14, 23),
            "\n\nclass Qwen35VLAgent:\n"
            '    """Stand-in for the upstream class: only its response parsing."""\n\n',
            ("ga_aae6", 465, 731),
        ],
    },
    "gym_anything_bf965cde0.py": {
        "notice": MIT_NOTICE,
        "parts": [
            "import json\nimport re\nfrom typing import Any, Dict, List, Optional, Tuple\n\n\n",
            ("ga_bf96_shared", 25, 218),
            "\n\nclass Qwen35VLAgent:\n"
            '    """Stand-in for the upstream class: only its response parsing."""\n\n',
            ("ga_bf96", 28, 39),
            "\n",
            ("ga_bf96", 246, 398),
            "\n\n",
            ("ga_bf96", 401, 414),
        ],
    },
}


def _header(name: str, spec: dict) -> str:
    lines = [
        spec["notice"],
        "#",
        "# Vendored by cotcodec (harness/q2/action_path/upstream/vendor.py).",
        "# CHANGED: this file is an extract. The line ranges below were copied byte for",
        "# byte from the upstream files; the enclosing class is replaced by a minimal",
        "# stand-in and the imports are reduced to those the extract uses. Nothing in",
        "# the copied ranges was modified.",
    ]
    for part in spec["parts"]:
        if isinstance(part, tuple):
            source = SOURCES[part[0]]
            lines.append(
                f"#   {source['repo']} @ {source['rev'][:12]} {source['path']} "
                f"lines {part[1]}-{part[2]}"
            )
    return "\n".join(lines) + "\n\n"


def block_text(texts: dict[str, list[str]], part: tuple[str, int, int]) -> str:
    source, first, last = part
    return "".join(texts[source][first - 1 : last])


def render(texts: dict[str, list[str]]) -> tuple[dict[str, str], dict]:
    modules: dict[str, str] = {}
    provenance: dict = {"sources": {}, "modules": {}}
    for key, source in SOURCES.items():
        provenance["sources"][key] = {k: v for k, v in source.items() if k != "file"}
    for name, spec in MODULES.items():
        out = [_header(name, spec)]
        blocks = []
        for part in spec["parts"]:
            if isinstance(part, tuple):
                text = block_text(texts, part)
                out.append(text)
                blocks.append(
                    {
                        "source": part[0],
                        "lines": [part[1], part[2]],
                        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    }
                )
            else:
                out.append(part)
        modules[name] = "".join(out)
        provenance["modules"][name] = {"blocks": blocks}
    return modules, provenance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--upstream-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    texts = {}
    for key, source in SOURCES.items():
        data = (args.upstream_dir / source["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise SystemExit(f"{source['file']} does not match its pinned SHA-256")
        texts[key] = data.decode("utf-8").splitlines(keepends=True)
    modules, provenance = render(texts)
    for name, text in modules.items():
        (HERE / name).write_text(text, encoding="utf-8")
    (HERE / "PROVENANCE.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
