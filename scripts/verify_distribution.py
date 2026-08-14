"""Fail closed if a wheel or sdist contains unexpected or unsafe files."""
from __future__ import annotations

import sys
import tarfile
import zipfile
from glob import glob
from pathlib import Path, PurePosixPath

FORBIDDEN_PARTS = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "casebook",
    "mcps",
    "work",
    "__pycache__",
}
FORBIDDEN_NAMES = {".env", ".env.local", "credentials.json", "secrets.json"}
FORBIDDEN_SUFFIXES = {".key", ".p12", ".pfx", ".pem", ".pyc"}
LEGAL_FILES = ("LICENSE", "NOTICE", "TRADEMARKS.md", "THIRD_PARTY_NOTICES.md")
LICENSE_METADATA = {
    "License-Expression: Apache-2.0",
    *(f"License-File: {name}" for name in LEGAL_FILES),
}
SOURCE_ROOT = Path(__file__).resolve().parents[1]
PRESETS = tuple(
    path.stem
    for path in sorted((SOURCE_ROOT / "templates" / "presets").glob("*.svg"))
)
if not PRESETS:
    raise RuntimeError("no source presets found for distribution verification")


def _members(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            return [member.name for member in archive.getmembers() if member.isfile()]
    raise ValueError(f"unsupported distribution: {path}")


def _relative_members(path: Path, members: list[str]) -> list[PurePosixPath]:
    normalized = [PurePosixPath(name.replace("\\", "/")) for name in members]
    for member in normalized:
        if member.is_absolute() or ".." in member.parts:
            raise ValueError(f"unsafe archive member in {path.name}: {member}")
    if path.name.endswith(".tar.gz"):
        roots = {member.parts[0] for member in normalized if member.parts}
        if len(roots) != 1:
            raise ValueError(f"sdist must have one top-level directory: {sorted(roots)}")
        return [PurePosixPath(*member.parts[1:]) for member in normalized]
    return normalized


def _read_member(path: Path, name: str) -> bytes:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return archive.read(name)
    with tarfile.open(path, "r:gz") as archive:
        extracted = archive.extractfile(name)
        if extracted is None:
            raise ValueError(f"archive member is not a regular file: {name}")
        return extracted.read()


def _verify_license_metadata(path: Path, metadata: bytes) -> None:
    try:
        fields = set(metadata.decode("utf-8").splitlines())
    except UnicodeDecodeError as exc:
        raise ValueError(f"package metadata is not UTF-8: {path.name}") from exc
    missing = sorted(LICENSE_METADATA - fields)
    if missing:
        raise ValueError(
            f"missing Apache-2.0 package metadata in {path.name}: "
            + ", ".join(missing)
        )


def verify(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"distribution not found: {path}")
    archive_members = _members(path)
    members = _relative_members(path, archive_members)
    archive_name = {
        str(relative): original for original, relative in zip(archive_members, members)
    }
    unsafe: list[str] = []
    for member in members:
        lower_parts = {part.lower() for part in member.parts}
        if lower_parts & FORBIDDEN_PARTS:
            unsafe.append(str(member))
        elif member.name.lower() in FORBIDDEN_NAMES:
            unsafe.append(str(member))
        elif member.suffix.lower() in FORBIDDEN_SUFFIXES:
            unsafe.append(str(member))
    if unsafe:
        raise ValueError(
            f"unexpected sensitive/generated members in {path.name}: "
            + ", ".join(sorted(unsafe))
        )

    names = {str(member) for member in members}
    common = {"README.md", "pyproject.toml", "iconflow/cli.py", "iconflow/rasterize.py"}
    if path.suffix == ".whl":
        required = {
            "iconflow/__init__.py",
            "iconflow/styles.py",
            "iconflow/resources/templates/master.svg",
            "iconflow/resources/docs/DESIGN_PLAYBOOK.md",
            "iconflow/resources/docs/STYLE_CATALOG.md",
            "iconflow/resources/docs/assets/style-gallery.png",
            *(f"iconflow/resources/presets/{preset}.svg" for preset in PRESETS),
        }
        metadata = [name for name in names if name.endswith(".dist-info/METADATA")]
        wheel_records = [name for name in names if name.endswith(".dist-info/RECORD")]
        if len(metadata) != 1 or len(wheel_records) != 1:
            raise ValueError(
                f"wheel must contain exactly one METADATA and RECORD: {path.name}"
            )
        for legal_file in LEGAL_FILES:
            suffix = f".dist-info/licenses/{legal_file}"
            if not any(name.endswith(suffix) for name in names):
                raise ValueError(
                    f"wheel is missing packaged legal file {legal_file}: {path.name}"
                )
        metadata_name = metadata[0]
    else:
        required = common | {
            "AGENTS.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "THIRD_PARTY_NOTICES.md",
            "brand/iconflow.toml",
            "brand/master-review.json",
            "brand/master.svg",
            "brand/tray.svg",
            "docs/STYLE_CATALOG.md",
            "docs/assets/style-gallery.png",
            "examples/README.md",
            "iconflow/styles.py",
            "scripts/setup.ps1",
            "scripts/setup.sh",
            "skills/iconflow/SKILL.md",
            "tests/test_cli.py",
            *(f"templates/presets/{preset}.svg" for preset in PRESETS),
            *LEGAL_FILES,
        }
        package_metadata = [name for name in names if name == "PKG-INFO"]
        if len(package_metadata) != 1:
            raise ValueError(f"sdist must contain one root PKG-INFO: {path.name}")
        metadata_name = package_metadata[0]
    missing = sorted(required - names)
    if missing:
        raise ValueError(f"required members missing from {path.name}: {', '.join(missing)}")
    if path.name.endswith(".tar.gz"):
        setup_sh = _read_member(path, archive_name["scripts/setup.sh"])
        if b"\r\n" in setup_sh:
            raise ValueError(f"POSIX setup script has CRLF line endings: {path.name}")
    _verify_license_metadata(path, _read_member(path, archive_name[metadata_name]))
    print(f"OK {path.name}: {len(members)} files, required resources present, no forbidden paths")


def main(arguments: list[str]) -> int:
    if not arguments:
        print("usage: verify_distribution.py DIST [DIST ...]", file=sys.stderr)
        return 2
    try:
        expanded = [match for argument in arguments for match in (glob(argument) or [argument])]
        for argument in expanded:
            verify(Path(argument))
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"distribution verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
