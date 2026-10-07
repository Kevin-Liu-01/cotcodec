# Vendored S2 upstream files

Byte-identical copies of the pinned upstream files the S2 substrates are built
from. They are not imported; `s2_catalog.py` reads them as text, checks each
size and SHA-256 against `UPSTREAM_FILES`, applies the recorded
normalisations, and writes the result into a substrate directory together with
the upstream `LICENSE` (and `NOTICE` where one exists).

| Directory | Upstream | Revision | Licence |
|---|---|---|---|
| `FlagGems/` | https://github.com/flagos-ai/FlagGems | tag `v1.0-manual`, `18b8e4281610c91e178518271bc756a98fdc84c9` (2024-04-25) | Apache-2.0, copyright 2024 BAAI (no NOTICE file at the tag) |
| `Liger-Kernel/` | https://github.com/linkedin/Liger-Kernel | tag `v0.3.1`, `1520999e60e34a9e034026d05917082de098be1e` (2024-10-01) | BSD-2-Clause, copyright 2024 LinkedIn Corporation; `utils.py` and `rms_norm.py` state that they incorporate Unsloth code under Apache-2.0 |
| `triton-tutorials/` | https://github.com/triton-lang/triton | `105cb56487cd8a433b8fbfe9cc63c1f1c04a4b2a` (2024-12-09), `python/tutorials/` | MIT, copyright 2018-2020 Philippe Tillet, 2020-2022 OpenAI |

Sizes and SHA-256 of every file are in `../s2_catalog.py` (`UPSTREAM_FILES`)
and are checked by `tests/test_q1_substrates.py`. The files are excluded from
ruff (`ruff.toml`) so they stay identical to upstream.
