"""S2 v4 registration: the committed K0 section, its code's constants and freeze hygiene."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from harness.s2_locale import k0_v4 as K

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "program/preregistrations/s2-arabic-cua-locale-v4.md"
# The SHA-256 of the K0 section's text as committed before any Phase 0 result existed. A change
# here before the freeze must be a visible, recorded decision; after any Phase 0 result has been
# read it voids the commitment (registration, section "K0").
K0_SECTION_SHA256 = "ed38b953c7934169fcede7b45ec5dc1b568afd5855c6008830aada68cf131a03"


def _k0_text() -> str:
    m = re.search(r"<!-- K0:BEGIN -->\n(.*?)<!-- K0:END -->", REG.read_text(encoding="utf-8"), re.S)
    assert m, "the K0 markers are missing"
    return m.group(1)


def test_k0_section_is_the_committed_text():
    assert hashlib.sha256(_k0_text().encode()).hexdigest() == K0_SECTION_SHA256


def test_k0_code_constants_match_the_text():
    text = _k0_text()
    assert f"at least {K.K_MIN} tasks are admitted" in text
    assert "at least 95%" in text and K.SHARE == 0.95
    assert "at least 90%" in text and K.DESCRIPTOR_SHARE == 0.90
    assert f"max({K.TOL_FLOOR_PX}\npx" in text or f"max({K.TOL_FLOOR_PX} px" in text
    assert f"rows 0-{K.SHELL_ROWS - 1}" in text
    for task in K.PD_VISIBLE_DEV:
        assert f"`{task}`" in text
    for task in K.C1_TASKS:
        assert f"`{task}`" in text
    assert ", ".join(K.ADMISSION_CELLS[:-1]) + ", " + K.ADMISSION_CELLS[-1] in text


def test_freezable_and_names_itself():
    text = REG.read_text(encoding="utf-8")
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", text), "freeze refuses placeholders"
    assert ("preregister.py freeze s2-arabic-cua-locale-v4 "
            "program/preregistrations/s2-arabic-cua-locale-v4.md") in text
    assert text.startswith("# S2 v4:") and "Status: DRAFT" in text
