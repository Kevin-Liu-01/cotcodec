"""Render one Dockerfile per TDF build of R04 from ``Dockerfile.in`` and ``levels.BUILDS``.

``python infra/r04-nuisance/render_dockerfiles.py`` writes ``lo-tdf/<build>/Dockerfile``;
``--check`` exits 1 if any committed file differs from its rendering (a test runs it).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from harness.r04_nuisance import levels  # noqa: E402

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "lo-tdf" / "Dockerfile.in"


def render(build: levels.Build) -> str:
    return TEMPLATE.read_text(encoding="utf-8").format(
        bid=build.id,
        version=build.version,
        series=build.series,
        url=build.tarball_url,
        size=build.tarball_bytes,
        sha256=build.tarball_sha256,
        install_dir=build.install_dir,
        soffice=build.soffice,
        base_tag=levels.LO_VM_TAG,
        base_id_short=levels.LO_VM_IMAGE_ID[:19],
    )


def targets() -> dict[Path, str]:
    return {
        HERE / "lo-tdf" / b.id / "Dockerfile": render(b) for b in levels.BUILDS if b.source == "tdf"
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    stale = []
    for path, text in targets().items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if stale:
        print("stale: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
