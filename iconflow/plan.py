# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The render plan: every byte a build will ship, computed once.

Before 0.8, ``ship`` audited in one Chromium session and ``build`` rendered
everything again in another, writing each file as it went. Nothing checked
that the pixels a person reviewed were the pixels that shipped, and a target
that failed late (an emote over its upload limit, an Android themed layer that
could not be derived) left a half-written output tree behind.

A :class:`RenderPlan` is the whole output — every PNG, container, manifest and
snippet — held in memory, immutable, with the source snapshots and parameters
that produced it. ``build`` computes one and writes it only once it is
complete. Review records the plan's identity in its receipt, and ``ship``
compares the plan it is about to write against that identity, so "the
reviewed pixels are the shipped pixels" is checked, not assumed. The design,
and what it does not promise, is ``docs/RENDER_PLAN.md``.

Two identities, deliberately different:

* :attr:`RenderPlan.digest` (content) — a PNG contributes the SHA-256 of its
  decoded RGBA pixels and size; an ICO or ICNS the pixels of every frame, in
  order, with its slot; any other file its bytes (text with CRLF read as LF).
  A lossless re-encode of a PNG or a platform's newlines are not drift; a
  changed pixel always is. It is a *hybrid* fingerprint: ``trayIcon.ts``
  embeds PNG bytes, so it is byte-sensitive.
* :attr:`RenderPlan.artifact_digest` (exact bytes) — every file's SHA-256.
  This is what ``ship --plan`` replays: the reviewed bytes, byte for byte.
"""
from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import os
import platform
import re
import shutil
import struct
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping

from PIL import Image

from . import assemble, htmlhead
from .rasterize import svg_text_from_bytes

#: Version of the manifest and of a receipt's ``plan`` binding.
PLAN_SCHEMA = 1
#: The manifest's file name inside a plan directory; payloads live under FILES_DIR.
MANIFEST_NAME = "plan.json"
FILES_DIR = "files"
#: Import bounds: a plan is a handful of icons, never a disk image.
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_PLAN_BYTES = 256 * 1024 * 1024
MAX_PLAN_FILES = 512
MAX_PLAN_DEPTH = 8
MAX_PIXELS = 8192 * 8192
#: Gate codes (exit 1): rendered pixels differ from the approved ones, or a
#: saved plan cannot be published as the reviewed output.
GATE_PLAN_DRIFT = "plan-drift"
GATE_PLAN_REPLAY = "plan-replay"


class PlanError(ValueError):
    """A plan that cannot honestly stand for reviewed output."""


def toolchain() -> dict[str, str | None]:
    """What rendered the pixels. Provenance only: it explains drift, never excuses it."""
    import importlib.metadata

    from . import __version__

    try:
        iconflow_version = importlib.metadata.version("iconflow")
    except importlib.metadata.PackageNotFoundError:
        iconflow_version = __version__
    try:
        import PIL
        pillow_version = getattr(PIL, "__version__", None)
    except ImportError:
        pillow_version = None
    chromium_version = None
    try:
        import playwright
        catalog = Path(playwright.__file__).resolve().parent / "driver" / "package" / "browsers.json"
        for browser in json.loads(catalog.read_text(encoding="utf-8")).get("browsers", []):
            if browser.get("name") == "chromium":
                chromium_version = browser.get("browserVersion") or None
                break
    except (ImportError, OSError, ValueError, AttributeError):
        chromium_version = None
    return {
        "iconflow": iconflow_version,
        "chromium": chromium_version,
        "pillow": pillow_version,
        "platform": platform.system() or None,
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ----------------------------------------------------------------- identities

def _pixels_sha256(png: bytes) -> str:
    """Domain-separated digest of a PNG's decoded RGBA8 samples, row-major."""
    try:
        with Image.open(io.BytesIO(png)) as image:
            if image.format != "PNG":
                raise PlanError("a .png output is not a PNG")
            if getattr(image, "is_animated", False):
                raise PlanError("an animated PNG cannot stand for one icon")
            if image.width * image.height > MAX_PIXELS:
                raise PlanError("a PNG output is too large to be an icon")
            image.load()
            rgba = image.convert("RGBA")
    except PlanError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise PlanError(f"an image output cannot be decoded: {exc}") from exc
    header = b"iconflow-pixels-v1\0" + rgba.width.to_bytes(4, "big") + rgba.height.to_bytes(4, "big")
    return _sha256(header + rgba.tobytes())


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_TEXT_SUFFIXES = frozenset({".svg", ".html", ".webmanifest", ".xml", ".ts", ".json"})


