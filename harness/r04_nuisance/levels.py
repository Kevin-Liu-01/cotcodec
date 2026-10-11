"""Registered factor levels and cells of r04-checker-nuisance-invariance-v1.

Standard library only; imported by the save stage inside the LibreOffice containers
(Python 3.10) and by the analysis anywhere.

Three nuisance factors, each varied one at a time from the control cell, which is the
checker-mutation study's registered GUI-faithful save (``B0.ctrl_s.L0``: the VM's own
LibreOffice build, Ctrl+S, the VM's en_US desktop):

* build (``B0``-``B5``): the VM's Ubuntu build, then five TDF builds unpacked side by side
  under ``/opt`` in images derived from the LO-VM image (no VM package changes);
* save route (``ctrl_s``, ``store_as``, ``headless_convert``): the registered Ctrl+S save
  under the GUI instance, a Save As in the document's own format through the document
  model (``storeAsURL`` with the filter the document was loaded with), and a headless
  ``--convert-to`` round trip in the same format;
* locale (``L0``-``L4``): the desktop and LibreOffice locale (``LANG``/``LC_ALL`` and the
  profile's ``ooSetupSystemLocale``), with the interface language kept en-US.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

EXPERIMENT_ID = "r04-checker-nuisance-invariance-v1"
PREREG_PATH = "program/preregistrations/r04-checker-nuisance-invariance-v1.md"

# The checker-mutation study's pinned images (q2-evaluator-mutation-v1, section 2).
LO_VM_IMAGE_ID = "sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361"
LO_VM_TAG = "cotcodec-q2-lo-vm:4d5db07d"
METRIC_IMAGE_ID = "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230"

TDF_ARCHIVE = "https://downloadarchive.documentfoundation.org/libreoffice/old"
ROUTES = ("ctrl_s", "store_as", "headless_convert")
CONTROL_CELL = "B0.ctrl_s.L0"
REPLICATE_CELL = "B0.ctrl_s.L0.r2"


@dataclass(frozen=True)
class Build:
    id: str
    label: str
    source: str  # "lo-vm" (the VM's own Ubuntu package) or "tdf"
    version: str
    series: str  # what the profile's ooSetupLastVersion is set to for this build
    soffice: str
    # The UNO client of route store_as: the VM's own Python with Ubuntu's python3-uno for
    # every build, so the client is constant and only the instance it drives (over a URP
    # pipe) changes with the build.
    uno_python: str
    tarball: str | None = None
    tarball_sha256: str | None = None
    tarball_bytes: int | None = None

    @property
    def tarball_url(self) -> str | None:
        if self.tarball is None:
            return None
        return f"{TDF_ARCHIVE}/{self.version}/deb/x86_64/{self.tarball}"

    @property
    def install_dir(self) -> str | None:
        return None if self.source == "lo-vm" else f"/opt/libreoffice{self.series}"


def _tdf(bid: str, version: str, sha256: str, size: int) -> Build:
    series = ".".join(version.split(".")[:2])
    return Build(
        id=bid,
        label=f"tdf-{version}",
        source="tdf",
        version=version,
        series=series,
        soffice=f"/opt/libreoffice{series}/program/soffice",
        uno_python="/usr/bin/python3",
        tarball=f"LibreOffice_{version}_Linux_x86-64_deb.tar.gz",
        tarball_sha256=sha256,
        tarball_bytes=size,
    )


# SHA-256 and sizes as TDF's archive states them (the .mirrorlist page of each tarball,
# read 2026-10-11); the image build checks the SHA-256 of the bytes it fetched.
BUILDS: tuple[Build, ...] = (
    Build(
        id="B0",
        label="ubuntu-1:7.3.7-0ubuntu0.22.04.4",
        source="lo-vm",
        version="7.3.7.2",
        series="7.3",
        soffice="/usr/bin/soffice",
        uno_python="/usr/bin/python3",
    ),
    _tdf(
        "B1",
        "7.3.7.2",
        "2c14b90744a9c2c320cca7863ae027e20ee14b9681e739ff8c2192c3672d9d80",
        194642869,
    ),
    _tdf(
        "B2",
        "7.6.7.2",
        "5fbd379bd9cedb037fa00b6e7e830619bff503a9451bc321e2b4e8d646081920",
        208207432,
    ),
    _tdf(
        "B3",
        "24.8.7.2",
        "c4e40e78d722508fa8f6e42d4e4113889f50a198a5d2c9360b86d5af8b6f7ab9",
        209653445,
    ),
    _tdf(
        "B4",
        "25.8.7.3",
        "7f4d7b2e36921eec5122c655249a24cc88935ee357e8261fd3bccd15aa1f7b9f",
        212886122,
    ),
    _tdf(
        "B5",
        "26.2.6.2",
        "ae25483b9c1b56ed156fb2398c85ce97e65048bc0bbcc079934cc1d2e0c11242",
        217261547,
    ),
)
BUILD_BY_ID = {b.id: b for b in BUILDS}


@dataclass(frozen=True)
class Locale:
    id: str
    posix: str
    bcp47: str
    why: str


LOCALES: tuple[Locale, ...] = (
    Locale("L0", "en_US", "en-US", "the VM's locale (control)"),
    Locale("L1", "de_DE", "de-DE", "decimal comma, '.' grouping, ';' list separator, dd.mm.yyyy"),
    Locale("L2", "ar_EG", "ar-EG", "right-to-left locale, Arabic-Indic digits available"),
    Locale("L3", "ja_JP", "ja-JP", "CJK locale, yyyy/mm/dd, CJK default document language"),
    Locale("L4", "tr_TR", "tr-TR", "dotted and dotless i in case mapping"),
)
LOCALE_BY_ID = {loc.id: loc for loc in LOCALES}


@dataclass(frozen=True)
class Cell:
    id: str
    build: str
    route: str
    locale: str
    replicate: int
    arm: str  # control, replicate, route, build, locale, build_route
    role: str  # control, validity, primary, secondary

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def cell_id(build: str, route: str, locale: str, replicate: int = 1) -> str:
    base = f"{build}.{route}.{locale}"
    return base if replicate == 1 else f"{base}.r{replicate}"


def registered_cells() -> tuple[Cell, ...]:
    """Every registered cell, in the registered run order (primary before secondary)."""
    cells = [
        Cell(CONTROL_CELL, "B0", "ctrl_s", "L0", 1, "control", "control"),
        Cell(REPLICATE_CELL, "B0", "ctrl_s", "L0", 2, "replicate", "validity"),
    ]
    for route in ("store_as", "headless_convert"):
        cells.append(Cell(cell_id("B0", route, "L0"), "B0", route, "L0", 1, "route", "primary"))
    for build in BUILDS[1:]:
        cells.append(
            Cell(cell_id(build.id, "ctrl_s", "L0"), build.id, "ctrl_s", "L0", 1, "build", "primary")
        )
    for loc in LOCALES[1:]:
        cells.append(
            Cell(cell_id("B0", "ctrl_s", loc.id), "B0", "ctrl_s", loc.id, 1, "locale", "primary")
        )
    for build in BUILDS[1:]:
        for route in ("store_as", "headless_convert"):
            cells.append(
                Cell(
                    cell_id(build.id, route, "L0"),
                    build.id,
                    route,
                    "L0",
                    1,
                    "build_route",
                    "secondary",
                )
            )
    return tuple(cells)


CELL_BY_ID = {c.id: c for c in registered_cells()}
PRIMARY_ARMS = ("route", "build", "locale")


def get_cell(cid: str) -> Cell:
    if cid not in CELL_BY_ID:
        raise KeyError(f"unregistered cell {cid!r}")
    return CELL_BY_ID[cid]


def profile_overrides(cell: Cell) -> list[tuple[str, str, str]]:
    """(node path, property, value) set in the copied VM profile for this cell.

    The control cell sets nothing: it is the registered save with the VM's profile
    unchanged. A build other than the VM's gets its own ``ooSetupLastVersion`` (so it does
    not open first-start or what's-new UI over the document); a locale cell sets the
    LibreOffice locale and pins the interface language to en-US.
    """
    out: list[tuple[str, str, str]] = []
    build = BUILD_BY_ID[cell.build]
    if build.series != "7.3":
        out.append(("/org.openoffice.Setup/Product", "ooSetupLastVersion", build.series))
    if cell.locale != "L0":
        loc = LOCALE_BY_ID[cell.locale]
        out.append(("/org.openoffice.Setup/L10N", "ooSetupSystemLocale", loc.bcp47))
        out.append(("/org.openoffice.Setup/L10N", "ooLocale", "en-US"))
    return out


def env_overrides(cell: Cell, locpath: str | None) -> dict[str, str]:
    """Environment of the LibreOffice and pyautogui processes for this cell (beyond the
    save stage's own: ``LANG``/``LC_ALL`` en_US.UTF-8 and the gtk3 VCL plugin)."""
    if cell.locale == "L0":
        return {}
    loc = LOCALE_BY_ID[cell.locale]
    env = {"LANG": f"{loc.posix}.UTF-8", "LC_ALL": f"{loc.posix}.UTF-8"}
    if locpath:
        env["LOCPATH"] = locpath
    return env


def cells_for_build(build: str, cells: tuple[Cell, ...] | None = None) -> list[Cell]:
    return [c for c in (cells or registered_cells()) if c.build == build]


def describe() -> dict[str, object]:
    """The registered design as data (pins block, tests, the run record)."""
    return {
        "experiment_id": EXPERIMENT_ID,
        "control_cell": CONTROL_CELL,
        "replicate_cell": REPLICATE_CELL,
        "builds": [
            {**asdict(b), "tarball_url": b.tarball_url, "install_dir": b.install_dir}
            for b in BUILDS
        ],
        "locales": [asdict(loc) for loc in LOCALES],
        "routes": list(ROUTES),
        "cells": [c.as_dict() for c in registered_cells()],
    }
