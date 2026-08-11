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


def verify(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"distribution not found: {path}")
    members = _relative_members(path, _members(path))
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
            "iconflow/resources/templates/master.svg",
            "iconflow/resources/presets/flat-geometric.svg",
            "iconflow/resources/docs/DESIGN_PLAYBOOK.md",
        }
        metadata = [name for name in names if name.endswith(".dist-info/METADATA")]
        wheel_records = [name for name in names if name.endswith(".dist-info/RECORD")]
        if len(metadata) != 1 or len(wheel_records) != 1:
            raise ValueError(
                f"wheel must contain exactly one METADATA and RECORD: {path.name}"
            )
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
            "examples/README.md",
            "scripts/setup.ps1",
            "skills/iconflow/SKILL.md",
            "tests/test_cli.py",
        }
    missing = sorted(required - names)
    if missing:
        raise ValueError(f"required members missing from {path.name}: {', '.join(missing)}")
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