def content_sha256(path: str, data: bytes) -> str:
    """The content identity of one output (see the module docstring).

    A container contributes every entry in slot order — its directory fields
    or chunk type, and the decoded pixels of its payload — so a repeated, an
    extra, a reordered or a re-described frame is a different container.
    """
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".png":
        return _pixels_sha256(data)
    if suffix in {".ico", ".icns"}:
        try:
            if suffix == ".ico":
                entries = [(",".join(map(str, fields[:6])), payload)
                           for fields, payload in assemble.ico_entries(data)]
            else:
                entries = [(ostype.hex(), payload) for ostype, payload in assemble.icns_entries(data)]
        except (ValueError, IndexError, struct.error) as exc:
            raise PlanError(f"{path}: unreadable container ({exc})") from exc
        # A PNG payload by its pixels; anything else (a BMP frame, a TOC or
        # unknown chunk) by its bytes, so it still counts.
        listing = "".join(
            f"{slot}:{described}:"
            f"{_pixels_sha256(payload) if payload[:8] == _PNG_SIGNATURE else _sha256(payload)}\n"
            for slot, (described, payload) in enumerate(entries))
        return _sha256(f"iconflow-{suffix[1:]}-v1\n{listing}".encode("ascii"))
    if suffix in _TEXT_SUFFIXES:
        return _sha256(data.replace(b"\r\n", b"\n"))
    return _sha256(data)


def _listing_digest(kind: str, entries: Mapping[str, str]) -> str:
    listing = "".join(f"{path}\t{entries[path]}\n" for path in sorted(entries))
    return _sha256(f"iconflow-plan-{kind}-v1\n{listing}".encode("utf-8"))


