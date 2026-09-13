import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_qt_source_archive_matches_locked_manifest() -> None:
    manifest = yaml.safe_load(
        (ROOT / "sources.yaml").read_text(encoding="utf-8")
    )
    archive = ROOT / "upstream" / Path(manifest["source"]).name

    assert archive.is_file()
    assert _sha256(archive) == manifest["sha256"]


def test_luna_mkspec_has_a_reproducible_source_template() -> None:
    mkspec = ROOT / "mkspecs" / "luna-armv8a"

    assert (mkspec / "qmake.conf").is_file()
    assert (mkspec / "qplatformdefs.h").is_file()
    build_driver = (ROOT / "scripts" / "qt5_build.py").read_text(
        encoding="utf-8"
    )
    assert "def materialize_spec()" in build_driver
    assert "for name in (\"qmake.conf\", \"qplatformdefs.h\")" in build_driver