def provenance_digest(inputs: Mapping, parameters: Mapping) -> str:
    """What produced the plan: each source role's hash and every effective setting.

    Source *paths* are left out — they are machine-local — so the same
    sources and settings give the same provenance on every machine.
    """
    canonical = {
        "inputs": {role: _thaw(record).get("sha256") for role, record in inputs.items()},
        "parameters": _thaw(parameters),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256(b"iconflow-plan-provenance-v1\n" + encoded.encode("utf-8"))


# ------------------------------------------------------------------- records

@dataclass(frozen=True)
class Source:
    """One source file, read once. Rendering, hashing and copying all use these bytes."""

    role: str
    path: str
    raw: bytes = field(repr=False)
    text: str = field(repr=False)

    @property
    def sha256(self) -> str:
        """The normalised-text hash receipts bind (``config.svg_sha256``)."""
        normalised = self.text.replace("\r\n", "\n").replace("\r", "\n")
        return _sha256(normalised.encode("utf-8"))


def snapshot(path: str | Path, role: str) -> Source:
    raw = Path(path).read_bytes()
    return Source(role=role, path=str(path), raw=raw, text=svg_text_from_bytes(raw, path))


@dataclass(frozen=True)
class PlanFile:
    path: str
    data: bytes = field(repr=False)
    sha256: str
    content_sha256: str

    @classmethod
    def of(cls, path: str, data: bytes) -> "PlanFile":
        _relative(path)
        data = bytes(data)
        return cls(path=path, data=data, sha256=_sha256(data), content_sha256=content_sha256(path, data))


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


#: Plan files that hold the master's own renders, untransformed, and how to
#: read sizes out of them (R01: approval surfaces show these, not new renders).
_MASTER_FRAME_FILES = ("favicon.ico", "icons/icon.ico", "icons/icon.icns")
_MASTER_PNG = re.compile(r"^(?:icon-(\d+)\.png|icons/(\d+)x\2\.png|emote/(\d+)\.png)$")


@dataclass(frozen=True)
class RenderPlan:
    """Every output of one build, immutable, with what produced it."""

    files: tuple[PlanFile, ...]
    inputs: Mapping[str, Mapping[str, str]]
    parameters: Mapping[str, object]
    toolchain: Mapping[str, object]

    @classmethod
    def create(cls, files: Mapping[str, bytes], *, inputs, parameters, toolchain) -> "RenderPlan":
        records = tuple(PlanFile.of(path, data) for path, data in files.items())
        folded = [record.path.casefold() for record in records]
        if len(set(folded)) != len(folded):
            raise PlanError("a plan names the same output path twice")
        return cls(files=records, inputs=_freeze(inputs), parameters=_freeze(parameters),
                   toolchain=_freeze(toolchain))

    @property
    def produced(self) -> list[str]:
        """Relative paths in the order the build produces them (``build()``'s return)."""
        return [record.path for record in self.files]

    def file(self, path: str) -> bytes:
        for record in self.files:
            if record.path == path:
                return record.data
        raise KeyError(path)

    def get(self, path: str) -> bytes | None:
        try:
            return self.file(path)
        except KeyError:
            return None

    def master_frames(self) -> dict[int, bytes]:
        """The master's own renders this plan ships, by pixel size.

        Taken from the untransformed outputs (favicon and Tauri containers,
        ``icon-N.png``, Tauri and emote PNGs), so a review surface that shows
        "the icon at 32px" can show the exact frame that ships.
        """
        frames: dict[int, bytes] = {}
        for record in self.files:
            match = _MASTER_PNG.match(record.path)
            if match:
                size = int(next(group for group in match.groups() if group))
                frames.setdefault(size, record.data)
            elif record.path in _MASTER_FRAME_FILES:
                read = assemble.ico_frames if record.path.endswith(".ico") else assemble.icns_frames
                for size, payload in read(record.data).items():
                    frames.setdefault(size, payload)
        return frames

    @property
    def digest(self) -> str:
        return _listing_digest("content", {r.path: r.content_sha256 for r in self.files})

    @property
    def artifact_digest(self) -> str:
        return _listing_digest("bytes", {r.path: f"{len(r.data)}:{r.sha256}" for r in self.files})

    @property
    def provenance_digest(self) -> str:
        return provenance_digest(self.inputs, self.parameters)

    def binding(self) -> dict:
        """What a review receipt records about the pixels it approved."""
        return {
            "schema": PLAN_SCHEMA,
            "digest": self.digest,
            "artifact_digest": self.artifact_digest,
            "provenance_digest": self.provenance_digest,
            "files": {r.path: {"content": r.content_sha256, "sha256": r.sha256} for r in self.files},
            "toolchain": _thaw(self.toolchain),
        }

    def manifest(self) -> dict:
        return {
            "schema": PLAN_SCHEMA,
            "digest": self.digest,
            "artifact_digest": self.artifact_digest,
            "provenance_digest": self.provenance_digest,
            "inputs": _thaw(self.inputs),
            "parameters": _thaw(self.parameters),
            "toolchain": _thaw(self.toolchain),
            "files": [
                {"path": r.path, "bytes": len(r.data), "sha256": r.sha256,
                 "content_sha256": r.content_sha256}
                for r in self.files
            ],
        }


# ------------------------------------------------------------------ planning

def plan_parameters(targets, *, name, theme_color, bg_color, electron_radius, tray_ts,
                    color_scheme, web_options, optimize_png, tray_template_mode,
                    maskable_scale, maskable_svg) -> dict:
    """The effective output parameters a plan records (and ``ship --plan`` re-derives)."""
    from .build import ADAPTIVE_TARGETS, resolve_maskable_scale

    options = web_options or htmlhead.WebMetaOptions()
    adaptive = bool(ADAPTIVE_TARGETS & set(targets))
    return {
        "targets": list(targets),
        "name": name,
        "theme_color": theme_color,
        "background_color": bg_color,
        "electron_radius": electron_radius,
        "tray_ts": bool(tray_ts),
        "color_scheme": color_scheme,
        "optimize_png": bool(optimize_png),
        "tray_template_mode": tray_template_mode,
        "maskable_scale": (
            resolve_maskable_scale(maskable_scale, linked=maskable_svg is not None)
            if adaptive else None
        ),
        "web_options": dataclasses.asdict(options),
    }


def consumed_roles(targets, *, tray_svg, maskable_svg, monochrome_svg) -> set[str]:
    """The source roles a build with these targets reads (the master always)."""
    from .build import ADAPTIVE_TARGETS

    targets = set(targets)
    roles = {"master"}
    if tray_svg is not None and ("tray" in targets or ("android" in targets and monochrome_svg is None)):
        roles.add("tray")
    if maskable_svg is not None and ADAPTIVE_TARGETS & targets:
        roles.add("maskable")
    if monochrome_svg is not None and "android" in targets:
        roles.add("monochrome")
    return roles


def _file_identity(path) -> object:
    """The same key for every path to one file (device and inode where the OS has them)."""
    try:
        status = os.stat(path)
    except OSError:
        return os.path.normcase(os.path.realpath(path))
    if status.st_ino:
        return (status.st_dev, status.st_ino)
    return os.path.normcase(os.path.realpath(path))


def compute_plan(master_svg: str | Path, targets=("web",), *,
                 name: str = "App", theme_color: str = "#0b0d12",
                 bg_color: str = "#ffffff", electron_radius: float = 0.0,
                 tray_ts: bool = False, color_scheme: str = "light",
                 web_options: htmlhead.WebMetaOptions | None = None,
                 optimize_png: bool = True, tray_svg: str | Path | None = None,
                 tray_template_mode: str = "auto",
                 maskable_scale: float | None = None,
                 maskable_svg: str | Path | None = None,
                 monochrome_svg: str | Path | None = None,
                 rasterizer=None) -> RenderPlan:
    """Render every output of a build into memory. No publication writes.

    Takes exactly :func:`iconflow.build.build`'s arguments (less ``outdir``),
    validates them the same way, and returns a plan whose files are the bytes
    ``build`` writes, in its order. Each source *file* is read once, whatever
    roles it plays; its snapshot is rendered, hashed and (for an unannotated
    favicon) copied, so an edit made mid-build cannot mix two versions.
    Optional sources a selected target does not consume are not read.
    """
    import importlib

    # ``iconflow.build`` the module: the package re-exports a function by that name.
    b = importlib.import_module(".build", __package__)

    targets = b.normalize_targets(targets)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    assemble.opaque_color(theme_color, "theme color")
    assemble.opaque_color(bg_color, "background color")
    electron_radius = assemble.validate_radius(electron_radius)
    if tray_template_mode not in {"auto", "alpha", "contrast"}:
        raise ValueError("tray_template_mode must be 'auto', 'alpha', or 'contrast'")
    if web_options and web_options.tile_color:
        assemble.opaque_color(web_options.tile_color, "tile color")
    if maskable_scale is not None:
        maskable_scale = b.validate_maskable_scale(maskable_scale)
    master_path = Path(master_svg)
    roles = consumed_roles(targets, tray_svg=tray_svg, maskable_svg=maskable_svg,
                           monochrome_svg=monochrome_svg)
    by_file: dict[str, Source] = {}
    sources: dict[str, Source] = {}

    def take(path, role) -> Source:
        # One snapshot per file, shared by every role that names it — by file
        # identity, so a symlink or a hard link to the same file is the same
        # snapshot (a link that names the master is still a link: the default
        # maskable scale depends on it, but the bytes are the master's).
        key = _file_identity(path)
        if key not in by_file:
            by_file[key] = snapshot(path, role)
        sources[role] = by_file[key]
        return by_file[key]

    master = take(master_path, "master")
    tray = take(tray_svg, "tray") if "tray" in roles else None
    maskable = take(maskable_svg, "maskable") if "maskable" in roles else None
    monochrome = take(monochrome_svg, "monochrome") if "monochrome" in roles else None

    def render(r) -> dict[str, bytes]:
        caches: dict[int, object] = {}

        def cache_for(source: Source | None):
            if source is None:
                return None
            if id(source) not in caches:
                caches[id(source)] = b.RenderCache(source.text, r, optimize=optimize_png)
            return caches[id(source)]

        cache = cache_for(master)
        files: dict[str, bytes] = {}
        maskable_cache = cache_for(maskable)
        if "web" in targets or "pwa" in targets:
            files.update(b.web_files(
                cache, master.raw, name, theme_color, bg_color, web_options,
                maskable_scale=maskable_scale, maskable_cache=maskable_cache,
            ))
        if "tauri" in targets:
            files.update(b.tauri_files(cache))
        if "electron" in targets:
            files.update(b.electron_files(cache, electron_radius))
        if "tray" in targets:
            files.update(b.tray_files(
                cache, tray_ts, tray_cache=cache_for(tray), template_mode=tray_template_mode,
            ))
        if "android" in targets:
            files.update(b.android_assets(
                cache, bg_color, maskable_scale=maskable_scale, maskable_cache=maskable_cache,
                monochrome_cache=cache_for(monochrome if monochrome is not None else tray),
                template_mode=tray_template_mode,
            ))
        if "emote" in targets:
            files.update(b.emote_files(cache))
        return files

    if rasterizer is not None:
        files = render(rasterizer)
    else:
        # Through ``iconflow.build`` so substituting its renderer (as tests and
        # callers have since 0.5) substitutes the plan's.
        with b.Rasterizer(color_scheme=color_scheme) as owned:
            files = render(owned)
    return RenderPlan.create(
        files,
        inputs={role: {"path": s.path, "sha256": s.sha256, "bytes_sha256": _sha256(s.raw)}
                for role, s in sources.items()},
        parameters=plan_parameters(
            targets, name=name, theme_color=theme_color, bg_color=bg_color,
            electron_radius=electron_radius, tray_ts=tray_ts, color_scheme=color_scheme,
            web_options=web_options, optimize_png=optimize_png,
            tray_template_mode=tray_template_mode, maskable_scale=maskable_scale,
            maskable_svg=maskable_svg,
        ),
        toolchain=toolchain(),
    )


# --------------------------------------------------------------- publication

# Portable relative paths only: no drive, no ADS, no control characters, no
# Windows-reserved names, nothing another filesystem would read as another path.
_SEGMENT = re.compile(r"[A-Za-z0-9_@+\-][A-Za-z0-9_@+.\-]*")
_RESERVED = frozenset({"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)),
                       *(f"lpt{i}" for i in range(10))})


def _relative(path: str) -> PurePosixPath:
    """A plan path, refused unless it is a plain, portable relative path."""
    if not isinstance(path, str) or not path or len(path) > 255:
        raise PlanError(f"plan file path must be a plain relative path: {path!r}")
    for part in path.split("/"):
        if (not _SEGMENT.fullmatch(part) or part.endswith(".")
                or part.split(".")[0].lower() in _RESERVED):
            raise PlanError(f"plan file path must be a plain relative path: {path!r}")
    return PurePosixPath(path)


def _preflight(plan: RenderPlan, outdir: Path) -> None:
    """Refuse, before touching anything, a destination a plan file cannot replace.

    A planned *file* must land on a file or on nothing — never on a directory
    (replacing one would delete what is in it) — and every directory above it
    must be a directory or nothing.
    """
    from .build import _is_link_or_reparse_point

    for record in plan.files:
        relative = _relative(record.path)
        current = outdir
        for part in relative.parts[:-1]:
            current = current / part
            if _is_link_or_reparse_point(current) or (current.exists() and not current.is_dir()):
                raise ValueError(f"cannot write {record.path}: {current} is not a directory")
        destination = outdir / relative
        if _is_link_or_reparse_point(destination) or (destination.exists() and not destination.is_file()):
            raise ValueError(f"cannot write {record.path}: {destination} exists and is not a file")


def write_plan(plan: RenderPlan, outdir: str | Path) -> list[str]:
    """Write a complete plan into ``outdir``; returns :attr:`RenderPlan.produced`.

    Guarantees, and their limits (``docs/RENDER_PLAN.md``):

    * every destination is checked first; a planned file never replaces a
      directory, a link, or a file standing where a directory must be;
    * nothing in ``outdir`` changes until every file is staged, so a failure
      before the commit leaves it exactly as it was, and an output directory
      that did not exist is removed again;
    * files are then moved into place one at a time; if a move fails, the
      files already replaced are restored. If a restore itself fails, the
      backups are *kept* and the error names where they are;
    * this is not crash-atomic: a power loss mid-commit can leave a mixture,
      and an interrupted run can leave a ``.iconflow-staging-*`` directory;
    * files ``outdir`` already holds that the plan does not name are left
      alone, exactly as every earlier release did.
    """
    from .build import _validate_output_tree

    outdir = Path(outdir)
    _validate_output_tree(outdir)
    _preflight(plan, outdir)
    created: list[Path] = []
    probe = outdir
    while not probe.exists():
        created.append(probe)
        probe = probe.parent
    staging: Path | None = None
    keep_staging = False
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".iconflow-staging-", dir=outdir))
        backups = staging / "backup"
        staged = staging / "new"
        for record in plan.files:
            target = staged / _relative(record.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(record.data)
        committed: list[tuple[Path, Path | None]] = []
        try:
            for record in plan.files:
                relative = _relative(record.path)
                destination = outdir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                backup = None
                if destination.exists():
                    backup = backups / relative
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(destination, backup)
                committed.append((destination, backup))
                os.replace(staged / relative, destination)
        except BaseException as exc:
            unrecovered = []
            for destination, backup in reversed(committed):
                try:
                    if backup is not None:
                        os.replace(backup, destination)
                    elif destination.exists():
                        destination.unlink()
                except OSError:
                    unrecovered.append(str(backup or destination))
            if unrecovered:
                keep_staging = True
                raise OSError(
                    f"writing the icon set failed ({exc}) and {len(unrecovered)} file(s) could "
                    f"not be restored; the originals are kept in {backups}: "
                    + ", ".join(unrecovered[:5])
                ) from exc
            raise
    except BaseException:
        if staging is not None and not keep_staging:
            shutil.rmtree(staging, ignore_errors=True)
            staging = None
        if not keep_staging:
            for directory in created:  # innermost first; only those this run made
                if not directory.exists():
                    continue
                try:
                    directory.rmdir()
                except OSError:
                    break
        raise
    if staging is not None:
        shutil.rmtree(staging, ignore_errors=True)
    return plan.produced


def _is_export(directory: Path) -> bool:
    """Whether ``directory`` is exactly a previous, intact plan export.

    Ownership is proven the way an import proves a plan: every entry is one
    the manifest names, with the bytes it records. Anything else — a note
    beside the files, a stray file inside ``files/`` — and it is not ours.
    """
    try:
        load_plan(directory)
    except PlanError:
        return False
    return True


def export_plan(plan: RenderPlan, directory: str | Path) -> Path:
    """Save a plan for ``ship --plan``: ``plan.json`` plus every file under ``files/``.

    The new export is written beside the destination and swapped in only once
    complete, so a failure keeps the previous export. A destination that holds
    anything other than a previous export is refused, never cleared.
    """
    from .build import _is_link_or_reparse_point, _validate_output_tree, link_in_path

    directory = Path(directory)
    link = link_in_path(directory)
    if link is not None:
        raise PlanError(f"the plan directory goes through a link or junction: {link}")
    _validate_output_tree(directory)
    if directory.exists() and any(directory.iterdir()) and not _is_export(directory):
        raise PlanError(f"{directory} holds files that are not a saved plan; choose an empty directory")
    directory.parent.mkdir(parents=True, exist_ok=True)
    fresh = Path(tempfile.mkdtemp(prefix=".iconflow-plan-", dir=directory.parent))
    try:
        for record in plan.files:
            target = fresh / FILES_DIR / _relative(record.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(record.data)
        (fresh / MANIFEST_NAME).write_text(
            json.dumps(plan.manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        retired = None
        if directory.exists():
            retired = directory.with_name(f".{directory.name}.retired-{os.getpid()}")
            if _is_link_or_reparse_point(directory):
                raise PlanError(f"{directory} became a link")
            os.replace(directory, retired)
        try:
            os.replace(fresh, directory)
        except OSError:
            if retired is not None:
                os.replace(retired, directory)
            raise
        if retired is not None:
            shutil.rmtree(retired, ignore_errors=True)
    finally:
        if fresh.exists():
            shutil.rmtree(fresh, ignore_errors=True)
    return directory / MANIFEST_NAME


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise PlanError("plan.json repeats a key")
    return dict(pairs)


def _is_hex64(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def load_plan(directory: str | Path) -> RenderPlan:
    """Import a saved plan as a hostile artifact.

    The directory holds exactly ``plan.json`` and ``files/``; nothing in it is
    a link; ``files/`` holds exactly the files the manifest names, within
    bounds checked while walking. Every identity is recomputed from the bytes
    actually read — the manifest's own hashes are only compared against.
    """
    from .build import _is_link_or_reparse_point, link_in_path

    directory = Path(directory)
    link = link_in_path(directory)
    if link is not None or _is_link_or_reparse_point(directory):
        raise PlanError(f"the plan is read through a link or junction ({link or directory})")
    if not directory.is_dir():
        raise PlanError(f"no saved plan at {directory}")
    root_names = set()
    with os.scandir(directory) as listing:
        for entry in listing:  # incremental: a huge directory stops at the third name
            root_names.add(entry.name)
            if len(root_names) > 2:
                break
    if root_names != {MANIFEST_NAME, FILES_DIR}:
        raise PlanError(f"{directory} must hold exactly {MANIFEST_NAME} and {FILES_DIR}/; "
                        f"found: {', '.join(sorted(root_names)) or 'nothing'}")
    manifest_path = directory / MANIFEST_NAME
    payload_root = directory / FILES_DIR
    for entry in (manifest_path, payload_root):
        if _is_link_or_reparse_point(entry):
            raise PlanError(f"the plan contains a link or junction: {entry}")
    if not manifest_path.is_file() or not payload_root.is_dir():
        raise PlanError(f"{directory} has no {MANIFEST_NAME} file and {FILES_DIR}/ directory")
    if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise PlanError(f"{MANIFEST_NAME} is too large")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeError, ValueError) as exc:
        raise PlanError(f"unreadable {MANIFEST_NAME}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != PLAN_SCHEMA:
        raise PlanError(f"{MANIFEST_NAME} is not a schema-{PLAN_SCHEMA} plan")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_PLAN_FILES:
        raise PlanError(f"{MANIFEST_NAME} has no valid file list")
    for key in ("inputs", "parameters", "toolchain"):
        if not isinstance(manifest.get(key), dict):
            raise PlanError(f"{MANIFEST_NAME} has no {key} object")
    inputs = manifest["inputs"]
    if "master" not in inputs:
        raise PlanError(f"{MANIFEST_NAME} names no master source")
    for role, record in inputs.items():
        if (role not in {"master", "tray", "maskable", "monochrome"} or not isinstance(record, dict)
                or not isinstance(record.get("path"), str) or not _is_hex64(record.get("sha256"))
                or not _is_hex64(record.get("bytes_sha256"))):
            raise PlanError(f"{MANIFEST_NAME} has a malformed {role!r} source record")

    on_disk: set[str] = set()
    seen = 0
    pending = [(payload_root, 0)]
    while pending:
        current, depth = pending.pop()
        if depth > MAX_PLAN_DEPTH:
            raise PlanError("the plan is nested deeper than any icon set")
        try:
            with os.scandir(current) as listing:
                for entry in listing:  # incremental, so the bound holds while reading
                    seen += 1
                    if seen > 4 * MAX_PLAN_FILES:
                        raise PlanError("the plan holds far more entries than any icon set")
                    path = Path(entry.path)
                    if _is_link_or_reparse_point(path):
                        raise PlanError(f"the plan contains a link or junction: {path}")
                    if entry.is_dir(follow_symlinks=False):
                        pending.append((path, depth + 1))
                    elif entry.is_file(follow_symlinks=False):
                        on_disk.add(path.relative_to(payload_root).as_posix())
                    else:
                        raise PlanError(f"the plan contains something that is not a file: {path}")
        except OSError as exc:
            raise PlanError(f"the plan cannot be read: {exc}") from exc

    files: dict[str, bytes] = {}
    total = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise PlanError(f"{MANIFEST_NAME} has a malformed file entry")
        path = entry.get("path")
        _relative(path)
        if path in files:
            raise PlanError(f"{MANIFEST_NAME} names {path} twice")
        if not _is_hex64(entry.get("sha256")) or not _is_hex64(entry.get("content_sha256")):
            raise PlanError(f"{MANIFEST_NAME} entry {path} has no valid hashes")
        target = payload_root / _relative(path)
        if path not in on_disk or not target.is_file():
            raise PlanError(f"the plan is missing {path}")
        size = target.stat().st_size
        total += size
        if total > MAX_PLAN_BYTES:
            raise PlanError("the plan is larger than any icon set could be")
        data = target.read_bytes()
        if len(data) != size or entry.get("bytes") != len(data) or _sha256(data) != entry["sha256"]:
            raise PlanError(f"{path} changed after the plan was saved")
        if content_sha256(path, data) != entry["content_sha256"]:
            raise PlanError(f"{path}: its recorded content identity does not match its bytes")
        files[path] = data
    extra = sorted(on_disk - set(files))
    if extra:
        raise PlanError("the plan holds files its manifest does not name: " + ", ".join(extra[:5]))
    plan = RenderPlan.create(files, inputs=inputs, parameters=manifest["parameters"],
                             toolchain=manifest["toolchain"])
    if (plan.digest != manifest.get("digest") or plan.artifact_digest != manifest.get("artifact_digest")
            or plan.provenance_digest != manifest.get("provenance_digest")):
        raise PlanError(f"{MANIFEST_NAME} digests do not match its files and settings")
    return plan


# ---------------------------------------------------------------- comparison

@dataclass(frozen=True)
class PlanCheck:
    """How a plan compares with the plan a receipt approved."""

    #: True: same content. False: drift. None: nothing to compare against.
    verified: bool | None
    #: True only when every file is byte-identical to the approved one.
    bytes_verified: bool | None
    changed: tuple[str, ...] = ()
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    approved_toolchain: Mapping | None = None

    @property
    def drift(self) -> list[str]:
        return [*self.changed, *self.added, *self.removed]

    def describe(self, plan: RenderPlan) -> dict:
        """The ``outputs.plan`` object of the ``--json`` envelopes."""
        return {
            "digest": plan.digest,
            "artifact_digest": plan.artifact_digest,
            "verified": self.verified,
            "bytes_verified": self.bytes_verified,
            "drift": self.drift,
        }


def validate_binding(value) -> dict:
    """A receipt's ``plan`` object, checked for shape. Raises PlanError."""
    if not isinstance(value, dict):
        raise PlanError("review receipt plan must be an object")
    if value.get("schema") != PLAN_SCHEMA:
        raise PlanError(f"review receipt plan schema must be {PLAN_SCHEMA}")
    for key in ("digest", "artifact_digest", "provenance_digest"):
        if not _is_hex64(value.get(key)):
            raise PlanError(f"review receipt plan.{key} must be a SHA-256 hex digest")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise PlanError("review receipt plan.files must name every approved output")
    for path, entry in files.items():
        _relative(path)
        if (not isinstance(entry, dict) or not _is_hex64(entry.get("content"))
                or not _is_hex64(entry.get("sha256"))):
            raise PlanError(f"review receipt plan.files[{path!r}] is malformed")
    if _listing_digest("content", {p: e["content"] for p, e in files.items()}) != value["digest"]:
        raise PlanError("review receipt plan.digest does not match its file list")
    if value.get("toolchain") is not None and not isinstance(value.get("toolchain"), dict):
        raise PlanError("review receipt plan.toolchain must be an object")
    return value


def compare(binding: Mapping | None, plan: RenderPlan) -> PlanCheck:
    """Compare a plan with an approved binding (None: legacy, unbound)."""
    if binding is None:
        return PlanCheck(verified=None, bytes_verified=None)
    approved = binding["files"]
    current = {r.path: r for r in plan.files}
    changed = tuple(sorted(p for p in set(approved) & set(current)
                           if approved[p]["content"] != current[p].content_sha256))
    added = tuple(sorted(set(current) - set(approved)))
    removed = tuple(sorted(set(approved) - set(current)))
    verified = not (changed or added or removed) and binding["digest"] == plan.digest
    return PlanCheck(
        verified=verified,
        bytes_verified=verified and binding["artifact_digest"] == plan.artifact_digest,
        changed=changed, added=added, removed=removed,
        approved_toolchain=binding.get("toolchain"),
    )
